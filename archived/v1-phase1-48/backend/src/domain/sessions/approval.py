"""
Tool Approval Manager

Sprint 46 (S46-4): Tool Approval Flow
Manages tool call approvals with Redis-based storage and expiration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, AsyncIterator, Protocol
from uuid import uuid4
import json
import logging

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """審批狀態枚舉"""
    PENDING = "pending"      # 待審批
    APPROVED = "approved"    # 已批准
    REJECTED = "rejected"    # 已拒絕
    EXPIRED = "expired"      # 已過期


@dataclass
class ToolApprovalRequest:
    """工具審批請求

    Attributes:
        id: 審批請求唯一 ID
        session_id: 所屬 Session ID
        execution_id: 執行 ID
        tool_call: 工具調用詳情
        created_at: 創建時間
        expires_at: 過期時間
        status: 審批狀態
        resolved_at: 解決時間
        resolved_by: 解決者 ID
        feedback: 用戶反饋
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    execution_id: str = ""
    tool_call: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=datetime.utcnow)
    status: ApprovalStatus = ApprovalStatus.PENDING
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    feedback: Optional[str] = None

    @property
    def is_pending(self) -> bool:
        """是否待審批"""
        return self.status == ApprovalStatus.PENDING

    @property
    def is_expired(self) -> bool:
        """是否已過期"""
        if self.status == ApprovalStatus.EXPIRED:
            return True
        if self.status == ApprovalStatus.PENDING:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def time_remaining(self) -> timedelta:
        """剩餘時間"""
        if not self.is_pending:
            return timedelta(0)
        remaining = self.expires_at - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    @property
    def tool_name(self) -> str:
        """工具名稱"""
        return self.tool_call.get("name", "")

    @property
    def tool_arguments(self) -> Dict[str, Any]:
        """工具參數"""
        return self.tool_call.get("arguments", {})

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "execution_id": self.execution_id,
            "tool_call": self.tool_call,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "feedback": self.feedback,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolApprovalRequest":
        """從字典創建"""
        return cls(
            id=data.get("id", str(uuid4())),
            session_id=data.get("session_id", ""),
            execution_id=data.get("execution_id", ""),
            tool_call=data.get("tool_call", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else datetime.utcnow(),
            status=ApprovalStatus(data.get("status", "pending")),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
            resolved_by=data.get("resolved_by"),
            feedback=data.get("feedback"),
        )


class ApprovalCacheProtocol(Protocol):
    """審批快取協議 - 用於依賴注入"""

    async def get(self, key: str) -> Optional[str]:
        """獲取值"""
        ...

    async def setex(self, key: str, ttl: int, value: str) -> None:
        """設置值並指定過期時間"""
        ...

    async def delete(self, *keys: str) -> int:
        """刪除鍵"""
        ...

    async def scan(self, cursor: int, match: str, count: int) -> tuple:
        """掃描鍵"""
        ...

    async def keys(self, pattern: str) -> List[bytes]:
        """獲取匹配的鍵"""
        ...


class ApprovalError(Exception):
    """審批錯誤基類"""
    pass


class ApprovalNotFoundError(ApprovalError):
    """審批請求未找到"""
    pass


class ApprovalAlreadyResolvedError(ApprovalError):
    """審批請求已解決"""
    pass


class ApprovalExpiredError(ApprovalError):
    """審批請求已過期"""
    pass


class ToolApprovalManager:
    """工具審批管理器

    管理工具調用的審批流程:
    - 創建審批請求
    - 查詢審批狀態
    - 解決審批 (批准/拒絕)
    - 超時處理

    使用 Redis 存儲審批請求，支援自動過期。
    """

    # Key 前綴
    APPROVAL_PREFIX = "approval:"
    SESSION_APPROVALS_PREFIX = "session:approvals:"

    # 預設超時 (秒)
    DEFAULT_TIMEOUT = 300  # 5 分鐘
    RESOLVED_TTL = 3600    # 解決後保留 1 小時

    def __init__(
        self,
        cache: ApprovalCacheProtocol,
        default_timeout: int = DEFAULT_TIMEOUT,
    ):
        """初始化審批管理器

        Args:
            cache: Redis 快取客戶端
            default_timeout: 預設審批超時時間 (秒)
        """
        self._cache = cache
        self._default_timeout = default_timeout

    async def create_approval_request(
        self,
        session_id: str,
        execution_id: str,
        tool_call: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> ToolApprovalRequest:
        """創建審批請求

        Args:
            session_id: Session ID
            execution_id: 執行 ID
            tool_call: 工具調用詳情
            timeout: 可選超時時間 (秒)

        Returns:
            創建的審批請求
        """
        timeout = timeout or self._default_timeout
        now = datetime.utcnow()

        request = ToolApprovalRequest(
            session_id=session_id,
            execution_id=execution_id,
            tool_call=tool_call,
            created_at=now,
            expires_at=now + timedelta(seconds=timeout),
            status=ApprovalStatus.PENDING,
        )

        # 存儲到 Redis
        key = self._approval_key(request.id)
        data = json.dumps(request.to_dict(), default=str)
        await self._cache.setex(key, timeout, data)

        # 添加到 Session 的審批列表
        await self._add_to_session_list(session_id, request.id, timeout)

        logger.info(
            f"Created approval request {request.id} for tool {request.tool_name} "
            f"in session {session_id}, timeout {timeout}s"
        )

        return request

    async def get_approval_request(
        self,
        approval_id: str,
    ) -> Optional[ToolApprovalRequest]:
        """獲取審批請求

        Args:
            approval_id: 審批請求 ID

        Returns:
            審批請求或 None
        """
        key = self._approval_key(approval_id)
        data = await self._cache.get(key)

        if data is None:
            return None

        try:
            request_dict = json.loads(data)
            request = ToolApprovalRequest.from_dict(request_dict)

            # 檢查是否過期
            if request.is_pending and request.is_expired:
                request.status = ApprovalStatus.EXPIRED
                # 更新狀態
                await self._update_request(request)

            return request
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse approval request {approval_id}: {e}")
            await self._cache.delete(key)
            return None

    async def resolve_approval(
        self,
        approval_id: str,
        approved: bool,
        resolved_by: str,
        feedback: Optional[str] = None,
    ) -> ToolApprovalRequest:
        """解決審批請求

        Args:
            approval_id: 審批請求 ID
            approved: 是否批准
            resolved_by: 解決者 ID
            feedback: 用戶反饋

        Returns:
            更新後的審批請求

        Raises:
            ApprovalNotFoundError: 審批請求未找到
            ApprovalAlreadyResolvedError: 審批請求已解決
            ApprovalExpiredError: 審批請求已過期
        """
        request = await self.get_approval_request(approval_id)

        if request is None:
            raise ApprovalNotFoundError(f"Approval request not found: {approval_id}")

        if request.status == ApprovalStatus.EXPIRED:
            raise ApprovalExpiredError(f"Approval request has expired: {approval_id}")

        if request.status != ApprovalStatus.PENDING:
            raise ApprovalAlreadyResolvedError(
                f"Approval already resolved with status: {request.status}"
            )

        # 更新狀態
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.resolved_at = datetime.utcnow()
        request.resolved_by = resolved_by
        request.feedback = feedback

        # 更新 Redis (延長 TTL 用於審計)
        await self._update_request(request, ttl=self.RESOLVED_TTL)

        action = "approved" if approved else "rejected"
        logger.info(
            f"Approval {approval_id} {action} by {resolved_by}, "
            f"tool: {request.tool_name}"
        )

        return request

    async def approve(
        self,
        approval_id: str,
        approved_by: str,
        feedback: Optional[str] = None,
    ) -> ToolApprovalRequest:
        """批准審批請求

        Args:
            approval_id: 審批請求 ID
            approved_by: 批准者 ID
            feedback: 可選反饋

        Returns:
            更新後的審批請求
        """
        return await self.resolve_approval(
            approval_id=approval_id,
            approved=True,
            resolved_by=approved_by,
            feedback=feedback,
        )

    async def reject(
        self,
        approval_id: str,
        rejected_by: str,
        reason: Optional[str] = None,
    ) -> ToolApprovalRequest:
        """拒絕審批請求

        Args:
            approval_id: 審批請求 ID
            rejected_by: 拒絕者 ID
            reason: 拒絕原因

        Returns:
            更新後的審批請求
        """
        return await self.resolve_approval(
            approval_id=approval_id,
            approved=False,
            resolved_by=rejected_by,
            feedback=reason,
        )

    async def get_pending_approvals(
        self,
        session_id: str,
    ) -> List[ToolApprovalRequest]:
        """獲取 Session 的待審批請求

        Args:
            session_id: Session ID

        Returns:
            待審批請求列表
        """
        approvals = []

        # 從 Session 列表獲取所有審批 ID
        approval_ids = await self._get_session_approval_ids(session_id)

        for approval_id in approval_ids:
            request = await self.get_approval_request(approval_id)
            if request and request.is_pending and not request.is_expired:
                approvals.append(request)

        return approvals

    async def get_all_approvals(
        self,
        session_id: str,
        include_resolved: bool = True,
    ) -> List[ToolApprovalRequest]:
        """獲取 Session 的所有審批請求

        Args:
            session_id: Session ID
            include_resolved: 是否包含已解決的

        Returns:
            審批請求列表
        """
        approvals = []

        approval_ids = await self._get_session_approval_ids(session_id)

        for approval_id in approval_ids:
            request = await self.get_approval_request(approval_id)
            if request:
                if include_resolved or request.is_pending:
                    approvals.append(request)

        return approvals

    async def cancel_approval(
        self,
        approval_id: str,
        cancelled_by: str,
        reason: Optional[str] = None,
    ) -> bool:
        """取消審批請求

        Args:
            approval_id: 審批請求 ID
            cancelled_by: 取消者 ID
            reason: 取消原因

        Returns:
            是否成功取消
        """
        request = await self.get_approval_request(approval_id)

        if request is None:
            return False

        if request.status != ApprovalStatus.PENDING:
            return False

        # 標記為過期 (作為取消的一種方式)
        request.status = ApprovalStatus.EXPIRED
        request.resolved_at = datetime.utcnow()
        request.resolved_by = cancelled_by
        request.feedback = reason or "Cancelled by user"

        await self._update_request(request, ttl=self.RESOLVED_TTL)

        logger.info(f"Approval {approval_id} cancelled by {cancelled_by}")
        return True

    async def cleanup_expired(
        self,
        session_id: Optional[str] = None,
    ) -> int:
        """清理過期的審批請求

        Args:
            session_id: 可選 Session ID，為空則清理所有

        Returns:
            清理的數量
        """
        count = 0

        if session_id:
            approvals = await self.get_all_approvals(session_id)
            for request in approvals:
                if request.is_expired:
                    key = self._approval_key(request.id)
                    await self._cache.delete(key)
                    count += 1
        else:
            # 掃描所有審批請求
            try:
                pattern = f"{self.APPROVAL_PREFIX}*"
                keys = await self._cache.keys(pattern)
                for key in keys:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    approval_id = key_str.replace(self.APPROVAL_PREFIX, "")
                    request = await self.get_approval_request(approval_id)
                    if request and request.is_expired:
                        await self._cache.delete(key_str)
                        count += 1
            except Exception as e:
                logger.error(f"Failed to cleanup expired approvals: {e}")

        if count > 0:
            logger.info(f"Cleaned up {count} expired approval requests")

        return count

    # ===== 私有方法 =====

    def _approval_key(self, approval_id: str) -> str:
        """生成審批請求的快取 key"""
        return f"{self.APPROVAL_PREFIX}{approval_id}"

    def _session_approvals_key(self, session_id: str) -> str:
        """生成 Session 審批列表的快取 key"""
        return f"{self.SESSION_APPROVALS_PREFIX}{session_id}"

    async def _update_request(
        self,
        request: ToolApprovalRequest,
        ttl: Optional[int] = None,
    ) -> None:
        """更新審批請求

        Args:
            request: 審批請求
            ttl: 可選 TTL
        """
        key = self._approval_key(request.id)
        data = json.dumps(request.to_dict(), default=str)
        await self._cache.setex(key, ttl or self.RESOLVED_TTL, data)

    async def _add_to_session_list(
        self,
        session_id: str,
        approval_id: str,
        ttl: int,
    ) -> None:
        """添加審批 ID 到 Session 列表

        Args:
            session_id: Session ID
            approval_id: 審批請求 ID
            ttl: TTL
        """
        key = self._session_approvals_key(session_id)
        # 使用 set 存儲 (簡化實現，實際可用 Redis Set)
        existing = await self._cache.get(key)
        ids = json.loads(existing) if existing else []
        if approval_id not in ids:
            ids.append(approval_id)
        data = json.dumps(ids)
        await self._cache.setex(key, max(ttl, self.RESOLVED_TTL), data)

    async def _get_session_approval_ids(
        self,
        session_id: str,
    ) -> List[str]:
        """獲取 Session 的審批 ID 列表

        Args:
            session_id: Session ID

        Returns:
            審批 ID 列表
        """
        key = self._session_approvals_key(session_id)
        data = await self._cache.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return []
        return []


def create_approval_manager(
    cache: ApprovalCacheProtocol,
    default_timeout: int = 300,
) -> ToolApprovalManager:
    """創建審批管理器

    Args:
        cache: Redis 快取客戶端
        default_timeout: 預設超時時間 (秒)

    Returns:
        ToolApprovalManager 實例
    """
    return ToolApprovalManager(cache=cache, default_timeout=default_timeout)
