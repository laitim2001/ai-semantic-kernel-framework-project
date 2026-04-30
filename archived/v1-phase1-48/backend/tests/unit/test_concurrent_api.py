# =============================================================================
# IPA Platform - Concurrent API Unit Tests
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Tests for Concurrent Execution API endpoints:
#   - POST /api/v1/concurrent/execute - Execute concurrent tasks
#   - GET /api/v1/concurrent/{id}/status - Get execution status
#   - GET /api/v1/concurrent/{id}/branches - Get branch list
#   - GET /api/v1/concurrent/{id}/branches/{bid} - Get branch status
#   - POST /api/v1/concurrent/{id}/cancel - Cancel execution
#   - POST /api/v1/concurrent/{id}/branches/{bid}/cancel - Cancel branch
#   - GET /api/v1/concurrent/stats - Get statistics
#   - GET /api/v1/concurrent/health - Health check
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.api.v1.concurrent.schemas import (
    BranchCancelRequest,
    BranchCancelResponse,
    BranchInfo,
    BranchListResponse,
    BranchStatusEnum,
    BranchStatusResponse,
    ConcurrentExecuteRequest,
    ConcurrentExecuteResponse,
    ConcurrentModeEnum,
    ConcurrentStatsResponse,
    ExecutionCancelRequest,
    ExecutionCancelResponse,
    ExecutionStatusEnum,
    ExecutionStatusResponse,
    WebSocketMessage,
    WebSocketMessageType,
)


# =============================================================================
# Schema Tests
# =============================================================================


class TestConcurrentSchemas:
    """Tests for Concurrent API Pydantic schemas."""

    def test_concurrent_execute_request_valid(self):
        """Test valid ConcurrentExecuteRequest."""
        request = ConcurrentExecuteRequest(
            workflow_id=uuid4(),
            inputs={"query": "test"},
            mode=ConcurrentModeEnum.ALL,
            timeout_seconds=300,
            max_concurrency=5,
        )

        assert request.mode == ConcurrentModeEnum.ALL
        assert request.timeout_seconds == 300
        assert request.max_concurrency == 5

    def test_concurrent_execute_request_defaults(self):
        """Test ConcurrentExecuteRequest with defaults."""
        workflow_id = uuid4()
        request = ConcurrentExecuteRequest(workflow_id=workflow_id)

        assert request.workflow_id == workflow_id
        assert request.inputs == {}
        assert request.mode == ConcurrentModeEnum.ALL
        assert request.timeout_seconds == 300
        assert request.max_concurrency == 10

    def test_concurrent_execute_request_all_modes(self):
        """Test all execution modes."""
        workflow_id = uuid4()

        for mode in ConcurrentModeEnum:
            request = ConcurrentExecuteRequest(
                workflow_id=workflow_id,
                mode=mode,
            )
            assert request.mode == mode

    def test_branch_info_schema(self):
        """Test BranchInfo schema."""
        info = BranchInfo(
            branch_id="branch-1",
            status=BranchStatusEnum.RUNNING,
            started_at=datetime.utcnow(),
        )

        assert info.branch_id == "branch-1"
        assert info.status == BranchStatusEnum.RUNNING
        assert info.result is None
        assert info.error is None

    def test_branch_info_completed(self):
        """Test BranchInfo with completed status."""
        now = datetime.utcnow()
        info = BranchInfo(
            branch_id="branch-1",
            status=BranchStatusEnum.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=1500.0,
            result={"output": "success"},
        )

        assert info.status == BranchStatusEnum.COMPLETED
        assert info.duration_ms == 1500.0
        assert info.result == {"output": "success"}

    def test_branch_info_failed(self):
        """Test BranchInfo with failed status."""
        info = BranchInfo(
            branch_id="branch-1",
            status=BranchStatusEnum.FAILED,
            error="Task execution failed",
        )

        assert info.status == BranchStatusEnum.FAILED
        assert info.error == "Task execution failed"

    def test_concurrent_execute_response(self):
        """Test ConcurrentExecuteResponse schema."""
        execution_id = uuid4()
        response = ConcurrentExecuteResponse(
            execution_id=execution_id,
            status=ExecutionStatusEnum.PENDING,
            mode=ConcurrentModeEnum.ALL,
            branches=[],
            created_at=datetime.utcnow(),
            timeout_seconds=300,
            message="Execution created",
        )

        assert response.execution_id == execution_id
        assert response.status == ExecutionStatusEnum.PENDING
        assert len(response.branches) == 0

    def test_execution_status_response(self):
        """Test ExecutionStatusResponse schema."""
        response = ExecutionStatusResponse(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatusEnum.RUNNING,
            mode=ConcurrentModeEnum.ALL,
            progress=50.0,
            total_branches=4,
            completed_branches=2,
            failed_branches=0,
            running_branches=2,
        )

        assert response.progress == 50.0
        assert response.total_branches == 4
        assert response.completed_branches == 2

    def test_branch_list_response(self):
        """Test BranchListResponse schema."""
        response = BranchListResponse(
            execution_id=uuid4(),
            branches=[
                BranchInfo(branch_id="b1", status=BranchStatusEnum.COMPLETED),
                BranchInfo(branch_id="b2", status=BranchStatusEnum.RUNNING),
            ],
            total=2,
            completed=1,
            running=1,
            failed=0,
        )

        assert response.total == 2
        assert len(response.branches) == 2

    def test_execution_cancel_response(self):
        """Test ExecutionCancelResponse schema."""
        response = ExecutionCancelResponse(
            execution_id=uuid4(),
            status=ExecutionStatusEnum.CANCELLED,
            cancelled_branches=["b1", "b2"],
            message="Execution cancelled",
        )

        assert response.status == ExecutionStatusEnum.CANCELLED
        assert len(response.cancelled_branches) == 2

    def test_branch_cancel_response(self):
        """Test BranchCancelResponse schema."""
        response = BranchCancelResponse(
            execution_id=uuid4(),
            branch_id="branch-1",
            status=BranchStatusEnum.CANCELLED,
            message="Branch cancelled",
        )

        assert response.branch_id == "branch-1"
        assert response.status == BranchStatusEnum.CANCELLED

    def test_concurrent_stats_response(self):
        """Test ConcurrentStatsResponse schema."""
        response = ConcurrentStatsResponse(
            total_executions=100,
            active_executions=5,
            completed_executions=90,
            failed_executions=5,
            cancelled_executions=0,
            total_branches=400,
            avg_branches_per_execution=4.0,
            avg_duration_seconds=30.5,
            total_duration_seconds=3050.0,
            mode_distribution={"all": 80, "any": 15, "majority": 5},
            success_rate=90.0,
            deadlocks_detected=2,
            deadlocks_resolved=2,
        )

        assert response.total_executions == 100
        assert response.success_rate == 90.0
        assert response.deadlocks_detected == 2


