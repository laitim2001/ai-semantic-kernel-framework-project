# =============================================================================
# IPA Platform - Tool Rendering Handler Tests
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-2: Backend Tool Rendering Tests
#
# Comprehensive unit tests for ToolRenderingHandler, ensuring proper result
# type detection, formatting, and AG-UI event generation.
# =============================================================================

import json
import uuid
from dataclasses import asdict
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.ag_ui.features.tool_rendering import (
    FormattedResult,
    ResultType,
    ToolCall,
    ToolExecutionStatus,
    ToolRenderingConfig,
    ToolRenderingHandler,
    create_tool_rendering_handler,
)
from src.integrations.ag_ui.events import AGUIEventType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_executor():
    """Create a mock UnifiedToolExecutor."""
    executor = MagicMock()
    executor.execute = AsyncMock()
    return executor


@pytest.fixture
def mock_execution_result():
    """Create a mock ToolExecutionResult factory."""
    def _create(
        success: bool = True,
        content: Any = "test result",
        error: Optional[str] = None,
        tool_name: str = "TestTool",
        duration_ms: int = 100,
    ):
        result = MagicMock()
        result.success = success
        result.content = content
        result.error = error
        result.tool_name = tool_name
        result.duration_ms = duration_ms
        return result
    return _create


@pytest.fixture
def tool_rendering_handler(mock_executor):
    """Create ToolRenderingHandler instance."""
    return ToolRenderingHandler(
        unified_executor=mock_executor,
        config=ToolRenderingConfig(),
    )


@pytest.fixture
def sample_tool_call():
    """Create a sample ToolCall."""
    return ToolCall(
        id="tc-test-123",
        name="Read",
        arguments={"file_path": "/test/file.py"},
    )


# =============================================================================
# Test ResultType Enum
# =============================================================================


class TestResultType:
    """Tests for ResultType enum."""

    def test_all_types_exist(self):
        """Test all result types are defined."""
        assert ResultType.TEXT == "text"
        assert ResultType.JSON == "json"
        assert ResultType.TABLE == "table"
        assert ResultType.IMAGE == "image"
        assert ResultType.CODE == "code"
        assert ResultType.ERROR == "error"
        assert ResultType.UNKNOWN == "unknown"

    def test_result_type_is_string(self):
        """Test ResultType values are strings."""
        for result_type in ResultType:
            assert isinstance(result_type.value, str)

    def test_result_type_count(self):
        """Test correct number of result types."""
        assert len(ResultType) == 7


# =============================================================================
# Test ToolExecutionStatus Enum
# =============================================================================


class TestToolExecutionStatus:
    """Tests for ToolExecutionStatus enum."""

    def test_all_statuses_exist(self):
        """Test all statuses are defined."""
        assert ToolExecutionStatus.PENDING == "pending"
        assert ToolExecutionStatus.RUNNING == "running"
        assert ToolExecutionStatus.SUCCESS == "success"
        assert ToolExecutionStatus.ERROR == "error"
        assert ToolExecutionStatus.CANCELLED == "cancelled"

    def test_status_count(self):
        """Test correct number of statuses."""
        assert len(ToolExecutionStatus) == 5


