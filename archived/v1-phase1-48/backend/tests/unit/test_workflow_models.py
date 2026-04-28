# =============================================================================
# IPA Platform - Workflow Models Unit Tests
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Tests for Workflow domain models including:
#   - WorkflowNode
#   - WorkflowEdge
#   - WorkflowDefinition validation
# =============================================================================

import pytest
from uuid import uuid4

from src.domain.workflows.models import (
    GatewayType,
    NodeType,
    TriggerType,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowNode,
)


# =============================================================================
# NodeType Enum Tests
# =============================================================================


class TestNodeType:
    """Tests for NodeType enum."""

    def test_node_type_values(self):
        """Test all NodeType enum values."""
        assert NodeType.START.value == "start"
        assert NodeType.END.value == "end"
        assert NodeType.AGENT.value == "agent"
        assert NodeType.GATEWAY.value == "gateway"

    def test_node_type_from_string(self):
        """Test NodeType can be created from string."""
        assert NodeType("start") == NodeType.START
        assert NodeType("agent") == NodeType.AGENT


class TestTriggerType:
    """Tests for TriggerType enum."""

    def test_trigger_type_values(self):
        """Test all TriggerType enum values."""
        assert TriggerType.MANUAL.value == "manual"
        assert TriggerType.SCHEDULE.value == "schedule"
        assert TriggerType.WEBHOOK.value == "webhook"
        assert TriggerType.EVENT.value == "event"


class TestGatewayType:
    """Tests for GatewayType enum."""

    def test_gateway_type_values(self):
        """Test all GatewayType enum values."""
        assert GatewayType.EXCLUSIVE.value == "exclusive"
        assert GatewayType.PARALLEL.value == "parallel"
        assert GatewayType.INCLUSIVE.value == "inclusive"


# =============================================================================
# WorkflowNode Tests
# =============================================================================


