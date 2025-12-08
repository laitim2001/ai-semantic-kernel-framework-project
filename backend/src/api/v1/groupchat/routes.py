# =============================================================================
# IPA Platform - GroupChat API Routes
# =============================================================================
# Sprint 9: S9-6 GroupChat API (8 points)
# Sprint 20: S20-1 Migrate to Agent Framework Adapter (8 points)
#
# RESTful API routes for group chat, multi-turn sessions, and voting.
#
# 重要變更 (Sprint 20):
#   - 移除 domain.orchestration.groupchat 依賴
#   - 使用 integrations.agent_framework.builders 適配器
#   - 保持 API 響應格式不變
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from src.api.v1.groupchat.schemas import (
    # GroupChat
    CreateGroupChatRequest,
    GroupChatConfigUpdate,
    GroupChatResponse,
    GroupChatSummaryResponse,
    SendMessageRequest,
    StartConversationRequest,
    ConversationResultResponse,
    MessageResponse,
    # Session
    CreateSessionRequest,
    SessionResponse,
    ExecuteTurnRequest,
    TurnResponse,
    SessionHistoryResponse,
    SessionContextUpdate,
    # Voting
    CreateVotingSessionRequest,
    CastVoteRequest,
    ChangeVoteRequest,
    VoteResponse,
    VotingSessionResponse,
    VotingResultResponse,
    VotingStatisticsResponse,
    # Common
    SuccessResponse,
)

# =============================================================================
# Sprint 20: Agent Framework Adapter Imports (取代 domain.orchestration.groupchat)
# =============================================================================
from src.integrations.agent_framework.builders import (
    # GroupChat Adapter
    GroupChatBuilderAdapter,
    GroupChatParticipant,
    GroupChatMessage,
    GroupChatState,
    GroupChatStatus,
    SpeakerSelectionMethod,
    MessageRole,
    # Voting Adapter (Sprint 20: S20-4)
    GroupChatVotingAdapter,
    VotingMethod,
    VotingConfig,
    Vote,
    VotingResult,
)

# =============================================================================
# Sprint 20: Compatibility Types (為向後兼容定義)
# =============================================================================
from dataclasses import dataclass, field
from enum import Enum


class MessageType(str, Enum):
    """Message types for backward compatibility."""
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"


@dataclass
class AgentInfo:
    """Agent info for backward compatibility with old API.

    Note: Internally converted to GroupChatParticipant.
    """
    agent_id: str
    name: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)

    def to_participant(self) -> GroupChatParticipant:
        """Convert to GroupChatParticipant."""
        return GroupChatParticipant(
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            metadata={"agent_id": self.agent_id},
        )


@dataclass
class GroupChatConfig:
    """GroupChat config for backward compatibility.

    Note: Maps to GroupChatBuilderAdapter constructor parameters.
    """
    max_rounds: int = 10
    max_messages_per_round: int = 5
    speaker_selection_method: SpeakerSelectionMethod = SpeakerSelectionMethod.ROUND_ROBIN
    allow_repeat_speaker: bool = False


class VoteType(str, Enum):
    """Vote types for backward compatibility.

    Maps to VotingMethod in S20-4.
    """
    YES_NO = "yes_no"
    MULTI_CHOICE = "multi_choice"
    RANKING = "ranking"
    WEIGHTED = "weighted"
    APPROVAL = "approval"

    def to_voting_method(self) -> VotingMethod:
        """Convert to VotingMethod."""
        mapping = {
            VoteType.YES_NO: VotingMethod.MAJORITY,
            VoteType.MULTI_CHOICE: VotingMethod.MAJORITY,
            VoteType.RANKING: VotingMethod.RANKED,
            VoteType.WEIGHTED: VotingMethod.WEIGHTED,
            VoteType.APPROVAL: VotingMethod.APPROVAL,
        }
        return mapping.get(self, VotingMethod.MAJORITY)


class VotingSessionStatus(str, Enum):
    """Voting session status for backward compatibility."""
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class VoteResult(str, Enum):
    """Vote result for backward compatibility."""
    PENDING = "pending"
    PASSED = "passed"
    REJECTED = "rejected"
    TIE = "tie"
    NO_QUORUM = "no_quorum"


# =============================================================================
# Sprint 32: S32-2 會話層遷移 (取代 domain.orchestration.multiturn)
# =============================================================================
# 使用 MultiTurnAPIService 包裝 MultiTurnAdapter
# 完整遷移至 integrations.agent_framework.multiturn
from src.api.v1.groupchat.multiturn_service import (
    MultiTurnAPIService,
    MultiTurnSession,
    SessionMessage,
    SessionStatus,
    get_multiturn_service,
)

router = APIRouter(prefix="/groupchat", tags=["GroupChat"])


# =============================================================================
# In-Memory State (for MVP - replace with proper DI in production)
# =============================================================================
# Sprint 20: 使用適配器取代 domain layer managers

# GroupChat adapter storage (取代 GroupChatManager)
_groupchat_states: Dict[str, Dict[str, Any]] = {}  # group_id -> state data
_groupchat_adapters: Dict[str, GroupChatBuilderAdapter] = {}  # group_id -> adapter

# Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
# 透過 get_multiturn_service() 獲取單例實例
_session_service: MultiTurnAPIService = None  # 延遲初始化


