"""
File: backend/tests/unit/adapters/azure_openai/test_pricing.py
Purpose: Verify get_pricing() reflects config + has correct invariants.
Category: Tests / Adapters / Azure OpenAI
Scope: Phase 49 / Sprint 49.4
"""

from __future__ import annotations

from adapters._base.pricing import PricingInfo
from adapters.azure_openai.adapter import AzureOpenAIAdapter
from adapters.azure_openai.config import AzureOpenAIConfig


def test_pricing_reflects_config(azure_adapter: AzureOpenAIAdapter) -> None:
    info = azure_adapter.get_pricing()
    assert info.input_per_million == 2.5
    assert info.output_per_million == 10.0
    assert info.cached_input_per_million == 1.25


def test_pricing_invariants(azure_adapter: AzureOpenAIAdapter) -> None:
    info = azure_adapter.get_pricing()
    # output should be more expensive than input (provider economics)
    assert info.output_per_million > info.input_per_million
    if info.cached_input_per_million is not None:
        assert info.cached_input_per_million < info.input_per_million


def test_pricing_currency_default() -> None:
    info = PricingInfo(input_per_million=1.0, output_per_million=2.0)
    assert info.currency == "USD"


def test_pricing_no_caching_provider() -> None:
    """Adapter for a provider without caching should report cached_input as None."""
    cfg = AzureOpenAIConfig(
        api_key="x",
        endpoint="https://x.openai.azure.com/",
        deployment_name="d",
        pricing_input_per_million=1.0,
        pricing_output_per_million=2.0,
        pricing_cached_input_per_million=None,
    )
    adapter = AzureOpenAIAdapter(config=cfg)
    info = adapter.get_pricing()
    assert info.cached_input_per_million is None
