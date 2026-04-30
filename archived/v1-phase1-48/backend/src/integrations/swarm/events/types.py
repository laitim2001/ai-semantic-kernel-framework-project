# =============================================================================
# IPA Platform - Swarm Event Types
# =============================================================================
# Sprint 101: Swarm Event System + SSE Integration
# S101-1: Swarm Event Type Definitions
#
# Defines all event payload types for Agent Swarm SSE streaming.
# These events are emitted via AG-UI CustomEvent format.
#
# Event Categories:
#   - Swarm Lifecycle: created, status_update, completed
#   - Worker Lifecycle: started, progress, thinking, tool_call, message, completed
#
# Dependencies:
#   - dataclasses
#   - typing
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# =============================================================================
# Swarm Lifecycle Events
# =============================================================================


@dataclass
class SwarmCreatedPayload:
    """
    Swarm 創建事件 payload.

    當新的 Swarm 協調任務開始時發送。

    Attributes:
        swarm_id: Swarm 唯一識別碼
        session_id: 關聯的會話 ID
        mode: 執行模式 (sequential, parallel, hierarchical)
        workers: 初始 Worker 列表 [{worker_id, worker_name, worker_type, role}]
        created_at: 創建時間 (ISO 8601)
    """

    swarm_id: str
    session_id: str
    mode: str
    workers: List[Dict[str, str]] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "session_id": self.session_id,
            "mode": self.mode,
            "workers": self.workers,
            "created_at": self.created_at,
        }


@dataclass
class SwarmStatusUpdatePayload:
    """
    Swarm 狀態更新事件 payload (完整狀態).

    定期發送 Swarm 的完整狀態快照。

    Attributes:
        swarm_id: Swarm 唯一識別碼
        session_id: 關聯的會話 ID
        mode: 執行模式
        status: 當前狀態 (initializing, running, paused, completed, failed)
        total_workers: Worker 總數
        overall_progress: 整體進度 (0-100)
        workers: Worker 摘要列表
        metadata: 附加元數據
    """

    swarm_id: str
    session_id: str
    mode: str
    status: str
    total_workers: int
    overall_progress: int
    workers: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "session_id": self.session_id,
            "mode": self.mode,
            "status": self.status,
            "total_workers": self.total_workers,
            "overall_progress": self.overall_progress,
            "workers": self.workers,
            "metadata": self.metadata,
        }


@dataclass
class SwarmCompletedPayload:
    """
    Swarm 完成事件 payload.

    當 Swarm 協調任務結束時發送 (成功或失敗)。

    Attributes:
        swarm_id: Swarm 唯一識別碼
        status: 最終狀態 (completed, failed)
        summary: 執行摘要 (可選)
        total_duration_ms: 總執行時間 (毫秒)
        completed_at: 完成時間 (ISO 8601)
    """

    swarm_id: str
    status: str
    total_duration_ms: int
    completed_at: str
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "status": self.status,
            "summary": self.summary,
            "total_duration_ms": self.total_duration_ms,
            "completed_at": self.completed_at,
        }


# =============================================================================
# Worker Lifecycle Events
# =============================================================================


@dataclass
class WorkerStartedPayload:
    """
    Worker 啟動事件 payload.

    當 Worker 開始執行任務時發送。

    Attributes:
        swarm_id: 所屬 Swarm ID
        worker_id: Worker 唯一識別碼
        worker_name: Worker 顯示名稱
        worker_type: Worker 類型 (research, writer, coder, etc.)
        role: Worker 角色描述
        task_description: 當前任務描述
        started_at: 開始時間 (ISO 8601)
    """

    swarm_id: str
    worker_id: str
    worker_name: str
    worker_type: str
    role: str
    task_description: str = ""
    started_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "worker_type": self.worker_type,
            "role": self.role,
            "task_description": self.task_description,
            "started_at": self.started_at,
        }


@dataclass
class WorkerProgressPayload:
    """
    Worker 進度更新事件 payload.

    定期發送 Worker 的進度更新。

    Attributes:
        swarm_id: 所屬 Swarm ID
        worker_id: Worker 唯一識別碼
        progress: 進度百分比 (0-100)
        current_action: 當前動作描述 (Read Todo, Think, Search, etc.)
        status: Worker 狀態
        updated_at: 更新時間 (ISO 8601)
    """

    swarm_id: str
    worker_id: str
    progress: int
    status: str
    updated_at: str
    current_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "worker_id": self.worker_id,
            "progress": self.progress,
            "current_action": self.current_action,
            "status": self.status,
            "updated_at": self.updated_at,
        }


@dataclass
class WorkerThinkingPayload:
    """
    Worker 思考過程事件 payload.

    當 Worker 產生 extended thinking 內容時發送。

    Attributes:
        swarm_id: 所屬 Swarm ID
        worker_id: Worker 唯一識別碼
        thinking_content: 思考內容文字
        token_count: Token 數量 (可選)
        timestamp: 時間戳 (ISO 8601)
    """

    swarm_id: str
    worker_id: str
    thinking_content: str
    timestamp: str
    token_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "worker_id": self.worker_id,
            "thinking_content": self.thinking_content,
            "token_count": self.token_count,
            "timestamp": self.timestamp,
        }


