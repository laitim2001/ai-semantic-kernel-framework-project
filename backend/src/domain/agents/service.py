# =============================================================================
# IPA Platform - Agent Service
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Core service for Agent Framework operations.
# Handles agent creation, execution, and LLM interaction.
#
# Dependencies:
#   - Microsoft Agent Framework (agent_framework)
#   - Azure OpenAI (azure-identity)
# =============================================================================

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.config import get_settings

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
    GPT4O_INPUT_PRICE = 5.0
    GPT4O_OUTPUT_PRICE = 15.0

    def __init__(self) -> None:
        """Initialize AgentService."""
        self._settings = get_settings()
        self._initialized = False
        self._client: Optional[Any] = None

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """
        Initialize Azure OpenAI client.

        Connects to Azure OpenAI service using configured credentials.
        Should be called during application startup.

        Raises:
            RuntimeError: If Azure OpenAI is not configured
        """
        if self._initialized:
            logger.debug("AgentService already initialized")
            return

        if not self._settings.azure_openai_configured:
            logger.warning(
                "Azure OpenAI not configured. Agent execution will be unavailable."
            )
            self._initialized = True
            return

        try:
            # Import Agent Framework components
            from agent_framework.azure import AzureOpenAIChatClient
            from azure.identity import DefaultAzureCredential

            # Create Azure OpenAI client
            self._client = AzureOpenAIChatClient(
                credential=DefaultAzureCredential(),
                endpoint=self._settings.azure_openai_endpoint,
                deployment_name=self._settings.azure_openai_deployment_name,
            )

            self._initialized = True
            logger.info("AgentService initialized successfully")

        except ImportError as e:
            logger.error(f"Agent Framework import error: {e}")
            logger.warning("Running in mock mode - Agent Framework not available")
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize AgentService: {e}")
            raise RuntimeError(f"AgentService initialization failed: {e}")

    async def shutdown(self) -> None:
        """
        Shutdown the service and release resources.

        Should be called during application shutdown.
        """
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

        # If no client (Azure not configured), return mock response
        if self._client is None:
            logger.warning("No LLM client available, returning mock response")
            return AgentExecutionResult(
                text=f"[Mock Response] Agent '{config.name}' received: {message}",
                llm_calls=0,
                llm_tokens=0,
                llm_cost=0.0,
            )

        try:
            from agent_framework import AgentExecutor, ChatMessage, Role

            # Create agent with configuration
            agent = self._client.create_agent(
                name=config.name,
                instructions=config.instructions,
                tools=config.tools,
            )

            # Create executor
            executor = AgentExecutor(agent, id=config.name)

            # Prepare messages
            messages = [ChatMessage(role=Role.USER, content=message)]

            # Add context if provided
            if context:
                context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
                messages.insert(
                    0,
                    ChatMessage(
                        role=Role.SYSTEM,
                        content=f"Additional context:\n{context_str}",
                    ),
                )

            # Run agent
            response = await executor.agent.run(messages)

            # Extract statistics
            llm_calls = 1
            llm_tokens = 0
            prompt_tokens = 0
            completion_tokens = 0

            if hasattr(response, "usage"):
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
                completion_tokens = getattr(response.usage, "completion_tokens", 0)
                llm_tokens = prompt_tokens + completion_tokens

            llm_cost = self._calculate_cost(prompt_tokens, completion_tokens)

            # Extract tool calls if any
            tool_calls = []
            if hasattr(response, "tool_calls"):
                for tc in response.tool_calls or []:
                    tool_calls.append(
                        {
                            "tool": getattr(tc, "name", "unknown"),
                            "input": getattr(tc, "arguments", {}),
                            "output": getattr(tc, "result", None),
                        }
                    )

            return AgentExecutionResult(
                text=response.text if hasattr(response, "text") else str(response),
                llm_calls=llm_calls,
                llm_tokens=llm_tokens,
                llm_cost=llm_cost,
                tool_calls=tool_calls,
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

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self.initialize()
            if self._client is None:
                return False

            # Simple test call
            result = await self.run_simple(
                instructions="You are a test assistant.",
                message="Say 'OK' if you can hear me.",
            )
            return "OK" in result.upper()

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
