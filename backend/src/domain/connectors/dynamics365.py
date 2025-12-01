# =============================================================================
# IPA Platform - Dynamics 365 Connector
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# Microsoft Dynamics 365 CRM connector for customer and case management.
# Provides:
#   - Dynamics365Connector: Full-featured Dynamics 365 integration
#   - Customer operations (get, list, search)
#   - Case/ticket operations (get, list, create, update)
#   - Contact and account management
#
# Dynamics 365 Web API Reference:
#   https://docs.microsoft.com/en-us/dynamics365/customer-engagement/developer/
#
# Authentication:
#   Uses OAuth 2.0 client credentials flow with Azure AD.
#   Required credentials:
#     - tenant_id: Azure AD tenant ID
#     - client_id: Application (client) ID
#     - client_secret: Client secret value
#     - resource: Dynamics 365 instance URL
#
# Usage:
#   config = ConnectorConfig(
#       name="prod-dynamics",
#       connector_type="dynamics365",
#       base_url="https://org.crm.dynamics.com",
#       auth_type=AuthType.OAUTH2,
#       credentials={
#           "tenant_id": "xxx",
#           "client_id": "xxx",
#           "client_secret": "xxx",
#       },
#   )
#   connector = Dynamics365Connector(config)
#   await connector.connect()
#   result = await connector.execute("get_customer", customer_id="xxx")
# =============================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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


