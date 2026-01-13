"""
MagenticBuilderAdapter Unit Tests - Sprint 17 (S17-6)

測試 magentic.py 模組的所有組件。

測試覆蓋:
    - MagenticStatus 枚舉
    - HumanInterventionKind 枚舉
    - HumanInterventionDecision 枚舉
    - MessageRole 枚舉
    - MagenticMessage 數據類
    - MagenticParticipant 數據類
    - MagenticContext 數據類
    - TaskLedger 數據類
    - ProgressLedgerItem 數據類
    - ProgressLedger 數據類
    - HumanInterventionRequest 數據類
    - HumanInterventionReply 數據類
    - MagenticRound 數據類
    - MagenticResult 數據類
    - MagenticManagerBase 抽象類
    - StandardMagenticManager 實現
    - MagenticBuilderAdapter 類
    - Factory functions

Author: IPA Platform Team
Sprint: 17 - MagenticBuilder 重構 (Magentic One)
Created: 2025-12-05
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Import modules under test
from src.integrations.agent_framework.builders.magentic import (
    # Enums
    MagenticStatus,
    HumanInterventionKind,
    HumanInterventionDecision,
    MessageRole,
    # Data classes
    MagenticMessage,
    MagenticParticipant,
    MagenticContext,
    TaskLedger,
    ProgressLedgerItem,
    ProgressLedger,
    HumanInterventionRequest,
    HumanInterventionReply,
    MagenticRound,
    MagenticResult,
    # Manager classes
    MagenticManagerBase,
    StandardMagenticManager,
    # Main adapter
    MagenticBuilderAdapter,
    # Factory functions
    create_magentic_adapter,
    create_research_workflow,
    create_coding_workflow,
    # Constants
    MAGENTIC_MANAGER_NAME,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestMagenticStatus:
    """測試 MagenticStatus 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert MagenticStatus.IDLE == "idle"
        assert MagenticStatus.PLANNING == "planning"
        assert MagenticStatus.EXECUTING == "executing"
        assert MagenticStatus.WAITING_APPROVAL == "waiting_approval"
        assert MagenticStatus.STALLED == "stalled"
        assert MagenticStatus.REPLANNING == "replanning"
        assert MagenticStatus.COMPLETED == "completed"
        assert MagenticStatus.FAILED == "failed"
        assert MagenticStatus.CANCELLED == "cancelled"

    def test_enum_from_string(self):
        """測試從字符串創建枚舉。"""
        status = MagenticStatus("planning")
        assert status == MagenticStatus.PLANNING

    def test_enum_str_representation(self):
        """測試字符串表示。"""
        assert str(MagenticStatus.IDLE.value) == "idle"


class TestHumanInterventionKind:
    """測試 HumanInterventionKind 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert HumanInterventionKind.PLAN_REVIEW == "plan_review"
        assert HumanInterventionKind.TOOL_APPROVAL == "tool_approval"
        assert HumanInterventionKind.STALL == "stall"

    def test_enum_from_string(self):
        """測試從字符串創建枚舉。"""
        kind = HumanInterventionKind("plan_review")
        assert kind == HumanInterventionKind.PLAN_REVIEW


class TestHumanInterventionDecision:
    """測試 HumanInterventionDecision 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert HumanInterventionDecision.APPROVE == "approve"
        assert HumanInterventionDecision.REVISE == "revise"
        assert HumanInterventionDecision.REJECT == "reject"
        assert HumanInterventionDecision.CONTINUE == "continue"
        assert HumanInterventionDecision.REPLAN == "replan"
        assert HumanInterventionDecision.GUIDANCE == "guidance"

    def test_enum_from_string(self):
        """測試從字符串創建枚舉。"""
        decision = HumanInterventionDecision("approve")
        assert decision == HumanInterventionDecision.APPROVE


