"""
MagenticBuilder Migration Unit Tests - Sprint 17 (S17-6)

測試 magentic_migration.py 模組的所有組件。

測試覆蓋:
    - DynamicPlannerStateLegacy 枚舉
    - PlannerActionTypeLegacy 枚舉
    - PlanStepLegacy 數據類
    - DynamicPlanLegacy 數據類
    - ProgressEvaluationLegacy 數據類
    - DynamicPlannerContextLegacy 數據類
    - DynamicPlannerResultLegacy 數據類
    - Conversion functions (狀態、上下文、Ledger)
    - HumanInterventionHandler 類
    - MagenticManagerAdapter 類
    - Factory functions

Author: IPA Platform Team
Sprint: 17 - MagenticBuilder 重構 (Magentic One)
Created: 2025-12-05
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional, Callable
from uuid import uuid4

# Import modules under test
from src.integrations.agent_framework.builders.magentic_migration import (
    # Legacy enums
    DynamicPlannerStateLegacy,
    PlannerActionTypeLegacy,
    # Legacy data classes
    PlanStepLegacy,
    DynamicPlanLegacy,
    ProgressEvaluationLegacy,
    DynamicPlannerContextLegacy,
    DynamicPlannerResultLegacy,
    # Conversion functions
    convert_legacy_state_to_magentic,
    convert_magentic_status_to_legacy,
    convert_legacy_context_to_magentic,
    convert_magentic_context_to_legacy,
    convert_legacy_plan_to_task_ledger,
    convert_task_ledger_to_legacy_plan,
    convert_legacy_progress_to_ledger,
    convert_progress_ledger_to_legacy,
    convert_magentic_result_to_legacy,
    # Handler and adapter
    HumanInterventionHandler,
    MagenticManagerAdapter,
    # Factory functions
    migrate_dynamic_planner,
    create_intervention_handler,
)

# Import new types for conversion testing
from src.integrations.agent_framework.builders.magentic import (
    MagenticStatus,
    MagenticContext,
    MagenticMessage,
    MessageRole,
    TaskLedger,
    ProgressLedger,
    ProgressLedgerItem,
    MagenticResult,
    HumanInterventionKind,
    HumanInterventionRequest,
    HumanInterventionReply,
    HumanInterventionDecision,
)


# =============================================================================
# Legacy Enum Tests
# =============================================================================


class TestDynamicPlannerStateLegacy:
    """測試 DynamicPlannerStateLegacy 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert DynamicPlannerStateLegacy.IDLE == "idle"
        assert DynamicPlannerStateLegacy.PLANNING == "planning"
        assert DynamicPlannerStateLegacy.EXECUTING == "executing"
        assert DynamicPlannerStateLegacy.EVALUATING == "evaluating"
        assert DynamicPlannerStateLegacy.REPLANNING == "replanning"
        assert DynamicPlannerStateLegacy.COMPLETED == "completed"
        assert DynamicPlannerStateLegacy.FAILED == "failed"
        assert DynamicPlannerStateLegacy.STALLED == "stalled"

    def test_enum_from_string(self):
        """測試從字符串創建枚舉。"""
        state = DynamicPlannerStateLegacy("planning")
        assert state == DynamicPlannerStateLegacy.PLANNING


