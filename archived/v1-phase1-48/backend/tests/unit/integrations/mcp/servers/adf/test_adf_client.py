"""Tests for AdfApiClient — Sprint 127, Story 127-2.

Tests cover:
    - AdfConfig construction, from_env(), base_url property, defaults
    - AdfApiClient token management (acquire, cache, refresh, failure)
    - Pipeline operations (list, get, run with params, cancel)
    - Monitoring operations (get run, list runs, default timerange, datasets, triggers)
    - Retry/resilience (connection error, timeout, exhausted, rate limit, no-retry 404/auth)
    - Health check (success and failure)
    - PipelineRunStatus enum values and string comparison

Total: 30 tests across 6 test classes.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.mcp.servers.adf.client import (
    AdfApiClient,
    AdfApiError,
    AdfAuthenticationError,
    AdfConfig,
    AdfConnectionError,
    AdfNotFoundError,
    AdfRateLimitError,
    PipelineRunStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adf_config():
    """Create a test AdfConfig with fast retry for tests."""
    return AdfConfig(
        subscription_id="sub-123",
        resource_group="rg-test",
        factory_name="adf-test",
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-123",
        timeout=5,
        max_retries=1,
    )


@pytest.fixture
def adf_client(adf_config):
    """Create a test AdfApiClient with a pre-cached token."""
    client = AdfApiClient(adf_config)
    client._access_token = "test-token-abc"
    client._token_expiry = time.time() + 3600
    return client


@pytest.fixture
def mock_response():
    """Create a mock httpx.Response factory."""

    def _create(status_code=200, json_data=None, text="", headers=None, content=b"ok"):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.text = text
        response.headers = headers or {}
        response.json.return_value = json_data or {}
        response.content = content
        return response

    return _create


@pytest.fixture
def mock_token_response():
    """Create a mock token endpoint response."""

    def _create(status_code=200, access_token="fresh-token-xyz", expires_in=3600):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.text = "" if status_code == 200 else "Unauthorized"
        response.json.return_value = {
            "access_token": access_token,
            "expires_in": expires_in,
            "token_type": "Bearer",
        }
        return response

    return _create


# ---------------------------------------------------------------------------
# 1. TestAdfConfig — Configuration (4 tests)
# ---------------------------------------------------------------------------


class TestAdfConfig:
    """Tests for AdfConfig configuration dataclass."""

    def test_config_construction(self):
        """Test creating AdfConfig with all fields and verify each value."""
        config = AdfConfig(
            subscription_id="sub-aaa",
            resource_group="rg-bbb",
            factory_name="adf-ccc",
            tenant_id="tenant-ddd",
            client_id="client-eee",
            client_secret="secret-fff",
            timeout=60,
            max_retries=5,
            retry_base_delay=2.0,
        )

        assert config.subscription_id == "sub-aaa"
        assert config.resource_group == "rg-bbb"
        assert config.factory_name == "adf-ccc"
        assert config.tenant_id == "tenant-ddd"
        assert config.client_id == "client-eee"
        assert config.client_secret == "secret-fff"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_base_delay == 2.0

    def test_config_from_env(self, monkeypatch):
        """Test creating config from environment variables including optional overrides."""
        monkeypatch.setenv("ADF_SUBSCRIPTION_ID", "sub-env-001")
        monkeypatch.setenv("ADF_RESOURCE_GROUP", "rg-env-prod")
        monkeypatch.setenv("ADF_FACTORY_NAME", "adf-env-factory")
        monkeypatch.setenv("ADF_TENANT_ID", "tenant-env-001")
        monkeypatch.setenv("ADF_CLIENT_ID", "client-env-001")
        monkeypatch.setenv("ADF_CLIENT_SECRET", "secret-env-001")
        monkeypatch.setenv("ADF_TIMEOUT", "45")
        monkeypatch.setenv("ADF_MAX_RETRIES", "5")

        config = AdfConfig.from_env()

        assert config.subscription_id == "sub-env-001"
        assert config.resource_group == "rg-env-prod"
        assert config.factory_name == "adf-env-factory"
        assert config.tenant_id == "tenant-env-001"
        assert config.client_id == "client-env-001"
        assert config.client_secret == "secret-env-001"
        assert config.timeout == 45
        assert config.max_retries == 5

    def test_config_from_env_missing_vars(self, monkeypatch):
        """Test that missing required env vars raises ValueError with variable names."""
        monkeypatch.delenv("ADF_SUBSCRIPTION_ID", raising=False)
        monkeypatch.delenv("ADF_RESOURCE_GROUP", raising=False)
        monkeypatch.delenv("ADF_FACTORY_NAME", raising=False)
        monkeypatch.delenv("ADF_TENANT_ID", raising=False)
        monkeypatch.delenv("ADF_CLIENT_ID", raising=False)
        monkeypatch.delenv("ADF_CLIENT_SECRET", raising=False)

        with pytest.raises(ValueError, match="Missing required environment variables"):
            AdfConfig.from_env()

    def test_config_base_url_property(self, adf_config):
        """Test base_url constructs the correct Azure Management REST API URL."""
        expected = (
            "https://management.azure.com/subscriptions/sub-123"
            "/resourceGroups/rg-test"
            "/providers/Microsoft.DataFactory/factories/adf-test"
        )
        assert adf_config.base_url == expected


# ---------------------------------------------------------------------------
# 2. TestAdfApiClientAuth — Authentication (5 tests)
# ---------------------------------------------------------------------------


class TestAdfApiClientAuth:
    """Tests for AdfApiClient token acquisition, caching, and refresh."""

    @pytest.mark.asyncio
    async def test_ensure_token_initial(self, adf_config, mock_token_response):
        """Test initial token acquisition from the OAuth2 token endpoint."""
        client = AdfApiClient(adf_config)
        mock_resp = mock_token_response(access_token="new-token-999", expires_in=7200)
        client._client.post = AsyncMock(return_value=mock_resp)

        token = await client._ensure_token()

        assert token == "new-token-999"
        assert client._access_token == "new-token-999"
        client._client.post.assert_called_once()

        # Verify the token URL contains the tenant_id
        call_args = client._client.post.call_args
        assert "tenant-123" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_ensure_token_cached(self, adf_client):
        """Test that a valid cached token is returned without issuing an HTTP request."""
        adf_client._client.post = AsyncMock()

        token = await adf_client._ensure_token()

        assert token == "test-token-abc"
        adf_client._client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_token_refresh_on_expiry(self, adf_config, mock_token_response):
        """Test that an expired token triggers a fresh token request."""
        client = AdfApiClient(adf_config)
        # Set a token that has already expired (past the 5-min buffer)
        client._access_token = "old-expired-token"
        client._token_expiry = time.time() - 100  # Expired

        mock_resp = mock_token_response(access_token="refreshed-token-777")
        client._client.post = AsyncMock(return_value=mock_resp)

        token = await client._ensure_token()

        assert token == "refreshed-token-777"
        assert client._access_token == "refreshed-token-777"
        client._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_token_failure(self, adf_config, mock_token_response):
        """Test that a non-200 from the token endpoint raises AdfAuthenticationError."""
        client = AdfApiClient(adf_config)
        mock_resp = mock_token_response(status_code=400)
        client._client.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(AdfAuthenticationError, match="Token acquisition failed"):
            await client._ensure_token()

    @pytest.mark.asyncio
    async def test_auto_refresh_on_401(self, adf_config, mock_response, mock_token_response):
        """Test that a 401 response on first attempt triggers token refresh and retry."""
        config = AdfConfig(
            subscription_id="sub-123",
            resource_group="rg-test",
            factory_name="adf-test",
            tenant_id="tenant-123",
            client_id="client-123",
            client_secret="secret-123",
            timeout=5,
            max_retries=2,
            retry_base_delay=0.01,
        )
        client = AdfApiClient(config)
        client._access_token = "stale-token"
        client._token_expiry = time.time() + 3600

        # First request returns 401, second request succeeds after token refresh
        mock_resp_401 = mock_response(status_code=401, text="Unauthorized")
        mock_resp_ok = mock_response(json_data={"value": []})
        client._client.request = AsyncMock(side_effect=[mock_resp_401, mock_resp_ok])

        # Mock token refresh
        fresh_token_resp = mock_token_response(access_token="fresh-token")
        client._client.post = AsyncMock(return_value=fresh_token_resp)

        result = await client.list_pipelines()

        assert result == {"value": []}
        assert client._client.request.call_count == 2
        assert client._access_token == "fresh-token"


# ---------------------------------------------------------------------------
# 3. TestAdfApiClientPipelines — Pipeline operations (6 tests)
# ---------------------------------------------------------------------------


class TestAdfApiClientPipelines:
    """Tests for AdfApiClient pipeline CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_pipelines(self, adf_client, mock_response):
        """Test listing pipelines returns the value array from the response."""
        mock_resp = mock_response(
            json_data={
                "value": [
                    {"name": "etl-daily", "properties": {"type": "Pipeline"}},
                    {"name": "etl-weekly", "properties": {"type": "Pipeline"}},
                ],
            }
        )
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.list_pipelines()

        assert len(result["value"]) == 2
        assert result["value"][0]["name"] == "etl-daily"
        assert result["value"][1]["name"] == "etl-weekly"

    @pytest.mark.asyncio
    async def test_get_pipeline(self, adf_client, mock_response):
        """Test getting pipeline details by name includes activities and parameters."""
        mock_resp = mock_response(
            json_data={
                "name": "etl-daily",
                "properties": {
                    "activities": [{"name": "CopyData", "type": "Copy"}],
                    "parameters": {"env": {"type": "String"}},
                },
            }
        )
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.get_pipeline("etl-daily")

        assert result["name"] == "etl-daily"
        assert len(result["properties"]["activities"]) == 1
        # Verify the pipeline name appears in the URL
        call_args = adf_client._client.request.call_args
        assert "etl-daily" in call_args.kwargs["url"]

    @pytest.mark.asyncio
    async def test_get_pipeline_not_found(self, adf_client, mock_response):
        """Test that a 404 response raises AdfNotFoundError."""
        mock_resp = mock_response(status_code=404, text="Pipeline not found")
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(AdfNotFoundError):
            await adf_client.get_pipeline("nonexistent-pipeline")

    @pytest.mark.asyncio
    async def test_run_pipeline(self, adf_client, mock_response):
        """Test triggering a pipeline run returns a runId."""
        mock_resp = mock_response(json_data={"runId": "run-abc-123"})
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.run_pipeline("etl-daily")

        assert result["runId"] == "run-abc-123"
        call_args = adf_client._client.request.call_args
        assert call_args.kwargs["method"] == "POST"
        assert "createRun" in call_args.kwargs["url"]

    @pytest.mark.asyncio
    async def test_run_pipeline_with_params(self, adf_client, mock_response):
        """Test running a pipeline with parameters passes them as JSON body."""
        mock_resp = mock_response(json_data={"runId": "run-param-456"})
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        params = {"env": "production", "date": "2026-02-25"}
        result = await adf_client.run_pipeline("etl-daily", parameters=params)

        assert result["runId"] == "run-param-456"
        call_args = adf_client._client.request.call_args
        assert call_args.kwargs["json"] == params

    @pytest.mark.asyncio
    async def test_cancel_pipeline_run(self, adf_client, mock_response):
        """Test cancelling a pipeline run sends POST to cancel endpoint."""
        mock_resp = mock_response(status_code=204, json_data={}, content=b"")
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.cancel_pipeline_run("run-abc-123")

        assert result == {}
        call_args = adf_client._client.request.call_args
        assert "run-abc-123" in call_args.kwargs["url"]
        assert "cancel" in call_args.kwargs["url"]


