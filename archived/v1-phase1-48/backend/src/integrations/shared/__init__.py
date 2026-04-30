"""
Shared Integration Protocols and Interfaces.

Sprint 116: Provides Protocol-based interfaces for cross-module communication
without creating circular dependencies.

Usage:
    L5 (orchestration/hybrid) depends on shared/protocols
    L6 (claude_sdk/agent_framework) implements shared/protocols

    This breaks:
        L5 -> L6 (for execution) -> L5 (for callbacks)
    Into:
        L5 -> shared/protocols <- L6
"""

from .protocols import (
    ExecutionEngineProtocol,
    ExecutionRequest,
    ExecutionResult,
    OrchestrationCallbackProtocol,
    ToolCallbackProtocol,
    ToolCallEvent,
    ToolCallStatus,
    ToolResultEvent,
    SwarmCallbackProtocol,
    SwarmEvent,
    check_protocol_compliance,
)

__all__ = [
    "ToolCallbackProtocol",
    "ToolCallEvent",
    "ToolCallStatus",
    "ToolResultEvent",
    "ExecutionEngineProtocol",
    "ExecutionRequest",
    "ExecutionResult",
    "OrchestrationCallbackProtocol",
    "SwarmCallbackProtocol",
    "SwarmEvent",
    "check_protocol_compliance",
]
