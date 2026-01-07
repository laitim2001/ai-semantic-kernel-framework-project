"""
Phase 16: Unified Chat Test Client

HTTP/SSE 測試客戶端，支援真實 API 和模擬模式。
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import httpx

# Support both module and script execution
try:
    from .mock_generator import MockSSEGenerator
    from ..config import DEFAULT_CONFIG, API_ENDPOINTS
except ImportError:
    from mock_generator import MockSSEGenerator
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import DEFAULT_CONFIG, API_ENDPOINTS


class SSEConnection:
    """
    SSE 連接管理器

    處理 SSE 連接的建立、斷線重連和事件接收。
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        url: str,
        use_simulation: bool = True,
        mock_generator: Optional[MockSSEGenerator] = None,
    ):
        self.client = client
        self.url = url
        self.use_simulation = use_simulation
        self.mock_generator = mock_generator or MockSSEGenerator()

        self.connected = False
        self.reconnect_count = 0
        self.max_reconnects = 5
        self.reconnect_delay = 1.0  # 初始重連延遲（秒）

        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._response: Optional[httpx.Response] = None
        self._listen_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        thread_id: str,
        session_id: str,
        initial_message: Optional[str] = None,
    ) -> bool:
        """
        建立 SSE 連接

        Args:
            thread_id: 對話線程 ID
            session_id: 會話 ID
            initial_message: 可選的初始消息

        Returns:
            bool: 連接是否成功
        """
        if self.use_simulation:
            self.connected = True
            return True

        try:
            request_body = {
                "thread_id": thread_id,
                "session_id": session_id,
                "messages": [],
            }
            if initial_message:
                request_body["messages"].append({
                    "role": "user",
                    "content": initial_message,
                })

            self._response = await self.client.stream(
                "POST",
                self.url,
                json=request_body,
                headers={"Accept": "text/event-stream"},
            ).__aenter__()

            if self._response.status_code == 200:
                self.connected = True
                self._listen_task = asyncio.create_task(self._listen_events())
                return True

            return False

        except Exception as e:
            print(f"SSE connection error: {e}")
            return False

    async def disconnect(self) -> bool:
        """
        關閉 SSE 連接

        Returns:
            bool: 斷開是否成功
        """
        self.connected = False

        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._response:
            await self._response.aclose()

        return True

    async def reconnect(self, thread_id: str, session_id: str) -> bool:
        """
        嘗試重連（指數退避）

        Args:
            thread_id: 對話線程 ID
            session_id: 會話 ID

        Returns:
            bool: 重連是否成功
        """
        if self.reconnect_count >= self.max_reconnects:
            return False

        self.reconnect_count += 1
        delay = self.reconnect_delay * (2 ** (self.reconnect_count - 1))

        await asyncio.sleep(delay)
        return await self.connect(thread_id, session_id)

    async def wait_for_event(
        self,
        event_type: str,
        timeout: float = 10.0,
    ) -> Optional[Dict[str, Any]]:
        """
        等待特定類型的事件

        Args:
            event_type: 事件類型
            timeout: 超時時間（秒）

        Returns:
            事件數據或 None
        """
        if self.use_simulation:
            # 模擬模式：直接返回模擬事件
            await asyncio.sleep(0.1)  # 模擬網絡延遲
            return self._generate_simulated_event(event_type)

        try:
            start = asyncio.get_event_loop().time()
            while True:
                remaining = timeout - (asyncio.get_event_loop().time() - start)
                if remaining <= 0:
                    return None

                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=remaining
                    )
                    if event.get("type") == event_type:
                        return event
                except asyncio.TimeoutError:
                    return None

        except Exception as e:
            print(f"Error waiting for event: {e}")
            return None

    async def _listen_events(self):
        """監聽 SSE 事件流"""
        try:
            async for line in self._response.aiter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data:
                        try:
                            event = json.loads(data)
                            await self._event_queue.put(event)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"SSE listen error: {e}")
            self.connected = False

    def _generate_simulated_event(self, event_type: str) -> Dict[str, Any]:
        """生成模擬事件"""
        generators = {
            "RUN_STARTED": self.mock_generator.generate_run_started,
            "RUN_FINISHED": self.mock_generator.generate_run_finished,
            "TEXT_MESSAGE_START": lambda: self.mock_generator.generate_text_message_start(),
            "TEXT_MESSAGE_CONTENT": lambda: self.mock_generator.generate_text_message_content("Simulated content"),
            "TEXT_MESSAGE_END": lambda: self.mock_generator.generate_text_message_end(),
            "TOOL_CALL_START": lambda: self.mock_generator.generate_tool_call_start(
                str(uuid.uuid4()), "test_tool"
            ),
            "STATE_SNAPSHOT": lambda: self.mock_generator.generate_state_snapshot({"status": "active"}),
        }
        generator = generators.get(event_type)
        if generator:
            return generator()
        return {"type": event_type, "timestamp": datetime.now().isoformat()}


