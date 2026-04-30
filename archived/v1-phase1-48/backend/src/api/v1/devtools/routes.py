# =============================================================================
# IPA Platform - DevTools API Routes
# =============================================================================
# Sprint 4: Developer Experience - DevUI Visual Debugging
#
# REST API endpoints for execution tracing and debugging:
#   - POST /devtools/traces - Start a new trace
#   - GET /devtools/traces - List traces
#   - GET /devtools/traces/{execution_id} - Get trace details
#   - POST /devtools/traces/{execution_id}/end - End a trace
#   - DELETE /devtools/traces/{execution_id} - Delete a trace
#   - POST /devtools/traces/{execution_id}/events - Add event
#   - GET /devtools/traces/{execution_id}/events - Get events
#   - POST /devtools/traces/{execution_id}/spans - Start span
#   - POST /devtools/spans/{span_id}/end - End span
#   - GET /devtools/traces/{execution_id}/timeline - Get timeline
#   - GET /devtools/traces/{execution_id}/statistics - Get statistics
#   - GET /devtools/health - Health check
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.devtools.schemas import (
    AddEventRequest,
    EndTraceRequest,
    EventListResponse,
    EventResponse,
    HealthCheckResponse,
    SpanResponse,
    StartSpanRequest,
    StartTraceRequest,
    TimelineEntryResponse,
    TimelineResponse,
    TraceListResponse,
    TraceResponse,
    TraceStatisticsResponse,
)
from src.domain.devtools import (
    ExecutionTracer,
    TraceEventType,
    TracerError,
)
from src.domain.devtools.tracer import TraceSeverity


router = APIRouter(prefix="/devtools", tags=["devtools"])


# =============================================================================
# Service Instance Management
# =============================================================================

_tracer: Optional[ExecutionTracer] = None


def get_tracer() -> ExecutionTracer:
    """Get or create tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = ExecutionTracer()
    return _tracer


def set_tracer(tracer: ExecutionTracer) -> None:
    """Set tracer instance (for testing)."""
    global _tracer
    _tracer = tracer


# =============================================================================
# Helper Functions
# =============================================================================


def _to_trace_response(trace) -> TraceResponse:
    """Convert trace to response."""
    return TraceResponse(
        id=trace.id,
        execution_id=trace.execution_id,
        workflow_id=trace.workflow_id,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        duration_ms=trace.duration_ms,
        status=trace.status,
        event_count=len(trace.events),
        span_count=len(trace.spans),
        metadata=trace.metadata,
    )


def _to_event_response(event) -> EventResponse:
    """Convert event to response."""
    return EventResponse(
        id=event.id,
        trace_id=event.trace_id,
        event_type=event.event_type.value,
        timestamp=event.timestamp,
        data=event.data,
        severity=event.severity.value,
        parent_event_id=event.parent_event_id,
        executor_id=event.executor_id,
        step_number=event.step_number,
        duration_ms=event.duration_ms,
        tags=event.tags,
        metadata=event.metadata,
    )


def _to_span_response(span) -> SpanResponse:
    """Convert span to response."""
    return SpanResponse(
        id=span.id,
        name=span.name,
        start_time=span.start_time,
        end_time=span.end_time,
        duration_ms=span.duration_ms,
        parent_span_id=span.parent_span_id,
        event_count=len(span.events),
        metadata=span.metadata,
    )


def _to_timeline_entry_response(entry) -> TimelineEntryResponse:
    """Convert timeline entry to response."""
    return TimelineEntryResponse(
        timestamp=entry.timestamp,
        event_type=entry.event_type.value,
        label=entry.label,
        details=entry.details,
        severity=entry.severity.value,
        duration_ms=entry.duration_ms,
        children=[_to_timeline_entry_response(c) for c in entry.children],
    )


# =============================================================================
# Static Routes (before dynamic routes)
# =============================================================================


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check devtools service health."""
    tracer = get_tracer()

    return HealthCheckResponse(
        service="devtools",
        status="healthy",
        active_traces=tracer.get_trace_count(),
    )


