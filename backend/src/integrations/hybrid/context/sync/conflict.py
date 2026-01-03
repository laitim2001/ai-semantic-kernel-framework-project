# =============================================================================
# IPA Platform - Conflict Resolver
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Handles conflict detection and resolution between MAF and Claude contexts.
#
# Resolution Strategies:
#   - SOURCE_WINS: Source context takes precedence
#   - TARGET_WINS: Target context takes precedence
#   - MERGE: Combine both contexts intelligently
#   - MANUAL: Require human intervention
# =============================================================================

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models import (
    ClaudeContext,
    Conflict,
    HybridContext,
    MAFContext,
    SyncDirection,
    SyncStrategy,
)

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Types of conflicts that can occur."""

    VERSION_MISMATCH = "version_mismatch"
    VALUE_DIVERGENCE = "value_divergence"
    CONCURRENT_UPDATE = "concurrent_update"
    MISSING_FIELD = "missing_field"
    TYPE_MISMATCH = "type_mismatch"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"


class ConflictSeverity(str, Enum):
    """Severity levels for conflicts."""

    LOW = "low"       # Auto-resolvable
    MEDIUM = "medium"  # May need review
    HIGH = "high"      # Requires attention
    CRITICAL = "critical"  # Blocks sync


class ConflictResolver:
    """
    衝突解決器

    檢測和解決 MAF 與 Claude 上下文之間的衝突。

    Features:
    - 版本衝突檢測
    - 值差異分析
    - 多種解決策略
    - 衝突歷史記錄

    Example:
        resolver = ConflictResolver()
        conflict = resolver.detect_conflicts(local_context, remote_context)
        if conflict:
            resolved = resolver.resolve(conflict, SyncStrategy.MERGE)
    """

    # Fields that should always come from MAF
    MAF_PRIORITY_FIELDS: Set[str] = {
        "workflow_id",
        "workflow_name",
        "checkpoint_id",
        "step_index",
        "agent_states",
    }

    # Fields that should always come from Claude
    CLAUDE_PRIORITY_FIELDS: Set[str] = {
        "session_id",
        "conversation_history",
        "tool_calls",
        "model_config",
    }

    def __init__(
        self,
        default_strategy: SyncStrategy = SyncStrategy.MERGE,
        auto_resolve_threshold: ConflictSeverity = ConflictSeverity.MEDIUM,
    ):
        """
        Initialize ConflictResolver.

        Args:
            default_strategy: Default resolution strategy
            auto_resolve_threshold: Max severity for auto-resolution
        """
        self.default_strategy = default_strategy
        self.auto_resolve_threshold = auto_resolve_threshold
        self._conflict_history: List[Conflict] = []

    def detect_conflicts(
        self,
        local: HybridContext,
        remote: HybridContext,
    ) -> Optional[Conflict]:
        """
        Detect conflicts between local and remote contexts.

        Args:
            local: Local hybrid context
            remote: Remote hybrid context

        Returns:
            Conflict object if conflicts detected, None otherwise
        """
        logger.debug(
            f"Detecting conflicts: local v{local.version} vs remote v{remote.version}"
        )

        # Check version mismatch
        if local.version != remote.version:
            if abs(local.version - remote.version) > 1:
                # Significant version gap
                conflict = Conflict(
                    field_path="version",
                    local_value=local.version,
                    remote_value=remote.version,
                    local_timestamp=local.updated_at,
                    remote_timestamp=remote.updated_at,
                )
                self._conflict_history.append(conflict)
                return conflict

        # Check for concurrent updates
        if local.last_sync_at and remote.last_sync_at:
            if local.last_sync_at != remote.last_sync_at:
                # Both have been modified since last sync
                field_conflicts = self._find_value_conflicts(local, remote)
                if field_conflicts:
                    # Return first conflict found
                    first_field = list(field_conflicts.keys())[0]
                    local_val, remote_val = field_conflicts[first_field]
                    conflict = Conflict(
                        field_path=first_field,
                        local_value=local_val,
                        remote_value=remote_val,
                        local_timestamp=local.updated_at,
                        remote_timestamp=remote.updated_at,
                    )
                    self._conflict_history.append(conflict)
                    return conflict

        logger.debug("No conflicts detected")
        return None

    def _find_value_conflicts(
        self,
        local: HybridContext,
        remote: HybridContext,
    ) -> Dict[str, Tuple[Any, Any]]:
        """Find fields with conflicting values."""
        conflicts = {}

        # Check MAF context conflicts
        if local.maf and remote.maf:
            maf_conflicts = self._compare_maf_contexts(local.maf, remote.maf)
            conflicts.update(maf_conflicts)

        # Check Claude context conflicts
        if local.claude and remote.claude:
            claude_conflicts = self._compare_claude_contexts(local.claude, remote.claude)
            conflicts.update(claude_conflicts)

        return conflicts

    def _compare_maf_contexts(
        self,
        local: MAFContext,
        remote: MAFContext,
    ) -> Dict[str, Tuple[Any, Any]]:
        """Compare MAF contexts for conflicts."""
        conflicts = {}

        if local.current_step != remote.current_step:
            conflicts["maf.current_step"] = (
                local.current_step,
                remote.current_step,
            )

        # Compare checkpoint data
        if local.checkpoint_data and remote.checkpoint_data:
            checkpoint_conflicts = self._find_dict_conflicts(
                local.checkpoint_data,
                remote.checkpoint_data,
            )
            for key, value in checkpoint_conflicts.items():
                conflicts[f"maf.checkpoint.{key}"] = value

        return conflicts

    def _compare_claude_contexts(
        self,
        local: ClaudeContext,
        remote: ClaudeContext,
    ) -> Dict[str, Tuple[Any, Any]]:
        """Compare Claude contexts for conflicts."""
        conflicts = {}

        # Compare message counts (significant divergence)
        local_msg_count = len(local.conversation_history) if local.conversation_history else 0
        remote_msg_count = len(remote.conversation_history) if remote.conversation_history else 0

        if abs(local_msg_count - remote_msg_count) > 5:
            conflicts["claude.message_count"] = (local_msg_count, remote_msg_count)

        # Compare context variables
        if local.context_variables and remote.context_variables:
            var_conflicts = self._find_dict_conflicts(
                local.context_variables,
                remote.context_variables,
            )
            for key, value in var_conflicts.items():
                conflicts[f"claude.vars.{key}"] = value

        return conflicts

    def _find_dict_conflicts(
        self,
        dict1: Dict[str, Any],
        dict2: Dict[str, Any],
    ) -> Dict[str, Tuple[Any, Any]]:
        """Find conflicting values between two dictionaries."""
        conflicts = {}

        # Check keys present in both
        common_keys = set(dict1.keys()) & set(dict2.keys())

        for key in common_keys:
            val1 = dict1[key]
            val2 = dict2[key]

            # Skip if both are None
            if val1 is None and val2 is None:
                continue

            # Check for value difference
            if val1 != val2:
                # Skip datetime differences < 1 second
                if isinstance(val1, datetime) and isinstance(val2, datetime):
                    if abs((val1 - val2).total_seconds()) < 1:
                        continue

                conflicts[key] = (val1, val2)

        return conflicts

    def resolve(
        self,
        conflict: Conflict,
        local: HybridContext,
        remote: HybridContext,
        strategy: Optional[SyncStrategy] = None,
    ) -> HybridContext:
        """
        Resolve a conflict using the specified strategy.

        Args:
            conflict: The conflict to resolve
            local: Local context
            remote: Remote context
            strategy: Resolution strategy (uses default if None)

        Returns:
            Resolved HybridContext
        """
        strategy = strategy or self.default_strategy
        logger.info(f"Resolving conflict {conflict.conflict_id} with strategy: {strategy}")

        # Mark conflict as resolved
        conflict.resolved = True
        conflict.resolution = strategy.value

        if strategy == SyncStrategy.SOURCE_WINS:
            return self._resolve_source_wins(local, remote)
        elif strategy == SyncStrategy.TARGET_WINS:
            return self._resolve_target_wins(local, remote)
        elif strategy == SyncStrategy.MAF_PRIMARY:
            return self._resolve_maf_primary(local, remote)
        elif strategy == SyncStrategy.CLAUDE_PRIMARY:
            return self._resolve_claude_primary(local, remote)
        elif strategy == SyncStrategy.MERGE:
            return self._resolve_merge(local, remote, conflict)
        else:
            # MANUAL - return local with conflict info
            logger.warning(f"Manual resolution required for conflict {conflict.conflict_id}")
            return local

    def _resolve_source_wins(
        self,
        local: HybridContext,
        remote: HybridContext,
    ) -> HybridContext:
        """Source (local) takes precedence."""
        return HybridContext(
            context_id=local.context_id,
            maf=local.maf,
            claude=local.claude,
            primary_framework=local.primary_framework,
            sync_status=local.sync_status,
            version=max(local.version, remote.version) + 1,
            last_sync_at=datetime.utcnow(),
        )

    def _resolve_target_wins(
        self,
        local: HybridContext,
        remote: HybridContext,
    ) -> HybridContext:
        """Target (remote) takes precedence."""
        return HybridContext(
            context_id=remote.context_id or local.context_id,
            maf=remote.maf,
            claude=remote.claude,
            primary_framework=remote.primary_framework,
            sync_status=remote.sync_status,
            version=max(local.version, remote.version) + 1,
            last_sync_at=datetime.utcnow(),
        )

    def _resolve_maf_primary(
        self,
        local: HybridContext,
        remote: HybridContext,
    ) -> HybridContext:
        """MAF context takes precedence."""
        # Use local MAF context, remote Claude context
        return HybridContext(
            context_id=local.context_id,
            maf=local.maf,
            claude=remote.claude,
            primary_framework="maf",
            version=max(local.version, remote.version) + 1,
            last_sync_at=datetime.utcnow(),
        )

    def _resolve_claude_primary(
        self,
        local: HybridContext,
        remote: HybridContext,
    ) -> HybridContext:
        """Claude context takes precedence."""
        return HybridContext(
            context_id=local.context_id,
            maf=remote.maf,
            claude=local.claude,
            primary_framework="claude",
            version=max(local.version, remote.version) + 1,
            last_sync_at=datetime.utcnow(),
        )

    def _resolve_merge(
        self,
        local: HybridContext,
        remote: HybridContext,
        conflict: Conflict,
    ) -> HybridContext:
        """Intelligent merge of both contexts."""
        # Merge MAF contexts
        merged_maf = self._merge_maf_contexts(local.maf, remote.maf)

        # Merge Claude contexts
        merged_claude = self._merge_claude_contexts(local.claude, remote.claude)

        return HybridContext(
            context_id=local.context_id,
            maf=merged_maf,
            claude=merged_claude,
            primary_framework=local.primary_framework,
            version=max(local.version, remote.version) + 1,
            last_sync_at=datetime.utcnow(),
        )

    def _merge_maf_contexts(
        self,
        local: Optional[MAFContext],
        remote: Optional[MAFContext],
    ) -> Optional[MAFContext]:
        """Merge two MAF contexts."""
        if not local:
            return remote
        if not remote:
            return local

        # Use the more recent state
        local_step = local.current_step or 0
        remote_step = remote.current_step or 0

        if remote_step > local_step:
            # Remote is ahead
            primary, secondary = remote, local
        else:
            primary, secondary = local, remote

        # Merge checkpoint data
        merged_checkpoint = {
            **(secondary.checkpoint_data or {}),
            **(primary.checkpoint_data or {}),
        }

        # Merge metadata
        merged_metadata = {
            **(secondary.metadata or {}),
            **(primary.metadata or {}),
        }

        return MAFContext(
            workflow_id=primary.workflow_id or secondary.workflow_id,
            workflow_name=primary.workflow_name or secondary.workflow_name,
            current_step=primary.current_step,
            total_steps=max(primary.total_steps or 0, secondary.total_steps or 0),
            checkpoint_data=merged_checkpoint,
            agent_states=primary.agent_states or secondary.agent_states,
            execution_history=primary.execution_history or secondary.execution_history,
            pending_approvals=primary.pending_approvals or secondary.pending_approvals,
            metadata=merged_metadata,
            last_updated=datetime.utcnow(),
        )

    def _merge_claude_contexts(
        self,
        local: Optional[ClaudeContext],
        remote: Optional[ClaudeContext],
    ) -> Optional[ClaudeContext]:
        """Merge two Claude contexts."""
        if not local:
            return remote
        if not remote:
            return local

        # Use the one with more messages (more complete history)
        local_msgs = len(local.conversation_history) if local.conversation_history else 0
        remote_msgs = len(remote.conversation_history) if remote.conversation_history else 0

        if remote_msgs > local_msgs:
            primary, secondary = remote, local
        else:
            primary, secondary = local, remote

        # Merge context variables
        merged_vars = {
            **(secondary.context_variables or {}),
            **(primary.context_variables or {}),
        }

        # Merge metadata
        merged_metadata = {
            **(secondary.metadata or {}),
            **(primary.metadata or {}),
        }

        return ClaudeContext(
            session_id=primary.session_id or secondary.session_id,
            conversation_history=primary.conversation_history,
            tool_call_history=primary.tool_call_history or secondary.tool_call_history,
            current_system_prompt=primary.current_system_prompt or secondary.current_system_prompt,
            context_variables=merged_vars,
            active_hooks=primary.active_hooks or secondary.active_hooks,
            mcp_server_states=primary.mcp_server_states or secondary.mcp_server_states,
            metadata=merged_metadata,
            last_updated=datetime.utcnow(),
        )

    def can_auto_resolve(self, conflict: Conflict) -> bool:
        """Check if a conflict can be auto-resolved."""
        # Check if already resolved
        if conflict.resolved:
            return True

        # Check if resolution strategy is set and not manual
        if conflict.resolution and conflict.resolution != SyncStrategy.MANUAL.value:
            return True

        # Simple conflicts (like version or simple field differences) can be auto-resolved
        if conflict.field_path in ["version", "sync_status"]:
            return True

        return False

    def get_conflict_history(self) -> List[Conflict]:
        """Get conflict history."""
        return self._conflict_history.copy()

    def clear_conflict_history(self) -> None:
        """Clear conflict history."""
        self._conflict_history.clear()
