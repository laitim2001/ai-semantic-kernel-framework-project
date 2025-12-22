"""Azure SDK Client Manager.

Provides unified management for all Azure SDK clients.

This module handles:
    - Azure authentication using DefaultAzureCredential
    - Lazy initialization of SDK clients
    - Client lifecycle management
    - Connection pooling and caching
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable
from dataclasses import dataclass, field
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class AzureConfig:
    """Azure configuration.

    Attributes:
        subscription_id: Azure subscription ID (required)
        tenant_id: Azure AD tenant ID (optional, for service principal auth)
        client_id: Azure AD application client ID (optional)
        client_secret: Azure AD application client secret (optional)
        resource_group: Default resource group (optional)
        location: Default Azure region (optional)

    Example:
        >>> # Using environment variables
        >>> config = AzureConfig.from_env()
        >>>
        >>> # Manual configuration
        >>> config = AzureConfig(
        ...     subscription_id="xxx-xxx",
        ...     tenant_id="yyy-yyy",
        ... )
    """

    subscription_id: str
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    resource_group: Optional[str] = None
    location: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AzureConfig":
        """Create configuration from environment variables.

        Environment Variables:
            AZURE_SUBSCRIPTION_ID: Subscription ID (required)
            AZURE_TENANT_ID: Tenant ID (optional)
            AZURE_CLIENT_ID: Client ID (optional)
            AZURE_CLIENT_SECRET: Client secret (optional)
            AZURE_RESOURCE_GROUP: Default resource group (optional)
            AZURE_LOCATION: Default location (optional)

        Returns:
            AzureConfig instance

        Raises:
            ValueError: If AZURE_SUBSCRIPTION_ID is not set
        """
        subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
        if not subscription_id:
            raise ValueError("AZURE_SUBSCRIPTION_ID environment variable is required")

        return cls(
            subscription_id=subscription_id,
            tenant_id=os.environ.get("AZURE_TENANT_ID"),
            client_id=os.environ.get("AZURE_CLIENT_ID"),
            client_secret=os.environ.get("AZURE_CLIENT_SECRET"),
            resource_group=os.environ.get("AZURE_RESOURCE_GROUP"),
            location=os.environ.get("AZURE_LOCATION"),
        )


@runtime_checkable
class AzureClient(Protocol):
    """Protocol for Azure SDK clients."""

    def close(self) -> None:
        """Close the client and release resources."""
        ...


class AzureClientManager:
    """Azure SDK client manager.

    Manages lifecycle of Azure SDK clients with lazy initialization
    and proper resource cleanup.

    Example:
        >>> config = AzureConfig(subscription_id="xxx")
        >>> manager = AzureClientManager(config)
        >>>
        >>> # Get Compute client
        >>> compute = manager.compute
        >>> vms = compute.virtual_machines.list_all()
        >>>
        >>> # Cleanup when done
        >>> manager.close()

    Supported Clients:
        - compute: ComputeManagementClient (VMs, disks, images)
        - resource: ResourceManagementClient (resource groups, resources)
        - network: NetworkManagementClient (VNets, NSGs, load balancers)
        - monitor: MonitorManagementClient (metrics, alerts, logs)
        - storage: StorageManagementClient (storage accounts, blobs)
    """

    def __init__(self, config: AzureConfig):
        """Initialize the client manager.

        Args:
            config: Azure configuration
        """
        self._config = config
        self._credential: Optional[Any] = None
        self._clients: Dict[str, Any] = {}
        logger.info(
            f"AzureClientManager initialized for subscription: {config.subscription_id[:8]}..."
        )

    def _get_credential(self) -> Any:
        """Get or create Azure credential.

        Uses DefaultAzureCredential which supports multiple authentication methods:
            - Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
            - Managed identity
            - Azure CLI
            - Visual Studio Code
            - Azure PowerShell

        Returns:
            Azure credential object
        """
        if self._credential is None:
            try:
                from azure.identity import DefaultAzureCredential

                self._credential = DefaultAzureCredential()
                logger.debug("Azure credential initialized")
            except ImportError:
                raise ImportError(
                    "azure-identity package is required. "
                    "Install with: pip install azure-identity"
                )
        return self._credential

    @property
    def compute(self) -> Any:
        """Get Compute Management client.

        Returns:
            ComputeManagementClient for VM and disk operations
        """
        if "compute" not in self._clients:
            try:
                from azure.mgmt.compute import ComputeManagementClient

                self._clients["compute"] = ComputeManagementClient(
                    credential=self._get_credential(),
                    subscription_id=self._config.subscription_id,
                )
                logger.debug("ComputeManagementClient initialized")
            except ImportError:
                raise ImportError(
                    "azure-mgmt-compute package is required. "
                    "Install with: pip install azure-mgmt-compute"
                )
        return self._clients["compute"]

    @property
    def resource(self) -> Any:
        """Get Resource Management client.

        Returns:
            ResourceManagementClient for resource group and resource operations
        """
        if "resource" not in self._clients:
            try:
                from azure.mgmt.resource import ResourceManagementClient

                self._clients["resource"] = ResourceManagementClient(
                    credential=self._get_credential(),
                    subscription_id=self._config.subscription_id,
                )
                logger.debug("ResourceManagementClient initialized")
            except ImportError:
                raise ImportError(
                    "azure-mgmt-resource package is required. "
                    "Install with: pip install azure-mgmt-resource"
                )
        return self._clients["resource"]

    @property
    def network(self) -> Any:
        """Get Network Management client.

        Returns:
            NetworkManagementClient for VNet, NSG, and load balancer operations
        """
        if "network" not in self._clients:
            try:
                from azure.mgmt.network import NetworkManagementClient

                self._clients["network"] = NetworkManagementClient(
                    credential=self._get_credential(),
                    subscription_id=self._config.subscription_id,
                )
                logger.debug("NetworkManagementClient initialized")
            except ImportError:
                raise ImportError(
                    "azure-mgmt-network package is required. "
                    "Install with: pip install azure-mgmt-network"
                )
        return self._clients["network"]

    @property
    def monitor(self) -> Any:
        """Get Monitor Management client.

        Returns:
            MonitorManagementClient for metrics, alerts, and log operations
        """
        if "monitor" not in self._clients:
            try:
                from azure.mgmt.monitor import MonitorManagementClient

                self._clients["monitor"] = MonitorManagementClient(
                    credential=self._get_credential(),
                    subscription_id=self._config.subscription_id,
                )
                logger.debug("MonitorManagementClient initialized")
            except ImportError:
                raise ImportError(
                    "azure-mgmt-monitor package is required. "
                    "Install with: pip install azure-mgmt-monitor"
                )
        return self._clients["monitor"]

    @property
    def storage(self) -> Any:
        """Get Storage Management client.

        Returns:
            StorageManagementClient for storage account operations
        """
        if "storage" not in self._clients:
            try:
                from azure.mgmt.storage import StorageManagementClient

                self._clients["storage"] = StorageManagementClient(
                    credential=self._get_credential(),
                    subscription_id=self._config.subscription_id,
                )
                logger.debug("StorageManagementClient initialized")
            except ImportError:
                raise ImportError(
                    "azure-mgmt-storage package is required. "
                    "Install with: pip install azure-mgmt-storage"
                )
        return self._clients["storage"]

    @property
    def subscription_id(self) -> str:
        """Get the subscription ID."""
        return self._config.subscription_id

    @property
    def default_resource_group(self) -> Optional[str]:
        """Get the default resource group."""
        return self._config.resource_group

    @property
    def default_location(self) -> Optional[str]:
        """Get the default location."""
        return self._config.location

    def get_client(self, client_type: str) -> Any:
        """Get a client by type name.

        Args:
            client_type: Client type name (compute, resource, network, monitor, storage)

        Returns:
            Azure SDK client

        Raises:
            ValueError: If client type is not supported
        """
        client_map = {
            "compute": lambda: self.compute,
            "resource": lambda: self.resource,
            "network": lambda: self.network,
            "monitor": lambda: self.monitor,
            "storage": lambda: self.storage,
        }

        if client_type not in client_map:
            raise ValueError(
                f"Unknown client type: {client_type}. "
                f"Supported types: {list(client_map.keys())}"
            )

        return client_map[client_type]()

    def is_client_initialized(self, client_type: str) -> bool:
        """Check if a client is initialized.

        Args:
            client_type: Client type name

        Returns:
            True if client is initialized
        """
        return client_type in self._clients

    def close(self) -> None:
        """Close all clients and release resources.

        Should be called when the client manager is no longer needed.
        """
        for name, client in self._clients.items():
            try:
                if hasattr(client, "close"):
                    client.close()
                    logger.debug(f"Closed {name} client")
            except Exception as e:
                logger.warning(f"Error closing {name} client: {e}")

        self._clients.clear()
        self._credential = None
        logger.info("AzureClientManager closed")

    def __enter__(self) -> "AzureClientManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    async def __aenter__(self) -> "AzureClientManager":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        self.close()
