"""
infrastructure.db.models — All ORM models registered against `Base.metadata`.

Sprint 49.2 builds these incrementally:
    Day 1.5: identity.py     — Tenant / User / Role / UserRole / RolePermission
    Day 2.1: sessions.py     — Session / Message / MessageEvent
    Day 3.1: tools.py        — ToolRegistry / ToolCall / ToolResult
    Day 4.1: state.py        — StateSnapshot / LoopState

Importing this package registers all ORM tables with Base.metadata, which
the Alembic env.py uses as `target_metadata`.

Per .claude/rules/multi-tenant-data.md 鐵律 1, all session-scoped tables
inherit `TenantScopedMixin` from `infrastructure.db.base`.
"""

from __future__ import annotations

# Day 1.5 — Identity
from infrastructure.db.models.identity import (
    Role,
    RolePermission,
    Tenant,
    User,
    UserRole,
)

# Day 2.1 — Sessions
from infrastructure.db.models.sessions import (
    Message,
    MessageEvent,
    Session,
)

# Day 3.1 — Tools
from infrastructure.db.models.tools import (
    ToolCall,
    ToolRegistry,
    ToolResult,
)

__all__ = [
    # Identity
    "Tenant",
    "User",
    "Role",
    "UserRole",
    "RolePermission",
    # Sessions
    "Session",
    "Message",
    "MessageEvent",
    # Tools
    "ToolRegistry",
    "ToolCall",
    "ToolResult",
]
