# =============================================================================
# IPA Platform - Context Bridge Module
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Cross-framework context bridging between MAF and Claude Agent SDK.
#
# Main Components:
#   - ContextBridge: Main bridge class for synchronization
#   - MAFContext: Microsoft Agent Framework context model
#   - ClaudeContext: Claude Agent SDK context model
#   - HybridContext: Merged context for unified view
# =============================================================================

from .bridge import ContextBridge
from .models import (
    AgentState,
    AgentStatus,
    ApprovalRequest,
    ApprovalStatus,
    ClaudeContext,
    Conflict,
    ExecutionRecord,
    HybridContext,
    MAFContext,
    Message,
    MessageRole,
    SyncDirection,
    SyncResult,
    SyncStatus,
    SyncStrategy,
    ToolCall,
    ToolCallStatus,
)

__all__ = [
    # Main Bridge
    "ContextBridge",
    # Context Models
    "MAFContext",
    "ClaudeContext",
    "HybridContext",
    # Supporting Types
    "AgentState",
    "AgentStatus",
    "ApprovalRequest",
    "ApprovalStatus",
    "ExecutionRecord",
    "Message",
    "MessageRole",
    "ToolCall",
    "ToolCallStatus",
    # Sync Types
    "SyncStatus",
    "SyncDirection",
    "SyncStrategy",
    "SyncResult",
    "Conflict",
]
