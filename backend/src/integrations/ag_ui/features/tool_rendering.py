# =============================================================================
# IPA Platform - Tool Rendering Handler
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-2: Backend Tool Rendering (7 pts)
#
# Tool execution result rendering handler that provides standardized formatting
# for various result types (text, json, table, image).
#
# Key Features:
#   - Integration with UnifiedToolExecutor for tool execution
#   - Automatic result type detection
#   - Standardized result formatting for frontend consumption
#   - Support for tool execution state tracking
#
# Dependencies:
#   - UnifiedToolExecutor (src.integrations.hybrid.execution)
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

import base64
import json
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

from src.integrations.ag_ui.events import (
    AGUIEventType,
    BaseAGUIEvent,
    CustomEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    ToolCallStatus,
)

if TYPE_CHECKING:
    from src.integrations.hybrid.execution.unified_executor import (
        UnifiedToolExecutor,
        ToolExecutionResult,
        ToolSource,
    )

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Types
# =============================================================================


class ResultType(str, Enum):
    """Type of tool execution result."""

    TEXT = "text"
    JSON = "json"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    ERROR = "error"
    UNKNOWN = "unknown"


class ToolExecutionStatus(str, Enum):
    """Status of tool execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ToolCall:
    """
    Represents a tool call request.

    Attributes:
        id: Unique identifier for the tool call
        name: Tool name
        arguments: Tool arguments
        status: Current execution status
        result: Execution result (if completed)
        error: Error message (if failed)
    """

    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    status: ToolExecutionStatus = ToolExecutionStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    result_type: ResultType = ResultType.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "result_type": self.result_type.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        """Create from dictionary representation."""
        return cls(
            id=data.get("id", f"tc-{uuid.uuid4().hex[:12]}"),
            name=data.get("name", ""),
            arguments=data.get("arguments", {}),
            status=ToolExecutionStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
            result_type=ResultType(data.get("result_type", "unknown")),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FormattedResult:
    """
    Formatted tool result for frontend rendering.

    Attributes:
        data: The actual result data
        result_type: Type of the result
        formatted: Whether the data has been formatted
        display_hint: Hint for frontend display
        metadata: Additional metadata for rendering
    """

    data: Any
    result_type: ResultType
    formatted: bool = True
    display_hint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "data": self.data,
            "result_type": self.result_type.value,
            "formatted": self.formatted,
            "display_hint": self.display_hint,
            "metadata": self.metadata,
        }


@dataclass
class ToolRenderingConfig:
    """
    Configuration for tool rendering.

    Attributes:
        max_text_length: Maximum text length before truncation
        max_json_depth: Maximum JSON depth for display
        max_table_rows: Maximum rows for table display
        enable_syntax_highlighting: Whether to enable code highlighting
        image_max_size_kb: Maximum image size in KB
    """

    max_text_length: int = 10000
    max_json_depth: int = 10
    max_table_rows: int = 100
    enable_syntax_highlighting: bool = True
    image_max_size_kb: int = 5120  # 5MB


# =============================================================================
# Tool Rendering Handler
# =============================================================================


class ToolRenderingHandler:
    """
    Backend tool rendering handler.

    Provides standardized formatting for tool execution results,
    enabling consistent display across different result types.

    Key Features:
    - Automatic result type detection
    - Result formatting for frontend consumption
    - Integration with UnifiedToolExecutor
    - AG-UI event generation for tool calls

    Example:
        >>> executor = UnifiedToolExecutor(...)
        >>> handler = ToolRenderingHandler(unified_executor=executor)
        >>> tool_call = ToolCall(id="tc-1", name="Read", arguments={"file": "x.py"})
        >>> async for event in handler.execute_and_stream(tool_call, "thread-123"):
        ...     print(event)
    """

    def __init__(
        self,
        *,
        unified_executor: "UnifiedToolExecutor",
        config: Optional[ToolRenderingConfig] = None,
    ):
        """
        Initialize ToolRenderingHandler.

        Args:
            unified_executor: UnifiedToolExecutor instance for tool execution
            config: Optional rendering configuration
        """
        self._executor = unified_executor
        self._config = config or ToolRenderingConfig()

        # Result type detection patterns
        self._image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        self._code_extensions = {".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp"}

        logger.info(
            f"ToolRenderingHandler initialized: "
            f"max_text={self._config.max_text_length}, "
            f"max_table_rows={self._config.max_table_rows}"
        )

    @property
    def executor(self) -> "UnifiedToolExecutor":
        """Get the unified executor instance."""
        return self._executor

    @property
    def config(self) -> ToolRenderingConfig:
        """Get the rendering configuration."""
        return self._config

    # =========================================================================
    # Result Type Detection
    # =========================================================================

    def detect_result_type(self, result: Any, tool_name: str = "") -> ResultType:
        """
        Detect the type of tool execution result.

        Args:
            result: The tool execution result
            tool_name: Name of the tool (for context)

        Returns:
            ResultType: Detected result type
        """
        if result is None:
            return ResultType.TEXT

        # Check for error
        if isinstance(result, dict) and result.get("error"):
            return ResultType.ERROR

        # Check for image
        if isinstance(result, dict):
            if "image_url" in result or "image_data" in result:
                return ResultType.IMAGE
            if any(key in result for key in ("image", "screenshot", "visualization")):
                return ResultType.IMAGE

        # Check for table
        if isinstance(result, dict):
            if "table" in result or "rows" in result:
                return ResultType.TABLE
            if "columns" in result and "data" in result:
                return ResultType.TABLE

        if isinstance(result, list):
            # List of dicts could be table data
            if result and isinstance(result[0], dict):
                return ResultType.TABLE

        # Check for code
        if isinstance(result, dict) and "code" in result:
            return ResultType.CODE

        if isinstance(result, str):
            # Check for code patterns
            if tool_name in ("Read", "Bash", "Edit"):
                if self._looks_like_code(result):
                    return ResultType.CODE

        # Check for structured JSON
        if isinstance(result, (dict, list)):
            return ResultType.JSON

        # Default to text
        return ResultType.TEXT

    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like code."""
        code_indicators = [
            "def ",
            "class ",
            "function ",
            "import ",
            "from ",
            "const ",
            "let ",
            "var ",
            "public ",
            "private ",
            "return ",
            "if (",
            "for (",
            "while (",
        ]
        return any(indicator in text for indicator in code_indicators)

    # =========================================================================
    # Result Formatting
    # =========================================================================

    def format_result(
        self,
        result: Any,
        result_type: Optional[ResultType] = None,
        tool_name: str = "",
    ) -> FormattedResult:
        """
        Format tool result for frontend rendering.

        Args:
            result: Raw tool execution result
            result_type: Optional explicit result type
            tool_name: Name of the executed tool

        Returns:
            FormattedResult: Formatted result for frontend
        """
        detected_type = result_type or self.detect_result_type(result, tool_name)

        if detected_type == ResultType.ERROR:
            return self._format_error(result)
        elif detected_type == ResultType.IMAGE:
            return self._format_image(result)
        elif detected_type == ResultType.TABLE:
            return self._format_table(result)
        elif detected_type == ResultType.CODE:
            return self._format_code(result, tool_name)
        elif detected_type == ResultType.JSON:
            return self._format_json(result)
        else:
            return self._format_text(result)

    def _format_text(self, result: Any) -> FormattedResult:
        """Format text result."""
        text = str(result)

        # Truncate if too long
        truncated = False
        if len(text) > self._config.max_text_length:
            text = text[: self._config.max_text_length]
            truncated = True

        return FormattedResult(
            data=text,
            result_type=ResultType.TEXT,
            display_hint="text" if not truncated else "truncated-text",
            metadata={"truncated": truncated, "original_length": len(str(result))},
        )

    def _format_json(self, result: Any) -> FormattedResult:
        """Format JSON result."""
        try:
            # Ensure it's properly serializable
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result

            # Limit depth for display
            formatted = json.dumps(data, indent=2, default=str)

            return FormattedResult(
                data=data,
                result_type=ResultType.JSON,
                display_hint="json-tree",
                metadata={
                    "formatted_string": formatted,
                    "keys": list(data.keys()) if isinstance(data, dict) else None,
                },
            )
        except (json.JSONDecodeError, TypeError):
            return self._format_text(result)

    def _format_table(self, result: Any) -> FormattedResult:
        """Format table result."""
        columns: List[str] = []
        rows: List[Dict[str, Any]] = []

        if isinstance(result, dict):
            if "columns" in result and "data" in result:
                columns = result["columns"]
                rows = result["data"]
            elif "columns" in result and "rows" in result:
                columns = result["columns"]
                rows = result["rows"]
            elif "rows" in result:
                rows = result["rows"]
                if rows:
                    columns = list(rows[0].keys())
            elif "table" in result:
                table_data = result["table"]
                if isinstance(table_data, list) and table_data:
                    rows = table_data
                    columns = list(table_data[0].keys())
        elif isinstance(result, list) and result:
            rows = result
            if isinstance(result[0], dict):
                columns = list(result[0].keys())

        # Truncate rows if needed
        truncated = False
        if len(rows) > self._config.max_table_rows:
            rows = rows[: self._config.max_table_rows]
            truncated = True

        return FormattedResult(
            data={"columns": columns, "rows": rows},
            result_type=ResultType.TABLE,
            display_hint="data-table",
            metadata={
                "row_count": len(rows),
                "column_count": len(columns),
                "truncated": truncated,
            },
        )

    def _format_image(self, result: Any) -> FormattedResult:
        """Format image result."""
        image_url = None
        image_data = None
        image_type = "unknown"

        if isinstance(result, dict):
            image_url = result.get("image_url") or result.get("url")
            image_data = result.get("image_data") or result.get("data")
            image_type = result.get("type", "png")

        return FormattedResult(
            data={
                "url": image_url,
                "data": image_data,
                "type": image_type,
            },
            result_type=ResultType.IMAGE,
            display_hint="image",
            metadata={"has_url": bool(image_url), "has_data": bool(image_data)},
        )

    def _format_code(self, result: Any, tool_name: str = "") -> FormattedResult:
        """Format code result."""
        code = ""
        language = "text"

        if isinstance(result, dict) and "code" in result:
            code = result["code"]
            language = result.get("language", "text")
        elif isinstance(result, str):
            code = result
            # Guess language from tool
            if tool_name == "Read":
                language = "python"  # Default, could be smarter
            elif tool_name == "Bash":
                language = "bash"

        # Truncate if too long
        truncated = False
        original_length = len(code)
        if len(code) > self._config.max_text_length:
            code = code[: self._config.max_text_length]
            truncated = True

        return FormattedResult(
            data={
                "code": code,
                "language": language,
            },
            result_type=ResultType.CODE,
            display_hint="code-block",
            metadata={
                "language": language,
                "truncated": truncated,
                "original_length": original_length,
                "highlight": self._config.enable_syntax_highlighting,
            },
        )

    def _format_error(self, result: Any) -> FormattedResult:
        """Format error result."""
        error_message = ""
        error_type = "unknown"
        stack_trace = None

        if isinstance(result, dict):
            error_message = result.get("error", str(result))
            error_type = result.get("error_type", "ExecutionError")
            stack_trace = result.get("stack_trace")
        elif isinstance(result, str):
            error_message = result
        else:
            error_message = str(result)

        return FormattedResult(
            data={
                "message": error_message,
                "type": error_type,
                "stack_trace": stack_trace,
            },
            result_type=ResultType.ERROR,
            display_hint="error",
            metadata={"has_stack_trace": bool(stack_trace)},
        )

    # =========================================================================
    # Tool Execution with Events
    # =========================================================================

    async def execute_and_format(
        self,
        tool_call: ToolCall,
        session_id: Optional[str] = None,
    ) -> ToolCallEndEvent:
        """
        Execute tool and format result.

        Args:
            tool_call: Tool call to execute
            session_id: Optional session ID for context

        Returns:
            ToolCallEndEvent: AG-UI event with formatted result
        """
        from src.integrations.hybrid.execution.unified_executor import ToolSource

        # Execute tool
        result = await self._executor.execute(
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
            source=ToolSource.CLAUDE,
            session_id=session_id,
        )

        # Detect and format result
        if result.success:
            result_type = self.detect_result_type(result.content, tool_call.name)
            formatted = self.format_result(result.content, result_type, tool_call.name)

            return ToolCallEndEvent(
                type=AGUIEventType.TOOL_CALL_END,
                tool_call_id=tool_call.id,
                status=ToolCallStatus.SUCCESS,
                result={
                    "type": formatted.result_type.value,
                    "data": formatted.data,
                    "display_hint": formatted.display_hint,
                    "metadata": formatted.metadata,
                },
            )
        else:
            formatted = self._format_error({"error": result.error})

            return ToolCallEndEvent(
                type=AGUIEventType.TOOL_CALL_END,
                tool_call_id=tool_call.id,
                status=ToolCallStatus.ERROR,
                result={
                    "type": ResultType.ERROR.value,
                    "data": formatted.data,
                },
                error=result.error,
            )

    async def create_start_event(
        self,
        tool_call: ToolCall,
        run_id: str,
    ) -> ToolCallStartEvent:
        """
        Create a tool call start event.

        Args:
            tool_call: Tool call to start
            run_id: Associated run ID

        Returns:
            ToolCallStartEvent: AG-UI event for tool start
        """
        return ToolCallStartEvent(
            type=AGUIEventType.TOOL_CALL_START,
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
        )

    def create_status_event(
        self,
        tool_call: ToolCall,
        status: ToolExecutionStatus,
        progress: Optional[float] = None,
    ) -> CustomEvent:
        """
        Create a tool status custom event.

        Args:
            tool_call: Tool call to report status for
            status: Current execution status
            progress: Optional progress percentage (0-100)

        Returns:
            CustomEvent: AG-UI custom event for tool status
        """
        return CustomEvent(
            type=AGUIEventType.CUSTOM,
            event_name="tool_status",
            payload={
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.name,
                "status": status.value,
                "progress": progress,
            },
        )


# =============================================================================
# Factory Function
# =============================================================================


def create_tool_rendering_handler(
    *,
    unified_executor: "UnifiedToolExecutor",
    config: Optional[ToolRenderingConfig] = None,
) -> ToolRenderingHandler:
    """
    Factory function to create ToolRenderingHandler.

    Args:
        unified_executor: UnifiedToolExecutor instance
        config: Optional ToolRenderingConfig

    Returns:
        Configured ToolRenderingHandler instance
    """
    return ToolRenderingHandler(
        unified_executor=unified_executor,
        config=config,
    )
