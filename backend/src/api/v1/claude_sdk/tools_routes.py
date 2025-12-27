"""Claude SDK Tools API routes.

Sprint 51: S51-1 Tools API Routes (8 pts)
Provides REST API endpoints for tool management and execution.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.integrations.claude_sdk.tools.registry import (
    get_available_tools,
    get_tool_instance,
    execute_tool,
    get_tool_definitions,
)


# --- Schemas ---


class ToolParameter(BaseModel):
    """Schema for tool parameter definition."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, integer, boolean, etc.)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(True, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value if not required")


class ToolInfo(BaseModel):
    """Schema for tool information."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    category: Optional[str] = Field(None, description="Tool category")
    requires_approval: bool = Field(False, description="Whether tool requires approval")
    enabled: bool = Field(True, description="Whether tool is enabled")


class ToolListResponse(BaseModel):
    """Response schema for listing tools."""

    tools: List[ToolInfo]
    total: int


class ToolExecuteRequest(BaseModel):
    """Request schema for tool execution."""

    tool_name: str = Field(..., description="Name of tool to execute", min_length=1)
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    working_directory: Optional[str] = Field(None, description="Working directory for execution")
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds", ge=1, le=300)
    require_approval: bool = Field(False, description="Whether to require approval before execution")


class ToolExecuteResponse(BaseModel):
    """Response schema for tool execution."""

    tool_name: str
    success: bool
    content: str
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ToolValidateRequest(BaseModel):
    """Request schema for tool parameter validation."""

    tool_name: str = Field(..., description="Name of tool to validate", min_length=1)
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to validate")


class ToolValidationError(BaseModel):
    """Schema for a single validation error."""

    parameter: str = Field(..., description="Parameter with error")
    error: str = Field(..., description="Error description")


class ToolValidateResponse(BaseModel):
    """Response schema for tool validation."""

    tool_name: str
    valid: bool
    errors: List[ToolValidationError] = Field(default_factory=list)


# --- Router ---


router = APIRouter(prefix="/tools", tags=["Claude SDK Tools"])


# --- Endpoints ---


@router.get("", response_model=ToolListResponse)
async def list_tools(
    category: Optional[str] = None,
    include_disabled: bool = False,
):
    """
    List all available tools.

    Returns a list of all registered tools with their metadata.
    Optionally filter by category or include disabled tools.
    """
    tool_names = get_available_tools()
    tools: List[ToolInfo] = []

    for name in tool_names:
        tool = get_tool_instance(name)
        if tool is None:
            continue

        # Get schema for parameters
        schema = tool.get_schema()
        parameters: List[ToolParameter] = []

        if "properties" in schema:
            required_params = schema.get("required", [])
            for param_name, param_info in schema["properties"].items():
                parameters.append(
                    ToolParameter(
                        name=param_name,
                        type=param_info.get("type", "string"),
                        description=param_info.get("description", ""),
                        required=param_name in required_params,
                        default=param_info.get("default"),
                    )
                )

        # Determine category from tool name
        tool_category = _get_tool_category(name)

        # Filter by category if specified
        if category and tool_category != category:
            continue

        tool_info = ToolInfo(
            name=tool.name,
            description=tool.description,
            parameters=parameters,
            category=tool_category,
            requires_approval=_tool_requires_approval(name),
            enabled=True,
        )
        tools.append(tool_info)

    return ToolListResponse(tools=tools, total=len(tools))


@router.get("/{name}", response_model=ToolInfo)
async def get_tool(name: str):
    """
    Get detailed information about a specific tool.

    Returns tool metadata, parameters, and configuration.
    """
    tool = get_tool_instance(name)

    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{name}' not found",
        )

    # Get schema for parameters
    schema = tool.get_schema()
    parameters: List[ToolParameter] = []

    if "properties" in schema:
        required_params = schema.get("required", [])
        for param_name, param_info in schema["properties"].items():
            parameters.append(
                ToolParameter(
                    name=param_name,
                    type=param_info.get("type", "string"),
                    description=param_info.get("description", ""),
                    required=param_name in required_params,
                    default=param_info.get("default"),
                )
            )

    return ToolInfo(
        name=tool.name,
        description=tool.description,
        parameters=parameters,
        category=_get_tool_category(name),
        requires_approval=_tool_requires_approval(name),
        enabled=True,
    )


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool_endpoint(request: ToolExecuteRequest):
    """
    Execute a tool with the provided arguments.

    The tool will be executed with the specified arguments.
    If require_approval is True, the execution may be pending approval.
    """
    import time

    # Verify tool exists
    tool = get_tool_instance(request.tool_name)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{request.tool_name}' not found",
        )

    # Check if tool requires approval and approval is needed
    if request.require_approval and _tool_requires_approval(request.tool_name):
        return ToolExecuteResponse(
            tool_name=request.tool_name,
            success=False,
            content="",
            error="Tool requires approval before execution",
        )

    # Execute tool
    start_time = time.time()
    try:
        result = await execute_tool(
            tool_name=request.tool_name,
            args=request.arguments,
            working_directory=request.working_directory,
        )
        execution_time = time.time() - start_time

        # Parse result for success/error
        if result.startswith("Error:"):
            return ToolExecuteResponse(
                tool_name=request.tool_name,
                success=False,
                content="",
                error=result,
                execution_time=execution_time,
            )

        return ToolExecuteResponse(
            tool_name=request.tool_name,
            success=True,
            content=result,
            execution_time=execution_time,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        return ToolExecuteResponse(
            tool_name=request.tool_name,
            success=False,
            content="",
            error=str(e),
            execution_time=execution_time,
        )


@router.post("/validate", response_model=ToolValidateResponse)
async def validate_tool_parameters(request: ToolValidateRequest):
    """
    Validate tool parameters without executing.

    Returns validation results indicating whether arguments are valid.
    """
    tool = get_tool_instance(request.tool_name)

    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{request.tool_name}' not found",
        )

    errors: List[ToolValidationError] = []
    schema = tool.get_schema()

    # Check required parameters
    required_params = schema.get("required", [])
    for param in required_params:
        if param not in request.arguments:
            errors.append(
                ToolValidationError(
                    parameter=param,
                    error=f"Required parameter '{param}' is missing",
                )
            )

    # Validate parameter types
    if "properties" in schema:
        for param_name, param_value in request.arguments.items():
            if param_name not in schema["properties"]:
                errors.append(
                    ToolValidationError(
                        parameter=param_name,
                        error=f"Unknown parameter '{param_name}'",
                    )
                )
                continue

            expected_type = schema["properties"][param_name].get("type", "string")
            if not _validate_type(param_value, expected_type):
                errors.append(
                    ToolValidationError(
                        parameter=param_name,
                        error=f"Expected type '{expected_type}', got '{type(param_value).__name__}'",
                    )
                )

    return ToolValidateResponse(
        tool_name=request.tool_name,
        valid=len(errors) == 0,
        errors=errors,
    )


# --- Helper Functions ---


def _get_tool_category(tool_name: str) -> str:
    """Determine tool category based on tool name."""
    file_tools = {"Read", "Write", "Edit", "MultiEdit", "Glob"}
    command_tools = {"Bash", "Grep"}
    agent_tools = {"Task"}
    web_tools = {"WebSearch", "WebFetch"}

    if tool_name in file_tools:
        return "file"
    elif tool_name in command_tools:
        return "command"
    elif tool_name in agent_tools:
        return "agent"
    elif tool_name in web_tools:
        return "web"
    else:
        return "other"


def _tool_requires_approval(tool_name: str) -> bool:
    """Determine if tool requires approval for execution."""
    # Tools that modify state typically require approval
    approval_required = {"Write", "Edit", "MultiEdit", "Bash"}
    return tool_name in approval_required


def _validate_type(value: Any, expected_type: str) -> bool:
    """Validate value matches expected JSON schema type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    expected = type_map.get(expected_type, str)
    if isinstance(expected, tuple):
        return isinstance(value, expected)
    return isinstance(value, expected)
