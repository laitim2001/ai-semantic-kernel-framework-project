"""Unit tests for MCP exceptions.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Tests for MCP exception classes.
"""

import pytest

from src.integrations.claude_sdk.mcp.exceptions import (
    MCPConfigurationError,
    MCPConnectionError,
    MCPDisconnectedError,
    MCPError,
    MCPInvalidParamsError,
    MCPInvalidRequestError,
    MCPMethodNotFoundError,
    MCPParseError,
    MCPServerError,
    MCPTimeoutError,
    MCPToolExecutionError,
    MCPToolNotFoundError,
)
from src.integrations.claude_sdk.mcp.types import MCPErrorCode


# ============================================================================
# MCPError Tests
# ============================================================================


class TestMCPError:
    """Tests for base MCPError class."""

    def test_default_message(self):
        """Test default error message."""
        error = MCPError()
        assert error.message == "Internal MCP error"
        assert error.code == MCPErrorCode.INTERNAL_ERROR
        assert str(error) == "Internal MCP error"

    def test_custom_message(self):
        """Test custom error message."""
        error = MCPError(message="Custom error")
        assert error.message == "Custom error"
        assert str(error) == "Custom error"

    def test_custom_code(self):
        """Test custom error code."""
        error = MCPError(code=-32001)
        assert error.code == -32001

    def test_with_data(self):
        """Test error with additional data."""
        error = MCPError(
            message="Error with data",
            data={"key": "value"},
        )
        assert error.data == {"key": "value"}

    def test_to_dict(self):
        """Test converting to JSON-RPC error format."""
        error = MCPError(
            message="Test error",
            code=-32000,
            data={"detail": "info"},
        )

        d = error.to_dict()
        assert d["code"] == -32000
        assert d["message"] == "Test error"
        assert d["data"] == {"detail": "info"}

    def test_to_dict_without_data(self):
        """Test converting to dict without data."""
        error = MCPError(message="Simple error")

        d = error.to_dict()
        assert d["code"] == MCPErrorCode.INTERNAL_ERROR
        assert d["message"] == "Simple error"
        assert "data" not in d


# ============================================================================
# MCPConnectionError Tests
# ============================================================================


class TestMCPConnectionError:
    """Tests for MCPConnectionError."""

    def test_default_message(self):
        """Test default message."""
        error = MCPConnectionError()
        assert "connect" in error.message.lower()
        assert error.code == MCPErrorCode.CONNECTION_ERROR

    def test_custom_message(self):
        """Test custom message."""
        error = MCPConnectionError("Connection refused")
        assert error.message == "Connection refused"


# ============================================================================
# MCPDisconnectedError Tests
# ============================================================================


class TestMCPDisconnectedError:
    """Tests for MCPDisconnectedError."""

    def test_default_message(self):
        """Test default message."""
        error = MCPDisconnectedError()
        assert "not connected" in error.message.lower()
        assert error.code == MCPErrorCode.SERVER_NOT_CONNECTED


# ============================================================================
# MCPTimeoutError Tests
# ============================================================================


class TestMCPTimeoutError:
    """Tests for MCPTimeoutError."""

    def test_default_message(self):
        """Test default message."""
        error = MCPTimeoutError()
        assert "timeout" in error.message.lower()
        assert error.code == MCPErrorCode.TIMEOUT_ERROR

    def test_custom_message(self):
        """Test custom message."""
        error = MCPTimeoutError("Request timed out after 30s")
        assert error.message == "Request timed out after 30s"


# ============================================================================
# MCPToolNotFoundError Tests
# ============================================================================


class TestMCPToolNotFoundError:
    """Tests for MCPToolNotFoundError."""

    def test_tool_name_only(self):
        """Test with tool name only."""
        error = MCPToolNotFoundError("read_file")
        assert error.tool_name == "read_file"
        assert "read_file" in error.message
        assert error.server_name is None
        assert error.code == MCPErrorCode.TOOL_NOT_FOUND

    def test_with_server_name(self):
        """Test with server name."""
        error = MCPToolNotFoundError("read_file", "filesystem")
        assert error.tool_name == "read_file"
        assert error.server_name == "filesystem"
        assert "read_file" in error.message
        assert "filesystem" in error.message

    def test_data_contains_tool_name(self):
        """Test data contains tool name."""
        error = MCPToolNotFoundError("my_tool")
        assert error.data == {"tool_name": "my_tool"}


