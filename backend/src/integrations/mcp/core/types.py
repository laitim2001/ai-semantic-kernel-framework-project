"""MCP Type Definitions.

This module defines the core types used in MCP (Model Context Protocol) communication,
following the official MCP specification.

Types:
    - ToolInputType: Enum for tool parameter types
    - ToolParameter: Definition of a tool parameter
    - ToolSchema: Complete tool definition including parameters
    - ToolResult: Result of a tool execution
    - MCPRequest: JSON-RPC 2.0 request format
    - MCPResponse: JSON-RPC 2.0 response format

Reference:
    - MCP Specification: https://modelcontextprotocol.io/
    - JSON-RPC 2.0: https://www.jsonrpc.org/specification
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ToolInputType(str, Enum):
    """Tool parameter types following JSON Schema types."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"


@dataclass
class ToolParameter:
    """Definition of a tool parameter.

    Attributes:
        name: Parameter name
        type: Parameter type
        description: Human-readable description
        required: Whether the parameter is required
        default: Default value if not provided
        enum: List of allowed values (optional)
        items: For array types, the type of items
        properties: For object types, nested properties
    """

    name: str
    type: ToolInputType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None
    items: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format.

        Returns:
            JSON Schema representation of the parameter
        """
        schema: Dict[str, Any] = {
            "type": self.type.value,
            "description": self.description,
        }

        if self.default is not None:
            schema["default"] = self.default
        if self.enum:
            schema["enum"] = self.enum
        if self.items:
            schema["items"] = self.items
        if self.properties:
            schema["properties"] = self.properties

        return schema


@dataclass
class ToolSchema:
    """MCP Tool Schema definition.

    Follows the MCP specification for tool definitions.

    Attributes:
        name: Unique tool identifier
        description: Human-readable description of what the tool does
        parameters: List of input parameters
        returns: Description of what the tool returns

    Example:
        >>> schema = ToolSchema(
        ...     name="list_vms",
        ...     description="List virtual machines in a resource group",
        ...     parameters=[
        ...         ToolParameter(
        ...             name="resource_group",
        ...             type=ToolInputType.STRING,
        ...             description="Azure resource group name",
        ...         )
        ...     ],
        ...     returns="List of VM objects with name, status, and size"
        ... )
        >>> mcp_format = schema.to_mcp_format()
    """

    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: Optional[str] = None

    def to_mcp_format(self) -> Dict[str, Any]:
        """Convert to MCP standard format.

        Returns:
            MCP-compliant tool definition
        """
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        result: Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
            },
        }

        if required:
            result["inputSchema"]["required"] = required

        return result

    @classmethod
    def from_mcp_format(cls, data: Dict[str, Any]) -> "ToolSchema":
        """Create ToolSchema from MCP format.

        Args:
            data: MCP tool definition

        Returns:
            ToolSchema instance
        """
        parameters = []
        input_schema = data.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required_params = input_schema.get("required", [])

        for name, prop in properties.items():
            param_type = prop.get("type", "string")
            try:
                type_enum = ToolInputType(param_type)
            except ValueError:
                type_enum = ToolInputType.STRING

            parameters.append(
                ToolParameter(
                    name=name,
                    type=type_enum,
                    description=prop.get("description", ""),
                    required=name in required_params,
                    default=prop.get("default"),
                    enum=prop.get("enum"),
                    items=prop.get("items"),
                    properties=prop.get("properties"),
                )
            )

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=parameters,
        )


@dataclass
class ToolResult:
    """Result of a tool execution.

    Attributes:
        success: Whether the execution was successful
        content: The result content (can be any type)
        error: Error message if execution failed
        metadata: Additional metadata about the execution
    """

    success: bool
    content: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_mcp_format(self) -> Dict[str, Any]:
        """Convert to MCP standard result format.

        Returns:
            MCP-compliant tool result
        """
        if self.success:
            # Handle different content types
            if isinstance(self.content, str):
                text_content = self.content
            elif isinstance(self.content, (dict, list)):
                import json

                text_content = json.dumps(self.content, ensure_ascii=False, indent=2)
            else:
                text_content = str(self.content)

            return {
                "content": [{"type": "text", "text": text_content}],
            }
        else:
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": self.error or "Unknown error"}
                ],
            }

    @classmethod
    def from_mcp_format(cls, data: Dict[str, Any]) -> "ToolResult":
        """Create ToolResult from MCP format.

        Args:
            data: MCP tool result

        Returns:
            ToolResult instance
        """
        is_error = data.get("isError", False)
        content_list = data.get("content", [])
        text_content = ""

        if content_list:
            first_content = content_list[0]
            if isinstance(first_content, dict):
                text_content = first_content.get("text", "")
            else:
                text_content = str(first_content)

        return cls(
            success=not is_error,
            content=text_content if not is_error else None,
            error=text_content if is_error else None,
        )


@dataclass
class MCPRequest:
    """MCP JSON-RPC 2.0 Request.

    Attributes:
        jsonrpc: JSON-RPC version (always "2.0")
        id: Request identifier
        method: Method name to invoke
        params: Method parameters
    """

    jsonrpc: str = "2.0"
    id: Union[str, int] = ""
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        result: Dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }

        if self.id:
            result["id"] = self.id
        if self.params:
            result["params"] = self.params

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create MCPRequest from dictionary.

        Args:
            data: Dictionary data

        Returns:
            MCPRequest instance
        """
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id", ""),
            method=data.get("method", ""),
            params=data.get("params", {}),
        )


@dataclass
class MCPResponse:
    """MCP JSON-RPC 2.0 Response.

    Attributes:
        jsonrpc: JSON-RPC version (always "2.0")
        id: Request identifier (matches the request)
        result: Result data (present on success)
        error: Error data (present on failure)
    """

    jsonrpc: str = "2.0"
    id: Union[str, int] = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return self.error is None

    @property
    def error_message(self) -> Optional[str]:
        """Get error message if present."""
        if self.error:
            return self.error.get("message")
        return None

    @property
    def error_code(self) -> Optional[int]:
        """Get error code if present."""
        if self.error:
            return self.error.get("code")
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        result: Dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }

        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPResponse":
        """Create MCPResponse from dictionary.

        Args:
            data: Dictionary data

        Returns:
            MCPResponse instance
        """
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id", ""),
            result=data.get("result"),
            error=data.get("error"),
        )

    @classmethod
    def create_error(
        cls,
        request_id: Union[str, int],
        code: int,
        message: str,
        data: Optional[Any] = None,
    ) -> "MCPResponse":
        """Create an error response.

        Args:
            request_id: Original request ID
            code: Error code
            message: Error message
            data: Additional error data

        Returns:
            Error response
        """
        error: Dict[str, Any] = {
            "code": code,
            "message": message,
        }
        if data is not None:
            error["data"] = data

        return cls(id=request_id, error=error)


# Standard JSON-RPC error codes
class MCPErrorCode:
    """Standard MCP/JSON-RPC error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
