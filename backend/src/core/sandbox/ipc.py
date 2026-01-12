# =============================================================================
# IPA Platform - IPC Protocol for Sandbox Communication
# =============================================================================
# Sprint 78: S78-1 - IPC Communication and Event Forwarding (7 pts)
#
# This module implements the IPC protocol for communication between the
# main process and sandbox worker processes.
#
# Protocol: JSON-RPC 2.0 over stdin/stdout
#
# Message Types:
#   - Request: Main -> Sandbox (execute, shutdown, ping)
#   - Response: Sandbox -> Main (result or error)
#   - Event: Sandbox -> Main (streaming events like TEXT_DELTA)
#
# =============================================================================

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Union


logger = logging.getLogger(__name__)


class IPCEventType(Enum):
    """Event types for IPC communication.

    These map to AG-UI Protocol events for frontend compatibility.
    """
    # Text events
    TEXT_DELTA = "TEXT_DELTA"
    TEXT_COMPLETE = "TEXT_COMPLETE"

    # Tool events
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_DELTA = "TOOL_CALL_DELTA"
    TOOL_CALL_RESULT = "TOOL_CALL_RESULT"

    # Thinking events
    THINKING_START = "THINKING_START"
    THINKING_DELTA = "THINKING_DELTA"
    THINKING_COMPLETE = "THINKING_COMPLETE"

    # State events
    STATE_UPDATE = "STATE_UPDATE"

    # Lifecycle events
    RUN_START = "RUN_START"
    RUN_COMPLETE = "RUN_COMPLETE"
    RUN_ERROR = "RUN_ERROR"

    # Control events
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"
    HEARTBEAT = "HEARTBEAT"


class IPCMethod(Enum):
    """RPC method names for IPC requests."""
    EXECUTE = "execute"
    SHUTDOWN = "shutdown"
    PING = "ping"
    EVENT = "event"


@dataclass
class IPCRequest:
    """JSON-RPC 2.0 Request structure.

    Attributes:
        method: The RPC method to call
        params: Method parameters
        id: Request identifier (optional for notifications)
    """
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params,
        }
        if self.id is not None:
            result["id"] = self.id
        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPCRequest":
        """Create from dictionary."""
        return cls(
            method=data.get("method", ""),
            params=data.get("params", {}),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )


