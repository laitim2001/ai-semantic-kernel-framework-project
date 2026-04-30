"""
File: backend/tests/unit/agent_harness/output_parser/test_stop_reason_mapping.py
Purpose: Verify StopReason enum is preserved verbatim through OutputParser.
Category: Tests / 範疇 6
Scope: Phase 50 / Sprint 50.1 (Day 1.3)

Description:
    Cat 6 must NOT translate / re-map StopReason — adapters do that. The
    parser only carries the neutral enum forward. This file tests preservation
    for all 6 StopReason values plus a couple of cross scenarios.

Created: 2026-04-29
"""

from __future__ import annotations

import pytest

from agent_harness._contracts import ChatResponse, StopReason, ToolCall
from agent_harness.output_parser import OutputParserImpl


@pytest.fixture
def parser() -> OutputParserImpl:
    return OutputParserImpl()


@pytest.mark.parametrize("stop", list(StopReason))
@pytest.mark.asyncio
async def test_stop_reason_preserved_pure_text(
    parser: OutputParserImpl, stop: StopReason
) -> None:
    """Each StopReason value is carried through parse() unchanged."""
    resp = ChatResponse(model="m", content="x", stop_reason=stop)
    out = await parser.parse(resp)
    assert out.stop_reason is stop


@pytest.mark.parametrize("stop", list(StopReason))
@pytest.mark.asyncio
async def test_stop_reason_preserved_with_tool_calls(
    parser: OutputParserImpl, stop: StopReason
) -> None:
    """StopReason preserved even when ChatResponse carries tool_calls."""
    resp = ChatResponse(
        model="m",
        content="",
        tool_calls=[ToolCall(id="1", name="t", arguments={})],
        stop_reason=stop,
    )
    out = await parser.parse(resp)
    assert out.stop_reason is stop


@pytest.mark.asyncio
async def test_stop_reason_default_end_turn_preserved(
    parser: OutputParserImpl,
) -> None:
    """When ChatResponse omits stop_reason, dataclass default is END_TURN."""
    resp = ChatResponse(model="m", content="hi")
    out = await parser.parse(resp)
    assert out.stop_reason is StopReason.END_TURN
