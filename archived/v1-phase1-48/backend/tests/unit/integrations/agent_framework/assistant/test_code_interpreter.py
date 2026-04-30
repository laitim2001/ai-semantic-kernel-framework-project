"""
Unit tests for CodeInterpreterAdapter.

Sprint 37: Phase 8 - Code Interpreter Integration
Sprint 38: Added Responses API Support
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import time

from src.integrations.agent_framework.builders.code_interpreter import (
    CodeInterpreterAdapter,
    CodeInterpreterConfig,
    ExecutionResult,
    APIMode,
)
from src.integrations.agent_framework.assistant.models import (
    CodeExecutionResult,
    ExecutionStatus,
    AssistantInfo,
)


class TestAPIMode:
    """Tests for APIMode enum."""

    def test_responses_mode(self):
        """Test RESPONSES mode value."""
        assert APIMode.RESPONSES.value == "responses"

    def test_assistants_mode(self):
        """Test ASSISTANTS mode value."""
        assert APIMode.ASSISTANTS.value == "assistants"

    def test_auto_mode(self):
        """Test AUTO mode value."""
        assert APIMode.AUTO.value == "auto"

    def test_mode_string_comparison(self):
        """Test string comparison for API modes."""
        assert APIMode.RESPONSES == "responses"
        assert APIMode.ASSISTANTS == "assistants"
        assert APIMode.AUTO == "auto"


class TestCodeInterpreterConfig:
    """Tests for CodeInterpreterConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CodeInterpreterConfig()
        assert config.assistant_name == "IPA-CodeInterpreter"
        assert "Python code execution" in config.instructions
        assert config.timeout == 60
        assert config.max_retries == 3
        assert config.auto_cleanup is True
        # New Responses API fields
        assert config.api_mode == APIMode.AUTO
        assert config.api_version == "2025-03-01-preview"
        assert config.azure_endpoint is None
        assert config.api_key is None
        assert config.deployment is None

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CodeInterpreterConfig(
            assistant_name="Custom-Interpreter",
            instructions="Custom instructions here",
            timeout=120,
            max_retries=5,
            auto_cleanup=False,
        )
        assert config.assistant_name == "Custom-Interpreter"
        assert config.instructions == "Custom instructions here"
        assert config.timeout == 120
        assert config.max_retries == 5
        assert config.auto_cleanup is False

    def test_responses_api_config(self):
        """Test configuration for Responses API mode."""
        config = CodeInterpreterConfig(
            api_mode=APIMode.RESPONSES,
            api_version="2025-03-01-preview",
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key-123",
            deployment="gpt-4",
        )
        assert config.api_mode == APIMode.RESPONSES
        assert config.api_version == "2025-03-01-preview"
        assert config.azure_endpoint == "https://test.openai.azure.com/"
        assert config.api_key == "test-key-123"
        assert config.deployment == "gpt-4"

    def test_assistants_api_config(self):
        """Test configuration for Assistants API mode."""
        config = CodeInterpreterConfig(
            api_mode=APIMode.ASSISTANTS,
            assistant_name="Legacy-Interpreter",
        )
        assert config.api_mode == APIMode.ASSISTANTS
        assert config.assistant_name == "Legacy-Interpreter"


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful execution result."""
        result = ExecutionResult(
            success=True,
            output="Result: 42",
            execution_time=1.5,
        )
        assert result.success is True
        assert result.output == "Result: 42"
        assert result.execution_time == 1.5
        assert result.files == []
        assert result.error is None
        assert result.metadata == {}

    def test_create_error_result(self):
        """Test creating an error execution result."""
        result = ExecutionResult(
            success=False,
            output="Error occurred",
            execution_time=0.5,
            error="SyntaxError: invalid syntax",
        )
        assert result.success is False
        assert result.error == "SyntaxError: invalid syntax"

    def test_result_with_files(self):
        """Test result with generated files."""
        result = ExecutionResult(
            success=True,
            output="Plot generated",
            execution_time=2.0,
            files=[
                {"type": "image", "file_id": "file-123"},
            ],
        )
        assert len(result.files) == 1
        assert result.files[0]["type"] == "image"

    def test_from_code_result(self):
        """Test creating ExecutionResult from CodeExecutionResult."""
        code_result = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="5050",
            execution_time=1.0,
            files=[{"type": "file", "file_id": "file-abc"}],
            code_outputs=["5050"],
        )

        result = ExecutionResult.from_code_result(code_result)
        assert result.success is True
        assert result.output == "5050"
        assert result.execution_time == 1.0
        assert len(result.files) == 1
        assert result.error is None
        assert result.metadata["status"] == "success"
        assert result.metadata["code_outputs"] == ["5050"]

    def test_from_code_result_error(self):
        """Test creating ExecutionResult from error CodeExecutionResult."""
        code_result = CodeExecutionResult(
            status=ExecutionStatus.ERROR,
            output="NameError: name 'x' is not defined",
            execution_time=0.5,
        )

        result = ExecutionResult.from_code_result(code_result)
        assert result.success is False
        assert result.error == "NameError: name 'x' is not defined"

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = ExecutionResult(
            success=True,
            output="Hello",
            execution_time=0.5,
            files=[],
            error=None,
            metadata={"status": "success"},
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["output"] == "Hello"
        assert data["execution_time"] == 0.5
        assert data["files"] == []
        assert data["error"] is None
        assert data["metadata"]["status"] == "success"

    def test_from_responses_api_with_message(self):
        """Test creating ExecutionResult from Responses API with message output."""
        # Mock response with message output
        mock_content = MagicMock()
        mock_content.text = "The result is 42"

        mock_item = MagicMock()
        mock_item.type = "message"
        mock_item.content = [mock_content]

        mock_response = MagicMock()
        mock_response.output = [mock_item]
        mock_response.id = "resp_123"

        result = ExecutionResult.from_responses_api(mock_response, 1.5)

        assert result.success is True
        assert "42" in result.output
        assert result.execution_time == 1.5
        assert result.error is None
        assert result.metadata["api_mode"] == "responses"
        assert result.metadata["response_id"] == "resp_123"

    def test_from_responses_api_with_code_interpreter(self):
        """Test creating ExecutionResult from Responses API with code interpreter output."""
        # Mock code interpreter output with logs
        mock_logs = MagicMock()
        mock_logs.type = "logs"
        mock_logs.logs = "5050\n"

        mock_code_item = MagicMock()
        mock_code_item.type = "code_interpreter_call"
        mock_code_item.id = "call_123"
        mock_code_item.code = "print(sum(range(101)))"
        mock_code_item.outputs = [mock_logs]

        mock_response = MagicMock()
        mock_response.output = [mock_code_item]
        mock_response.id = "resp_456"

        result = ExecutionResult.from_responses_api(mock_response, 2.0)

        assert result.success is True
        assert "5050" in result.output
        assert result.execution_time == 2.0
        assert result.metadata["api_mode"] == "responses"
        assert len(result.metadata["code_outputs"]) == 1
        assert result.metadata["code_outputs"][0]["id"] == "call_123"

    def test_from_responses_api_with_image_output(self):
        """Test creating ExecutionResult from Responses API with image output."""
        # Mock code interpreter output with image
        mock_image = MagicMock()
        mock_image.type = "image"
        mock_image.file_id = "file-abc123"

        mock_code_item = MagicMock()
        mock_code_item.type = "code_interpreter_call"
        mock_code_item.id = "call_789"
        mock_code_item.code = "plt.savefig('chart.png')"
        mock_code_item.outputs = [mock_image]

        mock_response = MagicMock()
        mock_response.output = [mock_code_item]
        mock_response.id = "resp_789"

        result = ExecutionResult.from_responses_api(mock_response, 3.0)

        assert result.success is True
        assert len(result.files) == 1
        assert result.files[0]["type"] == "image"
        assert result.files[0]["file_id"] == "file-abc123"

    def test_from_responses_api_with_output_text(self):
        """Test creating ExecutionResult from Responses API with output_text attribute."""
        mock_response = MagicMock()
        mock_response.output = []  # No structured output
        mock_response.output_text = "Simple text response"
        mock_response.id = "resp_text"

        result = ExecutionResult.from_responses_api(mock_response, 0.5)

        assert result.success is True
        assert result.output == "Simple text response"

    def test_from_responses_api_error_handling(self):
        """Test error handling in from_responses_api."""
        # Mock response that raises exception during parsing
        mock_response = MagicMock()
        mock_response.output = None  # Will cause AttributeError when iterating
        mock_response.id = "resp_error"
        # Make hasattr return True but iteration fails
        type(mock_response).output = PropertyMock(side_effect=Exception("Parse error"))

        result = ExecutionResult.from_responses_api(mock_response, 1.0)

        assert result.success is False
        assert result.error is not None
        assert "Parse error" in result.error


class TestCodeInterpreterAdapter:
    """Tests for CodeInterpreterAdapter class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        with patch('src.integrations.agent_framework.builders.code_interpreter.AssistantManagerService'):
            adapter = CodeInterpreterAdapter()
            assert adapter.config.assistant_name == "IPA-CodeInterpreter"
            assert adapter.is_initialized is False
            assert adapter.assistant_id is None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = CodeInterpreterConfig(
            assistant_name="Test-Interpreter",
            timeout=120,
        )
        with patch('src.integrations.agent_framework.builders.code_interpreter.AssistantManagerService'):
            adapter = CodeInterpreterAdapter(config=config)
            assert adapter.config.assistant_name == "Test-Interpreter"
            assert adapter.config.timeout == 120

    def test_init_with_manager(self):
        """Test initialization with provided manager."""
        mock_manager = MagicMock()
        adapter = CodeInterpreterAdapter(manager=mock_manager)
        assert adapter._manager is mock_manager

    def test_execute_initializes_on_first_call(self):
        """Test that execute triggers lazy initialization."""
        mock_manager = MagicMock()
        mock_assistant_info = MagicMock()
        mock_assistant_info.id = "asst_test123"
        mock_manager.create_assistant.return_value = mock_assistant_info
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="42",
            execution_time=1.0,
        )

        adapter = CodeInterpreterAdapter(manager=mock_manager)
        assert adapter.is_initialized is False

        result = adapter.execute("print(42)")

        assert adapter.is_initialized is True
        assert adapter.assistant_id == "asst_test123"
        mock_manager.create_assistant.assert_called_once()
        mock_manager.execute_code.assert_called_once()
        assert result.success is True
        assert "42" in result.output

    def test_execute_with_timeout(self):
        """Test execute with custom timeout."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="Result",
            execution_time=2.0,
        )

        adapter = CodeInterpreterAdapter(manager=mock_manager)
        adapter.execute("code", timeout=90)

        mock_manager.execute_code.assert_called_with(
            assistant_id="asst_123",
            code="code",
            timeout=90,
        )

    def test_analyze_task(self):
        """Test analyze_task method."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.run_task.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="3628800",
            execution_time=3.0,
        )

        adapter = CodeInterpreterAdapter(manager=mock_manager)
        result = adapter.analyze_task("Calculate factorial of 10")

        assert result.success is True
        assert "3628800" in result.output
        mock_manager.run_task.assert_called_once()

    def test_analyze_task_with_context(self):
        """Test analyze_task with context."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.run_task.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="15",
            execution_time=1.0,
        )

        adapter = CodeInterpreterAdapter(manager=mock_manager)
        context = {"data": [1, 2, 3, 4, 5]}
        adapter.analyze_task("Calculate sum", context=context)

        mock_manager.run_task.assert_called_with(
            assistant_id="asst_123",
            task="Calculate sum",
            context=context,
            timeout=60,
        )

    def test_cleanup(self):
        """Test cleanup method."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="",
            execution_time=0.5,
        )
        mock_manager.delete_assistant.return_value = True

        adapter = CodeInterpreterAdapter(manager=mock_manager)
        adapter.execute("print(1)")  # Initialize

        assert adapter.is_initialized is True

        success = adapter.cleanup()

        assert success is True
        assert adapter.is_initialized is False
        assert adapter.assistant_id is None
        mock_manager.delete_assistant.assert_called_with("asst_123")

    def test_cleanup_not_initialized(self):
        """Test cleanup when not initialized."""
        mock_manager = MagicMock()
        adapter = CodeInterpreterAdapter(manager=mock_manager)

        success = adapter.cleanup()

        assert success is True
        mock_manager.delete_assistant.assert_not_called()

    def test_context_manager(self):
        """Test using adapter as context manager."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="Done",
            execution_time=1.0,
        )
        mock_manager.delete_assistant.return_value = True

        config = CodeInterpreterConfig(auto_cleanup=True)

        with CodeInterpreterAdapter(config=config, manager=mock_manager) as adapter:
            adapter.execute("print('hello')")
            assert adapter.is_initialized is True

        mock_manager.delete_assistant.assert_called_once()

    def test_context_manager_no_auto_cleanup(self):
        """Test context manager without auto cleanup."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="Done",
            execution_time=1.0,
        )

        config = CodeInterpreterConfig(auto_cleanup=False)

        with CodeInterpreterAdapter(config=config, manager=mock_manager) as adapter:
            adapter.execute("print('hello')")

        mock_manager.delete_assistant.assert_not_called()

    def test_properties(self):
        """Test adapter properties."""
        mock_manager = MagicMock()
        mock_assistant_info = MagicMock()
        mock_assistant_info.id = "asst_props"
        mock_manager.create_assistant.return_value = mock_assistant_info
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="",
            execution_time=0.5,
        )

        config = CodeInterpreterConfig(assistant_name="Props-Test")
        adapter = CodeInterpreterAdapter(config=config, manager=mock_manager)

        # Before initialization
        assert adapter.is_initialized is False
        assert adapter.assistant_id is None
        assert adapter.assistant_info is None
        assert adapter.config.assistant_name == "Props-Test"

        # After initialization
        adapter.execute("1+1")
        assert adapter.is_initialized is True
        assert adapter.assistant_id == "asst_props"
        assert adapter.assistant_info is mock_assistant_info


