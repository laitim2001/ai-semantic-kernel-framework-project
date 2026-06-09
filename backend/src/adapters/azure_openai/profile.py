"""
File: backend/src/adapters/azure_openai/profile.py
Purpose: build_azure_model_profile — build the {action, cheap} ModelProfile for Azure.
Category: Adapters / Azure OpenAI
Scope: Phase 57 / Sprint 57.97

Description:
    Builds a ModelProfile pairing the (already-constructed) strong `action`
    Azure client with a `cheap` Azure client. The cheap client is a SECOND
    AzureOpenAIAdapter on AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME, reusing the SAME
    endpoint / api_key / api_version (loaded from the shared AZURE_OPENAI_* env)
    and overriding only the deployment + model name.

    Fallback: when AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME is unset, `cheap` IS the
    strong client (same instance) → byte-identical behavior. Safe to ship
    without a 2nd deployment.

    Cost attribution note: the cost-ledger (platform_layer/billing/cost_ledger.py)
    prices an LLM call via config/llm_pricing.yml keyed by (provider, model) — NOT
    by the adapter's config pricing field (which the cost-ledger ignores for the
    strong tier too). So the cheap tier's saving becomes visible in the cost-ledger
    purely because the cheap deployment returns its OWN model name: the verification
    call records a distinct `azure_openai_<cheap-model>_verification_*` sub_type
    (vs the main turn's `azure_openai_<strong-model>_*`). The model-attribution
    difference is visible regardless of pricing; for a $ delta, both the cheap and
    the strong model must be priced in config/llm_pricing.yml.

Key Components:
    - build_azure_model_profile(strong_client) -> ModelProfile

Created: 2026-06-09 (Sprint 57.97)
Last Modified: 2026-06-09

Modification History (newest-first):
    - 2026-06-09: Initial creation (Sprint 57.97) — Azure cheap-tier ModelProfile builder

Related:
    - adapters/_base/model_profile.py — the neutral ModelProfile type
    - api/v1/chat/handler.py — the sole caller (build_real_llm_handler)
    - platform_layer/billing/cost_ledger.py — prices via config/llm_pricing.yml (model-keyed)
    - 24-multi-model-profile-design.md — design note
"""

from __future__ import annotations

import os

from adapters._base.chat_client import ChatClient
from adapters._base.model_profile import ModelProfile
from adapters.azure_openai.adapter import AzureOpenAIAdapter
from adapters.azure_openai.config import AzureOpenAIConfig


def build_azure_model_profile(strong_client: ChatClient) -> ModelProfile:
    """Build the {action, cheap} ModelProfile for Azure.

    `strong_client` is the already-built action-tier adapter (== profile.action).
    The cheap tier is a 2nd Azure adapter on AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME
    (shared endpoint/key/api_version from env, overridden deployment + model name).
    When the cheap deployment env var is unset, `cheap` IS `strong_client` (the
    same instance) → byte-identical behavior.
    """
    cheap_deployment = os.environ.get("AZURE_OPENAI_CHEAP_DEPLOYMENT_NAME", "").strip()
    if not cheap_deployment:
        # No cheap tier configured → cheap IS the strong client (byte-identical).
        return ModelProfile(action=strong_client, cheap=strong_client)

    # The cheap config reuses the shared connection (endpoint / api_key /
    # api_version load from the SAME AZURE_OPENAI_* env — NOT passed here, so
    # BaseSettings loads them) and overrides only the deployment + model identity.
    # Explicit kwargs win over env in pydantic-settings, so the strong
    # AZURE_OPENAI_DEPLOYMENT_NAME is overridden by the cheap deployment for this
    # instance only. Cost is attributed via the model name in config/llm_pricing.yml
    # (see module docstring), not the adapter config pricing field.
    cheap_config = AzureOpenAIConfig(
        deployment_name=cheap_deployment,
        model_name=(
            os.environ.get("AZURE_OPENAI_CHEAP_MODEL_NAME", "").strip() or cheap_deployment
        ),
    )
    cheap_client: ChatClient = AzureOpenAIAdapter(cheap_config)
    return ModelProfile(action=strong_client, cheap=cheap_client)
