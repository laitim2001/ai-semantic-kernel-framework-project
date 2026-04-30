# =============================================================================
# IPA Platform - Shared State Handler Tests
# =============================================================================
# Sprint 60: AG-UI Advanced Features
# S60-2: Shared State (8 pts)
#
# Tests for SharedStateHandler, StateSyncManager, and state management.
# =============================================================================

import pytest
from unittest.mock import MagicMock, patch

from src.integrations.ag_ui.features.advanced.shared_state import (
    DiffOperation,
    ConflictResolutionStrategy,
    StateDiff,
    StateVersion,
    StateConflict,
    StateSyncManager,
    SharedStateHandler,
    create_shared_state_handler,
)


class TestDiffOperation:
    """Tests for DiffOperation enum."""

    def test_add_operation(self):
        """Test ADD operation value."""
        assert DiffOperation.ADD.value == "add"

    def test_remove_operation(self):
        """Test REMOVE operation value."""
        assert DiffOperation.REMOVE.value == "remove"

    def test_replace_operation(self):
        """Test REPLACE operation value."""
        assert DiffOperation.REPLACE.value == "replace"

    def test_move_operation(self):
        """Test MOVE operation value."""
        assert DiffOperation.MOVE.value == "move"


class TestConflictResolutionStrategy:
    """Tests for ConflictResolutionStrategy enum."""

    def test_server_wins(self):
        """Test SERVER_WINS strategy."""
        assert ConflictResolutionStrategy.SERVER_WINS.value == "server_wins"

    def test_client_wins(self):
        """Test CLIENT_WINS strategy."""
        assert ConflictResolutionStrategy.CLIENT_WINS.value == "client_wins"

    def test_last_write_wins(self):
        """Test LAST_WRITE_WINS strategy."""
        assert ConflictResolutionStrategy.LAST_WRITE_WINS.value == "last_write_wins"

    def test_merge(self):
        """Test MERGE strategy."""
        assert ConflictResolutionStrategy.MERGE.value == "merge"

    def test_manual(self):
        """Test MANUAL strategy."""
        assert ConflictResolutionStrategy.MANUAL.value == "manual"


class TestStateDiff:
    """Tests for StateDiff dataclass."""

    def test_basic_diff(self):
        """Test basic diff creation."""
        diff = StateDiff(
            path="user.name",
            operation=DiffOperation.REPLACE,
            old_value="John",
            new_value="Jane",
        )
        assert diff.path == "user.name"
        assert diff.operation == DiffOperation.REPLACE
        assert diff.old_value == "John"
        assert diff.new_value == "Jane"

    def test_add_diff(self):
        """Test ADD operation diff."""
        diff = StateDiff(
            path="user.email",
            operation=DiffOperation.ADD,
            new_value="test@example.com",
        )
        assert diff.operation == DiffOperation.ADD
        assert diff.old_value is None
        assert diff.new_value == "test@example.com"

    def test_remove_diff(self):
        """Test REMOVE operation diff."""
        diff = StateDiff(
            path="user.phone",
            operation=DiffOperation.REMOVE,
            old_value="123-456",
        )
        assert diff.operation == DiffOperation.REMOVE
        assert diff.old_value == "123-456"
        assert diff.new_value is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        diff = StateDiff(
            path="count",
            operation=DiffOperation.REPLACE,
            old_value=1,
            new_value=2,
        )
        result = diff.to_dict()
        assert result["path"] == "count"
        assert result["op"] == "replace"
        assert result["oldValue"] == 1
        assert result["newValue"] == 2
        assert "timestamp" in result

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "path": "status",
            "op": "replace",
            "oldValue": "pending",
            "newValue": "active",
            "timestamp": 1704456000.0,
        }
        diff = StateDiff.from_dict(data)
        assert diff.path == "status"
        assert diff.operation == DiffOperation.REPLACE
        assert diff.old_value == "pending"
        assert diff.new_value == "active"
        assert diff.timestamp == 1704456000.0


class TestStateVersion:
    """Tests for StateVersion dataclass."""

    def test_basic_version(self):
        """Test basic version creation."""
        version = StateVersion(version=1)
        assert version.version == 1
        assert version.timestamp > 0
        assert version.checksum is None

    def test_version_with_checksum(self):
        """Test version with checksum."""
        version = StateVersion(
            version=5,
            timestamp=1704456000.0,
            checksum="abc123",
        )
        assert version.version == 5
        assert version.timestamp == 1704456000.0
        assert version.checksum == "abc123"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        version = StateVersion(version=3, timestamp=1704456000.0)
        result = version.to_dict()
        assert result["version"] == 3
        assert result["timestamp"] == 1704456000.0
        assert "checksum" not in result

    def test_to_dict_with_checksum(self):
        """Test to_dict includes checksum when present."""
        version = StateVersion(version=2, checksum="hash123")
        result = version.to_dict()
        assert result["checksum"] == "hash123"


