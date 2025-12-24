"""
Tool Call Handler

Sprint 45-3: 工具調用框架
提供工具調用解析、執行和結果處理的完整框架。

主要功能:
- 工具調用解析 (from LLM response)
- 本地工具執行 (via ToolRegistry)
- MCP 工具執行 (via MCPClient)
- 結果格式化 (for LLM)
- 多輪工具調用支援
- 權限檢查
"""

from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Protocol,
    AsyncIterator,
    Callable,
    Awaitable,
    Union,
    runtime_checkable,
)
from enum import Enum
import asyncio
import json
import logging
import uuid
from datetime import datetime

from .events import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionEventFactory,
    ToolCallInfo,
    ToolResultInfo,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Types and Protocols
# =============================================================================


class ToolSource(str, Enum):
    """工具來源類型"""
    LOCAL = "local"     # 本地 ToolRegistry
    MCP = "mcp"         # MCP Server
    BUILTIN = "builtin" # 內建工具


class ToolPermission(str, Enum):
    """工具權限級別"""
    AUTO = "auto"                   # 自動執行
    NOTIFY = "notify"               # 通知用戶但自動執行
    APPROVAL_REQUIRED = "approval"  # 需要人工審批
    DENIED = "denied"               # 禁止執行


@runtime_checkable
class ToolRegistryProtocol(Protocol):
    """ToolRegistry 協議

    定義 ToolRegistry 需要實現的介面。
    """

    def get(self, name: str) -> Optional[Any]:
        """獲取工具"""
        ...

    def get_all(self) -> Dict[str, Any]:
        """獲取所有工具"""
        ...

    def get_schemas(self) -> List[Dict[str, Any]]:
        """獲取工具 schemas"""
        ...


@runtime_checkable
class MCPClientProtocol(Protocol):
    """MCPClient 協議

    定義 MCPClient 需要實現的介面。
    """

    async def call_tool(
        self,
        server: str,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """調用 MCP 工具"""
        ...

    async def list_tools(
        self,
        server_name: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, List[Any]]:
        """列出 MCP 工具"""
        ...

    @property
    def connected_servers(self) -> List[str]:
        """已連接的 servers"""
        ...


# 審批回調類型
ApprovalCallback = Callable[[str, ToolCallInfo], Awaitable[bool]]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ParsedToolCall:
    """解析後的工具調用

    從 LLM response 中解析出的工具調用信息。
    """
    id: str                           # 工具調用 ID (from LLM)
    name: str                         # 工具名稱
    arguments: Dict[str, Any]         # 工具參數
    source: ToolSource = ToolSource.LOCAL  # 工具來源
    server_name: Optional[str] = None # MCP server 名稱
    raw_arguments: Optional[str] = None  # 原始 JSON 字串 (for debugging)

    def to_tool_call_info(self, requires_approval: bool = False) -> ToolCallInfo:
        """轉換為 ToolCallInfo"""
        return ToolCallInfo(
            id=self.id,
            name=self.name,
            arguments=self.arguments,
            requires_approval=requires_approval,
        )


@dataclass
class ToolExecutionResult:
    """工具執行結果"""
    tool_call_id: str               # 對應的工具調用 ID
    name: str                       # 工具名稱
    success: bool                   # 是否成功
    result: Any                     # 執行結果
    error: Optional[str] = None     # 錯誤訊息
    execution_time_ms: float = 0.0  # 執行時間 (ms)
    source: ToolSource = ToolSource.LOCAL  # 工具來源

    def to_tool_result_info(self) -> ToolResultInfo:
        """轉換為 ToolResultInfo"""
        return ToolResultInfo(
            tool_call_id=self.tool_call_id,
            name=self.name,
            result=self.result,
            success=self.success,
            error_message=self.error,
        )

    def to_llm_message(self) -> Dict[str, Any]:
        """轉換為 LLM tool result message 格式"""
        content = self.result if self.success else f"Error: {self.error}"

        # 確保 content 是字串
        if not isinstance(content, str):
            try:
                content = json.dumps(content, ensure_ascii=False, default=str)
            except Exception:
                content = str(content)

        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": content,
        }


