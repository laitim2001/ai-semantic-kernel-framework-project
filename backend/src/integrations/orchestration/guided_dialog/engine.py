"""
Guided Dialog Engine Implementation

Orchestrates multi-turn dialog for information gathering.
Integrates BusinessIntentRouter, ConversationContextManager, and QuestionGenerator.

Sprint 94: Story 94-1 - Implement GuidedDialogEngine Core (Phase 28)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    RoutingDecision,
    WorkflowType,
)
from ..intent_router.router import BusinessIntentRouter, MockBusinessIntentRouter
from .context_manager import (
    ConversationContextManager,
    ContextState,
    DialogTurn,
    MockConversationContextManager,
)
from .generator import (
    GeneratedQuestion,
    MockQuestionGenerator,
    QuestionGenerator,
)
from .refinement_rules import RefinementRules

logger = logging.getLogger(__name__)


@dataclass
class DialogState:
    """
    Current state of the guided dialog.

    Attributes:
        phase: Current dialog phase ("initial", "gathering", "complete", "handoff")
        routing_decision: Current routing decision
        questions: Generated questions (if any)
        is_complete: Whether information is complete
        turn_count: Number of dialog turns
        started_at: When dialog started
    """
    phase: str = "initial"
    routing_decision: Optional[RoutingDecision] = None
    questions: List[GeneratedQuestion] = field(default_factory=list)
    is_complete: bool = False
    turn_count: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "phase": self.phase,
            "routing_decision": (
                self.routing_decision.to_dict()
                if self.routing_decision else None
            ),
            "questions": [q.to_dict() for q in self.questions],
            "is_complete": self.is_complete,
            "turn_count": self.turn_count,
            "started_at": self.started_at.isoformat(),
        }


@dataclass
class DialogResponse:
    """
    Response from the guided dialog engine.

    Attributes:
        message: Response message to show user
        questions: Follow-up questions (if any)
        state: Current dialog state
        should_continue: Whether dialog should continue
        next_action: Recommended next action
    """
    message: str
    questions: List[GeneratedQuestion] = field(default_factory=list)
    state: Optional[DialogState] = None
    should_continue: bool = True
    next_action: str = "gather_info"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message": self.message,
            "questions": [q.to_dict() for q in self.questions],
            "state": self.state.to_dict() if self.state else None,
            "should_continue": self.should_continue,
            "next_action": self.next_action,
        }


class GuidedDialogEngine:
    """
    Guided dialog engine for multi-turn information gathering.

    Orchestrates:
    - BusinessIntentRouter: Initial intent classification
    - ConversationContextManager: Context tracking with incremental updates
    - QuestionGenerator: Follow-up question generation

    Key Features:
    - Incremental updates without LLM re-classification
    - Rule-based sub_intent refinement
    - Template-based question generation
    - Configurable completeness thresholds

    Example:
        >>> engine = GuidedDialogEngine(router, context_manager, generator)
        >>> # Initial classification
        >>> response = await engine.start_dialog("ETL 今天報錯了")
        >>> print(response.questions)  # [請問是哪個系統有問題？, ...]
        >>>
        >>> # Process user response (incremental update)
        >>> response = await engine.process_response("是 ETL Pipeline，跑到一半失敗")
        >>> print(response.state.routing_decision.sub_intent)  # "etl_failure"
    """

    def __init__(
        self,
        router: BusinessIntentRouter,
        context_manager: Optional[ConversationContextManager] = None,
        question_generator: Optional[QuestionGenerator] = None,
        max_turns: int = 5,
    ):
        """
        Initialize the guided dialog engine.

        Args:
            router: BusinessIntentRouter for initial classification
            context_manager: ConversationContextManager (optional)
            question_generator: QuestionGenerator (optional)
            max_turns: Maximum dialog turns before handoff (default: 5)
        """
        self.router = router
        self.context_manager = context_manager or ConversationContextManager()
        self.question_generator = question_generator or QuestionGenerator()
        self.max_turns = max_turns

        # State
        self._dialog_state: Optional[DialogState] = None
        self._active: bool = False

    @property
    def is_active(self) -> bool:
        """Check if dialog is currently active."""
        return self._active

    @property
    def current_state(self) -> Optional[DialogState]:
        """Get current dialog state."""
        return self._dialog_state

    async def start_dialog(self, user_input: str) -> DialogResponse:
        """
        Start a new guided dialog with initial user input.

        This method:
        1. Routes the initial input through BusinessIntentRouter
        2. Initializes conversation context
        3. Generates initial questions if needed

        Args:
            user_input: Initial user input

        Returns:
            DialogResponse with initial assessment and questions
        """
        # 1. Route initial input
        routing_decision = await self.router.route(user_input)

        # 2. Initialize dialog state
        self._dialog_state = DialogState(
            phase="initial",
            routing_decision=routing_decision,
        )

        # 3. Initialize context manager
        self.context_manager.initialize(routing_decision)

        logger.info(
            f"Dialog started: category={routing_decision.intent_category.value}, "
            f"completeness={routing_decision.completeness.completeness_score:.2f}"
        )

        # 4. Check if complete or needs more info
        return self._evaluate_and_respond(routing_decision)

    async def process_response(self, user_response: str) -> DialogResponse:
        """
        Process user response and update dialog state.

        This method:
        1. Updates context with incremental changes (NO LLM re-classification)
        2. Refines sub_intent based on rules
        3. Recalculates completeness
        4. Generates follow-up questions or completes dialog

        Args:
            user_response: User's response to previous questions

        Returns:
            DialogResponse with updated state and next steps

        Raises:
            RuntimeError: If dialog not started
        """
        if not self._active or not self._dialog_state:
            raise RuntimeError("Dialog not started. Call start_dialog() first.")

        # 1. Update context (incremental, no LLM)
        updated_decision = self.context_manager.update_with_user_response(
            user_response
        )

        # 2. Update dialog state
        self._dialog_state.routing_decision = updated_decision
        self._dialog_state.turn_count += 1

        logger.info(
            f"Dialog turn {self._dialog_state.turn_count}: "
            f"sub_intent={updated_decision.sub_intent}, "
            f"completeness={updated_decision.completeness.completeness_score:.2f}"
        )

        # 3. Check if max turns reached
        if self._dialog_state.turn_count >= self.max_turns:
            return self._complete_with_handoff(
                "已達最大對話次數，將轉交人工處理"
            )

        # 4. Evaluate and respond
        return self._evaluate_and_respond(updated_decision)

    def _evaluate_and_respond(
        self,
        routing_decision: RoutingDecision,
    ) -> DialogResponse:
        """
        Evaluate routing decision and generate appropriate response.

        Args:
            routing_decision: Current routing decision

        Returns:
            DialogResponse based on completeness
        """
        completeness = routing_decision.completeness
        intent_category = routing_decision.intent_category

        # Handle unknown intent
        if intent_category == ITIntentCategory.UNKNOWN:
            return self._handle_unknown_intent()

        # Check completeness
        if completeness.is_complete:
            return self._complete_dialog(routing_decision)

        # Generate questions for missing fields
        questions = self.question_generator.generate(
            intent_category=intent_category,
            missing_fields=completeness.missing_fields,
        )

        # Update state
        self._dialog_state.phase = "gathering"
        self._dialog_state.questions = questions
        self._active = True

        # Format response message
        message = self._format_gathering_message(
            routing_decision,
            questions,
        )

        return DialogResponse(
            message=message,
            questions=questions,
            state=self._dialog_state,
            should_continue=True,
            next_action="gather_info",
        )

    def _complete_dialog(
        self,
        routing_decision: RoutingDecision,
    ) -> DialogResponse:
        """
        Complete the dialog with sufficient information.

        Args:
            routing_decision: Final routing decision

        Returns:
            DialogResponse marking completion
        """
        self._dialog_state.phase = "complete"
        self._dialog_state.is_complete = True
        self._active = False

        # Format completion message
        message = self._format_completion_message(routing_decision)

        logger.info(
            f"Dialog completed: sub_intent={routing_decision.sub_intent}, "
            f"workflow={routing_decision.workflow_type.value}"
        )

        return DialogResponse(
            message=message,
            questions=[],
            state=self._dialog_state,
            should_continue=False,
            next_action=f"execute_{routing_decision.workflow_type.value}",
        )

    def _complete_with_handoff(self, reason: str) -> DialogResponse:
        """
        Complete dialog with handoff to human.

        Args:
            reason: Reason for handoff

        Returns:
            DialogResponse for handoff
        """
        self._dialog_state.phase = "handoff"
        self._dialog_state.is_complete = False
        self._active = False

        if self._dialog_state.routing_decision:
            self._dialog_state.routing_decision.workflow_type = WorkflowType.HANDOFF

        return DialogResponse(
            message=f"{reason}\n\n我們將會盡快有專人與您聯繫。",
            questions=[],
            state=self._dialog_state,
            should_continue=False,
            next_action="handoff",
        )

    def _handle_unknown_intent(self) -> DialogResponse:
        """
        Handle unknown intent classification.

        Returns:
            DialogResponse requesting clarification
        """
        self._dialog_state.phase = "clarification"
        self._active = True

        return DialogResponse(
            message=(
                "抱歉，我不太確定您的需求。"
                "請問您是遇到系統問題、需要申請服務、"
                "還是有其他問題呢？"
            ),
            questions=[
                GeneratedQuestion(
                    question="請更詳細地描述您的需求",
                    target_field="clarification",
                    priority=100,
                ),
            ],
            state=self._dialog_state,
            should_continue=True,
            next_action="clarify",
        )

    def _format_gathering_message(
        self,
        routing_decision: RoutingDecision,
        questions: List[GeneratedQuestion],
    ) -> str:
        """
        Format message for information gathering phase.

        Args:
            routing_decision: Current routing decision
            questions: Questions to ask

        Returns:
            Formatted message string
        """
        # Determine intent description
        intent_desc = {
            ITIntentCategory.INCIDENT: "事件報告",
            ITIntentCategory.REQUEST: "服務請求",
            ITIntentCategory.CHANGE: "變更請求",
            ITIntentCategory.QUERY: "查詢",
        }.get(routing_decision.intent_category, "請求")

        # Build message
        lines = [
            f"了解，這是一個{intent_desc}。",
            "為了更快地協助您，請回答以下問題：",
            "",
        ]

        # Add questions
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q.question}")

        return "\n".join(lines)

    def _format_completion_message(
        self,
        routing_decision: RoutingDecision,
    ) -> str:
        """
        Format message for dialog completion.

        Args:
            routing_decision: Final routing decision

        Returns:
            Formatted completion message
        """
        intent_desc = {
            ITIntentCategory.INCIDENT: "事件",
            ITIntentCategory.REQUEST: "請求",
            ITIntentCategory.CHANGE: "變更",
            ITIntentCategory.QUERY: "查詢",
        }.get(routing_decision.intent_category, "請求")

        sub_intent = routing_decision.sub_intent or "一般"

        lines = [
            f"感謝您提供的資訊。",
            f"",
            f"已收集完成，將進行{intent_desc}處理：",
            f"- 類型：{sub_intent}",
            f"- 處理方式：{routing_decision.workflow_type.value}",
        ]

        if routing_decision.risk_level:
            lines.append(f"- 風險等級：{routing_decision.risk_level.value}")

        return "\n".join(lines)

    def generate_questions(
        self,
        missing_fields: Optional[List[str]] = None,
    ) -> List[GeneratedQuestion]:
        """
        Generate questions for current state.

        Args:
            missing_fields: Specific fields to generate questions for
                           (optional, uses current missing fields if not provided)

        Returns:
            List of GeneratedQuestion objects
        """
        if not self._dialog_state or not self._dialog_state.routing_decision:
            return []

        routing_decision = self._dialog_state.routing_decision
        fields = missing_fields or routing_decision.completeness.missing_fields

        return self.question_generator.generate(
            intent_category=routing_decision.intent_category,
            missing_fields=fields,
        )

    def get_dialog_summary(self) -> Dict[str, Any]:
        """
        Get summary of current dialog.

        Returns:
            Dictionary with dialog summary
        """
        if not self._dialog_state:
            return {"status": "not_started"}

        return {
            "status": self._dialog_state.phase,
            "turn_count": self._dialog_state.turn_count,
            "is_complete": self._dialog_state.is_complete,
            "collected_fields": self.context_manager.get_collected_fields(),
            "missing_fields": self.context_manager.get_missing_fields(),
            "routing_decision": (
                self._dialog_state.routing_decision.to_dict()
                if self._dialog_state.routing_decision else None
            ),
        }

    def reset(self) -> None:
        """Reset dialog to initial state."""
        self._dialog_state = None
        self._active = False
        self.context_manager.reset()
        logger.info("Dialog reset")


class MockGuidedDialogEngine(GuidedDialogEngine):
    """
    Mock guided dialog engine for testing.

    Uses mock components for deterministic behavior.
    """

    def __init__(
        self,
        max_turns: int = 5,
    ):
        """
        Initialize mock engine with mock components.

        Args:
            max_turns: Maximum dialog turns
        """
        router = MockBusinessIntentRouter()
        context_manager = MockConversationContextManager()
        question_generator = MockQuestionGenerator()

        super().__init__(
            router=router,
            context_manager=context_manager,
            question_generator=question_generator,
            max_turns=max_turns,
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_guided_dialog_engine(
    router: BusinessIntentRouter,
    refinement_rules: Optional[RefinementRules] = None,
    max_turns: int = 5,
) -> GuidedDialogEngine:
    """
    Factory function to create a fully configured GuidedDialogEngine.

    Args:
        router: BusinessIntentRouter instance
        refinement_rules: Custom refinement rules (optional)
        max_turns: Maximum dialog turns

    Returns:
        Configured GuidedDialogEngine instance
    """
    context_manager = ConversationContextManager(
        refinement_rules=refinement_rules,
    )
    question_generator = QuestionGenerator()

    return GuidedDialogEngine(
        router=router,
        context_manager=context_manager,
        question_generator=question_generator,
        max_turns=max_turns,
    )


def create_mock_dialog_engine(
    max_turns: int = 5,
) -> MockGuidedDialogEngine:
    """
    Factory function to create a mock engine for testing.

    Args:
        max_turns: Maximum dialog turns

    Returns:
        MockGuidedDialogEngine instance
    """
    return MockGuidedDialogEngine(max_turns=max_turns)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "DialogState",
    "DialogResponse",
    "GuidedDialogEngine",
    "MockGuidedDialogEngine",
    "create_guided_dialog_engine",
    "create_mock_dialog_engine",
]
