"""
Chat API Schemas — Request/Response models for the orchestration chat endpoint.

Phase 45: Orchestration Core (Sprint 156)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /orchestration/chat."""

    task: str = Field(..., min_length=1, max_length=5000, description="User's message/task")
    user_id: str = Field(default="default-user", description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session ID (auto-generated if not provided)")
    hitl_pre_approved: bool = Field(default=False, description="Skip HITL gate (set after approval resume)")


class ResumeRequest(BaseModel):
    """Request body for POST /orchestration/chat/resume."""

    checkpoint_id: str = Field(..., description="Checkpoint ID to resume from")
    user_id: str = Field(..., description="User identifier")

    # HITL resume
    approval_status: Optional[str] = Field(default=None, description="'approved' or 'rejected'")
    approval_approver: Optional[str] = Field(default=None, description="Who approved/rejected")

    # Re-route override
    override_route: Optional[str] = Field(default=None, description="Override route: direct_answer/subagent/team")

    # Agent retry
    retry_agents: Optional[List[str]] = Field(default=None, description="Agent names to retry")


class DialogRespondRequest(BaseModel):
    """Request body for POST /orchestration/chat/dialog-respond."""

    checkpoint_id: str = Field(..., description="Checkpoint ID from dialog pause")
    user_id: str = Field(..., description="User identifier")
    dialog_id: str = Field(..., description="Dialog session ID")
    responses: Dict[str, str] = Field(..., description="Field name → user response mapping")


class PipelineStepStatus(BaseModel):
    """Status of a single pipeline step."""

    step_index: int
    step_name: str
    status: str  # "pending" | "running" | "completed" | "paused" | "error"
    latency_ms: Optional[float] = None


class SessionStatusResponse(BaseModel):
    """Response for GET /orchestration/chat/session/{session_id}."""

    session_id: str
    user_id: str
    status: str  # "running" | "completed" | "paused_hitl" | "paused_dialog" | "error"
    selected_route: Optional[str] = None
    completed_steps: List[str] = []
    paused_at: Optional[str] = None
    checkpoint_id: Optional[str] = None
    total_ms: Optional[float] = None