class TestMessageRole:
    """測試 MessageRole 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.MANAGER == "manager"


# =============================================================================
# Data Class Tests
# =============================================================================


class TestMagenticMessage:
    """測試 MagenticMessage 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        msg = MagenticMessage(
            role=MessageRole.USER,
            content="Hello",
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.author_name is None
        assert msg.timestamp is not None

    def test_full_creation(self):
        """測試完整創建。"""
        msg = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content="Response",
            author_name="agent1",
            timestamp=1234567890.0,
            metadata={"key": "value"},
        )
        assert msg.author_name == "agent1"
        assert msg.timestamp == 1234567890.0
        assert msg.metadata["key"] == "value"

    def test_to_dict(self):
        """測試轉換為字典。"""
        msg = MagenticMessage(
            role=MessageRole.USER,
            content="Test",
            author_name="user",
        )
        data = msg.to_dict()
        assert data["role"] == "user"
        assert data["content"] == "Test"
        assert data["author_name"] == "user"

    def test_from_dict(self):
        """測試從字典創建。"""
        data = {
            "role": "assistant",
            "content": "Response",
            "author_name": "agent",
            "timestamp": 1234567890.0,
        }
        msg = MagenticMessage.from_dict(data)
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Response"
        assert msg.author_name == "agent"


class TestMagenticParticipant:
    """測試 MagenticParticipant 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        participant = MagenticParticipant(
            name="researcher",
            description="Research agent",
        )
        assert participant.name == "researcher"
        assert participant.description == "Research agent"
        assert participant.capabilities == []
        assert participant.metadata == {}

    def test_full_creation(self):
        """測試完整創建。"""
        participant = MagenticParticipant(
            name="writer",
            description="Writing agent",
            capabilities=["writing", "editing"],
            metadata={"priority": 1},
        )
        assert participant.name == "writer"
        assert "writing" in participant.capabilities
        assert participant.metadata["priority"] == 1

    def test_empty_name_allowed(self):
        """測試空名稱允許（由適配器層驗證）。"""
        # 實際驗證在 MagenticBuilderAdapter 層面進行
        participant = MagenticParticipant(name="", description="Empty name participant")
        assert participant.name == ""

    def test_to_dict(self):
        """測試轉換為字典。"""
        participant = MagenticParticipant(
            name="test",
            description="Test agent",
            capabilities=["cap1"],
        )
        data = participant.to_dict()
        assert data["name"] == "test"
        assert data["description"] == "Test agent"
        assert data["capabilities"] == ["cap1"]


class TestMagenticContext:
    """測試 MagenticContext 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        task_msg = MagenticMessage(role=MessageRole.USER, content="Complete the research")
        context = MagenticContext(
            task=task_msg,
        )
        assert context.task.content == "Complete the research"
        assert context.chat_history == []
        assert context.participant_descriptions == {}
        assert context.round_count == 0

    def test_full_creation(self):
        """測試完整創建。"""
        task_msg = MagenticMessage(role=MessageRole.USER, content="Task description")
        chat_msg = MagenticMessage(role=MessageRole.USER, content="Test")
        context = MagenticContext(
            task=task_msg,
            chat_history=[chat_msg],
            participant_descriptions={"agent1": "Agent 1 desc"},
            round_count=5,
            stall_count=1,
        )
        assert len(context.chat_history) == 1
        assert context.round_count == 5
        assert context.stall_count == 1

    def test_to_dict(self):
        """測試轉換為字典。"""
        task_msg = MagenticMessage(role=MessageRole.USER, content="Test")
        context = MagenticContext(task=task_msg)
        data = context.to_dict()
        assert data["task"]["content"] == "Test"
        assert data["round_count"] == 0


class TestTaskLedger:
    """測試 TaskLedger 數據類。"""

    def test_creation(self):
        """測試創建。"""
        facts_msg = MagenticMessage(
            role=MessageRole.SYSTEM,
            content="Known facts",
        )
        plan_msg = MagenticMessage(
            role=MessageRole.SYSTEM,
            content="Execution plan",
        )
        ledger = TaskLedger(facts=facts_msg, plan=plan_msg)
        assert ledger.facts.content == "Known facts"
        assert ledger.plan.content == "Execution plan"

    def test_to_dict(self):
        """測試轉換為字典。"""
        facts = MagenticMessage(role=MessageRole.SYSTEM, content="Facts")
        plan = MagenticMessage(role=MessageRole.SYSTEM, content="Plan")
        ledger = TaskLedger(facts=facts, plan=plan)
        data = ledger.to_dict()
        assert "facts" in data
        assert "plan" in data


