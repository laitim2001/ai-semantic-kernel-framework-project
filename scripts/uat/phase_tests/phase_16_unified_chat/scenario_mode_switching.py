"""
Phase 16 Scenario: Mode Switching (PHASE16-003)

驗證 Chat/Workflow 模式的自動檢測和手動切換。
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


class ModeSwitchingScenario(PhaseTestBase):
    """
    場景 3: 模式切換

    測試目標: 驗證 Chat/Workflow 模式的自動檢測和手動切換
    """

    SCENARIO_ID = "PHASE16-003"
    SCENARIO_NAME = "Mode Switching"
    SCENARIO_DESCRIPTION = "驗證 Chat/Workflow 模式的自動檢測和手動切換"
    PHASE = TestPhase.PHASE_16

    def __init__(
        self,
        config: Optional[PhaseTestConfig] = None,
        use_simulation: bool = True,
    ):
        super().__init__(config)
        self.use_simulation = use_simulation
        self.chat_client: Optional[UnifiedChatClient] = None
        self.detected_modes: Dict[str, str] = {}

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

        # Step 1: 發送 Chat 類型輸入
        result = await self.run_step(
            "STEP-1",
            "發送 Chat 類型輸入",
            self._step_detect_chat_mode
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 2: 發送 Workflow 類型輸入
        result = await self.run_step(
            "STEP-2",
            "發送 Workflow 類型輸入",
            self._step_detect_workflow_mode
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 3: 驗證信心分數
        result = await self.run_step(
            "STEP-3",
            "驗證信心分數",
            self._step_verify_confidence
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 4: 測試邊界情況
        result = await self.run_step(
            "STEP-4",
            "測試邊界情況（模糊輸入）",
            self._step_test_edge_cases
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 5: 驗證模式切換原因記錄
        result = await self.run_step(
            "STEP-5",
            "驗證模式切換原因記錄",
            self._step_verify_switch_reason
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 6: 測試多次切換
        result = await self.run_step(
            "STEP-6",
            "測試多次連續切換",
            self._step_test_multiple_switches
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        return all_passed

    # =========================================================================
    # 測試步驟實現
    # =========================================================================

    async def _step_detect_chat_mode(self) -> Dict[str, Any]:
        """Step 1: 發送 Chat 類型輸入，驗證模式為 CHAT_MODE"""
        chat_inputs = [
            "What is the weather like today?",
            "How do I use this feature?",
            "Tell me about machine learning.",
            "Why does this happen?",
        ]

        results = []
        for input_text in chat_inputs:
            analysis = await self.chat_client.analyze_intent(input_text)
            results.append({
                "input": input_text,
                "mode": analysis.get("mode"),
                "confidence": analysis.get("confidence"),
            })
            self.detected_modes[input_text] = analysis.get("mode")

        # 檢查是否大部分被識別為 CHAT_MODE
        chat_mode_count = sum(1 for r in results if r["mode"] == "CHAT_MODE")
        success = chat_mode_count >= len(chat_inputs) * 0.75  # 75% 以上正確

        if success:
            return {
                "success": True,
                "message": f"Chat 模式檢測通過 ({chat_mode_count}/{len(chat_inputs)} 正確)",
                "details": {"results": results},
            }
        else:
            return {
                "success": False,
                "message": f"Chat 模式檢測失敗 ({chat_mode_count}/{len(chat_inputs)} 正確)",
                "details": {"results": results},
            }

    async def _step_detect_workflow_mode(self) -> Dict[str, Any]:
        """Step 2: 發送 Workflow 類型輸入，驗證模式為 WORKFLOW_MODE"""
        workflow_inputs = [
            "Process this invoice and generate a report.",
            "Execute the data analysis workflow.",
            "Run the approval process for this document.",
            "Create a summary report and calculate totals.",
        ]

        results = []
        for input_text in workflow_inputs:
            analysis = await self.chat_client.analyze_intent(input_text)
            results.append({
                "input": input_text,
                "mode": analysis.get("mode"),
                "confidence": analysis.get("confidence"),
            })
            self.detected_modes[input_text] = analysis.get("mode")

        # 檢查是否大部分被識別為 WORKFLOW_MODE
        workflow_mode_count = sum(1 for r in results if r["mode"] == "WORKFLOW_MODE")
        success = workflow_mode_count >= len(workflow_inputs) * 0.75

        if success:
            return {
                "success": True,
                "message": f"Workflow 模式檢測通過 ({workflow_mode_count}/{len(workflow_inputs)} 正確)",
                "details": {"results": results},
            }
        else:
            return {
                "success": False,
                "message": f"Workflow 模式檢測失敗 ({workflow_mode_count}/{len(workflow_inputs)} 正確)",
                "details": {"results": results},
            }

    async def _step_verify_confidence(self) -> Dict[str, Any]:
        """Step 3: 驗證信心分數"""
        test_cases = [
            ("What is AI?", "CHAT_MODE"),  # 高信心 Chat
            ("Process the invoice workflow", "WORKFLOW_MODE"),  # 高信心 Workflow
        ]

        results = []
        all_valid = True

        for input_text, expected_mode in test_cases:
            analysis = await self.chat_client.analyze_intent(input_text)
            confidence = analysis.get("confidence", 0)

            # 信心分數應該在 0-1 範圍內
            is_valid = 0 <= confidence <= 1

            results.append({
                "input": input_text,
                "expected_mode": expected_mode,
                "detected_mode": analysis.get("mode"),
                "confidence": confidence,
                "is_valid": is_valid,
            })

            if not is_valid:
                all_valid = False

        if all_valid:
            avg_confidence = sum(r["confidence"] for r in results) / len(results)
            return {
                "success": True,
                "message": f"信心分數驗證通過 (平均: {avg_confidence:.2f})",
                "details": {"results": results, "average_confidence": avg_confidence},
            }
        else:
            return {
                "success": False,
                "message": "信心分數驗證失敗（存在無效值）",
                "details": {"results": results},
            }

    async def _step_test_edge_cases(self) -> Dict[str, Any]:
        """Step 4: 測試邊界情況（模糊輸入）"""
        edge_cases = [
            "",  # 空字符串
            "hi",  # 極短輸入
            "Hello! I need help with something.",  # 混合型
            "Can you process this? What will happen?",  # 問題 + 動作
        ]

        results = []
        for input_text in edge_cases:
            analysis = await self.chat_client.analyze_intent(input_text)
            results.append({
                "input": input_text if input_text else "(empty)",
                "mode": analysis.get("mode"),
                "confidence": analysis.get("confidence"),
                "reason": analysis.get("reason", "N/A"),
            })

        # 邊界情況只要不崩潰就算通過
        all_handled = all(r["mode"] is not None for r in results)

        if all_handled:
            return {
                "success": True,
                "message": f"邊界情況處理通過 ({len(results)} 個測試)",
                "details": {"results": results},
            }
        else:
            return {
                "success": False,
                "message": "邊界情況處理失敗",
                "details": {"results": results},
            }

    async def _step_verify_switch_reason(self) -> Dict[str, Any]:
        """Step 5: 驗證模式切換原因記錄"""
        # 測試一個典型的 Workflow 輸入
        test_input = "Execute the data pipeline and generate results"
        analysis = await self.chat_client.analyze_intent(test_input)

        reason = analysis.get("reason", "")
        has_reason = bool(reason)

        # 檢查分析詳情
        analysis_details = analysis.get("analysis", {})
        has_details = bool(analysis_details)

        if has_reason:
            return {
                "success": True,
                "message": f"模式切換原因: {reason}",
                "details": {
                    "input": test_input,
                    "mode": analysis.get("mode"),
                    "reason": reason,
                    "analysis": analysis_details,
                },
            }
        else:
            return {
                "success": False,
                "message": "未提供模式切換原因",
                "details": analysis,
            }

    async def _step_test_multiple_switches(self) -> Dict[str, Any]:
        """Step 6: 測試多次連續切換"""
        switch_sequence = [
            ("What is this?", "CHAT_MODE"),
            ("Process the document", "WORKFLOW_MODE"),
            ("Why did that happen?", "CHAT_MODE"),
            ("Run the analysis", "WORKFLOW_MODE"),
            ("Explain the results", "CHAT_MODE"),
        ]

        results = []
        previous_mode = None

        for input_text, expected_mode in switch_sequence:
            analysis = await self.chat_client.analyze_intent(input_text)
            detected_mode = analysis.get("mode")

            is_switch = previous_mode is not None and previous_mode != detected_mode

            results.append({
                "input": input_text,
                "expected": expected_mode,
                "detected": detected_mode,
                "is_switch": is_switch,
                "correct": detected_mode == expected_mode,
            })

            previous_mode = detected_mode

        correct_count = sum(1 for r in results if r["correct"])
        switch_count = sum(1 for r in results if r["is_switch"])

        # 至少 60% 正確，且有模式切換發生
        success = correct_count >= len(results) * 0.6 and switch_count > 0

        if success:
            return {
                "success": True,
                "message": f"多次切換測試通過 ({correct_count}/{len(results)} 正確, {switch_count} 次切換)",
                "details": {"results": results},
            }
        else:
            return {
                "success": False,
                "message": f"多次切換測試失敗 ({correct_count}/{len(results)} 正確)",
                "details": {"results": results},
            }


async def main():
    """獨立執行測試"""
    scenario = ModeSwitchingScenario(use_simulation=True)
    result = await scenario.run()
    return result


if __name__ == "__main__":
    asyncio.run(main())
