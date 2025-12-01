# =============================================================================
# IPA Platform - Audit Logger Service
# =============================================================================
# Sprint 3: 集成 & 可靠性 - 審計日誌系統
#
# 審計日誌服務實現，提供：
#   - 關鍵操作記錄
#   - 執行軌跡追蹤
#   - 查詢和導出功能
#   - 合規性支持
# =============================================================================

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class AuditAction(str, Enum):
    """審計動作類型."""

    # Workflow 相關
    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_UPDATED = "workflow.updated"
    WORKFLOW_DELETED = "workflow.deleted"
    WORKFLOW_TRIGGERED = "workflow.triggered"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"

    # Agent 相關
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    AGENT_EXECUTED = "agent.executed"
    AGENT_ERROR = "agent.error"

    # Checkpoint 相關
    CHECKPOINT_CREATED = "checkpoint.created"
    CHECKPOINT_APPROVED = "checkpoint.approved"
    CHECKPOINT_REJECTED = "checkpoint.rejected"
    CHECKPOINT_TIMEOUT = "checkpoint.timeout"

    # Execution 相關
    EXECUTION_STARTED = "execution.started"
    EXECUTION_PAUSED = "execution.paused"
    EXECUTION_RESUMED = "execution.resumed"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    EXECUTION_CANCELLED = "execution.cancelled"

    # User 相關
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # System 相關
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    CONFIG_CHANGED = "config.changed"

    # Integration 相關
    WEBHOOK_TRIGGERED = "webhook.triggered"
    WEBHOOK_FAILED = "webhook.failed"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"


class AuditResource(str, Enum):
    """審計資源類型."""

    WORKFLOW = "workflow"
    AGENT = "agent"
    EXECUTION = "execution"
    CHECKPOINT = "checkpoint"
    USER = "user"
    SYSTEM = "system"
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"
    TEMPLATE = "template"


class AuditSeverity(str, Enum):
    """審計嚴重程度."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AuditEntry:
    """
    審計日誌條目.

    Attributes:
        id: 條目 ID
        action: 動作類型
        resource: 資源類型
        resource_id: 資源 ID
        actor_id: 操作者 ID
        actor_name: 操作者名稱
        timestamp: 時間戳
        severity: 嚴重程度
        message: 消息
        details: 詳細信息
        metadata: 額外元數據
        ip_address: IP 地址
        user_agent: 用戶代理
        execution_id: 關聯的執行 ID (可選)
        workflow_id: 關聯的工作流 ID (可選)
    """

    action: AuditAction
    resource: AuditResource
    actor_id: Optional[str] = None
    actor_name: str = "system"
    id: UUID = field(default_factory=uuid4)
    resource_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: AuditSeverity = AuditSeverity.INFO
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    execution_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "action": self.action.value,
            "resource": self.resource.value,
            "resource_id": self.resource_id,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """從字典創建條目."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            action=AuditAction(data["action"]),
            resource=AuditResource(data["resource"]),
            resource_id=data.get("resource_id"),
            actor_id=data.get("actor_id"),
            actor_name=data.get("actor_name", "system"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            severity=AuditSeverity(data.get("severity", "info")),
            message=data.get("message", ""),
            details=data.get("details", {}),
            metadata=data.get("metadata", {}),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            execution_id=UUID(data["execution_id"]) if data.get("execution_id") else None,
            workflow_id=UUID(data["workflow_id"]) if data.get("workflow_id") else None,
        )


@dataclass
class AuditQueryParams:
    """
    審計查詢參數.

    Attributes:
        actions: 動作類型過濾
        resources: 資源類型過濾
        actor_id: 操作者 ID 過濾
        resource_id: 資源 ID 過濾
        execution_id: 執行 ID 過濾
        workflow_id: 工作流 ID 過濾
        severity: 嚴重程度過濾
        start_time: 開始時間
        end_time: 結束時間
        limit: 返回數量限制
        offset: 跳過數量
    """

    actions: Optional[List[AuditAction]] = None
    resources: Optional[List[AuditResource]] = None
    actor_id: Optional[str] = None
    resource_id: Optional[str] = None
    execution_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    severity: Optional[AuditSeverity] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


# =============================================================================
# Exceptions
# =============================================================================


