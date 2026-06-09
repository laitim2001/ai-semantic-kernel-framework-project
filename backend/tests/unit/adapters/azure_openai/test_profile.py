"""
File: backend/tests/unit/adapters/azure_openai/test_profile.py
Purpose: Unit tests for build_azure_model_profile (Sprint 57.97 cheap-tier builder).
Category: Tests / Adapters / Azure OpenAI
Scope: Phase 57 / Sprint 57.97

Created: 2026-06-09
"""

from __future__ import annotations

from typing import cast

import pytest

from adapters._base.chat_client import ChatClient
from adapters.azure_openai.adapter import AzureOpenAIAdapter
from adapters.azure_openai.profile import build_azure_model_profile


def test_unset_cheap_deployment_falls_back_to_action(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME → cheap IS the strong client (byte-identical)."""
    monkeypatch.delenv("AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME", raising=False)
    strong = cast(ChatClient, object())
    profile = build_azure_model_profile(strong)
    assert profile.action is strong
    assert profile.cheap is strong  # same instance, not a second adapter


def test_set_cheap_deployment_builds_distinct_cheap_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set cheap deployment → a distinct cheap AzureOpenAIAdapter with the cheap identity."""
    # The cheap adapter loads the shared connection from these (NOT passed by the builder).
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://placeholder.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "placeholder-key")
    monkeypatch.setenv("AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME", "cheap-deploy")
    monkeypatch.setenv("AZURE_OPENAI_CHEAP_MODEL_NAME", "cheap-model")

    strong = cast(ChatClient, object())
    profile = build_azure_model_profile(strong)

    assert profile.action is strong
    assert profile.cheap is not strong
    cheap = profile.cheap
    assert isinstance(cheap, AzureOpenAIAdapter)
    # The cheap adapter carries the cheap deployment + model name. The cost-ledger
    # attributes the verification call to the cheap model name (config/llm_pricing.yml
    # keyed by model), so the cheap identity is what makes the saving observable.
    assert cheap.config.deployment_name == "cheap-deploy"
    assert cheap.config.model_name == "cheap-model"


def test_set_cheap_deployment_defaults_model_name_to_deployment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When AZURE_OPENAI_CHEAP_MODEL_NAME is unset, model_name defaults to the deployment."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://placeholder.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "placeholder-key")
    monkeypatch.setenv("AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME", "mini-deploy")
    monkeypatch.delenv("AZURE_OPENAI_CHEAP_MODEL_NAME", raising=False)

    profile = build_azure_model_profile(cast(ChatClient, object()))
    cheap = profile.cheap
    assert isinstance(cheap, AzureOpenAIAdapter)
    assert cheap.config.deployment_name == "mini-deploy"
    assert cheap.config.model_name == "mini-deploy"  # falls back to the deployment name
