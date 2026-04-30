"""Tests for Claude SDK query module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from src.integrations.claude_sdk.query import execute_query
from src.integrations.claude_sdk.config import ClaudeSDKConfig
from src.integrations.claude_sdk.types import (
    QueryResult,
    ToolCall,
    QueryContext,
    HookResult,
    ALLOW,
)
from src.integrations.claude_sdk.exceptions import (
    ClaudeSDKError,
    TimeoutError,
    ToolError,
    HookRejectionError,
)


class TestExecuteQuery:
    """Tests for execute_query function."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Anthropic client."""
        client = MagicMock()
        client.messages = MagicMock()
        client.messages.create = AsyncMock()
        return client

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return ClaudeSDKConfig(
            api_key="test-key",
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            timeout=300,
        )

    @pytest.fixture
    def simple_response(self):
        """Create a simple text response."""
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Hello! How can I help you?"
        response.content = [text_block]
        response.usage = MagicMock()
        response.usage.input_tokens = 50
        response.usage.output_tokens = 20
        response.stop_reason = "end_turn"
        return response

    @pytest.fixture
    def tool_use_response(self):
        """Create a response with tool use."""
        response = MagicMock()
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_123"
        tool_block.name = "Read"
        tool_block.input = {"path": "/test.txt"}
        response.content = [tool_block]
        response.usage = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.stop_reason = "tool_use"
        return response

    @pytest.mark.asyncio
    async def test_execute_simple_query(
        self, mock_client, config, simple_response
    ):
        """Test executing a simple query without tools."""
        mock_client.messages.create.return_value = simple_response

        result = await execute_query(
            client=mock_client,
            config=config,
            prompt="Hello!",
            tools=[],
            max_tokens=4096,
            timeout=300,
            working_directory=None,
            hooks=[],
            mcp_servers=[],
        )

        assert isinstance(result, QueryResult)
        assert result.content == "Hello! How can I help you?"
        # Status is "success" not "completed"
        assert result.status == "success"
        assert result.tokens_used == 70  # 50 + 20
        assert len(result.tool_calls) == 0

    @pytest.mark.asyncio
    async def test_execute_query_with_system_prompt(
        self, mock_client, config, simple_response
    ):
        """Test query includes system prompt in request."""
        config.system_prompt = "You are a helpful assistant."
        mock_client.messages.create.return_value = simple_response

        await execute_query(
            client=mock_client,
            config=config,
            prompt="Hello!",
            tools=[],
            max_tokens=4096,
            timeout=300,
            working_directory=None,
            hooks=[],
            mcp_servers=[],
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs.get("system") == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_execute_query_with_tools(
        self, mock_client, config, tool_use_response, simple_response
    ):
        """Test query that uses tools."""
        # First call returns tool use, second returns final response
        mock_client.messages.create.side_effect = [
            tool_use_response,
            simple_response,
        ]

        with patch(
            "src.integrations.claude_sdk.query.execute_tool",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = "file content"

            result = await execute_query(
                client=mock_client,
                config=config,
                prompt="Read the file",
                tools=["Read"],
                max_tokens=4096,
                timeout=300,
                working_directory=None,
                hooks=[],
                mcp_servers=[],
            )

            assert result.status == "success"
            assert len(result.tool_calls) == 1
            assert result.tool_calls[0].name == "Read"

    @pytest.mark.asyncio
    async def test_execute_query_records_duration(
        self, mock_client, config, simple_response
    ):
        """Test that query duration is recorded."""
        mock_client.messages.create.return_value = simple_response

        result = await execute_query(
            client=mock_client,
            config=config,
            prompt="Hello!",
            tools=[],
            max_tokens=4096,
            timeout=300,
            working_directory=None,
            hooks=[],
            mcp_servers=[],
        )

        assert result.duration >= 0.0

    @pytest.mark.asyncio
    async def test_execute_query_custom_max_tokens(
        self, mock_client, config, simple_response
    ):
        """Test query with custom max_tokens."""
        mock_client.messages.create.return_value = simple_response

        await execute_query(
            client=mock_client,
            config=config,
            prompt="Hello!",
            tools=[],
            max_tokens=2048,
            timeout=300,
            working_directory=None,
            hooks=[],
            mcp_servers=[],
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 2048


class TestQueryWithHooks:
    """Tests for query execution with hooks."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock client."""
        client = MagicMock()
        client.messages = MagicMock()
        client.messages.create = AsyncMock()
        return client

    @pytest.fixture
    def config(self):
        """Create test config."""
        return ClaudeSDKConfig(api_key="test-key")

    @pytest.fixture
    def tool_use_response(self):
        """Create a tool use response."""
        response = MagicMock()
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_456"
        tool_block.name = "Bash"
        tool_block.input = {"command": "ls -la"}
        response.content = [tool_block]
        response.usage = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.stop_reason = "tool_use"
        return response

    @pytest.mark.asyncio
    async def test_pre_tool_call_hook_allows(
        self, mock_client, config, tool_use_response
    ):
        """Test pre_tool_call hook that allows execution."""
        simple_response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Done"
        simple_response.content = [text_block]
        simple_response.usage = MagicMock()
        simple_response.usage.input_tokens = 50
        simple_response.usage.output_tokens = 20
        simple_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [
            tool_use_response,
            simple_response,
        ]

        # Create a mock hook object with on_tool_call method
        mock_hook = MagicMock()
        mock_hook.on_tool_call = AsyncMock(return_value=ALLOW)
        mock_hook.on_tool_result = AsyncMock()

        with patch(
            "src.integrations.claude_sdk.query.execute_tool",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = "success"

            result = await execute_query(
                client=mock_client,
                config=config,
                prompt="Run ls",
                tools=["Bash"],
                max_tokens=4096,
                timeout=300,
                working_directory=None,
                hooks=[mock_hook],
                mcp_servers=[],
            )

            mock_hook.on_tool_call.assert_called()
            assert result.status == "success"

    @pytest.mark.asyncio
    async def test_pre_tool_call_hook_rejects(
        self, mock_client, config, tool_use_response
    ):
        """Test pre_tool_call hook that rejects execution."""
        simple_response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Done"
        simple_response.content = [text_block]
        simple_response.usage = MagicMock()
        simple_response.usage.input_tokens = 50
        simple_response.usage.output_tokens = 20

        mock_client.messages.create.side_effect = [
            tool_use_response,
            simple_response,
        ]

        # Create a mock hook that rejects
        mock_hook = MagicMock()
        mock_hook.on_tool_call = AsyncMock(
            return_value=HookResult.reject("Command not allowed")
        )
        mock_hook.on_tool_result = AsyncMock()

        # The query doesn't raise but continues with rejection message
        result = await execute_query(
            client=mock_client,
            config=config,
            prompt="Run dangerous command",
            tools=["Bash"],
            max_tokens=4096,
            timeout=300,
            working_directory=None,
            hooks=[mock_hook],
            mcp_servers=[],
        )

        # Hook was called
        mock_hook.on_tool_call.assert_called()

    @pytest.mark.asyncio
    async def test_pre_tool_call_hook_modifies(
        self, mock_client, config, tool_use_response
    ):
        """Test pre_tool_call hook that modifies arguments."""
        simple_response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Done"
        simple_response.content = [text_block]
        simple_response.usage = MagicMock()
        simple_response.usage.input_tokens = 50
        simple_response.usage.output_tokens = 20
        simple_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [
            tool_use_response,
            simple_response,
        ]

        modified_args = {"command": "ls -la --safe"}
        mock_hook = MagicMock()
        mock_hook.on_tool_call = AsyncMock(
            return_value=HookResult.modify(modified_args)
        )
        mock_hook.on_tool_result = AsyncMock()

        with patch(
            "src.integrations.claude_sdk.query.execute_tool",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = "success"

            await execute_query(
                client=mock_client,
                config=config,
                prompt="Run ls",
                tools=["Bash"],
                max_tokens=4096,
                timeout=300,
                working_directory=None,
                hooks=[mock_hook],
                mcp_servers=[],
            )

            mock_hook.on_tool_call.assert_called()


class TestQueryContext:
    """Tests for QueryContext functionality."""

    def test_query_context_creation(self):
        """Test QueryContext creation."""
        context = QueryContext(
            prompt="Test prompt",
            tools=["Read", "Write"],
            session_id="test-session",
        )

        assert context.prompt == "Test prompt"
        assert context.tools == ["Read", "Write"]
        assert context.session_id == "test-session"

    def test_query_context_defaults(self):
        """Test QueryContext default values."""
        context = QueryContext(prompt="Test")

        assert context.tools == []
        assert context.session_id is None


class TestQueryResultAggregation:
    """Tests for QueryResult aggregation."""

    def test_query_result_with_multiple_tool_calls(self):
        """Test QueryResult with multiple tool calls."""
        tool_calls = [
            ToolCall(id="1", name="Read", args={"path": "/a.txt"}),
            ToolCall(id="2", name="Read", args={"path": "/b.txt"}),
            ToolCall(id="3", name="Write", args={"path": "/c.txt", "content": "x"}),
        ]

        result = QueryResult(
            content="Done processing files",
            tool_calls=tool_calls,
            tokens_used=500,
            duration=2.5,
            status="success",
        )

        assert len(result.tool_calls) == 3
        assert result.tokens_used == 500

    def test_query_result_status_values(self):
        """Test different QueryResult status values."""
        # Valid status values based on implementation
        statuses = ["success", "timeout", "error"]

        for status in statuses:
            result = QueryResult(
                content="Test",
                tool_calls=[],
                tokens_used=100,
                duration=1.0,
                status=status,
            )
            assert result.status == status
