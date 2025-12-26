"""Tests for Claude SDK session module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import time

from src.integrations.claude_sdk.session import Session
from src.integrations.claude_sdk.config import ClaudeSDKConfig
from src.integrations.claude_sdk.types import (
    SessionResponse,
    ToolCall,
    Message,
    HookResult,
    ALLOW,
)
from src.integrations.claude_sdk.exceptions import ClaudeSDKError


class TestSessionInit:
    """Tests for Session initialization."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client."""
        client = MagicMock()
        client.messages = MagicMock()
        client.messages.create = AsyncMock()
        return client

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return ClaudeSDKConfig(api_key="test-key")

    def test_session_init_basic(self, mock_anthropic_client, config):
        """Test basic session initialization."""
        session = Session(
            session_id="test-session",
            client=mock_anthropic_client,
            config=config,
            tools=[],
            hooks=[],
            mcp_servers=[],
        )

        assert session.session_id == "test-session"
        assert len(session.get_history()) == 0

    def test_session_init_with_tools(self, mock_anthropic_client, config):
        """Test session initialization with tools."""
        session = Session(
            session_id="test-session",
            client=mock_anthropic_client,
            config=config,
            tools=["Read", "Write", "Bash"],
            hooks=[],
            mcp_servers=[],
        )

        assert session._tools == ["Read", "Write", "Bash"]

    def test_session_init_with_context(self, mock_anthropic_client, config):
        """Test session initialization with context."""
        context = {"project": "test-project", "user_id": "user-123"}
        session = Session(
            session_id="test-session",
            client=mock_anthropic_client,
            config=config,
            tools=[],
            hooks=[],
            mcp_servers=[],
            context=context,
        )

        assert session.get_context() == context

    def test_session_init_with_history(self, mock_anthropic_client, config):
        """Test session initialization with existing history."""
        history = [
            Message(role="user", content="Hello", timestamp=time.time()),
            Message(role="assistant", content="Hi there!", timestamp=time.time()),
        ]
        session = Session(
            session_id="test-session",
            client=mock_anthropic_client,
            config=config,
            tools=[],
            hooks=[],
            mcp_servers=[],
            history=history,
        )

        assert len(session.get_history()) == 2
        assert session.get_history()[0].content == "Hello"


