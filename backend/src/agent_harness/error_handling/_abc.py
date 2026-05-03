"""
File: backend/src/agent_harness/error_handling/_abc.py
Purpose: Category 8 ABCs — ErrorPolicy + CircuitBreaker + ErrorTerminator.
Category: 範疇 8 (Error Handling)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 53.2)

Description:
    4-class error taxonomy:
    1. Transient (retry with backoff)
    2. LLM-recoverable (feed error back to LLM, let it adapt)
    3. HITL-recoverable (resumable wait for human decision)
    4. Fatal (terminate via ErrorTerminator)

    Tripwire is OWNED BY CATEGORY 9 (Guardrails), NOT here. Per 17.md §6
    we use `ErrorTerminator` for cat-8-owned termination (vs `Tripwire`
    for cat-9-owned).

Owner: 01-eleven-categories-spec.md §範疇 8
Single-source: 17.md §2.1, §6

Created: 2026-04-29 (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class ErrorClass(Enum):
    """4-class taxonomy."""

    TRANSIENT = "transient"
    LLM_RECOVERABLE = "llm_recoverable"
    HITL_RECOVERABLE = "hitl_recoverable"
    FATAL = "fatal"


class ErrorPolicy(ABC):
    """Classifies errors and decides retry/recovery action."""

    @abstractmethod
    def classify(self, error: BaseException) -> ErrorClass: ...

    @abstractmethod
    def should_retry(
        self,
        error: BaseException,
        *,
        attempt: int,
    ) -> bool: ...

    @abstractmethod
    def backoff_seconds(self, attempt: int) -> float: ...


class CircuitBreaker(ABC):
    """Per-resource (provider / tool) failure rate tracker.

    Methods are async to allow asyncio.Lock-based state guarding from
    concurrent adapter / Loop callers (Sprint 53.2 Day 2 finalised).
    """

    @abstractmethod
    async def record(self, *, success: bool, resource: str) -> None: ...

    @abstractmethod
    async def is_open(self, resource: str) -> bool: ...


class ErrorTerminator(ABC):
    """Cat-8-owned loop terminator. NOT 'tripwire' (that's cat 9)."""

    @abstractmethod
    def should_terminate(
        self,
        *,
        consecutive_errors: int,
        budget_exhausted: bool,
        circuit_open: bool,
    ) -> bool: ...
