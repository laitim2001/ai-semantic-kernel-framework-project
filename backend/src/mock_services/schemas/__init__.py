"""
File: backend/src/mock_services/schemas/__init__.py
Purpose: Pydantic models for mock backend domain entities.
Category: Mock services / schemas
Scope: Phase 51 / Sprint 51.0 Day 1.2

Description:
    9 Pydantic models covering 7 mock domains:
    - CRM: Customer, Order, Ticket
    - KB: KBArticle, KBSearchResult
    - Patrol: PatrolResult
    - Correlation+Incident: Alert, Incident
    - Rootcause: RootCauseFinding
    - Audit: AuditLogEntry
    Each model has minimal realistic fields; example values for OpenAPI doc.

Created: 2026-04-30 (Sprint 51.0 Day 1)
Last Modified: 2026-04-30
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Customer(BaseModel):
    id: str = Field(..., examples=["cust_001"])
    name: str = Field(..., examples=["Acme Corp"])
    email: str = Field(..., examples=["billing@acme.example"])
    tier: Literal["free", "pro", "enterprise"] = "pro"
    created_at: datetime


class Order(BaseModel):
    id: str = Field(..., examples=["ord_0001"])
    customer_id: str
    total: float = Field(..., examples=[1299.50])
    status: Literal["pending", "paid", "shipped", "cancelled"] = "paid"
    items_count: int = Field(..., ge=1, examples=[3])
    created_at: datetime


class Ticket(BaseModel):
    id: str = Field(..., examples=["tkt_001"])
    customer_id: str
    subject: str
    status: Literal["open", "in_progress", "resolved", "closed"] = "open"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    created_at: datetime


class KBArticle(BaseModel):
    id: str = Field(..., examples=["kb_001"])
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)


class KBSearchResult(BaseModel):
    article: KBArticle
    score: float = Field(..., ge=0.0, le=1.0)


class PatrolResult(BaseModel):
    id: str = Field(..., examples=["pat_001"])
    server_id: str = Field(..., examples=["web-01"])
    health: Literal["ok", "warning", "critical"] = "ok"
    metrics: dict[str, float] = Field(
        default_factory=dict,
        examples=[{"cpu_pct": 32.1, "mem_pct": 47.8, "disk_pct": 61.2}],
    )
    checked_at: datetime


class Alert(BaseModel):
    id: str = Field(..., examples=["alert_001"])
    severity: Literal["info", "warning", "error", "critical"] = "warning"
    source: str = Field(..., examples=["prometheus"])
    server_id: str | None = None
    message: str
    timestamp: datetime


class Incident(BaseModel):
    id: str = Field(..., examples=["inc_001"])
    title: str
    severity: Literal["low", "medium", "high", "critical"] = "high"
    status: Literal["open", "investigating", "resolved", "closed"] = "open"
    alert_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class RootCauseFinding(BaseModel):
    id: str = Field(..., examples=["rcf_001"])
    incident_id: str
    hypothesis: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    created_at: datetime


class AuditLogEntry(BaseModel):
    id: str = Field(..., examples=["aud_001"])
    action: str = Field(..., examples=["incident.close"])
    user_id: str
    target: str = Field(..., examples=["inc_001"])
    metadata: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime


__all__ = [
    "Customer",
    "Order",
    "Ticket",
    "KBArticle",
    "KBSearchResult",
    "PatrolResult",
    "Alert",
    "Incident",
    "RootCauseFinding",
    "AuditLogEntry",
]
