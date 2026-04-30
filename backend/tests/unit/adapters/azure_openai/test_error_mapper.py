"""
File: backend/tests/unit/adapters/azure_openai/test_error_mapper.py
Purpose: Verify AzureOpenAIErrorMapper translates 8+ provider errors to neutral ProviderError.
Category: Tests / Adapters / Azure OpenAI
Scope: Phase 49 / Sprint 49.4

Description:
    The 9-row mapping table per .claude/rules/adapters-layer.md §錯誤映射表.
    Each parametrize row asserts: native exception class → expected ProviderError.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from adapters._base.errors import AdapterException, ProviderError
from adapters.azure_openai.error_mapper import AzureOpenAIErrorMapper


def _mock_request() -> httpx.Request:
    return httpx.Request("POST", "https://example.openai.azure.com/")


def _mock_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_mock_request())


def _build_openai_error(cls: Any, status_code: int, body: dict[str, Any]) -> Any:
    """openai SDK 2.x errors take (message, response, body) keyword pattern."""
    response = _mock_response(status_code)
    try:
        return cls(message=body.get("error", {}).get("message", ""), response=response, body=body)
    except TypeError:
        # different signature for older versions
        return cls(body.get("error", {}).get("message", ""), response, body)


def test_authentication_error_maps_to_auth_failed() -> None:
    exc = _build_openai_error(AuthenticationError, 401, {"error": {"message": "invalid api key"}})
    result = AzureOpenAIErrorMapper.map(exc)
    assert isinstance(result, AdapterException)
    assert result.category == ProviderError.AUTH_FAILED


def test_permission_denied_maps_to_auth_failed() -> None:
    exc = _build_openai_error(PermissionDeniedError, 403, {"error": {"message": "no access"}})
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.AUTH_FAILED


def test_rate_limit_maps_to_rate_limited() -> None:
    exc = _build_openai_error(RateLimitError, 429, {"error": {"message": "too many requests"}})
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.RATE_LIMITED


def test_quota_message_in_rate_limit_maps_to_quota_exceeded() -> None:
    exc = _build_openai_error(
        RateLimitError, 429, {"error": {"message": "You exceeded your current quota"}}
    )
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.QUOTA_EXCEEDED


def test_timeout_maps_to_timeout() -> None:
    exc = APITimeoutError(request=_mock_request())
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.TIMEOUT


def test_connection_error_maps_to_service_unavailable() -> None:
    exc = APIConnectionError(request=_mock_request())
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.SERVICE_UNAVAILABLE


def test_internal_server_error_maps_to_service_unavailable() -> None:
    exc = _build_openai_error(InternalServerError, 500, {"error": {"message": "boom"}})
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.SERVICE_UNAVAILABLE


def test_not_found_maps_to_model_unavailable() -> None:
    exc = _build_openai_error(NotFoundError, 404, {"error": {"message": "deployment not found"}})
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.MODEL_UNAVAILABLE


def test_context_length_in_bad_request_maps_to_context_window_exceeded() -> None:
    exc = _build_openai_error(
        BadRequestError,
        400,
        {"error": {"message": "This model's maximum context length is 8192 tokens"}},
    )
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.CONTEXT_WINDOW_EXCEEDED


def test_content_filter_in_bad_request_maps_to_safety_refusal() -> None:
    exc = _build_openai_error(
        BadRequestError, 400, {"error": {"message": "content_filter triggered"}}
    )
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.SAFETY_REFUSAL


def test_generic_bad_request_maps_to_invalid_request() -> None:
    exc = _build_openai_error(
        BadRequestError, 400, {"error": {"message": "missing required field"}}
    )
    assert AzureOpenAIErrorMapper.map(exc).category == ProviderError.INVALID_REQUEST


def test_unknown_exception_maps_to_unknown() -> None:
    exc = RuntimeError("something weird happened")
    result = AzureOpenAIErrorMapper.map(exc)
    assert result.category == ProviderError.UNKNOWN
    assert result.provider == "azure_openai"
    assert result.original is exc


@pytest.mark.parametrize(
    "status_code,expected",
    [
        (401, ProviderError.AUTH_FAILED),
        (403, ProviderError.AUTH_FAILED),
        (429, ProviderError.RATE_LIMITED),
        (404, ProviderError.MODEL_UNAVAILABLE),
        (500, ProviderError.SERVICE_UNAVAILABLE),
        (503, ProviderError.SERVICE_UNAVAILABLE),
    ],
)
def test_fallback_via_status_code(status_code: int, expected: ProviderError) -> None:
    """Generic exception with status_code attribute uses fallback path."""

    class _Exc(Exception):
        def __init__(self) -> None:
            super().__init__(f"http {status_code}")
            self.status_code = status_code

    assert AzureOpenAIErrorMapper.map(_Exc()).category == expected
