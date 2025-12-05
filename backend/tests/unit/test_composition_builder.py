# =============================================================================
# IPA Platform - Workflow Composition Builder Tests
# =============================================================================
# Sprint 11: S11-4 WorkflowCompositionBuilder Tests
#
# Unit tests for workflow composition building including:
# - Fluent API for composition building
# - Sequence, parallel, conditional, loop, switch patterns
# - Template-based composition (map-reduce, pipeline, etc.)
# - Composition validation and execution
# =============================================================================

import pytest
from uuid import uuid4

from src.domain.orchestration.nested import (
    WorkflowCompositionBuilder,
    CompositionType,
    WorkflowNode,
    CompositionBlock,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def builder():
    """Create a fresh WorkflowCompositionBuilder instance."""
    return WorkflowCompositionBuilder()


@pytest.fixture
def sample_workflow_ids():
    """Generate sample workflow IDs."""
    return [uuid4() for _ in range(5)]


# =============================================================================
# Node Tests
# =============================================================================


class TestWorkflowNode:
    """Tests for WorkflowNode."""

    def test_node_creation(self):
        """Test node creation."""
        workflow_id = uuid4()
        node = WorkflowNode(workflow_id=workflow_id)

        assert node.workflow_id == workflow_id
        assert node.inputs == {}
        assert node.condition is None

    def test_node_with_inputs(self):
        """Test node with inputs."""
        workflow_id = uuid4()
        node = WorkflowNode(
            workflow_id=workflow_id,
            inputs={"param1": "value1", "param2": 42},
        )

        assert node.inputs["param1"] == "value1"
        assert node.inputs["param2"] == 42

    def test_node_with_condition(self):
        """Test node with condition."""
        workflow_id = uuid4()
        node = WorkflowNode(
            workflow_id=workflow_id,
            condition="result > 10",
        )

        assert node.condition == "result > 10"

    def test_node_to_dict(self):
        """Test node serialization."""
        workflow_id = uuid4()
        node = WorkflowNode(
            workflow_id=workflow_id,
            inputs={"key": "value"},
        )

        result = node.to_dict()
        assert "node_id" in result
        assert "workflow_id" in result
        assert result["inputs"]["key"] == "value"


# =============================================================================
# Block Tests
# =============================================================================


class TestCompositionBlock:
    """Tests for CompositionBlock."""

    def test_block_creation(self):
        """Test block creation."""
        block = CompositionBlock(composition_type=CompositionType.SEQUENCE)

        assert block.composition_type == CompositionType.SEQUENCE
        assert block.nodes == []
        assert block.nested_blocks == []

    def test_block_with_nodes(self, sample_workflow_ids):
        """Test block with nodes."""
        nodes = [WorkflowNode(workflow_id=wid) for wid in sample_workflow_ids[:3]]
        block = CompositionBlock(
            composition_type=CompositionType.PARALLEL,
            nodes=nodes,
        )

        assert len(block.nodes) == 3
        assert block.composition_type == CompositionType.PARALLEL

    def test_block_to_dict(self, sample_workflow_ids):
        """Test block serialization."""
        nodes = [WorkflowNode(workflow_id=wid) for wid in sample_workflow_ids[:2]]
        block = CompositionBlock(
            composition_type=CompositionType.SEQUENCE,
            nodes=nodes,
        )

        result = block.to_dict()
        assert "block_id" in result
        assert result["composition_type"] == "sequence"
        assert len(result["nodes"]) == 2


# =============================================================================
# Builder Fluent API Tests
# =============================================================================


class TestBuilderFluentAPI:
    """Tests for builder fluent API."""

    def test_sequence_builder(self, builder, sample_workflow_ids):
        """Test building a sequence composition."""
        result = (
            builder
            .sequence()
            .add_workflow(sample_workflow_ids[0])
            .add_workflow(sample_workflow_ids[1])
            .add_workflow(sample_workflow_ids[2])
            .end()
            .build()
        )

        assert len(result["blocks"]) == 1
        assert result["blocks"][0]["composition_type"] == "sequence"
        assert len(result["blocks"][0]["nodes"]) == 3

    def test_parallel_builder(self, builder, sample_workflow_ids):
        """Test building a parallel composition."""
        result = (
            builder
            .parallel()
            .add_workflow(sample_workflow_ids[0])
            .add_workflow(sample_workflow_ids[1])
            .end()
            .build()
        )

        assert len(result["blocks"]) == 1
        assert result["blocks"][0]["composition_type"] == "parallel"

    def test_conditional_builder(self, builder, sample_workflow_ids):
        """Test building a conditional composition."""
        result = (
            builder
            .conditional("status == 'approved'")
            .add_workflow(sample_workflow_ids[0], condition="approved")
            .add_workflow(sample_workflow_ids[1], condition="rejected")
            .end()
            .build()
        )

        assert len(result["blocks"]) == 1
        assert result["blocks"][0]["composition_type"] == "conditional"

    def test_loop_builder(self, builder, sample_workflow_ids):
        """Test building a loop composition."""
        result = (
            builder
            .loop("counter < 5", max_iterations=10)
            .add_workflow(sample_workflow_ids[0])
            .end()
            .build()
        )

        assert result["blocks"][0]["composition_type"] == "loop"
        assert result["blocks"][0]["loop_condition"] == "counter < 5"

    def test_switch_builder(self, builder, sample_workflow_ids):
        """Test building a switch composition."""
        result = (
            builder
            .switch("category")
            .case("A", sample_workflow_ids[0])
            .case("B", sample_workflow_ids[1])
            .default(sample_workflow_ids[2])
            .end()
            .build()
        )

        assert result["blocks"][0]["composition_type"] == "switch"

    def test_nested_blocks(self, builder, sample_workflow_ids):
        """Test nested composition blocks."""
        result = (
            builder
            .sequence()
            .add_workflow(sample_workflow_ids[0])
            .parallel()
            .add_workflow(sample_workflow_ids[1])
            .add_workflow(sample_workflow_ids[2])
            .end()
            .add_workflow(sample_workflow_ids[3])
            .end()
            .build()
        )

        # Should have one top-level sequence with nested parallel
        assert len(result["blocks"]) == 1


# =============================================================================
# Template Tests
# =============================================================================


class TestTemplates:
    """Tests for template-based composition."""

    def test_map_reduce_template(self, builder, sample_workflow_ids):
        """Test map-reduce template."""
        result = builder.from_template(
            "map_reduce",
            mapper_workflow=sample_workflow_ids[0],
            reducer_workflow=sample_workflow_ids[1],
            items=["a", "b", "c"],
        )

        assert "blocks" in result
        assert result["template"] == "map_reduce"

    def test_pipeline_template(self, builder, sample_workflow_ids):
        """Test pipeline template."""
        result = builder.from_template(
            "pipeline",
            stages=sample_workflow_ids[:3],
        )

        assert "blocks" in result
        assert result["template"] == "pipeline"

    def test_scatter_gather_template(self, builder, sample_workflow_ids):
        """Test scatter-gather template."""
        result = builder.from_template(
            "scatter_gather",
            scatter_workflow=sample_workflow_ids[0],
            gather_workflow=sample_workflow_ids[1],
            worker_workflows=sample_workflow_ids[2:4],
        )

        assert "blocks" in result
        assert result["template"] == "scatter_gather"

    def test_saga_template(self, builder, sample_workflow_ids):
        """Test saga template."""
        result = builder.from_template(
            "saga",
            steps=[
                {"workflow": sample_workflow_ids[0], "compensation": sample_workflow_ids[1]},
                {"workflow": sample_workflow_ids[2], "compensation": sample_workflow_ids[3]},
            ],
        )

        assert "blocks" in result
        assert result["template"] == "saga"


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidation:
    """Tests for composition validation."""

    def test_validate_valid_composition(self, builder, sample_workflow_ids):
        """Test validating a valid composition."""
        builder.sequence().add_workflow(sample_workflow_ids[0]).end()

        errors = builder.validate()
        assert len(errors) == 0

    def test_validate_empty_composition(self, builder):
        """Test validating an empty composition."""
        errors = builder.validate()
        assert len(errors) > 0  # Should have error about empty composition

    def test_validate_unclosed_block(self, builder, sample_workflow_ids):
        """Test validating with unclosed block."""
        builder.sequence().add_workflow(sample_workflow_ids[0])
        # Don't call end()

        errors = builder.validate()
        assert len(errors) > 0


# =============================================================================
# Execution Tests
# =============================================================================


class TestExecution:
    """Tests for composition execution."""

    @pytest.mark.asyncio
    async def test_execute_sequence(self, builder, sample_workflow_ids):
        """Test executing a sequence composition."""
        builder.sequence().add_workflow(sample_workflow_ids[0]).add_workflow(sample_workflow_ids[1]).end()

        result = await builder.execute(inputs={"start": True})

        assert "status" in result

    @pytest.mark.asyncio
    async def test_execute_parallel(self, builder, sample_workflow_ids):
        """Test executing a parallel composition."""
        builder.parallel().add_workflow(sample_workflow_ids[0]).add_workflow(sample_workflow_ids[1]).end()

        result = await builder.execute(inputs={"parallel": True})

        assert "status" in result

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, builder, sample_workflow_ids):
        """Test executing with timeout."""
        builder.sequence().add_workflow(sample_workflow_ids[0]).end()

        result = await builder.execute(inputs={}, timeout=5.0)

        assert "status" in result


