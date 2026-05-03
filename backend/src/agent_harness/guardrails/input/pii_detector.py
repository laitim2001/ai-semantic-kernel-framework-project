"""
File: backend/src/agent_harness/guardrails/input/pii_detector.py
Purpose: Regex-based PII (Personally Identifiable Information) detector for input guardrail chain.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 1 (US-2 上半)

Description:
    Detects email / phone / SSN / credit card patterns in user input.
    Two-tier policy:
      - 0 hits           → PASS
      - 1 hit  (suspect) → ESCALATE (risk=MEDIUM) → loop routes to HITL
      - >= threshold     → BLOCK    (risk=HIGH)   → loop refuses request

    The threshold (default 2) keeps false-positive impact low: a single
    isolated email may legitimately appear in normal conversation
    (`"My email is john@example.com — what should I write?"`); a cluster
    of multiple PII types (`"Email john@x.com, phone +1-555-1234, ssn
    123-45-6789"`) is an active leak and must be blocked outright.

    Defense-in-depth: this layer is regex-only (< 10ms p95). A future
    layer can add LLM-as-judge for cases where regex is uncertain
    (US-2 plan §future enhancement; not in 53.3 scope).

    Per spec SLO `input guardrail p95 < 100ms`; regex-only path stays
    well under that. Per plan §accuracy `PII detection accuracy ≥ 95%`
    on red-team fixture (tests/fixtures/guardrails/pii_redteam.yaml).

Key Components:
    - PIIDetector(Guardrail): guardrail_type = INPUT
    - PATTERNS: 4 compiled regexes (email / phone / ssn / credit_card)
    - _extract_text: unwraps Message / dict / list content blocks → flat text

Owner: 01-eleven-categories-spec.md §範疇 9 (PII / jailbreak detection)
Single-source: GuardrailResult / GuardrailAction in 17.md §1.1

Created: 2026-05-03 (Sprint 53.3 Day 1)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-2) — regex-only impl

Related:
    - guardrails/_abc.py — Guardrail ABC contract
    - guardrails/engine.py — registers PIIDetector in INPUT chain
    - tests/fixtures/guardrails/pii_redteam.yaml — accuracy fixture (≥ 30 +/-)
"""

from __future__ import annotations

import re
from typing import Any, ClassVar, Pattern

from agent_harness._contracts import TraceContext
from agent_harness.guardrails._abc import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
)


