# =============================================================================
# IPA Platform - Shared State Handler
# =============================================================================
# Sprint 60: AG-UI Advanced Features
# S60-2: Shared State (8 pts)
#
# Provides bidirectional state synchronization between backend and frontend.
# Supports state snapshots, delta updates, and conflict resolution.
#
# Key Features:
#   - State snapshot emission for full state sync
#   - Delta updates for efficient incremental sync
#   - State diffing and merging algorithms
#   - Conflict detection and resolution
#   - Integration with AG-UI state events
#
# Dependencies:
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

import copy
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from src.integrations.ag_ui.events import (
    AGUIEventType,
    StateSnapshotEvent,
    StateDeltaEvent,
)

logger = logging.getLogger(__name__)


class DiffOperation(str, Enum):
    """Type of diff operation."""

    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"


class ConflictResolutionStrategy(str, Enum):
    """Strategy for resolving state conflicts."""

    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"
    MANUAL = "manual"


@dataclass
class StateDiff:
    """
    Represents a difference between two states.

    Attributes:
        path: JSON path to the changed value (e.g., "user.profile.name")
        operation: Type of operation
        old_value: Previous value (for replace/remove)
        new_value: New value (for add/replace)
        timestamp: When the diff was created
    """

    path: str
    operation: DiffOperation
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "path": self.path,
            "op": self.operation.value,
            "timestamp": self.timestamp,
        }
        if self.old_value is not None:
            result["oldValue"] = self.old_value
        if self.new_value is not None:
            result["newValue"] = self.new_value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateDiff":
        """Create from dictionary representation."""
        return cls(
            path=data.get("path", ""),
            operation=DiffOperation(data.get("op", "replace")),
            old_value=data.get("oldValue"),
            new_value=data.get("newValue"),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class StateVersion:
    """
    State version information.

    Attributes:
        version: Version number
        timestamp: When this version was created
        checksum: Optional checksum for integrity verification
    """

    version: int
    timestamp: float = field(default_factory=time.time)
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "version": self.version,
            "timestamp": self.timestamp,
        }
        if self.checksum:
            result["checksum"] = self.checksum
        return result


@dataclass
class StateConflict:
    """
    Represents a state conflict.

    Attributes:
        path: Path where conflict occurred
        server_value: Value on server
        client_value: Value from client
        resolution: How it was resolved
        resolved_value: Final resolved value
    """

    path: str
    server_value: Any
    client_value: Any
    resolution: Optional[ConflictResolutionStrategy] = None
    resolved_value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "path": self.path,
            "serverValue": self.server_value,
            "clientValue": self.client_value,
            "resolution": self.resolution.value if self.resolution else None,
            "resolvedValue": self.resolved_value,
        }


