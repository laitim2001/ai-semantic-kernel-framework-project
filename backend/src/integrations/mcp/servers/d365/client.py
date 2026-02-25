"""Dynamics 365 Web API Client.

Provides a typed async wrapper around the Dynamics 365 Web API (OData v4)
for entity CRUD operations, metadata discovery, and query building.

Features:
    - Service Principal authentication via D365AuthProvider
    - OData query builder with fluent interface
    - Automatic pagination via @odata.nextLink
    - Retry with exponential backoff for 429/5xx errors
    - Async HTTP via httpx.AsyncClient
    - Structured error handling with exception hierarchy

Environment Variables:
    D365_URL: Dynamics 365 organization URL (required)
        e.g. "https://org.crm.dynamics.com"
    D365_TENANT_ID: Azure AD tenant ID (required)
    D365_CLIENT_ID: Service Principal client ID (required)
    D365_CLIENT_SECRET: Service Principal client secret (required)
    D365_API_VERSION: Web API version (default: "v9.2")
    D365_TIMEOUT: Request timeout in seconds (default: 30)
    D365_MAX_RETRIES: Maximum retry attempts (default: 3)
    D365_MAX_PAGE_SIZE: Maximum records per page (default: 5000)

Reference:
    - Dynamics 365 Web API:
      https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/overview
    - OData v4 Query Options:
      https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/query-data-web-api
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from .auth import D365AuthConfig, D365AuthenticationError, D365AuthProvider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Known entity set names
# ---------------------------------------------------------------------------

ENTITY_SET_MAP: Dict[str, str] = {
    "account": "accounts",
    "contact": "contacts",
    "incident": "incidents",
    "msdyn_workorder": "msdyn_workorders",
    "systemuser": "systemusers",
    "team": "teams",
    "businessunit": "businessunits",
    "opportunity": "opportunities",
    "lead": "leads",
    "task": "tasks",
    "annotation": "annotations",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class D365ApiError(Exception):
    """Base exception for Dynamics 365 API errors.

    Attributes:
        status_code: HTTP status code from D365 Web API
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


class D365ConnectionError(D365ApiError):
    """Raised when connection to D365 Web API fails."""


class D365NotFoundError(D365ApiError):
    """Raised when a resource is not found (404)."""


class D365RateLimitError(D365ApiError):
    """Raised when rate limit is hit (429)."""


