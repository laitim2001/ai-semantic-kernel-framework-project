# =============================================================================
# IPA Platform - Tools Framework Unit Tests
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Tests for the tool framework including:
#   - ToolResult data class
#   - ToolError exception class
#   - BaseTool abstract class
#   - FunctionTool wrapper
#   - @tool decorator
#   - Built-in tools (HttpTool, DateTimeTool, etc.)
#   - ToolRegistry management
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.agents.tools import (
    BaseTool,
    DateTimeTool,
    FunctionTool,
    HttpTool,
    ToolError,
    ToolRegistry,
    ToolResult,
    calculate,
    get_tool_registry,
    get_weather,
    reset_tool_registry,
    search_knowledge_base,
    tool,
)


# =============================================================================
# ToolResult Tests
# =============================================================================


class TestToolResult:
    """Tests for ToolResult data class."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = ToolResult(success=True, data={"key": "value"})

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata == {}

    def test_error_result(self):
        """Test creating an error result."""
        result = ToolResult(
            success=False,
            error="Something went wrong",
            metadata={"tool_name": "test_tool"},
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.metadata["tool_name"] == "test_tool"

    def test_to_dict(self):
        """Test result serialization to dict."""
        result = ToolResult(
            success=True,
            data="test data",
            metadata={"key": "value"},
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["data"] == "test data"
        assert d["error"] is None
        assert d["metadata"]["key"] == "value"

    def test_str_success(self):
        """Test string representation of success result."""
        result = ToolResult(success=True, data={"temperature": 25})

        s = str(result)
        assert "temperature" in s
        assert "25" in s

    def test_str_error(self):
        """Test string representation of error result."""
        result = ToolResult(success=False, error="Connection failed")

        s = str(result)
        assert "Error" in s
        assert "Connection failed" in s

    def test_str_success_no_data(self):
        """Test string representation with no data."""
        result = ToolResult(success=True)

        s = str(result)
        assert s == "Success"


# =============================================================================
# ToolError Tests
# =============================================================================


class TestToolError:
    """Tests for ToolError exception class."""

    def test_basic_error(self):
        """Test creating basic error."""
        error = ToolError(message="Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.tool_name is None
        assert error.original_error is None

    def test_error_with_tool_name(self):
        """Test error with tool name."""
        error = ToolError(message="Failed", tool_name="http_tool")

        assert error.tool_name == "http_tool"

    def test_error_with_original_exception(self):
        """Test error wrapping original exception."""
        original = ValueError("Original error")
        error = ToolError(
            message="Wrapped error",
            tool_name="test_tool",
            original_error=original,
        )

        assert error.original_error is original

    def test_to_result(self):
        """Test converting error to ToolResult."""
        error = ToolError(
            message="Test failure",
            tool_name="test_tool",
            original_error=ValueError("cause"),
        )

        result = error.to_result()

        assert result.success is False
        assert result.error == "Test failure"
        assert result.metadata["tool_name"] == "test_tool"
        assert result.metadata["original_error"] == "cause"


# =============================================================================
# BaseTool Tests
# =============================================================================


class TestBaseTool:
    """Tests for BaseTool abstract class."""

    def test_tool_requires_name(self):
        """Test that tool requires name."""

        class NoNameTool(BaseTool):
            description = "Test"

            async def execute(self, **kwargs):
                return ToolResult(success=True)

        with pytest.raises(ValueError, match="must define 'name'"):
            NoNameTool()

    def test_tool_requires_description(self):
        """Test that tool requires description."""

        class NoDescTool(BaseTool):
            name = "test"

            async def execute(self, **kwargs):
                return ToolResult(success=True)

        with pytest.raises(ValueError, match="must define 'description'"):
            NoDescTool()

    def test_valid_tool_creation(self):
        """Test creating a valid tool."""

        class ValidTool(BaseTool):
            name = "valid_tool"
            description = "A valid tool"

            async def execute(self, **kwargs):
                return ToolResult(success=True, data="done")

        tool = ValidTool()

        assert tool.name == "valid_tool"
        assert tool.description == "A valid tool"

    @pytest.mark.asyncio
    async def test_tool_call(self):
        """Test calling a tool directly."""

        class TestTool(BaseTool):
            name = "test"
            description = "Test tool"

            async def execute(self, value: str = "default"):
                return ToolResult(success=True, data=value)

        tool = TestTool()
        result = await tool(value="hello")

        assert result.success is True
        assert result.data == "hello"

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test that __call__ catches ToolError."""

        class FailingTool(BaseTool):
            name = "failing"
            description = "Always fails"

            async def execute(self, **kwargs):
                raise ToolError(message="Intentional failure", tool_name=self.name)

        tool = FailingTool()
        result = await tool()

        assert result.success is False
        assert "Intentional failure" in result.error

    @pytest.mark.asyncio
    async def test_tool_unexpected_error_handling(self):
        """Test that __call__ catches unexpected exceptions."""

        class BrokenTool(BaseTool):
            name = "broken"
            description = "Throws unexpected error"

            async def execute(self, **kwargs):
                raise RuntimeError("Unexpected!")

        tool = BrokenTool()
        result = await tool()

        assert result.success is False
        assert "Unexpected!" in result.error

    def test_as_function(self):
        """Test converting tool to callable function."""

        class TestTool(BaseTool):
            name = "test_func"
            description = "Test function tool"

            async def execute(self, **kwargs):
                return ToolResult(success=True, data="result")

        tool = TestTool()
        func = tool.as_function()

        assert callable(func)
        assert func.__name__ == "test_func"
        assert func.__doc__ == "Test function tool"

    def test_get_schema_manual(self):
        """Test getting manually defined schema."""

        class SchemaToolManual(BaseTool):
            name = "schema_manual"
            description = "Manual schema"
            parameters = {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            }

            async def execute(self, x: int):
                return ToolResult(success=True, data=x)

        tool = SchemaToolManual()
        schema = tool.get_schema()

        assert schema["type"] == "object"
        assert "x" in schema["properties"]
        assert schema["required"] == ["x"]

    def test_get_schema_auto(self):
        """Test auto-generated schema from signature."""

        class SchemaToolAuto(BaseTool):
            name = "schema_auto"
            description = "Auto schema"

            async def execute(self, name: str, count: int, active: bool = True):
                return ToolResult(success=True)

        tool = SchemaToolAuto()
        schema = tool.get_schema()

        assert "name" in schema["properties"]
        assert "count" in schema["properties"]
        assert "active" in schema["properties"]
        assert "name" in schema["required"]
        assert "count" in schema["required"]
        assert "active" not in schema["required"]

    def test_repr(self):
        """Test string representation."""

        class ReprTool(BaseTool):
            name = "repr_test"
            description = "Test repr"

            async def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = ReprTool()

        assert "ReprTool" in repr(tool)
        assert "repr_test" in repr(tool)


