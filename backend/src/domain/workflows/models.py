# =============================================================================
# IPA Platform - Workflow Domain Models
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Domain models for Workflow definitions including:
#   - Node types (AGENT, GATEWAY, START, END)
#   - Trigger types (MANUAL, SCHEDULE, WEBHOOK, EVENT)
#   - Workflow structure validation
# =============================================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class NodeType(str, Enum):
    """
    Types of nodes in a workflow graph.

    Attributes:
        START: Entry point of the workflow
        END: Exit point of the workflow
        AGENT: AI agent node that processes input
        GATEWAY: Decision/routing node (parallel, conditional)
    """

    START = "start"
    END = "end"
    AGENT = "agent"
    GATEWAY = "gateway"


class TriggerType(str, Enum):
    """
    Types of workflow triggers.

    Attributes:
        MANUAL: Triggered by user action
        SCHEDULE: Triggered by time-based schedule (cron)
        WEBHOOK: Triggered by HTTP webhook
        EVENT: Triggered by system event
    """

    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    EVENT = "event"


class GatewayType(str, Enum):
    """
    Types of gateway routing behavior.

    Attributes:
        EXCLUSIVE: Only one path taken based on condition
        PARALLEL: All paths taken simultaneously
        INCLUSIVE: Multiple paths based on conditions
    """

    EXCLUSIVE = "exclusive"
    PARALLEL = "parallel"
    INCLUSIVE = "inclusive"


