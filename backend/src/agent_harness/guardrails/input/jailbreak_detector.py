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
Last Modified: 2026-05-04 (Sprint 53.7 Day 3)

Modification History (newest-first):
    - 2026-05-04: Sprint 53.7 Day 3 — close AD-Cat9-8 FP. Replaced bare-word
      Group 6 pattern `\b(?:jailbreak|jailbroken|jailbreaking)\b` (which
      false-positively matched meta-discussion like "what does jailbreak
      mean?", "the term jailbreak refers to...", "tutorials about
      jailbreaking are common") with two imperative-target patterns that
      require the word be followed by a target ("the assistant" / "you" /
      "claude" / "this AI" / etc.) or a self-target ("me" / "us" / "yourself").
      Pattern count: 14 -> 15. The 5 real attack styles tested in 53.7
      checklist all still TRIP (4 caught by Groups 1-5 unchanged; the
      one needing Group 6 — "jailbreak the assistant by..." — TRIPs the
      new imperative-target pattern). Fixture jb_neg_010 (previously left
      out as known-FP) is now added; jb_neg_023..025 cover other meta-
      discussion phrasings.
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

    # 15 high-precision patterns covering known jailbreak vectors.
    # Each pattern is intentionally specific to minimize false positives.
    # Group 6 was revised in Sprint 53.7 (closes AD-Cat9-8) to require
    # imperative + target context, so meta-discussion like "what does
    # jailbreak mean?" / "the term jailbreak refers to..." / "tutorials
    # about jailbreaking are common" no longer falsely matches. Real
    # attacks always specify a target (e.g. "jailbreak the assistant",
    # "jailbreak me") or use one of the other 14 attack-style patterns.
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
        # === Group 6: Imperative-target jailbreak (Sprint 53.7 revision) =
        # Pre-53.7 had a bare `\b(?:jailbreak|jailbroken|jailbreaking)\b`
        # which produced FPs on meta-discussion ("what does jailbreak
        # mean?"). Replaced with two imperative-target patterns: the word
        # must precede a target object (the AI under attack) or self-target
        # (me / us / yourself), reflecting how real attacks are phrased.
        # See AD-Cat9-8 closure in Modification History.
        re.compile(
            r"\bjailbreak\s+(?:the\s+|this\s+)?"
            r"(?:assistant|ai|model|chatbot|claude|gpt|chatgpt|llm|system|you)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:please\s+|let'?s\s+|help\s+me\s+)?"
            r"jailbreak\s+(?:me|us|yourself)\b",
            re.IGNORECASE,
        ),
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
