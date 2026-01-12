"""
Patrol Agent - 巡檢代理

Sprint 82 - S82-1: 主動巡檢模式
負責執行巡檢並分析結果
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

from .types import (
    CheckResult,
    CheckType,
    PatrolConfig,
    PatrolReport,
    PatrolStatus,
    RiskAssessment,
    calculate_risk_score,
    determine_overall_status,
)

logger = logging.getLogger(__name__)


class PatrolCheck:
    """巡檢檢查項目基類"""

    check_type: CheckType = CheckType.SERVICE_HEALTH

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    async def execute(self) -> CheckResult:
        """執行檢查 - 子類必須實現"""
        raise NotImplementedError("Subclasses must implement execute()")

    def _create_result(
        self,
        status: PatrolStatus,
        message: str,
        started_at: datetime,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        errors: Optional[List[str]] = None,
    ) -> CheckResult:
        """創建檢查結果"""
        completed_at = datetime.utcnow()
        return CheckResult(
            check_id=f"check_{uuid4().hex[:12]}",
            check_type=self.check_type,
            status=status,
            message=message,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            details=details or {},
            metrics=metrics or {},
            errors=errors or [],
        )


class PatrolAgent:
    """
    巡檢代理

    功能:
    - 執行巡檢任務
    - 聚合檢查結果
    - 使用 Claude 分析結果
    - 生成巡檢報告
    """

    def __init__(
        self,
        claude_client: Optional[Any] = None,
    ):
        self._claude_client = claude_client
        self._check_registry: Dict[CheckType, Type[PatrolCheck]] = {}
        self._running_patrols: Dict[str, bool] = {}

    def register_check(
        self,
        check_type: CheckType,
        check_class: Type[PatrolCheck],
    ) -> None:
        """註冊檢查項目"""
        self._check_registry[check_type] = check_class
        logger.info(f"Registered check: {check_type.value}")

    async def execute_patrol(
        self,
        config: PatrolConfig,
        execution_id: Optional[str] = None,
    ) -> PatrolReport:
        """
        執行巡檢

        Args:
            config: 巡檢配置
            execution_id: 執行 ID

        Returns:
            PatrolReport: 巡檢報告
        """
        exec_id = execution_id or f"exec_{uuid4().hex[:12]}"
        patrol_id = config.patrol_id
        started_at = datetime.utcnow()

        logger.info(f"Starting patrol execution: {config.name} (ID: {exec_id})")

        # 標記巡檢進行中
        self._running_patrols[exec_id] = True

        try:
            # 執行所有檢查
            checks = await self._execute_checks(config)

            # 計算整體狀態
            overall_status = determine_overall_status(checks)

            # 風險評估
            risk_assessment = await self._assess_risk(checks)

            # Claude 分析結果
            summary, recommendations = await self._analyze_results(
                config, checks, overall_status, risk_assessment
            )

            completed_at = datetime.utcnow()

            # 生成報告
            report = PatrolReport(
                report_id=f"report_{uuid4().hex[:12]}",
                patrol_id=patrol_id,
                patrol_name=config.name,
                started_at=started_at,
                completed_at=completed_at,
                checks=checks,
                overall_status=overall_status,
                risk_assessment=risk_assessment,
                summary=summary,
                recommendations=recommendations,
                metadata={
                    "execution_id": exec_id,
                    "config": {
                        "check_types": [ct.value for ct in config.check_types],
                        "priority": config.priority.value,
                    },
                },
            )

            logger.info(
                f"Patrol completed: {config.name} "
                f"(Status: {overall_status.value}, "
                f"Risk: {risk_assessment.risk_score:.1f})"
            )

            return report

        except Exception as e:
            logger.error(f"Patrol execution failed: {e}")

            # 返回錯誤報告
            completed_at = datetime.utcnow()
            return PatrolReport(
                report_id=f"report_{uuid4().hex[:12]}",
                patrol_id=patrol_id,
                patrol_name=config.name,
                started_at=started_at,
                completed_at=completed_at,
                checks=[],
                overall_status=PatrolStatus.CRITICAL,
                risk_assessment=RiskAssessment(
                    risk_score=100.0,
                    risk_level=PatrolStatus.CRITICAL,
                    risk_factors=["Patrol execution failed"],
                    mitigation_suggestions=["Check system logs", "Verify configuration"],
                ),
                summary=f"Patrol execution failed: {str(e)}",
                recommendations=["Investigate the failure cause"],
                metadata={"error": str(e), "execution_id": exec_id},
            )

        finally:
            # 清除運行標記
            if exec_id in self._running_patrols:
                del self._running_patrols[exec_id]

    async def _execute_checks(
        self,
        config: PatrolConfig,
    ) -> List[CheckResult]:
        """執行所有檢查項目"""
        results: List[CheckResult] = []
        tasks = []

        for check_type in config.check_types:
            if check_type in self._check_registry:
                check_class = self._check_registry[check_type]
                check = check_class(config.metadata.get(check_type.value, {}))
                tasks.append(self._execute_single_check(check, config.timeout_seconds))
            else:
                logger.warning(f"Check type not registered: {check_type.value}")

        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)

            for result in completed:
                if isinstance(result, Exception):
                    logger.error(f"Check execution error: {result}")
                    # 創建錯誤結果
                    results.append(
                        CheckResult(
                            check_id=f"check_{uuid4().hex[:12]}",
                            check_type=CheckType.SERVICE_HEALTH,
                            status=PatrolStatus.UNKNOWN,
                            message=f"Check execution failed: {str(result)}",
                            started_at=datetime.utcnow(),
                            completed_at=datetime.utcnow(),
                            duration_ms=0,
                            errors=[str(result)],
                        )
                    )
                elif isinstance(result, CheckResult):
                    results.append(result)

        return results

    async def _execute_single_check(
        self,
        check: PatrolCheck,
        timeout_seconds: int,
    ) -> CheckResult:
        """執行單個檢查（帶超時）"""
        try:
            result = await asyncio.wait_for(
                check.execute(),
                timeout=timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            return check._create_result(
                status=PatrolStatus.WARNING,
                message="Check timed out",
                started_at=datetime.utcnow(),
                errors=["Timeout exceeded"],
            )

    async def _assess_risk(
        self,
        checks: List[CheckResult],
    ) -> RiskAssessment:
        """評估風險"""
        risk_score = calculate_risk_score(checks)

        # 確定風險等級
        if risk_score >= 70:
            risk_level = PatrolStatus.CRITICAL
        elif risk_score >= 40:
            risk_level = PatrolStatus.WARNING
        else:
            risk_level = PatrolStatus.HEALTHY

        # 提取風險因素
        risk_factors = []
        for check in checks:
            if check.status == PatrolStatus.CRITICAL:
                risk_factors.append(f"Critical: {check.check_type.value} - {check.message}")
            elif check.status == PatrolStatus.WARNING:
                risk_factors.append(f"Warning: {check.check_type.value} - {check.message}")

        # 生成緩解建議
        mitigation_suggestions = self._generate_mitigation_suggestions(checks)

        return RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            mitigation_suggestions=mitigation_suggestions,
        )

    def _generate_mitigation_suggestions(
        self,
        checks: List[CheckResult],
    ) -> List[str]:
        """生成緩解建議"""
        suggestions = []

        for check in checks:
            if check.status in [PatrolStatus.WARNING, PatrolStatus.CRITICAL]:
                if check.check_type == CheckType.SERVICE_HEALTH:
                    suggestions.append("Check service health endpoints and restart if necessary")
                elif check.check_type == CheckType.API_RESPONSE:
                    suggestions.append("Review API response times and optimize slow endpoints")
                elif check.check_type == CheckType.RESOURCE_USAGE:
                    suggestions.append("Monitor resource usage and scale if needed")
                elif check.check_type == CheckType.LOG_ANALYSIS:
                    suggestions.append("Review error logs and address recurring issues")
                elif check.check_type == CheckType.SECURITY_SCAN:
                    suggestions.append("Address security vulnerabilities immediately")

        return list(set(suggestions))  # 去重

    async def _analyze_results(
        self,
        config: PatrolConfig,
        checks: List[CheckResult],
        overall_status: PatrolStatus,
        risk_assessment: RiskAssessment,
    ) -> tuple[str, List[str]]:
        """
        使用 Claude 分析巡檢結果

        Returns:
            (summary, recommendations)
        """
        if not self._claude_client:
            # 無 Claude 客戶端時返回基本分析
            return self._generate_basic_analysis(
                config, checks, overall_status, risk_assessment
            )

        try:
            # 構建分析提示
            prompt = self._build_analysis_prompt(
                config, checks, overall_status, risk_assessment
            )

            # 調用 Claude 分析
            response = await self._claude_client.send_message(
                message=prompt,
                system_prompt=(
                    "You are a system reliability expert. Analyze the patrol results "
                    "and provide a concise summary and actionable recommendations. "
                    "Focus on the most critical issues first."
                ),
            )

            # 解析響應
            summary, recommendations = self._parse_claude_response(response)
            return summary, recommendations

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return self._generate_basic_analysis(
                config, checks, overall_status, risk_assessment
            )

    def _build_analysis_prompt(
        self,
        config: PatrolConfig,
        checks: List[CheckResult],
        overall_status: PatrolStatus,
        risk_assessment: RiskAssessment,
    ) -> str:
        """構建 Claude 分析提示"""
        check_details = "\n".join(
            f"- {c.check_type.value}: {c.status.value} - {c.message}"
            for c in checks
        )

        return f"""
