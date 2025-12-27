"""
Session WebSocket Handler (S46-2)

WebSocket endpoint for real-time Session chat.
Provides streaming Agent responses and interactive tool approval.

Features:
- WebSocket connection management
- Real-time message streaming
- Tool approval handling
- Heartbeat keepalive
- Connection reconnect support
"""

from typing import Dict, Optional, Set, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.websockets import WebSocketState
import asyncio
import logging
import json
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.domain.sessions.bridge import (
    SessionAgentBridge,
    BridgeConfig,
    SessionNotFoundError as BridgeSessionNotFoundError,
    SessionNotActiveError as BridgeSessionNotActiveError,
    create_session_agent_bridge,
)
from src.domain.sessions.events import ExecutionEvent, ExecutionEventType
from src.domain.sessions.service import SessionService
from src.domain.sessions.repository import SQLAlchemySessionRepository
from src.domain.sessions.cache import SessionCache
from src.domain.sessions.approval import ToolApprovalManager, create_approval_manager
from src.infrastructure.database.session import get_session


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions-websocket"])


# =============================================================================
# WebSocket Message Types
# =============================================================================

class WebSocketMessageType:
    """WebSocket 訊息類型"""

    # Client -> Server
    MESSAGE = "message"           # 用戶訊息
    APPROVAL = "approval"         # 工具審批
    HEARTBEAT = "heartbeat"       # 心跳請求
    CANCEL = "cancel"             # 取消操作

    # Server -> Client
    CONNECTED = "connected"       # 連接確認
    HEARTBEAT_ACK = "heartbeat_ack"  # 心跳回應
    ERROR = "error"               # 錯誤訊息
    EVENT = "event"               # 執行事件


# =============================================================================
# Connection Manager
# =============================================================================