@dataclass
class ToolHandlerConfig:
    """工具處理器配置"""
    # 執行設置
    max_parallel_calls: int = 5          # 最大並行調用數
    default_timeout: float = 30.0        # 預設超時時間 (秒)
    max_tool_rounds: int = 10            # 最大工具調用輪次

    # 權限設置
    default_permission: ToolPermission = ToolPermission.AUTO
    approval_timeout: float = 300.0      # 審批超時 (秒)

    # 安全設置
    allowed_tools: Optional[Set[str]] = None      # 允許的工具 (None = 全部)
    blocked_tools: Set[str] = field(default_factory=set)  # 禁止的工具
    require_approval_tools: Set[str] = field(default_factory=set)  # 需要審批的工具

    # MCP 設置
    enable_mcp: bool = True              # 是否啟用 MCP
    mcp_tool_prefix: str = "mcp_"        # MCP 工具前綴


@dataclass
class ToolHandlerStats:
    """工具處理器統計"""
    total_calls: int = 0           # 總調用次數
    successful_calls: int = 0      # 成功次數
    failed_calls: int = 0          # 失敗次數
    total_execution_time_ms: float = 0.0  # 總執行時間
    calls_by_tool: Dict[str, int] = field(default_factory=dict)  # 各工具調用次數

    def record_call(self, tool_name: str, success: bool, execution_time_ms: float):
        """記錄調用"""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        self.total_execution_time_ms += execution_time_ms
        self.calls_by_tool[tool_name] = self.calls_by_tool.get(tool_name, 0) + 1

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def average_execution_time_ms(self) -> float:
        """平均執行時間"""
        if self.total_calls == 0:
            return 0.0
        return self.total_execution_time_ms / self.total_calls


# =============================================================================
# Tool Call Parser
# =============================================================================


