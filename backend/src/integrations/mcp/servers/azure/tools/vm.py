"""Azure VM Management Tools.

Provides MCP tools for virtual machine management operations.

Tools:
    - list_vms: List all virtual machines
    - get_vm: Get VM details
    - get_vm_status: Get VM power state
    - start_vm: Start a VM
    - stop_vm: Stop a VM (deallocate)
    - restart_vm: Restart a VM
    - run_command: Execute command on VM
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging

from ....core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from ..client import AzureClientManager

logger = logging.getLogger(__name__)


@dataclass
class VMInfo:
    """Virtual machine information.

    Attributes:
        id: Azure resource ID
        name: VM name
        resource_group: Resource group name
        location: Azure region
        vm_size: VM size (e.g., Standard_D2s_v3)
        status: Power state (running, stopped, deallocated)
        os_type: Operating system type (Windows, Linux)
        private_ip: Private IP address
        public_ip: Public IP address (if any)
    """

    id: str
    name: str
    resource_group: str
    location: str
    vm_size: str
    status: str
    os_type: str
    private_ip: Optional[str] = None
    public_ip: Optional[str] = None


class VMTools:
    """VM management tools for Azure MCP Server.

    Provides comprehensive VM management capabilities including
    listing, status checking, and power operations.

    Permission Levels:
        - Level 1 (READ): list_vms, get_vm, get_vm_status
        - Level 2 (EXECUTE): restart_vm
        - Level 3 (ADMIN): start_vm, stop_vm, run_command

    Example:
        >>> manager = AzureClientManager(config)
        >>> tools = VMTools(manager)
        >>> result = await tools.list_vms()
        >>> print(result.content)
    """

    # Permission levels for tools
    PERMISSION_LEVELS = {
        "list_vms": 1,
        "get_vm": 1,
        "get_vm_status": 1,
        "start_vm": 3,
        "stop_vm": 3,
        "restart_vm": 2,
        "run_command": 3,
    }

    def __init__(self, client_manager: AzureClientManager):
        """Initialize VM tools.

        Args:
            client_manager: Azure client manager instance
        """
        self._manager = client_manager

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all VM tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="list_vms",
                description="List all virtual machines in the subscription or resource group",
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
                name="get_vm",
                description="Get detailed information about a virtual machine",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="vm_name",
                        type=ToolInputType.STRING,
                        description="Virtual machine name",
                        required=True,
                    ),
                ],
            ),
            ToolSchema(
                name="get_vm_status",
                description="Get the power state and status of a virtual machine",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="vm_name",
                        type=ToolInputType.STRING,
                        description="Virtual machine name",
                        required=True,
                    ),
                ],
            ),
            ToolSchema(
                name="start_vm",
                description="Start a stopped virtual machine",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="vm_name",
                        type=ToolInputType.STRING,
                        description="Virtual machine name",
                        required=True,
                    ),
                    ToolParameter(
                        name="wait",
                        type=ToolInputType.BOOLEAN,
                        description="Wait for operation to complete (default: false)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="stop_vm",
                description="Stop a running virtual machine (deallocates resources)",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="vm_name",
                        type=ToolInputType.STRING,
                        description="Virtual machine name",
                        required=True,
                    ),
                    ToolParameter(
                        name="skip_shutdown",
                        type=ToolInputType.BOOLEAN,
                        description="Skip graceful shutdown (force stop)",
                        required=False,
                    ),
                    ToolParameter(
                        name="wait",
                        type=ToolInputType.BOOLEAN,
                        description="Wait for operation to complete (default: false)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="restart_vm",
                description="Restart a virtual machine",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="vm_name",
                        type=ToolInputType.STRING,
                        description="Virtual machine name",
                        required=True,
                    ),
                    ToolParameter(
                        name="wait",
                        type=ToolInputType.BOOLEAN,
                        description="Wait for operation to complete (default: false)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="run_command",
                description="Execute a command on a virtual machine",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Resource group name",
                        required=True,
                    ),
                    ToolParameter(
                        name="vm_name",
                        type=ToolInputType.STRING,
                        description="Virtual machine name",
                        required=True,
                    ),
                    ToolParameter(
                        name="command",
                        type=ToolInputType.STRING,
                        description="Command to execute",
                        required=True,
                    ),
                    ToolParameter(
                        name="command_id",
                        type=ToolInputType.STRING,
                        description="Command type: RunPowerShellScript (Windows) or RunShellScript (Linux)",
                        required=False,
                    ),
                ],
            ),
        ]

    async def list_vms(
        self,
        resource_group: Optional[str] = None,
    ) -> ToolResult:
        """List virtual machines.

        Args:
            resource_group: Optional resource group filter

        Returns:
            ToolResult with list of VMs
        """
        try:
            compute = self._manager.compute

            if resource_group:
                vms = compute.virtual_machines.list(resource_group)
                logger.info(f"Listing VMs in resource group: {resource_group}")
            else:
                vms = compute.virtual_machines.list_all()
                logger.info("Listing all VMs in subscription")

            vm_list = []
            for vm in vms:
                # Parse resource group from ID
                parts = vm.id.split("/")
                rg_idx = parts.index("resourceGroups") if "resourceGroups" in parts else -1
                rg = parts[rg_idx + 1] if rg_idx >= 0 else "unknown"

                # Get OS type
                os_type = "Unknown"
                if vm.storage_profile and vm.storage_profile.os_disk:
                    os_type = str(vm.storage_profile.os_disk.os_type or "Unknown")

                # Get VM size
                vm_size = "Unknown"
                if vm.hardware_profile:
                    vm_size = vm.hardware_profile.vm_size or "Unknown"

                vm_list.append({
                    "id": vm.id,
                    "name": vm.name,
                    "resource_group": rg,
                    "location": vm.location,
                    "vm_size": vm_size,
                    "os_type": os_type,
                    "provisioning_state": vm.provisioning_state,
                    "tags": vm.tags or {},
                })

            logger.info(f"Found {len(vm_list)} VMs")
            return ToolResult(
                success=True,
                content=vm_list,
                metadata={"count": len(vm_list)},
            )

        except Exception as e:
            logger.error(f"Failed to list VMs: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_vm(
        self,
        resource_group: str,
        vm_name: str,
    ) -> ToolResult:
        """Get VM details.

        Args:
            resource_group: Resource group name
            vm_name: VM name

        Returns:
            ToolResult with VM details
        """
        try:
            compute = self._manager.compute
            vm = compute.virtual_machines.get(
                resource_group,
                vm_name,
                expand="instanceView",
            )

            # Get power state
            status = "Unknown"
            if vm.instance_view and vm.instance_view.statuses:
                for s in vm.instance_view.statuses:
                    if s.code and s.code.startswith("PowerState/"):
                        status = s.code.replace("PowerState/", "")
                        break

            # Get OS disk info
            os_disk = None
            if vm.storage_profile and vm.storage_profile.os_disk:
                os_disk = {
                    "name": vm.storage_profile.os_disk.name,
                    "os_type": str(vm.storage_profile.os_disk.os_type or "Unknown"),
                    "disk_size_gb": vm.storage_profile.os_disk.disk_size_gb,
                    "caching": str(vm.storage_profile.os_disk.caching or "None"),
                }

            # Get data disks
            data_disks = []
            if vm.storage_profile and vm.storage_profile.data_disks:
                for disk in vm.storage_profile.data_disks:
                    data_disks.append({
                        "name": disk.name,
                        "lun": disk.lun,
                        "disk_size_gb": disk.disk_size_gb,
                        "caching": str(disk.caching or "None"),
                    })

            # Get network interfaces
            network_interfaces = []
            if vm.network_profile and vm.network_profile.network_interfaces:
                for nic in vm.network_profile.network_interfaces:
                    network_interfaces.append({
                        "id": nic.id,
                        "primary": nic.primary,
                    })

            logger.info(f"Retrieved VM details: {vm_name}")
            return ToolResult(
                success=True,
                content={
                    "id": vm.id,
                    "name": vm.name,
                    "resource_group": resource_group,
                    "location": vm.location,
                    "vm_size": vm.hardware_profile.vm_size if vm.hardware_profile else "Unknown",
                    "status": status,
                    "provisioning_state": vm.provisioning_state,
                    "os_disk": os_disk,
                    "data_disks": data_disks,
                    "network_interfaces": network_interfaces,
                    "tags": vm.tags or {},
                    "vm_id": vm.vm_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get VM {vm_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_vm_status(
        self,
        resource_group: str,
        vm_name: str,
    ) -> ToolResult:
        """Get VM power state and status.

        Args:
            resource_group: Resource group name
            vm_name: VM name

        Returns:
            ToolResult with VM status
        """
        try:
            compute = self._manager.compute
            instance_view = compute.virtual_machines.instance_view(
                resource_group,
                vm_name,
            )

            statuses = []
            power_state = "Unknown"

            if instance_view.statuses:
                for status in instance_view.statuses:
                    status_info = {
                        "code": status.code,
                        "level": str(status.level) if status.level else "Info",
                        "display_status": status.display_status,
                        "time": status.time.isoformat() if status.time else None,
                    }
                    statuses.append(status_info)

                    # Extract power state
                    if status.code and status.code.startswith("PowerState/"):
                        power_state = status.code.replace("PowerState/", "")

            # Get disk statuses
            disk_statuses = []
            if instance_view.disks:
                for disk in instance_view.disks:
                    disk_info = {
                        "name": disk.name,
                        "statuses": [],
                    }
                    if disk.statuses:
                        for ds in disk.statuses:
                            disk_info["statuses"].append({
                                "code": ds.code,
                                "level": str(ds.level) if ds.level else "Info",
                                "display_status": ds.display_status,
                            })
                    disk_statuses.append(disk_info)

            logger.info(f"Retrieved status for VM: {vm_name} ({power_state})")
            return ToolResult(
                success=True,
                content={
                    "vm_name": vm_name,
                    "resource_group": resource_group,
                    "power_state": power_state,
                    "statuses": statuses,
                    "disk_statuses": disk_statuses,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get VM status {vm_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def start_vm(
        self,
        resource_group: str,
        vm_name: str,
        wait: bool = False,
    ) -> ToolResult:
        """Start a VM.

        Args:
            resource_group: Resource group name
            vm_name: VM name
            wait: Wait for operation to complete

        Returns:
            ToolResult with operation status
        """
        try:
            compute = self._manager.compute
            logger.info(f"Starting VM: {vm_name}")

            poller = compute.virtual_machines.begin_start(
                resource_group,
                vm_name,
            )

            if wait:
                poller.result()
                logger.info(f"VM {vm_name} started successfully")
                return ToolResult(
                    success=True,
                    content={
                        "message": f"VM {vm_name} started successfully",
                        "vm_name": vm_name,
                        "resource_group": resource_group,
                        "status": "running",
                    },
                )
            else:
                return ToolResult(
                    success=True,
                    content={
                        "message": f"Starting VM {vm_name}",
                        "vm_name": vm_name,
                        "resource_group": resource_group,
                        "operation_id": poller.operation_id if hasattr(poller, "operation_id") else None,
                        "status": "starting",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to start VM {vm_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def stop_vm(
        self,
        resource_group: str,
        vm_name: str,
        skip_shutdown: bool = False,
        wait: bool = False,
    ) -> ToolResult:
        """Stop a VM (deallocate).

        Args:
            resource_group: Resource group name
            vm_name: VM name
            skip_shutdown: Skip graceful shutdown
            wait: Wait for operation to complete

        Returns:
            ToolResult with operation status
        """
        try:
            compute = self._manager.compute
            logger.info(f"Stopping VM: {vm_name} (skip_shutdown={skip_shutdown})")

            # Use deallocate to release resources and stop billing
            poller = compute.virtual_machines.begin_deallocate(
                resource_group,
                vm_name,
            )

            if wait:
                poller.result()
                logger.info(f"VM {vm_name} stopped successfully")
                return ToolResult(
                    success=True,
                    content={
                        "message": f"VM {vm_name} stopped and deallocated successfully",
                        "vm_name": vm_name,
                        "resource_group": resource_group,
                        "status": "deallocated",
                    },
                )
            else:
                return ToolResult(
                    success=True,
                    content={
                        "message": f"Stopping VM {vm_name}",
                        "vm_name": vm_name,
                        "resource_group": resource_group,
                        "operation_id": poller.operation_id if hasattr(poller, "operation_id") else None,
                        "status": "stopping",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to stop VM {vm_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def restart_vm(
        self,
        resource_group: str,
        vm_name: str,
        wait: bool = False,
    ) -> ToolResult:
        """Restart a VM.

        Args:
            resource_group: Resource group name
            vm_name: VM name
            wait: Wait for operation to complete

        Returns:
            ToolResult with operation status
        """
        try:
            compute = self._manager.compute
            logger.info(f"Restarting VM: {vm_name}")

            poller = compute.virtual_machines.begin_restart(
                resource_group,
                vm_name,
            )

            if wait:
                poller.result()
                logger.info(f"VM {vm_name} restarted successfully")
                return ToolResult(
                    success=True,
                    content={
                        "message": f"VM {vm_name} restarted successfully",
                        "vm_name": vm_name,
                        "resource_group": resource_group,
                        "status": "running",
                    },
                )
            else:
                return ToolResult(
                    success=True,
                    content={
                        "message": f"Restarting VM {vm_name}",
                        "vm_name": vm_name,
                        "resource_group": resource_group,
                        "operation_id": poller.operation_id if hasattr(poller, "operation_id") else None,
                        "status": "restarting",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to restart VM {vm_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def run_command(
        self,
        resource_group: str,
        vm_name: str,
        command: str,
        command_id: Optional[str] = None,
    ) -> ToolResult:
        """Execute a command on a VM.

        Args:
            resource_group: Resource group name
            vm_name: VM name
            command: Command to execute
            command_id: Command type (RunPowerShellScript or RunShellScript)

        Returns:
            ToolResult with command output
        """
        try:
            from azure.mgmt.compute.models import RunCommandInput

            compute = self._manager.compute

            # Auto-detect command type if not specified
            if not command_id:
                # Get VM to check OS type
                vm = compute.virtual_machines.get(resource_group, vm_name)
                if vm.storage_profile and vm.storage_profile.os_disk:
                    os_type = str(vm.storage_profile.os_disk.os_type or "").lower()
                    command_id = "RunPowerShellScript" if os_type == "windows" else "RunShellScript"
                else:
                    command_id = "RunShellScript"  # Default to Linux

            logger.info(f"Running command on VM {vm_name}: {command[:50]}...")

            run_command_input = RunCommandInput(
                command_id=command_id,
                script=[command],
            )

            poller = compute.virtual_machines.begin_run_command(
                resource_group,
                vm_name,
                run_command_input,
            )

            # Wait for command to complete
            result = poller.result()

            output = []
            if result.value:
                for v in result.value:
                    output.append({
                        "code": v.code,
                        "level": str(v.level) if v.level else "Info",
                        "message": v.message,
                    })

            logger.info(f"Command executed on VM {vm_name}")
            return ToolResult(
                success=True,
                content={
                    "vm_name": vm_name,
                    "resource_group": resource_group,
                    "command": command,
                    "command_id": command_id,
                    "output": output,
                },
            )

        except Exception as e:
            logger.error(f"Failed to run command on {vm_name}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
