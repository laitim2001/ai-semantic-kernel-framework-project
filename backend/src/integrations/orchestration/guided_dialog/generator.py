"""
Question Generator Implementation

Generates follow-up questions based on missing fields.
Uses template-based generation for consistency and efficiency.

Sprint 94: Story 94-4 - Implement QuestionGenerator (Phase 28)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..intent_router.models import ITIntentCategory

logger = logging.getLogger(__name__)


@dataclass
class QuestionTemplate:
    """
    Template for generating questions.

    Attributes:
        field_name: Name of the field this question targets
        question: Question text in Traditional Chinese
        priority: Question priority (higher = asked first)
        follow_up: Optional follow-up questions
        examples: Example valid answers
        category: Intent category this template applies to (None = all)
    """
    field_name: str
    question: str
    priority: int = 100
    follow_up: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    category: Optional[ITIntentCategory] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "field_name": self.field_name,
            "question": self.question,
            "priority": self.priority,
            "follow_up": self.follow_up,
            "examples": self.examples,
            "category": self.category.value if self.category else None,
        }


@dataclass
class GeneratedQuestion:
    """
    Generated question with metadata.

    Attributes:
        question: Question text
        target_field: Field this question aims to collect
        priority: Question priority
        context: Additional context for the question
    """
    question: str
    target_field: str
    priority: int = 100
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "question": self.question,
            "target_field": self.target_field,
            "priority": self.priority,
            "context": self.context,
        }


# =============================================================================
# Default Question Templates
# =============================================================================

# -----------------------------------------------------------------------------
# Incident Questions (事件相關問題)
# -----------------------------------------------------------------------------

INCIDENT_QUESTION_TEMPLATES: List[QuestionTemplate] = [
    QuestionTemplate(
        field_name="affected_system",
        question="請問是哪個系統有問題？",
        priority=100,
        examples=["ETL 系統", "CRM 服務", "訂單系統", "郵件伺服器"],
        category=ITIntentCategory.INCIDENT,
    ),
    QuestionTemplate(
        field_name="symptom_type",
        question="請描述具體的問題症狀",
        priority=90,
        follow_up=["是否有錯誤訊息？", "問題是何時開始的？"],
        examples=["執行失敗", "回應很慢", "完全無法使用", "顯示錯誤訊息"],
        category=ITIntentCategory.INCIDENT,
    ),
    QuestionTemplate(
        field_name="urgency",
        question="這個問題的緊急程度如何？是否影響業務？",
        priority=80,
        examples=["緊急，影響生產", "一般，可以等待", "非常緊急，客戶無法使用"],
        category=ITIntentCategory.INCIDENT,
    ),
    QuestionTemplate(
        field_name="error_message",
        question="有看到任何錯誤訊息嗎？請提供完整內容",
        priority=70,
        examples=["Connection timeout", "NullPointerException", "503 Service Unavailable"],
        category=ITIntentCategory.INCIDENT,
    ),
    QuestionTemplate(
        field_name="occurrence_time",
        question="問題是什麼時候開始發生的？",
        priority=60,
        examples=["今天下午 2 點", "剛才", "10 分鐘前", "今天早上開始"],
        category=ITIntentCategory.INCIDENT,
    ),
]

# -----------------------------------------------------------------------------
# Request Questions (請求相關問題)
# -----------------------------------------------------------------------------

REQUEST_QUESTION_TEMPLATES: List[QuestionTemplate] = [
    QuestionTemplate(
        field_name="request_type",
        question="請問您需要申請什麼？",
        priority=100,
        examples=["新帳號", "權限變更", "軟體安裝", "密碼重設"],
        category=ITIntentCategory.REQUEST,
    ),
    QuestionTemplate(
        field_name="requester",
        question="請問申請人是誰？",
        priority=90,
        follow_up=["申請人的部門是？", "申請人的員工編號是？"],
        examples=["張三", "行銷部 李小姐", "新進員工 王大明"],
        category=ITIntentCategory.REQUEST,
    ),
    QuestionTemplate(
        field_name="justification",
        question="請說明申請的原因或業務需求",
        priority=80,
        examples=["新專案需要", "工作職責變更", "臨時專案支援"],
        category=ITIntentCategory.REQUEST,
    ),
    QuestionTemplate(
        field_name="target_resource",
        question="需要存取哪些系統或資源？",
        priority=70,
        examples=["CRM 系統", "共用資料夾", "VPN 存取", "生產資料庫"],
        category=ITIntentCategory.REQUEST,
    ),
    QuestionTemplate(
        field_name="deadline",
        question="希望什麼時候完成？",
        priority=60,
        examples=["下週一前", "月底前", "越快越好", "本週五"],
        category=ITIntentCategory.REQUEST,
    ),
]

# -----------------------------------------------------------------------------
# Change Questions (變更相關問題)
# -----------------------------------------------------------------------------

CHANGE_QUESTION_TEMPLATES: List[QuestionTemplate] = [
    QuestionTemplate(
        field_name="change_type",
        question="請問這次變更的類型是什麼？",
        priority=100,
        examples=["版本部署", "配置更新", "資料庫修改", "系統升級"],
        category=ITIntentCategory.CHANGE,
    ),
    QuestionTemplate(
        field_name="target_system",
        question="變更會影響哪個系統或環境？",
        priority=95,
        examples=["訂單系統", "生產環境", "測試環境", "API 服務"],
        category=ITIntentCategory.CHANGE,
    ),
    QuestionTemplate(
        field_name="schedule",
        question="預計什麼時候執行變更？",
        priority=90,
        examples=["下週二凌晨 2 點", "維護窗口期間", "週末離峰時段"],
        category=ITIntentCategory.CHANGE,
    ),
    QuestionTemplate(
        field_name="version",
        question="要部署的版本號是多少？",
        priority=70,
        examples=["v2.1.0", "1.5.3-beta", "release-20240115"],
        category=ITIntentCategory.CHANGE,
    ),
    QuestionTemplate(
        field_name="rollback_plan",
        question="如果變更失敗，回滾方案是什麼？",
        priority=60,
        examples=["回滾到前一版本", "使用備份還原", "執行 rollback script"],
        category=ITIntentCategory.CHANGE,
    ),
    QuestionTemplate(
        field_name="impact_assessment",
        question="這次變更對服務有什麼影響？",
        priority=50,
        examples=["預計停機 30 分鐘", "不影響服務", "短暫服務降級"],
        category=ITIntentCategory.CHANGE,
    ),
]

# -----------------------------------------------------------------------------
# Query Questions (查詢相關問題)
# -----------------------------------------------------------------------------

QUERY_QUESTION_TEMPLATES: List[QuestionTemplate] = [
    QuestionTemplate(
        field_name="query_type",
        question="請問您想查詢什麼資訊？",
        priority=100,
        examples=["系統狀態", "工單進度", "使用報表", "操作說明"],
        category=ITIntentCategory.QUERY,
    ),
    QuestionTemplate(
        field_name="query_subject",
        question="請提供更具體的查詢對象",
        priority=80,
        examples=["單號 INC123456", "ETL 執行狀態", "昨天的報表"],
        category=ITIntentCategory.QUERY,
    ),
    QuestionTemplate(
        field_name="time_range",
        question="請問是查詢哪個時間範圍的資料？",
        priority=60,
        examples=["今天", "本週", "上個月", "1/1 到 1/15"],
        category=ITIntentCategory.QUERY,
    ),
]

# General templates (適用所有類型)
GENERAL_QUESTION_TEMPLATES: List[QuestionTemplate] = [
    QuestionTemplate(
        field_name="additional_details",
        question="請問還有其他需要補充的資訊嗎？",
        priority=10,
    ),
    QuestionTemplate(
        field_name="contact_info",
        question="方便留下您的聯絡方式嗎？",
        priority=5,
    ),
]


# =============================================================================
# Question Generator
# =============================================================================

class QuestionGenerator:
    """
    Rule-based question generator.

    Generates follow-up questions based on missing fields and templates.
    Does not use LLM for question generation.

    Attributes:
        templates: Dictionary of question templates by field name
        max_questions: Maximum questions to generate per call

    Example:
        >>> generator = QuestionGenerator()
        >>> questions = generator.generate(
        ...     intent_category=ITIntentCategory.INCIDENT,
        ...     missing_fields=["affected_system", "symptom_type"],
        ... )
        >>> for q in questions:
        ...     print(q.question)
        請問是哪個系統有問題？
        請描述具體的問題症狀
    """

    def __init__(
        self,
        custom_templates: Optional[List[QuestionTemplate]] = None,
        max_questions: int = 3,
    ):
        """
        Initialize the question generator.

        Args:
            custom_templates: Additional templates to include
            max_questions: Maximum questions per generation (default: 3)
        """
        self._templates: Dict[str, List[QuestionTemplate]] = {}
        self._max_questions = max_questions

        # Register default templates
        self._register_templates(INCIDENT_QUESTION_TEMPLATES)
        self._register_templates(REQUEST_QUESTION_TEMPLATES)
        self._register_templates(CHANGE_QUESTION_TEMPLATES)
        self._register_templates(QUERY_QUESTION_TEMPLATES)
        self._register_templates(GENERAL_QUESTION_TEMPLATES)

        # Register custom templates
        if custom_templates:
            self._register_templates(custom_templates)

    def _register_templates(self, templates: List[QuestionTemplate]) -> None:
        """Register question templates."""
        for template in templates:
            if template.field_name not in self._templates:
                self._templates[template.field_name] = []
            self._templates[template.field_name].append(template)

    def generate(
        self,
        intent_category: ITIntentCategory,
        missing_fields: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[GeneratedQuestion]:
        """
        Generate questions for missing fields.

        Args:
            intent_category: Current intent category
            missing_fields: List of missing field names
            context: Additional context for question selection

        Returns:
            List of GeneratedQuestion objects, sorted by priority
        """
        questions: List[GeneratedQuestion] = []

        for field_name in missing_fields:
            template = self._get_best_template(field_name, intent_category)
            if template:
                question = GeneratedQuestion(
                    question=template.question,
                    target_field=template.field_name,
                    priority=template.priority,
                    context={
                        "examples": template.examples,
                        "follow_up": template.follow_up,
                    },
                )
                questions.append(question)

        # Sort by priority (descending) and limit
        questions.sort(key=lambda q: q.priority, reverse=True)
        return questions[:self._max_questions]

    def _get_best_template(
        self,
        field_name: str,
        intent_category: ITIntentCategory,
    ) -> Optional[QuestionTemplate]:
        """
        Get the best template for a field.

        Prefers category-specific templates over general ones.

        Args:
            field_name: Field name to get template for
            intent_category: Current intent category

        Returns:
            Best matching QuestionTemplate or None
        """
        templates = self._templates.get(field_name, [])
        if not templates:
            return None

        # Find category-specific template first
        for template in templates:
            if template.category == intent_category:
                return template

        # Fall back to general template (category is None)
        for template in templates:
            if template.category is None:
                return template

        # Return first available
        return templates[0]

    def generate_for_intent(
        self,
        intent_category: ITIntentCategory,
        collected_fields: Optional[List[str]] = None,
    ) -> List[GeneratedQuestion]:
        """
        Generate all relevant questions for an intent category.

        Args:
            intent_category: Intent category
            collected_fields: Fields already collected (to exclude)

        Returns:
            List of relevant GeneratedQuestion objects
        """
        collected = set(collected_fields or [])

        # Get all templates for this category
        templates_for_category = [
            t for templates in self._templates.values()
            for t in templates
            if (t.category == intent_category or t.category is None)
            and t.field_name not in collected
        ]

        questions = [
            GeneratedQuestion(
                question=t.question,
                target_field=t.field_name,
                priority=t.priority,
                context={"examples": t.examples},
            )
            for t in templates_for_category
        ]

        questions.sort(key=lambda q: q.priority, reverse=True)
        return questions

    def get_question_text(
        self,
        field_name: str,
        intent_category: Optional[ITIntentCategory] = None,
    ) -> Optional[str]:
        """
        Get question text for a specific field.

        Args:
            field_name: Field name
            intent_category: Optional intent category for better matching

        Returns:
            Question text or None if not found
        """
        template = self._get_best_template(
            field_name,
            intent_category or ITIntentCategory.UNKNOWN,
        )
        return template.question if template else None

    def format_questions_as_text(
        self,
        questions: List[GeneratedQuestion],
        include_examples: bool = False,
    ) -> str:
        """
        Format questions as a single text block.

        Args:
            questions: List of questions to format
            include_examples: Whether to include example answers

        Returns:
            Formatted text with all questions
        """
        lines = []
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q.question}")
            if include_examples and q.context.get("examples"):
                examples = "、".join(q.context["examples"][:3])
                lines.append(f"   (例如：{examples})")

        return "\n".join(lines)

    def add_template(self, template: QuestionTemplate) -> None:
        """
        Add a new question template.

        Args:
            template: QuestionTemplate to add
        """
        if template.field_name not in self._templates:
            self._templates[template.field_name] = []
        self._templates[template.field_name].append(template)

    def get_all_templates(self) -> Dict[str, List[QuestionTemplate]]:
        """Get all registered templates."""
        return self._templates.copy()


class MockQuestionGenerator(QuestionGenerator):
    """
    Mock question generator for testing.

    Returns fixed questions regardless of input.
    """

    def __init__(self, **kwargs):
        """Initialize mock generator."""
        super().__init__(**kwargs)
        self._mock_questions = [
            GeneratedQuestion(
                question="請提供更多資訊",
                target_field="details",
                priority=100,
            ),
        ]

    def generate(
        self,
        intent_category: ITIntentCategory,
        missing_fields: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[GeneratedQuestion]:
        """Return fixed mock questions."""
        if not missing_fields:
            return []
        return self._mock_questions[:len(missing_fields)]


# =============================================================================
# Factory Functions
# =============================================================================

def create_question_generator(
    custom_templates: Optional[List[QuestionTemplate]] = None,
    max_questions: int = 3,
) -> QuestionGenerator:
    """
    Factory function to create a QuestionGenerator.

    Args:
        custom_templates: Additional templates to include
        max_questions: Maximum questions per generation

    Returns:
        QuestionGenerator instance
    """
    return QuestionGenerator(
        custom_templates=custom_templates,
        max_questions=max_questions,
    )


def create_mock_generator() -> MockQuestionGenerator:
    """
    Factory function to create a mock generator for testing.

    Returns:
        MockQuestionGenerator instance
    """
    return MockQuestionGenerator()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "QuestionTemplate",
    "GeneratedQuestion",
    "QuestionGenerator",
    "MockQuestionGenerator",
    # Template collections
    "INCIDENT_QUESTION_TEMPLATES",
    "REQUEST_QUESTION_TEMPLATES",
    "CHANGE_QUESTION_TEMPLATES",
    "QUERY_QUESTION_TEMPLATES",
    "GENERAL_QUESTION_TEMPLATES",
    # Factory functions
    "create_question_generator",
    "create_mock_generator",
]
