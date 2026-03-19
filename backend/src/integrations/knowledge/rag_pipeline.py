"""RAG Pipeline — end-to-end Retrieval-Augmented Generation.

Orchestrates the full RAG flow:
  Document → Parse → Chunk → Embed → Index → Retrieve → Augment

Sprint 118 — Phase 38 E2E Assembly C.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from src.integrations.knowledge.document_parser import DocumentParser, ParsedDocument
from src.integrations.knowledge.chunker import DocumentChunker, ChunkingStrategy, TextChunk
from src.integrations.knowledge.embedder import EmbeddingManager
from src.integrations.knowledge.vector_store import VectorStoreManager, IndexedDocument
from src.integrations.knowledge.retriever import KnowledgeRetriever, RetrievalResult

logger = logging.getLogger(__name__)


class RAGPipeline:
    """End-to-end RAG pipeline for knowledge management.

    Provides two main workflows:
    1. **Ingestion**: Document → Parse → Chunk → Embed → Index
    2. **Retrieval**: Query → Embed → Search → Rerank → Augment

    Args:
        chunk_size: Target chunk size for splitting.
        chunk_overlap: Overlap between chunks.
        collection: Default vector collection name.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        collection: str = "knowledge_base",
    ) -> None:
        self._parser = DocumentParser()
        self._chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=ChunkingStrategy.RECURSIVE,
        )
        self._embedder = EmbeddingManager()
        self._vector_store = VectorStoreManager(collection_name=collection)
        self._retriever = KnowledgeRetriever(
            vector_store=self._vector_store,
            embedder=self._embedder,
        )

    # ------------------------------------------------------------------
    # Ingestion Pipeline
    # ------------------------------------------------------------------

    async def ingest_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest a document file into the knowledge base.

        Flow: Parse → Chunk → Embed → Index

        Args:
            file_path: Path to the document.
            metadata: Additional metadata to attach to chunks.

        Returns:
            Ingestion statistics.
        """
        # Step 1: Parse
        doc = await self._parser.parse(file_path)
        if not doc.content:
            return {"success": False, "error": "Empty document", "chunks": 0}

        return await self._ingest_parsed(doc, metadata)

    async def ingest_text(
        self,
        text: str,
        title: str = "inline",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest raw text into the knowledge base."""
        doc = await self._parser.parse_text(text, title=title)
        return await self._ingest_parsed(doc, metadata)

    async def _ingest_parsed(
        self,
        doc: ParsedDocument,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest a parsed document."""
        base_meta = {
            "title": doc.title,
            "format": doc.format.value,
            **(metadata or {}),
        }

        # Step 2: Chunk
        chunks = self._chunker.chunk(doc.content, metadata=base_meta)
        if not chunks:
            return {"success": False, "error": "No chunks produced", "chunks": 0}

        # Step 3: Embed
        texts = [c.content for c in chunks]
        embeddings = await self._embedder.embed_batch(texts)

        # Step 4: Index
        indexed_docs = [
            IndexedDocument(
                doc_id=str(uuid.uuid4()),
                content=chunk.content,
                embedding=embedding,
                metadata={
                    **chunk.metadata,
                    "chunk_index": chunk.chunk_index,
                    "char_count": chunk.char_count,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        count = await self._vector_store.index_documents(indexed_docs)

        logger.info(
            "RAG: ingested '%s' → %d chunks → %d indexed",
            doc.title, len(chunks), count,
        )

        return {
            "success": True,
            "title": doc.title,
            "format": doc.format.value,
            "total_chars": doc.char_count,
            "chunks": len(chunks),
            "indexed": count,
        }

    # ------------------------------------------------------------------
    # Retrieval Pipeline
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        collection: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """Retrieve relevant knowledge for a query.

        Args:
            query: Search query.
            limit: Maximum results.
            collection: Optional specific collection.

        Returns:
            Ranked list of retrieval results.
        """
        return await self._retriever.retrieve(
            query=query,
            collection=collection,
            limit=limit,
        )

    async def retrieve_and_format(
        self,
        query: str,
        limit: int = 5,
    ) -> str:
        """Retrieve and format results as context for LLM injection.

        Returns a formatted string suitable for system prompt injection.
        """
        results = await self.retrieve(query, limit=limit)
        if not results:
            return ""

        lines = ["--- 知識庫參考資料 ---"]
        for i, r in enumerate(results, 1):
            source = r.metadata.get("title", "unknown")
            lines.append(f"{i}. [{source}] {r.content[:300]}")
        lines.append("--- 參考資料結束 ---")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # search_knowledge tool handler
    # ------------------------------------------------------------------

    async def handle_search_knowledge(
        self,
        query: str,
        collection: Optional[str] = None,
        limit: int = 5,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Handler for the search_knowledge orchestrator tool.

        Used by the Orchestrator Agent to autonomously search the
        enterprise knowledge base.
        """
        results = await self.retrieve(query, limit=limit, collection=collection)
        return {
            "results": [
                {
                    "content": r.content[:500],
                    "score": r.score,
                    "source": r.source,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "count": len(results),
            "query": query,
        }

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get vector store collection statistics."""
        return await self._vector_store.get_collection_info()

    async def delete_collection(self) -> bool:
        """Delete the entire knowledge collection."""
        return await self._vector_store.delete_collection()
