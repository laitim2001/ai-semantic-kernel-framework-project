# =============================================================================
# Test: Handoff Context Transfer Adapter
# =============================================================================
# Sprint 21: S21-3 單元測試
# Phase 4 Feature: ContextTransfer 整合驗證
#
# 測試涵蓋:
#   - TransferContextInfo 資料類
#   - TransformationRuleInfo 資料類
#   - ContextTransferAdapter 核心功能
#   - 上下文提取、轉換、驗證、傳輸
#   - 校驗碼計算和驗證
#
# 驗收標準:
#   - 上下文提取功能正確
#   - 轉換規則正確應用
#   - 驗證邏輯正確運作
#   - 傳輸結果正確返回
# =============================================================================

import pytest
from datetime import datetime
from typing import Dict, List, Any

from src.integrations.agent_framework.builders.handoff_context import (
    # Exceptions
    ContextTransferError,
    ContextValidationError,
    # Data Classes
    TransferContextInfo,
    TransformationRuleInfo,
    TransferResult,
    # Main Adapter
    ContextTransferAdapter,
    # Factory Functions
    create_context_transfer_adapter,
    create_transfer_context,
    create_transformation_rule,
)


# =============================================================================
# Test: TransferContextInfo
# =============================================================================


class TestTransferContextInfo:
    """測試 TransferContextInfo 資料類。"""

    def test_default_values(self):
        """驗證預設值。"""
        context = TransferContextInfo(task_id="task-1")
        assert context.task_id == "task-1"
        assert context.task_state == {}
        assert context.conversation_history == []
        assert context.metadata == {}
        assert context.source_agent_id is None
        assert context.target_agent_id is None
        assert context.handoff_reason == ""
        assert context.timestamp is not None
        assert context.checksum is None

    def test_custom_values(self):
        """驗證自訂值。"""
        context = TransferContextInfo(
            task_id="task-1",
            task_state={"status": "running"},
            conversation_history=[{"role": "user", "content": "hello"}],
            metadata={"key": "value"},
            source_agent_id="agent-1",
            target_agent_id="agent-2",
            handoff_reason="escalation",
        )
        assert context.task_state == {"status": "running"}
        assert len(context.conversation_history) == 1
        assert context.metadata == {"key": "value"}
        assert context.source_agent_id == "agent-1"

    def test_to_dict(self):
        """驗證 to_dict 方法。"""
        context = TransferContextInfo(
            task_id="task-1",
            task_state={"status": "running"},
        )
        result = context.to_dict()
        assert result["task_id"] == "task-1"
        assert result["task_state"] == {"status": "running"}
        assert "timestamp" in result

    def test_from_dict(self):
        """驗證 from_dict 方法。"""
        data = {
            "task_id": "task-1",
            "task_state": {"status": "running"},
            "conversation_history": [{"role": "user", "content": "hi"}],
            "timestamp": "2025-01-01T00:00:00",
        }
        context = TransferContextInfo.from_dict(data)
        assert context.task_id == "task-1"
        assert context.task_state == {"status": "running"}
        assert len(context.conversation_history) == 1
        assert context.timestamp.year == 2025


# =============================================================================
# Test: TransformationRuleInfo
# =============================================================================


class TestTransformationRuleInfo:
    """測試 TransformationRuleInfo 資料類。"""

    def test_default_values(self):
        """驗證預設值。"""
        rule = TransformationRuleInfo(
            source_field="field_a",
            target_field="field_b",
        )
        assert rule.source_field == "field_a"
        assert rule.target_field == "field_b"
        assert rule.transformer is None
        assert rule.required is False

    def test_with_transformer(self):
        """驗證帶轉換函數的規則。"""
        transformer = lambda x: x.upper()
        rule = TransformationRuleInfo(
            source_field="name",
            target_field="NAME",
            transformer=transformer,
            required=True,
        )
        assert rule.transformer is transformer
        assert rule.required is True


# =============================================================================
# Test: TransferResult
# =============================================================================


class TestTransferResult:
    """測試 TransferResult 資料類。"""

    def test_default_values(self):
        """驗證預設值。"""
        result = TransferResult()
        assert result.success is True
        assert result.context is None
        assert result.errors == []
        assert result.warnings == []

    def test_failure_result(self):
        """驗證失敗結果。"""
        result = TransferResult(
            success=False,
            errors=["Error 1", "Error 2"],
        )
        assert result.success is False
        assert len(result.errors) == 2


