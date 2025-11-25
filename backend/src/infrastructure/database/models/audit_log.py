"""
Audit Log Model for IPA Platform

Tracks all user actions and system events for compliance and debugging.
Sprint 2 - Story S2-7

Note: This model is designed to work with the existing audit_logs table.
Additional columns will be added via migration.
"""
import enum
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID

from .base import Base


class AuditAction(str, enum.Enum):
    """Enumeration of auditable actions."""
    # CRUD Operations
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    # Authentication
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"

    # Workflow Operations
    EXECUTE = "EXECUTE"
    CANCEL = "CANCEL"
    PAUSE = "PAUSE"
    RESUME = "RESUME"

    # Approval Operations
    APPROVE = "APPROVE"
    REJECT = "REJECT"

    # Webhook Operations
    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"
    WEBHOOK_PROCESSED = "WEBHOOK_PROCESSED"
    WEBHOOK_FAILED = "WEBHOOK_FAILED"

    # Notification Operations
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"

    # System Operations
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CONFIG_CHANGE = "CONFIG_CHANGE"


class AuditLog(Base):
    """
    Audit Log Model

    Stores comprehensive audit trail for all system activities.
    Uses BigInteger for id to support high-volume logging.

    Table: audit_logs (created in initial migration)

    Note: Only defines columns that exist in the current database schema.
    Additional columns can be added via future migrations.
    """
    __tablename__ = "audit_logs"

    # Primary key - BigInteger for high-volume support
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Actor information (no FK constraint for flexibility)
    user_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    # Action details
    action = Column(
        Enum(AuditAction, name="auditaction", create_type=False),
        nullable=False,
        index=True
    )

    # Resource information
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # Change tracking
    changes = Column(JSONB, nullable=True)

    # Request context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": str(self.user_id) if self.user_id else None,
            "actor_type": "user",  # Default for compatibility
            "action": self.action.value if self.action else None,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "resource_name": None,  # Not in current schema
            "changes": self.changes,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "request_id": None,  # Not in current schema
            "metadata": None,  # Not in current schema
            "error_message": None,  # Not in current schema
            "duration_ms": None,  # Not in current schema
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def create_log(
        cls,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        resource_name: Optional[str] = None,
        user_id: Optional[UUID] = None,
        actor_type: str = "user",
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        extra_data: Optional[dict] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> "AuditLog":
        """
        Factory method to create an audit log entry.

        Args:
            action: The action being logged
            resource_type: Type of resource (workflow, execution, agent, etc.)
            resource_id: UUID of the affected resource
            resource_name: Human-readable name of the resource (ignored - not in schema)
            user_id: UUID of the user performing the action
            actor_type: Type of actor (ignored - not in schema)
            changes: Dictionary of changes made
            ip_address: Client IP address
            user_agent: Client user agent string
            request_id: Correlation/request ID (ignored - not in schema)
            extra_data: Additional metadata (ignored - not in schema)
            error_message: Error message if action failed (ignored - not in schema)
            duration_ms: Duration of the action in milliseconds (ignored - not in schema)

        Returns:
            AuditLog instance
        """
        return cls(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
