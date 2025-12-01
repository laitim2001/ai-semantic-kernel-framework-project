# =============================================================================
# IPA Platform - SharePoint Connector
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Cross-System Integration
#
# Microsoft SharePoint connector for document management and collaboration.
# Provides:
#   - SharePointConnector: Full-featured SharePoint integration
#   - Document operations (list, get, search, upload, download)
#   - Site and list operations
#   - User and permissions queries
#
# SharePoint REST API Reference:
#   https://docs.microsoft.com/en-us/sharepoint/dev/sp-add-ins/get-to-know-the-sharepoint-rest-service
#
# Authentication:
#   Uses OAuth 2.0 with Azure AD (same as Dynamics 365).
#   Required credentials:
#     - tenant_id: Azure AD tenant ID
#     - client_id: Application (client) ID
#     - client_secret: Client secret value
#
# Usage:
#   config = ConnectorConfig(
#       name="prod-sharepoint",
#       connector_type="sharepoint",
#       base_url="https://company.sharepoint.com/sites/mysite",
#       auth_type=AuthType.OAUTH2,
#       credentials={
#           "tenant_id": "xxx",
#           "client_id": "xxx",
#           "client_secret": "xxx",
#       },
#   )
#   connector = SharePointConnector(config)
#   await connector.connect()
#   result = await connector.execute("list_documents", library="Documents")
# =============================================================================

import base64
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


