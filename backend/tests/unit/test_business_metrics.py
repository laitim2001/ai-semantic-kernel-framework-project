"""
Unit tests for Custom Business Metrics (S3-7)

Tests the MetricsService and business metrics tracking.
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.core.telemetry.metrics import (
    MetricsService,
    get_metrics_service,
    reset_metrics_service,
    UserActivity,
    MetricSnapshot,
)


class TestMetricsServiceSingleton:
    """Test cases for MetricsService singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset(self):
        """Reset singleton before each test."""
        reset_metrics_service()
        yield
        reset_metrics_service()

    def test_singleton_instance(self):
        """Test that MetricsService is a singleton."""
        m1 = MetricsService()
        m2 = MetricsService()
        assert m1 is m2

    def test_get_metrics_service(self):
        """Test get_metrics_service returns singleton."""
        m1 = get_metrics_service()
        m2 = get_metrics_service()
        assert m1 is m2

    def test_reset_creates_new_instance(self):
        """Test that reset allows new instance creation."""
        m1 = get_metrics_service()
        reset_metrics_service()
        m2 = get_metrics_service()
        assert m1 is not m2


class TestWorkflowMetrics:
    """Test cases for workflow metrics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_record_workflow_created(self):
        """Test recording workflow creation."""
        self.metrics.record_workflow_created(
            workflow_id="wf-001",
            created_by="user-001",
            workflow_type="standard",
        )
        # Verify no exception raised
        assert True

    def test_record_execution_start(self):
        """Test recording execution start."""
        self.metrics.record_execution_start(
            workflow_id="wf-001",
            triggered_by="manual",
        )
        assert True

    def test_record_execution_complete_success(self):
        """Test recording successful execution completion."""
        self.metrics.record_execution_complete(
            workflow_id="wf-001",
            duration_seconds=45.2,
            status="completed",
        )
        assert True

    def test_record_execution_complete_failed(self):
        """Test recording failed execution."""
        self.metrics.record_execution_complete(
            workflow_id="wf-001",
            duration_seconds=10.5,
            status="failed",
            error_type="timeout",
        )
        assert True

    def test_execution_lifecycle(self):
        """Test full execution lifecycle metrics."""
        self.metrics.record_workflow_created("wf-002", "user-001")
        self.metrics.record_execution_start("wf-002", "webhook")
        self.metrics.record_execution_complete("wf-002", 30.0, "completed")
        assert True


class TestLLMMetrics:
    """Test cases for LLM metrics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_record_llm_call_basic(self):
        """Test recording basic LLM call."""
        self.metrics.record_llm_call(
            model="gpt-4",
            tokens_used=1000,
            duration_seconds=2.5,
            cost=0.03,
            status="success",
        )
        assert True

    def test_record_llm_call_with_token_breakdown(self):
        """Test recording LLM call with prompt/completion tokens."""
        self.metrics.record_llm_call(
            model="gpt-4",
            prompt_tokens=500,
            completion_tokens=500,
            duration_seconds=3.0,
            cost=0.045,
        )
        assert True

    def test_record_llm_call_failure(self):
        """Test recording failed LLM call."""
        self.metrics.record_llm_call(
            model="gpt-4",
            tokens_used=0,
            status="error",
        )
        assert True


class TestUserActivityMetrics:
    """Test cases for user activity metrics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_record_user_activity(self):
        """Test recording user activity."""
        self.metrics.record_user_activity(
            user_id="user-001",
            action="workflow.create",
            resource_type="workflow",
        )
        assert True

    def test_record_user_login(self):
        """Test recording user login."""
        self.metrics.record_user_login(
            user_id="user-001",
            auth_method="jwt",
        )
        assert True

    def test_get_active_users_count(self):
        """Test getting active user count."""
        # Record some activity
        self.metrics.record_user_activity("user-001", "login")
        self.metrics.record_user_activity("user-002", "view")
        self.metrics.record_user_activity("user-003", "create")

        count = self.metrics.get_active_users_count(minutes=15)
        assert count == 3

    def test_get_active_users_empty(self):
        """Test getting active users when none exist."""
        count = self.metrics.get_active_users_count(minutes=15)
        assert count == 0

    def test_get_active_users_list(self):
        """Test getting active users list."""
        self.metrics.record_user_activity("user-001", "login")
        self.metrics.record_user_activity("user-002", "view")

        users = self.metrics.get_active_users(minutes=15)
        assert len(users) == 2
        assert any(u["user_id"] == "user-001" for u in users)
        assert any(u["user_id"] == "user-002" for u in users)

    def test_user_action_count_increments(self):
        """Test that action count increments for same user."""
        self.metrics.record_user_activity("user-001", "view")
        self.metrics.record_user_activity("user-001", "create")
        self.metrics.record_user_activity("user-001", "edit")

        users = self.metrics.get_active_users(minutes=15)
        user = next(u for u in users if u["user_id"] == "user-001")
        assert user["action_count"] == 3


class TestCheckpointMetrics:
    """Test cases for checkpoint metrics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_record_checkpoint_request(self):
        """Test recording checkpoint request."""
        self.metrics.record_checkpoint_request(
            workflow_id="wf-001",
            step_index=3,
        )
        assert True

    def test_record_checkpoint_response_approved(self):
        """Test recording approved checkpoint."""
        self.metrics.record_checkpoint_response(
            workflow_id="wf-001",
            step_index=3,
            wait_seconds=120.5,
            status="approved",
        )
        assert True

    def test_record_checkpoint_response_rejected(self):
        """Test recording rejected checkpoint."""
        self.metrics.record_checkpoint_response(
            workflow_id="wf-001",
            step_index=3,
            wait_seconds=30.0,
            status="rejected",
        )
        assert True


