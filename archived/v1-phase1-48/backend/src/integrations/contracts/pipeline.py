"""Cross-module contract interfaces for the E2E pipeline.

Defines data structures shared between orchestration/ and hybrid/ modules,
enabling loose coupling without direct imports.

Sprint 108 — Phase 35 A0 core hypothesis validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PipelineSource(str, Enum):
    """Source of the pipeline request."""

    USER = "user"
    SERVICENOW = "servicenow"
    PROMETHEUS = "prometheus"
    API = "api"


class PipelineRequest(BaseModel):
    """Input to the orchestration pipeline."""

    content: str
    source: PipelineSource = PipelineSource.USER
    mode: Optional[str] = None  # Sprint 144: user-selected mode (chat/workflow/swarm)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PipelineResponse(BaseModel):
    """Output from the orchestration pipeline."""

    content: str
    intent_category: Optional[str] = None
    confidence: Optional[float] = None
    risk_level: Optional[str] = None
    routing_layer: Optional[str] = None
    execution_mode: Optional[str] = None  # Sprint 144: user-selected or auto-detected mode
    suggested_mode: Optional[str] = None  # Sprint 144: routing suggestion (user can ignore)
    framework_used: str = "orchestrator_agent"
    session_id: Optional[str] = None
    is_complete: bool = True
    task_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Sprint 144: function calling results
    processing_time_ms: Optional[float] = None