# =============================================================================
# Test ToolCall Dataclass
# =============================================================================


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_create_minimal(self):
        """Test creating ToolCall with minimal args."""
        call = ToolCall(id="tc-1", name="Read")
        assert call.id == "tc-1"
        assert call.name == "Read"
        assert call.arguments == {}
        assert call.status == ToolExecutionStatus.PENDING
        assert call.result is None
        assert call.error is None
        assert call.result_type == ResultType.UNKNOWN

    def test_create_full(self):
        """Test creating ToolCall with all args."""
        call = ToolCall(
            id="tc-2",
            name="Edit",
            arguments={"file": "test.py", "content": "new"},
            status=ToolExecutionStatus.SUCCESS,
            result={"edited": True},
            error=None,
            result_type=ResultType.JSON,
            metadata={"source": "test"},
        )
        assert call.id == "tc-2"
        assert call.arguments == {"file": "test.py", "content": "new"}
        assert call.status == ToolExecutionStatus.SUCCESS
        assert call.result_type == ResultType.JSON

    def test_to_dict(self):
        """Test ToolCall.to_dict() method."""
        call = ToolCall(
            id="tc-3",
            name="Bash",
            arguments={"command": "ls"},
            status=ToolExecutionStatus.RUNNING,
        )
        data = call.to_dict()
        assert data["id"] == "tc-3"
        assert data["name"] == "Bash"
        assert data["arguments"] == {"command": "ls"}
        assert data["status"] == "running"
        assert data["result_type"] == "unknown"

    def test_from_dict(self):
        """Test ToolCall.from_dict() method."""
        data = {
            "id": "tc-4",
            "name": "Grep",
            "arguments": {"pattern": "def "},
            "status": "success",
            "result": ["line1", "line2"],
            "result_type": "table",
        }
        call = ToolCall.from_dict(data)
        assert call.id == "tc-4"
        assert call.name == "Grep"
        assert call.status == ToolExecutionStatus.SUCCESS
        assert call.result_type == ResultType.TABLE

    def test_from_dict_defaults(self):
        """Test ToolCall.from_dict() with minimal data."""
        data = {"name": "Read"}
        call = ToolCall.from_dict(data)
        assert call.name == "Read"
        assert call.status == ToolExecutionStatus.PENDING
        assert call.id.startswith("tc-")


# =============================================================================
# Test FormattedResult Dataclass
# =============================================================================


class TestFormattedResult:
    """Tests for FormattedResult dataclass."""

    def test_create_minimal(self):
        """Test creating FormattedResult with minimal args."""
        result = FormattedResult(data="test", result_type=ResultType.TEXT)
        assert result.data == "test"
        assert result.result_type == ResultType.TEXT
        assert result.formatted is True
        assert result.display_hint is None
        assert result.metadata == {}

    def test_create_full(self):
        """Test creating FormattedResult with all args."""
        result = FormattedResult(
            data={"key": "value"},
            result_type=ResultType.JSON,
            formatted=True,
            display_hint="json-tree",
            metadata={"keys": ["key"]},
        )
        assert result.result_type == ResultType.JSON
        assert result.display_hint == "json-tree"

    def test_to_dict(self):
        """Test FormattedResult.to_dict() method."""
        result = FormattedResult(
            data="code",
            result_type=ResultType.CODE,
            display_hint="code-block",
        )
        data = result.to_dict()
        assert data["data"] == "code"
        assert data["result_type"] == "code"
        assert data["display_hint"] == "code-block"


# =============================================================================
# Test ToolRenderingConfig Dataclass
# =============================================================================


