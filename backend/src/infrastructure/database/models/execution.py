"""
Execution Model

Database model for workflow executions.
"""
import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Text, Integer, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import BaseModel


class ExecutionStatus(str, enum.Enum):
    """Execution status enum."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Execution(BaseModel):
    """Execution model.

    Represents a single execution instance of a workflow.
    """

    __tablename__ = "executions"

    workflow_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    workflow_version_id = Column(UUID(as_uuid=True), nullable=False)
    triggered_by = Column(UUID(as_uuid=True), nullable=False, index=True)

    status = Column(
        Enum(ExecutionStatus, name="executionstatus", create_type=False),
        nullable=True,
        default=ExecutionStatus.PENDING,
        index=True,
    )

    # Execution timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Execution data
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=True)
    execution_metadata = Column("metadata", JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.duration_ms is not None:
            return self.duration_ms / 1000.0
        return None

    @property
    def current_step_index(self) -> Optional[int]:
        """Get current step index from metadata if available."""
        if self.execution_metadata and "current_step" in self.execution_metadata:
            return self.execution_metadata["current_step"]
        return None

    def mark_started(self):
        """Mark execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, output_data: Optional[dict] = None):
        """Mark execution as completed."""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at:
            started = self.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            self.duration_ms = int((self.completed_at - started).total_seconds() * 1000)
        if output_data:
            self.output_data = output_data

    def mark_failed(self, error_message: str):
        """Mark execution as failed."""
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message
        if self.started_at:
            started = self.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            self.duration_ms = int((self.completed_at - started).total_seconds() * 1000)
