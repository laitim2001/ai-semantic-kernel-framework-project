"""Vector Store Manager — Qdrant collection management for knowledge.

Manages vector collections for the knowledge base, supporting
create, index, search, and delete operations.

Sprint 118 — Phase 38 E2E Assembly C.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "knowledge_base"


@dataclass
class IndexedDocument:
    """A document chunk stored in the vector index."""

    doc_id: str
    content: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class VectorStoreManager:
    """Manages Qdrant vector collections for knowledge storage.

    Provides collection lifecycle management and CRUD operations
    for document vectors.

    Args:
        collection_name: Default collection to operate on.
        qdrant_path: Path for local Qdrant storage.
    """

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        qdrant_path: str = "./qdrant_data",
    ) -> None:
        self._collection = collection_name
        self._qdrant_path = qdrant_path
        self._client: Any = None
        self._initialized = False
        # In-memory fallback store
        self._memory_store: Dict[str, List[IndexedDocument]] = {}

    async def initialize(self, dimension: int = 3072) -> None:
        """Initialise Qdrant client and ensure collection exists."""
        if self._initialized:
            return
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            self._client = QdrantClient(path=self._qdrant_path)
            # Ensure collection exists
            collections = self._client.get_collections().collections
            names = [c.name for c in collections]
            if self._collection not in names:
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
                )
                logger.info("VectorStore: created collection '%s' (dim=%d)", self._collection, dimension)
            self._initialized = True
            logger.info("VectorStore: Qdrant initialized at %s", self._qdrant_path)
        except ImportError:
            logger.warning("VectorStore: qdrant_client not installed, using in-memory fallback")
            self._initialized = True
        except Exception as e:
            logger.error("VectorStore: Qdrant init failed: %s", e)
            self._initialized = True

    async def index_documents(
        self,
        documents: List[IndexedDocument],
        collection: Optional[str] = None,
    ) -> int:
        """Index a batch of documents into the vector store."""
        await self.initialize()
        col = collection or self._collection
        indexed = 0

        if self._client:
            try:
                from qdrant_client.models import PointStruct
                points = [
                    PointStruct(
                        id=doc.doc_id if doc.doc_id.isdigit() else str(uuid.uuid4().int)[:16],
                        vector=doc.embedding,
                        payload={"content": doc.content, **doc.metadata},
                    )
                    for doc in documents
                ]
                self._client.upsert(collection_name=col, points=points)
                indexed = len(points)
            except Exception as e:
                logger.error("VectorStore: indexing failed: %s", e)
        else:
            # In-memory fallback
            if col not in self._memory_store:
                self._memory_store[col] = []
            self._memory_store[col].extend(documents)
            indexed = len(documents)

        logger.info("VectorStore: indexed %d documents in '%s'", indexed, col)
        return indexed

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        collection: Optional[str] = None,
        score_threshold: float = 0.0,
    ) -> List[IndexedDocument]:
        """Search for similar documents by embedding vector."""
        await self.initialize()
        col = collection or self._collection

        if self._client:
            try:
                results = self._client.search(
                    collection_name=col,
                    query_vector=query_embedding,
                    limit=limit,
                    score_threshold=score_threshold,
                )
                return [
                    IndexedDocument(
                        doc_id=str(r.id),
                        content=r.payload.get("content", ""),
                        score=r.score,
                        metadata={k: v for k, v in r.payload.items() if k != "content"},
                    )
                    for r in results
                ]
            except Exception as e:
                logger.error("VectorStore: search failed: %s", e)

        # In-memory fallback — return all (no similarity)
        docs = self._memory_store.get(col, [])
        return docs[:limit]

    async def delete_collection(self, collection: Optional[str] = None) -> bool:
        """Delete an entire collection."""
        col = collection or self._collection
        if self._client:
            try:
                self._client.delete_collection(collection_name=col)
                logger.info("VectorStore: deleted collection '%s'", col)
                return True
            except Exception as e:
                logger.error("VectorStore: delete failed: %s", e)
        self._memory_store.pop(col, None)
        return True

    async def get_collection_info(self, collection: Optional[str] = None) -> Dict[str, Any]:
        """Get collection statistics."""
        col = collection or self._collection
        if self._client:
            try:
                info = self._client.get_collection(collection_name=col)
                return {
                    "name": col,
                    "vectors_count": info.vectors_count,
                    "points_count": info.points_count,
                    "status": str(info.status),
                }
            except Exception as e:
                return {"name": col, "error": str(e)}
        count = len(self._memory_store.get(col, []))
        return {"name": col, "vectors_count": count, "backend": "memory"}