# =============================================================================
# FunctionTool Tests
# =============================================================================


class TestFunctionTool:
    """Tests for FunctionTool wrapper."""

    @pytest.mark.asyncio
    async def test_wrap_async_function(self):
        """Test wrapping an async function."""

        async def async_func(x: int) -> int:
            return x * 2

        tool = FunctionTool(
            func=async_func,
            name="doubler",
            description="Double a number",
        )

        result = await tool(x=5)

        assert result.success is True
        assert result.data == 10

    @pytest.mark.asyncio
    async def test_wrap_sync_function(self):
        """Test wrapping a sync function."""

        def sync_func(name: str) -> str:
            return f"Hello, {name}!"

        tool = FunctionTool(
            func=sync_func,
            name="greeter",
            description="Greet someone",
        )

        result = await tool(name="World")

        assert result.success is True
        assert result.data == "Hello, World!"

    @pytest.mark.asyncio
    async def test_function_returning_tool_result(self):
        """Test function that returns ToolResult directly."""

        async def result_func() -> ToolResult:
            return ToolResult(success=True, data="direct result")

        tool = FunctionTool(
            func=result_func,
            name="direct",
            description="Returns ToolResult",
        )

        result = await tool()

        assert result.success is True
        assert result.data == "direct result"

    @pytest.mark.asyncio
    async def test_function_error_handling(self):
        """Test error handling in wrapped function."""

        def failing_func():
            raise ValueError("Function failed!")

        tool = FunctionTool(
            func=failing_func,
            name="failing",
            description="Always fails",
        )

        # The FunctionTool.execute raises ToolError, but __call__ catches it
        result = await tool()

        assert result.success is False
        assert "Function failed!" in result.error


# =============================================================================
# @tool Decorator Tests
# =============================================================================


class TestToolDecorator:
    """Tests for @tool decorator."""

    def test_decorator_creates_function_tool(self):
        """Test that decorator creates FunctionTool."""

        @tool(name="decorated", description="Decorated function")
        async def my_func(x: int) -> int:
            return x + 1

        assert isinstance(my_func, FunctionTool)
        assert my_func.name == "decorated"
        assert my_func.description == "Decorated function"

    @pytest.mark.asyncio
    async def test_decorated_function_execution(self):
        """Test executing decorated function."""

        @tool(name="adder", description="Add two numbers")
        async def add(a: int, b: int) -> int:
            return a + b

        result = await add(a=3, b=4)

        assert result.success is True
        assert result.data == 7

    def test_decorator_with_parameters(self):
        """Test decorator with custom parameters schema."""

        @tool(
            name="custom",
            description="Custom params",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "number"}},
            },
        )
        async def custom_func(value: float):
            return value * 2

        assert custom_func.parameters["type"] == "object"


