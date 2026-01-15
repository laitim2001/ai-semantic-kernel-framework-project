"""
Predefined Semantic Routes for IT Service Management

Defines 10+ semantic routes covering incident, request, change, and query categories.
Each route contains 3-5 example utterances for semantic matching.

Sprint 92: Story 92-2 - Define 10+ Semantic Routes
"""

from typing import List

from ..models import (
    ITIntentCategory,
    RiskLevel,
    SemanticRoute,
    WorkflowType,
)


# =============================================================================
# Incident Routes
# =============================================================================

INCIDENT_ETL_ROUTE = SemanticRoute(
    name="incident_etl",
    category=ITIntentCategory.INCIDENT,
    sub_intent="etl_failure",
    description="ETL job failures and data pipeline issues",
    utterances=[
        "ETL 今天跑失敗了",
        "ETL job 執行錯誤",
        "資料管線出問題",
        "資料同步失敗了",
        "ETL 任務沒有完成",
    ],
    workflow_type=WorkflowType.MAGENTIC,
    risk_level=RiskLevel.HIGH,
)

INCIDENT_NETWORK_ROUTE = SemanticRoute(
    name="incident_network",
    category=ITIntentCategory.INCIDENT,
    sub_intent="network_issue",
    description="Network connectivity and communication issues",
    utterances=[
        "網路連線有問題",
        "無法連上伺服器",
        "網路斷線了",
        "連線一直斷掉",
        "網路很不穩定",
    ],
    workflow_type=WorkflowType.MAGENTIC,
    risk_level=RiskLevel.HIGH,
)

INCIDENT_PERFORMANCE_ROUTE = SemanticRoute(
    name="incident_performance",
    category=ITIntentCategory.INCIDENT,
    sub_intent="performance_degradation",
    description="System slowness and performance issues",
    utterances=[
        "系統跑得很慢",
        "效能變得很差",
        "系統響應很慢",
        "應用程式卡頓",
        "頁面載入很久",
    ],
    workflow_type=WorkflowType.MAGENTIC,
    risk_level=RiskLevel.MEDIUM,
)

INCIDENT_SYSTEM_DOWN_ROUTE = SemanticRoute(
    name="incident_system_down",
    category=ITIntentCategory.INCIDENT,
    sub_intent="system_unavailable",
    description="System outage and unavailability",
    utterances=[
        "系統掛掉了",
        "服務無法使用",
        "系統完全不能用",
        "網站打不開",
        "服務中斷了",
    ],
    workflow_type=WorkflowType.MAGENTIC,
    risk_level=RiskLevel.CRITICAL,
)


# =============================================================================
# Request Routes
# =============================================================================

REQUEST_ACCOUNT_ROUTE = SemanticRoute(
    name="request_account",
    category=ITIntentCategory.REQUEST,
    sub_intent="account_creation",
    description="New account creation requests",
    utterances=[
        "我需要申請新帳號",
        "幫我建立帳號",
        "要開一個新的帳號",
        "申請系統帳號",
        "新員工需要帳號",
    ],
    workflow_type=WorkflowType.SEQUENTIAL,
    risk_level=RiskLevel.LOW,
)

REQUEST_ACCESS_ROUTE = SemanticRoute(
    name="request_access",
    category=ITIntentCategory.REQUEST,
    sub_intent="permission_change",
    description="Access permission requests",
    utterances=[
        "請幫我開通權限",
        "需要存取權限",
        "申請系統權限",
        "要開放資料夾權限",
        "沒有權限進入",
    ],
    workflow_type=WorkflowType.SEQUENTIAL,
    risk_level=RiskLevel.MEDIUM,
)

REQUEST_SOFTWARE_ROUTE = SemanticRoute(
    name="request_software",
    category=ITIntentCategory.REQUEST,
    sub_intent="software_installation",
    description="Software installation requests",
    utterances=[
        "可以幫我安裝軟體嗎",
        "需要安裝新程式",
        "申請安裝 Office",
        "要裝開發工具",
        "請幫我安裝 VS Code",
    ],
    workflow_type=WorkflowType.SIMPLE,
    risk_level=RiskLevel.LOW,
)

REQUEST_PASSWORD_ROUTE = SemanticRoute(
    name="request_password",
    category=ITIntentCategory.REQUEST,
    sub_intent="password_reset",
    description="Password reset and account recovery",
    utterances=[
        "忘記密碼了",
        "密碼被鎖住",
        "需要重設密碼",
        "帳號無法登入",
        "密碼過期了",
    ],
    workflow_type=WorkflowType.SIMPLE,
    risk_level=RiskLevel.MEDIUM,
)


# =============================================================================
# Change Routes
# =============================================================================

CHANGE_DEPLOYMENT_ROUTE = SemanticRoute(
    name="change_deployment",
    category=ITIntentCategory.CHANGE,
    sub_intent="release_deployment",
    description="System deployment and release requests",
    utterances=[
        "需要部署新版本",
        "上線新功能",
        "部署更新",
        "發布新版程式",
        "準備上 production",
    ],
    workflow_type=WorkflowType.MAGENTIC,
    risk_level=RiskLevel.HIGH,
)

CHANGE_CONFIG_ROUTE = SemanticRoute(
    name="change_config",
    category=ITIntentCategory.CHANGE,
    sub_intent="configuration_update",
    description="System configuration changes",
    utterances=[
        "要修改系統設定",
        "更新組態配置",
        "調整系統參數",
        "修改 config 檔",
        "變更環境設定",
    ],
    workflow_type=WorkflowType.SEQUENTIAL,
    risk_level=RiskLevel.MEDIUM,
)

