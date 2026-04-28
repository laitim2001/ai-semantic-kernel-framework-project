"""
Patrol System Types - 主動巡檢系統類型定義

Sprint 82 - S82-1: 主動巡檢模式
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PatrolStatus(str, Enum):
    """巡檢狀態"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class CheckType(str, Enum):
    """檢查類型"""
    SERVICE_HEALTH = "service_health"
    API_RESPONSE = "api_response"
    RESOURCE_USAGE = "resource_usage"
    LOG_ANALYSIS = "log_analysis"
    SECURITY_SCAN = "security_scan"


class ScheduleFrequency(str, Enum):
    """調度頻率"""
    EVERY_5_MINUTES = "*/5 * * * *"
    EVERY_10_MINUTES = "*/10 * * * *"
    EVERY_15_MINUTES = "*/15 * * * *"
    EVERY_30_MINUTES = "*/30 * * * *"
    HOURLY = "0 * * * *"
    DAILY = "0 0 * * *"
    WEEKLY = "0 0 * * 0"


class PatrolPriority(str, Enum):
    """巡檢優先級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PatrolConfig:
    """巡檢配置"""
    patrol_id: str
    name: str
    description: str
    check_types: List[CheckType]
    cron_expression: str
    enabled: bool = True
    priority: PatrolPriority = PatrolPriority.MEDIUM
    timeout_seconds: int = 300
    retry_count: int = 3
    notify_on_failure: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    """檢查結果"""
    check_id: str
    check_type: CheckType
    status: PatrolStatus
    message: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    details: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """風險評估"""
    risk_score: float  # 0-100
    risk_level: PatrolStatus
    risk_factors: List[str]
    mitigation_suggestions: List[str]


@dataclass
class PatrolReport:
    """巡檢報告"""
    report_id: str
    patrol_id: str
    patrol_name: str
    started_at: datetime
    completed_at: datetime
    checks: List[CheckResult]
    overall_status: PatrolStatus
    risk_assessment: RiskAssessment
    summary: str  # Claude 生成的摘要
    recommendations: List[str]  # Claude 生成的建議
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """計算巡檢持續時間（秒）"""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def healthy_count(self) -> int:
        """健康檢查數量"""
        return sum(1 for c in self.checks if c.status == PatrolStatus.HEALTHY)

    @property
    def warning_count(self) -> int:
        """警告檢查數量"""
        return sum(1 for c in self.checks if c.status == PatrolStatus.WARNING)

    @property
    def critical_count(self) -> int:
        """嚴重問題檢查數量"""
        return sum(1 for c in self.checks if c.status == PatrolStatus.CRITICAL)


@dataclass
class ScheduledPatrol:
    """已排程的巡檢"""
    job_id: str
    patrol_config: PatrolConfig
    next_run: Optional[datetime]
    last_run: Optional[datetime]
    last_status: Optional[PatrolStatus]
    run_count: int = 0
    failure_count: int = 0


@dataclass
class PatrolHistory:
    """巡檢歷史記錄"""
    patrol_id: str
    reports: List[PatrolReport]
    total_runs: int
    success_rate: float
    average_duration_seconds: float
    last_healthy_at: Optional[datetime]
    last_warning_at: Optional[datetime]
    last_critical_at: Optional[datetime]


@dataclass
class PatrolTriggerRequest:
    """手動觸發巡檢請求"""
    patrol_id: Optional[str] = None
    check_types: Optional[List[CheckType]] = None
    priority: PatrolPriority = PatrolPriority.HIGH
    skip_cache: bool = False
    notify_immediately: bool = True


@dataclass
class PatrolTriggerResponse:
    """手動觸發巡檢響應"""
    execution_id: str
    patrol_id: str
    status: str
    message: str
    estimated_duration_seconds: int


# 檢查項目配置
CHECK_DEFAULT_CONFIG: Dict[CheckType, Dict[str, Any]] = {
    CheckType.SERVICE_HEALTH: {
        "timeout_seconds": 30,
        "retry_count": 2,
        "check_interval_seconds": 300,
        "endpoints": [],
    },
    CheckType.API_RESPONSE: {
        "timeout_seconds": 60,
        "retry_count": 3,
        "expected_status_codes": [200, 201],
        "max_response_time_ms": 5000,
    },
    CheckType.RESOURCE_USAGE: {
        "cpu_warning_threshold": 70,
        "cpu_critical_threshold": 90,
        "memory_warning_threshold": 75,
        "memory_critical_threshold": 95,
        "disk_warning_threshold": 80,
        "disk_critical_threshold": 95,
    },
    CheckType.LOG_ANALYSIS: {
        "error_patterns": [r"ERROR", r"CRITICAL", r"FATAL"],
        "warning_patterns": [r"WARN", r"WARNING"],
        "time_window_minutes": 60,
        "max_error_count": 10,
    },
    CheckType.SECURITY_SCAN: {
        "scan_types": ["vulnerability", "compliance", "access"],
        "severity_threshold": "medium",
        "skip_low_severity": True,
    },
}


def calculate_risk_score(checks: List[CheckResult]) -> float:
    """
    計算風險分數

    算法:
    - HEALTHY: 0 分
    - WARNING: 20 分
    - CRITICAL: 50 分
    - UNKNOWN: 10 分

    最終分數 = min(100, sum(所有檢查得分))
    """
    score = 0.0
    for check in checks:
        if check.status == PatrolStatus.WARNING:
            score += 20.0
        elif check.status == PatrolStatus.CRITICAL:
            score += 50.0
        elif check.status == PatrolStatus.UNKNOWN:
            score += 10.0
    return min(100.0, score)


def determine_overall_status(checks: List[CheckResult]) -> PatrolStatus:
    """根據檢查結果決定整體狀態"""
    if any(c.status == PatrolStatus.CRITICAL for c in checks):
        return PatrolStatus.CRITICAL
    elif any(c.status == PatrolStatus.WARNING for c in checks):
        return PatrolStatus.WARNING
    elif all(c.status == PatrolStatus.HEALTHY for c in checks):
        return PatrolStatus.HEALTHY
    else:
        return PatrolStatus.UNKNOWN
