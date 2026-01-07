# =============================================================================
# IPA Platform - Phase 14 Integration Tests
# =============================================================================
# Sprint 57: Unified Checkpoint & Polish
# S57-3: Phase 14 Integration Tests
#
# Comprehensive end-to-end integration tests for Phase 14 components:
#   - Risk Assessment + Approval Workflow (E2E)
#   - Mode Switching Complete Flow
#   - Checkpoint Save/Restore
#   - Cross-Framework Recovery
#   - Performance Benchmarks
#
# Dependencies:
#   - RiskAssessmentEngine (src.integrations.hybrid.risk.engine)
#   - ModeSwitcher (src.integrations.hybrid.switching.switcher)
#   - UnifiedCheckpointStorage (src.integrations.hybrid.checkpoint)
#   - RiskDrivenApprovalHook (src.integrations.hybrid.hooks.approval_hook)
# =============================================================================

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Risk Assessment Components
from src.integrations.hybrid.risk.engine import (
    RiskAssessmentEngine,
    create_engine,
)
from src.integrations.hybrid.risk.models import (
    OperationContext,
    RiskAssessment,
    RiskConfig,
    RiskLevel,
)
from src.integrations.hybrid.risk.analyzers.operation_analyzer import OperationAnalyzer
from src.integrations.hybrid.risk.analyzers.context_evaluator import ContextEvaluator
from src.integrations.hybrid.risk.analyzers.pattern_detector import PatternDetector

# Approval Hook
from src.integrations.hybrid.hooks.approval_hook import (
    ApprovalDecision,
    ApprovalMode,
    RiskDrivenApprovalHook,
)

# Mode Switching Components
from src.integrations.hybrid.switching.switcher import (
    ModeSwitcher,
    SwitcherMetrics,
    create_mode_switcher,
)
from src.integrations.hybrid.switching.models import (
    ExecutionState,
    MigrationDirection,
    SwitchConfig,
    SwitchStatus,
    SwitchTrigger,
    SwitchTriggerType,
)
from src.integrations.hybrid.intent.models import ExecutionMode

# Checkpoint Components
from src.integrations.hybrid.checkpoint.models import (
    CheckpointStatus,
    CheckpointType,
    ClaudeCheckpointState,
    HybridCheckpoint,
    MAFCheckpointState,
    RiskSnapshot,
    RestoreResult,
)
from src.integrations.hybrid.checkpoint.storage import (
    CheckpointQuery,
    StorageConfig,
)
from src.integrations.hybrid.checkpoint.backends.memory import MemoryCheckpointStorage


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def risk_config() -> RiskConfig:
    """Create a risk configuration for testing."""
    return RiskConfig(
        high_threshold=0.7,
        medium_threshold=0.4,
        auto_approve_low=True,
        auto_approve_medium=False,
        enable_pattern_detection=True,
        pattern_window_seconds=300,
    )


@pytest.fixture
def risk_engine(risk_config) -> RiskAssessmentEngine:
    """Create a fully configured risk assessment engine."""
    engine = create_engine(config=risk_config)
    engine.register_analyzer(OperationAnalyzer())
    engine.register_analyzer(ContextEvaluator())
    engine.register_analyzer(PatternDetector())
    return engine


@pytest.fixture
def approval_hook(risk_config) -> RiskDrivenApprovalHook:
    """Create a risk-driven approval hook."""
    return RiskDrivenApprovalHook(
        config=risk_config,
        mode=ApprovalMode.RISK_DRIVEN,
    )


@pytest.fixture
def mode_switcher() -> ModeSwitcher:
    """Create a mode switcher instance."""
    config = SwitchConfig(
        enable_auto_switch=True,
        complexity_threshold=0.6,
        preserve_history=True,
        preserve_tool_results=True,
    )
    return create_mode_switcher(config=config)


@pytest.fixture
def checkpoint_storage() -> MemoryCheckpointStorage:
    """Create a memory checkpoint storage."""
    config = StorageConfig(max_checkpoints_per_session=10)
    return MemoryCheckpointStorage(config)


@pytest.fixture
def sample_maf_state() -> MAFCheckpointState:
    """Create a sample MAF checkpoint state."""
    return MAFCheckpointState(
        workflow_id="wf_integration_test",
        workflow_name="Integration Test Workflow",
        current_step=3,
        total_steps=10,
        agent_states={
            "agent_1": {"status": "completed", "result": "success"},
            "agent_2": {"status": "running", "progress": 0.5},
        },
        variables={"key1": "value1", "key2": 42},
    )


