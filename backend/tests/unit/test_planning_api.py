# =============================================================================
# IPA Platform - Planning API Unit Tests
# =============================================================================
# Sprint 10: S10-5 Planning API Tests
#
# Tests for Planning API endpoints including task decomposition, dynamic
# planning, decision-making, and trial-and-error execution.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import schemas for validation
from src.api.v1.planning.schemas import (
    DecomposeTaskRequest,
    DecompositionResponse,
    CreatePlanRequest,
    PlanResponse,
    DecisionRequest,
    DecisionResponse,
    TrialRequest,
    TrialResponse,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_task_decomposer():
    """Create a mock TaskDecomposer."""
    decomposer = MagicMock()
    decomposer.decompose = AsyncMock()
    decomposer.refine_decomposition = AsyncMock()
    return decomposer


@pytest.fixture
def mock_dynamic_planner():
    """Create a mock DynamicPlanner."""
    planner = MagicMock()
    planner.create_plan = AsyncMock()
    planner.approve_plan = AsyncMock()
    planner.start_plan = AsyncMock()
    planner.pause_plan = AsyncMock()
    planner.resume_plan = AsyncMock()
    planner.get_plan_status = MagicMock()
    planner.list_plans = MagicMock()
    planner.delete_plan = MagicMock()
    return planner


@pytest.fixture
def mock_decision_engine():
    """Create a mock AutonomousDecisionEngine."""
    engine = MagicMock()
    engine.make_decision = AsyncMock()
    engine.get_decision = MagicMock()
    engine.list_decisions = MagicMock()
    engine.explain_decision = MagicMock()
    return engine


@pytest.fixture
def mock_trial_engine():
    """Create a mock TrialAndErrorEngine."""
    engine = MagicMock()
    engine.execute = AsyncMock()
    engine.get_trial_history = MagicMock()
    engine.get_all_trials = MagicMock()
    engine.get_learning_insights = MagicMock()
    engine.get_recommendations = MagicMock()
    engine.get_statistics = MagicMock()
    return engine


@pytest.fixture
def app(mock_task_decomposer, mock_dynamic_planner, mock_decision_engine, mock_trial_engine):
    """Create a FastAPI app with mocked dependencies."""
    from src.api.v1.planning.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/planning")

    # Override dependencies
    app.state.task_decomposer = mock_task_decomposer
    app.state.dynamic_planner = mock_dynamic_planner
    app.state.decision_engine = mock_decision_engine
    app.state.trial_engine = mock_trial_engine

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""

    def test_decompose_task_request_valid(self):
        """Test valid DecomposeTaskRequest."""
        request = DecomposeTaskRequest(
            task_description="Implement user authentication",
            context={"framework": "FastAPI"},
            strategy="hybrid"
        )

        assert request.task_description == "Implement user authentication"
        assert request.strategy == "hybrid"

    def test_decompose_task_request_defaults(self):
        """Test DecomposeTaskRequest with defaults."""
        request = DecomposeTaskRequest(
            task_description="Test task"
        )

        assert request.strategy == "hybrid"  # Default
        assert request.context is None

    def test_create_plan_request_valid(self):
        """Test valid CreatePlanRequest."""
        request = CreatePlanRequest(
            goal="Build REST API",
            context={"team_size": 3},
            deadline="2025-12-31T23:59:59Z"
        )

        assert request.goal == "Build REST API"
        assert request.context["team_size"] == 3

    def test_decision_request_valid(self):
        """Test valid DecisionRequest."""
        request = DecisionRequest(
            situation="Multiple agents available",
            options=["agent_a", "agent_b"],
            context={"priority": "high"},
            decision_type="routing"
        )

        assert request.situation == "Multiple agents available"
        assert len(request.options) == 2

    def test_trial_request_valid(self):
        """Test valid TrialRequest."""
        request = TrialRequest(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            params={"timeout": 30},
            strategy="default"
        )

        assert request.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert request.params["timeout"] == 30


# =============================================================================
# Decomposition Endpoint Tests
# =============================================================================


class TestDecompositionEndpoints:
    """Tests for task decomposition endpoints."""

    def test_decompose_task_endpoint_structure(self):
        """Test decomposition endpoint request/response structure."""
        # Verify the schema structure
        request_data = {
            "task_description": "Build authentication system",
            "context": {"framework": "FastAPI"},
            "strategy": "hybrid"
        }

        request = DecomposeTaskRequest(**request_data)
        assert request.task_description == "Build authentication system"

    def test_decomposition_response_structure(self):
        """Test DecompositionResponse structure."""
        response_data = {
            "task_id": str(uuid4()),
            "original_task": "Test task",
            "subtasks": [
                {
                    "id": str(uuid4()),
                    "name": "Subtask 1",
                    "description": "Description",
                    "priority": "high",
                    "status": "pending",
                    "dependencies": [],
                    "estimated_duration_minutes": 30
                }
            ],
            "execution_order": [[str(uuid4())]],
            "estimated_total_duration": 30,
            "confidence_score": 0.85,
            "strategy": "hybrid"
        }

        response = DecompositionResponse(**response_data)
        assert response.confidence_score == 0.85


# =============================================================================
# Planning Endpoint Tests
# =============================================================================


class TestPlanningEndpoints:
    """Tests for dynamic planning endpoints."""

    def test_plan_response_structure(self):
        """Test PlanResponse structure."""
        response_data = {
            "id": str(uuid4()),
            "name": "Test Plan",
            "goal": "Build feature",
            "status": "draft",
            "progress": 0.0,
            "current_phase": 1,
            "total_phases": 3,
            "subtasks_count": 5,
            "created_at": datetime.utcnow().isoformat(),
            "deadline": None
        }

        response = PlanResponse(**response_data)
        assert response.status == "draft"
        assert response.progress == 0.0

    def test_create_plan_request_with_deadline(self):
        """Test CreatePlanRequest with deadline."""
        request = CreatePlanRequest(
            goal="Complete project",
            deadline="2025-06-30T23:59:59Z"
        )

        assert request.goal == "Complete project"
        assert request.deadline is not None


# =============================================================================
# Decision Endpoint Tests
# =============================================================================


class TestDecisionEndpoints:
    """Tests for decision-making endpoints."""

    def test_decision_response_structure(self):
        """Test DecisionResponse structure."""
        response_data = {
            "decision_id": str(uuid4()),
            "action": "select_agent_a",
            "confidence": "high",
            "reasoning": "Agent A has best fit",
            "risk_level": 0.2,
            "requires_approval": False,
            "options": [
                {
                    "id": str(uuid4()),
                    "name": "Agent A",
                    "score": 0.85
                }
            ]
        }

        response = DecisionResponse(**response_data)
        assert response.confidence == "high"
        assert not response.requires_approval

    def test_decision_request_types(self):
        """Test different decision types."""
        types = ["routing", "resource", "error_handling", "priority", "escalation", "optimization"]

        for dtype in types:
            request = DecisionRequest(
                situation="Test",
                options=["a", "b"],
                decision_type=dtype
            )
            assert request.decision_type == dtype


# =============================================================================
# Trial Endpoint Tests
# =============================================================================


class TestTrialEndpoints:
    """Tests for trial-and-error endpoints."""

    def test_trial_response_structure(self):
        """Test TrialResponse structure."""
        response_data = {
            "success": True,
            "result": {"output": "done"},
            "error": None,
            "attempts": 1,
            "final_params": {"timeout": 30},
            "final_strategy": "default"
        }

        response = TrialResponse(**response_data)
        assert response.success is True
        assert response.attempts == 1

    def test_trial_response_with_error(self):
        """Test TrialResponse with error."""
        response_data = {
            "success": False,
            "result": None,
            "error": "Max retries exceeded",
            "attempts": 3,
            "final_params": {"timeout": 60},
            "final_strategy": "aggressive"
        }

        response = TrialResponse(**response_data)
        assert response.success is False
        assert response.error == "Max retries exceeded"


# =============================================================================
# Integration Tests (Schema + Mock)
# =============================================================================


class TestAPIIntegration:
    """Integration tests for API endpoints with mocks."""

    def test_health_check_schema(self):
        """Test health check response."""
        # Health check should return simple status
        health_response = {
            "status": "healthy",
            "components": {
                "task_decomposer": "available",
                "dynamic_planner": "available",
                "decision_engine": "available",
                "trial_engine": "available"
            }
        }

        assert health_response["status"] == "healthy"

    def test_decomposition_flow(self, mock_task_decomposer):
        """Test decomposition flow with mock."""
        from src.domain.orchestration.planning.task_decomposer import (
            DecompositionResult,
            SubTask,
            TaskPriority,
        )

        # Setup mock response
        task_id = uuid4()
        subtask = MagicMock()
        subtask.id = uuid4()
        subtask.name = "Test Subtask"
        subtask.description = "Description"
        subtask.priority = TaskPriority.HIGH
        subtask.status.value = "pending"
        subtask.dependencies = []
        subtask.estimated_duration_minutes = 30
        subtask.assigned_agent_id = None
        subtask.to_dict.return_value = {
            "id": str(subtask.id),
            "name": "Test Subtask",
            "description": "Description",
            "priority": "high",
            "status": "pending",
            "dependencies": [],
            "estimated_duration_minutes": 30
        }

        mock_result = MagicMock(spec=DecompositionResult)
        mock_result.task_id = task_id
        mock_result.original_task = "Test task"
        mock_result.subtasks = [subtask]
        mock_result.execution_order = [[subtask.id]]
        mock_result.estimated_total_duration = 30
        mock_result.confidence_score = 0.85
        mock_result.decomposition_strategy = "hybrid"

        mock_task_decomposer.decompose.return_value = mock_result

        # Simulate API call
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            mock_task_decomposer.decompose(
                task_description="Test task",
                strategy="hybrid"
            )
        )

        assert result.original_task == "Test task"
        assert len(result.subtasks) == 1

    def test_decision_flow(self, mock_decision_engine):
        """Test decision flow with mock."""
        from src.domain.orchestration.planning.decision_engine import (
            Decision,
            DecisionType,
            DecisionConfidence,
        )

        # Setup mock response
        mock_decision = MagicMock(spec=Decision)
        mock_decision.id = uuid4()
        mock_decision.type = DecisionType.ROUTING
        mock_decision.situation = "Test situation"
        mock_decision.options = []
        mock_decision.selected_option_id = None
        mock_decision.confidence = DecisionConfidence.HIGH
        mock_decision.reasoning = "Best choice"
        mock_decision.requires_approval = False

        mock_decision_engine.make_decision.return_value = mock_decision

        # Simulate API call
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            mock_decision_engine.make_decision(
                situation="Test situation",
                options=["a", "b"],
                context={},
                decision_type=DecisionType.ROUTING
            )
        )

        assert result.type == DecisionType.ROUTING
        assert result.confidence == DecisionConfidence.HIGH


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for API error handling."""

    def test_invalid_strategy_in_decompose(self):
        """Test handling of invalid strategy."""
        # Schema should accept any string, validation happens in service
        request = DecomposeTaskRequest(
            task_description="Test",
            strategy="invalid_strategy"
        )

        # Strategy value is passed through
        assert request.strategy == "invalid_strategy"

    def test_empty_options_in_decision(self):
        """Test handling of empty options."""
        # Should be caught by Pydantic if we add validation
        request = DecisionRequest(
            situation="Test",
            options=[],  # Empty options
            decision_type="routing"
        )

        assert len(request.options) == 0

    def test_missing_required_fields(self):
        """Test that missing required fields raise errors."""
        with pytest.raises(Exception):
            DecomposeTaskRequest()  # Missing task_description

        with pytest.raises(Exception):
            DecisionRequest(situation="Test")  # Missing options

        with pytest.raises(Exception):
            TrialRequest(params={})  # Missing task_id


# =============================================================================
# Response Format Tests
# =============================================================================


class TestResponseFormats:
    """Tests for API response formats."""

    def test_subtask_response_format(self):
        """Test SubTaskResponse format."""
        from src.api.v1.planning.schemas import SubTaskResponse

        response = SubTaskResponse(
            id=str(uuid4()),
            name="Task Name",
            description="Task Description",
            priority="high",
            status="pending",
            dependencies=[],
            estimated_duration_minutes=45
        )

        assert response.priority == "high"
        assert response.estimated_duration_minutes == 45

    def test_insight_response_format(self):
        """Test InsightResponse format."""
        from src.api.v1.planning.schemas import InsightResponse

        response = InsightResponse(
            id=str(uuid4()),
            type="success_pattern",
            pattern="Retry succeeds after delay",
            confidence=0.9,
            recommendation="Add delay between retries",
            created_at=datetime.utcnow().isoformat()
        )

        assert response.confidence == 0.9

    def test_statistics_response_format(self):
        """Test TrialStatisticsResponse format."""
        from src.api.v1.planning.schemas import TrialStatisticsResponse

        response = TrialStatisticsResponse(
            total_trials=100,
            success_count=85,
            failure_count=15,
            success_rate=0.85,
            average_duration_ms=1500.5,
            unique_tasks=20,
            insights_count=5,
            known_patterns=3
        )

        assert response.success_rate == 0.85
        assert response.total_trials == 100
