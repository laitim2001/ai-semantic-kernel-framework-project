"""
Step 2: Knowledge Search — Query enterprise knowledge base via Qdrant.

Extracted from PoC agent_team_poc.py lines 915-952.
Uses Azure OpenAI embeddings + Qdrant vector similarity search.

Outputs:
    context.knowledge_text — Formatted knowledge base results.
    context.knowledge_metadata — Result count, scores, status.

Phase 45: Orchestration Core
"""

import logging
import os
from typing import Any, List, Optional

from ..context import PipelineContext
from .base import PipelineStep

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_COLLECTION = "ipa_knowledge"
DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"
DEFAULT_TOP_K = 3
DEFAULT_QUERY_TRUNCATE = 500


class KnowledgeStep(PipelineStep):
    """Search enterprise knowledge base using vector similarity.

    Uses Azure OpenAI to generate query embedding, then searches Qdrant
    for the top-K most similar knowledge base entries.

    Graceful degradation: if Qdrant or Azure is unavailable, sets
    context.knowledge_text = "" and logs warning. Pipeline continues.
    """

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        top_k: int = DEFAULT_TOP_K,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
    ):
        """Initialize KnowledgeStep.

        Args:
            collection_name: Qdrant collection to search.
            embedding_model: Azure OpenAI embedding model name.
            top_k: Number of results to retrieve.
            qdrant_host: Qdrant server host (default: localhost).
            qdrant_port: Qdrant server port (default: 6333).
        """
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._top_k = top_k
        self._qdrant_host = qdrant_host or os.getenv("QDRANT_HOST", "localhost")
        self._qdrant_port = qdrant_port or int(os.getenv("QDRANT_PORT", "6333"))

    @property
    def name(self) -> str:
        return "knowledge_search"

    @property
    def step_index(self) -> int:
        return 1

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        """Search knowledge base and format results.

        Args:
            context: PipelineContext with task set.

        Returns:
            PipelineContext with knowledge_text and knowledge_metadata populated.
        """
        try:
            query_text = context.task[:DEFAULT_QUERY_TRUNCATE]
            embedding = self._get_embedding(query_text)
            results = self._search_qdrant(embedding)

            context.knowledge_text = self._format_results(results)
            context.knowledge_metadata = {
                "result_count": len(results),
                "scores": [round(r.get("score", 0), 3) for r in results],
                "collection": self._collection_name,
                "status": "ok" if results else "no_results",
            }

            logger.info(
                "KnowledgeStep: found %d results from '%s' (task=%s...)",
                len(results),
                self._collection_name,
                context.task[:50],
            )

        except Exception as e:
            logger.warning(
                "KnowledgeStep: search failed — %s",
                str(e)[:150],
            )
            context.knowledge_text = ""
            context.knowledge_metadata = {
                "status": "unavailable",
                "error": str(e)[:200],
            }

        return context

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector via Azure OpenAI.

        Args:
            text: Query text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-01",
        )
        response = client.embeddings.create(
            input=text,
            model=self._embedding_model,
        )
        return response.data[0].embedding

    def _search_qdrant(self, embedding: List[float]) -> List[dict]:
        """Search Qdrant collection with embedding vector.

        Args:
            embedding: Query embedding vector.

        Returns:
            List of result dicts with 'source', 'content', 'score' keys.
        """
        from qdrant_client import QdrantClient

        client = QdrantClient(
            host=self._qdrant_host,
            port=self._qdrant_port,
        )
        search_results = client.query_points(
            self._collection_name,
            query=embedding,
            limit=self._top_k,
        )

        results: List[dict] = []
        for point in search_results.points:
            payload: Any = point.payload or {}
            results.append({
                "source": payload.get("source", "unknown"),
                "content": payload.get("content", ""),
                "score": point.score,
            })
        return results

    @staticmethod
    def _format_results(results: List[dict]) -> str:
        """Format search results as readable text for LLM consumption.

        Args:
            results: List of result dicts.

        Returns:
            Formatted text string. Empty string if no results.
        """
        if not results:
            return ""

        lines = []
        for r in results:
            source = r.get("source", "unknown")
            score = r.get("score", 0)
            content = r.get("content", "")
            lines.append(f"[{source}] (score={score:.2f}) {content}")

        return "\n".join(lines)
