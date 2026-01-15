"""
Guided Dialog Module

Provides guided dialog functionality for multi-turn information gathering.
Key feature: Incremental updates without LLM re-classification.

Sprint 94: GuidedDialogEngine + Incremental Update (Phase 28)

Components:
- GuidedDialogEngine: Main orchestration engine
- ConversationContextManager: Context tracking with incremental updates
- QuestionGenerator: Template-based question generation
- RefinementRules: Sub-intent refinement rules

Example:
    >>> from orchestration.guided_dialog import (
    ...     GuidedDialogEngine,
    ...     create_guided_dialog_engine,
    ... )
    >>> from orchestration.intent_router import create_router
    >>>
    >>> router = create_router(pattern_rules_path="rules.yaml")
    >>> engine = create_guided_dialog_engine(router)
    >>>
    >>> response = await engine.start_dialog("ETL 今天報錯了")
    >>> # Returns questions if more info needed
    >>>
    >>> response = await engine.process_response("是 Pipeline 報錯")
    >>> # Incrementally updates context, refines sub_intent via rules
"""

# Engine
from .engine import (
    DialogResponse,
    DialogState,
    GuidedDialogEngine,
    MockGuidedDialogEngine,
    create_guided_dialog_engine,
    create_mock_dialog_engine,
)

# Context Manager
from .context_manager import (
    ContextState,
    ConversationContextManager,
    DialogTurn,
    MockConversationContextManager,
    create_context_manager,
    create_mock_context_manager,
)

# Question Generator
from .generator import (
    GeneratedQuestion,
    MockQuestionGenerator,
    QuestionGenerator,
    QuestionTemplate,
    create_mock_generator,
    create_question_generator,
)

# Refinement Rules
from .refinement_rules import (
    CHANGE_REFINEMENT_RULES,
    INCIDENT_REFINEMENT_RULES,
    REQUEST_REFINEMENT_RULES,
    RefinementCondition,
    RefinementRule,
    RefinementRules,
    create_refinement_rule,
    get_default_refinement_rules,
)

__all__ = [
    # Engine
    "DialogState",
    "DialogResponse",
    "GuidedDialogEngine",
    "MockGuidedDialogEngine",
    "create_guided_dialog_engine",
    "create_mock_dialog_engine",
    # Context Manager
    "DialogTurn",
    "ContextState",
    "ConversationContextManager",
    "MockConversationContextManager",
    "create_context_manager",
    "create_mock_context_manager",
    # Question Generator
    "QuestionTemplate",
    "GeneratedQuestion",
    "QuestionGenerator",
    "MockQuestionGenerator",
    "create_question_generator",
    "create_mock_generator",
    # Refinement Rules
    "RefinementCondition",
    "RefinementRule",
    "RefinementRules",
    "INCIDENT_REFINEMENT_RULES",
    "REQUEST_REFINEMENT_RULES",
    "CHANGE_REFINEMENT_RULES",
    "get_default_refinement_rules",
    "create_refinement_rule",
]