# =============================================================================
# Test: ContextTransferAdapter - Extraction
# =============================================================================


class TestContextTransferAdapterExtraction:
    """測試上下文提取功能。"""

    def test_extract_context_basic(self):
        """驗證基本上下文提取。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
        )

        assert context.task_id == "task-1"
        assert context.task_state == {"status": "running"}
        assert context.checksum is not None

    def test_extract_context_full(self):
        """驗證完整上下文提取。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
            conversation_history=[
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            metadata={"priority": "high"},
            source_agent_id="agent-1",
            handoff_reason="escalation",
        )

        assert context.task_id == "task-1"
        assert len(context.conversation_history) == 2
        assert context.metadata == {"priority": "high"}
        assert context.source_agent_id == "agent-1"
        assert context.handoff_reason == "escalation"

    def test_extract_from_dict(self):
        """驗證從字典提取上下文。"""
        adapter = ContextTransferAdapter()
        data = {
            "task_id": "task-1",
            "task_state": {"key": "value"},
        }
        context = adapter.extract_from_dict(data)

        assert context.task_id == "task-1"
        assert context.checksum is not None


# =============================================================================
# Test: ContextTransferAdapter - Transformation
# =============================================================================


class TestContextTransferAdapterTransformation:
    """測試上下文轉換功能。"""

    def test_transform_context_no_rules(self):
        """驗證無規則轉換。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
        )

        transformed = adapter.transform_context(context)
        assert transformed.task_id == "task-1"
        assert transformed.task_state == {"status": "running"}

    def test_transform_context_with_rule(self):
        """驗證帶規則轉換。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"old_field": "value"},
        )

        rules = [
            TransformationRuleInfo(
                source_field="old_field",
                target_field="new_field",
            )
        ]
        transformed = adapter.transform_context(context, rules=rules)

        assert "new_field" in transformed.task_state
        assert "old_field" not in transformed.task_state
        assert transformed.task_state["new_field"] == "value"

    def test_transform_context_with_transformer(self):
        """驗證帶轉換函數的規則。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"name": "test"},
        )

        rules = [
            TransformationRuleInfo(
                source_field="name",
                target_field="NAME",
                transformer=lambda x: x.upper(),
            )
        ]
        transformed = adapter.transform_context(context, rules=rules)

        assert transformed.task_state["NAME"] == "TEST"

    def test_transform_context_trims_history(self):
        """驗證截斷過長歷史。"""
        adapter = ContextTransferAdapter(max_history_length=5)
        history = [{"content": f"msg-{i}"} for i in range(10)]
        context = adapter.extract_context(
            task_id="task-1",
            conversation_history=history,
        )

        transformed = adapter.transform_context(context)
        assert len(transformed.conversation_history) == 5

    def test_transform_required_field_missing(self):
        """驗證缺少必需欄位時拋出錯誤。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(task_id="task-1")

        rules = [
            TransformationRuleInfo(
                source_field="missing_field",
                target_field="target",
                required=True,
            )
        ]

        with pytest.raises(ContextTransferError) as exc_info:
            adapter.transform_context(context, rules=rules)
        assert "missing_field" in str(exc_info.value)

    def test_custom_transformer(self):
        """驗證自定義轉換器。"""
        def custom_transformer(ctx: TransferContextInfo) -> TransferContextInfo:
            ctx.metadata["transformed"] = True
            return ctx

        adapter = ContextTransferAdapter()
        adapter.register_transformer(custom_transformer)

        context = adapter.extract_context(task_id="task-1")
        transformed = adapter.transform_context(context)

        assert transformed.metadata.get("transformed") is True


# =============================================================================
# Test: ContextTransferAdapter - Validation
# =============================================================================


