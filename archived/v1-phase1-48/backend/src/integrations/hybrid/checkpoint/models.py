# =============================================================================
# IPA Platform - Unified Checkpoint Models
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Data models for unified checkpoint system supporting both MAF and Claude
# state persistence with version control and compression support.
#
# Key Models:
#   - MAFCheckpointState: MAF workflow state snapshot
#   - ClaudeCheckpointState: Claude session state snapshot
#   - HybridCheckpoint: Unified checkpoint structure
#   - RiskSnapshot: Risk profile snapshot
#   - RestoreResult: Checkpoint restore result
#
# Dependencies:
#   - SyncStatus (src.integrations.hybrid.context.models)
#   - ExecutionMode (src.integrations.hybrid.intent.models)
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.integrations.hybrid.context.models import SyncStatus


# =============================================================================
# Enums
# =============================================================================


class CheckpointStatus(str, Enum):
    """
    Status of a checkpoint.

    Statuses:
        ACTIVE: Checkpoint is available for restore
        EXPIRED: Checkpoint has expired
        RESTORED: Checkpoint has been used for restore
        DELETED: Checkpoint has been deleted
        CORRUPTED: Checkpoint data is corrupted
    """

    ACTIVE = "active"
    EXPIRED = "expired"
    RESTORED = "restored"
    DELETED = "deleted"
    CORRUPTED = "corrupted"


class CheckpointType(str, Enum):
    """
    Type of checkpoint.

    Types:
        AUTO: Automatically created checkpoint
        MANUAL: Manually created by user/API
        MODE_SWITCH: Created during mode switch
        HITL: Created for HITL approval
        RECOVERY: Created for error recovery
    """

    AUTO = "auto"
    MANUAL = "manual"
    MODE_SWITCH = "mode_switch"
    HITL = "hitl"
    RECOVERY = "recovery"


class CompressionAlgorithm(str, Enum):
    """
    Compression algorithm for checkpoint data.

    Algorithms:
        NONE: No compression
        ZLIB: zlib compression
        GZIP: gzip compression
        LZ4: LZ4 compression (if available)
    """

    NONE = "none"
    ZLIB = "zlib"
    GZIP = "gzip"
    LZ4 = "lz4"


