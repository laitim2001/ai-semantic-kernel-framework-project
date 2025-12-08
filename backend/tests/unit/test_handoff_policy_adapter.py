# =============================================================================
# Test: Handoff Policy Adapter
# =============================================================================
# Sprint 21: S21-1 單元測試
# Phase 4 Feature: Policy Mapping Layer 驗證
#
# 測試涵蓋:
#   - LegacyHandoffPolicy 枚舉
#   - AdaptedPolicyConfig 資料類
#   - HandoffPolicyAdapter 映射方法
#   - 條件評估器 (Condition Evaluators)
#   - 便捷函數 (Convenience Functions)
#
# 驗收標準:
#   - 所有政策類型映射正確
#   - 映射結果可用於官方 API
#   - 錯誤處理測試通過
# =============================================================================

import pytest
from typing import Dict, List

from src.integrations.agent_framework.builders.handoff_policy import (
    LegacyHandoffPolicy,
    AdaptedPolicyConfig,
    HandoffPolicyAdapter,
    create_keyword_condition,
    create_round_limit_condition,
    create_composite_condition,
    adapt_policy,
    adapt_immediate,
    adapt_graceful,
    adapt_conditional,
    adapt_conditional_with_keywords,
)


# =============================================================================
# Test: LegacyHandoffPolicy Enum
# =============================================================================


class TestLegacyHandoffPolicy:
    """測試 LegacyHandoffPolicy 枚舉。"""

    def test_immediate_value(self):
        """驗證 IMMEDIATE 值。"""
        assert LegacyHandoffPolicy.IMMEDIATE.value == "immediate"

    def test_graceful_value(self):
        """驗證 GRACEFUL 值。"""
        assert LegacyHandoffPolicy.GRACEFUL.value == "graceful"

    def test_conditional_value(self):
        """驗證 CONDITIONAL 值。"""
        assert LegacyHandoffPolicy.CONDITIONAL.value == "conditional"

    def test_enum_is_string(self):
        """驗證枚舉繼承自 str。"""
        assert isinstance(LegacyHandoffPolicy.IMMEDIATE, str)
        assert isinstance(LegacyHandoffPolicy.GRACEFUL, str)
        assert isinstance(LegacyHandoffPolicy.CONDITIONAL, str)

    def test_enum_from_string(self):
        """驗證可以從字串創建枚舉。"""
        assert LegacyHandoffPolicy("immediate") == LegacyHandoffPolicy.IMMEDIATE
        assert LegacyHandoffPolicy("graceful") == LegacyHandoffPolicy.GRACEFUL
        assert LegacyHandoffPolicy("conditional") == LegacyHandoffPolicy.CONDITIONAL


# =============================================================================
# Test: AdaptedPolicyConfig
# =============================================================================


class TestAdaptedPolicyConfig:
    """測試 AdaptedPolicyConfig 資料類。"""

    def test_default_values(self):
        """驗證預設值。"""
        config = AdaptedPolicyConfig()
        assert config.interaction_mode == "autonomous"
        assert config.termination_condition is None
        assert config.require_confirmation is False
        assert config.timeout_seconds == 300
        assert config.retry_on_failure is True
        assert config.metadata == {}

    def test_custom_values(self):
        """驗證自訂值。"""
        def custom_condition(conv):
            return True

        config = AdaptedPolicyConfig(
            interaction_mode="human_in_loop",
            termination_condition=custom_condition,
            require_confirmation=True,
            timeout_seconds=600,
            retry_on_failure=False,
            metadata={"key": "value"},
        )
        assert config.interaction_mode == "human_in_loop"
        assert config.termination_condition is custom_condition
        assert config.require_confirmation is True
        assert config.timeout_seconds == 600
        assert config.retry_on_failure is False
        assert config.metadata == {"key": "value"}

    def test_to_dict(self):
        """驗證 to_dict 方法。"""
        config = AdaptedPolicyConfig(
            interaction_mode="autonomous",
            timeout_seconds=120,
            metadata={"test": True},
        )
        result = config.to_dict()
        assert result["interaction_mode"] == "autonomous"
        assert result["termination_condition"] is None
        assert result["require_confirmation"] is False
        assert result["timeout_seconds"] == 120
        assert result["retry_on_failure"] is True
        assert result["metadata"] == {"test": True}


