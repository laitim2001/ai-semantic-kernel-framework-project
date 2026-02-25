"""Unit tests for D365ApiClient and D365Config.

Tests cover:
    - D365Config dataclass construction, from_env(), base_url, defaults
    - D365ApiClient initialization and is_healthy property
    - CRUD operations (query, get, create, update, delete) via mocked _request
    - Automatic pagination via @odata.nextLink
    - Retry behaviour for 429, 5xx, and 401 token refresh

Sprint 129 — D365 MCP Server test suite
"""

import asyncio
import json
import os
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.mcp.servers.d365.client import (
    D365ApiClient,
    D365ApiError,
    D365Config,
    D365ConnectionError,
    D365NotFoundError,
    D365RateLimitError,
    D365ValidationError,
    ODataQueryBuilder,
    _resolve_entity_set,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def d365_config() -> D365Config:
    """Create a D365Config with test values."""
    return D365Config(
        d365_url="https://test.crm.dynamics.com",
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-123",
    )


@pytest.fixture
def d365_client(d365_config: D365Config) -> D365ApiClient:
    """Create a D365ApiClient with default (unmocked) internals."""
    with patch(
        "src.integrations.mcp.servers.d365.client.D365AuthProvider"
    ):
        client = D365ApiClient(d365_config)
    return client


@pytest.fixture
def mock_client(d365_config: D365Config) -> D365ApiClient:
    """Create a D365ApiClient with a mocked _request method."""
    with patch(
        "src.integrations.mcp.servers.d365.client.D365AuthProvider"
    ):
        client = D365ApiClient(d365_config)
    client._request = AsyncMock()  # type: ignore[method-assign]
    return client


# ---------------------------------------------------------------------------
# TestD365Config
# ---------------------------------------------------------------------------


class TestD365Config:
    """Tests for D365Config dataclass."""

    def test_default_values(self) -> None:
        """Verify default field values for optional parameters."""
        config = D365Config(
            d365_url="https://test.crm.dynamics.com",
            tenant_id="t",
            client_id="c",
            client_secret="s",
        )

        assert config.api_version == "v9.2"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_base_delay == 1.0
        assert config.max_page_size == 5000

    def test_base_url(self, d365_config: D365Config) -> None:
        """base_url property composes org URL + api/data + version."""
        expected = "https://test.crm.dynamics.com/api/data/v9.2"

        assert d365_config.base_url == expected

    def test_base_url_custom_version(self) -> None:
        """base_url reflects a custom api_version."""
        config = D365Config(
            d365_url="https://org.crm.dynamics.com",
            tenant_id="t",
            client_id="c",
            client_secret="s",
            api_version="v9.1",
        )

        assert config.base_url == "https://org.crm.dynamics.com/api/data/v9.1"

    def test_from_env_success(self) -> None:
        """from_env() reads all required D365_ environment variables."""
        env_vars = {
            "D365_URL": "https://env.crm.dynamics.com/",
            "D365_TENANT_ID": "env-tenant",
            "D365_CLIENT_ID": "env-client",
            "D365_CLIENT_SECRET": "env-secret",
            "D365_API_VERSION": "v9.1",
            "D365_TIMEOUT": "60",
            "D365_MAX_RETRIES": "5",
            "D365_MAX_PAGE_SIZE": "1000",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = D365Config.from_env()

        # Trailing slash should be stripped
        assert config.d365_url == "https://env.crm.dynamics.com"
        assert config.tenant_id == "env-tenant"
        assert config.client_id == "env-client"
        assert config.client_secret == "env-secret"
        assert config.api_version == "v9.1"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.max_page_size == 1000

    def test_from_env_missing(self) -> None:
        """from_env() raises ValueError when required vars are absent."""
        env_vars = {
            "D365_URL": "https://test.crm.dynamics.com",
            # Missing D365_TENANT_ID, D365_CLIENT_ID, D365_CLIENT_SECRET
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="Missing required"):
                D365Config.from_env()


# ---------------------------------------------------------------------------
# TestD365ApiClientInit
# ---------------------------------------------------------------------------


class TestD365ApiClientInit:
    """Tests for D365ApiClient construction and properties."""

    def test_client_init(
        self, d365_client: D365ApiClient, d365_config: D365Config
    ) -> None:
        """Client stores config and creates auth provider + httpx client."""
        assert d365_client._config is d365_config
        assert d365_client._auth is not None
        assert d365_client._client is not None

    def test_is_healthy_default(self, d365_client: D365ApiClient) -> None:
        """is_healthy starts as False before any health check."""
        assert d365_client.is_healthy is False


# ---------------------------------------------------------------------------
# TestD365ApiClientCRUD
# ---------------------------------------------------------------------------


class TestD365ApiClientCRUD:
    """Tests for D365ApiClient CRUD methods with mocked _request."""

    @pytest.mark.asyncio
    async def test_query_entities(self, mock_client: D365ApiClient) -> None:
        """query_entities calls _request with GET and entity set name."""
        mock_client._request.return_value = {"value": [{"name": "Contoso"}]}

        result = await mock_client.query_entities("account")

        mock_client._request.assert_awaited_once_with(
            method="GET",
            endpoint="accounts",
            params={},
        )
        assert result == {"value": [{"name": "Contoso"}]}

    @pytest.mark.asyncio
    async def test_query_entities_with_odata(
        self, mock_client: D365ApiClient
    ) -> None:
        """query_entities passes built OData params correctly."""
        mock_client._request.return_value = {"value": []}
        query = ODataQueryBuilder().select("name").top(5)

        await mock_client.query_entities("contact", query)

        call_kwargs = mock_client._request.call_args
        assert call_kwargs.kwargs["params"] == {"$select": "name", "$top": "5"}

    @pytest.mark.asyncio
    async def test_get_record(self, mock_client: D365ApiClient) -> None:
        """get_record calls _request with GET and entity(id) endpoint."""
        record_id = "00000000-0000-0000-0000-000000000001"
        mock_client._request.return_value = {"name": "Contoso"}

        result = await mock_client.get_record("account", record_id)

        mock_client._request.assert_awaited_once_with(
            method="GET",
            endpoint=f"accounts({record_id})",
            params=None,
        )
        assert result["name"] == "Contoso"

    @pytest.mark.asyncio
    async def test_get_record_with_select(
        self, mock_client: D365ApiClient
    ) -> None:
        """get_record includes $select param when select list is provided."""
        record_id = "00000000-0000-0000-0000-000000000002"
        mock_client._request.return_value = {"name": "Contoso"}

        await mock_client.get_record(
            "account", record_id, select=["name", "accountnumber"]
        )

        call_kwargs = mock_client._request.call_args
        assert call_kwargs.kwargs["params"] == {
            "$select": "name,accountnumber"
        }

    @pytest.mark.asyncio
    async def test_create_record(self, mock_client: D365ApiClient) -> None:
        """create_record calls _request with POST and entity data."""
        mock_client._request.return_value = {
            "accountid": "new-id",
            "name": "New Account",
        }
        data = {"name": "New Account"}

        result = await mock_client.create_record("account", data)

        mock_client._request.assert_awaited_once_with(
            method="POST",
            endpoint="accounts",
            json_data=data,
        )
        assert result["accountid"] == "new-id"

    @pytest.mark.asyncio
    async def test_update_record(self, mock_client: D365ApiClient) -> None:
        """update_record calls _request with PATCH on entity(id)."""
        record_id = "00000000-0000-0000-0000-000000000003"
        mock_client._request.return_value = {"name": "Updated"}
        data = {"name": "Updated"}

        result = await mock_client.update_record("account", record_id, data)

        mock_client._request.assert_awaited_once_with(
            method="PATCH",
            endpoint=f"accounts({record_id})",
            json_data=data,
        )
        assert result["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_record(self, mock_client: D365ApiClient) -> None:
        """delete_record calls _request with DELETE and returns True."""
        record_id = "00000000-0000-0000-0000-000000000004"
        mock_client._request.return_value = {}

        result = await mock_client.delete_record("account", record_id)

        mock_client._request.assert_awaited_once_with(
            method="DELETE",
            endpoint=f"accounts({record_id})",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, mock_client: D365ApiClient
    ) -> None:
        """health_check calls WhoAmI and sets _healthy to True."""
        mock_client._request.return_value = {
            "UserId": "user-id",
            "OrganizationId": "org-id",
        }

        result = await mock_client.health_check()

        mock_client._request.assert_awaited_once_with(
            method="GET",
            endpoint="WhoAmI",
        )
        assert result is True
        assert mock_client.is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self, mock_client: D365ApiClient
    ) -> None:
        """health_check returns False and sets _healthy=False on error."""
        mock_client._request.side_effect = D365ConnectionError(
            "Connection refused"
        )

        result = await mock_client.health_check()

        assert result is False
        assert mock_client.is_healthy is False

    @pytest.mark.asyncio
    async def test_get_entity_metadata(
        self, mock_client: D365ApiClient
    ) -> None:
        """get_entity_metadata calls EntityDefinitions endpoint."""
        mock_client._request.return_value = {
            "LogicalName": "account",
            "EntitySetName": "accounts",
        }

        result = await mock_client.get_entity_metadata("account")

        call_args = mock_client._request.call_args
        assert "EntityDefinitions" in call_args.kwargs["endpoint"]
        assert result["LogicalName"] == "account"

    @pytest.mark.asyncio
    async def test_list_entity_types(
        self, mock_client: D365ApiClient
    ) -> None:
        """list_entity_types returns value list from EntityDefinitions."""
        mock_client._request.return_value = {
            "value": [
                {"LogicalName": "account"},
                {"LogicalName": "contact"},
            ]
        }

        result = await mock_client.list_entity_types()

        assert len(result) == 2
        assert result[0]["LogicalName"] == "account"


# ---------------------------------------------------------------------------
# TestD365ApiClientPagination
# ---------------------------------------------------------------------------


class TestD365ApiClientPagination:
    """Tests for query_entities_all automatic pagination."""

    @pytest.mark.asyncio
    async def test_single_page(self, mock_client: D365ApiClient) -> None:
        """Single page result (no nextLink) returns all records."""
        mock_client._request.return_value = {
            "value": [{"name": "A"}, {"name": "B"}],
        }

        result = await mock_client.query_entities_all("account")

        assert len(result) == 2
        assert result[0]["name"] == "A"

    @pytest.mark.asyncio
    async def test_multi_page(self, mock_client: D365ApiClient) -> None:
        """Follows @odata.nextLink to fetch multiple pages."""
        page1 = {
            "value": [{"name": "A"}],
            "@odata.nextLink": "https://test.crm.dynamics.com/api/data/v9.2/accounts?$skiptoken=1",
        }
        page2 = {
            "value": [{"name": "B"}],
            "@odata.nextLink": "https://test.crm.dynamics.com/api/data/v9.2/accounts?$skiptoken=2",
        }
        page3 = {
            "value": [{"name": "C"}],
        }

        mock_client._request.side_effect = [page1, page2, page3]

        result = await mock_client.query_entities_all("account")

        assert len(result) == 3
        assert [r["name"] for r in result] == ["A", "B", "C"]
        # First call is query_entities -> _request, then 2 nextLink calls
        assert mock_client._request.await_count == 3

    @pytest.mark.asyncio
    async def test_max_pages_limit(self, mock_client: D365ApiClient) -> None:
        """Stops fetching when max_pages limit is reached."""
        page_with_next = {
            "value": [{"name": "X"}],
            "@odata.nextLink": "https://test.crm.dynamics.com/api/data/v9.2/accounts?next",
        }

        # Always return a page with nextLink — pagination would be infinite
        mock_client._request.return_value = page_with_next

        result = await mock_client.query_entities_all(
            "account", max_pages=3
        )

        # Should have fetched exactly 3 pages then stopped
        assert len(result) == 3
        assert mock_client._request.await_count == 3


# ---------------------------------------------------------------------------
# TestD365ApiClientRetry
# ---------------------------------------------------------------------------


class TestD365ApiClientRetry:
    """Tests for D365ApiClient retry logic in _request.

    These tests mock the httpx AsyncClient directly to exercise the
    actual retry logic inside _request.
    """

    @pytest.mark.asyncio
    async def test_retry_on_429(self, d365_config: D365Config) -> None:
        """Retries after receiving a 429 rate limit response."""
        with patch(
            "src.integrations.mcp.servers.d365.client.D365AuthProvider"
        ) as mock_auth_cls:
            mock_auth = mock_auth_cls.return_value
            mock_auth.ensure_token = AsyncMock(return_value="test-token")
            mock_auth.invalidate_token = MagicMock()

            # Use 1 retry (total 2 attempts) with zero delay
            config = D365Config(
                d365_url="https://test.crm.dynamics.com",
                tenant_id="t",
                client_id="c",
                client_secret="s",
                max_retries=2,
                retry_base_delay=0.0,
            )
            client = D365ApiClient(config)

            # First response: 429, second response: 200
            response_429 = MagicMock(spec=httpx.Response)
            response_429.status_code = 429
            response_429.headers = {"Retry-After": "0"}
            response_429.text = "Rate limited"

            response_200 = MagicMock(spec=httpx.Response)
            response_200.status_code = 200
            response_200.content = b'{"value": []}'
            response_200.json.return_value = {"value": []}

            client._client.request = AsyncMock(
                side_effect=[response_429, response_200]
            )

            result = await client._request("GET", "accounts")

            assert result == {"value": []}
            assert client._client.request.await_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_500(self, d365_config: D365Config) -> None:
        """Retries after receiving a 500 server error response."""
        with patch(
            "src.integrations.mcp.servers.d365.client.D365AuthProvider"
        ) as mock_auth_cls:
            mock_auth = mock_auth_cls.return_value
            mock_auth.ensure_token = AsyncMock(return_value="test-token")

            config = D365Config(
                d365_url="https://test.crm.dynamics.com",
                tenant_id="t",
                client_id="c",
                client_secret="s",
                max_retries=2,
                retry_base_delay=0.0,
            )
            client = D365ApiClient(config)

            response_500 = MagicMock(spec=httpx.Response)
            response_500.status_code = 500
            response_500.text = "Internal Server Error"
            response_500.headers = {}

            response_200 = MagicMock(spec=httpx.Response)
            response_200.status_code = 200
            response_200.content = b'{"ok": true}'
            response_200.json.return_value = {"ok": True}

            client._client.request = AsyncMock(
                side_effect=[response_500, response_200]
            )

            result = await client._request("GET", "accounts")

            assert result == {"ok": True}
            assert client._client.request.await_count == 2

    @pytest.mark.asyncio
    async def test_401_refreshes_token(
        self, d365_config: D365Config
    ) -> None:
        """On 401, invalidates token and retries with a fresh token."""
        with patch(
            "src.integrations.mcp.servers.d365.client.D365AuthProvider"
        ) as mock_auth_cls:
            mock_auth = mock_auth_cls.return_value
            mock_auth.ensure_token = AsyncMock(
                side_effect=["old-token", "new-token"]
            )
            mock_auth.invalidate_token = MagicMock()

            config = D365Config(
                d365_url="https://test.crm.dynamics.com",
                tenant_id="t",
                client_id="c",
                client_secret="s",
                max_retries=2,
                retry_base_delay=0.0,
            )
            client = D365ApiClient(config)

            response_401 = MagicMock(spec=httpx.Response)
            response_401.status_code = 401
            response_401.text = "Unauthorized"
            response_401.headers = {}

            response_200 = MagicMock(spec=httpx.Response)
            response_200.status_code = 200
            response_200.content = b'{"UserId": "u1"}'
            response_200.json.return_value = {"UserId": "u1"}

            client._client.request = AsyncMock(
                side_effect=[response_401, response_200]
            )

            result = await client._request("GET", "WhoAmI")

            # Token was invalidated and re-acquired
            mock_auth.invalidate_token.assert_called_once()
            assert mock_auth.ensure_token.await_count == 2
            assert result == {"UserId": "u1"}

    @pytest.mark.asyncio
    async def test_429_exhausts_retries(
        self, d365_config: D365Config
    ) -> None:
        """Raises D365RateLimitError after all retries are exhausted."""
        with patch(
            "src.integrations.mcp.servers.d365.client.D365AuthProvider"
        ) as mock_auth_cls:
            mock_auth = mock_auth_cls.return_value
            mock_auth.ensure_token = AsyncMock(return_value="test-token")

            config = D365Config(
                d365_url="https://test.crm.dynamics.com",
                tenant_id="t",
                client_id="c",
                client_secret="s",
                max_retries=2,
                retry_base_delay=0.0,
            )
            client = D365ApiClient(config)

            response_429 = MagicMock(spec=httpx.Response)
            response_429.status_code = 429
            response_429.headers = {"Retry-After": "0"}
            response_429.text = "Rate limited"

            client._client.request = AsyncMock(
                return_value=response_429
            )

            with pytest.raises(D365RateLimitError, match="Rate limit"):
                await client._request("GET", "accounts")