class RestoreStatus(str, Enum):
    """
    Status of a restore operation.

    Statuses:
        SUCCESS: Restore completed successfully
        PARTIAL: Partial restore (some state couldn't be restored)
        FAILED: Restore failed
        VALIDATION_FAILED: Checkpoint validation failed
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"


# =============================================================================
# MAF Checkpoint State
# =============================================================================


@dataclass
class MAFCheckpointState:
    """
    MAF (Microsoft Agent Framework) state snapshot.

    Captures the complete workflow state for MAF-based execution,
    including agent states, variables, and execution history.

    Attributes:
        workflow_id: Unique workflow identifier
        workflow_name: Human-readable workflow name
        current_step: Current step index (0-based)
        total_steps: Total number of steps in workflow
        agent_states: State of each agent in workflow
        variables: Workflow variables and their values
        pending_approvals: List of pending approval request IDs
        execution_log: Execution history records
        checkpoint_data: MAF-native checkpoint data
        metadata: Additional metadata

    Example:
        >>> state = MAFCheckpointState(
        ...     workflow_id="wf_123",
        ...     workflow_name="Document Processing",
        ...     current_step=3,
        ...     total_steps=5,
        ...     agent_states={"agent1": {"status": "completed"}}
        ... )
    """

    workflow_id: str
    workflow_name: str
    current_step: int = 0
    total_steps: int = 0
    agent_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    pending_approvals: List[str] = field(default_factory=list)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "agent_states": self.agent_states,
            "variables": self.variables,
            "pending_approvals": self.pending_approvals,
            "execution_log": self.execution_log,
            "checkpoint_data": self.checkpoint_data,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MAFCheckpointState":
        """Create from dictionary."""
        return cls(
            workflow_id=data["workflow_id"],
            workflow_name=data["workflow_name"],
            current_step=data.get("current_step", 0),
            total_steps=data.get("total_steps", 0),
            agent_states=data.get("agent_states", {}),
            variables=data.get("variables", {}),
            pending_approvals=data.get("pending_approvals", []),
            execution_log=data.get("execution_log", []),
            checkpoint_data=data.get("checkpoint_data", {}),
            metadata=data.get("metadata", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
        )

    def get_progress(self) -> float:
        """Get workflow progress as percentage (0.0 to 1.0)."""
        if self.total_steps == 0:
            return 0.0
        return self.current_step / self.total_steps

    def has_pending_approvals(self) -> bool:
        """Check if there are pending approvals."""
        return len(self.pending_approvals) > 0


# =============================================================================
# Claude Checkpoint State
# =============================================================================


@dataclass
class ClaudeCheckpointState:
    """
    Claude Agent SDK state snapshot.

    Captures the complete session state for Claude-based execution,
    including conversation history, tool calls, and context variables.

    Attributes:
        session_id: Unique session identifier
        conversation_history: List of conversation messages
        tool_call_history: List of tool call records
        context_variables: Session context variables
        system_prompt_hash: Hash of current system prompt
        active_hooks: List of active hook names
        mcp_states: State of MCP servers
        pending_tool_calls: List of pending tool call IDs
        metadata: Additional metadata

    Example:
        >>> state = ClaudeCheckpointState(
        ...     session_id="sess_123",
        ...     conversation_history=[{"role": "user", "content": "Hello"}],
        ...     context_variables={"user_id": "u_456"}
        ... )
    """

    session_id: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_call_history: List[Dict[str, Any]] = field(default_factory=list)
    context_variables: Dict[str, Any] = field(default_factory=dict)
    system_prompt_hash: str = ""
    active_hooks: List[str] = field(default_factory=list)
    mcp_states: Dict[str, Any] = field(default_factory=dict)
    pending_tool_calls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "conversation_history": self.conversation_history,
            "tool_call_history": self.tool_call_history,
            "context_variables": self.context_variables,
            "system_prompt_hash": self.system_prompt_hash,
            "active_hooks": self.active_hooks,
            "mcp_states": self.mcp_states,
            "pending_tool_calls": self.pending_tool_calls,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClaudeCheckpointState":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            conversation_history=data.get("conversation_history", []),
            tool_call_history=data.get("tool_call_history", []),
            context_variables=data.get("context_variables", {}),
            system_prompt_hash=data.get("system_prompt_hash", ""),
            active_hooks=data.get("active_hooks", []),
            mcp_states=data.get("mcp_states", {}),
            pending_tool_calls=data.get("pending_tool_calls", []),
            metadata=data.get("metadata", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
        )

    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.conversation_history)

    def get_tool_call_count(self) -> int:
        """Get total tool call count."""
        return len(self.tool_call_history)

    def has_pending_tool_calls(self) -> bool:
        """Check if there are pending tool calls."""
        return len(self.pending_tool_calls) > 0


# =============================================================================
# Risk Snapshot
# =============================================================================


@dataclass
class RiskSnapshot:
    """
    Snapshot of risk assessment state.

    Captures the risk profile at checkpoint time for restoration.

    Attributes:
        overall_risk_level: Overall risk level (low/medium/high/critical)
        risk_score: Numeric risk score (0.0 to 1.0)
        risk_factors: Identified risk factors
        pending_approvals: Risk-based pending approvals
        mitigation_applied: Applied mitigation strategies
    """

    overall_risk_level: str = "low"
    risk_score: float = 0.0
    risk_factors: List[Dict[str, Any]] = field(default_factory=list)
    pending_approvals: List[str] = field(default_factory=list)
    mitigation_applied: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "overall_risk_level": self.overall_risk_level,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "pending_approvals": self.pending_approvals,
            "mitigation_applied": self.mitigation_applied,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskSnapshot":
        """Create from dictionary."""
        return cls(
            overall_risk_level=data.get("overall_risk_level", "low"),
            risk_score=data.get("risk_score", 0.0),
            risk_factors=data.get("risk_factors", []),
            pending_approvals=data.get("pending_approvals", []),
            mitigation_applied=data.get("mitigation_applied", []),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# Hybrid Checkpoint
# =============================================================================


@dataclass
class HybridCheckpoint:
    """
    Unified checkpoint structure for hybrid MAF + Claude SDK execution.

    Supports storing state from both frameworks with version control,
    compression, and validation capabilities.

    Attributes:
        checkpoint_id: Unique checkpoint identifier
        session_id: Associated session identifier
        version: Checkpoint format version (for migration)
        checkpoint_type: Type of checkpoint (auto/manual/mode_switch/etc.)
        status: Current checkpoint status

        maf_state: MAF workflow state snapshot (if applicable)
        claude_state: Claude session state snapshot (if applicable)

        execution_mode: Current execution mode (workflow/chat/hybrid)
        mode_history: History of mode transitions
        risk_snapshot: Risk assessment state

        sync_version: Context sync version number
        sync_status: Current sync status
        last_sync_at: Last sync timestamp

        compressed: Whether data is compressed
        compression_algorithm: Compression algorithm used
        checksum: Data integrity checksum

        created_at: Checkpoint creation time
        expires_at: Checkpoint expiration time
        restored_at: When checkpoint was restored (if applicable)
        metadata: Additional metadata

    Example:
        >>> checkpoint = HybridCheckpoint(
        ...     session_id="sess_123",
        ...     checkpoint_type=CheckpointType.MODE_SWITCH,
        ...     maf_state=maf_state,
        ...     claude_state=claude_state,
        ...     execution_mode="workflow"
        ... )
    """

    # Identification
    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    version: int = 2  # Current version
    checkpoint_type: CheckpointType = CheckpointType.AUTO
    status: CheckpointStatus = CheckpointStatus.ACTIVE

    # Framework States
    maf_state: Optional[MAFCheckpointState] = None
    claude_state: Optional[ClaudeCheckpointState] = None

    # Execution Mode
    execution_mode: str = "chat"  # workflow / chat / hybrid
    mode_history: List[Dict[str, Any]] = field(default_factory=list)

    # Risk Profile
    risk_snapshot: Optional[RiskSnapshot] = None

    # Sync Metadata
    sync_version: int = 0
    sync_status: SyncStatus = SyncStatus.SYNCED
    last_sync_at: Optional[datetime] = None

    # Compression
    compressed: bool = False
    compression_algorithm: CompressionAlgorithm = CompressionAlgorithm.NONE
    checksum: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    restored_at: Optional[datetime] = None

    # Additional
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "version": self.version,
            "checkpoint_type": self.checkpoint_type.value,
            "status": self.status.value,
            "maf_state": self.maf_state.to_dict() if self.maf_state else None,
            "claude_state": self.claude_state.to_dict() if self.claude_state else None,
            "execution_mode": self.execution_mode,
            "mode_history": self.mode_history,
            "risk_snapshot": self.risk_snapshot.to_dict() if self.risk_snapshot else None,
            "sync_version": self.sync_version,
            "sync_status": self.sync_status.value,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "compressed": self.compressed,
            "compression_algorithm": self.compression_algorithm.value,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "restored_at": self.restored_at.isoformat() if self.restored_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HybridCheckpoint":
        """Create from dictionary."""
        return cls(
            checkpoint_id=data.get("checkpoint_id", str(uuid4())),
            session_id=data.get("session_id", ""),
            version=data.get("version", 2),
            checkpoint_type=CheckpointType(data.get("checkpoint_type", "auto")),
            status=CheckpointStatus(data.get("status", "active")),
            maf_state=(
                MAFCheckpointState.from_dict(data["maf_state"])
                if data.get("maf_state")
                else None
            ),
            claude_state=(
                ClaudeCheckpointState.from_dict(data["claude_state"])
                if data.get("claude_state")
                else None
            ),
            execution_mode=data.get("execution_mode", "chat"),
            mode_history=data.get("mode_history", []),
            risk_snapshot=(
                RiskSnapshot.from_dict(data["risk_snapshot"])
                if data.get("risk_snapshot")
                else None
            ),
            sync_version=data.get("sync_version", 0),
            sync_status=SyncStatus(data.get("sync_status", "synced")),
            last_sync_at=(
                datetime.fromisoformat(data["last_sync_at"])
                if data.get("last_sync_at")
                else None
            ),
            compressed=data.get("compressed", False),
            compression_algorithm=CompressionAlgorithm(
                data.get("compression_algorithm", "none")
            ),
            checksum=data.get("checksum"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
            restored_at=(
                datetime.fromisoformat(data["restored_at"])
                if data.get("restored_at")
                else None
            ),
            metadata=data.get("metadata", {}),
        )

    def is_active(self) -> bool:
        """Check if checkpoint is active and can be restored."""
        return self.status == CheckpointStatus.ACTIVE

    def is_expired(self) -> bool:
        """Check if checkpoint has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def has_maf_state(self) -> bool:
        """Check if checkpoint has MAF state."""
        return self.maf_state is not None

    def has_claude_state(self) -> bool:
        """Check if checkpoint has Claude state."""
        return self.claude_state is not None

    def has_both_states(self) -> bool:
        """Check if checkpoint has both MAF and Claude states."""
        return self.has_maf_state() and self.has_claude_state()

    def mark_restored(self) -> None:
        """Mark checkpoint as restored."""
        self.status = CheckpointStatus.RESTORED
        self.restored_at = datetime.utcnow()

    def mark_expired(self) -> None:
        """Mark checkpoint as expired."""
        self.status = CheckpointStatus.EXPIRED

    def get_age_seconds(self) -> float:
        """Get checkpoint age in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()


# =============================================================================
# Restore Result
# =============================================================================


@dataclass
class RestoreResult:
    """
    Result of a checkpoint restore operation.

    Contains the outcome of restoring a checkpoint, including
    what was restored and any errors encountered.

    Attributes:
        success: Whether restore was successful
        status: Restore status
        checkpoint_id: ID of restored checkpoint
        restored_maf: Whether MAF state was restored
        restored_claude: Whether Claude state was restored
        restored_mode: Execution mode after restore
        validation_errors: List of validation errors
        warnings: List of warnings
        error: Error message if failed
        restore_time_ms: Time taken for restore
        restored_at: When restore was completed
    """

    success: bool
    status: RestoreStatus = RestoreStatus.SUCCESS
    checkpoint_id: str = ""
    restored_maf: bool = False
    restored_claude: bool = False
    restored_mode: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    restore_time_ms: int = 0
    restored_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "status": self.status.value,
            "checkpoint_id": self.checkpoint_id,
            "restored_maf": self.restored_maf,
            "restored_claude": self.restored_claude,
            "restored_mode": self.restored_mode,
            "validation_errors": self.validation_errors,
            "warnings": self.warnings,
            "error": self.error,
            "restore_time_ms": self.restore_time_ms,
            "restored_at": self.restored_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RestoreResult":
        """Create from dictionary."""
        return cls(
            success=data["success"],
            status=RestoreStatus(data.get("status", "success")),
            checkpoint_id=data.get("checkpoint_id", ""),
            restored_maf=data.get("restored_maf", False),
            restored_claude=data.get("restored_claude", False),
            restored_mode=data.get("restored_mode"),
            validation_errors=data.get("validation_errors", []),
            warnings=data.get("warnings", []),
            error=data.get("error"),
            restore_time_ms=data.get("restore_time_ms", 0),
            restored_at=(
                datetime.fromisoformat(data["restored_at"])
                if "restored_at" in data
                else datetime.utcnow()
            ),
        )

    def has_warnings(self) -> bool:
        """Check if restore has warnings."""
        return len(self.warnings) > 0

    def has_validation_errors(self) -> bool:
        """Check if restore has validation errors."""
        return len(self.validation_errors) > 0

    @classmethod
    def create_failure(cls, checkpoint_id: str, error: str) -> "RestoreResult":
        """Create a failure result."""
        return cls(
            success=False,
            status=RestoreStatus.FAILED,
            checkpoint_id=checkpoint_id,
            error=error,
        )

    @classmethod
    def create_validation_failure(
        cls, checkpoint_id: str, errors: List[str]
    ) -> "RestoreResult":
        """Create a validation failure result."""
        return cls(
            success=False,
            status=RestoreStatus.VALIDATION_FAILED,
            checkpoint_id=checkpoint_id,
            validation_errors=errors,
            error="Checkpoint validation failed",
        )
