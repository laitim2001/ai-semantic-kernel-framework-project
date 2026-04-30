"""
File: backend/tests/unit/adapters/azure_openai/conftest.py
Purpose: Shared fixtures for Azure OpenAI adapter tests.
Category: Tests / Adapters
Scope: Phase 49 / Sprint 49.4

Description:
    Builds:
    - azure_config: AzureOpenAIConfig with non-real placeholder values for
      tests that don't actually call Azure (token counting / pricing /
      capability / error mapping).
    - azure_adapter: AzureOpenAIAdapter built from azure_config.
    - sample_request: small ChatRequest for happy-path tests.

Created: 2026-04-29 (Sprint 49.4)
"""

from __future__ import annotations

import pytest

from adapters.azure_openai.adapter import AzureOpenAIAdapter
from adapters.azure_openai.config import AzureOpenAIConfig
from agent_harness._contracts import ChatRequest, Message
from agent_harness._contracts.tools import ToolSpec


@pytest.fixture
def azure_config() -> AzureOpenAIConfig:
    return AzureOpenAIConfig(
        api_key="placeholder-key",
        endpoint="https://placeholder.openai.azure.com/",
        api_version="2024-02-15-preview",
        deployment_name="gpt-5-4-deployment",
        model_name="gpt-4o",
        model_family="gpt",
        context_window=128_000,
        max_output_tokens=16_384,
        pricing_input_per_million=2.5,
        pricing_output_per_million=10.0,
        pricing_cached_input_per_million=1.25,
    )


@pytest.fixture
def azure_adapter(azure_config: AzureOpenAIConfig) -> AzureOpenAIAdapter:
    return AzureOpenAIAdapter(config=azure_config)


@pytest.fixture
def sample_messages() -> list[Message]:
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is 2 + 2?"),
    ]


@pytest.fixture
def sample_tool() -> ToolSpec:
    return ToolSpec(
        name="add",
        description="Add two numbers",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )


@pytest.fixture
def sample_request(sample_messages: list[Message]) -> ChatRequest:
    return ChatRequest(messages=sample_messages, temperature=0.0)
