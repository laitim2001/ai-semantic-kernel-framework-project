# =============================================================================
# IPA Platform - Sandbox Worker
# =============================================================================
# Sprint 77: S77-2 - SandboxWorker Implementation (8 pts)
#
# The SandboxWorker manages an individual sandbox subprocess, handling
# process lifecycle, IPC communication, and environment isolation.
#
# Architecture:
#   SandboxWorker (main process)
#   │
#   ├── subprocess.Popen() ──► worker_main.py (sandbox process)
#   │       ↓                         ↓
#   │   stdin (JSON-RPC) ──────► Request Handler
#   │   stdout (JSON-RPC) ◄────── Response/Events
#   │
#   └── Environment Isolation:
#       - Filtered env vars (no DB, Redis, secrets)
#       - Restricted working directory
#       - Separate Python process
#
# IPC Protocol: JSON-RPC 2.0 over stdin/stdout
#
# =============================================================================

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional
import os

from src.core.sandbox.config import ProcessSandboxConfig


logger = logging.getLogger(__name__)


class IPCError(Exception):
    """Error in IPC communication with sandbox process."""
    pass


class WorkerStartupError(Exception):
    """Error starting the sandbox worker process."""
    pass


class SandboxWorker:
    """Manages a single sandbox subprocess.

    The SandboxWorker creates and manages a Python subprocess that runs
    in an isolated environment. Communication uses JSON-RPC over stdin/stdout.

    Example:
        worker = SandboxWorker(
            worker_id="worker-1",
            config=ProcessSandboxConfig(),
            user_id="user-123",
            sandbox_dir=Path("/data/sandbox/user-123")
        )

        await worker.start()

        result = await worker.execute(
            message="Analyze this file",
            attachments=[{"id": "file-1", "type": "text/plain"}],
            session_id="session-456"
        )

        await worker.stop()

    Attributes:
        worker_id: Unique identifier for this worker
        config: Sandbox configuration
        user_id: User ID this worker serves
        sandbox_dir: Working directory for the sandbox
        process: The subprocess.Popen object
        is_running: Whether the worker is currently running
    """

    def __init__(
        self,
        worker_id: str,
        config: ProcessSandboxConfig,
        user_id: str,
        sandbox_dir: Path
    ):
        """Initialize the sandbox worker.

        Args:
            worker_id: Unique identifier for this worker
            config: Sandbox configuration
            user_id: User ID this worker serves
            sandbox_dir: Working directory for the sandbox
        """
        self.worker_id = worker_id
        self.config = config
        self.user_id = user_id
        self.sandbox_dir = sandbox_dir

        self._process: Optional[subprocess.Popen] = None
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._request_counter = 0

    @property
    def is_running(self) -> bool:
        """Check if the worker process is running."""
        if self._process is None:
            return False
        return self._process.poll() is None

    async def start(self) -> None:
        """Start the sandbox worker subprocess.

        Creates a new Python subprocess with restricted environment
        running the worker_main.py entry point.

        Raises:
            WorkerStartupError: If the process fails to start
        """
        if self.is_running:
            logger.warning(f"Worker {self.worker_id} already running")
            return

        # Get filtered environment
        env = self.config.get_filtered_env(
            user_id=self.user_id,
            sandbox_dir=self.sandbox_dir
        )

        # Build the command to run worker_main.py
        worker_main_path = Path(__file__).parent / "worker_main.py"

        cmd = [
            sys.executable,
            "-u",  # Unbuffered output
            str(worker_main_path),
            "--worker-id", self.worker_id,
        ]

        try:
            # Start the subprocess
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=str(self.sandbox_dir),
                text=True,
                bufsize=1,  # Line buffered
            )

            # Wait for ready signal
            ready_response = await self._read_response(timeout=10)
            if ready_response.get("result", {}).get("status") != "ready":
                raise WorkerStartupError(
                    f"Worker did not signal ready: {ready_response}"
                )

            logger.info(f"Worker {self.worker_id} started (PID: {self._process.pid})")

        except Exception as e:
            logger.error(f"Failed to start worker {self.worker_id}: {e}")
            await self.stop()
            raise WorkerStartupError(f"Failed to start worker: {e}")

    async def stop(self) -> None:
        """Stop the sandbox worker subprocess.

        Sends a shutdown request and waits for graceful termination.
        Falls back to SIGKILL if the process doesn't exit.
        """
        if not self._process:
            return

        pid = self._process.pid
        logger.info(f"Stopping worker {self.worker_id} (PID: {pid})")

        try:
            # Try graceful shutdown first
            if self.is_running:
                try:
                    await self._send_request("shutdown", {})
                    # Wait for process to exit
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, self._process.wait
                        ),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Worker {self.worker_id} didn't exit gracefully")

            # Force kill if still running
            if self.is_running:
                self._process.kill()
                self._process.wait()

            # Close pipes
            if self._process.stdin:
                self._process.stdin.close()
            if self._process.stdout:
                self._process.stdout.close()
            if self._process.stderr:
                self._process.stderr.close()

        except Exception as e:
            logger.error(f"Error stopping worker {self.worker_id}: {e}")

        finally:
            self._process = None
            logger.info(f"Worker {self.worker_id} stopped")

    async def execute(
        self,
        message: str,
        attachments: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a request in the sandbox.

        Args:
            message: The message/prompt to execute
            attachments: List of file attachments
            session_id: Optional session identifier
            config: Optional execution configuration

        Returns:
            Execution result dictionary

        Raises:
            RuntimeError: If worker is not running
            IPCError: If communication fails
            Exception: If execution fails
        """
        if not self.is_running:
            raise RuntimeError(f"Worker {self.worker_id} is not running")

        params = {
            "message": message,
            "attachments": attachments,
            "session_id": session_id,
            "config": config or {},
        }

        response = await self._send_request("execute", params)

        if "error" in response:
            raise Exception(f"Execution error: {response['error']}")

        return response.get("result", {})

    async def execute_stream(
        self,
        message: str,
        attachments: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute a request with streaming events.

        Args:
            message: The message/prompt to execute
            attachments: List of file attachments
            session_id: Optional session identifier
            config: Optional execution configuration

        Yields:
            Event dictionaries as they occur

        Raises:
            RuntimeError: If worker is not running
            IPCError: If communication fails
        """
        if not self.is_running:
            raise RuntimeError(f"Worker {self.worker_id} is not running")

        params = {
            "message": message,
            "attachments": attachments,
            "session_id": session_id,
            "config": config or {},
            "stream": True,
        }

        # Send request
        request_id = await self._send_request_async("execute", params)

        # Read streaming events
        while True:
            response = await self._read_response()

            # Check for final result
            if "result" in response and response.get("id") == request_id:
                # Yield final result and break
                yield {
                    "type": "COMPLETE",
                    "data": response["result"],
                }
                break

            # Check for error
            if "error" in response:
                yield {
                    "type": "ERROR",
                    "data": response["error"],
                }
                break

            # Check for streaming event (notification without id)
            if response.get("method") == "event":
                yield response.get("params", {})

    async def _send_request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout: float = 300.0
    ) -> Dict[str, Any]:
        """Send a request and wait for response.

        Args:
            method: RPC method name
            params: Method parameters
            timeout: Response timeout in seconds

        Returns:
            Response dictionary

        Raises:
            IPCError: If communication fails
            asyncio.TimeoutError: If response times out
        """
        request_id = await self._send_request_async(method, params)
        return await asyncio.wait_for(
            self._read_response(expected_id=request_id),
            timeout=timeout
        )

    async def _send_request_async(
        self,
        method: str,
        params: Dict[str, Any]
    ) -> str:
        """Send a request without waiting for response.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Request ID

        Raises:
            IPCError: If write fails
        """
        if not self._process or not self._process.stdin:
            raise IPCError("Worker process not available")

        self._request_counter += 1
        request_id = f"req-{self._request_counter}"

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }

        async with self._write_lock:
            try:
                line = json.dumps(request) + "\n"
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._process.stdin.write(line)
                )
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._process.stdin.flush
                )

                logger.debug(f"Worker {self.worker_id} sent: {method}")

            except Exception as e:
                raise IPCError(f"Failed to write to worker: {e}")

        return request_id

    async def _read_response(
        self,
        expected_id: Optional[str] = None,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Read a response from the worker.

        Args:
            expected_id: If set, read until this request ID is found
            timeout: Read timeout in seconds

        Returns:
            Response dictionary

        Raises:
            IPCError: If read fails
            asyncio.TimeoutError: If read times out
        """
        if not self._process or not self._process.stdout:
            raise IPCError("Worker process not available")

        async with self._read_lock:
            try:
                line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        self._process.stdout.readline
                    ),
                    timeout=timeout
                )

                if not line:
                    # Check if process died
                    if not self.is_running:
                        stderr = ""
                        if self._process.stderr:
                            stderr = self._process.stderr.read()
                        raise IPCError(
                            f"Worker process exited unexpectedly. "
                            f"Stderr: {stderr}"
                        )
                    raise IPCError("Empty response from worker")

                response = json.loads(line.strip())
                logger.debug(f"Worker {self.worker_id} received response")

                return response

            except json.JSONDecodeError as e:
                raise IPCError(f"Invalid JSON from worker: {e}")
            except Exception as e:
                if isinstance(e, (IPCError, asyncio.TimeoutError)):
                    raise
                raise IPCError(f"Failed to read from worker: {e}")

    def _create_restricted_env(self) -> Dict[str, str]:
        """Create restricted environment for the subprocess.

        Returns:
            Dictionary of environment variables
        """
        return self.config.get_filtered_env(
            user_id=self.user_id,
            sandbox_dir=self.sandbox_dir
        )