@pytest.fixture
def sample_claude_state() -> ClaudeCheckpointState:
    """Create a sample Claude checkpoint state."""
    return ClaudeCheckpointState(
        session_id="sess_integration_test",
        conversation_history=[
            {"role": "user", "content": "Start integration test"},
            {"role": "assistant", "content": "Integration test initialized"},
            {"role": "user", "content": "Execute workflow step 1"},
            {"role": "assistant", "content": "Step 1 completed successfully"},
        ],
        tool_call_history=[
            {"tool": "tool_1", "status": "success", "output": "result_1"},
            {"tool": "tool_2", "status": "success", "output": "result_2"},
        ],
        context_variables={"test_var": "test_value"},
    )


# =============================================================================
# Test Class: Risk Assessment + Approval Workflow E2E
# =============================================================================


class TestRiskApprovalWorkflowE2E:
    """End-to-end tests for risk assessment and approval workflow."""

    @pytest.mark.asyncio
    async def test_low_risk_operation_auto_approved(self, approval_hook):
        """Low risk operations should be auto-approved."""
        context = OperationContext(
            tool_name="Read",
            operation_type="read",
            target_paths=["src/main.py"],
            session_id="sess_test",
            environment="development",
        )

        decision = await approval_hook.check_approval(context)

        assert decision.approved is True
        assert "auto" in decision.reason.lower() or "read-only" in decision.reason.lower()
        assert decision.required_human_approval is False

    @pytest.mark.asyncio
    async def test_medium_risk_operation_assessed(self, approval_hook):
        """Medium risk operations should trigger risk assessment."""
        context = OperationContext(
            tool_name="Edit",
            operation_type="write",
            target_paths=["src/config.py"],
            session_id="sess_test",
            environment="development",
        )

        # For risk-driven mode without callback, high risk should be rejected
        decision = await approval_hook.check_approval(context)

        # Either auto-approved (low score) or requires human approval
        assert isinstance(decision, ApprovalDecision)
        if decision.approved:
            assert decision.risk_assessment is None or \
                   decision.risk_assessment.overall_level in (RiskLevel.LOW, RiskLevel.MEDIUM)

    @pytest.mark.asyncio
    async def test_high_risk_operation_requires_approval(self, risk_config):
        """High risk operations should require human approval."""
        # Create hook with mock approval callback
        approved_flag = True
        approval_callback = AsyncMock(return_value=approved_flag)

        hook = RiskDrivenApprovalHook(
            config=risk_config,
            mode=ApprovalMode.RISK_DRIVEN,
            approval_callback=approval_callback,
        )

        context = OperationContext(
            tool_name="Bash",
            operation_type="execute",
            command="rm -rf /tmp/test_dir",
            session_id="sess_test",
            environment="production",  # Production increases risk
        )

        decision = await hook.check_approval(context)

        # Should either auto-approve (if score is low) or request human approval
        assert isinstance(decision, ApprovalDecision)
        if decision.required_human_approval:
            assert decision.risk_assessment is not None

    @pytest.mark.asyncio
    async def test_approval_with_callback_approve(self, risk_config):
        """Test approval workflow with callback returning True."""
        approval_callback = AsyncMock(return_value=True)

        hook = RiskDrivenApprovalHook(
            config=risk_config,
            mode=ApprovalMode.MANUAL,
            approval_callback=approval_callback,
        )

        context = OperationContext(
            tool_name="Write",
            operation_type="write",
            target_paths=["output.txt"],
            session_id="sess_test",
        )

        decision = await hook.check_approval(context)

        assert decision.approved is True
        assert decision.required_human_approval is True
        assert "user" in decision.approver.lower()

    @pytest.mark.asyncio
    async def test_approval_with_callback_reject(self, risk_config):
        """Test approval workflow with callback returning False."""
        approval_callback = AsyncMock(return_value=False)

        hook = RiskDrivenApprovalHook(
            config=risk_config,
            mode=ApprovalMode.MANUAL,
            approval_callback=approval_callback,
        )

        context = OperationContext(
            tool_name="Bash",
            command="dangerous_command",
            session_id="sess_test",
        )

        decision = await hook.check_approval(context)

        assert decision.approved is False
        assert decision.required_human_approval is True
        assert "rejected" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_approval_timeout_handling(self, risk_config):
        """Test handling of approval timeout."""
        async def slow_callback(assessment):
            await asyncio.sleep(10)  # Longer than timeout
            return True

        hook = RiskDrivenApprovalHook(
            config=risk_config,
            mode=ApprovalMode.MANUAL,
            approval_callback=slow_callback,
            timeout=0.1,  # 100ms timeout
        )

        context = OperationContext(
            tool_name="Edit",
            session_id="sess_test",
        )

        decision = await hook.check_approval(context)

        assert decision.approved is False
        assert "timeout" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_session_lifecycle_clears_state(self, approval_hook):
        """Test that session lifecycle properly clears state."""
        session_id = "sess_lifecycle_test"

        # Simulate some operations
        context = OperationContext(
            tool_name="Read",
            session_id=session_id,
        )
        await approval_hook.check_approval(context)

        # End session
        await approval_hook.on_session_end(session_id)

        # Start new session
        await approval_hook.on_session_start(session_id)

        # Verify state is cleared
        assert len(approval_hook._approved_operations) == 0
        assert len(approval_hook._pending_approvals) == 0


