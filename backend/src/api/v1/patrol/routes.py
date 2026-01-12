"""
Patrol API Routes - 主動巡檢 API 路由

Sprint 82 - S82-1: 主動巡檢模式

API Endpoints:
- POST   /api/v1/patrol/trigger          # 手動觸發巡檢
- GET    /api/v1/patrol/reports          # 獲取巡檢報告
- GET    /api/v1/patrol/reports/{id}     # 獲取指定報告
- GET    /api/v1/patrol/schedule         # 獲取巡檢計劃
- PUT    /api/v1/patrol/schedule         # 更新巡檢計劃
- DELETE /api/v1/patrol/schedule/{id}    # 刪除巡檢計劃
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patrol", tags=["patrol"])


# ============================================================================
# Request/Response Models
# ============================================================================


class PatrolTriggerRequest(BaseModel):
    """手動觸發巡檢請求"""
    patrol_id: Optional[str] = Field(None, description="指定巡檢 ID，為空則執行所有檢查")
    check_types: Optional[List[str]] = Field(
        None,
        description="指定檢查類型列表",
        example=["service_health", "api_response"],
    )
    priority: str = Field("high", description="執行優先級")
    skip_cache: bool = Field(False, description="是否跳過緩存")
    notify_immediately: bool = Field(True, description="是否立即通知")


class PatrolTriggerResponse(BaseModel):
    """手動觸發巡檢響應"""
    execution_id: str
    patrol_id: str
    status: str
    message: str
    estimated_duration_seconds: int


class CheckResultModel(BaseModel):
    """檢查結果模型"""
    check_id: str
    check_type: str
    status: str
    message: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    details: Dict[str, Any] = {}
    metrics: Dict[str, float] = {}
    errors: List[str] = []


class RiskAssessmentModel(BaseModel):
    """風險評估模型"""
    risk_score: float
    risk_level: str
    risk_factors: List[str]
    mitigation_suggestions: List[str]


class PatrolReportModel(BaseModel):
    """巡檢報告模型"""
    report_id: str
    patrol_id: str
    patrol_name: str
    started_at: datetime
    completed_at: datetime
    overall_status: str
    risk_assessment: RiskAssessmentModel
    summary: str
    recommendations: List[str]
    checks: List[CheckResultModel]


class ScheduleConfigModel(BaseModel):
    """排程配置模型"""
    patrol_id: str
    name: str
    description: str = ""
    check_types: List[str]
    cron_expression: str = Field(
        ...,
        description="Cron 表達式",
        example="0 * * * *",
    )
    enabled: bool = True
    priority: str = "medium"
    timeout_seconds: int = 300


class ScheduleUpdateRequest(BaseModel):
    """更新排程請求"""
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    check_types: Optional[List[str]] = None
    priority: Optional[str] = None


class ScheduledPatrolModel(BaseModel):
    """已排程巡檢模型"""
    job_id: str
    patrol_id: str
    name: str
    cron_expression: str
    enabled: bool
    next_run: Optional[datetime]
    last_run: Optional[datetime]
    last_status: Optional[str]
    run_count: int
    failure_count: int


# ============================================================================
# In-Memory Storage (Production would use database)
# ============================================================================

_patrol_reports: Dict[str, Dict[str, Any]] = {}
_scheduled_patrols: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/trigger", response_model=PatrolTriggerResponse)
async def trigger_patrol(request: PatrolTriggerRequest) -> PatrolTriggerResponse:
    """
    手動觸發巡檢

    觸發一次即時巡檢，可以指定特定的巡檢 ID 或檢查類型。
    """
    execution_id = f"exec_{uuid4().hex[:12]}"
    patrol_id = request.patrol_id or f"manual_{uuid4().hex[:8]}"

    logger.info(
        f"Triggering patrol: {patrol_id} "
        f"(Types: {request.check_types}, Priority: {request.priority})"
    )

    # 估算執行時間
    check_count = len(request.check_types) if request.check_types else 5
    estimated_duration = check_count * 30  # 每個檢查約 30 秒

    # 創建模擬報告（實際會異步執行巡檢）
    _patrol_reports[execution_id] = {
        "report_id": f"report_{uuid4().hex[:12]}",
        "patrol_id": patrol_id,
        "patrol_name": f"Manual Patrol {patrol_id}",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "overall_status": "running",
        "execution_id": execution_id,
        "check_types": request.check_types or ["service_health", "api_response", "resource_usage"],
    }

    return PatrolTriggerResponse(
        execution_id=execution_id,
        patrol_id=patrol_id,
        status="triggered",
        message="Patrol triggered successfully. Use GET /reports/{execution_id} to check status.",
        estimated_duration_seconds=estimated_duration,
    )


@router.get("/reports", response_model=List[PatrolReportModel])
async def get_patrol_reports(
    limit: int = Query(10, ge=1, le=100, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    status: Optional[str] = Query(None, description="按狀態過濾"),
    patrol_id: Optional[str] = Query(None, description="按巡檢 ID 過濾"),
) -> List[PatrolReportModel]:
    """
    獲取巡檢報告列表

    支援分頁和過濾。
    """
    # 模擬一些報告數據
    sample_reports = [
        {
            "report_id": "report_sample_001",
            "patrol_id": "daily_patrol",
            "patrol_name": "Daily System Patrol",
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "overall_status": "healthy",
            "risk_assessment": {
                "risk_score": 15.0,
                "risk_level": "healthy",
                "risk_factors": [],
                "mitigation_suggestions": ["Continue regular monitoring"],
            },
            "summary": "All systems operating normally. No critical issues detected.",
            "recommendations": ["Continue regular monitoring", "Review pending updates"],
            "checks": [
                {
                    "check_id": "check_001",
                    "check_type": "service_health",
                    "status": "healthy",
                    "message": "All endpoints responding",
                    "started_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow(),
                    "duration_ms": 1500,
                    "details": {"endpoints_checked": 5, "all_healthy": True},
                    "metrics": {"health_ratio": 1.0},
                    "errors": [],
                },
            ],
        },
    ]

    # 添加存儲的報告
    for exec_id, report in _patrol_reports.items():
        if report.get("completed_at"):
            sample_reports.append(report)

    # 過濾
    if status:
        sample_reports = [r for r in sample_reports if r.get("overall_status") == status]
    if patrol_id:
        sample_reports = [r for r in sample_reports if r.get("patrol_id") == patrol_id]

    # 分頁
    paginated = sample_reports[offset : offset + limit]

    return [PatrolReportModel(**r) for r in paginated]


@router.get("/reports/{report_id}", response_model=PatrolReportModel)
async def get_patrol_report(report_id: str) -> PatrolReportModel:
    """
    獲取指定巡檢報告

    根據報告 ID 或執行 ID 獲取詳細報告。
    """
    # 檢查是否為執行 ID
    if report_id in _patrol_reports:
        report = _patrol_reports[report_id]
        if report.get("overall_status") == "running":
            # 模擬完成
            report["completed_at"] = datetime.utcnow().isoformat()
            report["overall_status"] = "healthy"
            report["risk_assessment"] = {
                "risk_score": 20.0,
                "risk_level": "healthy",
                "risk_factors": [],
                "mitigation_suggestions": [],
            }
            report["summary"] = "Patrol completed successfully."
            report["recommendations"] = ["Continue monitoring"]
            report["checks"] = [
                {
                    "check_id": f"check_{uuid4().hex[:8]}",
                    "check_type": ct,
                    "status": "healthy",
                    "message": "Check passed",
                    "started_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow(),
                    "duration_ms": 1000,
                    "details": {},
                    "metrics": {},
                    "errors": [],
                }
                for ct in report.get("check_types", ["service_health"])
            ]

        return PatrolReportModel(**report)

    raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")


@router.get("/schedule", response_model=List[ScheduledPatrolModel])
async def get_patrol_schedules() -> List[ScheduledPatrolModel]:
    """
    獲取巡檢計劃列表

    返回所有已配置的定時巡檢計劃。
    """
    # 返回存儲的排程 + 默認排程
    schedules = [
        {
            "job_id": "job_daily_001",
            "patrol_id": "daily_patrol",
            "name": "Daily System Patrol",
            "cron_expression": "0 0 * * *",
            "enabled": True,
            "next_run": datetime.utcnow(),
            "last_run": datetime.utcnow(),
            "last_status": "healthy",
            "run_count": 30,
            "failure_count": 0,
        },
        {
            "job_id": "job_hourly_001",
            "patrol_id": "hourly_health",
            "name": "Hourly Health Check",
            "cron_expression": "0 * * * *",
            "enabled": True,
            "next_run": datetime.utcnow(),
            "last_run": datetime.utcnow(),
            "last_status": "healthy",
            "run_count": 720,
            "failure_count": 2,
        },
    ]

    # 添加用戶創建的排程
    for patrol_id, schedule in _scheduled_patrols.items():
        schedules.append(schedule)

    return [ScheduledPatrolModel(**s) for s in schedules]


@router.post("/schedule", response_model=ScheduledPatrolModel)
async def create_patrol_schedule(config: ScheduleConfigModel) -> ScheduledPatrolModel:
    """
    創建巡檢計劃

    配置新的定時巡檢任務。
    """
    job_id = f"job_{uuid4().hex[:12]}"

    schedule = {
        "job_id": job_id,
        "patrol_id": config.patrol_id,
        "name": config.name,
        "cron_expression": config.cron_expression,
        "enabled": config.enabled,
        "next_run": datetime.utcnow(),
        "last_run": None,
        "last_status": None,
        "run_count": 0,
        "failure_count": 0,
    }

    _scheduled_patrols[config.patrol_id] = schedule

    logger.info(f"Created patrol schedule: {config.name} (ID: {config.patrol_id})")

    return ScheduledPatrolModel(**schedule)


@router.put("/schedule/{patrol_id}", response_model=ScheduledPatrolModel)
async def update_patrol_schedule(
    patrol_id: str,
    request: ScheduleUpdateRequest,
) -> ScheduledPatrolModel:
    """
    更新巡檢計劃

    修改現有巡檢計劃的配置。
    """
    if patrol_id not in _scheduled_patrols:
        # 檢查是否為默認排程
        if patrol_id in ["daily_patrol", "hourly_health"]:
            # 創建可修改的副本
            _scheduled_patrols[patrol_id] = {
                "job_id": f"job_{patrol_id}",
                "patrol_id": patrol_id,
                "name": f"Patrol {patrol_id}",
                "cron_expression": "0 * * * *",
                "enabled": True,
                "next_run": datetime.utcnow(),
                "last_run": datetime.utcnow(),
                "last_status": "healthy",
                "run_count": 0,
                "failure_count": 0,
            }
        else:
            raise HTTPException(status_code=404, detail=f"Schedule not found: {patrol_id}")

    schedule = _scheduled_patrols[patrol_id]

    if request.cron_expression is not None:
        schedule["cron_expression"] = request.cron_expression
    if request.enabled is not None:
        schedule["enabled"] = request.enabled

    logger.info(f"Updated patrol schedule: {patrol_id}")

    return ScheduledPatrolModel(**schedule)


@router.delete("/schedule/{patrol_id}")
async def delete_patrol_schedule(patrol_id: str) -> Dict[str, str]:
    """
    刪除巡檢計劃

    移除指定的定時巡檢任務。
    """
    if patrol_id in _scheduled_patrols:
        del _scheduled_patrols[patrol_id]
        logger.info(f"Deleted patrol schedule: {patrol_id}")
        return {"message": f"Schedule {patrol_id} deleted successfully"}

    raise HTTPException(status_code=404, detail=f"Schedule not found: {patrol_id}")
