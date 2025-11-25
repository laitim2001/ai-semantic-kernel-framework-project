"""
Workflow Model

Database model for workflow definitions.
"""
import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Text, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import BaseModel


class WorkflowStatus(str, enum.Enum):
    """Workflow status enum."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Workflow(BaseModel):
    """Workflow model.

    Represents a workflow definition with its configuration and metadata.
    """

    __tablename__ = "workflows"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(
        Enum(WorkflowStatus, name="workflowstatus", create_type=False),
        nullable=True,
        default=WorkflowStatus.DRAFT,
        index=True,
    )
    current_version_id = Column(UUID(as_uuid=True), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    workflow_metadata = Column("metadata", JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if workflow is active."""
        return self.status == WorkflowStatus.ACTIVE
