"""
Orchestration Mock Classes for Testing

Consolidated from backend/src/integrations/orchestration/ production code.
Sprint 112: S112-3 - Mock Separation

These mock classes provide deterministic test implementations of orchestration
components without requiring external dependencies (LLM APIs, vector databases, etc.).
"""

import time
import json
import logging
from typing import Any, Dict, List, Optional

from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    CompletenessInfo,
    RoutingDecision,
    RiskLevel,
    WorkflowType,
)
from src.integrations.orchestration.intent_router.pattern_matcher.matcher import PatternMatcher
from src.integrations.orchestration.intent_router.router import (
    BusinessIntentRouter,
    RouterConfig,
)
from src.integrations.orchestration.intent_router.semantic_router.router import (
    SemanticRouter,
    SemanticRoute,
    SemanticRouteResult,
)
from src.integrations.orchestration.intent_router.llm_classifier.classifier import (
    LLMClassifier,
    LLMClassificationResult,
)
from src.integrations.orchestration.intent_router.completeness.checker import (
    CompletenessChecker,
)
from src.integrations.orchestration.guided_dialog.engine import (
    GuidedDialogEngine,
)
from src.integrations.orchestration.guided_dialog.context_manager import (
    ConversationContextManager,
)
from src.integrations.orchestration.guided_dialog.generator import (
    QuestionGenerator,
    GeneratedQuestion,
    LLMQuestionGenerator,
)
from src.integrations.orchestration.input_gateway.gateway import (
    InputGateway,
    GatewayConfig,
)
from src.integrations.orchestration.input_gateway.models import (
    IncomingRequest,
    SourceType,
)
from src.integrations.orchestration.input_gateway.schema_validator import (
    SchemaValidator,
)
from src.integrations.orchestration.input_gateway.source_handlers.base_handler import (
    BaseSourceHandler,
)
from src.integrations.orchestration.input_gateway.source_handlers.servicenow_handler import (
    ServiceNowHandler,
)
from src.integrations.orchestration.input_gateway.source_handlers.prometheus_handler import (
    PrometheusHandler,
)
from src.integrations.orchestration.input_gateway.source_handlers.user_input_handler import (
    UserInputHandler,
)
from src.integrations.orchestration.hitl.controller import (
    HITLController,
    ApprovalRequest,
    ApprovalStatus,
    InMemoryApprovalStorage,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Mock Classes
# =============================================================================


class MockSemanticRouter(SemanticRouter):
    """Mock Semantic Router for testing without external dependencies."""

    def __init__(
        self,
        routes: Optional[List[SemanticRoute]] = None,
        threshold: float = 0.85,
        **kwargs,
    ):
        super().__init__(routes=routes, threshold=threshold, **kwargs)
        self._initialized = True

    @property
    def is_available(self) -> bool:
        return True

    async def route(self, user_input: str) -> SemanticRouteResult:
        user_input_lower = user_input.lower()

        best_match: Optional[SemanticRoute] = None
        best_score = 0.0

        for route in self.routes:
            if not route.enabled:
                continue

            match_score = 0.0
            max_utterance_score = 0.0

            for utterance in route.utterances:
                utterance_lower = utterance.lower()

                common_chars = 0
                for char in utterance_lower:
                    if char in user_input_lower and char not in " \t\n":
                        common_chars += 1

                if len(utterance_lower) > 0:
                    char_coverage = common_chars / len(utterance_lower.replace(" ", ""))

                    substring_bonus = 0.0
                    if utterance_lower in user_input_lower:
                        substring_bonus = 0.3
                    elif user_input_lower in utterance_lower:
                        substring_bonus = 0.2

                    utterance_score = min(char_coverage + substring_bonus, 1.0)
                    max_utterance_score = max(max_utterance_score, utterance_score)

            match_score = max_utterance_score

            if match_score > best_score:
                best_score = match_score
                best_match = route

        if best_score < self.threshold or best_match is None:
            return SemanticRouteResult.no_match(similarity=best_score)

        return SemanticRouteResult(
            matched=True,
            intent_category=best_match.category,
            sub_intent=best_match.sub_intent,
            similarity=best_score,
            route_name=best_match.name,
            metadata={
                "workflow_type": best_match.workflow_type.value,
                "risk_level": best_match.risk_level.value,
                "mock": True,
            },
        )


class MockLLMClassifier(LLMClassifier):
    """Mock LLM Classifier for testing without API calls."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def is_available(self) -> bool:
        return True

    async def classify(
        self,
        user_input: str,
        include_completeness: bool = True,
        simplified: bool = False,
    ) -> LLMClassificationResult:
        start_time = time.perf_counter()
        text_lower = user_input.lower()

        intent_category = ITIntentCategory.UNKNOWN
        sub_intent = None
        confidence = 0.7
        reasoning = "Mock classification based on keywords"

        if any(kw in text_lower for kw in ["etl", "失敗", "錯誤", "故障", "掛", "問題", "慢"]):
            intent_category = ITIntentCategory.INCIDENT
            if "etl" in text_lower:
                sub_intent = "etl_failure"
            elif "慢" in text_lower or "效能" in text_lower:
                sub_intent = "performance_degradation"
            elif "網路" in text_lower:
                sub_intent = "network_issue"
            else:
                sub_intent = "general_incident"
            confidence = 0.85

        elif any(kw in text_lower for kw in ["申請", "帳號", "權限", "安裝", "密碼"]):
            intent_category = ITIntentCategory.REQUEST
            if "帳號" in text_lower:
                sub_intent = "account_creation"
            elif "權限" in text_lower:
                sub_intent = "permission_change"
            elif "安裝" in text_lower:
                sub_intent = "software_installation"
            elif "密碼" in text_lower:
                sub_intent = "password_reset"
            else:
                sub_intent = "general_request"
            confidence = 0.85

        elif any(kw in text_lower for kw in ["部署", "變更", "更新", "config", "設定"]):
            intent_category = ITIntentCategory.CHANGE
            if "部署" in text_lower:
                sub_intent = "release_deployment"
            elif "設定" in text_lower or "config" in text_lower:
                sub_intent = "configuration_update"
            else:
                sub_intent = "general_change"
            confidence = 0.80

        elif any(kw in text_lower for kw in ["查詢", "狀態", "報表", "進度", "如何"]):
            intent_category = ITIntentCategory.QUERY
            if "狀態" in text_lower:
                sub_intent = "status_inquiry"
            elif "報表" in text_lower:
                sub_intent = "report_request"
            elif "進度" in text_lower:
                sub_intent = "ticket_status"
            else:
                sub_intent = "general_query"
            confidence = 0.75

        completeness = CompletenessInfo(
            is_complete=len(user_input) > 20,
            completeness_score=min(len(user_input) / 50, 1.0),
            missing_fields=[] if len(user_input) > 20 else ["詳細描述"],
            suggestions=[] if len(user_input) > 20 else ["請提供更多細節"],
        )

        processing_time = (time.perf_counter() - start_time) * 1000

        return LLMClassificationResult(
            intent_category=intent_category,
            sub_intent=sub_intent,
            confidence=confidence,
            completeness=completeness,
            reasoning=reasoning,
            raw_response=f"Mock response for: {user_input[:50]}...",
            model="mock-classifier",
            usage={"mock": True, "processing_time_ms": processing_time},
        )

    async def health_check(self) -> bool:
        return True


class MockCompletenessChecker(CompletenessChecker):
    """Mock completeness checker for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def check(
        self,
        intent_category: ITIntentCategory,
        user_input: str,
        collected_info: Optional[Dict[str, Any]] = None,
    ) -> CompletenessInfo:
        input_length = len(user_input)

        if input_length >= 50:
            score = 1.0
            is_complete = True
            missing = []
        elif input_length >= 30:
            score = 0.8
            is_complete = True
            missing = []
        elif input_length >= 15:
            score = 0.6
            is_complete = True
            missing = ["additional_details"]
        else:
            score = 0.3
            is_complete = False
            missing = ["description", "context"]

        return CompletenessInfo(
            is_complete=is_complete,
            completeness_score=score,
            missing_fields=missing,
            optional_missing=[],
            suggestions=[f"請提供更多詳細資訊"] if not is_complete else [],
        )


class MockBusinessIntentRouter(BusinessIntentRouter):
    """Mock BusinessIntentRouter for testing without external dependencies."""

    def __init__(
        self,
        pattern_rules: Optional[Dict[str, Any]] = None,
        semantic_routes: Optional[List[Any]] = None,
        config: Optional[RouterConfig] = None,
    ):
        pattern_matcher = PatternMatcher(rules_dict=pattern_rules or {"rules": []})
        semantic_router = MockSemanticRouter(routes=semantic_routes or [])
        llm_classifier = MockLLMClassifier()
        completeness_checker = MockCompletenessChecker()

        super().__init__(
            pattern_matcher=pattern_matcher,
            semantic_router=semantic_router,
            llm_classifier=llm_classifier,
            completeness_checker=completeness_checker,
            config=config or RouterConfig(),
        )


class MockQuestionGenerator(QuestionGenerator):
    """Mock question generator for testing."""

    def __init__(self, **kwargs):
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


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None

    async def messages_create(self, **kwargs) -> Any:
        self.call_count += 1
        self.last_prompt = kwargs.get("messages", [{}])[0].get("content", "")

        response_text = self.responses.get(
            "default",
            '{"questions": [{"field": "affected_system", "question": "請問是哪個系統有問題？", "options": ["ETL", "CRM", "API"]}]}',
        )

        class MockContent:
            def __init__(self, text):
                self.text = text

        class MockResponse:
            def __init__(self, text):
                self.content = [MockContent(text)]

        return MockResponse(response_text)

    @property
    def messages(self):
        return self

    async def create(self, **kwargs) -> Any:
        return await self.messages_create(**kwargs)


class MockConversationContextManager(ConversationContextManager):
    """Mock context manager for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mock_completeness_score = 0.5

    def update_with_user_response(
        self,
        user_response: str,
    ) -> RoutingDecision:
        """Mock update with deterministic behavior."""
        if not self._initialized or not self._routing_decision:
            raise RuntimeError("Context not initialized")

        response_length = len(user_response)

        if response_length >= 30:
            self._mock_completeness_score = min(1.0, self._mock_completeness_score + 0.3)
        elif response_length >= 15:
            self._mock_completeness_score = min(1.0, self._mock_completeness_score + 0.2)
        else:
            self._mock_completeness_score = min(1.0, self._mock_completeness_score + 0.1)

        self._routing_decision.completeness = CompletenessInfo(
            is_complete=self._mock_completeness_score >= 0.6,
            completeness_score=self._mock_completeness_score,
            missing_fields=[] if self._mock_completeness_score >= 0.6 else ["details"],
        )

        if "ETL" in user_response.upper() or "etl" in user_response:
            self._routing_decision.sub_intent = "etl_failure"
        elif "網路" in user_response or "network" in user_response.lower():
            self._routing_decision.sub_intent = "network_failure"

        return self._routing_decision


class MockGuidedDialogEngine(GuidedDialogEngine):
    """Mock guided dialog engine for testing."""

    def __init__(
        self,
        max_turns: int = 5,
    ):
        router = MockBusinessIntentRouter()
        context_manager = MockConversationContextManager()
        question_generator = MockQuestionGenerator()

        super().__init__(
            router=router,
            context_manager=context_manager,
            question_generator=question_generator,
            max_turns=max_turns,
        )


class MockSchemaValidator(SchemaValidator):
    """Mock schema validator for testing."""

    def __init__(self):
        super().__init__(strict_mode=False, allow_extra_fields=True)

    def validate(
        self,
        data: Dict[str, Any],
        schema: str,
    ) -> Dict[str, Any]:
        """Always return data without validation."""
        return data


class MockBaseHandler(BaseSourceHandler):
    """Mock base handler for testing."""

    def __init__(
        self,
        handler_type_name: str = "mock",
        default_intent: str = "incident",
        default_sub_intent: str = "general",
    ):
        super().__init__(enable_metrics=False)
        self._handler_type = handler_type_name
        self._default_intent = default_intent
        self._default_sub_intent = default_sub_intent

    @property
    def handler_type(self) -> str:
        return self._handler_type

    async def process(self, request: IncomingRequest) -> RoutingDecision:
        start_time = time.perf_counter()

        intent_category = ITIntentCategory.from_string(self._default_intent)

        return self.build_routing_decision(
            intent_category=intent_category,
            sub_intent=self._default_sub_intent,
            confidence=0.95,
            layer_used=f"{self.handler_type}_mock",
            reasoning="Mock handler response",
            metadata=self.extract_metadata(request),
            processing_time_ms=(time.perf_counter() - start_time) * 1000,
        )


class MockServiceNowHandler(ServiceNowHandler):
    """Mock ServiceNow handler for testing."""

    def __init__(self):
        super().__init__(
            schema_validator=None,
            pattern_matcher=None,
            enable_metrics=False,
        )

    async def process(self, request: IncomingRequest) -> RoutingDecision:
        start_time = time.perf_counter()

        data = request.data
        category = data.get("category", "incident").lower()
        subcategory = data.get("subcategory", "").lower()

        mapping_key = f"{category}/{subcategory}"
        mapping = self.CATEGORY_MAPPING.get(mapping_key)

        if mapping:
            intent_str, sub_intent = mapping
            intent_category = ITIntentCategory.from_string(intent_str)
        else:
            intent_category = ITIntentCategory.INCIDENT
            sub_intent = "general_incident"

        latency_ms = (time.perf_counter() - start_time) * 1000

        return self.build_routing_decision(
            intent_category=intent_category,
            sub_intent=sub_intent,
            confidence=0.95,
            layer_used="servicenow_mock",
            reasoning="Mock ServiceNow handler response",
            metadata={
                "servicenow_number": data.get("number"),
                "servicenow_category": category,
            },
            processing_time_ms=latency_ms,
        )


class MockPrometheusHandler(PrometheusHandler):
    """Mock Prometheus handler for testing."""

    def __init__(self):
        super().__init__(
            schema_validator=None,
            enable_metrics=False,
        )

    async def process(self, request: IncomingRequest) -> RoutingDecision:
        start_time = time.perf_counter()

        data = request.data
        alerts = data.get("alerts", [])

        if alerts:
            alert = alerts[0]
            alertname = alert.get("alertname", "")
            intent_category, sub_intent, workflow_str = self._match_alert(alertname)
        else:
            intent_category = ITIntentCategory.INCIDENT
            sub_intent = "general_incident"

        latency_ms = (time.perf_counter() - start_time) * 1000

        return self.build_routing_decision(
            intent_category=intent_category,
            sub_intent=sub_intent,
            confidence=0.95,
            layer_used="prometheus_mock",
            reasoning="Mock Prometheus handler response",
            metadata={
                "alertname": alerts[0].get("alertname") if alerts else None,
                "alert_count": len(alerts),
            },
            processing_time_ms=latency_ms,
        )


class MockUserInputHandler(UserInputHandler):
    """Mock user input handler for testing."""

    def __init__(self):
        super().__init__(
            business_router=MockBusinessIntentRouter(),
            enable_metrics=False,
        )

    async def process(self, request: IncomingRequest) -> RoutingDecision:
        start_time = time.perf_counter()

        user_text = self._normalize_input(request)

        if not user_text:
            return self._build_empty_decision(start_time)

        decision = await self.business_router.route(user_text)

        latency_ms = (time.perf_counter() - start_time) * 1000

        decision.metadata["handler_type"] = "user_mock"
        decision.metadata["original_input_length"] = len(user_text)
        decision.processing_time_ms = latency_ms

        return decision


class MockInputGateway(InputGateway):
    """Mock InputGateway for testing without external dependencies."""

    def __init__(
        self,
        config: Optional[GatewayConfig] = None,
    ):
        source_handlers = {
            "servicenow": MockServiceNowHandler(),
            "prometheus": MockPrometheusHandler(),
            "user": MockUserInputHandler(),
        }

        super().__init__(
            source_handlers=source_handlers,
            business_router=MockBusinessIntentRouter(),
            config=config or GatewayConfig(),
        )


class MockNotificationService:
    """Mock notification service for testing."""

    def __init__(self) -> None:
        self.sent_requests: List[ApprovalRequest] = []
        self.sent_results: List[tuple[ApprovalRequest, bool]] = []

    async def send_approval_request(self, request: ApprovalRequest) -> bool:
        self.sent_requests.append(request)
        return True

    async def send_approval_result(
        self, request: ApprovalRequest, approved: bool
    ) -> bool:
        self.sent_results.append((request, approved))
        return True

    def clear(self) -> None:
        self.sent_requests.clear()
        self.sent_results.clear()


# =============================================================================
# Factory Functions
# =============================================================================


def create_mock_router(
    config: Optional[RouterConfig] = None,
) -> MockBusinessIntentRouter:
    """Factory function to create a mock router for testing."""
    return MockBusinessIntentRouter(config=config)


def create_mock_dialog_engine(
    max_turns: int = 5,
) -> MockGuidedDialogEngine:
    """Factory function to create a mock engine for testing."""
    return MockGuidedDialogEngine(max_turns=max_turns)


def create_mock_context_manager() -> MockConversationContextManager:
    """Factory function to create a mock context manager for testing."""
    return MockConversationContextManager()


def create_mock_generator() -> MockQuestionGenerator:
    """Factory function to create a mock generator for testing."""
    return MockQuestionGenerator()


def create_mock_llm_generator() -> LLMQuestionGenerator:
    """Factory function to create a mock LLM generator for testing."""
    mock_client = MockLLMClient()
    return LLMQuestionGenerator(client=mock_client)


def create_mock_checker() -> MockCompletenessChecker:
    """Factory function to create a mock checker for testing."""
    return MockCompletenessChecker()


def create_mock_gateway(
    config: Optional[GatewayConfig] = None,
) -> MockInputGateway:
    """Factory function to create a mock gateway for testing."""
    return MockInputGateway(config=config)


def create_mock_hitl_controller() -> tuple[HITLController, InMemoryApprovalStorage, MockNotificationService]:
    """Factory function to create a mock HITL controller for testing."""
    storage = InMemoryApprovalStorage()
    notification = MockNotificationService()
    controller = HITLController(
        storage=storage,
        notification_service=notification,
        default_timeout_minutes=30,
    )
    return controller, storage, notification


# =============================================================================
# Export List
# =============================================================================

__all__ = [
    # Mock Classes
    "MockSemanticRouter",
    "MockLLMClassifier",
    "MockCompletenessChecker",
    "MockBusinessIntentRouter",
    "MockQuestionGenerator",
    "MockLLMClient",
    "MockConversationContextManager",
    "MockGuidedDialogEngine",
    "MockSchemaValidator",
    "MockBaseHandler",
    "MockServiceNowHandler",
    "MockPrometheusHandler",
    "MockUserInputHandler",
    "MockInputGateway",
    "MockNotificationService",
    # Factory Functions
    "create_mock_router",
    "create_mock_dialog_engine",
    "create_mock_context_manager",
    "create_mock_generator",
    "create_mock_llm_generator",
    "create_mock_checker",
    "create_mock_gateway",
    "create_mock_hitl_controller",
]
