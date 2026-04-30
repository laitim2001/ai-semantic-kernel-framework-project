"""
Routing Unit Tests
==================

Unit tests for cross-scenario routing service.

Sprint 3 - S3-5: Cross-Scenario Collaboration

Test Coverage:
- ScenarioConfig creation
- ScenarioRouter configuration
- Routing operations
- Relation management
- Execution chain queries
- Statistics

Author: IPA Platform Team
Created: 2025-11-30
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.domain.routing import (
    ExecutionRelation,
    RelationType,
    RoutingError,
    RoutingResult,
    Scenario,
    ScenarioConfig,
    ScenarioRouter,
)


# ============================================================================
# Scenario Tests
# ============================================================================

class TestScenario:
    """Tests for Scenario enum."""

    def test_scenario_values(self):
        """Test scenario enum values."""
        assert Scenario.IT_OPERATIONS.value == "it_operations"
        assert Scenario.CUSTOMER_SERVICE.value == "customer_service"
        assert Scenario.FINANCE.value == "finance"
        assert Scenario.HR.value == "hr"
        assert Scenario.SALES.value == "sales"

    def test_scenario_from_string(self):
        """Test scenario creation from string."""
        assert Scenario("it_operations") == Scenario.IT_OPERATIONS
        assert Scenario("customer_service") == Scenario.CUSTOMER_SERVICE


class TestRelationType:
    """Tests for RelationType enum."""

    def test_relation_type_values(self):
        """Test relation type values."""
        assert RelationType.ROUTED_TO.value == "routed_to"
        assert RelationType.ROUTED_FROM.value == "routed_from"
        assert RelationType.PARENT.value == "parent"
        assert RelationType.CHILD.value == "child"
        assert RelationType.ESCALATED_TO.value == "escalated_to"


# ============================================================================
# ScenarioConfig Tests
# ============================================================================

class TestScenarioConfig:
    """Tests for ScenarioConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = ScenarioConfig(scenario=Scenario.IT_OPERATIONS)

        assert config.scenario == Scenario.IT_OPERATIONS
        assert config.default_workflow_id is None
        assert config.enabled is True
        assert config.description == ""
        assert config.allowed_targets == []

    def test_custom_config(self):
        """Test custom configuration."""
        workflow_id = uuid4()
        config = ScenarioConfig(
            scenario=Scenario.CUSTOMER_SERVICE,
            default_workflow_id=workflow_id,
            enabled=True,
            description="Customer support workflows",
            allowed_targets=[Scenario.IT_OPERATIONS, Scenario.SALES],
        )

        assert config.default_workflow_id == workflow_id
        assert config.description == "Customer support workflows"
        assert len(config.allowed_targets) == 2


# ============================================================================
# ExecutionRelation Tests
# ============================================================================

class TestExecutionRelation:
    """Tests for ExecutionRelation."""

    def test_relation_creation(self):
        """Test relation creation."""
        relation = ExecutionRelation(
            id=uuid4(),
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            created_at=datetime.utcnow(),
        )

        assert relation.relation_type == RelationType.ROUTED_TO
        assert relation.source_scenario == Scenario.CUSTOMER_SERVICE
        assert relation.target_scenario == Scenario.IT_OPERATIONS
        assert relation.metadata == {}

    def test_relation_with_metadata(self):
        """Test relation with metadata."""
        relation = ExecutionRelation(
            id=uuid4(),
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            relation_type=RelationType.ESCALATED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            created_at=datetime.utcnow(),
            metadata={"reason": "high priority", "urgency": "critical"},
        )

        assert relation.metadata["reason"] == "high priority"
        assert relation.metadata["urgency"] == "critical"

    def test_relation_to_dict(self):
        """Test relation serialization."""
        relation_id = uuid4()
        source_id = uuid4()
        target_id = uuid4()

        relation = ExecutionRelation(
            id=relation_id,
            source_execution_id=source_id,
            target_execution_id=target_id,
            relation_type=RelationType.PARENT,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.IT_OPERATIONS,
            created_at=datetime.utcnow(),
        )

        result = relation.to_dict()

        assert result["id"] == str(relation_id)
        assert result["source_execution_id"] == str(source_id)
        assert result["target_execution_id"] == str(target_id)
        assert result["relation_type"] == "parent"


