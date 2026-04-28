# =============================================================================
# IPA Platform - Execution Tracer
# =============================================================================
# Sprint 4: Developer Experience - DevUI Visual Debugging
#
# Execution tracing service for real-time debugging and visualization.
# Captures workflow execution events for timeline display and analysis.
#
# Features:
#   - Event capture: workflow, executor, LLM, tool, checkpoint, error events
#   - Timeline generation for visual debugging
#   - Trace filtering and search
#   - Statistics and performance metrics
#   - Event streaming support (for WebSocket)
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class TraceEventType(str, Enum):
    """Types of traceable events."""

    # Workflow lifecycle
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    WORKFLOW_PAUSE = "workflow_pause"
    WORKFLOW_RESUME = "workflow_resume"

    # Executor lifecycle
    EXECUTOR_START = "executor_start"
    EXECUTOR_END = "executor_end"
    EXECUTOR_SKIP = "executor_skip"

    # LLM interactions
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    LLM_ERROR = "llm_error"
    LLM_STREAM_START = "llm_stream_start"
    LLM_STREAM_CHUNK = "llm_stream_chunk"
    LLM_STREAM_END = "llm_stream_end"

    # Tool operations
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"

    # Checkpoints
    CHECKPOINT_CREATED = "checkpoint_created"
    CHECKPOINT_APPROVED = "checkpoint_approved"
    CHECKPOINT_REJECTED = "checkpoint_rejected"
    CHECKPOINT_TIMEOUT = "checkpoint_timeout"

    # State changes
    STATE_CHANGE = "state_change"
    VARIABLE_SET = "variable_set"
    CONTEXT_UPDATE = "context_update"

    # Control flow
    CONDITION_EVAL = "condition_eval"
    BRANCH_TAKEN = "branch_taken"
    LOOP_ITERATION = "loop_iteration"

    # Errors and warnings
    ERROR = "error"
    WARNING = "warning"
    RETRY = "retry"

    # Custom/debug
    DEBUG = "debug"
    CUSTOM = "custom"


class TraceSeverity(str, Enum):
    """Severity levels for trace events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TraceEvent:
    """A single trace event."""

    id: UUID
    trace_id: UUID
    event_type: TraceEventType
    timestamp: datetime
    data: Dict[str, Any]
    severity: TraceSeverity = TraceSeverity.INFO
    parent_event_id: Optional[UUID] = None
    executor_id: Optional[str] = None
    step_number: Optional[int] = None
    duration_ms: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "trace_id": str(self.trace_id),
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "severity": self.severity.value,
            "parent_event_id": str(self.parent_event_id) if self.parent_event_id else None,
            "executor_id": self.executor_id,
            "step_number": self.step_number,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class TraceSpan:
    """A span representing a duration (start to end)."""

    id: UUID
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    parent_span_id: Optional[UUID] = None
    events: List[TraceEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        """Get span duration in milliseconds."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "parent_span_id": str(self.parent_span_id) if self.parent_span_id else None,
            "event_count": len(self.events),
            "metadata": self.metadata,
        }


@dataclass
class ExecutionTrace:
    """Complete trace for an execution."""

    id: UUID
    execution_id: UUID
    workflow_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str = "running"
    events: List[TraceEvent] = field(default_factory=list)
    spans: List[TraceSpan] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        """Get total trace duration in milliseconds."""
        if self.ended_at and self.started_at:
            delta = self.ended_at - self.started_at
            return delta.total_seconds() * 1000
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "execution_id": str(self.execution_id),
            "workflow_id": str(self.workflow_id),
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "event_count": len(self.events),
            "span_count": len(self.spans),
            "metadata": self.metadata,
        }


@dataclass
class TimelineEntry:
    """Entry for timeline visualization."""

    timestamp: datetime
    event_type: TraceEventType
    label: str
    details: str
    severity: TraceSeverity
    duration_ms: Optional[float] = None
    children: List["TimelineEntry"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "label": self.label,
            "details": self.details,
            "severity": self.severity.value,
            "duration_ms": self.duration_ms,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class TraceStatistics:
    """Statistics for a trace."""

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_events": self.total_events,
            "events_by_type": self.events_by_type,
            "total_duration_ms": self.total_duration_ms,
            "llm_calls": self.llm_calls,
            "llm_total_ms": self.llm_total_ms,
            "tool_calls": self.tool_calls,
            "tool_total_ms": self.tool_total_ms,
            "errors": self.errors,
            "warnings": self.warnings,
            "checkpoints": self.checkpoints,
        }


