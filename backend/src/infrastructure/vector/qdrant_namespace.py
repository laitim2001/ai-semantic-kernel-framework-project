"""
File: backend/src/infrastructure/vector/qdrant_namespace.py
Purpose: Tenant-aware Qdrant collection naming + payload filter rules.
Category: Infrastructure / Vector (範疇 3 Memory schema layer; Phase 51.2 will use)
Scope: Sprint 49.3 (Day 5.1 - Qdrant namespace abstraction)
Owner: infrastructure/vector owner

Description:
    Phase 51.2 (Memory layer) will use Qdrant for vector embeddings of
    memory_tenant / memory_user / KB content. To preserve multi-tenancy
    at the vector store layer, we enforce TWO independent isolation
    rules (defense-in-depth):

      1. Collection naming  → per-tenant per-layer prefix
         e.g. "tenant_<uuid_short>_user_memory"

      2. Payload filter     → every search includes
         {"must": [{"key": "tenant_id", "match": {"value": "<uuid>"}}]}

    Even if a future query bug picks a wrong collection, the payload
    filter still rejects mismatched tenant payloads. Conversely, if
    payload metadata is missing or malformed, the per-tenant collection
    prevents accidental cross-tenant mixing.

    Sprint 49.3 ships only the strategy class; no Qdrant client
    integration. Phase 51.2 will add upsert / search / scroll wrappers
    that consume this strategy.

    NOTE on uuid_short: we take the first 16 hex chars (8 bytes) of the
    canonical UUID string with hyphens removed. That gives 2^64 distinct
    collection prefixes — a collision is astronomically unlikely for any
    realistic tenant count, and the full tenant_id is still embedded in
    the payload filter for absolute safety.

Created: 2026-04-29 (Sprint 49.3 Day 5.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 5.1)

Related:
    - 09-db-schema-design.md memory_tenant.vector_id / memory_user.vector_id
    - 14-security-deep-dive.md §multi-tenant data isolation
    - sprint-49-3-plan.md §4 Qdrant Namespace
    - Phase 51.2 will integrate the Qdrant client on top of this.
"""

from __future__ import annotations

from typing import Any, Final, Literal
from uuid import UUID

# Allowed memory layer names. Phase 51.2 may extend this; for 49.3 the
# 5 memory tables in 09-db-schema-design.md cover the foreseeable set.
MemoryLayer = Literal[
    "user_memory",  # memory_user.vector_id
    "tenant_memory",  # memory_tenant.vector_id
    "session_memory",  # short-lived per-session embeddings
    "kb",  # knowledge base / RAG content
]

# Length of the tenant prefix taken from the UUID hex (without hyphens).
# 16 hex chars = 8 bytes = 2^64 distinct values; collision-resistant.
_TENANT_PREFIX_LEN: Final[int] = 16


class QdrantNamespaceStrategy:
    """Stateless helper for tenant-aware Qdrant naming + filtering.

    All methods are @staticmethod — there is no per-instance state.
    Phase 51.2's QdrantClient wrapper will call these to construct
    collection names + payload filters.
    """

    @staticmethod
    def collection_name(tenant_id: UUID, layer: MemoryLayer) -> str:
        """Build a per-tenant per-layer Qdrant collection name.

        Format: ``tenant_<16-hex>_<layer>``

        Args:
            tenant_id: tenant UUID (canonical form; hyphens stripped).
            layer: which memory layer this collection holds.

        Returns:
            Lower-case, hyphen-free, qdrant-safe collection name.
        """
        prefix = str(tenant_id).replace("-", "")[:_TENANT_PREFIX_LEN]
        return f"tenant_{prefix}_{layer}"

    @staticmethod
    def payload_filter(tenant_id: UUID) -> dict[str, Any]:
        """Build a Qdrant `Filter` payload that ensures tenant_id match.

        Used as defense-in-depth on top of collection naming. Every
        search/scroll/delete should include this filter so that even a
        wrong-collection query returns no foreign-tenant rows.

        Returns:
            dict in Qdrant filter shape: ``{"must": [{"key": "tenant_id",
            "match": {"value": "<uuid>"}}]}``
        """
        return {
            "must": [
                {"key": "tenant_id", "match": {"value": str(tenant_id)}},
            ]
        }


__all__ = ["MemoryLayer", "QdrantNamespaceStrategy"]