# =============================================================================
# HttpTool Tests
# =============================================================================


class TestHttpTool:
    """Tests for HttpTool."""

    def test_http_tool_attributes(self):
        """Test HttpTool has correct attributes."""
        tool = HttpTool()

        assert tool.name == "http_request"
        assert "HTTP" in tool.description
        assert tool.default_timeout == 30.0

    def test_custom_timeout(self):
        """Test HttpTool with custom timeout."""
        tool = HttpTool(default_timeout=60.0)

        assert tool.default_timeout == 60.0

    @pytest.mark.asyncio
    async def test_invalid_method(self):
        """Test error for invalid HTTP method."""
        tool = HttpTool()

        with pytest.raises(ToolError, match="Unsupported HTTP method"):
            await tool.execute(method="PATCH", url="https://example.com")

    @pytest.mark.asyncio
    async def test_get_request(self):
        """Test GET request execution."""
        tool = HttpTool()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"data": "test"}
            mock_response.text = '{"data": "test"}'

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(method="GET", url="https://api.example.com/data")

            assert result.success is True
            assert result.data["status_code"] == 200
            assert result.data["body"]["data"] == "test"

    @pytest.mark.asyncio
    async def test_post_request(self):
        """Test POST request execution."""
        tool = HttpTool()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.headers = {}
            mock_response.json.return_value = {"id": 123}
            mock_response.text = '{"id": 123}'

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(
                method="POST",
                url="https://api.example.com/items",
                body={"name": "test"},
            )

            assert result.success is True
            assert result.data["status_code"] == 201

    @pytest.mark.asyncio
    async def test_http_error_response(self):
        """Test handling HTTP error response."""
        tool = HttpTool()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.headers = {}
            mock_response.json.side_effect = Exception("Not JSON")
            mock_response.text = "Not Found"

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(method="GET", url="https://api.example.com/missing")

            assert result.success is False
            assert "404" in result.error


# =============================================================================
# DateTimeTool Tests
# =============================================================================


class TestDateTimeTool:
    """Tests for DateTimeTool."""

    def test_datetime_tool_attributes(self):
        """Test DateTimeTool has correct attributes."""
        tool = DateTimeTool()

        assert tool.name == "datetime"
        assert "date" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_now_operation(self):
        """Test getting current time."""
        tool = DateTimeTool()

        result = await tool.execute(operation="now")

        assert result.success is True
        assert "datetime" in result.data
        assert "timestamp" in result.data
        assert "timezone" in result.data

    @pytest.mark.asyncio
    async def test_now_with_timezone(self):
        """Test getting current time in specific timezone."""
        tool = DateTimeTool()

        result = await tool.execute(operation="now", timezone="Asia/Taipei")

        assert result.success is True
        assert "Asia/Taipei" in result.data["timezone"]

    @pytest.mark.asyncio
    async def test_timezone_alias(self):
        """Test timezone alias resolution."""
        tool = DateTimeTool()

        result = await tool.execute(operation="now", timezone="taipei")

        assert result.success is True
        assert "Asia/Taipei" in result.data["timezone"]

    @pytest.mark.asyncio
    async def test_format_operation(self):
        """Test formatting a datetime string."""
        tool = DateTimeTool()

        result = await tool.execute(
            operation="format",
            datetime_str="2024-01-15T10:30:00+00:00",
            format="%Y/%m/%d",
        )

        assert result.success is True
        assert result.data["formatted"] == "2024/01/15"

    @pytest.mark.asyncio
    async def test_convert_operation(self):
        """Test timezone conversion."""
        tool = DateTimeTool()

        result = await tool.execute(
            operation="convert",
            datetime_str="2024-01-15T10:00:00",
            from_timezone="UTC",
            to_timezone="Asia/Taipei",
        )

        assert result.success is True
        assert "Asia/Taipei" in result.data["to_timezone"]

    @pytest.mark.asyncio
    async def test_invalid_operation(self):
        """Test error for invalid operation."""
        tool = DateTimeTool()

        with pytest.raises(ToolError, match="Unknown operation"):
            await tool.execute(operation="invalid")

    @pytest.mark.asyncio
    async def test_format_missing_datetime_str(self):
        """Test error when datetime_str missing for format."""
        tool = DateTimeTool()

        with pytest.raises(ToolError, match="datetime_str is required"):
            await tool.execute(operation="format")

    @pytest.mark.asyncio
    async def test_invalid_timezone(self):
        """Test error for invalid timezone."""
        tool = DateTimeTool()

        with pytest.raises(ToolError, match="Unknown timezone"):
            await tool.execute(operation="now", timezone="Invalid/Zone")


