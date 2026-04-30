"""Azure Storage Tools.

Provides MCP tools for storage account management.

Tools:
    - list_storage_accounts: List storage accounts
    - get_storage_account: Get storage account details
    - list_containers: List blob containers
    - get_storage_usage: Get storage account usage
"""

from typing import Any, Dict, List, Optional
import logging

from ....core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from ..client import AzureClientManager

logger = logging.getLogger(__name__)


class StorageTools:
    """Storage tools for Azure MCP Server.

    Provides storage account discovery and management.

    Permission Levels:
        - Level 1 (READ): All tools (read-only operations)

    Example:
        >>> manager = AzureClientManager(config)
        >>> tools = StorageTools(manager)
        >>> result = await tools.list_storage_accounts()
        >>> print(result.content)
    """

    # Permission levels for tools
    PERMISSION_LEVELS = {
        "list_storage_accounts": 1,
        "get_storage_account": 1,
        "list_containers": 1,
        "get_storage_usage": 1,
    }

    def __init__(self, client_manager: AzureClientManager):
        """Initialize Storage tools.

        Args:
            client_manager: Azure client manager instance
        """
        self._manager = client_manager

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all Storage tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="list_storage_accounts",
                description="List all storage accounts in the subscription",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Optional resource group filter",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="get_storage_account",
                description="Get details of a storage account",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="account_name",
                        type=ToolInputType.STRING,
                        description="Storage account name",
                        required=True,
                    ),
                ],
            ),
            ToolSchema(
                name="list_containers",
                description="List blob containers in a storage account",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="account_name",
                        type=ToolInputType.STRING,
                        description="Storage account name",
                        required=True,
                    ),
                ],
            ),
            ToolSchema(
                name="get_storage_usage",
                description="Get storage account usage and capacity",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="account_name",
                        type=ToolInputType.STRING,
                        description="Storage account name",
                        required=True,
                    ),
                ],
            ),
        ]

    async def list_storage_accounts(
        self,
        resource_group: Optional[str] = None,
    ) -> ToolResult:
        """List storage accounts.

        Args:
            resource_group: Optional resource group filter

        Returns:
            ToolResult with list of storage accounts
        """
        try:
            storage = self._manager.storage

            if resource_group:
                accounts = storage.storage_accounts.list_by_resource_group(resource_group)
            else:
                accounts = storage.storage_accounts.list()

            account_list = []
            for account in accounts:
                rg = self._extract_resource_group(account.id)

                account_list.append({
                    "name": account.name,
                    "resource_group": rg,
                    "location": account.location,
                    "kind": str(account.kind) if account.kind else None,
                    "sku": account.sku.name if account.sku else None,
                    "access_tier": str(account.access_tier) if account.access_tier else None,
                    "provisioning_state": str(account.provisioning_state) if account.provisioning_state else None,
                    "primary_location": account.primary_location,
                    "status_of_primary": str(account.status_of_primary) if account.status_of_primary else None,
                    "creation_time": account.creation_time.isoformat() if account.creation_time else None,
                    "id": account.id,
                    "tags": account.tags or {},
                })

            logger.info(f"Found {len(account_list)} storage accounts")
            return ToolResult(
                success=True,
                content=account_list,
                metadata={"count": len(account_list)},
            )

        except Exception as e:
            logger.error(f"Failed to list storage accounts: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_storage_account(
        self,
        resource_group: str,
        account_name: str,
    ) -> ToolResult:
        """Get storage account details.

        Args:
            resource_group: Resource group name
            account_name: Storage account name

        Returns:
            ToolResult with storage account details
        """
        try:
            storage = self._manager.storage
            account = storage.storage_accounts.get_properties(
                resource_group,
                account_name,
            )

            # Get endpoints
            endpoints = {}
            if account.primary_endpoints:
                endpoints["blob"] = account.primary_endpoints.blob
                endpoints["queue"] = account.primary_endpoints.queue
                endpoints["table"] = account.primary_endpoints.table
                endpoints["file"] = account.primary_endpoints.file
                endpoints["web"] = account.primary_endpoints.web
                endpoints["dfs"] = account.primary_endpoints.dfs

            # Get network rules
            network_rules = None
            if account.network_rule_set:
                network_rules = {
                    "default_action": str(account.network_rule_set.default_action) if account.network_rule_set.default_action else None,
                    "bypass": str(account.network_rule_set.bypass) if account.network_rule_set.bypass else None,
                    "ip_rules_count": len(account.network_rule_set.ip_rules or []),
                    "vnet_rules_count": len(account.network_rule_set.virtual_network_rules or []),
                }

            # Get encryption
            encryption = None
            if account.encryption:
                encryption = {
                    "key_source": str(account.encryption.key_source) if account.encryption.key_source else None,
                    "services": {},
                }
                if account.encryption.services:
                    if account.encryption.services.blob:
                        encryption["services"]["blob"] = account.encryption.services.blob.enabled
                    if account.encryption.services.file:
                        encryption["services"]["file"] = account.encryption.services.file.enabled
                    if account.encryption.services.table:
                        encryption["services"]["table"] = account.encryption.services.table.enabled
                    if account.encryption.services.queue:
                        encryption["services"]["queue"] = account.encryption.services.queue.enabled

            logger.info(f"Retrieved storage account details: {account_name}")
            return ToolResult(
                success=True,
                content={
                    "name": account.name,
                    "resource_group": resource_group,
                    "location": account.location,
                    "kind": str(account.kind) if account.kind else None,
                    "sku": account.sku.name if account.sku else None,
                    "access_tier": str(account.access_tier) if account.access_tier else None,
                    "provisioning_state": str(account.provisioning_state) if account.provisioning_state else None,
                    "primary_location": account.primary_location,
                    "secondary_location": account.secondary_location,
                    "status_of_primary": str(account.status_of_primary) if account.status_of_primary else None,
                    "status_of_secondary": str(account.status_of_secondary) if account.status_of_secondary else None,
                    "creation_time": account.creation_time.isoformat() if account.creation_time else None,
                    "endpoints": endpoints,
                    "network_rules": network_rules,
                    "encryption": encryption,
                    "enable_https_traffic_only": account.enable_https_traffic_only,
                    "is_hns_enabled": account.is_hns_enabled,
                    "id": account.id,
                    "tags": account.tags or {},
                },
            )

        except Exception as e:
            logger.error(f"Failed to get storage account {account_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def list_containers(
        self,
        resource_group: str,
        account_name: str,
    ) -> ToolResult:
        """List blob containers.

        Args:
            resource_group: Resource group name
            account_name: Storage account name

        Returns:
            ToolResult with list of containers
        """
        try:
            storage = self._manager.storage

            containers = storage.blob_containers.list(
                resource_group,
                account_name,
            )

            container_list = []
            for container in containers:
                container_list.append({
                    "name": container.name,
                    "public_access": str(container.public_access) if container.public_access else "None",
                    "lease_state": str(container.lease_state) if container.lease_state else None,
                    "lease_status": str(container.lease_status) if container.lease_status else None,
                    "last_modified": container.last_modified_time.isoformat() if container.last_modified_time else None,
                    "has_immutability_policy": container.has_immutability_policy,
                    "has_legal_hold": container.has_legal_hold,
                    "id": container.id,
                })

            logger.info(f"Found {len(container_list)} containers in {account_name}")
            return ToolResult(
                success=True,
                content=container_list,
                metadata={
                    "count": len(container_list),
                    "storage_account": account_name,
                },
            )

        except Exception as e:
            logger.error(f"Failed to list containers in {account_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_storage_usage(
        self,
        resource_group: str,
        account_name: str,
    ) -> ToolResult:
        """Get storage account usage.

        Args:
            resource_group: Resource group name
            account_name: Storage account name

        Returns:
            ToolResult with storage usage information
        """
        try:
            # Note: Getting detailed usage requires metrics or blob service stats
            # This implementation provides basic account information
            storage = self._manager.storage

            account = storage.storage_accounts.get_properties(
                resource_group,
                account_name,
            )

            # Get usage from subscription level
            usages = storage.usages.list_by_location(account.location)

            usage_list = []
            for usage in usages:
                usage_list.append({
                    "name": usage.name.value if usage.name else "Unknown",
                    "display_name": usage.name.localized_value if usage.name else None,
                    "current_value": usage.current_value,
                    "limit": usage.limit,
                    "unit": str(usage.unit) if usage.unit else None,
                })

            logger.info(f"Retrieved usage for location: {account.location}")
            return ToolResult(
                success=True,
                content={
                    "storage_account": account_name,
                    "location": account.location,
                    "sku": account.sku.name if account.sku else None,
                    "kind": str(account.kind) if account.kind else None,
                    "location_usages": usage_list,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get storage usage for {account_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    def _extract_resource_group(self, resource_id: str) -> str:
        """Extract resource group name from resource ID."""
        try:
            parts = resource_id.split("/")
            idx = parts.index("resourceGroups")
            return parts[idx + 1]
        except (ValueError, IndexError):
            return "unknown"