# =============================================================================
# Test: Condition Evaluators
# =============================================================================


class TestKeywordCondition:
    """測試關鍵字條件評估器。"""

    def test_keyword_found(self):
        """驗證關鍵字被找到時返回 True。"""
        condition = create_keyword_condition(["DONE", "TERMINATE"])
        conversation = [{"content": "Task completed. DONE"}]
        assert condition(conversation) is True

    def test_keyword_not_found(self):
        """驗證關鍵字未找到時返回 False。"""
        condition = create_keyword_condition(["DONE", "TERMINATE"])
        conversation = [{"content": "Still working on it..."}]
        assert condition(conversation) is False

    def test_case_insensitive(self):
        """驗證大小寫不敏感。"""
        condition = create_keyword_condition(["DONE"])
        conversation = [{"content": "done"}]
        assert condition(conversation) is True

    def test_case_sensitive(self):
        """驗證大小寫敏感設定。"""
        condition = create_keyword_condition(["DONE"], case_sensitive=True)
        conversation = [{"content": "done"}]
        assert condition(conversation) is False
        conversation = [{"content": "DONE"}]
        assert condition(conversation) is True

    def test_empty_conversation(self):
        """驗證空對話返回 False。"""
        condition = create_keyword_condition(["DONE"])
        assert condition([]) is False

    def test_multiple_messages(self):
        """驗證只檢查最後一條訊息。"""
        condition = create_keyword_condition(["DONE"])
        conversation = [
            {"content": "DONE"},
            {"content": "Wait, still working on it"},
        ]
        assert condition(conversation) is False
        # 最後一條包含關鍵字應返回 True
        conversation.append({"content": "DONE"})
        assert condition(conversation) is True


class TestRoundLimitCondition:
    """測試輪數限制條件評估器。"""

    def test_under_limit(self):
        """驗證未達上限返回 False。"""
        condition = create_round_limit_condition(5)
        conversation = [{"content": "msg1"}, {"content": "msg2"}]
        assert condition(conversation) is False

    def test_at_limit(self):
        """驗證達到上限返回 True。"""
        condition = create_round_limit_condition(3)
        conversation = [
            {"content": "msg1"},
            {"content": "msg2"},
            {"content": "msg3"},
        ]
        assert condition(conversation) is True

    def test_over_limit(self):
        """驗證超過上限返回 True。"""
        condition = create_round_limit_condition(2)
        conversation = [
            {"content": "msg1"},
            {"content": "msg2"},
            {"content": "msg3"},
        ]
        assert condition(conversation) is True


class TestCompositeCondition:
    """測試複合條件評估器。"""

    def test_or_logic_any_true(self):
        """驗證 OR 邏輯 - 任一為 True 則為 True。"""
        condition1 = lambda conv: True
        condition2 = lambda conv: False
        composite = create_composite_condition([condition1, condition2], require_all=False)
        assert composite([]) is True

    def test_or_logic_all_false(self):
        """驗證 OR 邏輯 - 全為 False 則為 False。"""
        condition1 = lambda conv: False
        condition2 = lambda conv: False
        composite = create_composite_condition([condition1, condition2], require_all=False)
        assert composite([]) is False

    def test_and_logic_all_true(self):
        """驗證 AND 邏輯 - 全為 True 則為 True。"""
        condition1 = lambda conv: True
        condition2 = lambda conv: True
        composite = create_composite_condition([condition1, condition2], require_all=True)
        assert composite([]) is True

    def test_and_logic_any_false(self):
        """驗證 AND 邏輯 - 任一為 False 則為 False。"""
        condition1 = lambda conv: True
        condition2 = lambda conv: False
        composite = create_composite_condition([condition1, condition2], require_all=True)
        assert composite([]) is False

    def test_mixed_conditions(self):
        """驗證混合條件評估。"""
        keyword_cond = create_keyword_condition(["DONE"])
        round_cond = create_round_limit_condition(5)
        composite = create_composite_condition([keyword_cond, round_cond], require_all=False)

        # 關鍵字觸發
        assert composite([{"content": "DONE"}]) is True
        # 輪數觸發
        assert composite([{"content": f"msg{i}"} for i in range(5)]) is True
        # 都未觸發
        assert composite([{"content": "working"}]) is False


