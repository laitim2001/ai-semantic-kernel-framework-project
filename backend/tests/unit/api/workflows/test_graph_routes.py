# =============================================================================
# IPA Platform - Workflow Graph API Tests
# =============================================================================
# Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
#
# Tests for workflow graph API endpoints:
#   - GET /workflows/{id}/graph
#   - PUT /workflows/{id}/graph
#   - POST /workflows/{id}/graph/layout
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.api.v1.workflows.graph_routes import (
    GraphNodeSchema,
    GraphEdgeSchema,
    WorkflowGraphResponse,
    WorkflowGraphUpdateRequest,
    GraphLayoutRequest,
    GraphLayoutResponse,
    extract_graph_data,
    apply_simple_layout,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_graph_definition():
    """Sample workflow graph_definition JSONB."""
    return {
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "name": "Start",
                "config": {},
                "position": {"x": 100, "y": 50},
            },
            {
                "id": "agent-1",
                "type": "agent",
                "name": "Classifier Agent",
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "config": {"agent_type": "chat"},
                "position": {"x": 100, "y": 200},
            },
            {
                "id": "gateway-1",
                "type": "gateway",
                "name": "Route Decision",
                "config": {"gateway_type": "exclusive"},
                "position": {"x": 100, "y": 350},
            },
            {
                "id": "agent-2",
                "type": "agent",
                "name": "Support Agent",
                "config": {},
                "position": {"x": 0, "y": 500},
            },
            {
                "id": "agent-3",
                "type": "agent",
                "name": "Escalation Agent",
                "config": {},
                "position": {"x": 200, "y": 500},
            },
            {
                "id": "end",
                "type": "end",
                "name": "End",
                "config": {},
                "position": {"x": 100, "y": 650},
            },
        ],
        "edges": [
            {"source": "start", "target": "agent-1"},
            {"source": "agent-1", "target": "gateway-1"},
            {
                "source": "gateway-1",
                "target": "agent-2",
                "condition": "intent == 'support'",
                "label": "Support",
            },
            {
                "source": "gateway-1",
                "target": "agent-3",
                "condition": "intent == 'escalation'",
                "label": "Escalation",
            },
            {"source": "agent-2", "target": "end"},
            {"source": "agent-3", "target": "end"},
        ],
        "variables": {"intent": ""},
    }


@pytest.fixture
def mock_workflow(sample_graph_definition):
    """Create mock workflow ORM model."""
    wf = MagicMock()
    wf.id = uuid4()
    wf.name = "Test Workflow"
    wf.graph_definition = sample_graph_definition
    wf.status = "active"
    return wf


@pytest.fixture
def mock_workflow_empty():
    """Create mock workflow with empty graph."""
    wf = MagicMock()
    wf.id = uuid4()
    wf.name = "Empty Workflow"
    wf.graph_definition = {}
    wf.status = "draft"
    return wf


@pytest.fixture
def mock_workflow_no_positions():
    """Create mock workflow without position data."""
    wf = MagicMock()
    wf.id = uuid4()
    wf.name = "No Position Workflow"
    wf.graph_definition = {
        "nodes": [
            {"id": "start", "type": "start", "name": "Start", "config": {}},
            {"id": "end", "type": "end", "name": "End", "config": {}},
        ],
        "edges": [{"source": "start", "target": "end"}],
    }
    return wf


# =============================================================================
# Test: Schema Validation
# =============================================================================


class TestSchemas:
    """Tests for graph API schemas."""

    def test_graph_node_schema(self):
        """GraphNodeSchema creation."""
        node = GraphNodeSchema(
            id="agent-1",
            type="agent",
            name="Test Agent",
            agent_id="123",
            config={"key": "value"},
            position={"x": 100, "y": 200},
        )
        assert node.id == "agent-1"
        assert node.type == "agent"
        assert node.position == {"x": 100, "y": 200}

    def test_graph_node_schema_defaults(self):
        """GraphNodeSchema with defaults."""
        node = GraphNodeSchema(id="n1", type="start")
        assert node.name is None
        assert node.agent_id is None
        assert node.config == {}
        assert node.position is None

    def test_graph_edge_schema(self):
        """GraphEdgeSchema creation."""
        edge = GraphEdgeSchema(
            source="a",
            target="b",
            condition="x > 0",
            label="True path",
        )
        assert edge.source == "a"
        assert edge.target == "b"
        assert edge.condition == "x > 0"

    def test_graph_edge_schema_defaults(self):
        """GraphEdgeSchema with defaults."""
        edge = GraphEdgeSchema(source="a", target="b")
        assert edge.condition is None
        assert edge.label is None

    def test_workflow_graph_response(self):
        """WorkflowGraphResponse creation."""
        resp = WorkflowGraphResponse(
            workflow_id="wf-123",
            nodes=[GraphNodeSchema(id="n1", type="start")],
            edges=[GraphEdgeSchema(source="n1", target="n2")],
        )
        assert resp.workflow_id == "wf-123"
        assert len(resp.nodes) == 1
        assert len(resp.edges) == 1
        assert resp.layout_metadata == {}

    def test_graph_layout_request_default(self):
        """GraphLayoutRequest default direction."""
        req = GraphLayoutRequest()
        assert req.direction == "TB"

    def test_graph_layout_request_lr(self):
        """GraphLayoutRequest LR direction."""
        req = GraphLayoutRequest(direction="LR")
        assert req.direction == "LR"

    def test_update_request(self):
        """WorkflowGraphUpdateRequest creation."""
        req = WorkflowGraphUpdateRequest(
            nodes=[GraphNodeSchema(id="n1", type="agent")],
            edges=[GraphEdgeSchema(source="n1", target="n2")],
        )
        assert len(req.nodes) == 1
        assert len(req.edges) == 1


