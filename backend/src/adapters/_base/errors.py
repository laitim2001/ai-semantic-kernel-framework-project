"""
File: backend/src/adapters/_base/errors.py
Purpose: ProviderError enum + AdapterException — neutral error classification for all adapters.
Category: Adapters (LLM provider boundary; per 10-server-side-philosophy.md §原則 2)
Scope: Phase 49 / Sprint 49.4

Description:
    Single-source enum that all adapter error_mappers translate native errors
    into. Cat 8 (Error Handling) consumes this enum to decide retry / backoff
    / circuit-break / surface-to-user without knowing provider specifics.

    Per adapters-layer.md §錯誤映射表 (.claude/rules/).

Owner: 10-server-side-philosophy.md §原則 2 (single-source for adapter errors)
Single-source: this file (ProviderError enum + AdapterException base)

Created: 2026-04-29 (Sprint 49.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4) — required by azure_openai error_mapper

Related:
    - adapters-layer.md (.claude/rules/) — 錯誤映射表
    - azure_openai/error_mapper.py — first concrete consumer
"""

from __future__ import annotations

from enum import Enum


class ProviderError(Enum):
    """Neutral error category. Adapters map provider native errors to one of these."""

    AUTH_FAILED = "auth_failed"  # 401 / 403 / invalid api key
    RATE_LIMITED = "rate_limited"  # 429 — retry with backoff
    QUOTA_EXCEEDED = "quota_exceeded"  # quota used up — do NOT retry
    MODEL_UNAVAILABLE = "model_unavailable"  # model deprecated / paused
    CONTEXT_WINDOW_EXCEEDED = "context_too_long"  # input too long — Cat 4 should compact
    INVALID_REQUEST = "invalid_request"  # 400 — bad params / schema
    TIMEOUT = "timeout"  # request exceeded timeout
    SERVICE_UNAVAILABLE = "service_unavailable"  # 5xx — retry
    SAFETY_REFUSAL = "safety_refusal"  # provider safety filter
    UNKNOWN = "unknown"  # un-categorized


class AdapterException(Exception):
    """Base exception raised by adapters; carries ProviderError + original error.

    Cat 8 (Error Handling) catches this and dispatches by `category`:
    - RATE_LIMITED / SERVICE_UNAVAILABLE / TIMEOUT → retry with backoff
    - CONTEXT_WINDOW_EXCEEDED → trigger compaction
    - QUOTA_EXCEEDED / AUTH_FAILED → surface to user, do NOT retry
    - INVALID_REQUEST / UNKNOWN → log + surface
    """

    def __init__(
        self,
        category: ProviderError,
        message: str,
        *,
        original: Exception | None = None,
        provider: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.original = original
        self.provider = provider
        self.status_code = status_code

    def __repr__(self) -> str:
        return (
            f"AdapterException(category={self.category.value}, "
            f"provider={self.provider}, status={self.status_code}, "
            f"msg={self.message!r})"
        )
