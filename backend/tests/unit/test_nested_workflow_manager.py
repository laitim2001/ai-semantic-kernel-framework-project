# =============================================================================
# IPA Platform - Nested Workflow Manager Tests
# =============================================================================
# Sprint 11: S11-1 NestedWorkflowManager Tests
#
# Unit tests for nested workflow management including:
# - Workflow registration and configuration
# - Cycle detection
# - Depth limiting
# - Context management
# - Execution tree visualization
# =============================================================================

import pytest
from uuid import uuid4
from datetime import datetime

from src.domain.orchestration.nested import (
    NestedWorkflowManager,
    NestedWorkflowConfig,
    NestedWorkflowType,
    WorkflowScope,
    SubWorkflowReference,
    NestedExecutionContext,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def manager():
    """Create a fresh NestedWorkflowManager instance."""
    return NestedWorkflowManager()


@pytest.fixture
def sample_workflow_id():
    """Generate a sample workflow ID."""
    return uuid4()


@pytest.fixture
def sample_config(sample_workflow_id):
    """Create a sample nested workflow configuration."""
    return NestedWorkflowConfig(
        parent_workflow_id=sample_workflow_id,
        workflow_type=NestedWorkflowType.REFERENCE,
        scope=WorkflowScope.INHERITED,
        max_depth=5,
        timeout_seconds=300,
    )


# =============================================================================
# Configuration Tests
# =============================================================================


class TestNestedWorkflowConfig:
    """Tests for NestedWorkflowConfig."""

    def test_config_creation(self, sample_workflow_id):
        """Test configuration creation with defaults."""
        config = NestedWorkflowConfig(
            parent_workflow_id=sample_workflow_id,
        )
        assert config.parent_workflow_id == sample_workflow_id
        assert config.workflow_type == NestedWorkflowType.REFERENCE
        assert config.scope == WorkflowScope.INHERITED
        assert config.max_depth == 10
        assert config.timeout_seconds == 600

    def test_config_custom_values(self, sample_workflow_id):
        """Test configuration with custom values."""
        config = NestedWorkflowConfig(
            parent_workflow_id=sample_workflow_id,
            workflow_type=NestedWorkflowType.RECURSIVE,
            scope=WorkflowScope.ISOLATED,
            max_depth=20,
            timeout_seconds=1200,
            metadata={"key": "value"},
        )
        assert config.workflow_type == NestedWorkflowType.RECURSIVE
        assert config.scope == WorkflowScope.ISOLATED
        assert config.max_depth == 20
        assert config.timeout_seconds == 1200
        assert config.metadata["key"] == "value"

    def test_config_to_dict(self, sample_config):
        """Test configuration serialization."""
        result = sample_config.to_dict()
        assert "config_id" in result
        assert "parent_workflow_id" in result
        assert result["workflow_type"] == "reference"
        assert result["scope"] == "inherited"


# =============================================================================
# Manager Tests
# =============================================================================


class TestNestedWorkflowManager:
    """Tests for NestedWorkflowManager."""

    @pytest.mark.asyncio
    async def test_register_nested_workflow(self, manager, sample_workflow_id, sample_config):
        """Test registering a nested workflow."""
        sub_workflow_id = uuid4()

        result = await manager.register_nested_workflow(
            parent_workflow_id=sample_workflow_id,
            sub_workflow_id=sub_workflow_id,
            config=sample_config,
        )

        assert "reference" in result
        assert "config" in result
        assert result["config"]["parent_workflow_id"] == str(sample_workflow_id)

    @pytest.mark.asyncio
    async def test_register_multiple_nested_workflows(self, manager, sample_workflow_id, sample_config):
        """Test registering multiple nested workflows."""
        sub_ids = [uuid4() for _ in range(3)]

        for sub_id in sub_ids:
            await manager.register_nested_workflow(
                parent_workflow_id=sample_workflow_id,
                sub_workflow_id=sub_id,
                config=sample_config,
            )

        children = manager.get_children(sample_workflow_id)
        assert len(children) == 3

    @pytest.mark.asyncio
    async def test_unregister_nested_workflow(self, manager, sample_workflow_id, sample_config):
        """Test unregistering a nested workflow."""
        sub_workflow_id = uuid4()

        await manager.register_nested_workflow(
            parent_workflow_id=sample_workflow_id,
            sub_workflow_id=sub_workflow_id,
            config=sample_config,
        )

        success = await manager.unregister_nested_workflow(
            parent_workflow_id=sample_workflow_id,
            sub_workflow_id=sub_workflow_id,
        )

        assert success
        children = manager.get_children(sample_workflow_id)
        assert len(children) == 0


# =============================================================================
# Cycle Detection Tests
# =============================================================================


class TestCycleDetection:
    """Tests for cycle detection in nested workflows."""

    @pytest.mark.asyncio
    async def test_detect_simple_cycle(self, manager):
        """Test detection of simple A -> B -> A cycle."""
        workflow_a = uuid4()
        workflow_b = uuid4()

        config_a = NestedWorkflowConfig(parent_workflow_id=workflow_a)
        config_b = NestedWorkflowConfig(parent_workflow_id=workflow_b)

        # A -> B
        await manager.register_nested_workflow(
            parent_workflow_id=workflow_a,
            sub_workflow_id=workflow_b,
            config=config_a,
        )

        # B -> A (creates cycle)
        has_cycle = manager.detect_cycle(workflow_b, workflow_a)
        assert has_cycle

    @pytest.mark.asyncio
    async def test_detect_complex_cycle(self, manager):
        """Test detection of A -> B -> C -> A cycle."""
        workflow_a = uuid4()
        workflow_b = uuid4()
        workflow_c = uuid4()

        config = NestedWorkflowConfig(parent_workflow_id=workflow_a)

        # A -> B -> C
        await manager.register_nested_workflow(
            parent_workflow_id=workflow_a,
            sub_workflow_id=workflow_b,
            config=config,
        )
        await manager.register_nested_workflow(
            parent_workflow_id=workflow_b,
            sub_workflow_id=workflow_c,
            config=config,
        )

        # C -> A (creates cycle)
        has_cycle = manager.detect_cycle(workflow_c, workflow_a)
        assert has_cycle

    @pytest.mark.asyncio
    async def test_no_cycle_valid_hierarchy(self, manager):
        """Test no cycle detection for valid hierarchy."""
        workflow_a = uuid4()
        workflow_b = uuid4()
        workflow_c = uuid4()

        config = NestedWorkflowConfig(parent_workflow_id=workflow_a)

        # A -> B, A -> C (no cycle)
        await manager.register_nested_workflow(
            parent_workflow_id=workflow_a,
            sub_workflow_id=workflow_b,
            config=config,
        )
        await manager.register_nested_workflow(
            parent_workflow_id=workflow_a,
            sub_workflow_id=workflow_c,
            config=config,
        )

        # No cycle between B and C
        has_cycle = manager.detect_cycle(workflow_b, workflow_c)
        assert not has_cycle


# =============================================================================
# Depth Tests
# =============================================================================


class TestDepthLimiting:
    """Tests for depth limiting functionality."""

    @pytest.mark.asyncio
    async def test_get_depth(self, manager, sample_workflow_id, sample_config):
        """Test getting workflow depth."""
        sub_id = uuid4()
        await manager.register_nested_workflow(
            parent_workflow_id=sample_workflow_id,
            sub_workflow_id=sub_id,
            config=sample_config,
        )

        depth = manager.get_depth(sub_id)
        assert depth == 1

    @pytest.mark.asyncio
    async def test_depth_limit_check(self, manager, sample_workflow_id):
        """Test depth limit checking."""
        config = NestedWorkflowConfig(
            parent_workflow_id=sample_workflow_id,
            max_depth=2,
        )

        workflow_ids = [sample_workflow_id]
        for i in range(3):
            new_id = uuid4()
            await manager.register_nested_workflow(
                parent_workflow_id=workflow_ids[-1],
                sub_workflow_id=new_id,
                config=config,
            )
            workflow_ids.append(new_id)

        # Check depth at various levels
        assert manager.get_depth(workflow_ids[1]) == 1
        assert manager.get_depth(workflow_ids[2]) == 2
        assert manager.get_depth(workflow_ids[3]) == 3


# =============================================================================
# Context Tests
# =============================================================================


class TestExecutionContext:
    """Tests for nested execution context."""

    def test_context_creation(self, sample_workflow_id):
        """Test execution context creation."""
        context = NestedExecutionContext(
            execution_id=uuid4(),
            workflow_id=sample_workflow_id,
            depth=0,
        )
        assert context.workflow_id == sample_workflow_id
        assert context.depth == 0
        assert context.variables == {}

    def test_context_with_parent(self, sample_workflow_id):
        """Test execution context with parent context."""
        parent_context = NestedExecutionContext(
            execution_id=uuid4(),
            workflow_id=sample_workflow_id,
            depth=0,
            variables={"shared_var": "value"},
        )

        child_id = uuid4()
        child_context = NestedExecutionContext(
            execution_id=uuid4(),
            workflow_id=child_id,
            depth=1,
            parent_context=parent_context,
        )

        assert child_context.parent_context == parent_context
        assert child_context.depth == 1

    def test_context_to_dict(self, sample_workflow_id):
        """Test context serialization."""
        context = NestedExecutionContext(
            execution_id=uuid4(),
            workflow_id=sample_workflow_id,
            depth=2,
            variables={"key": "value"},
        )

        result = context.to_dict()
        assert "execution_id" in result
        assert "workflow_id" in result
        assert result["depth"] == 2
        assert result["variables"]["key"] == "value"


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for manager statistics."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, manager, sample_workflow_id, sample_config):
        """Test getting manager statistics."""
        # Register some workflows
        for i in range(5):
            await manager.register_nested_workflow(
                parent_workflow_id=sample_workflow_id,
                sub_workflow_id=uuid4(),
                config=sample_config,
            )

        stats = manager.get_statistics()

        assert "total_configs" in stats
        assert "total_references" in stats
        assert stats["total_configs"] >= 1


# =============================================================================
# Visualization Tests
# =============================================================================


class TestVisualization:
    """Tests for execution tree visualization."""

    @pytest.mark.asyncio
    async def test_visualize_execution_tree(self, manager, sample_workflow_id, sample_config):
        """Test visualizing execution tree."""
        sub_ids = [uuid4() for _ in range(3)]

        for sub_id in sub_ids:
            await manager.register_nested_workflow(
                parent_workflow_id=sample_workflow_id,
                sub_workflow_id=sub_id,
                config=sample_config,
            )

        tree = manager.visualize_execution_tree(sample_workflow_id)

        assert "root" in tree
        assert "children" in tree
        assert len(tree["children"]) == 3

