"""Claude SDK API schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# --- Query Schemas ---


class QueryRequest(BaseModel):
    """Request schema for one-shot query."""

    prompt: str = Field(..., description="Task description", min_length=1)
    tools: Optional[List[str]] = Field(None, description="Tools to enable")
    max_tokens: Optional[int] = Field(
        None, description="Max response tokens", ge=1, le=100000
    )
    timeout: Optional[int] = Field(
        None, description="Timeout in seconds", ge=1, le=3600
    )
    working_directory: Optional[str] = Field(
        None, description="Working directory for file operations"
    )


class ToolCallSchema(BaseModel):
    """Schema for a tool call."""

    id: str
    name: str
    args: Dict[str, Any]


class QueryResponse(BaseModel):
    """Response schema for one-shot query."""

    content: str
    tool_calls: List[ToolCallSchema]
    tokens_used: int
    duration: float
    status: str


# --- Session Schemas ---


class CreateSessionRequest(BaseModel):
    """Request schema for creating a session."""

    session_id: Optional[str] = Field(None, description="Custom session ID")
    system_prompt: Optional[str] = Field(None, description="System prompt override")
    tools: Optional[List[str]] = Field(None, description="Tools to enable")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Initial context variables"
    )


class SessionResponse(BaseModel):
    """Response schema for session creation."""

    session_id: str
    status: str = "active"


class SessionQueryRequest(BaseModel):
    """Request schema for session query."""

    prompt: str = Field(..., description="Query text", min_length=1)
    tools: Optional[List[str]] = Field(
        None, description="Override session tools for this query"
    )
    max_tokens: Optional[int] = Field(
        None, description="Override max tokens", ge=1, le=100000
    )


class SessionQueryResponse(BaseModel):
    """Response schema for session query."""

    content: str
    tool_calls: List[ToolCallSchema]
    tokens_used: int
    message_index: int


class SessionHistoryMessageSchema(BaseModel):
    """Schema for a message in session history."""

    role: str
    content: str
    timestamp: Optional[float] = None
    tool_calls: Optional[List[ToolCallSchema]] = None


class SessionHistoryResponse(BaseModel):
    """Response schema for session history."""

    session_id: str
    messages: List[SessionHistoryMessageSchema]


class CloseSessionResponse(BaseModel):
    """Response schema for closing a session."""

    status: str = "closed"
    session_id: str
