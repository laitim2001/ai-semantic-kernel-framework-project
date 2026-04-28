# =============================================================================
# IPA Platform - Built-in Tools
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Built-in tools available to all agents:
#   - HttpTool: Make HTTP requests (GET, POST, PUT, DELETE)
#   - DateTimeTool: Get and format date/time values
#   - get_weather: Example function tool for weather data
#   - search_knowledge_base: Example function tool for knowledge search
#
# These tools demonstrate both class-based and function-based patterns.
# =============================================================================

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx

from src.domain.agents.tools.base import BaseTool, ToolError, ToolResult, tool

logger = logging.getLogger(__name__)


# =============================================================================
# HTTP Tool
# =============================================================================


class HttpTool(BaseTool):
    """
    HTTP request tool for making web requests.

    Supports GET, POST, PUT, DELETE methods with configurable timeout
    and error handling.

    Example:
        tool = HttpTool()
        result = await tool.execute(
            method="GET",
            url="https://api.example.com/data",
            headers={"Authorization": "Bearer token"},
        )
    """

    name = "http_request"
    description = (
        "Make HTTP requests to external APIs. "
        "Supports GET, POST, PUT, DELETE methods. "
        "Use this to fetch data from or send data to web services."
    )

    parameters = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE"],
                "description": "HTTP method to use",
            },
            "url": {
                "type": "string",
                "description": "The URL to make the request to",
            },
            "headers": {
                "type": "object",
                "description": "Optional HTTP headers",
            },
            "body": {
                "type": "object",
                "description": "Optional request body for POST/PUT",
            },
            "timeout": {
                "type": "number",
                "description": "Request timeout in seconds (default: 30)",
            },
        },
        "required": ["method", "url"],
    }

    def __init__(self, default_timeout: float = 30.0):
        """
        Initialize HttpTool.

        Args:
            default_timeout: Default request timeout in seconds
        """
        super().__init__()
        self.default_timeout = default_timeout

    async def execute(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> ToolResult:
        """
        Execute HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Request URL
            headers: Optional request headers
            body: Optional request body (for POST/PUT)
            timeout: Request timeout in seconds

        Returns:
            ToolResult with response data or error
        """
        method = method.upper()
        if method not in ("GET", "POST", "PUT", "DELETE"):
            raise ToolError(
                message=f"Unsupported HTTP method: {method}",
                tool_name=self.name,
            )

        timeout_value = timeout or self.default_timeout

        try:
            async with httpx.AsyncClient(timeout=timeout_value) as client:
                # Make request based on method
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=body)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ToolError(message=f"Unknown method: {method}", tool_name=self.name)

                # Parse response
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                }

                # Try to parse JSON response
                try:
                    response_data["body"] = response.json()
                except Exception:
                    response_data["body"] = response.text

                # Check for HTTP errors
                if response.status_code >= 400:
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text[:200]}",
                        data=response_data,
                    )

                return ToolResult(
                    success=True,
                    data=response_data,
                    metadata={
                        "url": url,
                        "method": method,
                        "status_code": response.status_code,
                    },
                )

        except httpx.TimeoutException:
            raise ToolError(
                message=f"Request timed out after {timeout_value} seconds",
                tool_name=self.name,
            )
        except httpx.ConnectError as e:
            raise ToolError(
                message=f"Connection failed: {str(e)}",
                tool_name=self.name,
                original_error=e,
            )
        except Exception as e:
            raise ToolError(
                message=f"HTTP request failed: {str(e)}",
                tool_name=self.name,
                original_error=e,
            )


# =============================================================================
# DateTime Tool
# =============================================================================