class PIIDetector(Guardrail):
    """Regex-based PII detector for INPUT guardrail chain.

    Args:
        llm_judge_threshold: minimum total hit count to escalate from
            ESCALATE to BLOCK. Default 2 (one isolated PII = ESCALATE,
            two or more = BLOCK).

    Action policy:
        0 hits           → PASS
        1 hit, < threshold → ESCALATE (MEDIUM) — single suspect, route to HITL
        >= threshold      → BLOCK    (HIGH)   — active leak, refuse outright
    """

    guardrail_type = GuardrailType.INPUT

    # Compiled patterns. Tuned for high precision (≥ 95% accuracy target):
    # - email: standard local@domain.tld; allows + and . in local part
    # - phone: international + US/HK formats; requires reasonable digit count
    # - ssn: US format ###-##-#### with word boundaries (avoids dates / IDs)
    # - credit_card: 13-19 digits with optional separators; word-bounded
    PATTERNS: ClassVar[dict[str, Pattern[str]]] = {
        "email": re.compile(r"[\w\.\-\+]+@[\w\.\-]+\.\w{2,}", re.IGNORECASE),
        # phone: requires BOTH separators (dash/space/dot/parens) to avoid
        # matching generic numeric strings like "12345" or "987654321".
        # Accepts: "+1-555-123-4567", "555-123-4567", "(555) 123-4567",
        #          "+852 9123 4567", "555.123.4567"
        # Lookaround guards prevent partial-match within a credit card
        # like "5500 0000 0000 0004" (which has digit-sep-digit chunks
        # that look phone-like in isolation):
        #   `(?<!\d[-.\s])` — not preceded by a digit-then-separator
        #   `(?![-.\s]?\d)` — not followed by an optional-separator-then-digit
        "phone": re.compile(
            r"(?<!\d[-.\s])"  # left guard: not preceded by digit+sep
            r"(?:\+\d{1,3}[-.\s]?)?"  # optional country code "+X[-.\s]?"
            r"\(?\d{2,4}\)?"  # area / first group, optional parens
            r"[-.\s]\d{3,4}[-.\s]\d{3,4}"  # two more dash/space/dot-separated groups
            r"(?![-.\s]?\d)",  # right guard: not followed by sep+digit
        ),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        # credit_card: dashed/spaced 16-digit form OR plain 14-19 digit run
        # (14+ avoids overlap with shorter phone digit runs).
        "credit_card": re.compile(
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{14,19}\b",
        ),
    }

    def __init__(self, *, llm_judge_threshold: int = 2) -> None:
        if llm_judge_threshold < 1:
            raise ValueError("llm_judge_threshold must be >= 1")
        self._threshold = llm_judge_threshold

    # Pattern priority for span-based dedup. Ordering rationale:
    # SSN's tight format (\d{3}-\d{2}-\d{4}) has highest precision → first.
    # Credit card (16 digits dashed/spaced) is more specific than phone
    # (which matches sub-runs inside CC) → before phone. Email is span-
    # disjoint from numeric patterns → safe ordering.
    _PATTERN_PRIORITY: ClassVar[tuple[str, ...]] = (
        "ssn",
        "credit_card",
        "email",
        "phone",
    )

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        text = self._extract_text(content)
        # Span-based dedup: a PII region must be counted only once even
        # if multiple regexes match it. Without this, "5500 0000 0000 0004"
        # would count as both credit_card (4-4-4-4) AND phone (sub-run)
        # which is a double-count, not a real second PII type.
        claimed_spans: list[tuple[int, int]] = []
        hits: dict[str, list[str]] = {n: [] for n in self.PATTERNS}
        for name in self._PATTERN_PRIORITY:
            for match in self.PATTERNS[name].finditer(text):
                start, end = match.span()
                if any(not (end <= cs or start >= ce) for cs, ce in claimed_spans):
                    continue  # overlaps an earlier higher-priority match
                claimed_spans.append((start, end))
                hits[name].append(match.group())

        total = sum(len(matches) for matches in hits.values())
        if total == 0:
            return GuardrailResult(action=GuardrailAction.PASS)

        types_hit = sorted(name for name, matches in hits.items() if matches)
        if total >= self._threshold:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"PII detected: {types_hit} ({total} match{'es' if total > 1 else ''})",
                risk_level="HIGH",
            )
        return GuardrailResult(
            action=GuardrailAction.ESCALATE,
            reason=f"PII suspected: {types_hit} (1 match — single suspect, route to HITL)",
            risk_level="MEDIUM",
        )

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Best-effort flatten: str / Message / dict / list → text.

        Why best-effort: the guardrail's job is detection, not type
        validation; if a caller passes an unsupported shape we still
        run str() on it so the regex gets a chance.
        """
        if isinstance(content, str):
            return content
        # Message-like (has `.content`): str | list[content blocks]
        inner = getattr(content, "content", None)
        if inner is not None:
            if isinstance(inner, str):
                return inner
            if isinstance(inner, list):
                parts: list[str] = []
                for block in inner:
                    if isinstance(block, dict):
                        # Common shapes: {"type": "text", "text": "..."}
                        # or {"content": "..."}; both are string-bearing.
                        for key in ("text", "content"):
                            value = block.get(key)
                            if isinstance(value, str):
                                parts.append(value)
                                break
                    elif isinstance(block, str):
                        parts.append(block)
                return " ".join(parts)
        return str(content)
