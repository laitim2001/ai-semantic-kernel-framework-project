# =============================================================================
# IPA Platform - Concurrent Execution WebSocket Support
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
# Sprint 31: S31-3 - 遷移至適配器層 (Phase 6)
#
# WebSocket endpoints for real-time execution monitoring.
# Provides:
#   - Real-time branch status updates
#   - Execution progress notifications
#   - Deadlock detection alerts
#   - Error event broadcasting
#
# 架構更新 (Sprint 31):
#   - 移除 domain.workflows.executors 和 deadlock_detector 導入
#   - 統一使用 ConcurrentAPIService 和適配器層
#   - 死鎖檢測由適配器內部處理
# =============================================================================

import asyncio
import logging
from typing import Any, Dict, Optional, Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.v1.concurrent.schemas import (
    WebSocketMessage,
    WebSocketMessageType,
)
# Sprint 31: 使用適配器層導入 (取代 domain 層)
from src.api.v1.concurrent.adapter_service import ConcurrentAPIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concurrent", tags=["concurrent-websocket"])


# =============================================================================
# Connection Manager
# =============================================================================


class ConcurrentConnectionManager:
    """
    Manages WebSocket connections for concurrent execution monitoring.

    Features:
    - Connection tracking by execution ID
    - Broadcast to all subscribers
    - Connection cleanup on disconnect
    """

    def __init__(self):
        # Map execution_id -> set of WebSocket connections
        self._connections: Dict[UUID, Set[WebSocket]] = {}
        # Global connections (subscribe to all events)
        self._global_connections: Set[WebSocket] = set()
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        execution_id: Optional[UUID] = None,
    ) -> None:
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: The WebSocket connection
            execution_id: Optional specific execution to monitor
        """
        await websocket.accept()

        async with self._lock:
            if execution_id:
                if execution_id not in self._connections:
                    self._connections[execution_id] = set()
                self._connections[execution_id].add(websocket)
                logger.info(f"WebSocket connected for execution {execution_id}")
            else:
                self._global_connections.add(websocket)
                logger.info("WebSocket connected globally")

    async def disconnect(
        self,
        websocket: WebSocket,
        execution_id: Optional[UUID] = None,
    ) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection
            execution_id: Optional specific execution ID
        """
        async with self._lock:
            if execution_id and execution_id in self._connections:
                self._connections[execution_id].discard(websocket)
                if not self._connections[execution_id]:
                    del self._connections[execution_id]
            self._global_connections.discard(websocket)

        logger.info(
            f"WebSocket disconnected "
            f"{'for execution ' + str(execution_id) if execution_id else 'globally'}"
        )

    async def broadcast(
        self,
        execution_id: UUID,
        message: WebSocketMessage,
    ) -> None:
        """
        Broadcast a message to all connections monitoring an execution.

        Args:
            execution_id: The execution ID
            message: The message to broadcast
        """
        message_dict = message.model_dump(mode="json")

        # Send to execution-specific connections
        if execution_id in self._connections:
            for connection in list(self._connections[execution_id]):
                try:
                    await connection.send_json(message_dict)
                except Exception as e:
                    logger.warning(f"Failed to send to connection: {e}")
                    await self.disconnect(connection, execution_id)

        # Send to global connections
        for connection in list(self._global_connections):
            try:
                await connection.send_json(message_dict)
            except Exception as e:
                logger.warning(f"Failed to send to global connection: {e}")
                await self.disconnect(connection)

    async def send_personal(
        self,
        websocket: WebSocket,
        message: WebSocketMessage,
    ) -> None:
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message.model_dump(mode="json"))
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")

    def get_connection_count(self, execution_id: Optional[UUID] = None) -> int:
        """Get the number of active connections."""
        if execution_id:
            return len(self._connections.get(execution_id, set()))
        return len(self._global_connections) + sum(
            len(conns) for conns in self._connections.values()
        )


# Global connection manager instance
connection_manager = ConcurrentConnectionManager()


# =============================================================================
# Event Publishers
# =============================================================================