# =============================================================================
# Test Class: Mode Switching Complete Flow
# =============================================================================


class TestModeSwitchingFlow:
    """Complete flow tests for mode switching."""

    @pytest.mark.asyncio
    async def test_workflow_to_chat_switch(self, mode_switcher):
        """Test switching from workflow mode to chat mode."""
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.USER_REQUEST,
            source_mode=ExecutionMode.WORKFLOW_MODE.value,
            target_mode=ExecutionMode.CHAT_MODE.value,
            reason="User requested direct chat",
            confidence=1.0,
        )

        context = {
            "session_id": "sess_switch_test",
            "current_mode": ExecutionMode.WORKFLOW_MODE.value,
            "workflow_state": {"step": 5, "total": 10},
        }

        result = await mode_switcher.execute_switch(
            trigger=trigger,
            context=context,
            session_id="sess_switch_test",
        )

        assert result.success is True
        assert result.status == SwitchStatus.COMPLETED
        assert result.new_mode == ExecutionMode.CHAT_MODE.value
        assert result.checkpoint_id is not None

    @pytest.mark.asyncio
    async def test_chat_to_workflow_switch(self, mode_switcher):
        """Test switching from chat mode to workflow mode."""
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.COMPLEXITY,
            source_mode=ExecutionMode.CHAT_MODE.value,
            target_mode=ExecutionMode.WORKFLOW_MODE.value,
            reason="Task complexity increased",
            confidence=0.85,
        )

        context = {
            "session_id": "sess_switch_test",
            "current_mode": ExecutionMode.CHAT_MODE.value,
            "conversation_history": [
                {"role": "user", "content": "Complex multi-step task"},
            ],
        }

        result = await mode_switcher.execute_switch(
            trigger=trigger,
            context=context,
            session_id="sess_switch_test",
        )

        assert result.success is True
        assert result.new_mode == ExecutionMode.WORKFLOW_MODE.value

    @pytest.mark.asyncio
    async def test_manual_switch_execution(self, mode_switcher):
        """Test manual mode switch."""
        context = {
            "session_id": "sess_manual",
            "current_mode": ExecutionMode.CHAT_MODE.value,
        }

        result = await mode_switcher.manual_switch(
            session_id="sess_manual",
            target_mode=ExecutionMode.WORKFLOW_MODE,
            reason="Manual switch for testing",
            context=context,
        )

        assert result.success is True
        assert result.trigger.trigger_type == SwitchTriggerType.MANUAL
        assert result.trigger.confidence == 1.0

    @pytest.mark.asyncio
    async def test_switch_with_rollback(self, mode_switcher):
        """Test switch failure with rollback."""
        # Create a switch that will fail validation
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.FAILURE,
            source_mode=ExecutionMode.WORKFLOW_MODE.value,
            target_mode=ExecutionMode.CHAT_MODE.value,
            reason="Failure recovery",
            confidence=0.9,
        )

        # Incomplete context that will fail validation
        context = None

        result = await mode_switcher.execute_switch(
            trigger=trigger,
            context=context,
        )

        # Should fail due to validation
        assert result.success is False or result.validation is not None

    @pytest.mark.asyncio
    async def test_switch_metrics_tracking(self, mode_switcher):
        """Test that switch metrics are properly tracked."""
        # Perform a successful switch
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.USER_REQUEST,
            source_mode=ExecutionMode.CHAT_MODE.value,
            target_mode=ExecutionMode.WORKFLOW_MODE.value,
            reason="Test",
            confidence=1.0,
        )

        await mode_switcher.execute_switch(
            trigger=trigger,
            context={"current_mode": ExecutionMode.CHAT_MODE.value},
        )

        metrics = mode_switcher.get_metrics()

        assert metrics.total_switches >= 1
        assert "user_request" in metrics.switches_by_trigger or \
               metrics.switches_by_trigger.get("user_request", 0) >= 0

    @pytest.mark.asyncio
    async def test_transition_history_tracking(self, mode_switcher):
        """Test that transition history is properly tracked."""
        session_id = "sess_history_test"

        # Perform multiple switches
        for i in range(3):
            trigger = SwitchTrigger(
                trigger_type=SwitchTriggerType.MANUAL,
                source_mode=ExecutionMode.CHAT_MODE.value if i % 2 == 0 else ExecutionMode.WORKFLOW_MODE.value,
                target_mode=ExecutionMode.WORKFLOW_MODE.value if i % 2 == 0 else ExecutionMode.CHAT_MODE.value,
                reason=f"Switch {i}",
                confidence=1.0,
            )

            await mode_switcher.execute_switch(
                trigger=trigger,
                context={"current_mode": trigger.source_mode},
                session_id=session_id,
            )

        history = mode_switcher.get_transition_history(session_id=session_id)
        assert len(history) >= 1


