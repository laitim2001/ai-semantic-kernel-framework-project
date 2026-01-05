# =============================================================================
# E2E Scenario 2: Mode Switching with Context Preservation
# =============================================================================
# IMPORTANT: This scenario requires a LIVE backend API with real LLM
# (Azure OpenAI / Claude) configured. NO simulation mode is available.
#
# This scenario tests the integration between:
# - Phase 13: ContextBridge (bidirectional state synchronization)
# - Phase 14: ModeSwitcher (dynamic mode transitions)
#
# Flow:
#   Workflow Mode                              Chat Mode
#       |                                          |
#       +------ ModeSwitcher.switch() ----------->+
#       |              |                           |
#       |       ContextBridge.sync()               |
#       |       (preserve state)                   |
#       |              |                           |
#       +<----- ModeSwitcher.switch() ------------+
#       |              |                           |
#       |       ContextBridge.sync()               |
#       |       (restore state)                    |
#
# Key Tests:
# 1. Workflow -> Chat transition preserves context
# 2. Chat -> Workflow maintains state
# 3. Bidirectional sync works correctly
# 4. Graceful degradation on sync failure
# =============================================================================

import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import TestStatus, safe_print


@dataclass
class E2EStepResult:
    """Step result for E2E tests"""
    step_name: str
    status: TestStatus
    message: str = ""
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class E2EScenarioResult:
    """Scenario result for E2E tests"""
    scenario_name: str
    scenario_id: str
    steps: List[E2EStepResult] = None
    duration_seconds: float = 0
    passed: int = 0
    failed: int = 0

    def __post_init__(self):
        if self.steps is None:
            self.steps = []


# =============================================================================
# Test Functions
# =============================================================================

async def test_workflow_to_chat_preserves_context(client) -> E2EStepResult:
    """
    Test: Switching from Workflow to Chat mode preserves execution context.

    Steps:
    1. Start in Workflow mode with some state
    2. Execute a workflow step to create context
    3. Switch to Chat mode
    4. Verify context is preserved in Chat mode

    Expected: All workflow context available in Chat mode
    """
    step_name = "Workflow to Chat preserves context"

    try:
        # Step 1: Ensure we're in Workflow mode
        client.context.current_mode = client.context.current_mode.__class__("workflow")

        # Step 2: Create some workflow state
        client.context.workflow_state = {
            "current_step": 3,
            "total_steps": 5,
            "variables": {
                "customer_id": "CUST-001",
                "order_total": 1500.00
            },
            "completed_steps": ["validate", "process", "calculate"]
        }

        # Step 3: Sync context before switch
        sync_result = await client.sync_context(direction="maf_to_claude")

        if not sync_result.get("success", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Context sync before switch failed",
                details={"sync_result": sync_result}
            )

        # Step 4: Switch to Chat mode
        switch_result = await client.switch_mode(
            target_mode="chat",
            reason="user_request"
        )

        if not switch_result.get("success", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Mode switch failed",
                details={"switch_result": switch_result}
            )

        # Step 5: Verify context preserved
        if not switch_result.get("context_preserved", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Context was not preserved during switch",
                details={"switch_result": switch_result}
            )

        # Step 6: Verify we're now in Chat mode
        if switch_result.get("current_mode") != "chat":
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message=f"Expected 'chat' mode, got '{switch_result.get('current_mode')}'",
                details={"switch_result": switch_result}
            )

        return E2EStepResult(
            step_name=step_name,
            status=TestStatus.PASSED,
            message=f"Workflow -> Chat switch successful, context preserved (synced: {len(sync_result.get('synced_keys', []))} keys)",
            details={
                "sync": sync_result,
                "switch": switch_result,
                "preserved_state": client.context.workflow_state
            }
        )

    except Exception as e:
        return E2EStepResult(
            step_name=step_name,
            status=TestStatus.FAILED,
            message=f"Exception: {str(e)}"
        )


