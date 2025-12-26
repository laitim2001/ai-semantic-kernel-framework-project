"""Audit Hook for Claude SDK.

Sprint 49: S49-3 - Hooks System (10 pts)
Logs all activities with sensitive data redaction.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Pattern, Set

from .base import Hook
from ..types import (
    HookResult,
    QueryContext,
    ToolCallContext,
    ToolResultContext,
)


# Default patterns for sensitive data redaction
DEFAULT_REDACT_PATTERNS: List[str] = [
    # API keys and tokens
    r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
    r"(?i)(token|secret|password)\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?",
    r"(?i)bearer\s+([a-zA-Z0-9_\-\.]+)",

    # Common credential patterns
    r"(?i)(sk-[a-zA-Z0-9]{20,})",  # OpenAI API keys
    r"(?i)(xoxb-[a-zA-Z0-9\-]+)",  # Slack tokens
    r"(?i)(ghp_[a-zA-Z0-9]{36})",  # GitHub tokens

    # Email addresses (optional)
    r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
]

# Keys that should have their values redacted
SENSITIVE_KEYS: Set[str] = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "private_key",
    "credential",
    "auth",
}


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: float
    event_type: str  # 'session_start', 'tool_call', 'query', 'error', etc.
    session_id: Optional[str]
    details: Dict[str, Any]
    duration: Optional[float] = None


@dataclass
class AuditLog:
    """Collection of audit entries for a session."""

    session_id: str
    entries: List[AuditEntry] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    def add(self, entry: AuditEntry) -> None:
        """Add an entry to the log."""
        self.entries.append(entry)

    def to_dict(self) -> Dict[str, Any]:
        """Convert log to dictionary."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "entry_count": len(self.entries),
            "entries": [
                {
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "details": e.details,
                    "duration": e.duration,
                }
                for e in self.entries
            ],
        }