# ============================================================================
# RoutingResult Tests
# ============================================================================

class TestRoutingResult:
    """Tests for RoutingResult."""

    def test_successful_result(self):
        """Test successful routing result."""
        result = RoutingResult(
            success=True,
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            relation_id=uuid4(),
            message="Successfully routed",
            workflow_id=uuid4(),
        )

        assert result.success is True
        assert result.message == "Successfully routed"

    def test_failed_result(self):
        """Test failed routing result."""
        result = RoutingResult(
            success=False,
            source_execution_id=uuid4(),
            target_execution_id=None,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.HR,
            message="Routing not allowed",
        )

        assert result.success is False
        assert result.target_execution_id is None

    def test_result_to_dict(self):
        """Test result serialization."""
        result = RoutingResult(
            success=True,
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.CUSTOMER_SERVICE,
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["source_scenario"] == "it_operations"
        assert result_dict["target_scenario"] == "customer_service"


# ============================================================================
# ScenarioRouter Tests
# ============================================================================

class TestScenarioRouter:
    """Tests for ScenarioRouter."""

    @pytest.fixture
    def router(self):
        """Create router instance."""
        return ScenarioRouter()

    @pytest.fixture
    def router_with_workflow(self):
        """Create router with workflow mapping."""
        router = ScenarioRouter()
        workflow_id = uuid4()
        router.set_default_workflow(Scenario.IT_OPERATIONS, workflow_id)
        return router, workflow_id

    # -------------------------------------------------------------------------
    # Configuration Tests
    # -------------------------------------------------------------------------

    def test_default_configs(self, router):
        """Test default scenario configurations."""
        configs = router.list_scenarios()

        assert len(configs) == 5  # IT, CS, Finance, HR, Sales
        assert any(c.scenario == Scenario.IT_OPERATIONS for c in configs)
        assert any(c.scenario == Scenario.CUSTOMER_SERVICE for c in configs)

    def test_get_scenario_config(self, router):
        """Test getting scenario configuration."""
        config = router.get_scenario_config(Scenario.IT_OPERATIONS)

        assert config is not None
        assert config.scenario == Scenario.IT_OPERATIONS
        assert config.enabled is True

    def test_configure_scenario(self, router):
        """Test scenario configuration update."""
        new_config = ScenarioConfig(
            scenario=Scenario.IT_OPERATIONS,
            enabled=False,
            description="Disabled for maintenance",
        )

        router.configure_scenario(Scenario.IT_OPERATIONS, new_config)

        config = router.get_scenario_config(Scenario.IT_OPERATIONS)
        assert config.enabled is False
        assert config.description == "Disabled for maintenance"

    def test_set_default_workflow(self, router):
        """Test setting default workflow."""
        workflow_id = uuid4()
        router.set_default_workflow(Scenario.CUSTOMER_SERVICE, workflow_id)

        assert router.get_default_workflow(Scenario.CUSTOMER_SERVICE) == workflow_id

    def test_list_scenarios_enabled_only(self, router):
        """Test listing only enabled scenarios."""
        # Disable one scenario
        config = router.get_scenario_config(Scenario.HR)
        config.enabled = False
        router.configure_scenario(Scenario.HR, config)

        enabled = router.list_scenarios(enabled_only=True)
        disabled = router.list_scenarios(enabled_only=False)

        assert len(enabled) == 4
        assert len(disabled) == 5

    # -------------------------------------------------------------------------
    # Routing Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_route_to_scenario_success(self, router_with_workflow):
        """Test successful routing."""
        router, workflow_id = router_with_workflow
        source_id = uuid4()

        result = await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            source_execution_id=source_id,
            data={"ticket_id": "T-123"},
        )

        assert result.success is True
        assert result.target_execution_id is not None
        assert result.workflow_id == workflow_id
        assert result.relation_id is not None

    @pytest.mark.asyncio
    async def test_route_disabled_source(self, router):
        """Test routing from disabled scenario."""
        # Disable source scenario
        config = ScenarioConfig(
            scenario=Scenario.CUSTOMER_SERVICE,
            enabled=False,
        )
        router.configure_scenario(Scenario.CUSTOMER_SERVICE, config)

        result = await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            source_execution_id=uuid4(),
            data={},
        )

        assert result.success is False
        assert "not enabled" in result.message

    @pytest.mark.asyncio
    async def test_route_disabled_target(self, router):
        """Test routing to disabled scenario."""
        # Disable target scenario
        config = ScenarioConfig(
            scenario=Scenario.IT_OPERATIONS,
            enabled=False,
        )
        router.configure_scenario(Scenario.IT_OPERATIONS, config)

        result = await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            source_execution_id=uuid4(),
            data={},
        )

        assert result.success is False
        assert "not enabled" in result.message

    @pytest.mark.asyncio
    async def test_route_not_allowed(self, router_with_workflow):
        """Test routing to non-allowed target."""
        router, _ = router_with_workflow

        # HR is not in CS's allowed targets by default
        result = await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.HR,
            source_execution_id=uuid4(),
            data={},
        )

        assert result.success is False
        assert "not allowed" in result.message

    @pytest.mark.asyncio
    async def test_route_no_workflow_configured(self, router):
        """Test routing when no workflow is configured."""
        # Don't set any workflow

        result = await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            source_execution_id=uuid4(),
            data={},
        )

        assert result.success is False
        assert "No default workflow" in result.message

    @pytest.mark.asyncio
    async def test_route_creates_relations(self, router_with_workflow):
        """Test that routing creates bidirectional relations."""
        router, _ = router_with_workflow
        source_id = uuid4()

        await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            source_execution_id=source_id,
            data={},
        )

        # Check relations were created
        outgoing = router.get_related_executions(source_id, direction="outgoing")
        assert len(outgoing) == 1
        assert outgoing[0].relation_type == RelationType.ROUTED_TO

    @pytest.mark.asyncio
    async def test_route_with_metadata(self, router_with_workflow):
        """Test routing with metadata."""
        router, _ = router_with_workflow

        result = await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            source_execution_id=uuid4(),
            data={},
            metadata={"priority": "high", "sla": "4h"},
        )

        assert result.success is True

        # Check metadata was stored
        relation = router.get_relation(result.relation_id)
        assert relation.metadata["priority"] == "high"

    @pytest.mark.asyncio
    async def test_route_with_execution_callback(self):
        """Test routing with execution callback."""
        target_exec_id = uuid4()
        callback = AsyncMock(return_value=target_exec_id)

        router = ScenarioRouter(execution_callback=callback)
        workflow_id = uuid4()
        router.set_default_workflow(Scenario.IT_OPERATIONS, workflow_id)

        result = await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            source_execution_id=uuid4(),
            data={"key": "value"},
        )

        assert result.success is True
        assert result.target_execution_id == target_exec_id
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_with_audit_callback(self, router_with_workflow):
        """Test routing with audit callback."""
        router, _ = router_with_workflow
        audit_callback = MagicMock()
        router._audit_callback = audit_callback

        await router.route_to_scenario(
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            source_execution_id=uuid4(),
            data={},
        )

        audit_callback.assert_called_once()

    # -------------------------------------------------------------------------
    # Relation Management Tests
    # -------------------------------------------------------------------------

    def test_create_relation(self, router):
        """Test creating a relation."""
        source_id = uuid4()
        target_id = uuid4()

        relation = router.create_relation(
            source_execution_id=source_id,
            target_execution_id=target_id,
            relation_type=RelationType.PARENT,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.IT_OPERATIONS,
        )

        assert relation.source_execution_id == source_id
        assert relation.target_execution_id == target_id
        assert relation.relation_type == RelationType.PARENT

    def test_create_relation_with_reverse(self, router):
        """Test creating relation with reverse."""
        source_id = uuid4()
        target_id = uuid4()

        router.create_relation(
            source_execution_id=source_id,
            target_execution_id=target_id,
            relation_type=RelationType.PARENT,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=True,
        )

        # Check both relations exist
        outgoing = router.get_related_executions(source_id, direction="outgoing")
        incoming = router.get_related_executions(source_id, direction="incoming")

        assert len(outgoing) == 1
        assert len(incoming) == 1
        assert outgoing[0].relation_type == RelationType.PARENT
        assert incoming[0].relation_type == RelationType.CHILD

    def test_create_relation_without_reverse(self, router):
        """Test creating relation without reverse."""
        source_id = uuid4()
        target_id = uuid4()

        router.create_relation(
            source_execution_id=source_id,
            target_execution_id=target_id,
            relation_type=RelationType.REFERENCES,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.CUSTOMER_SERVICE,
            create_reverse=False,
        )

        # Only one relation should exist
        count = router.count_relations()
        assert count == 1

    def test_get_relation(self, router):
        """Test getting relation by ID."""
        source_id = uuid4()
        target_id = uuid4()

        created = router.create_relation(
            source_execution_id=source_id,
            target_execution_id=target_id,
            relation_type=RelationType.SIBLING,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        found = router.get_relation(created.id)

        assert found is not None
        assert found.id == created.id

    def test_get_relation_not_found(self, router):
        """Test getting non-existent relation."""
        found = router.get_relation(uuid4())
        assert found is None

    def test_delete_relation(self, router):
        """Test deleting a relation."""
        relation = router.create_relation(
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            relation_type=RelationType.REFERENCES,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        assert router.delete_relation(relation.id) is True
        assert router.get_relation(relation.id) is None

    def test_delete_relation_not_found(self, router):
        """Test deleting non-existent relation."""
        assert router.delete_relation(uuid4()) is False

    # -------------------------------------------------------------------------
    # Query Tests
    # -------------------------------------------------------------------------

    def test_get_related_outgoing(self, router):
        """Test getting outgoing relations."""
        source_id = uuid4()

        router.create_relation(
            source_execution_id=source_id,
            target_execution_id=uuid4(),
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        relations = router.get_related_executions(source_id, direction="outgoing")

        assert len(relations) == 1
        assert relations[0].source_execution_id == source_id

    def test_get_related_incoming(self, router):
        """Test getting incoming relations."""
        target_id = uuid4()

        router.create_relation(
            source_execution_id=uuid4(),
            target_execution_id=target_id,
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        relations = router.get_related_executions(target_id, direction="incoming")

        assert len(relations) == 1
        assert relations[0].target_execution_id == target_id

    def test_get_related_both_directions(self, router):
        """Test getting relations in both directions."""
        exec_id = uuid4()

        # Create outgoing
        router.create_relation(
            source_execution_id=exec_id,
            target_execution_id=uuid4(),
            relation_type=RelationType.PARENT,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        # Create incoming
        router.create_relation(
            source_execution_id=uuid4(),
            target_execution_id=exec_id,
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        relations = router.get_related_executions(exec_id, direction="both")

        assert len(relations) == 2

    def test_get_related_filtered_by_type(self, router):
        """Test filtering relations by type."""
        source_id = uuid4()

        # Create different relation types
        router.create_relation(
            source_execution_id=source_id,
            target_execution_id=uuid4(),
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        router.create_relation(
            source_execution_id=source_id,
            target_execution_id=uuid4(),
            relation_type=RelationType.REFERENCES,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.FINANCE,
            create_reverse=False,
        )

        routed = router.get_related_executions(
            source_id,
            relation_type=RelationType.ROUTED_TO,
            direction="outgoing",
        )

        assert len(routed) == 1
        assert routed[0].relation_type == RelationType.ROUTED_TO

    def test_get_execution_chain(self, router):
        """Test getting execution chain."""
        exec1 = uuid4()
        exec2 = uuid4()
        exec3 = uuid4()

        # Create chain: exec1 -> exec2 -> exec3
        router.create_relation(
            source_execution_id=exec1,
            target_execution_id=exec2,
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        router.create_relation(
            source_execution_id=exec2,
            target_execution_id=exec3,
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.FINANCE,
            create_reverse=False,
        )

        chain = router.get_execution_chain(exec1)

        assert len(chain) == 2

    def test_get_execution_chain_max_depth(self, router):
        """Test execution chain with max depth limit."""
        # Create a long chain
        prev_id = uuid4()
        for _ in range(5):
            next_id = uuid4()
            router.create_relation(
                source_execution_id=prev_id,
                target_execution_id=next_id,
                relation_type=RelationType.ROUTED_TO,
                source_scenario=Scenario.IT_OPERATIONS,
                target_scenario=Scenario.IT_OPERATIONS,
                create_reverse=False,
            )
            prev_id = next_id

        # Get chain with limited depth
        chain = router.get_execution_chain(prev_id, max_depth=2)

        # Should not exceed max depth
        assert len(chain) <= 2

    # -------------------------------------------------------------------------
    # Statistics Tests
    # -------------------------------------------------------------------------

    def test_statistics_empty(self, router):
        """Test statistics with no relations."""
        stats = router.get_statistics()

        assert stats["total_relations"] == 0
        assert stats["configured_scenarios"] == 5

    def test_statistics_with_relations(self, router):
        """Test statistics with relations."""
        # Create some relations
        router.create_relation(
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        router.create_relation(
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.SALES,
            create_reverse=False,
        )

        stats = router.get_statistics()

        assert stats["total_relations"] == 2
        assert stats["by_source_scenario"]["customer_service"] == 2
        assert stats["by_relation_type"]["routed_to"] == 2

    def test_count_relations(self, router):
        """Test counting relations."""
        router.create_relation(
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            relation_type=RelationType.ROUTED_TO,
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        router.create_relation(
            source_execution_id=uuid4(),
            target_execution_id=uuid4(),
            relation_type=RelationType.PARENT,
            source_scenario=Scenario.IT_OPERATIONS,
            target_scenario=Scenario.IT_OPERATIONS,
            create_reverse=False,
        )

        assert router.count_relations() == 2
        assert router.count_relations(scenario=Scenario.CUSTOMER_SERVICE) == 1
        assert router.count_relations(relation_type=RelationType.PARENT) == 1

    def test_clear_relations(self, router):
        """Test clearing all relations."""
        # Create some relations
        for _ in range(3):
            router.create_relation(
                source_execution_id=uuid4(),
                target_execution_id=uuid4(),
                relation_type=RelationType.ROUTED_TO,
                source_scenario=Scenario.CUSTOMER_SERVICE,
                target_scenario=Scenario.IT_OPERATIONS,
                create_reverse=False,
            )

        count = router.clear_relations()

        assert count == 3
        assert router.count_relations() == 0


# ============================================================================
# Exception Tests
# ============================================================================

class TestRoutingError:
    """Tests for RoutingError exception."""

    def test_error_creation(self):
        """Test error creation."""
        error = RoutingError(
            "Routing failed",
            source_scenario=Scenario.CUSTOMER_SERVICE,
            target_scenario=Scenario.IT_OPERATIONS,
            execution_id=uuid4(),
        )

        assert str(error) == "Routing failed"
        assert error.source_scenario == Scenario.CUSTOMER_SERVICE
        assert error.target_scenario == Scenario.IT_OPERATIONS

    def test_error_minimal(self):
        """Test error with minimal info."""
        error = RoutingError("Simple error")

        assert str(error) == "Simple error"
        assert error.source_scenario is None
