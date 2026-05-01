"""
File: backend/src/agent_harness/context_mgmt/observation_masker.py
Purpose: DefaultObservationMasker — redacts old role="tool" message bodies while keeping tool_calls intact.  # noqa: E501
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1 Day 3

Description:
    DefaultObservationMasker preserves the *fact* that tools were called by
    keeping every assistant message's `tool_calls` field, but replaces the
    body of old `role="tool"` messages (older than `keep_recent` user→
    assistant turns) with a tombstone string of the form:

        "[REDACTED: tool {name} result; bytes={n}]"

    Effect: the agent still knows it called tool X, but the heavy result
    blob no longer occupies tokens. role="user" / "system" / "assistant"
    content is never touched.

Why this exists:
    V1 ignored context rot (AP-7). Long conversations blew context windows
    not on user/assistant text but on stale tool result blobs that no
    longer matter. Masking is a cheap structural mitigation that runs
    before LLM-driven semantic compaction.

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1 (ObservationMasker row)

Related:
    - _abc.py ObservationMasker ABC
    - compactor/structural.py (Day 3.3 — wires injection of this masker)
    - 04-anti-patterns.md AP-7 (Context Rot Ignored — root motivation)

Created: 2026-05-01 (Sprint 52.1 Day 3.1)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 3.1) — default masker impl
"""

from __future__ import annotations

from dataclasses import replace

from agent_harness._contracts import Message
from agent_harness.context_mgmt._abc import ObservationMasker


class DefaultObservationMasker(ObservationMasker):
    """Tombstone-style masker; keeps tool_calls field, redacts old tool bodies."""

    def mask_old_results(
        self,
        messages: list[Message],
        *,
        keep_recent: int = 5,
    ) -> list[Message]:
        if not messages:
            return []

        # Anchor "turn" boundaries on user messages: the keep_recent-th-from-last
        # user message marks the cutoff. Everything from that user onwards is
        # untouched; older role="tool" messages get tombstoned.
        user_indices = [i for i, m in enumerate(messages) if m.role == "user"]
        if len(user_indices) <= keep_recent:
            return list(messages)

        cutoff_idx = user_indices[-keep_recent]

        out: list[Message] = []
        for i, msg in enumerate(messages):
            if msg.role == "tool" and i < cutoff_idx:
                tool_name = msg.name or "unknown"
                content_str = msg.content if isinstance(msg.content, str) else "[content blocks]"
                byte_count = len(content_str) if isinstance(content_str, str) else 0
                tombstone = f"[REDACTED: tool {tool_name} result; bytes={byte_count}]"
                out.append(replace(msg, content=tombstone))
            else:
                out.append(msg)
        return out