class TestStateConflict:
    """Tests for StateConflict dataclass."""

    def test_basic_conflict(self):
        """Test basic conflict creation."""
        conflict = StateConflict(
            path="user.name",
            server_value="Server",
            client_value="Client",
        )
        assert conflict.path == "user.name"
        assert conflict.server_value == "Server"
        assert conflict.client_value == "Client"
        assert conflict.resolution is None
        assert conflict.resolved_value is None

    def test_resolved_conflict(self):
        """Test conflict with resolution."""
        conflict = StateConflict(
            path="count",
            server_value=10,
            client_value=15,
            resolution=ConflictResolutionStrategy.SERVER_WINS,
            resolved_value=10,
        )
        assert conflict.resolution == ConflictResolutionStrategy.SERVER_WINS
        assert conflict.resolved_value == 10

    def test_to_dict(self):
        """Test conversion to dictionary."""
        conflict = StateConflict(
            path="status",
            server_value="active",
            client_value="inactive",
            resolution=ConflictResolutionStrategy.LAST_WRITE_WINS,
            resolved_value="active",
        )
        result = conflict.to_dict()
        assert result["path"] == "status"
        assert result["serverValue"] == "active"
        assert result["clientValue"] == "inactive"
        assert result["resolution"] == "last_write_wins"
        assert result["resolvedValue"] == "active"


class TestStateSyncManager:
    """Tests for StateSyncManager class."""

    @pytest.fixture
    def manager(self):
        """Create a StateSyncManager instance."""
        return StateSyncManager()

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.conflict_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS

    def test_custom_strategy(self):
        """Test manager with custom conflict strategy."""
        manager = StateSyncManager(conflict_strategy=ConflictResolutionStrategy.SERVER_WINS)
        assert manager.conflict_strategy == ConflictResolutionStrategy.SERVER_WINS

    def test_diff_state_no_changes(self, manager):
        """Test diffing identical states."""
        state = {"name": "test", "count": 1}
        diffs = manager.diff_state(state, state)
        assert len(diffs) == 0

    def test_diff_state_add_key(self, manager):
        """Test diffing with added key."""
        old = {"name": "test"}
        new = {"name": "test", "count": 1}
        diffs = manager.diff_state(old, new)
        assert len(diffs) == 1
        assert diffs[0].operation == DiffOperation.ADD
        assert diffs[0].path == "count"
        assert diffs[0].new_value == 1

    def test_diff_state_remove_key(self, manager):
        """Test diffing with removed key."""
        old = {"name": "test", "count": 1}
        new = {"name": "test"}
        diffs = manager.diff_state(old, new)
        assert len(diffs) == 1
        assert diffs[0].operation == DiffOperation.REMOVE
        assert diffs[0].path == "count"
        assert diffs[0].old_value == 1

    def test_diff_state_replace_value(self, manager):
        """Test diffing with changed value."""
        old = {"count": 1}
        new = {"count": 2}
        diffs = manager.diff_state(old, new)
        assert len(diffs) == 1
        assert diffs[0].operation == DiffOperation.REPLACE
        assert diffs[0].old_value == 1
        assert diffs[0].new_value == 2

    def test_diff_state_nested(self, manager):
        """Test diffing nested objects."""
        old = {"user": {"name": "John", "age": 30}}
        new = {"user": {"name": "Jane", "age": 30}}
        diffs = manager.diff_state(old, new)
        assert len(diffs) == 1
        assert diffs[0].path == "user.name"
        assert diffs[0].old_value == "John"
        assert diffs[0].new_value == "Jane"

    def test_diff_state_multiple_changes(self, manager):
        """Test diffing with multiple changes."""
        old = {"a": 1, "b": 2, "c": 3}
        new = {"a": 1, "b": 5, "d": 4}
        diffs = manager.diff_state(old, new)
        # Should have: c removed, b replaced, d added
        assert len(diffs) == 3
        paths = {d.path for d in diffs}
        assert paths == {"b", "c", "d"}

    def test_apply_diffs_add(self, manager):
        """Test applying ADD diff."""
        state = {"name": "test"}
        diffs = [
            StateDiff(path="count", operation=DiffOperation.ADD, new_value=1),
        ]
        result = manager.apply_diffs(state, diffs)
        assert result == {"name": "test", "count": 1}
        # Original should be unchanged
        assert "count" not in state

    def test_apply_diffs_remove(self, manager):
        """Test applying REMOVE diff."""
        state = {"name": "test", "count": 1}
        diffs = [
            StateDiff(path="count", operation=DiffOperation.REMOVE, old_value=1),
        ]
        result = manager.apply_diffs(state, diffs)
        assert result == {"name": "test"}

    def test_apply_diffs_replace(self, manager):
        """Test applying REPLACE diff."""
        state = {"count": 1}
        diffs = [
            StateDiff(path="count", operation=DiffOperation.REPLACE, old_value=1, new_value=5),
        ]
        result = manager.apply_diffs(state, diffs)
        assert result == {"count": 5}

    def test_apply_diffs_nested(self, manager):
        """Test applying diff to nested path."""
        state = {"user": {"name": "John"}}
        diffs = [
            StateDiff(path="user.name", operation=DiffOperation.REPLACE, new_value="Jane"),
        ]
        result = manager.apply_diffs(state, diffs)
        assert result == {"user": {"name": "Jane"}}

    def test_merge_state_no_conflict(self, manager):
        """Test merging states without conflict."""
        server = {"a": 1, "b": 2}
        client = {"c": 3, "d": 4}
        merged, conflicts = manager.merge_state(server, client)
        assert merged == {"a": 1, "b": 2, "c": 3, "d": 4}
        assert len(conflicts) == 0

    def test_merge_state_with_conflict(self, manager):
        """Test merging states with conflict."""
        server = {"name": "Server"}
        client = {"name": "Client"}
        merged, conflicts = manager.merge_state(server, client)
        assert len(conflicts) == 1
        assert conflicts[0].path == "name"

    def test_conflict_resolution_server_wins(self):
        """Test SERVER_WINS conflict resolution."""
        manager = StateSyncManager(conflict_strategy=ConflictResolutionStrategy.SERVER_WINS)
        server = {"value": "server"}
        client = {"value": "client"}
        merged, conflicts = manager.merge_state(server, client)
        assert merged["value"] == "server"

    def test_conflict_resolution_client_wins(self):
        """Test CLIENT_WINS conflict resolution."""
        manager = StateSyncManager(conflict_strategy=ConflictResolutionStrategy.CLIENT_WINS)
        server = {"value": "server"}
        client = {"value": "client"}
        merged, conflicts = manager.merge_state(server, client)
        assert merged["value"] == "client"

    def test_conflict_resolution_merge_lists(self):
        """Test MERGE strategy with lists."""
        manager = StateSyncManager(conflict_strategy=ConflictResolutionStrategy.MERGE)
        server = {"items": [1, 2, 3]}
        client = {"items": [3, 4, 5]}
        merged, conflicts = manager.merge_state(server, client)
        # Should be union of lists
        assert set(merged["items"]) == {1, 2, 3, 4, 5}


