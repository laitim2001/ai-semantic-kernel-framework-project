# =============================================================================
# IPA Platform - Agent Expert Model
# =============================================================================
# Sprint 163: Agent Expert CRUD + DB Persistence
#
# Stores agent expert definitions in the database, replacing YAML-only storage.
# Each expert has its own system prompt, tools, model, domain, and capabilities.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, TimestampMixin


class AgentExpert(Base, TimestampMixin):
    """
    Agent Expert definition model.

    Each expert represents a specialized AI agent with domain-specific
    knowledge, system prompt, tool access, and model configuration.

    Attributes:
        id: UUID primary key
        name: Unique expert identifier (slug format)
        display_name: English display name
        display_name_zh: Chinese display name
        description: Expert description
        domain: Expert domain (network, database, application, security, cloud, general, custom)
        capabilities: List of capability tags
        model: LLM model override (null = use system default)
        max_iterations: Maximum tool-call iterations
        system_prompt: Role-specific system prompt
        tools: List of allowed tool names
        enabled: Whether this expert is active
        is_builtin: Whether seeded from YAML (blocks deletion)
        metadata: Extra configuration data
        version: Version number (bumped on update)
    """

    __tablename__ = "agent_experts"

    # Primary key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Identity
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    display_name_zh: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Domain & capabilities
    domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    capabilities: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # LLM configuration
    model: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    max_iterations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    # System prompt
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Tools
    tools: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Status
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Extra
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "display_name_zh": self.display_name_zh,
            "description": self.description or "",
            "domain": self.domain,
            "capabilities": self.capabilities or [],
            "model": self.model,
            "max_iterations": self.max_iterations,
            "system_prompt": self.system_prompt,
            "tools": self.tools or [],
            "enabled": self.enabled,
            "is_builtin": self.is_builtin,
            "metadata": self.metadata_ or {},
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<AgentExpert name={self.name} domain={self.domain} enabled={self.enabled}>"
