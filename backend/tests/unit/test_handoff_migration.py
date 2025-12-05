# =============================================================================
# Unit Tests for HandoffController Migration Layer
# =============================================================================
# Sprint 15: HandoffBuilder 重構 - S15-5 測試
# Phase 3 Feature: P3-F2 (Agent Handoff 重構)
#
# 測試內容:
#   - HandoffPolicyLegacy 枚舉
#   - HandoffStatusLegacy 枚舉
#   - HandoffContextLegacy 數據類
#   - HandoffRequestLegacy 數據類
#   - HandoffResultLegacy 數據類
#   - 狀態轉換函數
#   - HandoffControllerAdapter 類
#   - 遷移工廠函數
# =============================================================================

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.integrations.agent_framework.builders.handoff import (
    HandoffBuilderAdapter,
    HandoffMode,
    HandoffStatus,
)
from src.integrations.agent_framework.builders.handoff_migration import (
    HandoffContextLegacy,
    HandoffControllerAdapter,
    HandoffPolicyLegacy,
    HandoffRequestLegacy,
    HandoffResultLegacy,
    HandoffStatusLegacy,
    convert_policy_to_mode,
    convert_status_from_legacy,
    convert_status_to_legacy,
    create_handoff_controller_adapter,
    migrate_handoff_controller,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def source_agent_id():
    """創建來源 Agent ID."""
    return uuid4()


@pytest.fixture
def target_agent_id():
    """創建目標 Agent ID."""
    return uuid4()


@pytest.fixture
def sample_context():
    """創建示例上下文."""
    return HandoffContextLegacy(
        task_id="task-001",
        task_state={"progress": 50, "variables": {"x": 1}},
        conversation_history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ],
        metadata={"category": "support"},
        priority=5,
        timeout=600,
    )


@pytest.fixture
def controller_adapter():
    """創建控制器適配器."""
    return HandoffControllerAdapter()


# =============================================================================
# Test HandoffPolicyLegacy Enum
# =============================================================================


class TestHandoffPolicyLegacy:
    """HandoffPolicyLegacy 枚舉測試."""

    def test_immediate_value(self):
        """測試 IMMEDIATE 值."""
        assert HandoffPolicyLegacy.IMMEDIATE.value == "immediate"

    def test_graceful_value(self):
        """測試 GRACEFUL 值."""
        assert HandoffPolicyLegacy.GRACEFUL.value == "graceful"

    def test_conditional_value(self):
        """測試 CONDITIONAL 值."""
        assert HandoffPolicyLegacy.CONDITIONAL.value == "conditional"

    def test_enum_count(self):
        """測試枚舉數量."""
        assert len(HandoffPolicyLegacy) == 3

    def test_string_conversion(self):
        """測試字符串轉換."""
        assert HandoffPolicyLegacy("immediate") == HandoffPolicyLegacy.IMMEDIATE


# =============================================================================
# Test HandoffStatusLegacy Enum
# =============================================================================


class TestHandoffStatusLegacy:
    """HandoffStatusLegacy 枚舉測試."""

    def test_all_status_values(self):
        """測試所有狀態值."""
        expected = {
            "initiated", "validating", "transferring",
            "completed", "failed", "cancelled", "rolled_back"
        }
        actual = {s.value for s in HandoffStatusLegacy}
        assert actual == expected

    def test_status_count(self):
        """測試狀態數量."""
        assert len(HandoffStatusLegacy) == 7

    def test_initiated_status(self):
        """測試 INITIATED 狀態."""
        assert HandoffStatusLegacy.INITIATED.value == "initiated"

    def test_rolled_back_status(self):
        """測試 ROLLED_BACK 狀態."""
        assert HandoffStatusLegacy.ROLLED_BACK.value == "rolled_back"


# =============================================================================
# Test HandoffContextLegacy Data Class
# =============================================================================


class TestHandoffContextLegacy:
    """HandoffContextLegacy 數據類測試."""

    def test_basic_creation(self):
        """測試基本創建."""
        context = HandoffContextLegacy(
            task_id="task-1",
            task_state={"key": "value"},
        )
        assert context.task_id == "task-1"
        assert context.task_state == {"key": "value"}
        assert context.conversation_history == []
        assert context.metadata == {}
        assert context.priority == 0
        assert context.timeout == 300

    def test_full_creation(self, sample_context):
        """測試完整創建."""
        assert sample_context.task_id == "task-001"
        assert sample_context.task_state["progress"] == 50
        assert len(sample_context.conversation_history) == 2
        assert sample_context.metadata["category"] == "support"
        assert sample_context.priority == 5
        assert sample_context.timeout == 600