# =============================================================================
# Exceptions
# =============================================================================


class TracerError(Exception):
    """Base exception for tracer errors."""

    pass


# =============================================================================
# Execution Tracer Service
# =============================================================================


class ExecutionTracer:
    """
    Execution tracer service for debugging and visualization.

    Captures and manages execution traces with support for:
    - Real-time event capture
    - Span tracking (start/end pairs)
    - Timeline generation
    - Statistics calculation
    - Event streaming
    """

    def __init__(self):
        """Initialize the tracer."""
        self._traces: Dict[UUID, ExecutionTrace] = {}
        self._active_spans: Dict[UUID, TraceSpan] = {}
        self._event_handlers: Dict[TraceEventType, List[Callable]] = {}
        self._stream_subscribers: Dict[UUID, List[Callable]] = {}

    # =========================================================================
    # Trace Lifecycle
    # =========================================================================

    def start_trace(
        self,
        execution_id: UUID,
        workflow_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionTrace:
        """Start a new execution trace."""
        trace = ExecutionTrace(
            id=uuid4(),
            execution_id=execution_id,
            workflow_id=workflow_id,
            started_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        self._traces[execution_id] = trace

        # Add initial event
        self.add_event(
            execution_id=execution_id,
            event_type=TraceEventType.WORKFLOW_START,
            data={
                "workflow_id": str(workflow_id),
                "execution_id": str(execution_id),
            },
        )

        return trace

    def end_trace(
        self,
        execution_id: UUID,
        status: str = "completed",
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExecutionTrace]:
        """End an execution trace."""
        trace = self._traces.get(execution_id)
        if not trace:
            return None

        trace.ended_at = datetime.utcnow()
        trace.status = status

        # Add final event
        self.add_event(
            execution_id=execution_id,
            event_type=TraceEventType.WORKFLOW_END,
            data={
                "status": status,
                "result": result or {},
                "duration_ms": trace.duration_ms,
            },
        )

        return trace

    def get_trace(self, execution_id: UUID) -> Optional[ExecutionTrace]:
        """Get trace for an execution."""
        return self._traces.get(execution_id)

    def delete_trace(self, execution_id: UUID) -> bool:
        """Delete a trace."""
        if execution_id in self._traces:
            del self._traces[execution_id]
            return True
        return False

    def list_traces(
        self,
        workflow_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExecutionTrace]:
        """List traces with optional filtering."""
        traces = list(self._traces.values())

        if workflow_id:
            traces = [t for t in traces if t.workflow_id == workflow_id]

        if status:
            traces = [t for t in traces if t.status == status]

        # Sort by start time (newest first)
        traces.sort(key=lambda t: t.started_at, reverse=True)

        return traces[:limit]

    # =========================================================================
    # Event Management
    # =========================================================================

    def add_event(
        self,
        execution_id: UUID,
        event_type: TraceEventType,
        data: Dict[str, Any],
        severity: TraceSeverity = TraceSeverity.INFO,
        parent_event_id: Optional[UUID] = None,
        executor_id: Optional[str] = None,
        step_number: Optional[int] = None,
        duration_ms: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TraceEvent]:
        """Add an event to a trace."""
        trace = self._traces.get(execution_id)
        if not trace:
            return None

        event = TraceEvent(
            id=uuid4(),
            trace_id=trace.id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data,
            severity=severity,
            parent_event_id=parent_event_id,
            executor_id=executor_id,
            step_number=step_number,
            duration_ms=duration_ms,
            tags=tags or [],
            metadata=metadata or {},
        )

        trace.events.append(event)

        # Notify handlers
        self._notify_handlers(event_type, event)

        # Notify stream subscribers
        self._notify_subscribers(execution_id, event)

        return event

    def get_events(
        self,
        execution_id: UUID,
        event_types: Optional[List[TraceEventType]] = None,
        severity: Optional[TraceSeverity] = None,
        executor_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[TraceEvent]:
        """Get events with filtering."""
        trace = self._traces.get(execution_id)
        if not trace:
            return []

        events = trace.events

        if event_types:
            events = [e for e in events if e.event_type in event_types]

        if severity:
            events = [e for e in events if e.severity == severity]

        if executor_id:
            events = [e for e in events if e.executor_id == executor_id]

        return events[:limit]

    # =========================================================================
    # Span Management
    # =========================================================================

    def start_span(
        self,
        execution_id: UUID,
        name: str,
        parent_span_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TraceSpan]:
        """Start a new span."""
        trace = self._traces.get(execution_id)
        if not trace:
            return None

        span = TraceSpan(
            id=uuid4(),
            name=name,
            start_time=datetime.utcnow(),
            parent_span_id=parent_span_id,
            metadata=metadata or {},
        )

        trace.spans.append(span)
        self._active_spans[span.id] = span

        return span

    def end_span(self, span_id: UUID) -> Optional[TraceSpan]:
        """End a span."""
        span = self._active_spans.get(span_id)
        if not span:
            return None

        span.end_time = datetime.utcnow()
        del self._active_spans[span_id]

        return span

    def get_span(self, span_id: UUID) -> Optional[TraceSpan]:
        """Get a span by ID."""
        return self._active_spans.get(span_id)

    # =========================================================================
    # Timeline Generation
    # =========================================================================

    def get_timeline(
        self,
        execution_id: UUID,
        include_details: bool = True,
    ) -> List[TimelineEntry]:
        """Generate timeline entries for visualization."""
        trace = self._traces.get(execution_id)
        if not trace:
            return []

        timeline: List[TimelineEntry] = []
        event_stack: Dict[str, TraceEvent] = {}

        for event in trace.events:
            entry = self._create_timeline_entry(event, include_details)

            # Handle paired events (start/end)
            if event.event_type in [
                TraceEventType.WORKFLOW_START,
                TraceEventType.EXECUTOR_START,
                TraceEventType.LLM_REQUEST,
                TraceEventType.TOOL_CALL,
            ]:
                key = f"{event.event_type.value}:{event.executor_id or 'root'}"
                event_stack[key] = event
                timeline.append(entry)

            elif event.event_type in [
                TraceEventType.WORKFLOW_END,
                TraceEventType.EXECUTOR_END,
                TraceEventType.LLM_RESPONSE,
                TraceEventType.TOOL_RESULT,
            ]:
                # Find matching start event
                start_type = event.event_type.value.replace("_end", "_start")
                start_type = start_type.replace("_response", "_request")
                start_type = start_type.replace("_result", "_call")
                key = f"{start_type}:{event.executor_id or 'root'}"

                if key in event_stack:
                    start_event = event_stack[key]
                    delta = event.timestamp - start_event.timestamp
                    entry.duration_ms = delta.total_seconds() * 1000
                    del event_stack[key]

                timeline.append(entry)

            else:
                timeline.append(entry)

        return timeline

    def _create_timeline_entry(
        self,
        event: TraceEvent,
        include_details: bool,
    ) -> TimelineEntry:
        """Create a timeline entry from an event."""
        # Generate label based on event type
        label = self._get_event_label(event)

        # Generate details
        details = ""
        if include_details:
            details = self._get_event_details(event)

        return TimelineEntry(
            timestamp=event.timestamp,
            event_type=event.event_type,
            label=label,
            details=details,
            severity=event.severity,
            duration_ms=event.duration_ms,
        )

    def _get_event_label(self, event: TraceEvent) -> str:
        """Get human-readable label for an event."""
        labels = {
            TraceEventType.WORKFLOW_START: "Workflow Started",
            TraceEventType.WORKFLOW_END: "Workflow Completed",
            TraceEventType.WORKFLOW_PAUSE: "Workflow Paused",
            TraceEventType.WORKFLOW_RESUME: "Workflow Resumed",
            TraceEventType.EXECUTOR_START: f"Executor: {event.executor_id or 'Unknown'}",
            TraceEventType.EXECUTOR_END: f"Executor Complete: {event.executor_id or 'Unknown'}",
            TraceEventType.LLM_REQUEST: "LLM Request",
            TraceEventType.LLM_RESPONSE: "LLM Response",
            TraceEventType.LLM_ERROR: "LLM Error",
            TraceEventType.TOOL_CALL: f"Tool: {event.data.get('tool_name', 'Unknown')}",
            TraceEventType.TOOL_RESULT: f"Tool Result: {event.data.get('tool_name', 'Unknown')}",
            TraceEventType.TOOL_ERROR: f"Tool Error: {event.data.get('tool_name', 'Unknown')}",
            TraceEventType.CHECKPOINT_CREATED: "Checkpoint Created",
            TraceEventType.CHECKPOINT_APPROVED: "Checkpoint Approved",
            TraceEventType.CHECKPOINT_REJECTED: "Checkpoint Rejected",
            TraceEventType.ERROR: f"Error: {event.data.get('error_type', 'Unknown')}",
            TraceEventType.WARNING: f"Warning: {event.data.get('message', '')[:50]}",
        }
        return labels.get(event.event_type, event.event_type.value)

    def _get_event_details(self, event: TraceEvent) -> str:
        """Get details string for an event."""
        if event.event_type == TraceEventType.LLM_REQUEST:
            prompt = event.data.get("prompt", "")
            return f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}"

        elif event.event_type == TraceEventType.LLM_RESPONSE:
            response = event.data.get("response", "")
            tokens = event.data.get("tokens_used", 0)
            return f"Response: {response[:100]}... (Tokens: {tokens})"

        elif event.event_type == TraceEventType.TOOL_CALL:
            args = event.data.get("arguments", {})
            return f"Arguments: {str(args)[:100]}"

        elif event.event_type == TraceEventType.TOOL_RESULT:
            result = event.data.get("result", "")
            return f"Result: {str(result)[:100]}"

        elif event.event_type == TraceEventType.ERROR:
            return event.data.get("message", "Unknown error")

        elif event.event_type == TraceEventType.STATE_CHANGE:
            old = event.data.get("old_state", "")
            new = event.data.get("new_state", "")
            return f"State: {old} -> {new}"

        else:
            return str(event.data)[:200] if event.data else ""

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self, execution_id: UUID) -> Optional[TraceStatistics]:
        """Get statistics for a trace."""
        trace = self._traces.get(execution_id)
        if not trace:
            return None

        events_by_type: Dict[str, int] = {}
        llm_calls = 0
        llm_total_ms = 0.0
        tool_calls = 0
        tool_total_ms = 0.0
        errors = 0
        warnings = 0
        checkpoints = 0

        for event in trace.events:
            # Count by type
            type_key = event.event_type.value
            events_by_type[type_key] = events_by_type.get(type_key, 0) + 1

            # LLM metrics
            if event.event_type == TraceEventType.LLM_RESPONSE:
                llm_calls += 1
                if event.duration_ms:
                    llm_total_ms += event.duration_ms

            # Tool metrics
            if event.event_type == TraceEventType.TOOL_RESULT:
                tool_calls += 1
                if event.duration_ms:
                    tool_total_ms += event.duration_ms

            # Error/warning counts
            if event.event_type == TraceEventType.ERROR:
                errors += 1
            if event.event_type == TraceEventType.WARNING:
                warnings += 1

            # Checkpoint counts
            if event.event_type in [
                TraceEventType.CHECKPOINT_CREATED,
                TraceEventType.CHECKPOINT_APPROVED,
                TraceEventType.CHECKPOINT_REJECTED,
            ]:
                checkpoints += 1

        return TraceStatistics(
            total_events=len(trace.events),
            events_by_type=events_by_type,
            total_duration_ms=trace.duration_ms,
            llm_calls=llm_calls,
            llm_total_ms=llm_total_ms,
            tool_calls=tool_calls,
            tool_total_ms=tool_total_ms,
            errors=errors,
            warnings=warnings,
            checkpoints=checkpoints,
        )

    # =========================================================================
    # Event Handlers (for extensibility)
    # =========================================================================

    def on_event(
        self,
        event_type: TraceEventType,
        handler: Callable[[TraceEvent], None],
    ) -> None:
        """Register an event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def _notify_handlers(
        self,
        event_type: TraceEventType,
        event: TraceEvent,
    ) -> None:
        """Notify all handlers for an event type."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # Don't let handler errors affect tracing

    # =========================================================================
    # Streaming Support
    # =========================================================================

    def subscribe(
        self,
        execution_id: UUID,
        callback: Callable[[TraceEvent], None],
    ) -> None:
        """Subscribe to events for an execution."""
        if execution_id not in self._stream_subscribers:
            self._stream_subscribers[execution_id] = []
        self._stream_subscribers[execution_id].append(callback)

    def unsubscribe(
        self,
        execution_id: UUID,
        callback: Callable[[TraceEvent], None],
    ) -> None:
        """Unsubscribe from events."""
        if execution_id in self._stream_subscribers:
            self._stream_subscribers[execution_id] = [
                c for c in self._stream_subscribers[execution_id] if c != callback
            ]

    def _notify_subscribers(
        self,
        execution_id: UUID,
        event: TraceEvent,
    ) -> None:
        """Notify all subscribers for an execution."""
        subscribers = self._stream_subscribers.get(execution_id, [])
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                pass  # Don't let subscriber errors affect tracing

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def clear_all(self) -> None:
        """Clear all traces (for testing)."""
        self._traces.clear()
        self._active_spans.clear()
        self._stream_subscribers.clear()

    def get_trace_count(self) -> int:
        """Get number of active traces."""
        return len(self._traces)
