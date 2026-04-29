"""
File: backend/src/adapters/_base/pricing.py
Purpose: PricingInfo dataclass — LLM-provider-neutral cost metadata.
Category: Adapters (LLM provider boundary; per 10-server-side-philosophy.md §原則 2)
Scope: Phase 49 / Sprint 49.4

Description:
    Cost metadata returned by ChatClient.get_pricing(). Used by:
    - Cat 4 (Context Mgmt): token budget cost estimation
    - Cat 8 (Error Handling): rate-limit / quota classification
    - Cat 12 (Observability): cost-per-request metric (llm_cost_usd)
    - Cost optimization layer (Phase 50+): provider routing by cost

    Single-source per 17.md §1 (returned by ChatClient ABC §2.1).

Owner: 10-server-side-philosophy.md §原則 2
Single-source: 17.md §2.1 (`ChatClient.get_pricing()`)

Created: 2026-04-29 (Sprint 49.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4) — extracted from chat_client.py for SoC

Related:
    - chat_client.py — ChatClient ABC consumer
    - adapters-layer.md (.claude/rules/) — provider onboarding SOP
    - 17-cross-category-interfaces.md §2.1 row `ChatClient`
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PricingInfo:
    """ChatClient.get_pricing() returns this. USD per 1M tokens.

    Adapters populate from their provider's published pricing. When provider
    raises rates, adapter version + pricing must be bumped together (no silent
    drift).
    """

    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None  # None = provider has no caching
    currency: Literal["USD"] = "USD"
