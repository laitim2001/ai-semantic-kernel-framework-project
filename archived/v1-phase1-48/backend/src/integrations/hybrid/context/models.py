# =============================================================================
# IPA Platform - Context Bridge Models
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Data models for cross-framework context bridging between
# Microsoft Agent Framework (MAF) and Claude Agent SDK.
#
# Key Models:
#   - MAFContext: Workflow state, checkpoints, agent states
#   - ClaudeContext: Session history, tool calls, context variables
#   - HybridContext: Merged context for unified view
#
# Dependencies:
#   - dataclasses for structured data
#   - enum for status types
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class SyncStatus(str, Enum):
    """同步狀態"""
    SYNCED = "synced"           # 已同步
    PENDING = "pending"         # 待同步
    CONFLICT = "conflict"       # 有衝突
    SYNCING = "syncing"         # 同步中
    FAILED = "failed"           # 同步失敗


class SyncDirection(str, Enum):
    """同步方向"""
    MAF_TO_CLAUDE = "maf_to_claude"
    CLAUDE_TO_MAF = "claude_to_maf"
    BIDIRECTIONAL = "bidirectional"


class SyncStrategy(str, Enum):
    """同步策略"""
    MERGE = "merge"                   # 合併兩邊變更
    SOURCE_WINS = "source_wins"       # 來源覆蓋目標
    TARGET_WINS = "target_wins"       # 保留目標
    MANUAL = "manual"                 # 需要人工介入
    MAF_PRIMARY = "maf_primary"       # MAF 優先
    CLAUDE_PRIMARY = "claude_primary" # Claude 優先