class TestContextTransferAdapterValidation:
    """測試上下文驗證功能。"""

    def test_validate_valid_context(self):
        """驗證有效上下文通過驗證。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
        )

        is_valid = adapter.validate_context(context)
        assert is_valid is True

    def test_validate_missing_task_id(self):
        """驗證缺少 task_id 時失敗。"""
        adapter = ContextTransferAdapter()
        context = TransferContextInfo(task_id="")

        with pytest.raises(ContextValidationError):
            adapter.validate_context(context, strict=True)

    def test_validate_missing_required_field(self):
        """驗證缺少必需欄位時失敗。"""
        adapter = ContextTransferAdapter(required_fields={"task_id", "task_state"})
        context = TransferContextInfo(task_id="task-1")

        # task_state 是空字典，應該失敗
        result = adapter.validate_context(context, strict=False)
        assert result is False

    def test_validate_non_strict_returns_false(self):
        """驗證非嚴格模式返回 False 而非拋出異常。"""
        adapter = ContextTransferAdapter()
        context = TransferContextInfo(task_id="")

        result = adapter.validate_context(context, strict=False)
        assert result is False

    def test_validate_context_size(self):
        """驗證上下文大小限制。"""
        adapter = ContextTransferAdapter(max_context_size=100)
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"data": "x" * 200},
        )

        with pytest.raises(ContextValidationError) as exc_info:
            adapter.validate_context(context, strict=True)
        # 錯誤詳情在 details 中
        errors = exc_info.value.details.get("errors", [])
        assert any("exceeds maximum" in str(e) for e in errors)

    def test_custom_validator(self):
        """驗證自定義驗證器。"""
        def custom_validator(ctx: TransferContextInfo) -> None:
            if ctx.task_state.get("invalid"):
                raise ContextValidationError("Invalid task state")

        adapter = ContextTransferAdapter()
        adapter.register_validator(custom_validator)

        context = adapter.extract_context(
            task_id="task-1",
            task_state={"invalid": True},
        )

        with pytest.raises(ContextValidationError):
            adapter.validate_context(context, strict=True)


# =============================================================================
# Test: ContextTransferAdapter - Transfer
# =============================================================================


class TestContextTransferAdapterTransfer:
    """測試上下文傳輸功能。"""

    def test_transfer_success(self):
        """驗證成功傳輸。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
        )

        result = adapter.transfer_context(context, target_agent_id="agent-2")
        assert result.success is True
        assert result.context is not None
        assert result.context.target_agent_id == "agent-2"

    def test_transfer_with_validation(self):
        """驗證帶驗證的傳輸。"""
        adapter = ContextTransferAdapter()
        context = TransferContextInfo(task_id="")  # 無效上下文

        result = adapter.transfer_context(context, target_agent_id="agent-2")
        assert result.success is False
        assert len(result.errors) > 0

    def test_transfer_skip_validation(self):
        """驗證跳過驗證的傳輸。"""
        adapter = ContextTransferAdapter()
        context = TransferContextInfo(task_id="")  # 無效上下文

        result = adapter.transfer_context(
            context, target_agent_id="agent-2", validate=False
        )
        assert result.success is True

    def test_prepare_handoff_context_success(self):
        """驗證準備 Handoff 上下文成功。"""
        adapter = ContextTransferAdapter()
        result = adapter.prepare_handoff_context(
            task_id="task-1",
            source_agent_id="agent-1",
            target_agent_id="agent-2",
            task_state={"status": "running"},
            handoff_reason="escalation",
        )

        assert result.success is True
        assert result.context.source_agent_id == "agent-1"
        assert result.context.target_agent_id == "agent-2"
        assert result.context.handoff_reason == "escalation"

    def test_prepare_handoff_context_with_history(self):
        """驗證準備帶歷史的 Handoff 上下文。"""
        adapter = ContextTransferAdapter()
        result = adapter.prepare_handoff_context(
            task_id="task-1",
            source_agent_id="agent-1",
            target_agent_id="agent-2",
            task_state={"status": "running"},
            conversation_history=[
                {"role": "user", "content": "help me"},
            ],
        )

        assert result.success is True
        assert len(result.context.conversation_history) == 1


# =============================================================================
# Test: ContextTransferAdapter - Checksum
# =============================================================================


