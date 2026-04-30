"""
File: tests/unit/agent_harness/context_mgmt/test_token_counter_generic.py
Purpose: Unit tests for GenericApproxCounter (impl: token_counter/generic_approx.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 3.9

3 tests:
  - test_plain_text_4chars_per_token
  - test_tools_buffer_adds_30_percent
  - test_accuracy_returns_approximate
"""

from __future__ import annotations

import math

from agent_harness._contracts import Message, ToolSpec
from agent_harness.context_mgmt.token_counter.generic_approx import GenericApproxCounter


def test_plain_text_4chars_per_token() -> None:
    """16-char content → ceil(16/4) = 4 tokens; plus per_message(3) + role(1) = 8."""
    counter = GenericApproxCounter()
    msg = Message(role="user", content="a" * 16)
    n = counter.count(messages=[msg])
    expected = 3 + 1 + 4  # per_message + ceil(len("user")/4) + ceil(16/4)
    assert n == expected


def test_tools_buffer_adds_30_percent() -> None:
    """Adding a tool inflates the token count by 30 % over raw schema serialisation."""
    counter = GenericApproxCounter()
    msg = Message(role="user", content="hi")

    base = counter.count(messages=[msg])
    tool = ToolSpec(
        name="db_query",
        description="Run a read-only SQL query.",
        input_schema={"type": "object", "properties": {"sql": {"type": "string"}}},
    )
    with_tool = counter.count(messages=[msg], tools=[tool])

    delta = with_tool - base
    assert delta > 0
    # Compute raw schema tokens and verify the 1.3 factor was applied.
    import json as _json
    schema = {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }
    raw_text_tokens = math.ceil(len(_json.dumps(schema, sort_keys=True, default=str)) / 4)
    expected_inflated = math.ceil(raw_text_tokens * 1.3)
    assert delta == expected_inflated


def test_accuracy_returns_approximate() -> None:
    counter = GenericApproxCounter()
    assert counter.accuracy() == "approximate"
