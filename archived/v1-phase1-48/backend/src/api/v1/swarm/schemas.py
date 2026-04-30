"""
Swarm API Schemas

Pydantic schemas for Swarm API request/response models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCallInfoSchema(BaseModel):
    """Tool call information schema."""

    tool_id: str = Field(..., description="Unique identifier for this tool call")
    tool_name: str = Field(..., description="Name of the tool")
    is_mcp: bool = Field(..., description="Whether this is an MCP tool")
    input_params: Dict[str, Any] = Field(
        default_factory=dict, description="Tool input parameters"
    )
    status: str = Field(..., description="Tool call status")
    result: Optional[Any] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="When tool call started")
    completed_at: Optional[datetime] = Field(
        None, description="When tool call completed"
    )
    duration_ms: Optional[int] = Field(
        None, description="Duration in milliseconds"
    )

    class Config:
        from_attributes = True


class ThinkingContentSchema(BaseModel):
    """Extended thinking content schema."""

    content: str = Field(..., description="Thinking content text")
    timestamp: datetime = Field(..., description="When thinking was generated")
    token_count: Optional[int] = Field(None, description="Number of tokens")

    class Config:
        from_attributes = True


class WorkerMessageSchema(BaseModel):
    """Worker message schema."""

    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")

    class Config:
        from_attributes = True


class WorkerSummarySchema(BaseModel):
    """Worker summary schema for list views."""

    worker_id: str = Field(..., description="Worker unique identifier")
    worker_name: str = Field(..., description="Worker display name")
    worker_type: str = Field(..., description="Worker type")
    role: str = Field(..., description="Worker role in current task")
    status: str = Field(..., description="Current worker status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_task: Optional[str] = Field(None, description="Current task description")
    tool_calls_count: int = Field(0, description="Total number of tool calls")
    started_at: Optional[datetime] = Field(None, description="When worker started")
    completed_at: Optional[datetime] = Field(None, description="When worker completed")

    class Config:
        from_attributes = True


class WorkerDetailResponse(BaseModel):
    """Detailed worker information response."""

    worker_id: str = Field(..., description="Worker unique identifier")
    worker_name: str = Field(..., description="Worker display name")
    worker_type: str = Field(..., description="Worker type")
    role: str = Field(..., description="Worker role in current task")
    status: str = Field(..., description="Current worker status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_task: Optional[str] = Field(None, description="Current task description")
    tool_calls: List[ToolCallInfoSchema] = Field(
        default_factory=list, description="List of tool calls"
    )
    thinking_contents: List[ThinkingContentSchema] = Field(
        default_factory=list, description="Extended thinking blocks"
    )
    messages: List[WorkerMessageSchema] = Field(
        default_factory=list, description="Conversation messages"
    )
    started_at: Optional[datetime] = Field(None, description="When worker started")
    completed_at: Optional[datetime] = Field(None, description="When worker completed")
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        from_attributes = True


class SwarmStatusResponse(BaseModel):
    """Swarm status response schema."""

    swarm_id: str = Field(..., description="Swarm unique identifier")
    mode: str = Field(..., description="Execution mode (sequential/parallel/hierarchical)")
    status: str = Field(..., description="Overall swarm status")
    overall_progress: int = Field(
        ..., ge=0, le=100, description="Overall progress percentage"
    )
    workers: List[WorkerSummarySchema] = Field(
        default_factory=list, description="List of workers"
    )
    total_tool_calls: int = Field(0, description="Total tool calls across all workers")
    completed_tool_calls: int = Field(0, description="Completed tool calls")
    started_at: datetime = Field(..., description="When swarm started")
    completed_at: Optional[datetime] = Field(None, description="When swarm completed")

    class Config:
        from_attributes = True


class WorkerListResponse(BaseModel):
    """Worker list response schema."""

    swarm_id: str = Field(..., description="Swarm unique identifier")
    workers: List[WorkerSummarySchema] = Field(
        default_factory=list, description="List of workers"
    )
    total: int = Field(0, description="Total number of workers")

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
