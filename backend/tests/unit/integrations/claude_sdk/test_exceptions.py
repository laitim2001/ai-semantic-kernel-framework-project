"""Tests for Claude SDK exceptions."""

import pytest

from src.integrations.claude_sdk.exceptions import (
    ClaudeSDKError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    ToolError,
    HookRejectionError,
    MCPError,
    MCPConnectionError,
    MCPToolError,
)


class TestClaudeSDKError:
    """Tests for base ClaudeSDKError."""

    def test_init_with_message(self):
        """Test exception with message only."""
        error = ClaudeSDKError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_init_with_details(self):
        """Test exception with message and details."""
        details = {"code": 500, "reason": "Internal error"}
        error = ClaudeSDKError("Test error", details=details)
        assert error.details == details


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_inherits_from_base(self):
        """Test that AuthenticationError inherits from ClaudeSDKError."""
        error = AuthenticationError("API key invalid")
        assert isinstance(error, ClaudeSDKError)


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_with_retry_after(self):
        """Test rate limit error with retry_after."""
        error = RateLimitError("Rate limited", retry_after=60)
        assert error.retry_after == 60

    def test_without_retry_after(self):
        """Test rate limit error without retry_after."""
        error = RateLimitError("Rate limited")
        assert error.retry_after is None


class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_creates_correctly(self):
        """Test timeout error creation."""
        error = TimeoutError("Operation timed out")
        assert isinstance(error, ClaudeSDKError)
        assert error.message == "Operation timed out"


class TestToolError:
    """Tests for ToolError."""

    def test_with_tool_info(self):
        """Test tool error with tool information."""
        error = ToolError(
            message="Tool failed",
            tool_name="Read",
            tool_args={"path": "/test.txt"},
        )
        assert error.tool_name == "Read"
        assert error.tool_args == {"path": "/test.txt"}

    def test_without_args(self):
        """Test tool error without args."""
        error = ToolError(message="Tool failed", tool_name="Bash")
        assert error.tool_args == {}


class TestHookRejectionError:
    """Tests for HookRejectionError."""

    def test_with_hook_name(self):
        """Test hook rejection error with hook name."""
        error = HookRejectionError(
            message="Operation rejected", hook_name="ApprovalHook"
        )
        assert error.hook_name == "ApprovalHook"


class TestMCPError:
    """Tests for MCP-related errors."""

    def test_mcp_error_base(self):
        """Test base MCP error."""
        error = MCPError("MCP operation failed")
        assert isinstance(error, ClaudeSDKError)

    def test_mcp_connection_error(self):
        """Test MCP connection error."""
        error = MCPConnectionError(
            message="Connection failed",
            server_name="filesystem",
            command="npx @modelcontextprotocol/filesystem",
        )
        assert error.server_name == "filesystem"
        assert error.command == "npx @modelcontextprotocol/filesystem"

    def test_mcp_tool_error(self):
        """Test MCP tool error."""
        error = MCPToolError(
            message="Tool execution failed",
            server_name="github",
            tool_name="list_repos",
        )
        assert error.server_name == "github"
        assert error.tool_name == "list_repos"