class TestProgressLedgerItem:
    """測試 ProgressLedgerItem 數據類。"""

    def test_creation_with_bool(self):
        """測試布爾值創建。"""
        item = ProgressLedgerItem(
            reason="Task complete check",
            answer=True,
        )
        assert item.reason == "Task complete check"
        assert item.answer is True

    def test_creation_with_string(self):
        """測試字符串值創建。"""
        item = ProgressLedgerItem(
            reason="Next speaker selection",
            answer="researcher",
        )
        assert item.answer == "researcher"

    def test_to_dict(self):
        """測試轉換為字典。"""
        item = ProgressLedgerItem(reason="Test", answer=False)
        data = item.to_dict()
        assert data["reason"] == "Test"
        assert data["answer"] is False


class TestProgressLedger:
    """測試 ProgressLedger 數據類。"""

    @pytest.fixture
    def sample_ledger(self):
        """創建示例 Progress Ledger。"""
        return ProgressLedger(
            is_request_satisfied=ProgressLedgerItem(
                reason="Not yet complete",
                answer=False,
            ),
            is_in_loop=ProgressLedgerItem(
                reason="No loop detected",
                answer=False,
            ),
            is_progress_being_made=ProgressLedgerItem(
                reason="Progress observed",
                answer=True,
            ),
            next_speaker=ProgressLedgerItem(
                reason="Research needed",
                answer="researcher",
            ),
            instruction_or_question=ProgressLedgerItem(
                reason="Next step",
                answer="Please investigate the topic",
            ),
        )

    def test_creation(self, sample_ledger):
        """測試創建。"""
        assert sample_ledger.is_request_satisfied.answer is False
        assert sample_ledger.is_in_loop.answer is False
        assert sample_ledger.is_progress_being_made.answer is True
        assert sample_ledger.next_speaker.answer == "researcher"

    def test_to_dict(self, sample_ledger):
        """測試轉換為字典。"""
        data = sample_ledger.to_dict()
        assert "is_request_satisfied" in data
        assert "is_in_loop" in data
        assert "next_speaker" in data


class TestHumanInterventionRequest:
    """測試 HumanInterventionRequest 數據類。"""

    def test_creation(self):
        """測試創建。"""
        request = HumanInterventionRequest(
            request_id="req-001",
            kind=HumanInterventionKind.PLAN_REVIEW,
            task_text="Build a web app",
            facts_text="User wants authentication",
            plan_text="1. Design auth\n2. Implement",
        )
        assert request.request_id == "req-001"
        assert request.kind == HumanInterventionKind.PLAN_REVIEW
        assert "authentication" in request.facts_text

    def test_stall_request(self):
        """測試停滯請求。"""
        request = HumanInterventionRequest(
            request_id="req-002",
            kind=HumanInterventionKind.STALL,
            stall_count=3,
            stall_reason="Agent stuck in loop",
            last_agent="researcher",
        )
        assert request.kind == HumanInterventionKind.STALL
        assert request.stall_count == 3

    def test_to_dict(self):
        """測試轉換為字典。"""
        request = HumanInterventionRequest(
            request_id="req-001",
            kind=HumanInterventionKind.TOOL_APPROVAL,
        )
        data = request.to_dict()
        assert data["request_id"] == "req-001"
        assert data["kind"] == "tool_approval"


class TestHumanInterventionReply:
    """測試 HumanInterventionReply 數據類。"""

    def test_approve_reply(self):
        """測試批准回覆。"""
        reply = HumanInterventionReply(
            decision=HumanInterventionDecision.APPROVE,
            comments="Looks good",
        )
        assert reply.decision == HumanInterventionDecision.APPROVE
        assert reply.comments == "Looks good"

    def test_revise_reply(self):
        """測試修訂回覆。"""
        reply = HumanInterventionReply(
            decision=HumanInterventionDecision.REVISE,
            edited_plan_text="1. New step\n2. Another step",
            comments="Please add error handling",
        )
        assert reply.decision == HumanInterventionDecision.REVISE
        assert reply.edited_plan_text is not None

    def test_guidance_reply(self):
        """測試指導回覆。"""
        reply = HumanInterventionReply(
            decision=HumanInterventionDecision.GUIDANCE,
            response_text="Try a different approach",
        )
        assert reply.decision == HumanInterventionDecision.GUIDANCE
        assert reply.response_text is not None

    def test_to_dict(self):
        """測試轉換為字典。"""
        reply = HumanInterventionReply(
            decision=HumanInterventionDecision.APPROVE,
        )
        data = reply.to_dict()
        assert data["decision"] == "approve"


