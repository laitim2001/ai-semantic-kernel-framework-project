# =============================================================================
# IPA Platform - Agent Service
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
# Sprint 31: S31-2 - 遷移至使用 AgentExecutorAdapter
#
# Core service for Agent Framework operations.
# Handles agent creation, execution, and LLM interaction.
#
# 架構更新 (Sprint 31):
#   - 所有官方 Agent Framework API 導入已移至 AgentExecutorAdapter
#   - 此服務層現在透過適配器呼叫官方 API
#   - 符合項目架構規範: 官方 API 集中於 integrations 層
#
# Dependencies:
#   - AgentExecutorAdapter (src.integrations.agent_framework.builders)
# =============================================================================

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.core.config import get_settings
from src.integrations.agent_framework.builders import (
    AgentExecutorAdapter,
    AgentExecutorConfig,
    AgentExecutorResult as AdapterResult,
    create_agent_executor_adapter,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """
    Agent configuration for creating executors.

    Attributes:
        name: Agent identifier
        instructions: System prompt/instructions
        tools: List of tool functions
        model_config: LLM configuration (temperature, etc.)
        max_iterations: Maximum reasoning iterations
    """

    name: str
    instructions: str
    tools: List[Callable] = field(default_factory=list)
    model_config: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 10


@dataclass
class AgentExecutionResult:
    """
    Result of agent execution.

    Attributes:
        text: Agent response text
        llm_calls: Number of LLM API calls
        llm_tokens: Total tokens used
        llm_cost: Estimated cost in USD
        tool_calls: List of tool invocations
    """

    text: str
    llm_calls: int = 0
    llm_tokens: int = 0
    llm_cost: float = 0.0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)


