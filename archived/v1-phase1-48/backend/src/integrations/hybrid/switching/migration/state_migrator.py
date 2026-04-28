# =============================================================================
# IPA Platform - State Migrator
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-3 State Migration
#
# Handles state migration between execution modes.
#
# Key Features:
#   - Workflow → Chat migration (execution history → conversation)
#   - Chat → Workflow migration (conversation → workflow state)
#   - Hybrid mode migration support
#   - Data integrity validation
#
# Dependencies:
#   - ExecutionMode (src.integrations.hybrid.intent.models)
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.integrations.hybrid.intent.models import ExecutionMode

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class MigrationError(Exception):
    """Raised when state migration fails."""

    def __init__(
        self,
        message: str,
        source_mode: Optional[ExecutionMode] = None,
        target_mode: Optional[ExecutionMode] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.source_mode = source_mode
        self.target_mode = target_mode
        self.details = details or {}


# =============================================================================
# Enums
# =============================================================================


class MigrationStatus(str, Enum):
    """Migration status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class MigrationConfig:
    """
    Configuration for state migration.

    Attributes:
        preserve_history: Whether to preserve execution/conversation history
        max_history_items: Maximum number of history items to migrate
        include_tool_calls: Whether to include tool call records
        include_metadata: Whether to include metadata
        validate_before_migrate: Whether to validate before migration
        validate_after_migrate: Whether to validate after migration
    """

    preserve_history: bool = True
    max_history_items: int = 100
    include_tool_calls: bool = True
    include_metadata: bool = True
    validate_before_migrate: bool = True
    validate_after_migrate: bool = True


@dataclass
class MigratedState:
    """
    Result of state migration.

    Attributes:
        source_mode: Original execution mode
        target_mode: Target execution mode
        status: Migration status
        migrated_at: When migration occurred
        conversation_history: Migrated conversation history
        workflow_state: Migrated workflow state
        tool_call_records: Migrated tool call records
        context_summary: Summary for context window
        preserved_data: Additional preserved data
        warnings: Any warnings during migration
    """

    source_mode: ExecutionMode
    target_mode: ExecutionMode
    status: MigrationStatus = MigrationStatus.COMPLETED
    migrated_at: datetime = field(default_factory=datetime.utcnow)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    tool_call_records: List[Dict[str, Any]] = field(default_factory=list)
    context_summary: str = ""
    preserved_data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def is_successful(self) -> bool:
        """Check if migration was successful."""
        return self.status in (MigrationStatus.COMPLETED, MigrationStatus.PARTIAL)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_mode": self.source_mode.value if hasattr(self.source_mode, 'value') else str(self.source_mode),
            "target_mode": self.target_mode.value if hasattr(self.target_mode, 'value') else str(self.target_mode),
            "status": self.status.value,
            "migrated_at": self.migrated_at.isoformat(),
            "conversation_history": self.conversation_history,
            "workflow_state": self.workflow_state,
            "tool_call_records": self.tool_call_records,
            "context_summary": self.context_summary,
            "preserved_data": self.preserved_data,
            "warnings": self.warnings,
        }


@dataclass
class MigrationContext:
    """
    Context data for migration.

    Represents the current state that needs to be migrated.

    Attributes:
        session_id: Session identifier
        current_mode: Current execution mode
        conversation_history: Current conversation history
        workflow_steps: Workflow execution steps
        tool_calls: Tool call records
        variables: Workflow variables
        agent_states: Agent state data
        metadata: Additional metadata
    """

    session_id: str
    current_mode: ExecutionMode
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    workflow_steps: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Migration Validator
# =============================================================================


class MigrationValidator:
    """
    Validates state migration.

    Ensures data integrity before and after migration.
    """

    def validate_source(
        self,
        context: MigrationContext,
        target_mode: ExecutionMode,
    ) -> tuple[bool, List[str]]:
        """
        Validate source context before migration.

        Args:
            context: Migration context to validate
            target_mode: Target execution mode

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check session ID
        if not context.session_id:
            issues.append("Missing session ID")

        # Check current mode
        if not context.current_mode:
            issues.append("Missing current mode")

        # Check for same mode migration (not an issue, just a warning)
        if context.current_mode == target_mode:
            issues.append("Source and target modes are the same")

        # Mode-specific validation
        if context.current_mode == ExecutionMode.WORKFLOW_MODE:
            # Workflow mode should have some execution data
            if not context.workflow_steps and not context.tool_calls:
                issues.append("Workflow mode has no execution data to migrate")

        elif context.current_mode == ExecutionMode.CHAT_MODE:
            # Chat mode should have conversation history
            if not context.conversation_history:
                issues.append("Chat mode has no conversation history to migrate")

        is_valid = len(issues) == 0 or all(
            "same" in issue.lower() for issue in issues
        )
        return is_valid, issues

    def validate_result(
        self,
        result: MigratedState,
        source_context: MigrationContext,
    ) -> tuple[bool, List[str]]:
        """
        Validate migration result.

        Args:
            result: Migration result to validate
            source_context: Original migration context

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check status
        if result.status == MigrationStatus.FAILED:
            issues.append("Migration failed")
            return False, issues

        # Check data preservation
        if source_context.conversation_history and not result.conversation_history:
            issues.append("Conversation history was lost during migration")

        if source_context.tool_calls and not result.tool_call_records:
            issues.append("Tool call records were lost during migration")

        # Check context summary for workflow → chat migration
        if (
            source_context.current_mode == ExecutionMode.WORKFLOW_MODE
            and result.target_mode == ExecutionMode.CHAT_MODE
            and not result.context_summary
        ):
            issues.append("Missing context summary for workflow to chat migration")

        is_valid = len(issues) == 0
        return is_valid, issues


# =============================================================================
# State Migrator
# =============================================================================


class StateMigrator:
    """
    Handles state migration between execution modes.

    Supports migration between:
    - Workflow → Chat (execution history → conversation)
    - Chat → Workflow (conversation → workflow state)
    - Hybrid mode transitions

    Example:
        >>> migrator = StateMigrator()
        >>> context = MigrationContext(
        ...     session_id="sess-123",
        ...     current_mode=ExecutionMode.WORKFLOW_MODE,
        ...     workflow_steps=[{"step": 1, "action": "fetch_data"}],
        ...     tool_calls=[{"tool": "http_request", "result": "..."}],
        ... )
        >>> result = await migrator.migrate(
        ...     context,
        ...     source_mode=ExecutionMode.WORKFLOW_MODE,
        ...     target_mode=ExecutionMode.CHAT_MODE,
        ... )
        >>> print(result.status)  # MigrationStatus.COMPLETED
    """

    def __init__(self, config: Optional[MigrationConfig] = None) -> None:
        """
        Initialize state migrator.

        Args:
            config: Migration configuration
        """
        self.config = config or MigrationConfig()
        self.validator = MigrationValidator()
        self._migration_count = 0

    async def migrate(
        self,
        context: MigrationContext,
        source_mode: ExecutionMode,
        target_mode: ExecutionMode,
    ) -> MigratedState:
        """
        Migrate state from source mode to target mode.

        Args:
            context: Current context to migrate
            source_mode: Source execution mode
            target_mode: Target execution mode

        Returns:
            MigratedState with migration results

        Raises:
            MigrationError: If migration fails and validation is strict
        """
        logger.info(
            f"Migrating state from {source_mode} to {target_mode} "
            f"for session {context.session_id}"
        )

        # Validate source if configured
        if self.config.validate_before_migrate:
            is_valid, issues = self.validator.validate_source(context, target_mode)
            if not is_valid:
                raise MigrationError(
                    f"Source validation failed: {', '.join(issues)}",
                    source_mode=source_mode,
                    target_mode=target_mode,
                    details={"validation_issues": issues},
                )

        # Perform migration based on modes
        try:
            if source_mode == ExecutionMode.WORKFLOW_MODE:
                result = await self._workflow_to_chat(context, target_mode)
            elif source_mode == ExecutionMode.CHAT_MODE:
                result = await self._chat_to_workflow(context, target_mode)
            else:
                result = await self._hybrid_migration(context, source_mode, target_mode)

            # Validate result if configured
            if self.config.validate_after_migrate:
                is_valid, issues = self.validator.validate_result(result, context)
                if not is_valid:
                    result.warnings.extend(issues)
                    if result.status == MigrationStatus.COMPLETED:
                        result.status = MigrationStatus.PARTIAL

            self._migration_count += 1
            logger.info(
                f"Migration completed with status {result.status} "
                f"for session {context.session_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            raise MigrationError(
                f"Migration failed: {str(e)}",
                source_mode=source_mode,
                target_mode=target_mode,
            ) from e

    async def _workflow_to_chat(
        self,
        context: MigrationContext,
        target_mode: ExecutionMode,
    ) -> MigratedState:
        """
        Migrate from Workflow mode to Chat mode.

        Preserves:
        - Execution history (converted to conversation history)
        - Intermediate results
        - Tool call records

        Converts:
        - Workflow steps → Chat context summary
        - Agent states → System prompt context
        """
        conversation_history = []

        # Convert workflow steps to conversation history
        for step in context.workflow_steps[: self.config.max_history_items]:
            conversation_history.append({
                "role": "assistant",
                "content": f"[Workflow Step] {step.get('action', 'Unknown action')}",
                "metadata": {
                    "type": "workflow_step",
                    "original_step": step,
                },
            })

        # Add existing conversation history
        if self.config.preserve_history:
            for msg in context.conversation_history[: self.config.max_history_items]:
                conversation_history.append(msg)

        # Build context summary
        context_summary = self._build_workflow_summary(context)

        # Migrate tool calls
        tool_call_records = []
        if self.config.include_tool_calls:
            tool_call_records = context.tool_calls[: self.config.max_history_items]

        # Preserve additional data
        preserved_data = {}
        if self.config.include_metadata:
            preserved_data = {
                "original_variables": context.variables,
                "agent_states": context.agent_states,
                "original_metadata": context.metadata,
            }

        return MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=target_mode,
            status=MigrationStatus.COMPLETED,
            conversation_history=conversation_history,
            tool_call_records=tool_call_records,
            context_summary=context_summary,
            preserved_data=preserved_data,
        )

    async def _chat_to_workflow(
        self,
        context: MigrationContext,
        target_mode: ExecutionMode,
    ) -> MigratedState:
        """
        Migrate from Chat mode to Workflow mode.

        Preserves:
        - Conversation history (as workflow context)
        - Tool call results
        - User intent

        Converts:
        - Conversation → Initial workflow state
        - Claude context → Workflow variables
        """
        # Build workflow state from conversation
        workflow_state = {
            "initial_context": self._extract_intent_from_conversation(
                context.conversation_history
            ),
            "variables": context.variables.copy(),
            "conversation_summary": self._summarize_conversation(
                context.conversation_history
            ),
        }

        # Migrate tool calls
        tool_call_records = []
        if self.config.include_tool_calls:
            tool_call_records = context.tool_calls[: self.config.max_history_items]

        # Keep conversation history for reference
        conversation_history = []
        if self.config.preserve_history:
            conversation_history = context.conversation_history[
                : self.config.max_history_items
            ]

        # Preserve additional data
        preserved_data = {}
        if self.config.include_metadata:
            preserved_data = {
                "original_metadata": context.metadata,
            }

        return MigratedState(
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=target_mode,
            status=MigrationStatus.COMPLETED,
            conversation_history=conversation_history,
            workflow_state=workflow_state,
            tool_call_records=tool_call_records,
            context_summary="",  # Not needed for chat → workflow
            preserved_data=preserved_data,
        )

    async def _hybrid_migration(
        self,
        context: MigrationContext,
        source_mode: ExecutionMode,
        target_mode: ExecutionMode,
    ) -> MigratedState:
        """
        Handle hybrid mode migration.

        Combines both workflow and chat state preservation.
        """
        # For hybrid, we preserve everything
        conversation_history = context.conversation_history[
            : self.config.max_history_items
        ]

        workflow_state = {
            "steps": context.workflow_steps,
            "variables": context.variables,
        }

        tool_call_records = context.tool_calls[: self.config.max_history_items]

        context_summary = self._build_workflow_summary(context)

        preserved_data = {
            "agent_states": context.agent_states,
            "original_metadata": context.metadata,
        }

        return MigratedState(
            source_mode=source_mode,
            target_mode=target_mode,
            status=MigrationStatus.COMPLETED,
            conversation_history=conversation_history,
            workflow_state=workflow_state,
            tool_call_records=tool_call_records,
            context_summary=context_summary,
            preserved_data=preserved_data,
        )

    def _build_workflow_summary(self, context: MigrationContext) -> str:
        """Build context summary from workflow execution."""
        parts = []

        if context.workflow_steps:
            step_count = len(context.workflow_steps)
            parts.append(f"Executed {step_count} workflow steps")

            # Include last few step actions
            recent_steps = context.workflow_steps[-3:]
            actions = [s.get("action", "unknown") for s in recent_steps]
            parts.append(f"Recent actions: {', '.join(actions)}")

        if context.tool_calls:
            tool_count = len(context.tool_calls)
            parts.append(f"Made {tool_count} tool calls")

        if context.variables:
            var_count = len(context.variables)
            parts.append(f"Variables set: {var_count}")

        return ". ".join(parts) if parts else "No workflow context available"

    def _extract_intent_from_conversation(
        self, history: List[Dict[str, Any]]
    ) -> str:
        """Extract user intent from conversation history."""
        # Look for the most recent user message
        for msg in reversed(history):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                # Return first 500 chars as intent context
                return content[:500] if len(content) > 500 else content
        return ""

    def _summarize_conversation(
        self, history: List[Dict[str, Any]]
    ) -> str:
        """Create a brief summary of conversation history."""
        if not history:
            return "No prior conversation"

        message_count = len(history)
        user_messages = sum(1 for m in history if m.get("role") == "user")
        assistant_messages = sum(1 for m in history if m.get("role") == "assistant")

        return (
            f"Conversation with {message_count} messages "
            f"({user_messages} user, {assistant_messages} assistant)"
        )

    def get_migration_count(self) -> int:
        """Get the number of migrations performed."""
        return self._migration_count

    def __repr__(self) -> str:
        return f"StateMigrator(migrations={self._migration_count})"
