# =============================================================================
# Agent Framework HandoffBuilder Adapter
# =============================================================================
# Sprint 15: HandoffBuilder 重構
# Phase 3 Feature: P3-F2 (Agent Handoff 重構)
#
# 此模組提供 HandoffBuilder 的適配器實現，將 Agent Framework 官方
# HandoffBuilder API 適配到 IPA Platform 的 Handoff 系統。
#
# 核心功能:
#   - HandoffBuilderAdapter: 主適配器類
#   - HandoffMode: 交互模式枚舉 (對應 interaction_mode)
#   - HandoffRoute: 路由配置
#   - HandoffExecutionResult: 執行結果
#
# 與 Phase 2 HandoffController 的對應:
#   - HandoffPolicy.IMMEDIATE → HandoffMode.AUTONOMOUS
#   - HandoffPolicy.GRACEFUL → HandoffMode.HUMAN_IN_LOOP
#   - HandoffPolicy.CONDITIONAL → 使用 termination_condition
#
# 使用方式:
#   adapter = HandoffBuilderAdapter(
#       id="support-workflow",
#       participants={"coordinator": agent1, "specialist": agent2},
#       coordinator_id="coordinator",
#   )
#   adapter.add_handoff("coordinator", ["specialist"])
#   result = await adapter.run("Hello, I need help")
#
# References:
#   - Agent Framework HandoffBuilder: reference/agent-framework/python/packages/core/agent_framework/_workflows/_handoff.py
#   - Phase 2 HandoffController: src/domain/orchestration/handoff/controller.py
# =============================================================================

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4

from ..base import BuilderAdapter