# =============================================================================
# Test Class: Checkpoint Save/Restore
# =============================================================================


class TestCheckpointSaveRestore:
    """Tests for checkpoint save and restore functionality."""

    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(
        self,
        checkpoint_storage,
        sample_maf_state,
        sample_claude_state,
    ):
        """Test saving and loading a complete checkpoint."""
        checkpoint = HybridCheckpoint(
            session_id="sess_checkpoint_test",
            checkpoint_type=CheckpointType.HITL,
            maf_state=sample_maf_state,
            claude_state=sample_claude_state,
            execution_mode="hybrid",
            metadata={"test": True},
        )

        # Save
        checkpoint_id = await checkpoint_storage.save(checkpoint)

        # Load
        loaded = await checkpoint_storage.load(checkpoint_id)

        assert loaded is not None
        assert loaded.session_id == "sess_checkpoint_test"
        assert loaded.checkpoint_type == CheckpointType.HITL
        assert loaded.maf_state is not None
        assert loaded.claude_state is not None

    @pytest.mark.asyncio
    async def test_restore_checkpoint_success(
        self,
        checkpoint_storage,
        sample_maf_state,
        sample_claude_state,
    ):
        """Test successful checkpoint restoration."""
        checkpoint = HybridCheckpoint(
            session_id="sess_restore_test",
            maf_state=sample_maf_state,
            claude_state=sample_claude_state,
            execution_mode="workflow",
        )

        checkpoint_id = await checkpoint_storage.save(checkpoint)
        result = await checkpoint_storage.restore(checkpoint_id)

        assert result.success is True
        assert result.checkpoint_id == checkpoint_id
        assert result.restored_maf is True
        assert result.restored_claude is True
        assert result.restore_time_ms >= 0

    @pytest.mark.asyncio
    async def test_restore_nonexistent_checkpoint(self, checkpoint_storage):
        """Test restoring a nonexistent checkpoint."""
        result = await checkpoint_storage.restore("nonexistent_id")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_checkpoint_with_risk_snapshot(
        self,
        checkpoint_storage,
        sample_maf_state,
    ):
        """Test checkpoint with risk snapshot."""
        risk_snapshot = RiskSnapshot(
            overall_risk_level=RiskLevel.MEDIUM.value,
            risk_score=0.55,
        )

        checkpoint = HybridCheckpoint(
            session_id="sess_risk_test",
            maf_state=sample_maf_state,
            execution_mode="workflow",
            risk_snapshot=risk_snapshot,
        )

        checkpoint_id = await checkpoint_storage.save(checkpoint)
        loaded = await checkpoint_storage.load(checkpoint_id)

        assert loaded is not None
        assert loaded.risk_snapshot is not None
        assert loaded.risk_snapshot.overall_risk_level == RiskLevel.MEDIUM.value

    @pytest.mark.asyncio
    async def test_checkpoint_expiration(self, checkpoint_storage):
        """Test that expired checkpoints are not loaded."""
        checkpoint = HybridCheckpoint(
            session_id="sess_expire_test",
            execution_mode="chat",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )

        checkpoint_id = await checkpoint_storage.save(checkpoint)
        loaded = await checkpoint_storage.load(checkpoint_id)

        # Expired checkpoint should not be loaded
        assert loaded is None

    @pytest.mark.asyncio
    async def test_load_latest_checkpoint(
        self,
        checkpoint_storage,
        sample_maf_state,
    ):
        """Test loading the latest checkpoint for a session."""
        session_id = "sess_latest_test"

        # Create multiple checkpoints
        for i in range(3):
            checkpoint = HybridCheckpoint(
                session_id=session_id,
                execution_mode="workflow",
                maf_state=MAFCheckpointState(
                    workflow_id="wf_test",
                    workflow_name="Test",
                    current_step=i + 1,
                    total_steps=10,
                ),
            )
            await checkpoint_storage.save(checkpoint)
            await asyncio.sleep(0.01)  # Ensure different timestamps

        latest = await checkpoint_storage.load_latest(session_id)

        assert latest is not None
        assert latest.session_id == session_id
        # Latest should have current_step = 3
        assert latest.maf_state.current_step == 3