# =============================================================================
# Test: extract_graph_data
# =============================================================================


class TestExtractGraphData:
    """Tests for extract_graph_data helper."""

    def test_extract_full(self, mock_workflow):
        """Extract graph data from workflow with full graph."""
        result = extract_graph_data(mock_workflow)
        assert result.workflow_id == str(mock_workflow.id)
        assert len(result.nodes) == 6
        assert len(result.edges) == 6

    def test_extract_node_details(self, mock_workflow):
        """Extracted nodes have correct details."""
        result = extract_graph_data(mock_workflow)
        agent_node = next(n for n in result.nodes if n.id == "agent-1")
        assert agent_node.type == "agent"
        assert agent_node.name == "Classifier Agent"
        assert agent_node.agent_id == "550e8400-e29b-41d4-a716-446655440000"
        assert agent_node.position == {"x": 100, "y": 200}

    def test_extract_edge_details(self, mock_workflow):
        """Extracted edges have correct details."""
        result = extract_graph_data(mock_workflow)
        cond_edge = next(
            e for e in result.edges if e.source == "gateway-1" and e.target == "agent-2"
        )
        assert cond_edge.condition == "intent == 'support'"
        assert cond_edge.label == "Support"

    def test_extract_empty(self, mock_workflow_empty):
        """Extract from empty graph returns empty lists."""
        result = extract_graph_data(mock_workflow_empty)
        assert result.nodes == []
        assert result.edges == []

    def test_extract_non_dict(self):
        """Extract handles non-dict graph_definition."""
        wf = MagicMock()
        wf.id = uuid4()
        wf.graph_definition = None
        result = extract_graph_data(wf)
        assert result.nodes == []
        assert result.edges == []

    def test_extract_no_positions(self, mock_workflow_no_positions):
        """Extract handles nodes without position data."""
        result = extract_graph_data(mock_workflow_no_positions)
        assert len(result.nodes) == 2
        start = next(n for n in result.nodes if n.id == "start")
        assert start.position is None


# =============================================================================
# Test: apply_simple_layout
# =============================================================================


class TestApplySimpleLayout:
    """Tests for apply_simple_layout helper."""

    def test_layout_empty(self):
        """Layout empty list returns empty list."""
        result = apply_simple_layout([], [], "TB")
        assert result == []

    def test_layout_single_node(self):
        """Layout single node positions at origin."""
        nodes = [GraphNodeSchema(id="n1", type="start")]
        result = apply_simple_layout(nodes, [], "TB")
        assert len(result) == 1
        assert result[0].position is not None
        assert "x" in result[0].position
        assert "y" in result[0].position

    def test_layout_linear_tb(self):
        """Layout linear chain top-to-bottom."""
        nodes = [
            GraphNodeSchema(id="a", type="start"),
            GraphNodeSchema(id="b", type="agent"),
            GraphNodeSchema(id="c", type="end"),
        ]
        edges = [
            GraphEdgeSchema(source="a", target="b"),
            GraphEdgeSchema(source="b", target="c"),
        ]
        result = apply_simple_layout(nodes, edges, "TB")
        assert len(result) == 3
        # In TB: y should increase with rank
        ys = [n.position["y"] for n in result]
        assert ys[0] < ys[1] < ys[2] or ys[0] <= ys[1] <= ys[2]

    def test_layout_linear_lr(self):
        """Layout linear chain left-to-right."""
        nodes = [
            GraphNodeSchema(id="a", type="start"),
            GraphNodeSchema(id="b", type="agent"),
            GraphNodeSchema(id="c", type="end"),
        ]
        edges = [
            GraphEdgeSchema(source="a", target="b"),
            GraphEdgeSchema(source="b", target="c"),
        ]
        result = apply_simple_layout(nodes, edges, "LR")
        assert len(result) == 3
        # In LR: x should increase with rank
        xs = [n.position["x"] for n in result]
        assert xs[0] < xs[1] < xs[2] or xs[0] <= xs[1] <= xs[2]

    def test_layout_branching(self):
        """Layout with branching preserves all nodes."""
        nodes = [
            GraphNodeSchema(id="start", type="start"),
            GraphNodeSchema(id="gw", type="gateway"),
            GraphNodeSchema(id="a", type="agent"),
            GraphNodeSchema(id="b", type="agent"),
            GraphNodeSchema(id="end", type="end"),
        ]
        edges = [
            GraphEdgeSchema(source="start", target="gw"),
            GraphEdgeSchema(source="gw", target="a"),
            GraphEdgeSchema(source="gw", target="b"),
            GraphEdgeSchema(source="a", target="end"),
            GraphEdgeSchema(source="b", target="end"),
        ]
        result = apply_simple_layout(nodes, edges, "TB")
        assert len(result) == 5
        # All nodes should have positions
        for n in result:
            assert n.position is not None

    def test_layout_preserves_metadata(self):
        """Layout preserves node metadata."""
        nodes = [
            GraphNodeSchema(
                id="ag1",
                type="agent",
                name="My Agent",
                agent_id="uuid-123",
                config={"key": "val"},
            )
        ]
        result = apply_simple_layout(nodes, [], "TB")
        assert result[0].name == "My Agent"
        assert result[0].agent_id == "uuid-123"
        assert result[0].config == {"key": "val"}

    def test_layout_disconnected_nodes(self):
        """Layout handles disconnected nodes."""
        nodes = [
            GraphNodeSchema(id="a", type="start"),
            GraphNodeSchema(id="b", type="agent"),
            GraphNodeSchema(id="c", type="end"),
        ]
        # No edges = all disconnected
        result = apply_simple_layout(nodes, [], "TB")
        assert len(result) == 3
        for n in result:
            assert n.position is not None