# =============================================================================
# Mode Enum Tests
# =============================================================================


class TestModeEnums:
    """Tests for mode enumerations."""

    def test_concurrent_mode_values(self):
        """Test ConcurrentModeEnum values."""
        assert ConcurrentModeEnum.ALL.value == "all"
        assert ConcurrentModeEnum.ANY.value == "any"
        assert ConcurrentModeEnum.MAJORITY.value == "majority"
        assert ConcurrentModeEnum.FIRST_SUCCESS.value == "first_success"

    def test_branch_status_values(self):
        """Test BranchStatusEnum values."""
        assert BranchStatusEnum.PENDING.value == "pending"
        assert BranchStatusEnum.RUNNING.value == "running"
        assert BranchStatusEnum.COMPLETED.value == "completed"
        assert BranchStatusEnum.FAILED.value == "failed"
        assert BranchStatusEnum.CANCELLED.value == "cancelled"
        assert BranchStatusEnum.TIMED_OUT.value == "timed_out"

    def test_execution_status_values(self):
        """Test ExecutionStatusEnum values."""
        assert ExecutionStatusEnum.PENDING.value == "pending"
        assert ExecutionStatusEnum.RUNNING.value == "running"
        assert ExecutionStatusEnum.WAITING.value == "waiting"
        assert ExecutionStatusEnum.COMPLETED.value == "completed"
        assert ExecutionStatusEnum.FAILED.value == "failed"
        assert ExecutionStatusEnum.CANCELLED.value == "cancelled"
        assert ExecutionStatusEnum.TIMED_OUT.value == "timed_out"


# =============================================================================
# WebSocket Message Tests
# =============================================================================


