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


def test_count_via_injected_tokenizer_or_fallback() -> None:
    """Counter returns a positive token estimate regardless of which path is active."""
    counter = ClaudeTokenCounter()
    msgs = [Message(role="user", content="hello world")]
    n = counter.count(messages=msgs)
    assert n > 0
    # Reasonable upper bound for short message
    assert n < 50


def test_fallback_to_approx_when_no_tokenizer_injected() -> None:
    """No tokenizer injected → 4-chars/token heuristic active; accuracy=approximate."""
    counter = ClaudeTokenCounter()  # default: no DI
    msg = Message(role="user", content="a" * 16)
    n = counter.count(messages=[msg])
    # 3 per_message + ceil("user"/4=1) + ceil(16/4=4) = 8
    assert n == 3 + 1 + 4
    assert counter.accuracy() == "approximate"


def test_accuracy_returns_appropriate_value() -> None:
    """accuracy() reflects whether an exact tokenizer was injected via DI."""
    # Default: no tokenizer → approximate
    counter_default = ClaudeTokenCounter()
    assert counter_default.accuracy() == "approximate"

    # Inject an exact tokenizer (simulates what an Anthropic adapter would do)
    fake_exact_tokenizer = lambda text: max(1, len(text) // 3)  # noqa: E731
    counter_with_lib = ClaudeTokenCounter(tokenizer_callable=fake_exact_tokenizer)
    assert counter_with_lib.accuracy() == "exact"

    # force_approximate=True overrides even an injected exact tokenizer
    counter_forced = ClaudeTokenCounter(
        tokenizer_callable=fake_exact_tokenizer,
        force_approximate=True,
    )
    assert counter_forced.accuracy() == "approximate"
