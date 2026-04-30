"""Tests for Azure VM management tools.

Tests VMTools class and its tool methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servers.azure.tools.vm import VMTools
from src.integrations.mcp.core.types import ToolInputType


class TestVMToolsSchemas:
    """Tests for VMTools schema definitions."""

    def test_get_schemas_returns_all_tools(self):
        """Test that get_schemas returns all VM tool schemas."""
        schemas = VMTools.get_schemas()
        assert len(schemas) == 7

        tool_names = [s.name for s in schemas]
        assert "list_vms" in tool_names
        assert "get_vm" in tool_names
        assert "get_vm_status" in tool_names
        assert "start_vm" in tool_names
        assert "stop_vm" in tool_names
        assert "restart_vm" in tool_names
        assert "run_command" in tool_names

    def test_list_vms_schema(self):
        """Test list_vms tool schema."""
        schemas = VMTools.get_schemas()
        schema = next(s for s in schemas if s.name == "list_vms")

        assert schema.description == "List all virtual machines in the subscription"
        assert len(schema.parameters) == 1

        param = schema.parameters[0]
        assert param.name == "resource_group"
        assert param.type == ToolInputType.STRING
        assert param.required is False

    def test_get_vm_schema(self):
        """Test get_vm tool schema."""
        schemas = VMTools.get_schemas()
        schema = next(s for s in schemas if s.name == "get_vm")

        assert "details" in schema.description.lower()
        assert len(schema.parameters) == 2

        # Check required parameters
        rg_param = next(p for p in schema.parameters if p.name == "resource_group")
        vm_param = next(p for p in schema.parameters if p.name == "vm_name")
        assert rg_param.required is True
        assert vm_param.required is True

    def test_run_command_schema(self):
        """Test run_command tool schema."""
        schemas = VMTools.get_schemas()
        schema = next(s for s in schemas if s.name == "run_command")

        assert len(schema.parameters) == 4

        # Check command_id parameter
        cmd_param = next(p for p in schema.parameters if p.name == "command_id")
        assert cmd_param.type == ToolInputType.STRING
        assert cmd_param.required is True


class TestVMToolsPermissions:
    """Tests for VMTools permission levels."""

    def test_permission_levels_defined(self):
        """Test that all tools have permission levels defined."""
        assert "list_vms" in VMTools.PERMISSION_LEVELS
        assert "get_vm" in VMTools.PERMISSION_LEVELS
        assert "get_vm_status" in VMTools.PERMISSION_LEVELS
        assert "start_vm" in VMTools.PERMISSION_LEVELS
        assert "stop_vm" in VMTools.PERMISSION_LEVELS
        assert "restart_vm" in VMTools.PERMISSION_LEVELS
        assert "run_command" in VMTools.PERMISSION_LEVELS

    def test_read_tools_have_level_1(self):
        """Test that read-only tools have level 1 permission."""
        assert VMTools.PERMISSION_LEVELS["list_vms"] == 1
        assert VMTools.PERMISSION_LEVELS["get_vm"] == 1
        assert VMTools.PERMISSION_LEVELS["get_vm_status"] == 1

    def test_write_tools_have_higher_levels(self):
        """Test that write tools have higher permission levels."""
        assert VMTools.PERMISSION_LEVELS["restart_vm"] == 2
        assert VMTools.PERMISSION_LEVELS["start_vm"] == 3
        assert VMTools.PERMISSION_LEVELS["stop_vm"] == 3
        assert VMTools.PERMISSION_LEVELS["run_command"] == 3


class TestVMToolsMethods:
    """Tests for VMTools methods."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock Azure client manager."""
        manager = MagicMock()
        manager.compute = MagicMock()
        return manager

    @pytest.fixture
    def vm_tools(self, mock_manager):
        """Create VMTools instance with mock manager."""
        return VMTools(mock_manager)

    @pytest.mark.asyncio
    async def test_list_vms_success(self, vm_tools, mock_manager):
        """Test successful VM listing."""
        # Setup mock VMs
        mock_vm = MagicMock()
        mock_vm.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1"
        mock_vm.name = "vm1"
        mock_vm.location = "eastus"
        mock_vm.vm_size = "Standard_DS2_v2"
        mock_vm.provisioning_state = "Succeeded"
        mock_vm.tags = {"env": "test"}
        mock_vm.hardware_profile = MagicMock()
        mock_vm.hardware_profile.vm_size = "Standard_DS2_v2"

        mock_manager.compute.virtual_machines.list_all.return_value = [mock_vm]

        result = await vm_tools.list_vms()

        assert result.success is True
        assert len(result.content) == 1
        assert result.content[0]["name"] == "vm1"
        assert result.content[0]["location"] == "eastus"

    @pytest.mark.asyncio
    async def test_list_vms_with_resource_group_filter(self, vm_tools, mock_manager):
        """Test VM listing with resource group filter."""
        mock_vm = MagicMock()
        mock_vm.id = "/subscriptions/sub/resourceGroups/test-rg/providers/Microsoft.Compute/virtualMachines/vm1"
        mock_vm.name = "vm1"
        mock_vm.location = "eastus"
        mock_vm.hardware_profile = MagicMock()
        mock_vm.hardware_profile.vm_size = "Standard_DS2_v2"
        mock_vm.provisioning_state = "Succeeded"
        mock_vm.tags = {}

        mock_manager.compute.virtual_machines.list.return_value = [mock_vm]

        result = await vm_tools.list_vms(resource_group="test-rg")

        mock_manager.compute.virtual_machines.list.assert_called_once_with("test-rg")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_list_vms_handles_error(self, vm_tools, mock_manager):
        """Test list_vms handles errors gracefully."""
        mock_manager.compute.virtual_machines.list_all.side_effect = Exception("API Error")

        result = await vm_tools.list_vms()

        assert result.success is False
        assert "API Error" in result.error

    @pytest.mark.asyncio
    async def test_get_vm_success(self, vm_tools, mock_manager):
        """Test successful VM retrieval."""
        mock_vm = MagicMock()
        mock_vm.id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1"
        mock_vm.name = "vm1"
        mock_vm.location = "eastus"
        mock_vm.hardware_profile = MagicMock()
        mock_vm.hardware_profile.vm_size = "Standard_DS2_v2"
        mock_vm.storage_profile = MagicMock()
        mock_vm.storage_profile.os_disk = MagicMock()
        mock_vm.storage_profile.os_disk.os_type = "Linux"
        mock_vm.storage_profile.os_disk.disk_size_gb = 128
        mock_vm.network_profile = MagicMock()
        mock_vm.network_profile.network_interfaces = []
        mock_vm.provisioning_state = "Succeeded"
        mock_vm.tags = {}

        mock_manager.compute.virtual_machines.get.return_value = mock_vm

        result = await vm_tools.get_vm("test-rg", "vm1")

        assert result.success is True
        assert result.content["name"] == "vm1"

    @pytest.mark.asyncio
    async def test_start_vm_success(self, vm_tools, mock_manager):
        """Test successful VM start."""
        mock_poller = MagicMock()
        mock_poller.result.return_value = None
        mock_manager.compute.virtual_machines.begin_start.return_value = mock_poller

        result = await vm_tools.start_vm("test-rg", "vm1")

        assert result.success is True
        mock_manager.compute.virtual_machines.begin_start.assert_called_once_with("test-rg", "vm1")

    @pytest.mark.asyncio
    async def test_stop_vm_success(self, vm_tools, mock_manager):
        """Test successful VM stop (deallocate)."""
        mock_poller = MagicMock()
        mock_poller.result.return_value = None
        mock_manager.compute.virtual_machines.begin_deallocate.return_value = mock_poller

        result = await vm_tools.stop_vm("test-rg", "vm1")

        assert result.success is True
        mock_manager.compute.virtual_machines.begin_deallocate.assert_called_once_with("test-rg", "vm1")

    @pytest.mark.asyncio
    async def test_restart_vm_success(self, vm_tools, mock_manager):
        """Test successful VM restart."""
        mock_poller = MagicMock()
        mock_poller.result.return_value = None
        mock_manager.compute.virtual_machines.begin_restart.return_value = mock_poller

        result = await vm_tools.restart_vm("test-rg", "vm1")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_command_success(self, vm_tools, mock_manager):
        """Test successful command execution on VM."""
        mock_result = MagicMock()
        mock_result.value = [MagicMock(message="command output", code="ProvisioningState/succeeded")]

        mock_poller = MagicMock()
        mock_poller.result.return_value = mock_result
        mock_manager.compute.virtual_machines.begin_run_command.return_value = mock_poller

        result = await vm_tools.run_command(
            resource_group="test-rg",
            vm_name="vm1",
            command_id="RunShellScript",
            script=["echo 'hello'"],
        )

        assert result.success is True
