# =============================================================================
# Agent Framework Handoff Context Transfer Adapter
# =============================================================================
# Sprint 21: Handoff 完整遷移
# Phase 4 Feature: S21-3 (ContextTransfer 整合)
#
# 此模組提供 Phase 2 ContextTransferManager 到官方 Agent Framework API 的整合。
# 在適配器層保留上下文傳輸功能，支持 Agent 間的完整上下文轉移。
#
# 設計原則:
#   - 複製關鍵資料類以避免循環依賴
#   - 提供統一的上下文傳輸接口
#   - 支持與 HandoffBuilderAdapter 整合
#
# 核心功能:
#   - TransferContextInfo: 傳輸上下文資料
#   - ContextTransferAdapter: 上下文傳輸適配器
#   - 上下文提取、轉換、驗證、注入
#
# 使用方式:
#   from integrations.agent_framework.builders.handoff_context import (
#       ContextTransferAdapter,
#       TransferContextInfo,
#   )
#
#   # 創建適配器
#   transfer = ContextTransferAdapter()
#
#   # 提取上下文
#   context = transfer.extract_context(task_id="task-1", task_state={...})
#
#   # 轉換上下文
#   transformed = transfer.transform_context(context, rules=[...])
#
#   # 驗證上下文
#   is_valid = transfer.validate_context(context)
#
# References:
#   - Phase 2 ContextTransfer: src/domain/orchestration/handoff/context_transfer.py
#   - HandoffBuilderAdapter: src/integrations/agent_framework/builders/handoff.py
# =============================================================================

from __future__ import annotations

