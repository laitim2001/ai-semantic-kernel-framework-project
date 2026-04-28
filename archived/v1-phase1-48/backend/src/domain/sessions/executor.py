"""
Agent Executor - Sprint 45 S45-1

統一的 Agent 執行器，整合 LLM 調用與串流支援。
提供 Workflow 和 Session 模式共享的執行邏輯。

功能:
- Agent 配置載入
- 訊息構建邏輯 (system + history + user)
- 同步與非同步執行模式
- 執行事件發送

依賴:
- LLMServiceProtocol (Phase 3)
- ToolRegistry (Phase 9)
- ExecutionEvent (S45-4)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
)
import uuid
import logging
import asyncio

from src.integrations.llm.protocol import LLMServiceProtocol, LLMServiceError
from src.domain.agents.tools.registry import ToolRegistry
from src.domain.sessions.events import (
    ExecutionEvent,
    ExecutionEventFactory,
    ExecutionEventType,
    UsageInfo,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================


class MessageRole(str, Enum):
    """訊息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """對話訊息

    Attributes:
        role: 訊息角色
        content: 訊息內容
        name: 發送者名稱（用於 tool role）
        tool_call_id: 工具調用 ID（用於 tool role）
    """
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式（用於 OpenAI API）"""
        result = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class AgentConfig:
    """Agent 配置

    從 Agent domain model 提取的執行配置。

    Attributes:
        agent_id: Agent ID
        name: Agent 名稱
        instructions: 系統指令（system prompt）
        tools: 可用工具列表
        model_config: LLM 模型配置
        max_iterations: 最大迭代次數
    """
    agent_id: str
    name: str
    instructions: str
    tools: List[str] = field(default_factory=list)
    model_config: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 10

    @classmethod
    def from_agent(cls, agent: Any) -> "AgentConfig":
        """從 Agent domain model 創建配置

        Args:
            agent: Agent domain model 或 AgentResponse schema

        Returns:
            AgentConfig 實例
        """
        # 支援 dict-like 和 object-like 訪問
        if hasattr(agent, "id"):
            agent_id = str(agent.id)
            name = agent.name
            instructions = agent.instructions
            tools = agent.tools if hasattr(agent, "tools") else []
            model_config = agent.model_config_data if hasattr(agent, "model_config_data") else {}
            max_iterations = agent.max_iterations if hasattr(agent, "max_iterations") else 10
        else:
            # dict 格式
            agent_id = str(agent.get("id", ""))
            name = agent.get("name", "")
            instructions = agent.get("instructions", "")
            tools = agent.get("tools", [])
            model_config = agent.get("model_config_data", {})
            max_iterations = agent.get("max_iterations", 10)

        return cls(
            agent_id=agent_id,
            name=name,
            instructions=instructions,
            tools=tools if isinstance(tools, list) else [],
            model_config=model_config if isinstance(model_config, dict) else {},
            max_iterations=max_iterations,
        )


@dataclass
class ExecutionConfig:
    """執行配置

    Attributes:
        stream: 是否串流回應
        max_tokens: 最大 token 數
        temperature: 溫度參數
        timeout: 超時秒數
        enable_tools: 是否啟用工具
        require_approval: 需要審批的工具列表
    """
    stream: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 120.0
    enable_tools: bool = True
    require_approval: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """執行結果

    非串流模式的完整執行結果。

    Attributes:
        content: 回應內容
        finish_reason: 完成原因
        usage: Token 使用量
        tool_calls: 工具調用記錄
        execution_id: 執行 ID
        duration_ms: 執行時間（毫秒）
    """
    content: str
    finish_reason: str = "stop"
    usage: Optional[UsageInfo] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    duration_ms: int = 0


# =============================================================================
# MCP Client Protocol
# =============================================================================


class MCPClientProtocol(Protocol):
    """MCP Client 協議

    定義 MCP Client 需要實現的介面。
    """

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """調用 MCP 工具

        Args:
            tool_name: 工具名稱
            arguments: 工具參數

        Returns:
            工具執行結果
        """
        ...

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """獲取可用工具列表

        Returns:
            工具 schema 列表
        """
        ...


# =============================================================================
# Agent Executor
# =============================================================================


class AgentExecutor:
    """Agent 執行器

    統一的 Agent 執行介面，支援 Workflow 和 Session 模式。

    Features:
    - 訊息構建：自動組裝 system prompt + history + user message
    - 串流支援：通過 AsyncGenerator 返回 ExecutionEvent
    - 工具調用：整合 ToolRegistry 和 MCP Client
    - 錯誤處理：包裝 LLM 錯誤為 ExecutionEvent

    Example:
        ```python
        executor = AgentExecutor(
            llm_service=azure_llm,
            tool_registry=registry,
        )

        # 串流執行
        async for event in executor.execute(
            agent_config=config,
            messages=[{"role": "user", "content": "Hello"}],
            session_id="session-123",
        ):
            print(event.to_json())

        # 非串流執行
        result = await executor.execute_sync(
            agent_config=config,
            messages=[{"role": "user", "content": "Hello"}],
            session_id="session-123",
        )
        print(result.content)
        ```
    """

    def __init__(
        self,
        llm_service: LLMServiceProtocol,
        tool_registry: Optional[ToolRegistry] = None,
        mcp_client: Optional[MCPClientProtocol] = None,
    ):
        """初始化執行器

        Args:
            llm_service: LLM 服務實例
            tool_registry: 工具註冊表（可選）
            mcp_client: MCP Client 實例（可選）
        """
        self._llm_service = llm_service
        self._tool_registry = tool_registry
        self._mcp_client = mcp_client

        logger.debug(
            f"AgentExecutor initialized: "
            f"llm={type(llm_service).__name__}, "
            f"tools={tool_registry is not None}, "
            f"mcp={mcp_client is not None}"
        )

    # =========================================================================
    # Public Methods
    # =========================================================================

    async def execute(
        self,
        agent_config: AgentConfig,
        messages: List[Union[ChatMessage, Dict[str, Any]]],
        session_id: str,
        execution_config: Optional[ExecutionConfig] = None,
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """執行 Agent（串流模式）

        Args:
            agent_config: Agent 配置
            messages: 對話歷史
            session_id: Session ID
            execution_config: 執行配置

        Yields:
            ExecutionEvent: 執行事件流
        """
        config = execution_config or ExecutionConfig()
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        # 發送開始事件
        yield ExecutionEventFactory.started(
            session_id=session_id,
            execution_id=execution_id,
            agent_id=agent_config.agent_id,
            agent_name=agent_config.name,
        )

        try:
            # 構建訊息
            built_messages = self._build_messages(agent_config, messages)

            # 獲取可用工具
            tools = self._get_available_tools(agent_config) if config.enable_tools else []

            # 調用 LLM
            if config.stream:
                # 串流模式 - 目前 LLMServiceProtocol 不支援串流，先用非串流模擬
                # S45-2 會實作真正的串流
                response = await self._call_llm(
                    built_messages,
                    agent_config,
                    config,
                )

                # 模擬串流：將內容分塊發送
                chunk_size = 20  # 每塊字符數
                content = response.get("content", "")

                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    yield ExecutionEventFactory.content_delta(
                        session_id=session_id,
                        execution_id=execution_id,
                        delta=chunk,
                    )
                    # 模擬網路延遲
                    await asyncio.sleep(0.01)

                # 發送完成事件
                usage = response.get("usage", {})
                yield ExecutionEventFactory.done(
                    session_id=session_id,
                    execution_id=execution_id,
                    finish_reason=response.get("finish_reason", "stop"),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                )
            else:
                # 非串流模式
                response = await self._call_llm(
                    built_messages,
                    agent_config,
                    config,
                )

                # 發送完整內容事件
                yield ExecutionEventFactory.content(
                    session_id=session_id,
                    execution_id=execution_id,
                    content=response.get("content", ""),
                )

                # 發送完成事件
                usage = response.get("usage", {})
                yield ExecutionEventFactory.done(
                    session_id=session_id,
                    execution_id=execution_id,
                    finish_reason=response.get("finish_reason", "stop"),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                )

        except LLMServiceError as e:
            logger.error(f"LLM error in execution {execution_id}: {e}")
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message=str(e),
                error_code="LLM_ERROR",
            )
        except Exception as e:
            logger.error(f"Unexpected error in execution {execution_id}: {e}", exc_info=True)
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message=f"Unexpected error: {str(e)}",
                error_code="EXECUTION_ERROR",
            )

    async def execute_sync(
        self,
        agent_config: AgentConfig,
        messages: List[Union[ChatMessage, Dict[str, Any]]],
        session_id: str,
        execution_config: Optional[ExecutionConfig] = None,
    ) -> ExecutionResult:
        """執行 Agent（非串流模式）

        收集所有事件並返回完整結果。

        Args:
            agent_config: Agent 配置
            messages: 對話歷史
            session_id: Session ID
            execution_config: 執行配置

        Returns:
            ExecutionResult: 完整執行結果
        """
        config = execution_config or ExecutionConfig(stream=False)
        config.stream = False  # 強制非串流

        content_parts = []
        usage = None
        finish_reason = "stop"
        execution_id = ""
        start_time = datetime.utcnow()
        tool_calls = []

        async for event in self.execute(
            agent_config=agent_config,
            messages=messages,
            session_id=session_id,
            execution_config=config,
        ):
            if event.event_type == ExecutionEventType.STARTED:
                execution_id = event.execution_id
            elif event.event_type == ExecutionEventType.CONTENT:
                content_parts.append(event.content or "")
            elif event.event_type == ExecutionEventType.CONTENT_DELTA:
                content_parts.append(event.content or "")
            elif event.event_type == ExecutionEventType.DONE:
                finish_reason = event.finish_reason or "stop"
                if event.usage:
                    usage = event.usage
            elif event.event_type == ExecutionEventType.TOOL_CALL:
                if event.tool_call:
                    tool_calls.append(event.tool_call.to_dict())
            elif event.event_type == ExecutionEventType.ERROR:
                raise LLMServiceError(event.error or "Unknown error")

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ExecutionResult(
            content="".join(content_parts),
            finish_reason=finish_reason,
            usage=usage,
            tool_calls=tool_calls,
            execution_id=execution_id,
            duration_ms=duration_ms,
        )

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _build_messages(
        self,
        agent_config: AgentConfig,
        messages: List[Union[ChatMessage, Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """構建完整訊息列表

        組裝順序：
        1. System prompt（from agent instructions）
        2. History messages
        3. User message（最後一條）

        Args:
            agent_config: Agent 配置
            messages: 原始訊息列表

        Returns:
            OpenAI API 格式的訊息列表
        """
        built = []

        # 1. System prompt
        if agent_config.instructions:
            built.append({
                "role": "system",
                "content": agent_config.instructions,
            })

        # 2. 轉換並添加訊息
        for msg in messages:
            if isinstance(msg, ChatMessage):
                built.append(msg.to_dict())
            elif isinstance(msg, dict):
                # 確保有 role 和 content
                if "role" in msg and "content" in msg:
                    built.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        **({"name": msg["name"]} if "name" in msg else {}),
                        **({"tool_call_id": msg["tool_call_id"]} if "tool_call_id" in msg else {}),
                    })

        logger.debug(f"Built {len(built)} messages for execution")
        return built

    def _get_available_tools(
        self,
        agent_config: AgentConfig,
    ) -> List[Dict[str, Any]]:
        """獲取 Agent 可用的工具列表

        合併來源：
        1. ToolRegistry 中的工具（根據 agent_config.tools 過濾）
        2. MCP Client 提供的工具

        Args:
            agent_config: Agent 配置

        Returns:
            OpenAI tools 格式的列表
        """
        tools = []

        # 從 ToolRegistry 獲取工具
        if self._tool_registry and agent_config.tools:
            for tool_name in agent_config.tools:
                tool = self._tool_registry.get(tool_name)
                if tool:
                    schema = tool.get_schema()
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": schema,
                        },
                    })

        # 從 MCP Client 獲取工具
        if self._mcp_client:
            try:
                mcp_tools = self._mcp_client.get_available_tools()
                for mcp_tool in mcp_tools:
                    # 檢查是否在 agent 配置的工具列表中
                    tool_name = mcp_tool.get("name", "")
                    if not agent_config.tools or tool_name in agent_config.tools:
                        tools.append({
                            "type": "function",
                            "function": mcp_tool,
                        })
            except Exception as e:
                logger.warning(f"Failed to get MCP tools: {e}")

        logger.debug(f"Available tools for agent: {[t['function']['name'] for t in tools]}")
        return tools

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        agent_config: AgentConfig,
        config: ExecutionConfig,
    ) -> Dict[str, Any]:
        """調用 LLM 服務

        Args:
            messages: 訊息列表
            agent_config: Agent 配置
            config: 執行配置

        Returns:
            LLM 回應字典，包含 content, finish_reason, usage
        """
        # 從 agent model config 和 execution config 合併參數
        temperature = agent_config.model_config.get("temperature", config.temperature)
        max_tokens = agent_config.model_config.get("max_tokens", config.max_tokens)

        # 構建 prompt（簡化版，只取最後用戶訊息）
        # 完整版會在 S45-2 實現
        prompt = "\n".join([
            f"{m['role']}: {m['content']}"
            for m in messages
        ])

        try:
            # 調用 LLM
            response = await self._llm_service.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # 構造回應
            # 注意：實際 token 計數需要在 S45-2 實現
            return {
                "content": response,
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": len(prompt) // 4,  # 估算
                    "completion_tokens": len(response) // 4,  # 估算
                },
            }
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_tool_registry(self) -> Optional[ToolRegistry]:
        """獲取工具註冊表"""
        return self._tool_registry

    def get_mcp_client(self) -> Optional[MCPClientProtocol]:
        """獲取 MCP Client"""
        return self._mcp_client

    def set_tool_registry(self, registry: ToolRegistry) -> None:
        """設置工具註冊表"""
        self._tool_registry = registry
        logger.debug("Tool registry updated")

    def set_mcp_client(self, client: MCPClientProtocol) -> None:
        """設置 MCP Client"""
        self._mcp_client = client
        logger.debug("MCP client updated")


# =============================================================================
# Factory Functions
# =============================================================================


def create_agent_executor(
    llm_service: LLMServiceProtocol,
    tool_registry: Optional[ToolRegistry] = None,
    mcp_client: Optional[MCPClientProtocol] = None,
) -> AgentExecutor:
    """創建 AgentExecutor 實例

    Factory 函數，便於依賴注入。

    Args:
        llm_service: LLM 服務
        tool_registry: 工具註冊表
        mcp_client: MCP Client

    Returns:
        AgentExecutor 實例
    """
    return AgentExecutor(
        llm_service=llm_service,
        tool_registry=tool_registry,
        mcp_client=mcp_client,
    )
