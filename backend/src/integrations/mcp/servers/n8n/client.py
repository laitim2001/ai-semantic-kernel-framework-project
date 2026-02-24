"""n8n REST API Client.

Provides a typed wrapper around the n8n REST API v1 for workflow
and execution management.

Features:
    - API Key authentication via X-N8N-API-KEY header
    - Automatic retry with exponential backoff
    - Connection health checking
    - Async HTTP via httpx.AsyncClient
    - Structured error handling

Environment Variables:
    N8N_BASE_URL: Base URL for n8n instance (default: http://localhost:5678)
    N8N_API_KEY: n8n API key for authentication (required)
    N8N_TIMEOUT: Request timeout in seconds (default: 30)
    N8N_MAX_RETRIES: Maximum retry attempts (default: 3)

Reference:
    - n8n API docs: https://docs.n8n.io/api/
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class N8nApiError(Exception):
    """Base exception for n8n API errors.

    Attributes:
        status_code: HTTP status code from n8n API
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


class N8nConnectionError(N8nApiError):
    """Raised when connection to n8n fails."""


class N8nAuthenticationError(N8nApiError):
    """Raised when authentication to n8n fails (401/403)."""


class N8nNotFoundError(N8nApiError):
    """Raised when a resource is not found in n8n (404)."""


class N8nRateLimitError(N8nApiError):
    """Raised when n8n rate limit is hit (429)."""