def _get_session_service() -> MultiTurnAPIService:
    """Get or create the MultiTurnAPIService instance."""
    global _session_service
    if _session_service is None:
        _session_service = get_multiturn_service()
    return _session_service

# Voting storage (使用 GroupChatVotingAdapter - Sprint 20 S20-4)
_voting_sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session data
_voting_adapters: Dict[str, GroupChatVotingAdapter] = {}  # group_id -> voting adapter

# WebSocket connections
_websocket_connections: Dict[UUID, List[WebSocket]] = {}


# =============================================================================
# Sprint 20: Helper Functions for Backward Compatibility
# =============================================================================

def _create_groupchat_state(
    group_id: str,
    name: str,
    agents: List[AgentInfo],
    config: GroupChatConfig,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a GroupChat state record for backward compatibility."""
    now = datetime.utcnow()
    return {
        "group_id": group_id,
        "name": name,
        "agents": agents,
        "config": config,
        "metadata": metadata or {},
        "messages": [],
        "status": GroupChatStatus.IDLE,
        "current_round": 0,
        "message_count": 0,
        "created_at": now,
        "started_at": None,
        "ended_at": None,
    }


@dataclass
class MessageRecord:
    """Message record for backward compatibility."""
    id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: MessageType
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class VoteRecord:
    """Vote record for backward compatibility (replaces domain VotingManager)."""
    vote_id: str
    voter_id: str
    voter_name: str
    choice: str
    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: Optional[str] = None


@dataclass
class VotingSessionRecord:
    """Voting session record for backward compatibility.

    Sprint 20: 取代 domain.orchestration.groupchat.VotingManager
    """
    session_id: str
    group_id: Optional[UUID]
    topic: str
    description: str
    vote_type: VoteType
    options: List[str]
    status: VotingSessionStatus = VotingSessionStatus.ACTIVE
    result: VoteResult = VoteResult.PENDING
    votes: Dict[str, VoteRecord] = field(default_factory=dict)
    required_quorum: float = 0.5
    pass_threshold: float = 0.5
    eligible_voters: Optional[set] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None

    @property
    def vote_count(self) -> int:
        return len(self.votes)

    @property
    def participation_rate(self) -> float:
        if self.eligible_voters:
            return self.vote_count / len(self.eligible_voters) if self.eligible_voters else 0
        return 0.0


# =============================================================================
# GroupChat Routes
# =============================================================================


@router.post("/", response_model=GroupChatResponse, status_code=201)
async def create_group_chat(request: CreateGroupChatRequest):
    """Create a new group chat.

    建立新的群組聊天。

    Sprint 20: 使用 GroupChatBuilderAdapter 取代 GroupChatManager
    """
    # Create agent info from IDs
    agents = [
        AgentInfo(
            agent_id=agent_id,
            name=f"Agent-{agent_id[:8]}",
            description="",
            capabilities=[],
        )
        for agent_id in request.agent_ids
    ]

    # Create config
    config_data = request.config or {}
    config = GroupChatConfig(
        max_rounds=config_data.get("max_rounds", 10),
        max_messages_per_round=config_data.get("max_messages_per_round", 5),
        speaker_selection_method=SpeakerSelectionMethod(
            config_data.get("speaker_selection_method", "round_robin")
        ),
        allow_repeat_speaker=config_data.get("allow_repeat_speaker", False),
    )

    # Sprint 20: 使用適配器取代 manager
    group_id = str(uuid4())
    metadata = {
        "description": request.description,
        "workflow_id": str(request.workflow_id) if request.workflow_id else None,
    }

    # Convert agents to participants for adapter
    participants = [agent.to_participant() for agent in agents]

    # Create adapter instance
    adapter = GroupChatBuilderAdapter(
        id=group_id,
        participants=participants,
        selection_method=config.speaker_selection_method,
        max_rounds=config.max_rounds,
        config={"allow_repeat_speaker": config.allow_repeat_speaker},
    )

    # Store state and adapter
    state = _create_groupchat_state(group_id, request.name, agents, config, metadata)
    _groupchat_states[group_id] = state
    _groupchat_adapters[group_id] = adapter

    return GroupChatResponse(
        group_id=UUID(group_id),
        name=request.name,
        description=request.description,
        status=state["status"].value,
        participants=[a.name for a in agents],
        message_count=state["message_count"],
        current_round=state["current_round"],
        created_at=state["created_at"],
    )


@router.get("/", response_model=List[GroupChatResponse])
async def list_group_chats(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all group chats.

    列出所有群組聊天。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    # Sprint 20: 從 in-memory state 讀取
    all_states = list(_groupchat_states.values())
    states = all_states[offset:offset + limit]

    return [
        GroupChatResponse(
            group_id=UUID(s["group_id"]),
            name=s["name"],
            description=s["metadata"].get("description", ""),
            status=s["status"].value,
            participants=[a.name for a in s["agents"]],
            message_count=s["message_count"],
            current_round=s["current_round"],
            created_at=s["created_at"],
            updated_at=s["started_at"],
        )
        for s in states
    ]


@router.get("/{group_id}", response_model=GroupChatResponse)
async def get_group_chat(group_id: UUID):
    """Get group chat details.

    獲取群組聊天詳情。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    return GroupChatResponse(
        group_id=UUID(state["group_id"]),
        name=state["name"],
        description=state["metadata"].get("description", ""),
        status=state["status"].value,
        participants=[a.name for a in state["agents"]],
        message_count=state["message_count"],
        current_round=state["current_round"],
        created_at=state["created_at"],
        updated_at=state["started_at"],
    )


@router.patch("/{group_id}/config", response_model=SuccessResponse)
async def update_group_config(group_id: UUID, config: GroupChatConfigUpdate):
    """Update group chat configuration.

    更新群組聊天配置。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Update config in state
    current_config = state["config"]
    if config.max_rounds is not None:
        current_config.max_rounds = config.max_rounds
    if config.max_messages_per_round is not None:
        current_config.max_messages_per_round = config.max_messages_per_round
    if config.speaker_selection_method is not None:
        current_config.speaker_selection_method = SpeakerSelectionMethod(
            config.speaker_selection_method
        )
    if config.allow_repeat_speaker is not None:
        current_config.allow_repeat_speaker = config.allow_repeat_speaker

    return SuccessResponse(message="Configuration updated")


@router.post("/{group_id}/agents/{agent_id}", response_model=SuccessResponse)
async def add_agent_to_group(
    group_id: UUID,
    agent_id: str,
    name: str = Query(...),
    capabilities: List[str] = Query(default=[]),
):
    """Add an agent to the group chat.

    添加 Agent 到群組聊天。

    Sprint 20: 使用 _groupchat_states 和 adapter 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    adapter = _groupchat_adapters.get(str(group_id))
    if not state or not adapter:
        raise HTTPException(status_code=404, detail="Group chat not found")

    agent = AgentInfo(
        agent_id=agent_id,
        name=name,
        capabilities=capabilities,
    )

    # Add to state
    state["agents"].append(agent)

    # Add to adapter
    try:
        adapter.add_participant(agent.to_participant())
    except ValueError as e:
        # Remove from state if adapter fails
        state["agents"].pop()
        raise HTTPException(status_code=400, detail=str(e))

    return SuccessResponse(message=f"Agent {agent_id} added to group")


@router.delete("/{group_id}/agents/{agent_id}", response_model=SuccessResponse)
async def remove_agent_from_group(group_id: UUID, agent_id: str):
    """Remove an agent from the group chat.

    從群組聊天移除 Agent。

    Sprint 20: 使用 _groupchat_states 和 adapter 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    adapter = _groupchat_adapters.get(str(group_id))
    if not state or not adapter:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Find and remove agent from state
    agent_to_remove = None
    for i, agent in enumerate(state["agents"]):
        if agent.agent_id == agent_id:
            agent_to_remove = state["agents"].pop(i)
            break

    if not agent_to_remove:
        raise HTTPException(status_code=404, detail="Agent not found in group")

    # Remove from adapter
    adapter.remove_participant(agent_to_remove.name)

    return SuccessResponse(message=f"Agent {agent_id} removed from group")


@router.post("/{group_id}/start", response_model=ConversationResultResponse)
async def start_conversation(group_id: UUID, request: StartConversationRequest):
    """Start a group conversation.

    開始群組對話。

    Sprint 20: 使用 _groupchat_states 和 adapter 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    adapter = _groupchat_adapters.get(str(group_id))
    if not state or not adapter:
        raise HTTPException(status_code=404, detail="Group chat not found")

    try:
        # Update state
        state["status"] = GroupChatStatus.RUNNING
        state["started_at"] = datetime.utcnow()

        # Add initial message
        initial_message = MessageRecord(
            id=str(uuid4()),
            sender_id=request.initiator,
            sender_name=request.initiator,
            content=request.initial_message,
            message_type=MessageType.USER,
            timestamp=datetime.utcnow(),
        )
        state["messages"].append(initial_message)
        state["message_count"] += 1

        # Initialize adapter
        await adapter.initialize()

        return ConversationResultResponse(
            status="started",
            rounds_completed=state["current_round"],
            messages=[m.to_dict() for m in state["messages"]],
            termination_reason=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{group_id}/message", response_model=MessageResponse)
async def send_message(group_id: UUID, request: SendMessageRequest):
    """Send a message to the group.

    發送訊息到群組。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Create message record
    message = MessageRecord(
        id=str(uuid4()),
        sender_id=request.sender_name,
        sender_name=request.sender_name,
        content=request.content,
        message_type=MessageType.USER,
        timestamp=datetime.utcnow(),
        metadata=request.metadata or {},
    )

    # Add to state
    state["messages"].append(message)
    state["message_count"] += 1

    # Broadcast to WebSocket connections
    await _broadcast_to_group(group_id, {
        "type": "message",
        "data": message.to_dict(),
    })

    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        content=message.content,
        message_type=message.message_type.value,
        timestamp=message.timestamp,
        metadata=message.metadata,
    )


@router.get("/{group_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    group_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Get messages from the group chat.

    獲取群組聊天訊息。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    messages = state["messages"][offset:offset + limit]

    return [
        MessageResponse(
            id=m.id,
            sender_id=m.sender_id,
            sender_name=m.sender_name,
            content=m.content,
            message_type=m.message_type.value,
            timestamp=m.timestamp,
            metadata=m.metadata,
        )
        for m in messages
    ]


@router.get("/{group_id}/transcript")
async def get_transcript(group_id: UUID):
    """Get the full conversation transcript.

    獲取完整對話記錄。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    transcript = []
    for msg in state["messages"]:
        transcript.append({
            "speaker": msg.sender_name,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        })

    return {"transcript": transcript}


@router.get("/{group_id}/summary", response_model=GroupChatSummaryResponse)
async def get_summary(group_id: UUID):
    """Get group chat summary.

    獲取群組聊天摘要。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Calculate messages per participant
    messages_per_participant: Dict[str, int] = {}
    for msg in state["messages"]:
        messages_per_participant[msg.sender_name] = (
            messages_per_participant.get(msg.sender_name, 0) + 1
        )

    # Calculate duration
    duration = None
    if state["started_at"] and state["ended_at"]:
        duration = (state["ended_at"] - state["started_at"]).total_seconds()

    return GroupChatSummaryResponse(
        group_id=UUID(state["group_id"]),
        name=state["name"],
        total_rounds=state["current_round"],
        total_messages=len(state["messages"]),
        participants=[a.name for a in state["agents"]],
        duration_seconds=duration,
        termination_reason=state["metadata"].get("termination_reason"),
        messages_per_participant=messages_per_participant,
    )


@router.post("/{group_id}/terminate", response_model=SuccessResponse)
async def terminate_group_chat(
    group_id: UUID,
    reason: str = Query(default="manual_termination"),
):
    """Terminate the group chat.

    終止群組聊天。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    state = _groupchat_states.get(str(group_id))
    adapter = _groupchat_adapters.get(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Update state
    state["status"] = GroupChatStatus.COMPLETED
    state["ended_at"] = datetime.utcnow()
    state["metadata"]["termination_reason"] = reason

    # Cleanup adapter if exists
    if adapter:
        await adapter.cleanup()

    # Notify WebSocket clients
    await _broadcast_to_group(group_id, {
        "type": "terminated",
        "reason": reason,
    })

    return SuccessResponse(message=f"Group chat terminated: {reason}")


@router.delete("/{group_id}", response_model=SuccessResponse)
async def delete_group_chat(group_id: UUID):
    """Delete a group chat.

    刪除群組聊天。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    gid = str(group_id)
    if gid not in _groupchat_states:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Remove state
    del _groupchat_states[gid]

    # Cleanup and remove adapter
    if gid in _groupchat_adapters:
        adapter = _groupchat_adapters.pop(gid)
        await adapter.cleanup()

    return SuccessResponse(message="Group chat deleted")


# =============================================================================
# WebSocket Routes
# =============================================================================


@router.websocket("/{group_id}/ws")
async def websocket_endpoint(websocket: WebSocket, group_id: UUID):
    """WebSocket endpoint for real-time group chat.

    WebSocket 端點用於實時群組聊天。

    Sprint 20: 使用 _groupchat_states 取代 GroupChatManager
    """
    await websocket.accept()

    # Register connection
    if group_id not in _websocket_connections:
        _websocket_connections[group_id] = []
    _websocket_connections[group_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                # Sprint 20: 使用 _groupchat_states 取代 manager
                state = _groupchat_states.get(str(group_id))
                if state:
                    message = MessageRecord(
                        id=str(uuid4()),
                        sender_id=data.get("sender", "user"),
                        sender_name=data.get("sender", "user"),
                        content=data.get("content", ""),
                        message_type=MessageType.USER,
                        timestamp=datetime.utcnow(),
                    )
                    state["messages"].append(message)
                    state["message_count"] += 1

                    # Broadcast to all connections
                    await _broadcast_to_group(group_id, {
                        "type": "message",
                        "data": message.to_dict(),
                    })

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif data.get("type") == "terminate":
                await _broadcast_to_group(group_id, {
                    "type": "terminated",
                    "reason": "websocket_request",
                })
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })
    finally:
        # Unregister connection
        if group_id in _websocket_connections:
            _websocket_connections[group_id].remove(websocket)


async def _broadcast_to_group(group_id: UUID, message: Dict[str, Any]):
    """Broadcast message to all WebSocket connections for a group."""
    connections = _websocket_connections.get(group_id, [])
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            pass


# =============================================================================
# Multi-turn Session Routes
# =============================================================================


@router.post("/sessions/", response_model=SessionResponse, status_code=201)
async def create_session(request: CreateSessionRequest):
    """Create a new multi-turn session.

    建立新的多輪對話會話。

    Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
    """
    service = _get_session_service()
    session = await service.create_session(
        user_id=request.user_id,
        initial_context=request.initial_context,
    )

    return SessionResponse(
        session_id=UUID(session.session_id),
        user_id=session.user_id,
        status=session.status.value,
        turn_count=session.current_turn,
        context=session.context,
        created_at=session.created_at,
        updated_at=session.last_activity,
        expires_at=session.expires_at,
    )


@router.get("/sessions/", response_model=List[SessionResponse])
async def list_sessions(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List multi-turn sessions.

    列出多輪對話會話。

    Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
    """
    service = _get_session_service()
    sessions = await service.list_sessions(user_id=user_id)

    if status:
        sessions = [s for s in sessions if s.status.value == status]

    sessions = sessions[offset:offset + limit]

    return [
        SessionResponse(
            session_id=UUID(s.session_id),
            user_id=s.user_id,
            status=s.status.value,
            turn_count=s.current_turn,
            context=s.context,
            created_at=s.created_at,
            updated_at=s.last_activity,
            expires_at=s.expires_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID):
    """Get session details.

    獲取會話詳情。

    Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
    """
    service = _get_session_service()
    session = await service.get_session(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=UUID(session.session_id),
        user_id=session.user_id,
        status=session.status.value,
        turn_count=session.current_turn,
        context=session.context,
        created_at=session.created_at,
        updated_at=session.last_activity,
        expires_at=session.expires_at,
    )


@router.post("/sessions/{session_id}/turns", response_model=TurnResponse)
async def execute_turn(session_id: UUID, request: ExecuteTurnRequest):
    """Execute a turn in the session.

    執行對話輪次。

    Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
    """
    service = _get_session_service()
    session = await service.get_session(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        import time
        start_time = time.time()

        # Simple mock agent handler for MVP
        def mock_agent_handler(agent_id: str, user_input: str, history: list) -> str:
            return f"Response to: {user_input}"

        # Execute turn with mock handler (Sprint 32: 透過 service 執行)
        response_message = await service.execute_turn(
            session_id=str(session_id),
            user_input=request.user_input,
            agent_handler=mock_agent_handler,
            agent_id=request.agent_id,
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        if not response_message:
            raise HTTPException(status_code=500, detail="Failed to execute turn")

        # Get updated session for turn number (Sprint 32: 透過 service 獲取)
        updated_session = await service.get_session(str(session_id))

        return TurnResponse(
            turn_id=UUID(response_message.message_id),
            turn_number=response_message.turn_number,
            user_input=request.user_input,
            agent_response=response_message.content,
            agent_id=response_message.sender_id,
            processing_time_ms=processing_time_ms,
            timestamp=response_message.timestamp,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get session turn history.

    獲取會話輪次歷史。

    Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
    """
    service = _get_session_service()
    history = await service.get_history(str(session_id), limit=limit)

    # Group messages by turn to create turn responses
    turns_by_number: Dict[int, Dict[str, Any]] = {}
    for msg in history:
        turn_num = msg.turn_number
        if turn_num not in turns_by_number:
            turns_by_number[turn_num] = {
                "turn_id": msg.message_id,
                "turn_number": turn_num,
                "user_input": "",
                "agent_response": "",
                "agent_id": None,
                "timestamp": msg.timestamp,
            }
        if msg.role == "user":
            turns_by_number[turn_num]["user_input"] = msg.content
        elif msg.role == "agent":
            turns_by_number[turn_num]["agent_response"] = msg.content
            turns_by_number[turn_num]["agent_id"] = msg.sender_id

    return SessionHistoryResponse(
        session_id=session_id,
        turns=[
            TurnResponse(
                turn_id=UUID(t["turn_id"]),
                turn_number=t["turn_number"],
                user_input=t["user_input"],
                agent_response=t["agent_response"],
                agent_id=t["agent_id"],
                processing_time_ms=0,
                timestamp=t["timestamp"],
            )
            for t in sorted(turns_by_number.values(), key=lambda x: x["turn_number"])
        ],
        total_turns=len(turns_by_number),
    )


@router.patch("/sessions/{session_id}/context", response_model=SuccessResponse)
async def update_session_context(session_id: UUID, request: SessionContextUpdate):
    """Update session context.

    更新會話上下文。

    Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
    """
    service = _get_session_service()
    result = await service.update_session(
        str(session_id),
        context=request.context,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return SuccessResponse(message="Context updated")


@router.post("/sessions/{session_id}/close", response_model=SuccessResponse)
async def close_session(session_id: UUID):
    """Close a session.

    關閉會話。

    Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
    """
    service = _get_session_service()
    result = await service.close_session(str(session_id))
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return SuccessResponse(message="Session closed")


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: UUID):
    """Delete a session.

    刪除會話。

    Sprint 32: 使用 MultiTurnAPIService (取代 MultiTurnSessionManager)
    """
    service = _get_session_service()
    result = await service.delete_session(str(session_id))
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return SuccessResponse(message="Session deleted")


# =============================================================================
# Voting Routes
# =============================================================================
# Sprint 20: 使用 _voting_sessions 取代 VotingManager


@router.post("/voting/", response_model=VotingSessionResponse, status_code=201)
async def create_voting_session(request: CreateVotingSessionRequest):
    """Create a new voting session.

    建立新的投票會話。

    Sprint 20: 使用 VotingSessionRecord 取代 VotingManager
    """
    try:
        vote_type = VoteType(request.vote_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid vote type: {request.vote_type}")

    # Sprint 20: 使用 in-memory storage
    session_id = str(uuid4())
    deadline = None
    if request.deadline_minutes:
        from datetime import timedelta
        deadline = datetime.utcnow() + timedelta(minutes=request.deadline_minutes)

    session = VotingSessionRecord(
        session_id=session_id,
        group_id=request.group_id,
        topic=request.topic,
        description=request.description or "",
        vote_type=vote_type,
        options=request.options,
        required_quorum=request.required_quorum or 0.5,
        pass_threshold=request.pass_threshold or 0.5,
        eligible_voters=set(request.eligible_voters) if request.eligible_voters else None,
        deadline=deadline,
    )

    _voting_sessions[session_id] = session

    return VotingSessionResponse(
        session_id=UUID(session.session_id),
        group_id=session.group_id,
        topic=session.topic,
        description=session.description,
        vote_type=session.vote_type.value,
        options=session.options,
        status=session.status.value,
        result=session.result.value,
        vote_count=session.vote_count,
        participation_rate=session.participation_rate,
        required_quorum=session.required_quorum,
        pass_threshold=session.pass_threshold,
        created_at=session.created_at,
        deadline=session.deadline,
    )


@router.get("/voting/", response_model=List[VotingSessionResponse])
async def list_voting_sessions(
    group_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
):
    """List voting sessions.

    列出投票會話。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    sessions = list(_voting_sessions.values())

    # Filter by group_id
    if group_id:
        sessions = [s for s in sessions if s.group_id == group_id]

    # Filter by status
    if status:
        try:
            voting_status = VotingSessionStatus(status)
            sessions = [s for s in sessions if s.status == voting_status]
        except ValueError:
            pass

    return [
        VotingSessionResponse(
            session_id=UUID(s.session_id),
            group_id=s.group_id,
            topic=s.topic,
            description=s.description,
            vote_type=s.vote_type.value,
            options=s.options,
            status=s.status.value,
            result=s.result.value,
            vote_count=s.vote_count,
            participation_rate=s.participation_rate,
            required_quorum=s.required_quorum,
            pass_threshold=s.pass_threshold,
            created_at=s.created_at,
            deadline=s.deadline,
        )
        for s in sessions
    ]


@router.get("/voting/{session_id}", response_model=VotingSessionResponse)
async def get_voting_session(session_id: UUID):
    """Get voting session details.

    獲取投票會話詳情。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    return VotingSessionResponse(
        session_id=UUID(session.session_id),
        group_id=session.group_id,
        topic=session.topic,
        description=session.description,
        vote_type=session.vote_type.value,
        options=session.options,
        status=session.status.value,
        result=session.result.value,
        vote_count=session.vote_count,
        participation_rate=session.participation_rate,
        required_quorum=session.required_quorum,
        pass_threshold=session.pass_threshold,
        created_at=session.created_at,
        deadline=session.deadline,
    )


@router.post("/voting/{session_id}/vote", response_model=VoteResponse)
async def cast_vote(session_id: UUID, request: CastVoteRequest):
    """Cast a vote.

    投票。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    if session.status != VotingSessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Voting session is not active")

    if request.voter_id in session.votes:
        raise HTTPException(status_code=400, detail="Voter has already voted")

    if request.choice not in session.options:
        raise HTTPException(status_code=400, detail=f"Invalid choice: {request.choice}")

    vote = VoteRecord(
        vote_id=str(uuid4()),
        voter_id=request.voter_id,
        voter_name=request.voter_name,
        choice=request.choice,
        weight=request.weight or 1.0,
        reason=request.reason,
    )

    session.votes[request.voter_id] = vote

    return VoteResponse(
        vote_id=UUID(vote.vote_id),
        voter_id=vote.voter_id,
        voter_name=vote.voter_name,
        choice=vote.choice,
        weight=vote.weight,
        timestamp=vote.timestamp,
        reason=vote.reason,
    )


@router.patch("/voting/{session_id}/vote/{voter_id}", response_model=VoteResponse)
async def change_vote(session_id: UUID, voter_id: str, request: ChangeVoteRequest):
    """Change a vote.

    更改投票。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    if voter_id not in session.votes:
        raise HTTPException(status_code=404, detail="Vote not found")

    if session.status != VotingSessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Voting session is not active")

    if request.new_choice not in session.options:
        raise HTTPException(status_code=400, detail=f"Invalid choice: {request.new_choice}")

    # Update vote
    vote = session.votes[voter_id]
    vote.choice = request.new_choice
    vote.timestamp = datetime.utcnow()
    if request.reason:
        vote.reason = request.reason

    return VoteResponse(
        vote_id=UUID(vote.vote_id),
        voter_id=vote.voter_id,
        voter_name=vote.voter_name,
        choice=vote.choice,
        weight=vote.weight,
        timestamp=vote.timestamp,
        reason=vote.reason,
    )


@router.delete("/voting/{session_id}/vote/{voter_id}", response_model=SuccessResponse)
async def withdraw_vote(session_id: UUID, voter_id: str):
    """Withdraw a vote.

    撤回投票。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    if voter_id not in session.votes:
        raise HTTPException(status_code=404, detail="Vote not found")

    if session.status != VotingSessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Voting session is not active")

    del session.votes[voter_id]

    return SuccessResponse(message="Vote withdrawn")


@router.get("/voting/{session_id}/votes", response_model=List[VoteResponse])
async def get_votes(session_id: UUID):
    """Get all votes for a session.

    獲取會話的所有投票。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    return [
        VoteResponse(
            vote_id=UUID(v.vote_id),
            voter_id=v.voter_id,
            voter_name=v.voter_name,
            choice=v.choice,
            weight=v.weight,
            timestamp=v.timestamp,
            reason=v.reason,
        )
        for v in session.votes.values()
    ]


@router.post("/voting/{session_id}/calculate", response_model=VotingResultResponse)
async def calculate_voting_result(
    session_id: UUID,
    total_eligible_voters: Optional[int] = Query(None),
):
    """Calculate voting result.

    計算投票結果。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    # Calculate vote counts by choice
    vote_counts: Dict[str, float] = {}
    for vote in session.votes.values():
        vote_counts[vote.choice] = vote_counts.get(vote.choice, 0) + vote.weight

    total_votes = len(session.votes)
    total_weight = sum(v.weight for v in session.votes.values())

    # Calculate participation rate
    eligible_count = total_eligible_voters or (len(session.eligible_voters) if session.eligible_voters else total_votes)
    participation_rate = total_votes / eligible_count if eligible_count > 0 else 0

    # Determine result based on vote type
    if participation_rate < session.required_quorum:
        session.result = VoteResult.NO_QUORUM
    else:
        # Find winner
        if vote_counts:
            winner = max(vote_counts, key=vote_counts.get)
            winner_ratio = vote_counts[winner] / total_weight if total_weight > 0 else 0
            if winner_ratio >= session.pass_threshold:
                session.result = VoteResult.PASSED
            else:
                session.result = VoteResult.REJECTED
        else:
            session.result = VoteResult.TIE

    result_details = {
        "vote_counts": vote_counts,
        "total_votes": total_votes,
        "total_weight": total_weight,
        "participation_rate": participation_rate,
        "required_quorum": session.required_quorum,
        "pass_threshold": session.pass_threshold,
    }

    return VotingResultResponse(
        session_id=session_id,
        result=session.result.value,
        result_details=result_details,
        participation_rate=participation_rate,
        total_votes=total_votes,
    )


@router.get("/voting/{session_id}/statistics", response_model=VotingStatisticsResponse)
async def get_voting_statistics(session_id: UUID):
    """Get voting statistics.

    獲取投票統計。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    votes = list(session.votes.values())
    first_vote = min((v.timestamp for v in votes), default=None) if votes else None
    last_vote = max((v.timestamp for v in votes), default=None) if votes else None

    return VotingStatisticsResponse(
        session_id=UUID(session.session_id),
        topic=session.topic,
        vote_type=session.vote_type.value,
        status=session.status.value,
        result=session.result.value,
        total_votes=session.vote_count,
        eligible_voters=len(session.eligible_voters) if session.eligible_voters else 0,
        participation_rate=session.participation_rate,
        first_vote=first_vote,
        last_vote=last_vote,
    )


@router.post("/voting/{session_id}/close", response_model=SuccessResponse)
async def close_voting_session(session_id: UUID):
    """Close a voting session.

    關閉投票會話。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    session.status = VotingSessionStatus.CLOSED

    return SuccessResponse(message="Voting session closed")


@router.post("/voting/{session_id}/cancel", response_model=SuccessResponse)
async def cancel_voting_session(
    session_id: UUID,
    reason: str = Query(default=""),
):
    """Cancel a voting session.

    取消投票會話。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    session = _voting_sessions.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    session.status = VotingSessionStatus.CANCELLED

    return SuccessResponse(message=f"Voting session cancelled: {reason}")


@router.delete("/voting/{session_id}", response_model=SuccessResponse)
async def delete_voting_session(session_id: UUID):
    """Delete a voting session.

    刪除投票會話。

    Sprint 20: 使用 _voting_sessions 取代 VotingManager
    """
    sid = str(session_id)
    if sid not in _voting_sessions:
        raise HTTPException(status_code=404, detail="Voting session not found")

    del _voting_sessions[sid]

    return SuccessResponse(message="Voting session deleted")


# =============================================================================
# Sprint 16: Agent Framework GroupChatBuilder Adapter Routes
# =============================================================================

from src.api.v1.groupchat.schemas import (
    # Sprint 16 schemas
    ParticipantSchema,
    MessageSchema,
    CreateGroupChatAdapterRequest,
    RunGroupChatAdapterRequest,
    GroupChatAdapterResponse,
    GroupChatResultSchema,
    ManagerSelectionRequestSchema,
    ManagerSelectionResponseSchema,
    OrchestratorStateSchema,
)

# Agent Framework adapter imports
try:
    from src.integrations.agent_framework.builders import (
        GroupChatBuilderAdapter,
        GroupChatParticipant,
        GroupChatMessage,
        SpeakerSelectionMethod,
        MessageRole,
        GroupChatOrchestrator,
        ManagerSelectionRequest,
        ManagerSelectionResponse,
    )
    _adapter_available = True
except ImportError:
    _adapter_available = False

# In-memory adapter storage
_groupchat_adapters: Dict[str, Any] = {}


@router.post("/adapter/", response_model=GroupChatAdapterResponse, status_code=201)
async def create_groupchat_adapter(request: CreateGroupChatAdapterRequest):
    """Create a new GroupChat adapter (Sprint 16).

    創建新的 GroupChat 適配器（使用 Agent Framework）。
    """
    if not _adapter_available:
        raise HTTPException(
            status_code=501,
            detail="Agent Framework adapter not available"
        )

    if request.id in _groupchat_adapters:
        raise HTTPException(
            status_code=409,
            detail=f"Adapter '{request.id}' already exists"
        )

    # Convert participants
    participants = [
        GroupChatParticipant(
            name=p.name,
            description=p.description,
            capabilities=p.capabilities,
            metadata=p.metadata,
        )
        for p in request.participants
    ]

    # Create adapter
    try:
        selection_method = SpeakerSelectionMethod(request.selection_method)
    except ValueError:
        selection_method = SpeakerSelectionMethod.ROUND_ROBIN

    adapter = GroupChatBuilderAdapter(
        id=request.id,
        participants=participants,
        selection_method=selection_method,
        max_rounds=request.max_rounds,
        config=request.config,
    )

    # Initialize adapter
    await adapter.initialize()

    # Store adapter
    _groupchat_adapters[request.id] = adapter

    return GroupChatAdapterResponse(
        id=adapter.id,
        status=adapter.status.value,
        selection_method=adapter.selection_method.value,
        participants=list(adapter.participants.keys()),
        is_built=adapter.is_built,
        is_initialized=adapter.is_initialized,
    )


@router.get("/adapter/", response_model=List[GroupChatAdapterResponse])
async def list_groupchat_adapters():
    """List all GroupChat adapters.

    列出所有 GroupChat 適配器。
    """
    if not _adapter_available:
        return []

    return [
        GroupChatAdapterResponse(
            id=adapter.id,
            status=adapter.status.value,
            selection_method=adapter.selection_method.value,
            participants=list(adapter.participants.keys()),
            is_built=adapter.is_built,
            is_initialized=adapter.is_initialized,
        )
        for adapter in _groupchat_adapters.values()
    ]


@router.get("/adapter/{adapter_id}", response_model=GroupChatAdapterResponse)
async def get_groupchat_adapter(adapter_id: str):
    """Get GroupChat adapter details.

    獲取 GroupChat 適配器詳情。
    """
    if adapter_id not in _groupchat_adapters:
        raise HTTPException(status_code=404, detail="Adapter not found")

    adapter = _groupchat_adapters[adapter_id]

    return GroupChatAdapterResponse(
        id=adapter.id,
        status=adapter.status.value,
        selection_method=adapter.selection_method.value,
        participants=list(adapter.participants.keys()),
        is_built=adapter.is_built,
        is_initialized=adapter.is_initialized,
    )


@router.post("/adapter/{adapter_id}/run", response_model=GroupChatResultSchema)
async def run_groupchat_adapter(adapter_id: str, request: RunGroupChatAdapterRequest):
    """Run GroupChat adapter.

    執行 GroupChat 適配器。
    """
    if adapter_id not in _groupchat_adapters:
        raise HTTPException(status_code=404, detail="Adapter not found")

    adapter = _groupchat_adapters[adapter_id]

    try:
        result = await adapter.run(request.input_message)

        # Convert result to schema
        conversation = []
        for msg in result.conversation:
            conversation.append(MessageSchema(
                role=msg.role.value,
                content=msg.content,
                author_name=msg.author_name,
                timestamp=msg.timestamp,
                metadata=msg.metadata,
            ))

        final_message = None
        if result.final_message:
            final_message = MessageSchema(
                role=result.final_message.role.value,
                content=result.final_message.content,
                author_name=result.final_message.author_name,
                timestamp=result.final_message.timestamp,
                metadata=result.final_message.metadata,
            )

        return GroupChatResultSchema(
            status=result.status.value,
            conversation=conversation,
            final_message=final_message,
            total_rounds=result.total_rounds,
            participants_involved=result.participants_involved,
            duration=result.duration,
            metadata=result.metadata,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adapter/{adapter_id}/participants", response_model=SuccessResponse)
async def add_adapter_participant(adapter_id: str, participant: ParticipantSchema):
    """Add participant to adapter.

    添加參與者到適配器。
    """
    if adapter_id not in _groupchat_adapters:
        raise HTTPException(status_code=404, detail="Adapter not found")

    adapter = _groupchat_adapters[adapter_id]

    try:
        new_participant = GroupChatParticipant(
            name=participant.name,
            description=participant.description,
            capabilities=participant.capabilities,
            metadata=participant.metadata,
        )
        adapter.add_participant(new_participant)
        return SuccessResponse(message=f"Participant '{participant.name}' added")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/adapter/{adapter_id}/participants/{name}", response_model=SuccessResponse)
async def remove_adapter_participant(adapter_id: str, name: str):
    """Remove participant from adapter.

    從適配器移除參與者。
    """
    if adapter_id not in _groupchat_adapters:
        raise HTTPException(status_code=404, detail="Adapter not found")

    adapter = _groupchat_adapters[adapter_id]

    if adapter.remove_participant(name):
        return SuccessResponse(message=f"Participant '{name}' removed")
    else:
        raise HTTPException(status_code=404, detail="Participant not found")


@router.delete("/adapter/{adapter_id}", response_model=SuccessResponse)
async def delete_groupchat_adapter(adapter_id: str):
    """Delete GroupChat adapter.

    刪除 GroupChat 適配器。
    """
    if adapter_id not in _groupchat_adapters:
        raise HTTPException(status_code=404, detail="Adapter not found")

    adapter = _groupchat_adapters.pop(adapter_id)
    await adapter.cleanup()

    return SuccessResponse(message=f"Adapter '{adapter_id}' deleted")


# =============================================================================
# Sprint 16: Orchestrator Routes (S16-3)
# =============================================================================


@router.post("/orchestrator/select", response_model=ManagerSelectionResponseSchema)
async def orchestrator_select_speaker(request: ManagerSelectionRequestSchema):
    """Select next speaker using orchestrator logic.

    使用編排器邏輯選擇下一位發言者。
    """
    if not _adapter_available:
        raise HTTPException(
            status_code=501,
            detail="Agent Framework adapter not available"
        )

    # Simple round-robin selection for demonstration
    participants = list(request.participants.keys())
    if not participants:
        return ManagerSelectionResponseSchema(
            finish=True,
            final_message="No participants available"
        )

    # Select based on round index
    selected_idx = request.round_index % len(participants)
    selected = participants[selected_idx]

    return ManagerSelectionResponseSchema(
        selected_participant=selected,
        instruction=None,
        finish=False,
        final_message=None,
    )