class AgentStatus(str, Enum):
    """Agent 狀態"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    """審批狀態"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCallStatus(str, Enum):
    """Tool 調用狀態"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# MAF Context Supporting Types
# =============================================================================


@dataclass
class AgentState:
    """Agent 狀態"""
    agent_id: str
    agent_name: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    last_output: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "current_task": self.current_task,
            "last_output": self.last_output,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            agent_name=data["agent_name"],
            status=AgentStatus(data.get("status", "idle")),
            current_task=data.get("current_task"),
            last_output=data.get("last_output"),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
        )


@dataclass
class ApprovalRequest:
    """審批請求"""
    request_id: str
    checkpoint_id: str
    action: str
    description: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: Optional[str] = None
    requested_at: datetime = field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = None
    response_by: Optional[str] = None
    response_message: Optional[str] = None
    timeout_seconds: int = 3600
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "checkpoint_id": self.checkpoint_id,
            "action": self.action,
            "description": self.description,
            "status": self.status.value,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat(),
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "response_by": self.response_by,
            "response_message": self.response_message,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        """Create from dictionary."""
        return cls(
            request_id=data["request_id"],
            checkpoint_id=data["checkpoint_id"],
            action=data["action"],
            description=data["description"],
            status=ApprovalStatus(data.get("status", "pending")),
            requested_by=data.get("requested_by"),
            requested_at=datetime.fromisoformat(data["requested_at"]) if "requested_at" in data else datetime.utcnow(),
            responded_at=datetime.fromisoformat(data["responded_at"]) if data.get("responded_at") else None,
            response_by=data.get("response_by"),
            response_message=data.get("response_message"),
            timeout_seconds=data.get("timeout_seconds", 3600),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExecutionRecord:
    """執行記錄"""
    record_id: str
    step_index: int
    step_name: str
    agent_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    status: str = "completed"
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "step_index": self.step_index,
            "step_name": self.step_name,
            "agent_id": self.agent_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "status": self.status,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionRecord":
        """Create from dictionary."""
        return cls(
            record_id=data["record_id"],
            step_index=data["step_index"],
            step_name=data["step_name"],
            agent_id=data["agent_id"],
            input_data=data.get("input_data", {}),
            output_data=data.get("output_data", {}),
            status=data.get("status", "completed"),
            error=data.get("error"),
            started_at=datetime.fromisoformat(data["started_at"]) if "started_at" in data else datetime.utcnow(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            duration_ms=data.get("duration_ms", 0),
        )


# =============================================================================
# Claude Context Supporting Types
# =============================================================================


@dataclass
class Message:
    """對話消息"""
    message_id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            message_id=data["message_id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ToolCall:
    """Tool 調用記錄"""
    call_id: str
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    status: ToolCallStatus = ToolCallStatus.PENDING
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "status": self.status.value,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        """Create from dictionary."""
        return cls(
            call_id=data["call_id"],
            tool_name=data["tool_name"],
            arguments=data.get("arguments", {}),
            result=data.get("result"),
            status=ToolCallStatus(data.get("status", "pending")),
            error=data.get("error"),
            started_at=datetime.fromisoformat(data["started_at"]) if "started_at" in data else datetime.utcnow(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            duration_ms=data.get("duration_ms", 0),
        )


# =============================================================================
# Main Context Models
# =============================================================================


@dataclass
class MAFContext:
    """
    Microsoft Agent Framework 上下文

    包含 Workflow 執行狀態、Checkpoint、Agent 狀態等資訊。
    """
    workflow_id: str
    workflow_name: str
    current_step: int = 0
    total_steps: int = 0
    agent_states: Dict[str, AgentState] = field(default_factory=dict)
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    pending_approvals: List[ApprovalRequest] = field(default_factory=list)
    execution_history: List[ExecutionRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "agent_states": {k: v.to_dict() for k, v in self.agent_states.items()},
            "checkpoint_data": self.checkpoint_data,
            "pending_approvals": [a.to_dict() for a in self.pending_approvals],
            "execution_history": [r.to_dict() for r in self.execution_history],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MAFContext":
        """Create from dictionary."""
        return cls(
            workflow_id=data["workflow_id"],
            workflow_name=data["workflow_name"],
            current_step=data.get("current_step", 0),
            total_steps=data.get("total_steps", 0),
            agent_states={k: AgentState.from_dict(v) for k, v in data.get("agent_states", {}).items()},
            checkpoint_data=data.get("checkpoint_data", {}),
            pending_approvals=[ApprovalRequest.from_dict(a) for a in data.get("pending_approvals", [])],
            execution_history=[ExecutionRecord.from_dict(r) for r in data.get("execution_history", [])],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.utcnow(),
        )

    def get_progress_percentage(self) -> float:
        """Get workflow progress percentage."""
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100

    def has_pending_approvals(self) -> bool:
        """Check if there are pending approvals."""
        return any(a.status == ApprovalStatus.PENDING for a in self.pending_approvals)

    def get_active_agents(self) -> List[AgentState]:
        """Get list of active agents."""
        return [a for a in self.agent_states.values() if a.status in (AgentStatus.RUNNING, AgentStatus.WAITING)]


@dataclass
class ClaudeContext:
    """
    Claude Agent SDK 上下文

    包含 Session 對話歷史、Tool 調用、上下文變數等資訊。
    """
    session_id: str
    conversation_history: List[Message] = field(default_factory=list)
    tool_call_history: List[ToolCall] = field(default_factory=list)
    current_system_prompt: str = ""
    context_variables: Dict[str, Any] = field(default_factory=dict)
    active_hooks: List[str] = field(default_factory=list)
    mcp_server_states: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "conversation_history": [m.to_dict() for m in self.conversation_history],
            "tool_call_history": [t.to_dict() for t in self.tool_call_history],
            "current_system_prompt": self.current_system_prompt,
            "context_variables": self.context_variables,
            "active_hooks": self.active_hooks,
            "mcp_server_states": self.mcp_server_states,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClaudeContext":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            conversation_history=[Message.from_dict(m) for m in data.get("conversation_history", [])],
            tool_call_history=[ToolCall.from_dict(t) for t in data.get("tool_call_history", [])],
            current_system_prompt=data.get("current_system_prompt", ""),
            context_variables=data.get("context_variables", {}),
            active_hooks=data.get("active_hooks", []),
            mcp_server_states=data.get("mcp_server_states", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.utcnow(),
        )

    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.conversation_history)

    def get_tool_call_count(self) -> int:
        """Get total tool call count."""
        return len(self.tool_call_history)

    def get_last_message(self) -> Optional[Message]:
        """Get the last message in conversation."""
        return self.conversation_history[-1] if self.conversation_history else None

    def get_pending_tool_calls(self) -> List[ToolCall]:
        """Get pending tool calls."""
        return [t for t in self.tool_call_history if t.status == ToolCallStatus.PENDING]


@dataclass
class HybridContext:
    """
    合併的混合上下文

    統一視圖，包含 MAF 和 Claude 兩邊的上下文資訊。
    """
    context_id: str = field(default_factory=lambda: str(uuid4()))
    maf: Optional[MAFContext] = None
    claude: Optional[ClaudeContext] = None
    primary_framework: str = "maf"  # "maf" | "claude"
    sync_status: SyncStatus = SyncStatus.PENDING
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "context_id": self.context_id,
            "maf": self.maf.to_dict() if self.maf else None,
            "claude": self.claude.to_dict() if self.claude else None,
            "primary_framework": self.primary_framework,
            "sync_status": self.sync_status.value,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "sync_error": self.sync_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HybridContext":
        """Create from dictionary."""
        return cls(
            context_id=data.get("context_id", str(uuid4())),
            maf=MAFContext.from_dict(data["maf"]) if data.get("maf") else None,
            claude=ClaudeContext.from_dict(data["claude"]) if data.get("claude") else None,
            primary_framework=data.get("primary_framework", "maf"),
            sync_status=SyncStatus(data.get("sync_status", "pending")),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
            last_sync_at=datetime.fromisoformat(data["last_sync_at"]) if data.get("last_sync_at") else None,
            sync_error=data.get("sync_error"),
        )

    def is_synced(self) -> bool:
        """Check if contexts are synced."""
        return self.sync_status == SyncStatus.SYNCED

    def has_conflict(self) -> bool:
        """Check if there is a sync conflict."""
        return self.sync_status == SyncStatus.CONFLICT

    def get_session_id(self) -> Optional[str]:
        """Get session ID (Claude) or workflow ID (MAF)."""
        if self.claude:
            return self.claude.session_id
        if self.maf:
            return self.maf.workflow_id
        return None

    def increment_version(self) -> None:
        """Increment version number."""
        self.version += 1
        self.updated_at = datetime.utcnow()


# =============================================================================
# Sync Result Types
# =============================================================================


@dataclass
class SyncResult:
    """同步結果"""
    success: bool
    direction: SyncDirection
    strategy: SyncStrategy
    source_version: int
    target_version: int
    changes_applied: int = 0
    conflicts_resolved: int = 0
    conflicts: List["Conflict"] = field(default_factory=list)
    hybrid_context: Optional["HybridContext"] = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "direction": self.direction.value,
            "strategy": self.strategy.value,
            "source_version": self.source_version,
            "target_version": self.target_version,
            "changes_applied": self.changes_applied,
            "conflicts_resolved": self.conflicts_resolved,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "hybrid_context": self.hybrid_context.to_dict() if self.hybrid_context else None,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }


@dataclass
class Conflict:
    """同步衝突"""
    conflict_id: str = field(default_factory=lambda: str(uuid4()))
    field_path: str = ""
    local_value: Any = None
    remote_value: Any = None
    local_timestamp: Optional[datetime] = None
    remote_timestamp: Optional[datetime] = None
    resolution: Optional[str] = None
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "field_path": self.field_path,
            "local_value": self.local_value,
            "remote_value": self.remote_value,
            "local_timestamp": self.local_timestamp.isoformat() if self.local_timestamp else None,
            "remote_timestamp": self.remote_timestamp.isoformat() if self.remote_timestamp else None,
            "resolution": self.resolution,
            "resolved": self.resolved,
        }