class TestWorkflowNode:
    """Tests for WorkflowNode dataclass."""

    def test_start_node(self):
        """Test creating a start node."""
        node = WorkflowNode(id="start", type=NodeType.START)

        assert node.id == "start"
        assert node.type == NodeType.START
        assert node.agent_id is None

    def test_end_node(self):
        """Test creating an end node."""
        node = WorkflowNode(id="end", type=NodeType.END)

        assert node.id == "end"
        assert node.type == NodeType.END

    def test_agent_node_with_agent_id(self):
        """Test creating an agent node with agent_id."""
        agent_id = uuid4()
        node = WorkflowNode(
            id="classifier",
            type=NodeType.AGENT,
            name="Intent Classifier",
            agent_id=agent_id,
        )

        assert node.id == "classifier"
        assert node.type == NodeType.AGENT
        assert node.agent_id == agent_id
        assert node.name == "Intent Classifier"

    def test_agent_node_without_agent_id_raises(self):
        """Test that agent node without agent_id raises error."""
        with pytest.raises(ValueError, match="must have an agent_id"):
            WorkflowNode(
                id="bad-agent",
                type=NodeType.AGENT,
            )

    def test_node_type_from_string(self):
        """Test node type conversion from string."""
        node = WorkflowNode(id="start", type="start")

        assert node.type == NodeType.START

    def test_agent_id_from_string(self):
        """Test agent_id conversion from string UUID."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        node = WorkflowNode(
            id="agent1",
            type=NodeType.AGENT,
            agent_id=uuid_str,
        )

        from uuid import UUID
        assert isinstance(node.agent_id, UUID)
        assert str(node.agent_id) == uuid_str

    def test_node_with_config(self):
        """Test node with configuration."""
        node = WorkflowNode(
            id="agent1",
            type=NodeType.AGENT,
            agent_id=uuid4(),
            config={"temperature": 0.7, "max_tokens": 1000},
        )

        assert node.config["temperature"] == 0.7
        assert node.config["max_tokens"] == 1000

    def test_node_with_position(self):
        """Test node with UI position."""
        node = WorkflowNode(
            id="start",
            type=NodeType.START,
            position={"x": 100, "y": 200},
        )

        assert node.position["x"] == 100
        assert node.position["y"] == 200

    def test_node_to_dict(self):
        """Test node serialization to dict."""
        agent_id = uuid4()
        node = WorkflowNode(
            id="agent1",
            type=NodeType.AGENT,
            name="Test Agent",
            agent_id=agent_id,
        )

        result = node.to_dict()

        assert result["id"] == "agent1"
        assert result["type"] == "agent"
        assert result["name"] == "Test Agent"
        assert result["agent_id"] == str(agent_id)


# =============================================================================
# WorkflowEdge Tests
# =============================================================================


class TestWorkflowEdge:
    """Tests for WorkflowEdge dataclass."""

    def test_simple_edge(self):
        """Test creating a simple edge."""
        edge = WorkflowEdge(source="start", target="agent1")

        assert edge.source == "start"
        assert edge.target == "agent1"
        assert edge.condition is None

    def test_conditional_edge(self):
        """Test creating a conditional edge."""
        edge = WorkflowEdge(
            source="gateway1",
            target="support_agent",
            condition="intent == 'support'",
            label="Support Path",
        )

        assert edge.condition == "intent == 'support'"
        assert edge.label == "Support Path"

    def test_edge_to_dict(self):
        """Test edge serialization to dict."""
        edge = WorkflowEdge(
            source="a",
            target="b",
            condition="x > 5",
        )

        result = edge.to_dict()

        assert result["source"] == "a"
        assert result["target"] == "b"
        assert result["condition"] == "x > 5"


# =============================================================================
# WorkflowDefinition Tests
# =============================================================================


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition dataclass."""

    def test_minimal_valid_workflow(self):
        """Test minimal valid workflow with start and end."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("start", "end"),
            ],
        )

        errors = definition.validate()
        assert len(errors) == 0
        assert definition.is_valid()

    def test_sequential_agent_workflow(self):
        """Test valid sequential workflow with agents."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("agent1", NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode("agent2", NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("start", "agent1"),
                WorkflowEdge("agent1", "agent2"),
                WorkflowEdge("agent2", "end"),
            ],
        )

        errors = definition.validate()
        assert len(errors) == 0

    def test_workflow_from_dict(self):
        """Test creating workflow from dictionary."""
        data = {
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "agent1", "type": "agent", "agent_id": str(uuid4())},
                {"id": "end", "type": "end"},
            ],
            "edges": [
                {"source": "start", "target": "agent1"},
                {"source": "agent1", "target": "end"},
            ],
        }

        definition = WorkflowDefinition.from_dict(data)

        assert len(definition.nodes) == 3
        assert len(definition.edges) == 2
        assert definition.is_valid()

    def test_workflow_to_dict(self):
        """Test workflow serialization to dict."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("start", "end"),
            ],
        )

        result = definition.to_dict()

        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    def test_get_node(self):
        """Test getting node by ID."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[],
        )

        start = definition.get_node("start")
        assert start is not None
        assert start.type == NodeType.START

        unknown = definition.get_node("unknown")
        assert unknown is None

    def test_get_start_node(self):
        """Test getting start node."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("my-start", NodeType.START),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[],
        )

        start = definition.get_start_node()
        assert start is not None
        assert start.id == "my-start"

    def test_get_end_nodes(self):
        """Test getting end nodes."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("end1", NodeType.END),
                WorkflowNode("end2", NodeType.END),
            ],
            edges=[],
        )

        ends = definition.get_end_nodes()
        assert len(ends) == 2

    def test_get_outgoing_edges(self):
        """Test getting outgoing edges from a node."""
        definition = WorkflowDefinition(
            nodes=[],
            edges=[
                WorkflowEdge("a", "b"),
                WorkflowEdge("a", "c"),
                WorkflowEdge("b", "d"),
            ],
        )

        outgoing = definition.get_outgoing_edges("a")
        assert len(outgoing) == 2

    def test_get_incoming_edges(self):
        """Test getting incoming edges to a node."""
        definition = WorkflowDefinition(
            nodes=[],
            edges=[
                WorkflowEdge("a", "c"),
                WorkflowEdge("b", "c"),
                WorkflowEdge("c", "d"),
            ],
        )

        incoming = definition.get_incoming_edges("c")
        assert len(incoming) == 2


# =============================================================================
# WorkflowDefinition Validation Tests
# =============================================================================


