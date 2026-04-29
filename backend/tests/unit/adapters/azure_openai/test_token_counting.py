"""
File: backend/tests/unit/adapters/azure_openai/test_token_counting.py
Purpose: Verify count_tokens() against tiktoken behavior on known inputs.
Category: Tests / Adapters / Azure OpenAI
Scope: Phase 49 / Sprint 49.4
"""

from __future__ import annotations

import pytest

from adapters.azure_openai.adapter import AzureOpenAIAdapter
from agent_harness._contracts import Message


@pytest.mark.asyncio
async def test_count_tokens_empty_messages(azure_adapter: AzureOpenAIAdapter) -> None:
    n = await azure_adapter.count_tokens(messages=[])
    assert n == 0


@pytest.mark.asyncio
async def test_count_tokens_single_short_message(
    azure_adapter: AzureOpenAIAdapter,
) -> None:
    msg = Message(role="user", content="Hello")
    n = await azure_adapter.count_tokens(messages=[msg])
    # overhead 4 + role + 1-token "Hello" + tokens — should be > 4
    assert n > 4
    assert n < 50


@pytest.mark.asyncio
async def test_count_tokens_scales_with_content(
    azure_adapter: AzureOpenAIAdapter,
) -> None:
    short = Message(role="user", content="Hi")
    long = Message(role="user", content="Hello " * 200)
    n_short = await azure_adapter.count_tokens(messages=[short])
    n_long = await azure_adapter.count_tokens(messages=[long])
    assert n_long > n_short * 5  # long message significantly larger