# ============================================================================
# MCPToolExecutionError Tests
# ============================================================================


class TestMCPToolExecutionError:
    """Tests for MCPToolExecutionError."""

    def test_basic_error(self):
        """Test basic execution error."""
        error = MCPToolExecutionError("read_file", "File not found")
        assert error.tool_name == "read_file"
        assert "read_file" in error.message
        assert "File not found" in error.message
        assert error.code == MCPErrorCode.TOOL_EXECUTION_ERROR

    def test_with_server_name(self):
        """Test with server name."""
        error = MCPToolExecutionError(
            "write_file",
            "Permission denied",
            "filesystem",
        )
        assert error.tool_name == "write_file"
        assert error.server_name == "filesystem"

    def test_data_contains_details(self):
        """Test data contains error details."""
        error = MCPToolExecutionError("tool", "error message")
        assert error.data["tool_name"] == "tool"
        assert error.data["error"] == "error message"


# ============================================================================
# MCPParseError Tests
# ============================================================================


class TestMCPParseError:
    """Tests for MCPParseError."""

    def test_default_message(self):
        """Test default message."""
        error = MCPParseError()
        assert "parse" in error.message.lower()
        assert error.code == MCPErrorCode.PARSE_ERROR


# ============================================================================
# MCPInvalidRequestError Tests
# ============================================================================


class TestMCPInvalidRequestError:
    """Tests for MCPInvalidRequestError."""

    def test_default_message(self):
        """Test default message."""
        error = MCPInvalidRequestError()
        assert "invalid" in error.message.lower()
        assert error.code == MCPErrorCode.INVALID_REQUEST


# ============================================================================
# MCPMethodNotFoundError Tests
# ============================================================================


class TestMCPMethodNotFoundError:
    """Tests for MCPMethodNotFoundError."""

    def test_with_method_name(self):
        """Test with method name."""
        error = MCPMethodNotFoundError("unknown_method")
        assert error.method == "unknown_method"
        assert "unknown_method" in error.message
        assert error.code == MCPErrorCode.METHOD_NOT_FOUND
        assert error.data == {"method": "unknown_method"}


# ============================================================================
# MCPInvalidParamsError Tests
# ============================================================================


class TestMCPInvalidParamsError:
    """Tests for MCPInvalidParamsError."""

    def test_default_message(self):
        """Test default message."""
        error = MCPInvalidParamsError()
        assert "param" in error.message.lower()
        assert error.code == MCPErrorCode.INVALID_PARAMS


# ============================================================================
# MCPServerError Tests
# ============================================================================


class TestMCPServerError:
    """Tests for MCPServerError."""

    def test_create_with_code_and_message(self):
        """Test creating with code and message."""
        error = MCPServerError(-32000, "Server error")
        assert error.code == -32000
        assert error.message == "Server error"

    def test_with_data(self):
        """Test with additional data."""
        error = MCPServerError(
            code=-32001,
            message="Error with data",
            data={"detail": "more info"},
        )
        assert error.data == {"detail": "more info"}

    def test_from_response(self):
        """Test creating from JSON-RPC error response."""
        response = {
            "code": -32602,
            "message": "Invalid params",
            "data": {"param": "name"},
        }

        error = MCPServerError.from_response(response)
        assert error.code == -32602
        assert error.message == "Invalid params"
        assert error.data == {"param": "name"}

    def test_from_response_minimal(self):
        """Test creating from minimal response."""
        response = {"code": -32000}

        error = MCPServerError.from_response(response)
        assert error.code == -32000
        assert error.message == "Unknown error"


# ============================================================================
# MCPConfigurationError Tests
# ============================================================================


class TestMCPConfigurationError:
    """Tests for MCPConfigurationError."""

    def test_with_message(self):
        """Test with message."""
        error = MCPConfigurationError("Invalid configuration")
        assert error.message == "Invalid configuration"
        assert error.code == MCPErrorCode.INTERNAL_ERROR

    def test_with_config_key(self):
        """Test with config key."""
        error = MCPConfigurationError(
            "Missing required field",
            config_key="url",
        )
        assert error.data == {"config_key": "url"}

    def test_without_config_key(self):
        """Test without config key."""
        error = MCPConfigurationError("General config error")
        assert error.data is None