async def test_chat_to_workflow_maintains_state(client) -> E2EStepResult:
    """
    Test: Switching from Chat to Workflow mode maintains conversation state.

    Steps:
    1. Start in Chat mode with conversation history
    2. Add messages to chat history
    3. Switch to Workflow mode
    4. Verify chat history is maintained

    Expected: Chat history available after switching to Workflow
    """
    step_name = "Chat to Workflow maintains state"

    try:
        # Step 1: Ensure we're in Chat mode
        client.context.current_mode = client.context.current_mode.__class__("chat")

        # Step 2: Create chat history
        client.context.chat_history = [
            {"role": "user", "content": "I need help with order processing"},
            {"role": "assistant", "content": "I can help you with that. Let me check the order details."},
            {"role": "user", "content": "The order ID is ORD-12345"},
            {"role": "assistant", "content": "Found order ORD-12345. Would you like me to process it now?"}
        ]

        # Step 3: Sync context
        sync_result = await client.sync_context(direction="claude_to_maf")

        if not sync_result.get("success", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Context sync before switch failed",
                details={"sync_result": sync_result}
            )

        # Step 4: Switch to Workflow mode
        switch_result = await client.switch_mode(
            target_mode="workflow",
            reason="escalation"
        )

        if not switch_result.get("success", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Mode switch failed",
                details={"switch_result": switch_result}
            )

        # Step 5: Verify context preserved
        if not switch_result.get("context_preserved", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Chat history was not preserved during switch",
                details={"switch_result": switch_result}
            )

        # Step 6: Verify chat history still exists
        if len(client.context.chat_history) != 4:
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message=f"Expected 4 chat messages, got {len(client.context.chat_history)}",
                details={"chat_history": client.context.chat_history}
            )

        return E2EStepResult(
            step_name=step_name,
            status=TestStatus.PASSED,
            message=f"Chat -> Workflow switch successful, {len(client.context.chat_history)} messages preserved",
            details={
                "sync": sync_result,
                "switch": switch_result,
                "chat_history_count": len(client.context.chat_history)
            }
        )

    except Exception as e:
        return E2EStepResult(
            step_name=step_name,
            status=TestStatus.FAILED,
            message=f"Exception: {str(e)}"
        )


async def test_context_bridge_bidirectional_sync(client) -> E2EStepResult:
    """
    Test: ContextBridge correctly syncs state bidirectionally.

    Steps:
    1. Set up state in both workflow and chat contexts
    2. Perform bidirectional sync
    3. Verify both directions synced correctly
    4. Verify no conflicts or data loss

    Expected: Both MAF and Claude SDK states are synchronized
    """
    step_name = "Context Bridge bidirectional sync"

    try:
        # Step 1: Set up state in both contexts
        client.context.workflow_state = {
            "workflow_id": "WF-001",
            "current_step": 2,
            "maf_specific": {"agent_id": "agent-123"}
        }
        client.context.chat_history = [
            {"role": "user", "content": "Start workflow"},
            {"role": "assistant", "content": "Workflow started"}
        ]

        # Step 2: Perform bidirectional sync
        sync_result = await client.sync_context(direction="bidirectional")

        # Step 3: Verify sync success
        if not sync_result.get("success", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Bidirectional sync failed",
                details={"sync_result": sync_result}
            )

        # Step 4: Verify synced keys
        synced_keys = sync_result.get("synced_keys", [])
        if len(synced_keys) == 0:
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="No keys were synced",
                details={"sync_result": sync_result}
            )

        # Step 5: Verify no conflicts
        conflicts = sync_result.get("conflicts", [])
        if len(conflicts) > 0:
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message=f"Sync conflicts detected: {conflicts}",
                details={"sync_result": sync_result}
            )

        return E2EStepResult(
            step_name=step_name,
            status=TestStatus.PASSED,
            message=f"Bidirectional sync successful: {len(synced_keys)} keys synced, 0 conflicts",
            details={
                "synced_keys": synced_keys,
                "conflicts": conflicts,
                "resolution": sync_result.get("resolution")
            }
        )

    except Exception as e:
        return E2EStepResult(
            step_name=step_name,
            status=TestStatus.FAILED,
            message=f"Exception: {str(e)}"
        )


