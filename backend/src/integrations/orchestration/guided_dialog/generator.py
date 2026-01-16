"""
Question Generator Implementation

Generates follow-up questions based on missing fields.
Supports both template-based and LLM-based generation.

Sprint 94: Story 94-4 - Implement QuestionGenerator (Phase 28)
Sprint 97: Story 97-4 - Implement LLM QuestionGenerator (Phase 28)
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

from ..intent_router.models import ITIntentCategory

logger = logging.getLogger(__name__)


# =============================================================================
# LLM Client Protocol
# =============================================================================


class LLMClient(Protocol):
    """Protocol for LLM client implementations."""

    async def create_message(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Create a message with the LLM."""
        ...


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
# LLM Question Generator
# =============================================================================


# LLM Prompt Template for question generation
QUESTION_GENERATION_PROMPT = """你是一個 IT 服務助手。根據以下資訊，生成適當的澄清問題。

## 意圖類別
{intent_category}

## 子意圖
{sub_intent}

## 缺失欄位
{missing_fields}

## 已知資訊
{collected_info}

## 要求
1. 生成 1-3 個問題
2. 問題要具體、易懂
3. 提供可選答案（如適用）
4. 使用繁體中文
5. 問題要針對缺失的欄位

## 輸出格式 (嚴格 JSON)
{{
  "questions": [
    {{
      "field": "欄位名稱",
      "question": "問題內容",
      "options": ["選項1", "選項2"]
    }}
  ]
}}

只輸出 JSON，不要其他文字。"""


@dataclass
class LLMQuestionConfig:
    """
    Configuration for LLM question generation.

    Attributes:
        model: LLM model to use (default: claude-3-haiku)
        max_tokens: Maximum tokens for response
        temperature: Generation temperature
        timeout_ms: Maximum generation time in milliseconds
        max_questions: Maximum questions to generate
        fallback_to_templates: Whether to fallback to templates on failure
    """

    model: str = "claude-3-haiku-20240307"
    max_tokens: int = 500
    temperature: float = 0.3
    timeout_ms: int = 2000
    max_questions: int = 3
    fallback_to_templates: bool = True


