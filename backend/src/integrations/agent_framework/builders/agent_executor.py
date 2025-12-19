# =============================================================================
# IPA Platform - Agent Executor Adapter
# =============================================================================
# Sprint 31: S31-2 - AgentExecutor 適配器創建
#
# 此適配器包裝 Microsoft Agent Framework 官方 API，提供：
#   - Azure OpenAI 客戶端初始化
#   - ChatAgent 創建和管理
#   - 訊息處理和執行追蹤
#
# 官方 API 參考:
#   - ChatAgent: 主要 Agent 抽象層
#   - ChatMessage/Role: 訊息格式
#   - AzureOpenAIResponsesClient: Azure 客戶端
#
# 遷移自: src/domain/agents/service.py
# =============================================================================

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# 配置資料類
# =============================================================================


@dataclass
class AgentExecutorConfig:
    """
    Agent 執行器配置。

    Attributes:
        name: Agent 識別名稱
        instructions: 系統提示詞 (System prompt)
        tools: 工具函數列表
        model_config: LLM 配置參數
        max_iterations: 最大推理迭代次數
    """

    name: str
    instructions: str
    tools: List[Callable] = field(default_factory=list)
    model_config: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 10


@dataclass
class AgentExecutorResult:
    """
    Agent 執行結果。

    Attributes:
        text: Agent 回應文本
        llm_calls: LLM API 呼叫次數
        llm_tokens: 使用的總 token 數
        llm_cost: 預估成本 (USD)
        tool_calls: 工具呼叫記錄列表
    """

    text: str
    llm_calls: int = 0
    llm_tokens: int = 0
    llm_cost: float = 0.0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# Agent 執行器適配器
# =============================================================================


