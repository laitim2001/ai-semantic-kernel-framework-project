"""
File: backend/tests/unit/adapters/azure_openai/test_contract.py
Purpose: Contract tests — every adapter must pass these to be considered
         a valid ChatClient implementation. Per .claude/rules/adapters-layer.md
         §Contract Test (every adapter 必通).

Category: Tests / Adapters / Contract
Scope: Phase 49 / Sprint 49.4

Description:
    These tests use the SDK's mockability via openai SDK's response objects;
    no real Azure call. Network-real tests live in test_integration.py
    (skipped by default; opt-in via @pytest.mark.integration).

Test count: 8 contract tests covering the 6 ABC methods + cancellation +
            error-mapper integration.

Created: 2026-04-29 (Sprint 49.4)
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from adapters._base.chat_client import ChatClient
from adapters._base.errors import AdapterException, ProviderError
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo
from adapters.azure_openai.adapter import AzureOpenAIAdapter
from agent_harness._contracts import ChatRequest, Message
from agent_harness._contracts.chat import StopReason

# ---------------------------------------------------------------------------
# 1. ABC compliance
# ---------------------------------------------------------------------------


class TestABCCompliance:
    def test_adapter_is_chat_client(self, azure_adapter: AzureOpenAIAdapter) -> None:
        """AzureOpenAIAdapter must satisfy ChatClient ABC (cannot be instantiated otherwise)."""
        assert isinstance(azure_adapter, ChatClient)


# ---------------------------------------------------------------------------
# 2. count_tokens — uses tiktoken locally; no network
# ---------------------------------------------------------------------------


class TestCountTokens:
    @pytest.mark.asyncio
    async def test_count_tokens_basic(
        self, azure_adapter: AzureOpenAIAdapter, sample_messages: list[Message]
    ) -> None:
        """count_tokens returns a positive int for any non-empty message list."""
        n = await azure_adapter.count_tokens(messages=sample_messages)
        assert isinstance(n, int)
        assert n > 0

    @pytest.mark.asyncio
    async def test_count_tokens_with_tools(
        self,
        azure_adapter: AzureOpenAIAdapter,
        sample_messages: list[Message],
        sample_tool: object,
    ) -> None:
        """Adding tools increases token count (schema serialization)."""
        n_no_tools = await azure_adapter.count_tokens(messages=sample_messages)
        n_with_tools = await azure_adapter.count_tokens(
            messages=sample_messages, tools=[sample_tool]  # type: ignore[list-item]
        )
        assert n_with_tools > n_no_tools


# ---------------------------------------------------------------------------
# 3. get_pricing — pure config, no network
# ---------------------------------------------------------------------------


class TestPricing:
    def test_pricing_returns_info(self, azure_adapter: AzureOpenAIAdapter) -> None:
        info = azure_adapter.get_pricing()
        assert isinstance(info, PricingInfo)
        assert info.input_per_million > 0
        assert info.output_per_million > 0
        assert info.currency == "USD"


# ---------------------------------------------------------------------------
# 4. supports_feature — pure config, no network
# ---------------------------------------------------------------------------


class TestSupportsFeature:
    @pytest.mark.parametrize(
        "feature,expected",
        [
            ("vision", True),
            ("caching", True),
            ("structured_output", True),
            ("parallel_tool_calls", True),
            ("thinking", False),
            ("audio", False),
            ("computer_use", False),
        ],
    )
    def test_feature_flags(
        self, azure_adapter: AzureOpenAIAdapter, feature: str, expected: bool
    ) -> None:
        assert azure_adapter.supports_feature(feature) is expected  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 5. model_info — pure config, no network
# ---------------------------------------------------------------------------


class TestModelInfo:
    def test_model_info_complete(self, azure_adapter: AzureOpenAIAdapter) -> None:
        info = azure_adapter.model_info()
        assert isinstance(info, ModelInfo)
        assert info.provider == "azure_openai"
        assert info.context_window > 0
        assert info.max_output_tokens > 0
        assert info.model_name == "gpt-4o"


# ---------------------------------------------------------------------------
# 6. chat — mocks the SDK call to avoid network
# ---------------------------------------------------------------------------


class TestChat:
    @pytest.mark.asyncio
    async def test_chat_returns_chat_response(
        self,
        azure_adapter: AzureOpenAIAdapter,
        sample_request: ChatRequest,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Mock the SDK; verify adapter parses response into neutral ChatResponse."""

        class _Choice:
            def __init__(self) -> None:
                self.message = SimpleNamespace(content="The answer is 4.", tool_calls=None)
                self.finish_reason = "stop"

        class _Usage:
            prompt_tokens = 12
            completion_tokens = 5
            total_tokens = 17
            prompt_tokens_details = SimpleNamespace(cached_tokens=0)

        class _Resp:
            model = "gpt-4o"
            choices = [_Choice()]
            usage = _Usage()

        async def _fake_create(**kwargs: object) -> _Resp:
            return _Resp()

        # bypass _get_client (no real Azure key); inject a stub client
        stub_client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
        )
        azure_adapter._client = stub_client  # type: ignore[assignment]

        resp = await azure_adapter.chat(sample_request)
        assert resp.model == "gpt-4o"
        assert resp.content == "The answer is 4."
        assert resp.stop_reason == StopReason.END_TURN
        assert resp.usage is not None
        assert resp.usage.prompt_tokens == 12

    @pytest.mark.asyncio
    async def test_chat_tool_calls_normalize_to_tool_use(
        self,
        azure_adapter: AzureOpenAIAdapter,
        sample_request: ChatRequest,
    ) -> None:
        """When provider returns tool_calls, stop_reason normalizes to TOOL_USE."""

        class _ToolCall:
            id = "call_1"
            function = SimpleNamespace(name="add", arguments='{"a": 1, "b": 2}')

        class _Choice:
            def __init__(self) -> None:
                self.message = SimpleNamespace(content=None, tool_calls=[_ToolCall()])
                self.finish_reason = "tool_calls"

        class _Resp:
            model = "gpt-4o"
            choices = [_Choice()]
            usage = None

        async def _fake_create(**kwargs: object) -> _Resp:
            return _Resp()

        azure_adapter._client = SimpleNamespace(  # type: ignore[assignment]
            chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
        )

        resp = await azure_adapter.chat(sample_request)
        assert resp.stop_reason == StopReason.TOOL_USE
        assert resp.tool_calls is not None
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "add"
        assert resp.tool_calls[0].arguments == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# 7. cancellation — CancelledError must propagate, not be swallowed