class SharePointConnector(BaseConnector):
    """
    Microsoft SharePoint connector for document management and collaboration.

    Supports operations:
        - list_documents: List documents in a library
        - get_document: Get document metadata
        - search_documents: Search documents across site
        - download_document: Download document content
        - upload_document: Upload new document
        - list_sites: List accessible sites
        - list_lists: List site lists
        - get_list_items: Get items from a list

    Authentication:
        Uses OAuth 2.0 with Azure AD.
        Token is automatically refreshed before expiry.

    Example:
        connector = SharePointConnector(config)
        await connector.connect()

        # List documents
        result = await connector.execute(
            "list_documents",
            library="Documents",
            folder="Projects",
        )

        # Search documents
        result = await connector.execute(
            "search_documents",
            query="quarterly report",
            limit=10,
        )
    """

    name = "sharepoint"
    description = "Microsoft SharePoint connector for document management and collaboration"

    supported_operations = [
        "list_documents",
        "get_document",
        "search_documents",
        "download_document",
        "upload_document",
        "list_sites",
        "list_lists",
        "get_list_items",
        "health_check",
    ]

    # Azure AD OAuth endpoints
    AZURE_AD_AUTHORITY = "https://login.microsoftonline.com"
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, config: ConnectorConfig):
        """
        Initialize SharePoint connector.

        Args:
            config: ConnectorConfig with SharePoint settings
        """
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._site_id: Optional[str] = None

    async def connect(self) -> None:
        """
        Establish connection to SharePoint site.

        Authenticates with Azure AD and resolves site ID.

        Raises:
            ConnectorError: If authentication fails
        """
        logger.info(f"Connecting to SharePoint: {self._config.base_url}")
        self._status = ConnectorStatus.CONNECTING

        try:
            # Authenticate with Azure AD
            await self._authenticate()

            # Create HTTP client with bearer token
            self._client = httpx.AsyncClient(
                base_url=self.GRAPH_API_BASE,
                timeout=self._config.timeout_seconds,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                    **self._config.headers,
                },
            )

            # Resolve site ID from URL
            await self._resolve_site_id()

            self._status = ConnectorStatus.CONNECTED
            self._connected_at = datetime.utcnow()
            logger.info(
                f"Connected to SharePoint: {self._config.base_url}, "
                f"Site ID: {self._site_id}"
            )

        except httpx.ConnectError as e:
            self._status = ConnectorStatus.ERROR
            self._last_error = str(e)
            raise ConnectorError(
                message=f"Failed to connect to SharePoint: {e}",
                connector_name=self.name,
                operation="connect",
                error_code="CONNECTION_FAILED",
                original_error=e,
            )

    async def _authenticate(self) -> None:
        """
        Authenticate with Azure AD using OAuth 2.0 client credentials.

        Gets access token for Microsoft Graph API.
        """
        tenant_id = self._config.credentials.get("tenant_id", "")
        client_id = self._config.credentials.get("client_id", "")
        client_secret = self._config.credentials.get("client_secret", "")

        token_url = f"{self.AZURE_AD_AUTHORITY}/{tenant_id}/oauth2/v2.0/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://graph.microsoft.com/.default",
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

    async def _resolve_site_id(self) -> None:
        """
        Resolve SharePoint site ID from URL.

        Parses the base_url to extract hostname and site path,
        then queries Graph API to get the site ID.
        """
        from urllib.parse import urlparse

        parsed = urlparse(self._config.base_url)
        hostname = parsed.netloc
        site_path = parsed.path

        # Build Graph API site identifier
        # Format: {hostname}:{site_path}:
        if site_path and site_path != "/":
            site_identifier = f"{hostname}:{site_path}"
        else:
            site_identifier = hostname

        response = await self._client.get(
            f"/sites/{site_identifier}",
        )

        if response.status_code == 404:
            raise ConnectorError(
                message=f"SharePoint site not found: {self._config.base_url}",
                connector_name=self.name,
                operation="resolve_site",
                error_code="SITE_NOT_FOUND",
                retryable=False,
            )

        if response.status_code >= 400:
            raise ConnectorError(
                message=f"Failed to resolve site: HTTP {response.status_code}",
                connector_name=self.name,
                operation="resolve_site",
                error_code=f"HTTP_{response.status_code}",
            )

        data = response.json()
        self._site_id = data.get("id")

    async def _ensure_token_valid(self) -> None:
        """Refresh token if expired or about to expire."""
        if self._token_expires and datetime.utcnow() >= self._token_expires:
            logger.info("Refreshing SharePoint access token")
            await self._authenticate()
            if self._client:
                self._client.headers["Authorization"] = f"Bearer {self._access_token}"

    async def disconnect(self) -> None:
        """Close connection to SharePoint."""
        if self._client:
            await self._client.aclose()
            self._client = None

        self._status = ConnectorStatus.DISCONNECTED
        self._access_token = None
        self._token_expires = None
        self._site_id = None
        logger.info(f"Disconnected from SharePoint: {self._config.base_url}")

    async def execute(self, operation: str, **kwargs) -> ConnectorResponse:
        """
        Execute a SharePoint operation.

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
            "list_documents": self._list_documents,
            "get_document": self._get_document,
            "search_documents": self._search_documents,
            "download_document": self._download_document,
            "upload_document": self._upload_document,
            "list_sites": self._list_sites,
            "list_lists": self._list_lists,
            "get_list_items": self._get_list_items,
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

    async def _list_documents(
        self,
        library: str = "Documents",
        folder: Optional[str] = None,
        limit: int = 50,
        **kwargs,
    ) -> ConnectorResponse:
        """
        List documents in a document library.

        Args:
            library: Document library name (default: "Documents")
            folder: Subfolder path (optional)
            limit: Maximum files to return

        Returns:
            ConnectorResponse with list of documents
        """
        logger.debug(f"Listing documents in {library}/{folder or ''}")

        try:
            # Build path to folder
            drive_path = f"/sites/{self._site_id}/drives"

            # Get drive ID for the library
            drives_response = await self._client.get(drive_path)
            if drives_response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to get drives: HTTP {drives_response.status_code}",
                    error_code=f"HTTP_{drives_response.status_code}",
                )

            drives_data = drives_response.json()
            drives = drives_data.get("value", [])

            # Find matching drive
            drive_id = None
            for drive in drives:
                if drive.get("name", "").lower() == library.lower():
                    drive_id = drive.get("id")
                    break

            if not drive_id and drives:
                # Fall back to first drive
                drive_id = drives[0].get("id")

            if not drive_id:
                return ConnectorResponse(
                    success=False,
                    error=f"Library not found: {library}",
                    error_code="LIBRARY_NOT_FOUND",
                )

            # List children
            if folder:
                items_path = f"/drives/{drive_id}/root:/{folder}:/children"
            else:
                items_path = f"/drives/{drive_id}/root/children"

            params = {"$top": limit}
            response = await self._client.get(items_path, params=params)

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to list documents: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            items = data.get("value", [])

            # Format response
            documents = [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "size": item.get("size"),
                    "type": "folder" if "folder" in item else "file",
                    "created": item.get("createdDateTime"),
                    "modified": item.get("lastModifiedDateTime"),
                    "web_url": item.get("webUrl"),
                }
                for item in items
            ]

            return ConnectorResponse(
                success=True,
                data={
                    "documents": documents,
                    "count": len(documents),
                    "library": library,
                    "folder": folder,
                },
            )

        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise ConnectorError(
                message=f"Failed to list documents: {e}",
                connector_name=self.name,
                operation="list_documents",
                original_error=e,
            )

    async def _get_document(
        self,
        document_id: str,
        drive_id: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Get document metadata.

        Args:
            document_id: Document/file ID
            drive_id: Drive ID (optional, uses default)

        Returns:
            ConnectorResponse with document metadata
        """
        logger.debug(f"Getting document: {document_id}")

        try:
            # If no drive_id, get default drive
            if not drive_id:
                drive_response = await self._client.get(
                    f"/sites/{self._site_id}/drive"
                )
                if drive_response.status_code >= 400:
                    return ConnectorResponse(
                        success=False,
                        error="Failed to get default drive",
                        error_code="DRIVE_ERROR",
                    )
                drive_id = drive_response.json().get("id")

            response = await self._client.get(
                f"/drives/{drive_id}/items/{document_id}"
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"Document not found: {document_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to get document: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            return ConnectorResponse(
                success=True,
                data={
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "size": data.get("size"),
                    "mime_type": data.get("file", {}).get("mimeType"),
                    "created": data.get("createdDateTime"),
                    "modified": data.get("lastModifiedDateTime"),
                    "created_by": data.get("createdBy", {}).get("user", {}).get("displayName"),
                    "modified_by": data.get("lastModifiedBy", {}).get("user", {}).get("displayName"),
                    "web_url": data.get("webUrl"),
                    "download_url": data.get("@microsoft.graph.downloadUrl"),
                },
                metadata={"document_id": document_id},
            )

        except Exception as e:
            logger.error(f"Error getting document {document_id}: {e}")
            raise ConnectorError(
                message=f"Failed to get document: {e}",
                connector_name=self.name,
                operation="get_document",
                original_error=e,
            )

    async def _search_documents(
        self,
        query: str,
        limit: int = 25,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Search for documents across the site.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            ConnectorResponse with matching documents
        """
        logger.debug(f"Searching documents: {query}")

        try:
            # Use Graph Search API
            search_request = {
                "requests": [
                    {
                        "entityTypes": ["driveItem"],
                        "query": {
                            "queryString": query,
                        },
                        "from": 0,
                        "size": limit,
                    }
                ]
            }

            response = await self._client.post(
                "/search/query",
                json=search_request,
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to search documents: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            hits = (
                data.get("value", [{}])[0]
                .get("hitsContainers", [{}])[0]
                .get("hits", [])
            )

            # Format results
            results = [
                {
                    "id": hit.get("resource", {}).get("id"),
                    "name": hit.get("resource", {}).get("name"),
                    "summary": hit.get("summary"),
                    "web_url": hit.get("resource", {}).get("webUrl"),
                    "rank": hit.get("rank"),
                }
                for hit in hits
            ]

            return ConnectorResponse(
                success=True,
                data={
                    "results": results,
                    "count": len(results),
                    "query": query,
                },
            )

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise ConnectorError(
                message=f"Failed to search documents: {e}",
                connector_name=self.name,
                operation="search_documents",
                original_error=e,
            )

    async def _download_document(
        self,
        document_id: str,
        drive_id: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Download document content.

        Args:
            document_id: Document/file ID
            drive_id: Drive ID (optional)

        Returns:
            ConnectorResponse with document content (base64 encoded)
        """
        logger.debug(f"Downloading document: {document_id}")

        try:
            # Get document metadata first (includes download URL)
            doc_result = await self._get_document(document_id, drive_id)
            if not doc_result.success:
                return doc_result

            download_url = doc_result.data.get("download_url")
            if not download_url:
                return ConnectorResponse(
                    success=False,
                    error="No download URL available",
                    error_code="NO_DOWNLOAD_URL",
                )

            # Download content
            async with httpx.AsyncClient() as download_client:
                response = await download_client.get(download_url)

                if response.status_code >= 400:
                    return ConnectorResponse(
                        success=False,
                        error=f"Download failed: HTTP {response.status_code}",
                        error_code=f"HTTP_{response.status_code}",
                    )

                content = response.content
                content_b64 = base64.b64encode(content).decode("utf-8")

            return ConnectorResponse(
                success=True,
                data={
                    "document_id": document_id,
                    "name": doc_result.data.get("name"),
                    "content_base64": content_b64,
                    "size": len(content),
                    "mime_type": doc_result.data.get("mime_type"),
                },
            )

        except Exception as e:
            logger.error(f"Error downloading document {document_id}: {e}")
            raise ConnectorError(
                message=f"Failed to download document: {e}",
                connector_name=self.name,
                operation="download_document",
                original_error=e,
            )

    async def _upload_document(
        self,
        name: str,
        content: bytes,
        folder: Optional[str] = None,
        drive_id: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Upload a new document.

        Args:
            name: File name
            content: File content as bytes
            folder: Destination folder path (optional)
            drive_id: Drive ID (optional)

        Returns:
            ConnectorResponse with uploaded document info
        """
        logger.debug(f"Uploading document: {name}")

        try:
            # Get default drive if not specified
            if not drive_id:
                drive_response = await self._client.get(
                    f"/sites/{self._site_id}/drive"
                )
                if drive_response.status_code >= 400:
                    return ConnectorResponse(
                        success=False,
                        error="Failed to get default drive",
                        error_code="DRIVE_ERROR",
                    )
                drive_id = drive_response.json().get("id")

            # Build upload path
            if folder:
                upload_path = f"/drives/{drive_id}/root:/{folder}/{name}:/content"
            else:
                upload_path = f"/drives/{drive_id}/root:/{name}:/content"

            # Upload file (simple upload for small files)
            response = await self._client.put(
                upload_path,
                content=content,
                headers={"Content-Type": "application/octet-stream"},
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                return ConnectorResponse(
                    success=False,
                    error=f"Upload failed: {error_data.get('error', {}).get('message', 'Unknown')}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            return ConnectorResponse(
                success=True,
                data={
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "size": data.get("size"),
                    "web_url": data.get("webUrl"),
                },
                metadata={"folder": folder},
            )

        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            raise ConnectorError(
                message=f"Failed to upload document: {e}",
                connector_name=self.name,
                operation="upload_document",
                original_error=e,
            )

    async def _list_sites(self, limit: int = 50, **kwargs) -> ConnectorResponse:
        """
        List accessible SharePoint sites.

        Args:
            limit: Maximum sites to return

        Returns:
            ConnectorResponse with list of sites
        """
        logger.debug("Listing SharePoint sites")

        try:
            response = await self._client.get(
                "/sites",
                params={"$top": limit},
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to list sites: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            sites = [
                {
                    "id": site.get("id"),
                    "name": site.get("displayName"),
                    "web_url": site.get("webUrl"),
                    "created": site.get("createdDateTime"),
                }
                for site in data.get("value", [])
            ]

            return ConnectorResponse(
                success=True,
                data={
                    "sites": sites,
                    "count": len(sites),
                },
            )

        except Exception as e:
            logger.error(f"Error listing sites: {e}")
            raise ConnectorError(
                message=f"Failed to list sites: {e}",
                connector_name=self.name,
                operation="list_sites",
                original_error=e,
            )

    async def _list_lists(self, limit: int = 50, **kwargs) -> ConnectorResponse:
        """
        List SharePoint lists in the site.

        Args:
            limit: Maximum lists to return

        Returns:
            ConnectorResponse with list of SharePoint lists
        """
        logger.debug(f"Listing lists in site: {self._site_id}")

        try:
            response = await self._client.get(
                f"/sites/{self._site_id}/lists",
                params={"$top": limit},
            )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to list lists: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            lists = [
                {
                    "id": lst.get("id"),
                    "name": lst.get("displayName"),
                    "template": lst.get("list", {}).get("template"),
                    "created": lst.get("createdDateTime"),
                    "web_url": lst.get("webUrl"),
                }
                for lst in data.get("value", [])
            ]

            return ConnectorResponse(
                success=True,
                data={
                    "lists": lists,
                    "count": len(lists),
                },
            )

        except Exception as e:
            logger.error(f"Error listing lists: {e}")
            raise ConnectorError(
                message=f"Failed to list lists: {e}",
                connector_name=self.name,
                operation="list_lists",
                original_error=e,
            )

    async def _get_list_items(
        self,
        list_id: str,
        limit: int = 100,
        filter: Optional[str] = None,
        **kwargs,
    ) -> ConnectorResponse:
        """
        Get items from a SharePoint list.

        Args:
            list_id: List ID or name
            limit: Maximum items to return
            filter: OData filter expression

        Returns:
            ConnectorResponse with list items
        """
        logger.debug(f"Getting items from list: {list_id}")

        try:
            params = {"$top": limit, "$expand": "fields"}
            if filter:
                params["$filter"] = filter

            response = await self._client.get(
                f"/sites/{self._site_id}/lists/{list_id}/items",
                params=params,
            )

            if response.status_code == 404:
                return ConnectorResponse(
                    success=False,
                    error=f"List not found: {list_id}",
                    error_code="NOT_FOUND",
                )

            if response.status_code >= 400:
                return ConnectorResponse(
                    success=False,
                    error=f"Failed to get list items: HTTP {response.status_code}",
                    error_code=f"HTTP_{response.status_code}",
                )

            data = response.json()
            items = [
                {
                    "id": item.get("id"),
                    "fields": item.get("fields", {}),
                    "created": item.get("createdDateTime"),
                    "modified": item.get("lastModifiedDateTime"),
                    "web_url": item.get("webUrl"),
                }
                for item in data.get("value", [])
            ]

            return ConnectorResponse(
                success=True,
                data={
                    "items": items,
                    "count": len(items),
                    "list_id": list_id,
                },
            )

        except Exception as e:
            logger.error(f"Error getting list items: {e}")
            raise ConnectorError(
                message=f"Failed to get list items: {e}",
                connector_name=self.name,
                operation="get_list_items",
                original_error=e,
            )

    async def health_check(self, **kwargs) -> ConnectorResponse:
        """
        Verify SharePoint connectivity and health.

        Returns:
            ConnectorResponse with health status
        """
        try:
            start_time = datetime.utcnow()

            # Check site access
            response = await self._client.get(
                f"/sites/{self._site_id}"
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

            site_data = response.json()

            return ConnectorResponse(
                success=True,
                data={
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                    "site_name": site_data.get("displayName"),
                    "site_url": site_data.get("webUrl"),
                    "site_id": self._site_id,
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
