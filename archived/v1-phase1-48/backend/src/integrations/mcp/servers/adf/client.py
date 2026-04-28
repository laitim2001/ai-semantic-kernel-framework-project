"""Azure Data Factory REST API Client.

Provides a typed wrapper around the Azure Data Factory REST API for
pipeline management, execution triggering, and monitoring.

Features:
    - Service Principal authentication (client_id + client_secret + tenant_id)
    - Automatic token refresh with caching
    - Retry with exponential backoff
    - Async HTTP via httpx.AsyncClient
    - Structured error handling

Environment Variables:
    ADF_SUBSCRIPTION_ID: Azure subscription ID (required)
    ADF_RESOURCE_GROUP: Azure resource group name (required)
    ADF_FACTORY_NAME: Data Factory name (required)
    ADF_TENANT_ID: Azure AD tenant ID (required)
    ADF_CLIENT_ID: Service Principal client ID (required)
    ADF_CLIENT_SECRET: Service Principal client secret (required)
    ADF_TIMEOUT: Request timeout in seconds (default: 30)
    ADF_MAX_RETRIES: Maximum retry attempts (default: 3)

Reference:
    - ADF REST API: https://learn.microsoft.com/en-us/rest/api/datafactory/
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AdfApiError(Exception):
    """Base exception for ADF API errors.

    Attributes:
        status_code: HTTP status code from ADF API
        message: Error message
        response_body: Raw response body if available
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AdfConnectionError(AdfApiError):
    """Raised when connection to ADF API fails."""


class AdfAuthenticationError(AdfApiError):
    """Raised when authentication fails (401/403)."""


class AdfNotFoundError(AdfApiError):
    """Raised when a resource is not found (404)."""