class StateSyncManager:
    """
    Manages state synchronization between server and clients.

    Provides algorithms for state diffing, merging, and conflict resolution.

    Example:
        >>> manager = StateSyncManager()
        >>> old_state = {"count": 1, "name": "test"}
        >>> new_state = {"count": 2, "name": "test", "active": True}
        >>> diffs = manager.diff_state(old_state, new_state)
        >>> # Returns diffs for count change and active addition
    """

    def __init__(
        self,
        *,
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
        max_diff_depth: int = 10,
    ):
        """
        Initialize StateSyncManager.

        Args:
            conflict_strategy: Default strategy for resolving conflicts
            max_diff_depth: Maximum depth for nested diff operations
        """
        self._conflict_strategy = conflict_strategy
        self._max_diff_depth = max_diff_depth

    @property
    def conflict_strategy(self) -> ConflictResolutionStrategy:
        """Get the conflict resolution strategy."""
        return self._conflict_strategy

    def diff_state(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
        *,
        path_prefix: str = "",
        depth: int = 0,
    ) -> List[StateDiff]:
        """
        Calculate differences between two states.

        Args:
            old_state: Previous state
            new_state: New state
            path_prefix: Prefix for path (used in recursion)
            depth: Current recursion depth

        Returns:
            List of StateDiff representing all changes
        """
        diffs: List[StateDiff] = []

        if depth > self._max_diff_depth:
            # Max depth reached, treat as replace
            if old_state != new_state:
                diffs.append(
                    StateDiff(
                        path=path_prefix or ".",
                        operation=DiffOperation.REPLACE,
                        old_value=old_state,
                        new_value=new_state,
                    )
                )
            return diffs

        # Get all keys from both states
        old_keys = set(old_state.keys()) if isinstance(old_state, dict) else set()
        new_keys = set(new_state.keys()) if isinstance(new_state, dict) else set()

        # Check for removed keys
        for key in old_keys - new_keys:
            path = f"{path_prefix}.{key}" if path_prefix else key
            diffs.append(
                StateDiff(
                    path=path,
                    operation=DiffOperation.REMOVE,
                    old_value=old_state[key],
                )
            )

        # Check for added keys
        for key in new_keys - old_keys:
            path = f"{path_prefix}.{key}" if path_prefix else key
            diffs.append(
                StateDiff(
                    path=path,
                    operation=DiffOperation.ADD,
                    new_value=new_state[key],
                )
            )

        # Check for changed values
        for key in old_keys & new_keys:
            path = f"{path_prefix}.{key}" if path_prefix else key
            old_val = old_state[key]
            new_val = new_state[key]

            if old_val != new_val:
                # If both are dicts, recurse
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    nested_diffs = self.diff_state(
                        old_val, new_val, path_prefix=path, depth=depth + 1
                    )
                    diffs.extend(nested_diffs)
                else:
                    diffs.append(
                        StateDiff(
                            path=path,
                            operation=DiffOperation.REPLACE,
                            old_value=old_val,
                            new_value=new_val,
                        )
                    )

        return diffs

    def apply_diffs(
        self,
        state: Dict[str, Any],
        diffs: List[StateDiff],
    ) -> Dict[str, Any]:
        """
        Apply a list of diffs to a state.

        Args:
            state: Current state
            diffs: List of diffs to apply

        Returns:
            New state with diffs applied
        """
        result = copy.deepcopy(state)

        for diff in diffs:
            self._apply_single_diff(result, diff)

        return result

    def _apply_single_diff(
        self,
        state: Dict[str, Any],
        diff: StateDiff,
    ) -> None:
        """Apply a single diff to state (mutates state)."""
        parts = diff.path.split(".") if diff.path != "." else []

        # Navigate to parent
        current = state
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Apply operation
        if not parts:
            # Root level operation
            if diff.operation == DiffOperation.REPLACE:
                state.clear()
                if isinstance(diff.new_value, dict):
                    state.update(diff.new_value)
            return

        key = parts[-1]
        if diff.operation == DiffOperation.ADD:
            current[key] = diff.new_value
        elif diff.operation == DiffOperation.REMOVE:
            if key in current:
                del current[key]
        elif diff.operation == DiffOperation.REPLACE:
            current[key] = diff.new_value

    def merge_state(
        self,
        server_state: Dict[str, Any],
        client_state: Dict[str, Any],
        *,
        server_version: Optional[StateVersion] = None,
        client_version: Optional[StateVersion] = None,
    ) -> Tuple[Dict[str, Any], List[StateConflict]]:
        """
        Merge server and client states.

        Args:
            server_state: Current server state
            client_state: Client's state changes
            server_version: Server state version
            client_version: Client state version

        Returns:
            Tuple of (merged_state, conflicts)
        """
        merged = copy.deepcopy(server_state)
        conflicts: List[StateConflict] = []

        def _merge_recursive(
            server: Any,
            client: Any,
            path: str = "",
        ) -> Tuple[Any, List[StateConflict]]:
            local_conflicts: List[StateConflict] = []

            if not isinstance(server, dict) or not isinstance(client, dict):
                # Not both dicts, check for conflict
                if server != client:
                    conflict = StateConflict(
                        path=path or ".",
                        server_value=server,
                        client_value=client,
                    )
                    resolved = self._resolve_conflict(
                        conflict, server_version, client_version
                    )
                    local_conflicts.append(conflict)
                    return resolved, local_conflicts
                return server, local_conflicts

            result = copy.deepcopy(server)

            for key, client_val in client.items():
                child_path = f"{path}.{key}" if path else key
                if key in server:
                    # Both have the key, recurse or compare
                    merged_val, child_conflicts = _merge_recursive(
                        server[key], client_val, child_path
                    )
                    result[key] = merged_val
                    local_conflicts.extend(child_conflicts)
                else:
                    # Only client has it, add it
                    result[key] = client_val

            return result, local_conflicts

        merged, conflicts = _merge_recursive(server_state, client_state)
        return merged, conflicts

    def _resolve_conflict(
        self,
        conflict: StateConflict,
        server_version: Optional[StateVersion] = None,
        client_version: Optional[StateVersion] = None,
    ) -> Any:
        """Resolve a conflict based on strategy."""
        strategy = self._conflict_strategy
        conflict.resolution = strategy

        if strategy == ConflictResolutionStrategy.SERVER_WINS:
            conflict.resolved_value = conflict.server_value
        elif strategy == ConflictResolutionStrategy.CLIENT_WINS:
            conflict.resolved_value = conflict.client_value
        elif strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            # Use version timestamps to determine winner
            server_ts = server_version.timestamp if server_version else 0
            client_ts = client_version.timestamp if client_version else 0
            if client_ts > server_ts:
                conflict.resolved_value = conflict.client_value
            else:
                conflict.resolved_value = conflict.server_value
        elif strategy == ConflictResolutionStrategy.MERGE:
            # Attempt to merge (works for lists, sets)
            if isinstance(conflict.server_value, list) and isinstance(
                conflict.client_value, list
            ):
                # Union of lists
                merged = list(conflict.server_value)
                for item in conflict.client_value:
                    if item not in merged:
                        merged.append(item)
                conflict.resolved_value = merged
            else:
                # Fall back to server wins for non-mergeable types
                conflict.resolved_value = conflict.server_value
        else:
            # Manual resolution needed, use server for now
            conflict.resolved_value = conflict.server_value

        return conflict.resolved_value


