# =============================================================================
# IPA Platform - Claude Mapper
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Maps Claude SDK state to MAF context.
#
# Conversions:
#   - context_variables → checkpoint_data
#   - conversation_history → execution_records
#   - tool_calls → pending_approvals (for HITL)
#   - session_metadata → workflow_metadata
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import (
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


class ClaudeMapper(BaseMapper[Dict[str, Any], Dict[str, Any]]):
    """
    Claude 狀態映射器

    將 Claude SDK 狀態轉換為 MAF Workflow 可用的格式。

    Features:
    - Context Variables → Checkpoint (remove claude_ prefix)
    - Conversation History → Execution Records
    - Tool Calls → Approval Requests (for HITL tools)
    - Session Metadata → Workflow Metadata

    Example:
        mapper = ClaudeMapper()
        checkpoint = mapper.to_maf_checkpoint(context_vars)
        records = mapper.to_execution_records(messages)
    """

    def __init__(
        self,
        strict: bool = False,
        prefix: str = "claude_",
        max_content_length: int = 1000,
    ):
        """
        Initialize Claude Mapper.

        Args:
            strict: If True, raise errors on mapping failures
            prefix: Prefix to remove from context variable keys
            max_content_length: Maximum content length for records
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
            Mapped dictionary with unprefixed keys
        """
        return self._unprefix_keys(source, self.prefix)

    def to_maf_checkpoint(
        self,
        context_vars: Dict[str, Any],
        tool_calls: Optional[List[ToolCall]] = None,
    ) -> Dict[str, Any]:
        """
        Convert Claude context variables to MAF checkpoint data.

        Removes 'claude_' prefix from keys and adds tool call state.

        Args:
            context_vars: Claude context variables dictionary
            tool_calls: Optional list of tool calls to include

        Returns:
            Checkpoint data dictionary
        """
        self.reset_counters()
        logger.debug(f"Mapping context vars to checkpoint: {len(context_vars)} keys")

        checkpoint = {}

        for key, value in context_vars.items():
            try:
                # Remove prefix if present
                if key.startswith(self.prefix):
                    new_key = key[len(self.prefix):]
                else:
                    new_key = key

                # Skip internal keys
                if new_key.startswith("_"):
                    continue

                # Handle special types
                if isinstance(value, datetime):
                    checkpoint[new_key] = value.isoformat()
                else:
                    checkpoint[new_key] = value

            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to map context var '{key}': {e}")
                if self.strict:
                    raise MappingError(
                        f"Failed to map context var '{key}'",
                        source_type="ClaudeContextVars",
                        target_type="MAFCheckpoint",
                        field=key,
                        original_error=e,
                    )

        # Add tool call state if provided
        if tool_calls:
            checkpoint["_pending_tool_calls"] = [
                self._tool_call_to_dict(tc) for tc in tool_calls
            ]

        logger.info(
            f"Mapped {len(context_vars)} context vars to checkpoint "
            f"(errors: {self._error_count})"
        )
        return checkpoint

    def _tool_call_to_dict(self, tool_call: ToolCall) -> Dict[str, Any]:
        """Convert ToolCall to dictionary for checkpoint storage."""
        return {
            "call_id": tool_call.call_id,
            "tool_name": tool_call.tool_name,
            "arguments": tool_call.arguments,
            "status": tool_call.status.value if tool_call.status else None,
            "result": tool_call.result,
            "started_at": (
                tool_call.started_at.isoformat()
                if tool_call.started_at else None
            ),
            "completed_at": (
                tool_call.completed_at.isoformat()
                if tool_call.completed_at else None
            ),
        }

    def to_execution_records(
        self,
        messages: List[Message],
        default_agent_id: str = "claude_assistant",
    ) -> List[ExecutionRecord]:
        """
        Convert Claude conversation messages to MAF execution records.

        Creates execution records from assistant messages with tool information.

        Args:
            messages: List of conversation messages
            default_agent_id: Default agent ID when not in metadata

        Returns:
            List of ExecutionRecord objects
        """
        self.reset_counters()
        logger.debug(f"Mapping {len(messages)} messages to execution records")

        records = []
        step_index = 0

        for message in messages:
            try:
                # Only create records for assistant messages
                if message.role != MessageRole.ASSISTANT:
                    continue

                record = self._message_to_execution_record(
                    message, step_index, default_agent_id
                )
                records.append(record)
                step_index += 1

            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to map message '{message.message_id}': {e}")
                if self.strict:
                    raise MappingError(
                        f"Failed to map message",
                        source_type="Message",
                        target_type="ExecutionRecord",
                        field=message.message_id,
                        original_error=e,
                    )

        logger.info(
            f"Mapped {len(messages)} messages to {len(records)} records "
            f"(errors: {self._error_count})"
        )
        return records

    def _message_to_execution_record(
        self,
        message: Message,
        step_index: int,
        default_agent_id: str = "claude_assistant",
    ) -> ExecutionRecord:
        """
        Convert single message to execution record.

        Args:
            message: Message to convert
            step_index: Step index in workflow
            default_agent_id: Default agent ID

        Returns:
            ExecutionRecord object
        """
        # Build step name from message content
        content = message.content or ""
        if len(content) > 50:
            step_name = content[:47] + "..."
        else:
            step_name = content or f"Step {step_index}"

        # Extract agent ID from metadata if available
        agent_id = default_agent_id
        if message.metadata:
            agent_id = message.metadata.get("agent_id", default_agent_id)

        # Determine status
        status = "completed"
        error = None
        if message.metadata:
            if message.metadata.get("error"):
                status = "failed"
                error = message.metadata.get("error")

        # Build output_data dict
        output_data = {"content": message.content} if message.content else {}

        return ExecutionRecord(
            record_id=message.message_id,
            step_index=step_index,
            step_name=step_name,
            agent_id=agent_id,
            status=status,
            output_data=output_data,
            error=error,
            started_at=message.timestamp,
            completed_at=message.timestamp,
            duration_ms=0,  # Not tracked in messages
        )

    def tool_call_to_approval_request(
        self,
        tool_call: ToolCall,
        checkpoint_id: str,
    ) -> ApprovalRequest:
        """
        Convert tool call to approval request for HITL.

        Args:
            tool_call: Tool call requiring approval
            checkpoint_id: Associated checkpoint ID

        Returns:
            ApprovalRequest object
        """
        # Determine approval status from tool call status
        status_map = {
            ToolCallStatus.PENDING: ApprovalStatus.PENDING,
            ToolCallStatus.EXECUTING: ApprovalStatus.PENDING,
            ToolCallStatus.COMPLETED: ApprovalStatus.APPROVED,
            ToolCallStatus.FAILED: ApprovalStatus.REJECTED,
            ToolCallStatus.CANCELLED: ApprovalStatus.REJECTED,
        }
        status = status_map.get(tool_call.status, ApprovalStatus.PENDING)

        # Build description from tool call
        description = f"Tool: {tool_call.tool_name}"
        if tool_call.arguments:
            args_str = str(tool_call.arguments)
            if len(args_str) > 200:
                args_str = args_str[:197] + "..."
            description += f"\nArguments: {args_str}"

        return ApprovalRequest(
            request_id=tool_call.call_id,
            checkpoint_id=checkpoint_id,
            action=f"execute_{tool_call.tool_name}",
            description=description,
            status=status,
            requested_at=tool_call.started_at or datetime.utcnow(),
            responded_at=tool_call.completed_at,
            response_message=(
                str(tool_call.result) if tool_call.status == ToolCallStatus.FAILED else None
            ),
        )

    def tool_calls_to_approval_requests(
        self,
        tool_calls: List[ToolCall],
        checkpoint_id: str,
    ) -> List[ApprovalRequest]:
        """
        Convert multiple tool calls to approval requests.

        Args:
            tool_calls: List of tool calls
            checkpoint_id: Associated checkpoint ID

        Returns:
            List of ApprovalRequest objects
        """
        self.reset_counters()
        return self._safe_map_list(
            tool_calls,
            lambda tc: self.tool_call_to_approval_request(tc, checkpoint_id),
            context="tool_calls",
        )

    def session_metadata_to_workflow(
        self,
        session_id: str,
        session_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert Claude session metadata to MAF workflow metadata.

        Args:
            session_id: Claude session ID
            session_metadata: Session metadata dictionary

        Returns:
            Workflow metadata dictionary
        """
        self.reset_counters()

        workflow_meta = {
            "source": "claude_sdk",
            "session_id": session_id,
        }

        # Map known fields
        field_mappings = {
            "model": "llm_model",
            "temperature": "llm_temperature",
            "max_tokens": "llm_max_tokens",
            "system_prompt": "agent_instructions",
            "tools": "available_tools",
            "created_at": "started_at",
            "updated_at": "last_activity",
        }

        for claude_key, maf_key in field_mappings.items():
            if claude_key in session_metadata:
                value = session_metadata[claude_key]
                if isinstance(value, datetime):
                    value = value.isoformat()
                workflow_meta[maf_key] = value

        # Copy remaining fields with prefix
        for key, value in session_metadata.items():
            if key not in field_mappings:
                if isinstance(value, datetime):
                    value = value.isoformat()
                workflow_meta[f"claude_{key}"] = value

        return workflow_meta

    def conversation_summary(
        self,
        messages: List[Message],
        max_length: int = 500,
    ) -> str:
        """
        Create a summary of conversation for MAF context.

        Args:
            messages: List of conversation messages
            max_length: Maximum summary length

        Returns:
            Conversation summary string
        """
        if not messages:
            return "No conversation history."

        lines = ["# Claude Conversation Summary", ""]

        # Count message types
        user_count = sum(1 for m in messages if m.role == MessageRole.USER)
        assistant_count = sum(1 for m in messages if m.role == MessageRole.ASSISTANT)
        tool_count = sum(1 for m in messages if m.role == MessageRole.TOOL)

        lines.append(f"Messages: {len(messages)} total")
        lines.append(f"  - User: {user_count}")
        lines.append(f"  - Assistant: {assistant_count}")
        lines.append(f"  - Tool: {tool_count}")
        lines.append("")

        # Add recent messages summary
        recent = messages[-5:]  # Last 5 messages
        lines.append("Recent activity:")
        for msg in recent:
            role_emoji = {
                MessageRole.USER: "👤",
                MessageRole.ASSISTANT: "🤖",
                MessageRole.SYSTEM: "⚙️",
                MessageRole.TOOL: "🔧",
            }.get(msg.role, "❓")

            content = msg.content or ""
            if len(content) > 100:
                content = content[:97] + "..."
            lines.append(f"  {role_emoji} {content}")

        summary = "\n".join(lines)
        return self._truncate_string(summary, max_length)

    def extract_tool_results(
        self,
        messages: List[Message],
    ) -> Dict[str, Any]:
        """
        Extract tool results from conversation for checkpoint.

        Args:
            messages: List of conversation messages

        Returns:
            Dictionary of tool results keyed by tool call ID
        """
        results = {}

        for message in messages:
            if message.role == MessageRole.TOOL:
                # Tool messages contain results
                if message.metadata:
                    call_id = message.metadata.get("tool_call_id")
                    if call_id:
                        results[call_id] = {
                            "content": message.content,
                            "timestamp": (
                                message.timestamp.isoformat()
                                if message.timestamp else None
                            ),
                            "metadata": message.metadata,
                        }

        return results
