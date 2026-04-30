# =============================================================================
# IPA Platform - Nested Workflow API Tests
# =============================================================================
# Sprint 11: S11-5 Nested Workflow API Tests
#
# Unit tests for nested workflow API endpoints including:
# - Configuration management endpoints
# - Sub-workflow execution endpoints
# - Recursive execution endpoints
# - Composition endpoints
# - Context propagation endpoints
# - Statistics endpoints
# =============================================================================

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.nested.routes import router
from src.api.v1.nested.schemas import (
    NestedWorkflowTypeEnum,
    WorkflowScopeEnum,
    SubWorkflowExecutionModeEnum,
    RecursionStrategyEnum,
    CompositionTypeEnum,
    PropagationTypeEnum,
    ExecutionStatusEnum,
)


# =============================================================================
# Test App Setup
# =============================================================================


@pytest.fixture
def app():
    """Create test FastAPI app with nested router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# =============================================================================
# Configuration Endpoint Tests
# =============================================================================


class TestConfigurationEndpoints:
    """Tests for configuration management endpoints."""

    def test_create_nested_config(self, client):
        """Test creating nested workflow configuration."""
        parent_id = str(uuid4())
        sub_id = str(uuid4())

        response = client.post(
            "/nested/configs",
            json={
                "parent_workflow_id": parent_id,
                "name": "test_nested",
                "workflow_type": "reference",
                "scope": "inherited",
                "sub_workflow_id": sub_id,
                "max_depth": 5,
                "timeout_seconds": 300,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "config_id" in data
        assert data["name"] == "test_nested"
        assert data["workflow_type"] == "reference"

    def test_create_nested_config_inline(self, client):
        """Test creating inline nested workflow configuration."""
        parent_id = str(uuid4())

        response = client.post(
            "/nested/configs",
            json={
                "parent_workflow_id": parent_id,
                "name": "inline_nested",
                "workflow_type": "inline",
                "scope": "isolated",
                "inline_definition": {"steps": [{"action": "process"}]},
                "max_depth": 3,
                "timeout_seconds": 120,
            },
        )

        assert response.status_code == 201

    def test_list_nested_configs(self, client):
        """Test listing nested workflow configurations."""
        response = client.get("/nested/configs")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_list_nested_configs_with_filter(self, client):
        """Test listing configurations with parent filter."""
        parent_id = str(uuid4())

        response = client.get(f"/nested/configs?parent_workflow_id={parent_id}")

        assert response.status_code == 200

    def test_get_nested_config_not_found(self, client):
        """Test getting non-existent configuration."""
        config_id = str(uuid4())

        response = client.get(f"/nested/configs/{config_id}")

        assert response.status_code == 404

    def test_delete_nested_config_not_found(self, client):
        """Test deleting non-existent configuration."""
        config_id = str(uuid4())

        response = client.delete(f"/nested/configs/{config_id}")

        assert response.status_code == 404


# =============================================================================
# Sub-Workflow Execution Tests
# =============================================================================


class TestSubWorkflowExecutionEndpoints:
    """Tests for sub-workflow execution endpoints."""

    def test_execute_sub_workflow_sync(self, client):
        """Test synchronous sub-workflow execution."""
        sub_id = str(uuid4())

        response = client.post(
            "/nested/sub-workflows/execute",
            json={
                "sub_workflow_id": sub_id,
                "inputs": {"param": "value"},
                "mode": "sync",
                "timeout_seconds": 60,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "execution_id" in data
        assert data["mode"] == "sync"

    def test_execute_sub_workflow_async(self, client):
        """Test asynchronous sub-workflow execution."""
        sub_id = str(uuid4())

        response = client.post(
            "/nested/sub-workflows/execute",
            json={
                "sub_workflow_id": sub_id,
                "inputs": {"param": "value"},
                "mode": "async",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["mode"] == "async"

    def test_batch_execute_parallel(self, client):
        """Test parallel batch execution."""
        sub_ids = [str(uuid4()) for _ in range(3)]

        response = client.post(
            "/nested/sub-workflows/batch",
            json={
                "sub_workflows": [
                    {"id": sub_ids[0], "inputs": {"step": 1}},
                    {"id": sub_ids[1], "inputs": {"step": 2}},
                    {"id": sub_ids[2], "inputs": {"step": 3}},
                ],
                "parallel": True,
                "stop_on_error": True,
                "timeout_seconds": 120,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "batch_id" in data
        assert data["total_workflows"] == 3

    def test_batch_execute_sequential(self, client):
        """Test sequential batch execution."""
        sub_ids = [str(uuid4()) for _ in range(2)]

        response = client.post(
            "/nested/sub-workflows/batch",
            json={
                "sub_workflows": [
                    {"id": sub_ids[0], "inputs": {"step": 1}},
                    {"id": sub_ids[1], "inputs": {"step": 2}},
                ],
                "parallel": False,
                "pass_outputs": True,
            },
        )

        assert response.status_code == 201

    def test_get_sub_workflow_status_not_found(self, client):
        """Test getting status for non-existent execution."""
        exec_id = str(uuid4())

        response = client.get(f"/nested/sub-workflows/{exec_id}/status")

        assert response.status_code == 404

    def test_cancel_sub_workflow_not_found(self, client):
        """Test cancelling non-existent execution."""
        exec_id = str(uuid4())

        response = client.post(f"/nested/sub-workflows/{exec_id}/cancel")

        assert response.status_code == 404


# =============================================================================
# Recursive Execution Tests
# =============================================================================


class TestRecursiveExecutionEndpoints:
    """Tests for recursive execution endpoints."""

    def test_execute_recursive_depth_first(self, client):
        """Test depth-first recursive execution."""
        workflow_id = str(uuid4())

        response = client.post(
            "/nested/recursive/execute",
            json={
                "workflow_id": workflow_id,
                "inputs": {"value": 5},
                "strategy": "depth_first",
                "max_depth": 5,
                "max_iterations": 50,
                "timeout_seconds": 60,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "execution_id" in data
        assert data["strategy"] == "depth_first"

    def test_execute_recursive_breadth_first(self, client):
        """Test breadth-first recursive execution."""
        workflow_id = str(uuid4())

        response = client.post(
            "/nested/recursive/execute",
            json={
                "workflow_id": workflow_id,
                "inputs": {"value": 3},
                "strategy": "breadth_first",
                "max_depth": 3,
            },
        )

        assert response.status_code == 201

    def test_execute_recursive_with_termination(self, client):
        """Test recursive execution with termination condition."""
        workflow_id = str(uuid4())

        response = client.post(
            "/nested/recursive/execute",
            json={
                "workflow_id": workflow_id,
                "inputs": {"value": 10},
                "strategy": "depth_first",
                "termination_condition": "value <= 1",
                "enable_memoization": True,
            },
        )

        assert response.status_code == 201

    def test_get_recursion_status_not_found(self, client):
        """Test getting recursion status for non-existent execution."""
        exec_id = str(uuid4())

        response = client.get(f"/nested/recursive/{exec_id}/status")

        assert response.status_code == 404


# =============================================================================
# Composition Tests
# =============================================================================


class TestCompositionEndpoints:
    """Tests for composition endpoints."""

    def test_create_sequence_composition(self, client):
        """Test creating sequence composition."""
        workflow_ids = [str(uuid4()) for _ in range(3)]

        response = client.post(
            "/nested/compositions",
            json={
                "name": "test_pipeline",
                "description": "Test sequence composition",
                "blocks": [
                    {
                        "composition_type": "sequence",
                        "nodes": [
                            {"workflow_id": workflow_ids[0]},
                            {"workflow_id": workflow_ids[1]},
                            {"workflow_id": workflow_ids[2]},
                        ],
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_pipeline"
        assert data["block_count"] == 1

    def test_create_parallel_composition(self, client):
        """Test creating parallel composition."""
        workflow_ids = [str(uuid4()) for _ in range(2)]

        response = client.post(
            "/nested/compositions",
            json={
                "name": "parallel_tasks",
                "blocks": [
                    {
                        "composition_type": "parallel",
                        "nodes": [
                            {"workflow_id": workflow_ids[0]},
                            {"workflow_id": workflow_ids[1]},
                        ],
                    }
                ],
            },
        )

        assert response.status_code == 201

    def test_create_conditional_composition(self, client):
        """Test creating conditional composition."""
        workflow_ids = [str(uuid4()) for _ in range(2)]

        response = client.post(
            "/nested/compositions",
            json={
                "name": "conditional_flow",
                "blocks": [
                    {
                        "composition_type": "conditional",
                        "nodes": [
                            {"workflow_id": workflow_ids[0], "condition": "approved"},
                            {"workflow_id": workflow_ids[1], "condition": "rejected"},
                        ],
                    }
                ],
            },
        )

        assert response.status_code == 201

    def test_execute_composition(self, client):
        """Test executing composition."""
        composition_id = str(uuid4())

        response = client.post(
            "/nested/compositions/execute",
            json={
                "composition_id": composition_id,
                "inputs": {"start_data": "value"},
                "timeout_seconds": 300,
                "fail_fast": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "execution_id" in data


# =============================================================================
# Context Propagation Tests
# =============================================================================


class TestContextPropagationEndpoints:
    """Tests for context propagation endpoints."""

    def test_propagate_context_copy(self, client):
        """Test context propagation with COPY type."""
        source_id = str(uuid4())
        target_id = str(uuid4())

        response = client.post(
            "/nested/context/propagate",
            json={
                "source_workflow_id": source_id,
                "target_workflow_id": target_id,
                "context": {"var1": "value1", "var2": 42},
                "propagation_type": "copy",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "keys_propagated" in data

    def test_propagate_context_filter(self, client):
        """Test context propagation with FILTER type."""
        source_id = str(uuid4())
        target_id = str(uuid4())

        response = client.post(
            "/nested/context/propagate",
            json={
                "source_workflow_id": source_id,
                "target_workflow_id": target_id,
                "context": {"keep": "this", "skip": "that"},
                "propagation_type": "filter",
                "filter_keys": ["keep"],
            },
        )

        assert response.status_code == 200

    def test_propagate_context_with_mappings(self, client):
        """Test context propagation with key mappings."""
        source_id = str(uuid4())
        target_id = str(uuid4())

        response = client.post(
            "/nested/context/propagate",
            json={
                "source_workflow_id": source_id,
                "target_workflow_id": target_id,
                "context": {"old_key": "value"},
                "propagation_type": "copy",
                "key_mappings": {"old_key": "new_key"},
            },
        )

        assert response.status_code == 200

    def test_get_data_flow_events(self, client):
        """Test getting data flow events."""
        workflow_id = str(uuid4())

        response = client.get(f"/nested/context/flow/{workflow_id}")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_tracker_stats(self, client):
        """Test getting data flow tracker statistics."""
        response = client.get("/nested/context/tracker/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "unique_workflows" in data


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatisticsEndpoints:
    """Tests for statistics endpoints."""

    def test_get_nested_stats(self, client):
        """Test getting nested workflow statistics."""
        response = client.get("/nested/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_nested_configs" in data
        assert "total_executions" in data
        assert "active_executions" in data
        assert "by_type" in data
        assert "by_scope" in data


# =============================================================================
# Input Validation Tests
# =============================================================================


class TestInputValidation:
    """Tests for input validation."""

    def test_invalid_workflow_type(self, client):
        """Test invalid workflow type."""
        response = client.post(
            "/nested/configs",
            json={
                "parent_workflow_id": str(uuid4()),
                "name": "test",
                "workflow_type": "invalid_type",
            },
        )

        assert response.status_code == 422

    def test_invalid_uuid(self, client):
        """Test invalid UUID format."""
        response = client.post(
            "/nested/configs",
            json={
                "parent_workflow_id": "not-a-uuid",
                "name": "test",
            },
        )

        assert response.status_code == 422

    def test_invalid_max_depth(self, client):
        """Test invalid max depth value."""
        response = client.post(
            "/nested/configs",
            json={
                "parent_workflow_id": str(uuid4()),
                "name": "test",
                "max_depth": 0,  # Should be >= 1
            },
        )

        assert response.status_code == 422

    def test_invalid_timeout(self, client):
        """Test invalid timeout value."""
        response = client.post(
            "/nested/sub-workflows/execute",
            json={
                "sub_workflow_id": str(uuid4()),
                "timeout_seconds": 0,  # Should be >= 1
            },
        )

        assert response.status_code == 422