class TestPlannerActionTypeLegacy:
    """測試 PlannerActionTypeLegacy 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert PlannerActionTypeLegacy.RESEARCH == "research"
        assert PlannerActionTypeLegacy.ANALYZE == "analyze"
        assert PlannerActionTypeLegacy.IMPLEMENT == "implement"
        assert PlannerActionTypeLegacy.REVIEW == "review"
        assert PlannerActionTypeLegacy.COMMUNICATE == "communicate"
        assert PlannerActionTypeLegacy.DECIDE == "decide"
        assert PlannerActionTypeLegacy.CUSTOM == "custom"


# =============================================================================
# Legacy Data Class Tests
# =============================================================================


class TestPlanStepLegacy:
    """測試 PlanStepLegacy 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        step = PlanStepLegacy(
            step_id="step-1",
            description="Research the topic",
            action_type=PlannerActionTypeLegacy.RESEARCH,
        )
        assert step.step_id == "step-1"
        assert step.description == "Research the topic"
        assert step.action_type == PlannerActionTypeLegacy.RESEARCH
        assert step.status == "pending"

    def test_full_creation(self):
        """測試完整創建。"""
        step = PlanStepLegacy(
            step_id="step-2",
            description="Implement feature",
            action_type=PlannerActionTypeLegacy.IMPLEMENT,
            assigned_agent="developer",
            dependencies=["step-1"],
            status="in_progress",
            output="Implementation started",
            metadata={"priority": "high"},
        )
        assert step.assigned_agent == "developer"
        assert "step-1" in step.dependencies
        assert step.status == "in_progress"

    def test_to_dict(self):
        """測試轉換為字典。"""
        step = PlanStepLegacy(
            step_id="step-1",
            description="Test",
            action_type=PlannerActionTypeLegacy.REVIEW,
        )
        data = step.to_dict()
        assert data["step_id"] == "step-1"
        assert data["action_type"] == "review"


class TestDynamicPlanLegacy:
    """測試 DynamicPlanLegacy 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        plan = DynamicPlanLegacy(
            plan_id="plan-001",
            goal="Build web application",
        )
        assert plan.plan_id == "plan-001"
        assert plan.goal == "Build web application"
        assert plan.steps == []
        assert plan.current_step_index == 0

    def test_with_steps(self):
        """測試帶步驟的計劃。"""
        step1 = PlanStepLegacy(
            step_id="s1",
            description="Step 1",
            action_type=PlannerActionTypeLegacy.RESEARCH,
        )
        step2 = PlanStepLegacy(
            step_id="s2",
            description="Step 2",
            action_type=PlannerActionTypeLegacy.IMPLEMENT,
        )
        plan = DynamicPlanLegacy(
            plan_id="plan-002",
            goal="Complete task",
            steps=[step1, step2],
        )
        assert len(plan.steps) == 2

    def test_with_facts(self):
        """測試帶事實的計劃。"""
        plan = DynamicPlanLegacy(
            plan_id="plan-003",
            goal="Goal",
            facts=["Fact 1", "Fact 2"],
        )
        assert len(plan.facts) == 2

    def test_to_dict(self):
        """測試轉換為字典。"""
        plan = DynamicPlanLegacy(
            plan_id="plan-001",
            goal="Test",
        )
        data = plan.to_dict()
        assert data["plan_id"] == "plan-001"
        assert data["goal"] == "Test"


class TestProgressEvaluationLegacy:
    """測試 ProgressEvaluationLegacy 數據類。"""

    def test_creation(self):
        """測試創建。"""
        evaluation = ProgressEvaluationLegacy(
            is_task_complete=False,
            is_stalled=False,
            progress_score=0.5,
            next_agent="researcher",
            next_instruction="Continue research",
        )
        assert evaluation.is_task_complete is False
        assert evaluation.progress_score == 0.5
        assert evaluation.next_agent == "researcher"

    def test_stalled_evaluation(self):
        """測試停滯評估。"""
        evaluation = ProgressEvaluationLegacy(
            is_task_complete=False,
            is_stalled=True,
            stall_reason="Agent not making progress",
            progress_score=0.0,
        )
        assert evaluation.is_stalled is True
        assert evaluation.stall_reason is not None

    def test_to_dict(self):
        """測試轉換為字典。"""
        evaluation = ProgressEvaluationLegacy(
            is_task_complete=True,
            is_stalled=False,
            progress_score=1.0,
        )
        data = evaluation.to_dict()
        assert data["is_task_complete"] is True
        assert data["progress_score"] == 1.0


class TestDynamicPlannerContextLegacy:
    """測試 DynamicPlannerContextLegacy 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        context = DynamicPlannerContextLegacy(
            task="Complete the project",
        )
        assert context.task == "Complete the project"
        assert context.history == []
        assert context.available_agents == {}

    def test_full_creation(self):
        """測試完整創建。"""
        context = DynamicPlannerContextLegacy(
            task="Build feature",
            history=["Step 1 done", "Step 2 done"],
            available_agents={"researcher": "Research agent"},
            current_plan=DynamicPlanLegacy(
                plan_id="p1",
                goal="Build",
            ),
            iteration_count=3,
            metadata={"key": "value"},
        )
        assert len(context.history) == 2
        assert context.iteration_count == 3

    def test_to_dict(self):
        """測試轉換為字典。"""
        context = DynamicPlannerContextLegacy(task="Test")
        data = context.to_dict()
        assert data["task"] == "Test"


