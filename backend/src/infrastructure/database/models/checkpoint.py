"""
Checkpoint Model for Human-in-the-Loop Approval Flow

Sprint 2 - Story S2-4: Teams Approval Flow

Checkpoints represent pause points in workflow execution where
human approval is required before proceeding.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class CheckpointStatus(str, enum.Enum):
    """Checkpoint status enumeration."""
    PENDING = "PENDING"              # Waiting for approval
    APPROVED = "APPROVED"            # Approved by user
    REJECTED = "REJECTED"            # Rejected by user
    EXPIRED = "EXPIRED"              # Approval window expired
    AUTO_APPROVED = "AUTO_APPROVED"  # Auto-approved by system


class Checkpoint(BaseModel):
    """
    Checkpoint model for human-in-the-loop approval.

    Attributes:
        execution_id: Reference to the execution
        step_index: The step number where checkpoint occurs
        step_name: Name of the step
        status: Current checkpoint status
        proposed_action: Description of what will happen if approved
        context: Additional context data for the approval decision
        approved_by: User ID who approved/rejected
        approved_at: Timestamp of approval/rejection
        feedback: Reviewer's feedback or rejection reason
        expires_at: When the approval request expires
        notification_sent: Whether Teams notification was sent
        notification_id: Reference to the notification ID
    """
    __tablename__ = "checkpoints"

    # Foreign Keys - Note: FK constraints exist in DB, but we don't define ForeignKey()
    # to avoid metadata issues with tables not in the same Base
    execution_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Step Information
    step_index = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=True)

    # Status
    status = Column(
        Enum(CheckpointStatus, name="checkpointstatus", create_type=False),
        default=CheckpointStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Approval Details
    proposed_action = Column(Text, nullable=True)
    context = Column(JSONB, nullable=True)

    # Approval Response - Note: FK constraint exists in DB, but we don't define relationship
    # to avoid circular import issues
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    feedback = Column(Text, nullable=True)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Notification Tracking
    notification_sent = Column(Boolean, default=False, nullable=False)
    notification_id = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<Checkpoint(id={self.id}, execution_id={self.execution_id}, status={self.status})>"

    def is_pending(self) -> bool:
        """Check if checkpoint is still pending approval."""
        return self.status == CheckpointStatus.PENDING

    def is_expired(self) -> bool:
        """Check if checkpoint has expired."""
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        # Handle both timezone-aware and naive datetimes from database
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    def can_be_approved(self) -> bool:
        """Check if checkpoint can be approved."""
        return self.is_pending() and not self.is_expired()

    def approve(self, user_id: str, feedback: Optional[str] = None) -> None:
        """Approve the checkpoint."""
        self.status = CheckpointStatus.APPROVED
        self.approved_by = user_id
        self.approved_at = datetime.utcnow()
        self.feedback = feedback

    def reject(self, user_id: str, reason: str) -> None:
        """Reject the checkpoint."""
        self.status = CheckpointStatus.REJECTED
        self.approved_by = user_id
        self.approved_at = datetime.utcnow()
        self.feedback = reason

    def expire(self) -> None:
        """Mark checkpoint as expired."""
        self.status = CheckpointStatus.EXPIRED
