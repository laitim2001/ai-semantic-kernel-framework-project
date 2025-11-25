"""
Security Configuration

Sprint 3 - Story S3-2: API Security Hardening

Centralized security configuration for the platform.
"""
import os
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class SecurityConfig:
    """Security configuration settings.

    All settings can be overridden via environment variables.

    Attributes:
        rate_limit_requests: Max requests per window (default: 60)
        rate_limit_window_seconds: Rate limit window in seconds (default: 60)
        cors_origins: Allowed CORS origins
        cors_allow_credentials: Allow credentials in CORS
        cors_allow_methods: Allowed HTTP methods
        cors_allow_headers: Allowed headers
        enable_hsts: Enable HTTP Strict Transport Security
        hsts_max_age: HSTS max age in seconds
        enable_csp: Enable Content Security Policy
        csp_directives: CSP directive string
        enable_xframe_options: Enable X-Frame-Options
        xframe_options_value: X-Frame-Options value
        enable_content_type_nosniff: Enable X-Content-Type-Options
        enable_xss_protection: Enable X-XSS-Protection
        trusted_hosts: List of trusted hosts
        max_request_size_mb: Maximum request body size in MB
    """

    # Rate Limiting
    rate_limit_requests: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    )
    rate_limit_window_seconds: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    )
    rate_limit_burst: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_BURST", "10"))
    )

    # CORS Configuration
    cors_origins: List[str] = field(default_factory=lambda: _get_cors_origins())
    cors_allow_credentials: bool = field(
        default_factory=lambda: os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    )
    cors_allow_methods: List[str] = field(
        default_factory=lambda: os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,PATCH,OPTIONS").split(",")
    )
    cors_allow_headers: List[str] = field(
        default_factory=lambda: os.getenv("CORS_ALLOW_HEADERS", "Authorization,Content-Type,X-Request-ID").split(",")
    )
    cors_max_age: int = field(
        default_factory=lambda: int(os.getenv("CORS_MAX_AGE", "600"))
    )

    # Security Headers - HSTS
    enable_hsts: bool = field(
        default_factory=lambda: os.getenv("ENABLE_HSTS", "true").lower() == "true"
    )
    hsts_max_age: int = field(
        default_factory=lambda: int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 year
    )
    hsts_include_subdomains: bool = field(
        default_factory=lambda: os.getenv("HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
    )
    hsts_preload: bool = field(
        default_factory=lambda: os.getenv("HSTS_PRELOAD", "false").lower() == "true"
    )

    # Security Headers - CSP
    enable_csp: bool = field(
        default_factory=lambda: os.getenv("ENABLE_CSP", "true").lower() == "true"
    )
    csp_directives: str = field(
        default_factory=lambda: os.getenv(
            "CSP_DIRECTIVES",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'"
        )
    )

    # Security Headers - X-Frame-Options
    enable_xframe_options: bool = field(
        default_factory=lambda: os.getenv("ENABLE_XFRAME_OPTIONS", "true").lower() == "true"
    )
    xframe_options_value: str = field(
        default_factory=lambda: os.getenv("XFRAME_OPTIONS_VALUE", "DENY")
    )

    # Security Headers - Other
    enable_content_type_nosniff: bool = field(
        default_factory=lambda: os.getenv("ENABLE_CONTENT_TYPE_NOSNIFF", "true").lower() == "true"
    )
    enable_xss_protection: bool = field(
        default_factory=lambda: os.getenv("ENABLE_XSS_PROTECTION", "true").lower() == "true"
    )
    enable_referrer_policy: bool = field(
        default_factory=lambda: os.getenv("ENABLE_REFERRER_POLICY", "true").lower() == "true"
    )
    referrer_policy_value: str = field(
        default_factory=lambda: os.getenv("REFERRER_POLICY_VALUE", "strict-origin-when-cross-origin")
    )
    enable_permissions_policy: bool = field(
        default_factory=lambda: os.getenv("ENABLE_PERMISSIONS_POLICY", "true").lower() == "true"
    )
    permissions_policy_value: str = field(
        default_factory=lambda: os.getenv(
            "PERMISSIONS_POLICY_VALUE",
            "geolocation=(), microphone=(), camera=()"
        )
    )

    # Request Validation
    max_request_size_mb: int = field(
        default_factory=lambda: int(os.getenv("MAX_REQUEST_SIZE_MB", "10"))
    )
    trusted_hosts: List[str] = field(
        default_factory=lambda: _get_trusted_hosts()
    )

    # Input Sanitization
    max_string_length: int = field(
        default_factory=lambda: int(os.getenv("MAX_STRING_LENGTH", "10000"))
    )
    allow_html_tags: bool = field(
        default_factory=lambda: os.getenv("ALLOW_HTML_TAGS", "false").lower() == "true"
    )

    # Logging
    log_security_events: bool = field(
        default_factory=lambda: os.getenv("LOG_SECURITY_EVENTS", "true").lower() == "true"
    )

    def get_hsts_header(self) -> str:
        """Generate HSTS header value."""
        value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            value += "; includeSubDomains"
        if self.hsts_preload:
            value += "; preload"
        return value


def _get_cors_origins() -> List[str]:
    """Get CORS origins from environment."""
    default_origins = "http://localhost:3000,http://localhost:8000,http://localhost:8080"
    origins_str = os.getenv("CORS_ORIGINS", default_origins)
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


def _get_trusted_hosts() -> List[str]:
    """Get trusted hosts from environment."""
    default_hosts = "localhost,127.0.0.1"
    hosts_str = os.getenv("TRUSTED_HOSTS", default_hosts)
    return [host.strip() for host in hosts_str.split(",") if host.strip()]


# Global security config instance
security_config = SecurityConfig()
