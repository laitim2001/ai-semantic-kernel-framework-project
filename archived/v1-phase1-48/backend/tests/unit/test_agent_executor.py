"""
AgentExecutor Unit Tests - Sprint 45 S45-1

測試 AgentExecutor 核心類別功能:
- 初始化與配置
- 訊息構建邏輯
- 工具獲取
- 串流執行
- 非串流執行
- 錯誤處理
"""

import pytest
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.sessions.executor import (
    AgentExecutor,
    AgentConfig,
    ExecutionConfig,
    ExecutionResult,
    ChatMessage,
    MessageRole,
    MCPClientProtocol,
    create_agent_executor,
)
from src.domain.sessions.events import (
    ExecutionEvent,
    ExecutionEventType,
    UsageInfo,
)
from src.integrations.llm.protocol import LLMServiceProtocol, LLMServiceError


# =============================================================================
# Fixtures
# =============================================================================


class MockLLMService:
    """Mock LLM Service for testing"""

    def __init__(self, response: str = "Test response"):
        self.response = response
        self.calls = []

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        self.calls.append({
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        return self.response

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return {"result": "structured"}


class MockToolRegistry:
    """Mock Tool Registry for testing"""

    def __init__(self, tools: Optional[Dict[str, Any]] = None):
        self._tools = tools or {}

    def get(self, name: str):
        return self._tools.get(name)

    def get_all(self):
        return self._tools


class MockTool:
    """Mock Tool for testing"""

    def __init__(self, name: str, description: str = "Test tool"):
        self.name = name
        self.description = description

    def get_schema(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            }
        }


class MockMCPClient:
    """Mock MCP Client for testing"""

    def __init__(self, tools: Optional[List[Dict[str, Any]]] = None):
        self._tools = tools or []
        self.calls = []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        self.calls.append({"tool_name": tool_name, "arguments": arguments})
        return {"result": f"executed {tool_name}"}

    def get_available_tools(self) -> List[Dict[str, Any]]:
        return self._tools


@pytest.fixture
def mock_llm():
    """Create mock LLM service"""
    return MockLLMService()


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry with test tools"""
    tool1 = MockTool("search", "Search knowledge base")
    tool2 = MockTool("calculate", "Perform calculations")
    return MockToolRegistry({
        "search": tool1,
        "calculate": tool2,
    })


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client"""
    return MockMCPClient([
        {"name": "mcp_tool1", "description": "MCP Tool 1"},
        {"name": "mcp_tool2", "description": "MCP Tool 2"},
    ])


@pytest.fixture
def agent_config():
    """Create test agent config"""
    return AgentConfig(
        agent_id="agent-123",
        name="Test Agent",
        instructions="You are a helpful assistant.",
        tools=["search", "calculate"],
        model_config={"temperature": 0.5, "max_tokens": 1000},
        max_iterations=5,
    )


@pytest.fixture
def executor(mock_llm, mock_tool_registry):
    """Create executor with mock dependencies"""
    return AgentExecutor(
        llm_service=mock_llm,
        tool_registry=mock_tool_registry,
    )


# =============================================================================
# AgentConfig Tests
# =============================================================================


class TestAgentConfig:
    """AgentConfig 測試"""

    def test_create_config_directly(self):
        """測試直接創建配置"""
        config = AgentConfig(
            agent_id="123",
            name="Test",
            instructions="Be helpful",
        )
        assert config.agent_id == "123"
        assert config.name == "Test"
        assert config.instructions == "Be helpful"
        assert config.tools == []
        assert config.model_config == {}
        assert config.max_iterations == 10

    def test_create_config_with_all_fields(self):
        """測試創建完整配置"""
        config = AgentConfig(
            agent_id="456",
            name="Full Agent",
            instructions="Full instructions",
            tools=["tool1", "tool2"],
            model_config={"temp": 0.5},
            max_iterations=20,
        )
        assert config.tools == ["tool1", "tool2"]
        assert config.model_config == {"temp": 0.5}
        assert config.max_iterations == 20

    def test_from_agent_object(self):
        """測試從 Agent 對象創建配置"""
        mock_agent = MagicMock()
        mock_agent.id = "agent-789"
        mock_agent.name = "Agent Name"
        mock_agent.instructions = "System prompt"
        mock_agent.tools = ["search"]
        mock_agent.model_config_data = {"temperature": 0.7}
        mock_agent.max_iterations = 15

        config = AgentConfig.from_agent(mock_agent)

        assert config.agent_id == "agent-789"
        assert config.name == "Agent Name"
        assert config.instructions == "System prompt"
        assert config.tools == ["search"]
        assert config.model_config == {"temperature": 0.7}
        assert config.max_iterations == 15

    def test_from_agent_dict(self):
        """測試從字典創建配置"""
        agent_dict = {
            "id": "dict-agent",
            "name": "Dict Agent",
            "instructions": "Dict instructions",
            "tools": ["calc"],
            "model_config_data": {"max_tokens": 500},
            "max_iterations": 8,
        }

        config = AgentConfig.from_agent(agent_dict)

        assert config.agent_id == "dict-agent"
        assert config.name == "Dict Agent"
        assert config.instructions == "Dict instructions"
        assert config.tools == ["calc"]

    def test_from_agent_missing_fields(self):
        """測試處理缺失字段"""
        mock_agent = MagicMock()
        mock_agent.id = "min-agent"
        mock_agent.name = "Min"
        mock_agent.instructions = "Min instructions"
        # tools, model_config_data, max_iterations 不存在

        # 移除這些屬性
        del mock_agent.tools
        del mock_agent.model_config_data
        del mock_agent.max_iterations

        config = AgentConfig.from_agent(mock_agent)

        assert config.tools == []
        assert config.model_config == {}
        assert config.max_iterations == 10


# =============================================================================
# ChatMessage Tests
# =============================================================================


class TestChatMessage:
    """ChatMessage 測試"""

    def test_create_user_message(self):
        """測試創建用戶訊息"""
        msg = ChatMessage(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.tool_call_id is None

    def test_create_assistant_message(self):
        """測試創建助手訊息"""
        msg = ChatMessage(role=MessageRole.ASSISTANT, content="Hi there!")
        assert msg.role == MessageRole.ASSISTANT

    def test_create_tool_message(self):
        """測試創建工具訊息"""
        msg = ChatMessage(
            role=MessageRole.TOOL,
            content='{"result": "success"}',
            name="search",
            tool_call_id="call-123",
        )
        assert msg.role == MessageRole.TOOL
        assert msg.name == "search"
        assert msg.tool_call_id == "call-123"

    def test_to_dict_basic(self):
        """測試基本字典轉換"""
        msg = ChatMessage(role=MessageRole.USER, content="Test")
        d = msg.to_dict()

        assert d == {"role": "user", "content": "Test"}

    def test_to_dict_with_name(self):
        """測試帶名稱的字典轉換"""
        msg = ChatMessage(role=MessageRole.TOOL, content="Result", name="calc")
        d = msg.to_dict()

        assert d["name"] == "calc"

    def test_to_dict_with_tool_call_id(self):
        """測試帶工具調用 ID 的字典轉換"""
        msg = ChatMessage(
            role=MessageRole.TOOL,
            content="Result",
            tool_call_id="tc-456",
        )
        d = msg.to_dict()

        assert d["tool_call_id"] == "tc-456"


# =============================================================================
# ExecutionConfig Tests
# =============================================================================


class TestExecutionConfig:
    """ExecutionConfig 測試"""

    def test_default_config(self):
        """測試默認配置"""
        config = ExecutionConfig()
        assert config.stream is True
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.timeout == 120.0
        assert config.enable_tools is True
        assert config.require_approval == []

    def test_custom_config(self):
        """測試自定義配置"""
        config = ExecutionConfig(
            stream=False,
            max_tokens=2000,
            temperature=0.3,
            timeout=60.0,
            enable_tools=False,
            require_approval=["dangerous_tool"],
        )
        assert config.stream is False
        assert config.max_tokens == 2000
        assert config.require_approval == ["dangerous_tool"]


# =============================================================================
# ExecutionResult Tests
# =============================================================================


class TestExecutionResult:
    """ExecutionResult 測試"""

    def test_default_result(self):
        """測試默認結果"""
        result = ExecutionResult(content="Response")
        assert result.content == "Response"
        assert result.finish_reason == "stop"
        assert result.usage is None
        assert result.tool_calls == []
        assert result.execution_id != ""
        assert result.duration_ms == 0

    def test_full_result(self):
        """測試完整結果"""
        usage = UsageInfo(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        result = ExecutionResult(
            content="Full response",
            finish_reason="tool_calls",
            usage=usage,
            tool_calls=[{"name": "search", "result": "found"}],
            execution_id="exec-123",
            duration_ms=500,
        )
        assert result.usage.total_tokens == 150
        assert len(result.tool_calls) == 1
        assert result.duration_ms == 500


# =============================================================================
# AgentExecutor Initialization Tests
# =============================================================================


class TestAgentExecutorInit:
    """AgentExecutor 初始化測試"""

    def test_init_with_llm_only(self, mock_llm):
        """測試只用 LLM 初始化"""
        executor = AgentExecutor(llm_service=mock_llm)
        assert executor._llm_service is mock_llm
        assert executor._tool_registry is None
        assert executor._mcp_client is None

    def test_init_with_all_dependencies(self, mock_llm, mock_tool_registry, mock_mcp_client):
        """測試完整初始化"""
        executor = AgentExecutor(
            llm_service=mock_llm,
            tool_registry=mock_tool_registry,
            mcp_client=mock_mcp_client,
        )
        assert executor._llm_service is mock_llm
        assert executor._tool_registry is mock_tool_registry
        assert executor._mcp_client is mock_mcp_client

    def test_factory_function(self, mock_llm, mock_tool_registry):
        """測試工廠函數"""
        executor = create_agent_executor(
            llm_service=mock_llm,
            tool_registry=mock_tool_registry,
        )
        assert isinstance(executor, AgentExecutor)
        assert executor._tool_registry is mock_tool_registry


# =============================================================================
# Message Building Tests
# =============================================================================


class TestMessageBuilding:
    """訊息構建測試"""

    def test_build_messages_with_system_prompt(self, executor, agent_config):
        """測試包含系統提示的訊息構建"""
        messages = [{"role": "user", "content": "Hello"}]
        built = executor._build_messages(agent_config, messages)

        assert len(built) == 2
        assert built[0]["role"] == "system"
        assert built[0]["content"] == "You are a helpful assistant."
        assert built[1]["role"] == "user"
        assert built[1]["content"] == "Hello"

    def test_build_messages_without_system_prompt(self, executor):
        """測試無系統提示的訊息構建"""
        config = AgentConfig(
            agent_id="no-sys",
            name="No System",
            instructions="",  # 空 instructions
        )
        messages = [{"role": "user", "content": "Hi"}]
        built = executor._build_messages(config, messages)

        assert len(built) == 1
        assert built[0]["role"] == "user"

    def test_build_messages_with_chat_message_objects(self, executor, agent_config):
        """測試使用 ChatMessage 對象"""
        messages = [
            ChatMessage(role=MessageRole.USER, content="First"),
            ChatMessage(role=MessageRole.ASSISTANT, content="Response"),
            ChatMessage(role=MessageRole.USER, content="Second"),
        ]
        built = executor._build_messages(agent_config, messages)

        assert len(built) == 4  # system + 3 messages
        assert built[1]["role"] == "user"
        assert built[1]["content"] == "First"
        assert built[2]["role"] == "assistant"
        assert built[3]["role"] == "user"

    def test_build_messages_mixed_format(self, executor, agent_config):
        """測試混合格式訊息"""
        messages = [
            {"role": "user", "content": "Dict message"},
            ChatMessage(role=MessageRole.ASSISTANT, content="Object message"),
        ]
        built = executor._build_messages(agent_config, messages)

        assert len(built) == 3
        assert built[1]["content"] == "Dict message"
        assert built[2]["content"] == "Object message"

    def test_build_messages_preserves_extra_fields(self, executor, agent_config):
        """測試保留額外字段"""
        messages = [{
            "role": "tool",
            "content": "Result",
            "name": "search",
            "tool_call_id": "tc-123",
        }]
        built = executor._build_messages(agent_config, messages)

        assert len(built) == 2
        tool_msg = built[1]
        assert tool_msg["name"] == "search"
        assert tool_msg["tool_call_id"] == "tc-123"


# =============================================================================
# Tool Discovery Tests
# =============================================================================


class TestToolDiscovery:
    """工具發現測試"""

    def test_get_tools_from_registry(self, executor, agent_config):
        """測試從 registry 獲取工具"""
        tools = executor._get_available_tools(agent_config)

        assert len(tools) == 2
        tool_names = [t["function"]["name"] for t in tools]
        assert "search" in tool_names
        assert "calculate" in tool_names

    def test_get_tools_filtered_by_config(self, mock_llm, mock_tool_registry):
        """測試根據配置過濾工具"""
        executor = AgentExecutor(
            llm_service=mock_llm,
            tool_registry=mock_tool_registry,
        )
        config = AgentConfig(
            agent_id="filtered",
            name="Filtered",
            instructions="Test",
            tools=["search"],  # 只允許 search
        )
        tools = executor._get_available_tools(config)

        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "search"

    def test_get_tools_with_mcp_client(self, mock_llm, mock_mcp_client):
        """測試包含 MCP 工具"""
        executor = AgentExecutor(
            llm_service=mock_llm,
            mcp_client=mock_mcp_client,
        )
        config = AgentConfig(
            agent_id="mcp",
            name="MCP Test",
            instructions="Test",
            tools=[],  # 空列表允許所有 MCP 工具
        )
        tools = executor._get_available_tools(config)

        assert len(tools) == 2
        names = [t["function"]["name"] for t in tools]
        assert "mcp_tool1" in names

    def test_get_tools_empty_config(self, executor):
        """測試空工具配置"""
        config = AgentConfig(
            agent_id="empty",
            name="Empty",
            instructions="Test",
            tools=[],
        )
        tools = executor._get_available_tools(config)

        assert len(tools) == 0

    def test_get_tools_no_registry(self, mock_llm):
        """測試無 registry"""
        executor = AgentExecutor(llm_service=mock_llm)
        config = AgentConfig(
            agent_id="no-reg",
            name="No Registry",
            instructions="Test",
            tools=["search"],
        )
        tools = executor._get_available_tools(config)

        assert len(tools) == 0


# =============================================================================
# Execution Tests
# =============================================================================


class TestExecution:
    """執行測試"""

    @pytest.mark.asyncio
    async def test_execute_streaming_basic(self, executor, agent_config):
        """測試基本串流執行"""
        messages = [{"role": "user", "content": "Hello"}]

        events = []
        async for event in executor.execute(
            agent_config=agent_config,
            messages=messages,
            session_id="session-123",
        ):
            events.append(event)

        # 驗證事件序列
        assert len(events) >= 3  # started + deltas + done
        assert events[0].event_type == ExecutionEventType.STARTED
        assert events[-1].event_type == ExecutionEventType.DONE

    @pytest.mark.asyncio
    async def test_execute_streaming_events(self, executor, agent_config):
        """測試串流事件內容"""
        messages = [{"role": "user", "content": "Test"}]

        started_event = None
        delta_events = []
        done_event = None

        async for event in executor.execute(
            agent_config=agent_config,
            messages=messages,
            session_id="sess-456",
        ):
            if event.event_type == ExecutionEventType.STARTED:
                started_event = event
            elif event.event_type == ExecutionEventType.CONTENT_DELTA:
                delta_events.append(event)
            elif event.event_type == ExecutionEventType.DONE:
                done_event = event

        # 驗證 started 事件
        assert started_event is not None
        assert started_event.session_id == "sess-456"
        assert started_event.execution_id != ""

        # 驗證 delta 事件
        assert len(delta_events) > 0
        full_content = "".join([e.content for e in delta_events])
        assert full_content == "Test response"  # MockLLMService 返回值

        # 驗證 done 事件
        assert done_event is not None
        assert done_event.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_execute_non_streaming(self, executor, agent_config):
        """測試非串流執行"""
        messages = [{"role": "user", "content": "Test"}]
        config = ExecutionConfig(stream=False)

        events = []
        async for event in executor.execute(
            agent_config=agent_config,
            messages=messages,
            session_id="sess-789",
            execution_config=config,
        ):
            events.append(event)

        # 非串流應該有 started, content (完整), done
        assert len(events) == 3
        assert events[0].event_type == ExecutionEventType.STARTED
        assert events[1].event_type == ExecutionEventType.CONTENT
        assert events[1].content == "Test response"
        assert events[2].event_type == ExecutionEventType.DONE

    @pytest.mark.asyncio
    async def test_execute_sync(self, executor, agent_config):
        """測試同步執行方法"""
        messages = [{"role": "user", "content": "Sync test"}]

        result = await executor.execute_sync(
            agent_config=agent_config,
            messages=messages,
            session_id="sync-session",
        )

        assert isinstance(result, ExecutionResult)
        assert result.content == "Test response"
        assert result.finish_reason == "stop"
        assert result.execution_id != ""
        assert result.duration_ms >= 0


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """錯誤處理測試"""

    @pytest.mark.asyncio
    async def test_llm_error_handling(self, mock_tool_registry, agent_config):
        """測試 LLM 錯誤處理"""
        # 創建會拋出錯誤的 mock
        error_llm = MockLLMService()
        error_llm.generate = AsyncMock(side_effect=LLMServiceError("API Error"))

        executor = AgentExecutor(
            llm_service=error_llm,
            tool_registry=mock_tool_registry,
        )

        messages = [{"role": "user", "content": "Test"}]
        events = []

        async for event in executor.execute(
            agent_config=agent_config,
            messages=messages,
            session_id="error-session",
        ):
            events.append(event)

        # 應該有 started 和 error 事件
        assert events[0].event_type == ExecutionEventType.STARTED
        assert events[-1].event_type == ExecutionEventType.ERROR
        assert "API Error" in events[-1].error
        assert events[-1].error_code == "LLM_ERROR"

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, mock_tool_registry, agent_config):
        """測試意外錯誤處理"""
        error_llm = MockLLMService()
        error_llm.generate = AsyncMock(side_effect=RuntimeError("Unexpected"))

        executor = AgentExecutor(
            llm_service=error_llm,
            tool_registry=mock_tool_registry,
        )

        messages = [{"role": "user", "content": "Test"}]
        events = []

        async for event in executor.execute(
            agent_config=agent_config,
            messages=messages,
            session_id="unexpected-session",
        ):
            events.append(event)

        assert events[-1].event_type == ExecutionEventType.ERROR
        assert events[-1].error_code == "EXECUTION_ERROR"

    @pytest.mark.asyncio
    async def test_execute_sync_raises_on_error(self, mock_tool_registry, agent_config):
        """測試同步執行遇錯拋出異常"""
        error_llm = MockLLMService()
        error_llm.generate = AsyncMock(side_effect=LLMServiceError("Sync Error"))

        executor = AgentExecutor(
            llm_service=error_llm,
            tool_registry=mock_tool_registry,
        )

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(LLMServiceError) as exc_info:
            await executor.execute_sync(
                agent_config=agent_config,
                messages=messages,
                session_id="sync-error",
            )

        assert "Sync Error" in str(exc_info.value)


# =============================================================================
# Utility Method Tests
# =============================================================================


class TestUtilityMethods:
    """工具方法測試"""

    def test_get_tool_registry(self, executor, mock_tool_registry):
        """測試獲取 tool registry"""
        assert executor.get_tool_registry() is mock_tool_registry

    def test_get_mcp_client(self, mock_llm, mock_mcp_client):
        """測試獲取 MCP client"""
        executor = AgentExecutor(
            llm_service=mock_llm,
            mcp_client=mock_mcp_client,
        )
        assert executor.get_mcp_client() is mock_mcp_client

    def test_set_tool_registry(self, executor):
        """測試設置 tool registry"""
        new_registry = MockToolRegistry({"new_tool": MockTool("new_tool")})
        executor.set_tool_registry(new_registry)
        assert executor.get_tool_registry() is new_registry

    def test_set_mcp_client(self, executor):
        """測試設置 MCP client"""
        new_client = MockMCPClient([{"name": "new_mcp"}])
        executor.set_mcp_client(new_client)
        assert executor.get_mcp_client() is new_client


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """整合測試"""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self, mock_llm, mock_tool_registry, mock_mcp_client):
        """測試完整執行流程"""
        executor = AgentExecutor(
            llm_service=mock_llm,
            tool_registry=mock_tool_registry,
            mcp_client=mock_mcp_client,
        )

        config = AgentConfig(
            agent_id="full-test",
            name="Full Test Agent",
            instructions="You are a comprehensive test agent.",
            tools=["search", "mcp_tool1"],
            model_config={"temperature": 0.5},
            max_iterations=3,
        )

        messages = [
            ChatMessage(role=MessageRole.USER, content="First message"),
            ChatMessage(role=MessageRole.ASSISTANT, content="First response"),
            ChatMessage(role=MessageRole.USER, content="Second message"),
        ]

        result = await executor.execute_sync(
            agent_config=config,
            messages=messages,
            session_id="full-test-session",
        )

        # 驗證結果
        assert result.content == "Test response"
        assert result.finish_reason == "stop"

        # 驗證 LLM 被調用
        assert len(mock_llm.calls) == 1
        call = mock_llm.calls[0]
        assert "comprehensive test agent" in call["prompt"]

    @pytest.mark.asyncio
    async def test_multiple_executions(self, executor, agent_config):
        """測試多次執行"""
        for i in range(3):
            messages = [{"role": "user", "content": f"Message {i}"}]
            result = await executor.execute_sync(
                agent_config=agent_config,
                messages=messages,
                session_id=f"multi-{i}",
            )
            assert result.content == "Test response"

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, executor, agent_config):
        """測試並發執行"""
        async def run_execution(session_id: str):
            messages = [{"role": "user", "content": f"Concurrent {session_id}"}]
            return await executor.execute_sync(
                agent_config=agent_config,
                messages=messages,
                session_id=session_id,
            )

        # 並發執行 5 個請求
        tasks = [run_execution(f"concurrent-{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert result.content == "Test response"
