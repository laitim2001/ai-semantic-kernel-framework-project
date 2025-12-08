# =============================================================================
# IPA Platform - WorkflowContextAdapter Unit Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26, Story S26-4: WorkflowContextAdapter Tests
#
# Comprehensive tests for the WorkflowContextAdapter including:
#   - Context creation and initialization
#   - Get/Set operations
#   - History tracking
#   - Serialization
#   - Factory functions
# =============================================================================

import pytest
from uuid import uuid4

from src.integrations.agent_framework.core.context import (
    WorkflowContextAdapter,
    create_context,
    adapt_context,
    merge_contexts,
)
from src.domain.workflows.models import WorkflowContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def execution_id():
    """Create a test execution ID."""
    return uuid4()


@pytest.fixture
def workflow_id():
    """Create a test workflow ID."""
    return uuid4()


@pytest.fixture
def domain_context(execution_id, workflow_id):
    """Create a domain WorkflowContext."""
    return WorkflowContext(
        execution_id=execution_id,
        workflow_id=workflow_id,
        variables={"initial_key": "initial_value"},
        input_data={"query": "test query"},
    )


@pytest.fixture
def context_adapter(domain_context):
    """Create a WorkflowContextAdapter."""
    return WorkflowContextAdapter(context=domain_context)


# =============================================================================
# Test: WorkflowContextAdapter - Creation
# =============================================================================

class TestWorkflowContextAdapterCreation:
    """Tests for WorkflowContextAdapter creation."""

    def test_create_from_domain_context(self, domain_context):
        """Test creating adapter from domain context."""
        adapter = WorkflowContextAdapter(context=domain_context)

        assert adapter.execution_id == domain_context.execution_id
        assert adapter.workflow_id == domain_context.workflow_id

    def test_create_new_context(self, execution_id, workflow_id):
        """Test creating adapter with new context."""
        adapter = WorkflowContextAdapter(
            execution_id=execution_id,
            workflow_id=workflow_id,
        )

        assert adapter.execution_id == execution_id
        assert adapter.workflow_id == workflow_id

    def test_create_with_initial_variables(self):
        """Test creating adapter with initial variables."""
        initial_vars = {"key1": "value1", "key2": 42}

        adapter = WorkflowContextAdapter(initial_variables=initial_vars)

        assert adapter.get("key1") == "value1"
        assert adapter.get("key2") == 42

    def test_create_generates_ids(self):
        """Test that IDs are generated if not provided."""
        adapter = WorkflowContextAdapter()

        assert adapter.execution_id is not None
        assert adapter.workflow_id is not None
        assert adapter.run_id is not None


# =============================================================================
# Test: WorkflowContextAdapter - Properties
# =============================================================================

class TestWorkflowContextAdapterProperties:
    """Tests for WorkflowContextAdapter properties."""

    def test_run_id(self, context_adapter, execution_id):
        """Test run_id property."""
        assert context_adapter.run_id == str(execution_id)

    def test_execution_id(self, context_adapter, execution_id):
        """Test execution_id property."""
        assert context_adapter.execution_id == execution_id

    def test_workflow_id(self, context_adapter, workflow_id):
        """Test workflow_id property."""
        assert context_adapter.workflow_id == workflow_id

    def test_current_node(self, context_adapter):
        """Test current_node property."""
        assert context_adapter.current_node is None

        context_adapter.current_node = "node_1"
        assert context_adapter.current_node == "node_1"

    def test_domain_context(self, context_adapter, domain_context):
        """Test domain_context property."""
        assert context_adapter.domain_context is domain_context


# =============================================================================
# Test: WorkflowContextAdapter - Get/Set Operations
# =============================================================================

class TestWorkflowContextAdapterGetSet:
    """Tests for WorkflowContextAdapter get/set operations."""

    def test_get_existing_variable(self, context_adapter):
        """Test getting an existing variable."""
        value = context_adapter.get("initial_key")
        assert value == "initial_value"

    def test_get_from_input_data(self, context_adapter):
        """Test getting value from input_data."""
        value = context_adapter.get("query")
        assert value == "test query"

    def test_get_nonexistent_returns_default(self, context_adapter):
        """Test getting nonexistent key returns default."""
        value = context_adapter.get("nonexistent", "default_value")
        assert value == "default_value"

    def test_get_nonexistent_returns_none(self, context_adapter):
        """Test getting nonexistent key returns None by default."""
        value = context_adapter.get("nonexistent")
        assert value is None

    def test_set_new_variable(self, context_adapter):
        """Test setting a new variable."""
        context_adapter.set("new_key", "new_value")
        assert context_adapter.get("new_key") == "new_value"

    def test_set_overwrites_existing(self, context_adapter):
        """Test setting overwrites existing value."""
        context_adapter.set("initial_key", "updated_value")
        assert context_adapter.get("initial_key") == "updated_value"

    def test_set_various_types(self, context_adapter):
        """Test setting values of various types."""
        context_adapter.set("string", "hello")
        context_adapter.set("int", 42)
        context_adapter.set("float", 3.14)
        context_adapter.set("bool", True)
        context_adapter.set("list", [1, 2, 3])
        context_adapter.set("dict", {"nested": "value"})

        assert context_adapter.get("string") == "hello"
        assert context_adapter.get("int") == 42
        assert context_adapter.get("float") == 3.14
        assert context_adapter.get("bool") is True
        assert context_adapter.get("list") == [1, 2, 3]
        assert context_adapter.get("dict") == {"nested": "value"}