# =============================================================================
# Test HandoffRequestLegacy Data Class
# =============================================================================


class TestHandoffRequestLegacy:
    """HandoffRequestLegacy 數據類測試."""

    def test_default_creation(self):
        """測試默認創建."""
        request = HandoffRequestLegacy()
        assert request.id is not None
        assert isinstance(request.id, UUID)
        assert request.source_agent_id is None
        assert request.target_agent_id is None
        assert request.context is None
        assert request.policy == HandoffPolicyLegacy.GRACEFUL
        assert request.reason == ""
        assert request.conditions == {}
        assert request.created_at is not None

    def test_custom_creation(self, source_agent_id, target_agent_id, sample_context):
        """測試自定義創建."""
        request = HandoffRequestLegacy(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.IMMEDIATE,
            reason="Urgent handoff",
            conditions={"max_turns": 5},
        )
        assert request.source_agent_id == source_agent_id
        assert request.target_agent_id == target_agent_id
        assert request.context == sample_context
        assert request.policy == HandoffPolicyLegacy.IMMEDIATE
        assert request.reason == "Urgent handoff"
        assert request.conditions["max_turns"] == 5


# =============================================================================
# Test HandoffResultLegacy Data Class
# =============================================================================


class TestHandoffResultLegacy:
    """HandoffResultLegacy 數據類測試."""

    def test_basic_creation(self, source_agent_id, target_agent_id):
        """測試基本創建."""
        result = HandoffResultLegacy(
            request_id=uuid4(),
            status=HandoffStatusLegacy.COMPLETED,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
        )
        assert result.status == HandoffStatusLegacy.COMPLETED
        assert result.error is None
        assert result.rollback_performed is False
        assert result.transferred_context == {}

    def test_failed_result(self, source_agent_id, target_agent_id):
        """測試失敗結果."""
        result = HandoffResultLegacy(
            request_id=uuid4(),
            status=HandoffStatusLegacy.FAILED,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            error="Connection failed",
        )
        assert result.status == HandoffStatusLegacy.FAILED
        assert result.error == "Connection failed"

    def test_rolled_back_result(self, source_agent_id, target_agent_id):
        """測試回滾結果."""
        result = HandoffResultLegacy(
            request_id=uuid4(),
            status=HandoffStatusLegacy.ROLLED_BACK,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            rollback_performed=True,
        )
        assert result.status == HandoffStatusLegacy.ROLLED_BACK
        assert result.rollback_performed is True


# =============================================================================
# Test Status Conversion Functions
# =============================================================================


class TestStatusConversion:
    """狀態轉換函數測試."""

    def test_convert_status_to_legacy_pending(self):
        """測試 PENDING 到 INITIATED 轉換."""
        result = convert_status_to_legacy(HandoffStatus.PENDING)
        assert result == HandoffStatusLegacy.INITIATED

    def test_convert_status_to_legacy_running(self):
        """測試 RUNNING 到 TRANSFERRING 轉換."""
        result = convert_status_to_legacy(HandoffStatus.RUNNING)
        assert result == HandoffStatusLegacy.TRANSFERRING

    def test_convert_status_to_legacy_waiting_input(self):
        """測試 WAITING_INPUT 到 VALIDATING 轉換."""
        result = convert_status_to_legacy(HandoffStatus.WAITING_INPUT)
        assert result == HandoffStatusLegacy.VALIDATING

    def test_convert_status_to_legacy_completed(self):
        """測試 COMPLETED 轉換."""
        result = convert_status_to_legacy(HandoffStatus.COMPLETED)
        assert result == HandoffStatusLegacy.COMPLETED

    def test_convert_status_to_legacy_failed(self):
        """測試 FAILED 轉換."""
        result = convert_status_to_legacy(HandoffStatus.FAILED)
        assert result == HandoffStatusLegacy.FAILED

    def test_convert_status_to_legacy_cancelled(self):
        """測試 CANCELLED 轉換."""
        result = convert_status_to_legacy(HandoffStatus.CANCELLED)
        assert result == HandoffStatusLegacy.CANCELLED

    def test_convert_status_from_legacy_initiated(self):
        """測試 INITIATED 到 PENDING 轉換."""
        result = convert_status_from_legacy(HandoffStatusLegacy.INITIATED)
        assert result == HandoffStatus.PENDING

    def test_convert_status_from_legacy_transferring(self):
        """測試 TRANSFERRING 到 RUNNING 轉換."""
        result = convert_status_from_legacy(HandoffStatusLegacy.TRANSFERRING)
        assert result == HandoffStatus.RUNNING

    def test_convert_status_from_legacy_validating(self):
        """測試 VALIDATING 到 RUNNING 轉換."""
        result = convert_status_from_legacy(HandoffStatusLegacy.VALIDATING)
        assert result == HandoffStatus.RUNNING

    def test_convert_status_from_legacy_rolled_back(self):
        """測試 ROLLED_BACK 到 FAILED 轉換."""
        result = convert_status_from_legacy(HandoffStatusLegacy.ROLLED_BACK)
        assert result == HandoffStatus.FAILED


