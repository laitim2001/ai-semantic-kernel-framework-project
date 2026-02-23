"""
Unit Tests for RITM Intent Mapper.

Sprint 114: AD 場景基礎建設 (Phase 32)
"""

import pytest

from src.integrations.orchestration.input.ritm_intent_mapper import (
    IntentMappingResult,
    RITMIntentMapper,
)
from src.integrations.orchestration.input.servicenow_webhook import (
    ServiceNowRITMEvent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mapper() -> RITMIntentMapper:
    """Create mapper with default (production) mappings.yaml."""
    return RITMIntentMapper()


@pytest.fixture
def custom_mapper() -> RITMIntentMapper:
    """Create mapper with custom inline mappings."""
    return RITMIntentMapper(
        mappings_dict={
            "mappings": [
                {
                    "cat_item_name": "Test Item",
                    "intent": "test.intent",
                    "extract_variables": {
                        "user": "variables.target_user",
                        "desc": "short_description",
                    },
                },
            ],
            "fallback": {
                "strategy": "test_fallback",
                "log_unmatched": True,
            },
        }
    )


def _make_event(
    cat_item_name: str = "AD Account Unlock",
    variables: dict = None,
    **kwargs,
) -> ServiceNowRITMEvent:
    """Helper to create test RITM events."""
    defaults = {
        "sys_id": "test_sys_id",
        "number": "RITM0099999",
        "cat_item_name": cat_item_name,
        "short_description": "Test request",
        "variables": variables or {},
    }
    defaults.update(kwargs)
    return ServiceNowRITMEvent(**defaults)


# ---------------------------------------------------------------------------
# Mapping Tests (default YAML)
# ---------------------------------------------------------------------------


class TestRITMMappingFromYAML:
    """Tests for RITM mapping using production ritm_mappings.yaml."""

    def test_mappings_loaded(self, mapper: RITMIntentMapper) -> None:
        """Test that mappings are loaded from default YAML."""
        assert mapper.get_mappings_count() == 5

    def test_supported_intents(self, mapper: RITMIntentMapper) -> None:
        """Test all 5 AD intents are supported."""
        intents = mapper.get_supported_intents()
        assert "ad.account.unlock" in intents
        assert "ad.password.reset" in intents
        assert "ad.group.modify" in intents
        assert "ad.account.create" in intents
        assert "ad.account.disable" in intents

    def test_map_account_unlock(self, mapper: RITMIntentMapper) -> None:
        """Test mapping AD Account Unlock."""
        event = _make_event(
            "AD Account Unlock",
            variables={"affected_user": "john.doe"},
        )
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True
        assert result.intent == "ad.account.unlock"
        assert result.variables["target_user"] == "john.doe"

    def test_map_password_reset(self, mapper: RITMIntentMapper) -> None:
        """Test mapping AD Password Reset."""
        event = _make_event(
            "AD Password Reset",
            variables={"affected_user": "jane.smith", "temp_password": "TmpP@ss1"},
        )
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True
        assert result.intent == "ad.password.reset"
        assert result.variables["target_user"] == "jane.smith"
        assert result.variables["temporary_password"] == "TmpP@ss1"

    def test_map_group_membership(self, mapper: RITMIntentMapper) -> None:
        """Test mapping AD Group Membership Change."""
        event = _make_event(
            "AD Group Membership Change",
            variables={
                "affected_user": "john.doe",
                "group_name": "IT-Admins",
                "action_type": "add",
            },
        )
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True
        assert result.intent == "ad.group.modify"
        assert result.variables["target_user"] == "john.doe"
        assert result.variables["group_name"] == "IT-Admins"
        assert result.variables["action"] == "add"

    def test_map_account_create(self, mapper: RITMIntentMapper) -> None:
        """Test mapping New AD Account."""
        event = _make_event(
            "New AD Account",
            variables={
                "display_name": "John Doe",
                "department": "IT",
                "manager": "jane.smith",
                "email": "john.doe@company.com",
            },
        )
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True
        assert result.intent == "ad.account.create"
        assert result.variables["display_name"] == "John Doe"
        assert result.variables["department"] == "IT"

    def test_map_account_disable(self, mapper: RITMIntentMapper) -> None:
        """Test mapping Disable AD Account."""
        event = _make_event(
            "Disable AD Account",
            variables={
                "affected_user": "john.doe",
                "disable_reason": "Terminated",
            },
        )
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True
        assert result.intent == "ad.account.disable"
        assert result.variables["target_user"] == "john.doe"
        assert result.variables["reason"] == "Terminated"


# ---------------------------------------------------------------------------
# Case Insensitivity Tests
# ---------------------------------------------------------------------------


class TestCaseInsensitiveMapping:
    """Tests for case-insensitive catalog item matching."""

    def test_lowercase_match(self, mapper: RITMIntentMapper) -> None:
        """Test lowercase catalog item name matches."""
        event = _make_event("ad account unlock")
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True
        assert result.intent == "ad.account.unlock"

    def test_uppercase_match(self, mapper: RITMIntentMapper) -> None:
        """Test uppercase catalog item name matches."""
        event = _make_event("AD ACCOUNT UNLOCK")
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True

    def test_mixed_case_match(self, mapper: RITMIntentMapper) -> None:
        """Test mixed case catalog item name matches."""
        event = _make_event("Ad Account Unlock")
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True


# ---------------------------------------------------------------------------
# Fallback Tests
# ---------------------------------------------------------------------------


class TestFallbackStrategy:
    """Tests for unmapped catalog item fallback."""

    def test_unknown_item_uses_fallback(self, mapper: RITMIntentMapper) -> None:
        """Test unknown catalog item triggers fallback."""
        event = _make_event("Unknown Catalog Item XYZ")
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is False
        assert result.fallback_used is True
        assert result.fallback_strategy == "semantic_router"

    def test_empty_item_name_uses_fallback(self, mapper: RITMIntentMapper) -> None:
        """Test empty catalog item name triggers fallback."""
        event = _make_event("")
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is False
        assert result.fallback_used is True

    def test_fallback_strategy_name(self, mapper: RITMIntentMapper) -> None:
        """Test fallback strategy name is correct."""
        assert mapper.get_fallback_strategy() == "semantic_router"


# ---------------------------------------------------------------------------
# Variable Extraction Tests
# ---------------------------------------------------------------------------


class TestVariableExtraction:
    """Tests for variable extraction from RITM events."""

    def test_extract_top_level_field(self, mapper: RITMIntentMapper) -> None:
        """Test extraction of top-level event fields."""
        event = _make_event(
            "AD Account Unlock",
            short_description="Unlock john's account",
        )
        result = mapper.map_ritm_to_intent(event)
        assert result.variables.get("reason") == "Unlock john's account"

    def test_extract_nested_variable(self, mapper: RITMIntentMapper) -> None:
        """Test extraction of nested variables."""
        event = _make_event(
            "AD Account Unlock",
            variables={"affected_user": "john.doe"},
        )
        result = mapper.map_ritm_to_intent(event)
        assert result.variables.get("target_user") == "john.doe"

    def test_missing_variable_skipped(self, mapper: RITMIntentMapper) -> None:
        """Test missing variables are silently skipped."""
        event = _make_event("AD Password Reset", variables={})
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is True
        # Variables with missing paths should not appear
        assert "temporary_password" not in result.variables


# ---------------------------------------------------------------------------
# Custom Mappings Tests
# ---------------------------------------------------------------------------


class TestCustomMappings:
    """Tests for inline/custom mapping configuration."""

    def test_custom_mapping_loaded(self, custom_mapper: RITMIntentMapper) -> None:
        """Test custom mapping is loaded."""
        assert custom_mapper.get_mappings_count() == 1

    def test_custom_mapping_match(self, custom_mapper: RITMIntentMapper) -> None:
        """Test custom mapping matches."""
        event = _make_event(
            "Test Item",
            variables={"target_user": "test_user"},
            short_description="Test desc",
        )
        result = custom_mapper.map_ritm_to_intent(event)
        assert result.matched is True
        assert result.intent == "test.intent"
        assert result.variables["user"] == "test_user"
        assert result.variables["desc"] == "Test desc"

    def test_custom_fallback(self, custom_mapper: RITMIntentMapper) -> None:
        """Test custom fallback strategy."""
        assert custom_mapper.get_fallback_strategy() == "test_fallback"


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestMappingErrorHandling:
    """Tests for mapping error handling."""

    def test_missing_mappings_file(self) -> None:
        """Test handling of missing mappings file."""
        mapper = RITMIntentMapper(mappings_path="/nonexistent/path.yaml")
        assert mapper.get_mappings_count() == 0

    def test_empty_mappings_dict(self) -> None:
        """Test handling of empty mappings dictionary."""
        mapper = RITMIntentMapper(mappings_dict={})
        assert mapper.get_mappings_count() == 0
        event = _make_event("Anything")
        result = mapper.map_ritm_to_intent(event)
        assert result.matched is False
