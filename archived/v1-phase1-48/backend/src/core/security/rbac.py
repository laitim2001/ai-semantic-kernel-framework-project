"""
Role-Based Access Control (RBAC) — basic role management for Phase 36.

Three roles:
- Admin: full access to all tools and operations
- Operator: core operational tools, no admin functions
- Viewer: read-only access, search and query tools only

Sprint 112 — Phase 36 Orchestrator completeness.
"""

import logging
from typing import Dict, Optional, Set
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """Platform user roles ordered by privilege level."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


@dataclass
class Permission:
    """Describes allowed actions on a resource.

    Examples:
        Permission(resource="tool:assess_risk", actions={"execute"})
        Permission(resource="api:chat", actions={"read", "write"})
    """

    resource: str  # e.g., "tool:assess_risk", "api:chat", "session:*"
    actions: Set[str]  # e.g., {"read", "write", "execute"}


class RBACManager:
    """Manages role-based permissions.

    Supports wildcard matching: a permission string ending with ``*`` matches
    any resource that shares the same prefix.

    Usage::

        rbac = RBACManager()
        rbac.assign_role("user_123", Role.OPERATOR)
        if rbac.check_permission("user_123", "tool:assess_risk", "execute"):
            ...
    """

    # Default role-permission mapping
    DEFAULT_PERMISSIONS: Dict[Role, Set[str]] = {
        Role.ADMIN: {"tool:*", "api:*", "session:*", "admin:*"},
        Role.OPERATOR: {
            "tool:assess_risk",
            "tool:search_memory",
            "tool:request_approval",
            "tool:create_task",
            "tool:respond_to_user",
            "tool:route_intent",
            "api:chat",
            "api:history",
            "session:own",
        },
        Role.VIEWER: {
            "tool:search_memory",
            "tool:respond_to_user",
            "tool:route_intent",
            "api:chat",
            "api:history:read",
            "session:own:read",
        },
    }

    def __init__(self) -> None:
        self._user_roles: Dict[str, Role] = {}  # user_id -> Role
        self._role_permissions: Dict[Role, Set[str]] = {
            role: set(perms) for role, perms in self.DEFAULT_PERMISSIONS.items()
        }

    # ------------------------------------------------------------------
    # Role management
    # ------------------------------------------------------------------

    def assign_role(self, user_id: str, role: Role) -> None:
        """Assign a role to a user, replacing any existing assignment."""
        previous = self._user_roles.get(user_id)
        self._user_roles[user_id] = role
        logger.info(
            "RBAC: user '%s' role changed %s -> %s",
            user_id,
            previous.value if previous else "none",
            role.value,
        )

    def get_role(self, user_id: str) -> Role:
        """Return the role for *user_id*, defaulting to ``Role.VIEWER``."""
        return self._user_roles.get(user_id, Role.VIEWER)

    # ------------------------------------------------------------------
    # Permission queries
    # ------------------------------------------------------------------

    def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str = "execute",
    ) -> bool:
        """Check whether *user_id* may perform *action* on *resource*.

        The check is purely resource-string-based: if any of the user's role
        permissions match the requested *resource* (including wildcard
        expansion) the call returns ``True``.

        The *action* parameter is reserved for future fine-grained checks and
        is currently accepted but not enforced beyond presence in the
        permission set.
        """
        role = self.get_role(user_id)
        permissions = self._role_permissions.get(role, set())
        return self._matches_any(resource, permissions)

    def get_permissions(self, user_id: str) -> Set[str]:
        """Return the full set of permission strings for *user_id*."""
        role = self.get_role(user_id)
        return set(self._role_permissions.get(role, set()))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_any(resource: str, permissions: Set[str]) -> bool:
        """Return ``True`` if *resource* matches any entry in *permissions*.

        Matching rules:
        - Exact match: ``"tool:assess_risk"`` matches ``"tool:assess_risk"``
        - Wildcard match: ``"tool:*"`` matches ``"tool:dispatch_workflow"``
          (the prefix before ``*`` must match the beginning of *resource*)
        """
        for perm in permissions:
            if perm == resource:
                return True
            if perm.endswith("*"):
                prefix = perm[:-1]  # e.g. "tool:" from "tool:*"
                if resource.startswith(prefix):
                    return True
        return False
