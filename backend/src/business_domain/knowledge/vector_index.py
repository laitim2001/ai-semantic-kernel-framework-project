"""
File: backend/src/business_domain/knowledge/vector_index.py
Purpose: KnowledgeVectorIndex — per-tenant Qdrant embedding + semantic search over the docs corpus.
Category: Business domain / knowledge (Cat 2 Tools — semantic retrieval)
Scope: Phase 57 / Sprint 57.147

Description:
    Semantic retrieval over the real .md/.txt corpus the keyword connector reads.
    Composes a provider-neutral EmbeddingClient (the ABC, NOT a concrete adapter —
    neutrality) + a QdrantVectorStore + a per-tenant LocalDocsConnector. ingest()
    chunks each doc into ## sections, batch-embeds the section bodies, and upserts
    them; search() embeds the query and returns cosine-ranked KnowledgeHit(s).

    Sprint 57.147 (per-tenant isolation): a tenant_id arg threads through search /
    ingest. Each tenant gets its OWN Qdrant collection (QdrantNamespaceStrategy
    "kb" layer) + a defense-in-depth tenant_id payload filter, fed by a per-tenant
    docs subfolder <root>/<tenant_id>/ (falling back to the shared root when no
    subfolder exists). tenant_id=None preserves the 57.146 single shared-collection
    behavior byte-for-byte (the keyword fallback path stays shared). Ingest is lazy:
    search() ensures the tenant's collection is populated (idempotent — skipped when
    the count already matches), so no startup-blocking all-tenant ingest is needed.

Key Components:
    - KnowledgeVectorIndex: search(query, top_k, tenant_id) + ingest(tenant_id) (idempotent)

Created: 2026-06-27 (Sprint 57.146)
Last Modified: 2026-06-27

Modification History (newest-first):
    - 2026-06-27: Sprint 57.147 — per-tenant collection + filter + corpus subfolder + lazy ingest
    - 2026-06-27: Initial creation (Sprint 57.146) — embedding/Qdrant semantic index
      (AD-Knowledge-Connector-First-Real-Source Slice 2)

Related:
    - adapters/_base/embedding_client.py — EmbeddingClient ABC
    - infrastructure/vector/qdrant_client.py — QdrantVectorStore
    - infrastructure/vector/qdrant_namespace.py — per-tenant naming + payload filter
    - chunking.py — section unit · connector.py — KnowledgeHit + file source
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from adapters._base.embedding_client import EmbeddingClient
from infrastructure.vector.qdrant_client import QdrantVectorStore
from infrastructure.vector.qdrant_namespace import QdrantNamespaceStrategy

from .chunking import split_sections
from .connector import KnowledgeHit, LocalDocsConnector

logger = logging.getLogger(__name__)

# Shared collection name when no tenant_id is supplied (57.146 behavior preserved).
_DEFAULT_COLLECTION = "knowledge_local_docs"
# Embed in small batches so a one-shot ingest of the whole corpus stays under the
# embedding deployment's tokens-per-minute quota. A single all-sections request
# returns HTTP 429 (Sprint 57.146 Day-3 drive-through finding); 16 sections
# (~6k tokens) per call fits comfortably and the SDK retries any residual 429.
_EMBED_BATCH = 16


class KnowledgeVectorIndex:
    """Embeds doc sections into per-tenant Qdrant collections + answers semantic queries.

    Sprint 57.147: tenant_id threads through search / ingest. Per tenant → its own
    collection (`tenant_<hex>_kb`) + payload filter + corpus subfolder. tenant_id=None
    → the shared `knowledge_local_docs` collection over the root (57.146 behavior).
    """

    def __init__(
        self,
        embedder: EmbeddingClient,
        store: QdrantVectorStore,
        docs_root: Path | str,
    ) -> None:
        self._embedder = embedder
        self._store = store
        # Base root; the per-tenant connector is resolved at ingest/search time so a
        # single process-wide index serves every tenant (collection/corpus by tenant_id).
        self._docs_root = Path(docs_root)

    # --- per-tenant resolution -------------------------------------------------
    def _collection_for(self, tenant_id: UUID | None) -> str:
        """Per-tenant Qdrant collection name, or the shared collection when tenant_id is None."""
        if tenant_id is None:
            return _DEFAULT_COLLECTION
        return QdrantNamespaceStrategy.collection_name(tenant_id, "kb")

    def _connector_for(self, tenant_id: UUID | None) -> LocalDocsConnector:
        """Resolve the corpus connector: <root>/<tenant_id>/ when it exists, else the shared root.

        Per-tenant subfolders give each tenant a distinct corpus (the isolation
        drive-through becomes falsifiable: tenant A cannot retrieve tenant B's
        unique doc). A tenant with no subfolder falls back to the shared root, so
        a single-corpus deployment behaves exactly like 57.146.
        """
        if tenant_id is not None:
            per_tenant = self._docs_root / str(tenant_id)
            if per_tenant.is_dir():
                return LocalDocsConnector(per_tenant)
        return LocalDocsConnector(self._docs_root)

    def _sections(self, connector: LocalDocsConnector) -> list[tuple[str, str]]:
        """Return (source_rel, section_body) pairs across every doc under the connector's root."""
        pairs: list[tuple[str, str]] = []
        for path in connector.list_files():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = path.relative_to(connector.root).as_posix()
            for section in split_sections(text):
                pairs.append((rel, section.body))
        return pairs

    async def ingest(self, tenant_id: UUID | None = None) -> int:
        """Embed the tenant's sections + upsert into its collection. Idempotent. Returns count.

        Skips re-embedding when the collection already holds the expected count.
        Otherwise recreates the collection (clean dim on a corpus / model change)
        and upserts. Each point's payload carries the tenant_id so the search-time
        payload filter rejects any cross-tenant row (defense-in-depth on top of the
        per-tenant collection name). Sections are embedded in `_EMBED_BATCH`-sized
        batches to stay under the deployment's TPM quota.
        """
        collection = self._collection_for(tenant_id)
        connector = self._connector_for(tenant_id)
        pairs = self._sections(connector)
        if not pairs:
            return 0
        expected = len(pairs)
        if await self._store.count(collection) == expected:
            return expected  # already ingested — idempotent no-op
        bodies = [body for _, body in pairs]
        vectors: list[list[float]] = []
        for start in range(0, len(bodies), _EMBED_BATCH):
            vectors.extend(await self._embedder.embed(bodies[start : start + _EMBED_BATCH]))
        if not vectors:
            return 0
        dim = len(vectors[0])
        await self._store.recreate_collection(collection, dim)
        # Defense-in-depth: stamp tenant_id into every payload so payload_filter
        # rejects a foreign-tenant row even if a query somehow hit the wrong collection.
        tenant_payload = {"tenant_id": str(tenant_id)} if tenant_id is not None else {}
        points = [
            (idx, vectors[idx], {"source": src, "snippet": body, **tenant_payload})
            for idx, (src, body) in enumerate(pairs)
        ]
        await self._store.upsert(collection, points)
        logger.info(
            "knowledge vector index ingested %d sections (tenant=%s)",
            expected,
            tenant_id if tenant_id is not None else "shared",
        )
        return expected

    async def search(
        self,
        query: str,
        top_k: int = 5,
        tenant_id: UUID | None = None,
    ) -> list[KnowledgeHit]:
        """Embed the query → tenant's Qdrant collection cosine top-k → KnowledgeHit per section.

        Lazily ensures the tenant's collection is ingested first (idempotent). The
        search is scoped to the tenant's collection AND carries the tenant_id payload
        filter — two independent isolation mechanisms (QdrantNamespaceStrategy).
        """
        if not query.strip():
            return []
        await self.ingest(tenant_id)  # lazy per-tenant ensure (idempotent skip when populated)
        collection = self._collection_for(tenant_id)
        payload_filter = (
            QdrantNamespaceStrategy.payload_filter(tenant_id) if tenant_id is not None else None
        )
        vectors = await self._embedder.embed([query])
        if not vectors:
            return []
        hits = await self._store.search(
            collection, vectors[0], top_k=top_k, payload_filter=payload_filter
        )
        return [
            KnowledgeHit(
                source=str(hit.payload.get("source", "")),
                snippet=str(hit.payload.get("snippet", "")),
                score=round(float(hit.score), 3),
            )
            for hit in hits
        ]


__all__ = ["KnowledgeVectorIndex"]
