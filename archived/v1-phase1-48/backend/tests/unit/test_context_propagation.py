# =============================================================================
# IPA Platform - Context Propagation Tests
# =============================================================================
# Sprint 11: S11-6 Context Propagation Tests
#
# Unit tests for context propagation including:
# - PropagationType (COPY, REFERENCE, MERGE, FILTER)
# - VariableScope management
# - ContextPropagator operations
# - DataFlowTracker monitoring
# =============================================================================

import pytest
from uuid import uuid4
from datetime import datetime

from src.domain.orchestration.nested import (
    PropagationType,
    VariableScopeType,
    DataFlowDirection,
    VariableDescriptor,
    PropagationRule,
    DataFlowEvent,
    VariableScope,
    ContextPropagator,
    DataFlowTracker,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_workflow_id():
    """Generate a sample workflow ID."""
    return uuid4()


@pytest.fixture
def variable_scope(sample_workflow_id):
    """Create a fresh VariableScope instance."""
    return VariableScope(workflow_id=sample_workflow_id)


@pytest.fixture
def context_propagator():
    """Create a fresh ContextPropagator instance."""
    return ContextPropagator()


@pytest.fixture
def data_flow_tracker():
    """Create a fresh DataFlowTracker instance."""
    return DataFlowTracker()


# =============================================================================
# VariableDescriptor Tests
# =============================================================================


class TestVariableDescriptor:
    """Tests for VariableDescriptor."""

    def test_descriptor_creation(self):
        """Test descriptor creation with defaults."""
        descriptor = VariableDescriptor(
            name="test_var",
            scope=VariableScopeType.LOCAL,
            value=42,
        )

        assert descriptor.name == "test_var"
        assert descriptor.scope == VariableScopeType.LOCAL
        assert descriptor.value == 42
        assert descriptor.read_only is False
        assert descriptor.propagate_down is True

    def test_descriptor_to_dict(self):
        """Test descriptor serialization."""
        descriptor = VariableDescriptor(
            name="test_var",
            scope=VariableScopeType.GLOBAL,
            value={"nested": "value"},
            read_only=True,
        )

        result = descriptor.to_dict()
        assert result["name"] == "test_var"
        assert result["scope"] == "global"
        assert result["read_only"] is True


# =============================================================================
# VariableScope Tests
# =============================================================================


class TestVariableScope:
    """Tests for VariableScope."""

    def test_set_and_get_local(self, variable_scope):
        """Test setting and getting local variables."""
        variable_scope.set("my_var", 123, scope=VariableScopeType.LOCAL)

        value = variable_scope.get("my_var")
        assert value == 123

    def test_set_and_get_global(self, variable_scope):
        """Test setting and getting global variables."""
        variable_scope.set("global_var", "shared", scope=VariableScopeType.GLOBAL)

        value = variable_scope.get("global_var")
        assert value == "shared"

    def test_get_nonexistent(self, variable_scope):
        """Test getting nonexistent variable."""
        value = variable_scope.get("nonexistent", default="default")
        assert value == "default"

    def test_exists(self, variable_scope):
        """Test variable existence check."""
        variable_scope.set("existing", True)

        assert variable_scope.exists("existing") is True
        assert variable_scope.exists("nonexistent") is False

    def test_delete(self, variable_scope):
        """Test variable deletion."""
        variable_scope.set("to_delete", "value")
        assert variable_scope.exists("to_delete")

        success = variable_scope.delete("to_delete")
        assert success
        assert not variable_scope.exists("to_delete")

    def test_get_descriptor(self, variable_scope):
        """Test getting variable descriptor."""
        variable_scope.set("my_var", 42, metadata={"info": "test"})

        descriptor = variable_scope.get_descriptor("my_var")
        assert descriptor is not None
        assert descriptor.value == 42
        assert descriptor.metadata["info"] == "test"

    def test_list_variables(self, variable_scope):
        """Test listing variables."""
        variable_scope.set("var1", 1)
        variable_scope.set("var2", 2)
        variable_scope.set("var3", 3, scope=VariableScopeType.GLOBAL)

        variables = variable_scope.list_variables()
        assert len(variables) >= 3

        local_only = variable_scope.list_variables(scope_filter=VariableScopeType.LOCAL)
        assert len(local_only) >= 2

    def test_create_child_scope(self, variable_scope):
        """Test creating child scope."""
        variable_scope.set("parent_var", "inherited", propagate_down=True)

        child_id = uuid4()
        child_scope = variable_scope.create_child_scope(child_id)

        # Child should have inherited variable
        value = child_scope.get("parent_var")
        assert value == "inherited"

    def test_child_scope_isolation(self, variable_scope):
        """Test child scope isolation."""
        variable_scope.set("parent_var", "parent_value")

        child_id = uuid4()
        child_scope = variable_scope.create_child_scope(child_id)

        # Set local in child
        child_scope.set("child_var", "child_value")

        # Parent should not have child's variable
        assert not variable_scope.exists("child_var")

    def test_to_dict(self, variable_scope):
        """Test scope serialization."""
        variable_scope.set("var1", 1)
        variable_scope.set("var2", 2, scope=VariableScopeType.GLOBAL)

        result = variable_scope.to_dict()
        assert "workflow_id" in result
        assert "local_count" in result
        assert "global_count" in result
        assert "variables" in result


# =============================================================================
# PropagationRule Tests
# =============================================================================


class TestPropagationRule:
    """Tests for PropagationRule."""

    def test_rule_creation(self):
        """Test rule creation."""
        rule = PropagationRule(
            source_key="input",
            target_key="output",
            propagation_type=PropagationType.COPY,
            direction=DataFlowDirection.DOWNSTREAM,
        )

        assert rule.source_key == "input"
        assert rule.target_key == "output"
        assert rule.propagation_type == PropagationType.COPY

    def test_rule_with_transform(self):
        """Test rule with transform function."""
        def transform(x):
            return x * 2

        rule = PropagationRule(
            source_key="value",
            transform=transform,
        )

        assert rule.transform is not None
        assert rule.transform(5) == 10

    def test_rule_to_dict(self):
        """Test rule serialization."""
        rule = PropagationRule(
            source_key="key",
            priority=10,
        )

        result = rule.to_dict()
        assert "rule_id" in result
        assert result["source_key"] == "key"
        assert result["priority"] == 10


# =============================================================================
# ContextPropagator Tests
# =============================================================================


class TestContextPropagator:
    """Tests for ContextPropagator."""

    def test_propagate_downstream_copy(self, context_propagator):
        """Test downstream propagation with COPY."""
        parent_context = {"var1": [1, 2, 3], "var2": "text"}

        result = context_propagator.propagate_downstream(
            parent_context=parent_context,
            propagation_type=PropagationType.COPY,
        )

        assert result["var1"] == [1, 2, 3]
        assert result["var2"] == "text"

        # Verify deep copy
        result["var1"].append(4)
        assert len(parent_context["var1"]) == 3

    def test_propagate_downstream_reference(self, context_propagator):
        """Test downstream propagation with REFERENCE."""
        parent_context = {"var1": [1, 2, 3]}

        result = context_propagator.propagate_downstream(
            parent_context=parent_context,
            propagation_type=PropagationType.REFERENCE,
        )

        # Should be same reference
        result["var1"].append(4)
        assert len(parent_context["var1"]) == 4

    def test_propagate_downstream_merge(self, context_propagator):
        """Test downstream propagation with MERGE."""
        parent_context = {"config": {"a": 1, "b": 2}}
        child_context = {"config": {"c": 3}}

        result = context_propagator.propagate_downstream(
            parent_context=parent_context,
            child_context=child_context,
            propagation_type=PropagationType.MERGE,
        )

        assert result["config"]["a"] == 1
        assert result["config"]["c"] == 3

    def test_propagate_downstream_filter(self, context_propagator):
        """Test downstream propagation with FILTER."""
        parent_context = {"var1": 1, "var2": 2, "var3": 3}

        result = context_propagator.propagate_downstream(
            parent_context=parent_context,
            propagation_type=PropagationType.FILTER,
            filter_keys={"var1", "var3"},
        )

        assert "var1" in result
        assert "var3" in result
        assert "var2" not in result

    def test_propagate_upstream(self, context_propagator):
        """Test upstream propagation."""
        parent_context = {"existing": "value"}
        child_context = {"new_key": "new_value", "existing": "updated"}

        result = context_propagator.propagate_upstream(
            child_context=child_context,
            parent_context=parent_context,
            merge_strategy="update",
        )

        assert result["new_key"] == "new_value"
        assert result["existing"] == "updated"

    def test_block_key(self, context_propagator):
        """Test blocking key propagation."""
        context_propagator.block_key("secret")

        parent_context = {"public": "data", "secret": "sensitive"}

        result = context_propagator.propagate_downstream(parent_context)

        assert "public" in result
        assert "secret" not in result

    def test_map_key(self, context_propagator):
        """Test key mapping."""
        context_propagator.map_key("old_name", "new_name")

        parent_context = {"old_name": "value"}

        result = context_propagator.propagate_downstream(parent_context)

        assert "new_name" in result
        assert result["new_name"] == "value"

    def test_add_rule(self, context_propagator):
        """Test adding propagation rule."""
        rule = PropagationRule(
            source_key="data",
            propagation_type=PropagationType.COPY,
            priority=10,
        )

        context_propagator.add_rule(rule)

        parent_context = {"data": "test"}
        result = context_propagator.propagate_downstream(parent_context)

        assert result["data"] == "test"

    def test_create_child_context(self, context_propagator):
        """Test creating child context."""
        parent_context = {"shared": "value"}
        child_inputs = {"child_specific": "input"}

        result = context_propagator.create_child_context(
            parent_context=parent_context,
            child_inputs=child_inputs,
        )

        assert result["shared"] == "value"
        assert result["child_specific"] == "input"

    def test_merge_child_results(self, context_propagator):
        """Test merging child results."""
        parent_context = {"initial": "data"}
        child_results = [
            {"result1": "value1"},
            {"result2": "value2"},
        ]

        result = context_propagator.merge_child_results(
            parent_context=parent_context,
            child_results=child_results,
        )

        assert result["initial"] == "data"
        assert result["result1"] == "value1"
        assert result["result2"] == "value2"

    def test_merge_child_results_conflict(self, context_propagator):
        """Test merging with conflicts."""
        parent_context = {}
        child_results = [
            {"key": "first"},
            {"key": "second"},
        ]

        result = context_propagator.merge_child_results(
            parent_context=parent_context,
            child_results=child_results,
            conflict_strategy="last_wins",
        )

        assert result["key"] == "second"


# =============================================================================
# DataFlowTracker Tests
# =============================================================================


class TestDataFlowTracker:
    """Tests for DataFlowTracker."""

    def test_record_flow(self, data_flow_tracker):
        """Test recording data flow."""
        source_id = uuid4()
        target_id = uuid4()

        event = data_flow_tracker.record_flow(
            source_workflow_id=source_id,
            target_workflow_id=target_id,
            variable_name="my_var",
            old_value=None,
            new_value=42,
            direction=DataFlowDirection.DOWNSTREAM,
            propagation_type=PropagationType.COPY,
        )

        assert event.source_workflow_id == source_id
        assert event.variable_name == "my_var"

    def test_get_events(self, data_flow_tracker):
        """Test getting events."""
        source_id = uuid4()
        target_id = uuid4()

        # Record multiple events
        for i in range(5):
            data_flow_tracker.record_flow(
                source_workflow_id=source_id,
                target_workflow_id=target_id,
                variable_name=f"var_{i}",
                old_value=None,
                new_value=i,
                direction=DataFlowDirection.DOWNSTREAM,
                propagation_type=PropagationType.COPY,
            )

        events = data_flow_tracker.get_events(workflow_id=source_id)
        assert len(events) == 5

    def test_get_events_with_filter(self, data_flow_tracker):
        """Test getting events with variable filter."""
        source_id = uuid4()
        target_id = uuid4()

        data_flow_tracker.record_flow(
            source_workflow_id=source_id,
            target_workflow_id=target_id,
            variable_name="target_var",
            old_value=None,
            new_value=1,
            direction=DataFlowDirection.DOWNSTREAM,
            propagation_type=PropagationType.COPY,
        )
        data_flow_tracker.record_flow(
            source_workflow_id=source_id,
            target_workflow_id=target_id,
            variable_name="other_var",
            old_value=None,
            new_value=2,
            direction=DataFlowDirection.DOWNSTREAM,
            propagation_type=PropagationType.COPY,
        )

        events = data_flow_tracker.get_events(variable_name="target_var")
        assert len(events) == 1

    def test_get_variable_history(self, data_flow_tracker):
        """Test getting variable history."""
        source_id = uuid4()
        target_id = uuid4()

        for i in range(3):
            data_flow_tracker.record_flow(
                source_workflow_id=source_id,
                target_workflow_id=target_id,
                variable_name="tracked_var",
                old_value=i,
                new_value=i + 1,
                direction=DataFlowDirection.DOWNSTREAM,
                propagation_type=PropagationType.COPY,
            )

        history = data_flow_tracker.get_variable_history("tracked_var")
        assert len(history) == 3

    def test_get_workflow_children(self, data_flow_tracker):
        """Test getting workflow children."""
        parent_id = uuid4()
        child1_id = uuid4()
        child2_id = uuid4()

        data_flow_tracker.record_flow(
            source_workflow_id=parent_id,
            target_workflow_id=child1_id,
            variable_name="var",
            old_value=None,
            new_value=1,
            direction=DataFlowDirection.DOWNSTREAM,
            propagation_type=PropagationType.COPY,
        )
        data_flow_tracker.record_flow(
            source_workflow_id=parent_id,
            target_workflow_id=child2_id,
            variable_name="var",
            old_value=None,
            new_value=2,
            direction=DataFlowDirection.DOWNSTREAM,
            propagation_type=PropagationType.COPY,
        )

        children = data_flow_tracker.get_workflow_children(parent_id)
        assert len(children) == 2
        assert child1_id in children
        assert child2_id in children

    def test_build_dependency_graph(self, data_flow_tracker):
        """Test building dependency graph."""
        source_id = uuid4()
        target_id = uuid4()

        data_flow_tracker.record_flow(
            source_workflow_id=source_id,
            target_workflow_id=target_id,
            variable_name="data",
            old_value=None,
            new_value="value",
            direction=DataFlowDirection.DOWNSTREAM,
            propagation_type=PropagationType.COPY,
        )

        graph = data_flow_tracker.build_dependency_graph()

        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1

    def test_get_statistics(self, data_flow_tracker):
        """Test getting tracker statistics."""
        source_id = uuid4()
        target_id = uuid4()

        for i in range(10):
            data_flow_tracker.record_flow(
                source_workflow_id=source_id,
                target_workflow_id=target_id,
                variable_name=f"var_{i % 3}",
                old_value=None,
                new_value=i,
                direction=DataFlowDirection.DOWNSTREAM if i % 2 == 0 else DataFlowDirection.UPSTREAM,
                propagation_type=PropagationType.COPY,
            )

        stats = data_flow_tracker.get_statistics()

        assert stats["total_events"] == 10
        assert "by_direction" in stats
        assert "by_propagation_type" in stats
        assert "top_variables" in stats

    def test_clear(self, data_flow_tracker):
        """Test clearing tracker."""
        source_id = uuid4()
        target_id = uuid4()

        data_flow_tracker.record_flow(
            source_workflow_id=source_id,
            target_workflow_id=target_id,
            variable_name="var",
            old_value=None,
            new_value=1,
            direction=DataFlowDirection.DOWNSTREAM,
            propagation_type=PropagationType.COPY,
        )

        data_flow_tracker.clear()

        stats = data_flow_tracker.get_statistics()
        assert stats["total_events"] == 0

    def test_max_events_limit(self):
        """Test max events limit."""
        tracker = DataFlowTracker(max_events=5)
        source_id = uuid4()
        target_id = uuid4()

        # Add more events than max
        for i in range(10):
            tracker.record_flow(
                source_workflow_id=source_id,
                target_workflow_id=target_id,
                variable_name=f"var_{i}",
                old_value=None,
                new_value=i,
                direction=DataFlowDirection.DOWNSTREAM,
                propagation_type=PropagationType.COPY,
            )

        stats = tracker.get_statistics()
        assert stats["total_events"] == 5  # Should be trimmed to max

