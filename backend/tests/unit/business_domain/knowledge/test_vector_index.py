"""
File: backend/tests/unit/business_domain/knowledge/test_vector_index.py
Purpose: Unit tests for KnowledgeVectorIndex (Sprint 57.146 base + 57.147 per-tenant isolation).
Category: Tests
Created: 2026-06-27
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from adapters._testing.embedding import DeterministicEmbeddingClient
from business_domain.knowledge.vector_index import KnowledgeVectorIndex
from infrastructure.vector.qdrant_client import VectorHit
from infrastructure.vector.qdrant_namespace import QdrantNamespaceStrategy


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class _FakeStore:
    """In-memory async stand-in for QdrantVectorStore (single collection — collection-agnostic)."""

    def __init__(self) -> None:
        self.points: list[tuple[int, list[float], dict[str, Any]]] = []
        self.dim: int | None = None

    async def count(self, name: str) -> int:
        return len(self.points)

    async def ensure_collection(self, name: str, dim: int) -> None:
        self.dim = dim

    async def recreate_collection(self, name: str, dim: int) -> None:
        self.points = []
        self.dim = dim

    async def upsert(
        self, name: str, points: list[tuple[int, list[float], dict[str, Any]]]
    ) -> None:
        self.points.extend(points)

    async def search(
        self,
        name: str,
        query_vector: list[float],
        top_k: int,
        payload_filter: Any = None,
    ) -> list[VectorHit]:
        ranked = sorted(self.points, key=lambda p: _cos(query_vector, p[1]), reverse=True)[:top_k]
        return [
            VectorHit(payload=payload, score=_cos(query_vector, vec))
            for (_, vec, payload) in ranked
        ]


class _PerCollectionFakeStore:
    """Collection-aware in-memory store: points keyed by collection name + honors payload_filter.

    Used by the per-tenant isolation tests (Sprint 57.147): tenant A's collection and
    tenant B's collection are physically separate, and search honors the tenant_id
    payload filter (defense-in-depth) the way real Qdrant does.
    """

    def __init__(self) -> None:
        self.collections: dict[str, list[tuple[int, list[float], dict[str, Any]]]] = {}

    async def count(self, name: str) -> int:
        return len(self.collections.get(name, []))

    async def ensure_collection(self, name: str, dim: int) -> None:
        self.collections.setdefault(name, [])

    async def recreate_collection(self, name: str, dim: int) -> None:
        self.collections[name] = []

    async def upsert(
        self, name: str, points: list[tuple[int, list[float], dict[str, Any]]]
    ) -> None:
        self.collections.setdefault(name, []).extend(points)

    async def search(
        self,
        name: str,
        query_vector: list[float],
        top_k: int,
        payload_filter: Any = None,
    ) -> list[VectorHit]:
        pts = self.collections.get(name, [])
        if payload_filter is not None:
            want = payload_filter["must"][0]["match"]["value"]
            pts = [p for p in pts if p[2].get("tenant_id") == want]
        ranked = sorted(pts, key=lambda p: _cos(query_vector, p[1]), reverse=True)[:top_k]
        return [
            VectorHit(payload=payload, score=_cos(query_vector, vec))
            for (_, vec, payload) in ranked
        ]


def _index(root: Path, store: Any, dim: int = 48) -> KnowledgeVectorIndex:
    return KnowledgeVectorIndex(DeterministicEmbeddingClient(dim=dim), cast(Any, store), root)


# --- Sprint 57.146 base behavior (tenant_id=None → shared collection) -----------


async def test_ingest_counts_sections() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, "doc.md", "## A\nbody a\n## B\nbody b\n")
        store = _FakeStore()
        assert await _index(root, store).ingest() == 2  # 2 sections (A, B)
        assert len(store.points) == 2


async def test_ingest_idempotent_skips_reembed() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, "doc.md", "## A\nbody a\n## B\nbody b\n")
        store = _FakeStore()
        index = _index(root, store)
        assert await index.ingest() == 2
        before = len(store.points)
        assert await index.ingest() == 2  # count matches → idempotent no-op
        assert len(store.points) == before  # not re-upserted


async def test_ingest_empty_corpus_returns_zero() -> None:
    with tempfile.TemporaryDirectory() as d:
        assert await _index(Path(d), _FakeStore()).ingest() == 0


async def test_search_exact_section_ranks_first() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, "doc.md", "# T\n## Alpha\nalpha body content\n## Beta\nbeta body content\n")
        store = _FakeStore()
        index = _index(root, store)
        await index.ingest()
        # Query with the EXACT Alpha section body → identical embedding → cosine 1.0 → first.
        hits = await index.search("## Alpha\nalpha body content", top_k=2)
        assert hits
        assert hits[0].source == "doc.md"
        assert "Alpha" in hits[0].snippet
        assert math.isclose(hits[0].score, 1.0, rel_tol=1e-6)


async def test_search_empty_query_returns_empty() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, "doc.md", "## A\nbody\n")
        assert await _index(root, _FakeStore()).search("   ") == []


class _CountingEmbedder:
    """Wraps the deterministic embedder + records each batch size (Sprint 57.146)."""

    def __init__(self, dim: int = 16) -> None:
        self._inner = DeterministicEmbeddingClient(dim=dim)
        self.batch_sizes: list[int] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.batch_sizes.append(len(texts))
        return await self._inner.embed(texts)

    def model_name(self) -> str:
        return "counting"


async def test_ingest_batches_embedding_calls() -> None:
    """Sprint 57.146 Day-3 fix: ingest embeds in _EMBED_BATCH chunks (one giant
    all-sections call returned HTTP 429 on the real embedding deployment)."""
    from business_domain.knowledge.vector_index import _EMBED_BATCH

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        n = _EMBED_BATCH + 4  # crosses the batch boundary → expect 2 calls
        _write(root, "big.md", "".join(f"## S{i}\nbody {i} content\n" for i in range(n)))
        store = _FakeStore()
        embedder = _CountingEmbedder()
        index = KnowledgeVectorIndex(cast(Any, embedder), cast(Any, store), root)
        assert await index.ingest() == n
        assert len(store.points) == n  # all sections upserted across batches
        assert embedder.batch_sizes == [_EMBED_BATCH, 4]  # batched, not one call


# --- Sprint 57.147 per-tenant isolation ----------------------------------------


async def test_ingest_is_per_tenant_collection() -> None:
    """A tenant_id ingests its <root>/<tenant>/ corpus into its OWN collection."""
    t_a = uuid4()
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, f"{t_a}/a.md", "## Alpha\nalpha unique body\n## Two\nsecond body\n")
        store = _PerCollectionFakeStore()
        index = _index(root, store)
        assert await index.ingest(tenant_id=t_a) == 2
        coll = QdrantNamespaceStrategy.collection_name(t_a, "kb")
        assert coll in store.collections
        assert len(store.collections[coll]) == 2
        # every point carries the tenant_id payload (defense-in-depth)
        assert all(p[2].get("tenant_id") == str(t_a) for p in store.collections[coll])


async def test_lazy_ingest_idempotent_per_tenant() -> None:
    """search() lazily ingests the tenant collection once; a second search does not re-embed."""
    t_a = uuid4()
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, f"{t_a}/a.md", "## Alpha\nalpha unique body content\n")
        store = _PerCollectionFakeStore()
        embedder = _CountingEmbedder(dim=32)
        index = KnowledgeVectorIndex(cast(Any, embedder), cast(Any, store), root)
        await index.search("alpha unique body content", top_k=3, tenant_id=t_a)
        batches_after_first = list(embedder.batch_sizes)
        await index.search("alpha unique body content", top_k=3, tenant_id=t_a)
        # second search: lazy ingest sees count==expected → skips re-embed; only the
        # per-search query embedding is added (one more batch of size 1), no corpus batch.
        assert embedder.batch_sizes == batches_after_first + [1]


async def test_tenant_a_cannot_retrieve_tenant_b_doc() -> None:
    """THE isolation proof: tenant A's search never returns tenant B's unique doc."""
    t_a, t_b = uuid4(), uuid4()
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, f"{t_a}/a.md", "## Alpha\nalpha unique content only tenant A has this\n")
        _write(root, f"{t_b}/b.md", "## Beta\nbeta unique content only tenant B has this\n")
        store = _PerCollectionFakeStore()
        index = _index(root, store)
        # tenant B ingests its corpus (e.g. B searched earlier)
        await index.search("beta unique content only tenant B has this", top_k=5, tenant_id=t_b)
        # tenant A searches for B's exact content → must get 0 of B's docs (own collection only)
        a_hits = await index.search(
            "beta unique content only tenant B has this", top_k=5, tenant_id=t_a
        )
        assert all(h.source != "b.md" for h in a_hits)
        # A only ever sees a.md (its own corpus)
        assert all(h.source == "a.md" for h in a_hits)
        # collections are physically separate
        coll_a = QdrantNamespaceStrategy.collection_name(t_a, "kb")
        coll_b = QdrantNamespaceStrategy.collection_name(t_b, "kb")
        assert coll_a in store.collections and coll_b in store.collections
        assert coll_a != coll_b


async def test_payload_filter_rejects_cross_tenant_row() -> None:
    """Defense-in-depth: a foreign-tenant payload in a collection is dropped by the filter."""
    t_a, t_b = uuid4(), uuid4()
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, f"{t_a}/a.md", "## Alpha\nshared phrasing here for both tenants alpha\n")
        store = _PerCollectionFakeStore()
        index = _index(root, store)
        await index.ingest(tenant_id=t_a)
        coll_a = QdrantNamespaceStrategy.collection_name(t_a, "kb")
        # Inject a rogue row stamped with tenant B into tenant A's collection.
        store.collections[coll_a].append(
            (999, [0.0] * 48, {"source": "leak.md", "snippet": "leak", "tenant_id": str(t_b)})
        )
        hits = await index.search(
            "shared phrasing here for both tenants alpha", top_k=10, tenant_id=t_a
        )
        # the payload filter (tenant_id == A) drops the rogue B-stamped row
        assert all(h.source != "leak.md" for h in hits)


async def test_tenant_id_none_uses_shared_collection() -> None:
    """tenant_id=None preserves the 57.146 shared-collection behavior."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root, "doc.md", "## A\nbody a\n")
        store = _PerCollectionFakeStore()
        index = _index(root, store)
        assert await index.ingest() == 1  # tenant_id omitted → None
        assert "knowledge_local_docs" in store.collections