class AdfRateLimitError(AdfApiError):
    """Raised when rate limit is hit (429)."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PipelineRunStatus(str, Enum):
    """ADF pipeline run status."""

    QUEUED = "Queued"
    IN_PROGRESS = "InProgress"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELING = "Canceling"
    CANCELLED = "Cancelled"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class AdfConfig:
    """Azure Data Factory connection configuration.

    Attributes:
        subscription_id: Azure subscription ID
        resource_group: Azure resource group name
        factory_name: Data Factory name
        tenant_id: Azure AD tenant ID
        client_id: Service Principal client ID
        client_secret: Service Principal client secret
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        retry_base_delay: Base delay for exponential backoff (seconds)
    """

    subscription_id: str
    resource_group: str
    factory_name: str
    tenant_id: str
    client_id: str
    client_secret: str
    timeout: int = 30
    max_retries: int = 3
    retry_base_delay: float = 1.0

    @classmethod
    def from_env(cls) -> "AdfConfig":
        """Create configuration from environment variables.

        Returns:
            AdfConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """
        required_vars = [
            "ADF_SUBSCRIPTION_ID",
            "ADF_RESOURCE_GROUP",
            "ADF_FACTORY_NAME",
            "ADF_TENANT_ID",
            "ADF_CLIENT_ID",
            "ADF_CLIENT_SECRET",
        ]

        missing = [v for v in required_vars if not os.environ.get(v)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            subscription_id=os.environ["ADF_SUBSCRIPTION_ID"],
            resource_group=os.environ["ADF_RESOURCE_GROUP"],
            factory_name=os.environ["ADF_FACTORY_NAME"],
            tenant_id=os.environ["ADF_TENANT_ID"],
            client_id=os.environ["ADF_CLIENT_ID"],
            client_secret=os.environ["ADF_CLIENT_SECRET"],
            timeout=int(os.environ.get("ADF_TIMEOUT", "30")),
            max_retries=int(os.environ.get("ADF_MAX_RETRIES", "3")),
        )

    @property
    def base_url(self) -> str:
        """Get the ADF REST API base URL."""
        return (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.DataFactory/factories/{self.factory_name}"
        )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AdfApiClient:
    """Azure Data Factory REST API client.

    Provides async methods for interacting with the ADF REST API.
    Handles Service Principal authentication with automatic token refresh.

    Example:
        >>> config = AdfConfig.from_env()
        >>> client = AdfApiClient(config)
        >>> pipelines = await client.list_pipelines()
        >>> run = await client.run_pipeline("my-pipeline", {"param1": "value1"})
        >>> await client.close()

    Context Manager:
        >>> async with AdfApiClient(config) as client:
        ...     pipelines = await client.list_pipelines()
    """

    API_VERSION = "2018-06-01"
    TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    TOKEN_SCOPE = "https://management.azure.com/.default"

    def __init__(self, config: AdfConfig):
        """Initialize the ADF API client.

        Args:
            config: ADF connection configuration
        """
        self._config = config
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._healthy = False

        logger.info(
            f"AdfApiClient initialized: factory={config.factory_name}, "
            f"resource_group={config.resource_group}"
        )

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    async def _ensure_token(self) -> str:
        """Ensure we have a valid access token.

        Requests a new token if the current one is expired or missing.
        Token is cached with a 5-minute buffer before expiry.

        Returns:
            Valid access token string

        Raises:
            AdfAuthenticationError: If token acquisition fails
        """
        # Use cached token if still valid (with 5 min buffer)
        if self._access_token and time.time() < (self._token_expiry - 300):
            return self._access_token

        token_url = self.TOKEN_URL_TEMPLATE.format(tenant_id=self._config.tenant_id)

        try:
            response = await self._client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                    "scope": self.TOKEN_SCOPE,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise AdfAuthenticationError(
                    f"Token acquisition failed: {response.status_code} {response.text}",
                    status_code=response.status_code,
                )

            token_data = response.json()
            self._access_token = token_data["access_token"]
            self._token_expiry = time.time() + token_data.get("expires_in", 3600)

            logger.debug("ADF access token acquired/refreshed")
            return self._access_token

        except httpx.HTTPError as e:
            raise AdfAuthenticationError(
                f"Token acquisition failed: {e}"
            ) from e

    # -------------------------------------------------------------------------
    # HTTP helpers
    # -------------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute an authenticated HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (appended to base_url)
            params: Query parameters (api-version auto-added)
            json_data: JSON request body

        Returns:
            Parsed JSON response

        Raises:
            AdfConnectionError: On connection failure after retries
            AdfAuthenticationError: On 401/403
            AdfNotFoundError: On 404
            AdfRateLimitError: On 429
            AdfApiError: On other HTTP errors
        """
        token = await self._ensure_token()
        url = f"{self._config.base_url}{path}"

        request_params = {"api-version": self.API_VERSION}
        if params:
            request_params.update(params)

        last_error: Optional[Exception] = None

        for attempt in range(self._config.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=request_params,
                    json=json_data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )

                # Handle error codes
                if response.status_code in (401, 403):
                    # Token might be stale, try refreshing once
                    if attempt == 0:
                        self._access_token = None
                        token = await self._ensure_token()
                        continue
                    raise AdfAuthenticationError(
                        f"Authentication failed: {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                if response.status_code == 404:
                    raise AdfNotFoundError(
                        f"Resource not found: {path}",
                        status_code=404,
                        response_body=response.text,
                    )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "10"))
                    if attempt < self._config.max_retries - 1:
                        logger.warning(
                            f"ADF rate limited, retrying after {retry_after}s "
                            f"(attempt {attempt + 1}/{self._config.max_retries})"
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    raise AdfRateLimitError(
                        "Rate limit exceeded after retries",
                        status_code=429,
                    )

                if response.status_code >= 400:
                    raise AdfApiError(
                        f"ADF API error: {response.status_code} {response.text}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # Parse response
                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self._config.max_retries - 1:
                    delay = self._config.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"ADF connection error: {e}, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{self._config.max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise AdfConnectionError(
                        f"Failed to connect to ADF after "
                        f"{self._config.max_retries} attempts: {e}"
                    ) from e
            except (AdfAuthenticationError, AdfNotFoundError):
                raise

        raise AdfConnectionError(
            f"Failed after {self._config.max_retries} attempts: {last_error}"
        )

    # -------------------------------------------------------------------------
    # Health check
    # -------------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Check ADF connectivity.

        Performs a lightweight API call to verify connectivity.

        Returns:
            True if ADF is reachable and responding
        """
        try:
            await self._request("GET", "/pipelines", params={"$top": "1"})
            self._healthy = True
            return True
        except Exception as e:
            logger.warning(f"ADF health check failed: {e}")
            self._healthy = False
            return False

    @property
    def is_healthy(self) -> bool:
        """Get the last known health status."""
        return self._healthy

    # -------------------------------------------------------------------------
    # Pipeline operations
    # -------------------------------------------------------------------------

    async def list_pipelines(self) -> Dict[str, Any]:
        """List all pipelines in the data factory.

        Returns:
            Dict with 'value' (list of pipelines)
        """
        return await self._request("GET", "/pipelines")

    async def get_pipeline(self, pipeline_name: str) -> Dict[str, Any]:
        """Get pipeline details.

        Args:
            pipeline_name: ADF pipeline name

        Returns:
            Pipeline definition object

        Raises:
            AdfNotFoundError: If pipeline does not exist
        """
        return await self._request("GET", f"/pipelines/{pipeline_name}")

    async def run_pipeline(
        self,
        pipeline_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Trigger a pipeline run.

        Args:
            pipeline_name: ADF pipeline name
            parameters: Pipeline parameters

        Returns:
            Dict with 'runId' for the created pipeline run

        Raises:
            AdfNotFoundError: If pipeline does not exist
        """
        return await self._request(
            "POST",
            f"/pipelines/{pipeline_name}/createRun",
            json_data=parameters or {},
        )

    async def cancel_pipeline_run(self, run_id: str) -> Dict[str, Any]:
        """Cancel a pipeline run.

        Args:
            run_id: Pipeline run ID

        Returns:
            Empty dict on success

        Raises:
            AdfNotFoundError: If run does not exist
        """
        return await self._request(
            "POST",
            f"/pipelineruns/{run_id}/cancel",
        )

    # -------------------------------------------------------------------------
    # Pipeline run monitoring
    # -------------------------------------------------------------------------

    async def get_pipeline_run(self, run_id: str) -> Dict[str, Any]:
        """Get pipeline run details.

        Args:
            run_id: Pipeline run ID

        Returns:
            Pipeline run object with status, timing, and parameters

        Raises:
            AdfNotFoundError: If run does not exist
        """
        return await self._request("GET", f"/pipelineruns/{run_id}")

    async def list_pipeline_runs(
        self,
        last_updated_after: Optional[str] = None,
        last_updated_before: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Query pipeline runs.

        Args:
            last_updated_after: ISO 8601 datetime filter (start)
            last_updated_before: ISO 8601 datetime filter (end)
            filters: Additional filter conditions

        Returns:
            Dict with 'value' (list of pipeline runs)
        """
        body: Dict[str, Any] = {}
        if last_updated_after:
            body["lastUpdatedAfter"] = last_updated_after
        if last_updated_before:
            body["lastUpdatedBefore"] = last_updated_before
        if filters:
            body["filters"] = filters

        # Default: last 24 hours
        if not body:
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            body = {
                "lastUpdatedAfter": (now - timedelta(days=1)).isoformat() + "Z",
                "lastUpdatedBefore": now.isoformat() + "Z",
            }

        return await self._request(
            "POST",
            "/queryPipelineRuns",
            json_data=body,
        )

    # -------------------------------------------------------------------------
    # Dataset and trigger operations
    # -------------------------------------------------------------------------

    async def list_datasets(self) -> Dict[str, Any]:
        """List all datasets in the data factory.

        Returns:
            Dict with 'value' (list of datasets)
        """
        return await self._request("GET", "/datasets")

    async def list_triggers(self) -> Dict[str, Any]:
        """List all triggers in the data factory.

        Returns:
            Dict with 'value' (list of triggers)
        """
        return await self._request("GET", "/triggers")

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()
        self._healthy = False
        self._access_token = None
        logger.info("AdfApiClient closed")

    async def __aenter__(self) -> "AdfApiClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