class ToolCallParser:
    """工具調用解析器

    從 LLM response 中解析工具調用。
    支援 OpenAI/Azure OpenAI function calling 格式。
    """

    @staticmethod
    def parse_from_response(
        response: Any,
        mcp_servers: Optional[List[str]] = None,
        mcp_tool_prefix: str = "mcp_",
    ) -> List[ParsedToolCall]:
        """從 LLM response 解析工具調用

        Args:
            response: LLM response (支援多種格式)
            mcp_servers: MCP server 列表
            mcp_tool_prefix: MCP 工具前綴

        Returns:
            解析後的工具調用列表
        """
        tool_calls = []
        mcp_servers = mcp_servers or []

        # 處理不同格式的 response
        if hasattr(response, "tool_calls") and response.tool_calls:
            # Azure OpenAI / OpenAI 格式
            for tc in response.tool_calls:
                parsed = ToolCallParser._parse_openai_tool_call(
                    tc, mcp_servers, mcp_tool_prefix
                )
                if parsed:
                    tool_calls.append(parsed)

        elif isinstance(response, dict):
            # Dict 格式
            if "tool_calls" in response:
                for tc in response["tool_calls"]:
                    parsed = ToolCallParser._parse_dict_tool_call(
                        tc, mcp_servers, mcp_tool_prefix
                    )
                    if parsed:
                        tool_calls.append(parsed)

        return tool_calls

    @staticmethod
    def parse_from_message(
        message: Dict[str, Any],
        mcp_servers: Optional[List[str]] = None,
        mcp_tool_prefix: str = "mcp_",
    ) -> List[ParsedToolCall]:
        """從 message dict 解析工具調用

        Args:
            message: LLM message dict
            mcp_servers: MCP server 列表
            mcp_tool_prefix: MCP 工具前綴

        Returns:
            解析後的工具調用列表
        """
        tool_calls = []
        mcp_servers = mcp_servers or []

        if "tool_calls" in message and message["tool_calls"]:
            for tc in message["tool_calls"]:
                parsed = ToolCallParser._parse_dict_tool_call(
                    tc, mcp_servers, mcp_tool_prefix
                )
                if parsed:
                    tool_calls.append(parsed)

        return tool_calls

    @staticmethod
    def _parse_openai_tool_call(
        tool_call: Any,
        mcp_servers: List[str],
        mcp_tool_prefix: str,
    ) -> Optional[ParsedToolCall]:
        """解析 OpenAI 格式的工具調用"""
        try:
            # 獲取 ID
            tc_id = getattr(tool_call, "id", None) or str(uuid.uuid4())

            # 獲取 function
            func = getattr(tool_call, "function", None)
            if not func:
                return None

            name = getattr(func, "name", "")
            arguments_str = getattr(func, "arguments", "{}")

            # 解析 arguments
            try:
                arguments = json.loads(arguments_str) if arguments_str else {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool arguments: {arguments_str}")
                arguments = {}

            # 判斷工具來源
            source, server_name = ToolCallParser._determine_source(
                name, mcp_servers, mcp_tool_prefix
            )

            return ParsedToolCall(
                id=tc_id,
                name=name,
                arguments=arguments,
                source=source,
                server_name=server_name,
                raw_arguments=arguments_str,
            )

        except Exception as e:
            logger.error(f"Error parsing tool call: {e}")
            return None

    @staticmethod
    def _parse_dict_tool_call(
        tool_call: Dict[str, Any],
        mcp_servers: List[str],
        mcp_tool_prefix: str,
    ) -> Optional[ParsedToolCall]:
        """解析 dict 格式的工具調用"""
        try:
            tc_id = tool_call.get("id") or str(uuid.uuid4())

            # 支援兩種格式
            if "function" in tool_call:
                func = tool_call["function"]
                name = func.get("name", "")
                arguments = func.get("arguments", {})
            else:
                name = tool_call.get("name", "")
                arguments = tool_call.get("arguments", {})

            # 如果 arguments 是字串，嘗試解析
            raw_arguments = None
            if isinstance(arguments, str):
                raw_arguments = arguments
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            # 判斷工具來源
            source, server_name = ToolCallParser._determine_source(
                name, mcp_servers, mcp_tool_prefix
            )

            return ParsedToolCall(
                id=tc_id,
                name=name,
                arguments=arguments,
                source=source,
                server_name=server_name,
                raw_arguments=raw_arguments,
            )

        except Exception as e:
            logger.error(f"Error parsing tool call dict: {e}")
            return None

    @staticmethod
    def _determine_source(
        tool_name: str,
        mcp_servers: List[str],
        mcp_tool_prefix: str,
    ) -> tuple[ToolSource, Optional[str]]:
        """判斷工具來源

        格式支援:
        - "mcp_servername_toolname" -> MCP 工具
        - "servername:toolname" -> MCP 工具
        - "toolname" -> 本地工具
        """
        # 檢查前綴格式: mcp_server_tool
        if tool_name.startswith(mcp_tool_prefix):
            parts = tool_name[len(mcp_tool_prefix):].split("_", 1)
            if len(parts) >= 1 and parts[0] in mcp_servers:
                return ToolSource.MCP, parts[0]

        # 檢查冒號格式: server:tool
        if ":" in tool_name:
            parts = tool_name.split(":", 1)
            if parts[0] in mcp_servers:
                return ToolSource.MCP, parts[0]

        return ToolSource.LOCAL, None


# =============================================================================
# Tool Call Handler
# =============================================================================


class ToolCallHandler:
    """工具調用處理器

    處理工具調用的完整生命週期:
    1. 解析工具調用
    2. 權限檢查
    3. 執行工具
    4. 格式化結果

    支援:
    - 本地工具 (via ToolRegistry)
    - MCP 工具 (via MCPClient)
    - 並行執行
    - 審批流程
    - 多輪調用
    """

    def __init__(
        self,
        tool_registry: Optional[ToolRegistryProtocol] = None,
        mcp_client: Optional[MCPClientProtocol] = None,
        config: Optional[ToolHandlerConfig] = None,
        approval_callback: Optional[ApprovalCallback] = None,
    ):
        """初始化工具處理器

        Args:
            tool_registry: 本地工具註冊表
            mcp_client: MCP 客戶端
            config: 處理器配置
            approval_callback: 審批回調函數
        """
        self.tool_registry = tool_registry
        self.mcp_client = mcp_client
        self.config = config or ToolHandlerConfig()
        self.approval_callback = approval_callback

        self.stats = ToolHandlerStats()
        self._round_count = 0

    # =========================================================================
    # Main API
    # =========================================================================

    async def handle_tool_calls(
        self,
        tool_calls: List[ParsedToolCall],
        session_id: str = "",
        execution_id: str = "",
    ) -> AsyncIterator[ExecutionEvent]:
        """處理工具調用列表

        Args:
            tool_calls: 工具調用列表
            session_id: Session ID
            execution_id: 執行 ID

        Yields:
            ExecutionEvent: 執行事件
        """
        if not tool_calls:
            return

        self._round_count += 1

        # 檢查輪次限制
        if self._round_count > self.config.max_tool_rounds:
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message=f"Exceeded maximum tool rounds: {self.config.max_tool_rounds}",
                error_code="MAX_TOOL_ROUNDS_EXCEEDED",
            )
            return

        # 分組處理: 需要審批 vs 可自動執行
        auto_calls = []
        approval_calls = []

        for tc in tool_calls:
            permission = self._check_permission(tc.name)

            if permission == ToolPermission.DENIED:
                yield ExecutionEventFactory.tool_result(
                    session_id=session_id,
                    execution_id=execution_id,
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    result=None,
                    success=False,
                    error_message=f"Tool '{tc.name}' is not allowed",
                )
                continue

            if permission == ToolPermission.APPROVAL_REQUIRED:
                approval_calls.append(tc)
            else:
                auto_calls.append(tc)

        # 處理需要審批的工具調用
        for tc in approval_calls:
            async for event in self._handle_approval_call(
                tc, session_id, execution_id
            ):
                yield event

        # 並行執行自動工具調用
        if auto_calls:
            async for event in self._execute_parallel(
                auto_calls, session_id, execution_id
            ):
                yield event

    async def execute_tool(
        self,
        tool_call: ParsedToolCall,
        session_id: str = "",
        execution_id: str = "",
    ) -> ToolExecutionResult:
        """執行單個工具調用

        Args:
            tool_call: 工具調用
            session_id: Session ID
            execution_id: 執行 ID

        Returns:
            工具執行結果
        """
        start_time = datetime.utcnow()

        try:
            if tool_call.source == ToolSource.MCP:
                result = await self._execute_mcp_tool(tool_call)
            else:
                result = await self._execute_local_tool(tool_call)

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time

            # 記錄統計
            self.stats.record_call(
                tool_call.name,
                result.success,
                execution_time,
            )

            return result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            self.stats.record_call(tool_call.name, False, execution_time)

            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time,
                source=tool_call.source,
            )

    def parse_tool_calls(
        self,
        response: Any,
    ) -> List[ParsedToolCall]:
        """解析工具調用

        Args:
            response: LLM response

        Returns:
            解析後的工具調用列表
        """
        mcp_servers = []
        if self.mcp_client and self.config.enable_mcp:
            mcp_servers = self.mcp_client.connected_servers

        return ToolCallParser.parse_from_response(
            response,
            mcp_servers=mcp_servers,
            mcp_tool_prefix=self.config.mcp_tool_prefix,
        )

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """獲取所有可用工具的 schema

        Returns:
            工具 schema 列表 (OpenAI function format)
        """
        tools = []

        # 本地工具
        if self.tool_registry:
            schemas = self.tool_registry.get_schemas()
            for schema in schemas:
                if self._is_tool_allowed(schema.get("name", "")):
                    tools.append(schema)

        # TODO: MCP 工具 schema
        # 需要從 MCP client 獲取並轉換為 OpenAI function format

        return tools

    def reset_round_count(self):
        """重置輪次計數"""
        self._round_count = 0

    def results_to_messages(
        self,
        results: List[ToolExecutionResult],
    ) -> List[Dict[str, Any]]:
        """將結果轉換為 LLM messages

        Args:
            results: 執行結果列表

        Returns:
            LLM tool result messages
        """
        return [r.to_llm_message() for r in results]

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _check_permission(self, tool_name: str) -> ToolPermission:
        """檢查工具權限"""
        # 檢查是否被禁止
        if tool_name in self.config.blocked_tools:
            return ToolPermission.DENIED

        # 檢查是否允許 (如果設置了白名單)
        if self.config.allowed_tools is not None:
            if tool_name not in self.config.allowed_tools:
                return ToolPermission.DENIED

        # 檢查是否需要審批
        if tool_name in self.config.require_approval_tools:
            return ToolPermission.APPROVAL_REQUIRED

        return self.config.default_permission

    def _is_tool_allowed(self, tool_name: str) -> bool:
        """檢查工具是否允許"""
        permission = self._check_permission(tool_name)
        return permission != ToolPermission.DENIED

    async def _execute_local_tool(
        self,
        tool_call: ParsedToolCall,
    ) -> ToolExecutionResult:
        """執行本地工具"""
        if not self.tool_registry:
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                result=None,
                error="Tool registry not available",
                source=ToolSource.LOCAL,
            )

        tool = self.tool_registry.get(tool_call.name)
        if not tool:
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                result=None,
                error=f"Tool not found: {tool_call.name}",
                source=ToolSource.LOCAL,
            )

        try:
            # 調用工具
            if asyncio.iscoroutinefunction(tool.execute):
                result = await tool.execute(**tool_call.arguments)
            else:
                result = tool.execute(**tool_call.arguments)

            # 處理 ToolResult 格式
            if hasattr(result, "success"):
                return ToolExecutionResult(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    success=result.success,
                    result=result.data if hasattr(result, "data") else result.result,
                    error=result.error if hasattr(result, "error") else None,
                    source=ToolSource.LOCAL,
                )

            # 直接返回結果
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=True,
                result=result,
                source=ToolSource.LOCAL,
            )

        except Exception as e:
            logger.error(f"Error executing local tool {tool_call.name}: {e}")
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                result=None,
                error=str(e),
                source=ToolSource.LOCAL,
            )

    async def _execute_mcp_tool(
        self,
        tool_call: ParsedToolCall,
    ) -> ToolExecutionResult:
        """執行 MCP 工具"""
        if not self.mcp_client:
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                result=None,
                error="MCP client not available",
                source=ToolSource.MCP,
            )

        if not tool_call.server_name:
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                result=None,
                error="MCP server not specified",
                source=ToolSource.MCP,
            )

        try:
            # 解析實際工具名稱 (去除 prefix/server)
            actual_tool_name = self._get_mcp_tool_name(tool_call.name, tool_call.server_name)

            result = await self.mcp_client.call_tool(
                server=tool_call.server_name,
                tool=actual_tool_name,
                arguments=tool_call.arguments,
                timeout=self.config.default_timeout,
            )

            # 處理 MCP ToolResult
            if hasattr(result, "success"):
                return ToolExecutionResult(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    success=result.success,
                    result=result.content,
                    error=result.error if not result.success else None,
                    source=ToolSource.MCP,
                )

            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=True,
                result=result,
                source=ToolSource.MCP,
            )

        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_call.name}: {e}")
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                result=None,
                error=str(e),
                source=ToolSource.MCP,
            )

    def _get_mcp_tool_name(self, full_name: str, server_name: str) -> str:
        """從完整名稱獲取 MCP 工具名稱"""
        prefix = self.config.mcp_tool_prefix

        # mcp_server_tool -> tool
        if full_name.startswith(f"{prefix}{server_name}_"):
            return full_name[len(f"{prefix}{server_name}_"):]

        # server:tool -> tool
        if full_name.startswith(f"{server_name}:"):
            return full_name[len(f"{server_name}:"):]

        return full_name

    async def _execute_parallel(
        self,
        tool_calls: List[ParsedToolCall],
        session_id: str,
        execution_id: str,
    ) -> AsyncIterator[ExecutionEvent]:
        """並行執行工具調用"""
        # 分批執行
        batch_size = self.config.max_parallel_calls

        for i in range(0, len(tool_calls), batch_size):
            batch = tool_calls[i:i + batch_size]

            # 發送工具調用事件
            for tc in batch:
                yield ExecutionEventFactory.tool_call(
                    session_id=session_id,
                    execution_id=execution_id,
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    requires_approval=False,
                )

            # 並行執行
            tasks = [
                self.execute_tool(tc, session_id, execution_id)
                for tc in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 發送結果事件
            for tc, result in zip(batch, results):
                if isinstance(result, Exception):
                    yield ExecutionEventFactory.tool_result(
                        session_id=session_id,
                        execution_id=execution_id,
                        tool_call_id=tc.id,
                        tool_name=tc.name,
                        result=None,
                        success=False,
                        error_message=str(result),
                    )
                else:
                    yield ExecutionEventFactory.tool_result(
                        session_id=session_id,
                        execution_id=execution_id,
                        tool_call_id=result.tool_call_id,
                        tool_name=result.name,
                        result=result.result,
                        success=result.success,
                        error_message=result.error,
                    )

    async def _handle_approval_call(
        self,
        tool_call: ParsedToolCall,
        session_id: str,
        execution_id: str,
    ) -> AsyncIterator[ExecutionEvent]:
        """處理需要審批的工具調用"""
        approval_request_id = str(uuid.uuid4())

        # 發送審批請求事件
        yield ExecutionEventFactory.approval_required(
            session_id=session_id,
            execution_id=execution_id,
            approval_request_id=approval_request_id,
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
        )

        # 等待審批
        if self.approval_callback:
            try:
                approved = await asyncio.wait_for(
                    self.approval_callback(
                        approval_request_id,
                        tool_call.to_tool_call_info(requires_approval=True),
                    ),
                    timeout=self.config.approval_timeout,
                )
            except asyncio.TimeoutError:
                approved = False
                yield ExecutionEventFactory.approval_response(
                    session_id=session_id,
                    execution_id=execution_id,
                    approval_request_id=approval_request_id,
                    approved=False,
                    feedback="Approval timeout",
                )

                yield ExecutionEventFactory.tool_result(
                    session_id=session_id,
                    execution_id=execution_id,
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    result=None,
                    success=False,
                    error_message="Approval timeout",
                )
                return

            yield ExecutionEventFactory.approval_response(
                session_id=session_id,
                execution_id=execution_id,
                approval_request_id=approval_request_id,
                approved=approved,
            )

            if approved:
                # 執行工具
                result = await self.execute_tool(tool_call, session_id, execution_id)

                yield ExecutionEventFactory.tool_result(
                    session_id=session_id,
                    execution_id=execution_id,
                    tool_call_id=result.tool_call_id,
                    tool_name=result.name,
                    result=result.result,
                    success=result.success,
                    error_message=result.error,
                )
            else:
                yield ExecutionEventFactory.tool_result(
                    session_id=session_id,
                    execution_id=execution_id,
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    result=None,
                    success=False,
                    error_message="Tool call rejected by approver",
                )
        else:
            # 沒有審批回調，自動拒絕
            yield ExecutionEventFactory.tool_result(
                session_id=session_id,
                execution_id=execution_id,
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result=None,
                success=False,
                error_message="No approval callback configured",
            )


# =============================================================================
# Factory Function
# =============================================================================


def create_tool_handler(
    tool_registry: Optional[ToolRegistryProtocol] = None,
    mcp_client: Optional[MCPClientProtocol] = None,
    config: Optional[ToolHandlerConfig] = None,
    approval_callback: Optional[ApprovalCallback] = None,
) -> ToolCallHandler:
    """創建工具處理器

    Args:
        tool_registry: 本地工具註冊表
        mcp_client: MCP 客戶端
        config: 處理器配置
        approval_callback: 審批回調函數

    Returns:
        ToolCallHandler 實例
    """
    return ToolCallHandler(
        tool_registry=tool_registry,
        mcp_client=mcp_client,
        config=config,
        approval_callback=approval_callback,
    )
