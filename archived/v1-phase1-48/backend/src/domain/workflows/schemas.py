# =============================================================================
# IPA Platform - Workflow Schemas
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Pydantic schemas for Workflow API request/response validation.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.domain.workflows.models import NodeType, TriggerType


class WorkflowNodeSchema(BaseModel):
    """Schema for workflow node."""

    id: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(start|end|agent|gateway)$")
    name: Optional[str] = Field(None, max_length=255)
    agent_id: Optional[UUID] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, float]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "classifier",
                "type": "agent",
                "name": "Intent Classifier",
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class WorkflowEdgeSchema(BaseModel):
    """Schema for workflow edge."""

    source: str = Field(..., min_length=1, max_length=100)
    target: str = Field(..., min_length=1, max_length=100)
    condition: Optional[str] = None
    label: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "source": "classifier",
                "target": "support_agent",
                "condition": "intent == 'support'",
            }
        }


class WorkflowGraphSchema(BaseModel):
    """Schema for workflow graph definition."""

    nodes: List[WorkflowNodeSchema] = Field(default_factory=list)
    edges: List[WorkflowEdgeSchema] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)


class WorkflowCreateRequest(BaseModel):
    """
    Request schema for creating a new workflow.

    Attributes:
        name: Workflow name
        description: Optional description
        trigger_type: How the workflow is triggered
        trigger_config: Trigger-specific configuration
        graph_definition: Node and edge definitions
    """

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: str = Field(default="manual", pattern="^(manual|schedule|webhook|event)$")
    trigger_config: Dict[str, Any] = Field(default_factory=dict)
    graph_definition: WorkflowGraphSchema

    @field_validator("graph_definition")
    @classmethod
    def validate_graph(cls, v: WorkflowGraphSchema) -> WorkflowGraphSchema:
        """Validate graph has required structure."""
        if not v.nodes:
            raise ValueError("Workflow must have at least one node")

        # Check for start node
        has_start = any(n.type == "start" for n in v.nodes)
        if not has_start:
            raise ValueError("Workflow must have a START node")

        # Check for end node
        has_end = any(n.type == "end" for n in v.nodes)
        if not has_end:
            raise ValueError("Workflow must have an END node")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "customer-support-workflow",
                "description": "Handles customer support inquiries",
                "trigger_type": "webhook",
                "trigger_config": {"endpoint": "/webhooks/support"},
                "graph_definition": {
                    "nodes": [
                        {"id": "start", "type": "start"},
                        {
                            "id": "classifier",
                            "type": "agent",
                            "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                        {"id": "end", "type": "end"},
                    ],
                    "edges": [
                        {"source": "start", "target": "classifier"},
                        {"source": "classifier", "target": "end"},
                    ],
                },
            }
        }


class WorkflowUpdateRequest(BaseModel):
    """
    Request schema for updating a workflow.

    All fields are optional - only provided fields will be updated.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: Optional[str] = Field(None, pattern="^(manual|schedule|webhook|event)$")
    trigger_config: Optional[Dict[str, Any]] = None
    graph_definition: Optional[WorkflowGraphSchema] = None
    status: Optional[str] = Field(None, pattern="^(draft|active|inactive|archived)$")


class WorkflowResponse(BaseModel):
    """
    Response schema for workflow data.

    Used for both single workflow and list responses.
    """

    id: UUID
    name: str
    description: Optional[str]
    trigger_type: str
    trigger_config: Dict[str, Any]
    graph_definition: Dict[str, Any]
    status: str
    version: int
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    """Response schema for paginated workflow list."""

    items: List[WorkflowResponse]
    total: int
    page: int
    page_size: int


class WorkflowExecuteRequest(BaseModel):
    """
    Request schema for executing a workflow.

    Attributes:
        input: Initial input data for the workflow
        variables: Optional runtime variables
    """

    input: Dict[str, Any] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "input": {"message": "I need help with my order", "user_id": "12345"},
                "variables": {"priority": "high"},
            }
        }


class NodeExecutionResult(BaseModel):
    """Result of a single node execution."""

    node_id: str
    type: str
    output: Optional[str] = None
    error: Optional[str] = None
    llm_calls: int = 0
    llm_tokens: int = 0
    llm_cost: float = 0.0
    started_at: datetime
    completed_at: Optional[datetime] = None


class WorkflowExecutionResponse(BaseModel):
    """
    Response schema for workflow execution.

    Attributes:
        execution_id: Unique execution identifier
        workflow_id: Workflow that was executed
        status: Execution status
        result: Final execution result
        node_results: Results from each node
        stats: Aggregate execution statistics
    """

    execution_id: UUID
    workflow_id: UUID
    status: str
    result: Optional[str] = None
    node_results: List[NodeExecutionResult] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "550e8400-e29b-41d4-a716-446655440001",
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "result": "Your order #12345 has been shipped...",
                "node_results": [
                    {
                        "node_id": "classifier",
                        "type": "agent",
                        "output": "Intent: order_status",
                        "llm_calls": 1,
                        "llm_tokens": 150,
                        "llm_cost": 0.001,
                        "started_at": "2024-01-15T10:30:00Z",
                        "completed_at": "2024-01-15T10:30:02Z",
                    }
                ],
                "stats": {
                    "total_llm_calls": 2,
                    "total_llm_tokens": 450,
                    "total_llm_cost": 0.003,
                    "duration_seconds": 5.2,
                },
                "started_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:05Z",
            }
        }


class WorkflowValidationResponse(BaseModel):
    """Response schema for workflow validation."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
