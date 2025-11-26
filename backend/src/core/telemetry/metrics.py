"""
Custom Business Metrics Service

Sprint 2 - Story S2-5: Monitoring Integration Service
Sprint 3 - Story S3-7: Custom Business Metrics

Provides custom metrics for:
- Workflow executions (count, duration, success rate)
- LLM API usage (calls, tokens, cost)
- Checkpoint approvals
- System health indicators
- Active users tracking
- Platform usage statistics
"""
from __future__ import annotations

import logging
import time
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, UpDownCounter, ObservableGauge

logger = logging.getLogger(__name__)


@dataclass
class UserActivity:
    """Tracks user activity for active user metrics."""
    user_id: str
    last_active: datetime
    action_count: int = 0


@dataclass
class MetricSnapshot:
    """A snapshot of a metric value at a point in time."""
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime


class MetricsService:
    """
    Service for recording custom business metrics.

    Example:
        metrics = MetricsService()

        # Record workflow execution
        metrics.record_execution_start("workflow-123")
        # ... execution happens ...
        metrics.record_execution_complete("workflow-123", duration=45.2, status="completed")

        # Record LLM usage
        metrics.record_llm_call(model="gpt-4", tokens=1500, cost=0.045)

        # Record user activity
        metrics.record_user_activity("user-001", "workflow.create")
    """

    _instance: Optional["MetricsService"] = None
    _lock = threading.Lock()

    def __new__(cls, meter_name: str = "ipa.platform"):
        """Singleton pattern for MetricsService."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, meter_name: str = "ipa.platform"):
        """Initialize MetricsService with custom meters."""
        if self._initialized:
            return

        self.meter = metrics.get_meter(meter_name)
        self._user_activities: Dict[str, UserActivity] = {}
        self._user_lock = threading.Lock()
        self._metric_history: List[MetricSnapshot] = []
        self._history_lock = threading.Lock()
        self._max_history = 10000
        self._setup_metrics()
        self._initialized = True

    def _setup_metrics(self):
        """Set up all custom metric instruments."""

        # ========================================
        # Workflow Execution Metrics
        # ========================================

        self.workflow_executions_total = self.meter.create_counter(
            name="workflow_executions_total",
            description="Total number of workflow executions",
            unit="1",
        )

        self.workflow_created_total = self.meter.create_counter(
            name="workflow_created_total",
            description="Total number of workflows created",
            unit="1",
        )

        self.workflow_failed_total = self.meter.create_counter(
            name="workflow_failed_total",
            description="Total number of workflow failures",
            unit="1",
        )

        self.execution_duration = self.meter.create_histogram(
            name="workflow_execution_duration_seconds",
            description="Workflow execution duration in seconds",
            unit="s",
        )

        self.active_executions = self.meter.create_up_down_counter(
            name="workflow_executions_active",
            description="Number of currently running executions",
            unit="1",
        )

        # ========================================
        # LLM API Metrics
        # ========================================

        self.llm_api_calls = self.meter.create_counter(
            name="llm_api_calls_total",
            description="Total LLM API calls",
            unit="1",
        )

        self.llm_tokens_used = self.meter.create_counter(
            name="llm_tokens_used_total",
            description="Total LLM tokens consumed",
            unit="tokens",
        )

        self.llm_prompt_tokens = self.meter.create_counter(
            name="llm_prompt_tokens_total",
            description="Total LLM prompt tokens",
            unit="tokens",
        )

        self.llm_completion_tokens = self.meter.create_counter(
            name="llm_completion_tokens_total",
            description="Total LLM completion tokens",
            unit="tokens",
        )

        self.llm_request_duration = self.meter.create_histogram(
            name="llm_request_duration_seconds",
            description="LLM API request duration",
            unit="s",
        )

        self.llm_cost = self.meter.create_counter(
            name="llm_cost_total",
            description="Total LLM API cost in USD",
            unit="USD",
        )

        # ========================================
        # Checkpoint Metrics
        # ========================================

        self.checkpoint_requests = self.meter.create_counter(
            name="checkpoint_requests_total",
            description="Total checkpoint approval requests",
            unit="1",
        )

        self.checkpoint_wait_time = self.meter.create_histogram(
            name="checkpoint_wait_time_seconds",
            description="Time waiting for checkpoint approval",
            unit="s",
        )

        # ========================================
        # Webhook Metrics
        # ========================================

        self.webhook_received = self.meter.create_counter(
            name="webhooks_received_total",
            description="Total webhooks received",
            unit="1",
        )

        self.webhook_triggered = self.meter.create_counter(
            name="webhooks_triggered_total",
            description="Total outbound webhook triggers",
            unit="1",
        )

        # ========================================
        # Notification Metrics
        # ========================================

        self.notifications_sent = self.meter.create_counter(
            name="notifications_sent_total",
            description="Total notifications sent",
            unit="1",
        )

        # ========================================
        # User Activity Metrics (S3-7)
        # ========================================

        self.user_actions_total = self.meter.create_counter(
            name="user_actions_total",
            description="Total user actions",
            unit="1",
        )

        self.user_logins_total = self.meter.create_counter(
            name="user_logins_total",
            description="Total user logins",
            unit="1",
        )

        # Observable gauge for active users (updates on read)
        self.meter.create_observable_gauge(
            name="active_users_count",
            description="Number of active users in the last 15 minutes",
            unit="1",
            callbacks=[self._get_active_users_callback],
        )

        # ========================================
        # API Metrics (S3-7)
        # ========================================

        self.api_requests_total = self.meter.create_counter(
            name="api_requests_total",
            description="Total API requests",
            unit="1",
        )

        self.api_errors_total = self.meter.create_counter(
            name="api_errors_total",
            description="Total API errors",
            unit="1",
        )

        logger.info("MetricsService: All custom metrics initialized (including S3-7 business metrics)")

    def _get_active_users_callback(self, options):
        """Callback for observable gauge to get active user count."""
        count = self.get_active_users_count(minutes=15)
        yield metrics.Observation(count)

    # ========================================
    # Workflow Execution Recording Methods
    # ========================================

    def record_workflow_created(
        self,
        workflow_id: str,
        created_by: str,
        workflow_type: str = "standard",
    ):
        """Record a new workflow creation."""
        self.workflow_created_total.add(
            1,
            {"workflow_id": workflow_id, "created_by": created_by, "type": workflow_type}
        )
        self._record_snapshot("workflow_created_total", 1, {"workflow_id": workflow_id})
        logger.debug(f"Metric recorded: workflow created {workflow_id}")

    def record_execution_start(
        self,
        workflow_id: str,
        triggered_by: str = "manual",
    ):
        """Record the start of a workflow execution."""
        self.workflow_executions_total.add(
            1,
            {"workflow_id": workflow_id, "triggered_by": triggered_by, "status": "started"}
        )
        self.active_executions.add(1, {"workflow_id": workflow_id})
        self._record_snapshot("workflow_executions_total", 1, {"status": "started"})
        logger.debug(f"Metric recorded: execution start for {workflow_id}")

    def record_execution_complete(
        self,
        workflow_id: str,
        duration_seconds: float,
        status: str = "completed",
        error_type: Optional[str] = None,
    ):
        """Record the completion of a workflow execution."""
        attributes = {
            "workflow_id": workflow_id,
            "status": status,
        }
        if error_type:
            attributes["error_type"] = error_type

        self.workflow_executions_total.add(1, {**attributes, "status": status})
        self.execution_duration.record(duration_seconds, attributes)
        self.active_executions.add(-1, {"workflow_id": workflow_id})

        if status == "failed":
            self.workflow_failed_total.add(1, attributes)

        self._record_snapshot("workflow_execution_duration_seconds", duration_seconds, {"status": status})
        logger.debug(f"Metric recorded: execution complete for {workflow_id} ({status})")

    # ========================================
    # LLM API Recording Methods
    # ========================================

    def record_llm_call(
        self,
        model: str,
        tokens_used: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        duration_seconds: float = 0.0,
        cost: float = 0.0,
        status: str = "success",
    ):
        """Record an LLM API call."""
        attributes = {"model": model, "status": status}

        self.llm_api_calls.add(1, attributes)

        total_tokens = tokens_used
        if total_tokens == 0 and (prompt_tokens > 0 or completion_tokens > 0):
            total_tokens = prompt_tokens + completion_tokens

        if total_tokens > 0:
            self.llm_tokens_used.add(total_tokens, attributes)

        if prompt_tokens > 0:
            self.llm_prompt_tokens.add(prompt_tokens, attributes)

        if completion_tokens > 0:
            self.llm_completion_tokens.add(completion_tokens, attributes)

        if duration_seconds > 0:
            self.llm_request_duration.record(duration_seconds, attributes)

        if cost > 0:
            self.llm_cost.add(cost, attributes)

        self._record_snapshot("llm_tokens_used_total", total_tokens, {"model": model})
        self._record_snapshot("llm_cost_total", cost, {"model": model})
        logger.debug(f"Metric recorded: LLM call to {model} ({total_tokens} tokens, ${cost:.4f})")

    # ========================================
    # Checkpoint Recording Methods
    # ========================================

    def record_checkpoint_request(
        self,
        workflow_id: str,
        step_index: int,
    ):
        """Record a checkpoint approval request."""
        self.checkpoint_requests.add(
            1,
            {"workflow_id": workflow_id, "step_index": str(step_index), "status": "pending"}
        )
        logger.debug(f"Metric recorded: checkpoint request for {workflow_id}")

    def record_checkpoint_response(
        self,
        workflow_id: str,
        step_index: int,
        wait_seconds: float,
        status: str,  # "approved", "rejected", "expired"
    ):
        """Record a checkpoint response."""
        attributes = {
            "workflow_id": workflow_id,
            "step_index": str(step_index),
            "status": status,
        }
        self.checkpoint_requests.add(1, attributes)
        self.checkpoint_wait_time.record(wait_seconds, attributes)
        logger.debug(f"Metric recorded: checkpoint {status} for {workflow_id}")

    # ========================================
    # Webhook Recording Methods
    # ========================================

    def record_webhook_received(
        self,
        source: str,
        workflow_id: Optional[str] = None,
        status: str = "processed",
    ):
        """Record an inbound webhook."""
        attributes = {"source": source, "status": status}
        if workflow_id:
            attributes["workflow_id"] = workflow_id

        self.webhook_received.add(1, attributes)
        logger.debug(f"Metric recorded: webhook received from {source}")

    def record_webhook_triggered(
        self,
        target: str,
        workflow_id: Optional[str] = None,
        status: str = "success",
    ):
        """Record an outbound webhook trigger."""
        attributes = {"target": target, "status": status}
        if workflow_id:
            attributes["workflow_id"] = workflow_id

        self.webhook_triggered.add(1, attributes)
        logger.debug(f"Metric recorded: webhook triggered to {target}")

    # ========================================
    # Notification Recording Methods
    # ========================================

    def record_notification_sent(
        self,
        provider: str,
        notification_type: str,
        status: str = "success",
    ):
        """Record a notification sent."""
        self.notifications_sent.add(
            1,
            {"provider": provider, "type": notification_type, "status": status}
        )
        logger.debug(f"Metric recorded: notification sent via {provider}")

    # ========================================
    # User Activity Recording Methods (S3-7)
    # ========================================

    def record_user_activity(
        self,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
    ):
        """Record user activity for active user tracking."""
        with self._user_lock:
            if user_id in self._user_activities:
                self._user_activities[user_id].last_active = datetime.utcnow()
                self._user_activities[user_id].action_count += 1
            else:
                self._user_activities[user_id] = UserActivity(
                    user_id=user_id,
                    last_active=datetime.utcnow(),
                    action_count=1,
                )

        attributes = {"action": action}
        if resource_type:
            attributes["resource_type"] = resource_type

        self.user_actions_total.add(1, attributes)
        logger.debug(f"Metric recorded: user activity {action} by {user_id}")

    def record_user_login(
        self,
        user_id: str,
        auth_method: str = "jwt",
    ):
        """Record a user login."""
        self.record_user_activity(user_id, "login")
        self.user_logins_total.add(1, {"auth_method": auth_method})
        logger.debug(f"Metric recorded: user login for {user_id}")

    def get_active_users_count(self, minutes: int = 15) -> int:
        """Get count of active users in the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        with self._user_lock:
            return sum(
                1 for activity in self._user_activities.values()
                if activity.last_active >= cutoff
            )

    def get_active_users(self, minutes: int = 15) -> List[Dict[str, Any]]:
        """Get list of active users in the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        with self._user_lock:
            return [
                {
                    "user_id": activity.user_id,
                    "last_active": activity.last_active.isoformat(),
                    "action_count": activity.action_count,
                }
                for activity in self._user_activities.values()
                if activity.last_active >= cutoff
            ]

    # ========================================
    # API Recording Methods (S3-7)
    # ========================================

    def record_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ):
        """Record an API request."""
        attributes = {
            "method": method,
            "path": path,
            "status_code": str(status_code),
        }
        self.api_requests_total.add(1, attributes)

        if status_code >= 400:
            self.api_errors_total.add(1, attributes)

        logger.debug(f"Metric recorded: API {method} {path} -> {status_code}")

    # ========================================
    # Metric History & Snapshots
    # ========================================

    def _record_snapshot(
        self,
        name: str,
        value: float,
        labels: Dict[str, str],
    ):
        """Record a metric snapshot for history."""
        snapshot = MetricSnapshot(
            name=name,
            value=value,
            labels=labels,
            timestamp=datetime.utcnow(),
        )
        with self._history_lock:
            self._metric_history.append(snapshot)
            if len(self._metric_history) > self._max_history:
                self._metric_history = self._metric_history[-self._max_history:]

    def get_metric_history(
        self,
        name: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get metric history."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with self._history_lock:
            filtered = [
                s for s in self._metric_history
                if s.timestamp >= cutoff
                and (name is None or s.name == name)
            ]
        return [
            {
                "name": s.name,
                "value": s.value,
                "labels": s.labels,
                "timestamp": s.timestamp.isoformat(),
            }
            for s in filtered[-limit:]
        ]

    # ========================================
    # Summary Methods
    # ========================================

    def get_business_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of business metrics."""
        return {
            "active_users_15m": self.get_active_users_count(15),
            "active_users_1h": self.get_active_users_count(60),
            "metric_history_size": len(self._metric_history),
            "tracked_users": len(self._user_activities),
            "metrics_available": [
                "workflow_executions_total",
                "workflow_created_total",
                "workflow_failed_total",
                "workflow_execution_duration_seconds",
                "llm_api_calls_total",
                "llm_tokens_used_total",
                "llm_cost_total",
                "checkpoint_requests_total",
                "checkpoint_wait_time_seconds",
                "webhooks_received_total",
                "webhooks_triggered_total",
                "notifications_sent_total",
                "user_actions_total",
                "user_logins_total",
                "active_users_count",
                "api_requests_total",
                "api_errors_total",
            ],
        }

    def health_check(self) -> Dict[str, Any]:
        """Health check for metrics service."""
        return {
            "status": "healthy",
            "service": "MetricsService",
            "initialized": self._initialized,
            "tracked_users": len(self._user_activities),
            "history_size": len(self._metric_history),
        }


# Global metrics service instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """
    Get the global MetricsService instance.

    Returns:
        MetricsService singleton instance
    """
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


def reset_metrics_service():
    """Reset the metrics service (for testing)."""
    global _metrics_service
    MetricsService._instance = None
    _metrics_service = None
