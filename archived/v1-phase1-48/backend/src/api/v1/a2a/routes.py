# =============================================================================
# IPA Platform - A2A API Routes
# =============================================================================
# Sprint 81: S81-2 - A2A Communication Protocol
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.integrations.a2a import (
    A2AMessage,
    AgentCapability,
    AgentDiscoveryService,
    DiscoveryQuery,
    MessageRouter,
    MessageType,
    MessagePriority,
    A2AAgentStatus,
)


router = APIRouter(prefix="/a2a", tags=["A2A Communication"])


class SendMessageRequest(BaseModel):
    from_agent: str
    to_agent: str
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    priority: str = "normal"
    ttl_seconds: int = 300


class RegisterAgentRequest(BaseModel):
    agent_id: str
    name: str
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    skills: Dict[str, float] = Field(default_factory=dict)
    version: str = "1.0.0"
    endpoint: Optional[str] = None
    max_concurrent_tasks: int = 5
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiscoverAgentsRequest(BaseModel):
    required_capabilities: List[str] = Field(default_factory=list)
    required_tags: List[str] = Field(default_factory=list)
    min_availability: float = Field(default=0.1, ge=0, le=1)
    max_results: int = Field(default=10, ge=1, le=100)
    include_busy: bool = False
    metadata_filters: Dict[str, Any] = Field(default_factory=dict)


class UpdateStatusRequest(BaseModel):
    status: str
    current_load: Optional[int] = None


_discovery_service: Optional[AgentDiscoveryService] = None
_message_router: Optional[MessageRouter] = None


def get_discovery_service() -> AgentDiscoveryService:
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = AgentDiscoveryService()
    return _discovery_service


def get_message_router() -> MessageRouter:
    global _message_router
    if _message_router is None:
        _message_router = MessageRouter()
    return _message_router


@router.post("/message")
async def send_message(request: SendMessageRequest):
    router_instance = get_message_router()
    try:
        msg_type = MessageType(request.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid message type: {request.type}")
    try:
        priority = MessagePriority(request.priority)
    except ValueError:
        priority = MessagePriority.NORMAL
    message = A2AMessage.create(
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        type=msg_type,
        payload=request.payload,
        correlation_id=request.correlation_id,
        priority=priority,
        ttl_seconds=request.ttl_seconds,
    )
    await router_instance.route_message(message)
    return {"message_id": message.message_id, "status": message.status.value}


@router.get("/message/{message_id}")
async def get_message_status(message_id: str):
    router_instance = get_message_router()
    message = router_instance.track_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail=f"Message not found: {message_id}")
    return message.to_dict()


@router.get("/messages/pending")
async def get_pending_messages(agent_id: Optional[str] = None):
    router_instance = get_message_router()
    messages = router_instance.get_pending_messages(agent_id)
    return {"messages": [m.to_dict() for m in messages], "count": len(messages)}


@router.get("/conversation/{correlation_id}")
async def get_conversation(correlation_id: str):
    router_instance = get_message_router()
    messages = router_instance.get_conversation_messages(correlation_id)
    return {"correlation_id": correlation_id, "messages": [m.to_dict() for m in messages]}


@router.post("/agents/register")
async def register_agent(request: RegisterAgentRequest):
    discovery = get_discovery_service()
    agent = AgentCapability(
        agent_id=request.agent_id,
        name=request.name,
        description=request.description,
        capabilities=request.capabilities,
        skills=request.skills,
        version=request.version,
        endpoint=request.endpoint,
        max_concurrent_tasks=request.max_concurrent_tasks,
        tags=request.tags,
        metadata=request.metadata,
    )
    discovery.register_agent(agent)
    return {"agent_id": agent.agent_id, "name": agent.name, "capabilities": agent.capabilities}


@router.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    discovery = get_discovery_service()
    success = discovery.unregister_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return {"message": f"Agent {agent_id} unregistered"}


@router.get("/agents")
async def list_agents():
    discovery = get_discovery_service()
    agents = discovery.get_all_agents()
    return {"agents": [a.to_dict() for a in agents], "count": len(agents)}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    discovery = get_discovery_service()
    agent = discovery.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return agent.to_dict()


@router.post("/agents/discover")
async def discover_agents(request: DiscoverAgentsRequest):
    discovery = get_discovery_service()
    query = DiscoveryQuery(
        required_capabilities=request.required_capabilities,
        required_tags=request.required_tags,
        min_availability=request.min_availability,
        max_results=request.max_results,
        include_busy=request.include_busy,
        metadata_filters=request.metadata_filters,
    )
    result = discovery.discover_agents(query)
    return result.to_dict()


@router.get("/agents/{agent_id}/capabilities")
async def get_agent_capabilities(agent_id: str):
    """Get capabilities of a specific agent."""
    discovery = get_discovery_service()
    agent = discovery.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return {
        "agent_id": agent_id,
        "capabilities": agent.capabilities,
        "skills": agent.skills,
        "tags": agent.tags,
    }


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str):
    discovery = get_discovery_service()
    success = discovery.update_heartbeat(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return {"message": "Heartbeat updated", "agent_id": agent_id}


@router.put("/agents/{agent_id}/status")
async def update_agent_status(agent_id: str, request: UpdateStatusRequest):
    discovery = get_discovery_service()
    try:
        agent_status = A2AAgentStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    success = discovery.update_status(agent_id=agent_id, status=agent_status, current_load=request.current_load)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return {"message": "Status updated", "agent_id": agent_id, "status": agent_status.value}


@router.get("/statistics")
async def get_statistics():
    discovery = get_discovery_service()
    router_instance = get_message_router()
    return {"discovery": discovery.get_statistics(), "router": router_instance.get_statistics()}


@router.post("/maintenance/cleanup")
async def run_cleanup():
    discovery = get_discovery_service()
    router_instance = get_message_router()
    stale_agents = discovery.cleanup_stale_agents()
    expired_messages = router_instance.cleanup_expired()
    return {"stale_agents_removed": stale_agents, "expired_messages_removed": expired_messages}