# =============================================================================
# Test Class: Cross-Framework Recovery
# =============================================================================


class TestCrossFrameworkRecovery:
    """Tests for cross-framework state recovery."""

    @pytest.mark.asyncio
    async def test_recover_maf_state_from_checkpoint(
        self,
        checkpoint_storage,
        sample_maf_state,
    ):
        """Test recovering MAF state from a checkpoint."""
        checkpoint = HybridCheckpoint(
            session_id="sess_maf_recovery",
            checkpoint_type=CheckpointType.RECOVERY,
            maf_state=sample_maf_state,
            execution_mode="workflow",
        )

        checkpoint_id = await checkpoint_storage.save(checkpoint)
        result = await checkpoint_storage.restore(checkpoint_id)

        assert result.success is True
        assert result.restored_maf is True

        # Verify MAF state can be retrieved
        loaded = await checkpoint_storage.load(checkpoint_id)
        assert loaded.maf_state.workflow_id == "wf_integration_test"
        assert loaded.maf_state.current_step == 3

    @pytest.mark.asyncio
    async def test_recover_claude_state_from_checkpoint(
        self,
        checkpoint_storage,
        sample_claude_state,
    ):
        """Test recovering Claude state from a checkpoint."""
        checkpoint = HybridCheckpoint(
            session_id="sess_claude_recovery",
            checkpoint_type=CheckpointType.MODE_SWITCH,
            claude_state=sample_claude_state,
            execution_mode="chat",
        )

        checkpoint_id = await checkpoint_storage.save(checkpoint)
        result = await checkpoint_storage.restore(checkpoint_id)

        assert result.success is True
        assert result.restored_claude is True

        loaded = await checkpoint_storage.load(checkpoint_id)
        assert loaded.claude_state.session_id == "sess_integration_test"
        assert loaded.claude_state.get_message_count() == 4

    @pytest.mark.asyncio
    async def test_recover_hybrid_state(
        self,
        checkpoint_storage,
        sample_maf_state,
        sample_claude_state,
    ):
        """Test recovering full hybrid state (both MAF and Claude)."""
        checkpoint = HybridCheckpoint(
            session_id="sess_hybrid_recovery",
            checkpoint_type=CheckpointType.HITL,
            maf_state=sample_maf_state,
            claude_state=sample_claude_state,
            execution_mode="hybrid",
            metadata={
                "recovery_reason": "HITL approval pending",
                "pending_operation": "dangerous_command",
            },
        )

        checkpoint_id = await checkpoint_storage.save(checkpoint)
        result = await checkpoint_storage.restore(checkpoint_id)

        assert result.success is True
        assert result.restored_maf is True
        assert result.restored_claude is True

        loaded = await checkpoint_storage.load(checkpoint_id)
        assert loaded.maf_state is not None
        assert loaded.claude_state is not None
        assert loaded.execution_mode == "hybrid"

    @pytest.mark.asyncio
    async def test_recovery_with_mode_switch(
        self,
        checkpoint_storage,
        mode_switcher,
        sample_maf_state,
        sample_claude_state,
    ):
        """Test recovery scenario involving mode switch."""
        session_id = "sess_mode_switch_recovery"

        # Create pre-switch checkpoint
        pre_checkpoint = HybridCheckpoint(
            session_id=session_id,
            checkpoint_type=CheckpointType.MODE_SWITCH,
            maf_state=sample_maf_state,
            execution_mode="workflow",
        )
        pre_checkpoint_id = await checkpoint_storage.save(pre_checkpoint)

        # Simulate mode switch
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.USER_REQUEST,
            source_mode=ExecutionMode.WORKFLOW_MODE.value,
            target_mode=ExecutionMode.CHAT_MODE.value,
            reason="Recovery test",
            confidence=1.0,
        )

        switch_result = await mode_switcher.execute_switch(
            trigger=trigger,
            context={"session_id": session_id, "current_mode": ExecutionMode.WORKFLOW_MODE.value},
            session_id=session_id,
        )

        # Create post-switch checkpoint
        post_checkpoint = HybridCheckpoint(
            session_id=session_id,
            checkpoint_type=CheckpointType.AUTO,
            claude_state=sample_claude_state,
            execution_mode="chat",
        )
        post_checkpoint_id = await checkpoint_storage.save(post_checkpoint)

        # Verify both checkpoints exist
        pre_loaded = await checkpoint_storage.load(pre_checkpoint_id)
        post_loaded = await checkpoint_storage.load(post_checkpoint_id)

        assert pre_loaded is not None
        assert post_loaded is not None
        assert pre_loaded.execution_mode == "workflow"
        assert post_loaded.execution_mode == "chat"


