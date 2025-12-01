# =============================================================================
# IPA Platform - DevTools API Schemas
# =============================================================================
# Sprint 4: Developer Experience - DevUI Visual Debugging
#
# Pydantic schemas for DevTools API request/response validation.
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Trace Schemas
# =============================================================================


class StartTraceRequest(BaseModel):
    """Request to start a new trace."""

    execution_id: UUID = Field(..., description="Execution ID to trace")
    workflow_id: UUID = Field(..., description="Workflow ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TraceResponse(BaseModel):
    """Trace response."""

    id: UUID
    execution_id: UUID
    workflow_id: UUID
    started_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[float]
    status: str
    event_count: int
    span_count: int
    metadata: Dict[str, Any]


class TraceListResponse(BaseModel):
    """Trace list response."""

    traces: List[TraceResponse]
    total: int


class EndTraceRequest(BaseModel):
    """Request to end a trace."""

    status: str = Field("completed", description="Final status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Execution result")


# =============================================================================
# Event Schemas
# =============================================================================


class AddEventRequest(BaseModel):
    """Request to add a trace event."""

    event_type: str = Field(..., description="Type of event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    severity: str = Field("info", description="Event severity")
    parent_event_id: Optional[UUID] = Field(None, description="Parent event ID")
    executor_id: Optional[str] = Field(None, description="Executor ID")
    step_number: Optional[int] = Field(None, description="Step number")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    tags: List[str] = Field(default_factory=list, description="Event tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EventResponse(BaseModel):
    """Event response."""

    id: UUID
    trace_id: UUID
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    severity: str
    parent_event_id: Optional[UUID]
    executor_id: Optional[str]
    step_number: Optional[int]
    duration_ms: Optional[float]
    tags: List[str]
    metadata: Dict[str, Any]


class EventListResponse(BaseModel):
    """Event list response."""

    events: List[EventResponse]
    total: int


# =============================================================================
# Span Schemas
# =============================================================================


class StartSpanRequest(BaseModel):
    """Request to start a span."""

    name: str = Field(..., description="Span name")
    parent_span_id: Optional[UUID] = Field(None, description="Parent span ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SpanResponse(BaseModel):
    """Span response."""

    id: UUID
    name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    parent_span_id: Optional[UUID]
    event_count: int
    metadata: Dict[str, Any]


# =============================================================================
# Timeline Schemas
# =============================================================================


class TimelineEntryResponse(BaseModel):
    """Timeline entry response."""

    timestamp: datetime
    event_type: str
    label: str
    details: str
    severity: str
    duration_ms: Optional[float]
    children: List["TimelineEntryResponse"] = Field(default_factory=list)


class TimelineResponse(BaseModel):
    """Timeline response."""

    execution_id: UUID
    entries: List[TimelineEntryResponse]
    total_duration_ms: Optional[float]


# =============================================================================
# Statistics Schemas
# =============================================================================


class TraceStatisticsResponse(BaseModel):
    """Trace statistics response."""

    execution_id: UUID
    total_events: int
    events_by_type: Dict[str, int]
    total_duration_ms: Optional[float]
    llm_calls: int
    llm_total_ms: float
    tool_calls: int
    tool_total_ms: float
    errors: int
    warnings: int
    checkpoints: int


# =============================================================================
# Health Check Schema
# =============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response."""

    service: str = "devtools"
    status: str
    active_traces: int


# Allow self-reference in TimelineEntryResponse
TimelineEntryResponse.model_rebuild()
