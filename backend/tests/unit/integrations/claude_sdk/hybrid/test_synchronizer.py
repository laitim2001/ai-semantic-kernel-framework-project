"""Unit tests for Context Synchronizer.

Sprint 50: S50-4 - Context Synchronizer (8 pts)
Tests for ContextSynchronizer class.
"""

import time

import pytest

from src.integrations.claude_sdk.hybrid.synchronizer import (
    ConflictResolution,
    ContextDiff,
    ContextFormat,
    ContextSnapshot,
    ContextState,
    ContextSynchronizer,
    Message,
    SyncDirection,
    create_synchronizer,
)
from src.integrations.claude_sdk.hybrid.types import HybridSessionConfig, ToolCall


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def synchronizer():
    """Create a default ContextSynchronizer."""
    return ContextSynchronizer()


@pytest.fixture
def synchronizer_with_config():
    """Create a synchronizer with custom config."""
    config = HybridSessionConfig(
        max_sync_messages=10,
        sync_context=True,
    )
    return ContextSynchronizer(config=config)


@pytest.fixture
def context_state():
    """Create a sample context state."""
    state = ContextState(
        context_id="test-context-1",
        system_prompt="You are a helpful assistant.",
        metadata={"user_id": "user-123"},
    )
    state.add_message("user", "Hello!")
    state.add_message("assistant", "Hi there! How can I help?")
    return state


