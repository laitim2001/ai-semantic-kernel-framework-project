"""ServiceNow Table API async client.

Provides async methods for ServiceNow Incident, RITM, Work Notes,
and Attachment operations via the Table API. Includes exponential
backoff retry for transient errors and comprehensive error handling.

Sprint 117 — ServiceNow MCP Server
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .servicenow_config import AuthMethod, ServiceNowConfig

logger = logging.getLogger(__name__)

try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


class ServiceNowError(Exception):
    """Base exception for ServiceNow API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_detail: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_detail = error_detail


class ServiceNowAuthError(ServiceNowError):
    """Authentication failure (401)."""

    pass


class ServiceNowPermissionError(ServiceNowError):
    """Permission denied (403)."""

    pass


class ServiceNowNotFoundError(ServiceNowError):
    """Record not found (404)."""

    pass


class ServiceNowServerError(ServiceNowError):
    """Server error (5xx)."""

    pass


class ServiceNowClient:
    """Async client for ServiceNow Table API.

    Wraps httpx.AsyncClient with authentication, retry logic,
    and structured error handling for ServiceNow REST API operations.

    Example:
        >>> config = ServiceNowConfig.from_env()
        >>> client = ServiceNowClient(config)
        >>> async with client:
        ...     incident = await client.create_incident(
        ...         short_description="Server down",
        ...         description="Web server is not responding",
        ...     )
        ...     print(incident["number"])
    """

    def __init__(self, config: ServiceNowConfig) -> None:
        if not _HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for ServiceNow client. "
                "Install with: pip install httpx"
            )

        self._config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create httpx client."""
        if self._client is None or self._client.is_closed:
            kwargs: Dict[str, Any] = {
                "timeout": httpx.Timeout(self._config.timeout),
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            }

            if self._config.auth_method == AuthMethod.BASIC:
                auth_tuple = self._config.auth_tuple
                if auth_tuple:
                    kwargs["auth"] = auth_tuple
            elif self._config.auth_method == AuthMethod.OAUTH2:
                kwargs["headers"].update(self._config.auth_headers)

            self._client = httpx.AsyncClient(**kwargs)

        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ServiceNowClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # =========================================================================
    # Internal HTTP helpers
    # =========================================================================

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        content: Optional[bytes] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute HTTP request with retry and error handling.

        Retries on HTTP 429 (rate limit) and 5xx (server errors)
        with exponential backoff.
        """
        client = await self._ensure_client()
        last_error: Optional[Exception] = None

        for attempt in range(self._config.max_retries + 1):
            try:
                kwargs: Dict[str, Any] = {"url": url}
                if json_data is not None:
                    kwargs["json"] = json_data
                if params is not None:
                    kwargs["params"] = params
                if content is not None:
                    kwargs["content"] = content
                if extra_headers:
                    kwargs["headers"] = extra_headers

                response = await client.request(method, **kwargs)
                self._check_response(response)

                if response.status_code == 204:
                    return {"success": True}

                return response.json()

            except (ServiceNowAuthError, ServiceNowPermissionError, ServiceNowNotFoundError):
                raise

            except ServiceNowServerError as e:
                last_error = e
                if attempt < self._config.max_retries:
                    delay = self._config.retry_base_delay * (2**attempt)
                    logger.warning(
                        "ServiceNow server error (attempt %d/%d), "
                        "retrying in %.1fs: %s",
                        attempt + 1,
                        self._config.max_retries + 1,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429 and attempt < self._config.max_retries:
                    retry_after = e.response.headers.get("Retry-After", "")
                    delay = (
                        float(retry_after)
                        if retry_after.replace(".", "", 1).isdigit()
                        else self._config.retry_base_delay * (2**attempt)
                    )
                    logger.warning(
                        "ServiceNow rate limited (attempt %d/%d), "
                        "retrying in %.1fs",
                        attempt + 1,
                        self._config.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise ServiceNowError(
                    f"HTTP {status}: {str(e)}",
                    status_code=status,
                )

            except httpx.ConnectError as e:
                last_error = e
                if attempt < self._config.max_retries:
                    delay = self._config.retry_base_delay * (2**attempt)
                    logger.warning(
                        "ServiceNow connection error (attempt %d/%d), "
                        "retrying in %.1fs: %s",
                        attempt + 1,
                        self._config.max_retries + 1,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise ServiceNowError(
                    f"Connection failed after {self._config.max_retries + 1} attempts: {e}"
                )

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self._config.max_retries:
                    delay = self._config.retry_base_delay * (2**attempt)
                    logger.warning(
                        "ServiceNow timeout (attempt %d/%d), "
                        "retrying in %.1fs",
                        attempt + 1,
                        self._config.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise ServiceNowError(
                    f"Request timed out after {self._config.max_retries + 1} attempts: {e}"
                )

        raise ServiceNowError(
            f"Request failed after {self._config.max_retries + 1} attempts: {last_error}"
        )

    def _check_response(self, response: "httpx.Response") -> None:
        """Check response status and raise appropriate exceptions."""
        status = response.status_code
        if 200 <= status < 300:
            return

        try:
            body = response.json()
            error_msg = body.get("error", {}).get("message", response.text)
        except Exception:
            error_msg = response.text

        if status == 401:
            raise ServiceNowAuthError(
                f"Authentication failed: {error_msg}",
                status_code=401,
                error_detail=error_msg,
            )
        elif status == 403:
            raise ServiceNowPermissionError(
                f"Permission denied: {error_msg}",
                status_code=403,
                error_detail=error_msg,
            )
        elif status == 404:
            raise ServiceNowNotFoundError(
                f"Record not found: {error_msg}",
                status_code=404,
                error_detail=error_msg,
            )
        elif status >= 500:
            raise ServiceNowServerError(
                f"Server error ({status}): {error_msg}",
                status_code=status,
                error_detail=error_msg,
            )
        else:
            response.raise_for_status()

    # =========================================================================
    # Incident Operations
    # =========================================================================

    async def create_incident(
        self,
        short_description: str,
        description: str,
        category: str = "inquiry",
        urgency: str = "3",
        assignment_group: Optional[str] = None,
        caller_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new ServiceNow Incident.

        Args:
            short_description: Brief incident summary.
            description: Detailed incident description.
            category: Incident category (default: inquiry).
            urgency: Urgency level 1-3 (default: 3 = low).
            assignment_group: sys_id of assignment group.
            caller_id: sys_id of caller.

        Returns:
            Created incident record from ServiceNow API.
        """
        url = f"{self._config.base_url}/table/incident"
        payload: Dict[str, Any] = {
            "short_description": short_description,
            "description": description,
            "category": category,
            "urgency": urgency,
        }
        if assignment_group:
            payload["assignment_group"] = assignment_group
        if caller_id:
            payload["caller_id"] = caller_id

        logger.info("Creating incident: %s", short_description[:80])
        response = await self._request("POST", url, json_data=payload)
        result = response.get("result", response)
        logger.info("Incident created: %s", result.get("number", "unknown"))
        return result

    async def update_incident(
        self,
        sys_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing ServiceNow Incident.

        Args:
            sys_id: Incident sys_id.
            updates: Dictionary of field names and new values.

        Returns:
            Updated incident record.
        """
        url = f"{self._config.base_url}/table/incident/{sys_id}"
        logger.info("Updating incident %s: %s", sys_id, list(updates.keys()))
        response = await self._request("PATCH", url, json_data=updates)
        return response.get("result", response)

    async def get_incident(
        self,
        number: Optional[str] = None,
        sys_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Query a ServiceNow Incident by number or sys_id.

        Args:
            number: Incident number (e.g., INC0010001).
            sys_id: Incident sys_id.

        Returns:
            Incident record if found, None otherwise.
        """
        if sys_id:
            url = f"{self._config.base_url}/table/incident/{sys_id}"
            try:
                response = await self._request("GET", url)
                return response.get("result", response)
            except ServiceNowNotFoundError:
                return None
        elif number:
            url = f"{self._config.base_url}/table/incident"
            params = {
                "sysparm_query": f"number={number}",
                "sysparm_limit": "1",
            }
            response = await self._request("GET", url, params=params)
            results = response.get("result", [])
            return results[0] if results else None
        else:
            raise ValueError("Either number or sys_id must be provided")

    # =========================================================================
    # RITM Operations
    # =========================================================================

    async def create_ritm(
        self,
        cat_item: str,
        variables: Dict[str, Any],
        requested_for: str,
        short_description: str,
    ) -> Dict[str, Any]:
        """Create a ServiceNow Requested Item (RITM).

        Args:
            cat_item: Catalog item sys_id.
            variables: Catalog item variable values.
            requested_for: sys_id of the person the item is for.
            short_description: Brief description of the request.

        Returns:
            Created RITM record.
        """
        url = f"{self._config.base_url}/table/sc_req_item"
        payload: Dict[str, Any] = {
            "cat_item": cat_item,
            "requested_for": requested_for,
            "short_description": short_description,
            "variables": variables,
        }

        logger.info("Creating RITM: %s", short_description[:80])
        response = await self._request("POST", url, json_data=payload)
        result = response.get("result", response)
        logger.info("RITM created: %s", result.get("number", "unknown"))
        return result

    async def get_ritm_status(
        self,
        number: Optional[str] = None,
        sys_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Query a ServiceNow RITM status.

        Args:
            number: RITM number (e.g., RITM0010001).
            sys_id: RITM sys_id.

        Returns:
            RITM record if found, None otherwise.
        """
        if sys_id:
            url = f"{self._config.base_url}/table/sc_req_item/{sys_id}"
            try:
                response = await self._request("GET", url)
                return response.get("result", response)
            except ServiceNowNotFoundError:
                return None
        elif number:
            url = f"{self._config.base_url}/table/sc_req_item"
            params = {
                "sysparm_query": f"number={number}",
                "sysparm_limit": "1",
            }
            response = await self._request("GET", url, params=params)
            results = response.get("result", [])
            return results[0] if results else None
        else:
            raise ValueError("Either number or sys_id must be provided")

    # =========================================================================
    # Work Notes and Attachment Operations
    # =========================================================================

    async def add_work_notes(
        self,
        table: str,
        sys_id: str,
        work_notes: str,
    ) -> Dict[str, Any]:
        """Add work notes to a ServiceNow record.

        Args:
            table: Table name (e.g., incident, sc_req_item).
            sys_id: Record sys_id.
            work_notes: Work notes text.

        Returns:
            Updated record.
        """
        url = f"{self._config.base_url}/table/{table}/{sys_id}"
        payload = {"work_notes": work_notes}
        logger.info("Adding work notes to %s/%s", table, sys_id)
        response = await self._request("PATCH", url, json_data=payload)
        return response.get("result", response)

    async def add_attachment(
        self,
        table: str,
        sys_id: str,
        file_name: str,
        content: bytes,
        content_type: str = "text/plain",
    ) -> Dict[str, Any]:
        """Add an attachment to a ServiceNow record.

        Args:
            table: Table name (e.g., incident, sc_req_item).
            sys_id: Record sys_id.
            file_name: Attachment file name.
            content: File content as bytes.
            content_type: MIME type (default: text/plain).

        Returns:
            Attachment metadata from ServiceNow.
        """
        url = (
            f"{self._config.attachment_url}/file"
            f"?table_name={table}"
            f"&table_sys_id={sys_id}"
            f"&file_name={file_name}"
        )
        extra_headers = {
            "Content-Type": content_type,
            "Accept": "application/json",
        }
        logger.info(
            "Adding attachment '%s' to %s/%s (%d bytes)",
            file_name,
            table,
            sys_id,
            len(content),
        )
        response = await self._request(
            "POST",
            url,
            content=content,
            extra_headers=extra_headers,
        )
        return response.get("result", response)
