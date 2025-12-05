# =============================================================================
# Agent Framework Handoff Human-in-the-Loop (HITL) Module
# =============================================================================
# Sprint 15: HandoffBuilder 重構
# Phase 3 Feature: P3-F2 (Agent Handoff 重構) - S15-3
#
# 此模組實現 Handoff 工作流的人機互動 (Human-in-the-Loop) 功能。
# 對應 Agent Framework 的 HandoffUserInputRequest 和 RequestInfoEvent。
#
# 核心功能:
#   - HITLSession: 管理單次 HITL 對話會話
#   - HITLManager: 管理所有活躍的 HITL 會話
#   - HITLCheckpointAdapter: 與 IPA Platform checkpoint 系統整合
#   - HITLCallback: 回調接口用於 UI 整合
#
# HITL 工作流程:
#   1. Handoff 工作流執行 → 到達需要用戶輸入的點
#   2. 發出 HITLInputRequest → 創建/更新 HITLSession
#   3. UI 層收到通知 → 顯示對話和輸入提示
#   4. 用戶提供輸入 → 調用 submit_user_input()
#   5. 工作流恢復執行 → 處理用戶輸入
#
# 與 IPA Checkpoint 系統的整合:
#   - HITL 請求可選擇性地創建 checkpoint
#   - 支持 timeout 和 escalation
#   - 支持審計日誌
#
# References:
#   - Agent Framework HandoffUserInputRequest
#   - IPA Platform Checkpoint System
# =============================================================================

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Union
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Enumerations
# =============================================================================


