# =============================================================================
# IPA Platform - Workflow Model
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Workflow model for defining agent orchestration flows.
# Supports graph-based workflow definitions with nodes and edges.
# =============================================================================

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.user import User
    from src.infrastructure.database.models.execution import Execution


class Workflow(Base, TimestampMixin):
    """
    Workflow definition model.

    Workflows define the orchestration of multiple agents in a graph structure.
    Each workflow contains nodes (agents, gateways) and edges (transitions).

    Attributes:
        id: UUID primary key
        name: Workflow name
        description: Workflow description
        trigger_type: How the workflow is triggered (manual, schedule, webhook, event)
        trigger_config: Trigger-specific configuration
        graph_definition: Node and edge definitions
        status: Workflow status (draft, active, inactive, archived)
        version: Workflow version number
        created_by: User who created the workflow

    Example:
        workflow = Workflow(
            name="customer-inquiry-flow",
            trigger_type="webhook",
            graph_definition={
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "classifier", "type": "agent", "agent_id": "..."},
                    {"id": "support", "type": "agent", "agent_id": "..."},
                    {"id": "end", "type": "end"},
                ],
                "edges": [
                    {"source": "start", "target": "classifier"},
                    {"source": "classifier", "target": "support"},
                    {"source": "support", "target": "end"},
                ],
            },
        )
    """

    __tablename__ = "workflows"

    # Primary key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Trigger configuration
    trigger_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
    )

    trigger_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Graph definition
    graph_definition: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        index=True,
    )

    # Version control
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Creator reference
    created_by: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="workflows",
    )

    executions: Mapped[List["Execution"]] = relationship(
        "Execution",
        back_populates="workflow",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary for serialization."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "graph_definition": self.graph_definition,
            "status": self.status,
            "version": self.version,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