# =============================================================================
# Test: HandoffPolicyAdapter
# =============================================================================


class TestHandoffPolicyAdapterImmediate:
    """測試 IMMEDIATE 政策適配。"""

    def test_adapt_immediate_enum(self):
        """驗證 IMMEDIATE 枚舉適配。"""
        config = HandoffPolicyAdapter.adapt(LegacyHandoffPolicy.IMMEDIATE)
        assert config.interaction_mode == "autonomous"
        assert config.termination_condition is None
        assert config.require_confirmation is False
        assert config.metadata["policy_type"] == "immediate"

    def test_adapt_immediate_string(self):
        """驗證 IMMEDIATE 字串適配。"""
        config = HandoffPolicyAdapter.adapt("immediate")
        assert config.interaction_mode == "autonomous"
        assert config.termination_condition is None

    def test_adapt_immediate_uppercase(self):
        """驗證大寫字串也能適配。"""
        config = HandoffPolicyAdapter.adapt("IMMEDIATE")
        assert config.interaction_mode == "autonomous"

    def test_adapt_immediate_with_confirmation(self):
        """驗證 IMMEDIATE 可以覆蓋確認設定。"""
        config = HandoffPolicyAdapter.adapt(
            LegacyHandoffPolicy.IMMEDIATE,
            require_confirmation=True,
        )
        assert config.require_confirmation is True


class TestHandoffPolicyAdapterGraceful:
    """測試 GRACEFUL 政策適配。"""

    def test_adapt_graceful_enum(self):
        """驗證 GRACEFUL 枚舉適配。"""
        config = HandoffPolicyAdapter.adapt(LegacyHandoffPolicy.GRACEFUL)
        assert config.interaction_mode == "human_in_loop"
        assert config.termination_condition is None
        assert config.require_confirmation is True
        assert config.metadata["policy_type"] == "graceful"

    def test_adapt_graceful_string(self):
        """驗證 GRACEFUL 字串適配。"""
        config = HandoffPolicyAdapter.adapt("graceful")
        assert config.interaction_mode == "human_in_loop"

    def test_adapt_graceful_with_timeout(self):
        """驗證 GRACEFUL 自訂超時。"""
        config = HandoffPolicyAdapter.adapt(
            LegacyHandoffPolicy.GRACEFUL,
            timeout_seconds=600,
        )
        assert config.timeout_seconds == 600


class TestHandoffPolicyAdapterConditional:
    """測試 CONDITIONAL 政策適配。"""

    def test_adapt_conditional_with_evaluator(self):
        """驗證 CONDITIONAL 帶評估器。"""
        evaluator = lambda conv: "DONE" in conv[-1].get("content", "")
        config = HandoffPolicyAdapter.adapt(
            LegacyHandoffPolicy.CONDITIONAL,
            condition_evaluator=evaluator,
        )
        assert config.interaction_mode == "autonomous"
        assert config.termination_condition is evaluator
        assert config.metadata["policy_type"] == "conditional"

    def test_adapt_conditional_without_evaluator_raises(self):
        """驗證 CONDITIONAL 沒有評估器時拋出錯誤。"""
        with pytest.raises(ValueError) as exc_info:
            HandoffPolicyAdapter.adapt(LegacyHandoffPolicy.CONDITIONAL)
        assert "CONDITIONAL 政策需要提供 condition_evaluator" in str(exc_info.value)

    def test_adapt_conditional_with_defaults(self):
        """驗證使用預設條件適配 CONDITIONAL。"""
        config = HandoffPolicyAdapter.adapt_with_defaults(
            LegacyHandoffPolicy.CONDITIONAL
        )
        assert config.interaction_mode == "autonomous"
        assert config.termination_condition is not None
        # 測試預設關鍵字
        assert config.termination_condition([{"content": "TERMINATE"}]) is True
        assert config.termination_condition([{"content": "DONE"}]) is True
        assert config.termination_condition([{"content": "working"}]) is False

    def test_adapt_conditional_with_custom_keywords(self):
        """驗證自訂關鍵字適配 CONDITIONAL。"""
        config = HandoffPolicyAdapter.adapt_with_defaults(
            LegacyHandoffPolicy.CONDITIONAL,
            termination_keywords=["FINISHED", "COMPLETE"],
        )
        assert config.termination_condition([{"content": "FINISHED"}]) is True
        assert config.termination_condition([{"content": "TERMINATE"}]) is False

    def test_adapt_conditional_with_max_rounds(self):
        """驗證 max_rounds 參數。"""
        config = HandoffPolicyAdapter.adapt_with_defaults(
            LegacyHandoffPolicy.CONDITIONAL,
            max_rounds=3,
        )
        # 輪數觸發
        conversation = [{"content": f"msg{i}"} for i in range(3)]
        assert config.termination_condition(conversation) is True
        # 未達輪數且無關鍵字
        assert config.termination_condition([{"content": "working"}]) is False


