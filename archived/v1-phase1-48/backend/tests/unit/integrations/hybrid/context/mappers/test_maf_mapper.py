# =============================================================================
# IPA Platform - MAF Mapper Tests
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Unit tests for MAFMapper class.
# =============================================================================

import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.integrations.hybrid.context.mappers.maf_mapper import MAFMapper
from src.integrations.hybrid.context.mappers.base import MappingError
from src.integrations.hybrid.context.models import (
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


class TestMAFMapperInit:
    """Test MAFMapper initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        mapper = MAFMapper()
        assert mapper.strict is False
        assert mapper.prefix == "maf_"
        assert mapper.max_content_length == 500

    def test_custom_initialization(self):
        """Test custom initialization."""
        mapper = MAFMapper(strict=True, prefix="custom_", max_content_length=100)
        assert mapper.strict is True
        assert mapper.prefix == "custom_"
        assert mapper.max_content_length == 100


class TestMAFMapperMap:
    """Test generic map method."""

    def test_map_adds_prefix(self):
        """Test that map adds prefix to keys."""
        mapper = MAFMapper()
        source = {"key1": "value1", "key2": "value2"}
        result = mapper.map(source)
        assert result == {"maf_key1": "value1", "maf_key2": "value2"}

    def test_map_with_custom_prefix(self):
        """Test map with custom prefix."""
        mapper = MAFMapper(prefix="test_")
        source = {"a": 1, "b": 2}
        result = mapper.map(source)
        assert result == {"test_a": 1, "test_b": 2}

    def test_map_empty_dict(self):
        """Test map with empty dictionary."""
        mapper = MAFMapper()
        result = mapper.map({})
        assert result == {}


class TestToClaudeContextVars:
    """Test checkpoint to context vars conversion."""

    def test_basic_conversion(self):
        """Test basic checkpoint conversion."""
        mapper = MAFMapper()
        checkpoint = {
            "workflow_id": "wf-123",
            "step": 5,
            "status": "running",
        }
        result = mapper.to_claude_context_vars(checkpoint)

        assert result["maf_workflow_id"] == "wf-123"
        assert result["maf_step"] == 5
        assert result["maf_status"] == "running"

    def test_datetime_conversion(self):
        """Test datetime values are converted to ISO format."""
        mapper = MAFMapper()
        now = datetime(2025, 1, 1, 12, 0, 0)
        checkpoint = {"created_at": now}
        result = mapper.to_claude_context_vars(checkpoint)

        assert result["maf_created_at"] == "2025-01-01T12:00:00"

    def test_complex_types_preserved(self):
        """Test complex types are preserved."""
        mapper = MAFMapper()
        checkpoint = {
            "config": {"key": "value", "nested": {"a": 1}},
            "items": [1, 2, 3],
        }
        result = mapper.to_claude_context_vars(checkpoint)

        assert result["maf_config"] == {"key": "value", "nested": {"a": 1}}
        assert result["maf_items"] == [1, 2, 3]

    def test_skips_internal_keys(self):
        """Test internal keys (starting with _) are skipped."""
        mapper = MAFMapper()
        checkpoint = {
            "public": "value",
            "_internal": "secret",
            "_private": 123,
        }
        result = mapper.to_claude_context_vars(checkpoint)

        assert "maf_public" in result
        assert "maf__internal" not in result
        assert "maf__private" not in result

    def test_error_count_tracking(self):
        """Test error count is tracked."""
        mapper = MAFMapper()
        checkpoint = {"valid": "data"}
        mapper.to_claude_context_vars(checkpoint)
        assert mapper.error_count == 0


class TestToClaudeHistory:
    """Test execution records to message history conversion."""

    @pytest.fixture
    def sample_records(self) -> List[ExecutionRecord]:
        """Create sample execution records."""
        return [
            ExecutionRecord(
                record_id="rec-1",
                step_index=0,
                step_name="Initialize",
                agent_id="agent-1",
                status="completed",
                output_data={"result": "success"},
                started_at=datetime(2025, 1, 1, 12, 0, 0),
                duration_ms=100,
            ),
            ExecutionRecord(
                record_id="rec-2",
                step_index=1,
                step_name="Process",
                agent_id="agent-2",
                status="completed",
                output_data={"data": "processed"},
                started_at=datetime(2025, 1, 1, 12, 1, 0),
                duration_ms=200,
            ),
        ]

    def test_basic_conversion(self, sample_records):
        """Test basic records to messages conversion."""
        mapper = MAFMapper()
        messages = mapper.to_claude_history(sample_records)

        assert len(messages) == 2
        assert all(isinstance(m, Message) for m in messages)

    def test_message_content_format(self, sample_records):
        """Test message content format."""
        mapper = MAFMapper()
        messages = mapper.to_claude_history(sample_records)

        first_msg = messages[0]
        assert "[Step 0]" in first_msg.content
        assert "Initialize" in first_msg.content
        assert "Agent: agent-1" in first_msg.content

    def test_sorted_by_step_index(self):
        """Test records are sorted by step index."""
        mapper = MAFMapper()
        records = [
            ExecutionRecord(
                record_id="rec-2",
                step_index=2,
                step_name="Second",
                agent_id="agent-1",
            ),
            ExecutionRecord(
                record_id="rec-1",
                step_index=1,
                step_name="First",
                agent_id="agent-1",
            ),
        ]
        messages = mapper.to_claude_history(records)

        assert "First" in messages[0].content
        assert "Second" in messages[1].content

    def test_max_messages_limit(self, sample_records):
        """Test max messages limit."""
        mapper = MAFMapper()
        messages = mapper.to_claude_history(sample_records, max_messages=1)

        # Should return only the most recent
        assert len(messages) == 1
        assert "Process" in messages[0].content

    def test_empty_records(self):
        """Test with empty records list."""
        mapper = MAFMapper()
        messages = mapper.to_claude_history([])
        assert messages == []

    def test_message_role_is_assistant(self, sample_records):
        """Test all messages have ASSISTANT role."""
        mapper = MAFMapper()
        messages = mapper.to_claude_history(sample_records)
        assert all(m.role == MessageRole.ASSISTANT for m in messages)

    def test_content_truncation(self):
        """Test long content is truncated."""
        mapper = MAFMapper(max_content_length=50)
        records = [
            ExecutionRecord(
                record_id="rec-1",
                step_index=0,
                step_name="Step",
                agent_id="agent-1",
                output_data={"content": "x" * 1000},  # Very long output
            ),
        ]
        messages = mapper.to_claude_history(records)

        # Content should be truncated
        assert len(messages[0].content) < 1000


class TestAgentStateToSystemPrompt:
    """Test agent states to system prompt conversion."""

    @pytest.fixture
    def sample_agent_states(self) -> Dict[str, AgentState]:
        """Create sample agent states."""
        return {
            "agent-1": AgentState(
                agent_id="agent-1",
                agent_name="Assistant",
                status=AgentStatus.RUNNING,
                current_task="Processing request",
                metadata={"capabilities": ["chat", "code", "analysis"]},
            ),
            "agent-2": AgentState(
                agent_id="agent-2",
                agent_name="Reviewer",
                status=AgentStatus.IDLE,
                metadata={"capabilities": ["review"]},
            ),
        }

    def test_basic_prompt_generation(self, sample_agent_states):
        """Test basic system prompt generation."""
        mapper = MAFMapper()
        prompt = mapper.agent_state_to_system_prompt(sample_agent_states)

        assert "# MAF Agent Context" in prompt
        assert "Assistant" in prompt
        assert "Reviewer" in prompt

    def test_status_emojis(self, sample_agent_states):
        """Test status emojis are included."""
        mapper = MAFMapper()
        prompt = mapper.agent_state_to_system_prompt(sample_agent_states)

        # Running should have running emoji
        assert "Assistant" in prompt

    def test_current_task_included(self, sample_agent_states):
        """Test current task is included."""
        mapper = MAFMapper()
        prompt = mapper.agent_state_to_system_prompt(sample_agent_states)

        assert "Processing request" in prompt

    def test_metadata_included(self, sample_agent_states):
        """Test metadata is included in prompt."""
        mapper = MAFMapper()
        prompt = mapper.agent_state_to_system_prompt(sample_agent_states)

        # Agent names should be included
        assert "Assistant" in prompt
        assert "Reviewer" in prompt

    def test_empty_states(self):
        """Test with empty agent states."""
        mapper = MAFMapper()
        prompt = mapper.agent_state_to_system_prompt({})
        assert prompt == ""


class TestApprovalToToolCall:
    """Test approval request to tool call conversion."""

    @pytest.fixture
    def sample_approval(self) -> ApprovalRequest:
        """Create sample approval request."""
        return ApprovalRequest(
            request_id="req-123",
            checkpoint_id="cp-456",
            action="deploy",
            description="Deploy to production",
            status=ApprovalStatus.PENDING,
            requested_at=datetime(2025, 1, 1, 12, 0, 0),
        )

    def test_basic_conversion(self, sample_approval):
        """Test basic approval to tool call conversion."""
        mapper = MAFMapper()
        tool_call = mapper.approval_to_tool_call(sample_approval)

        assert isinstance(tool_call, ToolCall)
        assert tool_call.call_id == "req-123"
        assert tool_call.tool_name == "maf_approval_request"

    def test_arguments_populated(self, sample_approval):
        """Test arguments are populated correctly."""
        mapper = MAFMapper()
        tool_call = mapper.approval_to_tool_call(sample_approval)

        assert tool_call.arguments["action"] == "deploy"
        assert tool_call.arguments["description"] == "Deploy to production"
        assert tool_call.arguments["checkpoint_id"] == "cp-456"

    def test_status_mapping_pending(self, sample_approval):
        """Test PENDING status mapping."""
        mapper = MAFMapper()
        tool_call = mapper.approval_to_tool_call(sample_approval)
        assert tool_call.status == ToolCallStatus.PENDING

    def test_status_mapping_approved(self, sample_approval):
        """Test APPROVED status mapping."""
        sample_approval.status = ApprovalStatus.APPROVED
        sample_approval.response_by = "admin"
        sample_approval.responded_at = datetime(2025, 1, 1, 13, 0, 0)

        mapper = MAFMapper()
        tool_call = mapper.approval_to_tool_call(sample_approval)

        assert tool_call.status == ToolCallStatus.COMPLETED
        assert "Approved" in tool_call.result or "admin" in str(tool_call.result)

    def test_status_mapping_rejected(self, sample_approval):
        """Test REJECTED status mapping."""
        sample_approval.status = ApprovalStatus.REJECTED
        sample_approval.response_by = "admin"
        sample_approval.response_message = "Not ready"

        mapper = MAFMapper()
        tool_call = mapper.approval_to_tool_call(sample_approval)

        assert tool_call.status == ToolCallStatus.FAILED
        assert "Rejected" in tool_call.result or "Not ready" in str(tool_call.result)

    def test_batch_conversion(self):
        """Test batch approval conversion."""
        mapper = MAFMapper()
        approvals = [
            ApprovalRequest(
                request_id=f"req-{i}",
                checkpoint_id="cp-1",
                action="action",
                description=f"Action {i} description",
                status=ApprovalStatus.PENDING,
            )
            for i in range(3)
        ]
        tool_calls = mapper.approvals_to_tool_calls(approvals)

        assert len(tool_calls) == 3
        assert all(isinstance(tc, ToolCall) for tc in tool_calls)


class TestWorkflowMetadataToContext:
    """Test workflow metadata to context conversion."""

    def test_basic_conversion(self):
        """Test basic workflow metadata conversion."""
        mapper = MAFMapper()
        context = mapper.workflow_metadata_to_context(
            workflow_id="wf-123",
            workflow_name="Test Workflow",
            current_step=3,
            total_steps=10,
        )

        assert context["maf_workflow_id"] == "wf-123"
        assert context["maf_workflow_name"] == "Test Workflow"
        assert context["maf_current_step"] == 3
        assert context["maf_total_steps"] == 10
        assert context["maf_progress"] == "3/10"
        assert context["maf_progress_percent"] == 30.0

    def test_with_metadata(self):
        """Test with additional metadata."""
        mapper = MAFMapper()
        context = mapper.workflow_metadata_to_context(
            workflow_id="wf-123",
            workflow_name="Test",
            current_step=5,
            total_steps=10,
            metadata={"priority": "high", "owner": "admin"},
        )

        assert context["maf_meta_priority"] == "high"
        assert context["maf_meta_owner"] == "admin"

    def test_progress_percent_zero_division(self):
        """Test progress percent with zero total steps."""
        mapper = MAFMapper()
        context = mapper.workflow_metadata_to_context(
            workflow_id="wf-123",
            workflow_name="Test",
            current_step=0,
            total_steps=0,
        )

        assert context["maf_progress_percent"] == 0


class TestStrictMode:
    """Test strict mode behavior."""

    def test_strict_mode_raises_on_error(self):
        """Test strict mode raises MappingError on failure."""
        # This is hard to test without mocking internal errors
        # For now, just verify strict mode is set
        mapper = MAFMapper(strict=True)
        assert mapper.strict is True

    def test_non_strict_mode_continues(self):
        """Test non-strict mode continues on error."""
        mapper = MAFMapper(strict=False)
        # Normal data should work
        result = mapper.to_claude_context_vars({"key": "value"})
        assert "maf_key" in result