# =============================================================================
# 官方 Agent Framework API 導入 (Sprint 19 整合)
# =============================================================================
from agent_framework import (
    HandoffBuilder,
    HandoffUserInputRequest,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enumerations
# =============================================================================


class HandoffMode(str, Enum):
    """
    Handoff 交互模式。

    對應 Agent Framework HandoffBuilder 的 interaction_mode:
        - HUMAN_IN_LOOP: 每次 Agent 回應後請求用戶輸入
        - AUTONOMOUS: Agent 持續執行直到 handoff 或終止條件

    與 Phase 2 HandoffPolicy 的映射:
        - IMMEDIATE → AUTONOMOUS (立即執行，不等待)
        - GRACEFUL → HUMAN_IN_LOOP (等待用戶確認)
        - CONDITIONAL → 使用 termination_condition
    """
    HUMAN_IN_LOOP = "human_in_loop"
    AUTONOMOUS = "autonomous"


class HandoffStatus(str, Enum):
    """
    Handoff 執行狀態。

    States:
        PENDING: 等待開始
        RUNNING: 執行中
        WAITING_INPUT: 等待用戶輸入
        COMPLETED: 成功完成
        FAILED: 執行失敗
        CANCELLED: 已取消
    """
    PENDING = "pending"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class HandoffRoute:
    """
    Handoff 路由配置。

    定義從 source agent 到 target agents 的路由規則。

    Attributes:
        source_id: 來源 Agent ID
        target_ids: 目標 Agent ID 列表
        description: 路由描述
        priority: 優先級 (數值越高越優先)
        metadata: 額外的路由元數據
    """
    source_id: str
    target_ids: List[str]
    description: Optional[str] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffParticipant:
    """
    Handoff 參與者。

    Attributes:
        id: 參與者 ID
        name: 顯示名稱
        description: 描述
        is_coordinator: 是否為協調者
        executor: 執行器實例
        capabilities: 能力列表
    """
    id: str
    name: str
    description: Optional[str] = None
    is_coordinator: bool = False
    executor: Any = None
    capabilities: List[str] = field(default_factory=list)


@dataclass
class UserInputRequest:
    """
    用戶輸入請求。

    對應 Agent Framework 的 HandoffUserInputRequest。

    Attributes:
        request_id: 請求 ID
        conversation: 對話歷史
        awaiting_agent_id: 等待輸入的 Agent ID
        prompt: 提示信息
        created_at: 創建時間
    """
    request_id: UUID = field(default_factory=uuid4)
    conversation: List[Dict[str, Any]] = field(default_factory=list)
    awaiting_agent_id: str = ""
    prompt: str = "Please provide your input."
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HandoffExecutionResult:
    """
    Handoff 執行結果。

    Attributes:
        execution_id: 執行 ID
        status: 最終狀態
        conversation: 完整對話歷史
        handoff_count: 發生的 handoff 次數
        participating_agents: 參與的 Agent ID 列表
        started_at: 開始時間
        completed_at: 完成時間
        duration_ms: 持續時間 (毫秒)
        final_agent_id: 最後處理的 Agent ID
        error: 錯誤信息 (如果失敗)
        metadata: 額外的執行元數據
    """
    execution_id: UUID
    status: HandoffStatus
    conversation: List[Dict[str, Any]]
    handoff_count: int = 0
    participating_agents: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    final_agent_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# HandoffBuilderAdapter
# =============================================================================


class HandoffBuilderAdapter(BuilderAdapter[Any, HandoffExecutionResult]):
    """
    HandoffBuilder 適配器。

    將 Agent Framework 的 HandoffBuilder API 適配到 IPA Platform。
    支持多 Agent 協調、人機互動、和自動路由。

    Features:
        - 多 Agent 參與者管理
        - 可配置的 handoff 路由
        - Human-in-the-loop 支持
        - 自主執行模式
        - 終止條件配置
        - 檢查點支持

    Example:
        # 創建適配器
        adapter = HandoffBuilderAdapter(
            id="support-workflow",
            participants={
                "coordinator": coordinator_agent,
                "refund": refund_agent,
                "shipping": shipping_agent,
            },
            coordinator_id="coordinator",
            mode=HandoffMode.HUMAN_IN_LOOP,
        )

        # 添加 handoff 路由
        adapter.add_handoff("coordinator", ["refund", "shipping"])

        # 執行
        result = await adapter.run("I need help with my order")

    Attributes:
        id: 適配器 ID
        participants: 參與者字典 {id: executor}
        coordinator_id: 協調者 ID
        mode: 交互模式
    """

    def __init__(
        self,
        id: str,
        participants: Optional[Dict[str, Any]] = None,
        coordinator_id: Optional[str] = None,
        mode: HandoffMode = HandoffMode.HUMAN_IN_LOOP,
        autonomous_turn_limit: int = 50,
        enable_return_to_previous: bool = False,
        request_prompt: Optional[str] = None,
        termination_condition: Optional[Callable[[List[Dict]], bool]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 HandoffBuilderAdapter。

        Args:
            id: 適配器唯一標識符
            participants: 參與者字典 {id: executor}
            coordinator_id: 協調者 Agent ID
            mode: 交互模式 (HUMAN_IN_LOOP 或 AUTONOMOUS)
            autonomous_turn_limit: 自主模式下的最大輪次
            enable_return_to_previous: 是否啟用返回上一個 Agent
            request_prompt: 請求用戶輸入時的提示信息
            termination_condition: 終止條件函數
            config: 額外配置
        """
        super().__init__(config)
        self._id = id
        self._participants: Dict[str, HandoffParticipant] = {}
        self._coordinator_id = coordinator_id
        self._mode = mode
        self._autonomous_turn_limit = autonomous_turn_limit
        self._enable_return_to_previous = enable_return_to_previous
        self._request_prompt = request_prompt or "Please provide your input."
        self._termination_condition = termination_condition
        self._handoff_routes: Dict[str, HandoffRoute] = {}

        # 執行狀態
        self._current_execution_id: Optional[UUID] = None
        self._conversation: List[Dict[str, Any]] = []
        self._current_agent_id: Optional[str] = None
        self._handoff_count: int = 0
        self._participating_agents: List[str] = []

        # 事件處理器
        self._on_handoff: List[Callable] = []
        self._on_user_input_request: List[Callable] = []
        self._on_completion: List[Callable] = []

        # Sprint 19: 使用官方 HandoffBuilder API
        self._builder = HandoffBuilder()

        # 註冊參與者
        if participants:
            for pid, executor in participants.items():
                self.add_participant(pid, executor)

        logger.info(f"HandoffBuilderAdapter initialized: {id}")

    @property
    def id(self) -> str:
        """獲取適配器 ID。"""
        return self._id

    @property
    def mode(self) -> HandoffMode:
        """獲取交互模式。"""
        return self._mode

    @property
    def coordinator_id(self) -> Optional[str]:
        """獲取協調者 ID。"""
        return self._coordinator_id

    @property
    def participants(self) -> Dict[str, HandoffParticipant]:
        """獲取所有參與者。"""
        return self._participants.copy()

    @property
    def handoff_routes(self) -> Dict[str, HandoffRoute]:
        """獲取所有 handoff 路由。"""
        return self._handoff_routes.copy()

    # =========================================================================
    # 參與者管理
    # =========================================================================

    def add_participant(
        self,
        participant_id: str,
        executor: Any,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_coordinator: bool = False,
        capabilities: Optional[List[str]] = None,
    ) -> "HandoffBuilderAdapter":
        """
        添加參與者。

        Args:
            participant_id: 參與者 ID
            executor: 執行器實例
            name: 顯示名稱
            description: 描述
            is_coordinator: 是否為協調者
            capabilities: 能力列表

        Returns:
            self (支持鏈式調用)
        """
        participant = HandoffParticipant(
            id=participant_id,
            name=name or participant_id,
            description=description,
            is_coordinator=is_coordinator,
            executor=executor,
            capabilities=capabilities or [],
        )

        self._participants[participant_id] = participant

        if is_coordinator:
            self._coordinator_id = participant_id

        logger.debug(f"Added participant: {participant_id}")
        return self

    def set_coordinator(
        self,
        coordinator_id: str,
    ) -> "HandoffBuilderAdapter":
        """
        設置協調者。

        Args:
            coordinator_id: 協調者 ID

        Returns:
            self (支持鏈式調用)

        Raises:
            ValueError: 如果協調者不在參與者列表中
        """
        if coordinator_id not in self._participants:
            raise ValueError(
                f"Coordinator '{coordinator_id}' is not in participants list"
            )

        # 重置之前的協調者
        for p in self._participants.values():
            p.is_coordinator = False

        # 設置新協調者
        self._participants[coordinator_id].is_coordinator = True
        self._coordinator_id = coordinator_id

        logger.debug(f"Set coordinator: {coordinator_id}")
        return self

    # =========================================================================
    # Handoff 路由配置
    # =========================================================================

    def add_handoff(
        self,
        source: str,
        targets: Union[str, List[str]],
        description: Optional[str] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "HandoffBuilderAdapter":
        """
        添加 handoff 路由。

        Args:
            source: 來源 Agent ID
            targets: 目標 Agent ID (單個或列表)
            description: 路由描述
            priority: 優先級
            metadata: 額外元數據

        Returns:
            self (支持鏈式調用)

        Raises:
            ValueError: 如果來源或目標不在參與者列表中
        """
        if source not in self._participants:
            raise ValueError(f"Source '{source}' is not in participants list")

        target_list = [targets] if isinstance(targets, str) else list(targets)

        for target in target_list:
            if target not in self._participants:
                raise ValueError(f"Target '{target}' is not in participants list")

        # 合併或創建路由
        if source in self._handoff_routes:
            existing = self._handoff_routes[source]
            for target in target_list:
                if target not in existing.target_ids:
                    existing.target_ids.append(target)
        else:
            self._handoff_routes[source] = HandoffRoute(
                source_id=source,
                target_ids=target_list,
                description=description,
                priority=priority,
                metadata=metadata or {},
            )

        logger.debug(f"Added handoff route: {source} -> {target_list}")
        return self

    def with_mode(
        self,
        mode: HandoffMode,
        autonomous_turn_limit: Optional[int] = None,
    ) -> "HandoffBuilderAdapter":
        """
        設置交互模式。

        Args:
            mode: 交互模式
            autonomous_turn_limit: 自主模式的輪次限制

        Returns:
            self (支持鏈式調用)
        """
        self._mode = mode
        if autonomous_turn_limit is not None:
            self._autonomous_turn_limit = autonomous_turn_limit

        return self

    def with_termination_condition(
        self,
        condition: Callable[[List[Dict]], bool],
    ) -> "HandoffBuilderAdapter":
        """
        設置終止條件。

        Args:
            condition: 終止條件函數，接收對話列表，返回是否終止

        Returns:
            self (支持鏈式調用)
        """
        self._termination_condition = condition
        return self

    def enable_return_to_previous(
        self,
        enabled: bool = True,
    ) -> "HandoffBuilderAdapter":
        """
        啟用返回上一個 Agent 功能。

        Args:
            enabled: 是否啟用

        Returns:
            self (支持鏈式調用)
        """
        self._enable_return_to_previous = enabled
        return self

    def with_request_prompt(
        self,
        prompt: str,
    ) -> "HandoffBuilderAdapter":
        """
        設置用戶輸入請求的提示信息。

        Args:
            prompt: 提示信息

        Returns:
            self (支持鏈式調用)
        """
        self._request_prompt = prompt
        return self

    # =========================================================================
    # 事件處理
    # =========================================================================

    def on_handoff(self, handler: Callable) -> "HandoffBuilderAdapter":
        """註冊 handoff 事件處理器。"""
        self._on_handoff.append(handler)
        return self

    def on_user_input_request(self, handler: Callable) -> "HandoffBuilderAdapter":
        """註冊用戶輸入請求事件處理器。"""
        self._on_user_input_request.append(handler)
        return self

    def on_completion(self, handler: Callable) -> "HandoffBuilderAdapter":
        """註冊完成事件處理器。"""
        self._on_completion.append(handler)
        return self

    # =========================================================================
    # 構建和執行
    # =========================================================================

    def build(self) -> Any:
        """
        構建 Handoff Workflow。

        使用官方 Agent Framework HandoffBuilder API 構建工作流。

        Returns:
            Workflow 實例

        Raises:
            ValueError: 如果沒有設置參與者或協調者
        """
        if not self._participants:
            raise ValueError("No participants configured. Call add_participant() first.")

        if not self._coordinator_id:
            raise ValueError("No coordinator configured. Call set_coordinator() first.")

        # Sprint 19: 使用官方 HandoffBuilder API 構建工作流
        # 將 IPA 平台參與者轉換為官方 API 格式
        participants = [p.executor for p in self._participants.values()]
        coordinator = self._participants.get(self._coordinator_id)

        try:
            # 調用官方 HandoffBuilder.participants().build()
            workflow = (
                self._builder
                .participants(participants)
                .build()
            )
            self._workflow = workflow
            logger.info(f"Official HandoffBuilder workflow created: {self._id}")
        except Exception as e:
            # 如果官方 API 失敗，記錄警告但繼續使用內部實現
            logger.warning(
                f"Official HandoffBuilder.build() failed: {e}. "
                f"Falling back to IPA platform implementation."
            )
            self._workflow = None

        self._built = True

        logger.info(
            f"Built HandoffBuilder workflow: {self._id} "
            f"with {len(self._participants)} participants"
        )

        # 返回 workflow 或備用配置
        if self._workflow:
            return self._workflow

        return {
            "id": self._id,
            "coordinator_id": self._coordinator_id,
            "participants": list(self._participants.keys()),
            "routes": {
                k: v.target_ids for k, v in self._handoff_routes.items()
            },
            "mode": self._mode.value,
            "built": True,
        }

    async def run(
        self,
        input_data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        session_id: Optional[str] = None,
    ) -> HandoffExecutionResult:
        """
        執行 Handoff Workflow。

        Args:
            input_data: 輸入數據 (字符串、字典或對話列表)
            session_id: 可選的會話 ID (用於恢復)

        Returns:
            HandoffExecutionResult 執行結果
        """
        if not self._built:
            self.build()

        execution_id = uuid4()
        self._current_execution_id = execution_id
        started_at = datetime.now(timezone.utc)

        # 初始化對話
        self._conversation = self._normalize_input(input_data)
        self._current_agent_id = self._coordinator_id
        self._handoff_count = 0
        self._participating_agents = [self._coordinator_id]

        logger.info(
            f"Starting handoff execution: {execution_id}, "
            f"coordinator={self._coordinator_id}, mode={self._mode.value}"
        )

        try:
            # 模擬執行循環
            turn_count = 0
            while turn_count < self._autonomous_turn_limit:
                turn_count += 1

                # 檢查終止條件
                if self._termination_condition:
                    if self._termination_condition(self._conversation):
                        logger.info(f"Termination condition met at turn {turn_count}")
                        break

                # 模擬 Agent 回應
                agent_response = await self._simulate_agent_response(
                    self._current_agent_id,
                    self._conversation,
                )

                # 添加回應到對話
                self._conversation.append({
                    "role": "assistant",
                    "content": agent_response.get("content", ""),
                    "agent_id": self._current_agent_id,
                })

                # 檢查是否有 handoff
                handoff_target = agent_response.get("handoff_to")
                if handoff_target:
                    await self._handle_handoff(
                        self._current_agent_id,
                        handoff_target,
                    )
                    continue

                # HUMAN_IN_LOOP 模式需要用戶輸入
                if self._mode == HandoffMode.HUMAN_IN_LOOP:
                    user_input = await self._request_user_input()
                    if user_input is None:
                        # 沒有更多輸入，結束
                        break
                    self._conversation.append({
                        "role": "user",
                        "content": user_input,
                    })

                # AUTONOMOUS 模式繼續循環
                # 除非達到輪次限制

            completed_at = datetime.now(timezone.utc)
            duration_ms = int(
                (completed_at - started_at).total_seconds() * 1000
            )

            result = HandoffExecutionResult(
                execution_id=execution_id,
                status=HandoffStatus.COMPLETED,
                conversation=self._conversation.copy(),
                handoff_count=self._handoff_count,
                participating_agents=self._participating_agents.copy(),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                final_agent_id=self._current_agent_id,
            )

            # 觸發完成事件
            await self._notify_completion(result)

            return result

        except Exception as e:
            logger.error(f"Handoff execution failed: {e}", exc_info=True)

            completed_at = datetime.now(timezone.utc)
            duration_ms = int(
                (completed_at - started_at).total_seconds() * 1000
            )

            return HandoffExecutionResult(
                execution_id=execution_id,
                status=HandoffStatus.FAILED,
                conversation=self._conversation.copy(),
                handoff_count=self._handoff_count,
                participating_agents=self._participating_agents.copy(),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                final_agent_id=self._current_agent_id,
                error=str(e),
            )

    # =========================================================================
    # 私有方法
    # =========================================================================

    def _normalize_input(
        self,
        input_data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """將輸入數據規範化為對話列表。"""
        if isinstance(input_data, str):
            return [{"role": "user", "content": input_data}]
        elif isinstance(input_data, dict):
            return [input_data]
        elif isinstance(input_data, list):
            return list(input_data)
        else:
            return [{"role": "user", "content": str(input_data)}]

    async def _simulate_agent_response(
        self,
        agent_id: str,
        conversation: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        模擬 Agent 回應。

        在真實整合中，這會調用實際的 Agent。
        目前實現為模擬，返回基本回應。
        """
        participant = self._participants.get(agent_id)
        if not participant:
            return {"content": "Agent not found", "error": True}

        # 模擬處理延遲
        await asyncio.sleep(0.01)

        # 檢查是否應該 handoff
        if agent_id in self._handoff_routes:
            route = self._handoff_routes[agent_id]
            if route.target_ids:
                # 模擬決定是否 handoff (簡單邏輯)
                last_message = conversation[-1] if conversation else {}
                content = last_message.get("content", "")

                # 根據內容決定是否 handoff
                for target_id in route.target_ids:
                    target_name = target_id.lower()
                    if target_name in content.lower():
                        return {
                            "content": f"Handing off to {target_id}",
                            "handoff_to": target_id,
                        }

        return {
            "content": f"Response from {agent_id}",
            "agent_id": agent_id,
        }

    async def _handle_handoff(
        self,
        source_id: str,
        target_id: str,
    ) -> None:
        """處理 handoff。"""
        self._handoff_count += 1
        self._current_agent_id = target_id

        if target_id not in self._participating_agents:
            self._participating_agents.append(target_id)

        logger.info(f"Handoff: {source_id} -> {target_id}")

        # 觸發 handoff 事件
        for handler in self._on_handoff:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(source_id, target_id)
                else:
                    handler(source_id, target_id)
            except Exception as e:
                logger.error(f"Handoff handler error: {e}")

    async def _request_user_input(self) -> Optional[str]:
        """
        請求用戶輸入。

        在真實整合中，這會通過事件系統請求用戶輸入。
        目前實現為模擬，返回 None 表示結束。
        """
        request = UserInputRequest(
            conversation=self._conversation.copy(),
            awaiting_agent_id=self._current_agent_id,
            prompt=self._request_prompt,
        )

        # 觸發用戶輸入請求事件
        for handler in self._on_user_input_request:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(request)
                else:
                    result = handler(request)
                if result:
                    return result
            except Exception as e:
                logger.error(f"User input handler error: {e}")

        # 模擬沒有更多輸入
        return None

    async def _notify_completion(
        self,
        result: HandoffExecutionResult,
    ) -> None:
        """通知完成事件處理器。"""
        for handler in self._on_completion:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(result)
                else:
                    handler(result)
            except Exception as e:
                logger.error(f"Completion handler error: {e}")


# =============================================================================
# 工廠函數
# =============================================================================


def create_handoff_adapter(
    id: str,
    participants: Dict[str, Any],
    coordinator_id: str,
    mode: HandoffMode = HandoffMode.HUMAN_IN_LOOP,
    **kwargs,
) -> HandoffBuilderAdapter:
    """
    創建 HandoffBuilderAdapter 的便捷工廠函數。

    Args:
        id: 適配器 ID
        participants: 參與者字典
        coordinator_id: 協調者 ID
        mode: 交互模式
        **kwargs: 其他配置參數

    Returns:
        配置好的 HandoffBuilderAdapter
    """
    adapter = HandoffBuilderAdapter(
        id=id,
        participants=participants,
        coordinator_id=coordinator_id,
        mode=mode,
        **kwargs,
    )

    # 自動為協調者添加到所有其他參與者的路由
    other_participants = [
        p for p in participants.keys() if p != coordinator_id
    ]
    if other_participants:
        adapter.add_handoff(coordinator_id, other_participants)

    return adapter


def create_autonomous_handoff(
    id: str,
    participants: Dict[str, Any],
    coordinator_id: str,
    turn_limit: int = 50,
    **kwargs,
) -> HandoffBuilderAdapter:
    """
    創建自主模式的 HandoffBuilderAdapter。

    Args:
        id: 適配器 ID
        participants: 參與者字典
        coordinator_id: 協調者 ID
        turn_limit: 輪次限制
        **kwargs: 其他配置參數

    Returns:
        自主模式的 HandoffBuilderAdapter
    """
    return create_handoff_adapter(
        id=id,
        participants=participants,
        coordinator_id=coordinator_id,
        mode=HandoffMode.AUTONOMOUS,
        autonomous_turn_limit=turn_limit,
        **kwargs,
    )


def create_human_in_loop_handoff(
    id: str,
    participants: Dict[str, Any],
    coordinator_id: str,
    request_prompt: Optional[str] = None,
    **kwargs,
) -> HandoffBuilderAdapter:
    """
    創建人機互動模式的 HandoffBuilderAdapter。

    Args:
        id: 適配器 ID
        participants: 參與者字典
        coordinator_id: 協調者 ID
        request_prompt: 請求用戶輸入的提示信息
        **kwargs: 其他配置參數

    Returns:
        人機互動模式的 HandoffBuilderAdapter
    """
    return create_handoff_adapter(
        id=id,
        participants=participants,
        coordinator_id=coordinator_id,
        mode=HandoffMode.HUMAN_IN_LOOP,
        request_prompt=request_prompt,
        **kwargs,
    )


# =============================================================================
# 模組導出
# =============================================================================

__all__ = [
    # Enums
    "HandoffMode",
    "HandoffStatus",
    # Data Classes
    "HandoffRoute",
    "HandoffParticipant",
    "UserInputRequest",
    "HandoffExecutionResult",
    # Adapter
    "HandoffBuilderAdapter",
    # Factory Functions
    "create_handoff_adapter",
    "create_autonomous_handoff",
    "create_human_in_loop_handoff",
]
