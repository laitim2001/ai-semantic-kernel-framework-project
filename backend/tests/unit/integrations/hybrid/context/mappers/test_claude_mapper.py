# =============================================================================
# IPA Platform - Claude Mapper Tests
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Unit tests for ClaudeMapper class.
# =============================================================================

import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.integrations.hybrid.context.mappers.claude_mapper import ClaudeMapper
from src.integrations.hybrid.context.mappers.base import MappingError
from src.integrations.hybrid.context.models import (
    ApprovalRequest,
    ApprovalStatus,
    ExecutionRecord,
    Message,
    MessageRole,
    ToolCall,
    ToolCallStatus,
)


class TestClaudeMapperInit:
    """Test ClaudeMapper initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        mapper = ClaudeMapper()
        assert mapper.strict is False
        assert mapper.prefix == "claude_"
        assert mapper.max_content_length == 1000

    def test_custom_initialization(self):
        """Test custom initialization."""
        mapper = ClaudeMapper(strict=True, prefix="sdk_", max_content_length=500)
        assert mapper.strict is True
        assert mapper.prefix == "sdk_"
        assert mapper.max_content_length == 500


class TestClaudeMapperMap:
    """Test generic map method."""

    def test_map_removes_prefix(self):
        """Test that map removes prefix from keys."""
        mapper = ClaudeMapper()
        source = {"claude_key1": "value1", "claude_key2": "value2"}
        result = mapper.map(source)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_map_preserves_non_prefixed(self):
        """Test that non-prefixed keys are preserved."""
        mapper = ClaudeMapper()
        source = {"claude_a": 1, "other_b": 2}
        result = mapper.map(source)
        assert result == {"a": 1, "other_b": 2}

    def test_map_empty_dict(self):
        """Test map with empty dictionary."""
        mapper = ClaudeMapper()
        result = mapper.map({})
        assert result == {}


class TestToMAFCheckpoint:
    """Test context vars to checkpoint conversion."""

    def test_basic_conversion(self):
        """Test basic context vars conversion."""
        mapper = ClaudeMapper()
        context_vars = {
            "claude_session_id": "sess-123",
            "claude_model": "gpt-4",
            "claude_temperature": 0.7,
        }
        result = mapper.to_maf_checkpoint(context_vars)

        assert result["session_id"] == "sess-123"
        assert result["model"] == "gpt-4"
        assert result["temperature"] == 0.7

    def test_datetime_conversion(self):
        """Test datetime values are converted to ISO format."""
        mapper = ClaudeMapper()
        now = datetime(2025, 1, 1, 12, 0, 0)
        context_vars = {"claude_created_at": now}
        result = mapper.to_maf_checkpoint(context_vars)

        assert result["created_at"] == "2025-01-01T12:00:00"

    def test_skips_internal_keys(self):
        """Test internal keys are skipped."""
        mapper = ClaudeMapper()
        context_vars = {
            "claude_public": "value",
            "claude__internal": "secret",
        }
        result = mapper.to_maf_checkpoint(context_vars)

        assert "public" in result
        assert "_internal" not in result

    def test_with_tool_calls(self):
        """Test checkpoint includes tool calls."""
        mapper = ClaudeMapper()
        tool_calls = [
            ToolCall(
                call_id="tc-1",
                tool_name="search",
                arguments={"query": "test"},
                status=ToolCallStatus.COMPLETED,
            )
        ]
        result = mapper.to_maf_checkpoint({"claude_key": "value"}, tool_calls)

        assert "_pending_tool_calls" in result
        assert len(result["_pending_tool_calls"]) == 1
        assert result["_pending_tool_calls"][0]["tool_name"] == "search"

    def test_error_count_tracking(self):
        """Test error count is tracked."""
        mapper = ClaudeMapper()
        mapper.to_maf_checkpoint({"claude_valid": "data"})
        assert mapper.error_count == 0


class TestToExecutionRecords:
    """Test messages to execution records conversion."""

    @pytest.fixture
    def sample_messages(self) -> List[Message]:
        """Create sample messages."""
        return [
            Message(
                message_id="msg-1",
                role=MessageRole.USER,
                content="Hello, please help me",
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
            ),
            Message(
                message_id="msg-2",
                role=MessageRole.ASSISTANT,
                content="I'll help you with that task",
                timestamp=datetime(2025, 1, 1, 12, 0, 30),
            ),
            Message(
                message_id="msg-3",
                role=MessageRole.ASSISTANT,
                content="Task completed successfully",
                timestamp=datetime(2025, 1, 1, 12, 1, 0),
            ),
        ]

    def test_basic_conversion(self, sample_messages):
        """Test basic messages to records conversion."""
        mapper = ClaudeMapper()
        records = mapper.to_execution_records(sample_messages)

        # Only assistant messages become records
        assert len(records) == 2
        assert all(isinstance(r, ExecutionRecord) for r in records)

    def test_only_assistant_messages(self, sample_messages):
        """Test only ASSISTANT messages are converted."""
        mapper = ClaudeMapper()
        records = mapper.to_execution_records(sample_messages)

        # Should not include USER message
        assert len(records) == 2
        assert "help you" in records[0].output_data or "help you" in records[0].step_name

    def test_step_index_assignment(self, sample_messages):
        """Test step indices are assigned correctly."""
        mapper = ClaudeMapper()
        records = mapper.to_execution_records(sample_messages)

        assert records[0].step_index == 0
        assert records[1].step_index == 1

    def test_custom_agent_id_assignment(self, sample_messages):
        """Test custom agent ID is assigned."""
        mapper = ClaudeMapper()
        records = mapper.to_execution_records(sample_messages, default_agent_id="custom_agent")

        assert all(r.agent_id == "custom_agent" for r in records)

    def test_empty_messages(self):
        """Test with empty messages list."""
        mapper = ClaudeMapper()
        records = mapper.to_execution_records([])
        assert records == []

    def test_step_name_truncation(self):
        """Test long content is truncated in step name."""
        mapper = ClaudeMapper()
        messages = [
            Message(
                message_id="msg-1",
                role=MessageRole.ASSISTANT,
                content="x" * 100,  # Long content
                timestamp=datetime.utcnow(),
            )
        ]
        records = mapper.to_execution_records(messages)

        # Step name should be truncated
        assert len(records[0].step_name) <= 50

    def test_error_metadata_handling(self):
        """Test error metadata is captured."""
        mapper = ClaudeMapper()
        messages = [
            Message(
                message_id="msg-1",
                role=MessageRole.ASSISTANT,
                content="Error occurred",
                timestamp=datetime.utcnow(),
                metadata={"error": "Connection failed"},
            )
        ]
        records = mapper.to_execution_records(messages)

        assert records[0].status == "failed"
        assert records[0].error == "Connection failed"


class TestToolCallToApprovalRequest:
    """Test tool call to approval request conversion."""

    @pytest.fixture
    def sample_tool_call(self) -> ToolCall:
        """Create sample tool call."""
        return ToolCall(
            call_id="tc-123",
            tool_name="deploy",
            arguments={"environment": "production"},
            status=ToolCallStatus.PENDING,
            started_at=datetime(2025, 1, 1, 12, 0, 0),
        )

    def test_basic_conversion(self, sample_tool_call):
        """Test basic tool call to approval conversion."""
        mapper = ClaudeMapper()
        approval = mapper.tool_call_to_approval_request(
            sample_tool_call, checkpoint_id="cp-456"
        )

        assert isinstance(approval, ApprovalRequest)
        assert approval.request_id == "tc-123"
        assert approval.checkpoint_id == "cp-456"

    def test_action_format(self, sample_tool_call):
        """Test action format."""
        mapper = ClaudeMapper()
        approval = mapper.tool_call_to_approval_request(
            sample_tool_call, checkpoint_id="cp-456"
        )

        assert approval.action == "execute_deploy"

    def test_description_includes_tool_info(self, sample_tool_call):
        """Test description includes tool information."""
        mapper = ClaudeMapper()
        approval = mapper.tool_call_to_approval_request(
            sample_tool_call, checkpoint_id="cp-456"
        )

        assert "Tool: deploy" in approval.description
        assert "environment" in approval.description

    def test_status_mapping_pending(self, sample_tool_call):
        """Test PENDING status mapping."""
        mapper = ClaudeMapper()
        approval = mapper.tool_call_to_approval_request(
            sample_tool_call, checkpoint_id="cp-456"
        )
        assert approval.status == ApprovalStatus.PENDING

    def test_status_mapping_completed(self, sample_tool_call):
        """Test COMPLETED status mapping."""
        sample_tool_call.status = ToolCallStatus.COMPLETED
        sample_tool_call.completed_at = datetime(2025, 1, 1, 13, 0, 0)

        mapper = ClaudeMapper()
        approval = mapper.tool_call_to_approval_request(
            sample_tool_call, checkpoint_id="cp-456"
        )

        assert approval.status == ApprovalStatus.APPROVED

    def test_status_mapping_failed(self, sample_tool_call):
        """Test FAILED status mapping."""
        sample_tool_call.status = ToolCallStatus.FAILED
        sample_tool_call.result = "Connection timeout"

        mapper = ClaudeMapper()
        approval = mapper.tool_call_to_approval_request(
            sample_tool_call, checkpoint_id="cp-456"
        )

        assert approval.status == ApprovalStatus.REJECTED
        assert approval.response_message == "Connection timeout"

    def test_batch_conversion(self):
        """Test batch tool call conversion."""
        mapper = ClaudeMapper()
        tool_calls = [
            ToolCall(
                call_id=f"tc-{i}",
                tool_name="action",
                arguments={},
                status=ToolCallStatus.PENDING,
            )
            for i in range(3)
        ]
        approvals = mapper.tool_calls_to_approval_requests(tool_calls, "cp-123")

        assert len(approvals) == 3
        assert all(isinstance(a, ApprovalRequest) for a in approvals)


class TestSessionMetadataToWorkflow:
    """Test session metadata to workflow conversion."""

    def test_basic_conversion(self):
        """Test basic session metadata conversion."""
        mapper = ClaudeMapper()
        result = mapper.session_metadata_to_workflow(
            session_id="sess-123",
            session_metadata={
                "model": "gpt-4",
                "temperature": 0.7,
            },
        )

        assert result["source"] == "claude_sdk"
        assert result["session_id"] == "sess-123"
        assert result["llm_model"] == "gpt-4"
        assert result["llm_temperature"] == 0.7

    def test_field_mappings(self):
        """Test known field mappings."""
        mapper = ClaudeMapper()
        result = mapper.session_metadata_to_workflow(
            session_id="sess-123",
            session_metadata={
                "max_tokens": 1000,
                "system_prompt": "Be helpful",
                "tools": ["search", "code"],
            },
        )

        assert result["llm_max_tokens"] == 1000
        assert result["agent_instructions"] == "Be helpful"
        assert result["available_tools"] == ["search", "code"]

    def test_datetime_conversion(self):
        """Test datetime values are converted."""
        mapper = ClaudeMapper()
        now = datetime(2025, 1, 1, 12, 0, 0)
        result = mapper.session_metadata_to_workflow(
            session_id="sess-123",
            session_metadata={"created_at": now},
        )

        assert result["started_at"] == "2025-01-01T12:00:00"

    def test_unknown_fields_prefixed(self):
        """Test unknown fields get claude_ prefix."""
        mapper = ClaudeMapper()
        result = mapper.session_metadata_to_workflow(
            session_id="sess-123",
            session_metadata={"custom_field": "value"},
        )

        assert result["claude_custom_field"] == "value"


class TestConversationSummary:
    """Test conversation summary generation."""

    @pytest.fixture
    def sample_messages(self) -> List[Message]:
        """Create sample messages for summary."""
        return [
            Message(
                message_id="1",
                role=MessageRole.USER,
                content="Hello",
                timestamp=datetime.utcnow(),
            ),
            Message(
                message_id="2",
                role=MessageRole.ASSISTANT,
                content="Hi there!",
                timestamp=datetime.utcnow(),
            ),
            Message(
                message_id="3",
                role=MessageRole.USER,
                content="Help me code",
                timestamp=datetime.utcnow(),
            ),
            Message(
                message_id="4",
                role=MessageRole.ASSISTANT,
                content="Sure, I'll help!",
                timestamp=datetime.utcnow(),
            ),
        ]

    def test_basic_summary(self, sample_messages):
        """Test basic summary generation."""
        mapper = ClaudeMapper()
        summary = mapper.conversation_summary(sample_messages)

        assert "Claude Conversation Summary" in summary
        assert "Messages:" in summary

    def test_message_counts(self, sample_messages):
        """Test message counts are included."""
        mapper = ClaudeMapper()
        summary = mapper.conversation_summary(sample_messages)

        assert "User: 2" in summary
        assert "Assistant: 2" in summary

    def test_empty_messages(self):
        """Test with empty messages."""
        mapper = ClaudeMapper()
        summary = mapper.conversation_summary([])
        assert "No conversation history" in summary

    def test_max_length_truncation(self, sample_messages):
        """Test summary is truncated to max length."""
        mapper = ClaudeMapper()
        summary = mapper.conversation_summary(sample_messages, max_length=100)
        assert len(summary) <= 100


class TestExtractToolResults:
    """Test tool results extraction."""

    def test_basic_extraction(self):
        """Test basic tool results extraction."""
        mapper = ClaudeMapper()
        messages = [
            Message(
                message_id="msg-1",
                role=MessageRole.TOOL,
                content='{"result": "success"}',
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
                metadata={"tool_call_id": "tc-123"},
            )
        ]
        results = mapper.extract_tool_results(messages)

        assert "tc-123" in results
        assert results["tc-123"]["content"] == '{"result": "success"}'

    def test_multiple_tool_messages(self):
        """Test extraction from multiple tool messages."""
        mapper = ClaudeMapper()
        messages = [
            Message(
                message_id="msg-1",
                role=MessageRole.TOOL,
                content="Result 1",
                timestamp=datetime.utcnow(),
                metadata={"tool_call_id": "tc-1"},
            ),
            Message(
                message_id="msg-2",
                role=MessageRole.TOOL,
                content="Result 2",
                timestamp=datetime.utcnow(),
                metadata={"tool_call_id": "tc-2"},
            ),
        ]
        results = mapper.extract_tool_results(messages)

        assert len(results) == 2
        assert "tc-1" in results
        assert "tc-2" in results

    def test_non_tool_messages_ignored(self):
        """Test non-tool messages are ignored."""
        mapper = ClaudeMapper()
        messages = [
            Message(
                message_id="msg-1",
                role=MessageRole.USER,
                content="Hello",
                timestamp=datetime.utcnow(),
            ),
            Message(
                message_id="msg-2",
                role=MessageRole.ASSISTANT,
                content="Hi",
                timestamp=datetime.utcnow(),
            ),
        ]
        results = mapper.extract_tool_results(messages)
        assert results == {}

    def test_missing_tool_call_id(self):
        """Test messages without tool_call_id are skipped."""
        mapper = ClaudeMapper()
        messages = [
            Message(
                message_id="msg-1",
                role=MessageRole.TOOL,
                content="Result",
                timestamp=datetime.utcnow(),
                metadata={},  # No tool_call_id
            )
        ]
        results = mapper.extract_tool_results(messages)
        assert results == {}


class TestStrictMode:
    """Test strict mode behavior."""

    def test_strict_mode_flag(self):
        """Test strict mode is set correctly."""
        mapper = ClaudeMapper(strict=True)
        assert mapper.strict is True

    def test_non_strict_mode_continues(self):
        """Test non-strict mode continues on normal data."""
        mapper = ClaudeMapper(strict=False)
        result = mapper.to_maf_checkpoint({"claude_key": "value"})
        assert "key" in result
