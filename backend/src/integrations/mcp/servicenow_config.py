"""ServiceNow connection configuration.

Provides environment-based configuration for ServiceNow Table API access.
Supports Basic Auth and OAuth2 Token authentication methods.

Sprint 117 — ServiceNow MCP Server
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AuthMethod(str, Enum):
    """ServiceNow authentication method."""

    BASIC = "basic"
    OAUTH2 = "oauth2"


@dataclass(frozen=True)
class ServiceNowConfig:
    """ServiceNow instance connection configuration.

    Attributes:
        instance_url: ServiceNow instance base URL (e.g., https://company.service-now.com)
        username: Username for Basic Auth
        password: Password for Basic Auth
        oauth_token: OAuth2 bearer token (alternative to username/password)
        auth_method: Authentication method (basic or oauth2)
        api_version: ServiceNow REST API version (default: v2)
        timeout: HTTP request timeout in seconds (default: 30)
        max_retries: Maximum retry attempts for transient errors (default: 3)
        retry_base_delay: Base delay for exponential backoff in seconds (default: 1.0)

    Example:
        >>> config = ServiceNowConfig.from_env()
        >>> config.base_url
        'https://company.service-now.com/api/now/v2'
    """

    instance_url: str
    username: str = ""
    password: str = ""
    oauth_token: str = ""
    auth_method: AuthMethod = AuthMethod.BASIC
    api_version: str = "v2"
    timeout: int = 30
    max_retries: int = 3
    retry_base_delay: float = 1.0

    @property
    def base_url(self) -> str:
        """Full API base URL including version."""
        url = self.instance_url.rstrip("/")
        return f"{url}/api/now/{self.api_version}"

    @property
    def attachment_url(self) -> str:
        """Attachment API base URL."""
        url = self.instance_url.rstrip("/")
        return f"{url}/api/now/attachment"

    @property
    def auth_tuple(self) -> Optional[tuple]:
        """HTTP Basic Auth tuple for httpx."""
        if self.auth_method == AuthMethod.BASIC and self.username and self.password:
            return (self.username, self.password)
        return None

    @property
    def auth_headers(self) -> dict:
        """Authorization headers for OAuth2."""
        if self.auth_method == AuthMethod.OAUTH2 and self.oauth_token:
            return {"Authorization": f"Bearer {self.oauth_token}"}
        return {}

    def validate(self) -> list:
        """Validate configuration, returns list of error messages."""
        errors = []
        if not self.instance_url:
            errors.append("instance_url is required")
        if not self.instance_url.startswith(("http://", "https://")):
            errors.append("instance_url must start with http:// or https://")
        if self.auth_method == AuthMethod.BASIC:
            if not self.username:
                errors.append("username is required for Basic Auth")
            if not self.password:
                errors.append("password is required for Basic Auth")
        elif self.auth_method == AuthMethod.OAUTH2:
            if not self.oauth_token:
                errors.append("oauth_token is required for OAuth2 Auth")
        if self.timeout < 1:
            errors.append("timeout must be at least 1 second")
        if self.max_retries < 0:
            errors.append("max_retries must be non-negative")
        return errors

    @classmethod
    def from_env(cls) -> "ServiceNowConfig":
        """Create configuration from environment variables.

        Environment Variables:
            SERVICENOW_INSTANCE_URL: ServiceNow instance URL (required)
            SERVICENOW_USERNAME: Username for Basic Auth
            SERVICENOW_PASSWORD: Password for Basic Auth
            SERVICENOW_OAUTH_TOKEN: OAuth2 bearer token
            SERVICENOW_AUTH_METHOD: Auth method (basic|oauth2, default: basic)
            SERVICENOW_API_VERSION: API version (default: v2)
            SERVICENOW_TIMEOUT: Request timeout seconds (default: 30)
            SERVICENOW_MAX_RETRIES: Max retry attempts (default: 3)
        """
        auth_method_str = os.environ.get("SERVICENOW_AUTH_METHOD", "basic").lower()
        try:
            auth_method = AuthMethod(auth_method_str)
        except ValueError:
            auth_method = AuthMethod.BASIC

        timeout_str = os.environ.get("SERVICENOW_TIMEOUT", "30")
        try:
            timeout = int(timeout_str)
        except (ValueError, TypeError):
            timeout = 30

        max_retries_str = os.environ.get("SERVICENOW_MAX_RETRIES", "3")
        try:
            max_retries = int(max_retries_str)
        except (ValueError, TypeError):
            max_retries = 3

        return cls(
            instance_url=os.environ.get("SERVICENOW_INSTANCE_URL", ""),
            username=os.environ.get("SERVICENOW_USERNAME", ""),
            password=os.environ.get("SERVICENOW_PASSWORD", ""),
            oauth_token=os.environ.get("SERVICENOW_OAUTH_TOKEN", ""),
            auth_method=auth_method,
            api_version=os.environ.get("SERVICENOW_API_VERSION", "v2"),
            timeout=timeout,
            max_retries=max_retries,
        )

    def to_dict(self) -> dict:
        """Export configuration as dictionary (excludes secrets)."""
        return {
            "instance_url": self.instance_url,
            "auth_method": self.auth_method.value,
            "api_version": self.api_version,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_base_delay": self.retry_base_delay,
            "base_url": self.base_url,
        }
