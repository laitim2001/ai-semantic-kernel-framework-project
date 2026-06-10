"""
File: backend/src/adapters/_base/model_profile.py
Purpose: ModelProfile — pair ChatClient instances by role so phases run on different model tiers.
Category: Adapters / _base (provider-neutral model selection)
Scope: Phase 57 / Sprint 57.97

Description:
    A thin, provider-neutral value object pairing pre-constructed ChatClient
    instances by role. The ChatClient ABC fixes the model at CONSTRUCTION time
    (no per-call `model=` param — see 17.md §2.1), so multi-model selection means
    "build N clients upfront, pick by phase". ModelProfile IS that picker.

    This sprint wires only `cheap` (the verification / llm_judge call runs on a
    cheaper deployment than the user-facing `action` turn). Future tiers add a
    field (e.g. `compaction`, `thinking`) and the consuming factory reads it for
    its phase; there is deliberately NO per-call dispatch method (the ABC has no
    phase param) — callers read `.action` / `.cheap` directly at construction.

    Provider-neutral: references ONLY the ChatClient ABC; constructs nothing and
    imports no SDK. Concrete adapters are built in the api/ handler layer (which
    may import a provider adapter) — see adapters/azure_openai/profile.py.

Key Components:
    - ModelProfile: frozen dataclass {action, cheap}

Created: 2026-06-09 (Sprint 57.97)
Last Modified: 2026-06-09

Modification History (newest-first):
    - 2026-06-09: Initial creation (Sprint 57.97) — thin {action, cheap} model-tier pairing

Related:
    - adapters/_base/chat_client.py — the ChatClient ABC paired here (unchanged)
    - adapters/azure_openai/profile.py — the Azure builder (cheap tier construction)
    - 24-multi-model-profile-design.md — design note
    - 17-cross-category-interfaces.md §2.1 — ChatClient contract (this WRAPS it; no change)
"""

from __future__ import annotations

from dataclasses import dataclass

from adapters._base.chat_client import ChatClient


@dataclass(frozen=True)
class ModelProfile:
    """Pair ChatClient instances by role for per-phase model selection.

    `action` is the strong, user-facing tier (main turn, compaction, prompt
    building, subagents). `cheap` is a cheaper tier for cost-insensitive phases
    (this sprint: the verification / llm_judge call). When no cheap deployment is
    configured the builder sets `cheap is action` (the SAME instance) so behavior
    and cost are byte-identical.
    """

    action: ChatClient
    cheap: ChatClient
