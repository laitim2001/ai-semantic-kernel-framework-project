# =============================================================================
# IPA Platform - Sandbox Process Isolation Module
# =============================================================================
# Sprint 77: Phase 21 - Sandbox Security Architecture
#
# This module provides process-level isolation for Claude Agent execution,
# ensuring that agents run in isolated subprocess with restricted environment.
#
# Architecture:
#   Main Process                    Sandbox Process
#   ├── API Layer           ──►     ├── ClaudeSDKClient
#   ├── SandboxOrchestrator ◄──     ├── Tool Executor
#   │   └── IPC (JSON-RPC)          └── Hook Handler
#   ├── DB Connection        X
#   └── Redis Connection     X      (No access to sensitive resources)
#
# Components:
#   - SandboxOrchestrator: Process pool management and request routing
#   - SandboxWorker: Individual subprocess wrapper
#   - ProcessSandboxConfig: Configuration for sandbox behavior
#   - IPC Protocol: JSON-RPC over stdin/stdout
#
# Usage:
#   from src.core.sandbox import SandboxOrchestrator, ProcessSandboxConfig
#
#   config = ProcessSandboxConfig()
#   orchestrator = SandboxOrchestrator(config)
#   result = await orchestrator.execute(user_id, message, attachments, session_id)
#
# =============================================================================

from src.core.sandbox.config import ProcessSandboxConfig
from src.core.sandbox.orchestrator import SandboxOrchestrator
from src.core.sandbox.worker import SandboxWorker
from src.core.sandbox.ipc import (
    IPCProtocol,
    IPCRequest,
    IPCResponse,
    IPCEvent,
    IPCEventType,
    IPCError,
    IPCTimeoutError,
    IPCConnectionError,
    IPCProtocolError,
    create_error_response,
    create_success_response,
    create_event_notification,
    map_ipc_to_sse_event,
)
from src.core.sandbox.adapter import (
    is_sandbox_enabled,
    get_sandbox_orchestrator,
    shutdown_sandbox_orchestrator,
    execute_in_sandbox,
    stream_in_sandbox,
    get_orchestrator_stats,
    SandboxExecutionContext,
    on_startup,
    on_shutdown,
)

__all__ = [
    # Core components
    "ProcessSandboxConfig",
    "SandboxOrchestrator",
    "SandboxWorker",
    # IPC Protocol
    "IPCProtocol",
    "IPCRequest",
    "IPCResponse",
    "IPCEvent",
    "IPCEventType",
    # IPC Errors
    "IPCError",
    "IPCTimeoutError",
    "IPCConnectionError",
    "IPCProtocolError",
    # IPC Utilities
    "create_error_response",
    "create_success_response",
    "create_event_notification",
    "map_ipc_to_sse_event",
    # Adapter (S78-2)
    "is_sandbox_enabled",
    "get_sandbox_orchestrator",
    "shutdown_sandbox_orchestrator",
    "execute_in_sandbox",
    "stream_in_sandbox",
    "get_orchestrator_stats",
    "SandboxExecutionContext",
    "on_startup",
    "on_shutdown",
]