class TestToolRenderingConfig:
    """Tests for ToolRenderingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ToolRenderingConfig()
        assert config.max_text_length == 10000
        assert config.max_json_depth == 10
        assert config.max_table_rows == 100
        assert config.enable_syntax_highlighting is True
        assert config.image_max_size_kb == 5120

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ToolRenderingConfig(
            max_text_length=5000,
            max_table_rows=50,
            enable_syntax_highlighting=False,
        )
        assert config.max_text_length == 5000
        assert config.max_table_rows == 50
        assert config.enable_syntax_highlighting is False


# =============================================================================
# Test ToolRenderingHandler - Type Detection
# =============================================================================


class TestToolRenderingHandlerTypeDetection:
    """Tests for result type detection."""

    def test_detect_none_as_text(self, tool_rendering_handler):
        """Test None result is detected as text."""
        result_type = tool_rendering_handler.detect_result_type(None)
        assert result_type == ResultType.TEXT

    def test_detect_error_dict(self, tool_rendering_handler):
        """Test error dict is detected."""
        result = {"error": "Something went wrong"}
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.ERROR

    def test_detect_image_url(self, tool_rendering_handler):
        """Test image URL is detected."""
        result = {"image_url": "https://example.com/image.png"}
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.IMAGE

    def test_detect_image_data(self, tool_rendering_handler):
        """Test image data is detected."""
        result = {"image_data": "base64..."}
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.IMAGE

    def test_detect_screenshot(self, tool_rendering_handler):
        """Test screenshot is detected as image."""
        result = {"screenshot": "data:image/png;base64,..."}
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.IMAGE

    def test_detect_visualization(self, tool_rendering_handler):
        """Test visualization is detected as image."""
        result = {"visualization": "data:image/png;base64,..."}
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.IMAGE

    def test_detect_table_with_columns_data(self, tool_rendering_handler):
        """Test table with columns and data."""
        result = {
            "columns": ["name", "value"],
            "data": [{"name": "a", "value": 1}],
        }
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.TABLE

    def test_detect_table_with_rows(self, tool_rendering_handler):
        """Test table with rows."""
        result = {"rows": [{"id": 1}, {"id": 2}]}
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.TABLE

    def test_detect_table_list_of_dicts(self, tool_rendering_handler):
        """Test list of dicts is detected as table."""
        result = [{"name": "a"}, {"name": "b"}]
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.TABLE

    def test_detect_code_dict(self, tool_rendering_handler):
        """Test code dict is detected."""
        result = {"code": "def foo(): pass", "language": "python"}
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.CODE

    def test_detect_code_from_read_tool(self, tool_rendering_handler):
        """Test code detection from Read tool."""
        result = "def hello():\n    return 'world'"
        result_type = tool_rendering_handler.detect_result_type(result, "Read")
        assert result_type == ResultType.CODE

    def test_detect_code_from_bash_tool(self, tool_rendering_handler):
        """Test code detection from Bash tool."""
        result = "import os\nprint(os.getcwd())"
        result_type = tool_rendering_handler.detect_result_type(result, "Bash")
        assert result_type == ResultType.CODE

    def test_detect_json_dict(self, tool_rendering_handler):
        """Test JSON dict detection."""
        result = {"key": "value", "number": 42}
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.JSON

    def test_detect_json_list_of_primitives(self, tool_rendering_handler):
        """Test JSON list of primitives."""
        result = [1, 2, 3, "a", "b"]
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.JSON

    def test_detect_text_string(self, tool_rendering_handler):
        """Test plain text string detection."""
        result = "Just some plain text output"
        result_type = tool_rendering_handler.detect_result_type(result)
        assert result_type == ResultType.TEXT


# =============================================================================
# Test ToolRenderingHandler - Result Formatting
# =============================================================================


class TestToolRenderingHandlerFormatting:
    """Tests for result formatting."""

    def test_format_text_basic(self, tool_rendering_handler):
        """Test basic text formatting."""
        result = tool_rendering_handler.format_result("Hello world")
        assert result.result_type == ResultType.TEXT
        assert result.data == "Hello world"
        assert result.formatted is True

    def test_format_text_truncation(self, mock_executor):
        """Test text truncation when exceeding max length."""
        config = ToolRenderingConfig(max_text_length=10)
        handler = ToolRenderingHandler(
            unified_executor=mock_executor,
            config=config,
        )
        long_text = "A" * 100
        result = handler.format_result(long_text)
        assert len(result.data) == 10
        assert result.display_hint == "truncated-text"
        assert result.metadata["truncated"] is True

    def test_format_json_dict(self, tool_rendering_handler):
        """Test JSON dict formatting."""
        result = tool_rendering_handler.format_result(
            {"key": "value"}, ResultType.JSON
        )
        assert result.result_type == ResultType.JSON
        assert result.data == {"key": "value"}
        assert result.display_hint == "json-tree"

    def test_format_json_string(self, tool_rendering_handler):
        """Test JSON string formatting."""
        json_str = '{"parsed": true}'
        result = tool_rendering_handler.format_result(json_str, ResultType.JSON)
        assert result.result_type == ResultType.JSON
        assert result.data == {"parsed": True}

    def test_format_json_invalid_falls_back_to_text(self, tool_rendering_handler):
        """Test invalid JSON falls back to text."""
        result = tool_rendering_handler.format_result("not json {", ResultType.JSON)
        assert result.result_type == ResultType.TEXT

    def test_format_table_with_columns_data(self, tool_rendering_handler):
        """Test table formatting with columns and data."""
        data = {
            "columns": ["id", "name"],
            "data": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
        }
        result = tool_rendering_handler.format_result(data, ResultType.TABLE)
        assert result.result_type == ResultType.TABLE
        assert result.data["columns"] == ["id", "name"]
        assert len(result.data["rows"]) == 2
        assert result.display_hint == "data-table"

    def test_format_table_truncation(self, mock_executor):
        """Test table row truncation."""
        config = ToolRenderingConfig(max_table_rows=2)
        handler = ToolRenderingHandler(
            unified_executor=mock_executor,
            config=config,
        )
        data = [{"id": i} for i in range(10)]
        result = handler.format_result(data, ResultType.TABLE)
        assert len(result.data["rows"]) == 2
        assert result.metadata["truncated"] is True

    def test_format_table_list_of_dicts(self, tool_rendering_handler):
        """Test table from list of dicts."""
        data = [{"name": "a"}, {"name": "b"}]
        result = tool_rendering_handler.format_result(data, ResultType.TABLE)
        assert result.data["columns"] == ["name"]
        assert result.data["rows"] == data

    def test_format_image_url(self, tool_rendering_handler):
        """Test image URL formatting."""
        data = {"image_url": "https://example.com/img.png", "type": "png"}
        result = tool_rendering_handler.format_result(data, ResultType.IMAGE)
        assert result.result_type == ResultType.IMAGE
        assert result.data["url"] == "https://example.com/img.png"
        assert result.display_hint == "image"

    def test_format_image_data(self, tool_rendering_handler):
        """Test image data formatting."""
        data = {"image_data": "base64...", "type": "jpeg"}
        result = tool_rendering_handler.format_result(data, ResultType.IMAGE)
        assert result.data["data"] == "base64..."
        assert result.data["type"] == "jpeg"

    def test_format_code_dict(self, tool_rendering_handler):
        """Test code dict formatting."""
        data = {"code": "print('hello')", "language": "python"}
        result = tool_rendering_handler.format_result(data, ResultType.CODE)
        assert result.result_type == ResultType.CODE
        assert result.data["code"] == "print('hello')"
        assert result.data["language"] == "python"
        assert result.display_hint == "code-block"

    def test_format_code_string(self, tool_rendering_handler):
        """Test code string formatting."""
        code = "def foo():\n    return 42"
        result = tool_rendering_handler.format_result(code, ResultType.CODE, "Read")
        assert result.data["code"] == code
        assert result.data["language"] == "python"

    def test_format_code_truncation(self, mock_executor):
        """Test code truncation."""
        config = ToolRenderingConfig(max_text_length=20)
        handler = ToolRenderingHandler(
            unified_executor=mock_executor,
            config=config,
        )
        code = "x" * 100
        result = handler.format_result(code, ResultType.CODE)
        assert len(result.data["code"]) == 20
        assert result.metadata["truncated"] is True

    def test_format_error_dict(self, tool_rendering_handler):
        """Test error dict formatting."""
        data = {
            "error": "File not found",
            "error_type": "FileNotFoundError",
            "stack_trace": "Traceback...",
        }
        result = tool_rendering_handler.format_result(data, ResultType.ERROR)
        assert result.result_type == ResultType.ERROR
        assert result.data["message"] == "File not found"
        assert result.data["type"] == "FileNotFoundError"
        assert result.data["stack_trace"] == "Traceback..."

    def test_format_error_string(self, tool_rendering_handler):
        """Test error string formatting."""
        result = tool_rendering_handler.format_result(
            "Something failed", ResultType.ERROR
        )
        assert result.data["message"] == "Something failed"


# =============================================================================
# Test ToolRenderingHandler - Event Generation
# =============================================================================


class TestToolRenderingHandlerEvents:
    """Tests for AG-UI event generation."""

    @pytest.mark.asyncio
    async def test_create_start_event(self, tool_rendering_handler, sample_tool_call):
        """Test creating tool call start event."""
        event = await tool_rendering_handler.create_start_event(
            sample_tool_call, "run-123"
        )
        assert event.type == AGUIEventType.TOOL_CALL_START
        assert event.tool_call_id == "tc-test-123"
        assert event.tool_name == "Read"

    def test_create_status_event(self, tool_rendering_handler, sample_tool_call):
        """Test creating tool status event."""
        event = tool_rendering_handler.create_status_event(
            sample_tool_call, ToolExecutionStatus.RUNNING, progress=50.0
        )
        assert event.type == AGUIEventType.CUSTOM
        assert event.event_name == "tool_status"
        assert event.payload["tool_call_id"] == "tc-test-123"
        assert event.payload["status"] == "running"
        assert event.payload["progress"] == 50.0

    def test_create_status_event_without_progress(
        self, tool_rendering_handler, sample_tool_call
    ):
        """Test creating status event without progress."""
        event = tool_rendering_handler.create_status_event(
            sample_tool_call, ToolExecutionStatus.PENDING
        )
        assert event.payload["progress"] is None

    @pytest.mark.asyncio
    async def test_execute_and_format_success(
        self, tool_rendering_handler, mock_executor, mock_execution_result, sample_tool_call
    ):
        """Test successful tool execution and formatting."""
        from src.integrations.ag_ui.events import ToolCallStatus

        mock_executor.execute.return_value = mock_execution_result(
            success=True,
            content="File content here",
        )

        event = await tool_rendering_handler.execute_and_format(
            sample_tool_call, session_id="session-123"
        )

        assert event.type == AGUIEventType.TOOL_CALL_END
        assert event.tool_call_id == "tc-test-123"
        assert event.status == ToolCallStatus.SUCCESS
        assert event.error is None
        assert event.result is not None

    @pytest.mark.asyncio
    async def test_execute_and_format_error(
        self, tool_rendering_handler, mock_executor, mock_execution_result, sample_tool_call
    ):
        """Test failed tool execution and formatting."""
        from src.integrations.ag_ui.events import ToolCallStatus

        mock_executor.execute.return_value = mock_execution_result(
            success=False,
            content=None,
            error="Permission denied",
        )

        event = await tool_rendering_handler.execute_and_format(sample_tool_call)

        assert event.type == AGUIEventType.TOOL_CALL_END
        assert event.error == "Permission denied"
        assert event.status == ToolCallStatus.ERROR
        assert event.result is not None
        assert event.result["type"] == "error"

    @pytest.mark.asyncio
    async def test_execute_and_format_with_json_result(
        self, tool_rendering_handler, mock_executor, mock_execution_result, sample_tool_call
    ):
        """Test execution with JSON result."""
        from src.integrations.ag_ui.events import ToolCallStatus

        mock_executor.execute.return_value = mock_execution_result(
            success=True,
            content={"data": [1, 2, 3], "count": 3},
        )

        event = await tool_rendering_handler.execute_and_format(sample_tool_call)

        assert event.status == ToolCallStatus.SUCCESS
        assert event.result is not None
        assert event.result["type"] == "json"


# =============================================================================
# Test ToolRenderingHandler - Properties
# =============================================================================


class TestToolRenderingHandlerProperties:
    """Tests for handler properties."""

    def test_executor_property(self, tool_rendering_handler, mock_executor):
        """Test executor property."""
        assert tool_rendering_handler.executor is mock_executor

    def test_config_property(self, tool_rendering_handler):
        """Test config property."""
        config = tool_rendering_handler.config
        assert isinstance(config, ToolRenderingConfig)
        assert config.max_text_length == 10000


# =============================================================================
# Test Factory Function
# =============================================================================


class TestCreateToolRenderingHandler:
    """Tests for factory function."""

    def test_create_with_defaults(self, mock_executor):
        """Test creating handler with defaults."""
        handler = create_tool_rendering_handler(unified_executor=mock_executor)
        assert handler.executor is mock_executor
        assert handler.config.max_text_length == 10000

    def test_create_with_custom_config(self, mock_executor):
        """Test creating handler with custom config."""
        config = ToolRenderingConfig(max_text_length=5000)
        handler = create_tool_rendering_handler(
            unified_executor=mock_executor,
            config=config,
        )
        assert handler.config.max_text_length == 5000


# =============================================================================
# Test Internal Methods
# =============================================================================


class TestToolRenderingHandlerInternals:
    """Tests for internal helper methods."""

    def test_looks_like_code_python(self, tool_rendering_handler):
        """Test code detection for Python."""
        code = "def hello():\n    return 42"
        assert tool_rendering_handler._looks_like_code(code) is True

    def test_looks_like_code_class(self, tool_rendering_handler):
        """Test code detection for class."""
        code = "class Foo:\n    pass"
        assert tool_rendering_handler._looks_like_code(code) is True

    def test_looks_like_code_import(self, tool_rendering_handler):
        """Test code detection for import."""
        code = "import os\nfrom typing import List"
        assert tool_rendering_handler._looks_like_code(code) is True

    def test_looks_like_code_javascript(self, tool_rendering_handler):
        """Test code detection for JavaScript."""
        code = "function hello() { return 42; }"
        assert tool_rendering_handler._looks_like_code(code) is True

    def test_looks_like_code_false_for_plain_text(self, tool_rendering_handler):
        """Test plain text is not detected as code."""
        text = "This is just some regular text content."
        assert tool_rendering_handler._looks_like_code(text) is False


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestToolRenderingEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_list_detection(self, tool_rendering_handler):
        """Test empty list detection."""
        result_type = tool_rendering_handler.detect_result_type([])
        assert result_type == ResultType.JSON

    def test_empty_dict_detection(self, tool_rendering_handler):
        """Test empty dict detection."""
        result_type = tool_rendering_handler.detect_result_type({})
        assert result_type == ResultType.JSON

    def test_nested_structure(self, tool_rendering_handler):
        """Test deeply nested structure."""
        data = {"level1": {"level2": {"level3": {"value": 42}}}}
        result = tool_rendering_handler.format_result(data, ResultType.JSON)
        assert result.data == data

    def test_unicode_content(self, tool_rendering_handler):
        """Test Unicode content handling."""
        result = tool_rendering_handler.format_result("中文測試 🚀")
        assert result.data == "中文測試 🚀"

    def test_special_characters_in_code(self, tool_rendering_handler):
        """Test special characters in code."""
        code = 'print("Hello\\nWorld")'
        result = tool_rendering_handler.format_result(code, ResultType.CODE)
        assert result.data["code"] == code

    def test_table_with_empty_rows(self, tool_rendering_handler):
        """Test table with empty rows list."""
        data = {"columns": ["a", "b"], "data": []}
        result = tool_rendering_handler.format_result(data, ResultType.TABLE)
        assert result.data["rows"] == []

    def test_table_extraction_from_table_key(self, tool_rendering_handler):
        """Test table extraction from 'table' key."""
        data = {"table": [{"id": 1}, {"id": 2}]}
        result = tool_rendering_handler.format_result(data, ResultType.TABLE)
        assert result.data["columns"] == ["id"]
        assert len(result.data["rows"]) == 2

    def test_format_result_auto_detection(self, tool_rendering_handler):
        """Test format_result with auto type detection."""
        # No explicit type - should auto-detect
        data = {"columns": ["a"], "rows": [{"a": 1}]}
        result = tool_rendering_handler.format_result(data)
        assert result.result_type == ResultType.TABLE
