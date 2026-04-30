# =============================================================================
# IPA Platform - Database Base Model
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Base model class and mixins for all SQLAlchemy ORM models.
# Provides common functionality like UUID primary keys and timestamps.
# =============================================================================

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides a declarative base with common type annotations.
    All models should inherit from this class.
    """

    # Type annotation map for common types
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.

    Attributes:
        created_at: Timestamp when the record was created (auto-set)
        updated_at: Timestamp when the record was last updated (auto-update)
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """
    Mixin that adds a UUID primary key.

    Attributes:
        id: UUID primary key (auto-generated)
    """

    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