class WorkflowStatus(str, Enum):
    """n8n workflow status."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class ExecutionStatus(str, Enum):
    """n8n execution status."""

    NEW = "new"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    WAITING = "waiting"


@dataclass
class N8nConfig:
    """n8n connection configuration.

    Attributes:
        base_url: n8n instance base URL
        api_key: API key for authentication
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_base_delay: Base delay for exponential backoff (seconds)

    Example:
        >>> config = N8nConfig.from_env()
        >>> print(config.base_url)
        'http://localhost:5678'
    """

    base_url: str
    api_key: str
    timeout: int = 30
    max_retries: int = 3
    retry_base_delay: float = 1.0

    @classmethod
    def from_env(cls) -> "N8nConfig":
        """Create configuration from environment variables.

        Environment Variables:
            N8N_BASE_URL: Base URL (default: http://localhost:5678)
            N8N_API_KEY: API key (required)
            N8N_TIMEOUT: Timeout in seconds (default: 30)
            N8N_MAX_RETRIES: Max retries (default: 3)

        Returns:
            N8nConfig instance

        Raises:
            ValueError: If N8N_API_KEY is not set
        """
        api_key = os.environ.get("N8N_API_KEY", "")
        if not api_key:
            raise ValueError("N8N_API_KEY environment variable is required")

        return cls(
            base_url=os.environ.get("N8N_BASE_URL", "http://localhost:5678").rstrip("/"),
            api_key=api_key,
            timeout=int(os.environ.get("N8N_TIMEOUT", "30")),
            max_retries=int(os.environ.get("N8N_MAX_RETRIES", "3")),
        )


class N8nApiClient:
    """n8n REST API client.

    Provides async methods for interacting with the n8n v1 API.
    Uses httpx.AsyncClient for HTTP communication with automatic
    retry logic and structured error handling.

    Example:
        >>> config = N8nConfig(base_url="http://localhost:5678", api_key="xxx")
        >>> client = N8nApiClient(config)
        >>> workflows = await client.list_workflows()
        >>> execution = await client.execute_workflow("workflow-id", {"key": "value"})
        >>> await client.close()

    Context Manager:
        >>> async with N8nApiClient(config) as client:
        ...     workflows = await client.list_workflows()
    """

    # n8n API v1 base path
    API_BASE = "/api/v1"

    def __init__(self, config: N8nConfig):
        """Initialize the n8n API client.

        Args:
            config: n8n connection configuration
        """
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout),
            headers={
                "X-N8N-API-KEY": config.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        self._healthy = False
        logger.info(
            f"N8nApiClient initialized: {config.base_url}"
        )

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
        """Execute an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            path: API path (appended to API_BASE)
            params: Query parameters
            json_data: JSON request body

        Returns:
            Parsed JSON response

        Raises:
            N8nConnectionError: On connection failure after retries
            N8nAuthenticationError: On 401/403
            N8nNotFoundError: On 404
            N8nRateLimitError: On 429
            N8nApiError: On other HTTP errors
        """
        url = f"{self.API_BASE}{path}"
        last_error: Optional[Exception] = None

        for attempt in range(self._config.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                )

                # Handle error status codes
                if response.status_code == 401 or response.status_code == 403:
                    raise N8nAuthenticationError(
                        f"Authentication failed: {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                if response.status_code == 404:
                    raise N8nNotFoundError(
                        f"Resource not found: {path}",
                        status_code=404,
                        response_body=response.text,
                    )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    if attempt < self._config.max_retries - 1:
                        logger.warning(
                            f"Rate limited, retrying after {retry_after}s "
                            f"(attempt {attempt + 1}/{self._config.max_retries})"
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    raise N8nRateLimitError(
                        "Rate limit exceeded after retries",
                        status_code=429,
                    )

                if response.status_code >= 400:
                    raise N8nApiError(
                        f"API error: {response.status_code} {response.text}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # Parse response
                if response.status_code == 204:
                    return {}

                return response.json()

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self._config.max_retries - 1:
                    delay = self._config.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"Connection error: {e}, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{self._config.max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise N8nConnectionError(
                        f"Failed to connect to n8n after {self._config.max_retries} attempts: {e}"
                    ) from e
            except (N8nAuthenticationError, N8nNotFoundError):
                # Don't retry auth or not-found errors
                raise

        raise N8nConnectionError(
            f"Failed after {self._config.max_retries} attempts: {last_error}"
        )

    # -------------------------------------------------------------------------
    # Health check
    # -------------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Check n8n instance health.

        Performs a lightweight API call to verify connectivity.

        Returns:
            True if n8n is reachable and responding
        """
        try:
            # Use a simple endpoint to verify connectivity
            await self._request("GET", "/workflows", params={"limit": 1})
            self._healthy = True
            return True
        except Exception as e:
            logger.warning(f"n8n health check failed: {e}")
            self._healthy = False
            return False

    @property
    def is_healthy(self) -> bool:
        """Get the last known health status."""
        return self._healthy

    # -------------------------------------------------------------------------
    # Workflow operations
    # -------------------------------------------------------------------------

    async def list_workflows(
        self,
        active: Optional[bool] = None,
        tags: Optional[str] = None,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all workflows.

        Args:
            active: Filter by active status
            tags: Filter by tag name
            limit: Maximum number of workflows to return
            cursor: Pagination cursor

        Returns:
            Dict with 'data' (list of workflows) and 'nextCursor'

        Example:
            >>> result = await client.list_workflows(active=True, limit=10)
            >>> for wf in result["data"]:
            ...     print(f"{wf['id']}: {wf['name']}")
        """
        params: Dict[str, Any] = {"limit": limit}
        if active is not None:
            params["active"] = str(active).lower()
        if tags:
            params["tags"] = tags
        if cursor:
            params["cursor"] = cursor

        return await self._request("GET", "/workflows", params=params)

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow details.

        Args:
            workflow_id: n8n workflow ID

        Returns:
            Workflow object with nodes, connections, and settings

        Raises:
            N8nNotFoundError: If workflow does not exist
        """
        return await self._request("GET", f"/workflows/{workflow_id}")

    async def activate_workflow(
        self, workflow_id: str, active: bool
    ) -> Dict[str, Any]:
        """Activate or deactivate a workflow.

        Args:
            workflow_id: n8n workflow ID
            active: True to activate, False to deactivate

        Returns:
            Updated workflow object

        Raises:
            N8nNotFoundError: If workflow does not exist
        """
        return await self._request(
            "PATCH",
            f"/workflows/{workflow_id}",
            json_data={"active": active},
        )

    # -------------------------------------------------------------------------
    # Execution operations
    # -------------------------------------------------------------------------

    async def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Trigger a workflow execution.

        Executes a workflow with optional input data. The workflow must be
        saved (but does not need to be active) for direct execution.

        Args:
            workflow_id: n8n workflow ID to execute
            data: Input data to pass to the workflow

        Returns:
            Execution result object

        Raises:
            N8nNotFoundError: If workflow does not exist

        Example:
            >>> result = await client.execute_workflow(
            ...     "wf-123",
            ...     data={"user": "admin", "action": "reset_password"}
            ... )
            >>> print(result["data"]["executionId"])
        """
        json_body: Dict[str, Any] = {}
        if data:
            json_body = data

        return await self._request(
            "POST",
            f"/workflows/{workflow_id}/execute",
            json_data=json_body,
        )

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get execution details.

        Args:
            execution_id: n8n execution ID

        Returns:
            Execution object with status, data, and timing information

        Raises:
            N8nNotFoundError: If execution does not exist
        """
        return await self._request("GET", f"/executions/{execution_id}")

    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List executions with filtering.

        Args:
            workflow_id: Filter by workflow ID
            status: Filter by execution status (success, error, waiting)
            limit: Maximum number of executions to return
            cursor: Pagination cursor

        Returns:
            Dict with 'data' (list of executions) and 'nextCursor'

        Example:
            >>> result = await client.list_executions(
            ...     workflow_id="wf-123",
            ...     status="error",
            ...     limit=5,
            ... )
        """
        params: Dict[str, Any] = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor

        return await self._request("GET", "/executions", params=params)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()
        self._healthy = False
        logger.info("N8nApiClient closed")

    async def __aenter__(self) -> "N8nApiClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