class TestDynamicPlannerResultLegacy:
    """測試 DynamicPlannerResultLegacy 數據類。"""

    def test_success_result(self):
        """測試成功結果。"""
        result = DynamicPlannerResultLegacy(
            success=True,
            final_output="Task completed successfully",
            total_iterations=5,
            final_state=DynamicPlannerStateLegacy.COMPLETED,
        )
        assert result.success is True
        assert result.total_iterations == 5

    def test_failure_result(self):
        """測試失敗結果。"""
        result = DynamicPlannerResultLegacy(
            success=False,
            error="Max iterations exceeded",
            total_iterations=10,
            final_state=DynamicPlannerStateLegacy.FAILED,
        )
        assert result.success is False
        assert result.error is not None

    def test_to_dict(self):
        """測試轉換為字典。"""
        result = DynamicPlannerResultLegacy(
            success=True,
            total_iterations=1,
            final_state=DynamicPlannerStateLegacy.COMPLETED,
        )
        data = result.to_dict()
        assert data["success"] is True


# =============================================================================
# Conversion Function Tests
# =============================================================================


class TestStateConversion:
    """測試狀態轉換函數。"""

    def test_legacy_idle_to_magentic(self):
        """測試 IDLE 轉換。"""
        result = convert_legacy_state_to_magentic(DynamicPlannerStateLegacy.IDLE)
        assert result == MagenticStatus.IDLE

    def test_legacy_executing_to_magentic(self):
        """測試 EXECUTING 轉換。"""
        result = convert_legacy_state_to_magentic(DynamicPlannerStateLegacy.EXECUTING)
        assert result == MagenticStatus.RUNNING

    def test_legacy_stalled_to_magentic(self):
        """測試 STALLED 轉換。"""
        result = convert_legacy_state_to_magentic(DynamicPlannerStateLegacy.STALLED)
        assert result == MagenticStatus.STALLED

    def test_legacy_completed_to_magentic(self):
        """測試 COMPLETED 轉換。"""
        result = convert_legacy_state_to_magentic(DynamicPlannerStateLegacy.COMPLETED)
        assert result == MagenticStatus.COMPLETED

    def test_magentic_idle_to_legacy(self):
        """測試 MagenticStatus.IDLE 轉換。"""
        result = convert_magentic_status_to_legacy(MagenticStatus.IDLE)
        assert result == DynamicPlannerStateLegacy.IDLE

    def test_magentic_running_to_legacy(self):
        """測試 MagenticStatus.RUNNING 轉換。"""
        result = convert_magentic_status_to_legacy(MagenticStatus.RUNNING)
        assert result == DynamicPlannerStateLegacy.EXECUTING

    def test_magentic_waiting_intervention_to_legacy(self):
        """測試 MagenticStatus.WAITING_INTERVENTION 轉換。"""
        result = convert_magentic_status_to_legacy(MagenticStatus.WAITING_INTERVENTION)
        assert result == DynamicPlannerStateLegacy.EVALUATING


class TestContextConversion:
    """測試上下文轉換函數。"""

    def test_legacy_to_magentic_context(self):
        """測試 Legacy 轉 Magentic 上下文。"""
        legacy = DynamicPlannerContextLegacy(
            task="Complete task",
            history=["Step 1", "Step 2"],
            available_agents={"agent1": "Agent 1 description"},
            iteration_count=5,
        )
        result = convert_legacy_context_to_magentic(legacy)

        assert isinstance(result, MagenticContext)
        assert result.task == "Complete task"
        assert result.round_count == 5
        assert "agent1" in result.participant_descriptions

    def test_magentic_to_legacy_context(self):
        """測試 Magentic 轉 Legacy 上下文。"""
        msg = MagenticMessage(role=MessageRole.USER, content="Test")
        magentic = MagenticContext(
            task="Test task",
            chat_history=[msg],
            participant_descriptions={"p1": "Participant 1"},
            round_count=3,
        )
        result = convert_magentic_context_to_legacy(magentic)

        assert isinstance(result, DynamicPlannerContextLegacy)
        assert result.task == "Test task"
        assert result.iteration_count == 3