class AgentService:
    """
    Agent Service - Wraps Microsoft Agent Framework operations.

    Provides high-level interface for:
        - Initializing Azure OpenAI connection
        - Creating agent executors
        - Running agents with message input
        - Tracking LLM usage and costs

    Usage:
        service = AgentService()
        await service.initialize()

        config = AgentConfig(
            name="support-agent",
            instructions="You are a helpful assistant...",
        )
        result = await service.run_agent_with_config(config, "Hello!")
    """

    # GPT-4o pricing (USD per million tokens)
    # 注意: 實際計算已委託給 AgentExecutorAdapter
    GPT4O_INPUT_PRICE = 5.0
    GPT4O_OUTPUT_PRICE = 15.0

    def __init__(self) -> None:
        """Initialize AgentService."""
        self._settings = get_settings()
        self._initialized = False
        # Sprint 31: 使用適配器取代直接的官方 API 客戶端
        self._adapter: Optional[AgentExecutorAdapter] = None
        # 保留 _client 屬性以維持向後兼容性
        self._client: Optional[Any] = None

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    @property
    def adapter(self) -> Optional[AgentExecutorAdapter]:
        """Get the underlying adapter instance."""
        return self._adapter

    async def initialize(self) -> None:
        """
        Initialize Agent service via AgentExecutorAdapter.

        透過 AgentExecutorAdapter 連接 Azure OpenAI 服務。
        應在應用程式啟動時呼叫。

        架構更新 (Sprint 31):
            - 所有官方 API 導入現在集中在 AgentExecutorAdapter
            - 此服務層透過適配器呼叫官方 API

        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            logger.debug("AgentService already initialized")
            return

        try:
            # Sprint 31: 透過適配器初始化 (官方 API 集中於適配器層)
            self._adapter = create_agent_executor_adapter(self._settings)
            await self._adapter.initialize()

            # 設定 _client 為 adapter 的客戶端引用以維持向後兼容
            if self._adapter.has_client:
                self._client = self._adapter  # 代理至適配器

            self._initialized = True
            logger.info("AgentService initialized via AgentExecutorAdapter")

        except Exception as e:
            logger.error(f"Failed to initialize AgentService: {e}")
            raise RuntimeError(f"AgentService initialization failed: {e}")

    async def shutdown(self) -> None:
        """
        Shutdown the service and release resources.

        Should be called during application shutdown.
        """
        # Sprint 31: 透過適配器關閉
        if self._adapter:
            await self._adapter.shutdown()
            self._adapter = None
        self._client = None
        self._initialized = False
        logger.info("AgentService shutdown complete")

    def _ensure_initialized(self) -> None:
        """Ensure service is initialized."""
        if not self._initialized:
            raise RuntimeError("AgentService not initialized. Call initialize() first.")

    def _calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate LLM cost based on token usage.

        Uses GPT-4o pricing:
            - Input: $5 per million tokens
            - Output: $15 per million tokens

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (prompt_tokens / 1_000_000) * self.GPT4O_INPUT_PRICE
        output_cost = (completion_tokens / 1_000_000) * self.GPT4O_OUTPUT_PRICE
        return input_cost + output_cost

    async def run_agent_with_config(
        self,
        config: AgentConfig,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionResult:
        """
        Run an agent with the given configuration.

        Creates a temporary agent executor and runs it with the message.
        Tracks LLM usage statistics for cost monitoring.

        架構更新 (Sprint 31):
            - 官方 API 呼叫已委託給 AgentExecutorAdapter
            - 此方法透過適配器執行，不再直接導入 agent_framework

        Args:
            config: Agent configuration
            message: User message to process
            context: Optional additional context

        Returns:
            AgentExecutionResult with response and statistics

        Raises:
            RuntimeError: If service not initialized or client unavailable
        """
        self._ensure_initialized()

        # Sprint 31: 透過適配器執行 (官方 API 集中於適配器層)
        if self._adapter is None:
            logger.warning("No adapter available, returning mock response")
            return AgentExecutionResult(
                text=f"[Mock Response] Agent '{config.name}' received: {message}",
                llm_calls=0,
                llm_tokens=0,
                llm_cost=0.0,
            )

        try:
            # 轉換配置格式
            adapter_config = AgentExecutorConfig(
                name=config.name,
                instructions=config.instructions,
                tools=config.tools,
                model_config=config.model_config,
                max_iterations=config.max_iterations,
            )

            # 透過適配器執行 (官方 API 呼叫在適配器內部)
            adapter_result = await self._adapter.execute(
                config=adapter_config,
                message=message,
                context=context,
            )

            # 轉換結果格式以維持向後兼容
            return AgentExecutionResult(
                text=adapter_result.text,
                llm_calls=adapter_result.llm_calls,
                llm_tokens=adapter_result.llm_tokens,
                llm_cost=adapter_result.llm_cost,
                tool_calls=adapter_result.tool_calls,
            )

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise RuntimeError(f"Agent execution failed: {e}")

    async def run_simple(
        self,
        instructions: str,
        message: str,
        tools: Optional[List[Callable]] = None,
    ) -> str:
        """
        Simple interface for running an agent.

        Creates a temporary agent with given instructions and runs it.
        Returns only the response text.

        Args:
            instructions: Agent system prompt
            message: User message
            tools: Optional list of tools

        Returns:
            Agent response text
        """
        config = AgentConfig(
            name="simple-agent",
            instructions=instructions,
            tools=tools or [],
        )
        result = await self.run_agent_with_config(config, message)
        return result.text

    async def test_connection(self) -> bool:
        """
        Test Azure OpenAI connection.

        架構更新 (Sprint 31):
            - 透過 AgentExecutorAdapter 進行連接測試

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self.initialize()
            # Sprint 31: 使用適配器進行連接測試
            if self._adapter is None:
                return False

            return await self._adapter.test_connection()

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global service instance (singleton pattern)
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """
    Get or create the global AgentService instance.

    Returns:
        AgentService singleton instance
    """
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service


async def init_agent_service() -> AgentService:
    """
    Initialize and return the global AgentService.

    Returns:
        Initialized AgentService instance
    """
    service = get_agent_service()
    await service.initialize()
    return service