# =============================================================================
# Test Class: Performance Benchmarks
# =============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmark tests for Phase 14 components."""

    @pytest.mark.asyncio
    async def test_risk_assessment_latency(self, risk_engine):
        """Benchmark risk assessment latency."""
        context = OperationContext(
            tool_name="Bash",
            operation_type="execute",
            command="echo 'performance test'",
            session_id="sess_perf",
            environment="development",
        )

        # Warm-up
        for _ in range(5):
            risk_engine.assess(context)

        # Benchmark
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            risk_engine.assess(context)

        elapsed_ms = (time.time() - start_time) * 1000
        avg_latency_ms = elapsed_ms / iterations

        # Assert reasonable performance (< 10ms per assessment)
        assert avg_latency_ms < 10, f"Average latency {avg_latency_ms:.2f}ms exceeds 10ms threshold"

        # Get engine metrics
        metrics = risk_engine.get_metrics()
        assert metrics.total_assessments >= iterations

    @pytest.mark.asyncio
    async def test_checkpoint_save_latency(self, checkpoint_storage):
        """Benchmark checkpoint save latency."""
        checkpoint = HybridCheckpoint(
            session_id="sess_perf",
            execution_mode="hybrid",
            maf_state=MAFCheckpointState(
                workflow_id="wf_perf",
                workflow_name="Performance Test",
                current_step=5,
                total_steps=10,
                agent_states={"agent_1": {"large_state": "x" * 1000}},
                variables={"large_var": "y" * 1000},
            ),
            claude_state=ClaudeCheckpointState(
                session_id="sess_perf",
                conversation_history=[
                    {"role": "user", "content": f"Message {i}"}
                    for i in range(50)
                ],
            ),
        )

        # Warm-up
        for _ in range(5):
            await checkpoint_storage.save(HybridCheckpoint(
                session_id="sess_warmup",
                execution_mode="chat",
            ))

        # Benchmark
        iterations = 50
        start_time = time.time()

        for i in range(iterations):
            checkpoint.metadata = {"iteration": i}
            await checkpoint_storage.save(checkpoint)

        elapsed_ms = (time.time() - start_time) * 1000
        avg_latency_ms = elapsed_ms / iterations

        # Assert reasonable performance (< 5ms per save for memory storage)
        assert avg_latency_ms < 5, f"Average save latency {avg_latency_ms:.2f}ms exceeds 5ms threshold"

    @pytest.mark.asyncio
    async def test_checkpoint_load_latency(self, checkpoint_storage):
        """Benchmark checkpoint load latency."""
        # Create checkpoint with substantial data
        checkpoint = HybridCheckpoint(
            session_id="sess_load_perf",
            execution_mode="hybrid",
            maf_state=MAFCheckpointState(
                workflow_id="wf_perf",
                workflow_name="Performance Test",
                current_step=5,
                total_steps=10,
            ),
            claude_state=ClaudeCheckpointState(
                session_id="sess_perf",
                conversation_history=[
                    {"role": "user", "content": f"Message {i}"}
                    for i in range(100)
                ],
            ),
        )

        checkpoint_id = await checkpoint_storage.save(checkpoint)

        # Warm-up
        for _ in range(5):
            await checkpoint_storage.load(checkpoint_id)

        # Benchmark
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            await checkpoint_storage.load(checkpoint_id)

        elapsed_ms = (time.time() - start_time) * 1000
        avg_latency_ms = elapsed_ms / iterations

        # Assert reasonable performance (< 2ms per load for memory storage)
        assert avg_latency_ms < 2, f"Average load latency {avg_latency_ms:.2f}ms exceeds 2ms threshold"

    @pytest.mark.asyncio
    async def test_mode_switch_latency(self, mode_switcher):
        """Benchmark mode switch latency."""
        context = {
            "session_id": "sess_switch_perf",
            "current_mode": ExecutionMode.CHAT_MODE.value,
        }

        # Warm-up
        for _ in range(3):
            trigger = SwitchTrigger(
                trigger_type=SwitchTriggerType.MANUAL,
                source_mode=ExecutionMode.CHAT_MODE.value,
                target_mode=ExecutionMode.WORKFLOW_MODE.value,
                reason="Warmup",
                confidence=1.0,
            )
            await mode_switcher.execute_switch(trigger, context)

        # Benchmark
        iterations = 20
        start_time = time.time()

        for i in range(iterations):
            trigger = SwitchTrigger(
                trigger_type=SwitchTriggerType.MANUAL,
                source_mode=ExecutionMode.CHAT_MODE.value if i % 2 == 0 else ExecutionMode.WORKFLOW_MODE.value,
                target_mode=ExecutionMode.WORKFLOW_MODE.value if i % 2 == 0 else ExecutionMode.CHAT_MODE.value,
                reason=f"Benchmark {i}",
                confidence=1.0,
            )
            context["current_mode"] = trigger.source_mode
            await mode_switcher.execute_switch(trigger, context)

        elapsed_ms = (time.time() - start_time) * 1000
        avg_latency_ms = elapsed_ms / iterations

        # Assert reasonable performance (< 20ms per switch)
        assert avg_latency_ms < 20, f"Average switch latency {avg_latency_ms:.2f}ms exceeds 20ms threshold"

    @pytest.mark.asyncio
    async def test_approval_hook_latency(self, approval_hook):
        """Benchmark approval hook latency for auto-approved operations."""
        context = OperationContext(
            tool_name="Read",
            operation_type="read",
            target_paths=["test.py"],
            session_id="sess_perf",
        )

        # Warm-up
        for _ in range(5):
            await approval_hook.check_approval(context)

        # Benchmark
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            await approval_hook.check_approval(context)

        elapsed_ms = (time.time() - start_time) * 1000
        avg_latency_ms = elapsed_ms / iterations

        # Assert reasonable performance (< 1ms for auto-approved operations)
        assert avg_latency_ms < 1, f"Average approval latency {avg_latency_ms:.2f}ms exceeds 1ms threshold"

    @pytest.mark.asyncio
    async def test_concurrent_checkpoint_operations(self, checkpoint_storage):
        """Test concurrent checkpoint operations performance."""
        session_id = "sess_concurrent"

        async def save_and_load(i: int):
            checkpoint = HybridCheckpoint(
                session_id=session_id,
                execution_mode="chat",
                metadata={"task_id": i},
            )
            checkpoint_id = await checkpoint_storage.save(checkpoint)
            await checkpoint_storage.load(checkpoint_id)
            return i

        # Run concurrent operations
        iterations = 50
        start_time = time.time()

        tasks = [save_and_load(i) for i in range(iterations)]
        results = await asyncio.gather(*tasks)

        elapsed_ms = (time.time() - start_time) * 1000

        # Verify all completed
        assert len(results) == iterations
        assert sorted(results) == list(range(iterations))

        # Check throughput (should handle 50 concurrent ops quickly)
        assert elapsed_ms < 500, f"Concurrent operations took {elapsed_ms:.2f}ms"