@router.get("/traces", response_model=TraceListResponse)
async def list_traces(
    workflow_id: Optional[UUID] = Query(None, description="Filter by workflow ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
):
    """List execution traces."""
    tracer = get_tracer()

    traces = tracer.list_traces(
        workflow_id=workflow_id,
        status=status,
        limit=limit,
    )

    return TraceListResponse(
        traces=[_to_trace_response(t) for t in traces],
        total=len(traces),
    )


# =============================================================================
# Trace Management
# =============================================================================


@router.post("/traces", response_model=TraceResponse)
async def start_trace(request: StartTraceRequest):
    """Start a new execution trace."""
    tracer = get_tracer()

    trace = tracer.start_trace(
        execution_id=request.execution_id,
        workflow_id=request.workflow_id,
        metadata=request.metadata,
    )

    return _to_trace_response(trace)


@router.get("/traces/{execution_id}", response_model=TraceResponse)
async def get_trace(execution_id: UUID):
    """Get trace details."""
    tracer = get_tracer()

    trace = tracer.get_trace(execution_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {execution_id}")

    return _to_trace_response(trace)


@router.post("/traces/{execution_id}/end", response_model=TraceResponse)
async def end_trace(execution_id: UUID, request: EndTraceRequest):
    """End an execution trace."""
    tracer = get_tracer()

    trace = tracer.end_trace(
        execution_id=execution_id,
        status=request.status,
        result=request.result,
    )

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {execution_id}")

    return _to_trace_response(trace)


@router.delete("/traces/{execution_id}")
async def delete_trace(execution_id: UUID):
    """Delete a trace."""
    tracer = get_tracer()

    if tracer.delete_trace(execution_id):
        return {"message": "Trace deleted", "execution_id": str(execution_id)}
    else:
        raise HTTPException(status_code=404, detail=f"Trace not found: {execution_id}")


# =============================================================================
# Event Management
# =============================================================================


@router.post("/traces/{execution_id}/events", response_model=EventResponse)
async def add_event(execution_id: UUID, request: AddEventRequest):
    """Add an event to a trace."""
    tracer = get_tracer()

    # Validate event type
    try:
        event_type = TraceEventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {request.event_type}",
        )

    # Validate severity
    try:
        severity = TraceSeverity(request.severity)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity: {request.severity}",
        )

    event = tracer.add_event(
        execution_id=execution_id,
        event_type=event_type,
        data=request.data,
        severity=severity,
        parent_event_id=request.parent_event_id,
        executor_id=request.executor_id,
        step_number=request.step_number,
        duration_ms=request.duration_ms,
        tags=request.tags,
        metadata=request.metadata,
    )

    if not event:
        raise HTTPException(status_code=404, detail=f"Trace not found: {execution_id}")

    return _to_event_response(event)


@router.get("/traces/{execution_id}/events", response_model=EventListResponse)
async def get_events(
    execution_id: UUID,
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    executor_id: Optional[str] = Query(None, description="Filter by executor ID"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum results"),
):
    """Get events for a trace."""
    tracer = get_tracer()

    # Parse event types
    types_list = None
    if event_types:
        try:
            types_list = [TraceEventType(t.strip()) for t in event_types.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")

    # Parse severity
    sev = None
    if severity:
        try:
            sev = TraceSeverity(severity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

    events = tracer.get_events(
        execution_id=execution_id,
        event_types=types_list,
        severity=sev,
        executor_id=executor_id,
        limit=limit,
    )

    return EventListResponse(
        events=[_to_event_response(e) for e in events],
        total=len(events),
    )


# =============================================================================
# Span Management
# =============================================================================


@router.post("/traces/{execution_id}/spans", response_model=SpanResponse)
async def start_span(execution_id: UUID, request: StartSpanRequest):
    """Start a new span."""
    tracer = get_tracer()

    span = tracer.start_span(
        execution_id=execution_id,
        name=request.name,
        parent_span_id=request.parent_span_id,
        metadata=request.metadata,
    )

    if not span:
        raise HTTPException(status_code=404, detail=f"Trace not found: {execution_id}")

    return _to_span_response(span)


@router.post("/spans/{span_id}/end", response_model=SpanResponse)
async def end_span(span_id: UUID):
    """End a span."""
    tracer = get_tracer()

    span = tracer.end_span(span_id)
    if not span:
        raise HTTPException(status_code=404, detail=f"Span not found: {span_id}")

    return _to_span_response(span)


# =============================================================================
# Timeline and Statistics
# =============================================================================


@router.get("/traces/{execution_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    execution_id: UUID,
    include_details: bool = Query(True, description="Include event details"),
):
    """Get timeline for visualization."""
    tracer = get_tracer()

    trace = tracer.get_trace(execution_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {execution_id}")

    timeline = tracer.get_timeline(
        execution_id=execution_id,
        include_details=include_details,
    )

    return TimelineResponse(
        execution_id=execution_id,
        entries=[_to_timeline_entry_response(e) for e in timeline],
        total_duration_ms=trace.duration_ms,
    )


@router.get("/traces/{execution_id}/statistics", response_model=TraceStatisticsResponse)
async def get_statistics(execution_id: UUID):
    """Get statistics for a trace."""
    tracer = get_tracer()

    stats = tracer.get_statistics(execution_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Trace not found: {execution_id}")

    return TraceStatisticsResponse(
        execution_id=execution_id,
        total_events=stats.total_events,
        events_by_type=stats.events_by_type,
        total_duration_ms=stats.total_duration_ms,
        llm_calls=stats.llm_calls,
        llm_total_ms=stats.llm_total_ms,
        tool_calls=stats.tool_calls,
        tool_total_ms=stats.tool_total_ms,
        errors=stats.errors,
        warnings=stats.warnings,
        checkpoints=stats.checkpoints,
    )
