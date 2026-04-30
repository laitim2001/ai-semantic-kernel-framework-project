# =============================================================================
# IPA Platform - Execution Model
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Execution model for tracking workflow execution instances.
# Stores execution state, results, and LLM usage statistics.
# =============================================================================

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.user import User
    from src.infrastructure.database.models.workflow import Workflow
    from src.infrastructure.database.models.checkpoint import Checkpoint


class Execution(Base, TimestampMixin):
    """
    Workflow execution instance model.

    Tracks the state and results of a workflow execution.
    Includes LLM usage statistics for cost tracking.

    Attributes:
        id: UUID primary key
        workflow_id: Reference to the workflow being executed
        status: Execution status (pending, running, paused, completed, failed, cancelled)
        started_at: When execution started
        completed_at: When execution completed or failed
        result: Execution output data
        error: Error message if failed
        llm_calls: Total number of LLM API calls
        llm_tokens: Total tokens used (input + output)
        llm_cost: Estimated cost in USD
        triggered_by: User who triggered the execution

    Status Flow:
        pending -> running -> completed
                          -> failed
                          -> cancelled
        running -> paused -> running
                         -> cancelled
    """

    __tablename__ = "executions"

    # Primary key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Workflow reference
    workflow_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Results
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # LLM Statistics
    llm_calls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    llm_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    llm_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        default=Decimal("0.000000"),
    )

    # Trigger reference
    triggered_by: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Input data
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="executions",
    )

    triggered_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="executions",
    )

    checkpoints: Mapped[List["Checkpoint"]] = relationship(
        "Checkpoint",
        back_populates="execution",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert execution to dictionary for serialization."""
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "llm_calls": self.llm_calls,
            "llm_tokens": self.llm_tokens,
            "llm_cost": float(self.llm_cost),
            "triggered_by": str(self.triggered_by) if self.triggered_by else None,
            "input_data": self.input_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