class TestMagenticRound:
    """測試 MagenticRound 數據類。"""

    def test_creation(self):
        """測試創建。"""
        response = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content="Research findings",
            author_name="researcher",
        )
        round_data = MagenticRound(
            round_index=1,
            speaker="researcher",
            instruction="Please research the topic",
            response=response,
            duration_seconds=5.2,
        )
        assert round_data.round_index == 1
        assert round_data.speaker == "researcher"
        assert round_data.duration_seconds == 5.2

    def test_without_response(self):
        """測試無回應的輪次。"""
        round_data = MagenticRound(
            round_index=0,
            speaker="manager",
            instruction="Initialize",
        )
        assert round_data.response is None

    def test_to_dict(self):
        """測試轉換為字典。"""
        round_data = MagenticRound(
            round_index=2,
            speaker="writer",
            instruction="Write content",
        )
        data = round_data.to_dict()
        assert data["round_index"] == 2
        assert data["speaker"] == "writer"


class TestMagenticResult:
    """測試 MagenticResult 數據類。"""

    def test_creation(self):
        """測試創建。"""
        msg = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content="Final answer",
        )
        result = MagenticResult(
            status=MagenticStatus.COMPLETED,
            conversation=[msg],
            rounds=[],
            total_rounds=5,
            total_resets=0,
            participants_involved=["researcher", "writer"],
            duration_seconds=30.0,
        )
        assert result.status == MagenticStatus.COMPLETED
        assert len(result.conversation) == 1
        assert result.total_rounds == 5

    def test_with_final_answer(self):
        """測試帶最終答案的結果。"""
        final = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content="The answer is 42",
        )
        result = MagenticResult(
            status=MagenticStatus.COMPLETED,
            final_answer=final,
            conversation=[],
            rounds=[],
            total_rounds=3,
            duration_seconds=15.0,
        )
        assert result.final_answer is not None
        assert "42" in result.final_answer.content

    def test_failed_result(self):
        """測試失敗結果。"""
        result = MagenticResult(
            status=MagenticStatus.FAILED,
            conversation=[],
            rounds=[],
            total_rounds=1,
            duration_seconds=2.0,
            termination_reason="Max rounds exceeded",
        )
        assert result.status == MagenticStatus.FAILED
        assert result.termination_reason is not None

    def test_to_dict(self):
        """測試轉換為字典。"""
        result = MagenticResult(
            status=MagenticStatus.COMPLETED,
            conversation=[],
            rounds=[],
            total_rounds=0,
            duration_seconds=0.0,
        )
        data = result.to_dict()
        assert data["status"] == "completed"


# =============================================================================
# Manager Tests
# =============================================================================


class TestStandardMagenticManager:
    """測試 StandardMagenticManager 類。"""

    @pytest.fixture
    def mock_agent_executor(self):
        """創建模擬 agent executor。"""
        async def executor(prompt: str) -> str:
            return "Manager response"
        return executor

    def test_creation(self, mock_agent_executor):
        """測試創建。"""
        manager = StandardMagenticManager(agent_executor=mock_agent_executor)
        assert manager._agent_executor == mock_agent_executor

    def test_creation_with_custom_prompts(self, mock_agent_executor):
        """測試自定義提示詞創建。"""
        manager = StandardMagenticManager(
            agent_executor=mock_agent_executor,
            facts_prompt="Custom facts prompt",
            plan_prompt="Custom plan prompt",
        )
        assert manager.facts_prompt == "Custom facts prompt"
        assert manager.plan_prompt == "Custom plan prompt"

    @pytest.mark.asyncio
    async def test_plan(self, mock_agent_executor):
        """測試創建計劃。"""
        manager = StandardMagenticManager(agent_executor=mock_agent_executor)
        task_msg = MagenticMessage(role=MessageRole.USER, content="Test task")
        context = MagenticContext(
            task=task_msg,
            participant_descriptions={"agent1": "Test agent"},
        )

        result = await manager.plan(context)
        assert result is not None
        assert isinstance(result, MagenticMessage)
        assert manager.task_ledger is not None

    @pytest.mark.asyncio
    async def test_create_progress_ledger(self, mock_agent_executor):
        """測試評估進度。"""
        manager = StandardMagenticManager(agent_executor=mock_agent_executor)
        task_msg = MagenticMessage(role=MessageRole.USER, content="Test")
        context = MagenticContext(
            task=task_msg,
            participant_descriptions={"agent1": "Agent 1"},
        )
        # 先創建 task_ledger
        await manager.plan(context)

        progress = await manager.create_progress_ledger(context)
        assert progress is not None
        assert isinstance(progress, ProgressLedger)


