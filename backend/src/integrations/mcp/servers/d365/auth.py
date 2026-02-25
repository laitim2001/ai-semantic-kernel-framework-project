"""Dynamics 365 OAuth Authentication Provider.

Provides Service Principal (client_credentials) authentication for the
Dynamics 365 Web API via Azure AD OAuth 2.0 token endpoint.

Features:
    - Client Credentials Grant flow (client_id + client_secret + tenant_id)
    - Automatic token caching with configurable refresh buffer
    - Token invalidation for 401 retry scenarios
    - Async HTTP via httpx.AsyncClient

Environment Variables:
    D365_TENANT_ID: Azure AD tenant ID (required)
    D365_CLIENT_ID: App registration client ID (required)
    D365_CLIENT_SECRET: App registration client secret (required)
    D365_URL: D365 instance URL, e.g. https://org.crm.dynamics.com (required)

Reference:
    - OAuth 2.0 client credentials:
      https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow
    - D365 Web API authentication:
      https://learn.microsoft.com/en-us/power-apps/developer/data-platform/authenticate-oauth
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class D365AuthenticationError(Exception):
    """Raised when D365 token acquisition or authentication fails.

    Attributes:
        message: Error description
        status_code: HTTP status code from the token endpoint (if available)
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class D365AuthConfig:
    """Dynamics 365 authentication configuration.

    Attributes:
        tenant_id: Azure AD tenant ID
        client_id: App registration client ID
        client_secret: App registration client secret
        d365_url: D365 instance URL (e.g. https://org.crm.dynamics.com)
    """

    tenant_id: str
    client_id: str
    client_secret: str
    d365_url: str

    @classmethod
    def from_env(cls) -> "D365AuthConfig":
        """Create configuration from environment variables.

        Returns:
            D365AuthConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """
        required_vars = [
            "D365_TENANT_ID",
            "D365_CLIENT_ID",
            "D365_CLIENT_SECRET",
            "D365_URL",
        ]

        missing = [v for v in required_vars if not os.environ.get(v)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            tenant_id=os.environ["D365_TENANT_ID"],
            client_id=os.environ["D365_CLIENT_ID"],
            client_secret=os.environ["D365_CLIENT_SECRET"],
            d365_url=os.environ["D365_URL"].rstrip("/"),
        )


# ---------------------------------------------------------------------------
# Auth Provider
# ---------------------------------------------------------------------------


class D365AuthProvider:
    """Dynamics 365 OAuth 2.0 authentication provider.

    Manages token acquisition and caching for D365 Web API access using
    the OAuth 2.0 Client Credentials Grant flow.

    The provider automatically refreshes expired tokens and supports
    explicit invalidation for 401 retry scenarios.

    Example:
        >>> config = D365AuthConfig.from_env()
        >>> auth = D365AuthProvider(config)
        >>> token = await auth.ensure_token()
        >>> headers = auth.get_auth_headers()
        >>> await auth.close()

    Context Manager:
        >>> async with D365AuthProvider(config) as auth:
        ...     headers = auth.get_auth_headers()
    """

    TOKEN_URL_TEMPLATE = (
        "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    )
    TOKEN_REFRESH_BUFFER = 300  # 5 minutes before expiry

    def __init__(self, config: D365AuthConfig):
        """Initialize the authentication provider.

        Args:
            config: D365 authentication configuration
        """
        self._config = config
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
        )
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._token_scope = f"{config.d365_url}/.default"

        logger.info(
            "D365AuthProvider initialized for tenant=%s, url=%s",
            config.tenant_id,
            config.d365_url,
        )

    # -----------------------------------------------------------------------
    # Token management
    # -----------------------------------------------------------------------

    async def ensure_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns a cached token when still valid. Acquires a new token
        via Client Credentials Grant when the cached token is missing
        or within TOKEN_REFRESH_BUFFER seconds of expiry.

        Returns:
            Valid access token string

        Raises:
            D365AuthenticationError: If token acquisition fails
        """
        if self.is_token_valid():
            return self._access_token  # type: ignore[return-value]

        logger.debug("Token missing or expired, acquiring new token")
        token, expires_in = await self._acquire_token()

        self._access_token = token
        self._token_expiry = time.time() + expires_in

        logger.debug(
            "D365 access token acquired, expires_in=%ds", expires_in
        )
        return self._access_token

    async def _acquire_token(self) -> Tuple[str, int]:
        """Acquire a new access token from Azure AD token endpoint.

        Performs an OAuth 2.0 Client Credentials Grant request against
        the Azure AD v2.0 token endpoint.

        Returns:
            Tuple of (access_token, expires_in_seconds)

        Raises:
            D365AuthenticationError: If the token request fails
        """
        token_url = self.TOKEN_URL_TEMPLATE.format(
            tenant_id=self._config.tenant_id,
        )

        try:
            response = await self._http_client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                    "scope": self._token_scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_detail = response.text[:500]
                logger.error(
                    "D365 token acquisition failed: status=%d, body=%s",
                    response.status_code,
                    error_detail,
                )
                raise D365AuthenticationError(
                    f"Token acquisition failed with status {response.status_code}: "
                    f"{error_detail}",
                    status_code=response.status_code,
                )

            token_data = response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise D365AuthenticationError(
                    "Token response missing 'access_token' field"
                )

            expires_in = int(token_data.get("expires_in", 3600))
            return access_token, expires_in

        except httpx.HTTPError as exc:
            logger.error("D365 token request failed: %s", exc)
            raise D365AuthenticationError(
                f"Token request failed due to network error: {exc}"
            ) from exc

    def is_token_valid(self) -> bool:
        """Check whether the cached token is still valid.

        A token is considered valid when it exists and the current time
        is before (expiry - TOKEN_REFRESH_BUFFER).

        Returns:
            True if the cached token can be used without refresh
        """
        if self._access_token is None:
            return False
        return time.time() < (self._token_expiry - self.TOKEN_REFRESH_BUFFER)

    def invalidate_token(self) -> None:
        """Force-clear the cached token.

        Call this after receiving a 401 response so that the next call
        to ensure_token() will acquire a fresh token.
        """
        self._access_token = None
        self._token_expiry = 0.0
        logger.debug("D365 access token invalidated")

    def get_auth_headers(self) -> Dict[str, str]:
        """Return HTTP authorization headers with the current token.

        Returns:
            Dict containing the Authorization header. If no token is
            cached, the header value will contain an empty bearer token.
        """
        token = self._access_token or ""
        return {"Authorization": f"Bearer {token}"}

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        await self._http_client.aclose()
        self._access_token = None
        self._token_expiry = 0.0
        logger.info("D365AuthProvider closed")

    async def __aenter__(self) -> "D365AuthProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.close()