class SharedStateHandler:
    """
    Handler for shared state between backend and frontend.

    Provides state management with snapshot and delta event emission,
    version tracking, and synchronization utilities.

    Key Features:
    - Full state snapshot emission
    - Incremental delta updates
    - Version tracking for optimistic updates
    - State persistence integration
    - Conflict resolution

    Example:
        >>> handler = SharedStateHandler()
        >>> # Set initial state
        >>> handler.set_state("thread-123", {"count": 0, "items": []})
        >>> # Update state and get delta event
        >>> event = handler.update_state(
        ...     thread_id="thread-123",
        ...     run_id="run-456",
        ...     updates={"count": 1},
        ... )
        >>> # Get current state snapshot
        >>> snapshot = handler.emit_state_snapshot("thread-123", "run-456")
    """

    def __init__(
        self,
        *,
        sync_manager: Optional[StateSyncManager] = None,
        max_history: int = 100,
    ):
        """
        Initialize SharedStateHandler.

        Args:
            sync_manager: Optional custom StateSyncManager
            max_history: Maximum number of state versions to keep
        """
        self._sync_manager = sync_manager or StateSyncManager()
        self._max_history = max_history

        # State storage: thread_id -> state
        self._states: Dict[str, Dict[str, Any]] = {}
        # Version tracking: thread_id -> StateVersion
        self._versions: Dict[str, StateVersion] = {}
        # State history: thread_id -> list of (version, state)
        self._history: Dict[str, List[Tuple[StateVersion, Dict[str, Any]]]] = {}
        # Subscriptions: thread_id -> set of callback IDs
        self._subscriptions: Dict[str, Set[str]] = {}

        logger.info(
            f"SharedStateHandler initialized: max_history={max_history}"
        )

    @property
    def sync_manager(self) -> StateSyncManager:
        """Get the sync manager."""
        return self._sync_manager

    def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for a thread."""
        return copy.deepcopy(self._states.get(thread_id))

    def get_version(self, thread_id: str) -> Optional[StateVersion]:
        """Get current version for a thread."""
        return self._versions.get(thread_id)

    def set_state(
        self,
        thread_id: str,
        state: Dict[str, Any],
        *,
        emit_event: bool = False,
        run_id: Optional[str] = None,
    ) -> Optional[StateSnapshotEvent]:
        """
        Set the full state for a thread.

        Args:
            thread_id: Thread ID
            state: New state
            emit_event: Whether to emit a snapshot event
            run_id: Run ID (required if emit_event is True)

        Returns:
            StateSnapshotEvent if emit_event is True, else None
        """
        # Store previous state for history
        old_state = self._states.get(thread_id)
        old_version = self._versions.get(thread_id)

        if old_state is not None and old_version is not None:
            # Add to history
            if thread_id not in self._history:
                self._history[thread_id] = []
            self._history[thread_id].append((old_version, old_state))
            # Trim history if needed
            if len(self._history[thread_id]) > self._max_history:
                self._history[thread_id] = self._history[thread_id][-self._max_history :]

        # Set new state
        self._states[thread_id] = copy.deepcopy(state)
        self._versions[thread_id] = StateVersion(
            version=(old_version.version + 1) if old_version else 1
        )

        logger.debug(
            f"State set for thread {thread_id}: version={self._versions[thread_id].version}"
        )

        if emit_event and run_id:
            return self.emit_state_snapshot(thread_id, run_id)
        return None

    def update_state(
        self,
        thread_id: str,
        run_id: str,
        updates: Dict[str, Any],
        *,
        merge: bool = True,
    ) -> StateDeltaEvent:
        """
        Update state and emit delta event.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            updates: Updates to apply
            merge: If True, merge with existing; if False, replace

        Returns:
            StateDeltaEvent with the changes
        """
        old_state = self._states.get(thread_id, {})

        if merge:
            new_state = copy.deepcopy(old_state)
            self._deep_update(new_state, updates)
        else:
            new_state = copy.deepcopy(updates)

        # Calculate diffs
        diffs = self._sync_manager.diff_state(old_state, new_state)

        # Update state
        self.set_state(thread_id, new_state)

        # Emit delta event
        return self.emit_state_delta(thread_id, run_id, diffs)

    def _deep_update(
        self,
        base: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> None:
        """Deep update a dict (mutates base)."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def emit_state_snapshot(
        self,
        thread_id: str,
        run_id: str,
    ) -> StateSnapshotEvent:
        """
        Emit a full state snapshot event.

        Args:
            thread_id: Thread ID
            run_id: Run ID

        Returns:
            StateSnapshotEvent with full state
        """
        state = self._states.get(thread_id, {})
        version = self._versions.get(thread_id)

        return StateSnapshotEvent(
            type=AGUIEventType.STATE_SNAPSHOT,
            snapshot=state,
            metadata={
                "threadId": thread_id,
                "runId": run_id,
                "version": version.to_dict() if version else None,
            },
        )

    def emit_state_delta(
        self,
        thread_id: str,
        run_id: str,
        diffs: List[StateDiff],
    ) -> StateDeltaEvent:
        """
        Emit a state delta event.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            diffs: List of diffs to emit

        Returns:
            StateDeltaEvent with the changes
        """
        version = self._versions.get(thread_id)

        # Convert diffs to delta format
        delta = [diff.to_dict() for diff in diffs]

        return StateDeltaEvent(
            type=AGUIEventType.STATE_DELTA,
            delta=delta,
            metadata={
                "threadId": thread_id,
                "runId": run_id,
                "version": version.to_dict() if version else None,
            },
        )

    def apply_client_update(
        self,
        thread_id: str,
        run_id: str,
        client_state: Dict[str, Any],
        *,
        client_version: Optional[int] = None,
    ) -> Tuple[StateDeltaEvent, List[StateConflict]]:
        """
        Apply an update from the client.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            client_state: Client's state changes
            client_version: Client's version number

        Returns:
            Tuple of (delta_event, conflicts)
        """
        server_state = self._states.get(thread_id, {})
        server_version = self._versions.get(thread_id)

        # Build client version info
        cv = StateVersion(version=client_version) if client_version else None

        # Merge states
        merged, conflicts = self._sync_manager.merge_state(
            server_state,
            client_state,
            server_version=server_version,
            client_version=cv,
        )

        # Calculate diffs from server state to merged
        diffs = self._sync_manager.diff_state(server_state, merged)

        # Update server state
        self.set_state(thread_id, merged)

        # Emit delta event
        event = self.emit_state_delta(thread_id, run_id, diffs)

        return event, conflicts

    def get_state_at_version(
        self,
        thread_id: str,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get state at a specific version.

        Args:
            thread_id: Thread ID
            version: Version number

        Returns:
            State at that version, or None if not found
        """
        # Check current version
        current_version = self._versions.get(thread_id)
        if current_version and current_version.version == version:
            return copy.deepcopy(self._states.get(thread_id))

        # Check history
        history = self._history.get(thread_id, [])
        for v, state in history:
            if v.version == version:
                return copy.deepcopy(state)

        return None

    def rollback_to_version(
        self,
        thread_id: str,
        run_id: str,
        version: int,
    ) -> Optional[StateSnapshotEvent]:
        """
        Rollback state to a specific version.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            version: Version to rollback to

        Returns:
            StateSnapshotEvent if rollback succeeded, None otherwise
        """
        state = self.get_state_at_version(thread_id, version)
        if state is None:
            logger.warning(f"Cannot rollback: version {version} not found for {thread_id}")
            return None

        return self.set_state(thread_id, state, emit_event=True, run_id=run_id)

    def clear_state(self, thread_id: str) -> None:
        """Clear all state for a thread."""
        if thread_id in self._states:
            del self._states[thread_id]
        if thread_id in self._versions:
            del self._versions[thread_id]
        if thread_id in self._history:
            del self._history[thread_id]
        if thread_id in self._subscriptions:
            del self._subscriptions[thread_id]

        logger.info(f"Cleared state for thread: {thread_id}")

    def clear_all(self) -> None:
        """Clear all state."""
        self._states.clear()
        self._versions.clear()
        self._history.clear()
        self._subscriptions.clear()
        logger.info("Cleared all shared state")


def create_shared_state_handler(
    *,
    conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
    max_history: int = 100,
) -> SharedStateHandler:
    """
    Factory function to create SharedStateHandler.

    Args:
        conflict_strategy: Strategy for resolving conflicts
        max_history: Maximum number of state versions to keep

    Returns:
        Configured SharedStateHandler instance
    """
    sync_manager = StateSyncManager(conflict_strategy=conflict_strategy)
    return SharedStateHandler(
        sync_manager=sync_manager,
        max_history=max_history,
    )
