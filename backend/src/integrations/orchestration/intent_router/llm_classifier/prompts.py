"""
LLM Classification Prompts

Defines multi-task prompts for intent classification and completeness assessment.
Designed for Claude Haiku to provide efficient, structured classification.

Sprint 92: Story 92-4 - Design Multi-Task Prompt
"""

from typing import List, Optional

# =============================================================================
# Main Classification Prompt
# =============================================================================

CLASSIFICATION_PROMPT = """你是一個 IT 服務管理分類專家。分析用戶輸入，返回 JSON 格式結果。

## 任務
1. 判斷意圖類別 (incident/request/change/query)
2. 判斷子意圖
3. 評估資訊完整度
4. 列出缺失的必要資訊

## 意圖類別說明

### incident (事件/故障)
用於報告系統故障、錯誤、效能問題等需要立即處理的情況。
子意圖範例: etl_failure, network_issue, performance_degradation, system_unavailable, database_error

### request (服務請求)
用於申請新服務、帳號、權限、軟體安裝等標準服務請求。
子意圖範例: account_creation, permission_change, software_installation, password_reset, hardware_request

### change (變更請求)
用於系統配置變更、部署、升級等需要變更管理的請求。
子意圖範例: release_deployment, configuration_update, database_change, infrastructure_upgrade

### query (查詢/詢問)
用於查詢狀態、報表、文檔、一般性問題等。
子意圖範例: status_inquiry, report_request, ticket_status, documentation_request, general_question

## 資訊完整度評估

根據意圖類別評估必要資訊是否完整：

### incident 必要資訊
- 問題描述 (what): 具體發生了什麼問題
- 影響範圍 (scope): 影響哪些系統/用戶
- 時間 (when): 問題何時開始發生

### request 必要資訊
- 請求內容 (what): 具體需要什麼服務
- 申請人/對象 (who): 誰需要這個服務
- 原因 (why): 為什麼需要（部分請求需要）

### change 必要資訊
- 變更內容 (what): 具體要變更什麼
- 變更原因 (why): 為什麼需要變更
- 預期時間 (when): 希望何時執行

### query 必要資訊
- 查詢內容 (what): 具體想知道什麼

## 用戶輸入
{user_input}

## 輸出格式 (純 JSON，不含 markdown 標記)
{{
  "intent_category": "incident|request|change|query",
  "sub_intent": "具體子意圖",
  "confidence": 0.0-1.0,
  "completeness": {{
    "score": 0.0-1.0,
    "is_complete": true|false,
    "missing_fields": ["欄位1", "欄位2"],
    "suggestions": ["建議1", "建議2"]
  }},
  "reasoning": "簡短說明分類理由"
}}

請直接輸出 JSON，不要包含 ```json 標記或其他文字。"""


# =============================================================================
# Simplified Classification Prompt (for faster response)
# =============================================================================

SIMPLE_CLASSIFICATION_PROMPT = """你是 IT 服務分類專家。分析輸入並返回 JSON。

類別: incident(故障), request(服務請求), change(變更), query(查詢)

輸入: {user_input}

輸出 JSON (純 JSON，無 markdown):
{{
  "intent_category": "類別",
  "sub_intent": "子意圖",
  "confidence": 0.0-1.0,
  "reasoning": "理由"
}}"""


# =============================================================================
# Completeness Assessment Prompt
# =============================================================================

COMPLETENESS_PROMPT = """分析以下 IT 服務請求的資訊完整度。

## 意圖類別: {intent_category}
## 用戶輸入: {user_input}

根據意圖類別評估資訊是否完整，返回 JSON:
{{
  "score": 0.0-1.0,
  "is_complete": true|false,
  "missing_fields": ["缺失欄位"],
  "suggestions": ["補充建議"]
}}

直接輸出 JSON，不要包含 markdown 標記。"""


# =============================================================================
# Helper Functions
# =============================================================================

def get_classification_prompt(
    user_input: str,
    include_completeness: bool = True,
    simplified: bool = False,
) -> str:
    """
    Generate the classification prompt for the given user input.

    Args:
        user_input: The user's input text to classify
        include_completeness: Whether to include completeness assessment
        simplified: Use simplified prompt for faster response

    Returns:
        Formatted prompt string
    """
    if simplified:
        return SIMPLE_CLASSIFICATION_PROMPT.format(user_input=user_input)

    return CLASSIFICATION_PROMPT.format(user_input=user_input)


def get_completeness_prompt(
    user_input: str,
    intent_category: str,
) -> str:
    """
    Generate the completeness assessment prompt.

    Args:
        user_input: The user's input text
        intent_category: The classified intent category

    Returns:
        Formatted prompt string
    """
    return COMPLETENESS_PROMPT.format(
        user_input=user_input,
        intent_category=intent_category,
    )


def get_required_fields(intent_category: str) -> List[str]:
    """
    Get required fields for a given intent category.

    Args:
        intent_category: The intent category

    Returns:
        List of required field names
    """
    required_fields = {
        "incident": ["問題描述", "影響範圍", "發生時間"],
        "request": ["請求內容", "申請人/對象"],
        "change": ["變更內容", "變更原因", "預期時間"],
        "query": ["查詢內容"],
    }
    return required_fields.get(intent_category.lower(), ["描述"])


def get_sub_intent_examples(intent_category: str) -> List[str]:
    """
    Get example sub-intents for a given category.

    Args:
        intent_category: The intent category

    Returns:
        List of example sub-intent names
    """
    sub_intents = {
        "incident": [
            "etl_failure",
            "network_issue",
            "performance_degradation",
            "system_unavailable",
            "database_error",
            "authentication_failure",
        ],
        "request": [
            "account_creation",
            "permission_change",
            "software_installation",
            "password_reset",
            "hardware_request",
            "vpn_access",
        ],
        "change": [
            "release_deployment",
            "configuration_update",
            "database_change",
            "infrastructure_upgrade",
            "security_patch",
        ],
        "query": [
            "status_inquiry",
            "report_request",
            "ticket_status",
            "documentation_request",
            "general_question",
        ],
    }
    return sub_intents.get(intent_category.lower(), [])
