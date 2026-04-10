"""
AnthropicChatClient — Anthropic API wrapped as MAF BaseChatClient + FunctionInvocationLayer.

Supports:
  - Text generation (chat)
  - Extended Thinking
  - Function calling (tool use) via FunctionInvocationLayer mixin
  - Streaming

MRO: AnthropicChatClient → FunctionInvocationLayer → BaseChatClient → ...
The FunctionInvocationLayer wraps get_response() with automatic tool call loop.
We just need to pass tools to Anthropic API and parse tool_use blocks in response.
"""

from __future__ import annotations

import json
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
    FunctionInvocationLayer,
    Message,
    ResponseStream,
)

logger = logging.getLogger(__name__)


class AnthropicChatClient(FunctionInvocationLayer, BaseChatClient):
    """Wraps Anthropic Messages API as MAF ChatClient with function calling.

    Inherits FunctionInvocationLayer to enable MAF's automatic tool call loop.
    This means Agent(this_client, tools=[...]) will work correctly.
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
        # FunctionInvocationLayer and BaseChatClient both use **kwargs + super()
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = AsyncAnthropic(api_key=self._api_key)
        self._model = model
        self._thinking_config = thinking_config
        self._max_tokens = max_tokens
        logger.info(f"AnthropicChatClient initialized: model={model}, function_calling=enabled")

    # ── Single abstract method (RC4 installed API) ──

    def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ):
        # When tools are present and streaming requested, use a non-streaming
        # call wrapped as a single-chunk stream (text_stream can't capture tool_use)
        has_tools = bool(self._extract_tools_from_options(options))
        if stream and has_tools:
            # Wrap non-streaming call as a single-update stream
            return self._build_response_stream(
                self._call_anthropic_as_stream(messages, options)
            )
        elif stream:
            return self._build_response_stream(self._stream_anthropic(messages, options))
        else:
            return self._call_anthropic(messages, options)

    # ── Non-streaming with tool support ──

    async def _call_anthropic(
        self, messages: Sequence[Message], options: Mapping[str, Any]
    ) -> ChatResponse:
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

        # Convert MAF tools to Anthropic format
        tools = self._extract_tools_from_options(options)
        if tools:
            request_kwargs["tools"] = tools

        logger.info(f"Calling Anthropic API: model={self._model}, tools={len(tools) if tools else 0}")
        response = await self._client.messages.create(**request_kwargs)
        logger.info(
            f"Anthropic response: model={response.model}, "
            f"stop_reason={response.stop_reason}, "
            f"input={response.usage.input_tokens}, output={response.usage.output_tokens}"
        )

        return self._convert_response_to_maf(response)

    # ── Non-streaming as single-chunk stream (for tool calls) ──

    async def _call_anthropic_as_stream(
        self, messages: Sequence[Message], options: Mapping[str, Any]
    ) -> AsyncIterable[ChatResponseUpdate]:
        """Call non-streaming API, yield result as single ChatResponseUpdate.

        Used when tools are present — streaming text_stream can't capture tool_use blocks.
        """
        response = await self._call_anthropic(messages, options)
        # Convert ChatResponse → single ChatResponseUpdate with all contents
        msg = response.messages[0] if response.messages else None
        if msg and msg.contents:
            yield ChatResponseUpdate(
                role="assistant",
                contents=msg.contents,
                model_id=self._model,
            )
        elif hasattr(response, "text") and response.text:
            yield ChatResponseUpdate(
                role="assistant",
                contents=[Content(type="text", text=response.text)],
                model_id=self._model,
            )

    # ── Streaming ──

    async def _stream_anthropic(
        self, messages: Sequence[Message], options: Mapping[str, Any]
    ) -> AsyncIterable[ChatResponseUpdate]:
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

        tools = self._extract_tools_from_options(options)
        if tools:
            request_kwargs["tools"] = tools

        logger.info(f"Streaming from Anthropic API: model={self._model}")

        async with self._client.messages.stream(**request_kwargs) as stream:
            async for text in stream.text_stream:
                yield ChatResponseUpdate(
                    role="assistant",
                    contents=[Content(type="text", text=text)],
                    model_id=self._model,
                )

    # ── Tool conversion: MAF → Anthropic ──

    def _extract_tools_from_options(self, options: Mapping[str, Any]) -> list[dict] | None:
        """Extract tools from MAF options and convert to Anthropic format."""
        tools_raw = options.get("tools")
        if not tools_raw:
            return None

        anthropic_tools = []
        for tool in tools_raw:
            if hasattr(tool, "name") and hasattr(tool, "description"):
                # MAF FunctionTool → Anthropic tool format
                tool_def: dict[str, Any] = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": {"type": "object", "properties": {}, "required": []},
                }
                # Extract schema from input_model if available
                if hasattr(tool, "input_model") and tool.input_model:
                    if hasattr(tool.input_model, "model_json_schema"):
                        schema = tool.input_model.model_json_schema()
                        tool_def["input_schema"] = schema
                    elif isinstance(tool.input_model, dict):
                        tool_def["input_schema"] = tool.input_model

                anthropic_tools.append(tool_def)

        return anthropic_tools if anthropic_tools else None

    # ── Message conversion: MAF → Anthropic ──

    def _convert_messages_to_anthropic(
        self, messages: Sequence[Message]
    ) -> list[dict[str, Any]]:
        """Convert MAF Message[] → Anthropic message format.

        Handles text, function_call (tool_use), and function_result (tool_result).
        Ensures tool_use/tool_result are always properly paired — unpaired ones
        are stripped to avoid Anthropic 400 errors in GroupChat context.
        """
        raw_messages = []
        for msg in messages:
            role_str = str(getattr(msg, "role", "user"))
            if "system" in role_str.lower():
                continue

            if "assistant" in role_str.lower():
                role = "assistant"
            elif "tool" in role_str.lower():
                role = "user"
            else:
                role = "user"

            contents = getattr(msg, "contents", None) or []
            text_parts = []
            tool_uses = []
            tool_results = []

            for c in contents:
                c_type = getattr(c, "type", None)
                if c_type and hasattr(c_type, "value"):
                    c_type = c_type.value

                if c_type == "function_call":
                    call_id = getattr(c, "call_id", None) or getattr(c, "id", "")
                    name = getattr(c, "name", "")
                    arguments = getattr(c, "arguments", "{}")
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except (json.JSONDecodeError, TypeError):
                            arguments = {}
                    tool_uses.append({
                        "type": "tool_use", "id": call_id,
                        "name": name, "input": arguments,
                    })
                elif c_type == "function_result":
                    call_id = getattr(c, "call_id", None) or getattr(c, "id", "")
                    res = getattr(c, "result", "")
                    if not isinstance(res, str):
                        res = str(res)
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": call_id,
                        "content": res,
                    })
                elif hasattr(c, "text") and c.text:
                    text_parts.append(c.text)

            raw_messages.append({
                "role": role, "text_parts": text_parts,
                "tool_uses": tool_uses, "tool_results": tool_results,
            })

        # Build final message list, ensuring tool_use/tool_result pairs
        result = []
        i = 0
        while i < len(raw_messages):
            m = raw_messages[i]

            if m["tool_uses"] and i + 1 < len(raw_messages) and raw_messages[i + 1]["tool_results"]:
                # Paired: assistant tool_use + user tool_result
                assistant_content = []
                if m["text_parts"]:
                    for t in m["text_parts"]:
                        assistant_content.append({"type": "text", "text": t})
                assistant_content.extend(m["tool_uses"])
                result.append({"role": "assistant", "content": assistant_content})

                user_content = raw_messages[i + 1]["tool_results"]
                result.append({"role": "user", "content": user_content})
                i += 2
            elif m["tool_uses"]:
                # Unpaired tool_use (from GroupChat history) — strip to text only
                text = " ".join(m["text_parts"]) if m["text_parts"] else "(tool call executed)"
                if text:
                    result.append({"role": m["role"], "content": text})
                i += 1
            elif m["tool_results"]:
                # Orphan tool_result — skip
                i += 1
            else:
                # Plain text message
                text = " ".join(m["text_parts"]) if m["text_parts"] else ""
                if not text:
                    text = getattr(messages[i], "text", None) or ""
                if text:
                    result.append({"role": m["role"], "content": text})
                i += 1

        # Anthropic requires alternating user/assistant — merge consecutive same-role
        if result:
            merged = [result[0]]
            for msg in result[1:]:
                if msg["role"] == merged[-1]["role"]:
                    # Merge content
                    prev = merged[-1]["content"]
                    curr = msg["content"]
                    if isinstance(prev, str) and isinstance(curr, str):
                        merged[-1]["content"] = prev + "\n" + curr
                    elif isinstance(prev, str):
                        merged[-1]["content"] = [{"type": "text", "text": prev}] + (curr if isinstance(curr, list) else [curr])
                    elif isinstance(curr, str):
                        merged[-1]["content"] = prev + [{"type": "text", "text": curr}]
                    else:
                        merged[-1]["content"] = prev + curr
                else:
                    merged.append(msg)
            result = merged

        return result

        return result

    def _extract_system_message(self, messages: Sequence[Message]) -> str | None:
        for msg in messages:
            role_str = str(getattr(msg, "role", ""))
            if "system" in role_str.lower():
                return getattr(msg, "text", None) or ""
        return None

    # ── Response conversion: Anthropic → MAF ──

    def _convert_response_to_maf(self, anthropic_response: Any) -> ChatResponse:
        """Convert Anthropic response → MAF ChatResponse.

        Handles both text and tool_use blocks.
        """
        maf_contents: list[Content] = []
        text_parts = []
        thinking_parts = []

        for block in anthropic_response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                # Tool call → MAF Content(type='function_call')
                arguments = block.input
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments)
                maf_contents.append(Content(
                    type="function_call",
                    call_id=block.id,
                    name=block.name,
                    arguments=arguments,
                ))
            elif hasattr(block, "text"):
                text_parts.append(block.text)
                maf_contents.append(Content(type="text", text=block.text))
            elif hasattr(block, "thinking"):
                thinking_parts.append(block.thinking)

        full_text = "\n".join(text_parts)

        # Build message with all contents
        assistant_message = Message(
            role="assistant",
            contents=maf_contents if maf_contents else None,
            text=full_text if full_text else None,
        )

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
