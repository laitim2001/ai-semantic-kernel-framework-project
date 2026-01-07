"""
Phase 16 Scenario: SSE Connection Management (PHASE16-001)

驗證 SSE 連接的建立、斷線重連和事件接收。
"""

import asyncio
from typing import Any, Dict, Optional

# Support both module and script execution
try:
    from ..base import PhaseTestBase, TestPhase, TestStatus
    from ..config import PhaseTestConfig
    from .unified_chat_client import UnifiedChatClient
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base import PhaseTestBase, TestPhase, TestStatus
    from config import PhaseTestConfig
    from unified_chat_client import UnifiedChatClient


class SSEConnectionScenario(PhaseTestBase):
    """
    場景 1: SSE 連接管理

    測試目標: 驗證 SSE 連接的建立、斷線重連和事件接收
    """

    SCENARIO_ID = "PHASE16-001"
    SCENARIO_NAME = "SSE Connection Management"
    SCENARIO_DESCRIPTION = "驗證 SSE 連接的建立、斷線重連和事件接收"
    PHASE = TestPhase.PHASE_16

    def __init__(
        self,
        config: Optional[PhaseTestConfig] = None,
        use_simulation: bool = True,
    ):
        super().__init__(config)
        self.use_simulation = use_simulation
        self.chat_client: Optional[UnifiedChatClient] = None

    async def setup(self) -> bool:
        """初始化測試環境"""
        self.chat_client = UnifiedChatClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            use_simulation=self.use_simulation,
        )
        await self.chat_client.__aenter__()
        return True

    async def teardown(self) -> bool:
        """清理測試環境"""
        if self.chat_client:
            await self.chat_client.__aexit__(None, None, None)
        return True

    async def execute(self) -> bool:
        """執行測試場景"""
        all_passed = True

        # Step 1: 建立 SSE 連接
        result = await self.run_step(
            "STEP-1",
            "建立 SSE 連接",
            self._step_establish_connection
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 2: 驗證連接狀態
        result = await self.run_step(
            "STEP-2",
            "驗證連接狀態",
            self._step_verify_connection_status
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 3: 接收事件
        result = await self.run_step(
            "STEP-3",
            "接收 SSE 事件",
            self._step_receive_events
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 4: 模擬斷線
        result = await self.run_step(
            "STEP-4",
            "模擬斷線",
            self._step_simulate_disconnect
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 5: 驗證自動重連
        result = await self.run_step(
            "STEP-5",
            "驗證自動重連",
            self._step_verify_reconnect
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 6: 關閉連接
        result = await self.run_step(
            "STEP-6",
            "關閉連接並驗證清理",
            self._step_close_connection
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        return all_passed

    # =========================================================================
    # 測試步驟實現
    # =========================================================================

    async def _step_establish_connection(self) -> Dict[str, Any]:
        """Step 1: 建立 SSE 連接"""
        connected = await self.chat_client.connect_sse()

        if connected:
            return {
                "success": True,
                "message": f"SSE 連接成功建立 (thread: {self.chat_client.thread_id[:8]}...)",
                "details": {
                    "thread_id": self.chat_client.thread_id,
                    "session_id": self.chat_client.session_id,
                    "simulation_mode": self.use_simulation,
                },
            }
        else:
            return {
                "success": False,
                "message": "SSE 連接建立失敗",
            }

    async def _step_verify_connection_status(self) -> Dict[str, Any]:
        """Step 2: 驗證連接狀態"""
        is_connected = self.chat_client.is_connected()
        stats = self.chat_client.get_connection_stats()

        if is_connected:
            return {
                "success": True,
                "message": "連接狀態驗證通過",
                "details": stats,
            }
        else:
            return {
                "success": False,
                "message": "連接狀態驗證失敗",
                "details": stats,
            }

    async def _step_receive_events(self) -> Dict[str, Any]:
        """Step 3: 接收 SSE 事件"""
        events_received = []

        # 嘗試接收幾個不同類型的事件
        event_types = ["RUN_STARTED", "TEXT_MESSAGE_START", "STATE_SNAPSHOT"]

        for event_type in event_types:
            event = await self.chat_client.wait_for_event(event_type, timeout=5.0)
            if event:
                events_received.append({
                    "type": event.get("type"),
                    "has_timestamp": "timestamp" in event,
                })

        if len(events_received) >= 2:  # 至少接收到 2 種事件
            return {
                "success": True,
                "message": f"成功接收 {len(events_received)} 種事件類型",
                "details": {"events": events_received},
            }
        else:
            return {
                "success": False,
                "message": f"事件接收不足，只接收到 {len(events_received)} 種",
                "details": {"events": events_received},
            }

    async def _step_simulate_disconnect(self) -> Dict[str, Any]:
        """Step 4: 模擬斷線"""
        # 斷開連接
        disconnected = await self.chat_client.disconnect_sse()

        if disconnected:
            is_connected = self.chat_client.is_connected()
            if not is_connected:
                return {
                    "success": True,
                    "message": "成功模擬斷線",
                    "details": {"connected": is_connected},
                }
            else:
                return {
                    "success": False,
                    "message": "斷線後連接狀態仍為 True",
                }
        else:
            return {
                "success": False,
                "message": "斷線操作失敗",
            }

    async def _step_verify_reconnect(self) -> Dict[str, Any]:
        """Step 5: 驗證自動重連"""
        # 嘗試重連
        reconnected = await self.chat_client.reconnect_sse()

        if reconnected:
            is_connected = self.chat_client.is_connected()
            stats = self.chat_client.get_connection_stats()

            if is_connected:
                return {
                    "success": True,
                    "message": f"重連成功 (嘗試次數: {stats.get('reconnect_count', 0)})",
                    "details": stats,
                }
            else:
                return {
                    "success": False,
                    "message": "重連後連接狀態仍為 False",
                    "details": stats,
                }
        else:
            return {
                "success": False,
                "message": "重連操作失敗",
            }

    async def _step_close_connection(self) -> Dict[str, Any]:
        """Step 6: 關閉連接並驗證清理"""
        closed = await self.chat_client.disconnect_sse()

        if closed:
            is_connected = self.chat_client.is_connected()
            if not is_connected:
                return {
                    "success": True,
                    "message": "連接已正確關閉並清理",
                    "details": {
                        "connected": is_connected,
                        "thread_id": self.chat_client.thread_id,
                    },
                }
            else:
                return {
                    "success": False,
                    "message": "關閉後連接狀態未清理",
                }
        else:
            return {
                "success": False,
                "message": "關閉操作失敗",
            }


async def main():
    """獨立執行測試"""
    scenario = SSEConnectionScenario(use_simulation=True)
    result = await scenario.run()
    return result


if __name__ == "__main__":
    asyncio.run(main())
