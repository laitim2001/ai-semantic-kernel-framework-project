"""
File: tests/unit/agent_harness/context_mgmt/test_compactor_semantic.py
Purpose: Unit tests for SemanticCompactor (impl ships Day 2.3; LLM-driven via ChatClient ABC).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 2 (placeholder created Day 1.8)

Test plan (Day 2.4): 4 tests
  - test_summarize_old_turns_via_mock_client
  - test_preserves_recent_n_turns
  - test_handles_llm_failure_raises
  - test_summary_metadata_marker

LLM neutrality: tests must use MockChatClient injection; no openai/anthropic SDK imports.
"""

import pytest


@pytest.mark.skip(reason="Day 2.4 implements SemanticCompactor + 4 tests via MockChatClient")
def test_placeholder_semantic() -> None:
    """Placeholder; replaced by Day 2.4 (4 tests with mock LLM injection)."""
