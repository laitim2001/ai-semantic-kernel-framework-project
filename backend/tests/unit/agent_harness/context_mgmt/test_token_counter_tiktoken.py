"""
File: tests/unit/agent_harness/context_mgmt/test_token_counter_tiktoken.py
Purpose: Unit tests for TiktokenCounter (impl: token_counter/tiktoken_counter.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 3.7

5 tests:
  - test_count_plain_text
  - test_count_messages_with_role_overhead
  - test_count_with_tools_schema
  - test_handles_model_variants
  - test_accuracy_returns_exact
"""

from __future__ import annotations

import pytest

from agent_harness._contracts import Message, ToolSpec
from agent_harness.context_mgmt.token_counter.tiktoken_counter import TiktokenCounter


def test_count_plain_text() -> None:
    """Empty messages and no tools → 0 tokens (aligns with adapter count_tokens([]) contract)."""
    c = TiktokenCounter(model="gpt-4o")
    assert c.count(messages=[]) == 0


def test_count_messages_with_role_overhead() -> None:
    """Message with single text content → request_overhead(3) + per_message(3) + role_tokens + content_tokens."""
    c = TiktokenCounter(model="gpt-4o")
    msg = Message(role="user", content="Hi")
    n = c.count(messages=[msg])
    # 3 request + 3 per_message + 1 'user' role + at least 1 'Hi' content = >= 8
    assert n >= 8
    # Same content twice should be approximately double the content portion
    n2 = c.count(messages=[msg, msg])
    assert n2 > n
    assert n2 - n >= 4  # at least per_message + role + content


def test_count_with_tools_schema() -> None:
    """Including a ToolSpec must add tokens for the schema serialisation."""
    c = TiktokenCounter(model="gpt-4o")
    msg = Message(role="user", content="hi")

    base = c.count(messages=[msg])
    tool = ToolSpec(
        name="db_query",
        description="Run a read-only SQL query against the warehouse.",
        input_schema={
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    )
    with_tool = c.count(messages=[msg], tools=[tool])
    assert with_tool > base
    # Schema has at least name + description + parameters = several tokens
    assert with_tool - base >= 10


def test_handles_model_variants() -> None:
    """gpt-4o uses o200k_base; gpt-3.5 uses cl100k_base — counts may differ but both work."""
    c_4o = TiktokenCounter(model="gpt-4o")
    c_35 = TiktokenCounter(model="gpt-3.5-turbo")
    msg = Message(role="user", content="hello world")
    n_4o = c_4o.count(messages=[msg])
    n_35 = c_35.count(messages=[msg])
    assert n_4o > 0
    assert n_35 > 0
    # Both encodings give plausible counts (not zero, not absurd)
    assert n_4o < 100
    assert n_35 < 100
    # The two encodings should be selected from the model names
    assert c_4o._encoding_name == "o200k_base"
    assert c_35._encoding_name == "cl100k_base"


def test_accuracy_returns_exact() -> None:
    """TiktokenCounter advertises exact accuracy."""
    c = TiktokenCounter(model="gpt-4o")
    assert c.accuracy() == "exact"
