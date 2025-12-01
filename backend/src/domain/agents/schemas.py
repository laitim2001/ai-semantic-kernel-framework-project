# =============================================================================
# IPA Platform - Agent Schemas
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Pydantic schemas for Agent API request/response validation.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    """
    Request schema for creating a new agent.

    Attributes:
        name: Unique agent name
        description: Optional description
        instructions: System prompt/instructions
        category: Optional category for organization
        tools: List of tool names to enable
        model_config_data: LLM model configuration
        max_iterations: Maximum reasoning iterations
    """

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    instructions: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    tools: List[str] = Field(default_factory=list)
    model_config_data: Dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = Field(default=10, ge=1, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "customer-support-agent",
                "description": "Handles customer support inquiries",
                "instructions": "You are a helpful customer support agent...",
                "category": "support",
                "tools": ["search_knowledge_base", "get_customer_info"],
                "model_config_data": {"temperature": 0.7, "max_tokens": 2000},
                "max_iterations": 10,
            }
        }


class AgentUpdateRequest(BaseModel):
    """
    Request schema for updating an agent.

    All fields are optional - only provided fields will be updated.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    tools: Optional[List[str]] = None
    model_config_data: Optional[Dict[str, Any]] = None
    max_iterations: Optional[int] = Field(None, ge=1, le=100)
    status: Optional[str] = Field(None, pattern="^(active|inactive|deprecated)$")


class AgentResponse(BaseModel):
    """
    Response schema for agent data.

    Used for both single agent and list responses.
    """

    id: UUID
    name: str
    description: Optional[str]
    instructions: str
    category: Optional[str]
    tools: List[str]
    model_config_data: Dict[str, Any]
    max_iterations: int
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Response schema for paginated agent list."""

    items: List[AgentResponse]
    total: int
    page: int
    page_size: int


class AgentRunRequest(BaseModel):
    """
    Request schema for running an agent.

    Attributes:
        message: User message to process
        context: Optional additional context
        tools_override: Optional tool list override
    """

    message: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None
    tools_override: Optional[List[str]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "How do I reset my password?",
                "context": {"user_id": "12345", "tier": "premium"},
            }
        }


class AgentRunResponse(BaseModel):
    """
    Response schema for agent execution.

    Attributes:
        result: Agent response text
        stats: Execution statistics (llm_calls, tokens, cost)
        tool_calls: List of tools called during execution
    """

    result: str
    stats: Dict[str, Any]
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "result": "To reset your password, go to Settings > Security...",
                "stats": {
                    "llm_calls": 1,
                    "llm_tokens": 450,
                    "llm_cost": 0.00225,
                },
                "tool_calls": [
                    {
                        "tool": "search_knowledge_base",
                        "input": {"query": "password reset"},
                        "output": "Found 3 results...",
                    }
                ],
            }
        }
