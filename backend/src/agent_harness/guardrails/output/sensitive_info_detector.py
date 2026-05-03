"""
File: backend/src/agent_harness/guardrails/output/sensitive_info_detector.py
Purpose: Detect system-prompt leaks and cross-tenant data leaks in LLM output.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 2 (US-3)

Description:
    Two checks against output text (CRITICAL severity — both BLOCK):
      1. System prompt leak: LLM accidentally reveals its own system
         prompt / role definition / configuration.
      2. Cross-tenant leak: output contains a UUID belonging to another
         tenant (data leak across multi-tenant boundary; per
         multi-tenant-data.md rule 1).

    Cross-tenant detection requires the orchestrator to inject a list of
    "forbidden" tenant_ids — typically all known tenants other than the
    current session's tenant. Production wiring computes this once per
    session and passes via `other_tenant_fetcher` callable so the
    detector stays stateless.

    Per spec SLO `output guardrail p95 < 200ms`. System-prompt regex is
    O(text length); tenant scan is O(N tenants × text length) — for
    typical tenant counts (< 1000) and output lengths this is well under
    200ms.

Key Components:
    - SensitiveInfoDetector(Guardrail): guardrail_type = OUTPUT
    - SYSTEM_PROMPT_LEAK_PATTERNS: 4 high-precision regexes
    - TenantIdFetcher protocol: async (current_tenant) → list[other tenants]
    - _noop_fetcher: no-op default (returns []) — production injects real

Owner: 01-eleven-categories-spec.md §範疇 9 + multi-tenant-data.md §rule 2
Single-source: GuardrailResult / GuardrailAction in 17.md §1.1

Created: 2026-05-03 (Sprint 53.3 Day 2)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-3) — 2-check baseline

Related:
    - guardrails/output/toxicity_detector.py — sibling OUTPUT detector
    - tests/fixtures/guardrails/sensitive_leak_cases.yaml — accuracy fixture
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Pattern
from uuid import UUID

from agent_harness._contracts import TraceContext
from agent_harness.guardrails._abc import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
)

#: Async callable: (current_tenant_id) → list of forbidden (other) tenant_ids.
#: Production wiring injects a real fetcher backed by the tenants table.
TenantIdFetcher = Callable[[UUID], Awaitable[list[UUID]]]


async def _noop_fetcher(_tenant_id: UUID) -> list[UUID]:
    """Default fetcher: returns no forbidden tenant_ids (cross-leak check
    is a no-op until production injects a real fetcher).
    """
    return []


class SensitiveInfoDetector(Guardrail):
    """Detects system-prompt leaks + cross-tenant leaks in OUTPUT.

    Args:
        other_tenant_fetcher: async callable returning list of UUIDs that
            should NOT appear in this tenant's output. Default returns
            empty list (cross-tenant check disabled). Production wiring
            should inject a real fetcher per session.

    Action policy: any match → BLOCK with risk_level=CRITICAL.
    """

    guardrail_type = GuardrailType.OUTPUT

    SYSTEM_PROMPT_LEAK_PATTERNS: ClassVar[list[Pattern[str]]] = [
        # "You are a/an X agent/assistant/AI" — common system prompt opener.
        # Allows up to 3 modifier words between determiner and role noun
        # (e.g. "You are an IT operations assistant", "You are the patrol agent").
        re.compile(
            r"You\s+are\s+(?:a|an|the)\s+(?:\w+\s+){0,3}" r"(?:agent|assistant|AI|chatbot|bot)",
            re.IGNORECASE,
        ),
        # XML-style system tag
        re.compile(r"<system>.*?</system>", re.DOTALL | re.IGNORECASE),
        # OpenAI-style "system: You are ..."
        re.compile(
            r"system\s*:\s*['\"]?[Yy]ou\s+are\b",
            re.IGNORECASE,
        ),
        # Role definition
        re.compile(
            r"\bYour\s+(?:role|task|primary\s+function)\s+is\s+to\b",
            re.IGNORECASE,
        ),
    ]

    def __init__(
        self,
        *,
        other_tenant_fetcher: TenantIdFetcher | None = None,
    ) -> None:
        self._fetcher: TenantIdFetcher = other_tenant_fetcher or _noop_fetcher

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        text = self._extract_text(content)

        # Check 1: system prompt leak (no tenant context required)
        for pattern in self.SYSTEM_PROMPT_LEAK_PATTERNS:
            match = pattern.search(text)
            if match:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=f"system prompt leak: matched {pattern.pattern!r}",
                    risk_level="CRITICAL",
                )

        # Check 2: cross-tenant leak (requires tenant_id in trace context)
        if trace_context is not None and trace_context.tenant_id is not None:
            forbidden = await self._fetcher(trace_context.tenant_id)
            for tid in forbidden:
                if str(tid) in text:
                    return GuardrailResult(
                        action=GuardrailAction.BLOCK,
                        reason=f"cross-tenant leak: {tid} (current={trace_context.tenant_id})",
                        risk_level="CRITICAL",
                    )

        return GuardrailResult(action=GuardrailAction.PASS)

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Same flatten contract as sibling detectors."""
        if isinstance(content, str):
            return content
        inner = getattr(content, "content", None)
        if inner is not None:
            if isinstance(inner, str):
                return inner
            if isinstance(inner, list):
                parts: list[str] = []
                for block in inner:
                    if isinstance(block, dict):
                        for key in ("text", "content"):
                            value = block.get(key)
                            if isinstance(value, str):
                                parts.append(value)
                                break
                    elif isinstance(block, str):
                        parts.append(block)
                return " ".join(parts)
        return str(content)
