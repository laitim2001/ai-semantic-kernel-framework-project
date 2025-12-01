# =============================================================================
# IPA Platform - Audit Log Model
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Audit log model for tracking all platform actions.
# Provides complete audit trail for compliance and debugging.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base


class AuditLog(Base):
    """
    Audit log model for tracking platform actions.

    Records all significant actions for compliance and debugging.
    Includes context about the action, actor, and target resources.

    Attributes:
        id: UUID primary key
        action: Action type (create, read, update, delete, execute, etc.)
        resource_type: Type of resource affected (agent, workflow, execution, etc.)
        resource_id: ID of the affected resource
        actor_id: User who performed the action
        actor_ip: IP address of the actor
        old_value: Previous state (for updates)
        new_value: New state (for creates/updates)
        metadata: Additional context
        timestamp: When the action occurred

    Example:
        log = AuditLog(
            action="update",
            resource_type="agent",
            resource_id=agent.id,
            actor_id=user.id,
            old_value={"status": "draft"},
            new_value={"status": "active"},
        )
    """

    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Action details
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    resource_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Actor information
    actor_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    actor_ip: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    # State tracking
    old_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    new_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Additional context
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Description
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamp (not using TimestampMixin as audit logs are immutable)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource_type={self.resource_type})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary for serialization."""
        return {
            "id": str(self.id),
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_ip": self.actor_ip,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "extra_data": self.extra_data,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
