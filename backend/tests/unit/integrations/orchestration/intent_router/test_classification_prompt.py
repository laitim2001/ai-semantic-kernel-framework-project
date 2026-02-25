"""
Classification Prompt Tests

Tests prompt generation, required fields, and sub-intent examples.

Sprint 128: Story 128-3
"""

import pytest

from src.integrations.orchestration.intent_router.llm_classifier.prompts import (
    CLASSIFICATION_PROMPT,
    SIMPLE_CLASSIFICATION_PROMPT,
    get_classification_prompt,
    get_required_fields,
    get_sub_intent_examples,
)


class TestGetClassificationPrompt:
    """Tests for get_classification_prompt()."""

    def test_full_prompt_contains_user_input(self):
        """Full prompt includes the user input text."""
        prompt = get_classification_prompt("ETL failed")
        assert "ETL failed" in prompt

    def test_full_prompt_contains_all_categories(self):
        """Full prompt contains all 4 intent categories."""
        prompt = get_classification_prompt("test input")
        assert "incident" in prompt.lower()
        assert "request" in prompt.lower()
        assert "change" in prompt.lower()
        assert "query" in prompt.lower()

    def test_full_prompt_contains_json_format(self):
        """Full prompt specifies JSON output format."""
        prompt = get_classification_prompt("test input")
        assert "intent_category" in prompt
        assert "confidence" in prompt
        assert "JSON" in prompt or "json" in prompt

    def test_simplified_prompt(self):
        """Simplified prompt is shorter and contains user input."""
        prompt = get_classification_prompt("test input", simplified=True)
        assert "test input" in prompt
        assert len(prompt) < len(get_classification_prompt("test input", simplified=False))

    def test_simplified_prompt_contains_categories(self):
        """Simplified prompt still references all categories."""
        prompt = get_classification_prompt("test", simplified=True)
        assert "incident" in prompt.lower()
        assert "request" in prompt.lower()


class TestGetRequiredFields:
    """Tests for get_required_fields()."""

    def test_incident_required_fields(self):
        """Incident has 3 required fields."""
        fields = get_required_fields("incident")
        assert len(fields) == 3
        assert "問題描述" in fields

    def test_request_required_fields(self):
        """Request has 2 required fields."""
        fields = get_required_fields("request")
        assert len(fields) == 2
        assert "請求內容" in fields

    def test_change_required_fields(self):
        """Change has 3 required fields."""
        fields = get_required_fields("change")
        assert len(fields) == 3

    def test_query_required_fields(self):
        """Query has 1 required field."""
        fields = get_required_fields("query")
        assert len(fields) == 1

    def test_unknown_category_default(self):
        """Unknown category returns default field."""
        fields = get_required_fields("unknown_category")
        assert "描述" in fields


class TestGetSubIntentExamples:
    """Tests for get_sub_intent_examples()."""

    def test_incident_sub_intents(self):
        """Incident has multiple sub-intents including etl_failure."""
        examples = get_sub_intent_examples("incident")
        assert len(examples) >= 5
        assert "etl_failure" in examples

    def test_request_sub_intents(self):
        """Request has multiple sub-intents including account_creation."""
        examples = get_sub_intent_examples("request")
        assert "account_creation" in examples
        assert "password_reset" in examples

    def test_change_sub_intents(self):
        """Change has sub-intents including release_deployment."""
        examples = get_sub_intent_examples("change")
        assert "release_deployment" in examples

    def test_query_sub_intents(self):
        """Query has sub-intents including status_inquiry."""
        examples = get_sub_intent_examples("query")
        assert "status_inquiry" in examples

    def test_unknown_category_empty(self):
        """Unknown category returns empty list."""
        examples = get_sub_intent_examples("nonexistent")
        assert examples == []
