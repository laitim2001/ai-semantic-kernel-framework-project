# =============================================================================
# IPA Platform - Sandbox Adapter for Existing Code
# =============================================================================
# Sprint 78: S78-2 - Existing Code Adaptation (5 pts)
#
# This module provides an adapter layer to integrate SandboxOrchestrator
# with existing API endpoints and services without major code changes.
#
# Usage:
#   from src.core.sandbox.adapter import execute_in_sandbox, get_sandbox_orchestrator
#
#   # Option 1: Direct execution
#   result = await execute_in_sandbox(user_id, message, attachments)
#
#   # Option 2: Streaming execution
#   async for event in stream_in_sandbox(user_id, message, attachments):
#       yield event
#
# Environment Variables:
#   SANDBOX_ENABLED=true      # Enable sandbox isolation (default: true)
#   SANDBOX_ENABLED=false     # Disable sandbox (development mode)
#
# =============================================================================

import asyncio
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.core.sandbox.config import ProcessSandboxConfig
from src.core.sandbox.orchestrator import SandboxOrchestrator
from src.core.sandbox.ipc import IPCEvent, map_ipc_to_sse_event


logger = logging.getLogger(__name__)


# Global orchestrator instance
_orchestrator: Optional[SandboxOrchestrator] = None
_orchestrator_lock = asyncio.Lock()


def is_sandbox_enabled() -> bool:
    """Check if sandbox mode is enabled.

    Sandbox can be disabled for development/debugging by setting
    SANDBOX_ENABLED=false in environment variables.

    Returns:
        True if sandbox is enabled (default), False otherwise
    """
    value = os.getenv("SANDBOX_ENABLED", "true").lower()
    return value in ("true", "1", "yes", "on")


async def get_sandbox_orchestrator() -> SandboxOrchestrator:
    """Get or create the global sandbox orchestrator.

    Thread-safe singleton pattern using asyncio lock.

    Returns:
        SandboxOrchestrator instance

    Raises:
        RuntimeError: If sandbox is disabled
    """
    global _orchestrator

    if not is_sandbox_enabled():
        raise RuntimeError(
            "Sandbox is disabled. Set SANDBOX_ENABLED=true to enable."
        )

    async with _orchestrator_lock:
        if _orchestrator is None:
            config = ProcessSandboxConfig()
            errors = config.validate()
            if errors:
                raise RuntimeError(f"Invalid sandbox config: {errors}")

            _orchestrator = SandboxOrchestrator(config)
            await _orchestrator.start()

            logger.info("Sandbox orchestrator initialized and started")

        return _orchestrator


async def shutdown_sandbox_orchestrator() -> None:
    """Shutdown the global sandbox orchestrator.

    Call this during application shutdown to cleanup resources.
    """
    global _orchestrator

    async with _orchestrator_lock:
        if _orchestrator is not None:
            await _orchestrator.shutdown()
            _orchestrator = None
            logger.info("Sandbox orchestrator shutdown complete")