class TestHandoffPolicyAdapterErrors:
    """測試錯誤處理。"""

    def test_unknown_policy_string(self):
        """驗證未知政策字串拋出錯誤。"""
        with pytest.raises(ValueError) as exc_info:
            HandoffPolicyAdapter.adapt("unknown_policy")
        assert "未知的 Handoff 政策" in str(exc_info.value)

    def test_unknown_policy_in_defaults(self):
        """驗證 adapt_with_defaults 也會拋出錯誤。"""
        with pytest.raises(ValueError):
            HandoffPolicyAdapter.adapt_with_defaults("bad_policy")


class TestHandoffPolicyAdapterToBuilderKwargs:
    """測試 to_builder_kwargs 方法。"""

    def test_autonomous_mode_kwargs(self):
        """驗證 autonomous 模式的 kwargs。"""
        config = AdaptedPolicyConfig(
            interaction_mode="autonomous",
            termination_condition=None,
        )
        kwargs = HandoffPolicyAdapter.to_builder_kwargs(config)
        # 應該是 AUTONOMOUS mode
        assert kwargs["mode"].value == "autonomous"
        assert kwargs["termination_condition"] is None

    def test_human_in_loop_mode_kwargs(self):
        """驗證 human_in_loop 模式的 kwargs。"""
        config = AdaptedPolicyConfig(
            interaction_mode="human_in_loop",
            termination_condition=None,
        )
        kwargs = HandoffPolicyAdapter.to_builder_kwargs(config)
        # 應該是 HUMAN_IN_LOOP mode
        assert kwargs["mode"].value == "human_in_loop"

    def test_with_termination_condition(self):
        """驗證帶終止條件的 kwargs。"""
        condition = lambda conv: True
        config = AdaptedPolicyConfig(
            interaction_mode="autonomous",
            termination_condition=condition,
        )
        kwargs = HandoffPolicyAdapter.to_builder_kwargs(config)
        assert kwargs["termination_condition"] is condition


# =============================================================================
# Test: Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """測試便捷函數。"""

    def test_adapt_policy(self):
        """驗證 adapt_policy 函數。"""
        config = adapt_policy(LegacyHandoffPolicy.IMMEDIATE)
        assert config.interaction_mode == "autonomous"

        config = adapt_policy("graceful")
        assert config.interaction_mode == "human_in_loop"

    def test_adapt_immediate(self):
        """驗證 adapt_immediate 函數。"""
        config = adapt_immediate()
        assert config.interaction_mode == "autonomous"
        assert config.require_confirmation is False
        assert config.metadata["policy_type"] == "immediate"

    def test_adapt_graceful(self):
        """驗證 adapt_graceful 函數。"""
        config = adapt_graceful()
        assert config.interaction_mode == "human_in_loop"
        assert config.require_confirmation is True

        # 自訂超時
        config = adapt_graceful(timeout_seconds=120)
        assert config.timeout_seconds == 120

    def test_adapt_conditional(self):
        """驗證 adapt_conditional 函數。"""
        condition = lambda conv: True
        config = adapt_conditional(condition)
        assert config.interaction_mode == "autonomous"
        assert config.termination_condition is condition

    def test_adapt_conditional_with_keywords(self):
        """驗證 adapt_conditional_with_keywords 函數。"""
        # 使用預設關鍵字
        config = adapt_conditional_with_keywords()
        assert config.termination_condition([{"content": "DONE"}]) is True

        # 自訂關鍵字
        config = adapt_conditional_with_keywords(keywords=["STOP"])
        assert config.termination_condition([{"content": "STOP"}]) is True
        assert config.termination_condition([{"content": "DONE"}]) is False

        # 帶 max_rounds
        config = adapt_conditional_with_keywords(max_rounds=5)
        conversation = [{"content": f"msg{i}"} for i in range(5)]
        assert config.termination_condition(conversation) is True


