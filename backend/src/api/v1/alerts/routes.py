"""
Alerts API Routes

Sprint 2 - Story S2-6: Alert Manager Integration

Provides endpoints for:
- AlertManager webhook receiver
- Alert history and statistics
- Active alerts listing
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, status

from src.domain.alerts import (
    AlertManagerPayload,
    AlertResponse,
    AlertHistoryItem,
    AlertStatsResponse,
    get_alert_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/webhook", response_model=AlertResponse)
async def receive_alertmanager_webhook(
    payload: AlertManagerPayload,
    severity: Optional[str] = Query(None, description="Filter by severity"),
):
    """
    Receive AlertManager webhook notifications.

    This endpoint is called by AlertManager when alerts fire or resolve.
    It processes the alerts and sends notifications for critical issues.

    The webhook payload follows AlertManager's webhook_config format:
    https://prometheus.io/docs/alerting/latest/configuration/#webhook_config

    Args:
        payload: AlertManager webhook payload
        severity: Optional severity filter (critical, warning, info)

    Returns:
        AlertResponse with processing results
    """
    logger.info(
        f"Received AlertManager webhook: {payload.status}, "
        f"{len(payload.alerts)} alerts, receiver: {payload.receiver}"
    )

    service = get_alert_service()
    response = await service.process_alert_webhook(payload, severity)

    return response


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_statistics():
    """
    Get alert statistics.

    Returns aggregated statistics including:
    - Total, firing, and resolved alert counts
    - Counts by severity level
    - Counts by team
    - Recent alerts list

    Returns:
        AlertStatsResponse with aggregated statistics
    """
    service = get_alert_service()
    return await service.get_alert_stats()


@router.get("/firing", response_model=list[AlertHistoryItem])
async def get_firing_alerts():
    """
    Get all currently firing alerts.

    Returns a list of all alerts that are currently in 'firing' state.
    Use this for dashboards and monitoring views.

    Returns:
        List of currently firing alerts
    """
    service = get_alert_service()
    return await service.get_firing_alerts()


@router.get("/history", response_model=list[AlertHistoryItem])
async def get_alert_history(
    limit: int = Query(100, ge=1, le=1000, description="Maximum alerts to return"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
):
    """
    Get alert history.

    Returns historical alerts with optional filtering.
    Sorted by start time, most recent first.

    Args:
        limit: Maximum number of alerts to return (1-1000)
        severity: Optional severity filter (critical, warning, info)

    Returns:
        List of AlertHistoryItem
    """
    service = get_alert_service()
    return await service.get_alert_history(limit=limit, severity=severity)


@router.delete("/clear", status_code=status.HTTP_200_OK)
async def clear_alerts():
    """
    Clear all alerts from memory.

    This is primarily for testing and maintenance.
    In production, alerts are persisted and this should be restricted.

    Returns:
        Count of cleared alerts
    """
    service = get_alert_service()
    count = await service.clear_alerts()
    return {"cleared": count, "message": f"Cleared {count} alerts"}


@router.post("/test", response_model=AlertResponse)
async def send_test_alert(
    alertname: str = Query("TestAlert", description="Alert name"),
    severity: str = Query("warning", description="Severity level"),
    message: str = Query("This is a test alert", description="Alert message"),
):
    """
    Send a test alert.

    Creates a synthetic alert for testing the alert pipeline.
    Useful for verifying notification channels are working.

    Args:
        alertname: Name of the test alert
        severity: Severity level (critical, warning, info)
        message: Alert message/description

    Returns:
        AlertResponse with processing results
    """
    from datetime import datetime, timezone

    # Create synthetic AlertManager payload
    payload = AlertManagerPayload(
        version="4",
        groupKey=f"test-{alertname}",
        status="firing",
        receiver="test-receiver",
        groupLabels={"alertname": alertname},
        commonLabels={"alertname": alertname, "severity": severity},
        commonAnnotations={"summary": message},
        alerts=[
            {
                "status": "firing",
                "labels": {
                    "alertname": alertname,
                    "severity": severity,
                    "instance": "test-instance",
                    "job": "test-job",
                },
                "annotations": {
                    "summary": message,
                    "description": f"Test alert: {message}",
                },
                "startsAt": datetime.now(timezone.utc).isoformat(),
                "endsAt": "0001-01-01T00:00:00Z",
                "fingerprint": f"test-{alertname}-{datetime.now().timestamp()}",
            }
        ],
    )

    service = get_alert_service()
    return await service.process_alert_webhook(payload)
