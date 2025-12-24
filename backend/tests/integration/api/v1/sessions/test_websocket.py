"""
Integration tests for Session WebSocket handler (S46-2)

Tests:
- SessionWebSocketManager
- WebSocketMessageHandler
- WebSocket endpoint
- HTTP status endpoints
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketState
from starlette.websockets import WebSocket

from src.api.v1.sessions.websocket import (
    SessionWebSocketManager,
    WebSocketMessageHandler,
    WebSocketMessageType,
    websocket_manager,
    router,
)
from src.domain.sessions.events import ExecutionEvent, ExecutionEventType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI application"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def manager() -> SessionWebSocketManager:
    """Create fresh WebSocket manager"""
    return SessionWebSocketManager()


def create_mock_websocket(state: WebSocketState = WebSocketState.CONNECTED) -> MagicMock:
    """Create mock WebSocket with proper state"""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    ws.client_state = state
    return ws


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create mock WebSocket"""
    return create_mock_websocket(WebSocketState.CONNECTED)


@pytest.fixture
def mock_bridge() -> MagicMock:
    """Create mock SessionAgentBridge"""
    bridge = MagicMock()
    bridge.process_message = AsyncMock()
    bridge.handle_tool_approval = AsyncMock()
    bridge.cancel_pending_approvals = AsyncMock(return_value=0)
    bridge.get_pending_approvals = AsyncMock(return_value=[])
    return bridge


@pytest.fixture
def mock_event() -> ExecutionEvent:
    """Create mock execution event"""
    return ExecutionEvent(
        event_type=ExecutionEventType.CONTENT,
        session_id="test-session-id",
        content="Test response",
    )


# =============================================================================
# SessionWebSocketManager Tests
# =============================================================================