# =============================================================================
# Reset and Clear Tests
# =============================================================================


class TestResetAndClear:
    """Tests for reset and clear functionality."""

    def test_reset_builder(self, builder, sample_workflow_ids):
        """Test resetting the builder."""
        builder.sequence().add_workflow(sample_workflow_ids[0]).end()

        builder.reset()

        result = builder.build()
        assert len(result["blocks"]) == 0

    def test_clear_current_block(self, builder, sample_workflow_ids):
        """Test clearing current block."""
        builder.sequence().add_workflow(sample_workflow_ids[0])

        builder.clear_current()

        # Should be able to start fresh
        builder.parallel().add_workflow(sample_workflow_ids[1]).end()

        result = builder.build()
        assert result["blocks"][0]["composition_type"] == "parallel"


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for builder statistics."""

    def test_get_statistics(self, builder, sample_workflow_ids):
        """Test getting builder statistics."""
        (
            builder
            .sequence()
            .add_workflow(sample_workflow_ids[0])
            .parallel()
            .add_workflow(sample_workflow_ids[1])
            .add_workflow(sample_workflow_ids[2])
            .end()
            .end()
        )

        stats = builder.get_statistics()

        assert "total_blocks" in stats
        assert "total_nodes" in stats
        assert "by_composition_type" in stats

