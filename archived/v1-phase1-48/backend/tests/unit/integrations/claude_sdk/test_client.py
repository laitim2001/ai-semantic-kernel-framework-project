"""Tests for Claude SDK client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.claude_sdk.client import ClaudeSDKClient
from src.integrations.claude_sdk.config import ClaudeSDKConfig
from src.integrations.claude_sdk.exceptions import (
    AuthenticationError,
    ClaudeSDKError,
    RateLimitError,
    TimeoutError,
)
from src.integrations.claude_sdk.types import QueryResult


class TestClaudeSDKClientInit:
    """Tests for ClaudeSDKClient initialization."""

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = ClaudeSDKClient(api_key="test-key")
        assert client.config.api_key == "test-key"
        assert client.config.model == "claude-sonnet-4-20250514"

    def test_init_with_custom_model(self):
        """Test client initialization with custom model."""
        client = ClaudeSDKClient(
            api_key="test-key", model="claude-opus-4-20250514"
        )
        assert client.config.model == "claude-opus-4-20250514"

    def test_init_with_custom_max_tokens(self):
        """Test client initialization with custom max_tokens."""
        client = ClaudeSDKClient(api_key="test-key", max_tokens=8192)
        assert client.config.max_tokens == 8192

    def test_init_with_system_prompt(self):
        """Test client initialization with system prompt."""
        client = ClaudeSDKClient(
            api_key="test-key",
            system_prompt="You are a helpful assistant.",
        )
        assert client.config.system_prompt == "You are a helpful assistant."

    def test_init_with_tools(self):
        """Test client initialization with tools list."""
        client = ClaudeSDKClient(
            api_key="test-key", tools=["Read", "Write", "Bash"]
        )
        # Tools are stored on client.tools, not config.tools
        assert client.tools == ["Read", "Write", "Bash"]

    def test_init_without_api_key_raises_error(self, monkeypatch):
        """Test that missing API key raises AuthenticationError."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(AuthenticationError) as exc_info:
            ClaudeSDKClient()
        assert "ANTHROPIC_API_KEY not configured" in str(exc_info.value)

    def test_init_from_env(self, monkeypatch):
        """Test client initialization from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        client = ClaudeSDKClient()
        assert client.config.api_key == "env-key"


class TestClaudeSDKClientQuery:
    """Tests for ClaudeSDKClient.query() method."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return ClaudeSDKClient(api_key="test-key")

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create a mock Anthropic API response."""
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Test response"
        response.content = [text_block]
        response.usage = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.stop_reason = "end_turn"
        return response

    @pytest.mark.asyncio
    async def test_query_basic(self, client, mock_anthropic_response):
        """Test basic query execution."""
        with patch.object(
            client._client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_anthropic_response

            result = await client.query("Hello, Claude!")

            assert isinstance(result, QueryResult)
            assert result.content == "Test response"
            # Status is "success" not "completed"
            assert result.status == "success"

    @pytest.mark.asyncio
    async def test_query_with_custom_max_tokens(
        self, client, mock_anthropic_response
    ):
        """Test query with custom max_tokens."""
        with patch.object(
            client._client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_anthropic_response

            await client.query("Hello!", max_tokens=2048)

            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args.kwargs["max_tokens"] == 2048

    @pytest.mark.asyncio
    async def test_query_with_tools(self, client, mock_anthropic_response):
        """Test query with specific tools."""
        with patch.object(
            client._client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_anthropic_response

            await client.query("Read file", tools=["Read"])

            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_error_returns_error_result(self, client):
        """Test query error returns result with error status (doesn't raise)."""
        with patch.object(
            client._client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("Connection timeout")

            # Query doesn't raise, returns QueryResult with status="error"
            result = await client.query("Hello!", timeout=1)

            assert isinstance(result, QueryResult)
            assert result.status == "error"
            assert "Connection timeout" in result.error

    @pytest.mark.asyncio
    async def test_query_api_error_returns_error_result(self, client):
        """Test query API error returns result with error status."""
        with patch.object(
            client._client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("API Error")

            result = await client.query("Hello!")

            assert isinstance(result, QueryResult)
            assert result.status == "error"


class TestClaudeSDKClientSession:
    """Tests for ClaudeSDKClient session management."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return ClaudeSDKClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_create_session(self, client):
        """Test session creation."""
        session = await client.create_session()

        assert session is not None
        assert session.session_id is not None
        # Session's _client is the AsyncAnthropic instance, not the ClaudeSDKClient
        assert session._client == client._client

    @pytest.mark.asyncio
    async def test_create_session_with_id(self, client):
        """Test session creation with custom ID."""
        session = await client.create_session(session_id="custom-session-123")

        assert session.session_id == "custom-session-123"

    @pytest.mark.asyncio
    async def test_create_session_with_context(self, client):
        """Test session creation with context."""
        context = {"project": "test-project", "user": "test-user"}
        session = await client.create_session(context=context)

        # Context is accessed via get_context() method
        assert session.get_context() == context

    @pytest.mark.asyncio
    async def test_resume_session(self, client):
        """Test session resumption."""
        # First create a session
        original_session = await client.create_session(
            session_id="resume-test"
        )

        # Then resume it
        resumed_session = await client.resume_session("resume-test")

        assert resumed_session.session_id == original_session.session_id

    @pytest.mark.asyncio
    async def test_resume_nonexistent_session_raises_error(self, client):
        """Test resuming non-existent session raises error."""
        with pytest.raises(ClaudeSDKError) as exc_info:
            await client.resume_session("nonexistent-session")
        # Error message format: "Session {id} not found"
        assert "nonexistent-session not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_sessions(self, client):
        """Test getting all sessions."""
        # Create multiple sessions
        await client.create_session(session_id="session-1")
        await client.create_session(session_id="session-2")

        sessions = client.get_sessions()

        assert "session-1" in sessions
        assert "session-2" in sessions

    @pytest.mark.asyncio
    async def test_close_session_marks_as_closed(self, client):
        """Test session closure marks session as closed."""
        session = await client.create_session(session_id="close-test")
        await session.close()

        # Session is marked as closed
        assert session.is_closed is True


class TestClaudeSDKClientHooks:
    """Tests for ClaudeSDKClient hook integration."""

    @pytest.fixture
    def mock_hook(self):
        """Create a mock hook."""
        hook = MagicMock()
        hook.on_session_start = AsyncMock()
        hook.on_session_end = AsyncMock()
        hook.on_tool_call = AsyncMock(return_value=None)
        hook.on_tool_result = AsyncMock()
        return hook

    @pytest.fixture
    def client_with_hooks(self, mock_hook):
        """Create a client with hooks."""
        return ClaudeSDKClient(api_key="test-key", hooks=[mock_hook])

    def test_hooks_registered(self, client_with_hooks, mock_hook):
        """Test hooks are registered on client."""
        # Hooks is a list attribute
        assert client_with_hooks.hooks is not None
        assert isinstance(client_with_hooks.hooks, list)
        assert len(client_with_hooks.hooks) == 1
        assert client_with_hooks.hooks[0] == mock_hook