class AgentExecutorAdapter:
    """
    Agent 執行器適配器 - 包裝官方 Microsoft Agent Framework API。

    此適配器將官方 ChatAgent API 集中管理，遵循項目架構規範：
    - 所有官方 API 導入集中於此適配器
    - 提供統一的執行接口
    - 支援 Azure OpenAI 和本地模型

    Usage:
        adapter = AgentExecutorAdapter(settings)
        await adapter.initialize()

        config = AgentExecutorConfig(
            name="support-agent",
            instructions="You are a helpful assistant...",
        )
        result = await adapter.execute(config, "Hello!")

    Official API:
        - ChatAgent: agent_framework.ChatAgent
        - ChatMessage: agent_framework.ChatMessage
        - Role: agent_framework.Role
        - AzureOpenAIResponsesClient: agent_framework.azure.AzureOpenAIResponsesClient
    """

    # GPT-4o 定價 (USD per million tokens)
    GPT4O_INPUT_PRICE = 5.0
    GPT4O_OUTPUT_PRICE = 15.0

    def __init__(self, settings: Any) -> None:
        """
        初始化 Agent 執行器適配器。

        Args:
            settings: 應用程式設定物件 (需包含 Azure 配置)
        """
        self._settings = settings
        self._initialized = False
        self._client: Optional[Any] = None
        self._chat_agent_class: Optional[type] = None
        self._chat_message_class: Optional[type] = None
        self._role_class: Optional[type] = None

    @property
    def is_initialized(self) -> bool:
        """檢查適配器是否已初始化。"""
        return self._initialized

    @property
    def has_client(self) -> bool:
        """檢查是否有可用的 LLM 客戶端。"""
        return self._client is not None

    async def initialize(self) -> None:
        """
        初始化 Azure OpenAI 客戶端。

        連接 Azure OpenAI 服務並快取官方 API 類別。
        應在應用程式啟動時呼叫。

        Raises:
            RuntimeError: 如果初始化失敗
        """
        if self._initialized:
            logger.debug("AgentExecutorAdapter already initialized")
            return

        # 檢查 Azure 配置
        azure_configured = getattr(self._settings, "azure_openai_configured", False)
        if not azure_configured:
            logger.warning(
                "Azure OpenAI not configured. Agent execution will use mock mode."
            )
            self._initialized = True
            return

        try:
            # 導入官方 Agent Framework API
            from agent_framework import ChatAgent, ChatMessage, Role
            from agent_framework.azure import AzureOpenAIResponsesClient
            from azure.identity import DefaultAzureCredential

            # 快取類別引用
            self._chat_agent_class = ChatAgent
            self._chat_message_class = ChatMessage
            self._role_class = Role

            # 創建 Azure OpenAI 客戶端
            endpoint = getattr(self._settings, "azure_openai_endpoint", None)
            deployment = getattr(self._settings, "azure_openai_deployment_name", None)

            self._client = AzureOpenAIResponsesClient(
                endpoint=endpoint,
                deployment_name=deployment,
                credential=DefaultAzureCredential(),
            )

            self._initialized = True
            logger.info("AgentExecutorAdapter initialized with Azure OpenAI")

        except ImportError as e:
            logger.error(f"Agent Framework import error: {e}")
            logger.warning("Running in mock mode - Agent Framework not installed")
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize AgentExecutorAdapter: {e}")
            raise RuntimeError(f"AgentExecutorAdapter initialization failed: {e}")

    async def shutdown(self) -> None:
        """
        關閉適配器並釋放資源。

        應在應用程式關閉時呼叫。
        """
        self._client = None
        self._chat_agent_class = None
        self._chat_message_class = None
        self._role_class = None
        self._initialized = False
        logger.info("AgentExecutorAdapter shutdown complete")

    def _ensure_initialized(self) -> None:
        """確保適配器已初始化。"""
        if not self._initialized:
            raise RuntimeError(
                "AgentExecutorAdapter not initialized. Call initialize() first."
            )

    def _calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        計算 LLM 使用成本。

        使用 GPT-4o 定價：
            - 輸入: $5 per million tokens
            - 輸出: $15 per million tokens

        Args:
            prompt_tokens: 輸入 token 數
            completion_tokens: 輸出 token 數

        Returns:
            預估成本 (USD)
        """
        input_cost = (prompt_tokens / 1_000_000) * self.GPT4O_INPUT_PRICE
        output_cost = (completion_tokens / 1_000_000) * self.GPT4O_OUTPUT_PRICE
        return input_cost + output_cost

    def create_message(
        self,
        content: str,
        role: str = "user",
    ) -> Any:
        """
        創建 ChatMessage 實例。

        Args:
            content: 訊息內容
            role: 角色類型 ("user", "assistant", "system", "tool")

        Returns:
            ChatMessage 實例

        Raises:
            RuntimeError: 如果適配器未初始化或在 mock 模式
        """
        self._ensure_initialized()

        if self._chat_message_class is None or self._role_class is None:
            raise RuntimeError("Agent Framework not available (mock mode)")

        role_map = {
            "user": self._role_class.USER,
            "assistant": self._role_class.ASSISTANT,
            "system": self._role_class.SYSTEM,
            "tool": self._role_class.TOOL,
        }

        role_enum = role_map.get(role.lower(), self._role_class.USER)
        return self._chat_message_class(role=role_enum, content=content)

    def create_agent(
        self,
        config: AgentExecutorConfig,
    ) -> Any:
        """
        創建 ChatAgent 實例。

        Args:
            config: Agent 配置

        Returns:
            ChatAgent 實例

        Raises:
            RuntimeError: 如果適配器未初始化或客戶端不可用
        """
        self._ensure_initialized()

        if self._client is None:
            raise RuntimeError("No LLM client available")

        if self._chat_agent_class is None:
            raise RuntimeError("Agent Framework not available (mock mode)")

        # 使用官方 API 創建 Agent
        return self._chat_agent_class(
            chat_client=self._client,
            name=config.name,
            instructions=config.instructions,
            tools=config.tools if config.tools else None,
        )

    def _create_client_from_config(
        self,
        model_config: Dict[str, Any],
    ) -> Optional[Any]:
        """
        根據 Agent 的 model_config 創建 LLM 客戶端。

        Args:
            model_config: Agent 的模型配置

        Returns:
            LLM 客戶端實例或 None
        """
        provider = model_config.get("provider", "azure_openai")

        if provider == "azure_openai":
            endpoint = model_config.get("azure_endpoint")
            deployment = model_config.get("azure_deployment_name")
            api_key = model_config.get("api_key")
            api_version = model_config.get("azure_api_version", "2024-10-21")

            if not endpoint or not deployment or not api_key:
                logger.warning(
                    f"Azure OpenAI config incomplete: endpoint={bool(endpoint)}, "
                    f"deployment={bool(deployment)}, api_key={bool(api_key)}"
                )
                return None

            try:
                from openai import AzureOpenAI

                client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version,
                )
                logger.info(f"Created Azure OpenAI client for deployment: {deployment}")
                return client

            except ImportError:
                logger.error("openai package not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to create Azure OpenAI client: {e}")
                return None

        elif provider == "openai":
            api_key = model_config.get("api_key")
            base_url = model_config.get("base_url")

            if not api_key:
                logger.warning("OpenAI API key not provided")
                return None

            try:
                from openai import OpenAI

                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url if base_url else None,
                )
                logger.info("Created OpenAI client")
                return client

            except ImportError:
                logger.error("openai package not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to create OpenAI client: {e}")
                return None

        else:
            logger.warning(f"Unsupported provider: {provider}")
            return None

    async def execute(
        self,
        config: AgentExecutorConfig,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutorResult:
        """
        使用給定配置執行 Agent。

        創建臨時 Agent 並執行訊息處理，追蹤 LLM 使用統計。
        優先使用 Agent 自己的 model_config，否則回退到全局配置。

        Args:
            config: Agent 配置
            message: 使用者訊息
            context: 可選的額外上下文

        Returns:
            AgentExecutorResult 包含回應和統計資訊

        Raises:
            RuntimeError: 如果服務未初始化或執行失敗
        """
        self._ensure_initialized()

        # 優先使用 Agent 自己的 model_config 創建客戶端
        agent_client = None
        model_config = config.model_config

        if model_config and model_config.get("api_key"):
            agent_client = self._create_client_from_config(model_config)
            if agent_client:
                logger.info(f"Using Agent-specific LLM client for: {config.name}")

        # 如果沒有 Agent 特定客戶端，使用全局客戶端
        client_to_use = agent_client if agent_client else self._client

        # Mock 模式回應
        if client_to_use is None:
            logger.warning("No LLM client available, returning mock response")
            return AgentExecutorResult(
                text=f"[Mock Response] Agent '{config.name}' received: {message}",
                llm_calls=0,
                llm_tokens=0,
                llm_cost=0.0,
            )

        try:
            # 如果使用 Agent 特定客戶端 (OpenAI SDK)，直接調用
            if agent_client is not None:
                return await self._execute_with_openai_client(
                    client=agent_client,
                    config=config,
                    message=message,
                    context=context,
                )

            # 否則使用 Agent Framework 官方 API
            agent = self.create_agent(config)

            # 準備訊息列表
            messages = []

            # 添加上下文 (如果提供)
            if context:
                context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
                context_message = self.create_message(
                    content=f"Additional context:\n{context_str}",
                    role="system",
                )
                messages.append(context_message)

            # 添加使用者訊息
            user_message = self.create_message(content=message, role="user")
            messages.append(user_message)

            # 執行 Agent (使用官方 run API)
            response = await agent.run(message)

            # 提取統計資訊
            llm_calls = 1
            llm_tokens = 0
            prompt_tokens = 0
            completion_tokens = 0

            if hasattr(response, "usage") and response.usage:
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
                completion_tokens = getattr(response.usage, "completion_tokens", 0)
                llm_tokens = prompt_tokens + completion_tokens

            llm_cost = self._calculate_cost(prompt_tokens, completion_tokens)

            # 提取工具呼叫 (如果有)
            tool_calls = []
            if hasattr(response, "tool_calls") and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append(
                        {
                            "tool": getattr(tc, "name", "unknown"),
                            "input": getattr(tc, "arguments", {}),
                            "output": getattr(tc, "result", None),
                        }
                    )

            # 提取回應文本
            response_text = (
                response.text if hasattr(response, "text") else str(response)
            )

            return AgentExecutorResult(
                text=response_text,
                llm_calls=llm_calls,
                llm_tokens=llm_tokens,
                llm_cost=llm_cost,
                tool_calls=tool_calls,
            )

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise RuntimeError(f"Agent execution failed: {e}")

    async def _execute_with_openai_client(
        self,
        client: Any,
        config: AgentExecutorConfig,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutorResult:
        """
        使用 OpenAI SDK 直接執行聊天。

        Args:
            client: OpenAI 或 AzureOpenAI 客戶端
            config: Agent 配置
            message: 使用者訊息
            context: 可選的額外上下文

        Returns:
            AgentExecutorResult
        """
        # 準備訊息
        messages = []

        # 系統訊息 (Agent 指令)
        if config.instructions:
            messages.append({
                "role": "system",
                "content": config.instructions,
            })

        # 添加上下文
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            messages.append({
                "role": "system",
                "content": f"Additional context:\n{context_str}",
            })

        # 使用者訊息
        messages.append({
            "role": "user",
            "content": message,
        })

        # 獲取模型配置
        model_config = config.model_config
        model = model_config.get("azure_deployment_name") or model_config.get("model", "gpt-4o")
        temperature = model_config.get("temperature", 0.7)
        # 新版 OpenAI API 使用 max_completion_tokens 而非 max_tokens
        max_completion_tokens = model_config.get("max_completion_tokens") or model_config.get("max_tokens", 2000)

        # 某些模型（如 o1 系列、推理模型）不支持 temperature 和 max_completion_tokens
        # 檢測是否是推理模型並調整參數
        is_reasoning_model = any(
            pattern in model.lower()
            for pattern in ["o1", "o3", "o4", "gpt-5", "reasoning"]
        )

        try:
            # 調用 OpenAI API - 根據模型類型調整參數
            if is_reasoning_model:
                # 推理模型只支持少量參數
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_completion_tokens,
                )
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_completion_tokens,
                )

            # 提取統計資訊
            llm_calls = 1
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            llm_tokens = prompt_tokens + completion_tokens
            llm_cost = self._calculate_cost(prompt_tokens, completion_tokens)

            # 提取回應文本
            response_text = response.choices[0].message.content if response.choices else ""

            logger.info(
                f"Agent '{config.name}' executed: "
                f"tokens={llm_tokens}, cost=${llm_cost:.6f}"
            )

            return AgentExecutorResult(
                text=response_text,
                llm_calls=llm_calls,
                llm_tokens=llm_tokens,
                llm_cost=llm_cost,
                tool_calls=[],
            )

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise RuntimeError(f"OpenAI API call failed: {e}")

    async def execute_simple(
        self,
        instructions: str,
        message: str,
        tools: Optional[List[Callable]] = None,
    ) -> str:
        """
        簡化的 Agent 執行接口。

        創建臨時 Agent 並執行，僅回傳回應文本。

        Args:
            instructions: Agent 系統提示詞
            message: 使用者訊息
            tools: 可選的工具列表

        Returns:
            Agent 回應文本
        """
        config = AgentExecutorConfig(
            name="simple-agent",
            instructions=instructions,
            tools=tools or [],
        )
        result = await self.execute(config, message)
        return result.text

    async def test_connection(self) -> bool:
        """
        測試 Azure OpenAI 連接。

        Returns:
            True 如果連接成功，False 否則
        """
        try:
            await self.initialize()
            if self._client is None:
                return False

            result = await self.execute_simple(
                instructions="You are a test assistant.",
                message="Say 'OK' if you can hear me.",
            )
            return "OK" in result.upper()

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# =============================================================================
# 工廠函數
# =============================================================================


def create_agent_executor_adapter(settings: Any) -> AgentExecutorAdapter:
    """
    創建 AgentExecutorAdapter 實例。

    Args:
        settings: 應用程式設定物件

    Returns:
        AgentExecutorAdapter 實例
    """
    return AgentExecutorAdapter(settings)


async def create_initialized_adapter(settings: Any) -> AgentExecutorAdapter:
    """
    創建並初始化 AgentExecutorAdapter。

    Args:
        settings: 應用程式設定物件

    Returns:
        已初始化的 AgentExecutorAdapter 實例
    """
    adapter = AgentExecutorAdapter(settings)
    await adapter.initialize()
    return adapter


# =============================================================================
# 全域適配器實例 (單例模式)
# =============================================================================

_agent_executor_adapter: Optional[AgentExecutorAdapter] = None


def get_agent_executor_adapter() -> Optional[AgentExecutorAdapter]:
    """
    取得全域 AgentExecutorAdapter 實例。

    Returns:
        AgentExecutorAdapter 實例或 None (如果未初始化)
    """
    return _agent_executor_adapter


def set_agent_executor_adapter(adapter: AgentExecutorAdapter) -> None:
    """
    設定全域 AgentExecutorAdapter 實例。

    Args:
        adapter: AgentExecutorAdapter 實例
    """
    global _agent_executor_adapter
    _agent_executor_adapter = adapter
