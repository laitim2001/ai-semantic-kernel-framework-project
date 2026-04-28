# =============================================================================
# Agent Framework Handoff Policy Adapter
# =============================================================================
# Sprint 21: Handoff 完整遷移
# Phase 4 Feature: S21-1 (政策映射層)
#
# 此模組提供 Phase 2 HandoffPolicy 到官方 Agent Framework API 的映射。
#
# 映射關係:
#   - HandoffPolicy.IMMEDIATE → interaction_mode="autonomous"
#   - HandoffPolicy.GRACEFUL → interaction_mode="human_in_loop"
#   - HandoffPolicy.CONDITIONAL → termination_condition=fn
#
# 使用方式:
#   from integrations.agent_framework.builders.handoff_policy import (
#       HandoffPolicyAdapter,
#       adapt_policy,
#   )
#
#   # 適配 Phase 2 政策
#   config = HandoffPolicyAdapter.adapt(HandoffPolicy.GRACEFUL)
#   # 返回: {"interaction_mode": "human_in_loop", "termination_condition": None}
#
# References:
#   - Phase 2 HandoffController: src/domain/orchestration/handoff/controller.py
#   - HandoffBuilderAdapter: src/integrations/agent_framework/builders/handoff.py
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Legacy Policy Enum (從 domain 層重新定義以避免循環依賴)
# =============================================================================


class LegacyHandoffPolicy(str, Enum):
    """
    Phase 2 Handoff 執行政策 (Legacy)。

    從 domain.orchestration.handoff.controller 複製，
    避免在適配器層產生循環依賴。

    Policies:
        IMMEDIATE: 立即轉移，不等待當前任務
        GRACEFUL: 等待當前任務完成後再轉移
        CONDITIONAL: 根據條件評估後決定是否轉移
    """
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    CONDITIONAL = "conditional"


# =============================================================================
# Adapted Policy Configuration
# =============================================================================


@dataclass
class AdaptedPolicyConfig:
    """
    適配後的政策配置。

    可直接用於 HandoffBuilderAdapter 或官方 HandoffBuilder。

    Attributes:
        interaction_mode: 交互模式 ("autonomous" 或 "human_in_loop")
        termination_condition: 終止條件函數 (可選)
        require_confirmation: 是否需要確認
        timeout_seconds: 超時時間 (秒)
        retry_on_failure: 失敗時是否重試
        metadata: 額外的配置元數據
    """
    interaction_mode: str = "autonomous"
    termination_condition: Optional[Callable[[List[Dict]], bool]] = None
    require_confirmation: bool = False
    timeout_seconds: int = 300
    retry_on_failure: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "interaction_mode": self.interaction_mode,
            "termination_condition": self.termination_condition,
            "require_confirmation": self.require_confirmation,
            "timeout_seconds": self.timeout_seconds,
            "retry_on_failure": self.retry_on_failure,
            "metadata": self.metadata,
        }


# =============================================================================
# Condition Evaluators
# =============================================================================


def create_keyword_condition(
    keywords: List[str],
    case_sensitive: bool = False,
) -> Callable[[List[Dict]], bool]:
    """
    創建關鍵字條件評估器。

    當對話中出現指定關鍵字時返回 True。

    Args:
        keywords: 觸發終止的關鍵字列表
        case_sensitive: 是否區分大小寫

    Returns:
        條件評估函數
    """
    def evaluator(conversation: List[Dict]) -> bool:
        if not conversation:
            return False

        last_message = conversation[-1]
        content = str(last_message.get("content", ""))

        if not case_sensitive:
            content = content.lower()
            check_keywords = [k.lower() for k in keywords]
        else:
            check_keywords = keywords

        return any(kw in content for kw in check_keywords)

    return evaluator


def create_round_limit_condition(max_rounds: int) -> Callable[[List[Dict]], bool]:
    """
    創建輪數限制條件評估器。

    當對話輪數達到上限時返回 True。

    Args:
        max_rounds: 最大輪數

    Returns:
        條件評估函數
    """
    def evaluator(conversation: List[Dict]) -> bool:
        return len(conversation) >= max_rounds

    return evaluator


def create_composite_condition(
    conditions: List[Callable[[List[Dict]], bool]],
    require_all: bool = False,
) -> Callable[[List[Dict]], bool]:
    """
    創建複合條件評估器。

    Args:
        conditions: 條件列表
        require_all: True=全部滿足 (AND), False=任一滿足 (OR)

    Returns:
        複合條件評估函數
    """
    def evaluator(conversation: List[Dict]) -> bool:
        if require_all:
            return all(cond(conversation) for cond in conditions)
        else:
            return any(cond(conversation) for cond in conditions)

    return evaluator


# =============================================================================
# Handoff Policy Adapter
# =============================================================================