class AuditHook(Hook):
    """Hook that logs all activities with sensitive data redaction.

    Captures all tool calls, queries, and errors for audit purposes.
    Automatically redacts sensitive data like API keys and passwords.

    Args:
        logger: Python logger instance (optional, creates default)
        log_level: Logging level (default: INFO)
        redact_patterns: Additional regex patterns for redaction
        redact_keys: Additional dictionary keys to redact
        log_callback: Optional callback for custom log handling
        include_results: Whether to log tool results (may be verbose)

    Example:
        audit = AuditHook(logger=my_logger, include_results=False)
        hook_chain.add(audit)
    """

    name: str = "audit"
    priority: int = 10  # Low priority - run after other hooks

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        log_level: int = logging.INFO,
        redact_patterns: Optional[List[str]] = None,
        redact_keys: Optional[Set[str]] = None,
        log_callback: Optional[Callable[[AuditEntry], None]] = None,
        include_results: bool = True,
    ):
        self.logger = logger or logging.getLogger("claude_sdk.audit")
        self.log_level = log_level
        self.log_callback = log_callback
        self.include_results = include_results

        # Compile redaction patterns
        patterns = DEFAULT_REDACT_PATTERNS.copy()
        if redact_patterns:
            patterns.extend(redact_patterns)
        self._redact_patterns: List[Pattern] = [
            re.compile(p) for p in patterns
        ]

        # Sensitive keys
        self._sensitive_keys = SENSITIVE_KEYS.copy()
        if redact_keys:
            self._sensitive_keys.update(redact_keys)

        # Session logs
        self._session_logs: Dict[str, AuditLog] = {}

        # Timing trackers
        self._tool_start_times: Dict[str, float] = {}
        self._query_start_times: Dict[str, float] = {}

    async def on_session_start(self, session_id: str) -> None:
        """Start logging for a session."""
        self._session_logs[session_id] = AuditLog(session_id=session_id)
        self._log_entry(
            session_id,
            AuditEntry(
                timestamp=time.time(),
                event_type="session_start",
                session_id=session_id,
                details={"action": "session_started"},
            ),
        )

    async def on_session_end(self, session_id: str) -> None:
        """End logging for a session."""
        self._log_entry(
            session_id,
            AuditEntry(
                timestamp=time.time(),
                event_type="session_end",
                session_id=session_id,
                details={"action": "session_ended"},
            ),
        )

    async def on_query_start(self, context: QueryContext) -> HookResult:
        """Log query start."""
        if context.session_id:
            self._query_start_times[context.session_id] = time.time()

        # Redact prompt content
        redacted_prompt = self._redact_string(context.prompt)

        self._log_entry(
            context.session_id,
            AuditEntry(
                timestamp=time.time(),
                event_type="query_start",
                session_id=context.session_id,
                details={
                    "prompt_length": len(context.prompt),
                    "prompt_preview": redacted_prompt[:200],
                    "tools": context.tools,
                },
            ),
        )
        return HookResult.ALLOW

    async def on_query_end(self, context: QueryContext, result: str) -> None:
        """Log query end."""
        duration = None
        if context.session_id and context.session_id in self._query_start_times:
            duration = time.time() - self._query_start_times.pop(context.session_id)

        self._log_entry(
            context.session_id,
            AuditEntry(
                timestamp=time.time(),
                event_type="query_end",
                session_id=context.session_id,
                details={
                    "result_length": len(result),
                },
                duration=duration,
            ),
        )

    async def on_tool_call(self, context: ToolCallContext) -> HookResult:
        """Log tool call."""
        tool_key = f"{context.session_id}:{context.tool_name}"
        self._tool_start_times[tool_key] = time.time()

        # Redact args
        redacted_args = self._redact_dict(context.args)

        self._log_entry(
            context.session_id,
            AuditEntry(
                timestamp=time.time(),
                event_type="tool_call",
                session_id=context.session_id,
                details={
                    "tool_name": context.tool_name,
                    "tool_source": context.tool_source,
                    "mcp_server": context.mcp_server,
                    "args": redacted_args,
                },
            ),
        )
        return HookResult.ALLOW

    async def on_tool_result(self, context: ToolResultContext) -> None:
        """Log tool result."""
        tool_key = f"{context.session_id}:{context.tool_name}"
        duration = None
        if tool_key in self._tool_start_times:
            duration = time.time() - self._tool_start_times.pop(tool_key)

        details: Dict[str, Any] = {
            "tool_name": context.tool_name,
            "success": context.success,
            "result_length": len(context.result) if context.result else 0,
        }

        if self.include_results:
            # Redact result content
            redacted_result = self._redact_string(context.result or "")
            details["result_preview"] = redacted_result[:200]

        self._log_entry(
            context.session_id,
            AuditEntry(
                timestamp=time.time(),
                event_type="tool_result",
                session_id=context.session_id,
                details=details,
                duration=duration or context.duration,
            ),
        )

    async def on_error(self, error: Exception) -> None:
        """Log error."""
        self._log_entry(
            None,
            AuditEntry(
                timestamp=time.time(),
                event_type="error",
                session_id=None,
                details={
                    "error_type": type(error).__name__,
                    "error_message": self._redact_string(str(error)),
                },
            ),
        )

    def get_session_log(self, session_id: str) -> Optional[AuditLog]:
        """Get audit log for a session."""
        return self._session_logs.get(session_id)

    def get_all_logs(self) -> Dict[str, AuditLog]:
        """Get all session logs."""
        return dict(self._session_logs)

    def clear_logs(self, session_id: Optional[str] = None) -> None:
        """Clear logs for a session or all sessions."""
        if session_id:
            self._session_logs.pop(session_id, None)
        else:
            self._session_logs.clear()

    def _log_entry(
        self,
        session_id: Optional[str],
        entry: AuditEntry,
    ) -> None:
        """Log an entry to all configured outputs."""
        # Add to session log
        if session_id and session_id in self._session_logs:
            self._session_logs[session_id].add(entry)

        # Log to Python logger
        self.logger.log(
            self.log_level,
            f"[{entry.event_type}] {json.dumps(entry.details)}",
        )

        # Custom callback
        if self.log_callback:
            self.log_callback(entry)

    def _redact_string(self, text: str) -> str:
        """Redact sensitive data from a string."""
        result = text
        for pattern in self._redact_patterns:
            result = pattern.sub("[REDACTED]", result)
        return result

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data from a dictionary."""
        result = {}
        for key, value in data.items():
            # Check if key is sensitive
            key_lower = key.lower()
            if any(s in key_lower for s in self._sensitive_keys):
                result[key] = "[REDACTED]"
            elif isinstance(value, str):
                result[key] = self._redact_string(value)
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._redact_dict(v) if isinstance(v, dict)
                    else self._redact_string(v) if isinstance(v, str)
                    else v
                    for v in value
                ]
            else:
                result[key] = value
        return result