# =============================================================================
# Adapter Tests
# =============================================================================


class TestMagenticBuilderAdapter:
    """測試 MagenticBuilderAdapter 類。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            MagenticParticipant(name="researcher", description="Research agent"),
            MagenticParticipant(name="writer", description="Writing agent"),
        ]

    def test_creation(self, sample_participants):
        """測試創建適配器。"""
        adapter = MagenticBuilderAdapter(
            id="test-magentic",
            participants=sample_participants,
        )
        assert adapter.id == "test-magentic"
        assert len(adapter.participants) == 2
        assert adapter.status == MagenticStatus.IDLE

    def test_creation_with_config(self, sample_participants):
        """測試帶配置創建。"""
        adapter = MagenticBuilderAdapter(
            id="test-magentic",
            participants=sample_participants,
            max_round_count=10,
            max_stall_count=5,
            config={"key": "value"},
        )
        assert adapter._max_round_count == 10
        assert adapter._max_stall_count == 5

    def test_empty_participants_raises_error(self):
        """測試空參與者列表拋出錯誤。"""
        with pytest.raises(ValueError, match="At least one participant"):
            MagenticBuilderAdapter(id="test", participants=[])

    def test_empty_id_raises_error(self, sample_participants):
        """測試空 ID 拋出錯誤。"""
        with pytest.raises(ValueError, match="ID cannot be empty"):
            MagenticBuilderAdapter(id="", participants=sample_participants)

    def test_add_participant(self, sample_participants):
        """測試添加參與者。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        new_participant = MagenticParticipant(
            name="reviewer",
            description="Review agent",
        )
        adapter.add_participant(new_participant)
        assert len(adapter.participants) == 3

    def test_add_duplicate_participant_raises_error(self, sample_participants):
        """測試添加重複參與者拋出錯誤。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        duplicate = MagenticParticipant(name="researcher", description="Duplicate")
        with pytest.raises(ValueError, match="already exists"):
            adapter.add_participant(duplicate)

    def test_remove_participant(self, sample_participants):
        """測試移除參與者。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.remove_participant("researcher")
        assert result is True
        assert len(adapter.participants) == 1

    def test_remove_nonexistent_participant(self, sample_participants):
        """測試移除不存在的參與者。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.remove_participant("nonexistent")
        assert result is False

    def test_with_manager(self, sample_participants):
        """測試設置 manager。"""
        async def mock_executor(prompt: str) -> str:
            return "response"
        manager = StandardMagenticManager(agent_executor=mock_executor)
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.with_manager(manager)
        assert result == adapter  # Fluent API
        assert adapter._manager == manager

    def test_with_standard_manager(self, sample_participants):
        """測試設置標準 manager。"""
        async def mock_executor(prompt: str) -> str:
            return "response"
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.with_standard_manager(agent_executor=mock_executor)
        assert result == adapter
        assert adapter._manager is not None
        assert isinstance(adapter._manager, StandardMagenticManager)

    def test_with_plan_review(self, sample_participants):
        """測試啟用計劃審核。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.with_plan_review(True)
        assert result == adapter
        assert adapter._enable_plan_review is True

    def test_with_stall_intervention(self, sample_participants):
        """測試啟用停滯干預。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.with_stall_intervention(True)
        assert result == adapter
        assert adapter._enable_stall_intervention is True

    def test_set_max_round_count(self, sample_participants):
        """測試設置最大輪數。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        adapter.set_max_round_count(30)
        assert adapter._max_round_count == 30

    def test_set_max_stall_count(self, sample_participants):
        """測試設置最大停滯次數。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        adapter.set_max_stall_count(10)
        assert adapter._max_stall_count == 10

    @pytest.mark.asyncio
    async def test_initialize(self, sample_participants):
        """測試初始化。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        await adapter.initialize()
        assert adapter.is_initialized is True

    def test_build(self, sample_participants):
        """測試構建。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        workflow = adapter.build()
        assert workflow is not None
        assert adapter.is_built is True

    def test_build_without_manager_uses_internal(self, sample_participants):
        """測試不設置 manager 時使用內部管理器。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        adapter.build()
        # Should not raise, uses internal simple manager
        assert adapter.is_built is True

    @pytest.mark.asyncio
    async def test_run(self, sample_participants):
        """測試執行。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
            max_round_count=3,
        )
        await adapter.initialize()
        result = await adapter.run("Test task")

        assert result.status == MagenticStatus.COMPLETED
        assert len(result.conversation) > 0
        assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_run_with_timeout(self, sample_participants):
        """測試帶超時執行。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
            max_round_count=100,  # High rounds
        )
        await adapter.initialize()

        # Run with short timeout
        result = await adapter.run("Test task", timeout_seconds=0.1)

        # Should complete or timeout
        assert result.status in [MagenticStatus.COMPLETED, MagenticStatus.TIMEOUT]

    @pytest.mark.asyncio
    async def test_cleanup(self, sample_participants):
        """測試清理。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        await adapter.initialize()
        adapter.build()
        await adapter.cleanup()

        assert adapter.is_initialized is False
        assert adapter.is_built is False

    @pytest.mark.asyncio
    async def test_reset(self, sample_participants):
        """測試重置。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        await adapter.initialize()
        await adapter.run("Test")
        await adapter.reset()

        assert adapter._round_count == 0
        assert adapter._stall_count == 0
        assert adapter.status == MagenticStatus.IDLE

    def test_get_state(self, sample_participants):
        """測試獲取狀態。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        state = adapter.get_state()

        assert "status" in state
        assert "is_built" in state
        assert "is_initialized" in state
        assert "round_count" in state
        assert "participants" in state

    def test_get_ledger_before_run(self, sample_participants):
        """測試執行前獲取 Ledger。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        ledger = adapter.get_ledger()
        assert ledger is None or ledger == {}

    def test_get_events(self, sample_participants):
        """測試獲取事件。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        events = adapter.get_events()
        assert isinstance(events, list)

    def test_clear_events(self, sample_participants):
        """測試清除事件。"""
        adapter = MagenticBuilderAdapter(
            id="test",
            participants=sample_participants,
        )
        adapter._events.append({"type": "test"})
        adapter.clear_events()
        assert len(adapter.get_events()) == 0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """測試工廠函數。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            MagenticParticipant(name="agent1", description="Agent 1"),
            MagenticParticipant(name="agent2", description="Agent 2"),
        ]

    def test_create_magentic_adapter(self, sample_participants):
        """測試 create_magentic_adapter。"""
        adapter = create_magentic_adapter(
            id="test",
            participants=sample_participants,
        )
        assert adapter.id == "test"
        assert len(adapter.participants) == 2

    def test_create_magentic_adapter_with_options(self, sample_participants):
        """測試帶選項創建。"""
        adapter = create_magentic_adapter(
            id="test",
            participants=sample_participants,
            max_round_count=30,
            max_stall_count=5,
        )
        assert adapter._max_round_count == 30
        assert adapter._max_stall_count == 5

    def test_create_research_workflow(self):
        """測試 create_research_workflow。"""
        adapter = create_research_workflow(
            id="research-test",
        )
        assert adapter.id == "research-test"
        # Should have predefined research participants
        participant_names = [p.name for p in adapter.participants]
        assert "researcher" in participant_names or len(participant_names) >= 2

    def test_create_coding_workflow(self):
        """測試 create_coding_workflow。"""
        adapter = create_coding_workflow(
            id="coding-test",
        )
        assert adapter.id == "coding-test"
        # Should have predefined coding participants
        participant_names = [p.name for p in adapter.participants]
        assert len(participant_names) >= 2


