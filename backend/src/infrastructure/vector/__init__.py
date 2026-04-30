"""
infrastructure.vector — Vector DB namespace + adapter abstractions.

Sprint 49.3 Day 5.1 ships only the namespace strategy:
    - QdrantNamespaceStrategy: tenant-aware collection naming + payload filter

Phase 51.2 (範疇 3 Memory) will add the actual Qdrant client integration
(connection / upsert / search) on top of this abstraction.

The namespace strategy enforces tenant isolation at TWO layers
(defense-in-depth):
    1. Per-tenant collection name prefix (storage-level partitioning)
    2. payload tenant_id `must` filter on every search (query-level safety)

Even if a future bug picks the wrong collection, the payload filter
still rejects cross-tenant payloads. Conversely, if payload metadata
is missing, the per-tenant collection prevents accidental mixing.
"""

from __future__ import annotations

from infrastructure.vector.qdrant_namespace import QdrantNamespaceStrategy

__all__ = ["QdrantNamespaceStrategy"]
