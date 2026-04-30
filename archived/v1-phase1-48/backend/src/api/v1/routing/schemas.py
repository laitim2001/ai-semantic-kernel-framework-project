"""
Routing API Schemas
===================

Pydantic schemas for routing API endpoints.

Sprint 3 - S3-5: Cross-Scenario Collaboration
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================

class RouteRequest(BaseModel):
    """Request to route an execution to another scenario."""

    source_scenario: str = Field(..., description="Source scenario name")
    target_scenario: str = Field(..., description="Target scenario name")
    source_execution_id: UUID = Field(..., description="Source execution ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Data to pass")
    relation_type: str = Field("routed_to", description="Relationship type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CreateRelationRequest(BaseModel):
    """Request to create a relationship between executions."""

    source_execution_id: UUID = Field(..., description="Source execution ID")
    target_execution_id: UUID = Field(..., description="Target execution ID")
    relation_type: str = Field(..., description="Relationship type")
    source_scenario: str = Field(..., description="Source scenario")
    target_scenario: str = Field(..., description="Target scenario")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    create_reverse: bool = Field(True, description="Create reverse relation")


class ConfigureScenarioRequest(BaseModel):
    """Request to configure a scenario."""

    default_workflow_id: Optional[UUID] = Field(None, description="Default workflow ID")
    enabled: Optional[bool] = Field(None, description="Enable/disable scenario")
    description: Optional[str] = Field(None, description="Scenario description")
    allowed_targets: Optional[List[str]] = Field(None, description="Allowed target scenarios")


# ============================================================================
# Response Schemas
# ============================================================================

class RoutingResultResponse(BaseModel):
    """Response for routing operation result."""

    success: bool
    source_execution_id: UUID
    target_execution_id: Optional[UUID]
    source_scenario: str
    target_scenario: str
    relation_id: Optional[UUID]
    message: Optional[str]
    workflow_id: Optional[UUID]
    timestamp: datetime


class ExecutionRelationResponse(BaseModel):
    """Response for execution relation."""

    id: UUID
    source_execution_id: UUID
    target_execution_id: UUID
    relation_type: str
    source_scenario: str
    target_scenario: str
    created_at: datetime
    metadata: Dict[str, Any]


class RelationListResponse(BaseModel):
    """Response for list of relations."""

    relations: List[ExecutionRelationResponse]
    total: int


class ScenarioConfigResponse(BaseModel):
    """Response for scenario configuration."""

    scenario: str
    default_workflow_id: Optional[UUID]
    enabled: bool
    description: str
    allowed_targets: List[str]


class ScenarioListResponse(BaseModel):
    """Response for list of scenarios."""

    scenarios: List[ScenarioConfigResponse]
    total: int


class RoutingStatisticsResponse(BaseModel):
    """Response for routing statistics."""

    total_relations: int
    by_source_scenario: Dict[str, int]
    by_relation_type: Dict[str, int]
    configured_scenarios: int
    configured_workflows: int


class RelationTypesResponse(BaseModel):
    """Response listing available relation types."""

    types: List[str]


class HealthCheckResponse(BaseModel):
    """Response for routing service health check."""

    service: str = "routing"
    status: str
    total_relations: int
    configured_scenarios: int
    configured_workflows: int
