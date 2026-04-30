"""
Unit Tests for Tool Call Handler (Sprint 45-3)

測試工具調用框架的各項功能:
- 工具調用解析
- 權限檢查
- 工具執行
- 結果格式化
- 多輪調用
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json

from src.domain.sessions.tool_handler import (
    ToolCallHandler,
    ToolCallParser,
    ToolHandlerConfig,
    ToolHandlerStats,
    ParsedToolCall,
    ToolExecutionResult,
    ToolSource,
    ToolPermission,
    ToolRegistryProtocol,
    MCPClientProtocol,
    create_tool_handler,
)
from src.domain.sessions.events import (
    ExecutionEvent,
    ExecutionEventType,
    ToolCallInfo,
    ToolResultInfo,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@dataclass
class MockToolResult:
    """Mock tool result"""
    success: bool
    data: Any
    error: Optional[str] = None


class MockTool:
    """Mock tool for testing"""
    def __init__(self, name: str, result: Any = None, error: str = None, is_async: bool = False):
        self.name = name
        self.description = f"Test tool: {name}"
        self.parameters = {"type": "object", "properties": {}}
        self._result = result if result is not None else {"status": "ok"}
        self._error = error
        self._is_async = is_async

    def execute(self, **kwargs):
        if self._error:
            raise Exception(self._error)
        if self._is_async:
            raise RuntimeError("Use async execute")
        return MockToolResult(success=True, data=self._result)

    async def async_execute(self, **kwargs):
        if self._error:
            raise Exception(self._error)
        return MockToolResult(success=True, data=self._result)


class MockToolRegistry:
    """Mock tool registry"""
    def __init__(self, tools: Dict[str, MockTool] = None):
        self._tools = tools or {}

    def get(self, name: str) -> Optional[MockTool]:
        return self._tools.get(name)

    def get_all(self) -> Dict[str, MockTool]:
        return self._tools

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            }
            for tool in self._tools.values()
        ]


class MockMCPResult:
    """Mock MCP tool result"""
    def __init__(self, success: bool, content: Any, error: str = None):
        self.success = success
        self.content = content
        self.error = error


class MockMCPClient:
    """Mock MCP client"""
    def __init__(self, servers: List[str] = None):
        self._servers = servers or []
        self._results = {}

    async def call_tool(
        self,
        server: str,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> MockMCPResult:
        key = f"{server}:{tool}"
        if key in self._results:
            return self._results[key]
        return MockMCPResult(success=True, content={"result": "mcp_ok"})

    async def list_tools(
        self,
        server_name: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, List[Any]]:
        return {s: [] for s in self._servers}

    @property
    def connected_servers(self) -> List[str]:
        return self._servers

    def set_result(self, server: str, tool: str, result: MockMCPResult):
        self._results[f"{server}:{tool}"] = result


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry with test tools"""
    tools = {
        "calculator": MockTool("calculator", {"result": 42}),
        "get_weather": MockTool("get_weather", {"temp": 25, "condition": "sunny"}),
        "error_tool": MockTool("error_tool", error="Tool error"),
    }
    return MockToolRegistry(tools)


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client"""
    return MockMCPClient(servers=["azure", "github"])


@pytest.fixture
def handler_config():
    """Create test handler config"""
    return ToolHandlerConfig(
        max_parallel_calls=3,
        default_timeout=10.0,
        max_tool_rounds=5,
        blocked_tools={"dangerous_tool"},
        require_approval_tools={"sensitive_tool"},
    )


@pytest.fixture
def tool_handler(mock_tool_registry, mock_mcp_client, handler_config):
    """Create tool handler with mocks"""
    return ToolCallHandler(
        tool_registry=mock_tool_registry,
        mcp_client=mock_mcp_client,
        config=handler_config,
    )


# =============================================================================
# Test ToolSource Enum
# =============================================================================


class TestToolSource:
    """Test ToolSource enum"""

    def test_tool_source_values(self):
        """Test enum values"""
        assert ToolSource.LOCAL.value == "local"
        assert ToolSource.MCP.value == "mcp"
        assert ToolSource.BUILTIN.value == "builtin"

    def test_tool_source_string(self):
        """Test string conversion"""
        assert str(ToolSource.LOCAL) == "ToolSource.LOCAL"


# =============================================================================
# Test ToolPermission Enum
# =============================================================================


class TestToolPermission:
    """Test ToolPermission enum"""

    def test_permission_values(self):
        """Test enum values"""
        assert ToolPermission.AUTO.value == "auto"
        assert ToolPermission.NOTIFY.value == "notify"
        assert ToolPermission.APPROVAL_REQUIRED.value == "approval"
        assert ToolPermission.DENIED.value == "denied"


# =============================================================================
# Test ParsedToolCall
# =============================================================================


class TestParsedToolCall:
    """Test ParsedToolCall dataclass"""

    def test_basic_creation(self):
        """Test basic creation"""
        tc = ParsedToolCall(
            id="tc_123",
            name="test_tool",
            arguments={"arg1": "value1"},
        )
        assert tc.id == "tc_123"
        assert tc.name == "test_tool"
        assert tc.arguments == {"arg1": "value1"}
        assert tc.source == ToolSource.LOCAL
        assert tc.server_name is None

    def test_mcp_tool_call(self):
        """Test MCP tool call"""
        tc = ParsedToolCall(
            id="tc_456",
            name="mcp_azure_list_vms",
            arguments={"rg": "prod"},
            source=ToolSource.MCP,
            server_name="azure",
        )
        assert tc.source == ToolSource.MCP
        assert tc.server_name == "azure"

    def test_to_tool_call_info(self):
        """Test conversion to ToolCallInfo"""
        tc = ParsedToolCall(
            id="tc_789",
            name="calculator",
            arguments={"x": 1, "y": 2},
        )
        info = tc.to_tool_call_info(requires_approval=True)

        assert isinstance(info, ToolCallInfo)
        assert info.id == "tc_789"
        assert info.name == "calculator"
        assert info.arguments == {"x": 1, "y": 2}
        assert info.requires_approval is True


# =============================================================================
# Test ToolExecutionResult
# =============================================================================


class TestToolExecutionResult:
    """Test ToolExecutionResult dataclass"""

    def test_successful_result(self):
        """Test successful result"""
        result = ToolExecutionResult(
            tool_call_id="tc_123",
            name="calculator",
            success=True,
            result={"answer": 42},
            execution_time_ms=15.5,
        )
        assert result.success is True
        assert result.result == {"answer": 42}
        assert result.error is None

    def test_failed_result(self):
        """Test failed result"""
        result = ToolExecutionResult(
            tool_call_id="tc_456",
            name="error_tool",
            success=False,
            result=None,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_to_tool_result_info(self):
        """Test conversion to ToolResultInfo"""
        result = ToolExecutionResult(
            tool_call_id="tc_123",
            name="calculator",
            success=True,
            result={"answer": 42},
        )
        info = result.to_tool_result_info()

        assert isinstance(info, ToolResultInfo)
        assert info.tool_call_id == "tc_123"
        assert info.name == "calculator"
        assert info.success is True
        assert info.result == {"answer": 42}

    def test_to_llm_message_success(self):
        """Test conversion to LLM message - success"""
        result = ToolExecutionResult(
            tool_call_id="tc_123",
            name="calculator",
            success=True,
            result={"answer": 42},
        )
        msg = result.to_llm_message()

        assert msg["role"] == "tool"
        assert msg["tool_call_id"] == "tc_123"
        assert "42" in msg["content"]

    def test_to_llm_message_failure(self):
        """Test conversion to LLM message - failure"""
        result = ToolExecutionResult(
            tool_call_id="tc_456",
            name="error_tool",
            success=False,
            result=None,
            error="Tool failed",
        )
        msg = result.to_llm_message()

        assert msg["role"] == "tool"
        assert "Error: Tool failed" in msg["content"]

    def test_to_llm_message_string_result(self):
        """Test conversion to LLM message - string result"""
        result = ToolExecutionResult(
            tool_call_id="tc_789",
            name="simple_tool",
            success=True,
            result="Simple string result",
        )
        msg = result.to_llm_message()

        assert msg["content"] == "Simple string result"


# =============================================================================
# Test ToolHandlerConfig
# =============================================================================


class TestToolHandlerConfig:
    """Test ToolHandlerConfig dataclass"""

    def test_default_values(self):
        """Test default configuration"""
        config = ToolHandlerConfig()
        assert config.max_parallel_calls == 5
        assert config.default_timeout == 30.0
        assert config.max_tool_rounds == 10
        assert config.default_permission == ToolPermission.AUTO
        assert config.enable_mcp is True

    def test_custom_values(self):
        """Test custom configuration"""
        config = ToolHandlerConfig(
            max_parallel_calls=10,
            blocked_tools={"tool1", "tool2"},
            require_approval_tools={"sensitive"},
        )
        assert config.max_parallel_calls == 10
        assert "tool1" in config.blocked_tools
        assert "sensitive" in config.require_approval_tools


# =============================================================================
# Test ToolHandlerStats
# =============================================================================


class TestToolHandlerStats:
    """Test ToolHandlerStats dataclass"""

    def test_initial_stats(self):
        """Test initial statistics"""
        stats = ToolHandlerStats()
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
        assert stats.success_rate == 0.0

    def test_record_successful_call(self):
        """Test recording successful call"""
        stats = ToolHandlerStats()
        stats.record_call("calculator", True, 15.0)

        assert stats.total_calls == 1
        assert stats.successful_calls == 1
        assert stats.failed_calls == 0
        assert stats.success_rate == 1.0
        assert stats.average_execution_time_ms == 15.0

    def test_record_failed_call(self):
        """Test recording failed call"""
        stats = ToolHandlerStats()
        stats.record_call("error_tool", False, 5.0)

        assert stats.total_calls == 1
        assert stats.successful_calls == 0
        assert stats.failed_calls == 1
        assert stats.success_rate == 0.0

    def test_multiple_calls(self):
        """Test multiple calls statistics"""
        stats = ToolHandlerStats()
        stats.record_call("tool1", True, 10.0)
        stats.record_call("tool1", True, 20.0)
        stats.record_call("tool2", False, 5.0)

        assert stats.total_calls == 3
        assert stats.successful_calls == 2
        assert stats.failed_calls == 1
        assert stats.success_rate == pytest.approx(2/3)
        assert stats.average_execution_time_ms == pytest.approx(35.0/3)
        assert stats.calls_by_tool["tool1"] == 2
        assert stats.calls_by_tool["tool2"] == 1


# =============================================================================
# Test ToolCallParser
# =============================================================================


class TestToolCallParser:
    """Test ToolCallParser"""

    def test_parse_dict_tool_call(self):
        """Test parsing dict format tool call"""
        message = {
            "tool_calls": [
                {
                    "id": "tc_123",
                    "function": {
                        "name": "calculator",
                        "arguments": '{"x": 1, "y": 2}',
                    }
                }
            ]
        }
        result = ToolCallParser.parse_from_message(message)

        assert len(result) == 1
        assert result[0].id == "tc_123"
        assert result[0].name == "calculator"
        assert result[0].arguments == {"x": 1, "y": 2}

    def test_parse_multiple_tool_calls(self):
        """Test parsing multiple tool calls"""
        message = {
            "tool_calls": [
                {"id": "tc_1", "function": {"name": "tool1", "arguments": "{}"}},
                {"id": "tc_2", "function": {"name": "tool2", "arguments": "{}"}},
            ]
        }
        result = ToolCallParser.parse_from_message(message)

        assert len(result) == 2
        assert result[0].name == "tool1"
        assert result[1].name == "tool2"

    def test_parse_mcp_tool_prefix_format(self):
        """Test parsing MCP tool with prefix format"""
        message = {
            "tool_calls": [
                {
                    "id": "tc_mcp",
                    "function": {
                        "name": "mcp_azure_list_vms",
                        "arguments": '{"rg": "prod"}',
                    }
                }
            ]
        }
        result = ToolCallParser.parse_from_message(
            message,
            mcp_servers=["azure", "github"],
            mcp_tool_prefix="mcp_",
        )

        assert len(result) == 1
        assert result[0].source == ToolSource.MCP
        assert result[0].server_name == "azure"

    def test_parse_mcp_tool_colon_format(self):
        """Test parsing MCP tool with colon format"""
        message = {
            "tool_calls": [
                {
                    "id": "tc_mcp",
                    "function": {
                        "name": "github:create_issue",
                        "arguments": '{"title": "Bug"}',
                    }
                }
            ]
        }
        result = ToolCallParser.parse_from_message(
            message,
            mcp_servers=["azure", "github"],
        )

        assert len(result) == 1
        assert result[0].source == ToolSource.MCP
        assert result[0].server_name == "github"

    def test_parse_empty_tool_calls(self):
        """Test parsing empty tool calls"""
        message = {"tool_calls": []}
        result = ToolCallParser.parse_from_message(message)
        assert len(result) == 0

    def test_parse_no_tool_calls(self):
        """Test parsing message without tool calls"""
        message = {"role": "assistant", "content": "Hello"}
        result = ToolCallParser.parse_from_message(message)
        assert len(result) == 0

    def test_parse_invalid_json_arguments(self):
        """Test parsing with invalid JSON arguments"""
        message = {
            "tool_calls": [
                {
                    "id": "tc_invalid",
                    "function": {
                        "name": "tool",
                        "arguments": "not valid json",
                    }
                }
            ]
        }
        result = ToolCallParser.parse_from_message(message)

        assert len(result) == 1
        assert result[0].arguments == {}  # Falls back to empty dict

    def test_parse_simple_dict_format(self):
        """Test parsing simplified dict format (no function wrapper)"""
        message = {
            "tool_calls": [
                {
                    "id": "tc_simple",
                    "name": "simple_tool",
                    "arguments": {"key": "value"},
                }
            ]
        }
        result = ToolCallParser.parse_from_message(message)

        assert len(result) == 1
        assert result[0].name == "simple_tool"
        assert result[0].arguments == {"key": "value"}


# =============================================================================
# Test ToolCallHandler - Initialization
# =============================================================================


class TestToolCallHandlerInit:
    """Test ToolCallHandler initialization"""

    def test_basic_init(self):
        """Test basic initialization"""
        handler = ToolCallHandler()
        assert handler.tool_registry is None
        assert handler.mcp_client is None
        assert handler.config is not None
        assert handler.approval_callback is None

    def test_init_with_registry(self, mock_tool_registry):
        """Test initialization with tool registry"""
        handler = ToolCallHandler(tool_registry=mock_tool_registry)
        assert handler.tool_registry is mock_tool_registry

    def test_init_with_mcp_client(self, mock_mcp_client):
        """Test initialization with MCP client"""
        handler = ToolCallHandler(mcp_client=mock_mcp_client)
        assert handler.mcp_client is mock_mcp_client

    def test_init_with_config(self, handler_config):
        """Test initialization with custom config"""
        handler = ToolCallHandler(config=handler_config)
        assert handler.config.max_parallel_calls == 3

    def test_init_stats(self, tool_handler):
        """Test initial statistics"""
        assert tool_handler.stats.total_calls == 0


# =============================================================================
# Test ToolCallHandler - Permission Checking
# =============================================================================


class TestToolCallHandlerPermission:
    """Test permission checking"""

    def test_auto_permission_default(self, tool_handler):
        """Test default auto permission"""
        permission = tool_handler._check_permission("calculator")
        assert permission == ToolPermission.AUTO

    def test_blocked_tool_denied(self, tool_handler):
        """Test blocked tool is denied"""
        permission = tool_handler._check_permission("dangerous_tool")
        assert permission == ToolPermission.DENIED

    def test_approval_required_tool(self, tool_handler):
        """Test approval required tool"""
        permission = tool_handler._check_permission("sensitive_tool")
        assert permission == ToolPermission.APPROVAL_REQUIRED

    def test_allowed_tools_whitelist(self):
        """Test allowed tools whitelist"""
        config = ToolHandlerConfig(
            allowed_tools={"tool1", "tool2"},
        )
        handler = ToolCallHandler(config=config)

        assert handler._check_permission("tool1") == ToolPermission.AUTO
        assert handler._check_permission("tool3") == ToolPermission.DENIED

    def test_is_tool_allowed(self, tool_handler):
        """Test is_tool_allowed helper"""
        assert tool_handler._is_tool_allowed("calculator") is True
        assert tool_handler._is_tool_allowed("dangerous_tool") is False


# =============================================================================
# Test ToolCallHandler - Tool Execution
# =============================================================================


class TestToolCallHandlerExecution:
    """Test tool execution"""

    @pytest.mark.asyncio
    async def test_execute_local_tool_success(self, tool_handler):
        """Test successful local tool execution"""
        tc = ParsedToolCall(
            id="tc_calc",
            name="calculator",
            arguments={"x": 5, "y": 3},
        )
        result = await tool_handler.execute_tool(tc)

        assert result.success is True
        assert result.name == "calculator"
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_local_tool_not_found(self, tool_handler):
        """Test local tool not found"""
        tc = ParsedToolCall(
            id="tc_unknown",
            name="unknown_tool",
            arguments={},
        )
        result = await tool_handler.execute_tool(tc)

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_local_tool_error(self, tool_handler):
        """Test local tool execution error"""
        tc = ParsedToolCall(
            id="tc_error",
            name="error_tool",
            arguments={},
        )
        result = await tool_handler.execute_tool(tc)

        assert result.success is False
        assert "Tool error" in result.error

    @pytest.mark.asyncio
    async def test_execute_without_registry(self):
        """Test execution without tool registry"""
        handler = ToolCallHandler()
        tc = ParsedToolCall(id="tc_1", name="tool", arguments={})
        result = await handler.execute_tool(tc)

        assert result.success is False
        assert "not available" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_success(self, tool_handler):
        """Test successful MCP tool execution"""
        tc = ParsedToolCall(
            id="tc_mcp",
            name="mcp_azure_list_vms",
            arguments={"rg": "prod"},
            source=ToolSource.MCP,
            server_name="azure",
        )
        result = await tool_handler.execute_tool(tc)

        assert result.success is True
        assert result.source == ToolSource.MCP

    @pytest.mark.asyncio
    async def test_execute_mcp_without_server_name(self, tool_handler):
        """Test MCP execution without server name"""
        tc = ParsedToolCall(
            id="tc_mcp",
            name="some_mcp_tool",
            arguments={},
            source=ToolSource.MCP,
            server_name=None,
        )
        result = await tool_handler.execute_tool(tc)

        assert result.success is False
        assert "not specified" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execution_updates_stats(self, tool_handler):
        """Test that execution updates statistics"""
        tc = ParsedToolCall(id="tc_1", name="calculator", arguments={})
        await tool_handler.execute_tool(tc)

        assert tool_handler.stats.total_calls == 1
        assert tool_handler.stats.successful_calls == 1


# =============================================================================
# Test ToolCallHandler - Handle Tool Calls
# =============================================================================


class TestToolCallHandlerHandle:
    """Test handle_tool_calls method"""

    @pytest.mark.asyncio
    async def test_handle_empty_list(self, tool_handler):
        """Test handling empty tool call list"""
        events = []
        async for event in tool_handler.handle_tool_calls([]):
            events.append(event)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_handle_single_tool_call(self, tool_handler):
        """Test handling single tool call"""
        tool_calls = [
            ParsedToolCall(id="tc_1", name="calculator", arguments={"x": 1})
        ]
        events = []
        async for event in tool_handler.handle_tool_calls(
            tool_calls, session_id="sess_1", execution_id="exec_1"
        ):
            events.append(event)

        # Should have tool_call and tool_result events
        event_types = [e.event_type for e in events]
        assert ExecutionEventType.TOOL_CALL in event_types
        assert ExecutionEventType.TOOL_RESULT in event_types

    @pytest.mark.asyncio
    async def test_handle_blocked_tool(self, tool_handler):
        """Test handling blocked tool"""
        tool_calls = [
            ParsedToolCall(id="tc_blocked", name="dangerous_tool", arguments={})
        ]
        events = []
        async for event in tool_handler.handle_tool_calls(tool_calls):
            events.append(event)

        # Should have tool_result with error
        result_events = [e for e in events if e.event_type == ExecutionEventType.TOOL_RESULT]
        assert len(result_events) == 1
        assert result_events[0].tool_result.success is False
        assert "not allowed" in result_events[0].tool_result.error_message.lower()

    @pytest.mark.asyncio
    async def test_handle_multiple_tool_calls(self, tool_handler):
        """Test handling multiple tool calls"""
        tool_calls = [
            ParsedToolCall(id="tc_1", name="calculator", arguments={}),
            ParsedToolCall(id="tc_2", name="get_weather", arguments={}),
        ]
        events = []
        async for event in tool_handler.handle_tool_calls(tool_calls):
            events.append(event)

        tool_call_events = [e for e in events if e.event_type == ExecutionEventType.TOOL_CALL]
        tool_result_events = [e for e in events if e.event_type == ExecutionEventType.TOOL_RESULT]

        assert len(tool_call_events) == 2
        assert len(tool_result_events) == 2

    @pytest.mark.asyncio
    async def test_max_rounds_exceeded(self, tool_handler):
        """Test max rounds exceeded error"""
        tool_handler._round_count = 5  # At max

        tool_calls = [ParsedToolCall(id="tc_1", name="calculator", arguments={})]
        events = []
        async for event in tool_handler.handle_tool_calls(tool_calls):
            events.append(event)

        error_events = [e for e in events if e.event_type == ExecutionEventType.ERROR]
        assert len(error_events) == 1
        assert "max" in error_events[0].error.lower()


# =============================================================================
# Test ToolCallHandler - Approval Flow
# =============================================================================


class TestToolCallHandlerApproval:
    """Test approval workflow"""

    @pytest.mark.asyncio
    async def test_approval_required_with_callback_approved(self, mock_tool_registry):
        """Test approval required - approved"""
        async def approve_callback(request_id, tool_call):
            return True

        handler = ToolCallHandler(
            tool_registry=mock_tool_registry,
            config=ToolHandlerConfig(require_approval_tools={"calculator"}),
            approval_callback=approve_callback,
        )

        tool_calls = [ParsedToolCall(id="tc_1", name="calculator", arguments={})]
        events = []
        async for event in handler.handle_tool_calls(tool_calls):
            events.append(event)

        event_types = [e.event_type for e in events]
        assert ExecutionEventType.APPROVAL_REQUIRED in event_types
        assert ExecutionEventType.APPROVAL_RESPONSE in event_types
        assert ExecutionEventType.TOOL_RESULT in event_types

        # Check approval was approved
        approval_response = next(
            e for e in events if e.event_type == ExecutionEventType.APPROVAL_RESPONSE
        )
        assert approval_response.approval_status == "approved"

    @pytest.mark.asyncio
    async def test_approval_required_with_callback_rejected(self, mock_tool_registry):
        """Test approval required - rejected"""
        async def reject_callback(request_id, tool_call):
            return False

        handler = ToolCallHandler(
            tool_registry=mock_tool_registry,
            config=ToolHandlerConfig(require_approval_tools={"calculator"}),
            approval_callback=reject_callback,
        )

        tool_calls = [ParsedToolCall(id="tc_1", name="calculator", arguments={})]
        events = []
        async for event in handler.handle_tool_calls(tool_calls):
            events.append(event)

        # Check approval was rejected
        approval_response = next(
            e for e in events if e.event_type == ExecutionEventType.APPROVAL_RESPONSE
        )
        assert approval_response.approval_status == "rejected"

        # Check tool result is failure
        tool_result = next(
            e for e in events if e.event_type == ExecutionEventType.TOOL_RESULT
        )
        assert tool_result.tool_result.success is False
        assert "rejected" in tool_result.tool_result.error_message.lower()

    @pytest.mark.asyncio
    async def test_approval_required_without_callback(self, mock_tool_registry):
        """Test approval required without callback"""
        handler = ToolCallHandler(
            tool_registry=mock_tool_registry,
            config=ToolHandlerConfig(require_approval_tools={"calculator"}),
            approval_callback=None,
        )

        tool_calls = [ParsedToolCall(id="tc_1", name="calculator", arguments={})]
        events = []
        async for event in handler.handle_tool_calls(tool_calls):
            events.append(event)

        # Should fail because no callback
        tool_result = next(
            e for e in events if e.event_type == ExecutionEventType.TOOL_RESULT
        )
        assert tool_result.tool_result.success is False
        assert "callback" in tool_result.tool_result.error_message.lower()


# =============================================================================
# Test ToolCallHandler - Utility Methods
# =============================================================================


class TestToolCallHandlerUtility:
    """Test utility methods"""

    def test_parse_tool_calls(self, tool_handler):
        """Test parse_tool_calls wrapper"""
        # Create mock response
        mock_response = MagicMock()
        mock_response.tool_calls = None

        result = tool_handler.parse_tool_calls(mock_response)
        assert result == []

    def test_get_available_tools(self, tool_handler):
        """Test get_available_tools"""
        tools = tool_handler.get_available_tools()
        assert len(tools) > 0

        # Check blocked tool is not included
        tool_names = [t["function"]["name"] for t in tools]
        assert "dangerous_tool" not in tool_names

    def test_reset_round_count(self, tool_handler):
        """Test reset_round_count"""
        tool_handler._round_count = 5
        tool_handler.reset_round_count()
        assert tool_handler._round_count == 0

    def test_results_to_messages(self, tool_handler):
        """Test results_to_messages"""
        results = [
            ToolExecutionResult(
                tool_call_id="tc_1",
                name="tool1",
                success=True,
                result={"data": 1},
            ),
            ToolExecutionResult(
                tool_call_id="tc_2",
                name="tool2",
                success=False,
                result=None,
                error="Error",
            ),
        ]
        messages = tool_handler.results_to_messages(results)

        assert len(messages) == 2
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "tc_1"
        assert messages[1]["tool_call_id"] == "tc_2"


# =============================================================================
# Test create_tool_handler Factory
# =============================================================================


class TestCreateToolHandler:
    """Test create_tool_handler factory function"""

    def test_create_default(self):
        """Test creating with defaults"""
        handler = create_tool_handler()
        assert isinstance(handler, ToolCallHandler)
        assert handler.tool_registry is None
        assert handler.mcp_client is None

    def test_create_with_all_params(self, mock_tool_registry, mock_mcp_client, handler_config):
        """Test creating with all parameters"""
        async def callback(r, t):
            return True

        handler = create_tool_handler(
            tool_registry=mock_tool_registry,
            mcp_client=mock_mcp_client,
            config=handler_config,
            approval_callback=callback,
        )

        assert handler.tool_registry is mock_tool_registry
        assert handler.mcp_client is mock_mcp_client
        assert handler.config is handler_config
        assert handler.approval_callback is callback


# =============================================================================
# Test Integration Scenarios
# =============================================================================


class TestToolHandlerIntegration:
    """Integration tests for tool handler"""

    @pytest.mark.asyncio
    async def test_full_workflow_local_tools(self, tool_handler):
        """Test full workflow with local tools"""
        # Simulate LLM response with tool calls
        message = {
            "tool_calls": [
                {"id": "tc_1", "function": {"name": "calculator", "arguments": '{"x": 5}'}},
            ]
        }

        # Parse tool calls
        parsed = ToolCallParser.parse_from_message(message)
        assert len(parsed) == 1

        # Handle tool calls
        events = []
        async for event in tool_handler.handle_tool_calls(
            parsed, session_id="sess_test", execution_id="exec_test"
        ):
            events.append(event)

        # Verify events
        assert any(e.event_type == ExecutionEventType.TOOL_CALL for e in events)
        assert any(e.event_type == ExecutionEventType.TOOL_RESULT for e in events)

        # Convert results to messages
        result_events = [e for e in events if e.event_type == ExecutionEventType.TOOL_RESULT]
        results = [
            ToolExecutionResult(
                tool_call_id=e.tool_result.tool_call_id,
                name=e.tool_result.name,
                success=e.tool_result.success,
                result=e.tool_result.result,
                error=e.tool_result.error_message,
            )
            for e in result_events
        ]
        messages = tool_handler.results_to_messages(results)

        assert len(messages) == 1
        assert messages[0]["role"] == "tool"

    @pytest.mark.asyncio
    async def test_mixed_local_and_mcp_tools(self, tool_handler):
        """Test handling mixed local and MCP tools"""
        tool_calls = [
            ParsedToolCall(id="tc_local", name="calculator", arguments={}),
            ParsedToolCall(
                id="tc_mcp",
                name="mcp_azure_list_vms",
                arguments={},
                source=ToolSource.MCP,
                server_name="azure",
            ),
        ]

        events = []
        async for event in tool_handler.handle_tool_calls(tool_calls):
            events.append(event)

        result_events = [e for e in events if e.event_type == ExecutionEventType.TOOL_RESULT]
        assert len(result_events) == 2

        # Both should succeed
        for e in result_events:
            assert e.tool_result.success is True

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel execution respects max_parallel_calls"""
        # Create slow tools
        class SlowTool:
            def __init__(self, name, delay=0.1):
                self.name = name
                self.description = f"Slow tool: {name}"
                self.parameters = {}
                self.delay = delay
                self.called = False

            async def execute(self, **kwargs):
                self.called = True
                await asyncio.sleep(self.delay)
                return MockToolResult(success=True, data="done")

        tools = {f"slow_{i}": SlowTool(f"slow_{i}", 0.05) for i in range(6)}
        registry = MockToolRegistry(tools)

        config = ToolHandlerConfig(max_parallel_calls=2)
        handler = ToolCallHandler(tool_registry=registry, config=config)

        # Create 6 tool calls
        tool_calls = [
            ParsedToolCall(id=f"tc_{i}", name=f"slow_{i}", arguments={})
            for i in range(6)
        ]

        events = []
        async for event in handler.handle_tool_calls(tool_calls):
            events.append(event)

        # All tools should have been called
        result_events = [e for e in events if e.event_type == ExecutionEventType.TOOL_RESULT]
        assert len(result_events) == 6
