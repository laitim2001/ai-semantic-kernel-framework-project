"""
File: backend/src/agent_harness/guardrails/output/toxicity_detector.py
Purpose: Pattern-based toxicity detector for output guardrail chain.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 2 (US-3)

Description:
    Detects toxic content in LLM output across 4 categories:
      - hate         (racial / ethnic slurs, hate speech)
      - harassment   (personal attacks, self-harm encouragement)
      - violence     (instructions for harm to people / property)
      - sexual       (explicit / graphic sexual content)

    Severity-driven action mapping:
      0 hits     → PASS
      LOW max    → REROLL (ask LLM to retry; mild content)
      MEDIUM max → SANITIZE (replace matched span with [REDACTED:<cat>];
                    return sanitized text)
      HIGH max   → BLOCK (refuse outright; severe content)

    Production-grade toxicity detection requires ML models (Perspective API,
    OpenAI Moderation, etc.); this regex baseline catches obvious patterns
    only. LLM-as-judge fallback for nuanced cases is deferred to 53.4.
    Per spec SLO `output guardrail p95 < 200ms`; regex-only path stays
    well under that.

Key Components:
    - ToxicityDetector(Guardrail): guardrail_type = OUTPUT
    - PATTERNS: dict[category → list[(pattern, severity)]]
    - _redact: replaces matched spans with [REDACTED:<category>]

Owner: 01-eleven-categories-spec.md §範疇 9
Single-source: GuardrailResult / GuardrailAction in 17.md §1.1

Created: 2026-05-03 (Sprint 53.3 Day 2)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-3) — regex baseline

Related:
    - guardrails/output/sensitive_info_detector.py — sibling OUTPUT detector
    - tests/fixtures/guardrails/toxicity_cases.yaml — accuracy fixture
"""

from __future__ import annotations

import re
from typing import Any, ClassVar, Literal, Pattern

from agent_harness._contracts import TraceContext
from agent_harness.guardrails._abc import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
)

Severity = Literal["LOW", "MEDIUM", "HIGH"]

_SEVERITY_RANK: dict[str, int] = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


class ToxicityDetector(Guardrail):
    """Regex-based toxicity detector for OUTPUT chain.

    Action policy (driven by max severity across all hits):
        0 hits     → PASS
        LOW max    → REROLL  — mild content; ask LLM to retry
        MEDIUM max → SANITIZE — moderate; redact spans, return sanitized
        HIGH max   → BLOCK    — severe; refuse outright with risk=HIGH
    """

    guardrail_type = GuardrailType.OUTPUT

    PATTERNS: ClassVar[dict[str, list[tuple[Pattern[str], Severity]]]] = {
        "hate": [
            (
                re.compile(
                    # "I hate all/every/those/these <something>" — captures
                    # blanket statements without requiring trailing 's'.
                    r"\bI\s+hate\s+(?:all|every|those|these)\b",
                    re.IGNORECASE,
                ),
                "MEDIUM",
            ),
            (
                re.compile(r"\b(?:racial|ethnic)\s+slurs?\b", re.IGNORECASE),
                "MEDIUM",
            ),
            (
                re.compile(
                    r"\b(?:they|those\s+people)\s+are\s+(?:vermin|inferior|subhuman)\b",
                    re.IGNORECASE,
                ),
                "HIGH",
            ),
        ],
        "harassment": [
            (
                re.compile(
                    r"\byou(?:'re|\s+are)\s+(?:stupid|worthless|pathetic|a\s+loser)\b",
                    re.IGNORECASE,
                ),
                "LOW",
            ),
            (
                re.compile(
                    r"\bnobody\s+(?:likes|wants|loves)\s+you\b",
                    re.IGNORECASE,
                ),
                "LOW",
            ),
            (
                re.compile(
                    r"\b(?:go\s+)?kill\s+yourself\b",
                    re.IGNORECASE,
                ),
                "HIGH",
            ),
            (
                re.compile(
                    r"\byou\s+should\s+(?:die|disappear)\b",
                    re.IGNORECASE,
                ),
                "HIGH",
            ),
        ],
        "violence": [
            (
                re.compile(
                    r"\bhow\s+to\s+(?:make|build|construct)\s+(?:a\s+)?"
                    r"(?:bomb|explosive|weapon|firearm)\b",
                    re.IGNORECASE,
                ),
                "HIGH",
            ),
            (
                re.compile(
                    r"\bhow\s+to\s+(?:kill|murder|harm|injure)\s+"
                    r"(?:someone|people|a\s+person)\b",
                    re.IGNORECASE,
                ),
                "HIGH",
            ),
            (
                re.compile(
                    r"\b(?:detailed\s+)?(?:instructions?|guide)\s+(?:for|to)\s+"
                    r"(?:violence|terrorism|attack)\b",
                    re.IGNORECASE,
                ),
                "HIGH",
            ),
        ],
        "sexual": [
            (
                re.compile(r"\bexplicit\s+sexual\s+content\b", re.IGNORECASE),
                "MEDIUM",
            ),
            (
                re.compile(
                    r"\b(?:hardcore|graphic)\s+(?:porn|pornography)\b",
                    re.IGNORECASE,
                ),
                "HIGH",
            ),
            (
                re.compile(
                    r"\bsexually\s+explicit\s+(?:material|description)\b",
                    re.IGNORECASE,
                ),
                "MEDIUM",
            ),
        ],
    }

    async def check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        text = self._extract_text(content)
        hits: list[tuple[str, Severity, tuple[int, int], str]] = []
        # (category, severity, span, matched_text)
        for category, plist in self.PATTERNS.items():
            for pattern, severity in plist:
                for match in pattern.finditer(text):
                    hits.append((category, severity, match.span(), match.group()))

        if not hits:
            return GuardrailResult(action=GuardrailAction.PASS)

        max_sev = max(_SEVERITY_RANK[s] for _, s, _, _ in hits)
        categories = sorted({c for c, _, _, _ in hits})

        if max_sev == _SEVERITY_RANK["HIGH"]:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"toxic content (HIGH): {categories}",
                risk_level="HIGH",
            )
        if max_sev == _SEVERITY_RANK["MEDIUM"]:
            return GuardrailResult(
                action=GuardrailAction.SANITIZE,
                reason=f"toxic content (MEDIUM): {categories}",
                sanitized_content=self._redact(text, hits),
                risk_level="MEDIUM",
            )
        # LOW
        return GuardrailResult(
            action=GuardrailAction.REROLL,
            reason=f"toxic content (LOW): {categories}",
            risk_level="LOW",
        )

    @staticmethod
    def _redact(
        text: str,
        hits: list[tuple[str, Severity, tuple[int, int], str]],
    ) -> str:
        """Replace each matched span with [REDACTED:<category>].

        Process hits right-to-left so earlier spans' indices stay valid.
        """
        sorted_hits = sorted(hits, key=lambda h: h[2][0], reverse=True)
        out = text
        for category, _, (start, end), _ in sorted_hits:
            out = f"{out[:start]}[REDACTED:{category}]{out[end:]}"
        return out

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Same flatten contract as input detectors."""
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
