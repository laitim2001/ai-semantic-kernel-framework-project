"""
File: backend/src/agent_harness/memory/extraction.py
Purpose: Session -> User memory extraction worker (manual-trigger in 51.2).
Category: 範疇 3 (Memory) / Extraction
Scope: Phase 51 / Sprint 51.2 Day 3

Description:
    MemoryExtractor reads session messages, prompts the LLM (via the
    middle-of-chain ChatClient ABC, preserving Provider Neutrality), and
    writes extracted user-level facts into UserLayer.

    51.2 design choices:
    - Manual trigger only (test calls extract_session_to_user() directly).
      Celery / Redis queue auto-trigger lands in CARRY-027 (Phase 53.1).
    - LLM judge prompt is minimal: "extract user preferences as JSON
      array; each item has content + confidence (0-1)".
    - Extraction uses ChatClient ABC; agent_harness must NOT import
      openai/anthropic directly (per llm-provider-neutrality.md).

Owner: 01-eleven-categories-spec.md §範疇 3 (Memory) extraction worker

Carry items resolved here:
    None (CARRY-027 handles the auto-trigger queue work).

Created: 2026-04-30 (Sprint 51.2 Day 3.3)
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from adapters._base.chat_client import ChatClient
from agent_harness._contracts import ChatRequest, Message, TraceContext
from agent_harness.memory.layers.user_layer import UserLayer

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """You are a memory extraction assistant. Read the conversation \
messages and extract durable user preferences or facts that should be \
remembered across sessions. Return a strict JSON array. Each item must \
have these fields:
  - "content": short factual statement (1 sentence)
  - "confidence": float between 0.0 and 1.0

Return [] if no durable facts can be extracted. No prose, only JSON.

Conversation:
{conversation}
"""


class MemoryExtractor:
    """Extract durable user-level facts from session messages.

    51.2 manual-trigger only. Returns the list of new MemoryUser entry
    IDs that were written.
    """

    def __init__(self, chat_client: ChatClient, user_layer: UserLayer) -> None:
        self._chat_client = chat_client
        self._user_layer = user_layer

    async def extract_session_to_user(
        self,
        *,
        session_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        messages: list[Message],
        trace_context: TraceContext | None = None,
    ) -> list[UUID]:
        if not messages:
            return []

        conversation_text = self._render_messages(messages)
        prompt = _EXTRACTION_PROMPT.format(conversation=conversation_text)

        request = ChatRequest(
            messages=[Message(role="user", content=prompt)],
            temperature=0.0,  # extraction is deterministic-ish
        )
        response = await self._chat_client.chat(
            request,
            trace_context=trace_context,
        )

        extracted = self._parse_extraction(self._content_text(response.content))
        if not extracted:
            return []

        new_ids: list[UUID] = []
        for item in extracted:
            content = item.get("content")
            confidence = float(item.get("confidence", 0.6))
            if not isinstance(content, str) or not content.strip():
                continue

            entry_id = await self._user_layer.write(
                content=content.strip(),
                tenant_id=tenant_id,
                user_id=user_id,
                time_scale="long_term",
                confidence=max(0.0, min(1.0, confidence)),
                trace_context=trace_context,
            )
            new_ids.append(entry_id)

        return new_ids

    @staticmethod
    def _render_messages(messages: list[Message]) -> str:
        lines: list[str] = []
        for msg in messages:
            text = MemoryExtractor._content_text(msg.content)
            lines.append(f"[{msg.role}] {text}")
        return "\n".join(lines)

    @staticmethod
    def _content_text(content: object) -> str:
        """Extract plain text from a Message.content that may be str or
        a list[ContentBlock] (per chat ABC).
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    parts.append(text)
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _parse_extraction(raw: str) -> list[dict[str, Any]]:
        """Parse the LLM response. Tolerant: extracts the first JSON array
        substring if extra prose surrounds it.
        """
        text = raw.strip()
        if not text:
            return []

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            # Try to locate first '[' ... ']' block
            start = text.find("[")
            end = text.rfind("]")
            if start == -1 or end == -1 or end <= start:
                logger.warning("MemoryExtractor: no JSON array found in response")
                return []
            try:
                obj = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                logger.warning("MemoryExtractor: response is not valid JSON")
                return []

        if not isinstance(obj, list):
            return []
        return [item for item in obj if isinstance(item, dict)]


__all__ = ["MemoryExtractor"]
