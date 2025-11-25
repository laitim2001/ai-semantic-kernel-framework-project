"""
Base Model Classes for IPA Platform
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model with common fields.

    Provides:
    - UUID primary key
    - Created and updated timestamps
    - Common helper methods
    """
    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """Auto-generate table name from class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return ''.join(
            ['_' + c.lower() if c.isupper() else c for c in name]
        ).lstrip('_') + 's'

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