class LLMQuestionGenerator:
    """
    LLM-based question generator.

    Uses Claude to generate contextually relevant follow-up questions
    when template-based generation is insufficient.

    Features:
    - Dynamic question generation based on context
    - Option suggestions for closed questions
    - Fallback to template-based generation
    - Latency control (< 2000ms target)

    Example:
        >>> from anthropic import AsyncAnthropic
        >>> client = AsyncAnthropic()
        >>> generator = LLMQuestionGenerator(client)
        >>> questions = await generator.generate(
        ...     intent_category=ITIntentCategory.INCIDENT,
        ...     missing_fields=["affected_system", "symptom_type"],
        ...     collected_info={"urgency": "high"},
        ... )
        >>> for q in questions:
        ...     print(q.question)
    """

    def __init__(
        self,
        client: Any,  # AsyncAnthropic or compatible client
        config: Optional[LLMQuestionConfig] = None,
        template_generator: Optional[QuestionGenerator] = None,
    ):
        """
        Initialize LLM question generator.

        Args:
            client: Anthropic async client or compatible
            config: Optional configuration
            template_generator: Optional template generator for fallback
        """
        self.client = client
        self.config = config or LLMQuestionConfig()
        self.template_generator = template_generator or QuestionGenerator()

        # Metrics
        self._total_calls = 0
        self._total_latency_ms = 0
        self._fallback_count = 0

    async def generate(
        self,
        intent_category: ITIntentCategory,
        missing_fields: List[str],
        collected_info: Optional[Dict[str, Any]] = None,
        sub_intent: Optional[str] = None,
    ) -> List[GeneratedQuestion]:
        """
        Generate questions using LLM.

        Args:
            intent_category: Current intent category
            missing_fields: List of missing field names
            collected_info: Information already collected
            sub_intent: Optional sub-intent for context

        Returns:
            List of GeneratedQuestion objects
        """
        if not missing_fields:
            return []

        start_time = time.time()

        try:
            # Build prompt
            prompt = self._build_prompt(
                intent_category=intent_category,
                missing_fields=missing_fields,
                collected_info=collected_info or {},
                sub_intent=sub_intent,
            )

            # Call LLM with timeout
            response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=self.config.timeout_ms / 1000,
            )

            # Parse response
            questions = self._parse_response(response, missing_fields)

            # Update metrics
            latency_ms = (time.time() - start_time) * 1000
            self._total_calls += 1
            self._total_latency_ms += latency_ms

            logger.debug(
                f"LLM question generation: {len(questions)} questions "
                f"in {latency_ms:.0f}ms"
            )

            return questions[:self.config.max_questions]

        except asyncio.TimeoutError:
            logger.warning("LLM question generation timeout, falling back to templates")
            self._fallback_count += 1
            return self._fallback_to_templates(intent_category, missing_fields)

        except Exception as e:
            logger.error(f"LLM question generation error: {e}")
            self._fallback_count += 1
            if self.config.fallback_to_templates:
                return self._fallback_to_templates(intent_category, missing_fields)
            return []

    async def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM API.

        Args:
            prompt: The prompt to send

        Returns:
            LLM response text
        """
        # For Anthropic client
        if hasattr(self.client, "messages"):
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        # For generic client with create_message method
        elif hasattr(self.client, "create_message"):
            response = await self.client.create_message(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.get("content", "")
        else:
            raise ValueError("Unsupported LLM client type")

    def _build_prompt(
        self,
        intent_category: ITIntentCategory,
        missing_fields: List[str],
        collected_info: Dict[str, Any],
        sub_intent: Optional[str],
    ) -> str:
        """Build the prompt for LLM."""
        # Format missing fields
        missing_str = "\n".join(f"- {field}" for field in missing_fields)

        # Format collected info
        if collected_info:
            info_str = "\n".join(
                f"- {k}: {v}" for k, v in collected_info.items()
            )
        else:
            info_str = "無"

        return QUESTION_GENERATION_PROMPT.format(
            intent_category=intent_category.value,
            sub_intent=sub_intent or "一般",
            missing_fields=missing_str,
            collected_info=info_str,
        )

    def _parse_response(
        self,
        response: str,
        missing_fields: List[str],
    ) -> List[GeneratedQuestion]:
        """
        Parse LLM response into GeneratedQuestion objects.

        Args:
            response: LLM response text
            missing_fields: Expected fields for validation

        Returns:
            List of GeneratedQuestion objects
        """
        questions = []

        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return []

            data = json.loads(json_match.group())
            question_list = data.get("questions", [])

            for q_data in question_list:
                field = q_data.get("field", "")
                question_text = q_data.get("question", "")
                options = q_data.get("options", [])

                if not question_text:
                    continue

                # Determine priority based on field position in missing_fields
                try:
                    priority = 100 - (missing_fields.index(field) * 10)
                except ValueError:
                    priority = 50

                questions.append(
                    GeneratedQuestion(
                        question=question_text,
                        target_field=field,
                        priority=priority,
                        context={
                            "options": options,
                            "source": "llm",
                        },
                    )
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return []

        return questions

    def _fallback_to_templates(
        self,
        intent_category: ITIntentCategory,
        missing_fields: List[str],
    ) -> List[GeneratedQuestion]:
        """Fallback to template-based generation."""
        return self.template_generator.generate(
            intent_category=intent_category,
            missing_fields=missing_fields,
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get generation metrics."""
        avg_latency = (
            self._total_latency_ms / self._total_calls
            if self._total_calls > 0 else 0
        )
        return {
            "total_calls": self._total_calls,
            "total_latency_ms": self._total_latency_ms,
            "average_latency_ms": avg_latency,
            "fallback_count": self._fallback_count,
            "fallback_rate": (
                self._fallback_count / self._total_calls
                if self._total_calls > 0 else 0
            ),
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._total_calls = 0
        self._total_latency_ms = 0
        self._fallback_count = 0


# =============================================================================
# Hybrid Question Generator
# =============================================================================


class HybridQuestionGenerator:
    """
    Hybrid question generator combining templates and LLM.

    Strategy:
    1. First try template-based generation for known fields
    2. Use LLM for fields without templates
    3. Optional: Always use LLM for better contextual questions

    Attributes:
        template_generator: Template-based generator
        llm_generator: LLM-based generator
        prefer_llm: Whether to prefer LLM over templates
    """

    def __init__(
        self,
        template_generator: Optional[QuestionGenerator] = None,
        llm_generator: Optional[LLMQuestionGenerator] = None,
        prefer_llm: bool = False,
    ):
        """
        Initialize hybrid generator.

        Args:
            template_generator: Template generator (created if None)
            llm_generator: LLM generator (optional)
            prefer_llm: Whether to prefer LLM for all questions
        """
        self.template_generator = template_generator or QuestionGenerator()
        self.llm_generator = llm_generator
        self.prefer_llm = prefer_llm

    async def generate(
        self,
        intent_category: ITIntentCategory,
        missing_fields: List[str],
        collected_info: Optional[Dict[str, Any]] = None,
        sub_intent: Optional[str] = None,
    ) -> List[GeneratedQuestion]:
        """
        Generate questions using hybrid approach.

        Args:
            intent_category: Current intent category
            missing_fields: List of missing field names
            collected_info: Information already collected
            sub_intent: Optional sub-intent for context

        Returns:
            List of GeneratedQuestion objects
        """
        if not missing_fields:
            return []

        # If LLM is preferred and available, use it
        if self.prefer_llm and self.llm_generator:
            return await self.llm_generator.generate(
                intent_category=intent_category,
                missing_fields=missing_fields,
                collected_info=collected_info,
                sub_intent=sub_intent,
            )

        # Try template generation first
        template_questions = self.template_generator.generate(
            intent_category=intent_category,
            missing_fields=missing_fields,
        )

        # Find fields not covered by templates
        covered_fields = {q.target_field for q in template_questions}
        uncovered_fields = [f for f in missing_fields if f not in covered_fields]

        # If all fields covered, return template questions
        if not uncovered_fields or not self.llm_generator:
            return template_questions

        # Use LLM for uncovered fields
        llm_questions = await self.llm_generator.generate(
            intent_category=intent_category,
            missing_fields=uncovered_fields,
            collected_info=collected_info,
            sub_intent=sub_intent,
        )

        # Combine and sort by priority
        all_questions = template_questions + llm_questions
        all_questions.sort(key=lambda q: q.priority, reverse=True)

        return all_questions[:3]  # Limit to 3 questions


# =============================================================================
# Mock LLM Client
# =============================================================================


class MockLLMClient:
    """
    Mock LLM client for testing.

    Returns predefined responses without actual API calls.
    """

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize mock client.

        Args:
            responses: Map of prompts to responses
        """
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None

    async def messages_create(self, **kwargs) -> Dict[str, Any]:
        """Mock messages.create method."""
        self.call_count += 1
        self.last_prompt = kwargs.get("messages", [{}])[0].get("content", "")

        # Return a mock response
        response_text = self.responses.get(
            "default",
            '{"questions": [{"field": "affected_system", "question": "請問是哪個系統有問題？", "options": ["ETL", "CRM", "API"]}]}',
        )

        # Create a mock response object
        class MockContent:
            def __init__(self, text):
                self.text = text

        class MockResponse:
            def __init__(self, text):
                self.content = [MockContent(text)]

        return MockResponse(response_text)

    @property
    def messages(self):
        """Return self for messages.create() pattern."""
        return self

    async def create(self, **kwargs) -> Dict[str, Any]:
        """Mock create method."""
        return await self.messages_create(**kwargs)


# =============================================================================
# Factory Functions (Extended)
# =============================================================================


def create_llm_question_generator(
    client: Any,
    config: Optional[LLMQuestionConfig] = None,
) -> LLMQuestionGenerator:
    """
    Factory function to create an LLM question generator.

    Args:
        client: Anthropic async client or compatible
        config: Optional configuration

    Returns:
        LLMQuestionGenerator instance
    """
    return LLMQuestionGenerator(client=client, config=config)


def create_hybrid_question_generator(
    llm_client: Optional[Any] = None,
    prefer_llm: bool = False,
) -> HybridQuestionGenerator:
    """
    Factory function to create a hybrid question generator.

    Args:
        llm_client: Optional LLM client for LLM-based generation
        prefer_llm: Whether to prefer LLM over templates

    Returns:
        HybridQuestionGenerator instance
    """
    template_generator = QuestionGenerator()
    llm_generator = None

    if llm_client:
        llm_generator = LLMQuestionGenerator(
            client=llm_client,
            template_generator=template_generator,
        )

    return HybridQuestionGenerator(
        template_generator=template_generator,
        llm_generator=llm_generator,
        prefer_llm=prefer_llm,
    )


def create_mock_llm_generator() -> LLMQuestionGenerator:
    """
    Factory function to create a mock LLM generator for testing.

    Returns:
        LLMQuestionGenerator with mock client
    """
    mock_client = MockLLMClient()
    return LLMQuestionGenerator(client=mock_client)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Data classes
    "QuestionTemplate",
    "GeneratedQuestion",
    "LLMQuestionConfig",
    # Generators
    "QuestionGenerator",
    "MockQuestionGenerator",
    "LLMQuestionGenerator",
    "HybridQuestionGenerator",
    # Protocol
    "LLMClient",
    # Mock
    "MockLLMClient",
    # Template collections
    "INCIDENT_QUESTION_TEMPLATES",
    "REQUEST_QUESTION_TEMPLATES",
    "CHANGE_QUESTION_TEMPLATES",
    "QUERY_QUESTION_TEMPLATES",
    "GENERAL_QUESTION_TEMPLATES",
    # Prompt
    "QUESTION_GENERATION_PROMPT",
    # Factory functions
    "create_question_generator",
    "create_mock_generator",
    "create_llm_question_generator",
    "create_hybrid_question_generator",
    "create_mock_llm_generator",
]