# =============================================================================
# Function Tools Tests
# =============================================================================


class TestFunctionTools:
    """Tests for built-in function tools."""

    @pytest.mark.asyncio
    async def test_get_weather(self):
        """Test get_weather function tool."""
        result = await get_weather(location="taipei")

        assert result.success is True
        assert "location" in result.data
        assert "temperature" in result.data
        assert "conditions" in result.data

    @pytest.mark.asyncio
    async def test_get_weather_fahrenheit(self):
        """Test get_weather with fahrenheit."""
        result = await get_weather(location="tokyo", units="fahrenheit")

        assert result.success is True
        assert "°F" in result.data["temperature"]

    @pytest.mark.asyncio
    async def test_get_weather_unknown_location(self):
        """Test get_weather with unknown location."""
        result = await get_weather(location="unknown_city")

        assert result.success is True
        assert result.data["conditions"] == "Unknown"

    @pytest.mark.asyncio
    async def test_search_knowledge_base(self):
        """Test search_knowledge_base function tool."""
        result = await search_knowledge_base(query="getting started")

        assert result.success is True
        assert "results" in result.data
        assert len(result.data["results"]) > 0

    @pytest.mark.asyncio
    async def test_search_knowledge_base_with_limit(self):
        """Test search_knowledge_base with max_results."""
        result = await search_knowledge_base(query="test", max_results=1)

        assert result.success is True
        assert len(result.data["results"]) <= 1

    @pytest.mark.asyncio
    async def test_search_knowledge_base_with_category(self):
        """Test search_knowledge_base with category filter."""
        result = await search_knowledge_base(query="test", category="technical")

        assert result.success is True
        for r in result.data["results"]:
            assert r["category"] == "technical"

    @pytest.mark.asyncio
    async def test_calculate_add(self):
        """Test calculate add operation."""
        result = await calculate(operation="add", a=5, b=3)

        assert result.success is True
        assert result.data["result"] == 8

    @pytest.mark.asyncio
    async def test_calculate_subtract(self):
        """Test calculate subtract operation."""
        result = await calculate(operation="subtract", a=10, b=4)

        assert result.success is True
        assert result.data["result"] == 6

    @pytest.mark.asyncio
    async def test_calculate_multiply(self):
        """Test calculate multiply operation."""
        result = await calculate(operation="multiply", a=6, b=7)

        assert result.success is True
        assert result.data["result"] == 42

    @pytest.mark.asyncio
    async def test_calculate_divide(self):
        """Test calculate divide operation."""
        result = await calculate(operation="divide", a=15, b=3)

        assert result.success is True
        assert result.data["result"] == 5.0

    @pytest.mark.asyncio
    async def test_calculate_divide_by_zero(self):
        """Test calculate divide by zero returns infinity."""
        result = await calculate(operation="divide", a=10, b=0)

        assert result.success is True
        assert result.data["result"] == float("inf")


