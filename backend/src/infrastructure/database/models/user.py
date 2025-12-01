# =============================================================================
# IPA Platform - User Model
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# User model for platform authentication and authorization.
# Supports role-based access control (admin, operator, viewer).
# =============================================================================

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.workflow import Workflow
    from src.infrastructure.database.models.execution import Execution


class User(Base, TimestampMixin):
    """
    Platform user model.

    Attributes:
        id: UUID primary key
        email: Unique email address
        hashed_password: Bcrypt hashed password
        full_name: User's display name
        role: User role (admin, operator, viewer)
        is_active: Whether user can log in
        last_login: Last successful login timestamp

    Relationships:
        workflows: Workflows created by this user
        executions: Executions triggered by this user
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Authorization
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="viewer",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    workflows: Mapped[List["Workflow"]] = relationship(
        "Workflow",
        back_populates="created_by_user",
        lazy="selectin",
    )

    executions: Mapped[List["Execution"]] = relationship(
        "Execution",
        back_populates="triggered_by_user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
