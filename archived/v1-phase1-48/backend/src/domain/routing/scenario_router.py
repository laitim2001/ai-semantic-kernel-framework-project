"""
Scenario Router Service
========================

Cross-scenario routing service for workflow orchestration across
different business domains (IT Operations, Customer Service).

Sprint 3 - S3-5: Cross-Scenario Collaboration

Features:
- Scenario-based workflow routing
- Execution relationship tracking
- Default workflow mapping
- Audit logging integration
- Relationship queries

Author: IPA Platform Team
Created: 2025-11-30
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4


class Scenario(str, Enum):
    """Business scenario enumeration."""

    IT_OPERATIONS = "it_operations"
    CUSTOMER_SERVICE = "customer_service"
    FINANCE = "finance"
    HR = "hr"
    SALES = "sales"


class RelationType(str, Enum):
    """Execution relationship types."""

    # Cross-scenario routing
    ROUTED_TO = "routed_to"
    ROUTED_FROM = "routed_from"

    # Workflow relationships
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"

    # Escalation
    ESCALATED_TO = "escalated_to"
    ESCALATED_FROM = "escalated_from"

    # Reference
    REFERENCES = "references"
    REFERENCED_BY = "referenced_by"


class RoutingError(Exception):
    """Exception raised for routing failures."""

    def __init__(
        self,
        message: str,
        source_scenario: Optional[Scenario] = None,
        target_scenario: Optional[Scenario] = None,
        execution_id: Optional[UUID] = None,
    ):
        super().__init__(message)
        self.source_scenario = source_scenario
        self.target_scenario = target_scenario
        self.execution_id = execution_id


@dataclass
class ScenarioConfig:
    """Configuration for a business scenario."""

    scenario: Scenario
    default_workflow_id: Optional[UUID] = None
    enabled: bool = True
    description: str = ""

    # Routing rules
    allowed_targets: List[Scenario] = field(default_factory=list)
    auto_route: bool = False


@dataclass
class ExecutionRelation:
    """Relationship between two executions."""

    id: UUID
    source_execution_id: UUID
    target_execution_id: UUID
    relation_type: RelationType
    source_scenario: Scenario
    target_scenario: Scenario
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "source_execution_id": str(self.source_execution_id),
            "target_execution_id": str(self.target_execution_id),
            "relation_type": self.relation_type.value,
            "source_scenario": self.source_scenario.value,
            "target_scenario": self.target_scenario.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RoutingResult:
    """Result of a routing operation."""

    success: bool
    source_execution_id: UUID
    target_execution_id: Optional[UUID]
    source_scenario: Scenario
    target_scenario: Scenario
    relation_id: Optional[UUID] = None
    message: Optional[str] = None
    workflow_id: Optional[UUID] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "source_execution_id": str(self.source_execution_id),
            "target_execution_id": str(self.target_execution_id) if self.target_execution_id else None,
            "source_scenario": self.source_scenario.value,
            "target_scenario": self.target_scenario.value,
            "relation_id": str(self.relation_id) if self.relation_id else None,
            "message": self.message,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "timestamp": self.timestamp.isoformat(),
        }


class ScenarioRouter:
    """
    Cross-scenario routing service.

    Manages routing of workflows between different business scenarios
    and tracks relationships between executions.
    """

    def __init__(
        self,
        execution_callback: Optional[Callable[[UUID, Dict[str, Any]], UUID]] = None,
        audit_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
    ):
        """
        Initialize scenario router.

        Args:
            execution_callback: Optional callback to execute workflows
            audit_callback: Optional callback for audit logging
        """
        self._execution_callback = execution_callback
        self._audit_callback = audit_callback

        # In-memory storage (MVP)
        self._scenario_configs: Dict[Scenario, ScenarioConfig] = {}
        self._relations: List[ExecutionRelation] = []
        self._workflow_mappings: Dict[Scenario, UUID] = {}

        # Initialize default configs
        self._init_default_configs()

    def _init_default_configs(self) -> None:
        """Initialize default scenario configurations."""
        self._scenario_configs = {
            Scenario.IT_OPERATIONS: ScenarioConfig(
                scenario=Scenario.IT_OPERATIONS,
                enabled=True,
                description="IT Operations: incident management, system monitoring",
                allowed_targets=[Scenario.CUSTOMER_SERVICE, Scenario.FINANCE],
            ),
            Scenario.CUSTOMER_SERVICE: ScenarioConfig(
                scenario=Scenario.CUSTOMER_SERVICE,
                enabled=True,
                description="Customer Service: ticket handling, customer inquiries",
                allowed_targets=[Scenario.IT_OPERATIONS, Scenario.SALES],
            ),
            Scenario.FINANCE: ScenarioConfig(
                scenario=Scenario.FINANCE,
                enabled=True,
                description="Finance: billing, refunds, financial operations",
                allowed_targets=[Scenario.CUSTOMER_SERVICE, Scenario.SALES],
            ),
            Scenario.HR: ScenarioConfig(
                scenario=Scenario.HR,
                enabled=True,
                description="HR: employee management, onboarding",
                allowed_targets=[Scenario.IT_OPERATIONS],
            ),
            Scenario.SALES: ScenarioConfig(
                scenario=Scenario.SALES,
                enabled=True,
                description="Sales: quotes, orders, customer engagement",
                allowed_targets=[Scenario.CUSTOMER_SERVICE, Scenario.FINANCE],
            ),
        }

    # =========================================================================
    # Configuration Management
    # =========================================================================

    def configure_scenario(
        self,
        scenario: Scenario,
        config: ScenarioConfig,
    ) -> None:
        """Configure a scenario."""
        self._scenario_configs[scenario] = config

    def get_scenario_config(self, scenario: Scenario) -> Optional[ScenarioConfig]:
        """Get scenario configuration."""
        return self._scenario_configs.get(scenario)

    def list_scenarios(self, enabled_only: bool = False) -> List[ScenarioConfig]:
        """List all scenarios."""
        configs = list(self._scenario_configs.values())
        if enabled_only:
            configs = [c for c in configs if c.enabled]
        return configs

    def set_default_workflow(self, scenario: Scenario, workflow_id: UUID) -> None:
        """Set default workflow for a scenario."""
        self._workflow_mappings[scenario] = workflow_id
        if scenario in self._scenario_configs:
            self._scenario_configs[scenario].default_workflow_id = workflow_id

    def get_default_workflow(self, scenario: Scenario) -> Optional[UUID]:
        """Get default workflow for a scenario."""
        return self._workflow_mappings.get(scenario)

    # =========================================================================
    # Routing Operations
    # =========================================================================

    async def route_to_scenario(
        self,
        source_scenario: Scenario,
        target_scenario: Scenario,
        source_execution_id: UUID,
        data: Dict[str, Any],
        relation_type: RelationType = RelationType.ROUTED_TO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RoutingResult:
        """
        Route an execution to a target scenario.

        Args:
            source_scenario: Source business scenario
            target_scenario: Target business scenario
            source_execution_id: Source execution ID
            data: Data to pass to target workflow
            relation_type: Type of relationship to create
            metadata: Optional additional metadata

        Returns:
            RoutingResult with routing outcome
        """
        timestamp = datetime.utcnow()

        # Validate scenarios
        source_config = self._scenario_configs.get(source_scenario)
        target_config = self._scenario_configs.get(target_scenario)

        if not source_config or not source_config.enabled:
            return RoutingResult(
                success=False,
                source_execution_id=source_execution_id,
                target_execution_id=None,
                source_scenario=source_scenario,
                target_scenario=target_scenario,
                message=f"Source scenario {source_scenario.value} is not enabled",
                timestamp=timestamp,
            )

        if not target_config or not target_config.enabled:
            return RoutingResult(
                success=False,
                source_execution_id=source_execution_id,
                target_execution_id=None,
                source_scenario=source_scenario,
                target_scenario=target_scenario,
                message=f"Target scenario {target_scenario.value} is not enabled",
                timestamp=timestamp,
            )

        # Check routing permission
        if target_scenario not in source_config.allowed_targets:
            return RoutingResult(
                success=False,
                source_execution_id=source_execution_id,
                target_execution_id=None,
                source_scenario=source_scenario,
                target_scenario=target_scenario,
                message=f"Routing from {source_scenario.value} to {target_scenario.value} is not allowed",
                timestamp=timestamp,
            )

        # Get target workflow
        target_workflow_id = self._workflow_mappings.get(target_scenario)
        if not target_workflow_id:
            return RoutingResult(
                success=False,
                source_execution_id=source_execution_id,
                target_execution_id=None,
                source_scenario=source_scenario,
                target_scenario=target_scenario,
                message=f"No default workflow configured for {target_scenario.value}",
                timestamp=timestamp,
            )

        # Prepare data with routing context
        enriched_data = {
            **data,
            "_routing": {
                "source_scenario": source_scenario.value,
                "source_execution_id": str(source_execution_id),
                "routed_at": timestamp.isoformat(),
            },
        }

        # Execute target workflow (via callback or mock)
        target_execution_id: Optional[UUID] = None

        if self._execution_callback:
            try:
                target_execution_id = await self._async_execute(
                    target_workflow_id,
                    enriched_data,
                )
            except Exception as e:
                return RoutingResult(
                    success=False,
                    source_execution_id=source_execution_id,
                    target_execution_id=None,
                    source_scenario=source_scenario,
                    target_scenario=target_scenario,
                    workflow_id=target_workflow_id,
                    message=f"Failed to execute target workflow: {e}",
                    timestamp=timestamp,
                )
        else:
            # Mock execution for MVP
            target_execution_id = uuid4()

        # Create relationship
        relation = ExecutionRelation(
            id=uuid4(),
            source_execution_id=source_execution_id,
            target_execution_id=target_execution_id,
            relation_type=relation_type,
            source_scenario=source_scenario,
            target_scenario=target_scenario,
            created_at=timestamp,
            metadata=metadata or {},
        )
        self._relations.append(relation)

        # Create reverse relationship
        reverse_type = self._get_reverse_relation(relation_type)
        if reverse_type:
            reverse_relation = ExecutionRelation(
                id=uuid4(),
                source_execution_id=target_execution_id,
                target_execution_id=source_execution_id,
                relation_type=reverse_type,
                source_scenario=target_scenario,
                target_scenario=source_scenario,
                created_at=timestamp,
                metadata=metadata or {},
            )
            self._relations.append(reverse_relation)

        # Audit logging
        if self._audit_callback:
            await self._async_audit(
                action="scenario.routed",
                actor="system",
                details={
                    "source_scenario": source_scenario.value,
                    "target_scenario": target_scenario.value,
                    "source_execution_id": str(source_execution_id),
                    "target_execution_id": str(target_execution_id),
                    "target_workflow_id": str(target_workflow_id),
                    "relation_type": relation_type.value,
                },
            )

        return RoutingResult(
            success=True,
            source_execution_id=source_execution_id,
            target_execution_id=target_execution_id,
            source_scenario=source_scenario,
            target_scenario=target_scenario,
            relation_id=relation.id,
            workflow_id=target_workflow_id,
            message="Successfully routed to target scenario",
            timestamp=timestamp,
        )

    async def _async_execute(
        self,
        workflow_id: UUID,
        data: Dict[str, Any],
    ) -> UUID:
        """Execute workflow asynchronously."""
        import asyncio

        if asyncio.iscoroutinefunction(self._execution_callback):
            return await self._execution_callback(workflow_id, data)
        return self._execution_callback(workflow_id, data)

    async def _async_audit(
        self,
        action: str,
        actor: str,
        details: Dict[str, Any],
    ) -> None:
        """Log audit asynchronously."""
        import asyncio

        if asyncio.iscoroutinefunction(self._audit_callback):
            await self._audit_callback(action, actor, details)
        else:
            self._audit_callback(action, actor, details)

    def _get_reverse_relation(self, relation_type: RelationType) -> Optional[RelationType]:
        """Get reverse relation type."""
        reverse_map = {
            RelationType.ROUTED_TO: RelationType.ROUTED_FROM,
            RelationType.ROUTED_FROM: RelationType.ROUTED_TO,
            RelationType.PARENT: RelationType.CHILD,
            RelationType.CHILD: RelationType.PARENT,
            RelationType.ESCALATED_TO: RelationType.ESCALATED_FROM,
            RelationType.ESCALATED_FROM: RelationType.ESCALATED_TO,
            RelationType.REFERENCES: RelationType.REFERENCED_BY,
            RelationType.REFERENCED_BY: RelationType.REFERENCES,
        }
        return reverse_map.get(relation_type)

    # =========================================================================
    # Relationship Queries
    # =========================================================================

    def get_related_executions(
        self,
        execution_id: UUID,
        relation_type: Optional[RelationType] = None,
        direction: str = "outgoing",  # "outgoing", "incoming", "both"
    ) -> List[ExecutionRelation]:
        """
        Get executions related to a given execution.

        Args:
            execution_id: Execution ID to query
            relation_type: Optional filter by relation type
            direction: "outgoing" (source), "incoming" (target), or "both"

        Returns:
            List of execution relations
        """
        results = []

        for relation in self._relations:
            match = False

            if direction in ("outgoing", "both"):
                if relation.source_execution_id == execution_id:
                    match = True

            if direction in ("incoming", "both"):
                if relation.target_execution_id == execution_id:
                    match = True

            if match:
                if relation_type is None or relation.relation_type == relation_type:
                    results.append(relation)

        return results

    def get_execution_chain(
        self,
        execution_id: UUID,
        max_depth: int = 10,
    ) -> List[ExecutionRelation]:
        """
        Get the full chain of related executions.

        Args:
            execution_id: Starting execution ID
            max_depth: Maximum recursion depth

        Returns:
            List of all relations in the chain
        """
        visited: set = set()
        chain: List[ExecutionRelation] = []

        def traverse(exec_id: UUID, depth: int) -> None:
            if depth > max_depth or exec_id in visited:
                return

            visited.add(exec_id)

            for relation in self._relations:
                if relation.source_execution_id == exec_id:
                    if relation not in chain:
                        chain.append(relation)
                    traverse(relation.target_execution_id, depth + 1)

        traverse(execution_id, 0)
        return chain

    def get_relation(self, relation_id: UUID) -> Optional[ExecutionRelation]:
        """Get a specific relation by ID."""
        for relation in self._relations:
            if relation.id == relation_id:
                return relation
        return None

    def count_relations(
        self,
        scenario: Optional[Scenario] = None,
        relation_type: Optional[RelationType] = None,
    ) -> int:
        """Count relations with optional filtering."""
        count = 0
        for relation in self._relations:
            if scenario and relation.source_scenario != scenario:
                continue
            if relation_type and relation.relation_type != relation_type:
                continue
            count += 1
        return count

    # =========================================================================
    # Relationship Management
    # =========================================================================

    def create_relation(
        self,
        source_execution_id: UUID,
        target_execution_id: UUID,
        relation_type: RelationType,
        source_scenario: Scenario,
        target_scenario: Scenario,
        metadata: Optional[Dict[str, Any]] = None,
        create_reverse: bool = True,
    ) -> ExecutionRelation:
        """
        Create a relationship between two executions.

        Args:
            source_execution_id: Source execution ID
            target_execution_id: Target execution ID
            relation_type: Type of relationship
            source_scenario: Source scenario
            target_scenario: Target scenario
            metadata: Optional metadata
            create_reverse: Whether to create reverse relation

        Returns:
            Created ExecutionRelation
        """
        timestamp = datetime.utcnow()

        relation = ExecutionRelation(
            id=uuid4(),
            source_execution_id=source_execution_id,
            target_execution_id=target_execution_id,
            relation_type=relation_type,
            source_scenario=source_scenario,
            target_scenario=target_scenario,
            created_at=timestamp,
            metadata=metadata or {},
        )
        self._relations.append(relation)

        if create_reverse:
            reverse_type = self._get_reverse_relation(relation_type)
            if reverse_type:
                reverse_relation = ExecutionRelation(
                    id=uuid4(),
                    source_execution_id=target_execution_id,
                    target_execution_id=source_execution_id,
                    relation_type=reverse_type,
                    source_scenario=target_scenario,
                    target_scenario=source_scenario,
                    created_at=timestamp,
                    metadata=metadata or {},
                )
                self._relations.append(reverse_relation)

        return relation

    def delete_relation(self, relation_id: UUID) -> bool:
        """Delete a relation by ID."""
        for i, relation in enumerate(self._relations):
            if relation.id == relation_id:
                del self._relations[i]
                return True
        return False

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get routing statistics."""
        by_scenario: Dict[str, int] = {}
        by_relation_type: Dict[str, int] = {}

        for relation in self._relations:
            scenario_key = relation.source_scenario.value
            by_scenario[scenario_key] = by_scenario.get(scenario_key, 0) + 1

            type_key = relation.relation_type.value
            by_relation_type[type_key] = by_relation_type.get(type_key, 0) + 1

        return {
            "total_relations": len(self._relations),
            "by_source_scenario": by_scenario,
            "by_relation_type": by_relation_type,
            "configured_scenarios": len(self._scenario_configs),
            "configured_workflows": len(self._workflow_mappings),
        }

    def clear_relations(self) -> int:
        """Clear all relations. Returns count cleared."""
        count = len(self._relations)
        self._relations = []
        return count
