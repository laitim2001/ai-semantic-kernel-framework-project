"""
File: backend/src/adapters/azure_openai/tool_converter.py
Purpose: Convert neutral ToolSpec / Message ↔ Azure OpenAI native function-calling format.
Category: Adapters / Azure OpenAI
Scope: Phase 49 / Sprint 49.4

Description:
    The translation boundary between agent_harness/_contracts/ types and Azure
    OpenAI's `tools` / `messages` / `tool_calls` shapes. All Azure-specific JSON
    structure stays in this file; everything else in the adapter speaks neutral
    types only.

Mapping reference:
    Azure OpenAI tool format (function calling):
        {"type": "function", "function": {"name", "description", "parameters"}}

    Azure response tool_calls:
        [{"id", "type": "function", "function": {"name", "arguments"}}]

    Azure messages (content + tool_call_id for tool replies):
        - {"role": "system" | "user" | "assistant", "content": "..."}
        - {"role": "assistant", "content": null, "tool_calls": [...]}
        - {"role": "tool", "content": "...", "tool_call_id": "..."}

Created: 2026-04-29 (Sprint 49.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4)

Related:
    - adapter.py — primary consumer (wraps every chat() call)
    - adapters-layer.md (.claude/rules/) §Tool Calling 格式對應
"""

from __future__ import annotations

import json
from typing import Any

from agent_harness._contracts.chat import ContentBlock, Message, ToolCall
from agent_harness._contracts.tools import ToolSpec


def tool_spec_to_azure(spec: ToolSpec) -> dict[str, Any]:
    """Neutral ToolSpec → Azure OpenAI function-calling tool dict."""
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.input_schema,
        },
    }


def tool_specs_to_azure(specs: list[ToolSpec]) -> list[dict[str, Any]]:
    """Batch convert ToolSpecs."""
    return [tool_spec_to_azure(s) for s in specs]


def message_to_azure(msg: Message) -> dict[str, Any]:
    """Neutral Message → Azure OpenAI message dict.

    Handles three shapes:
    - Plain text content (most common)
    - Multimodal content (list[ContentBlock]) — text/image only; tool blocks excluded
    - Assistant tool_calls (Message.tool_calls populated)
    - Tool reply (role='tool' + tool_call_id)
    """
    azure: dict[str, Any] = {"role": msg.role}

    if msg.role == "tool":
        if not msg.tool_call_id:
            raise ValueError("Message(role='tool') requires tool_call_id")
        azure["tool_call_id"] = msg.tool_call_id
        azure["content"] = _content_to_text(msg.content)
        return azure

    # assistant with tool_calls — content may be None
    if msg.role == "assistant" and msg.tool_calls:
        azure["content"] = _content_to_text(msg.content) if msg.content else None
        azure["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            }
            for tc in msg.tool_calls
        ]
        return azure

    # plain text or multimodal content
    if isinstance(msg.content, str):
        azure["content"] = msg.content
    else:
        azure["content"] = _multimodal_blocks_to_azure(msg.content)

    if msg.name:
        azure["name"] = msg.name
    return azure


def messages_to_azure(messages: list[Message]) -> list[dict[str, Any]]:
    """Batch convert Messages."""
    return [message_to_azure(m) for m in messages]


def azure_tool_call_to_neutral(azure_tc: Any) -> ToolCall:
    """Azure response tool_call object → neutral ToolCall.

    Azure SDK returns objects with .id / .function.name / .function.arguments
    (a JSON string). Parse arguments back into dict.
    """
    func = getattr(azure_tc, "function", None)
    if func is None:
        # dict shape (some test fixtures or raw JSON)
        func = azure_tc.get("function", {})
        tc_id = azure_tc.get("id", "")
        name = func.get("name", "")
        args_raw = func.get("arguments", "{}")
    else:
        tc_id = azure_tc.id
        name = func.name
        args_raw = func.arguments

    try:
        args = json.loads(args_raw) if args_raw else {}
    except json.JSONDecodeError:
        args = {"_raw": args_raw}

    return ToolCall(id=tc_id, name=name, arguments=args)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _content_to_text(content: str | list[ContentBlock]) -> str:
    """Flatten content to plain text (used for tool replies which must be string)."""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if block.type == "text" and block.text:
            parts.append(block.text)
        elif block.type == "tool_result" and block.tool_result_content:
            parts.append(block.tool_result_content)
    return "\n".join(parts)


def _multimodal_blocks_to_azure(blocks: list[ContentBlock]) -> list[dict[str, Any]]:
    """Convert text + image blocks to Azure multimodal content array.

    Tool blocks (tool_use / tool_result) are skipped here — they belong on
    `tool_calls` field or in role='tool' messages.
    """
    azure: list[dict[str, Any]] = []
    for b in blocks:
        if b.type == "text" and b.text:
            azure.append({"type": "text", "text": b.text})
        elif b.type == "image" and b.image_url:
            azure.append({"type": "image_url", "image_url": {"url": b.image_url}})
    return azure