# =============================================================================
# Test Policy to Mode Conversion
# =============================================================================


class TestPolicyToModeConversion:
    """策略到模式轉換測試."""

    def test_immediate_to_autonomous(self):
        """測試 IMMEDIATE 到 AUTONOMOUS 轉換."""
        result = convert_policy_to_mode(HandoffPolicyLegacy.IMMEDIATE)
        assert result == HandoffMode.AUTONOMOUS

    def test_graceful_to_human_in_loop(self):
        """測試 GRACEFUL 到 HUMAN_IN_LOOP 轉換."""
        result = convert_policy_to_mode(HandoffPolicyLegacy.GRACEFUL)
        assert result == HandoffMode.HUMAN_IN_LOOP

    def test_conditional_to_human_in_loop(self):
        """測試 CONDITIONAL 到 HUMAN_IN_LOOP 轉換."""
        result = convert_policy_to_mode(HandoffPolicyLegacy.CONDITIONAL)
        assert result == HandoffMode.HUMAN_IN_LOOP


# =============================================================================
# Test HandoffControllerAdapter Initialization
# =============================================================================


class TestHandoffControllerAdapterInit:
    """HandoffControllerAdapter 初始化測試."""

    def test_basic_init(self):
        """測試基本初始化."""
        adapter = HandoffControllerAdapter()
        assert adapter.active_handoffs == {}
        assert adapter._agent_service is None
        assert adapter._audit is None
        assert adapter._context_transfer is None

    def test_init_with_services(self):
        """測試帶服務初始化."""
        mock_service = MagicMock()
        mock_audit = MagicMock()

        adapter = HandoffControllerAdapter(
            agent_service=mock_service,
            audit_logger=mock_audit,
        )
        assert adapter._agent_service == mock_service
        assert adapter._audit == mock_audit


# =============================================================================
# Test HandoffControllerAdapter Event Handlers
# =============================================================================


class TestHandoffControllerAdapterEvents:
    """HandoffControllerAdapter 事件處理測試."""

    def test_register_completion_handler(self, controller_adapter):
        """測試註冊完成處理器."""
        handler = MagicMock()
        controller_adapter.register_completion_handler(handler)

        assert handler in controller_adapter._on_handoff_complete

    def test_register_failure_handler(self, controller_adapter):
        """測試註冊失敗處理器."""
        handler = MagicMock()
        controller_adapter.register_failure_handler(handler)

        assert handler in controller_adapter._on_handoff_failed


# =============================================================================
# Test HandoffControllerAdapter Initiate Handoff
# =============================================================================