class SessionWebSocketManager:
    """Session WebSocket 連接管理器

    管理所有活躍的 WebSocket 連接，支援:
    - 連接生命週期管理
    - 訊息廣播
    - 心跳保活
    """

    def __init__(self):
        """初始化連接管理器"""
        self._connections: Dict[str, WebSocket] = {}
        self._session_connections: Dict[str, Set[str]] = {}  # session_id -> connection_ids
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        connection_id: str,
    ) -> None:
        """建立 WebSocket 連接

        Args:
            websocket: WebSocket 連接
            session_id: Session ID
            connection_id: 連接唯一 ID
        """
        await websocket.accept()

        async with self._lock:
            self._connections[connection_id] = websocket

            if session_id not in self._session_connections:
                self._session_connections[session_id] = set()
            self._session_connections[session_id].add(connection_id)

        # 發送連接確認
        await self.send_message(
            connection_id,
            {
                "type": WebSocketMessageType.CONNECTED,
                "session_id": session_id,
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        logger.info(f"WebSocket connected: session={session_id}, conn={connection_id}")

    async def disconnect(self, connection_id: str, session_id: str) -> None:
        """斷開連接

        Args:
            connection_id: 連接 ID
            session_id: Session ID
        """
        async with self._lock:
            # 取消心跳任務
            if connection_id in self._heartbeat_tasks:
                self._heartbeat_tasks[connection_id].cancel()
                del self._heartbeat_tasks[connection_id]

            # 移除連接
            if connection_id in self._connections:
                del self._connections[connection_id]

            # 從 Session 連接集合移除
            if session_id in self._session_connections:
                self._session_connections[session_id].discard(connection_id)
                if not self._session_connections[session_id]:
                    del self._session_connections[session_id]

        logger.info(f"WebSocket disconnected: session={session_id}, conn={connection_id}")

    async def send_message(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """發送訊息到指定連接

        Args:
            connection_id: 連接 ID
            message: 訊息內容

        Returns:
            是否發送成功
        """
        websocket = self._connections.get(connection_id)
        if not websocket:
            return False

        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
                return True
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")

        return False

    async def send_event(
        self,
        connection_id: str,
        event: ExecutionEvent,
    ) -> bool:
        """發送執行事件到指定連接

        Args:
            connection_id: 連接 ID
            event: 執行事件

        Returns:
            是否發送成功
        """
        message = {
            "type": WebSocketMessageType.EVENT,
            "payload": event.to_dict(),
        }
        return await self.send_message(connection_id, message)

    async def broadcast_to_session(
        self,
        session_id: str,
        message: Dict[str, Any],
    ) -> int:
        """廣播訊息到 Session 的所有連接

        Args:
            session_id: Session ID
            message: 訊息內容

        Returns:
            成功發送的連接數
        """
        connection_ids = self._session_connections.get(session_id, set()).copy()
        success_count = 0

        for conn_id in connection_ids:
            if await self.send_message(conn_id, message):
                success_count += 1

        return success_count

    async def start_heartbeat(
        self,
        connection_id: str,
        interval: int = 30,
    ) -> None:
        """啟動心跳任務

        Args:
            connection_id: 連接 ID
            interval: 心跳間隔（秒）
        """
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(interval)
                try:
                    await self.send_message(
                        connection_id,
                        {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()}
                    )
                except Exception:
                    break

        task = asyncio.create_task(heartbeat_loop())
        self._heartbeat_tasks[connection_id] = task

    def get_connection_count(self, session_id: Optional[str] = None) -> int:
        """獲取連接數

        Args:
            session_id: 如果指定則只計算該 Session 的連接數

        Returns:
            連接數
        """
        if session_id:
            return len(self._session_connections.get(session_id, set()))
        return len(self._connections)

    def is_connected(self, connection_id: str) -> bool:
        """檢查連接是否存在

        Args:
            connection_id: 連接 ID

        Returns:
            是否存在
        """
        return connection_id in self._connections


# 全局連接管理器
websocket_manager = SessionWebSocketManager()


# =============================================================================
# Message Handler
# =============================================================================

class WebSocketMessageHandler:
    """WebSocket 訊息處理器

    處理來自客戶端的各類訊息:
    - message: 用戶聊天訊息
    - approval: 工具審批決定
    - heartbeat: 心跳保活
    - cancel: 取消操作
    """

    def __init__(
        self,
        bridge: SessionAgentBridge,
        manager: SessionWebSocketManager,
    ):
        """初始化處理器

        Args:
            bridge: SessionAgentBridge 實例
            manager: WebSocket 連接管理器
        """
        self._bridge = bridge
        self._manager = manager

    async def handle_message(
        self,
        websocket: WebSocket,
        connection_id: str,
        session_id: str,
        data: Dict[str, Any],
    ) -> None:
        """處理 WebSocket 訊息

        Args:
            websocket: WebSocket 連接
            connection_id: 連接 ID
            session_id: Session ID
            data: 訊息數據
        """
        msg_type = data.get("type", "")

        try:
            if msg_type == WebSocketMessageType.MESSAGE:
                await self._handle_user_message(connection_id, session_id, data)

            elif msg_type == WebSocketMessageType.APPROVAL:
                await self._handle_approval(connection_id, session_id, data)

            elif msg_type == WebSocketMessageType.HEARTBEAT:
                await self._manager.send_message(
                    connection_id,
                    {
                        "type": WebSocketMessageType.HEARTBEAT_ACK,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

            elif msg_type == WebSocketMessageType.CANCEL:
                await self._handle_cancel(connection_id, session_id, data)

            else:
                await self._send_error(
                    connection_id,
                    "UNKNOWN_MESSAGE_TYPE",
                    f"Unknown message type: {msg_type}",
                )

        except BridgeSessionNotFoundError:
            await self._send_error(
                connection_id,
                "SESSION_NOT_FOUND",
                f"Session not found: {session_id}",
            )

        except BridgeSessionNotActiveError:
            await self._send_error(
                connection_id,
                "SESSION_NOT_ACTIVE",
                f"Session is not active: {session_id}",
            )

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await self._send_error(
                connection_id,
                "INTERNAL_ERROR",
                str(e),
            )

    async def _handle_user_message(
        self,
        connection_id: str,
        session_id: str,
        data: Dict[str, Any],
    ) -> None:
        """處理用戶訊息

        Args:
            connection_id: 連接 ID
            session_id: Session ID
            data: 訊息數據
        """
        content = data.get("content", "")
        attachments = data.get("attachments")

        if not content and not attachments:
            await self._send_error(
                connection_id,
                "EMPTY_MESSAGE",
                "Message content is empty",
            )
            return

        # 處理訊息並串流回應
        async for event in self._bridge.process_message(
            session_id=session_id,
            content=content,
            attachments=attachments,
            stream=True,
        ):
            await self._manager.send_event(connection_id, event)

    async def _handle_approval(
        self,
        connection_id: str,
        session_id: str,
        data: Dict[str, Any],
    ) -> None:
        """處理工具審批

        Args:
            connection_id: 連接 ID
            session_id: Session ID
            data: 審批數據
        """
        approval_id = data.get("approval_id")
        approved = data.get("approved", False)
        feedback = data.get("feedback")
        approver_id = data.get("approver_id")

        if not approval_id:
            await self._send_error(
                connection_id,
                "MISSING_APPROVAL_ID",
                "approval_id is required",
            )
            return

        # 處理審批並串流結果
        async for event in self._bridge.handle_tool_approval(
            session_id=session_id,
            approval_id=approval_id,
            approved=approved,
            feedback=feedback,
            approver_id=approver_id,
        ):
            await self._manager.send_event(connection_id, event)

    async def _handle_cancel(
        self,
        connection_id: str,
        session_id: str,
        data: Dict[str, Any],
    ) -> None:
        """處理取消操作

        Args:
            connection_id: 連接 ID
            session_id: Session ID
            data: 取消數據
        """
        reason = data.get("reason", "user_cancelled")

        # 取消所有待審批請求
        cancelled_count = await self._bridge.cancel_pending_approvals(
            session_id=session_id,
            reason=reason,
        )

        await self._manager.send_message(
            connection_id,
            {
                "type": "cancelled",
                "session_id": session_id,
                "cancelled_approvals": cancelled_count,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def _send_error(
        self,
        connection_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        """發送錯誤訊息

        Args:
            connection_id: 連接 ID
            error_code: 錯誤碼
            error_message: 錯誤訊息
        """
        await self._manager.send_message(
            connection_id,
            {
                "type": WebSocketMessageType.ERROR,
                "error_code": error_code,
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


# =============================================================================
# Dependencies
# =============================================================================

# Redis client singleton
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """獲取 Redis 客戶端"""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password if settings.redis_password else None,
            decode_responses=True,
        )
    return _redis_client


async def get_session_bridge(
    db: AsyncSession = Depends(get_session),
) -> SessionAgentBridge:
    """獲取 SessionAgentBridge 實例

    Args:
        db: 數據庫 Session

    Returns:
        SessionAgentBridge 實例
    """
    redis_client = await get_redis()

    # 創建依賴組件
    repository = SQLAlchemySessionRepository(db)
    cache = SessionCache(redis_client)
    session_service = SessionService(repository=repository, cache=cache)

    # 創建審批管理器
    approval_manager = create_approval_manager(redis_client)

    # 創建 Bridge
    bridge = create_session_agent_bridge(
        session_service=session_service,
        approval_manager=approval_manager,
    )

    return bridge


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@router.websocket("/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_session),
) -> None:
    """Session WebSocket 端點

    建立 WebSocket 連接，支援:
    - 實時對話
    - 工具審批
    - 心跳保活

    訊息格式:

    Client -> Server:
    - {"type": "message", "content": "...", "attachments": [...]}
    - {"type": "approval", "approval_id": "...", "approved": true/false, "feedback": "..."}
    - {"type": "heartbeat"}
    - {"type": "cancel", "reason": "..."}

    Server -> Client:
    - {"type": "connected", "session_id": "...", "connection_id": "..."}
    - {"type": "event", "payload": {...}}  // ExecutionEvent
    - {"type": "heartbeat_ack"}
    - {"type": "error", "error_code": "...", "message": "..."}

    Args:
        websocket: WebSocket 連接
        session_id: Session ID
        db: 數據庫 Session
    """
    # 生成連接 ID
    import uuid
    connection_id = str(uuid.uuid4())

    # 獲取 Bridge
    bridge = await get_session_bridge(db)

    # 創建訊息處理器
    handler = WebSocketMessageHandler(bridge, websocket_manager)

    try:
        # 建立連接
        await websocket_manager.connect(websocket, session_id, connection_id)

        # 啟動心跳
        await websocket_manager.start_heartbeat(connection_id, interval=30)

        # 主循環：接收並處理訊息
        while True:
            try:
                data = await websocket.receive_json()
                await handler.handle_message(
                    websocket,
                    connection_id,
                    session_id,
                    data,
                )

            except json.JSONDecodeError:
                await websocket_manager.send_message(
                    connection_id,
                    {
                        "type": WebSocketMessageType.ERROR,
                        "error_code": "INVALID_JSON",
                        "message": "Invalid JSON format",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: session={session_id}, conn={connection_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        await websocket_manager.disconnect(connection_id, session_id)


# =============================================================================
# HTTP Endpoints for WebSocket Status
# =============================================================================

@router.get("/{session_id}/ws/status")
async def get_websocket_status(session_id: str) -> Dict[str, Any]:
    """獲取 WebSocket 連接狀態

    Args:
        session_id: Session ID

    Returns:
        連接狀態信息
    """
    return {
        "session_id": session_id,
        "connections": websocket_manager.get_connection_count(session_id),
        "total_connections": websocket_manager.get_connection_count(),
    }


@router.post("/{session_id}/ws/broadcast")
async def broadcast_to_session(
    session_id: str,
    message: Dict[str, Any],
) -> Dict[str, Any]:
    """廣播訊息到 Session 的所有連接

    Args:
        session_id: Session ID
        message: 要廣播的訊息

    Returns:
        廣播結果
    """
    success_count = await websocket_manager.broadcast_to_session(session_id, message)

    return {
        "session_id": session_id,
        "sent_count": success_count,
        "total_connections": websocket_manager.get_connection_count(session_id),
    }