import copy
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class ContextTransferError(Exception):
    """
    上下文傳輸錯誤。

    Attributes:
        message: 錯誤訊息
        field: 相關欄位名稱
        details: 詳細資訊
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.field = field
        self.details = details or {}


class ContextValidationError(ContextTransferError):
    """上下文驗證錯誤。"""
    pass


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TransferContextInfo:
    """
    傳輸上下文資料。

    Attributes:
        task_id: 任務識別碼
        task_state: 任務狀態字典
        conversation_history: 對話歷史列表
        metadata: 額外元數據
        source_agent_id: 來源 Agent ID
        target_agent_id: 目標 Agent ID
        handoff_reason: Handoff 原因
        timestamp: 提取時間戳
        checksum: 校驗碼
    """
    task_id: str
    task_state: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_agent_id: Optional[str] = None
    target_agent_id: Optional[str] = None
    handoff_reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "task_id": self.task_id,
            "task_state": self.task_state,
            "conversation_history": self.conversation_history,
            "metadata": self.metadata,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "handoff_reason": self.handoff_reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransferContextInfo":
        """從字典創建實例。"""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            task_id=data.get("task_id", ""),
            task_state=data.get("task_state", {}),
            conversation_history=data.get("conversation_history", []),
            metadata=data.get("metadata", {}),
            source_agent_id=data.get("source_agent_id"),
            target_agent_id=data.get("target_agent_id"),
            handoff_reason=data.get("handoff_reason", ""),
            timestamp=timestamp,
            checksum=data.get("checksum"),
        )


@dataclass
class TransformationRuleInfo:
    """
    上下文轉換規則。

    Attributes:
        source_field: 來源欄位
        target_field: 目標欄位
        transformer: 轉換函數
        required: 是否為必需欄位
    """
    source_field: str
    target_field: str
    transformer: Optional[Callable[[Any], Any]] = None
    required: bool = False


@dataclass
class TransferResult:
    """
    傳輸結果。

    Attributes:
        success: 是否成功
        context: 傳輸的上下文
        errors: 錯誤列表
        warnings: 警告列表
    """
    success: bool = True
    context: Optional[TransferContextInfo] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# Context Transfer Adapter
# =============================================================================


class ContextTransferAdapter:
    """
    上下文傳輸適配器。

    將 Phase 2 的 ContextTransferManager 功能封裝為適配器，
    可與 HandoffBuilderAdapter 整合使用。

    功能:
        - 上下文提取
        - 上下文轉換
        - 上下文驗證
        - 上下文注入

    Usage:
        adapter = ContextTransferAdapter()

        # 提取上下文
        context = adapter.extract_context(
            task_id="task-1",
            task_state={"status": "in_progress"},
        )

        # 驗證
        is_valid = adapter.validate_context(context)

        # 傳輸
        result = adapter.transfer_context(context, target_agent_id="agent-2")
    """

    # 預設必需欄位
    DEFAULT_REQUIRED_FIELDS: Set[str] = {"task_id", "task_state"}

    # 最大對話歷史長度
    DEFAULT_MAX_HISTORY_LENGTH: int = 100

    # 最大上下文大小 (10 MB)
    DEFAULT_MAX_CONTEXT_SIZE: int = 10 * 1024 * 1024

    def __init__(
        self,
        required_fields: Optional[Set[str]] = None,
        max_history_length: Optional[int] = None,
        max_context_size: Optional[int] = None,
    ):
        """
        初始化上下文傳輸適配器。

        Args:
            required_fields: 必需欄位集合
            max_history_length: 最大對話歷史長度
            max_context_size: 最大上下文大小 (bytes)
        """
        self._required_fields = required_fields or self.DEFAULT_REQUIRED_FIELDS.copy()
        self._max_history_length = max_history_length or self.DEFAULT_MAX_HISTORY_LENGTH
        self._max_context_size = max_context_size or self.DEFAULT_MAX_CONTEXT_SIZE

        # 自定義驗證器
        self._validators: List[Callable[[TransferContextInfo], None]] = []

        # 自定義轉換器
        self._transformers: List[Callable[[TransferContextInfo], TransferContextInfo]] = []

        logger.info("ContextTransferAdapter initialized")

    # =========================================================================
    # Validator and Transformer Registration
    # =========================================================================

    def register_validator(
        self,
        validator: Callable[[TransferContextInfo], None],
    ) -> None:
        """
        註冊自定義驗證器。

        Args:
            validator: 驗證函數，驗證失敗時拋出 ContextValidationError
        """
        self._validators.append(validator)

    def register_transformer(
        self,
        transformer: Callable[[TransferContextInfo], TransferContextInfo],
    ) -> None:
        """
        註冊自定義轉換器。

        Args:
            transformer: 轉換函數，返回轉換後的上下文
        """
        self._transformers.append(transformer)

    # =========================================================================
    # Context Extraction
    # =========================================================================

    def extract_context(
        self,
        task_id: str,
        task_state: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_agent_id: Optional[str] = None,
        handoff_reason: str = "",
    ) -> TransferContextInfo:
        """
        提取上下文。

        Args:
            task_id: 任務識別碼
            task_state: 任務狀態
            conversation_history: 對話歷史
            metadata: 元數據
            source_agent_id: 來源 Agent ID
            handoff_reason: Handoff 原因

        Returns:
            TransferContextInfo 實例
        """
        context = TransferContextInfo(
            task_id=task_id,
            task_state=task_state or {},
            conversation_history=conversation_history or [],
            metadata=metadata or {},
            source_agent_id=source_agent_id,
            handoff_reason=handoff_reason,
            timestamp=datetime.utcnow(),
        )

        # 計算校驗碼
        context.checksum = self._calculate_checksum(context)

        logger.debug(
            f"Context extracted: task_id={task_id}, "
            f"state_keys={len(context.task_state)}, "
            f"history_length={len(context.conversation_history)}"
        )

        return context

    def extract_from_dict(self, data: Dict[str, Any]) -> TransferContextInfo:
        """
        從字典提取上下文。

        Args:
            data: 上下文數據字典

        Returns:
            TransferContextInfo 實例
        """
        context = TransferContextInfo.from_dict(data)
        context.checksum = self._calculate_checksum(context)
        return context

    # =========================================================================
    # Context Transformation
    # =========================================================================

    def transform_context(
        self,
        context: TransferContextInfo,
        rules: Optional[List[TransformationRuleInfo]] = None,
    ) -> TransferContextInfo:
        """
        轉換上下文。

        Args:
            context: 原始上下文
            rules: 轉換規則列表

        Returns:
            轉換後的上下文
        """
        logger.debug(f"Transforming context for task {context.task_id}")

        # 深拷貝以避免修改原始數據
        transformed = copy.deepcopy(context)

        # 應用明確規則
        if rules:
            for rule in rules:
                transformed = self._apply_rule(transformed, rule)

        # 應用註冊的轉換器
        for transformer in self._transformers:
            transformed = transformer(transformed)

        # 截斷過長的對話歷史
        if len(transformed.conversation_history) > self._max_history_length:
            transformed.conversation_history = transformed.conversation_history[
                -self._max_history_length:
            ]
            logger.debug(
                f"Trimmed conversation history to {self._max_history_length} entries"
            )

        # 更新時間戳
        transformed.timestamp = datetime.utcnow()

        # 重新計算校驗碼
        transformed.checksum = self._calculate_checksum(transformed)

        return transformed

    def _apply_rule(
        self,
        context: TransferContextInfo,
        rule: TransformationRuleInfo,
    ) -> TransferContextInfo:
        """
        應用單個轉換規則。

        Args:
            context: 上下文
            rule: 轉換規則

        Returns:
            轉換後的上下文
        """
        source_value = context.task_state.get(rule.source_field)

        if source_value is None and rule.required:
            raise ContextTransferError(
                f"Required field '{rule.source_field}' not found in task_state",
                field=rule.source_field,
            )

        if source_value is not None:
            # 轉換值
            if rule.transformer:
                try:
                    transformed_value = rule.transformer(source_value)
                except Exception as e:
                    raise ContextTransferError(
                        f"Transformation failed for field '{rule.source_field}': {e}",
                        field=rule.source_field,
                    )
            else:
                transformed_value = source_value

            # 設置目標值
            context.task_state[rule.target_field] = transformed_value

            # 如果來源和目標不同，移除來源
            if rule.source_field != rule.target_field:
                del context.task_state[rule.source_field]

        return context

    # =========================================================================
    # Context Validation
    # =========================================================================

    def validate_context(
        self,
        context: TransferContextInfo,
        strict: bool = True,
    ) -> bool:
        """
        驗證上下文。

        Args:
            context: 要驗證的上下文
            strict: 嚴格模式下驗證失敗會拋出異常

        Returns:
            是否有效

        Raises:
            ContextValidationError: 嚴格模式下驗證失敗
        """
        logger.debug(f"Validating context for task {context.task_id}")

        errors: List[str] = []

        # 檢查必需欄位
        for field_name in self._required_fields:
            value = getattr(context, field_name, None)
            if value is None or (isinstance(value, dict) and not value):
                errors.append(f"Required field '{field_name}' is missing or empty")

        # 檢查 task_id
        if not context.task_id or not isinstance(context.task_id, str):
            errors.append("task_id must be a non-empty string")

        # 檢查 task_state
        if not isinstance(context.task_state, dict):
            errors.append("task_state must be a dictionary")

        # 檢查 conversation_history
        if not isinstance(context.conversation_history, list):
            errors.append("conversation_history must be a list")

        # 檢查大小
        try:
            size = len(json.dumps(context.to_dict(), default=str))
            if size > self._max_context_size:
                errors.append(
                    f"Context size ({size} bytes) exceeds maximum "
                    f"({self._max_context_size} bytes)"
                )
        except Exception as e:
            errors.append(f"Context is not JSON serializable: {e}")

        # 執行自定義驗證器
        for validator in self._validators:
            try:
                validator(context)
            except ContextValidationError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Validator failed: {e}")

        if errors:
            logger.warning(f"Context validation failed: {errors}")
            if strict:
                raise ContextValidationError(
                    f"Context validation failed with {len(errors)} error(s)",
                    details={"errors": errors},
                )
            return False

        logger.debug("Context validation passed")
        return True

    # =========================================================================
    # Context Transfer
    # =========================================================================

    def transfer_context(
        self,
        context: TransferContextInfo,
        target_agent_id: str,
        validate: bool = True,
    ) -> TransferResult:
        """
        傳輸上下文到目標 Agent。

        Args:
            context: 要傳輸的上下文
            target_agent_id: 目標 Agent ID
            validate: 是否在傳輸前驗證

        Returns:
            TransferResult 結果
        """
        result = TransferResult()

        try:
            # 驗證
            if validate:
                self.validate_context(context, strict=True)

            # 更新目標 Agent ID
            context.target_agent_id = target_agent_id

            result.success = True
            result.context = context

            logger.info(
                f"Context transferred to agent {target_agent_id}: "
                f"task_id={context.task_id}"
            )

        except ContextValidationError as e:
            result.success = False
            result.errors = e.details.get("errors", [str(e)])
            logger.error(f"Context transfer failed: {e}")

        except Exception as e:
            result.success = False
            result.errors = [str(e)]
            logger.error(f"Unexpected error during transfer: {e}")

        return result

    def prepare_handoff_context(
        self,
        task_id: str,
        source_agent_id: str,
        target_agent_id: str,
        task_state: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        handoff_reason: str = "",
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> TransferResult:
        """
        準備 Handoff 上下文。

        一站式方法：提取、轉換、驗證、準備傳輸。

        Args:
            task_id: 任務 ID
            source_agent_id: 來源 Agent ID
            target_agent_id: 目標 Agent ID
            task_state: 任務狀態
            conversation_history: 對話歷史
            handoff_reason: Handoff 原因
            additional_metadata: 額外元數據

        Returns:
            TransferResult 結果
        """
        result = TransferResult()

        try:
            # 提取上下文
            context = self.extract_context(
                task_id=task_id,
                task_state=task_state,
                conversation_history=conversation_history,
                metadata=additional_metadata or {},
                source_agent_id=source_agent_id,
                handoff_reason=handoff_reason,
            )

            # 轉換 (應用註冊的轉換器)
            context = self.transform_context(context)

            # 驗證
            self.validate_context(context, strict=True)

            # 設置目標
            context.target_agent_id = target_agent_id

            result.success = True
            result.context = context

            logger.info(
                f"Handoff context prepared: {source_agent_id} -> {target_agent_id}, "
                f"task_id={task_id}"
            )

        except ContextValidationError as e:
            result.success = False
            result.errors = e.details.get("errors", [str(e)])

        except Exception as e:
            result.success = False
            result.errors = [str(e)]

        return result

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _calculate_checksum(self, context: TransferContextInfo) -> str:
        """
        計算上下文校驗碼。

        Args:
            context: 上下文

        Returns:
            16 字元的校驗碼
        """
        content = json.dumps(
            {
                "task_id": context.task_id,
                "task_state": context.task_state,
                "conversation_history": context.conversation_history,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def verify_checksum(self, context: TransferContextInfo) -> bool:
        """
        驗證上下文校驗碼。

        Args:
            context: 上下文

        Returns:
            校驗碼是否匹配
        """
        if not context.checksum:
            return True  # 沒有校驗碼則跳過驗證

        expected = self._calculate_checksum(context)
        return context.checksum == expected

    def merge_contexts(
        self,
        contexts: List[TransferContextInfo],
        merge_strategy: str = "latest",
    ) -> TransferContextInfo:
        """
        合併多個上下文。

        Args:
            contexts: 上下文列表
            merge_strategy: 合併策略 ("latest", "combine")

        Returns:
            合併後的上下文
        """
        if not contexts:
            raise ContextTransferError("Cannot merge empty context list")

        if len(contexts) == 1:
            return copy.deepcopy(contexts[0])

        if merge_strategy == "latest":
            # 使用最新的上下文，按時間戳排序
            sorted_contexts = sorted(
                contexts,
                key=lambda c: c.timestamp or datetime.min,
                reverse=True,
            )
            merged = copy.deepcopy(sorted_contexts[0])

        elif merge_strategy == "combine":
            # 合併所有上下文
            merged = TransferContextInfo(
                task_id=contexts[0].task_id,
                task_state={},
                conversation_history=[],
                metadata={},
                timestamp=datetime.utcnow(),
            )

            for ctx in contexts:
                # 合併 task_state
                merged.task_state.update(ctx.task_state)

                # 合併對話歷史
                merged.conversation_history.extend(ctx.conversation_history)

                # 合併元數據
                merged.metadata.update(ctx.metadata)

            # 截斷過長的歷史
            if len(merged.conversation_history) > self._max_history_length:
                merged.conversation_history = merged.conversation_history[
                    -self._max_history_length:
                ]

        else:
            raise ContextTransferError(f"Unknown merge strategy: {merge_strategy}")

        # 重新計算校驗碼
        merged.checksum = self._calculate_checksum(merged)

        return merged

    @property
    def required_fields(self) -> Set[str]:
        """獲取必需欄位集合。"""
        return self._required_fields.copy()

    @property
    def max_history_length(self) -> int:
        """獲取最大對話歷史長度。"""
        return self._max_history_length

    @property
    def max_context_size(self) -> int:
        """獲取最大上下文大小。"""
        return self._max_context_size


# =============================================================================
# Factory Functions
# =============================================================================


def create_context_transfer_adapter(
    required_fields: Optional[Set[str]] = None,
    max_history_length: Optional[int] = None,
    max_context_size: Optional[int] = None,
) -> ContextTransferAdapter:
    """
    創建上下文傳輸適配器。

    Args:
        required_fields: 必需欄位集合
        max_history_length: 最大對話歷史長度
        max_context_size: 最大上下文大小

    Returns:
        ContextTransferAdapter 實例
    """
    return ContextTransferAdapter(
        required_fields=required_fields,
        max_history_length=max_history_length,
        max_context_size=max_context_size,
    )


def create_transfer_context(
    task_id: str,
    task_state: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    **kwargs,
) -> TransferContextInfo:
    """
    便捷函數：創建傳輸上下文。

    Args:
        task_id: 任務 ID
        task_state: 任務狀態
        conversation_history: 對話歷史
        **kwargs: 其他參數

    Returns:
        TransferContextInfo 實例
    """
    return TransferContextInfo(
        task_id=task_id,
        task_state=task_state or {},
        conversation_history=conversation_history or [],
        **kwargs,
    )


def create_transformation_rule(
    source_field: str,
    target_field: str,
    transformer: Optional[Callable[[Any], Any]] = None,
    required: bool = False,
) -> TransformationRuleInfo:
    """
    便捷函數：創建轉換規則。

    Args:
        source_field: 來源欄位
        target_field: 目標欄位
        transformer: 轉換函數
        required: 是否為必需

    Returns:
        TransformationRuleInfo 實例
    """
    return TransformationRuleInfo(
        source_field=source_field,
        target_field=target_field,
        transformer=transformer,
        required=required,
    )


# =============================================================================
# 模組導出
# =============================================================================

__all__ = [
    # Exceptions
    "ContextTransferError",
    "ContextValidationError",
    # Data Classes
    "TransferContextInfo",
    "TransformationRuleInfo",
    "TransferResult",
    # Main Adapter
    "ContextTransferAdapter",
    # Factory Functions
    "create_context_transfer_adapter",
    "create_transfer_context",
    "create_transformation_rule",
]
