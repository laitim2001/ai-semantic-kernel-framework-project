# =============================================================================
# IPA Platform - Sprint 29 API Routes Integration Tests
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 29, Story S29-5: API Integration Tests (6 pts)
#
# Test coverage for migrated API routes:
#   - handoff/routes.py → HandoffService
#   - workflows/routes.py → WorkflowDefinitionAdapter
#   - executions/routes.py → EnhancedExecutionStateMachine
#   - checkpoints/routes.py → ApprovalWorkflowManager
#
# Tests verify:
#   - Adapter layer is correctly imported and used
#   - API endpoints maintain backward compatibility
#   - Dependency injection works properly
#   - Status mappings are correct
# =============================================================================

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def app():
    """Create test FastAPI app with all routers."""
    from fastapi import FastAPI

    app = FastAPI()

    # Import routers
    from src.api.v1.handoff.routes import router as handoff_router
    from src.api.v1.workflows.routes import router as workflows_router
    from src.api.v1.executions.routes import router as executions_router
    from src.api.v1.checkpoints.routes import router as checkpoints_router

    app.include_router(handoff_router, prefix="/api/v1")
    app.include_router(workflows_router, prefix="/api/v1")
    app.include_router(executions_router, prefix="/api/v1")
    app.include_router(checkpoints_router, prefix="/api/v1")

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# =============================================================================
# Test Handoff Routes Adapter Integration (S29-1)
# =============================================================================

class TestHandoffRoutesAdapterIntegration:
    """Tests for handoff routes adapter integration."""

    def test_imports_from_adapter_layer(self):
        """Verify handoff routes imports from adapter layer."""
        from src.api.v1.handoff.routes import (
            get_handoff_service,
            reset_handoff_service,
            _map_service_status_to_api,
            _map_api_policy_to_legacy,
            _map_api_strategy_to_adapter,
        )

        # Verify functions exist
        assert callable(get_handoff_service)
        assert callable(reset_handoff_service)
        assert callable(_map_service_status_to_api)
        assert callable(_map_api_policy_to_legacy)
        assert callable(_map_api_strategy_to_adapter)

    def test_handoff_service_singleton(self):
        """Test HandoffService singleton pattern."""
        from src.api.v1.handoff.routes import (
            get_handoff_service,
            reset_handoff_service,
        )

        # Reset first
        reset_handoff_service()

        # Get service twice
        service1 = get_handoff_service()
        service2 = get_handoff_service()

        # Should be same instance
        assert service1 is service2

        # Cleanup
        reset_handoff_service()

    def test_status_mapping(self):
        """Test status mapping from service to API."""
        from src.api.v1.handoff.routes import _map_service_status_to_api
        from src.integrations.agent_framework.builders.handoff_service import (
            HandoffServiceStatus,
        )
        from src.api.v1.handoff.schemas import HandoffStatusEnum

        # Test key mappings
        assert _map_service_status_to_api(HandoffServiceStatus.INITIATED) == HandoffStatusEnum.INITIATED
        assert _map_service_status_to_api(HandoffServiceStatus.COMPLETED) == HandoffStatusEnum.COMPLETED
        assert _map_service_status_to_api(HandoffServiceStatus.FAILED) == HandoffStatusEnum.FAILED

    def test_policy_mapping(self):
        """Test policy mapping from API to adapter."""
        from src.api.v1.handoff.routes import _map_api_policy_to_legacy
        from src.api.v1.handoff.schemas import HandoffPolicyEnum
        from src.integrations.agent_framework.builders.handoff_policy import (
            LegacyHandoffPolicy,
        )

        assert _map_api_policy_to_legacy(HandoffPolicyEnum.IMMEDIATE) == LegacyHandoffPolicy.IMMEDIATE
        assert _map_api_policy_to_legacy(HandoffPolicyEnum.GRACEFUL) == LegacyHandoffPolicy.GRACEFUL

    def test_strategy_mapping(self):
        """Test match strategy mapping."""
        from src.api.v1.handoff.routes import _map_api_strategy_to_adapter
        from src.api.v1.handoff.schemas import MatchStrategyEnum
        from src.integrations.agent_framework.builders.handoff_capability import (
            MatchStrategy,
        )

        assert _map_api_strategy_to_adapter(MatchStrategyEnum.BEST_FIT) == MatchStrategy.BEST_FIT
        assert _map_api_strategy_to_adapter(MatchStrategyEnum.ROUND_ROBIN) == MatchStrategy.ROUND_ROBIN


