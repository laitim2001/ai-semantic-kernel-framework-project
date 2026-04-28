"""
Routing API Routes
==================

REST API endpoints for cross-scenario routing.

Sprint 3 - S3-5: Cross-Scenario Collaboration

Endpoints:
- POST /routing/route - Route execution to another scenario
- POST /routing/relations - Create a relation
- GET /routing/executions/{id}/relations - Get related executions
- GET /routing/executions/{id}/chain - Get execution chain
- GET /routing/relations/{id} - Get specific relation
- DELETE /routing/relations/{id} - Delete a relation
- GET /routing/scenarios - List scenarios
- GET /routing/scenarios/{name} - Get scenario config
- PUT /routing/scenarios/{name} - Configure scenario
- POST /routing/scenarios/{name}/workflow - Set default workflow
- GET /routing/relation-types - List relation types
- GET /routing/statistics - Get statistics
- GET /routing/health - Health check

Author: IPA Platform Team
Created: 2025-11-30
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.routing.schemas import (
    ConfigureScenarioRequest,
    CreateRelationRequest,
    ExecutionRelationResponse,
    HealthCheckResponse,
    RelationListResponse,
    RelationTypesResponse,
    RouteRequest,
    RoutingResultResponse,
    RoutingStatisticsResponse,
    ScenarioConfigResponse,
    ScenarioListResponse,
)
from src.domain.routing import (
    RelationType,
    Scenario,
    ScenarioConfig,
    ScenarioRouter,
)


router = APIRouter(prefix="/routing", tags=["routing"])


# Global service instance
_routing_service: Optional[ScenarioRouter] = None


def get_routing_service() -> ScenarioRouter:
    """Get or create routing service instance."""
    global _routing_service
    if _routing_service is None:
        _routing_service = ScenarioRouter()
    return _routing_service


def set_routing_service(service: ScenarioRouter) -> None:
    """Set routing service instance (for testing)."""
    global _routing_service
    _routing_service = service


# ============================================================================
# Routing Operations
# ============================================================================

@router.post("/route", response_model=RoutingResultResponse)
async def route_to_scenario(request: RouteRequest):
    """
    Route an execution to another business scenario.

    Triggers the default workflow for the target scenario
    and creates a relationship between the executions.
    """
    service = get_routing_service()

    # Parse scenarios
    try:
        source = Scenario(request.source_scenario.lower())
        target = Scenario(request.target_scenario.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {e}")

    # Parse relation type
    try:
        relation_type = RelationType(request.relation_type.lower())
    except ValueError:
        relation_type = RelationType.ROUTED_TO

    result = await service.route_to_scenario(
        source_scenario=source,
        target_scenario=target,
        source_execution_id=request.source_execution_id,
        data=request.data,
        relation_type=relation_type,
        metadata=request.metadata,
    )

    return RoutingResultResponse(
        success=result.success,
        source_execution_id=result.source_execution_id,
        target_execution_id=result.target_execution_id,
        source_scenario=result.source_scenario.value,
        target_scenario=result.target_scenario.value,
        relation_id=result.relation_id,
        message=result.message,
        workflow_id=result.workflow_id,
        timestamp=result.timestamp,
    )


# ============================================================================
# Relation Operations
# ============================================================================

@router.post("/relations", response_model=ExecutionRelationResponse)
async def create_relation(request: CreateRelationRequest):
    """
    Create a relationship between two executions.

    Can optionally create the reverse relationship as well.
    """
    service = get_routing_service()

    # Parse types
    try:
        relation_type = RelationType(request.relation_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid relation type: {request.relation_type}")

    try:
        source_scenario = Scenario(request.source_scenario.lower())
        target_scenario = Scenario(request.target_scenario.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {e}")

    relation = service.create_relation(
        source_execution_id=request.source_execution_id,
        target_execution_id=request.target_execution_id,
        relation_type=relation_type,
        source_scenario=source_scenario,
        target_scenario=target_scenario,
        metadata=request.metadata,
        create_reverse=request.create_reverse,
    )

    return ExecutionRelationResponse(
        id=relation.id,
        source_execution_id=relation.source_execution_id,
        target_execution_id=relation.target_execution_id,
        relation_type=relation.relation_type.value,
        source_scenario=relation.source_scenario.value,
        target_scenario=relation.target_scenario.value,
        created_at=relation.created_at,
        metadata=relation.metadata,
    )


@router.get("/executions/{execution_id}/relations", response_model=RelationListResponse)
async def get_execution_relations(
    execution_id: UUID,
    relation_type: Optional[str] = Query(None, description="Filter by type"),
    direction: str = Query("both", description="outgoing, incoming, or both"),
):
    """
    Get executions related to a given execution.

    Can filter by relation type and direction.
    """
    service = get_routing_service()

    # Parse relation type if provided
    type_filter = None
    if relation_type:
        try:
            type_filter = RelationType(relation_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid relation type: {relation_type}")

    relations = service.get_related_executions(
        execution_id=execution_id,
        relation_type=type_filter,
        direction=direction,
    )

    return RelationListResponse(
        relations=[
            ExecutionRelationResponse(
                id=r.id,
                source_execution_id=r.source_execution_id,
                target_execution_id=r.target_execution_id,
                relation_type=r.relation_type.value,
                source_scenario=r.source_scenario.value,
                target_scenario=r.target_scenario.value,
                created_at=r.created_at,
                metadata=r.metadata,
            )
            for r in relations
        ],
        total=len(relations),
    )


@router.get("/executions/{execution_id}/chain", response_model=RelationListResponse)
async def get_execution_chain(
    execution_id: UUID,
    max_depth: int = Query(10, ge=1, le=50, description="Maximum chain depth"),
):
    """
    Get the full chain of related executions.

    Traverses outgoing relations up to max_depth levels.
    """
    service = get_routing_service()

    chain = service.get_execution_chain(
        execution_id=execution_id,
        max_depth=max_depth,
    )

    return RelationListResponse(
        relations=[
            ExecutionRelationResponse(
                id=r.id,
                source_execution_id=r.source_execution_id,
                target_execution_id=r.target_execution_id,
                relation_type=r.relation_type.value,
                source_scenario=r.source_scenario.value,
                target_scenario=r.target_scenario.value,
                created_at=r.created_at,
                metadata=r.metadata,
            )
            for r in chain
        ],
        total=len(chain),
    )


@router.get("/relations/{relation_id}", response_model=ExecutionRelationResponse)
async def get_relation(relation_id: UUID):
    """Get a specific relation by ID."""
    service = get_routing_service()

    relation = service.get_relation(relation_id)
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    return ExecutionRelationResponse(
        id=relation.id,
        source_execution_id=relation.source_execution_id,
        target_execution_id=relation.target_execution_id,
        relation_type=relation.relation_type.value,
        source_scenario=relation.source_scenario.value,
        target_scenario=relation.target_scenario.value,
        created_at=relation.created_at,
        metadata=relation.metadata,
    )


@router.delete("/relations/{relation_id}")
async def delete_relation(relation_id: UUID):
    """Delete a relation by ID."""
    service = get_routing_service()

    if service.delete_relation(relation_id):
        return {"message": "Relation deleted", "relation_id": str(relation_id)}
    else:
        raise HTTPException(status_code=404, detail="Relation not found")


# ============================================================================
# Scenario Configuration
# ============================================================================

@router.get("/scenarios", response_model=ScenarioListResponse)
async def list_scenarios(
    enabled_only: bool = Query(False, description="Only show enabled scenarios"),
):
    """List all configured scenarios."""
    service = get_routing_service()

    configs = service.list_scenarios(enabled_only=enabled_only)

    return ScenarioListResponse(
        scenarios=[
            ScenarioConfigResponse(
                scenario=c.scenario.value,
                default_workflow_id=c.default_workflow_id,
                enabled=c.enabled,
                description=c.description,
                allowed_targets=[t.value for t in c.allowed_targets],
            )
            for c in configs
        ],
        total=len(configs),
    )


@router.get("/scenarios/{scenario_name}", response_model=ScenarioConfigResponse)
async def get_scenario_config(scenario_name: str):
    """Get configuration for a specific scenario."""
    service = get_routing_service()

    try:
        scenario = Scenario(scenario_name.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {scenario_name}")

    config = service.get_scenario_config(scenario)
    if not config:
        raise HTTPException(status_code=404, detail="Scenario not configured")

    return ScenarioConfigResponse(
        scenario=config.scenario.value,
        default_workflow_id=config.default_workflow_id,
        enabled=config.enabled,
        description=config.description,
        allowed_targets=[t.value for t in config.allowed_targets],
    )


@router.put("/scenarios/{scenario_name}", response_model=ScenarioConfigResponse)
async def configure_scenario(scenario_name: str, request: ConfigureScenarioRequest):
    """Update configuration for a scenario."""
    service = get_routing_service()

    try:
        scenario = Scenario(scenario_name.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {scenario_name}")

    current = service.get_scenario_config(scenario)
    if not current:
        raise HTTPException(status_code=404, detail="Scenario not configured")

    # Parse allowed targets
    allowed_targets = current.allowed_targets
    if request.allowed_targets is not None:
        try:
            allowed_targets = [Scenario(t.lower()) for t in request.allowed_targets]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid target scenario: {e}")

    # Create updated config
    new_config = ScenarioConfig(
        scenario=scenario,
        default_workflow_id=request.default_workflow_id or current.default_workflow_id,
        enabled=request.enabled if request.enabled is not None else current.enabled,
        description=request.description or current.description,
        allowed_targets=allowed_targets,
    )

    service.configure_scenario(scenario, new_config)

    return ScenarioConfigResponse(
        scenario=new_config.scenario.value,
        default_workflow_id=new_config.default_workflow_id,
        enabled=new_config.enabled,
        description=new_config.description,
        allowed_targets=[t.value for t in new_config.allowed_targets],
    )


@router.post("/scenarios/{scenario_name}/workflow")
async def set_default_workflow(scenario_name: str, workflow_id: UUID):
    """Set the default workflow for a scenario."""
    service = get_routing_service()

    try:
        scenario = Scenario(scenario_name.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {scenario_name}")

    service.set_default_workflow(scenario, workflow_id)

    return {
        "message": f"Default workflow set for {scenario_name}",
        "scenario": scenario_name,
        "workflow_id": str(workflow_id),
    }


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/relation-types", response_model=RelationTypesResponse)
async def list_relation_types():
    """List all available relation types."""
    return RelationTypesResponse(
        types=[t.value for t in RelationType]
    )


@router.get("/statistics", response_model=RoutingStatisticsResponse)
async def get_statistics():
    """Get routing statistics."""
    service = get_routing_service()
    stats = service.get_statistics()

    return RoutingStatisticsResponse(
        total_relations=stats["total_relations"],
        by_source_scenario=stats["by_source_scenario"],
        by_relation_type=stats["by_relation_type"],
        configured_scenarios=stats["configured_scenarios"],
        configured_workflows=stats["configured_workflows"],
    )


@router.delete("/relations")
async def clear_all_relations():
    """Clear all relations (admin operation)."""
    service = get_routing_service()
    count = service.clear_relations()

    return {"message": f"Cleared {count} relations", "cleared": count}


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check routing service health."""
    service = get_routing_service()
    stats = service.get_statistics()

    return HealthCheckResponse(
        service="routing",
        status="healthy",
        total_relations=stats["total_relations"],
        configured_scenarios=stats["configured_scenarios"],
        configured_workflows=stats["configured_workflows"],
    )
