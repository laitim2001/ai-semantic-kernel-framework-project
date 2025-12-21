# =============================================================================
# IPA Platform - LLM Service Factory
# =============================================================================
# Sprint 34: S34-2 LLM Service Factory (5 points)
#
# Factory for creating LLM service instances with proper configuration.
# Provides centralized service creation and dependency injection support.
#
# Features:
#   - Configuration-based service creation
#   - Automatic caching wrapper
#   - Mock service for testing
#   - Singleton pattern for efficiency
# =============================================================================

import logging
import os
from typing import Any, Dict, Optional

from .protocol import LLMServiceProtocol
from .azure_openai import AzureOpenAILLMService
from .mock import MockLLMService
from .cached import CachedLLMService

logger = logging.getLogger(__name__)


class LLMServiceFactory:
    """LLM 服務工廠。

    提供統一的 LLM 服務創建接口，支援多種後端和配置選項。

    Example:
        ```python
        # 創建預設服務（根據環境配置）
        service = LLMServiceFactory.create()

        # 創建帶緩存的服務
        service = LLMServiceFactory.create(use_cache=True)

        # 創建測試用 Mock 服務
        service = LLMServiceFactory.create_mock()

        # 使用自定義配置
        service = LLMServiceFactory.create(
            provider="azure",
            deployment_name="gpt-4o",
            max_retries=5,
        )
        ```
    """

    # 單例緩存
    _instances: Dict[str, LLMServiceProtocol] = {}

    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        use_cache: bool = False,
        cache_ttl: int = 3600,
        singleton: bool = True,
        **kwargs: Any,
    ) -> LLMServiceProtocol:
        """創建 LLM 服務實例。

        Args:
            provider: 提供者類型 ("azure", "mock")，如為 None 則自動檢測
            use_cache: 是否啟用緩存
            cache_ttl: 緩存 TTL（秒）
            singleton: 是否使用單例模式
            **kwargs: 傳遞給服務構造函數的額外參數

        Returns:
            LLMServiceProtocol 實例

        Raises:
            ValueError: 當提供者未知時
        """
        # 自動檢測提供者
        if provider is None:
            provider = cls._detect_provider()

        # 生成單例鍵
        cache_key = f"{provider}:{use_cache}:{cache_ttl}"

        # 檢查單例
        if singleton and cache_key in cls._instances:
            logger.debug(f"Returning singleton LLM service: {cache_key}")
            return cls._instances[cache_key]

        # 創建服務
        if provider == "azure":
            service = cls._create_azure_service(**kwargs)
        elif provider == "mock":
            service = cls._create_mock_service(**kwargs)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

        # 包裝緩存
        if use_cache:
            service = cls._wrap_with_cache(service, cache_ttl)

        # 存儲單例
        if singleton:
            cls._instances[cache_key] = service

        logger.info(f"Created LLM service: provider={provider}, cache={use_cache}")
        return service

    @classmethod
    def create_mock(
        cls,
        responses: Optional[Dict[str, str]] = None,
        default_response: str = "Mock LLM response",
        latency: float = 0.0,
        **kwargs: Any,
    ) -> MockLLMService:
        """創建 Mock LLM 服務。

        便捷方法，專門用於創建測試用的 Mock 服務。

        Args:
            responses: 回應字典
            default_response: 預設回應
            latency: 模擬延遲
            **kwargs: 額外參數

        Returns:
            MockLLMService 實例
        """
        return MockLLMService(
            responses=responses,
            default_response=default_response,
            latency=latency,
            **kwargs,
        )

    @classmethod
    def create_for_testing(
        cls,
        structured_responses: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> MockLLMService:
        """創建測試專用的 Mock 服務。

        預配置了常用的測試回應模式。

        Args:
            structured_responses: 額外的結構化回應

        Returns:
            預配置的 MockLLMService 實例
        """
        default_structured = {
            # TaskDecomposer 回應
            r"decompos|break.*down|split.*task": {
                "subtasks": [
                    {"name": "Subtask 1", "description": "First step", "priority": 1},
                    {"name": "Subtask 2", "description": "Second step", "priority": 2},
                ],
                "confidence": 0.85,
                "strategy": "sequential",
            },
            # DecisionEngine 回應
            r"decide|choose|select|decision": {
                "selected_option": "Option A",
                "reasoning": "Based on the analysis, Option A provides the best balance.",
                "confidence": 0.8,
                "risk_assessment": {
                    "risk_level": "medium",
                    "mitigations": ["Monitor closely", "Have fallback ready"],
                },
            },
            # TrialAndErrorEngine 回應
            r"error|fail|retry|learn": {
                "error_analysis": "The failure was caused by invalid input format.",
                "root_cause": "Input validation",
                "suggested_fix": "Add input validation before processing.",
                "parameter_adjustments": {"timeout": 30, "retries": 3},
                "confidence": 0.75,
            },
        }

        if structured_responses:
            default_structured.update(structured_responses)

        return MockLLMService(
            structured_responses=default_structured,
            default_response="This is a test LLM response.",
        )

    @classmethod
    def _detect_provider(cls) -> str:
        """自動檢測 LLM 提供者。

        根據環境變量決定使用哪個提供者。

        Returns:
            提供者名稱
        """
        # 檢查是否有 Azure OpenAI 配置
        if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
            return "azure"

        # 檢查測試環境
        if os.getenv("TESTING") == "true" or os.getenv("LLM_MOCK") == "true":
            return "mock"

        # 預設使用 mock（避免意外調用真實 API）
        logger.warning(
            "No LLM provider configured. Using mock service. "
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY for real LLM."
        )
        return "mock"

    @classmethod
    def _create_azure_service(cls, **kwargs: Any) -> AzureOpenAILLMService:
        """創建 Azure OpenAI 服務。

        Args:
            **kwargs: 服務參數

        Returns:
            AzureOpenAILLMService 實例
        """
        return AzureOpenAILLMService(
            endpoint=kwargs.get("endpoint"),
            api_key=kwargs.get("api_key"),
            deployment_name=kwargs.get("deployment_name"),
            api_version=kwargs.get("api_version", "2024-02-01"),
            max_retries=kwargs.get("max_retries", 3),
            timeout=kwargs.get("timeout", 60.0),
        )

    @classmethod
    def _create_mock_service(cls, **kwargs: Any) -> MockLLMService:
        """創建 Mock 服務。

        Args:
            **kwargs: 服務參數

        Returns:
            MockLLMService 實例
        """
        return MockLLMService(
            responses=kwargs.get("responses"),
            default_response=kwargs.get("default_response", "Mock LLM response"),
            latency=kwargs.get("latency", 0.0),
            structured_responses=kwargs.get("structured_responses"),
        )

    @classmethod
    def _wrap_with_cache(
        cls,
        service: LLMServiceProtocol,
        ttl: int,
    ) -> CachedLLMService:
        """為服務添加緩存包裝。

        Args:
            service: 原始服務
            ttl: 緩存 TTL

        Returns:
            CachedLLMService 實例
        """
        # 嘗試獲取 Redis 連接
        cache = cls._get_redis_cache()

        return CachedLLMService(
            inner_service=service,
            cache=cache,
            default_ttl=ttl,
            enabled=cache is not None,
        )

    @classmethod
    def _get_redis_cache(cls) -> Optional[Any]:
        """獲取 Redis 緩存連接。

        Returns:
            Redis 客戶端，如不可用則返回 None
        """
        redis_host = os.getenv("REDIS_HOST")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD")

        if not redis_host:
            logger.debug("Redis not configured, cache disabled")
            return None

        try:
            from redis import Redis

            cache = Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
            )
            # 測試連接
            cache.ping()
            logger.debug(f"Redis cache connected: {redis_host}:{redis_port}")
            return cache
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, cache disabled")
            return None

    @classmethod
    def clear_instances(cls) -> None:
        """清除所有單例實例。

        用於測試清理。
        """
        cls._instances.clear()
        logger.debug("LLMServiceFactory instances cleared")

    @classmethod
    def get_instance_count(cls) -> int:
        """獲取單例實例數量。

        Returns:
            實例數量
        """
        return len(cls._instances)