class AuditError(Exception):
    """審計相關錯誤."""

    def __init__(self, message: str, code: str = "AUDIT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# =============================================================================
# Audit Logger Service
# =============================================================================


class AuditLogger:
    """
    審計日誌服務.

    提供審計日誌的記錄、查詢和導出功能。
    採用 Append-only 設計，確保日誌不可修改/刪除。

    Attributes:
        _entries: 審計條目存儲 (內存)
        _repository: 持久化存儲 (可選)
        _subscribers: 事件訂閱者
    """

    def __init__(
        self,
        repository: Optional[Any] = None,
        max_memory_entries: int = 10000,
    ):
        """
        初始化服務.

        Args:
            repository: 持久化存儲 (可選，MVP 使用內存)
            max_memory_entries: 內存中最大條目數
        """
        self._entries: List[AuditEntry] = []
        self._repository = repository
        self._max_entries = max_memory_entries
        self._subscribers: List[Callable[[AuditEntry], None]] = []

    # -------------------------------------------------------------------------
    # Logging Methods
    # -------------------------------------------------------------------------

    def log(
        self,
        action: AuditAction,
        resource: AuditResource,
        message: str = "",
        **kwargs,
    ) -> AuditEntry:
        """
        記錄審計日誌.

        Args:
            action: 動作類型
            resource: 資源類型
            message: 消息
            **kwargs: 其他參數 (actor_id, resource_id, details, etc.)

        Returns:
            創建的審計條目
        """
        entry = AuditEntry(
            action=action,
            resource=resource,
            message=message,
            **kwargs,
        )

        # 存儲條目
        self._store_entry(entry)

        # 通知訂閱者
        self._notify_subscribers(entry)

        logger.debug(
            f"Audit log: {action.value} on {resource.value} - {message}",
            extra={"audit_entry_id": str(entry.id)},
        )

        return entry

    def log_workflow_event(
        self,
        action: AuditAction,
        workflow_id: UUID,
        message: str = "",
        execution_id: Optional[UUID] = None,
        **kwargs,
    ) -> AuditEntry:
        """記錄工作流相關事件."""
        return self.log(
            action=action,
            resource=AuditResource.WORKFLOW,
            message=message,
            resource_id=str(workflow_id),
            workflow_id=workflow_id,
            execution_id=execution_id,
            **kwargs,
        )

    def log_agent_event(
        self,
        action: AuditAction,
        agent_id: UUID,
        message: str = "",
        execution_id: Optional[UUID] = None,
        **kwargs,
    ) -> AuditEntry:
        """記錄 Agent 相關事件."""
        return self.log(
            action=action,
            resource=AuditResource.AGENT,
            message=message,
            resource_id=str(agent_id),
            execution_id=execution_id,
            **kwargs,
        )

    def log_checkpoint_event(
        self,
        action: AuditAction,
        checkpoint_id: UUID,
        message: str = "",
        execution_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        **kwargs,
    ) -> AuditEntry:
        """記錄檢查點相關事件."""
        return self.log(
            action=action,
            resource=AuditResource.CHECKPOINT,
            message=message,
            resource_id=str(checkpoint_id),
            execution_id=execution_id,
            workflow_id=workflow_id,
            **kwargs,
        )

    def log_user_event(
        self,
        action: AuditAction,
        user_id: str,
        message: str = "",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """記錄用戶相關事件."""
        return self.log(
            action=action,
            resource=AuditResource.USER,
            message=message,
            resource_id=user_id,
            actor_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            **kwargs,
        )

    def log_system_event(
        self,
        action: AuditAction,
        message: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        **kwargs,
    ) -> AuditEntry:
        """記錄系統相關事件."""
        return self.log(
            action=action,
            resource=AuditResource.SYSTEM,
            message=message,
            severity=severity,
            **kwargs,
        )

    def log_error(
        self,
        resource: AuditResource,
        message: str,
        error: Optional[Exception] = None,
        **kwargs,
    ) -> AuditEntry:
        """記錄錯誤事件."""
        details = kwargs.pop("details", {})
        if error:
            details["error_type"] = type(error).__name__
            details["error_message"] = str(error)

        return self.log(
            action=AuditAction.SYSTEM_ERROR,
            resource=resource,
            message=message,
            severity=AuditSeverity.ERROR,
            details=details,
            **kwargs,
        )

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def query(self, params: Optional[AuditQueryParams] = None) -> List[AuditEntry]:
        """
        查詢審計日誌.

        Args:
            params: 查詢參數

        Returns:
            匹配的審計條目列表
        """
        if params is None:
            params = AuditQueryParams()

        results = self._entries.copy()

        # 應用過濾
        if params.actions:
            results = [e for e in results if e.action in params.actions]

        if params.resources:
            results = [e for e in results if e.resource in params.resources]

        if params.actor_id:
            results = [e for e in results if e.actor_id == params.actor_id]

        if params.resource_id:
            results = [e for e in results if e.resource_id == params.resource_id]

        if params.execution_id:
            results = [e for e in results if e.execution_id == params.execution_id]

        if params.workflow_id:
            results = [e for e in results if e.workflow_id == params.workflow_id]

        if params.severity:
            results = [e for e in results if e.severity == params.severity]

        if params.start_time:
            results = [e for e in results if e.timestamp >= params.start_time]

        if params.end_time:
            results = [e for e in results if e.timestamp <= params.end_time]

        # 按時間排序 (最新在前)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # 應用分頁
        return results[params.offset:params.offset + params.limit]

    def get_entry(self, entry_id: UUID) -> Optional[AuditEntry]:
        """獲取單個審計條目."""
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def get_execution_trail(
        self,
        execution_id: UUID,
        include_related: bool = True,
    ) -> List[AuditEntry]:
        """
        獲取執行軌跡.

        Args:
            execution_id: 執行 ID
            include_related: 是否包含相關工作流/Agent 事件

        Returns:
            按時間排序的審計條目列表
        """
        results = [e for e in self._entries if e.execution_id == execution_id]

        if include_related:
            # 查找關聯的 workflow_id
            workflow_ids = set(
                e.workflow_id for e in results
                if e.workflow_id is not None
            )

            # 包含工作流相關事件
            for wid in workflow_ids:
                workflow_events = [
                    e for e in self._entries
                    if e.workflow_id == wid and e.execution_id != execution_id
                ]
                results.extend(workflow_events)

        # 去重並按時間排序
        seen = set()
        unique_results = []
        for entry in results:
            if entry.id not in seen:
                seen.add(entry.id)
                unique_results.append(entry)

        unique_results.sort(key=lambda e: e.timestamp)
        return unique_results

    def count(self, params: Optional[AuditQueryParams] = None) -> int:
        """獲取符合條件的審計條目數量."""
        if params is None:
            return len(self._entries)

        # 使用 query 方法但設置無限 limit
        unlimited_params = AuditQueryParams(
            actions=params.actions,
            resources=params.resources,
            actor_id=params.actor_id,
            resource_id=params.resource_id,
            execution_id=params.execution_id,
            workflow_id=params.workflow_id,
            severity=params.severity,
            start_time=params.start_time,
            end_time=params.end_time,
            limit=self._max_entries,
            offset=0,
        )
        return len(self.query(unlimited_params))

    # -------------------------------------------------------------------------
    # Export Methods
    # -------------------------------------------------------------------------

    def export_csv(
        self,
        params: Optional[AuditQueryParams] = None,
    ) -> str:
        """
        導出審計日誌為 CSV 格式.

        Args:
            params: 查詢參數

        Returns:
            CSV 格式的字符串
        """
        entries = self.query(params)

        output = io.StringIO()
        writer = csv.writer(output)

        # 寫入標題行
        headers = [
            "id", "timestamp", "action", "resource", "resource_id",
            "actor_id", "actor_name", "severity", "message",
            "execution_id", "workflow_id", "ip_address",
        ]
        writer.writerow(headers)

        # 寫入數據行
        for entry in entries:
            writer.writerow([
                str(entry.id),
                entry.timestamp.isoformat(),
                entry.action.value,
                entry.resource.value,
                entry.resource_id or "",
                entry.actor_id or "",
                entry.actor_name,
                entry.severity.value,
                entry.message,
                str(entry.execution_id) if entry.execution_id else "",
                str(entry.workflow_id) if entry.workflow_id else "",
                entry.ip_address or "",
            ])

        return output.getvalue()

    def export_json(
        self,
        params: Optional[AuditQueryParams] = None,
    ) -> List[Dict[str, Any]]:
        """
        導出審計日誌為 JSON 格式.

        Args:
            params: 查詢參數

        Returns:
            字典列表
        """
        entries = self.query(params)
        return [entry.to_dict() for entry in entries]

    # -------------------------------------------------------------------------
    # Subscription Methods
    # -------------------------------------------------------------------------

    def subscribe(self, callback: Callable[[AuditEntry], None]) -> None:
        """訂閱審計事件."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[AuditEntry], None]) -> bool:
        """取消訂閱."""
        try:
            self._subscribers.remove(callback)
            return True
        except ValueError:
            return False

    # -------------------------------------------------------------------------
    # Statistics Methods
    # -------------------------------------------------------------------------

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        獲取審計統計信息.

        Args:
            start_time: 開始時間
            end_time: 結束時間

        Returns:
            統計信息字典
        """
        params = AuditQueryParams(
            start_time=start_time,
            end_time=end_time,
            limit=self._max_entries,
        )
        entries = self.query(params)

        # 按動作統計
        action_counts: Dict[str, int] = {}
        for entry in entries:
            action_counts[entry.action.value] = action_counts.get(entry.action.value, 0) + 1

        # 按資源統計
        resource_counts: Dict[str, int] = {}
        for entry in entries:
            resource_counts[entry.resource.value] = resource_counts.get(entry.resource.value, 0) + 1

        # 按嚴重程度統計
        severity_counts: Dict[str, int] = {}
        for entry in entries:
            severity_counts[entry.severity.value] = severity_counts.get(entry.severity.value, 0) + 1

        return {
            "total_entries": len(entries),
            "by_action": action_counts,
            "by_resource": resource_counts,
            "by_severity": severity_counts,
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            },
        }

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    def _store_entry(self, entry: AuditEntry) -> None:
        """存儲審計條目."""
        self._entries.append(entry)

        # 如果超過最大數量，移除最舊的條目
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        # 持久化 (如果有 repository)
        if self._repository:
            try:
                self._repository.save(entry)
            except Exception as e:
                logger.error(f"Failed to persist audit entry: {e}")

    def _notify_subscribers(self, entry: AuditEntry) -> None:
        """通知訂閱者."""
        for subscriber in self._subscribers:
            try:
                subscriber(entry)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        """
        清空內存中的審計日誌.
        注意：此操作僅影響內存存儲，不影響持久化存儲。
        """
        self._entries.clear()
        logger.warning("Audit log memory cleared")

    def get_entry_count(self) -> int:
        """獲取條目總數."""
        return len(self._entries)