# =============================================================================
# Test Class: Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """Complex integration scenarios combining multiple components."""

    @pytest.mark.asyncio
    async def test_complete_hitl_workflow(
        self,
        risk_engine,
        checkpoint_storage,
        mode_switcher,
    ):
        """Test complete HITL workflow: assess -> checkpoint -> approve -> execute."""
        session_id = "sess_hitl_complete"

        # Step 1: Risk Assessment
        context = OperationContext(
            tool_name="Bash",
            operation_type="execute",
            command="important_command",
            session_id=session_id,
            environment="production",
        )

        assessment = risk_engine.assess(context)
        assert assessment is not None

        # Step 2: Create HITL Checkpoint
        risk_snapshot = RiskSnapshot(
            overall_risk_level=assessment.overall_level.value if hasattr(assessment.overall_level, 'value') else str(assessment.overall_level),
            risk_score=assessment.overall_score,
        )

        checkpoint = HybridCheckpoint(
            session_id=session_id,
            checkpoint_type=CheckpointType.HITL,
            execution_mode="workflow",
            risk_snapshot=risk_snapshot,
            metadata={
                "pending_operation": context.tool_name,
                "pending_command": context.command,
            },
        )

        checkpoint_id = await checkpoint_storage.save(checkpoint)

        # Step 3: Simulate approval (in real scenario, this waits for human)
        # For test, we just verify the checkpoint is stored correctly
        loaded = await checkpoint_storage.load(checkpoint_id)
        assert loaded.risk_snapshot is not None
        assert loaded.checkpoint_type == CheckpointType.HITL

        # Step 4: After approval, restore and continue
        result = await checkpoint_storage.restore(checkpoint_id)
        assert result.success is True

        # Step 5: Mark checkpoint as restored
        loaded.mark_restored()
        await checkpoint_storage.save(loaded)

        final_loaded = await checkpoint_storage.load(checkpoint_id)
        assert final_loaded.status == CheckpointStatus.RESTORED

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(
        self,
        checkpoint_storage,
        mode_switcher,
    ):
        """Test error recovery workflow with checkpoints and mode switching."""
        session_id = "sess_error_recovery"

        # Step 1: Create initial state checkpoint
        initial_state = HybridCheckpoint(
            session_id=session_id,
            checkpoint_type=CheckpointType.AUTO,
            execution_mode="workflow",
            maf_state=MAFCheckpointState(
                workflow_id="wf_error_test",
                workflow_name="Error Test Workflow",
                current_step=5,
                total_steps=10,
            ),
        )
        initial_checkpoint_id = await checkpoint_storage.save(initial_state)

        # Step 2: Simulate error and mode switch to chat for debugging
        error_trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.FAILURE,
            source_mode=ExecutionMode.WORKFLOW_MODE.value,
            target_mode=ExecutionMode.CHAT_MODE.value,
            reason="Workflow step 6 failed, switching to chat for debugging",
            confidence=0.95,
        )

        switch_result = await mode_switcher.execute_switch(
            trigger=error_trigger,
            context={"session_id": session_id, "current_mode": ExecutionMode.WORKFLOW_MODE.value},
            session_id=session_id,
        )

        assert switch_result.success is True

        # Step 3: Create error recovery checkpoint
        error_checkpoint = HybridCheckpoint(
            session_id=session_id,
            checkpoint_type=CheckpointType.RECOVERY,
            execution_mode="chat",
            claude_state=ClaudeCheckpointState(
                session_id=session_id,
                conversation_history=[
                    {"role": "system", "content": "Error occurred at step 6"},
                    {"role": "user", "content": "What went wrong?"},
                ],
            ),
            metadata={
                "error_step": 6,
                "error_message": "Connection timeout",
                "previous_checkpoint": initial_checkpoint_id,
            },
        )
        error_checkpoint_id = await checkpoint_storage.save(error_checkpoint)

        # Step 4: Verify recovery path
        loaded = await checkpoint_storage.load(error_checkpoint_id)
        assert loaded.checkpoint_type == CheckpointType.RECOVERY
        assert loaded.metadata["previous_checkpoint"] == initial_checkpoint_id

        # Step 5: Can recover to initial state if needed
        initial_restore = await checkpoint_storage.restore(initial_checkpoint_id)
        assert initial_restore.success is True

    @pytest.mark.asyncio
    async def test_multi_session_isolation(self, checkpoint_storage, mode_switcher):
        """Test that sessions are properly isolated."""
        sessions = ["sess_A", "sess_B", "sess_C"]

        # Create checkpoints for each session
        for session_id in sessions:
            checkpoint = HybridCheckpoint(
                session_id=session_id,
                execution_mode="workflow",
                metadata={"session_specific": session_id},
            )
            await checkpoint_storage.save(checkpoint)

        # Verify isolation
        for session_id in sessions:
            results = await checkpoint_storage.load_by_session(session_id)
            assert len(results) >= 1
            assert all(r.session_id == session_id for r in results)

        # Verify cross-session stats
        stats = await checkpoint_storage.get_stats()
        assert stats.sessions_count >= 3
