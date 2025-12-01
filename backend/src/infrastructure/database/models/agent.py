# =============================================================================
# IPA Platform - Agent Model
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Agent model for AI Agent definitions.
# Stores agent configuration, instructions, and tool assignments.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, TimestampMixin


class Agent(Base, TimestampMixin):
    """
    AI Agent definition model.

    Attributes:
        id: UUID primary key
        name: Unique agent name
        description: Agent description
        instructions: System prompt for the agent
        category: Agent category for organization
        tools: List of tool names the agent can use
        model_config: LLM model configuration (temperature, etc.)
        max_iterations: Maximum reasoning iterations
        status: Agent status (active, inactive, deprecated)
        version: Agent version number

    Example:
        agent = Agent(
            name="customer-support-agent",
            instructions="You are a helpful customer support agent...",
            tools=["search_knowledge_base", "get_customer_info"],
            model_config={"temperature": 0.7, "max_tokens": 2000},
        )
    """

    __tablename__ = "agents"

    # Primary key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Agent configuration
    instructions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Tools configuration
    tools: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Model configuration
    model_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Execution limits
    max_iterations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        index=True,
    )

    # Version control
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary for serialization."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "category": self.category,
            "tools": self.tools,
            "model_config": self.model_config,
            "max_iterations": self.max_iterations,
            "status": self.status,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