class TestContextTransferAdapterChecksum:
    """測試校驗碼功能。"""

    def test_checksum_calculated(self):
        """驗證校驗碼被計算。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
        )

        assert context.checksum is not None
        assert len(context.checksum) == 16

    def test_checksum_verified(self):
        """驗證校驗碼驗證成功。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
        )

        is_valid = adapter.verify_checksum(context)
        assert is_valid is True

    def test_checksum_verification_fails(self):
        """驗證校驗碼驗證失敗。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
        )

        # 修改數據後校驗碼應該不匹配
        context.task_state["modified"] = True

        is_valid = adapter.verify_checksum(context)
        assert is_valid is False

    def test_checksum_none_skips_verification(self):
        """驗證無校驗碼時跳過驗證。"""
        adapter = ContextTransferAdapter()
        context = TransferContextInfo(task_id="task-1", checksum=None)

        is_valid = adapter.verify_checksum(context)
        assert is_valid is True


# =============================================================================
# Test: ContextTransferAdapter - Merge
# =============================================================================


class TestContextTransferAdapterMerge:
    """測試上下文合併功能。"""

    def test_merge_single_context(self):
        """驗證合併單個上下文。"""
        adapter = ContextTransferAdapter()
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "running"},
        )

        merged = adapter.merge_contexts([context])
        assert merged.task_id == "task-1"

    def test_merge_latest_strategy(self):
        """驗證 latest 策略。"""
        adapter = ContextTransferAdapter()
        context1 = adapter.extract_context(
            task_id="task-1",
            task_state={"version": 1},
        )
        context2 = adapter.extract_context(
            task_id="task-1",
            task_state={"version": 2},
        )

        merged = adapter.merge_contexts(
            [context1, context2],
            merge_strategy="latest",
        )
        assert merged.task_state["version"] == 2

    def test_merge_combine_strategy(self):
        """驗證 combine 策略。"""
        adapter = ContextTransferAdapter()
        context1 = adapter.extract_context(
            task_id="task-1",
            task_state={"key1": "value1"},
            conversation_history=[{"content": "msg1"}],
        )
        context2 = adapter.extract_context(
            task_id="task-1",
            task_state={"key2": "value2"},
            conversation_history=[{"content": "msg2"}],
        )

        merged = adapter.merge_contexts(
            [context1, context2],
            merge_strategy="combine",
        )
        assert merged.task_state.get("key1") == "value1"
        assert merged.task_state.get("key2") == "value2"
        assert len(merged.conversation_history) == 2

    def test_merge_empty_list_raises(self):
        """驗證空列表拋出錯誤。"""
        adapter = ContextTransferAdapter()

        with pytest.raises(ContextTransferError):
            adapter.merge_contexts([])

    def test_merge_unknown_strategy_raises(self):
        """驗證未知策略拋出錯誤。"""
        adapter = ContextTransferAdapter()
        # 需要多個上下文才會觸發策略邏輯（單個上下文直接返回副本）
        context1 = adapter.extract_context(task_id="task-1")
        context2 = adapter.extract_context(task_id="task-1")

        with pytest.raises(ContextTransferError):
            adapter.merge_contexts([context1, context2], merge_strategy="unknown")


# =============================================================================
# Test: Factory Functions
# =============================================================================


class TestContextFactoryFunctions:
    """測試工廠函數。"""

    def test_create_context_transfer_adapter(self):
        """驗證創建適配器。"""
        adapter = create_context_transfer_adapter()
        assert isinstance(adapter, ContextTransferAdapter)

    def test_create_context_transfer_adapter_with_options(self):
        """驗證創建帶選項的適配器。"""
        adapter = create_context_transfer_adapter(
            required_fields={"task_id"},
            max_history_length=50,
            max_context_size=1024,
        )
        assert adapter.max_history_length == 50
        assert adapter.max_context_size == 1024

    def test_create_transfer_context(self):
        """驗證創建傳輸上下文。"""
        context = create_transfer_context(
            task_id="task-1",
            task_state={"status": "running"},
        )
        assert context.task_id == "task-1"
        assert context.task_state == {"status": "running"}

    def test_create_transformation_rule(self):
        """驗證創建轉換規則。"""
        rule = create_transformation_rule(
            source_field="old",
            target_field="new",
            required=True,
        )
        assert rule.source_field == "old"
        assert rule.target_field == "new"
        assert rule.required is True


# =============================================================================
# Test: Properties
# =============================================================================


class TestContextTransferAdapterProperties:
    """測試適配器屬性。"""

    def test_required_fields_property(self):
        """驗證 required_fields 屬性。"""
        adapter = ContextTransferAdapter(
            required_fields={"task_id", "custom_field"}
        )
        fields = adapter.required_fields
        assert "task_id" in fields
        assert "custom_field" in fields

    def test_max_history_length_property(self):
        """驗證 max_history_length 屬性。"""
        adapter = ContextTransferAdapter(max_history_length=20)
        assert adapter.max_history_length == 20

    def test_max_context_size_property(self):
        """驗證 max_context_size 屬性。"""
        adapter = ContextTransferAdapter(max_context_size=5000)
        assert adapter.max_context_size == 5000
