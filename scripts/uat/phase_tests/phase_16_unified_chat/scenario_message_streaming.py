"""
Phase 16 Scenario: Message Streaming (PHASE16-002)

驗證完整的消息發送和接收流程。
"""

import asyncio
from typing import Any, Dict, List, Optional

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


class MessageStreamingScenario(PhaseTestBase):
    """
    場景 2: 消息流式傳輸

    測試目標: 驗證完整的消息發送和接收流程
    """

    SCENARIO_ID = "PHASE16-002"
    SCENARIO_NAME = "Message Streaming"
    SCENARIO_DESCRIPTION = "驗證完整的消息發送和接收流程"
    PHASE = TestPhase.PHASE_16

    def __init__(
        self,
        config: Optional[PhaseTestConfig] = None,
        use_simulation: bool = True,
    ):
        super().__init__(config)
        self.use_simulation = use_simulation
        self.chat_client: Optional[UnifiedChatClient] = None
        self.received_events: List[Dict[str, Any]] = []
        self.accumulated_content: str = ""

    async def setup(self) -> bool:
        """初始化測試環境"""
        self.chat_client = UnifiedChatClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            use_simulation=self.use_simulation,
        )
        await self.chat_client.__aenter__()

        # 建立 SSE 連接
        connected = await self.chat_client.connect_sse()
        if not connected:
            self.logger.error("Failed to establish SSE connection in setup")
            return False

        return True

    async def teardown(self) -> bool:
        """清理測試環境"""
        if self.chat_client:
            await self.chat_client.__aexit__(None, None, None)
        return True

    async def execute(self) -> bool:
        """執行測試場景"""
        all_passed = True

        # Step 1: 發送用戶消息
        result = await self.run_step(
            "STEP-1",
            "發送用戶消息",
            self._step_send_message
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 2: 接收 RUN_STARTED 事件
        result = await self.run_step(
            "STEP-2",
            "接收 RUN_STARTED 事件",
            self._step_receive_run_started
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 3: 接收 TEXT_MESSAGE_START 事件
        result = await self.run_step(
            "STEP-3",
            "接收 TEXT_MESSAGE_START 事件",
            self._step_receive_message_start
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 4: 接收流式內容
        result = await self.run_step(
            "STEP-4",
            "接收 TEXT_MESSAGE_CONTENT 事件 (流式)",
            self._step_receive_content_stream
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 5: 接收 TEXT_MESSAGE_END 事件
        result = await self.run_step(
            "STEP-5",
            "接收 TEXT_MESSAGE_END 事件",
            self._step_receive_message_end
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 6: 接收 RUN_FINISHED 事件
        result = await self.run_step(
            "STEP-6",
            "接收 RUN_FINISHED 事件",
            self._step_receive_run_finished
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 7: 驗證消息完整性
        result = await self.run_step(
            "STEP-7",
            "驗證消息完整性",
            self._step_verify_message_integrity
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        return all_passed

    # =========================================================================
    # 測試步驟實現
    # =========================================================================

    async def _step_send_message(self) -> Dict[str, Any]:
        """Step 1: 發送用戶消息"""
        test_message = "Hello, this is a test message for streaming validation."

        result = await self.chat_client.send_message(test_message)

        if result.get("success"):
            # 如果是模擬模式，保存事件以供後續步驟使用
            if self.use_simulation and "events" in result:
                self.received_events = result["events"]

            return {
                "success": True,
                "message": f"消息發送成功 (ID: {result.get('message_id', 'N/A')[:8]}...)",
                "details": {
                    "content": test_message,
                    "message_id": result.get("message_id"),
                    "events_count": len(result.get("events", [])),
                },
            }
        else:
            return {
                "success": False,
                "message": f"消息發送失敗: {result.get('error', 'Unknown error')}",
            }

    async def _step_receive_run_started(self) -> Dict[str, Any]:
        """Step 2: 接收 RUN_STARTED 事件"""
        if self.use_simulation and self.received_events:
            # 從預生成的事件中查找
            event = next(
                (e for e in self.received_events if e.get("type") == "RUN_STARTED"),
                None
            )
        else:
            event = await self.chat_client.wait_for_event("RUN_STARTED", timeout=5.0)

        if event:
            return {
                "success": True,
                "message": f"接收到 RUN_STARTED (runId: {event.get('runId', 'N/A')[:8]}...)",
                "details": event,
            }
        else:
            return {
                "success": False,
                "message": "未接收到 RUN_STARTED 事件",
            }

    async def _step_receive_message_start(self) -> Dict[str, Any]:
        """Step 3: 接收 TEXT_MESSAGE_START 事件"""
        if self.use_simulation and self.received_events:
            event = next(
                (e for e in self.received_events if e.get("type") == "TEXT_MESSAGE_START"),
                None
            )
        else:
            event = await self.chat_client.wait_for_event("TEXT_MESSAGE_START", timeout=5.0)

        if event:
            return {
                "success": True,
                "message": f"接收到 TEXT_MESSAGE_START (role: {event.get('role', 'N/A')})",
                "details": event,
            }
        else:
            return {
                "success": False,
                "message": "未接收到 TEXT_MESSAGE_START 事件",
            }

    async def _step_receive_content_stream(self) -> Dict[str, Any]:
        """Step 4: 接收 TEXT_MESSAGE_CONTENT 事件 (流式)"""
        content_events = []

        if self.use_simulation and self.received_events:
            content_events = [
                e for e in self.received_events
                if e.get("type") == "TEXT_MESSAGE_CONTENT"
            ]
            for event in content_events:
                self.accumulated_content += event.get("content", "")
        else:
            # 從 SSE 流接收
            async for event in self.chat_client.receive_message_stream(timeout=10.0):
                content_events.append(event)
                self.accumulated_content += event.get("content", "")
                # 最多接收 10 個 chunk
                if len(content_events) >= 10:
                    break

        if content_events:
            return {
                "success": True,
                "message": f"接收到 {len(content_events)} 個內容片段",
                "details": {
                    "chunks_count": len(content_events),
                    "total_length": len(self.accumulated_content),
                    "preview": self.accumulated_content[:100] + "..." if len(self.accumulated_content) > 100 else self.accumulated_content,
                },
            }
        else:
            return {
                "success": False,
                "message": "未接收到任何 TEXT_MESSAGE_CONTENT 事件",
            }

    async def _step_receive_message_end(self) -> Dict[str, Any]:
        """Step 5: 接收 TEXT_MESSAGE_END 事件"""
        if self.use_simulation and self.received_events:
            event = next(
                (e for e in self.received_events if e.get("type") == "TEXT_MESSAGE_END"),
                None
            )
        else:
            event = await self.chat_client.wait_for_event("TEXT_MESSAGE_END", timeout=5.0)

        if event:
            return {
                "success": True,
                "message": f"接收到 TEXT_MESSAGE_END (messageId: {event.get('messageId', 'N/A')[:8]}...)",
                "details": event,
            }
        else:
            return {
                "success": False,
                "message": "未接收到 TEXT_MESSAGE_END 事件",
            }

    async def _step_receive_run_finished(self) -> Dict[str, Any]:
        """Step 6: 接收 RUN_FINISHED 事件"""
        if self.use_simulation and self.received_events:
            event = next(
                (e for e in self.received_events if e.get("type") == "RUN_FINISHED"),
                None
            )
        else:
            event = await self.chat_client.wait_for_event("RUN_FINISHED", timeout=5.0)

        if event:
            return {
                "success": True,
                "message": "接收到 RUN_FINISHED 事件",
                "details": event,
            }
        else:
            return {
                "success": False,
                "message": "未接收到 RUN_FINISHED 事件",
            }

    async def _step_verify_message_integrity(self) -> Dict[str, Any]:
        """Step 7: 驗證消息完整性"""
        # 驗證累積的內容
        has_content = len(self.accumulated_content) > 0

        # 驗證事件序列完整性
        if self.use_simulation and self.received_events:
            event_types = [e.get("type") for e in self.received_events]
            has_run_started = "RUN_STARTED" in event_types
            has_message_start = "TEXT_MESSAGE_START" in event_types
            has_content_events = "TEXT_MESSAGE_CONTENT" in event_types
            has_message_end = "TEXT_MESSAGE_END" in event_types
            has_run_finished = "RUN_FINISHED" in event_types

            is_complete = all([
                has_run_started,
                has_message_start,
                has_content_events,
                has_message_end,
                has_run_finished,
            ])
        else:
            # 非模擬模式下，基於已執行的步驟判斷
            is_complete = has_content

        if is_complete and has_content:
            return {
                "success": True,
                "message": f"消息完整性驗證通過 (總長度: {len(self.accumulated_content)} 字符)",
                "details": {
                    "content_length": len(self.accumulated_content),
                    "events_count": len(self.received_events),
                    "content_preview": self.accumulated_content[:200] + "..." if len(self.accumulated_content) > 200 else self.accumulated_content,
                },
                "ai_response": self.accumulated_content if len(self.accumulated_content) <= 500 else self.accumulated_content[:500] + "...",
            }
        else:
            return {
                "success": False,
                "message": "消息完整性驗證失敗",
                "details": {
                    "has_content": has_content,
                    "content_length": len(self.accumulated_content),
                },
            }


async def main():
    """獨立執行測試"""
    scenario = MessageStreamingScenario(use_simulation=True)
    result = await scenario.run()
    return result


if __name__ == "__main__":
    asyncio.run(main())
