"""MCP Permission Checker.

Sprint 113: S113-1 - Runtime permission enforcement for MCP tool calls.

Provides centralized permission checking with two modes:
  - log: Log permission violations as WARNING, don't block (Phase 1)
  - enforce: Block unauthorized operations with PermissionError (Phase 2)

Controlled by MCP_PERMISSION_MODE environment variable.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .permissions import PermissionLevel, PermissionManager, PermissionPolicy

logger = logging.getLogger(__name__)


class MCPPermissionChecker:
    """Centralized permission checker for MCP tool calls.

    Integrates with PermissionManager to check permissions before
    tool execution. Supports log-only and enforce modes.

    Environment Variables:
        MCP_PERMISSION_MODE: "log" (default) or "enforce"

    Example:
        >>> checker = MCPPermissionChecker()
        >>> allowed = checker.check_tool_permission(
        ...     server_name="shell",
        ...     tool_name="run_command",
        ...     required_level=3,
        ...     user_id="admin",
        ... )
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
    ):
        """Initialize the permission checker.

        Args:
            permission_manager: Optional PermissionManager instance.
                If not provided, a default manager is created based
                on the current APP_ENV environment variable.
        """
        self._manager = permission_manager or self._create_default_manager()
        self._mode = os.environ.get("MCP_PERMISSION_MODE", "log")
        self._check_count = 0
        self._deny_count = 0
        logger.info(
            f"MCPPermissionChecker initialized: mode={self._mode}"
        )

    def _create_default_manager(self) -> PermissionManager:
        """Create default PermissionManager with standard policies.

        In development/testing environments, a permissive default policy
        is added. In production, explicit policies should be configured.

        Returns:
            Configured PermissionManager instance
        """
        manager = PermissionManager()

        env = os.environ.get("APP_ENV", "development")
        if env in ("development", "testing"):
            manager.add_policy(PermissionPolicy(
                name="dev_default",
                servers=["*"],
                tools=["*"],
                level=PermissionLevel.ADMIN,
                priority=0,
            ))

        return manager

    @property
    def mode(self) -> str:
        """Current permission mode (log or enforce)."""
        return self._mode

    @property
    def check_count(self) -> int:
        """Total permission checks performed."""
        return self._check_count

    @property
    def deny_count(self) -> int:
        """Total permission denials."""
        return self._deny_count

    def check_tool_permission(
        self,
        server_name: str,
        tool_name: str,
        required_level: int = 2,
        user_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check permission for a tool call.

        Evaluates the permission through PermissionManager and either
        logs or enforces the result based on the current mode.

        Args:
            server_name: MCP server name (e.g., "shell", "azure", "filesystem")
            tool_name: Tool name (e.g., "run_command", "list_vms")
            required_level: Required PermissionLevel value (0-3)
            user_id: User identifier (from auth context)
            roles: User roles for RBAC evaluation
            context: Additional context for condition evaluation

        Returns:
            True if allowed, False if denied

        Raises:
            PermissionError: In enforce mode when permission is denied
        """
        self._check_count += 1

        # Clamp required_level to valid PermissionLevel range
        clamped_level = min(required_level, PermissionLevel.ADMIN)
        permission_level = PermissionLevel(clamped_level)

        allowed = self._manager.check_permission(
            user_id=user_id,
            roles=roles,
            server=server_name,
            tool=tool_name,
            level=permission_level,
            context=context,
        )

        if not allowed:
            self._deny_count += 1

            if self._mode == "enforce":
                logger.warning(
                    f"PERMISSION_DENIED (enforce): server={server_name}, "
                    f"tool={tool_name}, level={required_level}, "
                    f"user={user_id}"
                )
                raise PermissionError(
                    f"Permission denied: user={user_id} lacks permission "
                    f"for {server_name}/{tool_name} (level={required_level})"
                )
            else:
                logger.warning(
                    f"PERMISSION_DENIED (log-only): server={server_name}, "
                    f"tool={tool_name}, level={required_level}, "
                    f"user={user_id}"
                )
        else:
            logger.debug(
                f"PERMISSION_GRANTED: server={server_name}, "
                f"tool={tool_name}, user={user_id}"
            )

        return allowed

    def get_stats(self) -> Dict[str, Any]:
        """Get permission check statistics.

        Returns:
            Dict containing mode, total checks, denials, and denial rate
        """
        return {
            "mode": self._mode,
            "total_checks": self._check_count,
            "total_denials": self._deny_count,
            "denial_rate": (
                round(self._deny_count / self._check_count, 4)
                if self._check_count > 0
                else 0.0
            ),
        }