class TestWebhookMetrics:
    """Test cases for webhook metrics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_record_webhook_received(self):
        """Test recording received webhook."""
        self.metrics.record_webhook_received(
            source="n8n",
            workflow_id="wf-001",
            status="processed",
        )
        assert True

    def test_record_webhook_triggered(self):
        """Test recording triggered webhook."""
        self.metrics.record_webhook_triggered(
            target="external-api",
            workflow_id="wf-001",
            status="success",
        )
        assert True


class TestNotificationMetrics:
    """Test cases for notification metrics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_record_notification_sent(self):
        """Test recording sent notification."""
        self.metrics.record_notification_sent(
            provider="teams",
            notification_type="alert",
            status="success",
        )
        assert True


class TestAPIMetrics:
    """Test cases for API metrics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_record_api_request_success(self):
        """Test recording successful API request."""
        self.metrics.record_api_request(
            method="GET",
            path="/api/v1/workflows",
            status_code=200,
            duration_ms=45.5,
        )
        assert True

    def test_record_api_request_error(self):
        """Test recording API error."""
        self.metrics.record_api_request(
            method="POST",
            path="/api/v1/workflows",
            status_code=500,
            duration_ms=100.0,
        )
        assert True


class TestMetricHistory:
    """Test cases for metric history."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_get_metric_history_empty(self):
        """Test getting empty history."""
        history = self.metrics.get_metric_history()
        assert history == []

    def test_get_metric_history_with_data(self):
        """Test getting history with data."""
        # Generate some metrics
        self.metrics.record_workflow_created("wf-001", "user-001")
        self.metrics.record_execution_start("wf-001")
        self.metrics.record_execution_complete("wf-001", 30.0, "completed")

        history = self.metrics.get_metric_history()
        assert len(history) > 0

    def test_get_metric_history_filtered(self):
        """Test getting filtered history."""
        self.metrics.record_workflow_created("wf-001", "user-001")
        self.metrics.record_llm_call("gpt-4", tokens_used=1000, cost=0.03)

        history = self.metrics.get_metric_history(name="llm_tokens_used_total")
        assert all(h["name"] == "llm_tokens_used_total" for h in history)


class TestBusinessMetricsSummary:
    """Test cases for business metrics summary."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_get_business_metrics_summary(self):
        """Test getting business metrics summary."""
        # Add some activity
        self.metrics.record_user_activity("user-001", "login")

        summary = self.metrics.get_business_metrics_summary()

        assert "active_users_15m" in summary
        assert "active_users_1h" in summary
        assert "tracked_users" in summary
        assert "metrics_available" in summary
        assert len(summary["metrics_available"]) > 0


class TestHealthCheck:
    """Test cases for health check."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_health_check(self):
        """Test health check."""
        health = self.metrics.health_check()

        assert health["status"] == "healthy"
        assert health["service"] == "MetricsService"
        assert health["initialized"] is True


class TestDataclasses:
    """Test cases for dataclasses."""

    def test_user_activity_creation(self):
        """Test UserActivity dataclass."""
        activity = UserActivity(
            user_id="user-001",
            last_active=datetime.utcnow(),
            action_count=5,
        )
        assert activity.user_id == "user-001"
        assert activity.action_count == 5

    def test_metric_snapshot_creation(self):
        """Test MetricSnapshot dataclass."""
        snapshot = MetricSnapshot(
            name="test_metric",
            value=42.5,
            labels={"key": "value"},
            timestamp=datetime.utcnow(),
        )
        assert snapshot.name == "test_metric"
        assert snapshot.value == 42.5


class TestMetricsRoutes:
    """Test cases for metrics API routes."""

    def test_routes_import(self):
        """Test that routes can be imported."""
        from src.api.v1.metrics.routes import router
        assert router is not None

    def test_response_models(self):
        """Test Pydantic response models."""
        from src.api.v1.metrics.routes import (
            ActiveUserResponse,
            ActiveUsersResponse,
            LLMUsageResponse,
            WorkflowStatsResponse,
            BusinessMetricsSummaryResponse,
            MetricHistoryEntry,
            MetricHistoryResponse,
            HealthResponse,
        )

        # Test ActiveUserResponse
        user = ActiveUserResponse(
            user_id="user-001",
            last_active="2025-01-01T00:00:00",
            action_count=5,
        )
        assert user.user_id == "user-001"

        # Test ActiveUsersResponse
        users_response = ActiveUsersResponse(
            count=1,
            window_minutes=15,
            users=[user],
        )
        assert users_response.count == 1

        # Test LLMUsageResponse
        llm = LLMUsageResponse(
            total_calls=100,
            total_tokens=50000,
            total_cost_usd=1.5,
        )
        assert llm.total_calls == 100

        # Test HealthResponse
        health = HealthResponse(
            status="healthy",
            service="MetricsService",
            initialized=True,
            tracked_users=10,
            history_size=100,
        )
        assert health.status == "healthy"


class TestThreadSafety:
    """Test cases for thread safety."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        reset_metrics_service()
        self.metrics = get_metrics_service()
        yield
        reset_metrics_service()

    def test_concurrent_user_activity(self):
        """Test concurrent user activity recording."""
        import threading

        errors = []

        def worker(thread_id):
            try:
                for i in range(50):
                    self.metrics.record_user_activity(
                        f"user-{thread_id}",
                        f"action-{i}",
                    )
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Should have 5 unique users
        users = self.metrics.get_active_users(minutes=15)
        assert len(users) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
