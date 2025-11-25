"""
Alert Schemas

Sprint 2 - Story S2-6: Alert Manager Integration

Pydantic models for AlertManager webhook payloads and API responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlertLabel(BaseModel):
    """Alert labels from Prometheus."""
    alertname: str
    severity: str = "info"
    instance: Optional[str] = None
    job: Optional[str] = None
    team: Optional[str] = None
    # Allow extra fields
    class Config:
        extra = "allow"


class AlertAnnotation(BaseModel):
    """Alert annotations from Prometheus."""
    summary: Optional[str] = None
    description: Optional[str] = None
    runbook_url: Optional[str] = None
    # Allow extra fields
    class Config:
        extra = "allow"


class Alert(BaseModel):
    """Single alert from AlertManager."""
    status: str  # "firing" or "resolved"
    labels: AlertLabel
    annotations: AlertAnnotation
    startsAt: str
    endsAt: str
    generatorURL: Optional[str] = None
    fingerprint: str


class AlertManagerPayload(BaseModel):
    """AlertManager webhook payload.

    Reference: https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
    """
    version: str = "4"
    groupKey: str
    truncatedAlerts: int = 0
    status: str  # "firing" or "resolved"
    receiver: str
    groupLabels: dict = Field(default_factory=dict)
    commonLabels: dict = Field(default_factory=dict)
    commonAnnotations: dict = Field(default_factory=dict)
    externalURL: str = ""
    alerts: list[Alert] = Field(default_factory=list)


class AlertResponse(BaseModel):
    """Response model for alert operations."""
    received: bool
    alerts_count: int
    firing_count: int
    resolved_count: int
    message: str


class AlertHistoryItem(BaseModel):
    """Alert history item for dashboard display."""
    fingerprint: str
    alertname: str
    severity: str
    status: str
    summary: Optional[str]
    description: Optional[str]
    instance: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    notified: bool = False


class AlertStatsResponse(BaseModel):
    """Alert statistics response."""
    total_alerts: int
    firing_alerts: int
    resolved_alerts: int
    critical_count: int
    warning_count: int
    info_count: int
    alerts_by_team: dict[str, int]
    recent_alerts: list[AlertHistoryItem]
