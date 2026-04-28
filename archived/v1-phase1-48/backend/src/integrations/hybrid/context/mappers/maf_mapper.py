# =============================================================================
# IPA Platform - MAF Mapper
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Maps MAF (Microsoft Agent Framework) state to Claude context.
#
# Conversions:
#   - checkpoint_data → context_variables
#   - execution_records → conversation_history
#   - agent_states → system_prompt additions
#   - pending_approvals → tool_calls
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import (
    AgentState,
    AgentStatus,
    ApprovalRequest,
    ApprovalStatus,
    ExecutionRecord,
    Message,
    MessageRole,
    ToolCall,
    ToolCallStatus,
)
from .base import BaseMapper, MappingError

logger = logging.getLogger(__name__)


class MAFMapper(BaseMapper[Dict[str, Any], Dict[str, Any]]):
    """
    MAF 狀態映射器

    將 MAF Workflow 狀態轉換為 Claude SDK 可用的格式。

    Features:
    - Checkpoint → Context Variables (with maf_ prefix)
    - Execution History → Conversation Messages (compressed)
    - Agent States → System Prompt additions
    - Approvals → Tool Calls

    Example:
        mapper = MAFMapper()
        context_vars = mapper.to_claude_context_vars(checkpoint_data)
        messages = mapper.to_claude_history(execution_records, max_messages=50)
    """

    def __init__(
        self,
        strict: bool = False,
        prefix: str = "maf_",
        max_content_length: int = 500,
    ):
        """
        Initialize MAF Mapper.

        Args:
            strict: If True, raise errors on mapping failures
            prefix: Prefix for context variable keys
            max_content_length: Maximum content length for messages
        """
        super().__init__(strict=strict)
        self.prefix = prefix
        self.max_content_length = max_content_length

    def map(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic mapping method (required by BaseMapper).

        Args:
            source: Source dictionary

        Returns:
            Mapped dictionary with prefixed keys
        """
        return self._prefix_keys(source, self.prefix)

    def to_claude_context_vars(
        self,
        checkpoint: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert MAF checkpoint data to Claude context variables.

        Adds 'maf_' prefix to all keys to avoid conflicts.

        Args:
            checkpoint: MAF checkpoint data dictionary

        Returns:
            Context variables dictionary
        """
        self.reset_counters()
        logger.debug(f"Mapping checkpoint to context vars: {len(checkpoint)} keys")

        context_vars = {}

        for key, value in checkpoint.items():
            try:
                # Skip internal keys
                if key.startswith("_"):
                    continue

                # Handle special types
                if isinstance(value, datetime):
                    context_vars[f"{self.prefix}{key}"] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    # Keep complex types as-is for JSON serialization
                    context_vars[f"{self.prefix}{key}"] = value
                else:
                    context_vars[f"{self.prefix}{key}"] = value

            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to map checkpoint key '{key}': {e}")
                if self.strict:
                    raise MappingError(
                        f"Failed to map checkpoint key '{key}'",
                        source_type="MAFCheckpoint",
                        target_type="ClaudeContextVars",
                        field=key,
                        original_error=e,
                    )

        logger.info(
            f"Mapped checkpoint to {len(context_vars)} context vars "
            f"(errors: {self._error_count})"
        )
        return context_vars

    def to_claude_history(
        self,
        execution_records: List[ExecutionRecord],
        max_messages: int = 50,
    ) -> List[Message]:
        """
        Convert MAF execution records to Claude conversation messages.

        Compresses execution history into summarized messages.

        Args:
            execution_records: List of MAF execution records
            max_messages: Maximum number of messages to return

        Returns:
            List of Message objects
        """
        self.reset_counters()
        logger.debug(f"Mapping {len(execution_records)} execution records to messages")

        # Sort by step index
        sorted_records = sorted(execution_records, key=lambda r: r.step_index)

        # Take the most recent records
        recent_records = sorted_records[-max_messages:] if len(sorted_records) > max_messages else sorted_records

        messages = []
        for record in recent_records:
            try:
                message = self._execution_record_to_message(record)
                messages.append(message)
            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to map execution record '{record.record_id}': {e}")
                if self.strict:
                    raise MappingError(
                        f"Failed to map execution record",
                        source_type="ExecutionRecord",
                        target_type="Message",
                        field=record.record_id,
                        original_error=e,
                    )

        logger.info(
            f"Mapped {len(execution_records)} records to {len(messages)} messages "
            f"(errors: {self._error_count})"
        )
        return messages

    def _execution_record_to_message(self, record: ExecutionRecord) -> Message:
        """
        Convert single execution record to message.

        Args:
            record: Execution record

        Returns:
            Message object
        """
        # Build content from record
        content_parts = [f"[Step {record.step_index}] {record.step_name}"]

        if record.agent_id:
            content_parts.append(f"Agent: {record.agent_id}")

        if record.status:
            content_parts.append(f"Status: {record.status}")

        if record.output_data:
            output_str = str(record.output_data)
            if len(output_str) > self.max_content_length:
                output_str = self._truncate_string(output_str, self.max_content_length)
            content_parts.append(f"Output: {output_str}")

        if record.error:
            content_parts.append(f"Error: {record.error}")

        if record.duration_ms:
            content_parts.append(f"Duration: {record.duration_ms}ms")

        content = "\n".join(content_parts)

        # Determine role based on status
        role = MessageRole.ASSISTANT

        return Message(
            message_id=record.record_id,
            role=role,
            content=content,
            timestamp=record.started_at or datetime.utcnow(),
            metadata={
                "source": "maf_execution",
                "step_index": record.step_index,
                "step_name": record.step_name,
                "agent_id": record.agent_id,
                "status": record.status,
            },
        )

    def agent_state_to_system_prompt(
        self,
        agent_states: Dict[str, AgentState],
    ) -> str:
        """
        Convert agent states to system prompt addition.

        Creates a summary of active agents for Claude's context.

        Args:
            agent_states: Dictionary of agent states

        Returns:
            System prompt addition string
        """
        self.reset_counters()

        if not agent_states:
            return ""

        lines = [
            "# MAF Agent Context",
            "",
            "The following MAF agents are available in this workflow:",
            "",
        ]

        for agent_id, state in agent_states.items():
            try:
                status_emoji = self._get_status_emoji(state.status)
                line = f"- {status_emoji} **{state.agent_name}** ({agent_id})"

                if state.current_task:
                    line += f"\n  Current task: {state.current_task}"

                # Get capabilities from metadata if available
                if state.metadata and "capabilities" in state.metadata:
                    capabilities = state.metadata["capabilities"]
                    if capabilities:
                        caps = ", ".join(str(c) for c in capabilities[:5])
                        if len(capabilities) > 5:
                            caps += f", +{len(capabilities) - 5} more"
                        line += f"\n  Capabilities: {caps}"

                lines.append(line)

            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to format agent state '{agent_id}': {e}")
                if self.strict:
                    raise MappingError(
                        f"Failed to format agent state",
                        source_type="AgentState",
                        target_type="str",
                        field=agent_id,
                        original_error=e,
                    )

        lines.append("")  # Empty line at end
        return "\n".join(lines)

    def _get_status_emoji(self, status: AgentStatus) -> str:
        """Get emoji for agent status."""
        emoji_map = {
            AgentStatus.IDLE: "⏸️",
            AgentStatus.RUNNING: "🔄",
            AgentStatus.WAITING: "⏳",
            AgentStatus.COMPLETED: "✅",
            AgentStatus.FAILED: "❌",
        }
        return emoji_map.get(status, "❓")

    def approval_to_tool_call(
        self,
        approval: ApprovalRequest,
    ) -> ToolCall:
        """
        Convert approval request to tool call.

        Args:
            approval: Approval request

        Returns:
            ToolCall object
        """
        # Determine tool call status from approval status
        status_map = {
            ApprovalStatus.PENDING: ToolCallStatus.PENDING,
            ApprovalStatus.APPROVED: ToolCallStatus.COMPLETED,
            ApprovalStatus.REJECTED: ToolCallStatus.FAILED,
            ApprovalStatus.TIMEOUT: ToolCallStatus.FAILED,
        }
        status = status_map.get(approval.status, ToolCallStatus.PENDING)

        return ToolCall(
            call_id=approval.request_id,
            tool_name="maf_approval_request",
            arguments={
                "action": approval.action,
                "description": approval.description,
                "checkpoint_id": approval.checkpoint_id,
            },
            status=status,
            result=self._approval_status_to_result(approval),
            started_at=approval.requested_at,
            completed_at=approval.responded_at,
        )

    def _approval_status_to_result(
        self,
        approval: ApprovalRequest,
    ) -> Optional[str]:
        """Get result string from approval status."""
        if approval.status == ApprovalStatus.PENDING:
            return None
        elif approval.status == ApprovalStatus.APPROVED:
            return f"Approved by {approval.response_by or 'system'}"
        elif approval.status == ApprovalStatus.REJECTED:
            return f"Rejected by {approval.response_by or 'system'}: {approval.response_message or 'No reason provided'}"
        elif approval.status == ApprovalStatus.TIMEOUT:
            return "Timed out without response"
        return None

    def approvals_to_tool_calls(
        self,
        approvals: List[ApprovalRequest],
    ) -> List[ToolCall]:
        """
        Convert multiple approval requests to tool calls.

        Args:
            approvals: List of approval requests

        Returns:
            List of ToolCall objects
        """
        self.reset_counters()
        return self._safe_map_list(
            approvals,
            self.approval_to_tool_call,
            context="approvals",
        )

    def workflow_metadata_to_context(
        self,
        workflow_id: str,
        workflow_name: str,
        current_step: int,
        total_steps: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create context variables from workflow metadata.

        Args:
            workflow_id: Workflow ID
            workflow_name: Workflow name
            current_step: Current step index
            total_steps: Total number of steps
            metadata: Additional metadata

        Returns:
            Context variables dictionary
        """
        context = {
            f"{self.prefix}workflow_id": workflow_id,
            f"{self.prefix}workflow_name": workflow_name,
            f"{self.prefix}current_step": current_step,
            f"{self.prefix}total_steps": total_steps,
            f"{self.prefix}progress": f"{current_step}/{total_steps}",
            f"{self.prefix}progress_percent": (
                round(current_step / total_steps * 100, 1)
                if total_steps > 0 else 0
            ),
        }

        if metadata:
            for key, value in metadata.items():
                context[f"{self.prefix}meta_{key}"] = value

        return context
