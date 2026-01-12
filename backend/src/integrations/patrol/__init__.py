"""
Patrol System - 主動巡檢系統

Sprint 82 - S82-1: 主動巡檢模式

提供:
- PatrolScheduler: 巡檢調度器
- PatrolAgent: 巡檢代理
- PatrolCheck: 巡檢檢查基類
- 各種檢查項目實現
"""

from .agent import PatrolAgent, PatrolCheck
from .checks import (
    APIResponseCheck,
    BaseCheck,
    LogAnalysisCheck,
    ResourceUsageCheck,
    SecurityScanCheck,
    ServiceHealthCheck,
)
from .scheduler import PatrolScheduler
from .types import (
    CheckResult,
    CheckType,
    PatrolConfig,
    PatrolHistory,
    PatrolPriority,
    PatrolReport,
    PatrolStatus,
    PatrolTriggerRequest,
    PatrolTriggerResponse,
    RiskAssessment,
    ScheduledPatrol,
    ScheduleFrequency,
    calculate_risk_score,
    determine_overall_status,
)

__all__ = [
    # Core classes
    "PatrolScheduler",
    "PatrolAgent",
    "PatrolCheck",
    # Check implementations
    "BaseCheck",
    "ServiceHealthCheck",
    "APIResponseCheck",
    "ResourceUsageCheck",
    "LogAnalysisCheck",
    "SecurityScanCheck",
    # Types
    "PatrolConfig",
    "PatrolReport",
    "PatrolStatus",
    "PatrolPriority",
    "PatrolHistory",
    "PatrolTriggerRequest",
    "PatrolTriggerResponse",
    "RiskAssessment",
    "ScheduledPatrol",
    "ScheduleFrequency",
    "CheckType",
    "CheckResult",
    # Utilities
    "calculate_risk_score",
    "determine_overall_status",
]

# 版本信息
__version__ = "1.0.0"
__sprint__ = "82"
