# =============================================================================
# IPA Platform - Context Bridge
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Main bridge class for cross-framework context synchronization between
# Microsoft Agent Framework (MAF) and Claude Agent SDK.
#
# Responsibilities:
#   - Bidirectional context synchronization
#   - Context merging and conflict resolution
#   - Version management and change tracking
#
# Dependencies:
#   - models.py for data structures
#   - mappers for state transformation
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from uuid import uuid4

from .models import (
    AgentState,
    AgentStatus,
    ApprovalRequest,
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

logger = logging.getLogger(__name__)


# =============================================================================
# Mapper Protocols
# =============================================================================


class MAFMapperProtocol(Protocol):
    """MAF Mapper Protocol for dependency injection."""

    def to_claude_context_vars(
        self,
        checkpoint: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert MAF checkpoint to Claude context variables."""
        ...

    def to_claude_history(
        self,
        execution_records: List[ExecutionRecord],
        max_messages: int = 50,
    ) -> List[Message]:
        """Convert MAF execution records to Claude messages."""
        ...

    def agent_state_to_system_prompt(
        self,
        agent_states: Dict[str, AgentState],
    ) -> str:
        """Convert agent states to system prompt addition."""
        ...


class ClaudeMapperProtocol(Protocol):
    """Claude Mapper Protocol for dependency injection."""

    def to_maf_checkpoint(
        self,
        context_vars: Dict[str, Any],
        tool_calls: List[ToolCall],
    ) -> Dict[str, Any]:
        """Convert Claude context to MAF checkpoint."""
        ...

    def to_execution_records(
        self,
        conversation: List[Message],
    ) -> List[ExecutionRecord]:
        """Convert Claude messages to MAF execution records."""
        ...


class SynchronizerProtocol(Protocol):
    """Synchronizer Protocol for dependency injection."""

    async def sync(
        self,
        source: Any,
        target_type: str,
        strategy: SyncStrategy,
    ) -> SyncResult:
        """Perform synchronization."""
        ...

    async def detect_conflict(
        self,
        local: HybridContext,
        remote: HybridContext,
    ) -> Optional[Conflict]:
        """Detect sync conflicts."""
        ...


# =============================================================================
# Context Bridge
# =============================================================================


class ContextBridge:
    """
    跨框架上下文橋接器

    負責 MAF Workflow 和 Claude Session 之間的狀態同步。

    Features:
    - Bidirectional sync (MAF ↔ Claude)
    - Automatic context mapping
    - Conflict detection and resolution
    - Version control

    Usage:
        bridge = ContextBridge()
        claude_ctx = await bridge.sync_to_claude(maf_context)
        maf_ctx = await bridge.sync_to_maf(claude_context)
    """

    def __init__(
        self,
        maf_mapper: Optional[MAFMapperProtocol] = None,
        claude_mapper: Optional[ClaudeMapperProtocol] = None,
        synchronizer: Optional[SynchronizerProtocol] = None,
    ):
        """
        Initialize ContextBridge.

        Args:
            maf_mapper: Mapper for MAF state transformations
            claude_mapper: Mapper for Claude state transformations
            synchronizer: Synchronizer for conflict resolution
        """
        self._maf_mapper = maf_mapper
        self._claude_mapper = claude_mapper
        self._synchronizer = synchronizer
        self._context_cache: Dict[str, HybridContext] = {}

    # =========================================================================
    # Properties for mapper access
    # =========================================================================

    @property
    def maf_mapper(self) -> Optional[MAFMapperProtocol]:
        """Get MAF mapper."""
        return self._maf_mapper

    @property
    def claude_mapper(self) -> Optional[ClaudeMapperProtocol]:
        """Get Claude mapper."""
        return self._claude_mapper

    @property
    def synchronizer(self) -> Optional[SynchronizerProtocol]:
        """Get synchronizer."""
        return self._synchronizer

    async def sync_to_claude(
        self,
        maf_context: MAFContext,
        existing_claude: Optional[ClaudeContext] = None,
    ) -> ClaudeContext:
        """
        將 MAF 上下文同步到 Claude

        轉換映射:
        - workflow_id → session metadata
        - checkpoint_data → context_variables
        - execution_history → conversation_history (摘要)
        - pending_approvals → tool_call_history (待處理)
        - agent_states → system_prompt (附加資訊)

        Args:
            maf_context: Source MAF context
            existing_claude: Optional existing Claude context to merge with

        Returns:
            ClaudeContext: Synchronized Claude context
        """
        logger.info(f"Syncing MAF context to Claude: workflow_id={maf_context.workflow_id}")

        # Start with existing or create new Claude context
        if existing_claude:
            claude_context = existing_claude
        else:
            claude_context = ClaudeContext(
                session_id=f"claude-{maf_context.workflow_id}",
                created_at=datetime.utcnow(),
            )

        # Map checkpoint_data → context_variables
        if self.maf_mapper:
            claude_context.context_variables = self.maf_mapper.to_claude_context_vars(
                maf_context.checkpoint_data
            )
        else:
            claude_context.context_variables = self._default_checkpoint_to_context_vars(
                maf_context.checkpoint_data
            )

        # Map execution_history → conversation_history
        if self.maf_mapper:
            messages = self.maf_mapper.to_claude_history(
                maf_context.execution_history,
                max_messages=50,
            )
        else:
            messages = self._default_execution_to_messages(maf_context.execution_history)

        # Merge with existing history
        claude_context.conversation_history = self._merge_messages(
            claude_context.conversation_history,
            messages,
        )

        # Map agent_states → system_prompt addition
        if self.maf_mapper:
            prompt_addition = self.maf_mapper.agent_state_to_system_prompt(
                maf_context.agent_states
            )
        else:
            prompt_addition = self._default_agent_state_to_prompt(maf_context.agent_states)

        if prompt_addition:
            claude_context.current_system_prompt = self._append_to_system_prompt(
                claude_context.current_system_prompt,
                prompt_addition,
            )

        # Map pending_approvals → tool_call_history
        approval_tool_calls = self._approvals_to_tool_calls(maf_context.pending_approvals)
        claude_context.tool_call_history.extend(approval_tool_calls)

        # Update metadata
        claude_context.metadata["maf_workflow_id"] = maf_context.workflow_id
        claude_context.metadata["maf_workflow_name"] = maf_context.workflow_name
        claude_context.metadata["maf_current_step"] = maf_context.current_step
        claude_context.metadata["maf_total_steps"] = maf_context.total_steps
        claude_context.metadata["last_sync_from_maf"] = datetime.utcnow().isoformat()

        claude_context.last_updated = datetime.utcnow()

        logger.info(f"Sync to Claude completed: session_id={claude_context.session_id}")
        return claude_context

    async def sync_to_maf(
        self,
        claude_context: ClaudeContext,
        existing_maf: Optional[MAFContext] = None,
    ) -> MAFContext:
        """
        將 Claude 上下文同步回 MAF

        轉換映射:
        - conversation_history → execution_history
        - tool_call_history → checkpoint updates
        - context_variables → workflow metadata

        Args:
            claude_context: Source Claude context
            existing_maf: Optional existing MAF context to merge with

        Returns:
            MAFContext: Synchronized MAF context
        """
        logger.info(f"Syncing Claude context to MAF: session_id={claude_context.session_id}")

        # Start with existing or create new MAF context
        if existing_maf:
            maf_context = existing_maf
        else:
            # Extract workflow ID from session ID or metadata
            workflow_id = claude_context.metadata.get(
                "maf_workflow_id",
                f"maf-{claude_context.session_id}",
            )
            workflow_name = claude_context.metadata.get(
                "maf_workflow_name",
                "Claude-initiated Workflow",
            )
            maf_context = MAFContext(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                created_at=datetime.utcnow(),
            )

        # Map context_variables → checkpoint_data
        if self.claude_mapper:
            checkpoint = self.claude_mapper.to_maf_checkpoint(
                claude_context.context_variables,
                claude_context.tool_call_history,
            )
        else:
            checkpoint = self._default_context_vars_to_checkpoint(
                claude_context.context_variables,
                claude_context.tool_call_history,
            )
        maf_context.checkpoint_data.update(checkpoint)

        # Map conversation_history → execution_history
        if self.claude_mapper:
            records = self.claude_mapper.to_execution_records(
                claude_context.conversation_history
            )
        else:
            records = self._default_messages_to_execution(claude_context.conversation_history)

        # Merge with existing history
        maf_context.execution_history = self._merge_execution_records(
            maf_context.execution_history,
            records,
        )

        # Update step count based on execution history
        if maf_context.execution_history:
            max_step = max(r.step_index for r in maf_context.execution_history)
            maf_context.current_step = max_step

        # Update metadata
        maf_context.metadata["claude_session_id"] = claude_context.session_id
        maf_context.metadata["claude_message_count"] = len(claude_context.conversation_history)
        maf_context.metadata["claude_tool_call_count"] = len(claude_context.tool_call_history)
        maf_context.metadata["last_sync_from_claude"] = datetime.utcnow().isoformat()

        maf_context.last_updated = datetime.utcnow()

        logger.info(f"Sync to MAF completed: workflow_id={maf_context.workflow_id}")
        return maf_context

    async def merge_contexts(
        self,
        maf_context: Optional[MAFContext] = None,
        claude_context: Optional[ClaudeContext] = None,
        primary_framework: str = "maf",
    ) -> HybridContext:
        """
        合併 MAF 和 Claude 上下文

        Args:
            maf_context: MAF context
            claude_context: Claude context
            primary_framework: Which framework takes precedence ("maf" or "claude")

        Returns:
            HybridContext: Merged context
        """
        logger.info(f"Merging contexts with primary={primary_framework}")

        hybrid = HybridContext(
            maf=maf_context,
            claude=claude_context,
            primary_framework=primary_framework,
            sync_status=SyncStatus.PENDING,
        )

        # Determine sync status
        if maf_context is None and claude_context is None:
            hybrid.sync_status = SyncStatus.PENDING
        elif maf_context is None or claude_context is None:
            hybrid.sync_status = SyncStatus.PENDING
        else:
            # Both contexts exist, check for conflicts
            conflict = await self._detect_conflicts(maf_context, claude_context)
            if conflict:
                hybrid.sync_status = SyncStatus.CONFLICT
                hybrid.sync_error = f"Conflict in field: {conflict.field_path}"
            else:
                hybrid.sync_status = SyncStatus.SYNCED

        hybrid.last_sync_at = datetime.utcnow()
        hybrid.updated_at = datetime.utcnow()

        # Cache the hybrid context
        session_id = hybrid.get_session_id()
        if session_id:
            self._context_cache[session_id] = hybrid

        return hybrid

    async def get_hybrid_context(
        self,
        session_id: str,
    ) -> Optional[HybridContext]:
        """
        獲取混合上下文

        Args:
            session_id: Session or workflow ID

        Returns:
            Optional[HybridContext]: Cached hybrid context or None
        """
        return self._context_cache.get(session_id)

    async def sync_bidirectional(
        self,
        hybrid_context: HybridContext,
        strategy: SyncStrategy = SyncStrategy.MERGE,
    ) -> SyncResult:
        """
        雙向同步

        Args:
            hybrid_context: Context to sync
            strategy: Sync strategy to use

        Returns:
            SyncResult: Result of sync operation
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting bidirectional sync with strategy={strategy.value}")

        try:
            changes_applied = 0
            conflicts_resolved = 0
            conflicts: List[Conflict] = []

            # Handle missing contexts
            if hybrid_context.maf is None and hybrid_context.claude is not None:
                # Create MAF from Claude
                hybrid_context.maf = await self.sync_to_maf(hybrid_context.claude)
                changes_applied += 1

            if hybrid_context.claude is None and hybrid_context.maf is not None:
                # Create Claude from MAF
                hybrid_context.claude = await self.sync_to_claude(hybrid_context.maf)
                changes_applied += 1

            if hybrid_context.maf and hybrid_context.claude:
                # Sync both directions based on strategy
                if strategy == SyncStrategy.MAF_PRIMARY:
                    # MAF is primary, sync to Claude first
                    hybrid_context.claude = await self.sync_to_claude(
                        hybrid_context.maf,
                        hybrid_context.claude,
                    )
                    changes_applied += 1
                elif strategy == SyncStrategy.CLAUDE_PRIMARY:
                    # Claude is primary, sync to MAF
                    hybrid_context.maf = await self.sync_to_maf(
                        hybrid_context.claude,
                        hybrid_context.maf,
                    )
                    changes_applied += 1
                else:
                    # MERGE or default: sync both directions based on primary
                    if hybrid_context.primary_framework == "maf":
                        # MAF is primary, sync to Claude first
                        hybrid_context.claude = await self.sync_to_claude(
                            hybrid_context.maf,
                            hybrid_context.claude,
                        )
                        hybrid_context.maf = await self.sync_to_maf(
                            hybrid_context.claude,
                            hybrid_context.maf,
                        )
                    else:
                        # Claude is primary
                        hybrid_context.maf = await self.sync_to_maf(
                            hybrid_context.claude,
                            hybrid_context.maf,
                        )
                        hybrid_context.claude = await self.sync_to_claude(
                            hybrid_context.maf,
                            hybrid_context.claude,
                        )

                    changes_applied += 2  # Both directions synced

            hybrid_context.sync_status = SyncStatus.SYNCED
            hybrid_context.last_sync_at = datetime.utcnow()
            hybrid_context.increment_version()

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return SyncResult(
                success=True,
                direction=SyncDirection.BIDIRECTIONAL,
                strategy=strategy,
                source_version=hybrid_context.version - 1,
                target_version=hybrid_context.version,
                changes_applied=changes_applied,
                conflicts_resolved=conflicts_resolved,
                conflicts=conflicts,
                hybrid_context=hybrid_context,
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Bidirectional sync failed: {e}")
            hybrid_context.sync_status = SyncStatus.FAILED
            hybrid_context.sync_error = str(e)

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return SyncResult(
                success=False,
                direction=SyncDirection.BIDIRECTIONAL,
                strategy=strategy,
                source_version=hybrid_context.version,
                target_version=hybrid_context.version,
                hybrid_context=hybrid_context,
                error=str(e),
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
            )

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _default_checkpoint_to_context_vars(
        self,
        checkpoint: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Default conversion from checkpoint to context variables."""
        context_vars = {}
        for key, value in checkpoint.items():
            # Prefix MAF checkpoint data
            context_vars[f"maf_{key}"] = value
        return context_vars

    def _default_execution_to_messages(
        self,
        records: List[ExecutionRecord],
    ) -> List[Message]:
        """Default conversion from execution records to messages."""
        messages = []
        for record in records[-50:]:  # Limit to last 50
            # Create summary message for each execution
            content = f"[Step {record.step_index}] {record.step_name}"
            if record.output_data:
                output_summary = str(record.output_data)[:200]
                content += f": {output_summary}"
            if record.error:
                content += f" [ERROR: {record.error}]"

            messages.append(Message(
                message_id=record.record_id,
                role=MessageRole.ASSISTANT,
                content=content,
                timestamp=record.started_at,
                metadata={"source": "maf_execution", "step_index": record.step_index},
            ))
        return messages

    def _default_agent_state_to_prompt(
        self,
        agent_states: Dict[str, AgentState],
    ) -> str:
        """Default conversion from agent states to system prompt."""
        if not agent_states:
            return ""

        lines = ["[MAF Agent Context]"]
        for agent_id, state in agent_states.items():
            lines.append(f"- {state.agent_name} ({state.status.value})")
            if state.current_task:
                lines.append(f"  Task: {state.current_task}")
        return "\n".join(lines)

    def _default_context_vars_to_checkpoint(
        self,
        context_vars: Dict[str, Any],
        tool_calls: List[ToolCall],
    ) -> Dict[str, Any]:
        """Default conversion from context vars to checkpoint."""
        checkpoint = {}

        # Extract MAF-prefixed variables
        for key, value in context_vars.items():
            if key.startswith("maf_"):
                checkpoint[key[4:]] = value  # Remove maf_ prefix
            else:
                checkpoint[f"claude_{key}"] = value

        # Add tool call summaries
        if tool_calls:
            checkpoint["tool_calls_summary"] = {
                "total": len(tool_calls),
                "completed": sum(1 for t in tool_calls if t.status == ToolCallStatus.COMPLETED),
                "pending": sum(1 for t in tool_calls if t.status == ToolCallStatus.PENDING),
            }

        return checkpoint

    def _default_messages_to_execution(
        self,
        messages: List[Message],
    ) -> List[ExecutionRecord]:
        """Default conversion from messages to execution records."""
        records = []
        for i, msg in enumerate(messages):
            if msg.role == MessageRole.ASSISTANT:
                records.append(ExecutionRecord(
                    record_id=msg.message_id,
                    step_index=i,
                    step_name=f"Claude Response {i}",
                    agent_id="claude-agent",
                    output_data={"content": msg.content[:500]},
                    status="completed",
                    started_at=msg.timestamp,
                    completed_at=msg.timestamp,
                ))
        return records

    def _approvals_to_tool_calls(
        self,
        approvals: List[ApprovalRequest],
    ) -> List[ToolCall]:
        """Convert approval requests to tool calls."""
        tool_calls = []
        for approval in approvals:
            tool_calls.append(ToolCall(
                call_id=approval.request_id,
                tool_name="maf_approval_request",
                arguments={
                    "action": approval.action,
                    "description": approval.description,
                    "checkpoint_id": approval.checkpoint_id,
                },
                status=ToolCallStatus.PENDING if approval.status.value == "pending" else ToolCallStatus.COMPLETED,
                started_at=approval.requested_at,
            ))
        return tool_calls

    def _merge_messages(
        self,
        existing: List[Message],
        new: List[Message],
    ) -> List[Message]:
        """Merge message lists, avoiding duplicates."""
        existing_ids = {m.message_id for m in existing}
        merged = list(existing)
        for msg in new:
            if msg.message_id not in existing_ids:
                merged.append(msg)
        # Sort by timestamp
        merged.sort(key=lambda m: m.timestamp)
        return merged

    def _merge_execution_records(
        self,
        existing: List[ExecutionRecord],
        new: List[ExecutionRecord],
    ) -> List[ExecutionRecord]:
        """Merge execution record lists, avoiding duplicates."""
        existing_ids = {r.record_id for r in existing}
        merged = list(existing)
        for record in new:
            if record.record_id not in existing_ids:
                merged.append(record)
        # Sort by step index
        merged.sort(key=lambda r: r.step_index)
        return merged

    def _append_to_system_prompt(
        self,
        current_prompt: str,
        addition: str,
    ) -> str:
        """Append context to system prompt."""
        if not addition:
            return current_prompt
        if not current_prompt:
            return addition
        # Check if addition already exists
        if addition in current_prompt:
            return current_prompt
        return f"{current_prompt}\n\n{addition}"

    async def _detect_conflicts(
        self,
        maf: MAFContext,
        claude: ClaudeContext,
    ) -> Optional[Conflict]:
        """Detect conflicts between contexts."""
        # Check for significant time difference
        time_diff = abs((maf.last_updated - claude.last_updated).total_seconds())
        if time_diff > 60:  # More than 1 minute difference
            # Check if both have been modified
            maf_modified = "last_sync_from_claude" in maf.metadata
            claude_modified = "last_sync_from_maf" in claude.metadata

            if maf_modified and claude_modified:
                maf_sync_time = datetime.fromisoformat(
                    maf.metadata.get("last_sync_from_claude", maf.created_at.isoformat())
                )
                claude_sync_time = datetime.fromisoformat(
                    claude.metadata.get("last_sync_from_maf", claude.created_at.isoformat())
                )

                if maf.last_updated > maf_sync_time and claude.last_updated > claude_sync_time:
                    return Conflict(
                        field_path="both_modified",
                        local_value=maf.last_updated.isoformat(),
                        remote_value=claude.last_updated.isoformat(),
                        local_timestamp=maf.last_updated,
                        remote_timestamp=claude.last_updated,
                    )

        return None

    # =========================================================================
    # Public Helper Methods
    # =========================================================================

    def get_sync_status(self, hybrid_context: HybridContext) -> SyncStatus:
        """
        獲取混合上下文的同步狀態

        Args:
            hybrid_context: Hybrid context to check

        Returns:
            SyncStatus: Current sync status
        """
        return hybrid_context.sync_status

    def is_sync_needed(self, hybrid_context: HybridContext) -> bool:
        """
        檢查是否需要同步

        Args:
            hybrid_context: Hybrid context to check

        Returns:
            bool: True if sync is needed
        """
        return hybrid_context.sync_status in [
            SyncStatus.PENDING,
            SyncStatus.CONFLICT,
            SyncStatus.FAILED,
        ]

    def validate_context(
        self,
        hybrid_context: HybridContext,
    ) -> tuple[bool, List[str]]:
        """
        驗證混合上下文的有效性

        Args:
            hybrid_context: Context to validate

        Returns:
            tuple[bool, List[str]]: (is_valid, list of error messages)
        """
        errors = []

        # Check if at least one context exists
        if hybrid_context.maf is None and hybrid_context.claude is None:
            errors.append("At least one context (MAF or Claude) must be present")

        # Check context_id
        if not hybrid_context.context_id:
            errors.append("context_id is required")

        # Check version
        if hybrid_context.version < 1:
            errors.append("version must be >= 1")

        # Validate primary_framework
        if hybrid_context.primary_framework not in ["maf", "claude"]:
            errors.append("primary_framework must be 'maf' or 'claude'")

        # If MAF context exists, validate it
        if hybrid_context.maf:
            if not hybrid_context.maf.workflow_id:
                errors.append("MAF workflow_id is required")

        # If Claude context exists, validate it
        if hybrid_context.claude:
            if not hybrid_context.claude.session_id:
                errors.append("Claude session_id is required")

        return len(errors) == 0, errors