class TestHandoffControllerAdapterInitiate:
    """HandoffControllerAdapter initiate_handoff 測試."""

    @pytest.mark.asyncio
    async def test_initiate_handoff_success(
        self, controller_adapter, source_agent_id, target_agent_id, sample_context
    ):
        """測試成功發起 handoff."""
        request = await controller_adapter.initiate_handoff(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.GRACEFUL,
            reason="Customer needs specialist",
        )

        assert request is not None
        assert request.source_agent_id == source_agent_id
        assert request.target_agent_id == target_agent_id
        assert request.context == sample_context
        assert request.policy == HandoffPolicyLegacy.GRACEFUL
        assert request.reason == "Customer needs specialist"
        assert request.id in controller_adapter.active_handoffs

    @pytest.mark.asyncio
    async def test_initiate_handoff_immediate_policy(
        self, controller_adapter, source_agent_id, target_agent_id, sample_context
    ):
        """測試 IMMEDIATE 策略."""
        request = await controller_adapter.initiate_handoff(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.IMMEDIATE,
        )

        assert request.policy == HandoffPolicyLegacy.IMMEDIATE

    @pytest.mark.asyncio
    async def test_initiate_handoff_conditional_policy(
        self, controller_adapter, source_agent_id, target_agent_id, sample_context
    ):
        """測試 CONDITIONAL 策略."""
        conditions = {"max_turns": 10}
        request = await controller_adapter.initiate_handoff(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.CONDITIONAL,
            conditions=conditions,
        )

        assert request.policy == HandoffPolicyLegacy.CONDITIONAL
        assert request.conditions == conditions

    @pytest.mark.asyncio
    async def test_initiate_handoff_missing_source(
        self, controller_adapter, target_agent_id, sample_context
    ):
        """測試缺少來源 Agent."""
        with pytest.raises(ValueError, match="source_agent_id and target_agent_id are required"):
            await controller_adapter.initiate_handoff(
                source_agent_id=None,
                target_agent_id=target_agent_id,
                context=sample_context,
            )

    @pytest.mark.asyncio
    async def test_initiate_handoff_missing_target(
        self, controller_adapter, source_agent_id, sample_context
    ):
        """測試缺少目標 Agent."""
        with pytest.raises(ValueError, match="source_agent_id and target_agent_id are required"):
            await controller_adapter.initiate_handoff(
                source_agent_id=source_agent_id,
                target_agent_id=None,
                context=sample_context,
            )

    @pytest.mark.asyncio
    async def test_initiate_handoff_same_source_target(
        self, controller_adapter, source_agent_id, sample_context
    ):
        """測試來源等於目標."""
        with pytest.raises(ValueError, match="cannot be the same"):
            await controller_adapter.initiate_handoff(
                source_agent_id=source_agent_id,
                target_agent_id=source_agent_id,
                context=sample_context,
            )


# =============================================================================
# Test HandoffControllerAdapter Execute Handoff
# =============================================================================


class TestHandoffControllerAdapterExecute:
    """HandoffControllerAdapter execute_handoff 測試."""

    @pytest.mark.asyncio
    async def test_execute_handoff_success(
        self, controller_adapter, source_agent_id, target_agent_id, sample_context
    ):
        """測試成功執行 handoff."""
        # 先發起
        request = await controller_adapter.initiate_handoff(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
        )

        # 執行
        result = await controller_adapter.execute_handoff(request)

        assert result is not None
        assert result.request_id == request.id
        assert result.source_agent_id == source_agent_id
        assert result.target_agent_id == target_agent_id
        # 執行後應該從活躍列表中移除
        assert request.id not in controller_adapter.active_handoffs

    @pytest.mark.asyncio
    async def test_execute_handoff_not_initiated(self, controller_adapter):
        """測試執行未發起的 handoff."""
        fake_request = HandoffRequestLegacy(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
        )

        result = await controller_adapter.execute_handoff(fake_request)

        assert result.status == HandoffStatusLegacy.FAILED
        assert "Adapter not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_handoff_completion_handler_called(
        self, controller_adapter, source_agent_id, target_agent_id, sample_context
    ):
        """測試完成處理器被調用."""
        handler = MagicMock()
        controller_adapter.register_completion_handler(handler)

        request = await controller_adapter.initiate_handoff(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
        )

        await controller_adapter.execute_handoff(request)

        handler.assert_called_once()


# =============================================================================
# Test HandoffControllerAdapter Cancel Handoff
# =============================================================================


class TestHandoffControllerAdapterCancel:
    """HandoffControllerAdapter cancel_handoff 測試."""

    @pytest.mark.asyncio
    async def test_cancel_handoff_success(
        self, controller_adapter, source_agent_id, target_agent_id, sample_context
    ):
        """測試成功取消 handoff."""
        request = await controller_adapter.initiate_handoff(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
        )

        result = await controller_adapter.cancel_handoff(request.id)

        assert result is True
        assert request.id not in controller_adapter.active_handoffs

    @pytest.mark.asyncio
    async def test_cancel_handoff_not_found(self, controller_adapter):
        """測試取消不存在的 handoff."""
        fake_id = uuid4()
        result = await controller_adapter.cancel_handoff(fake_id)

        assert result is False


# =============================================================================
# Test HandoffControllerAdapter Get Status
# =============================================================================


class TestHandoffControllerAdapterGetStatus:
    """HandoffControllerAdapter get_handoff_status 測試."""

    @pytest.mark.asyncio
    async def test_get_status_active(
        self, controller_adapter, source_agent_id, target_agent_id, sample_context
    ):
        """測試獲取活躍 handoff 狀態."""
        request = await controller_adapter.initiate_handoff(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
        )

        status = await controller_adapter.get_handoff_status(request.id)

        assert status == HandoffStatusLegacy.TRANSFERRING

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, controller_adapter):
        """測試獲取不存在的 handoff 狀態."""
        fake_id = uuid4()
        status = await controller_adapter.get_handoff_status(fake_id)

        assert status is None


