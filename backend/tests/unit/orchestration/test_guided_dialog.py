"""
Unit Tests for Guided Dialog Module

Tests for GuidedDialogEngine, ConversationContextManager, QuestionGenerator,
and RefinementRules.

Sprint 94: Story 94-5 - Dialog Flow Unit Tests (Phase 28)
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List

from src.integrations.orchestration.intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    RiskLevel,
    RoutingDecision,
    WorkflowType,
)
from src.integrations.orchestration.guided_dialog import (
    ConversationContextManager,
    ContextState,
    DialogTurn,
    GeneratedQuestion,
    GuidedDialogEngine,
    MockConversationContextManager,
    MockGuidedDialogEngine,
    MockQuestionGenerator,
    QuestionGenerator,
    QuestionTemplate,
    RefinementCondition,
    RefinementRule,
    RefinementRules,
    create_context_manager,
    create_guided_dialog_engine,
    create_mock_context_manager,
    create_mock_dialog_engine,
    create_question_generator,
    get_default_refinement_rules,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_routing_decision() -> RoutingDecision:
    """Create a sample routing decision for testing."""
    return RoutingDecision(
        intent_category=ITIntentCategory.INCIDENT,
        sub_intent="general_incident",
        confidence=0.85,
        workflow_type=WorkflowType.SEQUENTIAL,
        risk_level=RiskLevel.MEDIUM,
        completeness=CompletenessInfo(
            is_complete=False,
            completeness_score=0.33,
            missing_fields=["affected_system", "symptom_type"],
        ),
        routing_layer="semantic",
        reasoning="Semantic route matched",
    )


@pytest.fixture
def complete_routing_decision() -> RoutingDecision:
    """Create a complete routing decision for testing."""
    return RoutingDecision(
        intent_category=ITIntentCategory.INCIDENT,
        sub_intent="etl_failure",
        confidence=0.95,
        workflow_type=WorkflowType.SEQUENTIAL,
        risk_level=RiskLevel.HIGH,
        completeness=CompletenessInfo(
            is_complete=True,
            completeness_score=1.0,
            missing_fields=[],
        ),
        routing_layer="pattern",
        reasoning="Pattern matched: ETL failure",
    )


@pytest.fixture
def context_manager() -> ConversationContextManager:
    """Create a context manager for testing."""
    return create_context_manager()


@pytest.fixture
def question_generator() -> QuestionGenerator:
    """Create a question generator for testing."""
    return create_question_generator()


@pytest.fixture
def refinement_rules() -> RefinementRules:
    """Get default refinement rules for testing."""
    return get_default_refinement_rules()


# =============================================================================
# RefinementCondition Tests
# =============================================================================

class TestRefinementCondition:
    """Tests for RefinementCondition."""

    def test_simple_match(self):
        """Test simple keyword matching."""
        condition = RefinementCondition(
            field_name="affected_system",
            field_value="ETL",
        )
        assert condition.matches({"affected_system": "ETL"})
        assert condition.matches({"affected_system": "ETL Pipeline"})
        assert not condition.matches({"affected_system": "CRM"})

    def test_match_any(self):
        """Test match_any with multiple keywords."""
        condition = RefinementCondition(
            field_name="affected_system",
            field_value="ETL|Pipeline|批次",
            match_any=True,
        )
        assert condition.matches({"affected_system": "ETL"})
        assert condition.matches({"affected_system": "Pipeline"})
        assert condition.matches({"affected_system": "批次排程"})
        assert not condition.matches({"affected_system": "CRM"})

    def test_pattern_match(self):
        """Test regex pattern matching."""
        condition = RefinementCondition(
            field_name="symptom_type",
            field_value=r"fail|error|錯誤",
            is_pattern=True,
        )
        assert condition.matches({"symptom_type": "failed to execute"})
        assert condition.matches({"symptom_type": "error occurred"})
        assert condition.matches({"symptom_type": "發生錯誤"})
        assert not condition.matches({"symptom_type": "running slowly"})

    def test_missing_field(self):
        """Test with missing field."""
        condition = RefinementCondition(
            field_name="affected_system",
            field_value="ETL",
        )
        assert not condition.matches({})
        assert not condition.matches({"other_field": "value"})


# =============================================================================
# RefinementRule Tests
# =============================================================================

class TestRefinementRule:
    """Tests for RefinementRule."""

    def test_rule_matches(self):
        """Test rule matching with multiple conditions."""
        rule = RefinementRule(
            id="TEST_001",
            category=ITIntentCategory.INCIDENT,
            from_sub_intent="general_incident",
            to_sub_intent="etl_failure",
            conditions=[
                RefinementCondition(
                    field_name="affected_system",
                    field_value="ETL",
                ),
                RefinementCondition(
                    field_name="symptom_type",
                    field_value="報錯|失敗",
                    match_any=True,
                ),
            ],
        )

        # Both conditions met
        assert rule.matches(
            "general_incident",
            {"affected_system": "ETL", "symptom_type": "報錯"},
        )

        # Only one condition met
        assert not rule.matches(
            "general_incident",
            {"affected_system": "ETL"},
        )

        # Wrong sub_intent
        assert not rule.matches(
            "other_incident",
            {"affected_system": "ETL", "symptom_type": "報錯"},
        )

    def test_wildcard_from_sub_intent(self):
        """Test rule with wildcard from_sub_intent."""
        rule = RefinementRule(
            id="TEST_002",
            category=ITIntentCategory.INCIDENT,
            from_sub_intent="*",
            to_sub_intent="system_down",
            conditions=[
                RefinementCondition(
                    field_name="symptom_type",
                    field_value="當機|掛",
                    match_any=True,
                ),
            ],
        )

        # Should match any from_sub_intent
        assert rule.matches("general_incident", {"symptom_type": "當機"})
        assert rule.matches("etl_failure", {"symptom_type": "系統掛了"})

    def test_disabled_rule(self):
        """Test disabled rule."""
        rule = RefinementRule(
            id="TEST_003",
            category=ITIntentCategory.INCIDENT,
            from_sub_intent="general_incident",
            to_sub_intent="etl_failure",
            conditions=[],
            enabled=False,
        )
        assert not rule.matches("general_incident", {})


# =============================================================================
# RefinementRules Registry Tests
# =============================================================================

class TestRefinementRules:
    """Tests for RefinementRules registry."""

    def test_default_rules_loaded(self, refinement_rules: RefinementRules):
        """Test that default rules are loaded."""
        incident_rules = refinement_rules.get_rules_for_category(
            ITIntentCategory.INCIDENT
        )
        assert len(incident_rules) > 0

        request_rules = refinement_rules.get_rules_for_category(
            ITIntentCategory.REQUEST
        )
        assert len(request_rules) > 0

    def test_find_rule_etl_failure(self, refinement_rules: RefinementRules):
        """Test finding ETL failure rule."""
        rule = refinement_rules.find_rule(
            category=ITIntentCategory.INCIDENT,
            current_sub_intent="general_incident",
            extracted_info={
                "affected_system": "ETL",
                "symptom_type": "報錯",
            },
        )
        assert rule is not None
        assert rule.to_sub_intent == "etl_failure"

    def test_find_rule_network_failure(self, refinement_rules: RefinementRules):
        """Test finding network failure rule."""
        rule = refinement_rules.find_rule(
            category=ITIntentCategory.INCIDENT,
            current_sub_intent="general_incident",
            extracted_info={
                "affected_system": "網路",
                "symptom_type": "斷線",
            },
        )
        assert rule is not None
        assert rule.to_sub_intent == "network_failure"

    def test_find_rule_account_request(self, refinement_rules: RefinementRules):
        """Test finding account request rule."""
        rule = refinement_rules.find_rule(
            category=ITIntentCategory.REQUEST,
            current_sub_intent="general_request",
            extracted_info={
                "request_type": "帳號",
            },
        )
        assert rule is not None
        assert rule.to_sub_intent == "account_request"

    def test_no_matching_rule(self, refinement_rules: RefinementRules):
        """Test when no rule matches."""
        rule = refinement_rules.find_rule(
            category=ITIntentCategory.INCIDENT,
            current_sub_intent="general_incident",
            extracted_info={
                "affected_system": "unknown",
            },
        )
        assert rule is None


# =============================================================================
# ConversationContextManager Tests
# =============================================================================

class TestConversationContextManager:
    """Tests for ConversationContextManager."""

    def test_initialize(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test context initialization."""
        context_manager.initialize(sample_routing_decision)

        assert context_manager.is_initialized
        assert context_manager.routing_decision is not None
        assert context_manager.routing_decision.intent_category == ITIntentCategory.INCIDENT

    def test_update_with_user_response_extracts_fields(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test that user response updates extract fields."""
        context_manager.initialize(sample_routing_decision)

        updated = context_manager.update_with_user_response(
            "是 ETL 系統，跑批次時報錯"
        )

        collected = context_manager.collected_info
        assert "affected_system" in collected
        assert collected["affected_system"] == "ETL"
        assert "symptom_type" in collected

    def test_update_refines_sub_intent(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test that sub_intent is refined based on rules."""
        context_manager.initialize(sample_routing_decision)

        updated = context_manager.update_with_user_response(
            "是 ETL 系統，跑批次時報錯"
        )

        # Should be refined from general_incident to etl_failure
        assert updated.sub_intent == "etl_failure"

    def test_update_recalculates_completeness(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test that completeness is recalculated."""
        context_manager.initialize(sample_routing_decision)
        initial_score = sample_routing_decision.completeness.completeness_score

        updated = context_manager.update_with_user_response(
            "是 ETL 系統，跑批次時報錯，很緊急"
        )

        # Completeness should increase
        assert updated.completeness.completeness_score > initial_score

    def test_no_llm_reclassification(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test that intent_category is NOT changed (no LLM re-classification)."""
        context_manager.initialize(sample_routing_decision)
        original_category = sample_routing_decision.intent_category

        updated = context_manager.update_with_user_response(
            "這是一個申請，我需要帳號"  # Sounds like a request
        )

        # Category should remain INCIDENT, not changed to REQUEST
        assert updated.intent_category == original_category

    def test_dialog_history_maintained(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test that dialog history is maintained."""
        context_manager.initialize(sample_routing_decision)

        context_manager.update_with_user_response("第一個回答")
        context_manager.update_with_user_response("第二個回答")

        history = context_manager.dialog_history
        assert len(history) == 2
        assert history[0].content == "第一個回答"
        assert history[1].content == "第二個回答"

    def test_get_missing_fields(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test getting missing fields."""
        context_manager.initialize(sample_routing_decision)

        missing = context_manager.get_missing_fields()
        assert len(missing) > 0

    def test_is_complete(
        self,
        context_manager: ConversationContextManager,
        complete_routing_decision: RoutingDecision,
    ):
        """Test is_complete check."""
        context_manager.initialize(complete_routing_decision)

        assert context_manager.is_complete()

    def test_reset(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test context reset."""
        context_manager.initialize(sample_routing_decision)
        context_manager.update_with_user_response("some response")

        context_manager.reset()

        assert not context_manager.is_initialized
        assert context_manager.routing_decision is None

    def test_not_initialized_error(
        self,
        context_manager: ConversationContextManager,
    ):
        """Test error when updating without initialization."""
        with pytest.raises(RuntimeError, match="not initialized"):
            context_manager.update_with_user_response("test")


# =============================================================================
# QuestionGenerator Tests
# =============================================================================

class TestQuestionGenerator:
    """Tests for QuestionGenerator."""

    def test_generate_questions_for_missing_fields(
        self,
        question_generator: QuestionGenerator,
    ):
        """Test generating questions for missing fields."""
        questions = question_generator.generate(
            intent_category=ITIntentCategory.INCIDENT,
            missing_fields=["affected_system", "symptom_type"],
        )

        assert len(questions) == 2
        assert any(q.target_field == "affected_system" for q in questions)
        assert any(q.target_field == "symptom_type" for q in questions)

    def test_questions_sorted_by_priority(
        self,
        question_generator: QuestionGenerator,
    ):
        """Test that questions are sorted by priority."""
        questions = question_generator.generate(
            intent_category=ITIntentCategory.INCIDENT,
            missing_fields=["affected_system", "symptom_type", "urgency"],
        )

        # Check priority order (descending)
        for i in range(len(questions) - 1):
            assert questions[i].priority >= questions[i + 1].priority

    def test_max_questions_limit(self):
        """Test that max_questions limit is respected."""
        generator = create_question_generator(max_questions=2)

        questions = generator.generate(
            intent_category=ITIntentCategory.INCIDENT,
            missing_fields=["affected_system", "symptom_type", "urgency", "error_message"],
        )

        assert len(questions) <= 2

    def test_category_specific_templates(
        self,
        question_generator: QuestionGenerator,
    ):
        """Test that category-specific templates are used."""
        incident_questions = question_generator.generate(
            intent_category=ITIntentCategory.INCIDENT,
            missing_fields=["affected_system"],
        )

        request_questions = question_generator.generate(
            intent_category=ITIntentCategory.REQUEST,
            missing_fields=["request_type"],
        )

        # Different questions for different categories
        assert incident_questions[0].question != request_questions[0].question

    def test_generate_for_intent(
        self,
        question_generator: QuestionGenerator,
    ):
        """Test generating all questions for an intent."""
        questions = question_generator.generate_for_intent(
            intent_category=ITIntentCategory.INCIDENT,
            collected_fields=["affected_system"],
        )

        # Should not include questions for collected fields
        assert not any(q.target_field == "affected_system" for q in questions)

    def test_format_questions_as_text(
        self,
        question_generator: QuestionGenerator,
    ):
        """Test formatting questions as text."""
        questions = question_generator.generate(
            intent_category=ITIntentCategory.INCIDENT,
            missing_fields=["affected_system"],
        )

        text = question_generator.format_questions_as_text(questions)
        assert "1." in text
        assert "?" in text or "？" in text

    def test_get_question_text(
        self,
        question_generator: QuestionGenerator,
    ):
        """Test getting question text for a field."""
        text = question_generator.get_question_text(
            "affected_system",
            ITIntentCategory.INCIDENT,
        )
        assert text is not None
        assert "系統" in text

    def test_empty_missing_fields(
        self,
        question_generator: QuestionGenerator,
    ):
        """Test with no missing fields."""
        questions = question_generator.generate(
            intent_category=ITIntentCategory.INCIDENT,
            missing_fields=[],
        )
        assert len(questions) == 0


# =============================================================================
# GuidedDialogEngine Tests
# =============================================================================

class TestGuidedDialogEngine:
    """Tests for GuidedDialogEngine."""

    @pytest.mark.asyncio
    async def test_start_dialog_incomplete(self):
        """Test starting dialog with incomplete information."""
        engine = create_mock_dialog_engine()

        response = await engine.start_dialog("系統有問題")

        assert engine.is_active
        assert response.should_continue
        assert len(response.questions) > 0

    @pytest.mark.asyncio
    async def test_start_dialog_complete(self):
        """Test starting dialog with complete information."""
        engine = create_mock_dialog_engine()

        # Long input triggers mock completeness
        response = await engine.start_dialog(
            "ETL Pipeline 今天下午跑批次時失敗了，影響到財務報表產出，很緊急需要處理"
        )

        # Mock uses input length for completeness
        assert response.state is not None

    @pytest.mark.asyncio
    async def test_process_response_updates_state(self):
        """Test that process_response updates dialog state."""
        engine = create_mock_dialog_engine()

        await engine.start_dialog("系統有問題")
        initial_turn_count = engine.current_state.turn_count

        await engine.process_response("是 ETL 系統報錯")

        assert engine.current_state.turn_count == initial_turn_count + 1

    @pytest.mark.asyncio
    async def test_multi_turn_dialog(self):
        """Test multi-turn dialog flow."""
        engine = create_mock_dialog_engine()

        # Turn 1 - use short input to ensure dialog continues
        response1 = await engine.start_dialog("問題")
        assert response1.should_continue

        # Turn 2
        response2 = await engine.process_response("ETL")
        assert response2.state.turn_count == 1

        # Turn 3 - continue dialog
        if engine.is_active:
            response3 = await engine.process_response("報錯")
            assert response3.state.turn_count == 2

    @pytest.mark.asyncio
    async def test_max_turns_triggers_handoff(self):
        """Test that exceeding max turns triggers handoff."""
        engine = create_mock_dialog_engine(max_turns=2)

        # Start with short input to ensure dialog continues
        response1 = await engine.start_dialog("問題")

        if response1.should_continue:
            await engine.process_response("a")  # Turn 1
            if engine.is_active:
                response = await engine.process_response("b")  # Turn 2

                # Either handoff or complete
                assert not response.should_continue or response.state.is_complete

    @pytest.mark.asyncio
    async def test_generate_questions(self):
        """Test generate_questions method."""
        engine = create_mock_dialog_engine()

        await engine.start_dialog("系統有問題")

        questions = engine.generate_questions()
        assert len(questions) > 0

    @pytest.mark.asyncio
    async def test_get_dialog_summary(self):
        """Test get_dialog_summary method."""
        engine = create_mock_dialog_engine()

        await engine.start_dialog("系統有問題")

        summary = engine.get_dialog_summary()
        assert "status" in summary
        assert "turn_count" in summary

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test dialog reset."""
        engine = create_mock_dialog_engine()

        await engine.start_dialog("系統有問題")
        engine.reset()

        assert not engine.is_active
        assert engine.current_state is None

    @pytest.mark.asyncio
    async def test_not_started_error(self):
        """Test error when processing without starting."""
        engine = create_mock_dialog_engine()

        with pytest.raises(RuntimeError, match="not started"):
            await engine.process_response("test")


# =============================================================================
# Incremental Update Tests (Core Feature)
# =============================================================================

class TestIncrementalUpdate:
    """Tests specifically for incremental update behavior."""

    def test_sub_intent_refinement_without_llm(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """
        Test that sub_intent is refined via rules, not LLM.

        This is the core feature of Sprint 94.
        """
        context_manager.initialize(sample_routing_decision)

        # Initial sub_intent
        initial_sub = sample_routing_decision.sub_intent
        assert initial_sub == "general_incident"

        # Update with ETL + error info
        updated = context_manager.update_with_user_response(
            "ETL Pipeline 報錯了"
        )

        # Sub-intent should be refined
        assert updated.sub_intent == "etl_failure"

        # Category should NOT change (no LLM re-classification)
        assert updated.intent_category == ITIntentCategory.INCIDENT

    def test_cumulative_information_collection(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test that information accumulates across turns."""
        context_manager.initialize(sample_routing_decision)

        # First response - add system
        context_manager.update_with_user_response("是 ETL 系統")
        collected1 = context_manager.collected_info.copy()

        # Second response - add symptom
        context_manager.update_with_user_response("執行時報錯了")
        collected2 = context_manager.collected_info.copy()

        # Information should accumulate
        assert len(collected2) >= len(collected1)

    def test_completeness_recalculation_accuracy(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test that completeness is correctly recalculated."""
        context_manager.initialize(sample_routing_decision)

        # Get initial completeness
        initial_score = sample_routing_decision.completeness.completeness_score
        initial_missing = sample_routing_decision.completeness.missing_fields.copy()

        # Provide information for missing fields
        context_manager.update_with_user_response(
            "ETL 系統報錯了，很緊急"
        )

        updated = context_manager.routing_decision
        final_score = updated.completeness.completeness_score
        final_missing = updated.completeness.missing_fields

        # Score should increase
        assert final_score >= initial_score

        # Missing fields should decrease
        assert len(final_missing) <= len(initial_missing)


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_user_response(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test handling of empty user response."""
        context_manager.initialize(sample_routing_decision)

        # Should not crash
        updated = context_manager.update_with_user_response("")

        assert updated is not None

    def test_very_long_response(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test handling of very long user response."""
        context_manager.initialize(sample_routing_decision)

        long_response = "ETL 系統 " * 100

        updated = context_manager.update_with_user_response(long_response)

        assert updated is not None
        assert "ETL" in context_manager.collected_info.get("affected_system", "")

    def test_special_characters_in_response(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test handling of special characters."""
        context_manager.initialize(sample_routing_decision)

        response = "系統 error: \"Connection failed\" @#$%"

        updated = context_manager.update_with_user_response(response)

        assert updated is not None

    def test_mixed_language_response(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test handling of mixed Chinese/English response."""
        context_manager.initialize(sample_routing_decision)

        response = "ETL Pipeline 發生 timeout error，已經 down 了 30 分鐘"

        updated = context_manager.update_with_user_response(response)

        assert updated is not None
        collected = context_manager.collected_info
        assert "affected_system" in collected

    @pytest.mark.asyncio
    async def test_unknown_intent_handling(self):
        """Test handling of unknown intent."""
        engine = create_mock_dialog_engine()

        response = await engine.start_dialog("???")

        assert response.state is not None

    def test_no_matching_refinement_rule(
        self,
        context_manager: ConversationContextManager,
        sample_routing_decision: RoutingDecision,
    ):
        """Test when no refinement rule matches."""
        context_manager.initialize(sample_routing_decision)

        # Provide info that doesn't match any rule
        updated = context_manager.update_with_user_response(
            "就是有問題啊"
        )

        # Sub-intent should remain unchanged
        assert updated.sub_intent == sample_routing_decision.sub_intent


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_context_manager(self):
        """Test create_context_manager factory."""
        manager = create_context_manager()
        assert isinstance(manager, ConversationContextManager)

    def test_create_mock_context_manager(self):
        """Test create_mock_context_manager factory."""
        manager = create_mock_context_manager()
        assert isinstance(manager, MockConversationContextManager)

    def test_create_question_generator(self):
        """Test create_question_generator factory."""
        generator = create_question_generator()
        assert isinstance(generator, QuestionGenerator)

    def test_create_mock_dialog_engine(self):
        """Test create_mock_dialog_engine factory."""
        engine = create_mock_dialog_engine()
        assert isinstance(engine, MockGuidedDialogEngine)

    def test_get_default_refinement_rules(self):
        """Test get_default_refinement_rules factory."""
        rules = get_default_refinement_rules()
        assert isinstance(rules, RefinementRules)


# =============================================================================
# Serialization Tests
# =============================================================================

class TestSerialization:
    """Tests for data serialization."""

    def test_dialog_turn_to_dict(self):
        """Test DialogTurn serialization."""
        turn = DialogTurn(
            role="user",
            content="test content",
            extracted={"field": "value"},
        )
        result = turn.to_dict()

        assert result["role"] == "user"
        assert result["content"] == "test content"
        assert "timestamp" in result

    def test_context_state_to_dict(
        self,
        sample_routing_decision: RoutingDecision,
    ):
        """Test ContextState serialization."""
        state = ContextState(
            routing_decision=sample_routing_decision,
            collected_info={"field": "value"},
            turn_count=2,
        )
        result = state.to_dict()

        assert "routing_decision" in result
        assert result["turn_count"] == 2

    def test_generated_question_to_dict(self):
        """Test GeneratedQuestion serialization."""
        question = GeneratedQuestion(
            question="Test question?",
            target_field="test_field",
            priority=100,
        )
        result = question.to_dict()

        assert result["question"] == "Test question?"
        assert result["priority"] == 100

    def test_refinement_rule_to_dict(self):
        """Test RefinementRule serialization."""
        rule = RefinementRule(
            id="TEST",
            category=ITIntentCategory.INCIDENT,
            from_sub_intent="general",
            to_sub_intent="specific",
            conditions=[
                RefinementCondition(
                    field_name="field",
                    field_value="value",
                ),
            ],
        )
        result = rule.to_dict()

        assert result["id"] == "TEST"
        assert len(result["conditions"]) == 1