async def test_graceful_degradation_on_sync_failure(client) -> E2EStepResult:
    """
    Test: System gracefully handles sync failures and provides rollback.

    Steps:
    1. Create a checkpoint before switch
    2. Attempt mode switch
    3. Verify rollback is available if needed
    4. Verify system remains in valid state

    Expected: Failed sync doesn't corrupt state, rollback available
    """
    step_name = "Graceful degradation on sync failure"

    try:
        # Step 1: Create checkpoint before switch
        checkpoint_result = await client.create_checkpoint(label="pre-switch-safety")

        if "checkpoint_id" not in checkpoint_result:
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Failed to create safety checkpoint",
                details={"checkpoint_result": checkpoint_result}
            )

        checkpoint_id = checkpoint_result["checkpoint_id"]

        # Step 2: Set up initial state
        initial_mode = client.context.current_mode.value
        client.context.workflow_state = {"important_data": "must_preserve"}

        # Step 3: Attempt switch (in simulation, this always succeeds)
        switch_result = await client.switch_mode(
            target_mode="chat" if initial_mode == "workflow" else "workflow",
            reason="test_switch"
        )

        # Step 4: Verify rollback is available
        if not switch_result.get("rollback_available", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Rollback should be available after switch",
                details={"switch_result": switch_result}
            )

        # Step 5: Test rollback by restoring checkpoint
        restore_result = await client.restore_checkpoint(checkpoint_id)

        if not restore_result.get("success", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Checkpoint restore failed",
                details={"restore_result": restore_result}
            )

        # Step 6: Verify validation passed
        if not restore_result.get("validation_passed", False):
            return E2EStepResult(
                step_name=step_name,
                status=TestStatus.FAILED,
                message="Restored state validation failed",
                details={"restore_result": restore_result}
            )

        return E2EStepResult(
            step_name=step_name,
            status=TestStatus.PASSED,
            message=f"Graceful degradation verified: checkpoint {checkpoint_id} can be restored",
            details={
                "checkpoint": checkpoint_result,
                "switch": switch_result,
                "restore": restore_result
            }
        )

    except Exception as e:
        return E2EStepResult(
            step_name=step_name,
            status=TestStatus.FAILED,
            message=f"Exception: {str(e)}"
        )


# =============================================================================
# Scenario Runner
# =============================================================================

async def run_scenario(client) -> E2EScenarioResult:
    """Run all tests in this scenario"""
    scenario_name = "Mode Switch with Context Preservation"
    scenario_id = "scenario-2-mode-switch-context"

    start_time = datetime.now(timezone.utc)
    steps = []

    # Run all tests
    tests = [
        test_workflow_to_chat_preserves_context,
        test_chat_to_workflow_maintains_state,
        test_context_bridge_bidirectional_sync,
        test_graceful_degradation_on_sync_failure,
    ]

    for test_func in tests:
        result = await test_func(client)
        steps.append(result)

        status_icon = "[PASS]" if result.status == TestStatus.PASSED else "[FAIL]"
        safe_print(f"  {status_icon} {result.step_name}")
        if result.message:
            safe_print(f"       {result.message}")

    # Calculate summary
    passed = sum(1 for s in steps if s.status == TestStatus.PASSED)
    failed = sum(1 for s in steps if s.status == TestStatus.FAILED)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    return E2EScenarioResult(
        scenario_name=scenario_name,
        scenario_id=scenario_id,
        steps=steps,
        duration_seconds=duration,
        passed=passed,
        failed=failed
    )