@pytest.fixture
def claude_format_data():
    """Sample data in Claude SDK format."""
    return {
        "messages": [
            {"role": "user", "content": "<system>You are a helpful assistant.</system>"},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        "tools": [
            {
                "name": "search",
                "description": "Search the web",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
            }
        ],
        "metadata": {"session": "test"},
    }


@pytest.fixture
def ms_agent_format_data():
    """Sample data in MS Agent Framework format."""
    return {
        "chat_history": [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        "system_message": "You are a helpful assistant.",
        "functions": [
            {
                "name": "search",
                "description": "Search the web",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            }
        ],
        "context": {"session": "test"},
    }


# ============================================================================
# Message Tests
# ============================================================================


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.message_id is not None
        assert msg.timestamp > 0
        assert msg.framework_source == "claude_sdk"

    def test_message_with_tool_calls(self):
        """Test message with tool calls."""
        tool_call = ToolCall(name="search", arguments={"query": "test"})
        msg = Message(
            role="assistant",
            content="Searching...",
            tool_calls=[tool_call],
        )

        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "search"

    def test_message_to_dict(self):
        """Test message serialization."""
        msg = Message(role="user", content="Hello", metadata={"key": "value"})
        data = msg.to_dict()

        assert data["role"] == "user"
        assert data["content"] == "Hello"
        assert data["metadata"]["key"] == "value"

    def test_message_from_dict(self):
        """Test message deserialization."""
        data = {
            "role": "assistant",
            "content": "Hello back",
            "metadata": {"source": "test"},
            "tool_calls": [{"name": "tool1", "arguments": {"arg": "val"}}],
        }
        msg = Message.from_dict(data)

        assert msg.role == "assistant"
        assert msg.content == "Hello back"
        assert msg.metadata["source"] == "test"
        assert len(msg.tool_calls) == 1


# ============================================================================
# ContextState Tests
# ============================================================================


class TestContextState:
    """Tests for ContextState dataclass."""

    def test_context_creation(self):
        """Test creating context state."""
        context = ContextState()

        assert context.context_id is not None
        assert len(context.messages) == 0
        assert context.version == 1

    def test_add_message(self):
        """Test adding messages."""
        context = ContextState()
        msg = context.add_message("user", "Hello")

        assert len(context.messages) == 1
        assert context.messages[0].content == "Hello"
        assert msg.role == "user"

    def test_add_message_updates_version(self):
        """Test that adding message updates version."""
        context = ContextState()
        initial_version = context.version

        context.add_message("user", "Test")

        assert context.version == initial_version + 1

    def test_compute_hash(self):
        """Test hash computation."""
        context = ContextState()
        context.add_message("user", "Hello")

        hash1 = context.compute_hash()
        context.add_message("assistant", "Hi")
        hash2 = context.compute_hash()

        assert hash1 != hash2

    def test_has_changed(self):
        """Test change detection."""
        context = ContextState()
        context.update_hash()

        assert not context.has_changed()

        context.messages.append(Message(role="user", content="New"))

        assert context.has_changed()

    def test_to_dict(self):
        """Test context serialization."""
        context = ContextState(
            context_id="test-1",
            system_prompt="System prompt",
            metadata={"key": "value"},
        )
        context.add_message("user", "Hello")

        data = context.to_dict()

        assert data["context_id"] == "test-1"
        assert data["system_prompt"] == "System prompt"
        assert len(data["messages"]) == 1

    def test_from_dict(self):
        """Test context deserialization."""
        data = {
            "context_id": "test-2",
            "messages": [{"role": "user", "content": "Hi"}],
            "system_prompt": "Be helpful",
            "metadata": {"test": True},
            "version": 5,
        }
        context = ContextState.from_dict(data)

        assert context.context_id == "test-2"
        assert context.system_prompt == "Be helpful"
        assert len(context.messages) == 1
        # from_dict calls update_hash which increments version
        assert context.version >= 5


# ============================================================================
# ContextDiff Tests
# ============================================================================


class TestContextDiff:
    """Tests for ContextDiff dataclass."""

    def test_empty_diff(self):
        """Test empty diff."""
        diff = ContextDiff()

        assert diff.is_empty()
        assert diff.summary() == "no changes"

    def test_diff_with_changes(self):
        """Test diff with various changes."""
        diff = ContextDiff(
            added_messages=[Message(role="user", content="New")],
            removed_messages=[Message(role="user", content="Old")],
            metadata_changes={"key": ("old", "new")},
            system_prompt_changed=True,
        )

        assert not diff.is_empty()
        summary = diff.summary()
        assert "+1 messages" in summary
        assert "-1 messages" in summary
        assert "metadata" in summary
        assert "system prompt" in summary


# ============================================================================
# ContextSnapshot Tests
# ============================================================================


class TestContextSnapshot:
    """Tests for ContextSnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test creating snapshot."""
        context = ContextState()
        context.add_message("user", "Hello")

        snapshot = ContextSnapshot(
            context_id=context.context_id,
            state=context,
            label="test-snapshot",
        )

        assert snapshot.snapshot_id is not None
        assert snapshot.label == "test-snapshot"
        assert snapshot.state is not None

    def test_snapshot_restore(self):
        """Test restoring from snapshot."""
        context = ContextState()
        context.add_message("user", "Original message")

        snapshot = ContextSnapshot(
            context_id=context.context_id,
            state=ContextState.from_dict(context.to_dict()),
        )

        # Modify original
        context.add_message("assistant", "New message")

        # Restore
        restored = snapshot.restore()

        assert len(restored.messages) == 1
        assert restored.messages[0].content == "Original message"

    def test_restore_empty_snapshot(self):
        """Test restoring empty snapshot raises error."""
        snapshot = ContextSnapshot()

        with pytest.raises(ValueError, match="no state"):
            snapshot.restore()


# ============================================================================
# ContextSynchronizer Initialization Tests
# ============================================================================


class TestContextSynchronizerInit:
    """Tests for ContextSynchronizer initialization."""

    def test_default_init(self):
        """Test default initialization."""
        sync = ContextSynchronizer()

        assert sync.context_count == 0
        assert sync.sync_count == 0
        assert sync.config is not None

    def test_custom_config(self):
        """Test initialization with custom config."""
        config = HybridSessionConfig(max_sync_messages=5)
        sync = ContextSynchronizer(config=config)

        assert sync.config.max_sync_messages == 5

    def test_custom_conflict_resolution(self):
        """Test initialization with custom conflict resolution."""
        sync = ContextSynchronizer(
            conflict_resolution=ConflictResolution.SOURCE_WINS
        )

        assert sync._conflict_resolution == ConflictResolution.SOURCE_WINS


# ============================================================================
# Context Management Tests
# ============================================================================


class TestContextManagement:
    """Tests for context management."""

    def test_create_context(self, synchronizer):
        """Test creating context."""
        context = synchronizer.create_context()

        assert context is not None
        assert synchronizer.context_count == 1

    def test_create_context_with_id(self, synchronizer):
        """Test creating context with custom ID."""
        context = synchronizer.create_context(context_id="custom-id")

        assert context.context_id == "custom-id"

    def test_create_context_with_metadata(self, synchronizer):
        """Test creating context with metadata."""
        context = synchronizer.create_context(
            metadata={"user": "test-user"}
        )

        assert context.metadata["user"] == "test-user"

    def test_get_context(self, synchronizer):
        """Test getting context."""
        created = synchronizer.create_context(context_id="test-get")
        retrieved = synchronizer.get_context("test-get")

        assert retrieved is created

    def test_get_nonexistent_context(self, synchronizer):
        """Test getting non-existent context."""
        result = synchronizer.get_context("nonexistent")

        assert result is None

    def test_remove_context(self, synchronizer):
        """Test removing context."""
        synchronizer.create_context(context_id="to-remove")

        result = synchronizer.remove_context("to-remove")

        assert result is True
        assert synchronizer.context_count == 0

    def test_remove_nonexistent_context(self, synchronizer):
        """Test removing non-existent context."""
        result = synchronizer.remove_context("nonexistent")

        assert result is False


# ============================================================================
# Format Conversion Tests
# ============================================================================


class TestFormatConversion:
    """Tests for format conversion."""

    def test_convert_to_claude(self, synchronizer, context_state):
        """Test converting to Claude format."""
        result = synchronizer.convert_to_claude(context_state)

        assert "messages" in result
        assert "tools" in result
        assert len(result["messages"]) > 0

    def test_convert_to_ms_agent(self, synchronizer, context_state):
        """Test converting to MS Agent format."""
        result = synchronizer.convert_to_ms_agent(context_state)

        assert "chat_history" in result
        assert "system_message" in result
        assert "functions" in result

    def test_convert_from_claude(self, synchronizer, claude_format_data):
        """Test converting from Claude format."""
        context = synchronizer.convert_from_claude(claude_format_data)

        assert context.current_framework == "claude_sdk"
        assert len(context.messages) > 0
        assert len(context.tools) == 1

    def test_convert_from_ms_agent(self, synchronizer, ms_agent_format_data):
        """Test converting from MS Agent format."""
        context = synchronizer.convert_from_ms_agent(ms_agent_format_data)

        assert context.current_framework == "microsoft_agent_framework"
        assert context.system_prompt == "You are a helpful assistant."
        assert len(context.messages) == 2

    def test_round_trip_conversion(self, synchronizer, context_state):
        """Test round-trip conversion preserves data."""
        # To Claude and back
        claude_data = synchronizer.convert_to_claude(context_state)
        restored = synchronizer.convert_from_claude(claude_data)

        assert len(restored.messages) == len(context_state.messages)


# ============================================================================
# Diff Tests
# ============================================================================


class TestDiff:
    """Tests for context diffing."""

    def test_diff_identical(self, synchronizer):
        """Test diff of identical contexts."""
        ctx1 = synchronizer.create_context()
        ctx1.add_message("user", "Hello")

        ctx2 = ContextState.from_dict(ctx1.to_dict())

        diff = synchronizer.diff(ctx1, ctx2)

        assert diff.is_empty()

    def test_diff_added_messages(self, synchronizer):
        """Test diff with added messages."""
        ctx1 = synchronizer.create_context()
        ctx1.add_message("user", "Hello")

        ctx2 = ContextState.from_dict(ctx1.to_dict())
        ctx2.add_message("assistant", "Hi there!")

        diff = synchronizer.diff(ctx1, ctx2)

        assert len(diff.added_messages) == 1
        assert diff.added_messages[0].content == "Hi there!"

    def test_diff_removed_messages(self, synchronizer):
        """Test diff with removed messages."""
        ctx1 = synchronizer.create_context()
        msg = ctx1.add_message("user", "Hello")
        ctx1.add_message("assistant", "Hi")

        ctx2 = ContextState.from_dict(ctx1.to_dict())
        ctx2.messages = [m for m in ctx2.messages if m.message_id != msg.message_id]

        diff = synchronizer.diff(ctx1, ctx2)

        assert len(diff.removed_messages) == 1

    def test_diff_metadata_changes(self, synchronizer):
        """Test diff with metadata changes."""
        ctx1 = synchronizer.create_context(metadata={"key": "old"})
        ctx2 = ContextState.from_dict(ctx1.to_dict())
        ctx2.metadata["key"] = "new"

        diff = synchronizer.diff(ctx1, ctx2)

        assert "key" in diff.metadata_changes
        assert diff.metadata_changes["key"] == ("old", "new")

    def test_diff_system_prompt_change(self, synchronizer):
        """Test diff with system prompt change."""
        ctx1 = synchronizer.create_context(system_prompt="Old prompt")
        ctx2 = ContextState.from_dict(ctx1.to_dict())
        ctx2.system_prompt = "New prompt"

        diff = synchronizer.diff(ctx1, ctx2)

        assert diff.system_prompt_changed
        assert diff.old_system_prompt == "Old prompt"
        assert diff.new_system_prompt == "New prompt"


# ============================================================================
# Merge Tests
# ============================================================================


class TestMerge:
    """Tests for context merging."""

    def test_merge_messages(self, synchronizer):
        """Test merging messages from two contexts."""
        ctx1 = synchronizer.create_context()
        ctx1.add_message("user", "Message from ctx1")

        ctx2 = synchronizer.create_context()
        ctx2.add_message("assistant", "Message from ctx2")

        merged = synchronizer.merge(ctx1, ctx2)

        assert len(merged.messages) == 2

    def test_merge_latest_wins(self, synchronizer):
        """Test merge with LATEST_WINS resolution."""
        ctx1 = synchronizer.create_context(system_prompt="Old prompt")
        ctx1.last_updated = time.time() - 100

        ctx2 = ContextState.from_dict(ctx1.to_dict())
        ctx2.system_prompt = "New prompt"
        ctx2.last_updated = time.time()

        merged = synchronizer.merge(ctx1, ctx2, ConflictResolution.LATEST_WINS)

        assert merged.system_prompt == "New prompt"

    def test_merge_source_wins(self, synchronizer):
        """Test merge with SOURCE_WINS resolution."""
        ctx1 = synchronizer.create_context(metadata={"key": "source"})
        ctx2 = synchronizer.create_context(metadata={"key": "target"})

        merged = synchronizer.merge(ctx1, ctx2, ConflictResolution.SOURCE_WINS)

        assert merged.metadata["key"] == "source"

    def test_merge_target_wins(self, synchronizer):
        """Test merge with TARGET_WINS resolution."""
        ctx1 = synchronizer.create_context(system_prompt="Source")
        ctx2 = synchronizer.create_context(system_prompt="Target")

        merged = synchronizer.merge(ctx1, ctx2, ConflictResolution.TARGET_WINS)

        assert merged.system_prompt == "Target"

    def test_merge_tools_union(self, synchronizer):
        """Test that tools are merged as union."""
        ctx1 = synchronizer.create_context()
        ctx1.tools = [{"name": "tool1"}]

        ctx2 = synchronizer.create_context()
        ctx2.tools = [{"name": "tool2"}]

        merged = synchronizer.merge(ctx1, ctx2)

        assert len(merged.tools) == 2


# ============================================================================
# Sync Tests
# ============================================================================


class TestSync:
    """Tests for context synchronization."""

    def test_sync_bidirectional(self, synchronizer):
        """Test bidirectional sync."""
        ctx1 = synchronizer.create_context(context_id="ctx1")
        ctx1.add_message("user", "From ctx1")

        ctx2 = synchronizer.create_context(context_id="ctx2")
        ctx2.add_message("assistant", "From ctx2")

        diff = synchronizer.sync("ctx1", "ctx2", SyncDirection.BIDIRECTIONAL)

        assert not diff.is_empty()
        assert synchronizer.sync_count == 1

    def test_sync_claude_to_ms(self, synchronizer):
        """Test sync from Claude to MS."""
        ctx_claude = synchronizer.create_context(context_id="claude-ctx")
        ctx_claude.add_message("user", "Claude message")
        ctx_claude.current_framework = "claude_sdk"

        ctx_ms = synchronizer.create_context(context_id="ms-ctx")
        ctx_ms.current_framework = "microsoft_agent_framework"

        diff = synchronizer.sync("claude-ctx", "ms-ctx", SyncDirection.CLAUDE_TO_MS)

        # diff shows source (claude) vs target (ms) differences
        # source has message but target doesn't, so it's in removed_messages
        assert not diff.is_empty()

        # Verify sync result: ms-ctx should have messages from claude-ctx
        ms_ctx = synchronizer.get_context("ms-ctx")
        assert len(ms_ctx.messages) > 0
        assert ms_ctx.messages[0].content == "Claude message"

    def test_sync_nonexistent_source(self, synchronizer):
        """Test sync with non-existent source."""
        synchronizer.create_context(context_id="target")

        with pytest.raises(ValueError, match="Source context not found"):
            synchronizer.sync("nonexistent", "target")

    def test_sync_nonexistent_target(self, synchronizer):
        """Test sync with non-existent target."""
        synchronizer.create_context(context_id="source")

        with pytest.raises(ValueError, match="Target context not found"):
            synchronizer.sync("source", "nonexistent")

    def test_sync_no_changes(self, synchronizer):
        """Test sync when no changes needed."""
        ctx = synchronizer.create_context(context_id="ctx1")

        # Create identical context
        synchronizer._contexts["ctx2"] = ContextState.from_dict(ctx.to_dict())
        synchronizer._contexts["ctx2"].context_id = "ctx2"

        diff = synchronizer.sync("ctx1", "ctx2")

        assert diff.is_empty()


# ============================================================================
# Snapshot Tests
# ============================================================================


class TestSnapshots:
    """Tests for snapshot management."""

    def test_create_snapshot(self, synchronizer):
        """Test creating snapshot."""
        ctx = synchronizer.create_context(context_id="test-ctx")
        ctx.add_message("user", "Hello")

        snapshot = synchronizer.create_snapshot("test-ctx", label="before-change")

        assert snapshot.label == "before-change"
        assert snapshot.context_id == "test-ctx"

    def test_create_snapshot_nonexistent(self, synchronizer):
        """Test creating snapshot for non-existent context."""
        with pytest.raises(ValueError, match="Context not found"):
            synchronizer.create_snapshot("nonexistent")

    def test_restore_snapshot(self, synchronizer):
        """Test restoring snapshot."""
        ctx = synchronizer.create_context(context_id="test-ctx")
        ctx.add_message("user", "Original")

        snapshot = synchronizer.create_snapshot("test-ctx")

        ctx.add_message("assistant", "Added later")
        assert len(ctx.messages) == 2

        restored = synchronizer.restore_snapshot(snapshot.snapshot_id)

        assert len(restored.messages) == 1

    def test_restore_nonexistent_snapshot(self, synchronizer):
        """Test restoring non-existent snapshot."""
        with pytest.raises(ValueError, match="Snapshot not found"):
            synchronizer.restore_snapshot("nonexistent")

    def test_get_snapshots(self, synchronizer):
        """Test getting all snapshots for context."""
        ctx = synchronizer.create_context(context_id="test-ctx")
        synchronizer.create_snapshot("test-ctx", label="snap1")
        synchronizer.create_snapshot("test-ctx", label="snap2")

        snapshots = synchronizer.get_snapshots("test-ctx")

        assert len(snapshots) == 2


# ============================================================================
# Sync Listener Tests
# ============================================================================


class TestSyncListeners:
    """Tests for sync listeners."""

    def test_add_sync_listener(self, synchronizer):
        """Test adding sync listener."""
        events = []

        def listener(context, direction):
            events.append((context.context_id, direction))

        synchronizer.add_sync_listener(listener)

        ctx1 = synchronizer.create_context(context_id="ctx1")
        ctx2 = synchronizer.create_context(context_id="ctx2")
        ctx1.add_message("user", "Hello")

        synchronizer.sync("ctx1", "ctx2")

        assert len(events) == 1
        assert events[0][1] == SyncDirection.BIDIRECTIONAL

    def test_remove_sync_listener(self, synchronizer):
        """Test removing sync listener."""
        events = []

        def listener(context, direction):
            events.append(context.context_id)

        synchronizer.add_sync_listener(listener)
        synchronizer.remove_sync_listener(listener)

        ctx1 = synchronizer.create_context(context_id="ctx1")
        ctx2 = synchronizer.create_context(context_id="ctx2")
        ctx1.add_message("user", "Hello")

        synchronizer.sync("ctx1", "ctx2")

        assert len(events) == 0


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateSynchronizer:
    """Tests for create_synchronizer factory function."""

    def test_create_default(self):
        """Test creating default synchronizer."""
        sync = create_synchronizer()

        assert isinstance(sync, ContextSynchronizer)
        assert sync.context_count == 0

    def test_create_with_config(self):
        """Test creating synchronizer with config."""
        config = HybridSessionConfig(max_sync_messages=5)
        sync = create_synchronizer(config=config)

        assert sync.config.max_sync_messages == 5

    def test_create_with_conflict_resolution(self):
        """Test creating synchronizer with conflict resolution."""
        sync = create_synchronizer(
            conflict_resolution=ConflictResolution.MERGE
        )

        assert sync._conflict_resolution == ConflictResolution.MERGE
