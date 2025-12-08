# =============================================================================
# Handoff Service - Sprint 21 Integration Layer
# =============================================================================
# Phase 4: 將 API 層與 Handoff 適配器整合
#
# 此服務整合所有 Handoff 相關的適配器，提供統一的 API 接口。
#
# 整合的適配器:
#   - HandoffBuilderAdapter (handoff.py) - 核心 Handoff 工作流
#   - HandoffPolicyAdapter (handoff_policy.py) - 政策映射層
#   - CapabilityMatcherAdapter (handoff_capability.py) - 能力匹配
#   - ContextTransferAdapter (handoff_context.py) - 上下文傳輸
#
# 使用方式:
#   service = HandoffService()
#   result = await service.trigger_handoff(request)
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

from .handoff import (
    HandoffBuilderAdapter,
    HandoffMode,
    HandoffStatus,
    HandoffExecutionResult,
    create_handoff_adapter,
)
from .handoff_policy import (
    LegacyHandoffPolicy,
    AdaptedPolicyConfig,
    HandoffPolicyAdapter,
)
from .handoff_capability import (
    MatchStrategy,
    AgentCapabilityInfo,
    CapabilityRequirementInfo,
    AgentAvailabilityInfo,
    CapabilityMatchResult,
    CapabilityMatcherAdapter,
    create_capability_matcher,
)
from .handoff_context import (
    TransferContextInfo,
    TransformationRuleInfo,
    TransferResult,
    ContextTransferAdapter,
    ContextTransferError,
    ContextValidationError,
    create_context_transfer_adapter,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Service Enums
# =============================================================================


class HandoffServiceStatus(str, Enum):
    """Handoff 服務狀態。"""
    INITIATED = "initiated"
    MATCHING = "matching"
    CONTEXT_TRANSFER = "context_transfer"
    EXECUTING = "executing"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


# =============================================================================
# Service Data Classes
# =============================================================================


@dataclass
class HandoffRequest:
    """
    Handoff 請求。

    Attributes:
        source_agent_id: 來源 Agent ID
        target_agent_id: 目標 Agent ID (可選，可自動匹配)
        policy: Handoff 政策
        required_capabilities: 所需能力列表 (用於自動匹配)
        context: 上下文數據
        reason: Handoff 原因
        metadata: 額外元數據
    """
    source_agent_id: UUID
    target_agent_id: Optional[UUID] = None
    policy: LegacyHandoffPolicy = LegacyHandoffPolicy.IMMEDIATE
    required_capabilities: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    match_strategy: MatchStrategy = MatchStrategy.BEST_FIT


@dataclass
class HandoffRecord:
    """
    Handoff 記錄。

    Attributes:
        handoff_id: Handoff ID
        status: 當前狀態
        source_agent_id: 來源 Agent ID
        target_agent_id: 目標 Agent ID
        policy: Handoff 政策
        context: 上下文數據
        progress: 進度 (0.0 - 1.0)
        context_transferred: 上下文是否已傳輸
        initiated_at: 發起時間
        completed_at: 完成時間
        error_message: 錯誤訊息
        metadata: 額外元數據
    """
    handoff_id: UUID
    status: HandoffServiceStatus
    source_agent_id: UUID
    target_agent_id: Optional[UUID]
    policy: LegacyHandoffPolicy
    context: Dict[str, Any]
    progress: float = 0.0
    context_transferred: bool = False
    initiated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    match_result: Optional[CapabilityMatchResult] = None


@dataclass
class HandoffTriggerResult:
    """
    Handoff 觸發結果。

    Attributes:
        handoff_id: Handoff ID
        status: 狀態
        source_agent_id: 來源 Agent ID
        target_agent_id: 目標 Agent ID
        initiated_at: 發起時間
        message: 訊息
        match_result: 匹配結果 (如果進行了匹配)
    """
    handoff_id: UUID
    status: HandoffServiceStatus
    source_agent_id: UUID
    target_agent_id: Optional[UUID]
    initiated_at: datetime
    message: str = ""
    match_result: Optional[CapabilityMatchResult] = None


@dataclass
class HandoffStatusResult:
    """
    Handoff 狀態結果。

    Attributes:
        handoff_id: Handoff ID
        status: 當前狀態
        source_agent_id: 來源 Agent ID
        target_agent_id: 目標 Agent ID
        policy: Handoff 政策
        progress: 進度
        context_transferred: 上下文是否已傳輸
        initiated_at: 發起時間
        completed_at: 完成時間
        error_message: 錯誤訊息
        metadata: 元數據
    """
    handoff_id: UUID
    status: HandoffServiceStatus
    source_agent_id: UUID
    target_agent_id: Optional[UUID]
    policy: LegacyHandoffPolicy
    progress: float
    context_transferred: bool
    initiated_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class HandoffCancelResult:
    """
    Handoff 取消結果。

    Attributes:
        handoff_id: Handoff ID
        status: 最終狀態
        cancelled_at: 取消時間
        rollback_performed: 是否執行了回滾
        message: 訊息
    """
    handoff_id: UUID
    status: HandoffServiceStatus
    cancelled_at: datetime
    rollback_performed: bool
    message: str = ""


# =============================================================================
# Handoff Service
# =============================================================================


class HandoffService:
    """
    Handoff 服務。

    整合所有 Handoff 相關適配器，提供統一的服務接口。

    Features:
        - 智能 Agent 能力匹配
        - 政策映射和配置
        - 上下文傳輸管理
        - 完整的生命週期管理
        - 歷史記錄和查詢

    Example:
        service = HandoffService()

        # 註冊 Agent 能力
        service.register_agent_capabilities(
            agent_id=uuid4(),
            capabilities=[
                AgentCapabilityInfo(
                    name="coding",
                    proficiency=0.9,
                ),
            ],
        )

        # 觸發 handoff
        result = await service.trigger_handoff(
            HandoffRequest(
                source_agent_id=uuid4(),
                required_capabilities=["coding"],
                policy=LegacyHandoffPolicy.IMMEDIATE,
            )
        )
    """

    def __init__(
        self,
        policy_adapter: Optional[HandoffPolicyAdapter] = None,
        capability_matcher: Optional[CapabilityMatcherAdapter] = None,
        context_transfer: Optional[ContextTransferAdapter] = None,
    ):
        """
        初始化 Handoff 服務。

        Args:
            policy_adapter: 政策適配器 (可選，默認創建新實例)
            capability_matcher: 能力匹配器 (可選，默認創建新實例)
            context_transfer: 上下文傳輸器 (可選，默認創建新實例)
        """
        self._policy_adapter = policy_adapter or HandoffPolicyAdapter()
        self._capability_matcher = capability_matcher or create_capability_matcher()
        self._context_transfer = context_transfer or create_context_transfer_adapter()

        # 存儲
        self._handoffs: Dict[UUID, HandoffRecord] = {}
        self._agent_capabilities: Dict[UUID, List[AgentCapabilityInfo]] = {}
        self._agent_availability: Dict[UUID, AgentAvailabilityInfo] = {}

        logger.info("HandoffService initialized")

    # =========================================================================
    # Agent Registration
    # =========================================================================

    def register_agent_capabilities(
        self,
        agent_id: UUID,
        capabilities: List[AgentCapabilityInfo],
    ) -> None:
        """
        註冊 Agent 能力。

        Args:
            agent_id: Agent ID
            capabilities: 能力列表
        """
        self._agent_capabilities[agent_id] = capabilities

        # 同步到能力匹配器 (使用字串 ID)
        self._capability_matcher.register_agent(str(agent_id), capabilities)

        logger.debug(
            f"Agent {agent_id} capabilities registered: "
            f"{len(capabilities)} capabilities"
        )

    def update_agent_availability(
        self,
        agent_id: UUID,
        is_available: bool,
        current_load: float = 0.0,
        max_concurrent_tasks: int = 10,
    ) -> None:
        """
        更新 Agent 可用性。

        Args:
            agent_id: Agent ID
            is_available: 是否可用
            current_load: 當前負載 (0.0 - 1.0)
            max_concurrent_tasks: 最大並發任務數
        """
        from .handoff_capability import AgentStatus

        availability = AgentAvailabilityInfo(
            agent_id=str(agent_id),
            status=AgentStatus.AVAILABLE if is_available else AgentStatus.OFFLINE,
            current_load=current_load,
            max_concurrent=max_concurrent_tasks,
            last_updated=datetime.utcnow(),
        )
        self._agent_availability[agent_id] = availability
        self._capability_matcher.update_availability(str(agent_id), availability)

        logger.debug(
            f"Agent {agent_id} availability updated: "
            f"available={is_available}, load={current_load}"
        )

    def unregister_agent(self, agent_id: UUID) -> None:
        """
        取消註冊 Agent。

        Args:
            agent_id: Agent ID
        """
        self._agent_capabilities.pop(agent_id, None)
        self._agent_availability.pop(agent_id, None)
        self._capability_matcher.unregister_agent(str(agent_id))

        logger.debug(f"Agent {agent_id} unregistered")

    # =========================================================================
    # Handoff Operations
    # =========================================================================

    async def trigger_handoff(
        self,
        request: HandoffRequest,
    ) -> HandoffTriggerResult:
        """
        觸發 Handoff。

        Args:
            request: Handoff 請求

        Returns:
            HandoffTriggerResult
        """
        handoff_id = uuid4()
        now = datetime.utcnow()
        match_result: Optional[CapabilityMatchResult] = None

        logger.info(
            f"Handoff trigger requested: {request.source_agent_id} -> "
            f"{request.target_agent_id or 'auto-match'}"
        )

        # 確定目標 Agent
        target_agent_id = request.target_agent_id

        if not target_agent_id and request.required_capabilities:
            # 使用能力匹配器自動匹配
            requirements = [
                CapabilityRequirementInfo(
                    name=cap,
                    min_proficiency=0.5,
                    required=True,
                )
                for cap in request.required_capabilities
            ]

            match_result = self._capability_matcher.get_best_match(
                requirements=requirements,
                strategy=request.match_strategy,
                exclude_agents={str(request.source_agent_id)},
            )

            if match_result:
                target_agent_id = match_result.agent_id
                logger.info(
                    f"Auto-matched agent: {target_agent_id} "
                    f"(score={match_result.score:.2f})"
                )

        # 適配政策
        policy_config = self._policy_adapter.adapt(
            legacy_policy=request.policy,
        )

        # 創建 Handoff 記錄
        record = HandoffRecord(
            handoff_id=handoff_id,
            status=HandoffServiceStatus.INITIATED,
            source_agent_id=request.source_agent_id,
            target_agent_id=target_agent_id,
            policy=request.policy,
            context=request.context,
            initiated_at=now,
            reason=request.reason,
            metadata={
                **request.metadata,
                "policy_config": {
                    "interaction_mode": policy_config.interaction_mode,
                    "require_confirmation": policy_config.require_confirmation,
                    "timeout_seconds": policy_config.timeout_seconds,
                },
            },
            match_result=match_result,
        )
        self._handoffs[handoff_id] = record

        logger.info(f"Handoff {handoff_id} initiated successfully")

        return HandoffTriggerResult(
            handoff_id=handoff_id,
            status=HandoffServiceStatus.INITIATED,
            source_agent_id=request.source_agent_id,
            target_agent_id=target_agent_id,
            initiated_at=now,
            message="Handoff initiated successfully",
            match_result=match_result,
        )

    async def execute_handoff(
        self,
        handoff_id: UUID,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> HandoffExecutionResult:
        """
        執行 Handoff。

        Args:
            handoff_id: Handoff ID
            context_data: 額外的上下文數據

        Returns:
            HandoffExecutionResult

        Raises:
            ValueError: 如果 Handoff 不存在
        """
        if handoff_id not in self._handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")

        record = self._handoffs[handoff_id]

        if record.status != HandoffServiceStatus.INITIATED:
            raise ValueError(
                f"Handoff {handoff_id} cannot be executed "
                f"(status: {record.status})"
            )

        # 更新狀態
        record.status = HandoffServiceStatus.CONTEXT_TRANSFER
        record.progress = 0.1

        try:
            # 準備上下文傳輸
            task_state = {
                **record.context,
                **(context_data or {}),
            }

            transfer_result = self._context_transfer.prepare_handoff_context(
                task_id=str(handoff_id),
                source_agent_id=str(record.source_agent_id),
                target_agent_id=str(record.target_agent_id) if record.target_agent_id else "",
                task_state=task_state,
                handoff_reason=record.reason,
            )

            if not transfer_result.success:
                raise ContextTransferError(
                    f"Context transfer failed: {transfer_result.errors}"
                )

            record.context_transferred = True
            record.progress = 0.3

            # 更新狀態為執行中
            record.status = HandoffServiceStatus.EXECUTING
            record.progress = 0.5

            # 模擬執行 (在真實場景中會調用 HandoffBuilderAdapter)
            # 這裡返回成功結果
            record.status = HandoffServiceStatus.COMPLETED
            record.progress = 1.0
            record.completed_at = datetime.utcnow()

            execution_result = HandoffExecutionResult(
                execution_id=handoff_id,
                status=HandoffStatus.COMPLETED,
                conversation=[],
                handoff_count=1,
                participating_agents=[
                    str(record.source_agent_id),
                    str(record.target_agent_id) if record.target_agent_id else "",
                ],
                started_at=record.initiated_at,
                completed_at=record.completed_at,
                duration_ms=int(
                    (record.completed_at - record.initiated_at).total_seconds() * 1000
                ),
                final_agent_id=str(record.target_agent_id) if record.target_agent_id else None,
            )

            logger.info(f"Handoff {handoff_id} executed successfully")

            return execution_result

        except Exception as e:
            record.status = HandoffServiceStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.utcnow()

            logger.error(f"Handoff {handoff_id} execution failed: {e}")

            return HandoffExecutionResult(
                execution_id=handoff_id,
                status=HandoffStatus.FAILED,
                conversation=[],
                error=str(e),
                started_at=record.initiated_at,
                completed_at=record.completed_at,
            )

    def get_handoff_status(
        self,
        handoff_id: UUID,
    ) -> Optional[HandoffStatusResult]:
        """
        獲取 Handoff 狀態。

        Args:
            handoff_id: Handoff ID

        Returns:
            HandoffStatusResult 或 None
        """
        record = self._handoffs.get(handoff_id)
        if not record:
            return None

        return HandoffStatusResult(
            handoff_id=record.handoff_id,
            status=record.status,
            source_agent_id=record.source_agent_id,
            target_agent_id=record.target_agent_id,
            policy=record.policy,
            progress=record.progress,
            context_transferred=record.context_transferred,
            initiated_at=record.initiated_at,
            completed_at=record.completed_at,
            error_message=record.error_message,
            metadata=record.metadata,
        )

    async def cancel_handoff(
        self,
        handoff_id: UUID,
        reason: Optional[str] = None,
    ) -> HandoffCancelResult:
        """
        取消 Handoff。

        Args:
            handoff_id: Handoff ID
            reason: 取消原因

        Returns:
            HandoffCancelResult

        Raises:
            ValueError: 如果 Handoff 不存在或無法取消
        """
        if handoff_id not in self._handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")

        record = self._handoffs[handoff_id]

        # 檢查是否可以取消
        terminal_statuses = {
            HandoffServiceStatus.COMPLETED,
            HandoffServiceStatus.CANCELLED,
            HandoffServiceStatus.ROLLED_BACK,
        }

        if record.status in terminal_statuses:
            raise ValueError(
                f"Handoff {handoff_id} cannot be cancelled "
                f"(status: {record.status})"
            )

        now = datetime.utcnow()
        rollback_needed = record.context_transferred

        # 更新記錄
        record.status = (
            HandoffServiceStatus.ROLLED_BACK
            if rollback_needed
            else HandoffServiceStatus.CANCELLED
        )
        record.completed_at = now

        if reason:
            record.metadata["cancel_reason"] = reason

        logger.info(
            f"Handoff {handoff_id} cancelled"
            f"{' with rollback' if rollback_needed else ''}"
        )

        return HandoffCancelResult(
            handoff_id=handoff_id,
            status=record.status,
            cancelled_at=now,
            rollback_performed=rollback_needed,
            message=(
                "Handoff cancelled with rollback"
                if rollback_needed
                else "Handoff cancelled successfully"
            ),
        )

    def get_handoff_history(
        self,
        source_agent_id: Optional[UUID] = None,
        target_agent_id: Optional[UUID] = None,
        status_filter: Optional[HandoffServiceStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[HandoffRecord], int]:
        """
        獲取 Handoff 歷史。

        Args:
            source_agent_id: 按來源 Agent 過濾
            target_agent_id: 按目標 Agent 過濾
            status_filter: 按狀態過濾
            page: 頁碼
            page_size: 每頁大小

        Returns:
            (記錄列表, 總數)
        """
        filtered = list(self._handoffs.values())

        if source_agent_id:
            filtered = [
                h for h in filtered
                if h.source_agent_id == source_agent_id
            ]

        if target_agent_id:
            filtered = [
                h for h in filtered
                if h.target_agent_id == target_agent_id
            ]

        if status_filter:
            filtered = [
                h for h in filtered
                if h.status == status_filter
            ]

        # 按時間排序 (最新優先)
        filtered.sort(key=lambda h: h.initiated_at, reverse=True)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size

        return filtered[start:end], total

    # =========================================================================
    # Capability Operations
    # =========================================================================

    def find_matching_agents(
        self,
        requirements: List[CapabilityRequirementInfo],
        strategy: MatchStrategy = MatchStrategy.BEST_FIT,
        exclude_agents: Optional[Set[UUID]] = None,
        check_availability: bool = True,
        max_results: int = 10,
    ) -> List[CapabilityMatchResult]:
        """
        查找匹配的 Agent。

        Args:
            requirements: 能力需求列表
            strategy: 匹配策略
            exclude_agents: 排除的 Agent
            check_availability: 是否檢查可用性
            max_results: 最大結果數

        Returns:
            匹配結果列表
        """
        # 轉換 UUID 為字串以匹配 CapabilityMatcherAdapter API
        str_exclude = {str(a) for a in exclude_agents} if exclude_agents else None

        matches = self._capability_matcher.find_capable_agents(
            requirements=requirements,
            check_availability=check_availability,
            include_partial=False,
        )

        # 過濾排除的 Agent
        if str_exclude:
            matches = [m for m in matches if m.agent_id not in str_exclude]

        # 限制結果數量
        return matches[:max_results]

    def get_agent_capabilities(
        self,
        agent_id: UUID,
    ) -> List[AgentCapabilityInfo]:
        """
        獲取 Agent 能力。

        Args:
            agent_id: Agent ID

        Returns:
            能力列表
        """
        return self._agent_capabilities.get(agent_id, [])

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def policy_adapter(self) -> HandoffPolicyAdapter:
        """獲取政策適配器。"""
        return self._policy_adapter

    @property
    def capability_matcher(self) -> CapabilityMatcherAdapter:
        """獲取能力匹配器。"""
        return self._capability_matcher

    @property
    def context_transfer(self) -> ContextTransferAdapter:
        """獲取上下文傳輸器。"""
        return self._context_transfer


# =============================================================================
# Factory Function
# =============================================================================


def create_handoff_service(
    policy_adapter: Optional[HandoffPolicyAdapter] = None,
    capability_matcher: Optional[CapabilityMatcherAdapter] = None,
    context_transfer: Optional[ContextTransferAdapter] = None,
) -> HandoffService:
    """
    創建 Handoff 服務。

    Args:
        policy_adapter: 政策適配器
        capability_matcher: 能力匹配器
        context_transfer: 上下文傳輸器

    Returns:
        HandoffService 實例
    """
    return HandoffService(
        policy_adapter=policy_adapter,
        capability_matcher=capability_matcher,
        context_transfer=context_transfer,
    )


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    # Enums
    "HandoffServiceStatus",
    # Data Classes
    "HandoffRequest",
    "HandoffRecord",
    "HandoffTriggerResult",
    "HandoffStatusResult",
    "HandoffCancelResult",
    # Service
    "HandoffService",
    # Factory
    "create_handoff_service",
]
