"""
LLM Classification Evaluation Set

Provides 54 evaluation cases balanced across intent categories
for measuring LLM classifier accuracy.

Sprint 128: Story 128-1 — Classification Evaluation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..models import ITIntentCategory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvaluationCase:
    """
    A single evaluation case for classification accuracy testing.

    Attributes:
        input_text: The user input to classify
        expected_category: Expected ITIntentCategory
        expected_sub_intent: Expected sub-intent (optional)
        description: Human-readable description of the case
        language: Input language ("zh" for Chinese, "en" for English)
    """

    input_text: str
    expected_category: ITIntentCategory
    expected_sub_intent: Optional[str] = None
    description: str = ""
    language: str = "zh"


@dataclass
class EvaluationResult:
    """
    Result of running evaluation cases through a classifier.

    Attributes:
        total: Total number of cases evaluated
        correct: Number of correctly classified cases
        incorrect: Number of incorrectly classified cases
        accuracy: Overall accuracy (0.0 to 1.0)
        per_category: Accuracy breakdown per category
        failures: List of failed case details
    """

    total: int = 0
    correct: int = 0
    incorrect: int = 0
    accuracy: float = 0.0
    per_category: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    failures: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# Evaluation Cases — 54 total
# =============================================================================

EVALUATION_CASES: List[EvaluationCase] = [
    # --- INCIDENT (15 cases) ---
    EvaluationCase(
        input_text="ETL Pipeline 今天凌晨跑失敗了，很緊急",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="etl_failure",
        description="ETL failure (urgent)",
    ),
    EvaluationCase(
        input_text="公司網路從下午兩點開始不穩定，很多人無法連線",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="network_issue",
        description="Network instability",
    ),
    EvaluationCase(
        input_text="系統回應速度越來越慢，API 平均延遲超過 5 秒",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="performance_degradation",
        description="Performance degradation",
    ),
    EvaluationCase(
        input_text="ERP 系統完全無法登入，所有使用者都受影響",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="system_unavailable",
        description="System unavailable",
    ),
    EvaluationCase(
        input_text="資料庫連線不斷斷開，應用程式無法寫入資料",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="database_error",
        description="Database connection error",
    ),
    EvaluationCase(
        input_text="SSO 認證服務掛掉了，全公司無法登入",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="authentication_failure",
        description="Authentication failure",
    ),
    EvaluationCase(
        input_text="The production database is returning timeout errors",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="database_error",
        description="Database timeout (English)",
        language="en",
    ),
    EvaluationCase(
        input_text="伺服器 CPU 使用率持續 100%，需要緊急處理",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="performance_degradation",
        description="CPU saturation",
    ),
    EvaluationCase(
        input_text="備份排程昨晚沒有執行，備份資料缺失",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="etl_failure",
        description="Backup schedule failure",
    ),
    EvaluationCase(
        input_text="DNS 解析失敗，內部服務互相無法呼叫",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="network_issue",
        description="DNS resolution failure",
    ),
    EvaluationCase(
        input_text="磁碟空間不足，系統日誌已停止寫入",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="system_unavailable",
        description="Disk space exhaustion",
    ),
    EvaluationCase(
        input_text="Load balancer 健康檢查失敗，流量無法正確分配",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="network_issue",
        description="Load balancer health check failure",
    ),
    EvaluationCase(
        input_text="Kafka consumer 停止消費訊息，訊息堆積嚴重",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="performance_degradation",
        description="Kafka consumer lag",
    ),
    EvaluationCase(
        input_text="SSL 憑證過期，HTTPS 連線被瀏覽器攔截",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="authentication_failure",
        description="SSL certificate expiry",
    ),
    EvaluationCase(
        input_text="容器不斷重啟，OOM Killed 錯誤",
        expected_category=ITIntentCategory.INCIDENT,
        expected_sub_intent="system_unavailable",
        description="Container OOM crash loop",
    ),
    # --- REQUEST (14 cases) ---
    EvaluationCase(
        input_text="我需要申請一個新的 Azure AD 帳號",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="account_creation",
        description="Account creation request",
    ),
    EvaluationCase(
        input_text="請幫我開通 GitHub Enterprise 的存取權限",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="permission_change",
        description="Permission change request",
    ),
    EvaluationCase(
        input_text="需要在我的電腦安裝 Visual Studio 2024",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="software_installation",
        description="Software installation request",
    ),
    EvaluationCase(
        input_text="我忘記密碼了，請幫我重設",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="password_reset",
        description="Password reset request",
    ),
    EvaluationCase(
        input_text="申請一台新的 MacBook Pro 做開發用",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="hardware_request",
        description="Hardware request",
    ),
    EvaluationCase(
        input_text="需要申請 VPN 帳號，要從家裡連公司網路",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="vpn_access",
        description="VPN access request",
    ),
    EvaluationCase(
        input_text="I need a new AWS IAM user account for the data team",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="account_creation",
        description="AWS account creation (English)",
        language="en",
    ),
    EvaluationCase(
        input_text="請幫新進人員開通 Office 365 授權",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="software_installation",
        description="Office license provisioning",
    ),
    EvaluationCase(
        input_text="申請將我的 AD 群組從 RD 改到 QA",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="permission_change",
        description="Group membership change",
    ),
    EvaluationCase(
        input_text="需要一個 Jira 專案空間給新團隊使用",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="account_creation",
        description="Jira project space request",
    ),
    EvaluationCase(
        input_text="我的筆電螢幕壞了，需要更換",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="hardware_request",
        description="Hardware replacement",
    ),
    EvaluationCase(
        input_text="需要申請 Slack 的管理員權限",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="permission_change",
        description="Slack admin permission",
    ),
    EvaluationCase(
        input_text="幫我安裝 Docker Desktop 和 kubectl",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="software_installation",
        description="Development tools installation",
    ),
    EvaluationCase(
        input_text="我的 MFA 裝置遺失，需要重新綁定",
        expected_category=ITIntentCategory.REQUEST,
        expected_sub_intent="password_reset",
        description="MFA device re-enrollment",
    ),
    # --- CHANGE (12 cases) ---
    EvaluationCase(
        input_text="週五需要部署 v2.5.0 到生產環境",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="release_deployment",
        description="Production deployment",
    ),
    EvaluationCase(
        input_text="需要修改防火牆規則，開放 8443 端口",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="configuration_update",
        description="Firewall rule change",
    ),
    EvaluationCase(
        input_text="要執行資料庫欄位新增的 migration script",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="database_change",
        description="Database migration",
    ),
    EvaluationCase(
        input_text="計劃升級 Kubernetes 叢集從 1.28 到 1.30",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="infrastructure_upgrade",
        description="K8s cluster upgrade",
    ),
    EvaluationCase(
        input_text="需要緊急套用 CVE-2026-1234 的安全修補",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="security_patch",
        description="Security patch application",
    ),
    EvaluationCase(
        input_text="要把 Redis 叢集從 6.x 升級到 7.x",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="infrastructure_upgrade",
        description="Redis upgrade",
    ),
    EvaluationCase(
        input_text="We need to deploy the hotfix to staging first",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="release_deployment",
        description="Hotfix deployment (English)",
        language="en",
    ),
    EvaluationCase(
        input_text="修改 Nginx 反向代理配置，加入新的 upstream",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="configuration_update",
        description="Nginx proxy configuration",
    ),
    EvaluationCase(
        input_text="需要新增資料庫的 read replica",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="database_change",
        description="Database read replica addition",
    ),
    EvaluationCase(
        input_text="要將日誌等級從 INFO 改成 DEBUG 做問題排查",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="configuration_update",
        description="Log level change",
    ),
    EvaluationCase(
        input_text="計劃將 CI/CD pipeline 從 Jenkins 遷移到 GitHub Actions",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="infrastructure_upgrade",
        description="CI/CD migration",
    ),
    EvaluationCase(
        input_text="需要更新 TLS 1.2 到 TLS 1.3 的配置",
        expected_category=ITIntentCategory.CHANGE,
        expected_sub_intent="security_patch",
        description="TLS version upgrade",
    ),
    # --- QUERY (9 cases) ---
    EvaluationCase(
        input_text="請問目前生產環境的 CPU 使用率是多少？",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="status_inquiry",
        description="System status inquiry",
    ),
    EvaluationCase(
        input_text="需要一份上個月的系統可用性報表",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="report_request",
        description="Availability report request",
    ),
    EvaluationCase(
        input_text="INC-2024-0512 這張工單的處理進度如何？",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="ticket_status",
        description="Ticket status inquiry",
    ),
    EvaluationCase(
        input_text="有沒有 Kubernetes 叢集維護的 SOP 文件？",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="documentation_request",
        description="Documentation request",
    ),
    EvaluationCase(
        input_text="API rate limit 的設定值是多少？",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="general_question",
        description="General technical question",
    ),
    EvaluationCase(
        input_text="What is the current disk usage on the production servers?",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="status_inquiry",
        description="Disk usage inquiry (English)",
        language="en",
    ),
    EvaluationCase(
        input_text="上次的維護視窗是什麼時候？",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="general_question",
        description="Maintenance window inquiry",
    ),
    EvaluationCase(
        input_text="可以看一下這個月的 incident 趨勢嗎？",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="report_request",
        description="Incident trend report",
    ),
    EvaluationCase(
        input_text="DR 切換的流程文件在哪裡？",
        expected_category=ITIntentCategory.QUERY,
        expected_sub_intent="documentation_request",
        description="DR procedure documentation",
    ),
    # --- AMBIGUOUS (4 cases) ---
    EvaluationCase(
        input_text="你好",
        expected_category=ITIntentCategory.UNKNOWN,
        description="Simple greeting",
    ),
    EvaluationCase(
        input_text="系統好像有點問題但我不確定",
        expected_category=ITIntentCategory.UNKNOWN,
        description="Vague unclear input",
    ),
    EvaluationCase(
        input_text="help me with something please",
        expected_category=ITIntentCategory.UNKNOWN,
        description="Vague help request (English)",
        language="en",
    ),
    EvaluationCase(
        input_text="謝謝你的幫忙",
        expected_category=ITIntentCategory.UNKNOWN,
        description="Thank you / closing",
    ),
]


async def evaluate_classifier(
    classifier: Any,
    cases: Optional[List[EvaluationCase]] = None,
) -> EvaluationResult:
    """
    Evaluate a classifier against evaluation cases.

    Runs all cases through the classifier and computes accuracy metrics.

    Args:
        classifier: An object with an async `classify(user_input)` method
                     that returns an object with `intent_category` attribute
        cases: Optional list of EvaluationCase. Uses EVALUATION_CASES if None.

    Returns:
        EvaluationResult with accuracy metrics and failure details
    """
    if cases is None:
        cases = EVALUATION_CASES

    result = EvaluationResult(total=len(cases))

    # Initialize per-category tracking
    category_stats: Dict[str, Dict[str, int]] = {}
    for cat in ITIntentCategory:
        category_stats[cat.value] = {"total": 0, "correct": 0}

    for case in cases:
        category_stats[case.expected_category.value]["total"] += 1

        try:
            classification = await classifier.classify(case.input_text)
            actual_category = classification.intent_category

            if actual_category == case.expected_category:
                result.correct += 1
                category_stats[case.expected_category.value]["correct"] += 1
            else:
                result.incorrect += 1
                result.failures.append({
                    "input": case.input_text,
                    "expected": case.expected_category.value,
                    "actual": actual_category.value,
                    "description": case.description,
                })
        except Exception as e:
            result.incorrect += 1
            result.failures.append({
                "input": case.input_text,
                "expected": case.expected_category.value,
                "actual": "error",
                "error": str(e),
                "description": case.description,
            })

    # Compute accuracy
    result.accuracy = result.correct / result.total if result.total > 0 else 0.0

    # Compute per-category accuracy
    for cat_value, stats in category_stats.items():
        if stats["total"] > 0:
            result.per_category[cat_value] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": stats["correct"] / stats["total"],
            }

    logger.info(
        f"Evaluation complete: {result.correct}/{result.total} "
        f"({result.accuracy:.1%} accuracy)"
    )

    return result