Analyze the following patrol results:

Patrol: {config.name}
Overall Status: {overall_status.value}
Risk Score: {risk_assessment.risk_score}/100
Risk Level: {risk_assessment.risk_level.value}

Check Results:
{check_details}

Risk Factors:
{chr(10).join(f'- {rf}' for rf in risk_assessment.risk_factors) or 'None identified'}

Please provide:
1. A concise summary (2-3 sentences) of the patrol findings
2. Top 3-5 actionable recommendations prioritized by urgency

Format your response as:
SUMMARY: <your summary>
RECOMMENDATIONS:
- <recommendation 1>
- <recommendation 2>
- ...
"""

    def _parse_claude_response(
        self,
        response: str,
    ) -> tuple[str, List[str]]:
        """解析 Claude 響應"""
        summary = ""
        recommendations = []

        lines = response.strip().split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith("SUMMARY:"):
                current_section = "summary"
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("RECOMMENDATIONS:"):
                current_section = "recommendations"
            elif current_section == "recommendations" and line.startswith("-"):
                recommendations.append(line[1:].strip())
            elif current_section == "summary" and line:
                summary += " " + line

        return summary.strip(), recommendations

    def _generate_basic_analysis(
        self,
        config: PatrolConfig,
        checks: List[CheckResult],
        overall_status: PatrolStatus,
        risk_assessment: RiskAssessment,
    ) -> tuple[str, List[str]]:
        """生成基本分析（無 Claude 時使用）"""
        # 統計
        total = len(checks)
        healthy = sum(1 for c in checks if c.status == PatrolStatus.HEALTHY)
        warning = sum(1 for c in checks if c.status == PatrolStatus.WARNING)
        critical = sum(1 for c in checks if c.status == PatrolStatus.CRITICAL)

        # 摘要
        summary = (
            f"Patrol '{config.name}' completed with overall status: {overall_status.value}. "
            f"Out of {total} checks: {healthy} healthy, {warning} warnings, {critical} critical. "
            f"Risk score: {risk_assessment.risk_score:.1f}/100."
        )

        # 建議
        recommendations = risk_assessment.mitigation_suggestions.copy()
        if not recommendations:
            if overall_status == PatrolStatus.HEALTHY:
                recommendations.append("System is healthy. Continue regular monitoring.")
            else:
                recommendations.append("Review the check details and address issues.")

        return summary, recommendations

    def is_patrol_running(self, execution_id: str) -> bool:
        """檢查巡檢是否運行中"""
        return execution_id in self._running_patrols

    @property
    def registered_checks(self) -> List[CheckType]:
        """已註冊的檢查類型"""
        return list(self._check_registry.keys())
