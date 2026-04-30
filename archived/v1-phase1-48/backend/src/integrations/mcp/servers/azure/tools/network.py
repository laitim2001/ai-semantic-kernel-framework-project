"""Azure Network Tools.

Provides MCP tools for network resource management.

Tools:
    - list_vnets: List virtual networks
    - get_vnet: Get VNet details
    - list_nsgs: List network security groups
    - get_nsg_rules: Get NSG rules
    - list_public_ips: List public IP addresses
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


class NetworkTools:
    """Network tools for Azure MCP Server.

    Provides network resource discovery and management.

    Permission Levels:
        - Level 1 (READ): All tools (read-only operations)

    Example:
        >>> manager = AzureClientManager(config)
        >>> tools = NetworkTools(manager)
        >>> result = await tools.list_vnets()
        >>> print(result.content)
    """

    # Permission levels for tools
    PERMISSION_LEVELS = {
        "list_vnets": 1,
        "get_vnet": 1,
        "list_nsgs": 1,
        "get_nsg_rules": 1,
        "list_public_ips": 1,
    }

    def __init__(self, client_manager: AzureClientManager):
        """Initialize Network tools.

        Args:
            client_manager: Azure client manager instance
        """
        self._manager = client_manager

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all Network tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="list_vnets",
                description="List all virtual networks in the subscription",
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
                name="get_vnet",
                description="Get details of a virtual network",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="vnet_name",
                        type=ToolInputType.STRING,
                        description="Virtual network name",
                        required=True,
                    ),
                ],
            ),
            ToolSchema(
                name="list_nsgs",
                description="List all network security groups",
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
                name="get_nsg_rules",
                description="Get rules of a network security group",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="nsg_name",
                        type=ToolInputType.STRING,
                        description="Network security group name",
                        required=True,
                    ),
                ],
            ),
            ToolSchema(
                name="list_public_ips",
                description="List all public IP addresses",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Optional resource group filter",
                        required=False,
                    ),
                ],
            ),
        ]

    async def list_vnets(
        self,
        resource_group: Optional[str] = None,
    ) -> ToolResult:
        """List virtual networks.

        Args:
            resource_group: Optional resource group filter

        Returns:
            ToolResult with list of VNets
        """
        try:
            network = self._manager.network

            if resource_group:
                vnets = network.virtual_networks.list(resource_group)
            else:
                vnets = network.virtual_networks.list_all()

            vnet_list = []
            for vnet in vnets:
                # Extract resource group from ID
                rg = self._extract_resource_group(vnet.id)

                # Get address space
                address_space = []
                if vnet.address_space and vnet.address_space.address_prefixes:
                    address_space = list(vnet.address_space.address_prefixes)

                # Get subnets summary
                subnets = []
                if vnet.subnets:
                    for subnet in vnet.subnets:
                        subnets.append({
                            "name": subnet.name,
                            "address_prefix": subnet.address_prefix,
                        })

                vnet_list.append({
                    "name": vnet.name,
                    "resource_group": rg,
                    "location": vnet.location,
                    "address_space": address_space,
                    "subnets_count": len(subnets),
                    "subnets": subnets,
                    "id": vnet.id,
                    "provisioning_state": vnet.provisioning_state,
                    "tags": vnet.tags or {},
                })

            logger.info(f"Found {len(vnet_list)} virtual networks")
            return ToolResult(
                success=True,
                content=vnet_list,
                metadata={"count": len(vnet_list)},
            )

        except Exception as e:
            logger.error(f"Failed to list VNets: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_vnet(
        self,
        resource_group: str,
        vnet_name: str,
    ) -> ToolResult:
        """Get VNet details.

        Args:
            resource_group: Resource group name
            vnet_name: VNet name

        Returns:
            ToolResult with VNet details
        """
        try:
            network = self._manager.network
            vnet = network.virtual_networks.get(resource_group, vnet_name)

            # Get address space
            address_space = []
            if vnet.address_space and vnet.address_space.address_prefixes:
                address_space = list(vnet.address_space.address_prefixes)

            # Get subnets
            subnets = []
            if vnet.subnets:
                for subnet in vnet.subnets:
                    subnet_info = {
                        "name": subnet.name,
                        "address_prefix": subnet.address_prefix,
                        "id": subnet.id,
                        "provisioning_state": subnet.provisioning_state,
                    }

                    # Get NSG if attached
                    if subnet.network_security_group:
                        subnet_info["network_security_group"] = subnet.network_security_group.id

                    subnets.append(subnet_info)

            # Get DNS servers
            dns_servers = []
            if vnet.dhcp_options and vnet.dhcp_options.dns_servers:
                dns_servers = list(vnet.dhcp_options.dns_servers)

            logger.info(f"Retrieved VNet details: {vnet_name}")
            return ToolResult(
                success=True,
                content={
                    "name": vnet.name,
                    "resource_group": resource_group,
                    "location": vnet.location,
                    "address_space": address_space,
                    "dns_servers": dns_servers,
                    "subnets": subnets,
                    "id": vnet.id,
                    "provisioning_state": vnet.provisioning_state,
                    "enable_ddos_protection": vnet.enable_ddos_protection,
                    "enable_vm_protection": vnet.enable_vm_protection,
                    "tags": vnet.tags or {},
                },
            )

        except Exception as e:
            logger.error(f"Failed to get VNet {vnet_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def list_nsgs(
        self,
        resource_group: Optional[str] = None,
    ) -> ToolResult:
        """List network security groups.

        Args:
            resource_group: Optional resource group filter

        Returns:
            ToolResult with list of NSGs
        """
        try:
            network = self._manager.network

            if resource_group:
                nsgs = network.network_security_groups.list(resource_group)
            else:
                nsgs = network.network_security_groups.list_all()

            nsg_list = []
            for nsg in nsgs:
                rg = self._extract_resource_group(nsg.id)

                # Count rules
                security_rules_count = len(nsg.security_rules or [])
                default_rules_count = len(nsg.default_security_rules or [])

                nsg_list.append({
                    "name": nsg.name,
                    "resource_group": rg,
                    "location": nsg.location,
                    "security_rules_count": security_rules_count,
                    "default_rules_count": default_rules_count,
                    "id": nsg.id,
                    "provisioning_state": nsg.provisioning_state,
                    "tags": nsg.tags or {},
                })

            logger.info(f"Found {len(nsg_list)} network security groups")
            return ToolResult(
                success=True,
                content=nsg_list,
                metadata={"count": len(nsg_list)},
            )

        except Exception as e:
            logger.error(f"Failed to list NSGs: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_nsg_rules(
        self,
        resource_group: str,
        nsg_name: str,
    ) -> ToolResult:
        """Get NSG rules.

        Args:
            resource_group: Resource group name
            nsg_name: NSG name

        Returns:
            ToolResult with NSG rules
        """
        try:
            network = self._manager.network
            nsg = network.network_security_groups.get(resource_group, nsg_name)

            # Get security rules
            security_rules = []
            for rule in nsg.security_rules or []:
                security_rules.append({
                    "name": rule.name,
                    "priority": rule.priority,
                    "direction": str(rule.direction) if rule.direction else None,
                    "access": str(rule.access) if rule.access else None,
                    "protocol": str(rule.protocol) if rule.protocol else None,
                    "source_address_prefix": rule.source_address_prefix,
                    "source_port_range": rule.source_port_range,
                    "destination_address_prefix": rule.destination_address_prefix,
                    "destination_port_range": rule.destination_port_range,
                    "description": rule.description,
                })

            # Get default rules
            default_rules = []
            for rule in nsg.default_security_rules or []:
                default_rules.append({
                    "name": rule.name,
                    "priority": rule.priority,
                    "direction": str(rule.direction) if rule.direction else None,
                    "access": str(rule.access) if rule.access else None,
                    "protocol": str(rule.protocol) if rule.protocol else None,
                })

            logger.info(f"Retrieved NSG rules: {nsg_name}")
            return ToolResult(
                success=True,
                content={
                    "name": nsg.name,
                    "resource_group": resource_group,
                    "location": nsg.location,
                    "security_rules": security_rules,
                    "default_rules": default_rules,
                    "id": nsg.id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get NSG rules {nsg_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def list_public_ips(
        self,
        resource_group: Optional[str] = None,
    ) -> ToolResult:
        """List public IP addresses.

        Args:
            resource_group: Optional resource group filter

        Returns:
            ToolResult with list of public IPs
        """
        try:
            network = self._manager.network

            if resource_group:
                public_ips = network.public_ip_addresses.list(resource_group)
            else:
                public_ips = network.public_ip_addresses.list_all()

            ip_list = []
            for ip in public_ips:
                rg = self._extract_resource_group(ip.id)

                ip_list.append({
                    "name": ip.name,
                    "resource_group": rg,
                    "location": ip.location,
                    "ip_address": ip.ip_address,
                    "allocation_method": str(ip.public_ip_allocation_method) if ip.public_ip_allocation_method else None,
                    "sku": ip.sku.name if ip.sku else None,
                    "dns_fqdn": ip.dns_settings.fqdn if ip.dns_settings else None,
                    "id": ip.id,
                    "provisioning_state": ip.provisioning_state,
                    "tags": ip.tags or {},
                })

            logger.info(f"Found {len(ip_list)} public IP addresses")
            return ToolResult(
                success=True,
                content=ip_list,
                metadata={"count": len(ip_list)},
            )

        except Exception as e:
            logger.error(f"Failed to list public IPs: {e}")
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