# ---------------------------------------------------------------------------


class TestCancellation:
    @pytest.mark.asyncio
    async def test_chat_cancellation_propagates(
        self,
        azure_adapter: AzureOpenAIAdapter,
        sample_request: ChatRequest,
    ) -> None:
        """asyncio.wait_for(timeout=tiny) → CancelledError must propagate."""

        async def _slow_create(**kwargs: object) -> object:
            await asyncio.sleep(10)
            return SimpleNamespace()

        azure_adapter._client = SimpleNamespace(  # type: ignore[assignment]
            chat=SimpleNamespace(completions=SimpleNamespace(create=_slow_create))
        )

        with pytest.raises((asyncio.TimeoutError, asyncio.CancelledError)):
            await asyncio.wait_for(azure_adapter.chat(sample_request), timeout=0.05)


# ---------------------------------------------------------------------------
# 8. error mapping — provider native exceptions become AdapterException
# ---------------------------------------------------------------------------


class TestErrorMapping:
    @pytest.mark.asyncio
    async def test_provider_error_wrapped_in_adapter_exception(
        self,
        azure_adapter: AzureOpenAIAdapter,
        sample_request: ChatRequest,
    ) -> None:
        """Any non-cancel exception is mapped to AdapterException with neutral category."""

        async def _err_create(**kwargs: object) -> object:
            raise RuntimeError("simulated provider failure")

        azure_adapter._client = SimpleNamespace(  # type: ignore[assignment]
            chat=SimpleNamespace(completions=SimpleNamespace(create=_err_create))
        )

        with pytest.raises(AdapterException) as exc_info:
            await azure_adapter.chat(sample_request)
        assert exc_info.value.category == ProviderError.UNKNOWN
        assert exc_info.value.provider == "azure_openai"
