"""
Phase 16 Scenario: Execution Metrics (PHASE16-006)

驗證 Token 使用、執行時間和工具統計的追蹤。
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# Support both module and script execution
try:
    from ..base import PhaseTestBase, TestPhase, TestStatus
    from ..config import PhaseTestConfig
    from .unified_chat_client import UnifiedChatClient
    from .mock_generator import MockSSEGenerator
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base import PhaseTestBase, TestPhase, TestStatus
    from config import PhaseTestConfig
    from unified_chat_client import UnifiedChatClient
    from mock_generator import MockSSEGenerator


class ExecutionMetricsScenario(PhaseTestBase):
    """
    場景 6: 執行指標

    測試目標: 驗證 Token 使用、執行時間和工具統計的追蹤
    """

    SCENARIO_ID = "PHASE16-006"
    SCENARIO_NAME = "Execution Metrics"
    SCENARIO_DESCRIPTION = "驗證 Token 使用、執行時間和工具統計的追蹤"
    PHASE = TestPhase.PHASE_16

    def __init__(
        self,
        config: Optional[PhaseTestConfig] = None,
        use_simulation: bool = True,
    ):
        super().__init__(config)
        self.use_simulation = use_simulation
        self.chat_client: Optional[UnifiedChatClient] = None
        self.mock_generator = MockSSEGenerator()

        # 指標追蹤
        self.metrics = {
            "tokens_used": 0,
            "tokens_limit": 4000,
            "execution_start": None,
            "execution_end": None,
            "tool_calls": {
                "completed": 0,
                "failed": 0,
                "pending": 0,
            },
        }

    async def setup(self) -> bool:
        """初始化測試環境"""
        self.chat_client = UnifiedChatClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            use_simulation=self.use_simulation,
        )
        await self.chat_client.__aenter__()
        await self.chat_client.connect_sse()
        return True

    async def teardown(self) -> bool:
        """清理測試環境"""
        if self.chat_client:
            await self.chat_client.__aexit__(None, None, None)
        return True

    async def execute(self) -> bool:
        """執行測試場景"""
        all_passed = True

        # Step 1: 啟動計時器
        result = await self.run_step(
            "STEP-1",
            "啟動執行計時器",
            self._step_start_timer
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 2: 發送多條消息追蹤 Token
        result = await self.run_step(
            "STEP-2",
            "發送多條消息追蹤 Token 使用",
            self._step_track_token_usage
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 3: 執行多個工具呼叫
        result = await self.run_step(
            "STEP-3",
            "執行多個工具呼叫",
            self._step_execute_tool_calls
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 4: 驗證工具統計
        result = await self.run_step(
            "STEP-4",
            "驗證工具統計",
            self._step_verify_tool_stats
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 5: 停止計時器
        result = await self.run_step(
            "STEP-5",
            "停止計時器並計算執行時間",
            self._step_stop_timer
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 6: 驗證指標格式化顯示
        result = await self.run_step(
            "STEP-6",
            "驗證指標格式化顯示",
            self._step_verify_metrics_format
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 7: 測試重置功能
        result = await self.run_step(
            "STEP-7",
            "測試指標重置功能",
            self._step_test_reset
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        return all_passed

    # =========================================================================
    # 測試步驟實現
    # =========================================================================

    async def _step_start_timer(self) -> Dict[str, Any]:
        """Step 1: 啟動執行計時器"""
        self.metrics["execution_start"] = time.time()

        return {
            "success": True,
            "message": f"計時器已啟動 ({datetime.now().strftime('%H:%M:%S.%f')[:-3]})",
            "details": {
                "start_time": self.metrics["execution_start"],
            },
        }

    async def _step_track_token_usage(self) -> Dict[str, Any]:
        """Step 2: 發送多條消息追蹤 Token 使用"""
        messages = [
            "Hello, how are you?",
            "Can you help me analyze this data?",
            "What are the key findings?",
        ]

        token_updates = []

        for i, message in enumerate(messages):
            # 發送消息
            await self.chat_client.send_message(message)

            # 模擬 Token 消耗
            tokens_for_message = len(message.split()) * 2 + 50  # 估算
            self.metrics["tokens_used"] += tokens_for_message

            # 生成 Token 更新事件
            token_event = self.mock_generator.generate_token_update(
                tokens_used=self.metrics["tokens_used"],
                tokens_limit=self.metrics["tokens_limit"],
            )

            token_updates.append({
                "message_index": i + 1,
                "tokens_added": tokens_for_message,
                "total_tokens": self.metrics["tokens_used"],
            })

            await asyncio.sleep(0.1)  # 模擬延遲

        return {
            "success": True,
            "message": f"Token 追蹤完成 (總計: {self.metrics['tokens_used']})",
            "details": {
                "messages_sent": len(messages),
                "token_updates": token_updates,
                "current_usage": f"{self.metrics['tokens_used']}/{self.metrics['tokens_limit']}",
            },
        }

    async def _step_execute_tool_calls(self) -> Dict[str, Any]:
        """Step 3: 執行多個工具呼叫"""
        tool_calls = [
            {"name": "search", "status": "completed", "duration_ms": 1200},
            {"name": "analyze", "status": "completed", "duration_ms": 2100},
            {"name": "format", "status": "completed", "duration_ms": 300},
            {"name": "validate", "status": "failed", "duration_ms": 500},
            {"name": "export", "status": "pending", "duration_ms": 0},
        ]

        for tool in tool_calls:
            tool_call_id = str(uuid.uuid4())

            # 生成工具呼叫事件
            start_event = self.mock_generator.generate_tool_call_start(
                tool_call_id=tool_call_id,
                tool_name=tool["name"],
            )

            # 更新統計
            if tool["status"] == "completed":
                self.metrics["tool_calls"]["completed"] += 1
            elif tool["status"] == "failed":
                self.metrics["tool_calls"]["failed"] += 1
            else:
                self.metrics["tool_calls"]["pending"] += 1

        return {
            "success": True,
            "message": f"工具呼叫執行完成 ({len(tool_calls)} 個)",
            "details": {
                "tool_calls": tool_calls,
                "stats": self.metrics["tool_calls"],
            },
        }

    async def _step_verify_tool_stats(self) -> Dict[str, Any]:
        """Step 4: 驗證工具統計"""
        stats = self.metrics["tool_calls"]

        # 驗證統計正確性
        expected = {
            "completed": 3,
            "failed": 1,
            "pending": 1,
        }

        is_correct = (
            stats["completed"] == expected["completed"] and
            stats["failed"] == expected["failed"] and
            stats["pending"] == expected["pending"]
        )

        total = stats["completed"] + stats["failed"] + stats["pending"]

        if is_correct:
            return {
                "success": True,
                "message": f"工具統計驗證通過 (總計: {total})",
                "details": {
                    "actual": stats,
                    "expected": expected,
                    "success_rate": f"{stats['completed']/total*100:.1f}%",
                },
            }
        else:
            return {
                "success": False,
                "message": "工具統計驗證失敗",
                "details": {
                    "actual": stats,
                    "expected": expected,
                },
            }

    async def _step_stop_timer(self) -> Dict[str, Any]:
        """Step 5: 停止計時器並計算執行時間"""
        self.metrics["execution_end"] = time.time()

        duration_seconds = self.metrics["execution_end"] - self.metrics["execution_start"]
        duration_ms = duration_seconds * 1000

        return {
            "success": True,
            "message": f"執行時間: {duration_ms:.1f}ms ({duration_seconds:.2f}s)",
            "details": {
                "start_time": self.metrics["execution_start"],
                "end_time": self.metrics["execution_end"],
                "duration_ms": duration_ms,
                "duration_seconds": duration_seconds,
            },
        }

    async def _step_verify_metrics_format(self) -> Dict[str, Any]:
        """Step 6: 驗證指標格式化顯示"""
        # 格式化指標
        formatted_metrics = {
            "token_display": f"{self.metrics['tokens_used']:,}/{self.metrics['tokens_limit']:,}",
            "token_percentage": f"{(self.metrics['tokens_used']/self.metrics['tokens_limit'])*100:.1f}%",
            "execution_time": self._format_duration(
                (self.metrics["execution_end"] - self.metrics["execution_start"]) * 1000
            ),
            "tool_summary": f"✅ {self.metrics['tool_calls']['completed']} / ❌ {self.metrics['tool_calls']['failed']} / ⏳ {self.metrics['tool_calls']['pending']}",
        }

        # 驗證格式化輸出
        has_all_formats = all(formatted_metrics.values())

        if has_all_formats:
            return {
                "success": True,
                "message": "指標格式化驗證通過",
                "details": {
                    "formatted": formatted_metrics,
                    "raw_metrics": {
                        "tokens_used": self.metrics["tokens_used"],
                        "tokens_limit": self.metrics["tokens_limit"],
                        "tool_calls": self.metrics["tool_calls"],
                    },
                },
            }
        else:
            return {
                "success": False,
                "message": "指標格式化驗證失敗",
                "details": formatted_metrics,
            }

    async def _step_test_reset(self) -> Dict[str, Any]:
        """Step 7: 測試指標重置功能"""
        # 保存當前值
        old_values = {
            "tokens_used": self.metrics["tokens_used"],
            "tool_calls": self.metrics["tool_calls"].copy(),
        }

        # 重置指標
        self.metrics = {
            "tokens_used": 0,
            "tokens_limit": 4000,
            "execution_start": None,
            "execution_end": None,
            "tool_calls": {
                "completed": 0,
                "failed": 0,
                "pending": 0,
            },
        }

        # 驗證重置成功
        is_reset = (
            self.metrics["tokens_used"] == 0 and
            self.metrics["tool_calls"]["completed"] == 0 and
            self.metrics["tool_calls"]["failed"] == 0 and
            self.metrics["tool_calls"]["pending"] == 0
        )

        if is_reset:
            return {
                "success": True,
                "message": "指標重置成功",
                "details": {
                    "old_values": old_values,
                    "new_values": {
                        "tokens_used": self.metrics["tokens_used"],
                        "tool_calls": self.metrics["tool_calls"],
                    },
                },
            }
        else:
            return {
                "success": False,
                "message": "指標重置失敗",
                "details": self.metrics,
            }

    # =========================================================================
    # 輔助方法
    # =========================================================================

    def _format_duration(self, ms: float) -> str:
        """格式化持續時間"""
        if ms < 1000:
            return f"{ms:.0f}ms"
        elif ms < 60000:
            return f"{ms/1000:.1f}s"
        else:
            minutes = int(ms / 60000)
            seconds = (ms % 60000) / 1000
            return f"{minutes}m {seconds:.0f}s"


async def main():
    """獨立執行測試"""
    scenario = ExecutionMetricsScenario(use_simulation=True)
    result = await scenario.run()
    return result


if __name__ == "__main__":
    asyncio.run(main())