class TestLedgerConversion:
    """測試 Ledger 轉換函數。"""

    def test_legacy_plan_to_task_ledger(self):
        """測試 Legacy 計劃轉 Task Ledger。"""
        step = PlanStepLegacy(
            step_id="s1",
            description="Step 1",
            action_type=PlannerActionTypeLegacy.RESEARCH,
        )
        legacy_plan = DynamicPlanLegacy(
            plan_id="plan-001",
            goal="Build app",
            steps=[step],
            facts=["Fact 1", "Fact 2"],
        )
        result = convert_legacy_plan_to_task_ledger(legacy_plan)

        assert isinstance(result, TaskLedger)
        assert result.facts is not None
        assert result.plan is not None
        assert "Fact 1" in result.facts.content

    def test_task_ledger_to_legacy_plan(self):
        """測試 Task Ledger 轉 Legacy 計劃。"""
        facts_msg = MagenticMessage(
            role=MessageRole.SYSTEM,
            content="Known facts:\n- Fact 1\n- Fact 2",
        )
        plan_msg = MagenticMessage(
            role=MessageRole.SYSTEM,
            content="Plan:\n1. Step 1\n2. Step 2",
        )
        ledger = TaskLedger(facts=facts_msg, plan=plan_msg)
        result = convert_task_ledger_to_legacy_plan(ledger, plan_id="test-plan")

        assert isinstance(result, DynamicPlanLegacy)
        assert result.plan_id == "test-plan"

    def test_legacy_progress_to_ledger(self):
        """測試 Legacy 進度轉 Progress Ledger。"""
        legacy = ProgressEvaluationLegacy(
            is_task_complete=False,
            is_stalled=False,
            progress_score=0.5,
            next_agent="researcher",
            next_instruction="Continue research",
        )
        result = convert_legacy_progress_to_ledger(legacy)

        assert isinstance(result, ProgressLedger)
        assert result.is_request_satisfied.answer is False
        assert result.next_speaker.answer == "researcher"

    def test_progress_ledger_to_legacy(self):
        """測試 Progress Ledger 轉 Legacy。"""
        ledger = ProgressLedger(
            is_request_satisfied=ProgressLedgerItem(reason="Not done", answer=False),
            is_in_loop=ProgressLedgerItem(reason="No loop", answer=False),
            is_progress_being_made=ProgressLedgerItem(reason="Yes", answer=True),
            next_speaker=ProgressLedgerItem(reason="Need research", answer="researcher"),
            instruction_or_question=ProgressLedgerItem(
                reason="Next step",
                answer="Please investigate",
            ),
        )
        result = convert_progress_ledger_to_legacy(ledger)

        assert isinstance(result, ProgressEvaluationLegacy)
        assert result.is_task_complete is False
        assert result.next_agent == "researcher"


class TestResultConversion:
    """測試結果轉換函數。"""

    def test_completed_result_conversion(self):
        """測試完成結果轉換。"""
        final_msg = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content="Final answer",
        )
        magentic_result = MagenticResult(
            status=MagenticStatus.COMPLETED,
            final_answer=final_msg,
            conversation=[final_msg],
            rounds=[],
            total_rounds=5,
            duration_seconds=30.0,
        )
        result = convert_magentic_result_to_legacy(magentic_result)

        assert isinstance(result, DynamicPlannerResultLegacy)
        assert result.success is True
        assert result.final_state == DynamicPlannerStateLegacy.COMPLETED
        assert result.total_iterations == 5

    def test_failed_result_conversion(self):
        """測試失敗結果轉換。"""
        magentic_result = MagenticResult(
            status=MagenticStatus.FAILED,
            conversation=[],
            rounds=[],
            total_rounds=10,
            duration_seconds=60.0,
            termination_reason="Max rounds exceeded",
        )
        result = convert_magentic_result_to_legacy(magentic_result)

        assert result.success is False
        assert result.final_state == DynamicPlannerStateLegacy.FAILED
        assert result.error == "Max rounds exceeded"