# =============================================================================
# Test: Integration with HandoffBuilderAdapter
# =============================================================================


class TestIntegrationWithHandoffBuilder:
    """測試與 HandoffBuilderAdapter 的整合。"""

    def test_immediate_policy_integration(self):
        """驗證 IMMEDIATE 政策可以用於 HandoffBuilderAdapter。"""
        config = adapt_immediate()
        kwargs = HandoffPolicyAdapter.to_builder_kwargs(config)

        # 驗證 kwargs 結構正確
        assert "mode" in kwargs
        assert "termination_condition" in kwargs

    def test_graceful_policy_integration(self):
        """驗證 GRACEFUL 政策可以用於 HandoffBuilderAdapter。"""
        config = adapt_graceful()
        kwargs = HandoffPolicyAdapter.to_builder_kwargs(config)

        # 應該是 human_in_loop 模式
        assert kwargs["mode"].value == "human_in_loop"

    def test_conditional_policy_integration(self):
        """驗證 CONDITIONAL 政策可以用於 HandoffBuilderAdapter。"""
        config = adapt_conditional_with_keywords(
            keywords=["DONE"],
            max_rounds=10,
        )
        kwargs = HandoffPolicyAdapter.to_builder_kwargs(config)

        # 應該有終止條件
        assert kwargs["termination_condition"] is not None
        assert kwargs["mode"].value == "autonomous"


# =============================================================================
# Test: Chinese Keywords Support
# =============================================================================


class TestChineseKeywordsSupport:
    """測試中文關鍵字支援。"""

    def test_default_chinese_keywords(self):
        """驗證預設中文關鍵字。"""
        config = adapt_conditional_with_keywords()
        # 中文「完成」應該觸發
        assert config.termination_condition([{"content": "任務完成"}]) is True
        # 中文「結束」應該觸發
        assert config.termination_condition([{"content": "對話結束"}]) is True

    def test_custom_chinese_keywords(self):
        """驗證自訂中文關鍵字。"""
        config = adapt_conditional_with_keywords(keywords=["任務完成", "交接完畢"])
        assert config.termination_condition([{"content": "任務完成了"}]) is True
        assert config.termination_condition([{"content": "交接完畢"}]) is True
        assert config.termination_condition([{"content": "還在進行"}]) is False


# =============================================================================
# Test: Metadata Preservation
# =============================================================================


class TestMetadataPreservation:
    """測試元數據保存。"""

    def test_custom_metadata(self):
        """驗證自訂元數據被保存。"""
        config = HandoffPolicyAdapter.adapt(
            LegacyHandoffPolicy.IMMEDIATE,
            metadata={"source": "test", "version": "1.0"},
        )
        assert config.metadata["source"] == "test"
        assert config.metadata["version"] == "1.0"
        # 自動添加的 policy_type 也應該存在
        assert config.metadata["policy_type"] == "immediate"

    def test_metadata_in_to_dict(self):
        """驗證元數據在 to_dict 中正確輸出。"""
        config = HandoffPolicyAdapter.adapt(
            LegacyHandoffPolicy.GRACEFUL,
            metadata={"key": "value"},
        )
        result = config.to_dict()
        assert result["metadata"]["key"] == "value"
        assert result["metadata"]["policy_type"] == "graceful"
