"""
Admin Dashboard Schemas

Sprint 2 - Story S2-8: Admin Dashboard APIs

Pydantic models for admin dashboard API responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WorkflowStats(BaseModel):
    """Workflow statistics."""
    total: int = Field(..., description="Total workflow count")
    active: int = Field(..., description="Active workflow count")
    draft: int = Field(default=0, description="Draft workflow count")
    archived: int = Field(default=0, description="Archived workflow count")


class ExecutionStats(BaseModel):
    """Execution statistics."""
    total: int = Field(..., description="Total execution count")
    successful: int = Field(..., description="Successful executions")
    failed: int = Field(..., description="Failed executions")
    running: int = Field(default=0, description="Currently running")
    pending: int = Field(default=0, description="Pending executions")
    today: int = Field(default=0, description="Today's executions")
    success_rate: float = Field(..., description="Success rate percentage")


class UserStats(BaseModel):
    """User statistics."""
    total: int = Field(..., description="Total user count")
    active: int = Field(..., description="Active users (last 30 days)")
    admins: int = Field(default=0, description="Admin user count")


class OverviewResponse(BaseModel):
    """Dashboard overview statistics response."""
    workflows: WorkflowStats
    executions: ExecutionStats
    users: UserStats
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TrendDataPoint(BaseModel):
    """Single data point in trend data."""
    date: str = Field(..., description="Date string (YYYY-MM-DD)")
    total: int = Field(default=0, description="Total executions")
    successful: int = Field(default=0, description="Successful executions")
    failed: int = Field(default=0, description="Failed executions")


class TrendResponse(BaseModel):
    """Execution trend response."""
    period: str = Field(..., description="Time period description")
    data: list[TrendDataPoint] = Field(default_factory=list)


class RunningExecution(BaseModel):
    """Details of a running execution."""
    execution_id: str
    workflow_id: str
    workflow_name: Optional[str]
    status: str
    started_at: datetime
    duration_seconds: float
    current_step: Optional[int]
    total_steps: Optional[int]


class RealtimeMetrics(BaseModel):
    """Real-time system metrics."""
    running_executions: list[RunningExecution] = Field(default_factory=list)
    running_count: int = Field(default=0, description="Number of running executions")
    pending_count: int = Field(default=0, description="Number of pending executions")
    recent_executions_5min: int = Field(default=0, description="Executions in last 5 minutes")
    avg_duration_seconds: Optional[float] = Field(None, description="Average duration (last hour)")
    queue_depth: int = Field(default=0, description="Message queue depth")
    active_checkpoints: int = Field(default=0, description="Pending checkpoint approvals")


class SystemStatus(BaseModel):
    """Overall system status."""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    uptime_seconds: float
    version: str
    environment: str
    components: dict[str, str] = Field(default_factory=dict)


class RecentActivity(BaseModel):
    """Recent activity item."""
    id: str
    type: str  # execution, workflow, user, alert
    action: str  # created, updated, completed, failed
    description: str
    timestamp: datetime
    user: Optional[str] = None


class ActivityFeedResponse(BaseModel):
    """Activity feed response."""
    activities: list[RecentActivity] = Field(default_factory=list)
    total_count: int = Field(default=0)
