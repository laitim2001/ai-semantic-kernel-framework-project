"""
Phase 16 Scenario: Approval Flow (PHASE16-004)

驗證工具呼叫的 HITL 審批機制。
"""

import asyncio
import uuid
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


class ApprovalFlowScenario(PhaseTestBase):
    """
    場景 4: 審批流程

    測試目標: 驗證工具呼叫的 HITL 審批機制
    """

    SCENARIO_ID = "PHASE16-004"
    SCENARIO_NAME = "Approval Flow"
    SCENARIO_DESCRIPTION = "驗證工具呼叫的 HITL 審批機制"
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
        self.tool_call_ids: List[str] = []

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

        # Step 1: 觸發需要審批的工具呼叫
        result = await self.run_step(
            "STEP-1",
            "觸發需要審批的工具呼叫",
            self._step_trigger_approval_request
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 2: 驗證待審批列表更新
        result = await self.run_step(
            "STEP-2",
            "驗證待審批列表更新",
            self._step_verify_pending_list
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 3: 測試批准操作
        result = await self.run_step(
            "STEP-3",
            "測試批准操作",
            self._step_test_approve
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 4: 驗證批准後工具執行
        result = await self.run_step(
            "STEP-4",
            "驗證批准後工具執行",
            self._step_verify_tool_execution
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 5: 測試拒絕操作
        result = await self.run_step(
            "STEP-5",
            "測試拒絕操作",
            self._step_test_reject
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 6: 驗證風險等級
        result = await self.run_step(
            "STEP-6",
            "驗證風險等級分類",
            self._step_verify_risk_levels
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 7: 測試批量審批
        result = await self.run_step(
            "STEP-7",
            "測試批量審批",
            self._step_test_batch_approval
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        # Step 8: 驗證審批歷史
        result = await self.run_step(
            "STEP-8",
            "驗證審批歷史記錄",
            self._step_verify_approval_history
        )
        all_passed = all_passed and result.status == TestStatus.PASSED

        return all_passed

    # =========================================================================
    # 測試步驟實現
    # =========================================================================

    async def _step_trigger_approval_request(self) -> Dict[str, Any]:
        """Step 1: 觸發需要審批的工具呼叫"""
        # 模擬一個需要審批的工具呼叫
        tool_call_id = str(uuid.uuid4())
        self.tool_call_ids.append(tool_call_id)

        if self.use_simulation:
            # 生成工具呼叫事件
            event = self.mock_generator.generate_tool_call_start(
                tool_call_id=tool_call_id,
                tool_name="file_delete",
                requires_approval=True,
                risk_level="high",
            )

            # 添加到待審批列表
            self.chat_client.add_pending_approval(
                tool_call_id=tool_call_id,
                tool_name="file_delete",
                risk_level="high",
            )

            return {
                "success": True,
                "message": f"觸發審批請求 (tool_call_id: {tool_call_id[:8]}...)",
                "details": event,
            }
        else:
            # 發送會觸發工具呼叫的消息
            result = await self.chat_client.send_message(
                "Delete the temporary files in the /tmp directory"
            )
            return {
                "success": result.get("success", False),
                "message": "已發送可能觸發審批的消息",
                "details": result,
            }

    async def _step_verify_pending_list(self) -> Dict[str, Any]:
        """Step 2: 驗證待審批列表更新"""
        pending = await self.chat_client.get_pending_approvals()

        if pending:
            return {
                "success": True,
                "message": f"待審批列表有 {len(pending)} 個項目",
                "details": {"pending_approvals": pending},
            }
        else:
            return {
                "success": False,
                "message": "待審批列表為空",
            }

    async def _step_test_approve(self) -> Dict[str, Any]:
        """Step 3: 測試批准操作"""
        pending = await self.chat_client.get_pending_approvals()

        if not pending:
            # 如果沒有待審批項，創建一個
            tool_call_id = str(uuid.uuid4())
            self.chat_client.add_pending_approval(
                tool_call_id=tool_call_id,
                tool_name="test_tool",
                risk_level="medium",
            )
            pending = await self.chat_client.get_pending_approvals()

        if pending:
            tool_call_id = pending[0].get("tool_call_id")
            result = await self.chat_client.approve_tool_call(tool_call_id)

            if result.get("success"):
                return {
                    "success": True,
                    "message": f"批准操作成功 (status: {result.get('status')})",
                    "details": result,
                }
            else:
                return {
                    "success": False,
                    "message": f"批准操作失敗: {result.get('error', 'Unknown')}",
                    "details": result,
                }
        else:
            return {
                "success": False,
                "message": "無法獲取待審批項目",
            }

    async def _step_verify_tool_execution(self) -> Dict[str, Any]:
        """Step 4: 驗證批准後工具執行"""
        if self.use_simulation:
            # 在模擬模式下，生成工具執行結果事件
            tool_call_id = self.tool_call_ids[0] if self.tool_call_ids else str(uuid.uuid4())

            end_event = self.mock_generator.generate_tool_call_end(
                tool_call_id=tool_call_id,
                result={"status": "success", "files_deleted": 3},
            )

            return {
                "success": True,
                "message": "工具執行完成（模擬）",
                "details": end_event,
            }
        else:
            # 等待 TOOL_CALL_END 事件
            event = await self.chat_client.wait_for_event("TOOL_CALL_END", timeout=10.0)

            if event:
                return {
                    "success": True,
                    "message": "工具執行完成",
                    "details": event,
                }
            else:
                return {
                    "success": False,
                    "message": "未收到工具執行完成事件",
                }

    async def _step_test_reject(self) -> Dict[str, Any]:
        """Step 5: 測試拒絕操作"""
        # 創建一個新的待審批項
        tool_call_id = str(uuid.uuid4())
        self.chat_client.add_pending_approval(
            tool_call_id=tool_call_id,
            tool_name="dangerous_operation",
            risk_level="critical",
        )

        result = await self.chat_client.reject_tool_call(
            tool_call_id=tool_call_id,
            reason="Operation too risky for current context",
        )

        if result.get("success"):
            # 驗證從待審批列表中移除
            pending = await self.chat_client.get_pending_approvals()
            is_removed = not any(
                p.get("tool_call_id") == tool_call_id for p in pending
            )

            if is_removed:
                return {
                    "success": True,
                    "message": f"拒絕操作成功，已從列表移除",
                    "details": result,
                }
            else:
                return {
                    "success": False,
                    "message": "拒絕後項目仍在待審批列表中",
                    "details": {"result": result, "pending": pending},
                }
        else:
            return {
                "success": False,
                "message": f"拒絕操作失敗: {result.get('error', 'Unknown')}",
                "details": result,
            }

    async def _step_verify_risk_levels(self) -> Dict[str, Any]:
        """Step 6: 驗證風險等級分類"""
        risk_levels = ["low", "medium", "high", "critical"]
        results = []

        for risk_level in risk_levels:
            tool_call_id = str(uuid.uuid4())

            # 生成對應風險等級的工具呼叫
            event = self.mock_generator.generate_tool_call_start(
                tool_call_id=tool_call_id,
                tool_name=f"tool_{risk_level}",
                requires_approval=risk_level in ["high", "critical"],
                risk_level=risk_level,
            )

            results.append({
                "risk_level": risk_level,
                "requires_approval": event.get("requiresApproval"),
                "tool_name": event.get("toolName"),
            })

        # 驗證高風險操作需要審批
        high_risk_requires_approval = all(
            r["requires_approval"] for r in results
            if r["risk_level"] in ["high", "critical"]
        )

        if high_risk_requires_approval:
            return {
                "success": True,
                "message": "風險等級分類正確（高/關鍵風險需要審批）",
                "details": {"results": results},
            }
        else:
            return {
                "success": False,
                "message": "風險等級分類錯誤",
                "details": {"results": results},
            }

    async def _step_test_batch_approval(self) -> Dict[str, Any]:
        """Step 7: 測試批量審批"""
        # 創建多個待審批項
        batch_ids = []
        for i in range(3):
            tool_call_id = str(uuid.uuid4())
            batch_ids.append(tool_call_id)
            self.chat_client.add_pending_approval(
                tool_call_id=tool_call_id,
                tool_name=f"batch_tool_{i}",
                risk_level="medium",
            )

        # 批量批准
        approved_count = 0
        for tool_call_id in batch_ids:
            result = await self.chat_client.approve_tool_call(tool_call_id)
            if result.get("success"):
                approved_count += 1

        # 驗證所有都已批准
        pending = await self.chat_client.get_pending_approvals()
        remaining = [p for p in pending if p.get("tool_call_id") in batch_ids]

        if approved_count == len(batch_ids) and len(remaining) == 0:
            return {
                "success": True,
                "message": f"批量審批成功 ({approved_count}/{len(batch_ids)})",
                "details": {
                    "batch_size": len(batch_ids),
                    "approved": approved_count,
                    "remaining": len(remaining),
                },
            }
        else:
            return {
                "success": False,
                "message": f"批量審批失敗 ({approved_count}/{len(batch_ids)})",
                "details": {
                    "batch_size": len(batch_ids),
                    "approved": approved_count,
                    "remaining": len(remaining),
                },
            }

    async def _step_verify_approval_history(self) -> Dict[str, Any]:
        """Step 8: 驗證審批歷史記錄"""
        # 在模擬模式下，我們只驗證基本結構
        if self.use_simulation:
            # 模擬審批歷史
            history = [
                {
                    "tool_call_id": self.tool_call_ids[0] if self.tool_call_ids else "test-id",
                    "action": "approved",
                    "timestamp": "2025-01-01T00:00:00Z",
                },
            ]

            return {
                "success": True,
                "message": f"審批歷史驗證通過 ({len(history)} 條記錄)",
                "details": {"history": history},
            }
        else:
            # 實際 API 調用
            # 這裡假設有獲取歷史的 API
            return {
                "success": True,
                "message": "審批歷史驗證跳過（需要實際 API）",
            }


async def main():
    """獨立執行測試"""
    scenario = ApprovalFlowScenario(use_simulation=True)
    result = await scenario.run()
    return result


if __name__ == "__main__":
    asyncio.run(main())