# =============================================================================
# HumanInterventionHandler Tests
# =============================================================================


class TestHumanInterventionHandler:
    """測試 HumanInterventionHandler 類。"""

    @pytest.fixture
    def handler(self):
        """創建處理程序。"""
        return HumanInterventionHandler()

    def test_creation(self, handler):
        """測試創建。"""
        assert handler is not None
        assert handler._pending_request is None

    def test_register_callback(self, handler):
        """測試註冊回調。"""
        callback = AsyncMock()
        handler.register_callback(HumanInterventionKind.PLAN_REVIEW, callback)
        assert HumanInterventionKind.PLAN_REVIEW in handler._callbacks

    def test_create_plan_review_request(self, handler):
        """測試創建計劃審核請求。"""
        request = handler.create_plan_review_request(
            task_text="Build app",
            facts_text="User needs auth",
            plan_text="1. Design\n2. Implement",
        )
        assert request.kind == HumanInterventionKind.PLAN_REVIEW
        assert request.task_text == "Build app"

    def test_create_stall_request(self, handler):
        """測試創建停滯請求。"""
        request = handler.create_stall_request(
            stall_count=3,
            stall_reason="No progress",
            last_agent="researcher",
            round_index=10,
        )
        assert request.kind == HumanInterventionKind.STALL
        assert request.stall_count == 3

    def test_create_tool_approval_request(self, handler):
        """測試創建工具批准請求。"""
        request = handler.create_tool_approval_request(
            tool_name="web_search",
            tool_params={"query": "test"},
            round_index=5,
        )
        assert request.kind == HumanInterventionKind.TOOL_APPROVAL

    @pytest.mark.asyncio
    async def test_submit_request(self, handler):
        """測試提交請求。"""
        callback = AsyncMock(return_value=HumanInterventionReply(
            decision=HumanInterventionDecision.APPROVE,
        ))
        handler.register_callback(HumanInterventionKind.PLAN_REVIEW, callback)

        request = handler.create_plan_review_request(
            task_text="Test",
            facts_text="Facts",
            plan_text="Plan",
        )
        reply = await handler.submit_request(request)

        assert reply is not None
        assert reply.decision == HumanInterventionDecision.APPROVE

    @pytest.mark.asyncio
    async def test_submit_request_no_callback(self, handler):
        """測試無回調時提交請求。"""
        request = handler.create_plan_review_request(
            task_text="Test",
            facts_text="Facts",
            plan_text="Plan",
        )

        # Without callback, should return default APPROVE
        reply = await handler.submit_request(request)
        assert reply.decision == HumanInterventionDecision.APPROVE

    def test_get_pending_request(self, handler):
        """測試獲取待處理請求。"""
        assert handler.get_pending_request() is None

        request = handler.create_plan_review_request(
            task_text="Test",
            facts_text="Facts",
            plan_text="Plan",
        )
        handler._pending_request = request

        assert handler.get_pending_request() == request

    def test_clear_pending_request(self, handler):
        """測試清除待處理請求。"""
        handler._pending_request = MagicMock()
        handler.clear_pending_request()
        assert handler._pending_request is None


# =============================================================================
# MagenticManagerAdapter Tests
# =============================================================================


