# =============================================================================
# Agent Framework HandoffController Migration Layer
# =============================================================================
# Sprint 15: HandoffBuilder 重構
# Phase 3 Feature: P3-F2 (Agent Handoff 重構) - S15-2
#
# 此模組提供 Phase 2 HandoffController 到 Agent Framework HandoffBuilder
# 的遷移適配層，確保現有 API 向後兼容。
#
# 遷移映射:
#   - HandoffPolicy.IMMEDIATE → HandoffMode.AUTONOMOUS
#   - HandoffPolicy.GRACEFUL → HandoffMode.HUMAN_IN_LOOP
#   - HandoffPolicy.CONDITIONAL → termination_condition
#   - HandoffContext → 轉換為對話格式
#   - HandoffRequest → 適配到 HandoffBuilderAdapter
#   - HandoffResult → HandoffExecutionResult
#
# 使用方式:
#   # 使用 Phase 2 API 創建
#   adapter = migrate_handoff_controller(
#       source_agent_id=uuid1,
#       target_agent_id=uuid2,
#       context=HandoffContextLegacy(...),
#       policy=HandoffPolicyLegacy.GRACEFUL,
#   )
#   result = await adapter.run(input_data)
#
# References:
#   - Phase 2 HandoffController: src/domain/orchestration/handoff/controller.py
#   - HandoffBuilderAdapter: builders/handoff.py
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from .handoff import (
    HandoffBuilderAdapter,
    HandoffExecutionResult,
    HandoffMode,
    HandoffStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 2 API Compatibility Types
# =============================================================================


class HandoffPolicyLegacy(str, Enum):
    """
    Phase 2 HandoffPolicy (保留向後兼容).

    與 HandoffMode 的映射:
        IMMEDIATE → AUTONOMOUS
        GRACEFUL → HUMAN_IN_LOOP
        CONDITIONAL → 使用 termination_condition
    """
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    CONDITIONAL = "conditional"


class HandoffStatusLegacy(str, Enum):
    """
    Phase 2 HandoffStatus (保留向後兼容).

    保留所有原有狀態以確保兼容:
        INITIATED → PENDING
        VALIDATING → RUNNING
        TRANSFERRING → RUNNING
        COMPLETED → COMPLETED
        FAILED → FAILED
        CANCELLED → CANCELLED
        ROLLED_BACK → FAILED (with rollback flag)
    """
    INITIATED = "initiated"
    VALIDATING = "validating"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


@dataclass
class HandoffContextLegacy:
    """
    Phase 2 HandoffContext (保留向後兼容).

    Attributes:
        task_id: 任務 ID
        task_state: 任務狀態 (變量、進度等)
        conversation_history: 對話歷史
        metadata: 額外元數據
        priority: 優先級
        timeout: 超時時間 (秒)
    """
    task_id: str
    task_state: Dict[str, Any]
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout: int = 300


@dataclass
class HandoffRequestLegacy:
    """
    Phase 2 HandoffRequest (保留向後兼容).

    Attributes:
        id: 請求 ID
        source_agent_id: 來源 Agent ID
        target_agent_id: 目標 Agent ID
        context: 傳輸的上下文
        policy: 執行策略
        reason: Handoff 原因
        conditions: 條件 (用於 CONDITIONAL 策略)
        created_at: 創建時間
    """
    id: UUID = field(default_factory=uuid4)
    source_agent_id: Optional[UUID] = None
    target_agent_id: Optional[UUID] = None
    context: Optional[HandoffContextLegacy] = None
    policy: HandoffPolicyLegacy = HandoffPolicyLegacy.GRACEFUL
    reason: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HandoffResultLegacy:
    """
    Phase 2 HandoffResult (保留向後兼容).

    Attributes:
        request_id: 請求 ID
        status: 最終狀態
        source_agent_id: 來源 Agent ID
        target_agent_id: 目標 Agent ID
        started_at: 開始時間
        completed_at: 完成時間
        duration_ms: 持續時間 (毫秒)
        error: 錯誤信息
        rollback_performed: 是否執行了回滾
        transferred_context: 已傳輸的上下文摘要
    """
    request_id: UUID
    status: HandoffStatusLegacy
    source_agent_id: UUID
    target_agent_id: UUID
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    rollback_performed: bool = False
    transferred_context: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Status Conversion
# =============================================================================


def convert_status_to_legacy(status: HandoffStatus) -> HandoffStatusLegacy:
    """
    將 HandoffStatus 轉換為 HandoffStatusLegacy.

    Args:
        status: 新的 HandoffStatus

    Returns:
        HandoffStatusLegacy
    """
    mapping = {
        HandoffStatus.PENDING: HandoffStatusLegacy.INITIATED,
        HandoffStatus.RUNNING: HandoffStatusLegacy.TRANSFERRING,
        HandoffStatus.WAITING_INPUT: HandoffStatusLegacy.VALIDATING,
        HandoffStatus.COMPLETED: HandoffStatusLegacy.COMPLETED,
        HandoffStatus.FAILED: HandoffStatusLegacy.FAILED,
        HandoffStatus.CANCELLED: HandoffStatusLegacy.CANCELLED,
    }
    return mapping.get(status, HandoffStatusLegacy.FAILED)


def convert_status_from_legacy(status: HandoffStatusLegacy) -> HandoffStatus:
    """
    將 HandoffStatusLegacy 轉換為 HandoffStatus.

    Args:
        status: Legacy HandoffStatusLegacy

    Returns:
        HandoffStatus
    """
    mapping = {
        HandoffStatusLegacy.INITIATED: HandoffStatus.PENDING,
        HandoffStatusLegacy.VALIDATING: HandoffStatus.RUNNING,
        HandoffStatusLegacy.TRANSFERRING: HandoffStatus.RUNNING,
        HandoffStatusLegacy.COMPLETED: HandoffStatus.COMPLETED,
        HandoffStatusLegacy.FAILED: HandoffStatus.FAILED,
        HandoffStatusLegacy.CANCELLED: HandoffStatus.CANCELLED,
        HandoffStatusLegacy.ROLLED_BACK: HandoffStatus.FAILED,
    }
    return mapping.get(status, HandoffStatus.FAILED)


def convert_policy_to_mode(policy: HandoffPolicyLegacy) -> HandoffMode:
    """
    將 HandoffPolicyLegacy 轉換為 HandoffMode.

    Mapping:
        IMMEDIATE → AUTONOMOUS
        GRACEFUL → HUMAN_IN_LOOP
        CONDITIONAL → HUMAN_IN_LOOP (with termination_condition)

    Args:
        policy: Phase 2 HandoffPolicy

    Returns:
        HandoffMode
    """
    if policy == HandoffPolicyLegacy.IMMEDIATE:
        return HandoffMode.AUTONOMOUS
    elif policy == HandoffPolicyLegacy.GRACEFUL:
        return HandoffMode.HUMAN_IN_LOOP
    else:  # CONDITIONAL
        return HandoffMode.HUMAN_IN_LOOP


# =============================================================================
# HandoffControllerAdapter
# =============================================================================


class HandoffControllerAdapter:
    """
    Phase 2 HandoffController 的適配器.

    提供與 Phase 2 HandoffController 相同的 API，
    但底層使用 HandoffBuilderAdapter 實現。

    Usage:
        adapter = HandoffControllerAdapter()

        request = await adapter.initiate_handoff(
            source_agent_id=uuid1,
            target_agent_id=uuid2,
            context=HandoffContextLegacy(task_id="task-1", task_state={}),
            policy=HandoffPolicyLegacy.GRACEFUL,
        )

        result = await adapter.execute_handoff(request)

    Attributes:
        active_handoffs: 活躍的 handoff 請求
        handoff_states: Handoff 狀態追蹤
    """

    def __init__(
        self,
        agent_service: Any = None,
        audit_logger: Any = None,
        context_transfer_manager: Any = None,
    ) -> None:
        """
        初始化 HandoffControllerAdapter.

        Args:
            agent_service: Agent 服務 (兼容 Phase 2)
            audit_logger: 審計日誌記錄器
            context_transfer_manager: 上下文傳輸管理器
        """
        self._agent_service = agent_service
        self._audit = audit_logger
        self._context_transfer = context_transfer_manager

        # 活躍的 handoff 追蹤
        self._active_handoffs: Dict[UUID, HandoffRequestLegacy] = {}
        self._handoff_adapters: Dict[UUID, HandoffBuilderAdapter] = {}

        # 事件處理器
        self._on_handoff_complete: List[Callable] = []
        self._on_handoff_failed: List[Callable] = []

        logger.info("HandoffControllerAdapter initialized")

    @property
    def active_handoffs(self) -> Dict[UUID, HandoffRequestLegacy]:
        """獲取活躍的 handoff 請求."""
        return self._active_handoffs.copy()

    def register_completion_handler(self, handler: Callable) -> None:
        """註冊完成事件處理器."""
        self._on_handoff_complete.append(handler)

    def register_failure_handler(self, handler: Callable) -> None:
        """註冊失敗事件處理器."""
        self._on_handoff_failed.append(handler)

    async def initiate_handoff(
        self,
        source_agent_id: UUID,
        target_agent_id: UUID,
        context: HandoffContextLegacy,
        policy: HandoffPolicyLegacy = HandoffPolicyLegacy.GRACEFUL,
        reason: str = "",
        conditions: Dict[str, Any] = None,
    ) -> HandoffRequestLegacy:
        """
        發起 handoff 請求 (Phase 2 API).

        Args:
            source_agent_id: 來源 Agent ID
            target_agent_id: 目標 Agent ID
            context: 傳輸的上下文
            policy: 執行策略
            reason: Handoff 原因
            conditions: 條件 (用於 CONDITIONAL 策略)

        Returns:
            HandoffRequestLegacy

        Raises:
            ValueError: 如果參數無效
        """
        if not source_agent_id or not target_agent_id:
            raise ValueError("Both source_agent_id and target_agent_id are required")

        if source_agent_id == target_agent_id:
            raise ValueError("Source and target agents cannot be the same")

        # 創建 Legacy 請求
        request = HandoffRequestLegacy(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=context,
            policy=policy,
            reason=reason,
            conditions=conditions or {},
        )

        # 創建底層 HandoffBuilderAdapter
        mode = convert_policy_to_mode(policy)

        # 準備參與者
        participants = {
            str(source_agent_id): self._create_agent_executor(source_agent_id),
            str(target_agent_id): self._create_agent_executor(target_agent_id),
        }

        # 創建終止條件 (用於 CONDITIONAL 策略)
        termination_condition = None
        if policy == HandoffPolicyLegacy.CONDITIONAL and conditions:
            termination_condition = self._create_termination_condition(conditions)

        adapter = HandoffBuilderAdapter(
            id=str(request.id),
            participants=participants,
            coordinator_id=str(source_agent_id),
            mode=mode,
            termination_condition=termination_condition,
            config={
                "legacy_request_id": str(request.id),
                "reason": reason,
                "priority": context.priority if context else 0,
                "timeout": context.timeout if context else 300,
            },
        )

        # 添加 handoff 路由
        adapter.add_handoff(str(source_agent_id), str(target_agent_id))

        # 追蹤
        self._active_handoffs[request.id] = request
        self._handoff_adapters[request.id] = adapter

        logger.info(
            f"Handoff initiated: {request.id} "
            f"from {source_agent_id} to {target_agent_id} "
            f"policy={policy.value}"
        )

        return request

    async def execute_handoff(
        self,
        request: HandoffRequestLegacy,
    ) -> HandoffResultLegacy:
        """
        執行 handoff 請求 (Phase 2 API).

        Args:
            request: Handoff 請求

        Returns:
            HandoffResultLegacy
        """
        adapter = self._handoff_adapters.get(request.id)
        if not adapter:
            return HandoffResultLegacy(
                request_id=request.id,
                status=HandoffStatusLegacy.FAILED,
                source_agent_id=request.source_agent_id,
                target_agent_id=request.target_agent_id,
                error="Adapter not found. Did you call initiate_handoff first?",
            )

        # 準備輸入
        input_data = self._prepare_input(request)

        # 執行
        execution_result = await adapter.run(input_data)

        # 轉換結果
        result = self._convert_result(request, execution_result)

        # 清理
        self._cleanup_handoff(request.id)

        # 通知處理器
        if result.status == HandoffStatusLegacy.COMPLETED:
            await self._notify_completion(result)
        else:
            await self._notify_failure(result)

        return result

    async def cancel_handoff(self, handoff_id: UUID) -> bool:
        """
        取消活躍的 handoff (Phase 2 API).

        Args:
            handoff_id: Handoff ID

        Returns:
            True 如果取消成功
        """
        if handoff_id not in self._active_handoffs:
            logger.warning(f"Cannot cancel: handoff {handoff_id} not found")
            return False

        self._cleanup_handoff(handoff_id)
        logger.info(f"Handoff cancelled: {handoff_id}")
        return True

    async def get_handoff_status(
        self,
        handoff_id: UUID,
    ) -> Optional[HandoffStatusLegacy]:
        """
        獲取 handoff 狀態 (Phase 2 API).

        Args:
            handoff_id: Handoff ID

        Returns:
            HandoffStatusLegacy 或 None
        """
        if handoff_id in self._active_handoffs:
            return HandoffStatusLegacy.TRANSFERRING
        return None

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _create_agent_executor(self, agent_id: UUID) -> Any:
        """
        創建 Agent 執行器.

        Args:
            agent_id: Agent ID

        Returns:
            執行器實例 (或模擬對象)
        """
        # 如果有 agent_service，嘗試獲取實際執行器
        if self._agent_service:
            # TODO: 整合實際 agent_service
            pass

        # 返回模擬執行器
        return {"agent_id": str(agent_id), "type": "mock_executor"}

    def _create_termination_condition(
        self,
        conditions: Dict[str, Any],
    ) -> Callable[[List[Dict]], bool]:
        """
        創建終止條件函數.

        Args:
            conditions: 條件字典

        Returns:
            終止條件函數
        """
        def termination_check(conversation: List[Dict]) -> bool:
            # 評估條件
            # TODO: 實現完整的條件評估邏輯
            if "max_turns" in conditions:
                return len(conversation) >= conditions["max_turns"]
            return False

        return termination_check

    def _prepare_input(self, request: HandoffRequestLegacy) -> Dict[str, Any]:
        """
        準備執行輸入.

        Args:
            request: Handoff 請求

        Returns:
            輸入數據字典
        """
        if not request.context:
            return {"role": "user", "content": f"Handoff: {request.reason}"}

        return {
            "task_id": request.context.task_id,
            "task_state": request.context.task_state,
            "conversation_history": request.context.conversation_history,
            "metadata": request.context.metadata,
            "handoff_reason": request.reason,
            "source_agent_id": str(request.source_agent_id),
        }

    def _convert_result(
        self,
        request: HandoffRequestLegacy,
        execution_result: HandoffExecutionResult,
    ) -> HandoffResultLegacy:
        """
        轉換執行結果.

        Args:
            request: 原始請求
            execution_result: HandoffBuilderAdapter 執行結果

        Returns:
            HandoffResultLegacy
        """
        legacy_status = convert_status_to_legacy(execution_result.status)

        # 處理 ROLLED_BACK 狀態
        rollback_performed = False
        if execution_result.status == HandoffStatus.FAILED:
            rollback_performed = execution_result.metadata.get(
                "rollback_performed", False
            )
            if rollback_performed:
                legacy_status = HandoffStatusLegacy.ROLLED_BACK

        return HandoffResultLegacy(
            request_id=request.id,
            status=legacy_status,
            source_agent_id=request.source_agent_id,
            target_agent_id=request.target_agent_id,
            started_at=execution_result.started_at or datetime.now(timezone.utc),
            completed_at=execution_result.completed_at,
            duration_ms=execution_result.duration_ms,
            error=execution_result.error,
            rollback_performed=rollback_performed,
            transferred_context={
                "task_id": request.context.task_id if request.context else None,
                "handoff_count": execution_result.handoff_count,
                "participating_agents": execution_result.participating_agents,
            },
        )

    def _cleanup_handoff(self, handoff_id: UUID) -> None:
        """清理 handoff 追蹤."""
        if handoff_id in self._active_handoffs:
            del self._active_handoffs[handoff_id]
        if handoff_id in self._handoff_adapters:
            del self._handoff_adapters[handoff_id]

    async def _notify_completion(self, result: HandoffResultLegacy) -> None:
        """通知完成處理器."""
        for handler in self._on_handoff_complete:
            try:
                if hasattr(handler, "__call__"):
                    if hasattr(handler, "__code__") and handler.__code__.co_flags & 0x80:
                        await handler(result)
                    else:
                        handler(result)
            except Exception as e:
                logger.error(f"Completion handler failed: {e}")

    async def _notify_failure(self, result: HandoffResultLegacy) -> None:
        """通知失敗處理器."""
        for handler in self._on_handoff_failed:
            try:
                if hasattr(handler, "__call__"):
                    if hasattr(handler, "__code__") and handler.__code__.co_flags & 0x80:
                        await handler(result)
                    else:
                        handler(result)
            except Exception as e:
                logger.error(f"Failure handler failed: {e}")


# =============================================================================
# Migration Factory Functions
# =============================================================================


def migrate_handoff_controller(
    source_agent_id: UUID,
    target_agent_id: UUID,
    context: HandoffContextLegacy,
    policy: HandoffPolicyLegacy = HandoffPolicyLegacy.GRACEFUL,
    reason: str = "",
    conditions: Dict[str, Any] = None,
) -> HandoffBuilderAdapter:
    """
    遷移函數: 從 Phase 2 參數創建 HandoffBuilderAdapter.

    這是將現有 Phase 2 代碼遷移到新 API 的便捷函數。

    Args:
        source_agent_id: 來源 Agent ID
        target_agent_id: 目標 Agent ID
        context: Phase 2 HandoffContext
        policy: Phase 2 HandoffPolicy
        reason: Handoff 原因
        conditions: 條件字典

    Returns:
        配置好的 HandoffBuilderAdapter

    Example:
        # 舊代碼:
        # controller = HandoffController()
        # request = await controller.initiate_handoff(...)
        # result = await controller.execute_handoff(request)

        # 新代碼:
        adapter = migrate_handoff_controller(
            source_agent_id=uuid1,
            target_agent_id=uuid2,
            context=context,
            policy=HandoffPolicyLegacy.GRACEFUL,
        )
        result = await adapter.run(input_data)
    """
    mode = convert_policy_to_mode(policy)

    # 準備參與者
    participants = {
        str(source_agent_id): {"agent_id": str(source_agent_id)},
        str(target_agent_id): {"agent_id": str(target_agent_id)},
    }

    # 創建終止條件
    termination_condition = None
    if policy == HandoffPolicyLegacy.CONDITIONAL and conditions:
        def term_check(conv: List[Dict]) -> bool:
            if "max_turns" in conditions:
                return len(conv) >= conditions["max_turns"]
            return False
        termination_condition = term_check

    adapter = HandoffBuilderAdapter(
        id=f"migrated-handoff-{uuid4()}",
        participants=participants,
        coordinator_id=str(source_agent_id),
        mode=mode,
        termination_condition=termination_condition,
        config={
            "reason": reason,
            "priority": context.priority if context else 0,
            "timeout": context.timeout if context else 300,
            "migrated_from": "HandoffController",
        },
    )

    # 添加 handoff 路由
    adapter.add_handoff(str(source_agent_id), str(target_agent_id))

    return adapter


def create_handoff_controller_adapter(
    agent_service: Any = None,
    audit_logger: Any = None,
) -> HandoffControllerAdapter:
    """
    創建 HandoffControllerAdapter 的便捷函數.

    Args:
        agent_service: Agent 服務
        audit_logger: 審計日誌記錄器

    Returns:
        HandoffControllerAdapter 實例
    """
    return HandoffControllerAdapter(
        agent_service=agent_service,
        audit_logger=audit_logger,
    )


# =============================================================================
# 模組導出
# =============================================================================

__all__ = [
    # Legacy Types (Phase 2 Compatibility)
    "HandoffPolicyLegacy",
    "HandoffStatusLegacy",
    "HandoffContextLegacy",
    "HandoffRequestLegacy",
    "HandoffResultLegacy",
    # Conversion Functions
    "convert_status_to_legacy",
    "convert_status_from_legacy",
    "convert_policy_to_mode",
    # Adapter
    "HandoffControllerAdapter",
    # Factory Functions
    "migrate_handoff_controller",
    "create_handoff_controller_adapter",
]
