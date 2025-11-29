"""
Semantic Kernel Service

封裝 Microsoft Semantic Kernel SDK,提供 LLM 推理能力和插件架構
"""
import logging
import time
import traceback
from typing import Dict, Any, Optional, List
from decimal import Decimal

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig

from src.core.config import settings
from src.domain.executions.error_schemas import ErrorType
from src.domain.executions.retry_policy import RetryPolicy, RetryConfig

logger = logging.getLogger(__name__)


class SemanticKernelConfig:
    """Semantic Kernel 配置類別"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        deployment_name: Optional[str] = None
    ):
        self.endpoint = endpoint or settings.azure_openai_endpoint
        self.api_key = api_key or settings.azure_openai_api_key
        self.api_version = api_version or settings.azure_openai_api_version
        self.deployment_name = deployment_name or settings.azure_openai_deployment_name

        # 驗證必要配置
        if not all([self.endpoint, self.api_key, self.deployment_name]):
            raise ValueError(
                "Azure OpenAI configuration incomplete. Required: "
                "endpoint, api_key, deployment_name"
            )

    def to_dict(self) -> dict:
        """轉換為字典 (隱藏 API key)"""
        return {
            "endpoint": self.endpoint,
            "api_version": self.api_version,
            "deployment_name": self.deployment_name,
            "api_key": "***" if self.api_key else None
        }


class LLMExecutionResult:
    """LLM 執行結果"""

    def __init__(
        self,
        output: str,
        tokens_used: int,
        prompt_tokens: int,
        completion_tokens: int,
        cost: Decimal,
        duration_ms: int,
        model: str,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        self.output = output
        self.tokens_used = tokens_used
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost = cost
        self.duration_ms = duration_ms
        self.model = model
        self.success = success
        self.error_message = error_message

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "output": self.output,
            "tokens_used": self.tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost": float(self.cost),
            "duration_ms": self.duration_ms,
            "model": self.model,
            "success": self.success,
            "error_message": self.error_message
        }


class SemanticKernelService:
    """
    Semantic Kernel 服務封裝

    提供:
    - Azure OpenAI 連接管理
    - LLM 推理執行
    - Plugin 架構支援
    - Token 使用量和成本追蹤
    - 錯誤處理和重試機制
    """

    # Azure OpenAI Pricing (USD per 1M tokens, 2024-02)
    PRICING_TABLE = {
        "gpt-4": {"input": Decimal("2.50"), "output": Decimal("10.00")},
        "gpt-4-32k": {"input": Decimal("5.00"), "output": Decimal("15.00")},
        "gpt-4-turbo": {"input": Decimal("10.00"), "output": Decimal("30.00")},
        "gpt-35-turbo": {"input": Decimal("0.50"), "output": Decimal("1.50")},
        "gpt-35-turbo-16k": {"input": Decimal("0.75"), "output": Decimal("2.25")},
    }

    def __init__(self, config: Optional[SemanticKernelConfig] = None):
        """
        初始化 Semantic Kernel Service

        Args:
            config: Semantic Kernel 配置,若為 None 則使用預設 settings
        """
        self.config = config or SemanticKernelConfig()
        self.kernel: Optional[Kernel] = None
        self.service_id = "azure-chat-gpt"
        self.retry_policy = RetryPolicy(
            RetryConfig(
                max_retries=3,
                base_delay_ms=1000,
                max_delay_ms=10000,
                jitter=True
            )
        )

        # 初始化 Kernel
        self._initialize_kernel()

        logger.info(
            f"SemanticKernelService initialized: {self.config.to_dict()}"
        )

    def _initialize_kernel(self) -> None:
        """初始化 Semantic Kernel"""
        try:
            self.kernel = Kernel()

            # 配置 Azure OpenAI Chat Completion
            self.kernel.add_service(
                AzureChatCompletion(
                    service_id=self.service_id,
                    deployment_name=self.config.deployment_name,
                    endpoint=self.config.endpoint,
                    api_key=self.config.api_key,
                    api_version=self.config.api_version
                )
            )

            logger.info(
                f"Kernel initialized with deployment: {self.config.deployment_name}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Kernel: {str(e)}")
            raise

    async def execute_prompt(
        self,
        prompt: str,
        variables: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0
    ) -> LLMExecutionResult:
        """
        執行 Prompt 並返回結果

        Args:
            prompt: Prompt 模板或內容
            variables: Prompt 變數字典
            max_tokens: 最大生成 tokens
            temperature: 溫度參數 (0-2)
            top_p: Top-p 採樣
            frequency_penalty: 頻率懲罰 (-2.0 to 2.0)
            presence_penalty: 存在懲罰 (-2.0 to 2.0)

        Returns:
            LLMExecutionResult: 執行結果包含輸出、token 使用量、成本等

        Raises:
            Exception: LLM 調用失敗
        """
        start_time = time.time()
        variables = variables or {}

        try:
            # 渲染 Prompt (替換變數)
            rendered_prompt = self._render_prompt(prompt, variables)

            logger.debug(f"Executing prompt (length: {len(rendered_prompt)})")

            # 建立 ChatHistory
            chat_history = ChatHistory()
            chat_history.add_user_message(rendered_prompt)

            # 執行設定
            execution_settings = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty
            }

            # 調用 Kernel
            response = await self.kernel.invoke_prompt(
                prompt="{{$chat_history}}",
                arguments={"chat_history": chat_history},
                **execution_settings
            )

            # 提取結果
            output_text = str(response)

            # 提取 metadata (token 使用量)
            metadata = getattr(response, "metadata", {})
            usage = metadata.get("usage", {})

            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            # 計算成本和時長
            duration_ms = int((time.time() - start_time) * 1000)
            cost = self._calculate_cost(
                prompt_tokens,
                completion_tokens,
                self.config.deployment_name
            )

            logger.info(
                f"LLM call success: tokens={total_tokens}, "
                f"cost=${float(cost):.4f}, duration={duration_ms}ms"
            )

            return LLMExecutionResult(
                output=output_text,
                tokens_used=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                duration_ms=duration_ms,
                model=self.config.deployment_name,
                success=True
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = f"LLM call failed: {str(e)}"

            logger.error(
                f"{error_message}\n{traceback.format_exc()}",
                extra={"duration_ms": duration_ms}
            )

            return LLMExecutionResult(
                output="",
                tokens_used=0,
                prompt_tokens=0,
                completion_tokens=0,
                cost=Decimal("0"),
                duration_ms=duration_ms,
                model=self.config.deployment_name,
                success=False,
                error_message=error_message
            )

    def _render_prompt(self, prompt: str, variables: Dict[str, Any]) -> str:
        """
        渲染 Prompt 模板 (替換變數)

        支援簡單的 {{variable}} 語法

        Args:
            prompt: Prompt 模板
            variables: 變數字典

        Returns:
            渲染後的 Prompt
        """
        rendered = prompt

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"

            # 將值轉換為字串
            if isinstance(value, (dict, list)):
                import json
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)

            rendered = rendered.replace(placeholder, value_str)

        return rendered

    def _calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str
    ) -> Decimal:
        """
        計算 LLM 調用成本

        Args:
            prompt_tokens: 輸入 tokens
            completion_tokens: 輸出 tokens
            model_name: 模型名稱

        Returns:
            成本 (USD)
        """
        # 標準化模型名稱 (移除版本後綴)
        model_key = model_name.lower()
        for key in self.PRICING_TABLE.keys():
            if key in model_key:
                model_key = key
                break

        # 獲取價格
        pricing = self.PRICING_TABLE.get(
            model_key,
            {"input": Decimal("2.50"), "output": Decimal("10.00")}  # 預設 GPT-4 pricing
        )

        # 計算成本 (per 1M tokens)
        input_cost = (Decimal(str(prompt_tokens)) / Decimal("1000000")) * pricing["input"]
        output_cost = (Decimal(str(completion_tokens)) / Decimal("1000000")) * pricing["output"]

        total_cost = input_cost + output_cost

        return total_cost.quantize(Decimal("0.000001"))  # 6 位小數

    def register_plugin(self, plugin: Any, plugin_name: str) -> None:
        """
        註冊 Plugin 到 Kernel

        Args:
            plugin: Plugin 實例
            plugin_name: Plugin 名稱
        """
        try:
            self.kernel.add_plugin(plugin, plugin_name=plugin_name)
            logger.info(f"Plugin '{plugin_name}' registered successfully")

        except Exception as e:
            logger.error(f"Failed to register plugin '{plugin_name}': {str(e)}")
            raise

    async def execute_with_plugin(
        self,
        plugin_name: str,
        function_name: str,
        **kwargs
    ) -> Any:
        """
        執行 Plugin Function

        Args:
            plugin_name: Plugin 名稱
            function_name: Function 名稱
            **kwargs: Function 參數

        Returns:
            Function 執行結果
        """
        try:
            result = await self.kernel.invoke(
                plugin_name=plugin_name,
                function_name=function_name,
                **kwargs
            )

            logger.info(f"Plugin function executed: {plugin_name}.{function_name}")
            return result

        except Exception as e:
            logger.error(
                f"Failed to execute plugin function '{plugin_name}.{function_name}': {str(e)}"
            )
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        執行簡單的 LLM 調用驗證連接狀態

        Returns:
            健康狀態字典
        """
        try:
            result = await self.execute_prompt(
                prompt="Say 'OK' if you can hear me.",
                max_tokens=10,
                temperature=0.0
            )

            return {
                "status": "healthy" if result.success else "unhealthy",
                "deployment": self.config.deployment_name,
                "endpoint": self.config.endpoint,
                "response_time_ms": result.duration_ms,
                "error": result.error_message
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "deployment": self.config.deployment_name,
                "endpoint": self.config.endpoint,
                "error": str(e)
            }