class TestMagenticManagerAdapter:
    """測試 MagenticManagerAdapter 類。"""

    @pytest.fixture
    def sample_funcs(self):
        """創建示例函數。"""
        async def extract_facts(ctx):
            return ["Fact 1", "Fact 2"]

        async def generate_plan(ctx, facts):
            return [
                PlanStepLegacy(
                    step_id="s1",
                    description="Step 1",
                    action_type=PlannerActionTypeLegacy.RESEARCH,
                )
            ]

        async def evaluate_progress(ctx, plan):
            return ProgressEvaluationLegacy(
                is_task_complete=False,
                is_stalled=False,
                progress_score=0.5,
                next_agent="agent1",
                next_instruction="Continue",
            )

        async def select_next_agent(ctx, progress):
            return "agent1"

        async def generate_instruction(ctx, agent, progress):
            return "Please continue"

        return {
            "extract_facts_fn": extract_facts,
            "generate_plan_fn": generate_plan,
            "evaluate_progress_fn": evaluate_progress,
            "select_next_agent_fn": select_next_agent,
            "generate_instruction_fn": generate_instruction,
        }

    def test_creation(self, sample_funcs):
        """測試創建。"""
        adapter = MagenticManagerAdapter(**sample_funcs)
        assert adapter.name == "MagenticManager"

    def test_creation_with_custom_name(self, sample_funcs):
        """測試自定義名稱創建。"""
        adapter = MagenticManagerAdapter(
            **sample_funcs,
            name="CustomManager",
        )
        assert adapter.name == "CustomManager"

    @pytest.mark.asyncio
    async def test_create_task_ledger(self, sample_funcs):
        """測試創建 Task Ledger。"""
        adapter = MagenticManagerAdapter(**sample_funcs)
        context = MagenticContext(task="Test task")

        ledger = await adapter.create_task_ledger(context)
        assert isinstance(ledger, TaskLedger)
        assert ledger.facts is not None
        assert ledger.plan is not None

    @pytest.mark.asyncio
    async def test_evaluate_progress(self, sample_funcs):
        """測試評估進度。"""
        adapter = MagenticManagerAdapter(**sample_funcs)
        context = MagenticContext(task="Test")
        task_ledger = TaskLedger(
            facts=MagenticMessage(role=MessageRole.SYSTEM, content="Facts"),
            plan=MagenticMessage(role=MessageRole.SYSTEM, content="Plan"),
        )

        progress = await adapter.evaluate_progress(context, task_ledger)
        assert isinstance(progress, ProgressLedger)
        assert progress.next_speaker.answer == "agent1"

    @pytest.mark.asyncio
    async def test_select_speaker(self, sample_funcs):
        """測試選擇發言者。"""
        adapter = MagenticManagerAdapter(**sample_funcs)
        context = MagenticContext(task="Test")
        progress = ProgressLedger(
            is_request_satisfied=ProgressLedgerItem(reason="", answer=False),
            is_in_loop=ProgressLedgerItem(reason="", answer=False),
            is_progress_being_made=ProgressLedgerItem(reason="", answer=True),
            next_speaker=ProgressLedgerItem(reason="", answer="agent1"),
            instruction_or_question=ProgressLedgerItem(reason="", answer="Do it"),
        )

        speaker = await adapter.select_speaker(context, progress)
        assert speaker == "agent1"

    @pytest.mark.asyncio
    async def test_generate_instruction(self, sample_funcs):
        """測試生成指令。"""
        adapter = MagenticManagerAdapter(**sample_funcs)
        context = MagenticContext(task="Test")
        progress = ProgressLedger(
            is_request_satisfied=ProgressLedgerItem(reason="", answer=False),
            is_in_loop=ProgressLedgerItem(reason="", answer=False),
            is_progress_being_made=ProgressLedgerItem(reason="", answer=True),
            next_speaker=ProgressLedgerItem(reason="", answer="agent1"),
            instruction_or_question=ProgressLedgerItem(reason="", answer="Continue"),
        )

        instruction = await adapter.generate_instruction(
            context, "agent1", progress
        )
        assert instruction == "Please continue"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """測試工廠函數。"""

    def test_create_intervention_handler(self):
        """測試 create_intervention_handler。"""
        handler = create_intervention_handler()
        assert isinstance(handler, HumanInterventionHandler)

    def test_create_intervention_handler_with_callbacks(self):
        """測試帶回調創建。"""
        callback = AsyncMock()
        callbacks = {HumanInterventionKind.PLAN_REVIEW: callback}
        handler = create_intervention_handler(callbacks=callbacks)

        assert HumanInterventionKind.PLAN_REVIEW in handler._callbacks

    @pytest.mark.asyncio
    async def test_migrate_dynamic_planner(self):
        """測試 migrate_dynamic_planner。"""
        async def extract_facts(ctx):
            return ["Fact"]

        async def generate_plan(ctx, facts):
            return []

        async def evaluate_progress(ctx, plan):
            return ProgressEvaluationLegacy(
                is_task_complete=True,
                is_stalled=False,
                progress_score=1.0,
            )

        async def select_next_agent(ctx, progress):
            return "agent"

        async def generate_instruction(ctx, agent, progress):
            return "Done"

        manager = migrate_dynamic_planner(
            extract_facts_fn=extract_facts,
            generate_plan_fn=generate_plan,
            evaluate_progress_fn=evaluate_progress,
            select_next_agent_fn=select_next_agent,
            generate_instruction_fn=generate_instruction,
        )

        assert isinstance(manager, MagenticManagerAdapter)


