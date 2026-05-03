"""
File: backend/src/agent_harness/error_handling/retry.py
Purpose: Per-(tool, ErrorClass) RetryPolicyMatrix for fine-grained retry tuning.
Category: 範疇 8 (Error Handling)
Scope: Phase 53.2 / Sprint 53.2

Description:
    Two-layer separation of retry concerns:

      Layer 1  DefaultErrorPolicy (policy.py)
               * Owns "should I retry at all?" — gated by ErrorClass
                 (HITL_RECOVERABLE / FATAL never retry).
               * Owns the global default backoff curve.

      Layer 2  RetryPolicyMatrix (this file)
               * Owns "if retrying, with what cap & backoff?"
               * Provides per-tool / per-ErrorClass override matrix.
               * Defaults match Cat 8 spec (TRANSIENT max=3,
                 LLM_RECOVERABLE max=2, HITL_RECOVERABLE max=0,
                 FATAL max=0).
               * YAML-loadable (`backend/config/retry_policies.yaml`)
                 so per-tool tuning ships as config, not code.

    The AgentLoop (US-6, Day 3-4) consults both:
      1. DefaultErrorPolicy.classify(exc) → ErrorClass
      2. DefaultErrorPolicy.should_retry(exc, attempt=N) → bool gate
      3. RetryPolicyMatrix.get_policy(tool_name, cls) → RetryConfig
      4. compute_backoff(config, attempt) → sleep duration
      5. Emit ErrorRetried event then asyncio.sleep(delay)

Key Components:
    - RetryConfig: frozen dataclass (max_attempts / backoff_base /
      backoff_max / jitter)
    - RetryPolicyMatrix: in-memory lookup with from_yaml() classmethod
    - compute_backoff(config, attempt): pure function (testable)

Owner: 01-eleven-categories-spec.md §Cat 8 + 17.md §1.1
Created: 2026-05-03 (Sprint 53.2 Day 1)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.2 Day 1) — US-2 production impl
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from agent_harness.error_handling._abc import ErrorClass


@dataclass(frozen=True)
class RetryConfig:
    """Frozen retry tuning for a (tool, ErrorClass) pair.

    max_attempts == 0 means "never retry"; the matrix uses this for
    HITL_RECOVERABLE and FATAL by default.
    """

    max_attempts: int
    backoff_base: float = 1.0
    backoff_max: float = 30.0
    jitter: bool = True


# Cat 8 spec defaults — keyed by ErrorClass when no per-tool override.
_DEFAULTS: dict[ErrorClass, RetryConfig] = {
    ErrorClass.TRANSIENT: RetryConfig(
        max_attempts=3, backoff_base=1.0, backoff_max=30.0, jitter=True
    ),
    ErrorClass.LLM_RECOVERABLE: RetryConfig(
        max_attempts=2, backoff_base=0.5, backoff_max=5.0, jitter=False
    ),
    ErrorClass.HITL_RECOVERABLE: RetryConfig(
        max_attempts=0, backoff_base=0.0, backoff_max=0.0, jitter=False
    ),
    ErrorClass.FATAL: RetryConfig(max_attempts=0, backoff_base=0.0, backoff_max=0.0, jitter=False),
}


class RetryPolicyMatrix:
    """Per-(tool, ErrorClass) RetryConfig lookup.

    Resolution order:
        1. (tool_name, error_class)  — per-tool override
        2. (None, error_class)       — global override (rarely set)
        3. _DEFAULTS[error_class]    — Cat 8 spec defaults
    """

    def __init__(
        self,
        matrix: dict[tuple[str | None, ErrorClass], RetryConfig] | None = None,
    ) -> None:
        self._matrix = matrix or {}

    def get_policy(
        self,
        tool_name: str | None,
        error_class: ErrorClass,
    ) -> RetryConfig:
        if (tool_name, error_class) in self._matrix:
            return self._matrix[(tool_name, error_class)]
        if (None, error_class) in self._matrix:
            return self._matrix[(None, error_class)]
        return _DEFAULTS[error_class]

    @classmethod
    def from_yaml(cls, path: Path | str) -> "RetryPolicyMatrix":
        """Load matrix from YAML file.

        Schema:
            defaults:
              TRANSIENT: {max_attempts: 3, backoff_base: 1.0, ...}
              LLM_RECOVERABLE: {...}
              ...
            per_tool:
              salesforce_query:
                TRANSIENT: {max_attempts: 5, backoff_max: 60.0}
              ...
        """
        text = Path(path).read_text(encoding="utf-8")
        raw = yaml.safe_load(text) or {}
        matrix: dict[tuple[str | None, ErrorClass], RetryConfig] = {}

        for key, body in (raw.get("defaults") or {}).items():
            cls_enum = ErrorClass(key.lower()) if not isinstance(key, ErrorClass) else key
            matrix[(None, cls_enum)] = _config_from_dict(body)

        for tool_name, by_class in (raw.get("per_tool") or {}).items():
            for key, body in (by_class or {}).items():
                cls_enum = ErrorClass(key.lower()) if not isinstance(key, ErrorClass) else key
                matrix[(tool_name, cls_enum)] = _config_from_dict(body)

        return cls(matrix=matrix)


def _config_from_dict(body: dict[str, Any]) -> RetryConfig:
    """Build RetryConfig from raw dict, merging with class defaults."""
    return RetryConfig(
        max_attempts=int(body.get("max_attempts", 0)),
        backoff_base=float(body.get("backoff_base", 1.0)),
        backoff_max=float(body.get("backoff_max", 30.0)),
        jitter=bool(body.get("jitter", True)),
    )


def compute_backoff(config: RetryConfig, attempt: int) -> float:
    """Exponential backoff with optional jitter.

    Formula: min(backoff_max, backoff_base * 2^(attempt-1)) * jitter_factor

    attempt is 1-indexed (first retry attempt = 1). Returns 0 for
    attempt <= 0 or when max_attempts is 0 (never-retry policies).
    """
    if attempt <= 0 or config.max_attempts == 0:
        return 0.0
    base: float = min(
        config.backoff_max,
        config.backoff_base * float(2 ** (attempt - 1)),
    )
    if config.jitter:
        jitter_factor: float = 1.0 + random.uniform(-0.1, 0.1)
        return float(base * jitter_factor)
    return base
