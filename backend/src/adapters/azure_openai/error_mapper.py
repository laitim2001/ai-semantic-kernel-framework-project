"""
File: backend/src/adapters/azure_openai/error_mapper.py
Purpose: Map Azure OpenAI native exceptions to neutral ProviderError enum.
Category: Adapters / Azure OpenAI
Scope: Phase 49 / Sprint 49.4

Description:
    All openai SDK exceptions / HTTP status codes / message patterns translate to
    one of the 10 ProviderError categories. Cat 8 (Error Handling) consumes the
    enum to decide retry / backoff / circuit-break — without ever importing openai.

    Mapping per .claude/rules/adapters-layer.md §錯誤映射表.

Created: 2026-04-29 (Sprint 49.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4) — 9-row mapping table

Related:
    - adapter.py — wraps every API call with map() try/except
    - adapters-layer.md (.claude/rules/) §錯誤映射表
"""

from __future__ import annotations

from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

from adapters._base.errors import AdapterException, ProviderError


class AzureOpenAIErrorMapper:
    """Translate openai SDK errors → neutral ProviderError + AdapterException."""

    @staticmethod
    def map(exc: Exception, *, provider: str = "azure_openai") -> AdapterException:
        """Convert any openai exception (or generic Exception) to AdapterException.

        Logic order matters: more specific exceptions first, fallback to message
        substring matching for cases the SDK doesn't expose as a typed exception.
        """
        category = AzureOpenAIErrorMapper._categorize(exc)
        status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
        return AdapterException(
            category=category,
            message=str(exc) or exc.__class__.__name__,
            original=exc,
            provider=provider,
            status_code=status,
        )

    @staticmethod
    def _categorize(exc: Exception) -> ProviderError:  # noqa: C901 — explicit branch table
        # 1. Auth
        if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
            return ProviderError.AUTH_FAILED

        # 2. Rate limited (429)
        if isinstance(exc, RateLimitError):
            msg = str(exc).lower()
            if "quota" in msg or "exceeded your current quota" in msg:
                return ProviderError.QUOTA_EXCEEDED
            return ProviderError.RATE_LIMITED

        # 3. Timeout / network
        if isinstance(exc, APITimeoutError):
            return ProviderError.TIMEOUT
        if isinstance(exc, APIConnectionError):
            return ProviderError.SERVICE_UNAVAILABLE

        # 4. 5xx server
        if isinstance(exc, InternalServerError):
            return ProviderError.SERVICE_UNAVAILABLE

        # 5. 404 — model not found
        if isinstance(exc, NotFoundError):
            return ProviderError.MODEL_UNAVAILABLE

        # 6. 400 / 422 — input issues
        if isinstance(exc, (BadRequestError, UnprocessableEntityError)):
            msg = str(exc).lower()
            if "context_length_exceeded" in msg or "maximum context length" in msg:
                return ProviderError.CONTEXT_WINDOW_EXCEEDED
            if "content_filter" in msg or "safety" in msg or "policy" in msg:
                return ProviderError.SAFETY_REFUSAL
            return ProviderError.INVALID_REQUEST

        # 7. Generic Exception fallback
        return AzureOpenAIErrorMapper._fallback(exc)

    @staticmethod
    def _fallback(exc: Exception) -> ProviderError:
        msg = str(exc).lower()
        status: Any = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
        if status == 401 or status == 403:
            return ProviderError.AUTH_FAILED
        if status == 429:
            return ProviderError.RATE_LIMITED
        if status == 404:
            return ProviderError.MODEL_UNAVAILABLE
        if isinstance(status, int) and 500 <= status < 600:
            return ProviderError.SERVICE_UNAVAILABLE
        if "timeout" in msg or "timed out" in msg:
            return ProviderError.TIMEOUT
        if "context_length" in msg:
            return ProviderError.CONTEXT_WINDOW_EXCEEDED
        return ProviderError.UNKNOWN
