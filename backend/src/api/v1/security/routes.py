"""
Security API Routes

Sprint 3 - Story S3-2: API Security Hardening

Provides endpoints for security testing and configuration.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Request, HTTPException, status

from src.core.security import (
    get_rate_limiter,
    rate_limit,
    InputValidator,
    sanitize_string,
    SafeString,
)
from src.core.security.config import security_config

router = APIRouter(prefix="/security", tags=["security"])


class SecurityConfigResponse(BaseModel):
    """Response model for security configuration."""

    rate_limit_requests: int = Field(description="Requests per window")
    rate_limit_window_seconds: int = Field(description="Window duration")
    cors_origins: list = Field(description="Allowed CORS origins")
    hsts_enabled: bool = Field(description="HSTS enabled")
    csp_enabled: bool = Field(description="CSP enabled")
    xframe_options: str = Field(description="X-Frame-Options value")


class RateLimitStatusResponse(BaseModel):
    """Response model for rate limit status."""

    key: str = Field(description="Rate limit key")
    current_usage: int = Field(description="Current request count")
    limit: int = Field(description="Maximum requests allowed")
    remaining: int = Field(description="Remaining requests")


class InputValidationRequest(BaseModel):
    """Request model for input validation testing."""

    text: Optional[str] = Field(None, max_length=1000)
    email: Optional[str] = Field(None)
    url: Optional[str] = Field(None)
    uuid: Optional[str] = Field(None)


class InputValidationResponse(BaseModel):
    """Response model for input validation testing."""

    original_text: Optional[str] = None
    sanitized_text: Optional[str] = None
    email_valid: Optional[bool] = None
    url_valid: Optional[bool] = None
    uuid_valid: Optional[bool] = None
    sql_injection_detected: bool = False
    xss_detected: bool = False
    is_safe: bool = True


class SecurityTestRequest(BaseModel):
    """Request model with SafeString validation."""

    name: SafeString = Field(..., min_length=1, max_length=100)
    description: Optional[SafeString] = Field(None, max_length=500)


@router.get(
    "/config",
    response_model=SecurityConfigResponse,
    summary="Get security configuration",
    description="Returns current security configuration (non-sensitive values only).",
)
async def get_security_config() -> SecurityConfigResponse:
    """Get current security configuration."""
    return SecurityConfigResponse(
        rate_limit_requests=security_config.rate_limit_requests,
        rate_limit_window_seconds=security_config.rate_limit_window_seconds,
        cors_origins=security_config.cors_origins,
        hsts_enabled=security_config.enable_hsts,
        csp_enabled=security_config.enable_csp,
        xframe_options=security_config.xframe_options_value,
    )


@router.get(
    "/rate-limit/status",
    response_model=RateLimitStatusResponse,
    summary="Get rate limit status",
    description="Returns current rate limit status for the requesting client.",
)
async def get_rate_limit_status(request: Request) -> RateLimitStatusResponse:
    """Get current rate limit status for the client."""
    limiter = get_rate_limiter()
    key = limiter.get_key_for_request(request)

    current, limit = await limiter._memory_limiter.get_usage(key)
    remaining = max(0, limit - current)

    return RateLimitStatusResponse(
        key=key,
        current_usage=current,
        limit=limit,
        remaining=remaining,
    )


@router.get(
    "/rate-limit/test",
    summary="Test rate limiting",
    description="Endpoint for testing rate limiting. Limited to 10 requests per minute.",
)
@rate_limit(requests_per_minute=10)
async def test_rate_limit(request: Request) -> Dict[str, Any]:
    """Test rate limiting functionality.

    This endpoint is limited to 10 requests per minute.
    """
    return {
        "message": "Request allowed",
        "remaining": getattr(request.state, "rate_limit_remaining", "unknown"),
        "limit": getattr(request.state, "rate_limit_limit", "unknown"),
    }


@router.post(
    "/validate",
    response_model=InputValidationResponse,
    summary="Validate and sanitize input",
    description="Tests input validation and sanitization functions.",
)
async def validate_input(data: InputValidationRequest) -> InputValidationResponse:
    """Validate and sanitize various input types.

    This endpoint demonstrates input validation capabilities.
    """
    response = InputValidationResponse()

    if data.text:
        response.original_text = data.text
        response.sanitized_text = sanitize_string(data.text)

        from src.core.security.validators import check_sql_injection, check_xss

        if check_sql_injection(data.text):
            response.sql_injection_detected = True
            response.is_safe = False

        if check_xss(data.text):
            response.xss_detected = True
            response.is_safe = False

    if data.email:
        response.email_valid = InputValidator.is_valid_email(data.email)

    if data.url:
        response.url_valid = InputValidator.is_valid_url(data.url)

    if data.uuid:
        response.uuid_valid = InputValidator.is_valid_uuid(data.uuid)

    return response


@router.post(
    "/test-safe-input",
    summary="Test SafeString validation",
    description="Tests Pydantic SafeString validation with automatic sanitization.",
)
async def test_safe_input(data: SecurityTestRequest) -> Dict[str, Any]:
    """Test SafeString Pydantic validation.

    The input is automatically sanitized and validated for injection attacks.
    """
    return {
        "name": data.name,
        "description": data.description,
        "message": "Input validated and sanitized successfully",
    }


@router.get(
    "/headers",
    summary="Check security headers",
    description="Returns the security headers that will be added to responses.",
)
async def check_security_headers() -> Dict[str, Any]:
    """Get information about configured security headers."""
    headers = {}

    if security_config.enable_hsts:
        headers["Strict-Transport-Security"] = security_config.get_hsts_header()

    if security_config.enable_csp:
        headers["Content-Security-Policy"] = security_config.csp_directives

    if security_config.enable_xframe_options:
        headers["X-Frame-Options"] = security_config.xframe_options_value

    if security_config.enable_content_type_nosniff:
        headers["X-Content-Type-Options"] = "nosniff"

    if security_config.enable_xss_protection:
        headers["X-XSS-Protection"] = "1; mode=block"

    if security_config.enable_referrer_policy:
        headers["Referrer-Policy"] = security_config.referrer_policy_value

    if security_config.enable_permissions_policy:
        headers["Permissions-Policy"] = security_config.permissions_policy_value

    return {
        "configured_headers": headers,
        "note": "These headers are automatically added to all responses",
    }
