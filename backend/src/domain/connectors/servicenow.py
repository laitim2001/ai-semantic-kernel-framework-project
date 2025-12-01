# =============================================================================
# IPA Platform - ServiceNow Connector
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# ServiceNow ITSM connector for incident and service request management.
# Provides:
#   - ServiceNowConnector: Full-featured ServiceNow integration
#   - Incident CRUD operations (get, list, create, update)
#   - Change request operations
#   - Knowledge base search
#
# ServiceNow API Reference:
#   https://docs.servicenow.com/bundle/tokyo-api/page/integrate/inbound-rest/
#
# Usage:
#   config = ConnectorConfig(
#       name="prod-snow",
#       connector_type="servicenow",
#       base_url="https://company.service-now.com",
#       auth_type=AuthType.BASIC,
#       credentials={"username": "api_user", "password": "secret"},
#   )
#   connector = ServiceNowConnector(config)
#   await connector.connect()
#   result = await connector.execute("get_incident", sys_id="abc123")
# =============================================================================

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from src.domain.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorConfig,
    ConnectorError,
    ConnectorResponse,
    ConnectorStatus,
)

logger = logging.getLogger(__name__)


class ServiceNowConnector(BaseConnector):
    """
    ServiceNow ITSM connector for incident and service management.

    Supports operations:
        - get_incident: Get incident by sys_id
        - list_incidents: List incidents with filters
        - create_incident: Create new incident
        - update_incident: Update existing incident
        - get_change: Get change request by sys_id
        - search_knowledge: Search knowledge base

    Authentication:
        - BASIC: Username/password authentication
        - OAUTH2: OAuth 2.0 client credentials

    Example:
        connector = ServiceNowConnector(config)
        await connector.connect()

        # Get incident
        result = await connector.execute(
            "get_incident",
            sys_id="abc123def456",
        )

        # List incidents
        result = await connector.execute(
            "list_incidents",
            state="new",
            limit=10,
        )
    """

    name = "servicenow"
    description = "ServiceNow ITSM connector for incident and service management"

    supported_operations = [
        "get_incident",
        "list_incidents",
        "create_incident",
        "update_incident",
        "get_change",
        "list_changes",
        "search_knowledge",
        "health_check",
    ]

    def __init__(self, config: ConnectorConfig):
        """
        Initialize ServiceNow connector.

        Args:
            config: ConnectorConfig with ServiceNow settings
        """
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._auth_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def connect(self) -> None:
        """
        Establish connection to ServiceNow instance.

        Validates credentials and creates HTTP client.

        Raises:
            ConnectorError: If authentication fails
        """
        logger.info(f"Connecting to ServiceNow: {self._config.base_url}")
        self._status = ConnectorStatus.CONNECTING

        try:
            # Create HTTP client with appropriate auth
            if self._config.auth_type == AuthType.BASIC:
                auth = httpx.BasicAuth(
                    username=self._config.credentials.get("username", ""),
                    password=self._config.credentials.get("password", ""),
                )
                self._client = httpx.AsyncClient(
                    base_url=self._config.base_url,
                    auth=auth,
                    timeout=self._config.timeout_seconds,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        **self._config.headers,
                    },
                )
            elif self._config.auth_type == AuthType.OAUTH2:
                await self._authenticate_oauth2()
                self._client = httpx.AsyncClient(
                    base_url=self._config.base_url,
                    timeout=self._config.timeout_seconds,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._auth_token}",
                        **self._config.headers,
                    },
                )
            else:
                # No auth
                self._client = httpx.AsyncClient(
                    base_url=self._config.base_url,
                    timeout=self._config.timeout_seconds,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        **self._config.headers,
                    },
                )

            # Verify connection with a simple API call
            response = await self._client.get("/api/now/table/sys_user?sysparm_limit=1")

            if response.status_code == 401:
                raise ConnectorError(
                    message="Authentication failed",
                    connector_name=self.name,
                    operation="connect",
                    error_code="AUTH_FAILED",
                    retryable=False,
                )

            if response.status_code >= 400:
                raise ConnectorError(
                    message=f"Connection failed: HTTP {response.status_code}",
                    connector_name=self.name,
                    operation="connect",
                    error_code=f"HTTP_{response.status_code}",
                )

            self._status = ConnectorStatus.CONNECTED
            self._connected_at = datetime.utcnow()
            logger.info(f"Connected to ServiceNow: {self._config.base_url}")

        except httpx.ConnectError as e:
            self._status = ConnectorStatus.ERROR
            self._last_error = str(e)
            raise ConnectorError(
                message=f"Failed to connect to ServiceNow: {e}",
                connector_name=self.name,
                operation="connect",
                error_code="CONNECTION_FAILED",
                original_error=e,
            )

    async def _authenticate_oauth2(self) -> None:
        """
        Authenticate using OAuth 2.0 client credentials.

        Sets self._auth_token and self._token_expires.
        """
        token_url = urljoin(self._config.base_url, "/oauth_token.do")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._config.credentials.get("client_id", ""),
                    "client_secret": self._config.credentials.get("client_secret", ""),
                },
            )

            if response.status_code != 200:
                raise ConnectorError(
                    message="OAuth2 authentication failed",
                    connector_name=self.name,
                    operation="authenticate",
                    error_code="OAUTH_FAILED",
                    retryable=False,
                )

            token_data = response.json()
            self._auth_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires = datetime.utcnow()

    async def disconnect(self) -> None:
        """Close connection to ServiceNow."""
        if self._client:
            await self._client.aclose()
            self._client = None

        self._status = ConnectorStatus.DISCONNECTED
        self._auth_token = None
        self._token_expires = None
        logger.info(f"Disconnected from ServiceNow: {self._config.base_url}")

    async def execute(self, operation: str, **kwargs) -> ConnectorResponse:
        """
        Execute a ServiceNow operation.

        Args:
            operation: Operation name
            **kwargs: Operation-specific parameters

        Returns:
            ConnectorResponse with operation result

        Raises:
            ConnectorError: If operation fails or is unsupported
        """
        if operation not in self.supported_operations:
            raise ConnectorError(
                message=f"Unsupported operation: {operation}",
                connector_name=self.name,
                operation=operation,
                error_code="UNSUPPORTED_OPERATION",
                retryable=False,
            )

        # Route to appropriate handler
        handlers = {
            "get_incident": self._get_incident,
            "list_incidents": self._list_incidents,
            "create_incident": self._create_incident,
            "update_incident": self._update_incident,
            "get_change": self._get_change,
            "list_changes": self._list_changes,
            "search_knowledge": self._search_knowledge,
            "health_check": self.health_check,
        }

        handler = handlers.get(operation)
        if handler:
            return await handler(**kwargs)

        raise ConnectorError(
            message=f"No handler for operation: {operation}",
            connector_name=self.name,
            operation=operation,
            error_code="NO_HANDLER",
        )

    async def _get_incident(self, sys_id: str, **kwargs) -> ConnectorResponse:
        """
        Get incident by sys_id.

        Args:
            sys_id: ServiceNow sys_id of the incident

        Returns:
            ConnectorResponse with incident data
        """
        logger.debug(f"Getting incident: {sys_id}")

        try:
            response = await self._client.get(
                f"/api/now/table/incident/{sys_id}",
                params={"sysparm_display_value": "true"},
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"Incident not found: {sys_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to get incident: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            return ConnectorResponse(
                success=True,
                data=data.get("result", {}),
                metadata={"sys_id": sys_id},
            )

        except Exception as e:
            logger.error(f"Error getting incident {sys_id}: {e}")
            raise ConnectorError(
                message=f"Failed to get incident: {e}",
                connector_name=self.name,
                operation="get_incident",
                original_error=e,
            )

    async def _list_incidents(
        self,
        limit: int = 20,
        offset: int = 0,
        state: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
        query: Optional[str] = None,
        order_by: str = "sys_created_on",
        order_desc: bool = True,
        **kwargs,
    ) -> ConnectorResponse:
        """
        List incidents with filtering.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            state: Filter by incident state (new, in_progress, resolved, closed)
            priority: Filter by priority (1-5)
            assigned_to: Filter by assigned user sys_id
            query: ServiceNow encoded query string
            order_by: Field to sort by
            order_desc: Sort descending if True

        Returns:
            ConnectorResponse with list of incidents
        """
        logger.debug(f"Listing incidents: limit={limit}, state={state}")

        try:
            # Build query params
            params = {
                "sysparm_limit": limit,
                "sysparm_offset": offset,
                "sysparm_display_value": "true",
                "sysparm_order_by": f"{order_by}{'DESC' if order_desc else ''}",
            }

            # Build query filter
            query_parts = []
            if state:
                state_map = {
                    "new": "1",
                    "in_progress": "2",
                    "on_hold": "3",
                    "resolved": "6",
                    "closed": "7",
                    "canceled": "8",
                }
                state_value = state_map.get(state.lower(), state)
                query_parts.append(f"state={state_value}")

            if priority:
                query_parts.append(f"priority={priority}")

            if assigned_to:
                query_parts.append(f"assigned_to={assigned_to}")

            if query:
                query_parts.append(query)

            if query_parts:
                params["sysparm_query"] = "^".join(query_parts)

            response = await self._client.get(
                "/api/now/table/incident",
                params=params,
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to list incidents: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            incidents = data.get("result", [])

            return ConnectorResponse(
                success=True,
                data={
                    "incidents": incidents,
                    "count": len(incidents),
                    "limit": limit,
                    "offset": offset,
                },
                metadata={
                    "query": params.get("sysparm_query"),
                },
            )

        except Exception as e:
            logger.error(f"Error listing incidents: {e}")
            raise ConnectorError(
                message=f"Failed to list incidents: {e}",
                connector_name=self.name,
                operation="list_incidents",
                original_error=e,
            )

    async def _create_incident(
        self,
        short_description: str,
        description: Optional[str] = None,
        caller_id: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        priority: int = 3,
        urgency: int = 3,
        impact: int = 3,
        assignment_group: Optional[str] = None,
        assigned_to: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Create a new incident.

        Args:
            short_description: Brief description of the incident
            description: Detailed description
            caller_id: sys_id of the caller
            category: Incident category
            subcategory: Incident subcategory
            priority: Priority (1-5, 1 is highest)
            urgency: Urgency (1-3)
            impact: Impact (1-3)
            assignment_group: sys_id of assignment group
            assigned_to: sys_id of assigned user

        Returns:
            ConnectorResponse with created incident data
        """
        logger.debug(f"Creating incident: {short_description}")

        try:
            payload = {
                "short_description": short_description,
                "priority": str(priority),
                "urgency": str(urgency),
                "impact": str(impact),
            }

            if description:
                payload["description"] = description
            if caller_id:
                payload["caller_id"] = caller_id
            if category:
                payload["category"] = category
            if subcategory:
                payload["subcategory"] = subcategory
            if assignment_group:
                payload["assignment_group"] = assignment_group
            if assigned_to:
                payload["assigned_to"] = assigned_to

            # Add any extra fields
            payload.update(kwargs)

            response = await self._client.post(
                "/api/now/table/incident",
                json=payload,
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to create incident: {error_data.get('error', {}).get('message', 'Unknown error')}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            incident = data.get("result", {})

            return ConnectorResponse(
                success=True,
                data=incident,
                metadata={
                    "sys_id": incident.get("sys_id"),
                    "number": incident.get("number"),
                },
            )

        except Exception as e:
            logger.error(f"Error creating incident: {e}")
            raise ConnectorError(
                message=f"Failed to create incident: {e}",
                connector_name=self.name,
                operation="create_incident",
                original_error=e,
            )

    async def _update_incident(
        self,
        sys_id: str,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Update an existing incident.

        Args:
            sys_id: ServiceNow sys_id of the incident
            **kwargs: Fields to update

        Returns:
            ConnectorResponse with updated incident data
        """
        logger.debug(f"Updating incident: {sys_id}")

        try:
            response = await self._client.patch(
                f"/api/now/table/incident/{sys_id}",
                json=kwargs,
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"Incident not found: {sys_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to update incident: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            return ConnectorResponse(
                success=True,
                data=data.get("result", {}),
                metadata={"sys_id": sys_id},
            )

        except Exception as e:
            logger.error(f"Error updating incident {sys_id}: {e}")
            raise ConnectorError(
                message=f"Failed to update incident: {e}",
                connector_name=self.name,
                operation="update_incident",
                original_error=e,
            )

    async def _get_change(self, sys_id: str, **kwargs) -> ConnectorResponse:
        """
        Get change request by sys_id.

        Args:
            sys_id: ServiceNow sys_id of the change request

        Returns:
            ConnectorResponse with change request data
        """
        logger.debug(f"Getting change request: {sys_id}")

        try:
            response = await self._client.get(
                f"/api/now/table/change_request/{sys_id}",
                params={"sysparm_display_value": "true"},
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"Change request not found: {sys_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to get change request: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            return ConnectorResponse(
                success=True,
                data=data.get("result", {}),
                metadata={"sys_id": sys_id},
            )

        except Exception as e:
            logger.error(f"Error getting change request {sys_id}: {e}")
            raise ConnectorError(
                message=f"Failed to get change request: {e}",
                connector_name=self.name,
                operation="get_change",
                original_error=e,
            )

    async def _list_changes(
        self,
        limit: int = 20,
        offset: int = 0,
        state: Optional[str] = None,
        type: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        List change requests with filtering.

        Args:
            limit: Maximum records to return
            offset: Records to skip
            state: Filter by state
            type: Filter by change type (normal, standard, emergency)

        Returns:
            ConnectorResponse with list of change requests
        """
        logger.debug(f"Listing change requests: limit={limit}")

        try:
            params = {
                "sysparm_limit": limit,
                "sysparm_offset": offset,
                "sysparm_display_value": "true",
            }

            query_parts = []
            if state:
                query_parts.append(f"state={state}")
            if type:
                query_parts.append(f"type={type}")

            if query_parts:
                params["sysparm_query"] = "^".join(query_parts)

            response = await self._client.get(
                "/api/now/table/change_request",
                params=params,
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to list change requests: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            changes = data.get("result", [])

            return ConnectorResponse(
                success=True,
                data={
                    "changes": changes,
                    "count": len(changes),
                    "limit": limit,
                    "offset": offset,
                },
            )

        except Exception as e:
            logger.error(f"Error listing change requests: {e}")
            raise ConnectorError(
                message=f"Failed to list change requests: {e}",
                connector_name=self.name,
                operation="list_changes",
                original_error=e,
            )

    async def _search_knowledge(
        self,
        query: str,
        limit: int = 10,
        knowledge_base: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Search knowledge base articles.

        Args:
            query: Search query string
            limit: Maximum results to return
            knowledge_base: Specific KB to search

        Returns:
            ConnectorResponse with matching articles
        """
        logger.debug(f"Searching knowledge base: {query}")

        try:
            params = {
                "sysparm_limit": limit,
                "sysparm_display_value": "true",
                "sysparm_query": f"short_descriptionLIKE{query}^ORtextLIKE{query}",
            }

            if knowledge_base:
                params["sysparm_query"] += f"^kb_knowledge_base={knowledge_base}"

            response = await self._client.get(
                "/api/now/table/kb_knowledge",
                params=params,
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to search knowledge base: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            articles = data.get("result", [])

            return ConnectorResponse(
                success=True,
                data={
                    "articles": articles,
                    "count": len(articles),
                    "query": query,
                },
            )

        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            raise ConnectorError(
                message=f"Failed to search knowledge base: {e}",
                connector_name=self.name,
                operation="search_knowledge",
                original_error=e,
            )

    async def health_check(self, **kwargs) -> ConnectorResponse:
        """
        Verify ServiceNow connectivity and health.

        Returns:
            ConnectorResponse with health status
        """
        try:
            start_time = datetime.utcnow()

            # Simple query to verify connectivity
            response = await self._client.get(
                "/api/now/table/sys_user",
                params={"sysparm_limit": 1},
            )

            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Health check failed: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                    data={
                        "status": "unhealthy",
                        "latency_ms": latency_ms,
                    },
                )

            return ConnectorResponse(
                success=True,
                data={
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                    "instance": self._config.base_url,
                    "last_check": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Health check failed: {e}",
                error_code="HEALTH_CHECK_FAILED",
                data={
                    "status": "unhealthy",
                    "error": str(e),
                },
            )
