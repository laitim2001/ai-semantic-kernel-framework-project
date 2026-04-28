# =============================================================================
# IPA Platform - LLM Service Module
# =============================================================================
# Sprint 34: LLM 服務基礎設施
#
# 提供統一的 LLM 服務接口，支援 Azure OpenAI 整合。
#
# 主要組件:
#   - LLMServiceProtocol: LLM 服務協議（接口）
#   - AzureOpenAILLMService: Azure OpenAI 實現
#   - MockLLMService: 測試用 Mock 實現
#   - CachedLLMService: 緩存包裝器
#   - LLMServiceFactory: 服務工廠
#
# 使用方式:
#   from src.integrations.llm import LLMServiceFactory
#   service = LLMServiceFactory.create()
#   response = await service.generate("Hello!")
# =============================================================================

from .protocol import (
    LLMServiceProtocol,
    LLMServiceError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMParseError,
    LLMValidationError,
)
from .azure_openai import AzureOpenAILLMService
from .mock import MockLLMService
from .cached import CachedLLMService
from .factory import LLMServiceFactory

__all__ = [
    # Protocol
    "LLMServiceProtocol",
    # Exceptions
    "LLMServiceError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMParseError",
    "LLMValidationError",
    # Implementations
    "AzureOpenAILLMService",
    "MockLLMService",
    "CachedLLMService",
    # Factory
    "LLMServiceFactory",
]
