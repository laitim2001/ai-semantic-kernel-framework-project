"""
File: backend/tests/unit/infrastructure/vector/test_qdrant_namespace.py
Purpose: QdrantNamespaceStrategy tenant-aware naming + payload filter tests.
Category: Tests / Infrastructure / Vector
Scope: Sprint 49.3 Day 5.2

Tests:
    1. test_collection_name_per_tenant_unique
    2. test_collection_name_per_layer_unique
    3. test_payload_filter_contains_tenant_id

Created: 2026-04-29 (Sprint 49.3 Day 5.2)
"""

from __future__ import annotations

from uuid import uuid4

from infrastructure.vector import QdrantNamespaceStrategy


def test_collection_name_per_tenant_unique() -> None:
    """Two different tenants → different collection names (same layer)."""
    a, b = uuid4(), uuid4()
    name_a = QdrantNamespaceStrategy.collection_name(a, "user_memory")
    name_b = QdrantNamespaceStrategy.collection_name(b, "user_memory")
    assert name_a != name_b
    assert name_a.startswith("tenant_")
    assert name_a.endswith("_user_memory")
    assert "tenant_" in name_b


def test_collection_name_per_layer_unique() -> None:
    """Same tenant, different layers → different collection names."""
    t = uuid4()
    user_mem = QdrantNamespaceStrategy.collection_name(t, "user_memory")
    tenant_mem = QdrantNamespaceStrategy.collection_name(t, "tenant_memory")
    kb = QdrantNamespaceStrategy.collection_name(t, "kb")
    # All share the tenant prefix but distinct suffixes
    assert user_mem != tenant_mem != kb
    common_prefix = user_mem[: len("tenant_") + 16]  # tenant_ + 16 hex
    assert tenant_mem.startswith(common_prefix)
    assert kb.startswith(common_prefix)


def test_payload_filter_contains_tenant_id() -> None:
    """payload_filter must include a `must` clause with tenant_id match."""
    t = uuid4()
    f = QdrantNamespaceStrategy.payload_filter(t)
    assert "must" in f
    assert isinstance(f["must"], list) and len(f["must"]) >= 1
    clause = f["must"][0]
    assert clause["key"] == "tenant_id"
    assert clause["match"]["value"] == str(t)
