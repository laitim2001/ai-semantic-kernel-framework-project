# =============================================================================
# IPA Platform - Workflow Graph API Routes
# =============================================================================
# Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
#
# DAG visualization endpoints for workflow graph operations:
#   - GET /workflows/{id}/graph — Get workflow DAG data
#   - PUT /workflows/{id}/graph — Save DAG layout
#   - POST /workflows/{id}/graph/layout — Auto-layout
#
# These routes are registered under the existing /workflows prefix.
# =============================================================================

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_session
from src.infrastructure.database.repositories.workflow import WorkflowRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflow Graph"])


# =============================================================================
# Schemas
# =============================================================================


class GraphNodeSchema(BaseModel):
    """Schema for a graph node with position data."""

    id: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    agent_id: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, float]] = None


class GraphEdgeSchema(BaseModel):
    """Schema for a graph edge."""

    source: str = Field(..., min_length=1, max_length=100)
    target: str = Field(..., min_length=1, max_length=100)
    condition: Optional[str] = None
    label: Optional[str] = None


class WorkflowGraphResponse(BaseModel):
    """Response schema for workflow graph data."""

    workflow_id: str
    nodes: List[GraphNodeSchema] = Field(default_factory=list)
    edges: List[GraphEdgeSchema] = Field(default_factory=list)
    layout_metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowGraphUpdateRequest(BaseModel):
    """Request schema for updating workflow graph layout."""

    nodes: List[GraphNodeSchema] = Field(default_factory=list)
    edges: List[GraphEdgeSchema] = Field(default_factory=list)


class GraphLayoutRequest(BaseModel):
    """Request schema for auto-layout."""

    direction: str = Field(default="TB", pattern="^(TB|LR)$")


class GraphLayoutResponse(BaseModel):
    """Response schema for auto-layout result."""

    workflow_id: str
    nodes: List[GraphNodeSchema] = Field(default_factory=list)
    edges: List[GraphEdgeSchema] = Field(default_factory=list)
    layout_metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Dependencies
# =============================================================================


async def get_workflow_repository(
    session: AsyncSession = Depends(get_session),
) -> WorkflowRepository:
    """Dependency for WorkflowRepository."""
    return WorkflowRepository(session)


# =============================================================================
# Helper Functions
# =============================================================================


def extract_graph_data(workflow) -> WorkflowGraphResponse:
    """Extract graph data from workflow ORM model."""
    graph_def = workflow.graph_definition
    if not isinstance(graph_def, dict):
        graph_def = {}

    raw_nodes = graph_def.get("nodes", [])
    raw_edges = graph_def.get("edges", [])

    nodes = []
    for n in raw_nodes:
        if isinstance(n, dict):
            nodes.append(
                GraphNodeSchema(
                    id=n.get("id", ""),
                    type=n.get("type", "agent"),
                    name=n.get("name"),
                    agent_id=str(n["agent_id"]) if n.get("agent_id") else None,
                    config=n.get("config", {}),
                    position=n.get("position"),
                )
            )

    edges = []
    for e in raw_edges:
        if isinstance(e, dict):
            edges.append(
                GraphEdgeSchema(
                    source=e.get("source", ""),
                    target=e.get("target", ""),
                    condition=e.get("condition"),
                    label=e.get("label"),
                )
            )

    layout_metadata = graph_def.get("layout_metadata", {})

    return WorkflowGraphResponse(
        workflow_id=str(workflow.id),
        nodes=nodes,
        edges=edges,
        layout_metadata=layout_metadata if isinstance(layout_metadata, dict) else {},
    )