class TestWebSocketMessages:
    """Tests for WebSocket message schemas."""

    def test_websocket_message_types(self):
        """Test all WebSocket message types."""
        expected_types = [
            "execution_started",
            "execution_completed",
            "execution_failed",
            "execution_cancelled",
            "branch_started",
            "branch_completed",
            "branch_failed",
            "branch_progress",
            "deadlock_detected",
            "deadlock_resolved",
            "error",
        ]

        for msg_type in WebSocketMessageType:
            assert msg_type.value in expected_types

    def test_websocket_message_schema(self):
        """Test WebSocketMessage schema."""
        message = WebSocketMessage(
            type=WebSocketMessageType.BRANCH_STARTED,
            execution_id=uuid4(),
            branch_id="branch-1",
            data={"progress": 0},
            message="Branch started",
        )

        assert message.type == WebSocketMessageType.BRANCH_STARTED
        assert message.branch_id == "branch-1"
        assert message.timestamp is not None

    def test_websocket_message_serialization(self):
        """Test WebSocketMessage JSON serialization."""
        execution_id = uuid4()
        message = WebSocketMessage(
            type=WebSocketMessageType.EXECUTION_COMPLETED,
            execution_id=execution_id,
            data={"result": "success"},
        )

        json_data = message.model_dump(mode="json")

        assert json_data["type"] == "execution_completed"
        assert json_data["execution_id"] == str(execution_id)
        assert json_data["data"] == {"result": "success"}

    def test_websocket_error_message(self):
        """Test error type WebSocket message."""
        message = WebSocketMessage(
            type=WebSocketMessageType.ERROR,
            execution_id=uuid4(),
            data={"error": "Something went wrong", "error_type": "RuntimeError"},
            message="Error occurred",
        )

        assert message.type == WebSocketMessageType.ERROR
        assert "error" in message.data

    def test_deadlock_detected_message(self):
        """Test deadlock detection message."""
        message = WebSocketMessage(
            type=WebSocketMessageType.DEADLOCK_DETECTED,
            execution_id=uuid4(),
            data={"cycle": ["A", "B", "C"], "cycle_length": 3},
            message="Deadlock detected",
        )

        assert message.type == WebSocketMessageType.DEADLOCK_DETECTED
        assert message.data["cycle_length"] == 3


# =============================================================================
# Request Validation Tests
# =============================================================================


class TestRequestValidation:
    """Tests for request validation."""

    def test_timeout_validation_range(self):
        """Test timeout_seconds validation range."""
        # Valid range
        request = ConcurrentExecuteRequest(
            workflow_id=uuid4(),
            timeout_seconds=3600,  # Max
        )
        assert request.timeout_seconds == 3600

        request = ConcurrentExecuteRequest(
            workflow_id=uuid4(),
            timeout_seconds=1,  # Min
        )
        assert request.timeout_seconds == 1

    def test_max_concurrency_validation_range(self):
        """Test max_concurrency validation range."""
        # Valid range
        request = ConcurrentExecuteRequest(
            workflow_id=uuid4(),
            max_concurrency=100,  # Max
        )
        assert request.max_concurrency == 100

        request = ConcurrentExecuteRequest(
            workflow_id=uuid4(),
            max_concurrency=1,  # Min
        )
        assert request.max_concurrency == 1

    def test_timeout_validation_out_of_range(self):
        """Test timeout_seconds out of range."""
        with pytest.raises(ValueError):
            ConcurrentExecuteRequest(
                workflow_id=uuid4(),
                timeout_seconds=0,  # Below min
            )

        with pytest.raises(ValueError):
            ConcurrentExecuteRequest(
                workflow_id=uuid4(),
                timeout_seconds=7200,  # Above max
            )

    def test_max_concurrency_out_of_range(self):
        """Test max_concurrency out of range."""
        with pytest.raises(ValueError):
            ConcurrentExecuteRequest(
                workflow_id=uuid4(),
                max_concurrency=0,  # Below min
            )

        with pytest.raises(ValueError):
            ConcurrentExecuteRequest(
                workflow_id=uuid4(),
                max_concurrency=200,  # Above max
            )

    def test_progress_validation_range(self):
        """Test progress field validation."""
        response = BranchStatusResponse(
            execution_id=uuid4(),
            branch_id="b1",
            status=BranchStatusEnum.RUNNING,
            progress=50.0,
        )
        assert response.progress == 50.0

        with pytest.raises(ValueError):
            BranchStatusResponse(
                execution_id=uuid4(),
                branch_id="b1",
                status=BranchStatusEnum.RUNNING,
                progress=-10.0,  # Below 0
            )

        with pytest.raises(ValueError):
            BranchStatusResponse(
                execution_id=uuid4(),
                branch_id="b1",
                status=BranchStatusEnum.RUNNING,
                progress=150.0,  # Above 100
            )