async def execute_in_sandbox(
    user_id: str,
    message: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a request in the sandbox.

    This is the primary entry point for non-streaming execution.

    Args:
        user_id: User identifier for sandbox isolation
        message: The message/prompt to execute
        attachments: Optional list of file attachments
        session_id: Optional session identifier
        config: Optional execution configuration

    Returns:
        Execution result dictionary containing:
            - content: Response content
            - tool_calls: List of tool calls made
            - tokens_used: Token usage statistics
            - duration: Execution duration in seconds

    Raises:
        RuntimeError: If sandbox is disabled or not available
        TimeoutError: If execution exceeds timeout
        Exception: If execution fails
    """
    if not is_sandbox_enabled():
        # Fallback mode: Return a placeholder when sandbox is disabled
        logger.warning("Sandbox disabled, returning placeholder response")
        return {
            "content": "[Sandbox Disabled] Request would be executed here.",
            "tool_calls": [],
            "tokens_used": {"input": 0, "output": 0},
            "duration": 0,
            "sandbox_disabled": True,
        }

    orchestrator = await get_sandbox_orchestrator()
    return await orchestrator.execute(
        user_id=user_id,
        message=message,
        attachments=attachments or [],
        session_id=session_id,
        config=config,
    )


async def stream_in_sandbox(
    user_id: str,
    message: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute a request in the sandbox with streaming.

    This is the primary entry point for streaming execution.

    Args:
        user_id: User identifier for sandbox isolation
        message: The message/prompt to execute
        attachments: Optional list of file attachments
        session_id: Optional session identifier
        config: Optional execution configuration

    Yields:
        Event dictionaries in SSE format:
            - event: Event type (e.g., "text_delta", "complete")
            - data: Event data

    Raises:
        RuntimeError: If sandbox is disabled or not available
        TimeoutError: If execution exceeds timeout
        Exception: If execution fails
    """
    if not is_sandbox_enabled():
        # Fallback mode: Yield a placeholder when sandbox is disabled
        logger.warning("Sandbox disabled, returning placeholder events")
        yield {
            "event": "text_delta",
            "data": {"delta": "[Sandbox Disabled] "},
        }
        yield {
            "event": "text_delta",
            "data": {"delta": "Request would be executed here."},
        }
        yield {
            "event": "complete",
            "data": {"sandbox_disabled": True},
        }
        return

    orchestrator = await get_sandbox_orchestrator()
    async for event in orchestrator.execute_stream(
        user_id=user_id,
        message=message,
        attachments=attachments or [],
        session_id=session_id,
        config=config,
    ):
        # Convert IPC events to SSE format if needed
        if isinstance(event, dict) and "type" in event:
            ipc_event = IPCEvent(
                type=event["type"],
                data=event.get("data", {}),
            )
            yield map_ipc_to_sse_event(ipc_event)
        else:
            yield event


def get_orchestrator_stats() -> Optional[Dict[str, Any]]:
    """Get statistics about the sandbox orchestrator.

    Returns:
        Statistics dictionary, or None if orchestrator is not running
    """
    if _orchestrator is None or not _orchestrator.is_running:
        return None

    return _orchestrator.get_pool_stats()


# =============================================================================
# Integration Helpers
# =============================================================================


class SandboxExecutionContext:
    """Context manager for sandbox execution.

    Provides a convenient way to execute code in sandbox with proper
    error handling and cleanup.

    Example:
        async with SandboxExecutionContext(user_id="user-123") as ctx:
            result = await ctx.execute("Analyze this code")
            async for event in ctx.stream("Generate report"):
                print(event)
    """

    def __init__(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the context.

        Args:
            user_id: User identifier for sandbox isolation
            session_id: Optional session identifier
            config: Optional execution configuration
        """
        self.user_id = user_id
        self.session_id = session_id
        self.config = config

    async def __aenter__(self) -> "SandboxExecutionContext":
        """Enter the context."""
        # Ensure orchestrator is available
        if is_sandbox_enabled():
            await get_sandbox_orchestrator()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context."""
        # No cleanup needed for individual contexts
        pass

    async def execute(
        self,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Execute a request.

        Args:
            message: The message/prompt to execute
            attachments: Optional list of file attachments

        Returns:
            Execution result dictionary
        """
        return await execute_in_sandbox(
            user_id=self.user_id,
            message=message,
            attachments=attachments,
            session_id=self.session_id,
            config=self.config,
        )

    async def stream(
        self,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a request with streaming.

        Args:
            message: The message/prompt to execute
            attachments: Optional list of file attachments

        Yields:
            Event dictionaries in SSE format
        """
        async for event in stream_in_sandbox(
            user_id=self.user_id,
            message=message,
            attachments=attachments,
            session_id=self.session_id,
            config=self.config,
        ):
            yield event


# =============================================================================
# Application Lifecycle Integration
# =============================================================================


async def on_startup() -> None:
    """Initialize sandbox on application startup.

    Call this in FastAPI's startup event handler.
    """
    if is_sandbox_enabled():
        await get_sandbox_orchestrator()
        logger.info("Sandbox adapter initialized on startup")
    else:
        logger.info("Sandbox disabled, skipping initialization")


async def on_shutdown() -> None:
    """Cleanup sandbox on application shutdown.

    Call this in FastAPI's shutdown event handler.
    """
    await shutdown_sandbox_orchestrator()
    logger.info("Sandbox adapter cleanup complete")
