"""Tests for AdfApiClient.

Tests cover:
    - AdfConfig creation and validation (from_env, base_url, defaults)
    - AdfApiClient initialization and token management
    - Pipeline CRUD operations (list, get, run, cancel)
    - Monitoring operations (pipeline runs, datasets, triggers)
    - Retry logic for connection errors, rate limits, and auth refresh
    - Error handling (authentication, not found, rate limit, connection)
    - Health check
    - Client lifecycle (close, context manager)
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
    """Create a test AdfConfig."""
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
    # Pre-populate token so _ensure_token is a no-op for most tests
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
# TestAdfConfig
# ---------------------------------------------------------------------------


class TestAdfConfig:
    """Tests for AdfConfig configuration."""

    def test_from_env_success(self, monkeypatch):
        """Test creating config from all required environment variables."""
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

    def test_from_env_missing_vars(self, monkeypatch):
        """Test that missing required env vars raises ValueError."""
        monkeypatch.delenv("ADF_SUBSCRIPTION_ID", raising=False)
        monkeypatch.delenv("ADF_RESOURCE_GROUP", raising=False)
        monkeypatch.delenv("ADF_FACTORY_NAME", raising=False)
        monkeypatch.delenv("ADF_TENANT_ID", raising=False)
        monkeypatch.delenv("ADF_CLIENT_ID", raising=False)
        monkeypatch.delenv("ADF_CLIENT_SECRET", raising=False)

        with pytest.raises(ValueError, match="Missing required environment variables"):
            AdfConfig.from_env()

    def test_base_url_construction(self, adf_config):
        """Test that base_url is properly constructed from config fields."""
        expected = (
            "https://management.azure.com/subscriptions/sub-123"
            "/resourceGroups/rg-test"
            "/providers/Microsoft.DataFactory/factories/adf-test"
        )
        assert adf_config.base_url == expected

    def test_default_values(self):
        """Test that optional fields use correct defaults."""
        config = AdfConfig(
            subscription_id="sub",
            resource_group="rg",
            factory_name="adf",
            tenant_id="tenant",
            client_id="client",
            client_secret="secret",
        )
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_base_delay == 1.0


# ---------------------------------------------------------------------------
# TestAdfApiClient
# ---------------------------------------------------------------------------


class TestAdfApiClient:
    """Tests for AdfApiClient initialization and token management."""

    def test_initialization(self, adf_config):
        """Test client initializes with correct state."""
        client = AdfApiClient(adf_config)

        assert client._config is adf_config
        assert client._access_token is None
        assert client._token_expiry == 0.0
        assert client._healthy is False
        assert isinstance(client._client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_ensure_token_success(self, adf_config, mock_token_response):
        """Test successful token acquisition from the token endpoint."""
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
        """Test that a valid cached token is returned without re-requesting."""
        # adf_client already has a token with expiry in the future
        adf_client._client.post = AsyncMock()

        token = await adf_client._ensure_token()

        assert token == "test-token-abc"
        adf_client._client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_token_failure(self, adf_config, mock_token_response):
        """Test that a non-200 from the token endpoint raises AdfAuthenticationError."""
        client = AdfApiClient(adf_config)
        mock_resp = mock_token_response(status_code=401)
        client._client.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(AdfAuthenticationError, match="Token acquisition failed"):
            await client._ensure_token()

    @pytest.mark.asyncio
    async def test_health_check(self, adf_client, mock_response):
        """Test health check returns True on success."""
        mock_resp = mock_response(json_data={"value": []})
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.health_check()

        assert result is True
        assert adf_client.is_healthy is True


# ---------------------------------------------------------------------------
# TestPipelineOperations
# ---------------------------------------------------------------------------


class TestPipelineOperations:
    """Tests for AdfApiClient pipeline CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_pipelines(self, adf_client, mock_response):
        """Test listing pipelines returns value array."""
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
        """Test getting pipeline details by name."""
        mock_resp = mock_response(
            json_data={
                "name": "etl-daily",
                "properties": {
                    "activities": [
                        {"name": "CopyData", "type": "Copy"},
                    ],
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
        """Test getting a non-existent pipeline raises AdfNotFoundError."""
        mock_resp = mock_response(status_code=404, text="Pipeline not found")
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(AdfNotFoundError):
            await adf_client.get_pipeline("nonexistent-pipeline")

    @pytest.mark.asyncio
    async def test_run_pipeline(self, adf_client, mock_response):
        """Test triggering a pipeline run returns a runId."""
        mock_resp = mock_response(
            json_data={"runId": "run-abc-123"},
        )
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.run_pipeline(
            "etl-daily", parameters={"env": "production"}
        )

        assert result["runId"] == "run-abc-123"

        # Verify POST method and createRun path
        call_args = adf_client._client.request.call_args
        assert call_args.kwargs["method"] == "POST"
        assert "createRun" in call_args.kwargs["url"]

    @pytest.mark.asyncio
    async def test_cancel_pipeline_run(self, adf_client, mock_response):
        """Test cancelling a pipeline run."""
        mock_resp = mock_response(status_code=204, json_data={}, content=b"")
        adf_client._client.request = AsyncMock(return_value=mock_resp)

        result = await adf_client.cancel_pipeline_run("run-abc-123")

        assert result == {}

        # Verify the run_id and cancel path
        call_args = adf_client._client.request.call_args
        assert "run-abc-123" in call_args.kwargs["url"]
        assert "cancel" in call_args.kwargs["url"]


# ---------------------------------------------------------------------------
# TestMonitoringOperations
# ---------------------------------------------------------------------------


class TestMonitoringOperations:
    """Tests for AdfApiClient monitoring operations."""

    @pytest.mark.asyncio
    async def test_get_pipeline_run(self, adf_client, mock_response):
        """Test getting pipeline run details."""
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
        """Test querying pipeline runs with time filters."""
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

        # Verify POST method for queryPipelineRuns
        call_args = adf_client._client.request.call_args
        assert call_args.kwargs["method"] == "POST"

    @pytest.mark.asyncio
    async def test_list_datasets(self, adf_client, mock_response):
        """Test listing datasets."""
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
        """Test listing triggers."""
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
# TestRetryLogic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Tests for AdfApiClient retry and error recovery logic."""

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, adf_config, mock_response):
        """Test that connection errors are retried before raising AdfConnectionError."""
        config = AdfConfig(
            subscription_id="sub-123",
            resource_group="rg-test",
            factory_name="adf-test",
            tenant_id="tenant-123",
            client_id="client-123",
            client_secret="secret-123",
            timeout=5,
            max_retries=3,
            retry_base_delay=0.01,  # Fast retries for testing
        )
        client = AdfApiClient(config)
        client._access_token = "test-token"
        client._token_expiry = time.time() + 3600

        client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(AdfConnectionError, match="Failed to connect"):
            await client.list_pipelines()

        # Should have retried max_retries times
        assert client._client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, adf_config, mock_response):
        """Test that 429 responses are retried before raising AdfRateLimitError."""
        config = AdfConfig(
            subscription_id="sub-123",
            resource_group="rg-test",
            factory_name="adf-test",
            tenant_id="tenant-123",
            client_id="client-123",
            client_secret="secret-123",
            timeout=5,
            max_retries=3,
            retry_base_delay=0.01,
        )
        client = AdfApiClient(config)
        client._access_token = "test-token"
        client._token_expiry = time.time() + 3600

        mock_resp_429 = mock_response(
            status_code=429,
            headers={"Retry-After": "0"},
        )
        client._client.request = AsyncMock(return_value=mock_resp_429)

        with pytest.raises(AdfRateLimitError, match="Rate limit exceeded"):
            await client.list_pipelines()

        # Should have retried max_retries times
        assert client._client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_auth_refresh_on_401(self, adf_config, mock_response, mock_token_response):
        """Test that 401 triggers token refresh before retrying."""
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
        # First call got 401, token refreshed, second call succeeded
        assert client._client.request.call_count == 2
        # Token should have been refreshed
        assert client._access_token == "fresh-token"


# ---------------------------------------------------------------------------
# TestLifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Tests for AdfApiClient lifecycle management."""

    @pytest.mark.asyncio
    async def test_close(self, adf_client):
        """Test that close releases resources and clears state."""
        adf_client._client.aclose = AsyncMock()
        adf_client._healthy = True

        await adf_client.close()

        adf_client._client.aclose.assert_called_once()
        assert adf_client.is_healthy is False
        assert adf_client._access_token is None

    @pytest.mark.asyncio
    async def test_context_manager(self, adf_config):
        """Test async context manager entry and exit."""
        async with AdfApiClient(adf_config) as client:
            assert isinstance(client, AdfApiClient)
            assert client._config is adf_config

        # After exiting, access_token should be cleared (close was called)
        assert client._access_token is None
        assert client.is_healthy is False


# ---------------------------------------------------------------------------
# TestPipelineRunStatus (bonus enum coverage)
# ---------------------------------------------------------------------------


class TestPipelineRunStatus:
    """Tests for PipelineRunStatus enum."""

    def test_status_values(self):
        """Test that PipelineRunStatus has the expected values."""
        assert PipelineRunStatus.QUEUED == "Queued"
        assert PipelineRunStatus.IN_PROGRESS == "InProgress"
        assert PipelineRunStatus.SUCCEEDED == "Succeeded"
        assert PipelineRunStatus.FAILED == "Failed"
        assert PipelineRunStatus.CANCELING == "Canceling"
        assert PipelineRunStatus.CANCELLED == "Cancelled"


# ---------------------------------------------------------------------------
# TestHealthCheckFailure (additional edge case)
# ---------------------------------------------------------------------------


class TestHealthCheckFailure:
    """Tests for AdfApiClient health check failure path."""

    @pytest.mark.asyncio
    async def test_health_check_failure(self, adf_client):
        """Test health check returns False on connection failure."""
        adf_client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = await adf_client.health_check()

        assert result is False
        assert adf_client.is_healthy is False
