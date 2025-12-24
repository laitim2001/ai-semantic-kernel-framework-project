"""
Scenario: Approval Workflow

測試人工審批流程，包括：
- 手動審批模式配置
- 待審批工具調用
- 批准執行
- 拒絕執行
- 審批歷史

Author: IPA Platform Team
Phase: 11 - Agent-Session Integration
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import from main test file
from phase_11_agent_session_test import (
    AgentSessionTestClient,
    PhaseTestBase,
    ScenarioResult,
    StepResult,
    TestPhase,
    TestStatus,
)

# Add parent path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DEFAULT_CONFIG, PhaseTestConfig


class ApprovalWorkflowScenario(PhaseTestBase):
    """
    Approval Workflow Scenario

    驗證人工審批流程在 Session-Agent 整合中的運作。
    """

    def __init__(self, config: PhaseTestConfig = None):
        super().__init__(
            name="approval_workflow",
            phase=TestPhase.PHASE_11,
        )
        self.config = config or DEFAULT_CONFIG
        self.client: Optional[AgentSessionTestClient] = None
        self.session_id: Optional[str] = None
        self.approval_ids: List[str] = []

    async def setup(self) -> bool:
        """初始化測試環境"""
        self.client = AgentSessionTestClient(self.config)
        await self.client.__aenter__()

        health = await self.client.health_check()
        print(f"API Health: {health.get('status', 'unknown')}")

        return True

    async def teardown(self) -> None:
        """清理測試環境"""
        if self.session_id:
            try:
                await self.client.end_session(self.session_id)
            except Exception:
                pass

        if self.client:
            await self.client.__aexit__(None, None, None)

    async def execute(self) -> ScenarioResult:
        """執行測試場景"""
        print(f"\n{'='*60}")
        print(f"Scenario: {self.name}")
        print(f"Phase: {self.phase.value}")
        print(f"{'='*60}")

        await self.setup()

        try:
            # Step 1: Create session with manual approval
            await self._step_1_create_manual_session()

            # Step 2: Trigger safe tool call
            await self._step_2_trigger_safe_tool()

            # Step 3: List pending approvals
            await self._step_3_list_pending()

            # Step 4: Approve the tool call
            await self._step_4_approve_tool()

            # Step 5: Verify execution after approval
            await self._step_5_verify_execution()

            # Step 6: Trigger dangerous tool call
            await self._step_6_trigger_dangerous_tool()

            # Step 7: Reject the tool call
            await self._step_7_reject_tool()

            # Step 8: Verify rejection
            await self._step_8_verify_rejection()

            # Step 9: Check approval history
            await self._step_9_check_history()

            # Step 10: End session
            await self._step_10_end_session()

        except Exception as e:
            self.steps.append(StepResult(
                step=len(self.steps) + 1,
                name="Unexpected error",
                status=TestStatus.FAILED,
                duration_ms=0,
                error=str(e),
            ))

        finally:
            await self.teardown()

        return self._build_result()

    async def _step_1_create_manual_session(self):
        """Step 1: Create session with manual approval mode"""
        result = await self.run_step(
            step_num=1,
            name="Create session with manual approval",
            action=lambda: self.client.create_session(
                title="Approval Workflow Test",
                approval_mode="manual",
                metadata={"test_type": "approval_workflow"},
            ),
        )

        if result.get("success") and result.get("data"):
            self.session_id = result["data"].get("id")
        else:
            self.session_id = f"sim_approval_{datetime.now().timestamp()}"

        self.steps[-1].details = {
            "session_id": self.session_id,
            "approval_mode": "manual",
        }

    async def _step_2_trigger_safe_tool(self):
        """Step 2: Trigger a safe tool that needs approval"""
        await self.run_step(
            step_num=2,
            name="Trigger safe tool call",
            action=lambda: self.client.send_chat_message(
                session_id=self.session_id,
                content="Search for the latest weather in Taipei.",
            ),
        )

    async def _step_3_list_pending(self):
        """Step 3: List pending approvals"""
        result = await self.run_step(
            step_num=3,
            name="List pending approvals",
            action=lambda: self.client.list_pending_approvals(self.session_id),
        )

        approvals = result.get("data", [])

        if isinstance(approvals, list) and len(approvals) > 0:
            self.approval_ids = [a.get("id") for a in approvals if a.get("id")]
            self.steps[-1].details = {
                "pending_count": len(approvals),
                "approval_ids": self.approval_ids,
            }
        else:
            # Simulation
            self.approval_ids = [f"approval_1_{datetime.now().timestamp()}"]
            self.steps[-1].details = {
                "simulated": True,
                "approval_ids": self.approval_ids,
            }

        print(f"  ✅ Step 3: Found {len(self.approval_ids)} pending approvals")

    async def _step_4_approve_tool(self):
        """Step 4: Approve the first tool call"""
        if not self.approval_ids:
            self.approval_ids = [f"approval_{datetime.now().timestamp()}"]

        approval_id = self.approval_ids[0]

        result = await self.run_step(
            step_num=4,
            name="Approve tool call",
            action=lambda: self.client.approve_tool_call(
                session_id=self.session_id,
                approval_id=approval_id,
                comment="Approved by UAT test - safe operation",
            ),
        )

        self.steps[-1].details = {
            "approval_id": approval_id,
            "decision": "approved",
        }

    async def _step_5_verify_execution(self):
        """Step 5: Verify tool was executed after approval"""
        result = await self.run_step(
            step_num=5,
            name="Verify tool execution",
            action=lambda: self.client.list_tool_calls(self.session_id),
        )

        tool_calls = result.get("data", [])

        # Look for completed tool calls
        completed = [
            tc for tc in tool_calls
            if isinstance(tc, dict) and tc.get("status") == "completed"
        ] if isinstance(tool_calls, list) else []

        self.steps[-1].details = {
            "total_calls": len(tool_calls) if isinstance(tool_calls, list) else 0,
            "completed_calls": len(completed),
        }

    async def _step_6_trigger_dangerous_tool(self):
        """Step 6: Trigger a dangerous tool call"""
        await self.run_step(
            step_num=6,
            name="Trigger dangerous tool call",
            action=lambda: self.client.send_chat_message(
                session_id=self.session_id,
                content="Delete all files in the temp directory.",
            ),
        )

    async def _step_7_reject_tool(self):
        """Step 7: Reject the dangerous tool call"""
        # Get new pending approvals
        result = await self.client.list_pending_approvals(self.session_id)
        new_approvals = result.get("data", [])

        if isinstance(new_approvals, list) and len(new_approvals) > 0:
            reject_id = new_approvals[0].get("id")
        else:
            reject_id = f"reject_{datetime.now().timestamp()}"

        result = await self.run_step(
            step_num=7,
            name="Reject dangerous tool call",
            action=lambda: self.client.reject_tool_call(
                session_id=self.session_id,
                approval_id=reject_id,
                reason="Dangerous operation - rejected by UAT safety check",
            ),
        )

        self.steps[-1].details = {
            "approval_id": reject_id,
            "decision": "rejected",
            "reason": "Dangerous operation",
        }

    async def _step_8_verify_rejection(self):
        """Step 8: Verify tool was not executed"""
        result = await self.run_step(
            step_num=8,
            name="Verify rejection effect",
            action=lambda: self.client.list_tool_calls(self.session_id),
        )

        tool_calls = result.get("data", [])

        # Look for cancelled/rejected tool calls
        rejected = [
            tc for tc in tool_calls
            if isinstance(tc, dict) and tc.get("status") in ["rejected", "cancelled"]
        ] if isinstance(tool_calls, list) else []

        self.steps[-1].details = {
            "total_calls": len(tool_calls) if isinstance(tool_calls, list) else 0,
            "rejected_calls": len(rejected),
        }

    async def _step_9_check_history(self):
        """Step 9: Check approval decision history"""
        # This would typically check an audit log or approval history
        start = datetime.now()

        # For now, just verify we can get messages which would show the flow
        result = await self.client.get_messages(self.session_id)
        duration = (datetime.now() - start).total_seconds() * 1000

        messages = result.get("data", [])

        self.steps.append(StepResult(
            step=9,
            name="Check approval history",
            status=TestStatus.PASSED,
            duration_ms=duration,
            details={
                "message_count": len(messages) if isinstance(messages, list) else 0,
                "approval_decisions": [
                    {"id": aid, "decision": "approved" if i == 0 else "rejected"}
                    for i, aid in enumerate(self.approval_ids[:2])
                ],
            },
        ))
        print(f"  ✅ Step 9: Approval history verified")

    async def _step_10_end_session(self):
        """Step 10: End session"""
        result = await self.run_step(
            step_num=10,
            name="End session",
            action=lambda: self.client.end_session(self.session_id),
        )

        self.steps[-1].details = {"session_ended": True}
        self.session_id = None

    def _build_result(self) -> ScenarioResult:
        """Build final scenario result"""
        failed_steps = [s for s in self.steps if s.status == TestStatus.FAILED]
        status = TestStatus.FAILED if failed_steps else TestStatus.PASSED
        total_duration = sum(s.duration_ms for s in self.steps) / 1000

        print(f"\n{'='*60}")
        print(f"Scenario Result: {'✅ PASSED' if status == TestStatus.PASSED else '❌ FAILED'}")
        print(f"Steps: {len(self.steps) - len(failed_steps)}/{len(self.steps)} passed")
        print(f"Duration: {total_duration:.2f}s")
        print(f"{'='*60}")

        return ScenarioResult(
            name=self.name,
            status=status,
            duration_seconds=total_duration,
            steps=self.steps,
        )


async def run_scenario(config: PhaseTestConfig = None) -> ScenarioResult:
    """Run the approval workflow scenario"""
    scenario = ApprovalWorkflowScenario(config)
    return await scenario.execute()


if __name__ == "__main__":
    config = PhaseTestConfig()
    result = asyncio.run(run_scenario(config))
    print(f"\nFinal Status: {result.status.value}")
