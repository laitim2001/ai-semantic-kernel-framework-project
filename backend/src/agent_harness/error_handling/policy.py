"""
File: backend/src/agent_harness/error_handling/policy.py
Purpose: Production-grade DefaultErrorPolicy implementing ErrorPolicy ABC.
Category: 範疇 8 (Error Handling)
Scope: Phase 53.2 / Sprint 53.2

Description:
    Concrete impl of `ErrorPolicy` (defined in `_abc.py`):
      - classify(error) -> ErrorClass via type-based registry + MRO walk
      - should_retry(error, *, attempt) -> bool gated by ErrorClass + attempt cap
      - backoff_seconds(attempt) -> float exponential backoff with optional jitter

    Default registry (built from stdlib + agent_harness types only — no
    optional 3rd-party imports, keeps Cat 8 free of provider lock-in):

      TRANSIENT          ConnectionError, OSError, TimeoutError,
                         asyncio.TimeoutError
      LLM_RECOVERABLE    ToolExecutionError
      HITL_RECOVERABLE   AuthenticationError, MissingDataError
      FATAL              fallback (any unregistered exception type)

    Provider adapters (`adapters/azure_openai/`, etc.) register their
    SDK-specific exception types via `policy.register(SomeProviderError,
    ErrorClass.TRANSIENT)` at adapter __init__ — keeps SDK imports
    confined to the adapters/ layer per LLM Provider Neutrality.

Key Components:
    - DefaultErrorPolicy: implements ErrorPolicy ABC
    - register(exc_class, error_class): runtime registry extension

Owner: 01-eleven-categories-spec.md §Cat 8 + 17.md §1.1
Single-source: ErrorClass enum stays in _abc.py; this file consumes it.
Created: 2026-05-03 (Sprint 53.2 Day 1)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.2 Day 1) — US-1 production impl
"""

from __future__ import annotations

import asyncio
import random
from typing import Type

from agent_harness._contracts.errors import (
    AuthenticationError,
    MissingDataError,
    ToolExecutionError,
)
from agent_harness.error_handling._abc import ErrorClass, ErrorPolicy


class DefaultErrorPolicy(ErrorPolicy):
    """In-memory ErrorPolicy with type-based classification + backoff curve.

    Thread-safe: classification is read-only after construction; the
    only mutator is `register()` which is intended for one-time setup
    at adapter __init__.

    Defaults:
        max_attempts = 3 (Stripe-pattern conservative cap)
        backoff_base = 1.0 (seconds)
        backoff_max = 30.0 (seconds — caps tail latency)
        jitter = True (avoids thundering herd on retry storms)
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        backoff_base: float = 1.0,
        backoff_max: float = 30.0,
        jitter: bool = True,
    ) -> None:
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._jitter = jitter
        self._registry: dict[Type[BaseException], ErrorClass] = {}
        self._register_defaults()

    # === Registry ============================================================
    # Why: type-based classification with MRO walk so subclasses inherit the
    # parent's category (e.g. SalesforceConnectionError(ToolExecutionError)
    # → LLM_RECOVERABLE without explicit registration).

    def _register_defaults(self) -> None:
        # TRANSIENT — stdlib only (no aiohttp / requests imports here)
        self._registry[ConnectionError] = ErrorClass.TRANSIENT
        self._registry[OSError] = ErrorClass.TRANSIENT
        self._registry[TimeoutError] = ErrorClass.TRANSIENT
        self._registry[asyncio.TimeoutError] = ErrorClass.TRANSIENT

        # LLM_RECOVERABLE — agent_harness contracts
        self._registry[ToolExecutionError] = ErrorClass.LLM_RECOVERABLE

        # HITL_RECOVERABLE — agent_harness contracts
        self._registry[AuthenticationError] = ErrorClass.HITL_RECOVERABLE
        self._registry[MissingDataError] = ErrorClass.HITL_RECOVERABLE

        # FATAL — fallback when no registered match found

    def register(
        self,
        exc_class: Type[BaseException],
        error_class: ErrorClass,
    ) -> None:
        """Register an exception type → ErrorClass mapping.

        Intended for adapter __init__ to map SDK-specific exception types
        (e.g. openai.RateLimitError → TRANSIENT). Idempotent: re-registering
        the same type silently overwrites the previous mapping.
        """
        self._registry[exc_class] = error_class

    # === ErrorPolicy ABC ====================================================

    def classify(self, error: BaseException) -> ErrorClass:
        # MRO walk so subclasses inherit parent's classification
        for exc_type in type(error).__mro__:
            if exc_type in self._registry:
                return self._registry[exc_type]
        return ErrorClass.FATAL

    def should_retry(
        self,
        error: BaseException,
        *,
        attempt: int,
    ) -> bool:
        cls = self.classify(error)
        # HITL_RECOVERABLE: human must intervene; no automatic retry
        # FATAL: bug / unrecognized; bubble up
        if cls in (ErrorClass.HITL_RECOVERABLE, ErrorClass.FATAL):
            return False
        # TRANSIENT / LLM_RECOVERABLE: retry within attempt cap
        return attempt < self._max_attempts

    def backoff_seconds(self, attempt: int) -> float:
        """Exponential backoff with optional jitter.

        Formula: min(backoff_max, backoff_base * 2^(attempt-1)) * jitter_factor

        attempt is 1-indexed (first retry attempt = 1). Negative or zero
        attempts return 0 (no delay).
        """
        if attempt <= 0:
            return 0.0
        base: float = min(
            self._backoff_max,
            self._backoff_base * float(2 ** (attempt - 1)),
        )
        if self._jitter:
            # ±10% jitter to avoid thundering herd
            jitter_factor: float = 1.0 + random.uniform(-0.1, 0.1)
            return float(base * jitter_factor)
        return base