# =============================================================================
# Integration Tests
# =============================================================================


class TestMigrationIntegration:
    """遷移整合測試。"""

    @pytest.mark.asyncio
    async def test_full_legacy_to_magentic_flow(self):
        """測試完整的 Legacy 到 Magentic 流程。"""
        # Create legacy context
        legacy_context = DynamicPlannerContextLegacy(
            task="Build a web application",
            history=["Requirements gathered", "Design complete"],
            available_agents={
                "developer": "Software developer",
                "tester": "QA tester",
            },
            iteration_count=2,
        )

        # Convert to Magentic
        magentic_context = convert_legacy_context_to_magentic(legacy_context)

        # Verify conversion
        assert magentic_context.task == legacy_context.task
        assert magentic_context.round_count == legacy_context.iteration_count
        assert "developer" in magentic_context.participant_descriptions

        # Convert back to legacy
        back_to_legacy = convert_magentic_context_to_legacy(magentic_context)

        # Verify round-trip
        assert back_to_legacy.task == legacy_context.task
        assert back_to_legacy.iteration_count == legacy_context.iteration_count

    @pytest.mark.asyncio
    async def test_full_plan_conversion_flow(self):
        """測試完整的計劃轉換流程。"""
        # Create legacy plan
        steps = [
            PlanStepLegacy(
                step_id="s1",
                description="Research",
                action_type=PlannerActionTypeLegacy.RESEARCH,
            ),
            PlanStepLegacy(
                step_id="s2",
                description="Implement",
                action_type=PlannerActionTypeLegacy.IMPLEMENT,
                dependencies=["s1"],
            ),
        ]
        legacy_plan = DynamicPlanLegacy(
            plan_id="plan-001",
            goal="Complete feature",
            steps=steps,
            facts=["Fact 1", "Fact 2"],
        )

        # Convert to Task Ledger
        task_ledger = convert_legacy_plan_to_task_ledger(legacy_plan)

        # Verify
        assert task_ledger.facts is not None
        assert task_ledger.plan is not None
        assert "Fact 1" in task_ledger.facts.content

        # Convert back
        back_to_plan = convert_task_ledger_to_legacy_plan(
            task_ledger, plan_id="converted-plan"
        )

        # The conversion back may not preserve exact structure
        # but should maintain the core information
        assert back_to_plan.plan_id == "converted-plan"

    @pytest.mark.asyncio
    async def test_manager_adapter_integration(self):
        """測試 Manager 適配器整合。"""
        # Create functions
        async def extract_facts(ctx):
            return [f"Working on: {ctx.task}"]

        async def generate_plan(ctx, facts):
            return [
                PlanStepLegacy(
                    step_id="s1",
                    description="Execute task",
                    action_type=PlannerActionTypeLegacy.IMPLEMENT,
                )
            ]

        async def evaluate_progress(ctx, plan):
            return ProgressEvaluationLegacy(
                is_task_complete=True,
                is_stalled=False,
                progress_score=1.0,
                next_agent=None,
            )

        async def select_next_agent(ctx, progress):
            return None

        async def generate_instruction(ctx, agent, progress):
            return "Task complete"

        # Create adapter
        manager = migrate_dynamic_planner(
            extract_facts_fn=extract_facts,
            generate_plan_fn=generate_plan,
            evaluate_progress_fn=evaluate_progress,
            select_next_agent_fn=select_next_agent,
            generate_instruction_fn=generate_instruction,
        )

        # Create context and test
        context = MagenticContext(task="Integration test")
        ledger = await manager.create_task_ledger(context)

        assert "Integration test" in ledger.facts.content

        # Evaluate progress
        progress = await manager.evaluate_progress(context, ledger)
        assert progress.is_request_satisfied.answer is True