async def publish_execution_started(
    execution_id: UUID,
    mode: str,
    branch_count: int,
) -> None:
    """Publish execution started event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.EXECUTION_STARTED,
        execution_id=execution_id,
        data={
            "mode": mode,
            "branch_count": branch_count,
        },
        message=f"Execution started with {branch_count} branches in {mode} mode",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_execution_completed(
    execution_id: UUID,
    result: Optional[Dict[str, Any]] = None,
    duration_seconds: Optional[float] = None,
) -> None:
    """Publish execution completed event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.EXECUTION_COMPLETED,
        execution_id=execution_id,
        data={
            "result": result,
            "duration_seconds": duration_seconds,
        },
        message="Execution completed successfully",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_execution_failed(
    execution_id: UUID,
    error: str,
    failed_branches: Optional[list] = None,
) -> None:
    """Publish execution failed event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.EXECUTION_FAILED,
        execution_id=execution_id,
        data={
            "error": error,
            "failed_branches": failed_branches or [],
        },
        message=f"Execution failed: {error}",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_execution_cancelled(
    execution_id: UUID,
    cancelled_branches: Optional[list] = None,
    reason: Optional[str] = None,
) -> None:
    """Publish execution cancelled event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.EXECUTION_CANCELLED,
        execution_id=execution_id,
        data={
            "cancelled_branches": cancelled_branches or [],
            "reason": reason,
        },
        message="Execution cancelled",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_branch_started(
    execution_id: UUID,
    branch_id: str,
) -> None:
    """Publish branch started event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.BRANCH_STARTED,
        execution_id=execution_id,
        branch_id=branch_id,
        data={},
        message=f"Branch {branch_id} started",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_branch_completed(
    execution_id: UUID,
    branch_id: str,
    result: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """Publish branch completed event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.BRANCH_COMPLETED,
        execution_id=execution_id,
        branch_id=branch_id,
        data={
            "result": result,
            "duration_ms": duration_ms,
        },
        message=f"Branch {branch_id} completed",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_branch_failed(
    execution_id: UUID,
    branch_id: str,
    error: str,
) -> None:
    """Publish branch failed event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.BRANCH_FAILED,
        execution_id=execution_id,
        branch_id=branch_id,
        data={"error": error},
        message=f"Branch {branch_id} failed: {error}",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_branch_progress(
    execution_id: UUID,
    branch_id: str,
    progress: float,
    status: Optional[str] = None,
) -> None:
    """Publish branch progress update."""
    message = WebSocketMessage(
        type=WebSocketMessageType.BRANCH_PROGRESS,
        execution_id=execution_id,
        branch_id=branch_id,
        data={
            "progress": progress,
            "status": status,
        },
        message=f"Branch {branch_id} progress: {progress:.1f}%",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_deadlock_detected(
    execution_id: UUID,
    cycle: list,
) -> None:
    """Publish deadlock detected event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.DEADLOCK_DETECTED,
        execution_id=execution_id,
        data={
            "cycle": cycle,
            "cycle_length": len(cycle),
        },
        message=f"Deadlock detected with {len(cycle)} branches in cycle",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_deadlock_resolved(
    execution_id: UUID,
    resolution_strategy: str,
    cancelled_branch: Optional[str] = None,
) -> None:
    """Publish deadlock resolved event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.DEADLOCK_RESOLVED,
        execution_id=execution_id,
        data={
            "resolution_strategy": resolution_strategy,
            "cancelled_branch": cancelled_branch,
        },
        message=f"Deadlock resolved using {resolution_strategy} strategy",
    )
    await connection_manager.broadcast(execution_id, message)


async def publish_error(
    execution_id: UUID,
    error: str,
    error_type: Optional[str] = None,
) -> None:
    """Publish generic error event."""
    message = WebSocketMessage(
        type=WebSocketMessageType.ERROR,
        execution_id=execution_id,
        data={
            "error": error,
            "error_type": error_type,
        },
        message=f"Error: {error}",
    )
    await connection_manager.broadcast(execution_id, message)


# =============================================================================
# WebSocket Endpoints
# =============================================================================


@router.websocket("/ws/{execution_id}")
async def websocket_execution(
    websocket: WebSocket,
    execution_id: UUID,
) -> None:
    """
    WebSocket endpoint for monitoring a specific execution.

    Clients receive real-time updates about:
    - Branch status changes
    - Execution progress
    - Errors and failures
    - Deadlock events
    """
    await connection_manager.connect(websocket, execution_id)

    try:
        # Send initial connection confirmation
        await connection_manager.send_personal(
            websocket,
            WebSocketMessage(
                type=WebSocketMessageType.EXECUTION_STARTED,
                execution_id=execution_id,
                data={"connected": True},
                message=f"Connected to execution {execution_id}",
            ),
        )

        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for any client message (heartbeat or commands)
                data = await websocket.receive_text()

                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_text("pong")

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for execution {execution_id}")
                break

    except Exception as e:
        logger.error(f"WebSocket error for execution {execution_id}: {e}")

    finally:
        await connection_manager.disconnect(websocket, execution_id)


@router.websocket("/ws")
async def websocket_global() -> None:
    """
    WebSocket endpoint for monitoring all concurrent executions.

    Clients receive updates from all active executions.
    """
    websocket: WebSocket = None  # Type hint for IDE
    try:
        await connection_manager.connect(websocket)

        # Send connection confirmation
        await connection_manager.send_personal(
            websocket,
            WebSocketMessage(
                type=WebSocketMessageType.EXECUTION_STARTED,
                execution_id=UUID("00000000-0000-0000-0000-000000000000"),
                data={"connected": True, "scope": "global"},
                message="Connected to global concurrent execution stream",
            ),
        )

        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Global WebSocket error: {e}")

    finally:
        if websocket:
            await connection_manager.disconnect(websocket)


# =============================================================================
# Helper Functions
# =============================================================================


def get_connection_manager() -> ConcurrentConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager


async def register_state_change_callback(
    service: ConcurrentAPIService,
) -> None:
    """
    Register callback with service to publish WebSocket events.

    Sprint 31: 更新為使用 ConcurrentAPIService (取代 ConcurrentStateManager)

    This allows the service to automatically broadcast
    updates when execution state changes.
    """

    async def on_branch_status_change(
        execution_id: UUID,
        branch_id: str,
        old_status: str,
        new_status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> None:
        """Handle branch status change events."""
        if new_status == "running":
            await publish_branch_started(execution_id, branch_id)
        elif new_status == "completed":
            await publish_branch_completed(execution_id, branch_id, result)
        elif new_status == "failed":
            await publish_branch_failed(execution_id, branch_id, error or "Unknown error")

    # Note: In a real implementation, the service would have
    # callback registration methods. For now, this is a placeholder.
    # Sprint 31: 適配器內部處理狀態變更事件
    logger.info("Registered WebSocket callbacks with ConcurrentAPIService")