# =============================================================================
# Test: WorkflowContextAdapter - Delete/Has/Keys
# =============================================================================

class TestWorkflowContextAdapterDeleteHasKeys:
    """Tests for delete, has, and keys operations."""

    def test_delete_existing(self, context_adapter):
        """Test deleting an existing key."""
        context_adapter.set("to_delete", "value")
        assert context_adapter.has("to_delete") is True

        result = context_adapter.delete("to_delete")

        assert result is True
        assert context_adapter.has("to_delete") is False

    def test_delete_nonexistent(self, context_adapter):
        """Test deleting a nonexistent key."""
        result = context_adapter.delete("nonexistent")
        assert result is False

    def test_has_variable(self, context_adapter):
        """Test has for variable."""
        assert context_adapter.has("initial_key") is True
        assert context_adapter.has("nonexistent") is False

    def test_has_input_data(self, context_adapter):
        """Test has for input_data."""
        assert context_adapter.has("query") is True

    def test_keys(self, context_adapter):
        """Test getting all keys."""
        keys = context_adapter.keys()

        assert "initial_key" in keys
        assert "query" in keys

    def test_keys_after_modifications(self, context_adapter):
        """Test keys after adding and removing."""
        context_adapter.set("new_key", "value")
        keys = context_adapter.keys()

        assert "new_key" in keys

        context_adapter.delete("new_key")
        keys = context_adapter.keys()

        assert "new_key" not in keys


# =============================================================================
# Test: WorkflowContextAdapter - Update/Clear
# =============================================================================

class TestWorkflowContextAdapterUpdateClear:
    """Tests for update and clear operations."""

    def test_update_multiple(self, context_adapter):
        """Test updating multiple values at once."""
        context_adapter.update({
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        })

        assert context_adapter.get("key1") == "value1"
        assert context_adapter.get("key2") == "value2"
        assert context_adapter.get("key3") == "value3"

    def test_clear_variables(self, context_adapter):
        """Test clearing variables."""
        context_adapter.set("extra_key", "extra_value")
        context_adapter.clear()

        assert context_adapter.get("initial_key") is None
        assert context_adapter.get("extra_key") is None
        # input_data should still be accessible
        assert context_adapter.get("query") == "test query"


# =============================================================================
# Test: WorkflowContextAdapter - History
# =============================================================================

class TestWorkflowContextAdapterHistory:
    """Tests for history tracking."""

    def test_add_history(self, context_adapter):
        """Test adding history entries."""
        context_adapter.add_history(
            node_id="node_1",
            action="execute",
            result="success",
        )

        assert len(context_adapter.history) == 1
        assert context_adapter.history[0]["node_id"] == "node_1"
        assert context_adapter.history[0]["action"] == "execute"

    def test_add_history_with_error(self, context_adapter):
        """Test adding history with error."""
        context_adapter.add_history(
            node_id="node_1",
            action="execute",
            error="Execution failed",
        )

        assert context_adapter.history[0]["error"] == "Execution failed"

    def test_multiple_history_entries(self, context_adapter):
        """Test multiple history entries."""
        context_adapter.add_history("node_1", "start")
        context_adapter.add_history("node_1", "execute")
        context_adapter.add_history("node_1", "complete")

        assert len(context_adapter.history) == 3

    def test_modifications_tracked(self, context_adapter):
        """Test that modifications are tracked."""
        context_adapter.set("key1", "value1")
        context_adapter.set("key2", "value2")
        context_adapter.delete("key1")

        mods = context_adapter.modifications

        assert len(mods) == 3
        assert mods[0]["action"] == "set"
        assert mods[0]["key"] == "key1"
        assert mods[2]["action"] == "delete"


# =============================================================================
# Test: WorkflowContextAdapter - Serialization
# =============================================================================