class UnifiedChatClient:
    """
    Phase 16 統一聊天測試客戶端

    提供完整的 HTTP/SSE 操作，支援真實 API 和模擬模式。
    """

    def __init__(
        self,
        base_url: str = None,
        timeout: float = 60.0,
        use_simulation: bool = True,
    ):
        """
        初始化客戶端

        Args:
            base_url: API 基礎 URL
            timeout: 請求超時（秒）
            use_simulation: 是否使用模擬模式
        """
        self.base_url = base_url or DEFAULT_CONFIG.base_url
        self.timeout = timeout
        self.use_simulation = use_simulation

        self.mock_generator = MockSSEGenerator()
        self.client: Optional[httpx.AsyncClient] = None
        self.sse_connection: Optional[SSEConnection] = None

        # 會話狀態
        self.thread_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.messages: List[Dict[str, Any]] = []
        self.pending_approvals: List[Dict[str, Any]] = []

    async def __aenter__(self):
        """非同步上下文管理器進入"""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同步上下文管理器退出"""
        if self.sse_connection:
            await self.sse_connection.disconnect()
        if self.client:
            await self.client.aclose()

    # =========================================================================
    # SSE 連接管理
    # =========================================================================

    async def connect_sse(
        self,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """
        建立 SSE 連接

        Args:
            thread_id: 對話線程 ID（可選，自動生成）
            session_id: 會話 ID（可選，自動生成）

        Returns:
            bool: 連接是否成功
        """
        self.thread_id = thread_id or str(uuid.uuid4())
        self.session_id = session_id or str(uuid.uuid4())

        self.sse_connection = SSEConnection(
            client=self.client,
            url=API_ENDPOINTS["unified_chat"]["sse_stream"],
            use_simulation=self.use_simulation,
            mock_generator=self.mock_generator,
        )

        return await self.sse_connection.connect(self.thread_id, self.session_id)

    async def disconnect_sse(self) -> bool:
        """
        斷開 SSE 連接

        Returns:
            bool: 斷開是否成功
        """
        if self.sse_connection:
            return await self.sse_connection.disconnect()
        return True

    async def reconnect_sse(self) -> bool:
        """
        嘗試重連 SSE

        Returns:
            bool: 重連是否成功
        """
        if self.sse_connection and self.thread_id and self.session_id:
            return await self.sse_connection.reconnect(self.thread_id, self.session_id)
        return False

    async def wait_for_event(
        self,
        event_type: str,
        timeout: float = 10.0,
    ) -> Optional[Dict[str, Any]]:
        """
        等待特定類型的事件

        Args:
            event_type: 事件類型
            timeout: 超時時間（秒）

        Returns:
            事件數據或 None
        """
        if self.sse_connection:
            return await self.sse_connection.wait_for_event(event_type, timeout)
        return None

    # =========================================================================
    # 消息操作
    # =========================================================================

    async def send_message(
        self,
        content: str,
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        發送用戶消息

        Args:
            content: 消息內容
            attachments: 可選的附件列表

        Returns:
            發送結果
        """
        if self.use_simulation:
            # 模擬模式：返回模擬的消息流事件
            return {
                "success": True,
                "message_id": str(uuid.uuid4()),
                "events": self.mock_generator.generate_message_stream(
                    f"This is a simulated response to: {content}"
                ),
            }

        try:
            request_body = {
                "thread_id": self.thread_id,
                "session_id": self.session_id,
                "messages": [{"role": "user", "content": content}],
            }
            if attachments:
                request_body["attachments"] = attachments

            response = await self.client.post(
                API_ENDPOINTS["unified_chat"]["send_message"],
                json=request_body,
                headers={"Accept": "text/event-stream"},
            )

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "message_id": str(uuid.uuid4()),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def receive_message_stream(
        self,
        timeout: float = 30.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        接收消息流

        Args:
            timeout: 總超時時間（秒）

        Yields:
            事件數據
        """
        if self.use_simulation:
            # 模擬模式：生成模擬事件流
            events = self.mock_generator.generate_message_stream(
                "This is a simulated streaming response."
            )
            for event in events:
                await asyncio.sleep(0.05)  # 模擬流式延遲
                yield event
            return

        start = asyncio.get_event_loop().time()
        while True:
            remaining = timeout - (asyncio.get_event_loop().time() - start)
            if remaining <= 0:
                break

            event = await self.wait_for_event("TEXT_MESSAGE_CONTENT", timeout=remaining)
            if event:
                yield event
            else:
                break

    async def cancel_stream(self) -> bool:
        """
        取消當前消息流

        Returns:
            bool: 取消是否成功
        """
        # 目前通過斷開 SSE 連接實現
        if self.sse_connection:
            await self.sse_connection.disconnect()
            # 重新連接
            return await self.connect_sse(self.thread_id, self.session_id)
        return False

    # =========================================================================
    # 審批操作
    # =========================================================================

    async def get_pending_approvals(
        self,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        獲取待審批列表

        Args:
            session_id: 會話 ID（可選，使用當前會話）

        Returns:
            待審批項目列表
        """
        session_id = session_id or self.session_id

        if self.use_simulation:
            return self.pending_approvals

        try:
            endpoint = API_ENDPOINTS["unified_chat"]["pending_approvals"].format(
                session_id=session_id
            )
            response = await self.client.get(endpoint)

            if response.status_code == 200:
                return response.json().get("approvals", [])
            return []

        except Exception as e:
            print(f"Error getting pending approvals: {e}")
            return []

    async def approve_tool_call(
        self,
        tool_call_id: str,
    ) -> Dict[str, Any]:
        """
        批准工具呼叫

        Args:
            tool_call_id: 工具呼叫 ID

        Returns:
            批准結果
        """
        if self.use_simulation:
            # 從待審批列表中移除
            self.pending_approvals = [
                a for a in self.pending_approvals
                if a.get("tool_call_id") != tool_call_id
            ]
            return {
                "success": True,
                "tool_call_id": tool_call_id,
                "status": "approved",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            endpoint = API_ENDPOINTS["unified_chat"]["tool_approve"].format(
                tool_call_id=tool_call_id
            )
            response = await self.client.post(endpoint)

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def reject_tool_call(
        self,
        tool_call_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        拒絕工具呼叫

        Args:
            tool_call_id: 工具呼叫 ID
            reason: 拒絕原因

        Returns:
            拒絕結果
        """
        if self.use_simulation:
            # 從待審批列表中移除
            self.pending_approvals = [
                a for a in self.pending_approvals
                if a.get("tool_call_id") != tool_call_id
            ]
            return {
                "success": True,
                "tool_call_id": tool_call_id,
                "status": "rejected",
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }

        try:
            endpoint = API_ENDPOINTS["unified_chat"]["tool_reject"].format(
                tool_call_id=tool_call_id
            )
            response = await self.client.post(
                endpoint,
                json={"reason": reason} if reason else None
            )

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def add_pending_approval(
        self,
        tool_call_id: str,
        tool_name: str,
        risk_level: str = "low",
    ):
        """
        添加待審批項目（模擬模式）

        Args:
            tool_call_id: 工具呼叫 ID
            tool_name: 工具名稱
            risk_level: 風險等級
        """
        self.pending_approvals.append({
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "risk_level": risk_level,
            "created_at": datetime.now().isoformat(),
        })

    # =========================================================================
    # 檢查點操作
    # =========================================================================

    async def get_checkpoints(
        self,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        獲取檢查點列表

        Args:
            session_id: 會話 ID（可選，使用當前會話）

        Returns:
            檢查點列表
        """
        if self.use_simulation:
            return [
                {
                    "checkpoint_id": f"cp-{i}",
                    "step_index": i,
                    "step_name": f"Step {i + 1}",
                    "created_at": datetime.now().isoformat(),
                }
                for i in range(3)
            ]

        try:
            response = await self.client.get(
                API_ENDPOINTS["unified_chat"]["checkpoints_list"]
            )

            if response.status_code == 200:
                return response.json().get("checkpoints", [])
            return []

        except Exception as e:
            print(f"Error getting checkpoints: {e}")
            return []

    async def restore_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Dict[str, Any]:
        """
        恢復檢查點

        Args:
            checkpoint_id: 檢查點 ID

        Returns:
            恢復結果
        """
        if self.use_simulation:
            return {
                "success": True,
                "checkpoint_id": checkpoint_id,
                "restored_at": datetime.now().isoformat(),
                "message": f"Successfully restored to checkpoint {checkpoint_id}",
            }

        try:
            endpoint = API_ENDPOINTS["unified_chat"]["checkpoint_restore"].format(
                checkpoint_id=checkpoint_id
            )
            response = await self.client.post(endpoint)

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # 模式檢測
    # =========================================================================

    async def analyze_intent(
        self,
        input_text: str,
    ) -> Dict[str, Any]:
        """
        分析用戶意圖以決定執行模式

        Args:
            input_text: 用戶輸入

        Returns:
            意圖分析結果
        """
        if self.use_simulation:
            return self.mock_generator.generate_intent_analysis_response(input_text)

        try:
            response = await self.client.post(
                API_ENDPOINTS["unified_chat"]["analyze_intent"],
                json={"input": input_text}
            )

            if response.status_code == 200:
                return response.json()
            return {
                "mode": "CHAT_MODE",
                "confidence": 0.5,
                "reason": "Default fallback",
            }

        except Exception as e:
            return {
                "mode": "CHAT_MODE",
                "confidence": 0.5,
                "reason": f"Error: {e}",
            }

    # =========================================================================
    # 狀態同步
    # =========================================================================

    async def sync_state(
        self,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        同步會話狀態

        Args:
            session_id: 會話 ID（可選，使用當前會話）

        Returns:
            狀態快照
        """
        session_id = session_id or self.session_id

        if self.use_simulation:
            return {
                "session_id": session_id,
                "mode": "CHAT_MODE",
                "messages_count": len(self.messages),
                "pending_approvals": len(self.pending_approvals),
                "timestamp": datetime.now().isoformat(),
            }

        try:
            endpoint = API_ENDPOINTS["unified_chat"]["state_sync"].format(
                session_id=session_id
            )
            response = await self.client.get(endpoint)

            if response.status_code == 200:
                return response.json()
            return {}

        except Exception as e:
            print(f"Error syncing state: {e}")
            return {}

    # =========================================================================
    # 輔助方法
    # =========================================================================

    def is_connected(self) -> bool:
        """檢查 SSE 是否連接"""
        return self.sse_connection is not None and self.sse_connection.connected

    def get_connection_stats(self) -> Dict[str, Any]:
        """獲取連接統計"""
        if self.sse_connection:
            return {
                "connected": self.sse_connection.connected,
                "reconnect_count": self.sse_connection.reconnect_count,
                "max_reconnects": self.sse_connection.max_reconnects,
            }
        return {"connected": False}
