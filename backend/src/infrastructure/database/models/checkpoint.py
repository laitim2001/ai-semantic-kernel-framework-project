# =============================================================================
# IPA Platform - Checkpoint Model
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Checkpoint model for human-in-the-loop workflow pausing.
# Allows workflows to pause and wait for human approval or input.
# =============================================================================

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.execution import Execution


class Checkpoint(Base, TimestampMixin):
    """
    Human-in-the-loop checkpoint model.

    Checkpoints allow workflows to pause execution and wait for
    human approval, review, or additional input before continuing.

    Attributes:
        id: UUID primary key
        execution_id: Reference to the parent execution
        node_id: ID of the workflow node that created this checkpoint
        status: Checkpoint status (pending, approved, rejected, expired)
        payload: Data to be reviewed by human
        response: Human response/decision
        responded_by: User who responded
        responded_at: When response was received
        expires_at: When checkpoint expires if not responded

    Example:
        checkpoint = Checkpoint(
            execution_id=execution.id,
            node_id="approval-gate",
            payload={"amount": 10000, "reason": "Large purchase"},
        )
    """

    __tablename__ = "checkpoints"

    # Primary key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Execution reference
    execution_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Node reference
    node_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )

    # Payload for review
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Human response
    response: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    responded_by: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Notes/comments
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    execution: Mapped["Execution"] = relationship(
        "Execution",
        back_populates="checkpoints",
    )

    def __repr__(self) -> str:
        return f"<Checkpoint(id={self.id}, execution_id={self.execution_id}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "id": str(self.id),
            "execution_id": str(self.execution_id),
            "node_id": self.node_id,
            "status": self.status,
            "payload": self.payload,
            "response": self.response,
            "responded_by": str(self.responded_by) if self.responded_by else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def is_expired(self) -> bool:
        """Check if checkpoint has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