# =============================================================================
# Human Intervention Tests
# =============================================================================


class TestHumanIntervention:
    """測試 Human Intervention 功能。"""

    @pytest.fixture
    def adapter_with_plan_review(self):
        """創建帶計劃審核的適配器。"""
        participants = [
            MagenticParticipant(name="agent1", description="Agent 1"),
            MagenticParticipant(name="agent2", description="Agent 2"),
        ]
        adapter = MagenticBuilderAdapter(
            id="intervention-test",
            participants=participants,
        )
        adapter.with_plan_review(True)
        return adapter

    def test_plan_review_enabled(self, adapter_with_plan_review):
        """測試計劃審核已啟用。"""
        assert adapter_with_plan_review._enable_plan_review is True

    @pytest.mark.asyncio
    async def test_respond_to_intervention_approve(self, adapter_with_plan_review):
        """測試批准干預。"""
        await adapter_with_plan_review.initialize()

        # Simulate pending intervention
        adapter_with_plan_review._pending_intervention = HumanInterventionRequest(
            request_id="req-001",
            kind=HumanInterventionKind.PLAN_REVIEW,
            plan_text="Test plan",
        )

        reply = HumanInterventionReply(
            decision=HumanInterventionDecision.APPROVE,
            comments="Approved",
        )

        await adapter_with_plan_review.respond_to_intervention(reply)
        assert adapter_with_plan_review._pending_intervention is None

    @pytest.mark.asyncio
    async def test_respond_to_intervention_no_pending(self, adapter_with_plan_review):
        """測試無待處理干預時回應。"""
        await adapter_with_plan_review.initialize()

        reply = HumanInterventionReply(
            decision=HumanInterventionDecision.APPROVE,
        )

        # Should not raise, just log warning
        await adapter_with_plan_review.respond_to_intervention(reply)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """整合測試。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            MagenticParticipant(
                name="researcher",
                description="Research agent",
                capabilities=["research", "analysis"],
            ),
            MagenticParticipant(
                name="writer",
                description="Writing agent",
                capabilities=["writing", "editing"],
            ),
            MagenticParticipant(
                name="reviewer",
                description="Review agent",
                capabilities=["review", "feedback"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_full_workflow_execution(self, sample_participants):
        """測試完整工作流執行。"""
        adapter = MagenticBuilderAdapter(
            id="full-test",
            participants=sample_participants,
            max_round_count=5,
        )

        await adapter.initialize()
        assert adapter.is_initialized

        result = await adapter.run("Write an article about AI")

        assert result.status == MagenticStatus.COMPLETED
        assert result.total_rounds >= 0
        assert len(result.participants_involved) > 0
        assert result.duration_seconds > 0

        await adapter.cleanup()
        assert not adapter.is_initialized

    @pytest.mark.asyncio
    async def test_context_manager(self, sample_participants):
        """測試上下文管理器。"""
        adapter = MagenticBuilderAdapter(
            id="context-test",
            participants=sample_participants,
        )

        async with adapter:
            assert adapter.is_initialized
            result = await adapter.run("Test task")
            assert result is not None

        assert not adapter.is_initialized

    @pytest.mark.asyncio
    async def test_state_tracking(self, sample_participants):
        """測試狀態追蹤。"""
        adapter = MagenticBuilderAdapter(
            id="state-test",
            participants=sample_participants,
            max_round_count=3,
        )

        await adapter.initialize()
        assert adapter.status == MagenticStatus.IDLE

        result = await adapter.run("Test task")

        # 執行後應該是 COMPLETED
        assert adapter.status == MagenticStatus.COMPLETED

        # 狀態應該被追蹤
        state = adapter.get_state()
        assert state["round_count"] > 0

    @pytest.mark.asyncio
    async def test_multiple_runs(self, sample_participants):
        """測試多次執行。"""
        adapter = MagenticBuilderAdapter(
            id="multi-run-test",
            participants=sample_participants,
            max_round_count=2,
        )

        await adapter.initialize()

        # First run
        result1 = await adapter.run("First task")
        assert result1.status == MagenticStatus.COMPLETED

        # Reset and second run
        await adapter.reset()
        result2 = await adapter.run("Second task")
        assert result2.status == MagenticStatus.COMPLETED