class TestCodeInterpreterAdapterErrorHandling:
    """Tests for error handling in CodeInterpreterAdapter."""

    def test_execute_handles_error_result(self):
        """Test that execute handles error results correctly."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.ERROR,
            output="SyntaxError: invalid syntax",
            execution_time=0.5,
        )

        adapter = CodeInterpreterAdapter(manager=mock_manager)
        result = adapter.execute("print(")

        assert result.success is False
        assert "SyntaxError" in result.output
        assert result.error is not None

    def test_execute_handles_timeout_result(self):
        """Test that execute handles timeout results correctly."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.TIMEOUT,
            output="Execution timed out after 60 seconds",
            execution_time=60.0,
        )

        adapter = CodeInterpreterAdapter(manager=mock_manager)
        result = adapter.execute("while True: pass")

        assert result.success is False
        assert "timed out" in result.output.lower()

    def test_cleanup_handles_exception(self):
        """Test that cleanup handles exceptions gracefully."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="",
            execution_time=0.5,
        )
        mock_manager.delete_assistant.side_effect = Exception("Network error")

        adapter = CodeInterpreterAdapter(manager=mock_manager)
        adapter.execute("1")  # Initialize

        success = adapter.cleanup()

        assert success is False


class TestCodeInterpreterAdapterResponsesAPI:
    """Tests for Responses API support in CodeInterpreterAdapter."""

    def test_init_with_responses_api_config(self):
        """Test initialization with Responses API configuration."""
        config = CodeInterpreterConfig(
            api_mode=APIMode.RESPONSES,
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="gpt-4",
        )

        adapter = CodeInterpreterAdapter(config=config)

        assert adapter.config.api_mode == APIMode.RESPONSES
        assert adapter.config.azure_endpoint == "https://test.openai.azure.com/"
        assert adapter.config.deployment == "gpt-4"
        assert adapter.is_initialized is False

    def test_active_api_mode_property(self):
        """Test active_api_mode property before and after initialization."""
        mock_manager = MagicMock()
        mock_manager.create_assistant.return_value = MagicMock(id="asst_123")
        mock_manager.execute_code.return_value = CodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="42",
            execution_time=1.0,
        )

        config = CodeInterpreterConfig(api_mode=APIMode.ASSISTANTS)
        adapter = CodeInterpreterAdapter(config=config, manager=mock_manager)

        # Before initialization
        assert adapter.active_api_mode is None

        # After initialization
        adapter.execute("print(42)")
        assert adapter.active_api_mode == APIMode.ASSISTANTS

    @patch('openai.AzureOpenAI')
    @patch('src.core.config.get_settings')
    def test_execute_with_responses_api(self, mock_settings, mock_azure_openai):
        """Test execute method using Responses API."""
        # Setup mock settings
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
        mock_settings.return_value.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4"

        # Setup mock OpenAI client
        mock_client = MagicMock()
        mock_azure_openai.return_value = mock_client

        # Setup mock response
        mock_content = MagicMock()
        mock_content.text = "Result: 4"

        mock_item = MagicMock()
        mock_item.type = "message"
        mock_item.content = [mock_content]

        mock_response = MagicMock()
        mock_response.output = [mock_item]
        mock_response.id = "resp_test"

        mock_client.responses.create.return_value = mock_response

        # Create adapter and execute
        config = CodeInterpreterConfig(
            api_mode=APIMode.RESPONSES,
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="gpt-4",
        )
        adapter = CodeInterpreterAdapter(config=config)
        result = adapter.execute("print(2+2)")

        assert result.success is True
        assert "4" in result.output
        assert result.metadata["api_mode"] == "responses"
        mock_client.responses.create.assert_called_once()

    @patch('openai.AzureOpenAI')
    @patch('src.core.config.get_settings')
    def test_execute_responses_api_with_code_interpreter_tool(
        self, mock_settings, mock_azure_openai
    ):
        """Test execute method using Responses API with code_interpreter tool."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
        mock_settings.return_value.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4"

        mock_client = MagicMock()
        mock_azure_openai.return_value = mock_client

        mock_logs = MagicMock()
        mock_logs.type = "logs"
        mock_logs.logs = "5050"

        mock_code_item = MagicMock()
        mock_code_item.type = "code_interpreter_call"
        mock_code_item.id = "call_abc"
        mock_code_item.code = "print(sum(range(101)))"
        mock_code_item.outputs = [mock_logs]

        mock_response = MagicMock()
        mock_response.output = [mock_code_item]
        mock_response.id = "resp_code"

        mock_client.responses.create.return_value = mock_response

        config = CodeInterpreterConfig(
            api_mode=APIMode.RESPONSES,
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="gpt-4",
        )
        adapter = CodeInterpreterAdapter(config=config)
        result = adapter.execute("print(sum(range(101)))")

        assert result.success is True
        assert "5050" in result.output

        # Verify code_interpreter tool was used
        call_kwargs = mock_client.responses.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"][0]["type"] == "code_interpreter"

    @patch('openai.AzureOpenAI')
    @patch('src.core.config.get_settings')
    def test_execute_simple_method(self, mock_settings, mock_azure_openai):
        """Test execute_simple method (no code_interpreter tool)."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
        mock_settings.return_value.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4"

        mock_client = MagicMock()
        mock_azure_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.output_text = "1200"
        mock_response.id = "resp_simple"

        mock_client.responses.create.return_value = mock_response

        config = CodeInterpreterConfig(
            api_mode=APIMode.RESPONSES,
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="gpt-4",
        )
        adapter = CodeInterpreterAdapter(config=config)
        result = adapter.execute_simple("What is 25 * 48?")

        assert result.success is True
        assert "1200" in result.output
        assert result.metadata["method"] == "simple"

        # Verify no tools were passed
        call_kwargs = mock_client.responses.create.call_args[1]
        assert "tools" not in call_kwargs or call_kwargs.get("tools") is None

    @patch('openai.AzureOpenAI')
    @patch('src.core.config.get_settings')
    def test_analyze_task_with_responses_api(self, mock_settings, mock_azure_openai):
        """Test analyze_task method using Responses API."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
        mock_settings.return_value.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4"

        mock_client = MagicMock()
        mock_azure_openai.return_value = mock_client

        mock_content = MagicMock()
        mock_content.text = "Mean: 3.0, Std: 1.41"

        mock_item = MagicMock()
        mock_item.type = "message"
        mock_item.content = [mock_content]

        mock_response = MagicMock()
        mock_response.output = [mock_item]
        mock_response.id = "resp_analyze"

        mock_client.responses.create.return_value = mock_response

        config = CodeInterpreterConfig(
            api_mode=APIMode.RESPONSES,
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="gpt-4",
        )
        adapter = CodeInterpreterAdapter(config=config)
        result = adapter.analyze_task(
            "Calculate mean and std of data",
            context={"data": [1, 2, 3, 4, 5]}
        )

        assert result.success is True
        assert "Mean" in result.output or "3.0" in result.output

    @patch('openai.AzureOpenAI')
    @patch('src.core.config.get_settings')
    def test_responses_api_error_handling(self, mock_settings, mock_azure_openai):
        """Test error handling in Responses API execution."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
        mock_settings.return_value.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4"

        mock_client = MagicMock()
        mock_azure_openai.return_value = mock_client
        mock_client.responses.create.side_effect = Exception("API rate limit exceeded")

        config = CodeInterpreterConfig(
            api_mode=APIMode.RESPONSES,
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment="gpt-4",
        )
        adapter = CodeInterpreterAdapter(config=config)
        result = adapter.execute("print(1)")

        assert result.success is False
        assert result.error is not None
        assert "rate limit" in result.error.lower()
        assert result.metadata["error_type"] == "Exception"

    def test_cleanup_responses_api(self):
        """Test cleanup for Responses API (should be no-op)."""
        config = CodeInterpreterConfig(api_mode=APIMode.RESPONSES)
        adapter = CodeInterpreterAdapter(config=config)

        # Force initialization state
        adapter._initialized = True
        adapter._active_api_mode = APIMode.RESPONSES

        success = adapter.cleanup()

        assert success is True
        assert adapter.is_initialized is False

    def test_determine_api_mode_explicit_responses(self):
        """Test _determine_api_mode with explicit RESPONSES mode."""
        config = CodeInterpreterConfig(api_mode=APIMode.RESPONSES)
        adapter = CodeInterpreterAdapter(config=config)

        mode = adapter._determine_api_mode()

        assert mode == APIMode.RESPONSES

    def test_determine_api_mode_explicit_assistants(self):
        """Test _determine_api_mode with explicit ASSISTANTS mode."""
        config = CodeInterpreterConfig(api_mode=APIMode.ASSISTANTS)
        adapter = CodeInterpreterAdapter(config=config)

        mode = adapter._determine_api_mode()

        assert mode == APIMode.ASSISTANTS

    @patch('openai.AzureOpenAI')
    @patch('src.core.config.get_settings')
    def test_determine_api_mode_auto_with_responses_available(
        self, mock_settings, mock_azure_openai
    ):
        """Test _determine_api_mode with AUTO when Responses API is available."""
        mock_settings.return_value.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com/"
        mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"

        mock_client = MagicMock()
        mock_client.responses = MagicMock()  # Has responses attribute
        mock_azure_openai.return_value = mock_client

        config = CodeInterpreterConfig(
            api_mode=APIMode.AUTO,
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        adapter = CodeInterpreterAdapter(config=config)

        mode = adapter._determine_api_mode()

        assert mode == APIMode.RESPONSES

    def test_determine_api_mode_auto_fallback_to_assistants(self):
        """Test _determine_api_mode with AUTO falls back to Assistants when Responses unavailable."""
        config = CodeInterpreterConfig(
            api_mode=APIMode.AUTO,
            # No azure_endpoint or api_key - will fail to create client
        )
        adapter = CodeInterpreterAdapter(config=config)

        with patch.object(adapter, '_get_openai_client', side_effect=Exception("No config")):
            mode = adapter._determine_api_mode()

        assert mode == APIMode.ASSISTANTS

    @patch('openai.AzureOpenAI')
    @patch('src.core.config.get_settings')
    def test_get_deployment_from_config(self, mock_settings, mock_azure_openai):
        """Test _get_deployment returns config value first."""
        mock_settings.return_value.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4-default"

        config = CodeInterpreterConfig(deployment="gpt-4-custom")
        adapter = CodeInterpreterAdapter(config=config)

        deployment = adapter._get_deployment()

        assert deployment == "gpt-4-custom"

    @patch('src.core.config.get_settings')
    def test_get_deployment_from_settings(self, mock_settings):
        """Test _get_deployment falls back to settings."""
        mock_settings.return_value.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4-from-settings"

        config = CodeInterpreterConfig(deployment=None)
        adapter = CodeInterpreterAdapter(config=config)

        deployment = adapter._get_deployment()

        assert deployment == "gpt-4-from-settings"

    def test_get_deployment_default(self):
        """Test _get_deployment returns default when no config or settings."""
        config = CodeInterpreterConfig(deployment=None)
        adapter = CodeInterpreterAdapter(config=config)

        with patch(
            'src.core.config.get_settings',
            side_effect=Exception("No settings")
        ):
            deployment = adapter._get_deployment()

        assert deployment == "gpt-4"  # Default value
