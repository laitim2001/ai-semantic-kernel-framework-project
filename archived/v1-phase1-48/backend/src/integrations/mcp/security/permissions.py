"""MCP Permission Management.

This module provides permission management for MCP tool access,
supporting role-based and attribute-based access control.

Permission Levels:
    - NONE: No access allowed
    - READ: Can list and view tool schemas
    - EXECUTE: Can execute tools
    - ADMIN: Full control including configuration

Example:
    >>> manager = PermissionManager()
    >>> manager.add_policy(PermissionPolicy(
    ...     name="developer",
    ...     servers=["*"],
    ...     tools=["read_*", "list_*"],
    ...     level=PermissionLevel.EXECUTE,
    ... ))
    >>> allowed = manager.check_permission(
    ...     user_id="user123",
    ...     roles=["developer"],
    ...     server="azure-mcp",
    ...     tool="read_file",
    ... )
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from enum import IntEnum
from datetime import datetime
import fnmatch
import logging

logger = logging.getLogger(__name__)


class PermissionLevel(IntEnum):
    """Permission level hierarchy."""

    NONE = 0
    READ = 1
    EXECUTE = 2
    ADMIN = 3


@dataclass
class Permission:
    """A single permission entry.

    Attributes:
        server: Server name or pattern (supports wildcards)
        tool: Tool name or pattern (supports wildcards)
        level: Permission level
        conditions: Optional conditions for dynamic evaluation
    """

    server: str
    tool: str
    level: PermissionLevel
    conditions: Optional[Dict[str, Any]] = None

    def matches(
        self,
        server: str,
        tool: str,
    ) -> bool:
        """Check if this permission matches the given server and tool.

        Args:
            server: Server name to match
            tool: Tool name to match

        Returns:
            True if this permission matches
        """
        server_match = fnmatch.fnmatch(server, self.server)
        tool_match = fnmatch.fnmatch(tool, self.tool)
        return server_match and tool_match


@dataclass
class PermissionPolicy:
    """A policy defining permissions for a role or user.

    Attributes:
        name: Policy name (e.g., role name)
        servers: List of server patterns
        tools: List of tool patterns
        level: Default permission level
        deny_list: Explicit denials (takes precedence)
        conditions: Optional dynamic conditions
        priority: Policy priority (higher = evaluated first)
    """

    name: str
    servers: List[str] = field(default_factory=lambda: ["*"])
    tools: List[str] = field(default_factory=lambda: ["*"])
    level: PermissionLevel = PermissionLevel.NONE
    deny_list: List[str] = field(default_factory=list)
    conditions: Optional[Dict[str, Any]] = None
    priority: int = 0

    def check(
        self,
        server: str,
        tool: str,
        required_level: PermissionLevel,
    ) -> Optional[bool]:
        """Check if this policy allows the requested access.

        Args:
            server: Server name
            tool: Tool name
            required_level: Required permission level

        Returns:
            True if allowed, False if denied, None if not applicable
        """
        # Check deny list first
        for pattern in self.deny_list:
            if fnmatch.fnmatch(f"{server}/{tool}", pattern):
                return False

        # Check if this policy applies to the server
        server_match = any(
            fnmatch.fnmatch(server, pattern) for pattern in self.servers
        )
        if not server_match:
            return None

        # Check if this policy applies to the tool
        tool_match = any(
            fnmatch.fnmatch(tool, pattern) for pattern in self.tools
        )
        if not tool_match:
            return None

        # Check permission level
        return self.level >= required_level


# Type alias for condition evaluators
ConditionEvaluator = Callable[[Dict[str, Any], Dict[str, Any]], bool]


class PermissionManager:
    """Manages permissions for MCP operations.

    Supports multiple policies with priority-based evaluation,
    explicit denials, and dynamic conditions.

    Example:
        >>> manager = PermissionManager()
        >>>
        >>> # Add policies
        >>> manager.add_policy(PermissionPolicy(
        ...     name="admin",
        ...     servers=["*"],
        ...     tools=["*"],
        ...     level=PermissionLevel.ADMIN,
        ...     priority=100,
        ... ))
        >>>
        >>> manager.add_policy(PermissionPolicy(
        ...     name="developer",
        ...     servers=["dev-*"],
        ...     tools=["*"],
        ...     level=PermissionLevel.EXECUTE,
        ...     deny_list=["*/delete_*", "*/destroy_*"],
        ... ))
        >>>
        >>> # Check permissions
        >>> if manager.check_permission(
        ...     user_id="user123",
        ...     roles=["developer"],
        ...     server="dev-mcp",
        ...     tool="list_files",
        ... ):
        ...     print("Access granted")
    """

    def __init__(self):
        """Initialize the permission manager."""
        self._policies: Dict[str, PermissionPolicy] = {}
        self._user_policies: Dict[str, Set[str]] = {}
        self._role_policies: Dict[str, Set[str]] = {}
        self._condition_evaluators: Dict[str, ConditionEvaluator] = {}
        self._default_level = PermissionLevel.NONE

    def add_policy(self, policy: PermissionPolicy) -> None:
        """Add a permission policy.

        Args:
            policy: Policy to add
        """
        self._policies[policy.name] = policy
        logger.info(f"Added permission policy: {policy.name}")

    def remove_policy(self, name: str) -> bool:
        """Remove a permission policy.

        Args:
            name: Policy name to remove

        Returns:
            True if policy was removed
        """
        if name in self._policies:
            del self._policies[name]
            logger.info(f"Removed permission policy: {name}")
            return True
        return False

    def assign_policy_to_user(
        self,
        user_id: str,
        policy_name: str,
    ) -> bool:
        """Assign a policy to a user.

        Args:
            user_id: User identifier
            policy_name: Policy name to assign

        Returns:
            True if assignment successful
        """
        if policy_name not in self._policies:
            logger.warning(f"Policy not found: {policy_name}")
            return False

        if user_id not in self._user_policies:
            self._user_policies[user_id] = set()

        self._user_policies[user_id].add(policy_name)
        return True

    def assign_policy_to_role(
        self,
        role: str,
        policy_name: str,
    ) -> bool:
        """Assign a policy to a role.

        Args:
            role: Role name
            policy_name: Policy name to assign

        Returns:
            True if assignment successful
        """
        if policy_name not in self._policies:
            logger.warning(f"Policy not found: {policy_name}")
            return False

        if role not in self._role_policies:
            self._role_policies[role] = set()

        self._role_policies[role].add(policy_name)
        return True

    def register_condition_evaluator(
        self,
        name: str,
        evaluator: ConditionEvaluator,
    ) -> None:
        """Register a custom condition evaluator.

        Args:
            name: Evaluator name
            evaluator: Function (context, conditions) -> bool
        """
        self._condition_evaluators[name] = evaluator

    def check_permission(
        self,
        user_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        server: str = "",
        tool: str = "",
        level: PermissionLevel = PermissionLevel.EXECUTE,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if an operation is permitted.

        Args:
            user_id: User identifier
            roles: User's roles
            server: MCP server name
            tool: Tool name
            level: Required permission level
            context: Additional context for condition evaluation

        Returns:
            True if operation is permitted
        """
        # Collect applicable policies
        applicable_policies: List[PermissionPolicy] = []

        # User-specific policies
        if user_id and user_id in self._user_policies:
            for policy_name in self._user_policies[user_id]:
                if policy_name in self._policies:
                    applicable_policies.append(self._policies[policy_name])

        # Role-based policies
        if roles:
            for role in roles:
                if role in self._role_policies:
                    for policy_name in self._role_policies[role]:
                        if policy_name in self._policies:
                            policy = self._policies[policy_name]
                            if policy not in applicable_policies:
                                applicable_policies.append(policy)

        # If no specific policies, check all policies (for simple setups)
        if not applicable_policies:
            applicable_policies = list(self._policies.values())

        # Sort by priority (highest first)
        applicable_policies.sort(key=lambda p: p.priority, reverse=True)

        # Evaluate policies
        for policy in applicable_policies:
            # Check conditions if any
            if policy.conditions and context:
                if not self._evaluate_conditions(
                    policy.conditions, context
                ):
                    continue

            result = policy.check(server, tool, level)

            if result is not None:
                if result:
                    logger.debug(
                        f"Permission granted: {user_id} -> "
                        f"{server}/{tool} by policy {policy.name}"
                    )
                else:
                    logger.debug(
                        f"Permission denied: {user_id} -> "
                        f"{server}/{tool} by policy {policy.name}"
                    )
                return result

        # Default deny
        logger.debug(
            f"Permission denied (default): {user_id} -> {server}/{tool}"
        )
        return self._default_level >= level

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate dynamic conditions.

        Args:
            conditions: Condition definitions
            context: Evaluation context

        Returns:
            True if conditions are satisfied
        """
        for cond_type, cond_value in conditions.items():
            if cond_type in self._condition_evaluators:
                evaluator = self._condition_evaluators[cond_type]
                if not evaluator(context, cond_value):
                    return False
            elif cond_type == "time_range":
                if not self._check_time_range(cond_value):
                    return False
            elif cond_type == "ip_whitelist":
                ip = context.get("ip_address")
                if ip and ip not in cond_value:
                    return False

        return True

    def _check_time_range(self, time_range: Dict[str, str]) -> bool:
        """Check if current time is within the specified range.

        Args:
            time_range: Dict with 'start' and 'end' times (HH:MM format)

        Returns:
            True if current time is within range
        """
        try:
            now = datetime.now().time()
            start = datetime.strptime(
                time_range.get("start", "00:00"), "%H:%M"
            ).time()
            end = datetime.strptime(
                time_range.get("end", "23:59"), "%H:%M"
            ).time()
            return start <= now <= end
        except Exception:
            return True  # Default allow if parsing fails

    def get_user_permissions(
        self,
        user_id: str,
        roles: Optional[List[str]] = None,
    ) -> List[PermissionPolicy]:
        """Get all policies applicable to a user.

        Args:
            user_id: User identifier
            roles: User's roles

        Returns:
            List of applicable policies
        """
        policies = []

        if user_id in self._user_policies:
            for policy_name in self._user_policies[user_id]:
                if policy_name in self._policies:
                    policies.append(self._policies[policy_name])

        if roles:
            for role in roles:
                if role in self._role_policies:
                    for policy_name in self._role_policies[role]:
                        if policy_name in self._policies:
                            policy = self._policies[policy_name]
                            if policy not in policies:
                                policies.append(policy)

        return policies

    def set_default_level(self, level: PermissionLevel) -> None:
        """Set the default permission level when no policy matches.

        Args:
            level: Default permission level
        """
        self._default_level = level

    def get_policy(self, name: str) -> Optional[PermissionPolicy]:
        """Get a policy by name.

        Args:
            name: Policy name

        Returns:
            Policy or None if not found
        """
        return self._policies.get(name)

    @property
    def policies(self) -> Dict[str, PermissionPolicy]:
        """Get all policies."""
        return self._policies.copy()
