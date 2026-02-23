"""
Swarm Demo API Routes

FastAPI routes for demonstrating Agent Swarm execution with simulated progress.
This allows frontend testing without requiring actual agent execution.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.integrations.swarm import (
    SwarmIntegration,
    SwarmMode,
    SwarmStatus,
    WorkerStatus,
    WorkerType,
    get_swarm_tracker,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/swarm/demo", tags=["Swarm Demo"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class DemoScenario(str, Enum):
    """Available demo scenarios."""

    SECURITY_AUDIT = "security_audit"
    ETL_PIPELINE = "etl_pipeline"
    DATA_PIPELINE = "data_pipeline"
    CUSTOM = "custom"


class WorkerConfig(BaseModel):
    """Configuration for a demo worker."""

    name: str = Field(..., description="Worker display name")
    role: str = Field(..., description="Worker role description")
    worker_type: str = Field("analyst", description="Worker type (analyst, coder, etc.)")
    task_description: str = Field(..., description="Task description")
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list, description="Simulated tool calls"
    )
    thinking_contents: List[str] = Field(
        default_factory=list, description="Extended thinking contents"
    )
    duration_seconds: float = Field(3.0, ge=1.0, le=30.0, description="Simulation duration")


class DemoStartRequest(BaseModel):
    """Request to start a demo swarm execution."""

    scenario: DemoScenario = Field(
        DemoScenario.SECURITY_AUDIT, description="Demo scenario to run"
    )
    mode: str = Field("parallel", description="Execution mode")
    speed_multiplier: float = Field(
        1.0, ge=0.5, le=5.0, description="Speed multiplier (1.0 = normal)"
    )
    workers: Optional[List[WorkerConfig]] = Field(
        None, description="Custom worker configurations (for CUSTOM scenario)"
    )


class DemoStartResponse(BaseModel):
    """Response after starting demo."""

    swarm_id: str = Field(..., description="Swarm ID for tracking")
    session_id: str = Field(..., description="Session ID for SSE subscription")
    status: str = Field(..., description="Initial status")
    message: str = Field(..., description="Status message")
    sse_endpoint: str = Field(..., description="SSE endpoint for real-time updates")


class DemoStatusResponse(BaseModel):
    """Demo execution status."""

    swarm_id: str
    status: str
    progress: int
    workers_completed: int
    workers_total: int


# =============================================================================
# Demo Scenarios
# =============================================================================


def get_security_audit_workers() -> List[WorkerConfig]:
    """Get workers for security audit scenario."""
    return [
        WorkerConfig(
            name="Network Scanner",
            role="網路掃描",
            worker_type="analyst",
            task_description="執行網路掃描，識別開放端口和服務",
            tool_calls=[
                {"name": "nmap:scan", "params": {"target": "10.0.0.0/24"}},
                {"name": "azure:list_vms", "params": {"subscription": "prod"}},
            ],
            thinking_contents=[
                "我需要先掃描網路段落，找出所有活動的主機...",
                "發現 47 個開放端口，其中 3 個是高風險服務...",
            ],
            duration_seconds=5.0,
        ),
        WorkerConfig(
            name="Vulnerability Analyzer",
            role="漏洞分析",
            worker_type="analyst",
            task_description="分析已知漏洞並評估風險",
            tool_calls=[
                {"name": "cve:search", "params": {"product": "nginx"}},
                {"name": "trivy:scan", "params": {"image": "prod-api:latest"}},
            ],
            thinking_contents=[
                "根據掃描結果，我需要檢查這些服務的已知漏洞...",
                "發現 CVE-2024-1234，這是一個高危漏洞，需要立即處理...",
            ],
            duration_seconds=6.0,
        ),
        WorkerConfig(
            name="Compliance Checker",
            role="合規檢查",
            worker_type="reviewer",
            task_description="檢查安全合規性（SOC2、ISO27001）",
            tool_calls=[
                {"name": "compliance:check_soc2", "params": {"scope": "infrastructure"}},
                {"name": "compliance:check_iso27001", "params": {"scope": "data"}},
            ],
            thinking_contents=[
                "正在檢查 SOC2 合規項目...",
                "ISO27001 控制點檢查完成，發現 2 個需要改進的項目...",
            ],
            duration_seconds=4.0,
        ),
        WorkerConfig(
            name="Report Generator",
            role="報告生成",
            worker_type="writer",
            task_description="整合所有分析結果，生成安全審計報告",
            tool_calls=[
                {"name": "report:generate", "params": {"format": "pdf"}},
                {"name": "email:send", "params": {"to": "security-team@company.com"}},
            ],
            thinking_contents=[
                "正在整合所有掃描和分析結果...",
                "報告生成完成，包含 12 個發現項目和修復建議...",
            ],
            duration_seconds=3.0,
        ),
    ]


def get_etl_pipeline_workers() -> List[WorkerConfig]:
    """Get workers for ETL pipeline diagnostic scenario."""
    return [
        WorkerConfig(
            name="Log Analyzer",
            role="日誌分析",
            worker_type="analyst",
            task_description="分析 ETL Pipeline 錯誤日誌",
            tool_calls=[
                {"name": "azure:query_adf_logs", "params": {"pipeline": "APAC_Glider", "hours": 24}},
                {"name": "elastic:search", "params": {"index": "etl-errors-*"}},
            ],
            thinking_contents=[
                "正在查詢 ADF Pipeline 執行日誌...",
                "發現 47 個連線超時錯誤，主要發生在 02:00-04:00 時段...",
            ],
            duration_seconds=4.0,
        ),
        WorkerConfig(
            name="Root Cause Investigator",
            role="根因調查",
            worker_type="analyst",
            task_description="調查錯誤根本原因",
            tool_calls=[
                {"name": "azure:check_connectivity", "params": {"source": "adf", "target": "sql"}},
                {"name": "azure:get_metrics", "params": {"resource": "sql-server-prod"}},
            ],
            thinking_contents=[
                "分析連線錯誤的時間模式...",
                "發現 SQL Server 在該時段有 CPU 使用率峰值，可能是批次作業衝突...",
            ],
            duration_seconds=5.0,
        ),
        WorkerConfig(
            name="Solution Designer",
            role="方案設計",
            worker_type="coder",
            task_description="設計修復方案",
            tool_calls=[
                {"name": "jira:create_ticket", "params": {"type": "task", "priority": "high"}},
                {"name": "confluence:update_page", "params": {"page_id": "runbook-etl"}},
            ],
            thinking_contents=[
                "基於根因分析，我建議以下修復方案：調整批次作業排程...",
                "已創建工單 INC-2024-001，優先級設為高...",
            ],
            duration_seconds=4.0,
        ),
    ]


def get_data_pipeline_workers() -> List[WorkerConfig]:
    """Get workers for data pipeline monitoring scenario."""
    return [
        WorkerConfig(
            name="Data Quality Monitor",
            role="資料品質",
            worker_type="analyst",
            task_description="監控資料品質指標",
            tool_calls=[
                {"name": "great_expectations:run", "params": {"suite": "core_metrics"}},
                {"name": "dbt:test", "params": {"models": "staging.*"}},
            ],
            thinking_contents=[
                "正在執行資料品質檢查...",
                "發現 customer_id 欄位有 0.3% 的空值，需要調查來源...",
            ],
            duration_seconds=4.0,
        ),
        WorkerConfig(
            name="Performance Optimizer",
            role="效能優化",
            worker_type="coder",
            task_description="分析和優化 Pipeline 效能",
            tool_calls=[
                {"name": "spark:explain", "params": {"query": "select * from sales"}},
                {"name": "databricks:get_job_metrics", "params": {"job_id": "daily-etl"}},
            ],
            thinking_contents=[
                "分析 Spark 執行計劃...",
                "發現 shuffle 操作過多，建議調整分區策略...",
            ],
            duration_seconds=5.0,
        ),
    ]


# =============================================================================
# Demo Execution Logic
# =============================================================================

# Store active demo sessions
_active_demos: Dict[str, Dict[str, Any]] = {}


async def run_demo_swarm(
    swarm_id: str,
    session_id: str,
    workers: List[WorkerConfig],
    mode: SwarmMode,
    speed_multiplier: float,
):
    """
    Run a demo swarm execution with simulated progress.

    This function simulates worker execution by:
    1. Starting each worker
    2. Updating progress incrementally
    3. Adding tool calls and thinking content
    4. Completing workers
    """
    tracker = get_swarm_tracker()
    integration = SwarmIntegration(tracker=tracker)

    # Create swarm
    subtasks = [
        {"id": f"subtask-{i}", "name": w.name, "description": w.task_description}
        for i, w in enumerate(workers)
    ]

    integration.on_coordination_started(
        swarm_id=swarm_id,
        mode=mode,
        subtasks=subtasks,
        metadata={"session_id": session_id, "demo": True},
    )

    _active_demos[swarm_id] = {"status": "running", "session_id": session_id}

    try:
        if mode == SwarmMode.PARALLEL:
            # Run all workers in parallel
            tasks = [
                _run_worker(integration, swarm_id, i, worker, speed_multiplier)
                for i, worker in enumerate(workers)
            ]
            await asyncio.gather(*tasks)
        else:
            # Run workers sequentially
            for i, worker in enumerate(workers):
                await _run_worker(integration, swarm_id, i, worker, speed_multiplier)

        # Complete swarm
        integration.on_coordination_completed(swarm_id, SwarmStatus.COMPLETED)
        _active_demos[swarm_id]["status"] = "completed"

    except Exception as e:
        logger.error(f"Demo swarm failed: {e}")
        integration.on_coordination_completed(swarm_id, SwarmStatus.FAILED)
        _active_demos[swarm_id]["status"] = "failed"
        raise


async def _run_worker(
    integration: SwarmIntegration,
    swarm_id: str,
    worker_index: int,
    config: WorkerConfig,
    speed_multiplier: float,
):
    """Run a single worker simulation."""
    worker_id = f"worker-{worker_index + 1}"
    worker_type = _parse_worker_type(config.worker_type)

    # Start worker
    integration.on_subtask_started(
        swarm_id=swarm_id,
        worker_id=worker_id,
        worker_name=config.name,
        worker_type=worker_type,
        role=config.role,
        task_description=config.task_description,
    )

    # Calculate step duration
    duration = config.duration_seconds / speed_multiplier
    steps = 10
    step_duration = duration / steps

    # Simulate progress with thinking and tool calls
    thinking_idx = 0
    tool_idx = 0

    for step in range(steps):
        progress = int((step + 1) * 100 / steps)

        # Add thinking content at certain progress points
        if config.thinking_contents and thinking_idx < len(config.thinking_contents):
            if progress >= (thinking_idx + 1) * (100 // (len(config.thinking_contents) + 1)):
                integration.on_thinking(
                    swarm_id=swarm_id,
                    worker_id=worker_id,
                    content=config.thinking_contents[thinking_idx],
                    token_count=len(config.thinking_contents[thinking_idx]) * 2,
                )
                thinking_idx += 1

        # Add tool calls at certain progress points
        if config.tool_calls and tool_idx < len(config.tool_calls):
            if progress >= (tool_idx + 1) * (100 // (len(config.tool_calls) + 1)):
                tool_call = config.tool_calls[tool_idx]
                tool_id = f"tc-{worker_index}-{tool_idx}"

                integration.on_tool_call(
                    swarm_id=swarm_id,
                    worker_id=worker_id,
                    tool_id=tool_id,
                    tool_name=tool_call.get("name", "unknown_tool"),
                    is_mcp=tool_call.get("is_mcp", True),
                    input_params=tool_call.get("params", {}),
                )

                # Simulate tool execution time
                await asyncio.sleep(step_duration * 0.5)

                # Complete tool call
                integration.on_tool_result(
                    swarm_id=swarm_id,
                    worker_id=worker_id,
                    tool_id=tool_id,
                    result={"status": "success", "data": "simulated result"},
                )
                tool_idx += 1

        # Update progress
        integration.on_subtask_progress(
            swarm_id=swarm_id,
            worker_id=worker_id,
            progress=progress,
            current_task=f"{config.task_description} ({progress}%)",
        )

        await asyncio.sleep(step_duration)

    # Complete worker
    integration.on_subtask_completed(
        swarm_id=swarm_id,
        worker_id=worker_id,
        status=WorkerStatus.COMPLETED,
    )


def _parse_worker_type(type_str: str) -> WorkerType:
    """Parse worker type from string."""
    type_map = {
        "analyst": WorkerType.ANALYST,
        "coder": WorkerType.CODER,
        "writer": WorkerType.WRITER,
        "reviewer": WorkerType.REVIEWER,
        "researcher": WorkerType.RESEARCH,
        "designer": WorkerType.DESIGNER,
        "coordinator": WorkerType.COORDINATOR,
        "tester": WorkerType.TESTER,
    }
    return type_map.get(type_str.lower(), WorkerType.CUSTOM)


# =============================================================================
# API Routes
# =============================================================================


@router.post(
    "/start",
    response_model=DemoStartResponse,
    summary="Start Demo Swarm",
    description="Start a demo swarm execution with simulated progress updates.",
)
async def start_demo(
    request: DemoStartRequest,
    background_tasks: BackgroundTasks,
) -> DemoStartResponse:
    """
    Start a demo swarm execution.

    This endpoint starts a background task that simulates agent swarm execution.
    The frontend can subscribe to SSE events to receive real-time updates.
    """
    # Generate IDs
    swarm_id = f"demo-{uuid4().hex[:8]}"
    session_id = f"session-{uuid4().hex[:8]}"

    # Get workers based on scenario
    if request.scenario == DemoScenario.SECURITY_AUDIT:
        workers = get_security_audit_workers()
    elif request.scenario == DemoScenario.ETL_PIPELINE:
        workers = get_etl_pipeline_workers()
    elif request.scenario == DemoScenario.DATA_PIPELINE:
        workers = get_data_pipeline_workers()
    elif request.scenario == DemoScenario.CUSTOM:
        if not request.workers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom scenario requires workers configuration",
            )
        workers = request.workers
    else:
        workers = get_security_audit_workers()

    # Parse mode
    mode_map = {
        "parallel": SwarmMode.PARALLEL,
        "sequential": SwarmMode.SEQUENTIAL,
        "hierarchical": SwarmMode.HIERARCHICAL,
    }
    mode = mode_map.get(request.mode.lower(), SwarmMode.PARALLEL)

    # Start background task
    background_tasks.add_task(
        run_demo_swarm,
        swarm_id=swarm_id,
        session_id=session_id,
        workers=workers,
        mode=mode,
        speed_multiplier=request.speed_multiplier,
    )

    return DemoStartResponse(
        swarm_id=swarm_id,
        session_id=session_id,
        status="started",
        message=f"Demo swarm started with {len(workers)} workers",
        sse_endpoint=f"/api/v1/swarm/{swarm_id}/events",
    )


@router.get(
    "/status/{swarm_id}",
    response_model=DemoStatusResponse,
    summary="Get Demo Status",
    description="Get the current status of a demo swarm execution.",
)
async def get_demo_status(swarm_id: str) -> DemoStatusResponse:
    """Get demo execution status."""
    if swarm_id not in _active_demos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo not found: {swarm_id}",
        )

    tracker = get_swarm_tracker()
    swarm = tracker.get_swarm(swarm_id)

    if swarm is None:
        return DemoStatusResponse(
            swarm_id=swarm_id,
            status=_active_demos[swarm_id].get("status", "unknown"),
            progress=0,
            workers_completed=0,
            workers_total=0,
        )

    workers_completed = sum(
        1 for w in swarm.workers if w.status == WorkerStatus.COMPLETED
    )

    return DemoStatusResponse(
        swarm_id=swarm_id,
        status=swarm.status.value,
        progress=swarm.overall_progress,
        workers_completed=workers_completed,
        workers_total=len(swarm.workers),
    )


@router.post(
    "/stop/{swarm_id}",
    summary="Stop Demo",
    description="Stop a running demo swarm execution.",
)
async def stop_demo(swarm_id: str) -> Dict[str, str]:
    """Stop a demo execution (mark as cancelled)."""
    if swarm_id not in _active_demos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo not found: {swarm_id}",
        )

    _active_demos[swarm_id]["status"] = "cancelled"
    return {"message": f"Demo {swarm_id} stop requested"}


@router.get(
    "/scenarios",
    summary="List Demo Scenarios",
    description="Get available demo scenarios and their descriptions.",
)
async def list_scenarios() -> List[Dict[str, Any]]:
    """List available demo scenarios."""
    return [
        {
            "id": "security_audit",
            "name": "安全審計",
            "description": "執行完整的安全審計流程，包括網路掃描、漏洞分析和合規檢查",
            "workers_count": 4,
            "estimated_duration": "18 seconds",
        },
        {
            "id": "etl_pipeline",
            "name": "ETL Pipeline 診斷",
            "description": "診斷 ETL Pipeline 錯誤，分析日誌並設計修復方案",
            "workers_count": 3,
            "estimated_duration": "13 seconds",
        },
        {
            "id": "data_pipeline",
            "name": "資料管道監控",
            "description": "監控資料品質和效能，提供優化建議",
            "workers_count": 2,
            "estimated_duration": "9 seconds",
        },
    ]


# =============================================================================
# SSE Event Stream
# =============================================================================


async def swarm_event_generator(swarm_id: str):
    """
    Generate SSE events for a swarm execution.

    This generator polls the SwarmTracker and yields events when state changes.
    """
    import json

    tracker = get_swarm_tracker()
    last_state = None
    poll_interval = 0.2  # 200ms

    while True:
        swarm = tracker.get_swarm(swarm_id)

        if swarm is None:
            # Wait for swarm to be created
            if swarm_id in _active_demos:
                await asyncio.sleep(poll_interval)
                continue
            else:
                # Demo not found or finished
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Swarm not found"}),
                }
                break

        # Build current state snapshot
        current_state = {
            "swarm_id": swarm.swarm_id,
            "status": swarm.status.value,
            "mode": swarm.mode.value,
            "overall_progress": swarm.overall_progress,
            "total_tool_calls": swarm.total_tool_calls,
            "completed_tool_calls": swarm.completed_tool_calls,
            "workers": [
                {
                    "worker_id": w.worker_id,
                    "worker_name": w.worker_name,
                    "worker_type": w.worker_type.value,
                    "role": w.role,
                    "status": w.status.value,
                    "progress": w.progress,
                    "current_task": w.current_task,
                    "tool_calls_count": len(w.tool_calls),
                    "tool_calls": [
                        {
                            "tool_id": tc.tool_id,
                            "tool_name": tc.tool_name,
                            "status": tc.status,
                            "is_mcp": tc.is_mcp,
                        }
                        for tc in w.tool_calls
                    ],
                    "thinking_contents": [
                        {
                            "content": tc.content,
                            "token_count": tc.token_count,
                        }
                        for tc in w.thinking_contents
                    ],
                }
                for w in swarm.workers
            ],
        }

        # Only send if state changed
        if current_state != last_state:
            yield {
                "event": "swarm_update",
                "data": json.dumps(current_state),
            }
            last_state = current_state

            # Check if completed
            if swarm.status in [SwarmStatus.COMPLETED, SwarmStatus.FAILED]:
                yield {
                    "event": "swarm_complete",
                    "data": json.dumps({
                        "swarm_id": swarm.swarm_id,
                        "status": swarm.status.value,
                        "final_progress": swarm.overall_progress,
                    }),
                }
                break

        await asyncio.sleep(poll_interval)


@router.get(
    "/events/{swarm_id}",
    summary="Subscribe to Swarm Events",
    description="Subscribe to real-time SSE events for a swarm execution.",
)
async def subscribe_swarm_events(swarm_id: str):
    """
    Subscribe to swarm events via Server-Sent Events (SSE).

    This endpoint streams real-time updates about swarm execution.
    """
    return EventSourceResponse(swarm_event_generator(swarm_id))