CHANGE_DATABASE_ROUTE = SemanticRoute(
    name="change_database",
    category=ITIntentCategory.CHANGE,
    sub_intent="database_change",
    description="Database schema and data changes",
    utterances=[
        "資料庫需要變更",
        "新增資料表欄位",
        "修改資料庫結構",
        "更新 schema",
        "資料庫 migration",
    ],
    workflow_type=WorkflowType.MAGENTIC,
    risk_level=RiskLevel.HIGH,
)


# =============================================================================
# Query Routes
# =============================================================================

QUERY_STATUS_ROUTE = SemanticRoute(
    name="query_status",
    category=ITIntentCategory.QUERY,
    sub_intent="status_inquiry",
    description="System status inquiries",
    utterances=[
        "目前系統狀態如何",
        "服務運作正常嗎",
        "現在系統穩定嗎",
        "檢查系統健康狀態",
        "服務有問題嗎",
    ],
    workflow_type=WorkflowType.SIMPLE,
    risk_level=RiskLevel.LOW,
)

QUERY_REPORT_ROUTE = SemanticRoute(
    name="query_report",
    category=ITIntentCategory.QUERY,
    sub_intent="report_request",
    description="Report generation requests",
    utterances=[
        "可以給我報表嗎",
        "需要一份報告",
        "產出統計數據",
        "匯出資料報表",
        "要看使用報告",
    ],
    workflow_type=WorkflowType.SIMPLE,
    risk_level=RiskLevel.LOW,
)

QUERY_TICKET_ROUTE = SemanticRoute(
    name="query_ticket",
    category=ITIntentCategory.QUERY,
    sub_intent="ticket_status",
    description="Ticket status inquiries",
    utterances=[
        "我的工單進度如何",
        "申請案件處理到哪了",
        "查詢需求單狀態",
        "案件編號查詢",
        "工單什麼時候處理",
    ],
    workflow_type=WorkflowType.SIMPLE,
    risk_level=RiskLevel.LOW,
)

QUERY_DOCUMENTATION_ROUTE = SemanticRoute(
    name="query_documentation",
    category=ITIntentCategory.QUERY,
    sub_intent="documentation_request",
    description="Documentation and help requests",
    utterances=[
        "有操作手冊嗎",
        "系統說明文件在哪",
        "怎麼使用這個功能",
        "教我怎麼操作",
        "有使用教學嗎",
    ],
    workflow_type=WorkflowType.SIMPLE,
    risk_level=RiskLevel.LOW,
)


# =============================================================================
# Route Collections
# =============================================================================

# All incident routes
INCIDENT_ROUTES: List[SemanticRoute] = [
    INCIDENT_ETL_ROUTE,
    INCIDENT_NETWORK_ROUTE,
    INCIDENT_PERFORMANCE_ROUTE,
    INCIDENT_SYSTEM_DOWN_ROUTE,
]

# All request routes
REQUEST_ROUTES: List[SemanticRoute] = [
    REQUEST_ACCOUNT_ROUTE,
    REQUEST_ACCESS_ROUTE,
    REQUEST_SOFTWARE_ROUTE,
    REQUEST_PASSWORD_ROUTE,
]

# All change routes
CHANGE_ROUTES: List[SemanticRoute] = [
    CHANGE_DEPLOYMENT_ROUTE,
    CHANGE_CONFIG_ROUTE,
    CHANGE_DATABASE_ROUTE,
]

# All query routes
QUERY_ROUTES: List[SemanticRoute] = [
    QUERY_STATUS_ROUTE,
    QUERY_REPORT_ROUTE,
    QUERY_TICKET_ROUTE,
    QUERY_DOCUMENTATION_ROUTE,
]

# All routes combined (15 total)
IT_SEMANTIC_ROUTES: List[SemanticRoute] = (
    INCIDENT_ROUTES + REQUEST_ROUTES + CHANGE_ROUTES + QUERY_ROUTES
)


def get_default_routes() -> List[SemanticRoute]:
    """
    Get the default set of IT service semantic routes.

    Returns:
        List of 15 predefined SemanticRoute objects covering:
        - 4 Incident routes (ETL, network, performance, system down)
        - 4 Request routes (account, access, software, password)
        - 3 Change routes (deployment, config, database)
        - 4 Query routes (status, report, ticket, documentation)
    """
    return IT_SEMANTIC_ROUTES.copy()


def get_routes_by_category(category: ITIntentCategory) -> List[SemanticRoute]:
    """
    Get routes filtered by intent category.

    Args:
        category: ITIntentCategory to filter by

    Returns:
        List of routes matching the category
    """
    category_map = {
        ITIntentCategory.INCIDENT: INCIDENT_ROUTES,
        ITIntentCategory.REQUEST: REQUEST_ROUTES,
        ITIntentCategory.CHANGE: CHANGE_ROUTES,
        ITIntentCategory.QUERY: QUERY_ROUTES,
    }
    return category_map.get(category, []).copy()


def get_route_statistics() -> dict:
    """
    Get statistics about the defined routes.

    Returns:
        Dictionary with route counts by category
    """
    return {
        "total": len(IT_SEMANTIC_ROUTES),
        "by_category": {
            "incident": len(INCIDENT_ROUTES),
            "request": len(REQUEST_ROUTES),
            "change": len(CHANGE_ROUTES),
            "query": len(QUERY_ROUTES),
        },
        "total_utterances": sum(
            len(r.utterances) for r in IT_SEMANTIC_ROUTES
        ),
    }
