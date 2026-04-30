"""
File: tests/unit/agent_harness/context_mgmt/test_token_counter_claude.py
Purpose: Unit tests for ClaudeTokenCounter (impl ships Day 3.8; anthropic.tokenizer or fallback).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 3 (placeholder created Day 1.8)

Test plan (Day 3.8): 3 tests
  - test_count_via_anthropic_lib  (when lib available)
  - test_fallback_to_approx_when_lib_missing
  - test_accuracy_returns_appropriate_value  (exact if lib, approximate otherwise)
"""

import pytest


@pytest.mark.skip(reason="Day 3.8 implements ClaudeTokenCounter + 3 tests")
def test_placeholder_claude_counter() -> None:
    """Placeholder; replaced by Day 3.8 (3 tests with fallback path)."""
