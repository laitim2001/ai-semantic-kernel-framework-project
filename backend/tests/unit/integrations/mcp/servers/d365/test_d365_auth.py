"""Tests for D365AuthProvider — Sprint 129, Story 129-1.

Tests cover:
    - D365AuthConfig construction, from_env(), trailing-slash stripping, frozen immutability
    - D365AuthProvider token scope initialization
    - Token acquisition (initial, cached, expired, within-buffer refresh)
    - Error handling (non-200 response, missing access_token field, network error)
    - Token invalidation and auth header generation
    - Token validity checks (no token, valid token)
    - Lifecycle (close clears state, async context manager)

Total: 17 tests across 3 test classes.
"""

import time
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.mcp.servers.d365.auth import (
    D365AuthConfig,
    D365AuthenticationError,
    D365AuthProvider,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def d365_config():
    """Create a test D365AuthConfig with typical values."""
    return D365AuthConfig(
        tenant_id="tenant-test-001",
        client_id="client-test-001",
        client_secret="secret-test-001",
        d365_url="https://org-test.crm.dynamics.com",
    )


@pytest.fixture
def auth_provider(d365_config):
    """Create a D365AuthProvider with a pre-cached valid token."""
    provider = D365AuthProvider(d365_config)
    provider._access_token = "cached-token-abc"
    provider._token_expiry = time.time() + 3600
    return provider


@pytest.fixture
def mock_token_response():
    """Create a mock httpx.Response factory for token endpoint responses."""

    def _create(status_code=200, access_token="fresh-token-xyz", expires_in=3600, text=""):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.text = text if text else ("" if status_code == 200 else "Unauthorized")
        if status_code == 200:
            response.json.return_value = {
                "access_token": access_token,
                "expires_in": expires_in,
                "token_type": "Bearer",
            }
        else:
            response.json.return_value = {
                "error": "invalid_client",
                "error_description": "Client authentication failed",
            }
        return response

    return _create


# ---------------------------------------------------------------------------
# 1. TestD365AuthConfig — Configuration (5 tests)
# ---------------------------------------------------------------------------


class TestD365AuthConfig:
    """Tests for D365AuthConfig frozen dataclass and from_env() classmethod."""

    def test_config_fields(self):
        """Test creating D365AuthConfig with all fields and verifying each value."""
        config = D365AuthConfig(
            tenant_id="tenant-aaa",
            client_id="client-bbb",
            client_secret="secret-ccc",
            d365_url="https://org.crm.dynamics.com",
        )

        assert config.tenant_id == "tenant-aaa"
        assert config.client_id == "client-bbb"
        assert config.client_secret == "secret-ccc"
        assert config.d365_url == "https://org.crm.dynamics.com"

    def test_from_env_success(self, monkeypatch):
        """Test creating config from environment variables with all required vars set."""
        monkeypatch.setenv("D365_TENANT_ID", "tenant-env-001")
        monkeypatch.setenv("D365_CLIENT_ID", "client-env-001")
        monkeypatch.setenv("D365_CLIENT_SECRET", "secret-env-001")
        monkeypatch.setenv("D365_URL", "https://org-env.crm.dynamics.com")

        config = D365AuthConfig.from_env()

        assert config.tenant_id == "tenant-env-001"
        assert config.client_id == "client-env-001"
        assert config.client_secret == "secret-env-001"
        assert config.d365_url == "https://org-env.crm.dynamics.com"

    def test_from_env_missing_vars(self, monkeypatch):
        """Test that missing required env vars raises ValueError listing the missing names."""
        monkeypatch.delenv("D365_TENANT_ID", raising=False)
        monkeypatch.delenv("D365_CLIENT_ID", raising=False)
        monkeypatch.delenv("D365_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("D365_URL", raising=False)

        with pytest.raises(ValueError, match="Missing required environment variables"):
            D365AuthConfig.from_env()

    def test_from_env_strips_trailing_slash(self, monkeypatch):
        """Test that a trailing slash on D365_URL is stripped during from_env()."""
        monkeypatch.setenv("D365_TENANT_ID", "tenant-strip")
        monkeypatch.setenv("D365_CLIENT_ID", "client-strip")
        monkeypatch.setenv("D365_CLIENT_SECRET", "secret-strip")
        monkeypatch.setenv("D365_URL", "https://org.crm.dynamics.com/")

        config = D365AuthConfig.from_env()

        assert config.d365_url == "https://org.crm.dynamics.com"
        assert not config.d365_url.endswith("/")

    def test_frozen_immutability(self, d365_config):
        """Test that frozen=True prevents mutation of config attributes."""
        with pytest.raises(FrozenInstanceError):
            d365_config.tenant_id = "modified-tenant"

        with pytest.raises(FrozenInstanceError):
            d365_config.client_secret = "modified-secret"


# ---------------------------------------------------------------------------
# 2. TestD365AuthProvider — Token management (13 tests)
# ---------------------------------------------------------------------------


class TestD365AuthProvider:
    """Tests for D365AuthProvider token acquisition, caching, refresh, and helpers."""

    def test_init_sets_token_scope(self, d365_config):
        """Test that __init__ sets _token_scope to '{d365_url}/.default'."""
        provider = D365AuthProvider(d365_config)

        assert provider._token_scope == "https://org-test.crm.dynamics.com/.default"

    @pytest.mark.asyncio
    async def test_ensure_token_acquires_on_first_call(self, d365_config, mock_token_response):
        """Test initial token acquisition via POST to the Azure AD token endpoint."""
        provider = D365AuthProvider(d365_config)
        mock_resp = mock_token_response(access_token="first-token-999", expires_in=7200)
        provider._http_client.post = AsyncMock(return_value=mock_resp)

        token = await provider.ensure_token()

        assert token == "first-token-999"
        assert provider._access_token == "first-token-999"
        provider._http_client.post.assert_called_once()

        # Verify the token URL contains the tenant_id
        call_args = provider._http_client.post.call_args
        token_url = call_args[0][0]
        assert "tenant-test-001" in token_url

        # Verify client_credentials grant data
        post_data = call_args[1]["data"]
        assert post_data["grant_type"] == "client_credentials"
        assert post_data["client_id"] == "client-test-001"
        assert post_data["client_secret"] == "secret-test-001"
        assert post_data["scope"] == "https://org-test.crm.dynamics.com/.default"

    @pytest.mark.asyncio
    async def test_ensure_token_returns_cached(self, auth_provider):
        """Test that a valid cached token is returned without issuing an HTTP request."""
        auth_provider._http_client.post = AsyncMock()

        token = await auth_provider.ensure_token()

        assert token == "cached-token-abc"
        auth_provider._http_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_token_refreshes_expired(self, d365_config, mock_token_response):
        """Test that an expired token triggers a fresh token request."""
        provider = D365AuthProvider(d365_config)
        provider._access_token = "old-expired-token"
        provider._token_expiry = time.time() - 100  # Already expired

        mock_resp = mock_token_response(access_token="refreshed-token-777")
        provider._http_client.post = AsyncMock(return_value=mock_resp)

        token = await provider.ensure_token()

        assert token == "refreshed-token-777"
        assert provider._access_token == "refreshed-token-777"
        provider._http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_token_refreshes_within_buffer(self, d365_config, mock_token_response):
        """Test that a token within TOKEN_REFRESH_BUFFER (300s) of expiry is refreshed."""
        provider = D365AuthProvider(d365_config)
        provider._access_token = "soon-expiring-token"
        # Set expiry to 200 seconds from now — less than the 300s buffer
        provider._token_expiry = time.time() + 200

        mock_resp = mock_token_response(access_token="buffer-refreshed-token")
        provider._http_client.post = AsyncMock(return_value=mock_resp)

        token = await provider.ensure_token()

        assert token == "buffer-refreshed-token"
        provider._http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_token_non_200_raises(self, d365_config):
        """Test that a non-200 response from the token endpoint raises D365AuthenticationError."""
        provider = D365AuthProvider(d365_config)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 401
        mock_resp.text = "Invalid client credentials"
        provider._http_client.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(D365AuthenticationError, match="Token acquisition failed with status 401"):
            await provider.ensure_token()

    @pytest.mark.asyncio
    async def test_acquire_token_missing_field_raises(self, d365_config):
        """Test that a 200 response without 'access_token' raises D365AuthenticationError."""
        provider = D365AuthProvider(d365_config)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "token_type": "Bearer",
            "expires_in": 3600,
            # Intentionally missing "access_token"
        }
        provider._http_client.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(D365AuthenticationError, match="missing 'access_token' field"):
            await provider.ensure_token()

    @pytest.mark.asyncio
    async def test_acquire_token_network_error_raises(self, d365_config):
        """Test that an httpx.HTTPError during token acquisition raises D365AuthenticationError."""
        provider = D365AuthProvider(d365_config)
        provider._http_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(D365AuthenticationError, match="network error"):
            await provider.ensure_token()

    def test_invalidate_token_clears_cache(self, auth_provider, mock_token_response):
        """Test that invalidate_token clears the cached token and expiry."""
        # Verify token exists before invalidation
        assert auth_provider._access_token == "cached-token-abc"
        assert auth_provider.is_token_valid() is True

        auth_provider.invalidate_token()

        assert auth_provider._access_token is None
        assert auth_provider._token_expiry == 0.0
        assert auth_provider.is_token_valid() is False

    def test_get_auth_headers_with_token(self, auth_provider):
        """Test that get_auth_headers returns correct Bearer header with cached token."""
        headers = auth_provider.get_auth_headers()

        assert headers == {"Authorization": "Bearer cached-token-abc"}

    def test_get_auth_headers_without_token(self, d365_config):
        """Test that get_auth_headers returns empty bearer when no token is cached."""
        provider = D365AuthProvider(d365_config)

        headers = provider.get_auth_headers()

        assert headers == {"Authorization": "Bearer "}

    def test_is_token_valid_no_token(self, d365_config):
        """Test that is_token_valid returns False when no token is cached."""
        provider = D365AuthProvider(d365_config)

        assert provider.is_token_valid() is False

    def test_is_token_valid_with_valid_token(self, auth_provider):
        """Test that is_token_valid returns True for a non-expired token outside buffer."""
        assert auth_provider.is_token_valid() is True


# ---------------------------------------------------------------------------
# 3. TestD365AuthProviderLifecycle — Lifecycle management (2 tests)
# ---------------------------------------------------------------------------


class TestD365AuthProviderLifecycle:
    """Tests for D365AuthProvider close() and async context manager."""

    @pytest.mark.asyncio
    async def test_close_clears_state(self, auth_provider):
        """Test that close() clears the cached token and closes the HTTP client."""
        auth_provider._http_client.aclose = AsyncMock()

        await auth_provider.close()

        assert auth_provider._access_token is None
        assert auth_provider._token_expiry == 0.0
        auth_provider._http_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, d365_config):
        """Test that async with D365AuthProvider(...) as auth calls close on exit."""
        with patch.object(D365AuthProvider, "close", new_callable=AsyncMock) as mock_close:
            async with D365AuthProvider(d365_config) as auth:
                assert isinstance(auth, D365AuthProvider)

            mock_close.assert_called_once()
