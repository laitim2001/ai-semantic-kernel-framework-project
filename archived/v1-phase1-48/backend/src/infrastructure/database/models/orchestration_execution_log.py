# =============================================================================
# IPA Platform - Orchestration Execution Log Model
# =============================================================================
# Sprint 169 — Phase 47: Pipeline execution persistence
#
# Stores every orchestration pipeline execution for audit and history.
# Each row captures the full 8-step pipeline output: routing decision,
# risk assessment, agent events, and final response.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, TimestampMixin


class OrchestrationExecutionLog(Base, TimestampMixin):
    """
    Orchestration pipeline execution log.

    Persists the complete processing trace of each user message through
    the 8-step orchestration pipeline, enabling historical review and audit.

    Attributes:
        id: UUID primary key
        request_id: Unique pipeline invocation ID (dedup key)
        session_id: Chat session identifier
        user_id: User who triggered the execution
        user_input: Original user message
        routing_decision: Intent classification result (JSONB)
        risk_assessment: Risk evaluation result (JSONB)
        completeness_info: Completeness check result (JSONB)
        selected_route: Execution route (direct_answer/subagent/team)
        route_reasoning: LLM reasoning for route choice
        pipeline_steps: Per-step status and timing (JSONB)
        agent_events: Agent execution events (JSONB array)
        final_response: Synthesized response text
        dispatch_result: Full dispatch result (JSONB)
        status: Execution outcome (completed/failed/paused_hitl/paused_dialog)
        error: Error message if failed
        started_at: Pipeline start timestamp
        completed_at: Pipeline completion timestamp
        total_ms: Total execution time in milliseconds
        fast_path_applied: Whether fast-path was used
    """

    __tablename__ = "orchestration_execution_logs"

    # Primary key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Identifiers
    request_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )

    # Input
    user_input: Mapped[str] = mapped_column(Text, nullable=False)

    # Pipeline step outputs (JSONB)
    routing_decision: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
    )
    risk_assessment: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
    )
    completeness_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
    )

    # Route selection
    selected_route: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True,
    )
    route_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution details (JSONB)
    pipeline_steps: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
    )
    agent_events: Mapped[Optional[List[Any]]] = mapped_column(
        JSONB, nullable=True,
    )
    final_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dispatch_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, server_default="completed",
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    total_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fast_path_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all fields for API responses."""
        return {
            "id": str(self.id),
            "request_id": self.request_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_input": self.user_input,
            "routing_decision": self.routing_decision,
            "risk_assessment": self.risk_assessment,
            "completeness_info": self.completeness_info,
            "selected_route": self.selected_route,
            "route_reasoning": self.route_reasoning,
            "pipeline_steps": self.pipeline_steps,
            "agent_events": self.agent_events,
            "final_response": self.final_response,
            "dispatch_result": self.dispatch_result,
            "status": self.status,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_ms": self.total_ms,
            "fast_path_applied": self.fast_path_applied,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<OrchestrationExecutionLog(id={self.id}, "
            f"session={self.session_id}, route={self.selected_route}, "
            f"status={self.status})>"
        )
