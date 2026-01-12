#!/usr/bin/env python3
# =============================================================================
# IPA Platform - Sandbox Worker Main Entry Point
# =============================================================================
# Sprint 77: S77-2 - SandboxWorker Implementation (8 pts)
#
# This script is the entry point for sandbox subprocess. It runs in an
# isolated environment with restricted access to sensitive resources.
#
# Environment:
#   - No database connection strings
#   - No Redis passwords
#   - No secret keys
#   - Only ANTHROPIC_API_KEY and sandbox-specific variables
#
# IPC Protocol: JSON-RPC 2.0 over stdin/stdout
#   - Request: {"jsonrpc": "2.0", "method": "execute", "params": {...}, "id": "..."}
#   - Response: {"jsonrpc": "2.0", "result": {...}, "id": "..."}
#   - Event: {"jsonrpc": "2.0", "method": "event", "params": {...}}
#
# Usage:
#   python worker_main.py --worker-id worker-1
#
# =============================================================================

import argparse
import asyncio
import json
import logging
import os
import sys
import traceback
from typing import Any, Dict, Optional


# Configure logging to stderr (stdout is for IPC)
logging.basicConfig(
    level=logging.DEBUG if os.getenv("SANDBOX_DEBUG") else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("sandbox_worker")


class SandboxExecutor:
    """Executor for handling requests in the sandbox.

    This class handles incoming requests and delegates to the
    appropriate handler (Claude SDK, tools, etc.).

    Note: In Phase 21 Sprint 77, this is a basic implementation.
    Sprint 78 will integrate with the full Claude SDK client.
    """

    def __init__(self, worker_id: str):
        """Initialize the executor.

        Args:
            worker_id: Unique identifier for this worker
        """
        self.worker_id = worker_id
        self.user_id = os.getenv("SANDBOX_USER_ID", "unknown")
        self.sandbox_dir = os.getenv("SANDBOX_DIR", os.getcwd())
        self._claude_client = None

        logger.info(
            f"SandboxExecutor initialized: worker={worker_id}, "
            f"user={self.user_id}, sandbox={self.sandbox_dir}"
        )

    async def initialize(self) -> None:
        """Initialize the Claude SDK client.

        This sets up the Claude SDK with the API key from environment.
        The SDK is initialized lazily on first request if not done here.
        """
        try:
            # Check for API key
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not set in sandbox environment")
                return

            # TODO: Sprint 78 will integrate with actual Claude SDK
            # For now, we just validate the environment is set up correctly
            logger.info("Claude SDK environment ready (full integration in Sprint 78)")

        except Exception as e:
            logger.error(f"Failed to initialize Claude SDK: {e}")
            raise

    async def execute(
        self,
        message: str,
        attachments: list,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Execute a request.

        Args:
            message: The message/prompt to execute
            attachments: List of file attachments
            session_id: Optional session identifier
            config: Optional execution configuration
            stream: Whether to stream the response

        Returns:
            Execution result dictionary
        """
        logger.debug(f"Executing: message={message[:50]}..., stream={stream}")

        try:
            # TODO: Sprint 78 - Full Claude SDK integration
            # For now, return a placeholder response that demonstrates
            # the sandbox isolation is working

            # Verify isolation - these should NOT be in environment
            blocked_vars = ["DB_PASSWORD", "REDIS_PASSWORD", "SECRET_KEY"]
            isolation_check = {
                var: os.getenv(var) is None
                for var in blocked_vars
            }

            result = {
                "content": f"[Sandbox Worker {self.worker_id}] Received message in isolated environment.\n\n"
                           f"Environment isolation verified:\n"
                           + "\n".join(
                               f"  - {var}: {'✅ Blocked' if blocked else '❌ LEAK!'}"
                               for var, blocked in isolation_check.items()
                           )
                           + f"\n\nUser: {self.user_id}\n"
                           f"Sandbox Dir: {self.sandbox_dir}\n\n"
                           f"Full Claude SDK integration coming in Sprint 78.",
                "tool_calls": [],
                "tokens_used": {
                    "input": len(message.split()),
                    "output": 100,
                },
                "session_id": session_id,
            }

            return result

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            raise


class IPCHandler:
    """Handles JSON-RPC communication over stdin/stdout.

    Reads requests from stdin and writes responses to stdout.
    Uses JSON-RPC 2.0 format for all messages.
    """

    def __init__(self, executor: SandboxExecutor):
        """Initialize the IPC handler.

        Args:
            executor: The SandboxExecutor to handle requests
        """
        self.executor = executor
        self._running = True

    def send_response(
        self,
        result: Any = None,
        error: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> None:
        """Send a JSON-RPC response.

        Args:
            result: The result data (for success)
            error: The error data (for failure)
            request_id: The request ID to respond to
        """
        response = {"jsonrpc": "2.0"}

        if error:
            response["error"] = error
        else:
            response["result"] = result

        if request_id:
            response["id"] = request_id

        line = json.dumps(response) + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()

    def send_event(self, event_type: str, data: Any) -> None:
        """Send a streaming event (notification).

        Args:
            event_type: Type of the event
            data: Event data
        """
        notification = {
            "jsonrpc": "2.0",
            "method": "event",
            "params": {
                "type": event_type,
                "data": data,
            },
        }
        line = json.dumps(notification) + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()

    async def handle_request(self, request: Dict[str, Any]) -> None:
        """Handle a single JSON-RPC request.

        Args:
            request: The parsed request dictionary
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.debug(f"Handling request: method={method}, id={request_id}")

        try:
            if method == "execute":
                result = await self.executor.execute(
                    message=params.get("message", ""),
                    attachments=params.get("attachments", []),
                    session_id=params.get("session_id"),
                    config=params.get("config", {}),
                    stream=params.get("stream", False),
                )
                self.send_response(result=result, request_id=request_id)

            elif method == "shutdown":
                logger.info("Received shutdown request")
                self.send_response(result={"status": "shutting_down"}, request_id=request_id)
                self._running = False

            elif method == "ping":
                self.send_response(result={"status": "pong"}, request_id=request_id)

            else:
                self.send_response(
                    error={
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                    request_id=request_id,
                )

        except Exception as e:
            logger.error(f"Request handling failed: {e}", exc_info=True)
            self.send_response(
                error={
                    "code": -32000,
                    "message": str(e),
                    "data": {"traceback": traceback.format_exc()},
                },
                request_id=request_id,
            )

    async def run(self) -> None:
        """Main loop: read requests from stdin and process them.

        This method runs until a shutdown request is received or
        stdin is closed.
        """
        # Signal that we're ready
        self.send_response(result={"status": "ready"})

        loop = asyncio.get_event_loop()

        while self._running:
            try:
                # Read a line from stdin (blocking in executor)
                line = await loop.run_in_executor(None, sys.stdin.readline)

                if not line:
                    # stdin closed
                    logger.info("stdin closed, exiting")
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    self.send_response(
                        error={
                            "code": -32700,
                            "message": f"Parse error: {e}",
                        }
                    )
                    continue

                # Handle the request
                await self.handle_request(request)

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                self.send_response(
                    error={
                        "code": -32000,
                        "message": f"Internal error: {e}",
                    }
                )

        logger.info("IPC handler stopped")


async def main(worker_id: str) -> None:
    """Main entry point for the sandbox worker.

    Args:
        worker_id: Unique identifier for this worker
    """
    logger.info(f"Sandbox worker starting: {worker_id}")

    # Verify we're in a restricted environment
    logger.info("Environment check:")
    logger.info(f"  SANDBOX_USER_ID: {os.getenv('SANDBOX_USER_ID', 'NOT SET')}")
    logger.info(f"  SANDBOX_DIR: {os.getenv('SANDBOX_DIR', 'NOT SET')}")
    logger.info(f"  ANTHROPIC_API_KEY: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")
    logger.info(f"  DB_PASSWORD: {'LEAKED!' if os.getenv('DB_PASSWORD') else 'Blocked (OK)'}")

    # Initialize executor
    executor = SandboxExecutor(worker_id)
    await executor.initialize()

    # Start IPC handler
    handler = IPCHandler(executor)
    await handler.run()

    logger.info("Sandbox worker exiting")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sandbox Worker Process")
    parser.add_argument(
        "--worker-id",
        required=True,
        help="Unique identifier for this worker",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.worker_id))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
