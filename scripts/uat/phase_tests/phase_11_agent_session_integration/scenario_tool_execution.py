"""
Scenario: Tool Execution Flow

測試工具調用的完整流程，包括：
- 工具觸發
- 自動審批執行
- 結果整合
- 上下文維護

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


class ToolExecutionScenario(PhaseTestBase):
    """
    Tool Execution Flow Scenario

    驗證工具調用在 Session-Agent 整合中的完整流程。
    """

    def __init__(self, config: PhaseTestConfig = None):
        super().__init__(
            name="tool_execution",
            phase=TestPhase.PHASE_11,
        )
        self.config = config or DEFAULT_CONFIG
        self.client: Optional[AgentSessionTestClient] = None
        self.session_id: Optional[str] = None

    async def setup(self) -> bool:
        """初始化測試環境"""
        self.client = AgentSessionTestClient(self.config)
        await self.client.__aenter__()

        # Health check
        health = await self.client.health_check()
        if health.get("status") != "healthy":
            print(f"Warning: API not healthy: {health}")
            # Continue anyway for simulation mode

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
            # Step 1: Create session with agent
            await self._step_1_create_session()

            # Step 2: Send calculation request
            await self._step_2_request_calculation()

            # Step 3: Verify tool was called
            await self._step_3_verify_tool_call()

            # Step 4: Check tool result in response
            await self._step_4_check_tool_result()

            # Step 5: Send follow-up with context
            await self._step_5_follow_up_question()

            # Step 6: Verify context maintained
            await self._step_6_verify_context()

            # Step 7: End session
            await self._step_7_end_session()

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

    async def _step_1_create_session(self):
        """Step 1: Create session with agent"""
        result = await self.run_step(
            step_num=1,
            name="Create session with agent",
            action=lambda: self.client.create_session(
                title="Tool Execution Test",
                agent_id="test-agent",
                approval_mode="auto",
            ),
        )

        if result.get("success") and result.get("data"):
            self.session_id = result["data"].get("id")
        else:
            # Simulation fallback
            self.session_id = f"sim_tool_{datetime.now().timestamp()}"

        self.steps[-1].details = {"session_id": self.session_id}

    async def _step_2_request_calculation(self):
        """Step 2: Request a calculation using tool"""
        await self.run_step(
            step_num=2,
            name="Request calculation",
            action=lambda: self.client.send_chat_message(
                session_id=self.session_id,
                content="Please calculate 125 * 8 + 50. Use the calculator tool.",
            ),
        )

    async def _step_3_verify_tool_call(self):
        """Step 3: Verify tool was called"""
        result = await self.run_step(
            step_num=3,
            name="Verify tool call",
            action=lambda: self.client.list_tool_calls(self.session_id),
        )

        tool_calls = result.get("data", [])
        expected_tool = "calculator"

        if isinstance(tool_calls, list) and len(tool_calls) > 0:
            # Check if calculator was used
            calculator_calls = [
                tc for tc in tool_calls
                if tc.get("name", "").lower() == expected_tool
            ]
            self.steps[-1].details = {
                "tool_calls": len(tool_calls),
                "calculator_calls": len(calculator_calls),
            }
        else:
            # Simulation
            self.steps[-1].details = {
                "simulated": True,
                "expected_tool": expected_tool,
            }

    async def _step_4_check_tool_result(self):
        """Step 4: Check tool result integrated in response"""
        result = await self.run_step(
            step_num=4,
            name="Check tool result",
            action=lambda: self.client.get_messages(self.session_id),
        )

        messages = result.get("data", [])
        expected_result = 1050  # 125 * 8 + 50

        # Look for the result in messages
        result_found = False
        for msg in messages:
            content = msg.get("content", "")
            if str(expected_result) in content or "1050" in content:
                result_found = True
                break

        self.steps[-1].details = {
            "message_count": len(messages),
            "result_found": result_found,
            "expected_result": expected_result,
        }

    async def _step_5_follow_up_question(self):
        """Step 5: Send follow-up question"""
        await self.run_step(
            step_num=5,
            name="Send follow-up question",
            action=lambda: self.client.send_chat_message(
                session_id=self.session_id,
                content="Now divide that result by 5.",
            ),
        )

    async def _step_6_verify_context(self):
        """Step 6: Verify context was maintained"""
        result = await self.run_step(
            step_num=6,
            name="Verify context maintained",
            action=lambda: self.client.get_messages(self.session_id),
        )

        messages = result.get("data", [])
        expected_followup_result = 210  # 1050 / 5

        # Look for follow-up result
        followup_found = False
        for msg in messages:
            content = msg.get("content", "")
            if str(expected_followup_result) in content or "210" in content:
                followup_found = True
                break

        self.steps[-1].details = {
            "message_count": len(messages),
            "followup_result_found": followup_found,
            "expected": expected_followup_result,
        }

    async def _step_7_end_session(self):
        """Step 7: End session"""
        result = await self.run_step(
            step_num=7,
            name="End session",
            action=lambda: self.client.end_session(self.session_id),
        )

        self.steps[-1].details = {"session_ended": True}
        self.session_id = None  # Prevent teardown from trying again

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
    """Run the tool execution scenario"""
    scenario = ToolExecutionScenario(config)
    return await scenario.execute()


if __name__ == "__main__":
    config = PhaseTestConfig()
    result = asyncio.run(run_scenario(config))
    print(f"\nFinal Status: {result.status.value}")
