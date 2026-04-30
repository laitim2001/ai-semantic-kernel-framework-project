# =============================================================================
# IPA Platform - Tool Security Gateway
# =============================================================================
# Sprint 109: Story 1 (4 SP)
# Phase 36: Security Hardening
#
# Tool Security Gateway — validates all Orchestrator tool calls.
#
# Four-layer security:
# 1. Input Sanitization — check params for injection patterns, length limits
# 2. Permission Check — verify user role allows this tool
# 3. Rate Limiting — per-user per-tool call limits
# 4. Audit Logging — record every tool call with who/what/when/result
# =============================================================================

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Enums & Data Classes
# =============================================================================


class UserRole(str, Enum):
    """User roles for tool permission control."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


@dataclass
class ToolCallValidation:
    """Result of a tool call validation."""

    allowed: bool
    reason: str
    sanitized_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _RateLimitEntry:
    """Tracks call counts within a time window."""

    count: int = 0
    window_start: float = 0.0


# =============================================================================
# Constants
# =============================================================================

# Injection patterns to detect in tool call parameters
_INJECTION_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r";\s*DROP\b", re.IGNORECASE),
    re.compile(r";\s*DELETE\b", re.IGNORECASE),
    re.compile(r";\s*UPDATE\b", re.IGNORECASE),
    re.compile(r";\s*INSERT\b", re.IGNORECASE),
    re.compile(r"--\s*$", re.MULTILINE),
    re.compile(r"UNION\s+SELECT", re.IGNORECASE),
    re.compile(r"<script\b", re.IGNORECASE),
    re.compile(r"</script>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"IGNORE\s+PREVIOUS", re.IGNORECASE),
    re.compile(r"DISREGARD\s+(ALL\s+)?PREVIOUS", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"__import__\s*\(", re.IGNORECASE),
    re.compile(r"os\.system\s*\(", re.IGNORECASE),
    re.compile(r"subprocess\.", re.IGNORECASE),
]

# Maximum length for any single parameter value
_MAX_PARAM_VALUE_LENGTH = 10_000

# Role-based tool whitelist
_ROLE_TOOL_PERMISSIONS: Dict[UserRole, FrozenSet[str]] = {
    UserRole.ADMIN: frozenset(),  # Empty means all tools allowed
    UserRole.OPERATOR: frozenset(
        {
            "route_intent",
            "assess_risk",
            "search_memory",
            "respond_to_user",
            "create_task",
        }
    ),
    UserRole.VIEWER: frozenset(
        {
            "route_intent",
            "search_memory",
            "respond_to_user",
        }
    ),
}

# High-risk tools with stricter rate limits
_HIGH_RISK_TOOLS: FrozenSet[str] = frozenset(
    {
        "dispatch_workflow",
        "dispatch_swarm",
    }
)

# Rate limit settings
_DEFAULT_RATE_LIMIT_PER_MINUTE = 30
_HIGH_RISK_RATE_LIMIT_PER_MINUTE = 5
_RATE_WINDOW_SECONDS = 60.0


# =============================================================================
# ToolSecurityGateway
# =============================================================================


class ToolSecurityGateway:
    """
    Validates all Orchestrator tool calls through four security layers.

    Usage as a standalone validator:
        gateway = ToolSecurityGateway()
        result = await gateway.validate_tool_call(
            tool_name="route_intent",
            params={"query": "hello"},
            user_id="user-123",
            user_role=UserRole.OPERATOR,
        )
        if not result.allowed:
            raise PermissionError(result.reason)

    Usage as a decorator:
        @gateway.secure_tool_call(tool_name="route_intent")
        async def route_intent(params, user_id, user_role):
            ...
    """

    def __init__(
        self,
        custom_permissions: Optional[Dict[UserRole, Set[str]]] = None,
        default_rate_limit: int = _DEFAULT_RATE_LIMIT_PER_MINUTE,
        high_risk_rate_limit: int = _HIGH_RISK_RATE_LIMIT_PER_MINUTE,
        max_param_length: int = _MAX_PARAM_VALUE_LENGTH,
    ):
        """
        Initialize ToolSecurityGateway.

        Args:
            custom_permissions: Override default role-tool permissions.
            default_rate_limit: Max tool calls per user per minute (default tools).
            high_risk_rate_limit: Max tool calls per user per minute (high-risk tools).
            max_param_length: Maximum allowed length for any single parameter value.
        """
        self._permissions: Dict[UserRole, FrozenSet[str]] = {}
        if custom_permissions:
            for role, tools in custom_permissions.items():
                self._permissions[role] = frozenset(tools)
        else:
            self._permissions = dict(_ROLE_TOOL_PERMISSIONS)

        self._default_rate_limit = default_rate_limit
        self._high_risk_rate_limit = high_risk_rate_limit
        self._max_param_length = max_param_length

        # In-memory rate limit counters: key = "{user_id}:{tool_name}"
        # Phase 36 Sprint 110 will migrate to Redis
        self._rate_counters: Dict[str, _RateLimitEntry] = {}

    async def validate_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: str,
        user_role: UserRole,
    ) -> ToolCallValidation:
        """
        Validate a tool call through all four security layers.

        Args:
            tool_name: Name of the tool being called.
            params: Parameters for the tool call.
            user_id: ID of the user making the call.
            user_role: Role of the user making the call.

        Returns:
            ToolCallValidation with allowed status, reason, and sanitized params.
        """
        timestamp = time.time()

        # Layer 1: Input Sanitization
        sanitization_result = self._sanitize_params(params)
        if not sanitization_result["clean"]:
            reason = (
                f"Input sanitization failed: {sanitization_result['reason']}"
            )
            self._audit_log(
                tool_name=tool_name,
                user_id=user_id,
                params=params,
                allowed=False,
                reason=reason,
                timestamp=timestamp,
            )
            return ToolCallValidation(
                allowed=False,
                reason=reason,
                sanitized_params={},
            )

        sanitized_params = sanitization_result["sanitized_params"]

        # Layer 2: Permission Check
        if not self._check_permission(user_role, tool_name):
            reason = (
                f"Permission denied: role '{user_role.value}' "
                f"cannot access tool '{tool_name}'"
            )
            self._audit_log(
                tool_name=tool_name,
                user_id=user_id,
                params=sanitized_params,
                allowed=False,
                reason=reason,
                timestamp=timestamp,
            )
            return ToolCallValidation(
                allowed=False,
                reason=reason,
                sanitized_params=sanitized_params,
            )

        # Layer 3: Rate Limiting
        rate_ok, rate_reason = self._check_rate_limit(
            user_id=user_id,
            tool_name=tool_name,
            timestamp=timestamp,
        )
        if not rate_ok:
            self._audit_log(
                tool_name=tool_name,
                user_id=user_id,
                params=sanitized_params,
                allowed=False,
                reason=rate_reason,
                timestamp=timestamp,
            )
            return ToolCallValidation(
                allowed=False,
                reason=rate_reason,
                sanitized_params=sanitized_params,
            )

        # Layer 4: Audit Logging (success)
        self._audit_log(
            tool_name=tool_name,
            user_id=user_id,
            params=sanitized_params,
            allowed=True,
            reason="All security checks passed",
            timestamp=timestamp,
        )

        return ToolCallValidation(
            allowed=True,
            reason="All security checks passed",
            sanitized_params=sanitized_params,
        )

    def secure_tool_call(
        self, tool_name: str
    ) -> Callable[..., Any]:
        """
        Decorator to secure an async tool call function.

        The decorated function must accept keyword arguments:
        user_id (str) and user_role (UserRole).

        Args:
            tool_name: Name of the tool to secure.

        Returns:
            Decorator function.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(
                *args: Any,
                params: Optional[Dict[str, Any]] = None,
                user_id: str = "unknown",
                user_role: UserRole = UserRole.VIEWER,
                **kwargs: Any,
            ) -> Any:
                call_params = params or {}
                validation = await self.validate_tool_call(
                    tool_name=tool_name,
                    params=call_params,
                    user_id=user_id,
                    user_role=user_role,
                )
                if not validation.allowed:
                    raise PermissionError(
                        f"Tool call '{tool_name}' denied: {validation.reason}"
                    )
                return await func(
                    *args,
                    params=validation.sanitized_params,
                    user_id=user_id,
                    user_role=user_role,
                    **kwargs,
                )

            return wrapper

        return decorator

    # =========================================================================
    # Layer 1: Input Sanitization
    # =========================================================================

    def _sanitize_params(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check parameters for injection patterns and length violations.

        Returns:
            Dict with 'clean' (bool), 'reason' (str), 'sanitized_params' (dict).
        """
        sanitized: Dict[str, Any] = {}

        for key, value in params.items():
            # Check key name for suspicious patterns
            if not isinstance(key, str) or len(key) > 256:
                return {
                    "clean": False,
                    "reason": f"Invalid parameter key: {repr(key)[:50]}",
                    "sanitized_params": {},
                }

            # Recursively sanitize values
            result = self._sanitize_value(key, value)
            if not result["clean"]:
                return result
            sanitized[key] = result["value"]

        return {
            "clean": True,
            "reason": "",
            "sanitized_params": sanitized,
        }

    def _sanitize_value(
        self, key: str, value: Any
    ) -> Dict[str, Any]:
        """Sanitize a single parameter value (recursive for dicts/lists)."""
        if value is None:
            return {"clean": True, "value": None}

        if isinstance(value, (int, float, bool)):
            return {"clean": True, "value": value}

        if isinstance(value, str):
            # Length check
            if len(value) > self._max_param_length:
                return {
                    "clean": False,
                    "reason": (
                        f"Parameter '{key}' exceeds max length "
                        f"({len(value)} > {self._max_param_length})"
                    ),
                    "sanitized_params": {},
                }
            # Injection pattern check
            for pattern in _INJECTION_PATTERNS:
                if pattern.search(value):
                    return {
                        "clean": False,
                        "reason": (
                            f"Injection pattern detected in parameter '{key}': "
                            f"matched pattern '{pattern.pattern}'"
                        ),
                        "sanitized_params": {},
                    }
            return {"clean": True, "value": value}

        if isinstance(value, list):
            sanitized_list = []
            for i, item in enumerate(value):
                result = self._sanitize_value(f"{key}[{i}]", item)
                if not result["clean"]:
                    return result
                sanitized_list.append(result["value"])
            return {"clean": True, "value": sanitized_list}

        if isinstance(value, dict):
            sanitized_dict: Dict[str, Any] = {}
            for k, v in value.items():
                result = self._sanitize_value(f"{key}.{k}", v)
                if not result["clean"]:
                    return result
                sanitized_dict[k] = result["value"]
            return {"clean": True, "value": sanitized_dict}

        # Unknown types: convert to string and sanitize
        str_value = str(value)
        return self._sanitize_value(key, str_value)

    # =========================================================================
    # Layer 2: Permission Check
    # =========================================================================

    def _check_permission(self, user_role: UserRole, tool_name: str) -> bool:
        """
        Check if the user role is allowed to call the specified tool.

        Admin role (empty frozenset) means all tools are allowed.

        Args:
            user_role: The user's role.
            tool_name: The tool being called.

        Returns:
            True if allowed, False otherwise.
        """
        allowed_tools = self._permissions.get(user_role)
        if allowed_tools is None:
            # Unknown role — deny by default
            return False
        if len(allowed_tools) == 0:
            # Empty set = all tools allowed (Admin)
            return True
        return tool_name in allowed_tools

    # =========================================================================
    # Layer 3: Rate Limiting
    # =========================================================================

    def _check_rate_limit(
        self,
        user_id: str,
        tool_name: str,
        timestamp: float,
    ) -> tuple[bool, str]:
        """
        Check per-user per-tool rate limits.

        Uses in-memory counters with sliding window.
        Phase 36 Sprint 110 will migrate to Redis.

        Args:
            user_id: The user ID.
            tool_name: The tool being called.
            timestamp: Current timestamp.

        Returns:
            Tuple of (allowed: bool, reason: str).
        """
        # Determine rate limit for this tool
        if tool_name in _HIGH_RISK_TOOLS:
            limit = self._high_risk_rate_limit
        else:
            limit = self._default_rate_limit

        counter_key = f"{user_id}:{tool_name}"
        entry = self._rate_counters.get(counter_key)

        if entry is None:
            # First call — initialize counter
            self._rate_counters[counter_key] = _RateLimitEntry(
                count=1, window_start=timestamp
            )
            return True, ""

        # Check if window has expired
        elapsed = timestamp - entry.window_start
        if elapsed >= _RATE_WINDOW_SECONDS:
            # Reset window
            entry.count = 1
            entry.window_start = timestamp
            return True, ""

        # Within window — check limit
        if entry.count >= limit:
            remaining = _RATE_WINDOW_SECONDS - elapsed
            reason = (
                f"Rate limit exceeded for tool '{tool_name}': "
                f"{entry.count}/{limit} calls per minute "
                f"(retry in {remaining:.0f}s)"
            )
            return False, reason

        # Increment counter
        entry.count += 1
        return True, ""

    # =========================================================================
    # Layer 4: Audit Logging
    # =========================================================================

    def _audit_log(
        self,
        tool_name: str,
        user_id: str,
        params: Dict[str, Any],
        allowed: bool,
        reason: str,
        timestamp: float,
    ) -> None:
        """
        Record a tool call for audit purposes.

        Args:
            tool_name: Name of the tool called.
            user_id: ID of the user.
            params: Parameters (sanitized if available).
            allowed: Whether the call was allowed.
            reason: Reason for the decision.
            timestamp: When the call was made.
        """
        # Truncate params for logging to avoid excessive log sizes
        param_keys = list(params.keys()) if params else []

        log_data = {
            "event": "tool_call_validation",
            "tool_name": tool_name,
            "user_id": user_id,
            "param_keys": param_keys,
            "allowed": allowed,
            "reason": reason,
            "timestamp": timestamp,
        }

        if allowed:
            logger.info(
                "Tool call allowed: tool=%s user=%s params_keys=%s",
                tool_name,
                user_id,
                param_keys,
                extra=log_data,
            )
        else:
            logger.warning(
                "Tool call denied: tool=%s user=%s reason=%s",
                tool_name,
                user_id,
                reason,
                extra=log_data,
            )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_allowed_tools(self, user_role: UserRole) -> List[str]:
        """
        Get the list of tools allowed for a given role.

        Args:
            user_role: The user role to check.

        Returns:
            List of allowed tool names. Empty list for Admin means all tools.
        """
        allowed = self._permissions.get(user_role, frozenset())
        return sorted(allowed)

    def reset_rate_limits(self, user_id: Optional[str] = None) -> None:
        """
        Reset rate limit counters.

        Args:
            user_id: If provided, only reset for this user.
                     If None, reset all counters.
        """
        if user_id is None:
            self._rate_counters.clear()
            logger.info("All rate limit counters reset")
        else:
            keys_to_remove = [
                k for k in self._rate_counters if k.startswith(f"{user_id}:")
            ]
            for key in keys_to_remove:
                del self._rate_counters[key]
            logger.info("Rate limit counters reset for user=%s", user_id)