class TestSharedStateHandler:
    """Tests for SharedStateHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a SharedStateHandler instance."""
        return SharedStateHandler(max_history=10)

    def test_initialization(self, handler):
        """Test handler initialization."""
        assert handler.sync_manager is not None

    def test_get_state_empty(self, handler):
        """Test getting state for unknown thread."""
        state = handler.get_state("unknown-thread")
        assert state is None

    def test_set_state(self, handler):
        """Test setting state."""
        handler.set_state("thread-1", {"count": 1})
        state = handler.get_state("thread-1")
        assert state == {"count": 1}

    def test_set_state_version(self, handler):
        """Test version increment on set_state."""
        handler.set_state("thread-1", {"count": 1})
        v1 = handler.get_version("thread-1")
        assert v1.version == 1

        handler.set_state("thread-1", {"count": 2})
        v2 = handler.get_version("thread-1")
        assert v2.version == 2

    def test_set_state_emit_event(self, handler):
        """Test set_state with emit_event."""
        event = handler.set_state(
            "thread-1",
            {"count": 1},
            emit_event=True,
            run_id="run-123",
        )
        assert event is not None
        assert event.snapshot == {"count": 1}

    def test_update_state_merge(self, handler):
        """Test update_state with merge."""
        handler.set_state("thread-1", {"a": 1, "b": 2})
        event = handler.update_state("thread-1", "run-1", {"b": 5, "c": 3})
        state = handler.get_state("thread-1")
        assert state == {"a": 1, "b": 5, "c": 3}

    def test_update_state_replace(self, handler):
        """Test update_state without merge."""
        handler.set_state("thread-1", {"a": 1, "b": 2})
        event = handler.update_state("thread-1", "run-1", {"c": 3}, merge=False)
        state = handler.get_state("thread-1")
        assert state == {"c": 3}

    def test_emit_state_snapshot(self, handler):
        """Test emitting state snapshot."""
        handler.set_state("thread-1", {"data": "test"})
        event = handler.emit_state_snapshot("thread-1", "run-1")
        assert event.snapshot == {"data": "test"}
        assert event.metadata["threadId"] == "thread-1"
        assert event.metadata["runId"] == "run-1"

    def test_emit_state_delta(self, handler):
        """Test emitting state delta."""
        handler.set_state("thread-1", {"count": 1})
        diffs = [
            StateDiff(path="count", operation=DiffOperation.REPLACE, new_value=2),
        ]
        event = handler.emit_state_delta("thread-1", "run-1", diffs)
        assert len(event.delta) == 1
        assert event.delta[0]["path"] == "count"

    def test_apply_client_update(self, handler):
        """Test applying client update."""
        handler.set_state("thread-1", {"a": 1})
        event, conflicts = handler.apply_client_update(
            "thread-1", "run-1", {"b": 2}
        )
        state = handler.get_state("thread-1")
        assert state == {"a": 1, "b": 2}

    def test_apply_client_update_with_conflict(self, handler):
        """Test applying client update with conflict."""
        handler.set_state("thread-1", {"value": "server"})
        event, conflicts = handler.apply_client_update(
            "thread-1", "run-1", {"value": "client"}
        )
        assert len(conflicts) == 1

    def test_get_state_at_version(self, handler):
        """Test getting state at specific version."""
        handler.set_state("thread-1", {"v": 1})
        handler.set_state("thread-1", {"v": 2})
        handler.set_state("thread-1", {"v": 3})

        # Get current version
        state = handler.get_state_at_version("thread-1", 3)
        assert state == {"v": 3}

        # Get historical version
        state = handler.get_state_at_version("thread-1", 1)
        assert state == {"v": 1}

    def test_rollback_to_version(self, handler):
        """Test rolling back to previous version."""
        handler.set_state("thread-1", {"v": 1})
        handler.set_state("thread-1", {"v": 2})
        handler.set_state("thread-1", {"v": 3})

        event = handler.rollback_to_version("thread-1", "run-1", 1)
        assert event is not None
        state = handler.get_state("thread-1")
        assert state == {"v": 1}

    def test_rollback_nonexistent_version(self, handler):
        """Test rollback to nonexistent version."""
        handler.set_state("thread-1", {"v": 1})
        event = handler.rollback_to_version("thread-1", "run-1", 999)
        assert event is None

    def test_clear_state(self, handler):
        """Test clearing state for a thread."""
        handler.set_state("thread-1", {"data": "test"})
        handler.clear_state("thread-1")
        assert handler.get_state("thread-1") is None
        assert handler.get_version("thread-1") is None

    def test_clear_all(self, handler):
        """Test clearing all state."""
        handler.set_state("thread-1", {"a": 1})
        handler.set_state("thread-2", {"b": 2})
        handler.clear_all()
        assert handler.get_state("thread-1") is None
        assert handler.get_state("thread-2") is None

    def test_history_limit(self):
        """Test history respects max_history limit."""
        handler = SharedStateHandler(max_history=3)
        for i in range(10):
            handler.set_state("thread-1", {"v": i})

        # After 10 set_state calls with max_history=3:
        # - Current: version 10, state={v:9}
        # - History: versions 7, 8, 9 (last 3 before current)
        assert handler.get_state_at_version("thread-1", 10) is not None  # Current
        assert handler.get_state_at_version("thread-1", 9) is not None   # History
        assert handler.get_state_at_version("thread-1", 8) is not None   # History
        assert handler.get_state_at_version("thread-1", 7) is not None   # History
        assert handler.get_state_at_version("thread-1", 6) is None       # Too old (pruned)


class TestCreateSharedStateHandler:
    """Tests for create_shared_state_handler factory function."""

    def test_create_handler_defaults(self):
        """Test creating handler with defaults."""
        handler = create_shared_state_handler()
        assert isinstance(handler, SharedStateHandler)
        assert handler.sync_manager.conflict_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS

    def test_create_handler_custom_strategy(self):
        """Test creating handler with custom strategy."""
        handler = create_shared_state_handler(
            conflict_strategy=ConflictResolutionStrategy.SERVER_WINS
        )
        assert handler.sync_manager.conflict_strategy == ConflictResolutionStrategy.SERVER_WINS

    def test_create_handler_custom_history(self):
        """Test creating handler with custom max_history."""
        handler = create_shared_state_handler(max_history=50)
        # Verify by checking behavior
        for i in range(60):
            handler.set_state("test", {"v": i})
        # Version 10 should still be in history (60 - 50 = 10)
        assert handler.get_state_at_version("test", 10) is not None
        # Version 5 should be gone (60 - 50 = 10, so 5 < 10)
        assert handler.get_state_at_version("test", 5) is None
