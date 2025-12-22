"""MCP Audit Logging.

This module provides comprehensive audit logging for MCP operations,
enabling compliance tracking and security monitoring.

Features:
    - Structured audit events with timestamps
    - Multiple event types (access, execution, error, admin)
    - Pluggable storage backends
    - Event filtering and querying
    - Async and sync logging support

Example:
    >>> logger = AuditLogger(storage=FileAuditStorage("audit.log"))
    >>> await logger.log(AuditEvent(
    ...     event_type=AuditEventType.TOOL_EXECUTION,
    ...     user_id="user123",
    ...     server="azure-mcp",
    ...     tool="list_vms",
    ...     status="success",
    ... ))
    >>> events = await logger.query(
    ...     filter=AuditFilter(user_id="user123")
    ... )
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable, Awaitable
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import asyncio
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Connection events
    SERVER_CONNECT = "server_connect"
    SERVER_DISCONNECT = "server_disconnect"
    SERVER_ERROR = "server_error"

    # Tool events
    TOOL_LIST = "tool_list"
    TOOL_EXECUTION = "tool_execution"
    TOOL_ERROR = "tool_error"

    # Access events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Admin events
    CONFIG_CHANGE = "config_change"
    POLICY_CHANGE = "policy_change"

    # System events
    SYSTEM_START = "system_start"
    SYSTEM_SHUTDOWN = "system_shutdown"


@dataclass
class AuditEvent:
    """A single audit event.

    Attributes:
        event_id: Unique event identifier
        event_type: Type of event
        timestamp: Event timestamp
        user_id: User who triggered the event
        server: MCP server name
        tool: Tool name (for tool events)
        arguments: Tool arguments (sanitized)
        result: Operation result summary
        status: Event status (success, failure, pending)
        duration_ms: Operation duration in milliseconds
        ip_address: Client IP address
        session_id: Session identifier
        metadata: Additional event metadata
    """

    event_type: AuditEventType
    user_id: Optional[str] = None
    server: Optional[str] = None
    tool: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    status: str = "success"
    duration_ms: Optional[float] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["timestamp"] = self.timestamp.isoformat()

        # Sanitize arguments (remove sensitive data)
        if data["arguments"]:
            data["arguments"] = self._sanitize_arguments(data["arguments"])

        return data

    def _sanitize_arguments(
        self,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Remove sensitive data from arguments.

        Args:
            args: Original arguments

        Returns:
            Sanitized arguments
        """
        sensitive_keys = {
            "password",
            "secret",
            "token",
            "api_key",
            "credential",
            "auth",
            "private_key",
        }

        sanitized = {}
        for key, value in args.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_arguments(value)
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Create AuditEvent from dictionary.

        Args:
            data: Dictionary data

        Returns:
            AuditEvent instance
        """
        data = data.copy()
        data["event_type"] = AuditEventType(data["event_type"])

        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)


@dataclass
class AuditFilter:
    """Filter for querying audit events.

    Attributes:
        user_id: Filter by user
        server: Filter by server
        tool: Filter by tool
        event_types: Filter by event types
        status: Filter by status
        start_time: Filter events after this time
        end_time: Filter events before this time
        limit: Maximum number of events to return
        offset: Offset for pagination
    """

    user_id: Optional[str] = None
    server: Optional[str] = None
    tool: Optional[str] = None
    event_types: Optional[List[AuditEventType]] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0

    def matches(self, event: AuditEvent) -> bool:
        """Check if an event matches this filter.

        Args:
            event: Event to check

        Returns:
            True if event matches filter
        """
        if self.user_id and event.user_id != self.user_id:
            return False
        if self.server and event.server != self.server:
            return False
        if self.tool and event.tool != self.tool:
            return False
        if self.event_types and event.event_type not in self.event_types:
            return False
        if self.status and event.status != self.status:
            return False
        if self.start_time and event.timestamp < self.start_time:
            return False
        if self.end_time and event.timestamp > self.end_time:
            return False
        return True


class AuditStorage(ABC):
    """Abstract base class for audit storage backends."""

    @abstractmethod
    async def store(self, event: AuditEvent) -> bool:
        """Store an audit event.

        Args:
            event: Event to store

        Returns:
            True if stored successfully
        """
        pass

    @abstractmethod
    async def query(
        self,
        filter: Optional[AuditFilter] = None,
    ) -> List[AuditEvent]:
        """Query stored audit events.

        Args:
            filter: Optional filter criteria

        Returns:
            List of matching events
        """
        pass

    @abstractmethod
    async def delete_before(self, timestamp: datetime) -> int:
        """Delete events before a timestamp.

        Args:
            timestamp: Delete events before this time

        Returns:
            Number of events deleted
        """
        pass


class InMemoryAuditStorage(AuditStorage):
    """In-memory audit storage for testing and development.

    Uses a deque with maximum size to prevent unbounded growth.
    """

    def __init__(self, max_size: int = 10000):
        """Initialize in-memory storage.

        Args:
            max_size: Maximum number of events to store
        """
        self._events: deque = deque(maxlen=max_size)
        self._lock = asyncio.Lock()

    async def store(self, event: AuditEvent) -> bool:
        """Store an audit event."""
        async with self._lock:
            self._events.append(event)
        return True

    async def query(
        self,
        filter: Optional[AuditFilter] = None,
    ) -> List[AuditEvent]:
        """Query stored audit events."""
        async with self._lock:
            if filter is None:
                events = list(self._events)[-100:]
            else:
                events = [e for e in self._events if filter.matches(e)]
                events = events[filter.offset : filter.offset + filter.limit]

        # Sort by timestamp descending
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events

    async def delete_before(self, timestamp: datetime) -> int:
        """Delete events before a timestamp."""
        async with self._lock:
            initial_count = len(self._events)
            self._events = deque(
                (e for e in self._events if e.timestamp >= timestamp),
                maxlen=self._events.maxlen,
            )
            return initial_count - len(self._events)


class FileAuditStorage(AuditStorage):
    """File-based audit storage using JSON Lines format."""

    def __init__(self, file_path: str):
        """Initialize file storage.

        Args:
            file_path: Path to audit log file
        """
        self._file_path = file_path
        self._lock = asyncio.Lock()

    async def store(self, event: AuditEvent) -> bool:
        """Store an audit event."""
        try:
            async with self._lock:
                with open(self._file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event.to_dict()) + "\n")
            return True
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")
            return False

    async def query(
        self,
        filter: Optional[AuditFilter] = None,
    ) -> List[AuditEvent]:
        """Query stored audit events."""
        events = []

        try:
            async with self._lock:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                event = AuditEvent.from_dict(data)
                                if filter is None or filter.matches(event):
                                    events.append(event)
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.warning(f"Invalid audit entry: {e}")

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")

        # Apply pagination and sort
        events.sort(key=lambda e: e.timestamp, reverse=True)
        if filter:
            events = events[filter.offset : filter.offset + filter.limit]
        else:
            events = events[:100]

        return events

    async def delete_before(self, timestamp: datetime) -> int:
        """Delete events before a timestamp."""
        deleted = 0

        try:
            async with self._lock:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                kept_lines = []
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            event_time = datetime.fromisoformat(
                                data["timestamp"]
                            )
                            if event_time >= timestamp:
                                kept_lines.append(line + "\n")
                            else:
                                deleted += 1
                        except (json.JSONDecodeError, KeyError):
                            kept_lines.append(line + "\n")

                with open(self._file_path, "w", encoding="utf-8") as f:
                    f.writelines(kept_lines)

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Failed to delete audit events: {e}")

        return deleted


# Type alias for event handlers
AuditEventHandler = Callable[[AuditEvent], Awaitable[None]]


class AuditLogger:
    """MCP Audit Logger.

    Provides comprehensive audit logging with multiple storage backends
    and event handlers for real-time monitoring.

    Example:
        >>> storage = InMemoryAuditStorage()
        >>> logger = AuditLogger(storage=storage)
        >>>
        >>> # Add real-time handler
        >>> async def alert_handler(event):
        ...     if event.status == "failure":
        ...         await send_alert(event)
        >>> logger.add_handler(alert_handler)
        >>>
        >>> # Log events
        >>> await logger.log_tool_execution(
        ...     user_id="user123",
        ...     server="azure-mcp",
        ...     tool="list_vms",
        ...     status="success",
        ...     duration_ms=150.5,
        ... )
    """

    def __init__(
        self,
        storage: Optional[AuditStorage] = None,
        enabled: bool = True,
    ):
        """Initialize the audit logger.

        Args:
            storage: Storage backend (defaults to in-memory)
            enabled: Enable/disable logging
        """
        self._storage = storage or InMemoryAuditStorage()
        self._enabled = enabled
        self._handlers: List[AuditEventHandler] = []

    async def log(self, event: AuditEvent) -> bool:
        """Log an audit event.

        Args:
            event: Event to log

        Returns:
            True if logged successfully
        """
        if not self._enabled:
            return False

        try:
            # Store the event
            success = await self._storage.store(event)

            # Call event handlers
            for handler in self._handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Audit handler error: {e}")

            return success

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    async def log_tool_execution(
        self,
        user_id: str,
        server: str,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
        status: str = "success",
        result: Optional[str] = None,
        duration_ms: Optional[float] = None,
        **kwargs,
    ) -> bool:
        """Log a tool execution event.

        Args:
            user_id: User who executed the tool
            server: MCP server name
            tool: Tool name
            arguments: Tool arguments
            status: Execution status
            result: Execution result summary
            duration_ms: Execution duration
            **kwargs: Additional metadata

        Returns:
            True if logged successfully
        """
        event = AuditEvent(
            event_type=AuditEventType.TOOL_EXECUTION,
            user_id=user_id,
            server=server,
            tool=tool,
            arguments=arguments,
            status=status,
            result=result,
            duration_ms=duration_ms,
            metadata=kwargs,
        )
        return await self.log(event)

    async def log_access(
        self,
        user_id: str,
        server: str,
        tool: str,
        granted: bool,
        reason: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Log an access control event.

        Args:
            user_id: User requesting access
            server: MCP server name
            tool: Tool name
            granted: Whether access was granted
            reason: Reason for decision
            **kwargs: Additional metadata

        Returns:
            True if logged successfully
        """
        event = AuditEvent(
            event_type=(
                AuditEventType.ACCESS_GRANTED
                if granted
                else AuditEventType.ACCESS_DENIED
            ),
            user_id=user_id,
            server=server,
            tool=tool,
            status="granted" if granted else "denied",
            result=reason,
            metadata=kwargs,
        )
        return await self.log(event)

    async def log_server_event(
        self,
        event_type: AuditEventType,
        server: str,
        status: str = "success",
        error: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Log a server connection event.

        Args:
            event_type: Type of server event
            server: MCP server name
            status: Event status
            error: Error message if any
            **kwargs: Additional metadata

        Returns:
            True if logged successfully
        """
        event = AuditEvent(
            event_type=event_type,
            server=server,
            status=status,
            result=error,
            metadata=kwargs,
        )
        return await self.log(event)

    async def query(
        self,
        filter: Optional[AuditFilter] = None,
    ) -> List[AuditEvent]:
        """Query audit events.

        Args:
            filter: Optional filter criteria

        Returns:
            List of matching events
        """
        return await self._storage.query(filter)

    async def get_user_activity(
        self,
        user_id: str,
        hours: int = 24,
    ) -> List[AuditEvent]:
        """Get recent activity for a user.

        Args:
            user_id: User identifier
            hours: Hours of history to retrieve

        Returns:
            List of user's events
        """
        filter = AuditFilter(
            user_id=user_id,
            start_time=datetime.utcnow() - timedelta(hours=hours),
        )
        return await self.query(filter)

    async def get_server_activity(
        self,
        server: str,
        hours: int = 24,
    ) -> List[AuditEvent]:
        """Get recent activity for a server.

        Args:
            server: Server name
            hours: Hours of history to retrieve

        Returns:
            List of server's events
        """
        filter = AuditFilter(
            server=server,
            start_time=datetime.utcnow() - timedelta(hours=hours),
        )
        return await self.query(filter)

    async def cleanup(self, days: int = 30) -> int:
        """Clean up old audit events.

        Args:
            days: Delete events older than this

        Returns:
            Number of events deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = await self._storage.delete_before(cutoff)
        logger.info(f"Cleaned up {deleted} audit events older than {days} days")
        return deleted

    def add_handler(self, handler: AuditEventHandler) -> None:
        """Add an event handler for real-time processing.

        Args:
            handler: Async callback for events
        """
        self._handlers.append(handler)

    def remove_handler(self, handler: AuditEventHandler) -> None:
        """Remove an event handler.

        Args:
            handler: Handler to remove
        """
        if handler in self._handlers:
            self._handlers.remove(handler)

    @property
    def enabled(self) -> bool:
        """Check if logging is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable/disable logging."""
        self._enabled = value
