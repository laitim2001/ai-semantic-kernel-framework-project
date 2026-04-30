"""
File: tests/unit/agent_harness/context_mgmt/test_token_counter_claude.py
Purpose: Unit tests for ClaudeTokenCounter (impl: token_counter/claude_counter.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 3.8

3 tests:
  - test_count_via_anthropic_lib_or_fallback
  - test_fallback_to_approx_when_lib_missing  (force_approximate=True path)
  - test_accuracy_returns_appropriate_value
"""

from __future__ import annotations

import pytest

from agent_harness._contracts import Message
from agent_harness.context_mgmt.token_counter import claude_counter as cc_module
from agent_harness.context_mgmt.token_counter.claude_counter import ClaudeTokenCounter


def test_count_via_anthropic_lib_or_fallback() -> None:
    """Counter returns a positive token estimate regardless of which path is active."""
    counter = ClaudeTokenCounter()
    msgs = [Message(role="user", content="hello world")]
    n = counter.count(messages=msgs)
    assert n > 0
    # Reasonable upper bound for short message
    assert n < 50


def test_fallback_to_approx_when_lib_missing() -> None:
    """force_approximate=True must use the 4-chars/token heuristic regardless of lib presence."""
    counter = ClaudeTokenCounter(force_approximate=True)
    # 16-char content under approx → ceil(16/4) = 4 tokens for content alone
    msg = Message(role="user", content="a" * 16)
    n = counter.count(messages=[msg])
    # 3 per_message + ceil("user"/4=1) + ceil(16/4=4) = 8
    assert n == 3 + 1 + 4
    assert counter.accuracy() == "approximate"


def test_accuracy_returns_appropriate_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """accuracy() reflects whether anthropic.tokenizer was loaded.

    We monkeypatch the module-level _ANTHROPIC_COUNTER to simulate both
    presence and absence without requiring the library to be installed.
    """
    counter = ClaudeTokenCounter()
    # Reflect current real-world state: matches whatever the module loaded
    if cc_module._ANTHROPIC_COUNTER is not None:
        assert counter.accuracy() == "exact"
    else:
        assert counter.accuracy() == "approximate"

    # Now force-simulate "lib present" by injecting a fake counter
    monkeypatch.setattr(cc_module, "_ANTHROPIC_COUNTER", lambda text: max(1, len(text) // 3))
    counter_with_lib = ClaudeTokenCounter()
    assert counter_with_lib.accuracy() == "exact"

    # And simulate "lib missing"
    monkeypatch.setattr(cc_module, "_ANTHROPIC_COUNTER", None)
    counter_without_lib = ClaudeTokenCounter()
    assert counter_without_lib.accuracy() == "approximate"
