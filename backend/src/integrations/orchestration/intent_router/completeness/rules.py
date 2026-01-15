"""
Completeness Rules Definition

Defines completeness checking rules for each IT intent category.
Rules specify required fields, optional fields, thresholds, and extraction patterns.

Sprint 93: Story 93-3 - Define Completeness Rules (Phase 28)
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern, Tuple

from ..models import ITIntentCategory


@dataclass
class FieldDefinition:
    """
    Definition of a field to be extracted from user input.

    Attributes:
        name: Field identifier (e.g., "affected_system")
        display_name: Human-readable name (e.g., "受影響系統")
        description: Description of the field
        patterns: Regex patterns for extraction
        keywords: Keywords that indicate field presence
        required: Whether this field is required
        examples: Example values for this field
    """
    name: str
    display_name: str
    description: str = ""
    patterns: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    required: bool = True
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "patterns": self.patterns,
            "keywords": self.keywords,
            "required": self.required,
            "examples": self.examples,
        }


@dataclass
class CompletenessRule:
    """
    Rule for checking completeness of a specific intent category.

    Attributes:
        category: Intent category this rule applies to
        threshold: Minimum completeness score (0.0 to 1.0)
        required_fields: List of required field definitions
        optional_fields: List of optional field definitions
        description: Human-readable description
        suggestions_template: Template for generating suggestions
    """
    category: ITIntentCategory
    threshold: float
    required_fields: List[FieldDefinition]
    optional_fields: List[FieldDefinition] = field(default_factory=list)
    description: str = ""
    suggestions_template: str = "請提供 {field_name}"

    def __post_init__(self):
        """Validate threshold range."""
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "threshold": self.threshold,
            "required_fields": [f.to_dict() for f in self.required_fields],
            "optional_fields": [f.to_dict() for f in self.optional_fields],
            "description": self.description,
        }

    def get_all_field_names(self) -> List[str]:
        """Get all field names (required + optional)."""
        return (
            [f.name for f in self.required_fields] +
            [f.name for f in self.optional_fields]
        )

    def get_required_field_names(self) -> List[str]:
        """Get required field names only."""
        return [f.name for f in self.required_fields]


# =============================================================================
# Field Definitions by Category
# =============================================================================

# -----------------------------------------------------------------------------
# Incident Fields (事件類)
# -----------------------------------------------------------------------------

INCIDENT_FIELDS = {
    "affected_system": FieldDefinition(
        name="affected_system",
        display_name="受影響系統",
        description="發生問題的系統或服務名稱",
        patterns=[
            r"(?:系統|服務|平台|模組|應用)[：:]\s*([^\s,，。]+)",
            r"([A-Z][A-Za-z0-9_-]+)\s*(?:系統|服務|平台)?(?:掛了|故障|出問題|失敗|錯誤)",
            r"(?:ETL|API|DB|CRM|ERP|SAP|Oracle|SQL|Redis|MongoDB|Kafka|RabbitMQ)",
        ],
        keywords=[
            "系統", "服務", "平台", "模組", "應用", "ETL", "API", "資料庫",
            "CRM", "ERP", "SAP", "網站", "APP", "後台",
        ],
        required=True,
        examples=["ETL 系統", "CRM 服務", "訂單系統", "API Gateway"],
    ),
    "symptom_type": FieldDefinition(
        name="symptom_type",
        display_name="症狀類型",
        description="問題的症狀或表現",
        patterns=[
            r"(失敗|錯誤|故障|掛了|當機|超時|延遲|緩慢|異常|無法|不能)",
            r"(error|fail|timeout|slow|crash|down|unavailable)",
        ],
        keywords=[
            "失敗", "錯誤", "故障", "掛", "當機", "超時", "延遲",
            "慢", "異常", "無法", "不能", "問題", "error", "fail",
        ],
        required=True,
        examples=["執行失敗", "回應超時", "系統當機", "效能緩慢"],
    ),
    "urgency": FieldDefinition(
        name="urgency",
        display_name="緊急程度",
        description="問題的緊急程度或業務影響",
        patterns=[
            r"(緊急|急|馬上|立刻|嚴重|重大|critical|urgent|asap)",
            r"(影響|導致|造成).*?(業務|生產|客戶|訂單|交易)",
        ],
        keywords=[
            "緊急", "急", "馬上", "立刻", "嚴重", "重大",
            "影響", "業務", "生產", "客戶", "critical", "urgent",
        ],
        required=True,
        examples=["緊急", "影響生產", "客戶無法使用", "業務停擺"],
    ),
    "error_message": FieldDefinition(
        name="error_message",
        display_name="錯誤訊息",
        description="系統顯示的錯誤訊息",
        patterns=[
            r"(?:錯誤|error|exception|訊息)[：:]?\s*(.+?)(?:[。,，]|$)",
            r"\"([^\"]+error[^\"]+)\"",
            r"'([^']+error[^']+)'",
        ],
        keywords=["錯誤訊息", "error message", "exception", "log"],
        required=False,
        examples=["Connection timeout", "NullPointerException", "503 Service Unavailable"],
    ),
    "occurrence_time": FieldDefinition(
        name="occurrence_time",
        display_name="發生時間",
        description="問題發生的時間",
        patterns=[
            r"(\d{1,2}[/:]\d{2}(?:[/:]\d{2})?)",
            r"(今天|昨天|剛才|上午|下午|早上|晚上)\s*\d*[點時]?",
            r"(\d+\s*(?:分鐘|小時|天)前)",
        ],
        keywords=["時間", "發生", "開始", "何時", "什麼時候"],
        required=False,
        examples=["今天下午 2 點", "剛才", "10 分鐘前", "14:30"],
    ),
}

# -----------------------------------------------------------------------------
# Request Fields (請求類)
# -----------------------------------------------------------------------------

REQUEST_FIELDS = {
    "request_type": FieldDefinition(
        name="request_type",
        display_name="請求類型",
        description="請求的類型或性質",
        patterns=[
            r"(?:申請|請求|需要|想要)[：:]?\s*([^\s,，。]+)",
            r"(帳號|權限|軟體|設備|安裝|重設|更換|新增)",
        ],
        keywords=[
            "申請", "請求", "需要", "想要", "帳號", "權限",
            "軟體", "設備", "安裝", "重設", "更換", "新增",
        ],
        required=True,
        examples=["帳號申請", "權限變更", "軟體安裝", "密碼重設"],
    ),
    "requester": FieldDefinition(
        name="requester",
        display_name="申請人",
        description="提出請求的人員",
        patterns=[
            r"(?:申請人|使用者|用戶|員工)[：:]?\s*([^\s,，。]+)",
            r"(?:為|幫|給)\s*([^\s,，。]+)\s*(?:申請|開)",
        ],
        keywords=["申請人", "使用者", "員工", "同事", "部門"],
        required=True,
        examples=["張三", "新進員工", "行銷部門"],
    ),
    "justification": FieldDefinition(
        name="justification",
        display_name="申請理由",
        description="申請的理由或業務需求",
        patterns=[
            r"(?:因為|由於|為了|原因)[：:]?\s*(.+?)(?:[。,，]|$)",
            r"(?:需要|必須).*?(?:所以|因此)(.+?)(?:[。,，]|$)",
        ],
        keywords=["因為", "由於", "為了", "原因", "需要", "業務"],
        required=True,
        examples=["新專案需要", "業務需求", "工作必要"],
    ),
    "target_resource": FieldDefinition(
        name="target_resource",
        display_name="目標資源",
        description="申請存取或使用的資源",
        patterns=[
            r"(?:存取|使用|連接)\s*([^\s,，。]+)",
            r"([A-Z][A-Za-z0-9_-]+)(?:系統|服務|資料庫)?(?:的)?(?:權限|存取)",
        ],
        keywords=["系統", "服務", "資料庫", "資料夾", "檔案", "VPN"],
        required=False,
        examples=["CRM 系統", "共用資料夾", "VPN 存取"],
    ),
    "deadline": FieldDefinition(
        name="deadline",
        display_name="期望完成日期",
        description="希望完成的日期或時間",
        patterns=[
            r"(?:希望|期望|需要).*?(\d{1,2}[/\-月]\d{1,2}[日號]?)",
            r"(今天|明天|這週|下週|本週|月底)(?:前)?(?:完成|需要)?",
        ],
        keywords=["希望", "期望", "之前", "月底", "週末"],
        required=False,
        examples=["下週一前", "月底前", "越快越好"],
    ),
}

# -----------------------------------------------------------------------------
# Change Fields (變更類)
# -----------------------------------------------------------------------------

CHANGE_FIELDS = {
    "change_type": FieldDefinition(
        name="change_type",
        display_name="變更類型",
        description="變更的類型或性質",
        patterns=[
            r"(?:部署|更新|升級|安裝|配置|修改|調整)[：:]?\s*([^\s,，。]+)?",
            r"(release|deploy|update|upgrade|config|patch)",
        ],
        keywords=[
            "部署", "更新", "升級", "安裝", "配置", "修改",
            "調整", "release", "deploy", "update", "patch",
        ],
        required=True,
        examples=["版本部署", "設定更新", "系統升級", "補丁安裝"],
    ),
    "target_system": FieldDefinition(
        name="target_system",
        display_name="目標系統",
        description="變更影響的系統或服務",
        patterns=[
            r"(?:系統|服務|平台|模組)[：:]\s*([^\s,，。]+)",
            r"(?:在|對)\s*([^\s,，。]+)\s*(?:上|中|裡)?(?:部署|更新|安裝|修改)",
        ],
        keywords=[
            "系統", "服務", "平台", "模組", "伺服器", "環境",
            "生產", "測試", "開發",
        ],
        required=True,
        examples=["訂單系統", "生產環境", "API 服務", "資料庫"],
    ),
    "schedule": FieldDefinition(
        name="schedule",
        display_name="排程時間",
        description="計劃執行變更的時間",
        patterns=[
            r"(?:預計|計劃|排定|安排).*?(\d{1,2}[/\-月]\d{1,2}[日號]?)",
            r"(\d{1,2}[/:]\d{2})\s*(?:執行|部署|更新)",
            r"(今晚|明天|週末|下週)(?:的)?(?:維護窗口|時段)?",
        ],
        keywords=[
            "預計", "計劃", "排定", "安排", "時間", "日期",
            "維護窗口", "離峰", "凌晨",
        ],
        required=True,
        examples=["下週二 02:00", "維護窗口期間", "週末離峰時段"],
    ),
    "version": FieldDefinition(
        name="version",
        display_name="版本號",
        description="要部署或更新的版本",
        patterns=[
            r"(?:版本|version|v)[：:]?\s*([\d.]+(?:-[a-zA-Z0-9]+)?)",
            r"(v?[\d]+\.[\d]+\.[\d]+(?:-[a-zA-Z0-9]+)?)",
        ],
        keywords=["版本", "version", "v", "release"],
        required=False,
        examples=["v2.1.0", "1.5.3-beta", "release-20240115"],
    ),
    "rollback_plan": FieldDefinition(
        name="rollback_plan",
        display_name="回滾計劃",
        description="變更失敗時的回滾方案",
        patterns=[
            r"(?:回滾|rollback|復原)[：:]?\s*(.+?)(?:[。,，]|$)",
        ],
        keywords=["回滾", "rollback", "復原", "備份", "還原"],
        required=False,
        examples=["回滾到前一版本", "使用備份還原", "執行 rollback script"],
    ),
    "impact_assessment": FieldDefinition(
        name="impact_assessment",
        display_name="影響評估",
        description="變更對系統或業務的影響",
        patterns=[
            r"(?:影響|衝擊)[：:]?\s*(.+?)(?:[。,，]|$)",
            r"(?:停機|中斷)\s*(\d+\s*(?:分鐘|小時))?",
        ],
        keywords=["影響", "衝擊", "停機", "中斷", "降級"],
        required=False,
        examples=["預計停機 30 分鐘", "不影響服務", "短暫降級"],
    ),
}

# -----------------------------------------------------------------------------
# Query Fields (查詢類)
# -----------------------------------------------------------------------------

QUERY_FIELDS = {
    "query_type": FieldDefinition(
        name="query_type",
        display_name="查詢類型",
        description="查詢的類型或目的",
        patterns=[
            r"(?:查詢|詢問|了解|知道)[：:]?\s*([^\s,，。？?]+)",
            r"(?:如何|怎麼|什麼|哪裡|為什麼)(.+?)(?:[。？?]|$)",
        ],
        keywords=[
            "查詢", "詢問", "了解", "知道", "如何", "怎麼",
            "什麼", "哪裡", "為什麼", "狀態", "進度",
        ],
        required=True,
        examples=["系統狀態查詢", "如何重設密碼", "報表在哪裡"],
    ),
    "query_subject": FieldDefinition(
        name="query_subject",
        display_name="查詢主題",
        description="查詢的具體主題或對象",
        patterns=[
            r"(?:關於|有關|針對)\s*([^\s,，。？?]+)",
            r"([^\s,，。？?]+)(?:的)?(?:狀態|進度|資訊|文件)",
        ],
        keywords=["關於", "有關", "針對", "系統", "單號", "報表"],
        required=False,
        examples=["單號 INC123456", "ETL 執行狀態", "月報表"],
    ),
    "time_range": FieldDefinition(
        name="time_range",
        display_name="時間範圍",
        description="查詢的時間範圍",
        patterns=[
            r"(今天|昨天|本週|上週|本月|上月)",
            r"(\d{1,2}[/\-月]\d{1,2}[日號]?)(?:到|至)(\d{1,2}[/\-月]\d{1,2}[日號]?)",
        ],
        keywords=["今天", "昨天", "本週", "本月", "從", "到"],
        required=False,
        examples=["今天", "本週", "1/1 到 1/15"],
    ),
}


# =============================================================================
# Default Completeness Rules
# =============================================================================

def _get_threshold_from_env(category: str, default: float) -> float:
    """Get threshold from environment variable or use default."""
    env_key = f"COMPLETENESS_{category.upper()}_THRESHOLD"
    try:
        return float(os.getenv(env_key, default))
    except (ValueError, TypeError):
        return default


# Incident Rule (事件類規則) - 閾值 60%
INCIDENT_RULE = CompletenessRule(
    category=ITIntentCategory.INCIDENT,
    threshold=_get_threshold_from_env("incident", 0.60),
    required_fields=[
        INCIDENT_FIELDS["affected_system"],
        INCIDENT_FIELDS["symptom_type"],
        INCIDENT_FIELDS["urgency"],
    ],
    optional_fields=[
        INCIDENT_FIELDS["error_message"],
        INCIDENT_FIELDS["occurrence_time"],
    ],
    description="事件報告完整度規則：需要受影響系統、症狀類型和緊急程度",
    suggestions_template="請說明{field_name}以便更快處理您的問題",
)

# Request Rule (請求類規則) - 閾值 60%
REQUEST_RULE = CompletenessRule(
    category=ITIntentCategory.REQUEST,
    threshold=_get_threshold_from_env("request", 0.60),
    required_fields=[
        REQUEST_FIELDS["request_type"],
        REQUEST_FIELDS["requester"],
        REQUEST_FIELDS["justification"],
    ],
    optional_fields=[
        REQUEST_FIELDS["target_resource"],
        REQUEST_FIELDS["deadline"],
    ],
    description="服務請求完整度規則：需要請求類型、申請人和申請理由",
    suggestions_template="請提供{field_name}以完成申請",
)

# Change Rule (變更類規則) - 閾值 70%
CHANGE_RULE = CompletenessRule(
    category=ITIntentCategory.CHANGE,
    threshold=_get_threshold_from_env("change", 0.70),
    required_fields=[
        CHANGE_FIELDS["change_type"],
        CHANGE_FIELDS["target_system"],
        CHANGE_FIELDS["schedule"],
    ],
    optional_fields=[
        CHANGE_FIELDS["version"],
        CHANGE_FIELDS["rollback_plan"],
        CHANGE_FIELDS["impact_assessment"],
    ],
    description="變更請求完整度規則：需要變更類型、目標系統和排程時間",
    suggestions_template="請提供{field_name}以進行變更評估",
)

# Query Rule (查詢類規則) - 閾值 50%
QUERY_RULE = CompletenessRule(
    category=ITIntentCategory.QUERY,
    threshold=_get_threshold_from_env("query", 0.50),
    required_fields=[
        QUERY_FIELDS["query_type"],
    ],
    optional_fields=[
        QUERY_FIELDS["query_subject"],
        QUERY_FIELDS["time_range"],
    ],
    description="一般查詢完整度規則：需要查詢類型",
    suggestions_template="請說明{field_name}以提供更準確的答覆",
)

# Unknown/Default Rule
UNKNOWN_RULE = CompletenessRule(
    category=ITIntentCategory.UNKNOWN,
    threshold=0.0,
    required_fields=[],
    optional_fields=[],
    description="未知意圖類型：無特定完整度要求",
)


# =============================================================================
# Rules Registry
# =============================================================================

class CompletenessRules:
    """
    Registry for completeness rules by intent category.

    Provides rule lookup and management for the CompletenessChecker.
    """

    # Default rules mapping
    _default_rules: Dict[ITIntentCategory, CompletenessRule] = {
        ITIntentCategory.INCIDENT: INCIDENT_RULE,
        ITIntentCategory.REQUEST: REQUEST_RULE,
        ITIntentCategory.CHANGE: CHANGE_RULE,
        ITIntentCategory.QUERY: QUERY_RULE,
        ITIntentCategory.UNKNOWN: UNKNOWN_RULE,
    }

    def __init__(
        self,
        rules: Optional[Dict[ITIntentCategory, CompletenessRule]] = None,
    ):
        """
        Initialize the rules registry.

        Args:
            rules: Custom rules to override defaults (optional)
        """
        self._rules = self._default_rules.copy()
        if rules:
            self._rules.update(rules)

    def get_rule(self, category: ITIntentCategory) -> CompletenessRule:
        """
        Get the completeness rule for a category.

        Args:
            category: The intent category

        Returns:
            CompletenessRule for the category (or UNKNOWN_RULE if not found)
        """
        return self._rules.get(category, UNKNOWN_RULE)

    def set_rule(
        self,
        category: ITIntentCategory,
        rule: CompletenessRule,
    ) -> None:
        """
        Set or update a rule for a category.

        Args:
            category: The intent category
            rule: The completeness rule to set
        """
        self._rules[category] = rule

    def get_all_rules(self) -> Dict[ITIntentCategory, CompletenessRule]:
        """Get all rules in the registry."""
        return self._rules.copy()

    def get_rule_categories(self) -> List[ITIntentCategory]:
        """Get list of categories with defined rules."""
        return list(self._rules.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Convert all rules to dictionary for serialization."""
        return {
            cat.value: rule.to_dict()
            for cat, rule in self._rules.items()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompletenessRules":
        """
        Create CompletenessRules from dictionary.

        Args:
            data: Dictionary with rule definitions

        Returns:
            CompletenessRules instance
        """
        rules = {}
        for cat_str, rule_data in data.items():
            category = ITIntentCategory.from_string(cat_str)
            fields = []
            for field_data in rule_data.get("required_fields", []):
                fields.append(FieldDefinition(**field_data))

            opt_fields = []
            for field_data in rule_data.get("optional_fields", []):
                opt_fields.append(FieldDefinition(**field_data))

            rule = CompletenessRule(
                category=category,
                threshold=rule_data.get("threshold", 0.5),
                required_fields=fields,
                optional_fields=opt_fields,
                description=rule_data.get("description", ""),
            )
            rules[category] = rule

        return cls(rules=rules)


# =============================================================================
# Utility Functions
# =============================================================================

def get_default_rules() -> CompletenessRules:
    """Get default completeness rules instance."""
    return CompletenessRules()


def get_required_fields(category: ITIntentCategory) -> List[str]:
    """
    Get list of required field names for a category.

    Args:
        category: The intent category

    Returns:
        List of required field names
    """
    rules = get_default_rules()
    rule = rules.get_rule(category)
    return rule.get_required_field_names()


def get_field_definition(
    category: ITIntentCategory,
    field_name: str,
) -> Optional[FieldDefinition]:
    """
    Get field definition by category and field name.

    Args:
        category: The intent category
        field_name: The field name to look up

    Returns:
        FieldDefinition if found, None otherwise
    """
    rules = get_default_rules()
    rule = rules.get_rule(category)

    for field in rule.required_fields + rule.optional_fields:
        if field.name == field_name:
            return field

    return None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "FieldDefinition",
    "CompletenessRule",
    "CompletenessRules",
    # Default rules
    "INCIDENT_RULE",
    "REQUEST_RULE",
    "CHANGE_RULE",
    "QUERY_RULE",
    "UNKNOWN_RULE",
    # Field collections
    "INCIDENT_FIELDS",
    "REQUEST_FIELDS",
    "CHANGE_FIELDS",
    "QUERY_FIELDS",
    # Utility functions
    "get_default_rules",
    "get_required_fields",
    "get_field_definition",
]