@dataclass
class WorkerToolCallPayload:
    """
    Worker 工具調用事件 payload.

    當 Worker 調用工具時發送。

    Attributes:
        swarm_id: 所屬 Swarm ID
        worker_id: Worker 唯一識別碼
        tool_call_id: 工具調用 ID
        tool_name: 工具名稱
        status: 調用狀態 (pending, running, completed, failed)
        input_args: 輸入參數
        output_result: 輸出結果 (可選)
        error: 錯誤信息 (可選)
        duration_ms: 執行時間毫秒 (可選)
        timestamp: 時間戳 (ISO 8601)
    """

    swarm_id: str
    worker_id: str
    tool_call_id: str
    tool_name: str
    status: str
    timestamp: str
    input_args: Dict[str, Any] = field(default_factory=dict)
    output_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "worker_id": self.worker_id,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "input_args": self.input_args,
            "output_result": self.output_result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class WorkerMessagePayload:
    """
    Worker 消息事件 payload.

    當 Worker 產生消息時發送。

    Attributes:
        swarm_id: 所屬 Swarm ID
        worker_id: Worker 唯一識別碼
        role: 消息角色 (system, user, assistant, tool)
        content: 消息內容
        tool_call_id: 關聯的工具調用 ID (可選)
        timestamp: 時間戳 (ISO 8601)
    """

    swarm_id: str
    worker_id: str
    role: str
    content: str
    timestamp: str
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "worker_id": self.worker_id,
            "role": self.role,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
            "timestamp": self.timestamp,
        }


@dataclass
class WorkerCompletedPayload:
    """
    Worker 完成事件 payload.

    當 Worker 完成執行時發送 (成功或失敗)。

    Attributes:
        swarm_id: 所屬 Swarm ID
        worker_id: Worker 唯一識別碼
        status: 最終狀態 (completed, failed)
        result: 執行結果 (可選)
        error: 錯誤信息 (可選)
        duration_ms: 執行時間毫秒
        completed_at: 完成時間 (ISO 8601)
    """

    swarm_id: str
    worker_id: str
    status: str
    duration_ms: int
    completed_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "swarm_id": self.swarm_id,
            "worker_id": self.worker_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "completed_at": self.completed_at,
        }


# =============================================================================
# Event Name Constants
# =============================================================================


class SwarmEventNames:
    """
    Swarm 事件名稱常量.

    用於 CustomEvent 的 event_name 字段。
    """

    # Swarm lifecycle events
    SWARM_CREATED = "swarm_created"
    SWARM_STATUS_UPDATE = "swarm_status_update"
    SWARM_COMPLETED = "swarm_completed"

    # Worker lifecycle events
    WORKER_STARTED = "worker_started"
    WORKER_PROGRESS = "worker_progress"
    WORKER_THINKING = "worker_thinking"
    WORKER_TOOL_CALL = "worker_tool_call"
    WORKER_MESSAGE = "worker_message"
    WORKER_COMPLETED = "worker_completed"

    @classmethod
    def all_events(cls) -> List[str]:
        """Get all event names."""
        return [
            cls.SWARM_CREATED,
            cls.SWARM_STATUS_UPDATE,
            cls.SWARM_COMPLETED,
            cls.WORKER_STARTED,
            cls.WORKER_PROGRESS,
            cls.WORKER_THINKING,
            cls.WORKER_TOOL_CALL,
            cls.WORKER_MESSAGE,
            cls.WORKER_COMPLETED,
        ]

    @classmethod
    def swarm_events(cls) -> List[str]:
        """Get swarm-level event names."""
        return [
            cls.SWARM_CREATED,
            cls.SWARM_STATUS_UPDATE,
            cls.SWARM_COMPLETED,
        ]

    @classmethod
    def worker_events(cls) -> List[str]:
        """Get worker-level event names."""
        return [
            cls.WORKER_STARTED,
            cls.WORKER_PROGRESS,
            cls.WORKER_THINKING,
            cls.WORKER_TOOL_CALL,
            cls.WORKER_MESSAGE,
            cls.WORKER_COMPLETED,
        ]

    @classmethod
    def priority_events(cls) -> List[str]:
        """Get high-priority events that should be sent immediately."""
        return [
            cls.SWARM_CREATED,
            cls.SWARM_COMPLETED,
            cls.WORKER_STARTED,
            cls.WORKER_COMPLETED,
            cls.WORKER_TOOL_CALL,
        ]

    @classmethod
    def throttled_events(cls) -> List[str]:
        """Get events that can be throttled."""
        return [
            cls.SWARM_STATUS_UPDATE,
            cls.WORKER_PROGRESS,
            cls.WORKER_THINKING,
        ]
