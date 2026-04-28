# =============================================================================
# IPA Platform - AG-UI State Events Unit Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Unit tests for AG-UI state events (StateSnapshot, StateDelta, Custom).
# =============================================================================

import json

import pytest

from src.integrations.ag_ui.events.base import AGUIEventType
from src.integrations.ag_ui.events.state import (
    CustomEvent,
    StateDeltaEvent,
    StateDeltaItem,
    StateDeltaOperation,
    StateSnapshotEvent,
)


class TestStateSnapshotEvent:
    """Tests for StateSnapshotEvent class."""

    def test_create_state_snapshot_event(self):
        """Test creating a state snapshot event."""
        event = StateSnapshotEvent(
            snapshot={
                "user": {"name": "Alice", "role": "admin"},
                "conversation": {"turn": 5}
            }
        )
        assert event.type == AGUIEventType.STATE_SNAPSHOT
        assert event.snapshot["user"]["name"] == "Alice"
        assert event.snapshot["conversation"]["turn"] == 5

    def test_empty_snapshot(self):
        """Test empty snapshot."""
        event = StateSnapshotEvent()
        assert event.snapshot == {}

    def test_complex_snapshot(self):
        """Test complex nested snapshot."""
        snapshot = {
            "user": {
                "id": "user-123",
                "name": "Alice",
                "preferences": {
                    "theme": "dark",
                    "language": "zh-TW"
                }
            },
            "session": {
                "id": "session-456",
                "started_at": "2026-01-05T10:00:00Z",
                "tools_available": ["search", "calculate", "generate"]
            },
            "context": {
                "current_task": "Analysis",
                "progress": 0.5
            }
        }
        event = StateSnapshotEvent(snapshot=snapshot)

        assert event.snapshot["user"]["preferences"]["theme"] == "dark"
        assert len(event.snapshot["session"]["tools_available"]) == 3

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = StateSnapshotEvent(
            snapshot={"key": "value", "nested": {"deep": True}}
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "STATE_SNAPSHOT"
        assert data["snapshot"]["key"] == "value"
        assert data["snapshot"]["nested"]["deep"] is True


class TestStateDeltaOperation:
    """Tests for StateDeltaOperation values."""

    def test_operation_values(self):
        """Test operation type values."""
        assert StateDeltaOperation.SET == "set"
        assert StateDeltaOperation.DELETE == "delete"
        assert StateDeltaOperation.APPEND == "append"
        assert StateDeltaOperation.INCREMENT == "increment"


class TestStateDeltaItem:
    """Tests for StateDeltaItem class."""

    def test_create_set_operation(self):
        """Test creating a set operation."""
        item = StateDeltaItem(
            path="user.name",
            operation=StateDeltaOperation.SET,
            value="Bob"
        )
        assert item.path == "user.name"
        assert item.operation == "set"
        assert item.value == "Bob"

    def test_create_delete_operation(self):
        """Test creating a delete operation."""
        item = StateDeltaItem(
            path="user.temp_data",
            operation=StateDeltaOperation.DELETE
        )
        assert item.operation == "delete"
        assert item.value is None

    def test_create_increment_operation(self):
        """Test creating an increment operation."""
        item = StateDeltaItem(
            path="conversation.turn",
            operation=StateDeltaOperation.INCREMENT,
            value=1
        )
        assert item.operation == "increment"
        assert item.value == 1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        item = StateDeltaItem(
            path="user.score",
            operation=StateDeltaOperation.SET,
            value=100
        )
        d = item.to_dict()

        assert d["path"] == "user.score"
        assert d["operation"] == "set"
        assert d["value"] == 100

    def test_to_dict_without_value(self):
        """Test conversion to dictionary without value."""
        item = StateDeltaItem(
            path="user.temp",
            operation=StateDeltaOperation.DELETE
        )
        d = item.to_dict()

        assert d["path"] == "user.temp"
        assert d["operation"] == "delete"
        assert "value" not in d


class TestStateDeltaEvent:
    """Tests for StateDeltaEvent class."""

    def test_create_state_delta_event(self):
        """Test creating a state delta event."""
        event = StateDeltaEvent(
            delta=[
                {"path": "user.name", "operation": "set", "value": "Bob"}
            ]
        )
        assert event.type == AGUIEventType.STATE_DELTA
        assert len(event.delta) == 1
        assert event.delta[0]["path"] == "user.name"

    def test_empty_delta(self):
        """Test empty delta."""
        event = StateDeltaEvent()
        assert event.delta == []

    def test_multiple_deltas(self):
        """Test multiple delta operations."""
        event = StateDeltaEvent(
            delta=[
                {"path": "conversation.turn", "operation": "increment", "value": 1},
                {"path": "user.last_active", "operation": "set", "value": "2026-01-05T10:00:00Z"},
                {"path": "user.temp_data", "operation": "delete"}
            ]
        )
        assert len(event.delta) == 3
        assert event.delta[0]["operation"] == "increment"
        assert event.delta[1]["operation"] == "set"
        assert event.delta[2]["operation"] == "delete"

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = StateDeltaEvent(
            delta=[
                {"path": "key", "operation": "set", "value": "new_value"}
            ]
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "STATE_DELTA"
        assert data["delta"][0]["path"] == "key"


class TestCustomEvent:
    """Tests for CustomEvent class."""

    def test_create_custom_event(self):
        """Test creating a custom event."""
        event = CustomEvent(
            event_name="progress_update",
            payload={"step": 3, "total": 5, "message": "Processing..."}
        )
        assert event.type == AGUIEventType.CUSTOM
        assert event.event_name == "progress_update"
        assert event.payload["step"] == 3
        assert event.payload["total"] == 5

    def test_empty_payload(self):
        """Test custom event with empty payload."""
        event = CustomEvent(event_name="heartbeat")
        assert event.payload == {}

    def test_mode_switch_event(self):
        """Test custom event for mode switching."""
        event = CustomEvent(
            event_name="mode_switch",
            payload={
                "from": "workflow",
                "to": "chat",
                "reason": "User initiated conversation",
                "context_preserved": True
            }
        )
        assert event.event_name == "mode_switch"
        assert event.payload["from"] == "workflow"
        assert event.payload["to"] == "chat"

    def test_ui_component_event(self):
        """Test custom event for UI component rendering."""
        event = CustomEvent(
            event_name="render_component",
            payload={
                "component_type": "chart",
                "config": {
                    "type": "bar",
                    "data": [10, 20, 30],
                    "labels": ["A", "B", "C"]
                }
            }
        )
        assert event.event_name == "render_component"
        assert event.payload["component_type"] == "chart"

    def test_json_serialization(self):
        """Test JSON serialization."""
        event = CustomEvent(
            event_name="custom_action",
            payload={"action": "refresh", "target": "dashboard"}
        )
        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["type"] == "CUSTOM"
        assert data["event_name"] == "custom_action"
        assert data["payload"]["action"] == "refresh"

    def test_required_event_name(self):
        """Test event_name is required."""
        with pytest.raises(ValueError):
            CustomEvent(payload={"data": "test"})
