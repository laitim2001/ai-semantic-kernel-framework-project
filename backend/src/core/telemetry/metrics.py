"""
Custom Business Metrics Service

Sprint 2 - Story S2-5: Monitoring Integration Service

Provides custom metrics for:
- Workflow executions (count, duration, success rate)
- LLM API usage (calls, tokens, cost)
- Checkpoint approvals
- System health indicators
"""
from __future__ import annotations

import logging
from typing import Optional

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, UpDownCounter

logger = logging.getLogger(__name__)


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
    """

    def __init__(self, meter_name: str = "ipa.platform"):
        """Initialize MetricsService with custom meters."""
        self.meter = metrics.get_meter(meter_name)
        self._setup_metrics()

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

        logger.info("MetricsService: All custom metrics initialized")

    # ========================================
    # Workflow Execution Recording Methods
    # ========================================

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

        if tokens_used > 0:
            self.llm_tokens_used.add(tokens_used, attributes)
        elif prompt_tokens > 0 or completion_tokens > 0:
            self.llm_tokens_used.add(prompt_tokens + completion_tokens, attributes)

        if duration_seconds > 0:
            self.llm_request_duration.record(duration_seconds, attributes)

        if cost > 0:
            self.llm_cost.add(cost, attributes)

        logger.debug(f"Metric recorded: LLM call to {model} ({tokens_used} tokens)")

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
