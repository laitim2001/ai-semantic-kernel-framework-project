"""
File: backend/src/agent_harness/guardrails/_abc.py
Purpose: Category 9 ABCs — Guardrail (3 types) + Tripwire.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 53.3-53.4)

Description:
    3 guardrail types: input / output / tool. Each implements Guardrail
    ABC and returns GuardrailResult (block / sanitize / escalate / reroll).

    Tripwire is severe: detected policy violation (PII leak / jailbreak /
    data exfil) → immediate loop terminate (NOT retry). Cat 8's
    ErrorTerminator is for budget/circuit; Tripwire is for security.

Owner: 01-eleven-categories-spec.md §範疇 9
Single-source: 17.md §2.1, §6

Created: 2026-04-29 (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from agent_harness._contracts import Message, ToolCall, TraceContext


class GuardrailType(Enum):
    INPUT = "input"
    OUTPUT = "output"
    TOOL = "tool"


class GuardrailAction(Enum):
    """Action returned by Guardrail.check()."""

    PASS = "pass"
    BLOCK = "block"
    SANITIZE = "sanitize"
    ESCALATE = "escalate"  # → HITL via §HITL
    REROLL = "reroll"  # ask LLM to retry


@dataclass(frozen=True)
class GuardrailResult:
    """Output of Guardrail.check()."""

    action: GuardrailAction
    reason: str | None = None
    sanitized_content: Any | None = None  # if action=SANITIZE
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"


class Guardrail(ABC):
    """Single guardrail check. Multiple guardrails compose in a chain."""

    guardrail_type: GuardrailType

    @abstractmethod
    async def check(
        self,
        *,
        content: str | Message | ToolCall,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult: ...


class Tripwire(ABC):
    """Severe policy violation detector. Triggers IMMEDIATE loop termination.

    Per 17.md §6: tripwire is OWNED BY CATEGORY 9 (NOT cat 8).
    """

    @abstractmethod
    async def trigger_check(
        self,
        *,
        content: Any,
        trace_context: TraceContext | None = None,
    ) -> bool:
        """True = tripwire triggered, terminate loop."""
        ...

    @abstractmethod
    def register_pattern(
        self,
        *,
        name: str,
        detector: Any,  # callable; concretely defined by implementation
    ) -> None: ...
