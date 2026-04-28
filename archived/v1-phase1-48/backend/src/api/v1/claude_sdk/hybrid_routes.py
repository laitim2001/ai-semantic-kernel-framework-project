"""Claude SDK Hybrid API routes.

Sprint 51: S51-4 Hybrid API Routes (5 pts)
Provides REST API endpoints for hybrid orchestration between Claude SDK and MS Agent Framework.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.integrations.claude_sdk.hybrid.orchestrator import (
    HybridOrchestrator,
    ExecutionContext,
)
from src.integrations.claude_sdk.hybrid.types import (
    TaskCapability,
    Framework,
    TaskAnalysis,
    HybridResult,
    HybridSessionConfig,
)
from src.integrations.claude_sdk.hybrid.synchronizer import ContextSynchronizer
from src.integrations.claude_sdk.hybrid.capability import CapabilityMatcher


# --- Enums ---


class FrameworkType(str, Enum):
    """Framework types for hybrid orchestration."""

    CLAUDE_SDK = "claude_sdk"
    MICROSOFT_AGENT = "microsoft_agent"
    AUTO = "auto"


class TaskCapabilityType(str, Enum):
    """Task capability types."""

    MULTI_AGENT = "multi_agent"
    HANDOFF = "handoff"
    FILE_OPERATIONS = "file_operations"
    CODE_EXECUTION = "code_execution"
    WEB_SEARCH = "web_search"
    TOOL_USE = "tool_use"
    CONVERSATION = "conversation"
    PLANNING = "planning"


# --- Schemas ---


class HybridExecuteRequest(BaseModel):
    """Request schema for hybrid execution."""

    task: str = Field(..., description="Task to execute", min_length=1)
    session_id: Optional[str] = Field(None, description="Optional session ID")
    preferred_framework: FrameworkType = Field(
        FrameworkType.AUTO, description="Preferred framework"
    )
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")
    tools: Optional[List[str]] = Field(None, description="Available tools")
    timeout: Optional[float] = Field(None, description="Execution timeout", ge=1.0, le=600.0)


class ToolCallInfo(BaseModel):
    """Schema for tool call information."""

    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    result: Optional[Any] = Field(None, description="Tool result")
    duration_ms: Optional[float] = Field(None, description="Execution duration")


class HybridExecuteResponse(BaseModel):
    """Response schema for hybrid execution."""

    session_id: str = Field(..., description="Session ID")
    framework_used: FrameworkType = Field(..., description="Framework that handled execution")
    success: bool = Field(..., description="Whether execution succeeded")
    content: Optional[str] = Field(None, description="Response content")
    tool_calls: List[ToolCallInfo] = Field(default_factory=list, description="Tool calls made")
    execution_time_ms: Optional[float] = Field(None, description="Total execution time")
    error: Optional[str] = Field(None, description="Error message if failed")


class HybridAnalyzeRequest(BaseModel):
    """Request schema for task analysis."""

    task: str = Field(..., description="Task to analyze", min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict, description="Task context")


class CapabilityInfo(BaseModel):
    """Schema for capability information."""

    capability: TaskCapabilityType = Field(..., description="Capability type")
    confidence: float = Field(..., description="Confidence score (0-1)", ge=0.0, le=1.0)


class HybridAnalyzeResponse(BaseModel):
    """Response schema for task analysis."""

    task: str = Field(..., description="Original task")
    recommended_framework: FrameworkType = Field(..., description="Recommended framework")
    capabilities: List[CapabilityInfo] = Field(..., description="Detected capabilities")
    complexity_score: float = Field(..., description="Task complexity (0-1)", ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Analysis reasoning")


class HybridMetricsResponse(BaseModel):
    """Response schema for hybrid metrics."""

    total_executions: int = Field(..., description="Total executions")
    claude_sdk_executions: int = Field(..., description="Claude SDK executions")
    ms_agent_executions: int = Field(..., description="MS Agent Framework executions")
    avg_execution_time_ms: float = Field(..., description="Average execution time")
    success_rate: float = Field(..., description="Success rate (0-1)")
    capability_distribution: Dict[str, int] = Field(..., description="Capability usage counts")
    last_updated: datetime = Field(..., description="Last update timestamp")


class ContextSyncRequest(BaseModel):
    """Request schema for context synchronization."""

    session_id: str = Field(..., description="Session ID", min_length=1)
    source_framework: FrameworkType = Field(..., description="Source framework")
    target_framework: FrameworkType = Field(..., description="Target framework")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context to sync")


class ContextSyncResponse(BaseModel):
    """Response schema for context synchronization."""

    session_id: str = Field(..., description="Session ID")
    success: bool = Field(..., description="Whether sync succeeded")
    source_framework: FrameworkType = Field(..., description="Source framework")
    target_framework: FrameworkType = Field(..., description="Target framework")
    synced_keys: List[str] = Field(..., description="Keys that were synced")
    conflicts: List[str] = Field(default_factory=list, description="Conflicting keys")
    error: Optional[str] = Field(None, description="Error message if failed")


class CapabilityListResponse(BaseModel):
    """Response schema for listing capabilities."""

    capabilities: Dict[str, List[TaskCapabilityType]] = Field(
        ..., description="Framework capabilities"
    )
    total_capabilities: int = Field(..., description="Total capability count")


# --- Global Instances ---


_orchestrator: Optional[HybridOrchestrator] = None
_synchronizer: Optional[ContextSynchronizer] = None
_capability_matcher: Optional[CapabilityMatcher] = None


def get_orchestrator() -> HybridOrchestrator:
    """Get the global hybrid orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = HybridOrchestrator()
    return _orchestrator