# =============================================================================
# Test Migration Factory Functions
# =============================================================================


class TestMigrationFactoryFunctions:
    """遷移工廠函數測試."""

    def test_migrate_handoff_controller_graceful(
        self, source_agent_id, target_agent_id, sample_context
    ):
        """測試 GRACEFUL 策略遷移."""
        adapter = migrate_handoff_controller(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.GRACEFUL,
        )

        assert adapter is not None
        assert isinstance(adapter, HandoffBuilderAdapter)
        assert adapter.mode == HandoffMode.HUMAN_IN_LOOP
        assert str(source_agent_id) in adapter.participants
        assert str(target_agent_id) in adapter.participants

    def test_migrate_handoff_controller_immediate(
        self, source_agent_id, target_agent_id, sample_context
    ):
        """測試 IMMEDIATE 策略遷移."""
        adapter = migrate_handoff_controller(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.IMMEDIATE,
        )

        assert adapter.mode == HandoffMode.AUTONOMOUS

    def test_migrate_handoff_controller_conditional(
        self, source_agent_id, target_agent_id, sample_context
    ):
        """測試 CONDITIONAL 策略遷移."""
        adapter = migrate_handoff_controller(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.CONDITIONAL,
            conditions={"max_turns": 10},
        )

        assert adapter._termination_condition is not None
        # 測試終止條件
        conversation = [{"role": "user"} for _ in range(10)]
        assert adapter._termination_condition(conversation) is True

    def test_migrate_handoff_controller_with_reason(
        self, source_agent_id, target_agent_id, sample_context
    ):
        """測試帶原因的遷移."""
        adapter = migrate_handoff_controller(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            reason="Specialist needed",
        )

        assert adapter.config["reason"] == "Specialist needed"

    def test_create_handoff_controller_adapter_basic(self):
        """測試創建控制器適配器."""
        adapter = create_handoff_controller_adapter()

        assert adapter is not None
        assert isinstance(adapter, HandoffControllerAdapter)

    def test_create_handoff_controller_adapter_with_services(self):
        """測試帶服務創建控制器適配器."""
        mock_service = MagicMock()
        mock_audit = MagicMock()

        adapter = create_handoff_controller_adapter(
            agent_service=mock_service,
            audit_logger=mock_audit,
        )

        assert adapter._agent_service == mock_service
        assert adapter._audit == mock_audit


# =============================================================================
# Integration Tests
# =============================================================================


class TestMigrationIntegration:
    """遷移整合測試."""

    @pytest.mark.asyncio
    async def test_full_migration_workflow(
        self, source_agent_id, target_agent_id, sample_context
    ):
        """測試完整遷移工作流."""
        # 使用遷移函數創建適配器
        adapter = migrate_handoff_controller(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.GRACEFUL,
            reason="Migration test",
        )

        # 執行
        result = await adapter.run("Test input for migrated handoff")

        # 驗證
        assert result.status == HandoffStatus.COMPLETED
        assert str(source_agent_id) in result.participating_agents

    @pytest.mark.asyncio
    async def test_controller_adapter_full_workflow(
        self, source_agent_id, target_agent_id, sample_context
    ):
        """測試控制器適配器完整工作流."""
        adapter = HandoffControllerAdapter()

        # 發起
        request = await adapter.initiate_handoff(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=sample_context,
            policy=HandoffPolicyLegacy.IMMEDIATE,
            reason="Full workflow test",
        )

        # 驗證請求
        assert request.id in adapter.active_handoffs

        # 執行
        result = await adapter.execute_handoff(request)

        # 驗證結果
        assert result is not None
        assert result.request_id == request.id
        assert "transferred_context" in result.__dict__

    @pytest.mark.asyncio
    async def test_multiple_handoffs(
        self, controller_adapter, sample_context
    ):
        """測試多個並行 handoff."""
        requests = []

        # 創建多個 handoff
        for i in range(3):
            request = await controller_adapter.initiate_handoff(
                source_agent_id=uuid4(),
                target_agent_id=uuid4(),
                context=sample_context,
                reason=f"Handoff {i}",
            )
            requests.append(request)

        assert len(controller_adapter.active_handoffs) == 3

        # 執行所有
        results = []
        for request in requests:
            result = await controller_adapter.execute_handoff(request)
            results.append(result)

        assert len(results) == 3
        assert len(controller_adapter.active_handoffs) == 0