class TestSessionQuery:
    """Tests for Session.query() method."""

    @pytest.fixture
    def mock_anthropic_client(self):
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
    def session(self, mock_anthropic_client, config):
        """Create a test session."""
        return Session(
            session_id="test-session",
            client=mock_anthropic_client,
            config=config,
            tools=["Read"],
            hooks=[],
            mcp_servers=[],
        )

    @pytest.fixture
    def simple_response(self):
        """Create a simple API response."""
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Hello! I'm Claude."
        response.content = [text_block]
        response.usage = MagicMock()
        response.usage.input_tokens = 50
        response.usage.output_tokens = 30
        return response

    @pytest.mark.asyncio
    async def test_query_basic(
        self, session, simple_response, mock_anthropic_client
    ):
        """Test basic session query."""
        mock_anthropic_client.messages.create.return_value = simple_response

        result = await session.query("Hello!")

        assert isinstance(result, SessionResponse)
        assert result.content == "Hello! I'm Claude."

    @pytest.mark.asyncio
    async def test_query_updates_history(
        self, session, simple_response, mock_anthropic_client
    ):
        """Test that query updates session history."""
        mock_anthropic_client.messages.create.return_value = simple_response

        await session.query("Hello!")

        history = session.get_history()
        # Should have user message and assistant message
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hello!"
        assert history[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_query_closed_session_raises_error(
        self, session, mock_anthropic_client
    ):
        """Test that querying closed session raises error."""
        session._closed = True

        with pytest.raises(RuntimeError) as exc_info:
            await session.query("Hello!")

        assert "Session is closed" in str(exc_info.value)


class TestSessionHistory:
    """Tests for session history management."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock client."""
        return MagicMock()

    @pytest.fixture
    def config(self):
        """Create test config."""
        return ClaudeSDKConfig(api_key="test-key")

    @pytest.fixture
    def session(self, mock_anthropic_client, config):
        """Create a test session."""
        return Session(
            session_id="test-session",
            client=mock_anthropic_client,
            config=config,
            tools=[],
            hooks=[],
            mcp_servers=[],
        )

    def test_get_history_empty(self, session):
        """Test getting empty history."""
        history = session.get_history()
        assert history == []

    def test_get_history_with_messages(self, session):
        """Test getting history with messages."""
        session._history = [
            Message(role="user", content="Hello", timestamp=time.time()),
            Message(role="assistant", content="Hi!", timestamp=time.time()),
        ]

        history = session.get_history()

        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"

    def test_get_history_returns_copy(self, session):
        """Test that get_history returns a copy."""
        session._history = [
            Message(role="user", content="Hello", timestamp=time.time()),
        ]

        history = session.get_history()
        history.append(Message(role="user", content="Modified", timestamp=time.time()))

        # Original should be unchanged
        assert len(session._history) == 1


class TestSessionFork:
    """Tests for session forking."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock client."""
        return MagicMock()

    @pytest.fixture
    def config(self):
        """Create test config."""
        return ClaudeSDKConfig(api_key="test-key")

    @pytest.fixture
    def session(self, mock_anthropic_client, config):
        """Create a test session with history."""
        session = Session(
            session_id="original-session",
            client=mock_anthropic_client,
            config=config,
            tools=["Read", "Write"],
            hooks=[],
            mcp_servers=[],
            context={"project": "test"},
        )
        session._history = [
            Message(role="user", content="Hello", timestamp=time.time()),
            Message(role="assistant", content="Hi!", timestamp=time.time()),
        ]
        return session

    @pytest.mark.asyncio
    async def test_fork_creates_new_session(self, session):
        """Test that fork creates a new session."""
        forked = await session.fork()

        assert forked.session_id != session.session_id
        assert "original-session:" in forked.session_id

    @pytest.mark.asyncio
    async def test_fork_copies_history(self, session):
        """Test that fork copies conversation history."""
        forked = await session.fork()

        assert len(forked.get_history()) == len(session.get_history())
        assert forked.get_history()[0].content == session.get_history()[0].content

    @pytest.mark.asyncio
    async def test_fork_copies_context(self, session):
        """Test that fork copies session context."""
        forked = await session.fork()

        assert forked.get_context() == session.get_context()

    @pytest.mark.asyncio
    async def test_fork_with_custom_branch_name(self, session):
        """Test fork with custom branch name."""
        forked = await session.fork(branch_name="experiment-1")

        assert forked.session_id == "original-session:experiment-1"

    @pytest.mark.asyncio
    async def test_fork_independence(self, session):
        """Test that forked session is independent."""
        forked = await session.fork()

        # Modify forked session
        forked._history.append(
            Message(role="user", content="New message", timestamp=time.time())
        )

        # Original should be unchanged
        assert len(session._history) == 2
        assert len(forked._history) == 3


class TestSessionClose:
    """Tests for session close functionality."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock client."""
        return MagicMock()

    @pytest.fixture
    def config(self):
        """Create test config."""
        return ClaudeSDKConfig(api_key="test-key")

    @pytest.fixture
    def session(self, mock_anthropic_client, config):
        """Create a test session."""
        return Session(
            session_id="close-test",
            client=mock_anthropic_client,
            config=config,
            tools=[],
            hooks=[],
            mcp_servers=[],
        )

    @pytest.mark.asyncio
    async def test_close_marks_session_closed(self, session):
        """Test that close marks session as closed."""
        await session.close()

        assert session.is_closed is True

    @pytest.mark.asyncio
    async def test_close_twice_is_safe(self, session):
        """Test that closing twice is safe."""
        await session.close()
        await session.close()

        assert session.is_closed is True

    @pytest.mark.asyncio
    async def test_close_triggers_hook(self, session):
        """Test that close triggers session end hook."""
        mock_hook = MagicMock()
        mock_hook.on_session_end = AsyncMock()
        session._hooks = [mock_hook]

        await session.close()

        mock_hook.on_session_end.assert_called_once_with("close-test")


class TestSessionContextManagement:
    """Tests for session context management."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock client."""
        return MagicMock()

    @pytest.fixture
    def config(self):
        """Create test config."""
        return ClaudeSDKConfig(api_key="test-key")

    @pytest.fixture
    def session(self, mock_anthropic_client, config):
        """Create a test session."""
        return Session(
            session_id="test-session",
            client=mock_anthropic_client,
            config=config,
            tools=[],
            hooks=[],
            mcp_servers=[],
            context={"project": "test", "environment": "dev"},
        )

    def test_get_context(self, session):
        """Test getting session context."""
        context = session.get_context()

        assert context["project"] == "test"
        assert context["environment"] == "dev"

    def test_get_context_returns_copy(self, session):
        """Test that get_context returns a copy."""
        context = session.get_context()
        context["new_key"] = "new_value"

        # Original should be unchanged
        assert "new_key" not in session.get_context()

    def test_add_context(self, session):
        """Test adding context value."""
        session.add_context("feature_flag", True)

        assert session.get_context()["feature_flag"] is True
        assert session.get_context()["project"] == "test"  # Preserved

