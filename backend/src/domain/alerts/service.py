"""
Alert Service

Sprint 2 - Story S2-6: Alert Manager Integration

Handles alert processing, storage, and notification routing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict

from .schemas import (
    AlertManagerPayload,
    AlertResponse,
    AlertHistoryItem,
    AlertStatsResponse,
)

logger = logging.getLogger(__name__)


class AlertService:
    """Service for processing and managing alerts from AlertManager.

    This service:
    - Receives webhooks from AlertManager
    - Stores alerts in memory (for local dev) or Redis (for production)
    - Routes critical alerts to notification channels
    - Provides alert history and statistics

    Example:
        service = AlertService()
        response = await service.process_alert_webhook(payload)
    """

    def __init__(self):
        """Initialize AlertService with in-memory storage."""
        # In-memory storage for local development
        # In production, this would use Redis or PostgreSQL
        self._alerts: dict[str, AlertHistoryItem] = {}
        self._alert_history: list[AlertHistoryItem] = []
        self._max_history = 1000

    async def process_alert_webhook(
        self,
        payload: AlertManagerPayload,
        severity_filter: Optional[str] = None,
    ) -> AlertResponse:
        """Process incoming AlertManager webhook.

        Args:
            payload: AlertManager webhook payload
            severity_filter: Optional severity filter from query params

        Returns:
            AlertResponse with processing results
        """
        firing_count = 0
        resolved_count = 0

        for alert in payload.alerts:
            # Apply severity filter if specified
            if severity_filter and alert.labels.severity != severity_filter:
                continue

            fingerprint = alert.fingerprint
            alertname = alert.labels.alertname
            severity = alert.labels.severity
            status = alert.status

            # Parse timestamps
            try:
                started_at = datetime.fromisoformat(
                    alert.startsAt.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                started_at = datetime.now(timezone.utc)

            ended_at = None
            duration = None
            if status == "resolved":
                try:
                    ended_at = datetime.fromisoformat(
                        alert.endsAt.replace("Z", "+00:00")
                    )
                    duration = (ended_at - started_at).total_seconds()
                except (ValueError, AttributeError):
                    ended_at = datetime.now(timezone.utc)
                    duration = (ended_at - started_at).total_seconds()

            # Create history item
            history_item = AlertHistoryItem(
                fingerprint=fingerprint,
                alertname=alertname,
                severity=severity,
                status=status,
                summary=alert.annotations.summary,
                description=alert.annotations.description,
                instance=alert.labels.instance,
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=duration,
                notified=False,
            )

            # Update or add alert
            self._alerts[fingerprint] = history_item

            # Add to history
            self._alert_history.append(history_item)
            if len(self._alert_history) > self._max_history:
                self._alert_history = self._alert_history[-self._max_history:]

            if status == "firing":
                firing_count += 1
                await self._handle_firing_alert(history_item)
            else:
                resolved_count += 1
                await self._handle_resolved_alert(history_item)

            logger.info(
                f"Processed alert: {alertname} ({severity}) - {status}",
                extra={
                    "fingerprint": fingerprint,
                    "alertname": alertname,
                    "severity": severity,
                    "status": status,
                }
            )

        return AlertResponse(
            received=True,
            alerts_count=len(payload.alerts),
            firing_count=firing_count,
            resolved_count=resolved_count,
            message=f"Processed {len(payload.alerts)} alerts"
        )

    async def _handle_firing_alert(self, alert: AlertHistoryItem):
        """Handle a firing alert - send notifications if needed."""
        # Import notification service for critical alerts
        if alert.severity == "critical":
            try:
                from src.domain.notifications.service import ConsoleNotificationProvider
                from src.domain.notifications.schemas import AdaptiveCardContent, FactItem

                # Build facts list
                facts = [
                    FactItem(title="Severity", value=alert.severity),
                    FactItem(title="Instance", value=alert.instance or "N/A"),
                    FactItem(title="Started", value=alert.started_at.isoformat()),
                ]

                # Build adaptive card
                card = AdaptiveCardContent(
                    title=f"[{alert.severity.upper()}] {alert.alertname}",
                    message=alert.description or alert.summary or "Alert triggered",
                    color="FF0000",  # Red for critical
                    facts=facts,
                )

                # Use console provider for local development
                provider = ConsoleNotificationProvider()
                await provider.send(card)
                alert.notified = True
                logger.info(f"Sent notification for critical alert: {alert.alertname}")
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")

    async def _handle_resolved_alert(self, alert: AlertHistoryItem):
        """Handle a resolved alert - send resolution notification."""
        # Only notify resolution for critical alerts that were notified
        original = self._alerts.get(alert.fingerprint)
        if original and original.notified and alert.severity == "critical":
            try:
                from src.domain.notifications.service import ConsoleNotificationProvider
                from src.domain.notifications.schemas import AdaptiveCardContent, FactItem

                duration_str = "N/A"
                if alert.duration_seconds:
                    minutes = int(alert.duration_seconds // 60)
                    seconds = int(alert.duration_seconds % 60)
                    duration_str = f"{minutes}m {seconds}s"

                # Build facts list
                facts = [
                    FactItem(title="Severity", value=alert.severity),
                    FactItem(title="Instance", value=alert.instance or "N/A"),
                    FactItem(title="Duration", value=duration_str),
                ]

                # Build adaptive card
                card = AdaptiveCardContent(
                    title=f"[RESOLVED] {alert.alertname}",
                    message=f"Alert has been resolved after {duration_str}",
                    color="00FF00",  # Green for resolved
                    facts=facts,
                )

                # Use console provider for local development
                provider = ConsoleNotificationProvider()
                await provider.send(card)
                logger.info(f"Sent resolution notification for: {alert.alertname}")
            except Exception as e:
                logger.warning(f"Failed to send resolution notification: {e}")

    async def get_alert_stats(self) -> AlertStatsResponse:
        """Get alert statistics.

        Returns:
            AlertStatsResponse with aggregated statistics
        """
        total = len(self._alert_history)
        firing = sum(1 for a in self._alerts.values() if a.status == "firing")
        resolved = sum(1 for a in self._alerts.values() if a.status == "resolved")

        severity_counts = defaultdict(int)
        team_counts = defaultdict(int)

        for alert in self._alert_history:
            severity_counts[alert.severity] += 1

        # Recent alerts (last 50)
        recent = sorted(
            self._alert_history,
            key=lambda x: x.started_at,
            reverse=True
        )[:50]

        return AlertStatsResponse(
            total_alerts=total,
            firing_alerts=firing,
            resolved_alerts=resolved,
            critical_count=severity_counts.get("critical", 0),
            warning_count=severity_counts.get("warning", 0),
            info_count=severity_counts.get("info", 0),
            alerts_by_team=dict(team_counts),
            recent_alerts=recent,
        )

    async def get_firing_alerts(self) -> list[AlertHistoryItem]:
        """Get all currently firing alerts.

        Returns:
            List of firing alerts
        """
        return [
            alert for alert in self._alerts.values()
            if alert.status == "firing"
        ]

    async def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[str] = None,
    ) -> list[AlertHistoryItem]:
        """Get alert history with optional filtering.

        Args:
            limit: Maximum number of alerts to return
            severity: Optional severity filter

        Returns:
            List of AlertHistoryItem
        """
        history = self._alert_history

        if severity:
            history = [a for a in history if a.severity == severity]

        return sorted(
            history,
            key=lambda x: x.started_at,
            reverse=True
        )[:limit]

    async def clear_alerts(self) -> int:
        """Clear all alerts (for testing/maintenance).

        Returns:
            Number of alerts cleared
        """
        count = len(self._alerts)
        self._alerts.clear()
        self._alert_history.clear()
        logger.info(f"Cleared {count} alerts")
        return count


# Global service instance
_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """Get the global AlertService instance.

    Returns:
        AlertService singleton instance
    """
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service