# ---------------------------------------------------------------------------
# 4. TestAdfApiClientMonitoring — Monitoring operations (5 tests)
# ---------------------------------------------------------------------------


class TestAdfApiClientMonitoring:
    """Tests for AdfApiClient monitoring operations."""

    @pytest.mark.asyncio
    async def test_get_pipeline_run(self, adf_client, mock_response):
        """Test getting pipeline run details returns all expected fields."""
        mock_resp = mock_response(
            json_data={
                "runId": "run-abc-123",
                "pipelineName": "etl-daily",
                "status": "Succeeded",
                "runStart": "2026-02-24T10:00:00Z",
                "runEnd": "2026-02-24T10:05:00Z",
                "durationInMs": 300000,
            }
        )
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.get_pipeline_run("run-abc-123")

        assert result["runId"] == "run-abc-123"
        assert result["status"] == "Succeeded"
        assert result["pipelineName"] == "etl-daily"

    @pytest.mark.asyncio
    async def test_list_pipeline_runs(self, adf_client, mock_response):
        """Test querying pipeline runs with explicit time range filters."""
        mock_resp = mock_response(
            json_data={
                "value": [
                    {"runId": "run-1", "status": "Succeeded"},
                    {"runId": "run-2", "status": "Failed"},
                ],
            }
        )
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.list_pipeline_runs(
            last_updated_after="2026-02-23T00:00:00Z",
            last_updated_before="2026-02-24T00:00:00Z",
        )

        assert len(result["value"]) == 2
        assert result["value"][0]["status"] == "Succeeded"
        assert result["value"][1]["status"] == "Failed"
        call_args = adf_client._client.request.call_args
        assert call_args.kwargs["method"] == "POST"

    @pytest.mark.asyncio
    async def test_list_pipeline_runs_default_timerange(self, adf_client, mock_response):
        """Test that calling list_pipeline_runs with no filters uses default 24h range."""
        mock_resp = mock_response(json_data={"value": []})
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.list_pipeline_runs()

        assert result == {"value": []}
        call_args = adf_client._client.request.call_args
        json_body = call_args.kwargs["json"]
        # Default body should include lastUpdatedAfter and lastUpdatedBefore
        assert "lastUpdatedAfter" in json_body
        assert "lastUpdatedBefore" in json_body
        # Both values should end with "Z" (UTC ISO format)
        assert json_body["lastUpdatedAfter"].endswith("Z")
        assert json_body["lastUpdatedBefore"].endswith("Z")

    @pytest.mark.asyncio
    async def test_list_datasets(self, adf_client, mock_response):
        """Test listing datasets returns the value array."""
        mock_resp = mock_response(
            json_data={
                "value": [
                    {"name": "ds-input-csv", "properties": {"type": "AzureBlob"}},
                    {"name": "ds-output-sql", "properties": {"type": "AzureSqlTable"}},
                ],
            }
        )
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.list_datasets()

        assert len(result["value"]) == 2
        assert result["value"][0]["name"] == "ds-input-csv"

    @pytest.mark.asyncio
    async def test_list_triggers(self, adf_client, mock_response):
        """Test listing triggers returns the value array."""
        mock_resp = mock_response(
            json_data={
                "value": [
                    {"name": "daily-schedule", "properties": {"type": "ScheduleTrigger"}},
                ],
            }
        )
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.list_triggers()

        assert len(result["value"]) == 1
        assert result["value"][0]["name"] == "daily-schedule"