class Dynamics365Connector(BaseConnector):
    """
    Microsoft Dynamics 365 CRM connector for customer and case management.

    Supports operations:
        - get_customer: Get customer (account or contact) by ID
        - list_customers: List customers with filters
        - search_customers: Search customers by name or email
        - get_case: Get case/incident by ID
        - list_cases: List cases with filters
        - create_case: Create new case
        - update_case: Update existing case
        - get_contact: Get contact by ID
        - get_account: Get account by ID

    Authentication:
        Uses OAuth 2.0 client credentials with Azure AD.
        Token is automatically refreshed before expiry.

    Example:
        connector = Dynamics365Connector(config)
        await connector.connect()

        # Get customer
        result = await connector.execute(
            "get_customer",
            customer_id="12345-abcde",
        )

        # Search customers
        result = await connector.execute(
            "search_customers",
            query="Contoso",
            limit=10,
        )
    """

    name = "dynamics365"
    description = "Microsoft Dynamics 365 CRM connector for customer and case management"

    supported_operations = [
        "get_customer",
        "list_customers",
        "search_customers",
        "get_case",
        "list_cases",
        "create_case",
        "update_case",
        "get_contact",
        "get_account",
        "list_contacts",
        "list_accounts",
        "health_check",
    ]

    # Azure AD OAuth endpoints
    AZURE_AD_AUTHORITY = "https://login.microsoftonline.com"

    def __init__(self, config: ConnectorConfig):
        """
        Initialize Dynamics 365 connector.

        Args:
            config: ConnectorConfig with Dynamics 365 settings
        """
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def connect(self) -> None:
        """
        Establish connection to Dynamics 365 instance.

        Authenticates with Azure AD and creates HTTP client.

        Raises:
            ConnectorError: If authentication fails
        """
        logger.info(f"Connecting to Dynamics 365: {self._config.base_url}")
        self._status = ConnectorStatus.CONNECTING

        try:
            # Authenticate with Azure AD
            await self._authenticate()

            # Create HTTP client with bearer token
            self._client = httpx.AsyncClient(
                base_url=self._config.base_url,
                timeout=self._config.timeout_seconds,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "OData-MaxVersion": "4.0",
                    "OData-Version": "4.0",
                    "Prefer": "odata.include-annotations=*",
                    "Authorization": f"Bearer {self._access_token}",
                    **self._config.headers,
                },
            )

            # Verify connection with WhoAmI
            response = await self._client.get("/api/data/v9.2/WhoAmI")

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

            who_am_i = response.json()
            logger.info(
                f"Connected to Dynamics 365: {self._config.base_url}, "
                f"User: {who_am_i.get('UserId')}"
            )

        except httpx.ConnectError as e:
            self._status = ConnectorStatus.ERROR
            self._last_error = str(e)
            raise ConnectorError(
                message=f"Failed to connect to Dynamics 365: {e}",
                connector_name=self.name,
                operation="connect",
                error_code="CONNECTION_FAILED",
                original_error=e,
            )

    async def _authenticate(self) -> None:
        """
        Authenticate with Azure AD using OAuth 2.0 client credentials.

        Gets access token and sets expiry time.
        """
        tenant_id = self._config.credentials.get("tenant_id", "")
        client_id = self._config.credentials.get("client_id", "")
        client_secret = self._config.credentials.get("client_secret", "")
        resource = self._config.base_url

        token_url = f"{self.AZURE_AD_AUTHORITY}/{tenant_id}/oauth2/v2.0/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": f"{resource}/.default",
                },
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise ConnectorError(
                    message=f"OAuth authentication failed: {error_data.get('error_description', 'Unknown error')}",
                    connector_name=self.name,
                    operation="authenticate",
                    error_code="OAUTH_FAILED",
                    retryable=False,
                )

            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 300)

    async def _ensure_token_valid(self) -> None:
        """Refresh token if expired or about to expire."""
        if self._token_expires and datetime.utcnow() >= self._token_expires:
            logger.info("Refreshing Dynamics 365 access token")
            await self._authenticate()
            # Update client headers
            if self._client:
                self._client.headers["Authorization"] = f"Bearer {self._access_token}"

    async def disconnect(self) -> None:
        """Close connection to Dynamics 365."""
        if self._client:
            await self._client.aclose()
            self._client = None

        self._status = ConnectorStatus.DISCONNECTED
        self._access_token = None
        self._token_expires = None
        logger.info(f"Disconnected from Dynamics 365: {self._config.base_url}")

    async def execute(self, operation: str, **kwargs) -> ConnectorResponse:
        """
        Execute a Dynamics 365 operation.

        Args:
            operation: Operation name
            **kwargs: Operation-specific parameters

        Returns:
            ConnectorResponse with operation result

        Raises:
            ConnectorError: If operation fails or is unsupported
        """
        # Ensure token is valid
        await self._ensure_token_valid()

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
            "get_customer": self._get_customer,
            "list_customers": self._list_customers,
            "search_customers": self._search_customers,
            "get_case": self._get_case,
            "list_cases": self._list_cases,
            "create_case": self._create_case,
            "update_case": self._update_case,
            "get_contact": self._get_contact,
            "get_account": self._get_account,
            "list_contacts": self._list_contacts,
            "list_accounts": self._list_accounts,
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

    async def _get_customer(
        self,
        customer_id: str,
        customer_type: str = "contact",
        **kwargs,
    ) -> ConnectorResponse:
        """
        Get customer by ID.

        Args:
            customer_id: Dynamics 365 record ID
            customer_type: "contact" or "account"

        Returns:
            ConnectorResponse with customer data
        """
        logger.debug(f"Getting {customer_type}: {customer_id}")

        if customer_type == "contact":
            return await self._get_contact(contact_id=customer_id)
        else:
            return await self._get_account(account_id=customer_id)

    async def _get_contact(self, contact_id: str, **kwargs) -> ConnectorResponse:
        """
        Get contact by ID.

        Args:
            contact_id: Contact record ID

        Returns:
            ConnectorResponse with contact data
        """
        try:
            response = await self._client.get(
                f"/api/data/v9.2/contacts({contact_id})",
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"Contact not found: {contact_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to get contact: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            return ConnectorResponse(
                success=True,
                data=data,
                metadata={"contact_id": contact_id},
            )

        except Exception as e:
            logger.error(f"Error getting contact {contact_id}: {e}")
            raise ConnectorError(
                message=f"Failed to get contact: {e}",
                connector_name=self.name,
                operation="get_contact",
                original_error=e,
            )

    async def _get_account(self, account_id: str, **kwargs) -> ConnectorResponse:
        """
        Get account by ID.

        Args:
            account_id: Account record ID

        Returns:
            ConnectorResponse with account data
        """
        try:
            response = await self._client.get(
                f"/api/data/v9.2/accounts({account_id})",
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"Account not found: {account_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to get account: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            return ConnectorResponse(
                success=True,
                data=data,
                metadata={"account_id": account_id},
            )

        except Exception as e:
            logger.error(f"Error getting account {account_id}: {e}")
            raise ConnectorError(
                message=f"Failed to get account: {e}",
                connector_name=self.name,
                operation="get_account",
                original_error=e,
            )

    async def _list_customers(
        self,
        customer_type: str = "contact",
        limit: int = 20,
        **kwargs,
    ) -> ConnectorResponse:
        """
        List customers.

        Args:
            customer_type: "contact" or "account"
            limit: Maximum records to return

        Returns:
            ConnectorResponse with list of customers
        """
        if customer_type == "account":
            return await self._list_accounts(limit=limit, **kwargs)
        else:
            return await self._list_contacts(limit=limit, **kwargs)

    async def _list_contacts(
        self,
        limit: int = 20,
        filter: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        List contacts.

        Args:
            limit: Maximum records to return
            filter: OData filter expression

        Returns:
            ConnectorResponse with list of contacts
        """
        try:
            params = {
                "$top": limit,
                "$select": "contactid,fullname,emailaddress1,telephone1,jobtitle",
            }
            if filter:
                params["$filter"] = filter

            response = await self._client.get(
                "/api/data/v9.2/contacts",
                params=params,
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to list contacts: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            contacts = data.get("value", [])

            return ConnectorResponse(
                success=True,
                data={
                    "contacts": contacts,
                    "count": len(contacts),
                    "limit": limit,
                },
            )

        except Exception as e:
            logger.error(f"Error listing contacts: {e}")
            raise ConnectorError(
                message=f"Failed to list contacts: {e}",
                connector_name=self.name,
                operation="list_contacts",
                original_error=e,
            )

    async def _list_accounts(
        self,
        limit: int = 20,
        filter: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        List accounts.

        Args:
            limit: Maximum records to return
            filter: OData filter expression

        Returns:
            ConnectorResponse with list of accounts
        """
        try:
            params = {
                "$top": limit,
                "$select": "accountid,name,emailaddress1,telephone1,websiteurl",
            }
            if filter:
                params["$filter"] = filter

            response = await self._client.get(
                "/api/data/v9.2/accounts",
                params=params,
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to list accounts: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            accounts = data.get("value", [])

            return ConnectorResponse(
                success=True,
                data={
                    "accounts": accounts,
                    "count": len(accounts),
                    "limit": limit,
                },
            )

        except Exception as e:
            logger.error(f"Error listing accounts: {e}")
            raise ConnectorError(
                message=f"Failed to list accounts: {e}",
                connector_name=self.name,
                operation="list_accounts",
                original_error=e,
            )

    async def _search_customers(
        self,
        query: str,
        customer_type: str = "contact",
        limit: int = 10,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Search customers by name or email.

        Args:
            query: Search query string
            customer_type: "contact" or "account"
            limit: Maximum results to return

        Returns:
            ConnectorResponse with matching customers
        """
        logger.debug(f"Searching {customer_type}s: {query}")

        try:
            if customer_type == "account":
                filter_expr = f"contains(name, '{query}')"
                endpoint = "/api/data/v9.2/accounts"
                select = "accountid,name,emailaddress1,telephone1"
            else:
                filter_expr = f"contains(fullname, '{query}') or contains(emailaddress1, '{query}')"
                endpoint = "/api/data/v9.2/contacts"
                select = "contactid,fullname,emailaddress1,telephone1"

            params = {
                "$top": limit,
                "$select": select,
                "$filter": filter_expr,
            }

            response = await self._client.get(endpoint, params=params)

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to search customers: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            results = data.get("value", [])

            return ConnectorResponse(
                success=True,
                data={
                    "results": results,
                    "count": len(results),
                    "query": query,
                    "customer_type": customer_type,
                },
            )

        except Exception as e:
            logger.error(f"Error searching customers: {e}")
            raise ConnectorError(
                message=f"Failed to search customers: {e}",
                connector_name=self.name,
                operation="search_customers",
                original_error=e,
            )

    async def _get_case(self, case_id: str, **kwargs) -> ConnectorResponse:
        """
        Get case by ID.

        Args:
            case_id: Case/incident record ID

        Returns:
            ConnectorResponse with case data
        """
        logger.debug(f"Getting case: {case_id}")

        try:
            response = await self._client.get(
                f"/api/data/v9.2/incidents({case_id})",
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"Case not found: {case_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to get case: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            return ConnectorResponse(
                success=True,
                data=data,
                metadata={"case_id": case_id},
            )

        except Exception as e:
            logger.error(f"Error getting case {case_id}: {e}")
            raise ConnectorError(
                message=f"Failed to get case: {e}",
                connector_name=self.name,
                operation="get_case",
                original_error=e,
            )

    async def _list_cases(
        self,
        limit: int = 20,
        state: Optional[int] = None,
        priority: Optional[int] = None,
        customer_id: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        List cases with filtering.

        Args:
            limit: Maximum records to return
            state: Filter by state code (0=Active, 1=Resolved, 2=Cancelled)
            priority: Filter by priority (1=High, 2=Normal, 3=Low)
            customer_id: Filter by customer ID

        Returns:
            ConnectorResponse with list of cases
        """
        logger.debug(f"Listing cases: limit={limit}, state={state}")

        try:
            params = {
                "$top": limit,
                "$select": "incidentid,title,ticketnumber,prioritycode,statecode,createdon",
                "$orderby": "createdon desc",
            }

            filters = []
            if state is not None:
                filters.append(f"statecode eq {state}")
            if priority is not None:
                filters.append(f"prioritycode eq {priority}")
            if customer_id:
                filters.append(f"_customerid_value eq '{customer_id}'")

            if filters:
                params["$filter"] = " and ".join(filters)

            response = await self._client.get(
                "/api/data/v9.2/incidents",
                params=params,
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to list cases: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            cases = data.get("value", [])

            return ConnectorResponse(
                success=True,
                data={
                    "cases": cases,
                    "count": len(cases),
                    "limit": limit,
                },
            )

        except Exception as e:
            logger.error(f"Error listing cases: {e}")
            raise ConnectorError(
                message=f"Failed to list cases: {e}",
                connector_name=self.name,
                operation="list_cases",
                original_error=e,
            )

    async def _create_case(
        self,
        title: str,
        description: Optional[str] = None,
        customer_id: Optional[str] = None,
        priority: int = 2,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Create a new case.

        Args:
            title: Case title
            description: Detailed description
            customer_id: Customer (contact/account) ID
            priority: Priority code (1=High, 2=Normal, 3=Low)

        Returns:
            ConnectorResponse with created case data
        """
        logger.debug(f"Creating case: {title}")

        try:
            payload = {
                "title": title,
                "prioritycode": priority,
            }

            if description:
                payload["description"] = description
            if customer_id:
                payload["customerid_contact@odata.bind"] = f"/contacts({customer_id})"

            # Add extra fields
            payload.update(kwargs)

            response = await self._client.post(
                "/api/data/v9.2/incidents",
                json=payload,
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to create case: {error_data.get('error', {}).get('message', 'Unknown')}",
                    error_code=f"HTTP_{response.status_code}",
                )

            # Get created record ID from header
            location = response.headers.get("OData-EntityId", "")
            case_id = location.split("(")[-1].rstrip(")") if location else None

            return ConnectorResponse(
                success=True,
                data={
                    "case_id": case_id,
                    "title": title,
                },
                metadata={"location": location},
            )

        except Exception as e:
            logger.error(f"Error creating case: {e}")
            raise ConnectorError(
                message=f"Failed to create case: {e}",
                connector_name=self.name,
                operation="create_case",
                original_error=e,
            )

    async def _update_case(
        self,
        case_id: str,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Update an existing case.

        Args:
            case_id: Case record ID
            **kwargs: Fields to update

        Returns:
            ConnectorResponse with update confirmation
        """
        logger.debug(f"Updating case: {case_id}")

        try:
            response = await self._client.patch(
                f"/api/data/v9.2/incidents({case_id})",
                json=kwargs,
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"Case not found: {case_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to update case: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            return ConnectorResponse(
                success=True,
                data={"case_id": case_id, "updated": True},
                metadata={"fields_updated": list(kwargs.keys())},
            )

        except Exception as e:
            logger.error(f"Error updating case {case_id}: {e}")
            raise ConnectorError(
                message=f"Failed to update case: {e}",
                connector_name=self.name,
                operation="update_case",
                original_error=e,
            )

    async def health_check(self, **kwargs) -> ConnectorResponse:
        """
        Verify Dynamics 365 connectivity and health.

        Returns:
            ConnectorResponse with health status
        """
        try:
            start_time = datetime.utcnow()

            # WhoAmI is a lightweight call to verify connectivity
            response = await self._client.get("/api/data/v9.2/WhoAmI")

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

            who_am_i = response.json()

            return ConnectorResponse(
                success=True,
                data={
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                    "organization_id": who_am_i.get("OrganizationId"),
                    "user_id": who_am_i.get("UserId"),
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