def get_synchronizer() -> ContextSynchronizer:
    """Get the global context synchronizer instance."""
    global _synchronizer
    if _synchronizer is None:
        _synchronizer = ContextSynchronizer()
    return _synchronizer


def get_capability_matcher() -> CapabilityMatcher:
    """Get the global capability matcher instance."""
    global _capability_matcher
    if _capability_matcher is None:
        _capability_matcher = CapabilityMatcher()
    return _capability_matcher


# --- Router ---


router = APIRouter(prefix="/hybrid", tags=["Claude SDK Hybrid"])


# --- Endpoints ---


@router.post("/execute", response_model=HybridExecuteResponse)
async def execute_hybrid_task(request: HybridExecuteRequest):
    """
    Execute a task using hybrid orchestration.

    Automatically selects the best framework based on task analysis,
    or uses the preferred framework if specified.
    """
    import time
    import uuid

    orchestrator = get_orchestrator()
    session_id = request.session_id or str(uuid.uuid4())

    start_time = time.time()
    try:
        # Create execution context
        context = ExecutionContext(
            session_id=session_id,
            task=request.task,
            context=request.context,
            tools=request.tools or [],
        )

        # Execute with hybrid orchestration
        result = await orchestrator.execute(
            task=request.task,
            context=context,
            preferred_framework=_map_framework(request.preferred_framework),
            timeout=request.timeout,
        )

        execution_time = (time.time() - start_time) * 1000

        # Map tool calls
        tool_calls = [
            ToolCallInfo(
                name=tc.name,
                arguments=tc.arguments,
                result=tc.result,
                duration_ms=tc.duration_ms,
            )
            for tc in result.tool_calls
        ]

        return HybridExecuteResponse(
            session_id=session_id,
            framework_used=_map_framework_to_api(result.framework_used),
            success=result.success,
            content=result.content,
            tool_calls=tool_calls,
            execution_time_ms=execution_time,
            error=result.error,
        )

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return HybridExecuteResponse(
            session_id=session_id,
            framework_used=FrameworkType.AUTO,
            success=False,
            tool_calls=[],
            execution_time_ms=execution_time,
            error=str(e),
        )