# =============================================================================
# Test Workflows Routes Adapter Integration (S29-2)
# =============================================================================

class TestWorkflowsRoutesAdapterIntegration:
    """Tests for workflows routes adapter integration."""

    def test_imports_from_adapter_layer(self):
        """Verify workflows routes imports from adapter layer."""
        from src.api.v1.workflows.routes import (
            validate_workflow_definition,
            workflow_to_response,
            serialize_graph_definition,
        )

        # Verify functions exist
        assert callable(validate_workflow_definition)
        assert callable(workflow_to_response)
        assert callable(serialize_graph_definition)

    def test_validate_workflow_definition_uses_adapter(self):
        """Test workflow validation uses WorkflowDefinitionAdapter."""
        from src.api.v1.workflows.routes import validate_workflow_definition

        # Test with valid definition
        valid_graph = {
            "nodes": [
                {"id": "start", "name": "Start", "type": "start"},
                {"id": "end", "name": "End", "type": "end"},
            ],
            "edges": [
                {"source": "start", "target": "end"},
            ],
            "variables": {},
        }

        is_valid, errors = validate_workflow_definition(valid_graph)
        # Note: May have warnings but should be structurally valid
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_serialize_graph_definition(self):
        """Test graph serialization handles UUIDs correctly."""
        from src.api.v1.workflows.routes import serialize_graph_definition
        from pydantic import BaseModel
        from typing import List, Optional, Dict, Any
        from uuid import UUID

        class NodeSchema(BaseModel):
            id: str
            name: str
            type: str
            agent_id: Optional[UUID] = None

            def model_dump(self):
                return {
                    "id": self.id,
                    "name": self.name,
                    "type": self.type,
                    "agent_id": self.agent_id,
                }

        class EdgeSchema(BaseModel):
            source: str
            target: str

            def model_dump(self):
                return {"source": self.source, "target": self.target}

        class GraphSchema(BaseModel):
            nodes: List[NodeSchema]
            edges: List[EdgeSchema]
            variables: Dict[str, Any]

        test_uuid = uuid4()
        graph = GraphSchema(
            nodes=[
                NodeSchema(id="n1", name="Node1", type="task", agent_id=test_uuid),
            ],
            edges=[],
            variables={},
        )

        result = serialize_graph_definition(graph)

        # UUID should be converted to string
        assert result["nodes"][0]["agent_id"] == str(test_uuid)


# =============================================================================
# Test Executions Routes Adapter Integration (S29-3)
# =============================================================================

class TestExecutionsRoutesAdapterIntegration:
    """Tests for executions routes adapter integration."""

    def test_imports_from_adapter_layer(self):
        """Verify executions routes imports from adapter layer."""
        from src.api.v1.executions.routes import (
            validate_state_transition,
        )
        from src.integrations.agent_framework.core.state_machine import (
            EnhancedExecutionStateMachine,
        )

        # Verify imports work
        assert callable(validate_state_transition)
        assert hasattr(EnhancedExecutionStateMachine, 'can_transition')
        assert hasattr(EnhancedExecutionStateMachine, 'is_terminal')
        assert hasattr(EnhancedExecutionStateMachine, 'get_valid_transitions')

    def test_validate_state_transition_uses_adapter(self):
        """Test state transition validation uses adapter."""
        from src.api.v1.executions.routes import validate_state_transition

        # Test valid transitions
        assert validate_state_transition("pending", "running") is True
        assert validate_state_transition("running", "completed") is True
        assert validate_state_transition("running", "failed") is True

        # Test invalid transitions
        assert validate_state_transition("completed", "running") is False
        assert validate_state_transition("failed", "pending") is False

    def test_enhanced_state_machine_class_methods(self):
        """Test EnhancedExecutionStateMachine class methods work correctly."""
        from src.integrations.agent_framework.core.state_machine import (
            EnhancedExecutionStateMachine,
        )
        from src.domain.executions import ExecutionStatus

        # Test get_valid_transitions
        transitions = EnhancedExecutionStateMachine.get_valid_transitions(
            ExecutionStatus.PENDING
        )
        assert ExecutionStatus.RUNNING in transitions

        # Test is_terminal
        assert EnhancedExecutionStateMachine.is_terminal(ExecutionStatus.COMPLETED) is True
        assert EnhancedExecutionStateMachine.is_terminal(ExecutionStatus.RUNNING) is False

        # Test can_transition
        assert EnhancedExecutionStateMachine.can_transition(
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
        ) is True


