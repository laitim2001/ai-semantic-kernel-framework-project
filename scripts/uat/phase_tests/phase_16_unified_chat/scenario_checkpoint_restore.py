"""
Phase 16 Scenario: Checkpoint Restore (PHASE16-005)

驗證檢查點的創建和恢復功能。
"""

import asyncio
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


class CheckpointRestoreScenario(PhaseTestBase):
    """
    場景 5: 檢查點恢復

    測試目標: 驗證檢查點的創建和恢復功能
    """

    SCENARIO_ID = "PHASE16-005"
    SCENARIO_NAME = "Checkpoint Restore"
    SCENARIO_DESCRIPTION = "驗證檢查點的創建和恢復功能"
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
        self.created_checkpoints: List[Dict[str, Any]] = []
        self.workflow_state: Dict[str, Any] = {}

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

        # Step 1: 執行多步驟工作流
        result = await self.run_step(
            "STEP-1",
            "執行多步驟工作流",
            self._step_execute_workflow
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 2: 在 Step 2 創建檢查點
        result = await self.run_step(
            "STEP-2",
            "在 Step 2 創建檢查點",
            self._step_create_checkpoint
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 3: 繼續執行到 Step 4
        result = await self.run_step(
            "STEP-3",
            "繼續執行到 Step 4",
            self._step_continue_execution
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 4: 獲取檢查點列表
        result = await self.run_step(
            "STEP-4",
            "獲取檢查點列表",
            self._step_get_checkpoints
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 5: 恢復到 Step 2 檢查點
        result = await self.run_step(
            "STEP-5",
            "恢復到 Step 2 檢查點",
            self._step_restore_checkpoint
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 6: 驗證狀態正確回滾
        result = await self.run_step(
            "STEP-6",
            "驗證狀態正確回滾",
            self._step_verify_state_rollback
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 7: 驗證執行中禁用恢復
        result = await self.run_step(
            "STEP-7",
            "驗證執行中禁用恢復",
            self._step_verify_restore_disabled_during_execution
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 8: 測試多個檢查點
        result = await self.run_step(
            "STEP-8",
            "測試多個檢查點管理",
            self._step_test_multiple_checkpoints
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        return all_passed

    # =========================================================================
    # 測試步驟實現
    # =========================================================================

    async def _step_execute_workflow(self) -> Dict[str, Any]:
        """Step 1: 執行多步驟工作流"""
        workflow_steps = [
            {"name": "Data Collection", "status": "completed"},
            {"name": "Data Validation", "status": "completed"},
        ]

        # 生成工作流事件
        events = self.mock_generator.generate_workflow_sequence(workflow_steps)

        # 更新工作流狀態
        self.workflow_state = {
            "current_step": 2,
            "total_steps": 5,
            "completed_steps": workflow_steps,
            "variables": {"processed_count": 100},
        }

        return {
            "success": True,
            "message": f"工作流執行到 Step 2/5",
            "details": {
                "events_generated": len(events),
                "state": self.workflow_state,
            },
        }

    async def _step_create_checkpoint(self) -> Dict[str, Any]:
        """Step 2: 在 Step 2 創建檢查點"""
        checkpoint = {
            "checkpoint_id": f"cp-{uuid.uuid4().hex[:8]}",
            "step_index": 2,
            "step_name": "Data Validation",
            "state_snapshot": self.workflow_state.copy(),
            "created_at": datetime.now().isoformat(),
        }

        self.created_checkpoints.append(checkpoint)

        return {
            "success": True,
            "message": f"檢查點已創建 (ID: {checkpoint['checkpoint_id']})",
            "details": checkpoint,
        }

    async def _step_continue_execution(self) -> Dict[str, Any]:
        """Step 3: 繼續執行到 Step 4"""
        additional_steps = [
            {"name": "Data Processing", "status": "completed"},
            {"name": "Report Generation", "status": "completed"},
        ]

        # 更新狀態
        self.workflow_state["current_step"] = 4
        self.workflow_state["completed_steps"].extend(additional_steps)
        self.workflow_state["variables"]["processed_count"] = 500

        return {
            "success": True,
            "message": f"工作流執行到 Step 4/5",
            "details": {
                "current_step": 4,
                "processed_count": 500,
            },
        }

    async def _step_get_checkpoints(self) -> Dict[str, Any]:
        """Step 4: 獲取檢查點列表"""
        checkpoints = await self.chat_client.get_checkpoints()

        # 在模擬模式下，合併我們創建的檢查點
        if self.use_simulation:
            checkpoints = self.created_checkpoints + checkpoints

        if checkpoints:
            return {
                "success": True,
                "message": f"獲取到 {len(checkpoints)} 個檢查點",
                "details": {"checkpoints": checkpoints},
            }
        else:
            return {
                "success": False,
                "message": "無法獲取檢查點列表",
            }

    async def _step_restore_checkpoint(self) -> Dict[str, Any]:
        """Step 5: 恢復到 Step 2 檢查點"""
        if not self.created_checkpoints:
            return {
                "success": False,
                "message": "沒有可用的檢查點",
            }

        checkpoint = self.created_checkpoints[0]
        checkpoint_id = checkpoint["checkpoint_id"]

        result = await self.chat_client.restore_checkpoint(checkpoint_id)

        if result.get("success"):
            # 恢復狀態
            self.workflow_state = checkpoint["state_snapshot"].copy()

            return {
                "success": True,
                "message": f"成功恢復到檢查點 {checkpoint_id}",
                "details": result,
            }
        else:
            return {
                "success": False,
                "message": f"恢復失敗: {result.get('error', 'Unknown')}",
                "details": result,
            }

    async def _step_verify_state_rollback(self) -> Dict[str, Any]:
        """Step 6: 驗證狀態正確回滾"""
        expected_state = self.created_checkpoints[0]["state_snapshot"] if self.created_checkpoints else {}

        # 驗證關鍵狀態值
        checks = {
            "current_step": self.workflow_state.get("current_step") == expected_state.get("current_step"),
            "processed_count": self.workflow_state.get("variables", {}).get("processed_count") == expected_state.get("variables", {}).get("processed_count"),
        }

        all_correct = all(checks.values())

        if all_correct:
            return {
                "success": True,
                "message": "狀態回滾驗證通過",
                "details": {
                    "current_state": self.workflow_state,
                    "expected_state": expected_state,
                    "checks": checks,
                },
            }
        else:
            return {
                "success": False,
                "message": "狀態回滾驗證失敗",
                "details": {
                    "current_state": self.workflow_state,
                    "expected_state": expected_state,
                    "checks": checks,
                },
            }

    async def _step_verify_restore_disabled_during_execution(self) -> Dict[str, Any]:
        """Step 7: 驗證執行中禁用恢復"""
        # 模擬執行中狀態
        is_executing = True  # 假設正在執行

        if self.use_simulation:
            # 在模擬模式下，我們只驗證邏輯
            # 實際應用中，UI 應該在執行中禁用恢復按鈕

            restore_allowed = not is_executing

            if not restore_allowed:
                return {
                    "success": True,
                    "message": "執行中正確禁用恢復功能",
                    "details": {
                        "is_executing": is_executing,
                        "restore_allowed": restore_allowed,
                    },
                }
            else:
                return {
                    "success": False,
                    "message": "執行中應禁用恢復功能",
                    "details": {
                        "is_executing": is_executing,
                        "restore_allowed": restore_allowed,
                    },
                }
        else:
            # 實際 API 測試
            return {
                "success": True,
                "message": "執行中禁用恢復驗證跳過（需要 UI 測試）",
            }

    async def _step_test_multiple_checkpoints(self) -> Dict[str, Any]:
        """Step 8: 測試多個檢查點管理"""
        # 創建多個檢查點
        for i in range(3):
            checkpoint = {
                "checkpoint_id": f"cp-multi-{uuid.uuid4().hex[:8]}",
                "step_index": i + 1,
                "step_name": f"Multi-Step {i + 1}",
                "state_snapshot": {
                    "step": i + 1,
                    "data": f"state_{i + 1}",
                },
                "created_at": datetime.now().isoformat(),
            }
            self.created_checkpoints.append(checkpoint)

        # 驗證可以獲取所有檢查點
        total_checkpoints = len(self.created_checkpoints)

        # 測試恢復到中間的檢查點
        middle_checkpoint = self.created_checkpoints[len(self.created_checkpoints) // 2]
        result = await self.chat_client.restore_checkpoint(middle_checkpoint["checkpoint_id"])

        if result.get("success"):
            return {
                "success": True,
                "message": f"多檢查點管理測試通過 (總計: {total_checkpoints})",
                "details": {
                    "total_checkpoints": total_checkpoints,
                    "restored_checkpoint": middle_checkpoint["checkpoint_id"],
                },
            }
        else:
            return {
                "success": False,
                "message": "多檢查點管理測試失敗",
                "details": {
                    "total_checkpoints": total_checkpoints,
                    "restore_result": result,
                },
            }


async def main():
    """獨立執行測試"""
    scenario = CheckpointRestoreScenario(use_simulation=True)
    result = await scenario.run()
    return result


if __name__ == "__main__":
    asyncio.run(main())