@dataclass
class IPCResponse:
    """JSON-RPC 2.0 Response structure.

    Attributes:
        result: Success result (mutually exclusive with error)
        error: Error information (mutually exclusive with result)
        id: Corresponding request identifier
    """
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"jsonrpc": self.jsonrpc}

        if self.error is not None:
            result["error"] = self.error
        else:
            result["result"] = self.result or {}

        if self.id is not None:
            result["id"] = self.id

        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPCResponse":
        """Create from dictionary."""
        return cls(
            result=data.get("result"),
            error=data.get("error"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )

    @property
    def is_error(self) -> bool:
        """Check if this is an error response."""
        return self.error is not None

    @property
    def is_success(self) -> bool:
        """Check if this is a success response."""
        return self.error is None


@dataclass
class IPCEvent:
    """IPC Event structure for streaming notifications.

    Attributes:
        type: Event type from IPCEventType
        data: Event payload
        timestamp: When the event occurred
    """
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_sse_event(self) -> Dict[str, Any]:
        """Convert to SSE event format for frontend.

        Returns:
            Dictionary with 'event' and 'data' keys for SSE transmission.
        """
        # Map IPC event types to SSE event names
        event_name = self.type.lower()

        return {
            "event": event_name,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPCEvent":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            type=data.get("type", "unknown"),
            data=data.get("data", {}),
            timestamp=timestamp,
        )


class IPCProtocol:
    """Protocol handler for IPC communication.

    Manages encoding/decoding of messages and provides utilities
    for building requests and parsing responses.

    Example:
        protocol = IPCProtocol()

        # Create a request
        request = protocol.create_execute_request(
            message="Analyze this",
            attachments=[],
            session_id="session-123"
        )

        # Encode for transmission
        line = protocol.encode(request.to_dict())

        # Decode response
        response_data = protocol.decode(received_line)
        response = IPCResponse.from_dict(response_data)
    """

    def __init__(self):
        """Initialize the protocol handler."""
        self._request_counter = 0

    def create_request_id(self) -> str:
        """Generate a unique request ID."""
        self._request_counter += 1
        return f"req-{self._request_counter}"

    def create_execute_request(
        self,
        message: str,
        attachments: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> IPCRequest:
        """Create an execute request.

        Args:
            message: The message/prompt to execute
            attachments: List of file attachments
            session_id: Optional session identifier
            config: Optional execution configuration
            stream: Whether to stream the response

        Returns:
            IPCRequest ready for transmission
        """
        return IPCRequest(
            method=IPCMethod.EXECUTE.value,
            params={
                "message": message,
                "attachments": attachments,
                "session_id": session_id,
                "config": config or {},
                "stream": stream,
            },
            id=self.create_request_id(),
        )

    def create_shutdown_request(self) -> IPCRequest:
        """Create a shutdown request."""
        return IPCRequest(
            method=IPCMethod.SHUTDOWN.value,
            params={},
            id=self.create_request_id(),
        )

    def create_ping_request(self) -> IPCRequest:
        """Create a ping request for health check."""
        return IPCRequest(
            method=IPCMethod.PING.value,
            params={},
            id=self.create_request_id(),
        )

    def encode(self, message: Dict[str, Any]) -> str:
        """Encode a message for transmission.

        Args:
            message: Message dictionary to encode

        Returns:
            JSON string with newline terminator
        """
        return json.dumps(message) + "\n"

    def decode(self, line: str) -> Dict[str, Any]:
        """Decode a received message.

        Args:
            line: Raw line received from IPC

        Returns:
            Parsed message dictionary

        Raises:
            json.JSONDecodeError: If line is not valid JSON
        """
        return json.loads(line.strip())

    def is_event(self, message: Dict[str, Any]) -> bool:
        """Check if a message is an event notification.

        Events are JSON-RPC notifications without an 'id' field
        and with method='event'.
        """
        return (
            message.get("method") == IPCMethod.EVENT.value and
            "id" not in message
        )

    def is_response(self, message: Dict[str, Any]) -> bool:
        """Check if a message is a response.

        Responses have 'result' or 'error' and typically have 'id'.
        """
        return "result" in message or "error" in message

    def parse_event(self, message: Dict[str, Any]) -> IPCEvent:
        """Parse an event notification.

        Args:
            message: Raw message dictionary

        Returns:
            Parsed IPCEvent
        """
        params = message.get("params", {})
        return IPCEvent.from_dict(params)

    def parse_response(self, message: Dict[str, Any]) -> IPCResponse:
        """Parse a response message.

        Args:
            message: Raw message dictionary

        Returns:
            Parsed IPCResponse
        """
        return IPCResponse.from_dict(message)


class IPCError(Exception):
    """Base exception for IPC errors."""
    pass


class IPCTimeoutError(IPCError):
    """Timeout waiting for IPC response."""
    pass


class IPCConnectionError(IPCError):
    """Connection to worker process failed."""
    pass


class IPCProtocolError(IPCError):
    """Protocol violation in IPC communication."""
    pass


def create_error_response(
    code: int,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> IPCResponse:
    """Create a standardized error response.

    Standard error codes:
        -32700: Parse error
        -32600: Invalid request
        -32601: Method not found
        -32602: Invalid params
        -32603: Internal error
        -32000 to -32099: Server errors

    Args:
        code: Error code
        message: Error message
        data: Additional error data
        request_id: Corresponding request ID

    Returns:
        IPCResponse with error
    """
    error_dict = {
        "code": code,
        "message": message,
    }
    if data:
        error_dict["data"] = data

    return IPCResponse(
        error=error_dict,
        id=request_id,
    )


def create_success_response(
    result: Dict[str, Any],
    request_id: Optional[str] = None
) -> IPCResponse:
    """Create a success response.

    Args:
        result: Result data
        request_id: Corresponding request ID

    Returns:
        IPCResponse with result
    """
    return IPCResponse(
        result=result,
        id=request_id,
    )


def create_event_notification(
    event_type: Union[str, IPCEventType],
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create an event notification message.

    Args:
        event_type: Type of event
        data: Event data

    Returns:
        JSON-RPC notification dictionary
    """
    if isinstance(event_type, IPCEventType):
        event_type = event_type.value

    return {
        "jsonrpc": "2.0",
        "method": IPCMethod.EVENT.value,
        "params": {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        },
    }


# Event type mapping for AG-UI compatibility
AG_UI_EVENT_MAPPING = {
    IPCEventType.TEXT_DELTA.value: "text_delta",
    IPCEventType.TEXT_COMPLETE.value: "text_complete",
    IPCEventType.TOOL_CALL_START.value: "tool_call_start",
    IPCEventType.TOOL_CALL_DELTA.value: "tool_call_delta",
    IPCEventType.TOOL_CALL_RESULT.value: "tool_call_result",
    IPCEventType.THINKING_START.value: "thinking_start",
    IPCEventType.THINKING_DELTA.value: "thinking_delta",
    IPCEventType.THINKING_COMPLETE.value: "thinking_complete",
    IPCEventType.STATE_UPDATE.value: "state_update",
    IPCEventType.RUN_START.value: "run_start",
    IPCEventType.RUN_COMPLETE.value: "run_complete",
    IPCEventType.RUN_ERROR.value: "run_error",
    IPCEventType.COMPLETE.value: "complete",
    IPCEventType.ERROR.value: "error",
    IPCEventType.HEARTBEAT.value: "heartbeat",
}


def map_ipc_to_sse_event(ipc_event: IPCEvent) -> Dict[str, Any]:
    """Map an IPC event to SSE event format.

    Args:
        ipc_event: The IPC event to map

    Returns:
        SSE event dictionary with 'event' and 'data' keys
    """
    event_name = AG_UI_EVENT_MAPPING.get(
        ipc_event.type,
        ipc_event.type.lower()
    )

    return {
        "event": event_name,
        "data": ipc_event.data,
    }
