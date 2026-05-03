"""
File: backend/src/agent_harness/guardrails/input/jailbreak_detector.py
Purpose: Pattern-based jailbreak / prompt-injection detector for input guardrail chain.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 2 (US-2 下半)

Description:
    Detects common jailbreak / prompt-injection vectors in user input:
      1. Imperative instruction override   ("ignore previous instructions")
      2. Persona override                  ("DAN mode", "act as jailbroken")
      3. Bypass / privilege escalation     ("bypass safety", "override system")
      4. Mode escalation                   ("enable developer mode")
      5. System prompt extraction          ("reveal your system prompt")
      6. Self-referential jailbreak terms  ("jailbreak", "jailbroken")

    Single-tier policy (severe by nature; defense-in-depth with downstream
    LLM safety + range-9 Tripwire):
      0 hits → PASS
      ≥ 1 hit → BLOCK (risk=HIGH)

    No ESCALATE tier — jailbreak attempts are rarely false alarms with
    these specific patterns; sending to HITL would create approval fatigue.
    The accuracy bar is ≥ 90% (per plan §US-2) — fewer detection types but
    each pattern is high-precision-by-design.

    Defense-in-depth: pattern-based at this layer; future LLM-as-judge
    (deferred to 53.4) will add semantic detection for novel phrasings.

Key Components:
    - JailbreakDetector(Guardrail): guardrail_type = INPUT
    - PATTERNS: 14 high-precision compiled regexes
    - _extract_text: same content unwrap as PIIDetector

Owner: 01-eleven-categories-spec.md §範疇 9 (jailbreak detection)
Single-source: GuardrailResult / GuardrailAction in 17.md §1.1

Created: 2026-05-03 (Sprint 53.3 Day 2)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-2 下半)

Related:
    - guardrails/_abc.py — Guardrail ABC contract
    - guardrails/engine.py — registers JailbreakDetector in INPUT chain
    - guardrails/input/pii_detector.py — sibling INPUT detector
    - tests/fixtures/guardrails/jailbreak_redteam.yaml — accuracy fixture (≥ 30 +/-)
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


class JailbreakDetector(Guardrail):
    """Pattern-based jailbreak / prompt-injection detector for INPUT chain.

    Action policy:
        0 hits → PASS
        ≥ 1 hit → BLOCK (HIGH) — single match is enough; jailbreak attempts
                                  are inherently severe (no ESCALATE tier).
    """

    guardrail_type = GuardrailType.INPUT

    # 14 high-precision patterns covering known jailbreak vectors.
    # Each pattern is intentionally specific to minimize false positives
    # (e.g. "tell me about jailbreaking" should NOT block — but "this is
    # a jailbreak" using bare \b\bjailbreak\b\b will trigger; we accept
    # this trade-off because the ≥90% target tolerates ~10% precision
    # loss and missing real jailbreaks is worse than over-blocking
    # discussions about the topic).
    PATTERNS: ClassVar[list[Pattern[str]]] = [
        # === Group 1: Imperative instruction override ====================
        re.compile(
            r"ignore\s+(?:all\s+|the\s+|your\s+)?"
            r"(?:previous\s+|prior\s+)?"
            r"(?:instructions?|rules?|guidelines?|prompts?)",
            re.IGNORECASE,
        ),
        re.compile(
            r"ignore\s+(?:everything|anything)\s+(?:above|before|stated|written)",
            re.IGNORECASE,
        ),
        re.compile(
            r"disregard\s+(?:all\s+|the\s+)?"
            r"(?:previous|prior|earlier)\s+(?:instructions?|rules?)",
            re.IGNORECASE,
        ),
        re.compile(
            r"forget\s+(?:all\s+|your\s+|everything\s+)?"
            r"(?:previous|prior)\s+(?:instructions?|context|rules?)",
            re.IGNORECASE,
        ),
        # === Group 2: Persona override ===================================
        # "DAN" / "do anything now" — bare DAN is rare in normal English
        re.compile(r"\bDAN\s+(?:mode|now)\b", re.IGNORECASE),
        re.compile(r"do\s+anything\s+now", re.IGNORECASE),
        re.compile(
            r"(?:act\s+as|pretend\s+(?:you\s+are|to\s+be)|you\s+are\s+now)"
            r"\s+(?:a\s+|an\s+)?"
            r"(?:DAN|jailbroken|unrestricted|uncensored|evil)",
            re.IGNORECASE,
        ),
        # === Group 3: Mode escalation ====================================
        re.compile(
            r"(?:enable|activate|switch\s+to|turn\s+on)"
            r"\s+(?:developer|debug|admin|sudo|god)\s+mode",
            re.IGNORECASE,
        ),
        re.compile(
            r"developer\s+mode\s+(?:on|enabled|activated)",
            re.IGNORECASE,
        ),
        # === Group 4: Bypass / privilege escalation ======================
        re.compile(
            r"bypass\s+(?:your\s+|all\s+|the\s+)?"
            r"(?:safety|restrictions?|guardrails?|filters?|guidelines?)",
            re.IGNORECASE,
        ),
        re.compile(
            r"override\s+(?:your\s+|the\s+|all\s+)?"
            r"(?:system|safety|instructions|guidelines|rules)",
            re.IGNORECASE,
        ),
        # === Group 5: System prompt extraction ===========================
        re.compile(
            r"(?:reveal|show|print|output|display|repeat)"
            r"\s+(?:me\s+)?(?:your\s+|the\s+)?"
            r"(?:system\s+)?(?:prompt|instructions?|configuration)",
            re.IGNORECASE,
        ),
        re.compile(
            r"what(?:'s|\s+is|\s+are)\s+your\s+"
            r"(?:system\s+)?(?:prompt|instructions?|original\s+rules?)",
            re.IGNORECASE,
        ),
        # === Group 6: Self-referential jailbreak terms ===================
        re.compile(r"\b(?:jailbreak|jailbroken|jailbreaking)\b", re.IGNORECASE),
    ]

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        text = self._extract_text(content)
        for pattern in self.PATTERNS:
            match = pattern.search(text)
            if match:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=f"Jailbreak pattern match: {match.group()!r}",
                    risk_level="HIGH",
                )
        return GuardrailResult(action=GuardrailAction.PASS)

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Same flatten contract as PIIDetector — kept independent
        to avoid cross-detector coupling.
        """
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