# =============================================================================
# ToolRegistry Tests
# =============================================================================


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_registry_creation(self):
        """Test creating empty registry."""
        registry = ToolRegistry()

        assert registry.count() == 0
        assert len(registry) == 0

    def test_register_tool_instance(self):
        """Test registering a tool instance."""
        registry = ToolRegistry()
        tool = HttpTool()

        registry.register(tool)

        assert registry.has("http_request")
        assert registry.get("http_request") is tool

    def test_register_callable(self):
        """Test registering a callable function."""
        registry = ToolRegistry()

        async def my_func():
            return "result"

        registry.register(my_func, name="my_tool", description="My tool")

        assert registry.has("my_tool")

    def test_register_duplicate_raises(self):
        """Test that registering duplicate name raises error."""
        registry = ToolRegistry()
        registry.register(HttpTool())

        with pytest.raises(ValueError, match="already registered"):
            registry.register(HttpTool())

    def test_register_invalid_type_raises(self):
        """Test that registering invalid type raises error."""
        registry = ToolRegistry()

        with pytest.raises(TypeError, match="Expected BaseTool"):
            registry.register("not a tool")

    def test_register_class(self):
        """Test registering a tool class."""
        registry = ToolRegistry()

        registry.register_class(DateTimeTool)

        assert registry.has("datetime")

    def test_unregister(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        registry.register(HttpTool())

        result = registry.unregister("http_request")

        assert result is True
        assert not registry.has("http_request")

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent tool."""
        registry = ToolRegistry()

        result = registry.unregister("nonexistent")

        assert result is False

    def test_get_nonexistent(self):
        """Test getting nonexistent tool returns None."""
        registry = ToolRegistry()

        tool = registry.get("nonexistent")

        assert tool is None

    def test_get_required(self):
        """Test get_required returns tool."""
        registry = ToolRegistry()
        registry.register(HttpTool())

        tool = registry.get_required("http_request")

        assert tool.name == "http_request"

    def test_get_required_raises(self):
        """Test get_required raises for missing tool."""
        registry = ToolRegistry()

        with pytest.raises(ToolError, match="not found"):
            registry.get_required("missing")

    def test_get_all(self):
        """Test getting all tools."""
        registry = ToolRegistry()
        registry.register(HttpTool())
        registry.register(DateTimeTool())

        all_tools = registry.get_all()

        assert len(all_tools) == 2
        assert "http_request" in all_tools
        assert "datetime" in all_tools

    def test_get_names(self):
        """Test getting all tool names."""
        registry = ToolRegistry()
        registry.register(HttpTool())
        registry.register(DateTimeTool())

        names = registry.get_names()

        assert "http_request" in names
        assert "datetime" in names

    def test_get_functions(self):
        """Test getting tools as functions."""
        registry = ToolRegistry()
        registry.register(HttpTool())

        functions = registry.get_functions()

        assert len(functions) == 1
        assert callable(functions[0])

    def test_get_schemas(self):
        """Test getting all tool schemas."""
        registry = ToolRegistry()
        registry.register(HttpTool())

        schemas = registry.get_schemas()

        assert "http_request" in schemas
        assert "type" in schemas["http_request"]

    def test_contains(self):
        """Test 'in' operator."""
        registry = ToolRegistry()
        registry.register(HttpTool())

        assert "http_request" in registry
        assert "nonexistent" not in registry

    def test_clear(self):
        """Test clearing registry."""
        registry = ToolRegistry()
        registry.register(HttpTool())
        registry.register(DateTimeTool())

        registry.clear()

        assert registry.count() == 0

    def test_load_builtins(self):
        """Test loading built-in tools."""
        registry = ToolRegistry()

        registry.load_builtins()

        assert registry.has("http_request")
        assert registry.has("datetime")
        assert registry.has("get_weather")
        assert registry.has("search_knowledge_base")
        assert registry.has("calculate")
        assert registry.count() == 5

    def test_get_tool_info(self):
        """Test getting tool information."""
        registry = ToolRegistry()
        registry.register(HttpTool())

        info = registry.get_tool_info("http_request")

        assert info["name"] == "http_request"
        assert "HTTP" in info["description"]
        assert "parameters" in info
        assert info["class"] == "HttpTool"

    def test_get_tool_info_nonexistent(self):
        """Test getting info for nonexistent tool."""
        registry = ToolRegistry()

        info = registry.get_tool_info("nonexistent")

        assert info is None

    def test_get_all_info(self):
        """Test getting all tool info."""
        registry = ToolRegistry()
        registry.register(HttpTool())
        registry.register(DateTimeTool())

        all_info = registry.get_all_info()

        assert len(all_info) == 2
        names = [i["name"] for i in all_info]
        assert "http_request" in names
        assert "datetime" in names

    def test_repr(self):
        """Test registry repr."""
        registry = ToolRegistry()
        registry.register(HttpTool())

        r = repr(registry)

        assert "ToolRegistry" in r
        assert "http_request" in r


# =============================================================================
# Global Registry Tests
# =============================================================================


class TestGlobalRegistry:
    """Tests for global registry singleton."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_tool_registry()

    def teardown_method(self):
        """Reset registry after each test."""
        reset_tool_registry()

    def test_get_tool_registry_singleton(self):
        """Test that get_tool_registry returns singleton."""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()

        assert registry1 is registry2

    def test_registry_has_builtins(self):
        """Test that singleton has built-in tools loaded."""
        registry = get_tool_registry()

        assert registry.has("http_request")
        assert registry.has("datetime")
        assert registry.has("get_weather")

    def test_reset_clears_singleton(self):
        """Test that reset clears the singleton."""
        registry1 = get_tool_registry()
        reset_tool_registry()
        registry2 = get_tool_registry()

        assert registry1 is not registry2
