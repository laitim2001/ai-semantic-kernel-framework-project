"""
Pydantic schemas for Orchestration Execution Log API.

Sprint 169 — Phase 47: Pipeline execution persistence.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ExecutionLogSummary(BaseModel):
    """Summary view for list endpoints."""

    id: str
    request_id: str
    session_id: str
    user_id: str
    user_input: str
    selected_route: Optional[str] = None
    status: str
    total_ms: Optional[float] = None
    fast_path_applied: bool = False
    created_at: Optional[str] = None
    pipeline_steps: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ExecutionLogDetail(ExecutionLogSummary):
    """Detail view with all fields."""

    routing_decision: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    completeness_info: Optional[Dict[str, Any]] = None
    route_reasoning: Optional[str] = None
    agent_events: Optional[List[Any]] = None
    final_response: Optional[str] = None
    dispatch_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ExecutionLogListResponse(BaseModel):
    """Paginated list response."""

    data: List[ExecutionLogSummary]
    total: int
    page: int
    page_size: int


class ExecutionLogDetailResponse(BaseModel):
    """Single record detail response."""

    data: ExecutionLogDetail
    message: str = "Success"