class HandoffPolicyAdapter:
    """
    Handoff 政策適配器。

    將 Phase 2 的 HandoffPolicy 映射到官方 Agent Framework API 配置。

    映射邏輯:
        - IMMEDIATE: 自主模式，立即執行不等待
        - GRACEFUL: 人機互動模式，需要確認
        - CONDITIONAL: 自主模式，使用條件評估器

    Usage:
        # 基本使用
        config = HandoffPolicyAdapter.adapt(HandoffPolicy.GRACEFUL)

        # 帶條件的使用
        condition = lambda conv: "DONE" in conv[-1].get("content", "")
        config = HandoffPolicyAdapter.adapt(
            HandoffPolicy.CONDITIONAL,
            condition_evaluator=condition,
        )

        # 使用預設條件
        config = HandoffPolicyAdapter.adapt_with_defaults(
            HandoffPolicy.CONDITIONAL,
            termination_keywords=["TERMINATE", "DONE"],
        )
    """

    # 預設終止關鍵字
    DEFAULT_TERMINATION_KEYWORDS = [
        "TERMINATE",
        "DONE",
        "END CONVERSATION",
        "TASK COMPLETE",
        "完成",
        "結束",
    ]

    @staticmethod
    def adapt(
        legacy_policy: Union[LegacyHandoffPolicy, str],
        condition_evaluator: Optional[Callable[[List[Dict]], bool]] = None,
        timeout_seconds: int = 300,
        require_confirmation: bool = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AdaptedPolicyConfig:
        """
        將 Phase 2 HandoffPolicy 適配到官方 API 配置。

        Args:
            legacy_policy: Phase 2 政策 (枚舉或字符串)
            condition_evaluator: CONDITIONAL 政策的條件評估器
            timeout_seconds: 超時時間
            require_confirmation: 是否需要確認 (None=自動決定)
            metadata: 額外元數據

        Returns:
            AdaptedPolicyConfig 配置對象

        Raises:
            ValueError: 如果政策未知或 CONDITIONAL 缺少評估器
        """
        # 標準化政策值
        if isinstance(legacy_policy, str):
            try:
                legacy_policy = LegacyHandoffPolicy(legacy_policy.lower())
            except ValueError:
                raise ValueError(f"未知的 Handoff 政策: {legacy_policy}")

        logger.debug(f"Adapting handoff policy: {legacy_policy.value}")

        config = AdaptedPolicyConfig(
            timeout_seconds=timeout_seconds,
            metadata=metadata or {},
        )

        if legacy_policy == LegacyHandoffPolicy.IMMEDIATE:
            # IMMEDIATE: 自主模式，立即執行
            config.interaction_mode = "autonomous"
            config.termination_condition = None
            config.require_confirmation = (
                require_confirmation if require_confirmation is not None else False
            )
            config.metadata["policy_type"] = "immediate"
            config.metadata["description"] = "立即交接，不等待確認"

        elif legacy_policy == LegacyHandoffPolicy.GRACEFUL:
            # GRACEFUL: 人機互動模式，需要確認
            config.interaction_mode = "human_in_loop"
            config.termination_condition = None
            config.require_confirmation = (
                require_confirmation if require_confirmation is not None else True
            )
            config.metadata["policy_type"] = "graceful"
            config.metadata["description"] = "等待確認後交接"

        elif legacy_policy == LegacyHandoffPolicy.CONDITIONAL:
            # CONDITIONAL: 自主模式，使用條件評估
            if condition_evaluator is None:
                raise ValueError(
                    "CONDITIONAL 政策需要提供 condition_evaluator。"
                    "請使用 adapt_with_defaults() 獲取預設條件，"
                    "或提供自定義條件評估器。"
                )

            config.interaction_mode = "autonomous"
            config.termination_condition = condition_evaluator
            config.require_confirmation = (
                require_confirmation if require_confirmation is not None else False
            )
            config.metadata["policy_type"] = "conditional"
            config.metadata["description"] = "根據條件評估決定交接"

        else:
            raise ValueError(f"未知的 Handoff 政策: {legacy_policy}")

        logger.info(
            f"Policy adapted: {legacy_policy.value} -> "
            f"interaction_mode={config.interaction_mode}"
        )

        return config

    @staticmethod
    def adapt_with_defaults(
        legacy_policy: Union[LegacyHandoffPolicy, str],
        termination_keywords: Optional[List[str]] = None,
        max_rounds: Optional[int] = None,
        timeout_seconds: int = 300,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AdaptedPolicyConfig:
        """
        使用預設值適配 Handoff 政策。

        對於 CONDITIONAL 政策，自動創建條件評估器。

        Args:
            legacy_policy: Phase 2 政策
            termination_keywords: 終止關鍵字 (CONDITIONAL 時使用)
            max_rounds: 最大輪數 (CONDITIONAL 時使用)
            timeout_seconds: 超時時間
            metadata: 額外元數據

        Returns:
            AdaptedPolicyConfig 配置對象
        """
        # 標準化政策值
        if isinstance(legacy_policy, str):
            try:
                legacy_policy = LegacyHandoffPolicy(legacy_policy.lower())
            except ValueError:
                raise ValueError(f"未知的 Handoff 政策: {legacy_policy}")

        condition_evaluator = None

        if legacy_policy == LegacyHandoffPolicy.CONDITIONAL:
            # 創建預設條件評估器
            conditions = []

            # 添加關鍵字條件
            keywords = (
                termination_keywords
                or HandoffPolicyAdapter.DEFAULT_TERMINATION_KEYWORDS
            )
            conditions.append(create_keyword_condition(keywords))

            # 添加輪數限制條件
            if max_rounds:
                conditions.append(create_round_limit_condition(max_rounds))

            # 組合條件 (OR 邏輯)
            condition_evaluator = create_composite_condition(
                conditions,
                require_all=False,
            )

            logger.debug(
                f"Created default condition evaluator with "
                f"{len(keywords)} keywords and max_rounds={max_rounds}"
            )

        return HandoffPolicyAdapter.adapt(
            legacy_policy=legacy_policy,
            condition_evaluator=condition_evaluator,
            timeout_seconds=timeout_seconds,
            metadata=metadata,
        )

    @staticmethod
    def to_builder_kwargs(config: AdaptedPolicyConfig) -> Dict[str, Any]:
        """
        將配置轉換為 HandoffBuilderAdapter 的 kwargs。

        Args:
            config: 適配後的配置

        Returns:
            可用於 HandoffBuilderAdapter 的參數字典
        """
        from .handoff import HandoffMode

        # 映射 interaction_mode 到 HandoffMode
        mode = (
            HandoffMode.HUMAN_IN_LOOP
            if config.interaction_mode == "human_in_loop"
            else HandoffMode.AUTONOMOUS
        )

        return {
            "mode": mode,
            "termination_condition": config.termination_condition,
        }


# =============================================================================
# Convenience Functions
# =============================================================================


def adapt_policy(
    policy: Union[LegacyHandoffPolicy, str],
    **kwargs,
) -> AdaptedPolicyConfig:
    """
    便捷函數：適配 Handoff 政策。

    Args:
        policy: Phase 2 政策
        **kwargs: 傳遞給 adapt() 的額外參數

    Returns:
        AdaptedPolicyConfig 配置對象
    """
    return HandoffPolicyAdapter.adapt(policy, **kwargs)


def adapt_immediate() -> AdaptedPolicyConfig:
    """
    便捷函數：創建 IMMEDIATE 政策配置。

    Returns:
        IMMEDIATE 模式的配置
    """
    return HandoffPolicyAdapter.adapt(LegacyHandoffPolicy.IMMEDIATE)


def adapt_graceful(
    timeout_seconds: int = 300,
) -> AdaptedPolicyConfig:
    """
    便捷函數：創建 GRACEFUL 政策配置。

    Args:
        timeout_seconds: 超時時間

    Returns:
        GRACEFUL 模式的配置
    """
    return HandoffPolicyAdapter.adapt(
        LegacyHandoffPolicy.GRACEFUL,
        timeout_seconds=timeout_seconds,
    )


def adapt_conditional(
    condition: Callable[[List[Dict]], bool],
    timeout_seconds: int = 300,
) -> AdaptedPolicyConfig:
    """
    便捷函數：創建 CONDITIONAL 政策配置。

    Args:
        condition: 條件評估器
        timeout_seconds: 超時時間

    Returns:
        CONDITIONAL 模式的配置
    """
    return HandoffPolicyAdapter.adapt(
        LegacyHandoffPolicy.CONDITIONAL,
        condition_evaluator=condition,
        timeout_seconds=timeout_seconds,
    )


def adapt_conditional_with_keywords(
    keywords: Optional[List[str]] = None,
    max_rounds: Optional[int] = None,
) -> AdaptedPolicyConfig:
    """
    便捷函數：創建帶關鍵字條件的 CONDITIONAL 政策配置。

    Args:
        keywords: 終止關鍵字列表 (None=使用預設)
        max_rounds: 最大輪數 (None=不限制)

    Returns:
        CONDITIONAL 模式的配置
    """
    return HandoffPolicyAdapter.adapt_with_defaults(
        LegacyHandoffPolicy.CONDITIONAL,
        termination_keywords=keywords,
        max_rounds=max_rounds,
    )


# =============================================================================
# 模組導出
# =============================================================================

__all__ = [
    # Enums
    "LegacyHandoffPolicy",
    # Data Classes
    "AdaptedPolicyConfig",
    # Main Adapter
    "HandoffPolicyAdapter",
    # Condition Creators
    "create_keyword_condition",
    "create_round_limit_condition",
    "create_composite_condition",
    # Convenience Functions
    "adapt_policy",
    "adapt_immediate",
    "adapt_graceful",
    "adapt_conditional",
    "adapt_conditional_with_keywords",
]