class TestWorkflowContextAdapterSerialization:
    """Tests for serialization."""

    def test_to_dict(self, context_adapter):
        """Test converting to dictionary."""
        data = context_adapter.to_dict()

        assert "execution_id" in data
        assert "workflow_id" in data
        assert "variables" in data
        assert "input_data" in data
        assert "history" in data
        assert "created_at" in data

    def test_from_dict(self, context_adapter):
        """Test creating from dictionary."""
        data = context_adapter.to_dict()

        restored = WorkflowContextAdapter.from_dict(data)

        assert restored.run_id == context_adapter.run_id
        assert restored.get("initial_key") == "initial_value"

    def test_round_trip(self, context_adapter):
        """Test serialization round trip."""
        context_adapter.set("new_key", "new_value")
        context_adapter.add_history("node", "action")

        data = context_adapter.to_dict()
        restored = WorkflowContextAdapter.from_dict(data)

        assert restored.get("new_key") == "new_value"
        assert len(restored.history) == 1

    def test_snapshot(self, context_adapter):
        """Test creating snapshot."""
        context_adapter.current_node = "active_node"
        context_adapter.add_history("node", "action")

        snapshot = context_adapter.snapshot()

        assert "timestamp" in snapshot
        assert snapshot["execution_id"] == str(context_adapter.execution_id)
        assert snapshot["current_node"] == "active_node"
        assert snapshot["history_count"] == 1


# =============================================================================
# Test: WorkflowContextAdapter - Repr
# =============================================================================

class TestWorkflowContextAdapterRepr:
    """Tests for string representation."""

    def test_repr(self, context_adapter):
        """Test repr output."""
        repr_str = repr(context_adapter)

        assert "WorkflowContextAdapter" in repr_str
        assert "run_id=" in repr_str
        assert "keys=" in repr_str
        assert "history=" in repr_str


# =============================================================================
# Test: Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_context(self):
        """Test create_context factory."""
        adapter = create_context(
            input_data={"query": "test"},
            initial_variables={"var1": "value1"},
        )

        assert adapter.get("query") == "test"
        assert adapter.get("var1") == "value1"

    def test_create_context_with_ids(self, execution_id, workflow_id):
        """Test create_context with IDs."""
        adapter = create_context(
            execution_id=execution_id,
            workflow_id=workflow_id,
        )

        assert adapter.execution_id == execution_id
        assert adapter.workflow_id == workflow_id

    def test_adapt_context(self, domain_context):
        """Test adapt_context factory."""
        adapter = adapt_context(domain_context)

        assert adapter.domain_context is domain_context
        assert adapter.execution_id == domain_context.execution_id


class TestMergeContexts:
    """Tests for merge_contexts function."""

    def test_merge_basic(self):
        """Test basic context merge."""
        primary = create_context(initial_variables={"a": 1, "b": 2})
        secondary = create_context(initial_variables={"c": 3, "d": 4})

        merged = merge_contexts(primary, secondary)

        assert merged.get("a") == 1
        assert merged.get("b") == 2
        assert merged.get("c") == 3
        assert merged.get("d") == 4

    def test_merge_primary_takes_precedence(self):
        """Test that primary values take precedence."""
        primary = create_context(initial_variables={"key": "primary_value"})
        secondary = create_context(initial_variables={"key": "secondary_value"})

        merged = merge_contexts(primary, secondary)

        assert merged.get("key") == "primary_value"

    def test_merge_combines_history(self):
        """Test that history is combined."""
        primary = create_context()
        secondary = create_context()

        primary.add_history("node_1", "action_1")
        secondary.add_history("node_2", "action_2")

        merged = merge_contexts(primary, secondary)

        assert len(merged.history) == 2

    def test_merge_preserves_ids(self):
        """Test that merge preserves primary IDs."""
        exec_id = uuid4()
        wf_id = uuid4()

        primary = create_context(execution_id=exec_id, workflow_id=wf_id)
        secondary = create_context()

        merged = merge_contexts(primary, secondary)

        assert merged.execution_id == exec_id
        assert merged.workflow_id == wf_id


# =============================================================================
# Test: Integration with Domain Context
# =============================================================================

class TestDomainIntegration:
    """Tests for integration with domain WorkflowContext."""

    def test_changes_reflect_in_domain(self, context_adapter, domain_context):
        """Test that changes in adapter reflect in domain context."""
        context_adapter.set("adapter_key", "adapter_value")

        # Should be visible in domain context
        assert domain_context.variables.get("adapter_key") == "adapter_value"

    def test_domain_changes_visible(self, context_adapter, domain_context):
        """Test that domain changes are visible in adapter."""
        domain_context.set_variable("domain_key", "domain_value")

        # Should be visible in adapter
        assert context_adapter.get("domain_key") == "domain_value"

    def test_sync_methods(self, context_adapter):
        """Test sync methods don't error."""
        # These are no-ops since we use the same object
        context_adapter.sync_from_domain()
        context_adapter.sync_to_domain()

        # Should not raise any errors
        assert True
