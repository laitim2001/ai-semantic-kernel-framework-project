"""
Unit Tests for ConversationContextManager

Tests for:
- Initialization and state management
- update_with_user_response() incremental updates
- Dialog history tracking
- get_state() and property accessors
- Error handling for uninitialized state
- Re-initialization clears previous state

Sprint 123: Story 123-1 - Orchestration Module Tests (Phase 33)
"""

import pytest

from src.integrations.orchestration.intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    RiskLevel,
    RoutingDecision,
    WorkflowType,
)
from src.integrations.orchestration.guided_dialog.context_manager import (
    ContextState,
    ConversationContextManager,
    create_context_manager,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def manager() -> ConversationContextManager:
    """Create a ConversationContextManager for testing."""
    return create_context_manager()


@pytest.fixture
def incomplete_decision() -> RoutingDecision:
    """Create an incomplete routing decision for testing."""
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
def complete_decision() -> RoutingDecision:
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
def change_decision() -> RoutingDecision:
    """Create a CHANGE routing decision for testing."""
    return RoutingDecision(
        intent_category=ITIntentCategory.CHANGE,
        sub_intent="general_change",
        confidence=0.80,
        workflow_type=WorkflowType.SEQUENTIAL,
        risk_level=RiskLevel.MEDIUM,
        completeness=CompletenessInfo(
            is_complete=False,
            completeness_score=0.25,
            missing_fields=["change_type", "target_system"],
        ),
        routing_layer="semantic",
        reasoning="Semantic route matched for change",
    )


# =============================================================================
# ConversationContextManager Tests
# =============================================================================


class TestConversationContextManager:
    """Tests for ConversationContextManager core functionality."""

    def test_initial_state_not_initialized(self, manager: ConversationContextManager):
        """Freshly created manager should not be initialized."""
        assert manager.is_initialized is False
        assert manager.routing_decision is None
        assert manager.collected_info == {}
        assert manager.dialog_history == []

    def test_initialize_with_routing_decision(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Initialize should set routing decision and mark as initialized."""
        manager.initialize(incomplete_decision)

        assert manager.is_initialized is True
        assert manager.routing_decision is not None
        assert manager.routing_decision.intent_category == ITIntentCategory.INCIDENT
        assert manager.routing_decision.sub_intent == "general_incident"
        assert manager.routing_decision.confidence == 0.85

    def test_initialize_deep_copies_decision(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Initialize should deep-copy the decision to avoid external mutation."""
        manager.initialize(incomplete_decision)

        # Mutate the original decision
        incomplete_decision.sub_intent = "mutated_sub_intent"

        # Manager's copy should be unaffected
        assert manager.routing_decision.sub_intent == "general_incident"

    def test_initialize_clears_previous_state(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
        complete_decision: RoutingDecision,
    ):
        """Re-initializing should clear all previous state."""
        # First initialization and some updates
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("是 ETL 系統")
        assert len(manager.dialog_history) == 1
        assert len(manager.collected_info) > 0

        # Re-initialize with different decision
        manager.initialize(complete_decision)

        assert manager.is_initialized is True
        assert manager.routing_decision.sub_intent == "etl_failure"
        assert manager.dialog_history == []
        assert manager.collected_info == {}

    def test_update_with_user_response_adds_to_history(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """update_with_user_response should add a turn to dialog history."""
        manager.initialize(incomplete_decision)

        manager.update_with_user_response("是 ETL 系統報錯")

        history = manager.dialog_history
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "是 ETL 系統報錯"

    def test_update_returns_routing_decision(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """update_with_user_response should return a RoutingDecision."""
        manager.initialize(incomplete_decision)

        result = manager.update_with_user_response("ETL 系統報錯了")

        assert isinstance(result, RoutingDecision)
        assert result.intent_category == ITIntentCategory.INCIDENT

    def test_get_state_returns_context_state(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """get_state() should return a ContextState with correct data."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("ETL 系統有問題")

        state = manager.get_state()

        assert isinstance(state, ContextState)
        assert state.routing_decision is not None
        assert state.routing_decision.intent_category == ITIntentCategory.INCIDENT
        assert state.turn_count == 1

    def test_get_state_serializable(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """get_state().to_dict() should produce a serializable dictionary."""
        manager.initialize(incomplete_decision)

        state = manager.get_state()
        state_dict = state.to_dict()

        assert "routing_decision" in state_dict
        assert "collected_info" in state_dict
        assert "turn_count" in state_dict
        assert "last_updated" in state_dict

    def test_properties_after_initialization(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """All properties should be accessible after initialization."""
        manager.initialize(incomplete_decision)

        assert manager.is_initialized is True
        assert manager.routing_decision is not None
        assert isinstance(manager.collected_info, dict)
        assert isinstance(manager.dialog_history, list)

    def test_dialog_history_tracks_multiple_turns(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Dialog history should correctly track multiple user turns."""
        manager.initialize(incomplete_decision)

        manager.update_with_user_response("第一個回答：ETL 系統")
        manager.update_with_user_response("第二個回答：報錯了")
        manager.update_with_user_response("第三個回答：很緊急")

        history = manager.dialog_history
        assert len(history) == 3
        assert history[0].content == "第一個回答：ETL 系統"
        assert history[1].content == "第二個回答：報錯了"
        assert history[2].content == "第三個回答：很緊急"
        assert all(turn.role == "user" for turn in history)

    def test_update_without_initialize_raises(
        self,
        manager: ConversationContextManager,
    ):
        """Calling update_with_user_response before initialize should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.update_with_user_response("test input")

    def test_collected_info_returns_copy(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """collected_info property should return a copy (no external mutation)."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("ETL 系統")

        info = manager.collected_info
        info["injected_key"] = "should_not_persist"

        assert "injected_key" not in manager.collected_info

    def test_dialog_history_returns_copy(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """dialog_history property should return a copy (no external mutation)."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("ETL 系統")

        history = manager.dialog_history
        history.clear()

        assert len(manager.dialog_history) == 1


# =============================================================================
# Field Extraction and Sub-intent Refinement Tests
# =============================================================================


class TestFieldExtractionAndRefinement:
    """Tests for field extraction from user responses and sub-intent refinement."""

    def test_extract_affected_system(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Should extract affected_system from user response."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("是 ETL 系統出問題了")

        collected = manager.collected_info
        assert "affected_system" in collected
        assert collected["affected_system"] == "ETL"

    def test_extract_symptom_type(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Should extract symptom_type from user response."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("系統報錯了")

        collected = manager.collected_info
        assert "symptom_type" in collected

    def test_extract_urgency(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Should extract urgency from user response."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("很緊急需要處理")

        collected = manager.collected_info
        assert "urgency" in collected
        assert collected["urgency"] == "緊急"

    def test_sub_intent_refined_to_etl_failure(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Sub-intent should be refined from general_incident to etl_failure."""
        manager.initialize(incomplete_decision)
        updated = manager.update_with_user_response("ETL Pipeline 報錯了")

        assert updated.sub_intent == "etl_failure"

    def test_intent_category_never_changes(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Intent category must NOT change during dialog (no LLM re-classification)."""
        manager.initialize(incomplete_decision)
        original_category = incomplete_decision.intent_category

        # User response that sounds like a REQUEST, not an INCIDENT
        updated = manager.update_with_user_response("我想申請一個新帳號")

        assert updated.intent_category == original_category

    def test_cumulative_field_collection(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Fields should accumulate across multiple turns."""
        manager.initialize(incomplete_decision)

        manager.update_with_user_response("是 ETL 系統")
        fields_after_first = set(manager.collected_info.keys())

        manager.update_with_user_response("執行時報錯了")
        fields_after_second = set(manager.collected_info.keys())

        assert len(fields_after_second) >= len(fields_after_first)

    def test_completeness_score_increases(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Completeness score should increase as more info is provided."""
        manager.initialize(incomplete_decision)
        initial_score = incomplete_decision.completeness.completeness_score

        updated = manager.update_with_user_response("ETL 系統報錯了，很緊急")
        final_score = updated.completeness.completeness_score

        assert final_score >= initial_score


# =============================================================================
# Additional Context Manager Methods Tests
# =============================================================================


class TestContextManagerMethods:
    """Tests for additional ConversationContextManager methods."""

    def test_get_missing_fields(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """get_missing_fields() should return fields still needed."""
        manager.initialize(incomplete_decision)

        missing = manager.get_missing_fields()
        assert isinstance(missing, list)
        assert len(missing) > 0

    def test_get_missing_fields_not_initialized(
        self,
        manager: ConversationContextManager,
    ):
        """get_missing_fields() should return empty list when not initialized."""
        missing = manager.get_missing_fields()
        assert missing == []

    def test_get_collected_fields(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """get_collected_fields() should return names of collected fields."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("ETL 系統報錯")

        fields = manager.get_collected_fields()
        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_is_complete_for_incomplete_decision(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """is_complete() should return False for incomplete information."""
        manager.initialize(incomplete_decision)
        assert manager.is_complete() is False

    def test_is_complete_for_complete_decision(
        self,
        manager: ConversationContextManager,
        complete_decision: RoutingDecision,
    ):
        """is_complete() should return True for complete information."""
        manager.initialize(complete_decision)
        assert manager.is_complete() is True

    def test_is_complete_not_initialized(
        self,
        manager: ConversationContextManager,
    ):
        """is_complete() should return False when not initialized."""
        assert manager.is_complete() is False

    def test_add_assistant_turn(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """add_assistant_turn() should add an assistant turn to history."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("ETL 系統")
        manager.add_assistant_turn("請問具體的錯誤訊息是什麼？")

        history = manager.dialog_history
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"
        assert history[1].content == "請問具體的錯誤訊息是什麼？"

    def test_reset_clears_all_state(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """reset() should clear all state back to initial."""
        manager.initialize(incomplete_decision)
        manager.update_with_user_response("ETL 系統報錯")

        manager.reset()

        assert manager.is_initialized is False
        assert manager.routing_decision is None
        assert manager.collected_info == {}
        assert manager.dialog_history == []


# =============================================================================
# Edge Cases
# =============================================================================


class TestContextManagerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_response(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Empty user response should not crash."""
        manager.initialize(incomplete_decision)
        result = manager.update_with_user_response("")

        assert result is not None
        assert isinstance(result, RoutingDecision)

    def test_very_long_response(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Very long user response should be handled gracefully."""
        manager.initialize(incomplete_decision)
        long_text = "ETL 系統 " * 500

        result = manager.update_with_user_response(long_text)

        assert result is not None
        assert "affected_system" in manager.collected_info

    def test_special_characters(
        self,
        manager: ConversationContextManager,
        incomplete_decision: RoutingDecision,
    ):
        """Special characters in response should not crash."""
        manager.initialize(incomplete_decision)
        result = manager.update_with_user_response('error: "timeout" @#$%^&*()')

        assert result is not None

    def test_change_category_field_extraction(
        self,
        manager: ConversationContextManager,
        change_decision: RoutingDecision,
    ):
        """Should extract change-specific fields."""
        manager.initialize(change_decision)
        manager.update_with_user_response("需要部署新版本到正式環境")

        collected = manager.collected_info
        assert "change_type" in collected
        assert collected["change_type"] == "部署"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for create_context_manager() factory."""

    def test_create_context_manager_returns_instance(self):
        """create_context_manager() should return a ConversationContextManager."""
        manager = create_context_manager()
        assert isinstance(manager, ConversationContextManager)

    def test_create_context_manager_is_not_initialized(self):
        """Newly created manager should not be initialized."""
        manager = create_context_manager()
        assert manager.is_initialized is False

    def test_create_context_manager_with_custom_rules(self):
        """create_context_manager() should accept custom rules."""
        # Passing None for both should use defaults
        manager = create_context_manager(
            refinement_rules=None,
            completeness_rules=None,
        )
        assert isinstance(manager, ConversationContextManager)