# =============================================================================
# Cancel Request Tests
# =============================================================================


class TestCancelRequests:
    """Tests for cancel request schemas."""

    def test_branch_cancel_request(self):
        """Test BranchCancelRequest schema."""
        request = BranchCancelRequest(reason="User requested cancellation")
        assert request.reason == "User requested cancellation"

    def test_branch_cancel_request_no_reason(self):
        """Test BranchCancelRequest without reason."""
        request = BranchCancelRequest()
        assert request.reason is None

    def test_execution_cancel_request(self):
        """Test ExecutionCancelRequest schema."""
        request = ExecutionCancelRequest(
            reason="Timeout exceeded",
            force=True,
        )
        assert request.reason == "Timeout exceeded"
        assert request.force is True

    def test_execution_cancel_request_defaults(self):
        """Test ExecutionCancelRequest with defaults."""
        request = ExecutionCancelRequest()
        assert request.reason is None
        assert request.force is False


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for API helper functions."""

    def test_convert_branch_status(self):
        """Test branch status conversion."""
        from src.api.v1.concurrent.routes import _convert_branch_status

        assert _convert_branch_status("pending") == BranchStatusEnum.PENDING
        assert _convert_branch_status("running") == BranchStatusEnum.RUNNING
        assert _convert_branch_status("completed") == BranchStatusEnum.COMPLETED
        assert _convert_branch_status("failed") == BranchStatusEnum.FAILED
        assert _convert_branch_status("cancelled") == BranchStatusEnum.CANCELLED
        assert _convert_branch_status("timed_out") == BranchStatusEnum.TIMED_OUT
        assert _convert_branch_status("PENDING") == BranchStatusEnum.PENDING
        assert _convert_branch_status("unknown") == BranchStatusEnum.PENDING

    def test_convert_execution_status(self):
        """Test execution status conversion."""
        from src.api.v1.concurrent.routes import _convert_execution_status

        assert _convert_execution_status("pending") == ExecutionStatusEnum.PENDING
        assert _convert_execution_status("running") == ExecutionStatusEnum.RUNNING
        assert _convert_execution_status("waiting") == ExecutionStatusEnum.WAITING
        assert _convert_execution_status("completed") == ExecutionStatusEnum.COMPLETED
        assert _convert_execution_status("failed") == ExecutionStatusEnum.FAILED
        assert _convert_execution_status("cancelled") == ExecutionStatusEnum.CANCELLED
        assert _convert_execution_status("timed_out") == ExecutionStatusEnum.TIMED_OUT
        assert _convert_execution_status("unknown") == ExecutionStatusEnum.PENDING

    def test_convert_mode(self):
        """Test mode conversion."""
        from src.api.v1.concurrent.routes import _convert_mode
        from src.domain.workflows.executors import ConcurrentMode

        assert _convert_mode(ConcurrentModeEnum.ALL) == ConcurrentMode.ALL
        assert _convert_mode(ConcurrentModeEnum.ANY) == ConcurrentMode.ANY
        assert _convert_mode(ConcurrentModeEnum.MAJORITY) == ConcurrentMode.MAJORITY
        assert _convert_mode(ConcurrentModeEnum.FIRST_SUCCESS) == ConcurrentMode.FIRST_SUCCESS


# =============================================================================
# Integration-Style Tests (Mocked)
# =============================================================================


class TestConcurrentAPIRoutes:
    """Tests for concurrent API routes with mocked dependencies."""

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager."""
        manager = MagicMock()
        manager.get_statistics.return_value = {
            "total_executions": 10,
            "active_executions": 2,
            "completed_executions": 7,
            "failed_executions": 1,
            "cancelled_executions": 0,
            "total_branches": 40,
            "avg_branches_per_execution": 4.0,
            "avg_duration_seconds": 25.0,
            "total_duration_seconds": 250.0,
            "mode_distribution": {"all": 8, "any": 2},
        }
        return manager

    @pytest.fixture
    def mock_deadlock_detector(self):
        """Create mock deadlock detector."""
        detector = MagicMock()
        detector.get_statistics.return_value = {
            "is_monitoring": True,
            "waiting_tasks": 0,
            "deadlocks_detected": 1,
            "deadlocks_resolved": 1,
        }
        return detector

    def test_stats_response_structure(self, mock_state_manager, mock_deadlock_detector):
        """Test stats endpoint response structure."""
        # Verify mock stats can be converted to response
        sm_stats = mock_state_manager.get_statistics()
        dd_stats = mock_deadlock_detector.get_statistics()

        response = ConcurrentStatsResponse(
            total_executions=sm_stats.get("total_executions", 0),
            active_executions=sm_stats.get("active_executions", 0),
            completed_executions=sm_stats.get("completed_executions", 0),
            failed_executions=sm_stats.get("failed_executions", 0),
            cancelled_executions=sm_stats.get("cancelled_executions", 0),
            total_branches=sm_stats.get("total_branches", 0),
            avg_branches_per_execution=sm_stats.get("avg_branches_per_execution", 0.0),
            avg_duration_seconds=sm_stats.get("avg_duration_seconds", 0.0),
            total_duration_seconds=sm_stats.get("total_duration_seconds", 0.0),
            mode_distribution=sm_stats.get("mode_distribution", {}),
            success_rate=70.0,
            deadlocks_detected=dd_stats.get("deadlocks_detected", 0),
            deadlocks_resolved=dd_stats.get("deadlocks_resolved", 0),
        )

        assert response.total_executions == 10
        assert response.deadlocks_detected == 1

    def test_execute_request_processing(self):
        """Test execute request can be processed."""
        request = ConcurrentExecuteRequest(
            workflow_id=uuid4(),
            inputs={"key": "value"},
            mode=ConcurrentModeEnum.ANY,
            timeout_seconds=60,
        )

        # Verify all fields accessible
        assert request.workflow_id is not None
        assert request.inputs["key"] == "value"
        assert request.mode == ConcurrentModeEnum.ANY
        assert request.timeout_seconds == 60


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_branches_list(self):
        """Test response with empty branches."""
        response = ConcurrentExecuteResponse(
            execution_id=uuid4(),
            status=ExecutionStatusEnum.PENDING,
            mode=ConcurrentModeEnum.ALL,
            branches=[],
            created_at=datetime.utcnow(),
            timeout_seconds=300,
            message="No branches yet",
        )

        assert response.branches == []

    def test_many_branches(self):
        """Test response with many branches."""
        branches = [
            BranchInfo(
                branch_id=f"branch-{i}",
                status=BranchStatusEnum.COMPLETED,
            )
            for i in range(100)
        ]

        response = BranchListResponse(
            execution_id=uuid4(),
            branches=branches,
            total=100,
            completed=100,
            running=0,
            failed=0,
        )

        assert response.total == 100
        assert len(response.branches) == 100

    def test_unicode_in_messages(self):
        """Test unicode characters in messages."""
        message = WebSocketMessage(
            type=WebSocketMessageType.BRANCH_COMPLETED,
            execution_id=uuid4(),
            branch_id="branch-1",
            message="分支執行完成 ✓",
            data={"status": "成功"},
        )

        assert "✓" in message.message
        assert message.data["status"] == "成功"

    def test_large_result_data(self):
        """Test handling large result data."""
        large_data = {"items": [f"item_{i}" for i in range(1000)]}

        info = BranchInfo(
            branch_id="branch-1",
            status=BranchStatusEnum.COMPLETED,
            result=large_data,
        )

        assert len(info.result["items"]) == 1000

    def test_zero_progress(self):
        """Test zero progress value."""
        response = ExecutionStatusResponse(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatusEnum.PENDING,
            mode=ConcurrentModeEnum.ALL,
            progress=0.0,
            total_branches=5,
            completed_branches=0,
            failed_branches=0,
            running_branches=0,
        )

        assert response.progress == 0.0

    def test_hundred_progress(self):
        """Test 100% progress value."""
        response = ExecutionStatusResponse(
            execution_id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatusEnum.COMPLETED,
            mode=ConcurrentModeEnum.ALL,
            progress=100.0,
            total_branches=5,
            completed_branches=5,
            failed_branches=0,
            running_branches=0,
        )

        assert response.progress == 100.0

    def test_none_optional_fields(self):
        """Test None for optional fields."""
        info = BranchInfo(
            branch_id="branch-1",
            status=BranchStatusEnum.PENDING,
        )

        assert info.started_at is None
        assert info.completed_at is None
        assert info.duration_ms is None
        assert info.result is None
        assert info.error is None
