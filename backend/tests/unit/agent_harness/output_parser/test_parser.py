"""
File: backend/tests/unit/agent_harness/output_parser/test_parser.py
Purpose: Unit tests for OutputParserImpl.parse() — Cat 6 core transformation.
Category: Tests / 範疇 6
Scope: Phase 50 / Sprint 50.1 (Day 1.4)
Created: 2026-04-29
"""

from __future__ import annotations

import pytest

from agent_harness._contracts import (
    ChatResponse,
    ContentBlock,
    StopReason,
    ToolCall,
)
from agent_harness.output_parser import OutputParserImpl, ParsedOutput


@pytest.fixture
def parser() -> OutputParserImpl:
    return OutputParserImpl()


@pytest.mark.asyncio
async def test_parse_string_content(parser: OutputParserImpl) -> None:
    """str content passes through unchanged; tool_calls empty list."""
    resp = ChatResponse(model="m", content="hello", stop_reason=StopReason.END_TURN)
    out = await parser.parse(resp)
    assert isinstance(out, ParsedOutput)
    assert out.text == "hello"
    assert out.tool_calls == []
    assert out.stop_reason == StopReason.END_TURN
    assert out.raw_response_id is None
    assert out.metadata == {}


@pytest.mark.asyncio
async def test_parse_content_block_list(parser: OutputParserImpl) -> None:
    """list[ContentBlock]: text blocks joined; non-text blocks skipped."""
    resp = ChatResponse(
        model="m",
        content=[
            ContentBlock(type="text", text="part1 "),
            ContentBlock(type="text", text="part2"),
            ContentBlock(type="image", image_url="http://x"),
        ],
        stop_reason=StopReason.END_TURN,
    )
    out = await parser.parse(resp)
    assert out.text == "part1 part2"


@pytest.mark.asyncio
async def test_parse_tool_calls_extracted(parser: OutputParserImpl) -> None:
    """tool_calls preserved as list[ToolCall]; None becomes []."""
    tc = ToolCall(id="c1", name="echo", arguments={"text": "hi"})
    resp = ChatResponse(
        model="m",
        content="",
        tool_calls=[tc],
        stop_reason=StopReason.TOOL_USE,
    )
    out = await parser.parse(resp)
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].name == "echo"
    assert out.stop_reason == StopReason.TOOL_USE


@pytest.mark.asyncio
async def test_parse_raw_response_id_from_provider(parser: OutputParserImpl) -> None:
    """raw_provider_response.id surfaces as raw_response_id."""
    resp = ChatResponse(
        model="m",
        content="ok",
        stop_reason=StopReason.END_TURN,
        raw_provider_response={"id": "resp-abc-123", "usage": {}},
    )
    out = await parser.parse(resp)
    assert out.raw_response_id == "resp-abc-123"


@pytest.mark.asyncio
async def test_parse_no_regex_text_parsing(parser: OutputParserImpl) -> None:
    """AP-9: tool_calls come from native field, NOT regex-parsed from text."""
    # text contains a fake "tool call" pattern; parser must NOT extract it
    resp = ChatResponse(
        model="m",
        content='I will call <tool name="bad_inject">{"x":1}</tool>',
        tool_calls=None,
        stop_reason=StopReason.END_TURN,
    )
    out = await parser.parse(resp)
    assert out.tool_calls == []  # only native; regex not used