# ---------------------------------------------------------------------------
# 5. TestAdfApiClientResilience — Retry and error resilience (8 tests)
# ---------------------------------------------------------------------------


class TestAdfApiClientResilience:
    """Tests for AdfApiClient retry logic, error handling, and resilience."""

    def _make_retry_client(self, max_retries=3):
        """Helper to create a client configured for fast retries."""
        config = AdfConfig(
            subscription_id="sub-123",
            resource_group="rg-test",
            factory_name="adf-test",
            tenant_id="tenant-123",
            client_id="client-123",
            client_secret="secret-123",
            timeout=5,
            max_retries=max_retries,
            retry_base_delay=0.001,  # Very fast retries for testing
        )
        client = AdfApiClient(config)
        client._access_token = "test-token"
        client._token_expiry = time.time() + 3600
        return client

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, mock_response):
        """Test that httpx.ConnectError triggers retries up to max_retries."""
        client = self._make_retry_client(max_retries=3)
        client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(AdfConnectionError, match="Failed to connect"):
            await client.list_pipelines()

        assert client._client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, mock_response):
        """Test that httpx.TimeoutException triggers retries."""
        client = self._make_retry_client(max_retries=3)
        client._client.request = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        with pytest.raises(AdfConnectionError, match="Failed to connect"):
            await client.list_pipelines()

        assert client._client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, mock_response):
        """Test that after all retries are exhausted, AdfConnectionError is raised."""
        client = self._make_retry_client(max_retries=2)
        client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("Network unreachable")
        )

        with pytest.raises(AdfConnectionError, match="Failed to connect.*2 attempts"):
            await client.list_pipelines()

        assert client._client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        """Test that 429 response with Retry-After header triggers retry."""
        client = self._make_retry_client(max_retries=3)

        mock_resp_429 = MagicMock(spec=httpx.Response)
        mock_resp_429.status_code = 429
        mock_resp_429.headers = {"Retry-After": "0"}
        mock_resp_429.text = "Rate limited"
        mock_resp_429.content = b"Rate limited"

        client._client.request = AsyncMock(return_value=mock_resp_429)

        with pytest.raises(AdfRateLimitError, match="Rate limit exceeded"):
            await client.list_pipelines()

        # All 3 retries should have been attempted
        assert client._client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        """Test that 404 error raises AdfNotFoundError immediately without retry."""
        client = self._make_retry_client(max_retries=3)

        mock_resp_404 = MagicMock(spec=httpx.Response)
        mock_resp_404.status_code = 404
        mock_resp_404.text = "Not found"
        mock_resp_404.content = b"Not found"

        client._client.request = AsyncMock(return_value=mock_resp_404)

        with pytest.raises(AdfNotFoundError):
            await client.get_pipeline("nonexistent")

        # 404 should not be retried
        assert client._client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, mock_token_response):
        """Test that persistent auth failure raises AdfAuthenticationError without infinite retry."""
        client = self._make_retry_client(max_retries=2)

        mock_resp_401 = MagicMock(spec=httpx.Response)
        mock_resp_401.status_code = 401
        mock_resp_401.text = "Unauthorized"
        mock_resp_401.content = b"Unauthorized"

        # Both attempts return 401
        client._client.request = AsyncMock(return_value=mock_resp_401)
        # Token refresh succeeds but API keeps rejecting
        fresh_resp = mock_token_response(access_token="new-but-still-rejected")
        client._client.post = AsyncMock(return_value=fresh_resp)

        with pytest.raises(AdfAuthenticationError, match="Authentication failed"):
            await client.list_pipelines()

    @pytest.mark.asyncio
    async def test_health_check_success(self, adf_client, mock_response):
        """Test health_check returns True when list_pipelines succeeds."""
        mock_resp = mock_response(json_data={"value": []})
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.health_check()

        assert result is True
        assert adf_client.is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, adf_client):
        """Test health_check returns False on connection failure."""
        adf_client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = await adf_client.health_check()

        assert result is False
        assert adf_client.is_healthy is False