class TestWorkflowValidation:
    """Tests for WorkflowDefinition validation."""

    def test_no_nodes_error(self):
        """Test error when workflow has no nodes."""
        definition = WorkflowDefinition(nodes=[], edges=[])

        errors = definition.validate()
        assert "at least one node" in errors[0]

    def test_no_start_node_error(self):
        """Test error when workflow has no start node."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("agent1", NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("agent1", "end"),
            ],
        )

        errors = definition.validate()
        assert any("START node" in e for e in errors)

    def test_multiple_start_nodes_error(self):
        """Test error when workflow has multiple start nodes."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start1", NodeType.START),
                WorkflowNode("start2", NodeType.START),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[],
        )

        errors = definition.validate()
        assert any("only one START node" in e for e in errors)

    def test_no_end_node_error(self):
        """Test error when workflow has no end node."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("agent1", NodeType.AGENT, agent_id=uuid4()),
            ],
            edges=[
                WorkflowEdge("start", "agent1"),
            ],
        )

        errors = definition.validate()
        assert any("END node" in e for e in errors)

    def test_duplicate_node_ids_error(self):
        """Test error when workflow has duplicate node IDs."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("start", NodeType.END),  # Duplicate ID
            ],
            edges=[],
        )

        errors = definition.validate()
        assert any("Duplicate" in e for e in errors)

    def test_edge_invalid_source_error(self):
        """Test error when edge references invalid source."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("nonexistent", "end"),
            ],
        )

        errors = definition.validate()
        assert any("source 'nonexistent'" in e for e in errors)

    def test_edge_invalid_target_error(self):
        """Test error when edge references invalid target."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("start", "nonexistent"),
            ],
        )

        errors = definition.validate()
        assert any("target 'nonexistent'" in e for e in errors)

    def test_node_no_outgoing_edges_error(self):
        """Test error when non-end node has no outgoing edges."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("agent1", NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("start", "end"),  # agent1 not connected
            ],
        )

        errors = definition.validate()
        assert any("no outgoing edges" in e for e in errors)

    def test_node_no_incoming_edges_error(self):
        """Test error when non-start node has no incoming edges."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("agent1", NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("start", "end"),  # agent1 not connected
            ],
        )

        errors = definition.validate()
        assert any("no incoming edges" in e for e in errors)

    def test_start_node_has_incoming_edges_error(self):
        """Test error when start node has incoming edges."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("agent1", NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("agent1", "start"),  # Invalid - going to start
                WorkflowEdge("start", "agent1"),
                WorkflowEdge("agent1", "end"),
            ],
        )

        errors = definition.validate()
        assert any("cannot have incoming edges" in e for e in errors)

    def test_end_node_has_outgoing_edges_error(self):
        """Test error when end node has outgoing edges."""
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("start", "end"),
                WorkflowEdge("end", "start"),  # Invalid - from end
            ],
        )

        errors = definition.validate()
        assert any("cannot have outgoing edges" in e for e in errors)


# =============================================================================
# WorkflowContext Tests
# =============================================================================


class TestWorkflowContext:
    """Tests for WorkflowContext dataclass."""

    def test_context_creation(self):
        """Test creating execution context."""
        exec_id = uuid4()
        workflow_id = uuid4()

        context = WorkflowContext(
            execution_id=exec_id,
            workflow_id=workflow_id,
        )

        assert context.execution_id == exec_id
        assert context.workflow_id == workflow_id
        assert context.variables == {}
        assert context.history == []

    def test_context_set_variable(self):
        """Test setting context variable."""
        context = WorkflowContext(
            execution_id=uuid4(),
            workflow_id=uuid4(),
        )

        context.set_variable("result", "success")
        assert context.get_variable("result") == "success"

    def test_context_get_variable_default(self):
        """Test getting variable with default."""
        context = WorkflowContext(
            execution_id=uuid4(),
            workflow_id=uuid4(),
        )

        value = context.get_variable("missing", "default")
        assert value == "default"

    def test_context_add_history(self):
        """Test adding execution history."""
        context = WorkflowContext(
            execution_id=uuid4(),
            workflow_id=uuid4(),
        )

        context.add_history("agent1", "executed", result="Done")

        assert len(context.history) == 1
        assert context.history[0]["node_id"] == "agent1"
        assert context.history[0]["action"] == "executed"
        assert context.history[0]["result"] == "Done"
        assert "timestamp" in context.history[0]