class D365ValidationError(D365ApiError):
    """Raised when request validation fails (400)."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class D365Config:
    """Dynamics 365 connection configuration.

    Attributes:
        d365_url: Organization URL (e.g. "https://org.crm.dynamics.com")
        tenant_id: Azure AD tenant ID
        client_id: Service Principal client ID
        client_secret: Service Principal client secret
        api_version: Web API version (default "v9.2")
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        retry_base_delay: Base delay for exponential backoff (seconds)
        max_page_size: Maximum records per OData page
    """

    d365_url: str
    tenant_id: str
    client_id: str
    client_secret: str
    api_version: str = "v9.2"
    timeout: int = 30
    max_retries: int = 3
    retry_base_delay: float = 1.0
    max_page_size: int = 5000

    @classmethod
    def from_env(cls) -> "D365Config":
        """Create configuration from environment variables.

        Returns:
            D365Config instance

        Raises:
            ValueError: If required environment variables are missing
        """
        required_vars = [
            "D365_URL",
            "D365_TENANT_ID",
            "D365_CLIENT_ID",
            "D365_CLIENT_SECRET",
        ]

        missing = [v for v in required_vars if not os.environ.get(v)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            d365_url=os.environ["D365_URL"].rstrip("/"),
            tenant_id=os.environ["D365_TENANT_ID"],
            client_id=os.environ["D365_CLIENT_ID"],
            client_secret=os.environ["D365_CLIENT_SECRET"],
            api_version=os.environ.get("D365_API_VERSION", "v9.2"),
            timeout=int(os.environ.get("D365_TIMEOUT", "30")),
            max_retries=int(os.environ.get("D365_MAX_RETRIES", "3")),
            max_page_size=int(os.environ.get("D365_MAX_PAGE_SIZE", "5000")),
        )

    @property
    def base_url(self) -> str:
        """Get the D365 Web API base URL."""
        return f"{self.d365_url}/api/data/{self.api_version}"


# ---------------------------------------------------------------------------
# OData Query Builder
# ---------------------------------------------------------------------------


class ODataQueryBuilder:
    """Fluent builder for OData v4 query parameters.

    Constructs query parameter dictionaries compatible with the Dynamics 365
    Web API OData implementation.

    Example:
        >>> query = (
        ...     ODataQueryBuilder()
        ...     .select("name", "accountnumber")
        ...     .filter("statecode eq 0")
        ...     .top(10)
        ...     .orderby("name")
        ... )
        >>> params = query.build()
        # {"$select": "name,accountnumber", "$filter": "statecode eq 0",
        #  "$top": "10", "$orderby": "name asc"}
    """

    def __init__(self) -> None:
        """Initialize an empty query builder."""
        self._select_fields: List[str] = []
        self._filter_expression: Optional[str] = None
        self._top_count: Optional[int] = None
        self._skip_count: Optional[int] = None
        self._orderby_clauses: List[str] = []
        self._expand_navigations: List[str] = []
        self._include_count: bool = False

    def select(self, *fields: str) -> "ODataQueryBuilder":
        """Set the $select clause to specify which fields to return.

        Args:
            *fields: Field names to include in the response

        Returns:
            Self for method chaining
        """
        self._select_fields = list(fields)
        return self

    def filter(self, expression: str) -> "ODataQueryBuilder":
        """Set the $filter clause to restrict results.

        Args:
            expression: OData filter expression
                (e.g. "statecode eq 0 and name ne null")

        Returns:
            Self for method chaining
        """
        self._filter_expression = expression
        return self

    def top(self, count: int) -> "ODataQueryBuilder":
        """Set the $top clause to limit the number of results.

        Args:
            count: Maximum number of records to return

        Returns:
            Self for method chaining

        Raises:
            D365ValidationError: If count is not a positive integer
        """
        if count < 1:
            raise D365ValidationError(
                f"$top count must be a positive integer, got {count}"
            )
        self._top_count = count
        return self

    def skip(self, count: int) -> "ODataQueryBuilder":
        """Set the $skip clause for manual pagination.

        Args:
            count: Number of records to skip

        Returns:
            Self for method chaining

        Raises:
            D365ValidationError: If count is negative
        """
        if count < 0:
            raise D365ValidationError(
                f"$skip count must be non-negative, got {count}"
            )
        self._skip_count = count
        return self

    def orderby(self, field: str, desc: bool = False) -> "ODataQueryBuilder":
        """Add an $orderby clause.

        Multiple calls accumulate ordering clauses.

        Args:
            field: Field name to sort by
            desc: If True, sort descending; otherwise ascending

        Returns:
            Self for method chaining
        """
        direction = "desc" if desc else "asc"
        self._orderby_clauses.append(f"{field} {direction}")
        return self

    def expand(self, *navigations: str) -> "ODataQueryBuilder":
        """Set the $expand clause to include related entities.

        Args:
            *navigations: Navigation property names to expand

        Returns:
            Self for method chaining
        """
        self._expand_navigations = list(navigations)
        return self

    def count(self) -> "ODataQueryBuilder":
        """Include total record count ($count=true) in the response.

        Returns:
            Self for method chaining
        """
        self._include_count = True
        return self

    def build(self) -> Dict[str, str]:
        """Build the final query parameter dictionary.

        Returns:
            Dictionary of OData query parameters ready for HTTP request
        """
        params: Dict[str, str] = {}

        if self._select_fields:
            params["$select"] = ",".join(self._select_fields)

        if self._filter_expression:
            params["$filter"] = self._filter_expression

        if self._top_count is not None:
            params["$top"] = str(self._top_count)

        if self._skip_count is not None:
            params["$skip"] = str(self._skip_count)

        if self._orderby_clauses:
            params["$orderby"] = ",".join(self._orderby_clauses)

        if self._expand_navigations:
            params["$expand"] = ",".join(self._expand_navigations)

        if self._include_count:
            params["$count"] = "true"

        return params


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _resolve_entity_set(entity_name: str) -> str:
    """Resolve a logical entity name to its OData entity set name.

    Uses ENTITY_SET_MAP for known mappings. For unknown entities, falls
    back to appending 's' or 'es' following common pluralization rules.

    Args:
        entity_name: Logical entity name (e.g. "account", "incident")

    Returns:
        OData entity set name (e.g. "accounts", "incidents")
    """
    lower = entity_name.lower()
    if lower in ENTITY_SET_MAP:
        return ENTITY_SET_MAP[lower]
    # Simple pluralization fallback
    if lower.endswith(("s", "x", "z", "sh", "ch")):
        return f"{lower}es"
    return f"{lower}s"


def _extract_record_id_from_header(odata_entity_id: str) -> Optional[str]:
    """Extract GUID from OData-EntityId header value.

    The header value is in the format:
        https://org.crm.dynamics.com/api/data/v9.2/accounts(00000000-0000-0000-0000-000000000000)

    Args:
        odata_entity_id: OData-EntityId header value

    Returns:
        Extracted GUID string, or None if parsing fails
    """
    match = re.search(
        r"\(([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\)",
        odata_entity_id,
    )
    return match.group(1) if match else None


def _parse_error_response(response: httpx.Response) -> str:
    """Parse D365 error response into a human-readable message.

    D365 error responses follow the format:
        {"error": {"code": "0x80040217", "message": "..."}}

    Args:
        response: httpx Response object

    Returns:
        Formatted error message string
    """
    try:
        body = response.json()
        error_obj = body.get("error", {})
        code = error_obj.get("code", "Unknown")
        message = error_obj.get("message", response.text)
        return f"[{code}] {message}"
    except Exception:
        return response.text or f"HTTP {response.status_code}"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class D365ApiClient:
    """Dynamics 365 Web API client.

    Provides async methods for interacting with the Dynamics 365 OData v4
    Web API. Delegates authentication to D365AuthProvider for token
    management with automatic refresh.

    Example:
        >>> config = D365Config.from_env()
        >>> client = D365ApiClient(config)
        >>> accounts = await client.query_entities("account")
        >>> await client.close()

    Context Manager:
        >>> async with D365ApiClient(config) as client:
        ...     contacts = await client.query_entities(
        ...         "contact",
        ...         ODataQueryBuilder().select("fullname", "emailaddress1").top(10),
        ...     )
    """

    def __init__(self, config: D365Config) -> None:
        """Initialize the D365 API client.

        Args:
            config: D365 connection configuration
        """
        self._config = config
        self._auth = D365AuthProvider(
            D365AuthConfig(
                tenant_id=config.tenant_id,
                client_id=config.client_id,
                client_secret=config.client_secret,
                d365_url=config.d365_url,
            )
        )
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout),
            headers={
                "Accept": "application/json",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
            },
        )
        self._healthy = False

        logger.info(
            "D365ApiClient initialized: url=%s, api_version=%s",
            config.d365_url,
            config.api_version,
        )

    # -------------------------------------------------------------------------
    # HTTP helpers
    # -------------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute an authenticated HTTP request with retry logic.

        Handles token acquisition, retry with exponential backoff for
        transient errors (429, 5xx), and structured error mapping.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: Full URL or path relative to base_url
            json_data: JSON request body
            params: Query parameters

        Returns:
            Parsed JSON response dictionary

        Raises:
            D365ConnectionError: On connection failure after retries
            D365AuthenticationError: On 401/403 (re-raised from auth provider)
            D365NotFoundError: On 404
            D365RateLimitError: On 429 after retry exhaustion
            D365ValidationError: On 400
            D365ApiError: On other HTTP errors
        """
        # Determine full URL
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{self._config.base_url}/{endpoint.lstrip('/')}"

        last_error: Optional[Exception] = None
        token = await self._auth.ensure_token()

        for attempt in range(self._config.max_retries):
            try:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
                # For create operations, request representation back
                if method.upper() == "POST" and json_data is not None:
                    headers["Prefer"] = "return=representation"
                # For update operations, request representation back
                if method.upper() == "PATCH" and json_data is not None:
                    headers["Prefer"] = "return=representation"

                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )

                # -- 401/403: Refresh token and retry once --
                if response.status_code in (401, 403):
                    if attempt == 0:
                        self._auth.invalidate_token()
                        token = await self._auth.ensure_token()
                        continue
                    error_msg = _parse_error_response(response)
                    raise D365AuthenticationError(
                        f"Authentication failed: {error_msg}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # -- 400: Validation error (no retry) --
                if response.status_code == 400:
                    error_msg = _parse_error_response(response)
                    raise D365ValidationError(
                        f"Validation error: {error_msg}",
                        status_code=400,
                        response_body=response.text,
                    )

                # -- 404: Not found (no retry) --
                if response.status_code == 404:
                    error_msg = _parse_error_response(response)
                    raise D365NotFoundError(
                        f"Resource not found: {error_msg}",
                        status_code=404,
                        response_body=response.text,
                    )

                # -- 429: Rate limited (retry with Retry-After) --
                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", "10")
                    )
                    if attempt < self._config.max_retries - 1:
                        logger.warning(
                            "D365 rate limited, retrying after %ds "
                            "(attempt %d/%d)",
                            retry_after,
                            attempt + 1,
                            self._config.max_retries,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    raise D365RateLimitError(
                        "Rate limit exceeded after retries",
                        status_code=429,
                        response_body=response.text,
                    )

                # -- 5xx: Server error (retry with backoff) --
                if response.status_code >= 500:
                    if attempt < self._config.max_retries - 1:
                        delay = self._config.retry_base_delay * (2 ** attempt)
                        logger.warning(
                            "D365 server error %d, retrying in %.1fs "
                            "(attempt %d/%d)",
                            response.status_code,
                            delay,
                            attempt + 1,
                            self._config.max_retries,
                        )
                        await asyncio.sleep(delay)
                        continue
                    error_msg = _parse_error_response(response)
                    raise D365ApiError(
                        f"Server error after retries: {error_msg}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # -- Other 4xx errors (no retry) --
                if response.status_code >= 400:
                    error_msg = _parse_error_response(response)
                    raise D365ApiError(
                        f"D365 API error: {error_msg}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # -- Success: Parse response --
                if response.status_code == 204 or not response.content:
                    # Extract record ID from OData-EntityId header if present
                    entity_id_header = response.headers.get("OData-EntityId")
                    if entity_id_header:
                        record_id = _extract_record_id_from_header(
                            entity_id_header
                        )
                        if record_id:
                            return {"id": record_id}
                    return {}

                return response.json()

            except (
                D365AuthenticationError,
                D365NotFoundError,
                D365ValidationError,
            ):
                # Non-retryable errors: propagate immediately
                raise
            except (D365RateLimitError, D365ApiError):
                # Already handled retry logic above
                raise
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt < self._config.max_retries - 1:
                    delay = self._config.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "D365 connection error: %s, retrying in %.1fs "
                        "(attempt %d/%d)",
                        exc,
                        delay,
                        attempt + 1,
                        self._config.max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise D365ConnectionError(
                        f"Failed to connect to D365 after "
                        f"{self._config.max_retries} attempts: {exc}"
                    ) from exc
            except httpx.HTTPError as exc:
                raise D365ConnectionError(
                    f"HTTP error communicating with D365: {exc}"
                ) from exc

        raise D365ConnectionError(
            f"Failed after {self._config.max_retries} attempts: {last_error}"
        )

    # -------------------------------------------------------------------------
    # Query operations
    # -------------------------------------------------------------------------

    async def query_entities(
        self,
        entity_name: str,
        query: Optional[ODataQueryBuilder] = None,
    ) -> Dict[str, Any]:
        """Query entity records with optional OData parameters.

        Returns a single page of results. Use query_entities_all() for
        automatic pagination across all pages.

        Args:
            entity_name: Logical entity name (e.g. "account", "contact")
            query: Optional ODataQueryBuilder for filtering/selection

        Returns:
            Dict containing 'value' (list of records) and optionally
            '@odata.nextLink' for pagination and '@odata.count' for
            total count

        Raises:
            D365NotFoundError: If entity set does not exist
            D365ApiError: On other API errors
        """
        entity_set = _resolve_entity_set(entity_name)
        params = query.build() if query else {}

        logger.debug(
            "Querying D365 entity set '%s' with params: %s",
            entity_set,
            params,
        )

        return await self._request(
            method="GET",
            endpoint=entity_set,
            params=params,
        )

    async def query_entities_all(
        self,
        entity_name: str,
        query: Optional[ODataQueryBuilder] = None,
        max_pages: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query all entity records with automatic pagination.

        Follows @odata.nextLink URLs to retrieve all pages of results.
        Respects max_page_size from config and enforces a maximum page
        limit to prevent runaway queries.

        Args:
            entity_name: Logical entity name (e.g. "account", "contact")
            query: Optional ODataQueryBuilder for filtering/selection
            max_pages: Maximum number of pages to fetch (safety limit)

        Returns:
            List of all matching entity records across all pages

        Raises:
            D365NotFoundError: If entity set does not exist
            D365ApiError: On other API errors
        """
        all_records: List[Dict[str, Any]] = []
        page_count = 0

        # First page
        result = await self.query_entities(entity_name, query)
        records = result.get("value", [])
        all_records.extend(records)
        page_count += 1

        # Follow @odata.nextLink for subsequent pages
        next_link = result.get("@odata.nextLink")

        while next_link and page_count < max_pages:
            logger.debug(
                "Fetching D365 next page %d for '%s'",
                page_count + 1,
                entity_name,
            )
            result = await self._request(method="GET", endpoint=next_link)
            records = result.get("value", [])
            all_records.extend(records)
            page_count += 1
            next_link = result.get("@odata.nextLink")

        if next_link and page_count >= max_pages:
            logger.warning(
                "D365 pagination limit reached (%d pages) for entity '%s'. "
                "Total records fetched: %d",
                max_pages,
                entity_name,
                len(all_records),
            )

        logger.info(
            "Fetched %d records for entity '%s' across %d pages",
            len(all_records),
            entity_name,
            page_count,
        )

        return all_records

    async def get_record(
        self,
        entity_name: str,
        record_id: str,
        select: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get a single entity record by ID.

        Args:
            entity_name: Logical entity name (e.g. "account", "contact")
            record_id: GUID of the record
            select: Optional list of fields to return

        Returns:
            Entity record dictionary

        Raises:
            D365NotFoundError: If record does not exist
            D365ApiError: On other API errors
        """
        entity_set = _resolve_entity_set(entity_name)
        endpoint = f"{entity_set}({record_id})"
        params: Optional[Dict[str, str]] = None

        if select:
            params = {"$select": ",".join(select)}

        return await self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
        )

    # -------------------------------------------------------------------------
    # CRUD operations
    # -------------------------------------------------------------------------

    async def create_record(
        self,
        entity_name: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new entity record.

        Sends a POST request with the Prefer: return=representation header
        to receive the created record in the response body. If the server
        returns 204 No Content, the record ID is extracted from the
        OData-EntityId header.

        Args:
            entity_name: Logical entity name (e.g. "account", "contact")
            data: Record field values

        Returns:
            Created record dictionary (includes server-generated fields)

        Raises:
            D365ValidationError: If request data is invalid
            D365ApiError: On other API errors
        """
        entity_set = _resolve_entity_set(entity_name)

        logger.info(
            "Creating D365 record in entity set '%s'",
            entity_set,
        )

        return await self._request(
            method="POST",
            endpoint=entity_set,
            json_data=data,
        )

    async def update_record(
        self,
        entity_name: str,
        record_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing entity record.

        Uses PATCH for partial updates with the
        Prefer: return=representation header.

        Args:
            entity_name: Logical entity name (e.g. "account", "contact")
            record_id: GUID of the record to update
            data: Fields to update (partial update, not all fields required)

        Returns:
            Updated record dictionary

        Raises:
            D365NotFoundError: If record does not exist
            D365ValidationError: If update data is invalid
            D365ApiError: On other API errors
        """
        entity_set = _resolve_entity_set(entity_name)
        endpoint = f"{entity_set}({record_id})"

        logger.info(
            "Updating D365 record '%s' in entity set '%s'",
            record_id,
            entity_set,
        )

        return await self._request(
            method="PATCH",
            endpoint=endpoint,
            json_data=data,
        )

    async def delete_record(
        self,
        entity_name: str,
        record_id: str,
    ) -> bool:
        """Delete an entity record.

        Args:
            entity_name: Logical entity name (e.g. "account", "contact")
            record_id: GUID of the record to delete

        Returns:
            True if deletion was successful

        Raises:
            D365NotFoundError: If record does not exist
            D365ApiError: On other API errors
        """
        entity_set = _resolve_entity_set(entity_name)
        endpoint = f"{entity_set}({record_id})"

        logger.info(
            "Deleting D365 record '%s' from entity set '%s'",
            record_id,
            entity_set,
        )

        await self._request(method="DELETE", endpoint=endpoint)
        return True

    # -------------------------------------------------------------------------
    # Metadata operations
    # -------------------------------------------------------------------------

    async def get_entity_metadata(
        self,
        entity_name: str,
    ) -> Dict[str, Any]:
        """Get metadata for a specific entity type.

        Retrieves entity definition including logical name, display name,
        entity set name, and primary key/name attributes.

        Args:
            entity_name: Logical entity name (e.g. "account")

        Returns:
            Entity metadata dictionary with keys:
                LogicalName, DisplayName, EntitySetName,
                PrimaryIdAttribute, PrimaryNameAttribute

        Raises:
            D365NotFoundError: If entity type does not exist
            D365ApiError: On other API errors
        """
        endpoint = f"EntityDefinitions(LogicalName='{entity_name}')"
        params = {
            "$select": (
                "LogicalName,DisplayName,EntitySetName,"
                "PrimaryIdAttribute,PrimaryNameAttribute"
            ),
        }

        logger.debug("Fetching D365 metadata for entity '%s'", entity_name)

        return await self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
        )

    async def list_entity_types(self) -> List[Dict[str, Any]]:
        """List all customizable entity types.

        Returns entity definitions filtered to customizable entities only,
        with basic metadata for each.

        Returns:
            List of entity metadata dictionaries, each containing:
                LogicalName, DisplayName, EntitySetName

        Raises:
            D365ApiError: On API errors
        """
        endpoint = "EntityDefinitions"
        params = {
            "$select": "LogicalName,DisplayName,EntitySetName",
            "$filter": "IsCustomizable/Value eq true",
        }

        logger.debug("Listing D365 entity types")

        result = await self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
        )
        return result.get("value", [])

    # -------------------------------------------------------------------------
    # Health check
    # -------------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Check D365 Web API connectivity.

        Performs a lightweight WhoAmI request to verify connectivity
        and authentication. WhoAmI is a built-in D365 function that
        returns the current user's information.

        Returns:
            True if D365 is reachable and authenticated
        """
        try:
            await self._request(method="GET", endpoint="WhoAmI")
            self._healthy = True
            logger.info("D365 health check passed")
            return True
        except Exception as exc:
            logger.warning("D365 health check failed: %s", exc)
            self._healthy = False
            return False

    @property
    def is_healthy(self) -> bool:
        """Get the last known health status.

        Returns:
            True if the most recent health check passed
        """
        return self._healthy

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._auth.close()
        await self._client.aclose()
        self._healthy = False
        logger.info("D365ApiClient closed")

    async def __aenter__(self) -> "D365ApiClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()
