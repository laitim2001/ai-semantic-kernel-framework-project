"""
File: backend/src/agent_harness/guardrails/tripwire.py
Purpose: DefaultTripwire concrete impl with plug-in detector registry.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 3 (US-5)

Description:
    Tripwire is severe-by-nature: any match → loop terminates IMMEDIATELY,
    no retry, no negotiation. Per 17.md §6 boundary, Tripwire is OWNED BY
    CATEGORY 9 (NOT category 8 ErrorTerminator):

        Cat 8 ErrorTerminator → budget / circuit-breaker / fatal_exception
        Cat 9 Tripwire        → policy violation (PII leak / jailbreak / etc.)

    DefaultTripwire ships 4 baseline detectors covering the most common
    severe violations. The plug-in registry (`register_pattern`) lets
    operators add domain-specific detectors at runtime without modifying
    this file (e.g. customer-PII, regulated-keyword, etc.).

    Detection logic is intentionally minimal and disjoint from
    PII/Jailbreak/Toxicity detectors — those are the "soft" guardrail
    signals (BLOCK/SANITIZE/ESCALATE/REROLL); Tripwire is the "hard"
    signal (terminate). Soft + hard run in parallel; hard wins.

    Per spec SLO `tripwire detection < 50ms`. With 4 stdlib regexes the
    p95 is well under 5ms; plug-in detectors are responsible for their
    own latency budget.

Key Components:
    - DefaultTripwire(Tripwire): impl with register_pattern + trigger_check
    - DetectorFn = async callable [content] → bool
    - 4 baseline patterns (kept high-precision; FP is preferable to FN here)

Owner: 01-eleven-categories-spec.md §範疇 9 + 17.md §6 (boundary)
Single-source: TripwireTriggered event in 17.md §3 (already in
               _contracts/events.py:232 from Sprint 49.1 stub)

Created: 2026-05-03 (Sprint 53.3 Day 3)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-5) — 4 baseline detectors

Related:
    - guardrails/_abc.py — Tripwire ABC contract
    - _contracts/events.py — TripwireTriggered event (emitted by Loop)
    - 17.md §6 — Cat 8 vs Cat 9 boundary裁定
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any, Pattern

from agent_harness._contracts import TraceContext
from agent_harness.guardrails._abc import Tripwire as TripwireABC

#: Async predicate: True ⇒ this content trips the wire.
DetectorFn = Callable[[Any], Awaitable[bool]]


class DefaultTripwire(TripwireABC):
    """Tripwire with plug-in detector registry.

    Built-in patterns (registered at construction):
      pii_leak_detected         — SSN-like or 16-digit credit-card pattern
      prompt_injection_detected — common injection phrases (DAN / ignore)
      unauthorized_tool_access  — code injection sigils (eval/subprocess)
      unsafe_output_detected    — direct harm phrases (kill yourself)

    Custom detectors via register_pattern():
        tripwire.register_pattern(name="customer_pii", detector=my_async_fn)
    """

    def __init__(self) -> None:
        self._patterns: dict[str, DetectorFn] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._patterns["pii_leak_detected"] = self._detect_pii_leak
        self._patterns["prompt_injection_detected"] = self._detect_prompt_injection
        self._patterns["unauthorized_tool_access"] = self._detect_unauth_tool
        self._patterns["unsafe_output_detected"] = self._detect_unsafe_output

    def register_pattern(
        self,
        *,
        name: str,
        detector: Any,
    ) -> None:
        """Register a custom detector by name. Idempotent — re-registering
        the same name silently overwrites the previous detector.
        """
        # ABC types `detector: Any` to keep the contract loose; we narrow
        # at runtime by relying on the duck-typed async-callable shape.
        self._patterns[name] = detector

    async def trigger_check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> bool:
        """Return True ⇒ at least one detector tripped; loop must terminate.

        Detectors run in registration order; first True short-circuits.
        Defensive: a detector raising an exception is treated as "no trip"
        (we log via tracer in production wiring) — a buggy custom detector
        should not crash the tripwire chain.
        """
        for fn in self._patterns.values():
            try:
                if await fn(content):
                    return True
            except Exception:
                # Defensive: don't let a buggy detector mask others.
                continue
        return False

    # === Built-in detectors =================================================
    # Kept disjoint from PII/Jailbreak/Toxicity Detectors so soft + hard
    # signals run independently. Each pattern targets the most severe
    # variant only — softer cases are caught by the Guardrail chain.

    _SSN_PATTERN: Pattern[str] = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    _CC_PATTERN: Pattern[str] = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")

    @staticmethod
    async def _detect_pii_leak(content: Any) -> bool:
        text = DefaultTripwire._coerce_text(content)
        return bool(
            DefaultTripwire._SSN_PATTERN.search(text) or DefaultTripwire._CC_PATTERN.search(text)
        )

    _INJECTION_PATTERNS: list[Pattern[str]] = [
        re.compile(r"ignore\s+(?:all\s+|the\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"\bDAN\s+(?:mode|now)\b", re.IGNORECASE),
        re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    ]

    @staticmethod
    async def _detect_prompt_injection(content: Any) -> bool:
        text = DefaultTripwire._coerce_text(content)
        return any(p.search(text) for p in DefaultTripwire._INJECTION_PATTERNS)

    _UNAUTH_PATTERNS: list[Pattern[str]] = [
        re.compile(r"\b__import__\s*\(", re.IGNORECASE),
        re.compile(r"\b(?:eval|exec)\s*\(", re.IGNORECASE),
        re.compile(r"\bsubprocess\s*\.\s*(?:run|Popen|call)\b", re.IGNORECASE),
        re.compile(r"\bos\s*\.\s*system\s*\(", re.IGNORECASE),
    ]

    @staticmethod
    async def _detect_unauth_tool(content: Any) -> bool:
        text = DefaultTripwire._coerce_text(content)
        return any(p.search(text) for p in DefaultTripwire._UNAUTH_PATTERNS)

    _UNSAFE_PATTERNS: list[Pattern[str]] = [
        re.compile(r"\b(?:go\s+)?kill\s+yourself\b", re.IGNORECASE),
        re.compile(
            r"\bhow\s+to\s+(?:make|build)\s+(?:a\s+)?(?:bomb|explosive)\b",
            re.IGNORECASE,
        ),
    ]

    @staticmethod
    async def _detect_unsafe_output(content: Any) -> bool:
        text = DefaultTripwire._coerce_text(content)
        return any(p.search(text) for p in DefaultTripwire._UNSAFE_PATTERNS)

    @staticmethod
    def _coerce_text(content: Any) -> str:
        """Detectors are content-shape-agnostic — coerce anything → str."""
        if isinstance(content, str):
            return content
        inner = getattr(content, "content", None)
        if isinstance(inner, str):
            return inner
        return str(content)