def apply_simple_layout(
    nodes: List[GraphNodeSchema],
    edges: List[GraphEdgeSchema],
    direction: str = "TB",
) -> List[GraphNodeSchema]:
    """Apply a simple topological layout to nodes.

    This is a server-side fallback. The primary layout engine runs
    client-side using dagre. This implementation provides a basic
    grid-based layout when the client cannot do it.
    """
    if not nodes:
        return nodes

    # Build adjacency for topological ordering
    adj: Dict[str, List[str]] = {n.id: [] for n in nodes}
    in_degree: Dict[str, int] = {n.id: 0 for n in nodes}

    for edge in edges:
        if edge.source in adj:
            adj[edge.source].append(edge.target)
        if edge.target in in_degree:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    # Kahn's topological sort
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    sorted_ids: List[str] = []
    while queue:
        current = queue.pop(0)
        sorted_ids.append(current)
        for neighbor in adj.get(current, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Assign positions by rank
    rank_map: Dict[str, int] = {}
    for i, nid in enumerate(sorted_ids):
        rank_map[nid] = i

    # Add any unvisited nodes (cycles or disconnected)
    for n in nodes:
        if n.id not in rank_map:
            rank_map[n.id] = len(rank_map)

    # Position spacing
    h_space = 250
    v_space = 120

    # Track nodes per rank for horizontal spread
    rank_counts: Dict[int, int] = {}
    node_rank_index: Dict[str, int] = {}
    for nid, rank in rank_map.items():
        idx = rank_counts.get(rank, 0)
        node_rank_index[nid] = idx
        rank_counts[rank] = idx + 1

    positioned = []
    for n in nodes:
        rank = rank_map.get(n.id, 0)
        rank_idx = node_rank_index.get(n.id, 0)
        count_in_rank = rank_counts.get(rank, 1)
        offset = (rank_idx - (count_in_rank - 1) / 2) * h_space

        if direction == "LR":
            pos = {"x": rank * h_space, "y": offset}
        else:
            pos = {"x": offset, "y": rank * v_space}

        positioned.append(
            GraphNodeSchema(
                id=n.id,
                type=n.type,
                name=n.name,
                agent_id=n.agent_id,
                config=n.config,
                position=pos,
            )
        )

    return positioned


# =============================================================================
# Routes
# =============================================================================


@router.get(
    "/{workflow_id}/graph",
    response_model=WorkflowGraphResponse,
    summary="Get workflow DAG graph data",
)
async def get_workflow_graph(
    workflow_id: UUID,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowGraphResponse:
    """
    Get workflow DAG visualization data.

    Returns nodes with positions and edges for ReactFlow rendering.
    """
    workflow = await repo.get(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return extract_graph_data(workflow)


@router.put(
    "/{workflow_id}/graph",
    response_model=WorkflowGraphResponse,
    summary="Save workflow DAG layout",
)
async def update_workflow_graph(
    workflow_id: UUID,
    request: WorkflowGraphUpdateRequest,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowGraphResponse:
    """
    Save workflow DAG layout with node positions.

    Updates the graph_definition JSONB field with position data
    for persisting the visual layout.
    """
    workflow = await repo.get(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    # Merge positions into existing graph_definition
    existing_def = workflow.graph_definition
    if not isinstance(existing_def, dict):
        existing_def = {}

    # Build updated graph definition preserving existing variables
    updated_def = {
        "nodes": [n.model_dump() for n in request.nodes],
        "edges": [e.model_dump() for e in request.edges],
        "variables": existing_def.get("variables", {}),
        "layout_metadata": {
            "last_saved": True,
            "node_count": len(request.nodes),
            "edge_count": len(request.edges),
        },
    }

    await repo.update(workflow_id, {"graph_definition": updated_def})

    # Re-fetch to return updated data
    workflow = await repo.get(workflow_id)
    return extract_graph_data(workflow)


@router.post(
    "/{workflow_id}/graph/layout",
    response_model=GraphLayoutResponse,
    summary="Auto-layout workflow DAG",
)
async def auto_layout_workflow_graph(
    workflow_id: UUID,
    request: GraphLayoutRequest,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> GraphLayoutResponse:
    """
    Apply auto-layout to workflow DAG.

    Uses server-side topological layout as fallback.
    Primary layout engine runs client-side using dagre.
    """
    workflow = await repo.get(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    graph_data = extract_graph_data(workflow)

    # Apply layout
    positioned_nodes = apply_simple_layout(
        graph_data.nodes,
        graph_data.edges,
        direction=request.direction,
    )

    # Save positioned layout
    updated_def = {
        "nodes": [n.model_dump() for n in positioned_nodes],
        "edges": [e.model_dump() for e in graph_data.edges],
        "variables": (
            workflow.graph_definition.get("variables", {})
            if isinstance(workflow.graph_definition, dict)
            else {}
        ),
        "layout_metadata": {
            "direction": request.direction,
            "auto_layout": True,
            "node_count": len(positioned_nodes),
            "edge_count": len(graph_data.edges),
        },
    }

    await repo.update(workflow_id, {"graph_definition": updated_def})

    return GraphLayoutResponse(
        workflow_id=str(workflow_id),
        nodes=positioned_nodes,
        edges=graph_data.edges,
        layout_metadata=updated_def["layout_metadata"],
    )