class TestSessionWebSocketManager:
    """Test SessionWebSocketManager"""

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(
        self, manager: SessionWebSocketManager, mock_websocket: MagicMock
    ):
        """Test connect accepts WebSocket connection"""
        session_id = "session-123"
        connection_id = "conn-456"

        await manager.connect(mock_websocket, session_id, connection_id)

        mock_websocket.accept.assert_called_once()
        assert manager.is_connected(connection_id)
        assert manager.get_connection_count(session_id) == 1

    @pytest.mark.asyncio
    async def test_connect_sends_connected_message(
        self, manager: SessionWebSocketManager, mock_websocket: MagicMock
    ):
        """Test connect sends connected confirmation message"""
        session_id = "session-123"
        connection_id = "conn-456"

        await manager.connect(mock_websocket, session_id, connection_id)

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == WebSocketMessageType.CONNECTED
        assert call_args["session_id"] == session_id
        assert call_args["connection_id"] == connection_id

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(
        self, manager: SessionWebSocketManager, mock_websocket: MagicMock
    ):
        """Test disconnect removes connection"""
        session_id = "session-123"
        connection_id = "conn-456"

        await manager.connect(mock_websocket, session_id, connection_id)
        assert manager.is_connected(connection_id)

        await manager.disconnect(connection_id, session_id)

        assert not manager.is_connected(connection_id)
        assert manager.get_connection_count(session_id) == 0

    @pytest.mark.asyncio
    async def test_disconnect_cancels_heartbeat_task(
        self, manager: SessionWebSocketManager, mock_websocket: MagicMock
    ):
        """Test disconnect cancels heartbeat task"""
        session_id = "session-123"
        connection_id = "conn-456"

        await manager.connect(mock_websocket, session_id, connection_id)
        await manager.start_heartbeat(connection_id, interval=1)

        # Verify heartbeat task exists
        assert connection_id in manager._heartbeat_tasks

        await manager.disconnect(connection_id, session_id)

        # Heartbeat task should be removed
        assert connection_id not in manager._heartbeat_tasks

    @pytest.mark.asyncio
    async def test_send_message_to_connected_client(
        self, manager: SessionWebSocketManager, mock_websocket: MagicMock
    ):
        """Test send message to connected client"""
        session_id = "session-123"
        connection_id = "conn-456"
        message = {"type": "test", "data": "hello"}

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        result = await manager.send_message(connection_id, message)

        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_message_to_nonexistent_connection_returns_false(
        self, manager: SessionWebSocketManager
    ):
        """Test send message to non-existent connection returns False"""
        result = await manager.send_message("nonexistent", {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_event_wraps_event_in_message(
        self, manager: SessionWebSocketManager, mock_websocket: MagicMock, mock_event: ExecutionEvent
    ):
        """Test send event wraps ExecutionEvent in message"""
        session_id = "session-123"
        connection_id = "conn-456"

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        result = await manager.send_event(connection_id, mock_event)

        assert result is True
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == WebSocketMessageType.EVENT
        assert "payload" in call_args

    @pytest.mark.asyncio
    async def test_broadcast_to_session_sends_to_all_connections(
        self, manager: SessionWebSocketManager
    ):
        """Test broadcast sends message to all session connections"""
        session_id = "session-123"
        message = {"type": "broadcast", "data": "test"}

        # Create multiple connections
        mock_ws1 = create_mock_websocket(WebSocketState.CONNECTED)
        mock_ws2 = create_mock_websocket(WebSocketState.CONNECTED)

        await manager.connect(mock_ws1, session_id, "conn-1")
        await manager.connect(mock_ws2, session_id, "conn-2")
        mock_ws1.send_json.reset_mock()
        mock_ws2.send_json.reset_mock()

        success_count = await manager.broadcast_to_session(session_id, message)

        assert success_count == 2
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_session_returns_zero(
        self, manager: SessionWebSocketManager
    ):
        """Test broadcast to session with no connections returns 0"""
        success_count = await manager.broadcast_to_session("empty-session", {"type": "test"})
        assert success_count == 0

    @pytest.mark.asyncio
    async def test_get_connection_count_returns_correct_count(
        self, manager: SessionWebSocketManager
    ):
        """Test get_connection_count returns correct count"""
        assert manager.get_connection_count() == 0
        assert manager.get_connection_count("session-123") == 0

        mock_ws = create_mock_websocket(WebSocketState.CONNECTED)

        await manager.connect(mock_ws, "session-123", "conn-1")

        assert manager.get_connection_count() == 1
        assert manager.get_connection_count("session-123") == 1
        assert manager.get_connection_count("session-456") == 0

    @pytest.mark.asyncio
    async def test_multiple_sessions_tracked_independently(
        self, manager: SessionWebSocketManager
    ):
        """Test multiple sessions are tracked independently"""
        mock_ws1 = create_mock_websocket(WebSocketState.CONNECTED)
        mock_ws2 = create_mock_websocket(WebSocketState.CONNECTED)

        await manager.connect(mock_ws1, "session-1", "conn-1")
        await manager.connect(mock_ws2, "session-2", "conn-2")

        assert manager.get_connection_count("session-1") == 1
        assert manager.get_connection_count("session-2") == 1
        assert manager.get_connection_count() == 2

        await manager.disconnect("conn-1", "session-1")

        assert manager.get_connection_count("session-1") == 0
        assert manager.get_connection_count("session-2") == 1

    @pytest.mark.asyncio
    async def test_is_connected_returns_correct_status(
        self, manager: SessionWebSocketManager, mock_websocket: MagicMock
    ):
        """Test is_connected returns correct status"""
        session_id = "session-123"
        connection_id = "conn-456"

        assert not manager.is_connected(connection_id)

        await manager.connect(mock_websocket, session_id, connection_id)
        assert manager.is_connected(connection_id)

        await manager.disconnect(connection_id, session_id)
        assert not manager.is_connected(connection_id)


# =============================================================================
# WebSocketMessageHandler Tests
# =============================================================================


class TestWebSocketMessageHandler:
    """Test WebSocketMessageHandler"""

    @pytest.mark.asyncio
    async def test_handle_heartbeat_sends_ack(
        self,
        manager: SessionWebSocketManager,
        mock_bridge: MagicMock,
        mock_websocket: MagicMock,
    ):
        """Test heartbeat message receives acknowledgment"""
        session_id = "session-123"
        connection_id = "conn-456"
        handler = WebSocketMessageHandler(mock_bridge, manager)

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        await handler.handle_message(
            mock_websocket,
            connection_id,
            session_id,
            {"type": WebSocketMessageType.HEARTBEAT},
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == WebSocketMessageType.HEARTBEAT_ACK

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type_sends_error(
        self,
        manager: SessionWebSocketManager,
        mock_bridge: MagicMock,
        mock_websocket: MagicMock,
    ):
        """Test unknown message type sends error"""
        session_id = "session-123"
        connection_id = "conn-456"
        handler = WebSocketMessageHandler(mock_bridge, manager)

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        await handler.handle_message(
            mock_websocket,
            connection_id,
            session_id,
            {"type": "unknown_type"},
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == WebSocketMessageType.ERROR
        assert call_args["error_code"] == "UNKNOWN_MESSAGE_TYPE"

    @pytest.mark.asyncio
    async def test_handle_user_message_calls_bridge(
        self,
        manager: SessionWebSocketManager,
        mock_bridge: MagicMock,
        mock_websocket: MagicMock,
        mock_event: ExecutionEvent,
    ):
        """Test user message calls bridge.process_message"""
        session_id = "session-123"
        connection_id = "conn-456"
        content = "Hello, AI!"

        async def mock_process_message(*args, **kwargs):
            yield mock_event

        mock_bridge.process_message = mock_process_message
        handler = WebSocketMessageHandler(mock_bridge, manager)

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        await handler.handle_message(
            mock_websocket,
            connection_id,
            session_id,
            {"type": WebSocketMessageType.MESSAGE, "content": content},
        )

        # Should send event back
        assert mock_websocket.send_json.called

    @pytest.mark.asyncio
    async def test_handle_empty_message_sends_error(
        self,
        manager: SessionWebSocketManager,
        mock_bridge: MagicMock,
        mock_websocket: MagicMock,
    ):
        """Test empty message sends error"""
        session_id = "session-123"
        connection_id = "conn-456"
        handler = WebSocketMessageHandler(mock_bridge, manager)

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        await handler.handle_message(
            mock_websocket,
            connection_id,
            session_id,
            {"type": WebSocketMessageType.MESSAGE, "content": ""},
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == WebSocketMessageType.ERROR
        assert call_args["error_code"] == "EMPTY_MESSAGE"

    @pytest.mark.asyncio
    async def test_handle_approval_calls_bridge(
        self,
        manager: SessionWebSocketManager,
        mock_bridge: MagicMock,
        mock_websocket: MagicMock,
        mock_event: ExecutionEvent,
    ):
        """Test approval message calls bridge.handle_tool_approval"""
        session_id = "session-123"
        connection_id = "conn-456"
        approval_id = "approval-789"

        async def mock_handle_approval(*args, **kwargs):
            yield mock_event

        mock_bridge.handle_tool_approval = mock_handle_approval
        handler = WebSocketMessageHandler(mock_bridge, manager)

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        await handler.handle_message(
            mock_websocket,
            connection_id,
            session_id,
            {
                "type": WebSocketMessageType.APPROVAL,
                "approval_id": approval_id,
                "approved": True,
                "feedback": "Looks good",
            },
        )

        # Should send event back
        assert mock_websocket.send_json.called

    @pytest.mark.asyncio
    async def test_handle_approval_without_id_sends_error(
        self,
        manager: SessionWebSocketManager,
        mock_bridge: MagicMock,
        mock_websocket: MagicMock,
    ):
        """Test approval without approval_id sends error"""
        session_id = "session-123"
        connection_id = "conn-456"
        handler = WebSocketMessageHandler(mock_bridge, manager)

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        await handler.handle_message(
            mock_websocket,
            connection_id,
            session_id,
            {"type": WebSocketMessageType.APPROVAL, "approved": True},
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == WebSocketMessageType.ERROR
        assert call_args["error_code"] == "MISSING_APPROVAL_ID"

    @pytest.mark.asyncio
    async def test_handle_cancel_calls_bridge(
        self,
        manager: SessionWebSocketManager,
        mock_bridge: MagicMock,
        mock_websocket: MagicMock,
    ):
        """Test cancel message calls bridge.cancel_pending_approvals"""
        session_id = "session-123"
        connection_id = "conn-456"
        mock_bridge.cancel_pending_approvals = AsyncMock(return_value=2)
        handler = WebSocketMessageHandler(mock_bridge, manager)

        await manager.connect(mock_websocket, session_id, connection_id)
        mock_websocket.send_json.reset_mock()

        await handler.handle_message(
            mock_websocket,
            connection_id,
            session_id,
            {"type": WebSocketMessageType.CANCEL, "reason": "test_cancel"},
        )

        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "cancelled"
        assert call_args["cancelled_approvals"] == 2
        assert call_args["reason"] == "test_cancel"


# =============================================================================
# HTTP Endpoint Tests
# =============================================================================


class TestWebSocketStatusEndpoints:
    """Test WebSocket HTTP status endpoints"""

    def test_get_websocket_status_returns_counts(self, test_client: TestClient):
        """Test get_websocket_status returns connection counts"""
        response = test_client.get("/sessions/test-session/ws/status")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "connections" in data
        assert "total_connections" in data
        assert data["session_id"] == "test-session"

    def test_broadcast_to_session_returns_result(self, test_client: TestClient):
        """Test broadcast_to_session returns broadcast result"""
        response = test_client.post(
            "/sessions/test-session/ws/broadcast",
            json={"type": "notification", "message": "Hello"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "sent_count" in data
        assert "total_connections" in data
        assert data["session_id"] == "test-session"


# =============================================================================
# Integration Tests (WebSocket Connection Flow)
# =============================================================================


class TestWebSocketIntegration:
    """Integration tests for WebSocket connection flow"""

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(
        self, manager: SessionWebSocketManager
    ):
        """Test complete WebSocket connection lifecycle"""
        session_id = "session-123"
        connection_id = "conn-456"

        # Create mock WebSocket
        mock_ws = create_mock_websocket(WebSocketState.CONNECTED)

        # Connect
        await manager.connect(mock_ws, session_id, connection_id)
        assert manager.is_connected(connection_id)
        assert manager.get_connection_count(session_id) == 1

        # Send message
        result = await manager.send_message(connection_id, {"type": "test"})
        assert result is True

        # Disconnect
        await manager.disconnect(connection_id, session_id)
        assert not manager.is_connected(connection_id)
        assert manager.get_connection_count(session_id) == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_same_session(
        self, manager: SessionWebSocketManager
    ):
        """Test multiple connections to same session"""
        session_id = "session-123"

        connections = []
        for i in range(3):
            mock_ws = create_mock_websocket(WebSocketState.CONNECTED)
            connections.append((f"conn-{i}", mock_ws))

        # Connect all
        for conn_id, ws in connections:
            await manager.connect(ws, session_id, conn_id)

        assert manager.get_connection_count(session_id) == 3

        # Broadcast
        message = {"type": "broadcast", "data": "test"}
        for _, ws in connections:
            ws.send_json.reset_mock()

        success_count = await manager.broadcast_to_session(session_id, message)
        assert success_count == 3

        # Disconnect one
        await manager.disconnect("conn-1", session_id)
        assert manager.get_connection_count(session_id) == 2

        # Disconnect all
        for conn_id, _ in connections:
            if conn_id != "conn-1":
                await manager.disconnect(conn_id, session_id)

        assert manager.get_connection_count(session_id) == 0

    @pytest.mark.asyncio
    async def test_concurrent_connections(
        self, manager: SessionWebSocketManager
    ):
        """Test concurrent WebSocket connections"""
        session_ids = [f"session-{i}" for i in range(5)]

        async def connect_session(session_id: str):
            mock_ws = create_mock_websocket(WebSocketState.CONNECTED)
            await manager.connect(mock_ws, session_id, f"conn-{session_id}")
            return session_id

        # Connect concurrently
        results = await asyncio.gather(
            *[connect_session(sid) for sid in session_ids]
        )

        assert len(results) == 5
        assert manager.get_connection_count() == 5

        for session_id in session_ids:
            assert manager.get_connection_count(session_id) == 1


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestWebSocketErrorHandling:
    """Test WebSocket error handling"""

    @pytest.mark.asyncio
    async def test_send_message_handles_disconnected_socket(
        self, manager: SessionWebSocketManager
    ):
        """Test send_message handles disconnected WebSocket gracefully"""
        session_id = "session-123"
        connection_id = "conn-456"

        # Create connected socket for initial connect, then change state
        mock_ws = create_mock_websocket(WebSocketState.CONNECTED)
        await manager.connect(mock_ws, session_id, connection_id)

        # Simulate disconnection after connect
        mock_ws.client_state = WebSocketState.DISCONNECTED

        result = await manager.send_message(connection_id, {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_handles_send_exception(
        self, manager: SessionWebSocketManager
    ):
        """Test send_message handles send exception gracefully"""
        session_id = "session-123"
        connection_id = "conn-456"

        mock_ws = create_mock_websocket(WebSocketState.CONNECTED)
        await manager.connect(mock_ws, session_id, connection_id)

        # Set send_json to raise exception after connection
        mock_ws.send_json = AsyncMock(side_effect=Exception("Send failed"))

        result = await manager.send_message(connection_id, {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_handles_nonexistent_connection(
        self, manager: SessionWebSocketManager
    ):
        """Test disconnect handles non-existent connection gracefully"""
        # Should not raise exception
        await manager.disconnect("nonexistent", "nonexistent-session")
        assert manager.get_connection_count() == 0


# =============================================================================
# WebSocketMessageType Tests
# =============================================================================


class TestWebSocketMessageType:
    """Test WebSocketMessageType constants"""

    def test_client_message_types(self):
        """Test client -> server message types"""
        assert WebSocketMessageType.MESSAGE == "message"
        assert WebSocketMessageType.APPROVAL == "approval"
        assert WebSocketMessageType.HEARTBEAT == "heartbeat"
        assert WebSocketMessageType.CANCEL == "cancel"

    def test_server_message_types(self):
        """Test server -> client message types"""
        assert WebSocketMessageType.CONNECTED == "connected"
        assert WebSocketMessageType.HEARTBEAT_ACK == "heartbeat_ack"
        assert WebSocketMessageType.ERROR == "error"
        assert WebSocketMessageType.EVENT == "event"