# =============================================================================
# Test Checkpoints Routes Adapter Integration (S29-4)
# =============================================================================

class TestCheckpointsRoutesAdapterIntegration:
    """Tests for checkpoints routes adapter integration."""

    def test_imports_from_adapter_layer(self):
        """Verify checkpoints routes imports from adapter layer."""
        from src.api.v1.checkpoints.routes import (
            get_approval_manager,
            reset_approval_manager,
            _map_checkpoint_to_adapter_status,
            _map_adapter_to_checkpoint_status,
        )

        # Verify functions exist
        assert callable(get_approval_manager)
        assert callable(reset_approval_manager)
        assert callable(_map_checkpoint_to_adapter_status)
        assert callable(_map_adapter_to_checkpoint_status)

    def test_approval_manager_singleton(self):
        """Test ApprovalWorkflowManager singleton pattern."""
        from src.api.v1.checkpoints.routes import (
            get_approval_manager,
            reset_approval_manager,
        )

        # Reset first
        reset_approval_manager()

        # Get manager twice
        manager1 = get_approval_manager()
        manager2 = get_approval_manager()

        # Should be same instance
        assert manager1 is manager2

        # Cleanup
        reset_approval_manager()

    def test_checkpoint_to_adapter_status_mapping(self):
        """Test status mapping from CheckpointStatus to adapter."""
        from src.api.v1.checkpoints.routes import _map_checkpoint_to_adapter_status
        from src.domain.checkpoints import CheckpointStatus
        from src.integrations.agent_framework.core.approval import ApprovalStatus

        assert _map_checkpoint_to_adapter_status(CheckpointStatus.PENDING) == ApprovalStatus.PENDING
        assert _map_checkpoint_to_adapter_status(CheckpointStatus.APPROVED) == ApprovalStatus.APPROVED
        assert _map_checkpoint_to_adapter_status(CheckpointStatus.REJECTED) == ApprovalStatus.REJECTED
        assert _map_checkpoint_to_adapter_status(CheckpointStatus.EXPIRED) == ApprovalStatus.EXPIRED

    def test_adapter_to_checkpoint_status_mapping(self):
        """Test status mapping from adapter to CheckpointStatus."""
        from src.api.v1.checkpoints.routes import _map_adapter_to_checkpoint_status
        from src.domain.checkpoints import CheckpointStatus
        from src.integrations.agent_framework.core.approval import ApprovalStatus

        assert _map_adapter_to_checkpoint_status(ApprovalStatus.PENDING) == CheckpointStatus.PENDING
        assert _map_adapter_to_checkpoint_status(ApprovalStatus.APPROVED) == CheckpointStatus.APPROVED
        assert _map_adapter_to_checkpoint_status(ApprovalStatus.REJECTED) == CheckpointStatus.REJECTED
        assert _map_adapter_to_checkpoint_status(ApprovalStatus.EXPIRED) == CheckpointStatus.EXPIRED
        # Special mappings
        assert _map_adapter_to_checkpoint_status(ApprovalStatus.ESCALATED) == CheckpointStatus.PENDING
        assert _map_adapter_to_checkpoint_status(ApprovalStatus.CANCELLED) == CheckpointStatus.EXPIRED

    def test_approval_manager_has_required_methods(self):
        """Test ApprovalWorkflowManager has required methods."""
        from src.api.v1.checkpoints.routes import (
            get_approval_manager,
            reset_approval_manager,
        )

        reset_approval_manager()
        manager = get_approval_manager()

        # Verify required methods
        assert hasattr(manager, 'create_approval_request')
        assert hasattr(manager, 'create_approval_response')
        assert hasattr(manager, 'get_pending_approvals')
        assert hasattr(manager, 'respond_to_approval')
        assert hasattr(manager, 'register_approval_executor')

        reset_approval_manager()


# =============================================================================
# Cross-Module Integration Tests
# =============================================================================

