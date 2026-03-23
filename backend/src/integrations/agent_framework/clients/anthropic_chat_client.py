"""
PoC: AnthropicChatClient — Anthropic API wrapped as MAF BaseChatClient.

Implements the single abstract method required by installed RC4 BaseChatClient:
  _inner_get_response(*, messages, stream, options, **kwargs)
    - stream=False → return Awaitable[ChatResponse]
    - stream=True  → return ResponseStream[ChatResponseUpdate, ChatResponse]

Key difference from reference code: installed RC4 has ONE abstract method
(with stream param), not two separate methods.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterable, Mapping, Sequence
from typing import Any, ClassVar

from anthropic import AsyncAnthropic

from agent_framework import (
    BaseChatClient,
    ChatResponse,
    ChatResponseUpdate,
    Content,
    Message,
    ResponseStream,
)

logger = logging.getLogger(__name__)


class AnthropicChatClient(BaseChatClient):
    """Wraps Anthropic Messages API as a MAF BaseChatClient.

    Supports Extended Thinking via thinking_config parameter.
    """

    OTEL_PROVIDER_NAME: ClassVar[str] = "anthropic"

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        thinking_config: dict | None = None,
        max_tokens: int = 16000,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = AsyncAnthropic(api_key=self._api_key)
        self._model = model
        self._thinking_config = thinking_config
        self._max_tokens = max_tokens
        logger.info(f"AnthropicChatClient initialized: model={model}")

    # ── Single abstract method (RC4 installed API) ──

    def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ):
        """Send a chat request to Anthropic API.

        Args:
            messages: MAF Message sequence
            stream: If True, return ResponseStream; if False, return awaitable ChatResponse
            options: Validated options dict
        """
        if stream:
            return self._build_response_stream(self._stream_anthropic(messages, options))
        else:
            return self._call_anthropic(messages, options)

    # ── Non-streaming implementation ──

    async def _call_anthropic(
        self, messages: Sequence[Message], options: Mapping[str, Any]
    ) -> ChatResponse:
        """Call Anthropic API and return ChatResponse."""
        anthropic_messages = self._convert_messages_to_anthropic(messages)

        request_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": options.get("max_tokens", self._max_tokens),
        }

        system_msg = self._extract_system_message(messages)
        if system_msg:
            request_kwargs["system"] = system_msg

        if self._thinking_config:
            request_kwargs["thinking"] = self._thinking_config

        logger.info(f"Calling Anthropic API: model={self._model}")
        response = await self._client.messages.create(**request_kwargs)
        logger.info(
            f"Anthropic response: model={response.model}, "
            f"input={response.usage.input_tokens}, output={response.usage.output_tokens}"
        )

        return self._convert_response_to_maf(response)

    # ── Streaming implementation ──

    async def _stream_anthropic(
        self, messages: Sequence[Message], options: Mapping[str, Any]
    ) -> AsyncIterable[ChatResponseUpdate]:
        """Stream from Anthropic API, yielding ChatResponseUpdate chunks."""
        anthropic_messages = self._convert_messages_to_anthropic(messages)

        request_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": options.get("max_tokens", self._max_tokens),
        }

        system_msg = self._extract_system_message(messages)
        if system_msg:
            request_kwargs["system"] = system_msg

        if self._thinking_config:
            request_kwargs["thinking"] = self._thinking_config

        logger.info(f"Streaming from Anthropic API: model={self._model}")

        async with self._client.messages.stream(**request_kwargs) as stream:
            async for text in stream.text_stream:
                yield ChatResponseUpdate(
                    role="assistant",
                    contents=[Content(type="text", text=text)],
                    model_id=self._model,
                )

    # ── Conversion helpers ──

    def _convert_messages_to_anthropic(
        self, messages: Sequence[Message]
    ) -> list[dict[str, str]]:
        """Convert MAF Message[] → Anthropic message format."""
        result = []
        for msg in messages:
            role_str = str(getattr(msg, "role", "user"))
            if "assistant" in role_str.lower():
                role = "assistant"
            elif "system" in role_str.lower():
                continue
            else:
                role = "user"

            text = getattr(msg, "text", None) or ""
            if not text and hasattr(msg, "contents") and msg.contents:
                for content in msg.contents:
                    if hasattr(content, "text"):
                        text += content.text

            if text:
                result.append({"role": role, "content": text})

        return result

    def _extract_system_message(self, messages: Sequence[Message]) -> str | None:
        """Extract system message for Anthropic's top-level system param."""
        for msg in messages:
            role_str = str(getattr(msg, "role", ""))
            if "system" in role_str.lower():
                return getattr(msg, "text", None) or ""
        return None

    def _convert_response_to_maf(self, anthropic_response: Any) -> ChatResponse:
        """Convert Anthropic Messages response → MAF ChatResponse."""
        text_parts = []
        thinking_parts = []
        for block in anthropic_response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif hasattr(block, "thinking"):
                thinking_parts.append(block.thinking)

        full_text = "\n".join(text_parts)

        assistant_message = Message(role="assistant", text=full_text)

        response = ChatResponse(
            messages=[assistant_message],
            response_id=anthropic_response.id,
            model_id=anthropic_response.model,
            finish_reason=anthropic_response.stop_reason or "stop",
        )

        if thinking_parts:
            if response.additional_properties is None:
                response.additional_properties = {}
            response.additional_properties["thinking"] = thinking_parts

        return response