@router.post("/analyze", response_model=HybridAnalyzeResponse)
async def analyze_task(request: HybridAnalyzeRequest):
    """
    Analyze a task to determine optimal framework and capabilities.

    Returns framework recommendation, detected capabilities, and complexity assessment.
    """
    orchestrator = get_orchestrator()
    matcher = get_capability_matcher()

    try:
        # Analyze task
        analysis = await orchestrator.analyze_task(
            task=request.task,
            context=request.context,
        )

        # Get capabilities from matcher
        capabilities = matcher.analyze(request.task)

        capability_infos = [
            CapabilityInfo(
                capability=TaskCapabilityType(cap.value),
                confidence=conf,
            )
            for cap, conf in capabilities.items()
        ]

        # Determine recommended framework
        recommended = matcher.match_framework(request.task)

        return HybridAnalyzeResponse(
            task=request.task,
            recommended_framework=_map_framework_to_api(recommended),
            capabilities=capability_infos,
            complexity_score=analysis.complexity_score,
            reasoning=analysis.reasoning,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.get("/metrics", response_model=HybridMetricsResponse)
async def get_metrics():
    """
    Get hybrid orchestration metrics.

    Returns execution statistics, framework usage, and capability distribution.
    """
    orchestrator = get_orchestrator()

    try:
        metrics = orchestrator.get_metrics()

        return HybridMetricsResponse(
            total_executions=metrics.total_executions,
            claude_sdk_executions=metrics.claude_sdk_executions,
            ms_agent_executions=metrics.ms_agent_executions,
            avg_execution_time_ms=metrics.avg_execution_time_ms,
            success_rate=metrics.success_rate,
            capability_distribution=metrics.capability_distribution,
            last_updated=metrics.last_updated,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}",
        )


@router.post("/context/sync", response_model=ContextSyncResponse)
async def sync_context(request: ContextSyncRequest):
    """
    Synchronize context between frameworks.

    Enables seamless handoff of session state between Claude SDK and MS Agent Framework.
    """
    synchronizer = get_synchronizer()

    try:
        # Perform synchronization
        result = await synchronizer.sync(
            session_id=request.session_id,
            source=_map_framework(request.source_framework),
            target=_map_framework(request.target_framework),
            context=request.context,
        )

        return ContextSyncResponse(
            session_id=request.session_id,
            success=result.success,
            source_framework=request.source_framework,
            target_framework=request.target_framework,
            synced_keys=result.synced_keys,
            conflicts=result.conflicts,
            error=result.error,
        )

    except Exception as e:
        return ContextSyncResponse(
            session_id=request.session_id,
            success=False,
            source_framework=request.source_framework,
            target_framework=request.target_framework,
            synced_keys=[],
            conflicts=[],
            error=str(e),
        )


@router.get("/capabilities", response_model=CapabilityListResponse)
async def list_capabilities():
    """
    List capabilities supported by each framework.

    Returns the capability matrix for framework selection decisions.
    """
    # Define framework capabilities
    claude_sdk_caps = [
        TaskCapabilityType.TOOL_USE,
        TaskCapabilityType.CONVERSATION,
        TaskCapabilityType.CODE_EXECUTION,
        TaskCapabilityType.WEB_SEARCH,
        TaskCapabilityType.FILE_OPERATIONS,
    ]

    ms_agent_caps = [
        TaskCapabilityType.MULTI_AGENT,
        TaskCapabilityType.HANDOFF,
        TaskCapabilityType.PLANNING,
        TaskCapabilityType.TOOL_USE,
        TaskCapabilityType.CONVERSATION,
    ]

    capabilities = {
        "claude_sdk": claude_sdk_caps,
        "microsoft_agent": ms_agent_caps,
    }

    total = len(set(claude_sdk_caps + ms_agent_caps))

    return CapabilityListResponse(
        capabilities=capabilities,
        total_capabilities=total,
    )


# --- Helper Functions ---


def _map_framework(framework_type: FrameworkType) -> Optional[Framework]:
    """Map API framework type to internal Framework enum."""
    if framework_type == FrameworkType.CLAUDE_SDK:
        return Framework.CLAUDE_SDK
    elif framework_type == FrameworkType.MICROSOFT_AGENT:
        return Framework.MICROSOFT_AGENT_FRAMEWORK
    return None  # AUTO


def _map_framework_to_api(framework: Optional[Framework]) -> FrameworkType:
    """Map internal Framework enum to API framework type."""
    if framework == Framework.CLAUDE_SDK:
        return FrameworkType.CLAUDE_SDK
    elif framework == Framework.MICROSOFT_AGENT_FRAMEWORK:
        return FrameworkType.MICROSOFT_AGENT
    return FrameworkType.AUTO