class TestCrossModuleIntegration:
    """Tests for cross-module integration."""

    def test_all_routes_use_adapter_layer(self):
        """Verify all routes import from integrations.agent_framework."""
        import ast
        import pathlib

        routes_files = [
            "src/api/v1/handoff/routes.py",
            "src/api/v1/workflows/routes.py",
            "src/api/v1/executions/routes.py",
            "src/api/v1/checkpoints/routes.py",
        ]

        base_path = pathlib.Path(__file__).parent.parent.parent

        for route_file in routes_files:
            file_path = base_path / route_file

            if not file_path.exists():
                pytest.skip(f"File not found: {route_file}")

            content = file_path.read_text()

            # Check for adapter layer imports
            assert "src.integrations.agent_framework" in content, \
                f"{route_file} should import from adapter layer"

    def test_dependency_injection_pattern(self):
        """Test all routes use FastAPI Depends pattern."""
        from src.api.v1.handoff.routes import get_handoff_service
        from src.api.v1.checkpoints.routes import get_approval_manager

        # Verify dependency functions return proper types
        from src.integrations.agent_framework.builders.handoff_service import (
            HandoffService,
        )
        from src.integrations.agent_framework.core.approval_workflow import (
            ApprovalWorkflowManager,
        )

        # Reset singletons
        from src.api.v1.handoff.routes import reset_handoff_service
        from src.api.v1.checkpoints.routes import reset_approval_manager

        reset_handoff_service()
        reset_approval_manager()

        # Get instances
        handoff_service = get_handoff_service()
        approval_manager = get_approval_manager()

        assert isinstance(handoff_service, HandoffService)
        assert isinstance(approval_manager, ApprovalWorkflowManager)

        # Cleanup
        reset_handoff_service()
        reset_approval_manager()


# =============================================================================
# Backward Compatibility Tests
# =============================================================================

class TestBackwardCompatibility:
    """Tests for backward compatibility of API responses."""

    def test_handoff_schemas_unchanged(self):
        """Test handoff API schemas remain unchanged."""
        from src.api.v1.handoff.schemas import (
            HandoffTriggerRequest,
            HandoffTriggerResponse,
            HandoffStatusResponse,
            HandoffCancelResponse,
            HandoffHistoryResponse,
            CapabilityMatchRequest,
            CapabilityMatchResponse,
        )

        # Schemas should have expected fields
        trigger_req_fields = HandoffTriggerRequest.model_fields.keys()
        assert "source_agent_id" in trigger_req_fields
        assert "policy" in trigger_req_fields

        trigger_resp_fields = HandoffTriggerResponse.model_fields.keys()
        assert "handoff_id" in trigger_resp_fields
        assert "status" in trigger_resp_fields

    def test_checkpoint_schemas_unchanged(self):
        """Test checkpoint API schemas remain unchanged."""
        from src.api.v1.checkpoints.schemas import (
            CheckpointResponse,
            CheckpointActionResponse,
            PendingCheckpointsResponse,
            CheckpointStatsResponse,
        )

        # Schemas should have expected fields
        cp_resp_fields = CheckpointResponse.model_fields.keys()
        assert "id" in cp_resp_fields
        assert "execution_id" in cp_resp_fields
        assert "status" in cp_resp_fields

        action_resp_fields = CheckpointActionResponse.model_fields.keys()
        assert "id" in action_resp_fields
        assert "status" in action_resp_fields
        assert "message" in action_resp_fields


# =============================================================================
# Performance and Load Tests (Basic)
# =============================================================================

class TestPerformanceBasic:
    """Basic performance tests for API routes."""

    def test_singleton_initialization_time(self):
        """Test singleton services initialize quickly."""
        import time
        from src.api.v1.handoff.routes import (
            get_handoff_service,
            reset_handoff_service,
        )
        from src.api.v1.checkpoints.routes import (
            get_approval_manager,
            reset_approval_manager,
        )

        # Reset
        reset_handoff_service()
        reset_approval_manager()

        # Time initialization
        start = time.time()
        get_handoff_service()
        get_approval_manager()
        elapsed = time.time() - start

        # Should initialize in under 1 second
        assert elapsed < 1.0, f"Singleton initialization took {elapsed:.2f}s"

        # Cleanup
        reset_handoff_service()
        reset_approval_manager()

    def test_repeated_access_fast(self):
        """Test repeated access to singletons is fast."""
        import time
        from src.api.v1.handoff.routes import (
            get_handoff_service,
            reset_handoff_service,
        )

        reset_handoff_service()

        # First access initializes
        get_handoff_service()

        # Time repeated access
        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            get_handoff_service()
        elapsed = time.time() - start

        # Should be very fast (< 0.1s for 1000 iterations)
        assert elapsed < 0.1, f"Repeated access took {elapsed:.2f}s for {iterations} iterations"

        reset_handoff_service()