@dataclass
class WorkflowNode:
    """
    A node in the workflow graph.

    Attributes:
        id: Unique node identifier within the workflow
        type: Node type (start, end, agent, gateway)
        name: Display name for the node
        agent_id: Reference to Agent ID (for agent nodes)
        config: Node-specific configuration
        position: Optional UI position {x, y}

    Example:
        node = WorkflowNode(
            id="classifier",
            type=NodeType.AGENT,
            name="Intent Classifier",
            agent_id=UUID("..."),
        )
    """

    id: str
    type: NodeType
    name: Optional[str] = None
    agent_id: Optional[UUID] = None
    config: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Dict[str, float]] = None

    def __post_init__(self):
        """Validate node after creation."""
        # Convert string to enum if needed
        if isinstance(self.type, str):
            self.type = NodeType(self.type)

        # Agent nodes must have agent_id
        if self.type == NodeType.AGENT and not self.agent_id:
            raise ValueError(f"Agent node '{self.id}' must have an agent_id")

        # Convert string UUID to UUID object
        if self.agent_id and isinstance(self.agent_id, str):
            self.agent_id = UUID(self.agent_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        result = {
            "id": self.id,
            "type": self.type.value,
            "name": self.name or self.id,
        }
        if self.agent_id:
            result["agent_id"] = str(self.agent_id)
        if self.config:
            result["config"] = self.config
        if self.position:
            result["position"] = self.position
        return result


@dataclass
class WorkflowEdge:
    """
    An edge connecting two nodes in the workflow.

    Attributes:
        source: Source node ID
        target: Target node ID
        condition: Optional condition expression for conditional edges
        label: Display label for the edge

    Example:
        edge = WorkflowEdge(
            source="classifier",
            target="support_agent",
            condition="intent == 'support'",
        )
    """

    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary."""
        result = {
            "source": self.source,
            "target": self.target,
        }
        if self.condition:
            result["condition"] = self.condition
        if self.label:
            result["label"] = self.label
        return result


@dataclass
class WorkflowDefinition:
    """
    Complete workflow definition with validation.

    Attributes:
        nodes: List of workflow nodes
        edges: List of workflow edges
        variables: Workflow-level variables

    Example:
        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode("start", NodeType.START),
                WorkflowNode("agent1", NodeType.AGENT, agent_id=uuid4()),
                WorkflowNode("end", NodeType.END),
            ],
            edges=[
                WorkflowEdge("start", "agent1"),
                WorkflowEdge("agent1", "end"),
            ],
        )
        errors = definition.validate()
    """

    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Convert raw dicts to proper objects."""
        # Convert node dicts to WorkflowNode objects
        processed_nodes = []
        for node in self.nodes:
            if isinstance(node, dict):
                processed_nodes.append(WorkflowNode(**node))
            else:
                processed_nodes.append(node)
        self.nodes = processed_nodes

        # Convert edge dicts to WorkflowEdge objects
        processed_edges = []
        for edge in self.edges:
            if isinstance(edge, dict):
                processed_edges.append(WorkflowEdge(**edge))
            else:
                processed_edges.append(edge)
        self.edges = processed_edges

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_node_ids(self) -> List[str]:
        """Get all node IDs."""
        return [node.id for node in self.nodes]

    def get_start_node(self) -> Optional[WorkflowNode]:
        """Get the start node."""
        for node in self.nodes:
            if node.type == NodeType.START:
                return node
        return None

    def get_end_nodes(self) -> List[WorkflowNode]:
        """Get all end nodes."""
        return [node for node in self.nodes if node.type == NodeType.END]

    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Get all edges leaving a node."""
        return [edge for edge in self.edges if edge.source == node_id]

    def get_incoming_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Get all edges entering a node."""
        return [edge for edge in self.edges if edge.target == node_id]

    def validate(self) -> List[str]:
        """
        Validate the workflow definition.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for at least one node
        if not self.nodes:
            errors.append("Workflow must have at least one node")
            return errors

        node_ids = self.get_node_ids()

        # Check for duplicate node IDs
        if len(node_ids) != len(set(node_ids)):
            errors.append("Duplicate node IDs found")

        # Check for exactly one start node
        start_nodes = [n for n in self.nodes if n.type == NodeType.START]
        if len(start_nodes) == 0:
            errors.append("Workflow must have exactly one START node")
        elif len(start_nodes) > 1:
            errors.append("Workflow must have only one START node")

        # Check for at least one end node
        end_nodes = self.get_end_nodes()
        if len(end_nodes) == 0:
            errors.append("Workflow must have at least one END node")

        # Validate edges reference existing nodes
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge source '{edge.source}' not found in nodes")
            if edge.target not in node_ids:
                errors.append(f"Edge target '{edge.target}' not found in nodes")

        # Check that all non-end nodes have outgoing edges
        for node in self.nodes:
            if node.type != NodeType.END:
                outgoing = self.get_outgoing_edges(node.id)
                if not outgoing:
                    errors.append(f"Node '{node.id}' has no outgoing edges")

        # Check that all non-start nodes have incoming edges
        for node in self.nodes:
            if node.type != NodeType.START:
                incoming = self.get_incoming_edges(node.id)
                if not incoming:
                    errors.append(f"Node '{node.id}' has no incoming edges")

        # Check start node has no incoming edges
        start_node = self.get_start_node()
        if start_node and self.get_incoming_edges(start_node.id):
            errors.append("START node cannot have incoming edges")

        # Check end nodes have no outgoing edges
        for end_node in end_nodes:
            if self.get_outgoing_edges(end_node.id):
                errors.append(f"END node '{end_node.id}' cannot have outgoing edges")

        return errors

    def is_valid(self) -> bool:
        """Check if workflow is valid."""
        return len(self.validate()) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow definition to dictionary."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "variables": self.variables,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """Create WorkflowDefinition from dictionary."""
        return cls(
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            variables=data.get("variables", {}),
        )


@dataclass
class WorkflowContext:
    """
    Runtime context for workflow execution.

    Attributes:
        execution_id: Unique execution identifier
        workflow_id: Workflow being executed
        variables: Runtime variables
        input_data: Initial input data
        current_node: Currently executing node
        history: Execution history
    """

    execution_id: UUID
    workflow_id: UUID
    variables: Dict[str, Any] = field(default_factory=dict)
    input_data: Dict[str, Any] = field(default_factory=dict)
    current_node: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def add_history(
        self,
        node_id: str,
        action: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Add an entry to execution history."""
        from datetime import datetime

        self.history.append(
            {
                "node_id": node_id,
                "action": action,
                "result": result,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def set_variable(self, key: str, value: Any) -> None:
        """Set a runtime variable."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a runtime variable."""
        return self.variables.get(key, default)