# ---------------------------------------------------------------------------
# 6. TestPipelineRunStatus — Enum coverage (2 tests)
# ---------------------------------------------------------------------------


class TestPipelineRunStatus:
    """Tests for PipelineRunStatus enum."""

    def test_status_enum_values(self):
        """Test that all PipelineRunStatus members have the expected string values."""
        assert PipelineRunStatus.QUEUED.value == "Queued"
        assert PipelineRunStatus.IN_PROGRESS.value == "InProgress"
        assert PipelineRunStatus.SUCCEEDED.value == "Succeeded"
        assert PipelineRunStatus.FAILED.value == "Failed"
        assert PipelineRunStatus.CANCELING.value == "Canceling"
        assert PipelineRunStatus.CANCELLED.value == "Cancelled"
        # Verify total count of members
        assert len(PipelineRunStatus) == 6

    def test_status_string_comparison(self):
        """Test that PipelineRunStatus members compare equal to their string values."""
        assert PipelineRunStatus.SUCCEEDED == "Succeeded"
        assert PipelineRunStatus.FAILED == "Failed"
        assert PipelineRunStatus.IN_PROGRESS == "InProgress"
        assert PipelineRunStatus.QUEUED == "Queued"
        assert PipelineRunStatus.CANCELING == "Canceling"
        assert PipelineRunStatus.CANCELLED == "Cancelled"
        # Negative case: should NOT equal wrong string
        assert PipelineRunStatus.SUCCEEDED != "Failed"
