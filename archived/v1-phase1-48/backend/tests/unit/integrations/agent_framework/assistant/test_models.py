"""
Unit tests for Code Interpreter data models.

Sprint 37: Phase 8 - Code Interpreter Integration
"""

import pytest
from unittest.mock import MagicMock

from src.integrations.agent_framework.assistant.models import (
    ExecutionStatus,
    CodeExecutionResult,
    AssistantConfig,
    ThreadMessage,
    AssistantInfo,
    FileInfo,
)


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_status_values(self):
        """Test that all status values are correct."""
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.ERROR.value == "error"
        assert ExecutionStatus.TIMEOUT.value == "timeout"
        assert ExecutionStatus.CANCELLED.value == "cancelled"

    def test_status_is_string_enum(self):
        """Test that status values can be used as strings."""
        assert str(ExecutionStatus.SUCCESS) == "ExecutionStatus.SUCCESS"
        assert ExecutionStatus.SUCCESS == "success"


class TestCodeExecutionResult:
    """Tests for CodeExecutionResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful execution result."""
        result = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="Hello, World!",
            execution_time=1.5,
        )
        assert result.is_success is True
        assert result.output == "Hello, World!"
        assert result.execution_time == 1.5
        assert result.files == []
        assert result.code_outputs == []

    def test_create_error_result(self):
        """Test creating an error execution result."""
        result = CodeExecutionResult(
            status=ExecutionStatus.ERROR,
            output="SyntaxError: invalid syntax",
            execution_time=0.5,
        )
        assert result.is_success is False
        assert "SyntaxError" in result.output

    def test_create_timeout_result(self):
        """Test creating a timeout execution result."""
        result = CodeExecutionResult(
            status=ExecutionStatus.TIMEOUT,
            output="Execution timed out",
            execution_time=60.0,
        )
        assert result.is_success is False
        assert result.status == ExecutionStatus.TIMEOUT

    def test_result_with_files(self):
        """Test result with generated files."""
        result = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="Plot generated",
            execution_time=2.0,
            files=[
                {"type": "image", "file_id": "file-123"},
                {"type": "file", "file_id": "file-456"},
            ],
        )
        assert len(result.files) == 2
        assert result.files[0]["type"] == "image"

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="5050",
            execution_time=1.0,
        )
        data = result.to_dict()
        assert data["status"] == "success"
        assert data["output"] == "5050"
        assert data["execution_time"] == 1.0
        assert data["files"] == []
        assert data["code_outputs"] == []


class TestAssistantConfig:
    """Tests for AssistantConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AssistantConfig()
        assert config.name == "IPA-CodeInterpreter"
        assert "Python code execution" in config.instructions
        assert config.model is None
        assert config.timeout == 60
        assert config.max_retries == 3

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AssistantConfig(
            name="Custom-Interpreter",
            instructions="Custom instructions",
            model="gpt-4o",
            timeout=120,
            max_retries=5,
        )
        assert config.name == "Custom-Interpreter"
        assert config.instructions == "Custom instructions"
        assert config.model == "gpt-4o"
        assert config.timeout == 120
        assert config.max_retries == 5


class TestThreadMessage:
    """Tests for ThreadMessage dataclass."""

    def test_create_user_message(self):
        """Test creating a user message."""
        message = ThreadMessage(
            role="user",
            content="Execute print('hello')",
        )
        assert message.role == "user"
        assert message.content == "Execute print('hello')"
        assert message.file_ids == []

    def test_create_assistant_message_with_files(self):
        """Test creating an assistant message with file attachments."""
        message = ThreadMessage(
            role="assistant",
            content="Here's the plot",
            file_ids=["file-123", "file-456"],
        )
        assert message.role == "assistant"
        assert len(message.file_ids) == 2


class TestAssistantInfo:
    """Tests for AssistantInfo dataclass."""

    def test_create_assistant_info(self):
        """Test creating assistant info."""
        info = AssistantInfo(
            id="asst_abc123",
            name="Test Assistant",
            model="gpt-4o",
            tools=["code_interpreter"],
            created_at=1702920000,
        )
        assert info.id == "asst_abc123"
        assert info.name == "Test Assistant"
        assert info.model == "gpt-4o"
        assert "code_interpreter" in info.tools
        assert info.created_at == 1702920000

    def test_from_api_response(self):
        """Test creating from API response."""
        mock_response = MagicMock()
        mock_response.id = "asst_xyz789"
        mock_response.name = "API Assistant"
        mock_response.model = "gpt-4o"
        mock_response.tools = [MagicMock(type="code_interpreter")]
        mock_response.created_at = 1702920000

        info = AssistantInfo.from_api_response(mock_response)
        assert info.id == "asst_xyz789"
        assert info.name == "API Assistant"
        assert info.tools == ["code_interpreter"]

    def test_from_api_response_no_name(self):
        """Test creating from API response with no name."""
        mock_response = MagicMock()
        mock_response.id = "asst_123"
        mock_response.name = None
        mock_response.model = "gpt-4o"
        mock_response.tools = []
        mock_response.created_at = 1702920000

        info = AssistantInfo.from_api_response(mock_response)
        assert info.name == ""
        assert info.tools == []


class TestFileInfo:
    """Tests for FileInfo dataclass."""

    def test_create_file_info(self):
        """Test creating file info."""
        info = FileInfo(
            id="file-abc123",
            filename="output.png",
            bytes=1024,
            created_at=1702920000,
            purpose="assistants",
        )
        assert info.id == "file-abc123"
        assert info.filename == "output.png"
        assert info.bytes == 1024
        assert info.purpose == "assistants"

    def test_from_api_response(self):
        """Test creating from API response."""
        mock_response = MagicMock()
        mock_response.id = "file-xyz789"
        mock_response.filename = "data.csv"
        mock_response.bytes = 2048
        mock_response.created_at = 1702920000
        mock_response.purpose = "assistants_output"

        info = FileInfo.from_api_response(mock_response)
        assert info.id == "file-xyz789"
        assert info.filename == "data.csv"
        assert info.bytes == 2048
        assert info.purpose == "assistants_output"