class DateTimeTool(BaseTool):
    """
    Date and time utility tool.

    Provides current time, time zone conversion, and formatting capabilities.

    Example:
        tool = DateTimeTool()
        result = await tool.execute(
            operation="now",
            timezone="Asia/Taipei",
            format="%Y-%m-%d %H:%M:%S",
        )
    """

    name = "datetime"
    description = (
        "Get current date and time, convert time zones, or format dates. "
        "Use this when you need to know the current time or work with dates."
    )

    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["now", "format", "convert"],
                "description": "Operation to perform: now (get current time), format (format a datetime), convert (convert timezone)",
            },
            "timezone": {
                "type": "string",
                "description": "Timezone name (e.g., 'Asia/Taipei', 'America/New_York', 'UTC')",
            },
            "format": {
                "type": "string",
                "description": "Date format string (e.g., '%Y-%m-%d %H:%M:%S')",
            },
            "datetime_str": {
                "type": "string",
                "description": "Datetime string for format/convert operations",
            },
            "from_timezone": {
                "type": "string",
                "description": "Source timezone for conversion",
            },
            "to_timezone": {
                "type": "string",
                "description": "Target timezone for conversion",
            },
        },
        "required": ["operation"],
    }

    # Common timezone aliases
    TIMEZONE_ALIASES = {
        "taipei": "Asia/Taipei",
        "tokyo": "Asia/Tokyo",
        "beijing": "Asia/Shanghai",
        "shanghai": "Asia/Shanghai",
        "new_york": "America/New_York",
        "los_angeles": "America/Los_Angeles",
        "london": "Europe/London",
        "paris": "Europe/Paris",
    }

    def _get_timezone(self, tz_name: Optional[str]) -> ZoneInfo:
        """Get ZoneInfo from timezone name or alias."""
        if not tz_name:
            return ZoneInfo("UTC")

        # Check aliases
        tz_lower = tz_name.lower().replace(" ", "_")
        if tz_lower in self.TIMEZONE_ALIASES:
            tz_name = self.TIMEZONE_ALIASES[tz_lower]

        try:
            return ZoneInfo(tz_name)
        except Exception:
            raise ToolError(
                message=f"Unknown timezone: {tz_name}",
                tool_name=self.name,
            )

    async def execute(
        self,
        operation: str = "now",
        timezone: Optional[str] = None,
        format: Optional[str] = None,
        datetime_str: Optional[str] = None,
        from_timezone: Optional[str] = None,
        to_timezone: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute datetime operation.

        Args:
            operation: Operation type (now, format, convert)
            timezone: Target timezone
            format: Date format string
            datetime_str: Datetime string for format/convert
            from_timezone: Source timezone for conversion
            to_timezone: Target timezone for conversion

        Returns:
            ToolResult with datetime data
        """
        try:
            if operation == "now":
                # Get current time in specified timezone
                tz = self._get_timezone(timezone)
                now = datetime.now(tz)

                date_format = format or "%Y-%m-%d %H:%M:%S %Z"
                formatted = now.strftime(date_format)

                return ToolResult(
                    success=True,
                    data={
                        "datetime": formatted,
                        "timestamp": now.timestamp(),
                        "timezone": str(tz),
                        "iso": now.isoformat(),
                    },
                )

            elif operation == "format":
                # Format a datetime string
                if not datetime_str:
                    raise ToolError(
                        message="datetime_str is required for format operation",
                        tool_name=self.name,
                    )

                # Parse input datetime
                dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))

                # Apply timezone if specified
                if timezone:
                    tz = self._get_timezone(timezone)
                    dt = dt.astimezone(tz)

                date_format = format or "%Y-%m-%d %H:%M:%S %Z"
                formatted = dt.strftime(date_format)

                return ToolResult(
                    success=True,
                    data={"formatted": formatted, "original": datetime_str},
                )

            elif operation == "convert":
                # Convert between timezones
                if not datetime_str:
                    raise ToolError(
                        message="datetime_str is required for convert operation",
                        tool_name=self.name,
                    )

                from_tz = self._get_timezone(from_timezone or "UTC")
                to_tz = self._get_timezone(to_timezone or timezone)

                # Parse and localize to source timezone
                dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=from_tz)

                # Convert to target timezone
                converted = dt.astimezone(to_tz)

                date_format = format or "%Y-%m-%d %H:%M:%S %Z"

                return ToolResult(
                    success=True,
                    data={
                        "original": datetime_str,
                        "from_timezone": str(from_tz),
                        "to_timezone": str(to_tz),
                        "converted": converted.strftime(date_format),
                        "iso": converted.isoformat(),
                    },
                )

            else:
                raise ToolError(
                    message=f"Unknown operation: {operation}. Use 'now', 'format', or 'convert'",
                    tool_name=self.name,
                )

        except ToolError:
            raise
        except Exception as e:
            raise ToolError(
                message=f"DateTime operation failed: {str(e)}",
                tool_name=self.name,
                original_error=e,
            )


# =============================================================================
# Function-based Tools (Examples)
# =============================================================================


@tool(
    name="get_weather",
    description=(
        "Get current weather conditions for a location. "
        "Returns temperature, conditions, and humidity. "
        "Note: This is a mock implementation for demonstration."
    ),
)
async def get_weather(
    location: str,
    units: str = "celsius",
) -> Dict[str, Any]:
    """
    Get weather for a location (mock implementation).

    Args:
        location: City or location name
        units: Temperature units ('celsius' or 'fahrenheit')

    Returns:
        Weather data dictionary
    """
    # Mock weather data for demonstration
    # In production, this would call a real weather API
    mock_weather = {
        "taipei": {"temp": 28, "conditions": "Partly Cloudy", "humidity": 75},
        "tokyo": {"temp": 22, "conditions": "Clear", "humidity": 60},
        "new york": {"temp": 15, "conditions": "Rainy", "humidity": 85},
        "london": {"temp": 12, "conditions": "Overcast", "humidity": 80},
        "default": {"temp": 20, "conditions": "Unknown", "humidity": 50},
    }

    location_lower = location.lower()
    weather = mock_weather.get(location_lower, mock_weather["default"])

    # Convert temperature if needed
    temp = weather["temp"]
    if units.lower() == "fahrenheit":
        temp = (temp * 9 / 5) + 32
        unit_symbol = "°F"
    else:
        unit_symbol = "°C"

    return {
        "location": location,
        "temperature": f"{temp}{unit_symbol}",
        "conditions": weather["conditions"],
        "humidity": f"{weather['humidity']}%",
        "note": "This is mock data for demonstration purposes",
    }


@tool(
    name="search_knowledge_base",
    description=(
        "Search the internal knowledge base for information. "
        "Returns relevant documents and snippets. "
        "Note: This is a mock implementation for demonstration."
    ),
)
async def search_knowledge_base(
    query: str,
    max_results: int = 5,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search knowledge base (mock implementation).

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        category: Optional category filter

    Returns:
        Search results dictionary
    """
    # Mock search results for demonstration
    # In production, this would search a real knowledge base
    mock_results = [
        {
            "id": "doc-001",
            "title": "Getting Started Guide",
            "snippet": "Welcome to the IPA Platform. This guide covers...",
            "category": "documentation",
            "relevance": 0.95,
        },
        {
            "id": "doc-002",
            "title": "API Reference",
            "snippet": "The REST API provides endpoints for...",
            "category": "technical",
            "relevance": 0.87,
        },
        {
            "id": "doc-003",
            "title": "Troubleshooting FAQ",
            "snippet": "Common issues and solutions...",
            "category": "support",
            "relevance": 0.82,
        },
    ]

    # Filter by category if specified
    if category:
        mock_results = [r for r in mock_results if r["category"] == category]

    # Limit results
    results = mock_results[:max_results]

    return {
        "query": query,
        "total_results": len(results),
        "results": results,
        "note": "This is mock data for demonstration purposes",
    }


# =============================================================================
# Additional Utility Tools
# =============================================================================


@tool(
    name="calculate",
    description=(
        "Perform basic mathematical calculations. "
        "Supports addition, subtraction, multiplication, division."
    ),
)
async def calculate(
    operation: str,
    a: float,
    b: float,
) -> Dict[str, Any]:
    """
    Perform basic calculations.

    Args:
        operation: Operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number

    Returns:
        Calculation result
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else float("inf"),
    }

    op = operation.lower()
    if op not in operations:
        raise ValueError(f"Unknown operation: {operation}. Use: add, subtract, multiply, divide")

    result = operations[op](a, b)

    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
        "expression": f"{a} {op} {b} = {result}",
    }
