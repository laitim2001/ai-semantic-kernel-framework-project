"""adapters.azure_openai — Azure OpenAI ChatClient implementation. See README.md."""

from adapters.azure_openai.adapter import AzureOpenAIAdapter
from adapters.azure_openai.config import AzureOpenAIConfig
from adapters.azure_openai.error_mapper import AzureOpenAIErrorMapper

__all__ = [
    "AzureOpenAIAdapter",
    "AzureOpenAIConfig",
    "AzureOpenAIErrorMapper",
]