class HITLSessionStatus(str, Enum):
    """
    HITL 會話狀態。

    States:
        ACTIVE: 等待用戶輸入
        INPUT_RECEIVED: 已收到用戶輸入，等待處理
        PROCESSING: 正在處理用戶輸入
        COMPLETED: 會話完成
        TIMEOUT: 超時
        CANCELLED: 已取消
        ESCALATED: 已升級
    """
    ACTIVE = "active"
    INPUT_RECEIVED = "input_received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class HITLInputType(str, Enum):
    """
    HITL 輸入類型。

    Types:
        TEXT: 純文字輸入
        CHOICE: 選項選擇
        CONFIRMATION: 確認 (是/否)
        FILE: 文件上傳
        FORM: 表單數據
    """
    TEXT = "text"
    CHOICE = "choice"
    CONFIRMATION = "confirmation"
    FILE = "file"
    FORM = "form"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class HITLInputRequest:
    """
    HITL 輸入請求。

    對應 Agent Framework 的 HandoffUserInputRequest。

    Attributes:
        request_id: 請求 ID
        session_id: 會話 ID
        conversation: 對話歷史
        awaiting_agent_id: 等待輸入的 Agent ID
        prompt: 提示信息
        input_type: 期望的輸入類型
        choices: 可選項 (用於 CHOICE 類型)
        default_value: 默認值
        validation_rules: 驗證規則
        timeout_seconds: 超時時間 (秒)
        metadata: 額外元數據
        created_at: 創建時間
    """
    request_id: UUID = field(default_factory=uuid4)
    session_id: Optional[UUID] = None
    conversation: List[Dict[str, Any]] = field(default_factory=list)
    awaiting_agent_id: str = ""
    prompt: str = "Please provide your input."
    input_type: HITLInputType = HITLInputType.TEXT
    choices: List[str] = field(default_factory=list)
    default_value: Optional[str] = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def expires_at(self) -> datetime:
        """計算過期時間。"""
        return self.created_at + timedelta(seconds=self.timeout_seconds)

    @property
    def is_expired(self) -> bool:
        """檢查是否已過期。"""
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class HITLInputResponse:
    """
    HITL 輸入回應。

    Attributes:
        response_id: 回應 ID
        request_id: 對應的請求 ID
        input_value: 用戶輸入值
        input_type: 輸入類型
        user_id: 用戶 ID (如果已知)
        responded_at: 回應時間
        metadata: 額外元數據
    """
    response_id: UUID = field(default_factory=uuid4)
    request_id: UUID = field(default_factory=uuid4)
    input_value: Any = None
    input_type: HITLInputType = HITLInputType.TEXT
    user_id: Optional[str] = None
    responded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HITLSession:
    """
    HITL 會話。

    管理單次人機互動會話的完整生命週期。

    Attributes:
        session_id: 會話 ID
        handoff_execution_id: 關聯的 Handoff 執行 ID
        status: 當前狀態
        current_request: 當前等待的請求
        history: 請求/回應歷史
        created_at: 創建時間
        updated_at: 最後更新時間
        completed_at: 完成時間
        checkpoint_id: 關聯的 checkpoint ID (如果有)
        metadata: 額外元數據
    """
    session_id: UUID = field(default_factory=uuid4)
    handoff_execution_id: Optional[UUID] = None
    status: HITLSessionStatus = HITLSessionStatus.ACTIVE
    current_request: Optional[HITLInputRequest] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    checkpoint_id: Optional[UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_request(self, request: HITLInputRequest) -> None:
        """添加新請求到歷史。"""
        self.current_request = request
        self.history.append({
            "type": "request",
            "request_id": str(request.request_id),
            "prompt": request.prompt,
            "input_type": request.input_type.value,
            "timestamp": request.created_at.isoformat(),
        })
        self.updated_at = datetime.now(timezone.utc)

    def add_response(self, response: HITLInputResponse) -> None:
        """添加回應到歷史。"""
        self.history.append({
            "type": "response",
            "response_id": str(response.response_id),
            "request_id": str(response.request_id),
            "input_value": str(response.input_value)[:100],  # 截斷長輸入
            "timestamp": response.responded_at.isoformat(),
        })
        self.current_request = None
        self.updated_at = datetime.now(timezone.utc)


# =============================================================================
# Callback Protocol
# =============================================================================


class HITLCallback(Protocol):
    """
    HITL 回調接口。

    用於 UI 整合，允許外部系統接收 HITL 事件通知。
    """

    async def on_input_requested(
        self,
        session: HITLSession,
        request: HITLInputRequest,
    ) -> None:
        """當需要用戶輸入時調用。"""
        ...

    async def on_input_received(
        self,
        session: HITLSession,
        response: HITLInputResponse,
    ) -> None:
        """當收到用戶輸入時調用。"""
        ...

    async def on_session_completed(
        self,
        session: HITLSession,
    ) -> None:
        """當會話完成時調用。"""
        ...

    async def on_session_timeout(
        self,
        session: HITLSession,
    ) -> None:
        """當會話超時時調用。"""
        ...

    async def on_session_escalated(
        self,
        session: HITLSession,
        escalation_reason: str,
    ) -> None:
        """當會話升級時調用。"""
        ...


# =============================================================================
# Default Callback Implementation
# =============================================================================


class DefaultHITLCallback:
    """默認 HITL 回調實現 (僅記錄日誌)。"""

    async def on_input_requested(
        self,
        session: HITLSession,
        request: HITLInputRequest,
    ) -> None:
        logger.info(
            f"HITL input requested: session={session.session_id}, "
            f"agent={request.awaiting_agent_id}"
        )

    async def on_input_received(
        self,
        session: HITLSession,
        response: HITLInputResponse,
    ) -> None:
        logger.info(
            f"HITL input received: session={session.session_id}, "
            f"response_id={response.response_id}"
        )

    async def on_session_completed(
        self,
        session: HITLSession,
    ) -> None:
        logger.info(f"HITL session completed: {session.session_id}")

    async def on_session_timeout(
        self,
        session: HITLSession,
    ) -> None:
        logger.warning(f"HITL session timeout: {session.session_id}")

    async def on_session_escalated(
        self,
        session: HITLSession,
        escalation_reason: str,
    ) -> None:
        logger.warning(
            f"HITL session escalated: {session.session_id}, "
            f"reason={escalation_reason}"
        )


# =============================================================================
# HITLManager
# =============================================================================


class HITLManager:
    """
    HITL 管理器。

    管理所有活躍的 HITL 會話，提供:
    - 會話創建和查詢
    - 用戶輸入提交
    - 超時處理
    - 升級處理
    - 與 checkpoint 系統整合

    Usage:
        manager = HITLManager()

        # 創建會話
        session = await manager.create_session(
            handoff_execution_id=execution_id,
        )

        # 請求用戶輸入
        request = await manager.request_input(
            session_id=session.session_id,
            prompt="Please confirm the refund",
            input_type=HITLInputType.CONFIRMATION,
        )

        # 提交用戶輸入
        response = await manager.submit_input(
            request_id=request.request_id,
            input_value="yes",
        )
    """

    def __init__(
        self,
        checkpoint_service: Any = None,
        callback: Optional[HITLCallback] = None,
        default_timeout: int = 300,
    ) -> None:
        """
        初始化 HITLManager。

        Args:
            checkpoint_service: IPA checkpoint 服務 (可選)
            callback: HITL 回調實現
            default_timeout: 默認超時時間 (秒)
        """
        self._checkpoint_service = checkpoint_service
        self._callback = callback or DefaultHITLCallback()
        self._default_timeout = default_timeout

        # 活躍會話存儲
        self._sessions: Dict[UUID, HITLSession] = {}
        self._request_to_session: Dict[UUID, UUID] = {}

        # 等待輸入的 Future 映射
        self._waiting_futures: Dict[UUID, asyncio.Future] = {}

        # 超時檢查任務
        self._timeout_task: Optional[asyncio.Task] = None

        logger.info("HITLManager initialized")

    @property
    def active_sessions(self) -> Dict[UUID, HITLSession]:
        """獲取所有活躍會話。"""
        return {
            sid: sess for sid, sess in self._sessions.items()
            if sess.status == HITLSessionStatus.ACTIVE
        }

    async def start(self) -> None:
        """啟動 HITL 管理器 (開始超時檢查)。"""
        if self._timeout_task is None:
            self._timeout_task = asyncio.create_task(self._check_timeouts())
            logger.info("HITLManager started")

    async def stop(self) -> None:
        """停止 HITL 管理器。"""
        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass
            self._timeout_task = None
            logger.info("HITLManager stopped")

    async def create_session(
        self,
        handoff_execution_id: Optional[UUID] = None,
        create_checkpoint: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HITLSession:
        """
        創建新的 HITL 會話。

        Args:
            handoff_execution_id: 關聯的 Handoff 執行 ID
            create_checkpoint: 是否創建 checkpoint
            metadata: 額外元數據

        Returns:
            HITLSession
        """
        session = HITLSession(
            handoff_execution_id=handoff_execution_id,
            metadata=metadata or {},
        )

        # 創建 checkpoint (如果需要)
        if create_checkpoint and self._checkpoint_service:
            try:
                checkpoint = await self._checkpoint_service.create_checkpoint(
                    execution_id=handoff_execution_id,
                    checkpoint_type="hitl",
                    context={"session_id": str(session.session_id)},
                )
                session.checkpoint_id = checkpoint.id
            except Exception as e:
                logger.error(f"Failed to create checkpoint: {e}")

        self._sessions[session.session_id] = session

        logger.info(
            f"HITL session created: {session.session_id}, "
            f"execution={handoff_execution_id}"
        )

        return session

    async def request_input(
        self,
        session_id: UUID,
        prompt: str,
        awaiting_agent_id: str = "",
        input_type: HITLInputType = HITLInputType.TEXT,
        choices: Optional[List[str]] = None,
        default_value: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        conversation: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HITLInputRequest:
        """
        請求用戶輸入。

        Args:
            session_id: 會話 ID
            prompt: 提示信息
            awaiting_agent_id: 等待輸入的 Agent ID
            input_type: 期望的輸入類型
            choices: 可選項 (用於 CHOICE 類型)
            default_value: 默認值
            timeout_seconds: 超時時間 (秒)
            conversation: 對話歷史
            metadata: 額外元數據

        Returns:
            HITLInputRequest

        Raises:
            ValueError: 如果會話不存在或狀態無效
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status != HITLSessionStatus.ACTIVE:
            raise ValueError(
                f"Session {session_id} is not active (status={session.status})"
            )

        request = HITLInputRequest(
            session_id=session_id,
            prompt=prompt,
            awaiting_agent_id=awaiting_agent_id,
            input_type=input_type,
            choices=choices or [],
            default_value=default_value,
            timeout_seconds=timeout_seconds or self._default_timeout,
            conversation=conversation or [],
            metadata=metadata or {},
        )

        # 更新會話
        session.add_request(request)
        self._request_to_session[request.request_id] = session_id

        # 創建等待 Future
        future: asyncio.Future = asyncio.Future()
        self._waiting_futures[request.request_id] = future

        # 通知回調
        await self._callback.on_input_requested(session, request)

        logger.info(
            f"HITL input requested: request={request.request_id}, "
            f"session={session_id}, agent={awaiting_agent_id}"
        )

        return request

    async def submit_input(
        self,
        request_id: UUID,
        input_value: Any,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HITLInputResponse:
        """
        提交用戶輸入。

        Args:
            request_id: 請求 ID
            input_value: 用戶輸入值
            user_id: 用戶 ID
            metadata: 額外元數據

        Returns:
            HITLInputResponse

        Raises:
            ValueError: 如果請求不存在或已處理
        """
        session_id = self._request_to_session.get(request_id)
        if not session_id:
            raise ValueError(f"Request {request_id} not found")

        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.current_request:
            raise ValueError(f"No pending request for session {session_id}")

        if session.current_request.request_id != request_id:
            raise ValueError(f"Request {request_id} is not the current request")

        # 創建回應
        response = HITLInputResponse(
            request_id=request_id,
            input_value=input_value,
            input_type=session.current_request.input_type,
            user_id=user_id,
            metadata=metadata or {},
        )

        # 更新會話
        session.add_response(response)
        session.status = HITLSessionStatus.INPUT_RECEIVED

        # 解除等待的 Future
        future = self._waiting_futures.pop(request_id, None)
        if future and not future.done():
            future.set_result(response)

        # 清理映射
        self._request_to_session.pop(request_id, None)

        # 通知回調
        await self._callback.on_input_received(session, response)

        logger.info(
            f"HITL input submitted: response={response.response_id}, "
            f"request={request_id}, session={session_id}"
        )

        return response

    async def wait_for_input(
        self,
        request_id: UUID,
        timeout: Optional[float] = None,
    ) -> HITLInputResponse:
        """
        等待用戶輸入。

        Args:
            request_id: 請求 ID
            timeout: 超時時間 (秒)

        Returns:
            HITLInputResponse

        Raises:
            TimeoutError: 如果超時
            ValueError: 如果請求不存在
        """
        future = self._waiting_futures.get(request_id)
        if not future:
            raise ValueError(f"Request {request_id} not found or already processed")

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            # 處理超時
            session_id = self._request_to_session.get(request_id)
            if session_id:
                session = self._sessions.get(session_id)
                if session:
                    await self._handle_timeout(session)
            raise TimeoutError(f"Input request {request_id} timed out")

    async def complete_session(
        self,
        session_id: UUID,
    ) -> HITLSession:
        """
        完成 HITL 會話。

        Args:
            session_id: 會話 ID

        Returns:
            HITLSession

        Raises:
            ValueError: 如果會話不存在
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = HITLSessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)

        # 完成 checkpoint (如果有)
        if session.checkpoint_id and self._checkpoint_service:
            try:
                await self._checkpoint_service.complete_checkpoint(
                    checkpoint_id=session.checkpoint_id,
                )
            except Exception as e:
                logger.error(f"Failed to complete checkpoint: {e}")

        # 通知回調
        await self._callback.on_session_completed(session)

        logger.info(f"HITL session completed: {session_id}")

        return session

    async def cancel_session(
        self,
        session_id: UUID,
        reason: str = "",
    ) -> HITLSession:
        """
        取消 HITL 會話。

        Args:
            session_id: 會話 ID
            reason: 取消原因

        Returns:
            HITLSession

        Raises:
            ValueError: 如果會話不存在
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = HITLSessionStatus.CANCELLED
        session.completed_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)
        session.metadata["cancel_reason"] = reason

        # 取消等待的 Future
        if session.current_request:
            future = self._waiting_futures.pop(
                session.current_request.request_id, None
            )
            if future and not future.done():
                future.cancel()
            self._request_to_session.pop(
                session.current_request.request_id, None
            )

        logger.info(f"HITL session cancelled: {session_id}, reason={reason}")

        return session

    async def escalate_session(
        self,
        session_id: UUID,
        reason: str = "",
        escalation_target: Optional[str] = None,
    ) -> HITLSession:
        """
        升級 HITL 會話。

        Args:
            session_id: 會話 ID
            reason: 升級原因
            escalation_target: 升級目標 (如管理員)

        Returns:
            HITLSession

        Raises:
            ValueError: 如果會話不存在
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = HITLSessionStatus.ESCALATED
        session.updated_at = datetime.now(timezone.utc)
        session.metadata["escalation_reason"] = reason
        session.metadata["escalation_target"] = escalation_target

        # 通知回調
        await self._callback.on_session_escalated(session, reason)

        logger.warning(
            f"HITL session escalated: {session_id}, "
            f"reason={reason}, target={escalation_target}"
        )

        return session

    def get_session(self, session_id: UUID) -> Optional[HITLSession]:
        """獲取會話。"""
        return self._sessions.get(session_id)

    def get_pending_requests(self) -> List[HITLInputRequest]:
        """獲取所有等待中的請求。"""
        requests = []
        for session in self._sessions.values():
            if (
                session.status == HITLSessionStatus.ACTIVE
                and session.current_request
            ):
                requests.append(session.current_request)
        return requests

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _check_timeouts(self) -> None:
        """定期檢查超時的會話。"""
        while True:
            try:
                await asyncio.sleep(10)  # 每 10 秒檢查一次

                now = datetime.now(timezone.utc)
                for session in list(self._sessions.values()):
                    if (
                        session.status == HITLSessionStatus.ACTIVE
                        and session.current_request
                        and session.current_request.is_expired
                    ):
                        await self._handle_timeout(session)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in timeout check: {e}")

    async def _handle_timeout(self, session: HITLSession) -> None:
        """處理會話超時。"""
        session.status = HITLSessionStatus.TIMEOUT
        session.completed_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)

        # 取消等待的 Future
        if session.current_request:
            future = self._waiting_futures.pop(
                session.current_request.request_id, None
            )
            if future and not future.done():
                future.set_exception(
                    TimeoutError(f"Session {session.session_id} timed out")
                )
            self._request_to_session.pop(
                session.current_request.request_id, None
            )

        # 通知回調
        await self._callback.on_session_timeout(session)

        logger.warning(f"HITL session timeout: {session.session_id}")


# =============================================================================
# HITLCheckpointAdapter
# =============================================================================


class HITLCheckpointAdapter:
    """
    HITL Checkpoint 適配器。

    將 HITL 會話與 IPA Platform 的 checkpoint 系統整合。
    支持:
    - 創建 HITL checkpoint
    - 處理 checkpoint 審批
    - 恢復工作流
    """

    def __init__(
        self,
        hitl_manager: HITLManager,
        checkpoint_service: Any = None,
    ) -> None:
        """
        初始化適配器。

        Args:
            hitl_manager: HITL 管理器
            checkpoint_service: IPA checkpoint 服務
        """
        self._hitl_manager = hitl_manager
        self._checkpoint_service = checkpoint_service

        logger.info("HITLCheckpointAdapter initialized")

    async def create_hitl_checkpoint(
        self,
        execution_id: UUID,
        handoff_context: Dict[str, Any],
        prompt: str,
        awaiting_agent_id: str,
        timeout_seconds: int = 300,
    ) -> HITLSession:
        """
        創建 HITL checkpoint。

        Args:
            execution_id: 執行 ID
            handoff_context: Handoff 上下文
            prompt: 提示信息
            awaiting_agent_id: 等待輸入的 Agent ID
            timeout_seconds: 超時時間

        Returns:
            HITLSession
        """
        # 創建會話
        session = await self._hitl_manager.create_session(
            handoff_execution_id=execution_id,
            create_checkpoint=True,
            metadata={
                "handoff_context": handoff_context,
            },
        )

        # 請求輸入
        await self._hitl_manager.request_input(
            session_id=session.session_id,
            prompt=prompt,
            awaiting_agent_id=awaiting_agent_id,
            timeout_seconds=timeout_seconds,
            conversation=handoff_context.get("conversation", []),
        )

        return session

    async def process_checkpoint_approval(
        self,
        checkpoint_id: UUID,
        approved: bool,
        approver_id: str,
        comments: str = "",
    ) -> HITLInputResponse:
        """
        處理 checkpoint 審批。

        Args:
            checkpoint_id: Checkpoint ID
            approved: 是否批准
            approver_id: 審批者 ID
            comments: 審批意見

        Returns:
            HITLInputResponse
        """
        # 找到關聯的會話
        session = None
        for s in self._hitl_manager._sessions.values():
            if s.checkpoint_id == checkpoint_id:
                session = s
                break

        if not session:
            raise ValueError(f"No HITL session for checkpoint {checkpoint_id}")

        if not session.current_request:
            raise ValueError(f"No pending request for checkpoint {checkpoint_id}")

        # 提交輸入
        input_value = "approved" if approved else "rejected"
        if comments:
            input_value = f"{input_value}: {comments}"

        return await self._hitl_manager.submit_input(
            request_id=session.current_request.request_id,
            input_value=input_value,
            user_id=approver_id,
            metadata={
                "approved": approved,
                "comments": comments,
            },
        )


# =============================================================================
# Factory Functions
# =============================================================================


def create_hitl_manager(
    checkpoint_service: Any = None,
    callback: Optional[HITLCallback] = None,
    default_timeout: int = 300,
) -> HITLManager:
    """
    創建 HITLManager 的便捷工廠函數。

    Args:
        checkpoint_service: IPA checkpoint 服務
        callback: HITL 回調實現
        default_timeout: 默認超時時間 (秒)

    Returns:
        HITLManager
    """
    return HITLManager(
        checkpoint_service=checkpoint_service,
        callback=callback,
        default_timeout=default_timeout,
    )


def create_hitl_checkpoint_adapter(
    hitl_manager: HITLManager,
    checkpoint_service: Any = None,
) -> HITLCheckpointAdapter:
    """
    創建 HITLCheckpointAdapter 的便捷工廠函數。

    Args:
        hitl_manager: HITL 管理器
        checkpoint_service: IPA checkpoint 服務

    Returns:
        HITLCheckpointAdapter
    """
    return HITLCheckpointAdapter(
        hitl_manager=hitl_manager,
        checkpoint_service=checkpoint_service,
    )


# =============================================================================
# 模組導出
# =============================================================================

__all__ = [
    # Enums
    "HITLSessionStatus",
    "HITLInputType",
    # Data Classes
    "HITLInputRequest",
    "HITLInputResponse",
    "HITLSession",
    # Protocols
    "HITLCallback",
    # Classes
    "DefaultHITLCallback",
    "HITLManager",
    "HITLCheckpointAdapter",
    # Factory Functions
    "create_hitl_manager",
    "create_hitl_checkpoint_adapter",
]
