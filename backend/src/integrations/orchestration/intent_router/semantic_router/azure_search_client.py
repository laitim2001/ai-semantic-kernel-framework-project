"""
Azure AI Search Client for Semantic Route Operations

Wraps azure-search-documents SDK for vector and hybrid search
against the semantic-routes index. All synchronous SDK calls are
executed in a thread pool to expose an async interface.

Sprint 115: Story 115-2 - Azure Semantic Router Components (Phase 32)
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import (
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

logger = logging.getLogger(__name__)

# Default retry configuration
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_BASE_DELAY = 0.5
_DEFAULT_TIMEOUT_SECONDS = 30


class AzureSearchClient:
    """Azure AI Search client wrapper for semantic route operations.

    Provides async-compatible vector and hybrid search backed by
    Azure AI Search. Synchronous SDK calls are offloaded to a
    ``ThreadPoolExecutor`` so callers may ``await`` each operation.

    Attributes:
        endpoint: Azure AI Search service endpoint.
        index_name: Name of the search index.
        max_retries: Maximum number of retry attempts for transient errors.
        retry_base_delay: Base delay in seconds for exponential backoff.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        index_name: str = "semantic-routes",
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_base_delay: float = _DEFAULT_RETRY_BASE_DELAY,
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
        max_workers: int = 4,
    ) -> None:
        """Initialize Azure Search client.

        Args:
            endpoint: Azure AI Search service endpoint URL.
            api_key: Azure AI Search admin or query API key.
            index_name: Name of the target search index.
            max_retries: Maximum retry attempts for transient failures.
            retry_base_delay: Base delay (seconds) for exponential backoff.
            timeout_seconds: Per-request timeout in seconds.
            max_workers: Thread pool size for async wrapping.
        """
        if not endpoint:
            raise ValueError("endpoint must not be empty")
        if not api_key:
            raise ValueError("api_key must not be empty")

        self.endpoint = endpoint
        self.index_name = index_name
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.timeout_seconds = timeout_seconds

        credential = AzureKeyCredential(api_key)
        self._client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=credential,
        )
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        logger.info(
            "AzureSearchClient initialized: endpoint=%s, index=%s",
            endpoint[:40],
            index_name,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_in_executor(self, func, *args):
        """Run a synchronous function in the thread pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args)

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute *func* with exponential-backoff retry on transient errors.

        Retries on ``HttpResponseError`` with status 429 or 5xx, and on
        ``ServiceRequestError`` (network-level failures).
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except HttpResponseError as exc:
                last_exception = exc
                status = getattr(exc, "status_code", None)
                if status and (status == 429 or status >= 500):
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "Azure Search HTTP %s (attempt %d/%d), retrying in %.1fs",
                        status,
                        attempt + 1,
                        self.max_retries + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise
            except ServiceRequestError as exc:
                last_exception = exc
                delay = self.retry_base_delay * (2 ** attempt)
                logger.warning(
                    "Azure Search service error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)
                continue

        raise last_exception  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Sync implementations (called via executor)
    # ------------------------------------------------------------------

    def _vector_search_sync(
        self,
        vector: List[float],
        top_k: int,
        filters: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Synchronous vector search implementation."""
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=top_k,
            fields="utterance_vector",
        )

        results = self._retry_with_backoff(
            self._client.search,
            search_text=None,
            vector_queries=[vector_query],
            filter=filters,
            top=top_k,
        )

        documents: List[Dict[str, Any]] = []
        for result in results:
            doc = dict(result)
            documents.append(doc)

        return documents

    def _hybrid_search_sync(
        self,
        query: str,
        vector: List[float],
        top_k: int,
        filters: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Synchronous hybrid search implementation."""
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=top_k,
            fields="utterance_vector",
        )

        results = self._retry_with_backoff(
            self._client.search,
            search_text=query,
            vector_queries=[vector_query],
            filter=filters,
            top=top_k,
        )

        documents: List[Dict[str, Any]] = []
        for result in results:
            doc = dict(result)
            documents.append(doc)

        return documents

    def _upload_documents_sync(
        self,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Synchronous document upload implementation."""
        result = self._retry_with_backoff(
            self._client.merge_or_upload_documents,
            documents=documents,
        )

        succeeded = sum(1 for r in result if r.succeeded)
        failed = sum(1 for r in result if not r.succeeded)

        return {
            "total": len(documents),
            "succeeded": succeeded,
            "failed": failed,
        }

    def _delete_documents_sync(
        self,
        ids: List[str],
    ) -> Dict[str, Any]:
        """Synchronous document deletion implementation."""
        documents = [{"id": doc_id} for doc_id in ids]
        result = self._retry_with_backoff(
            self._client.delete_documents,
            documents=documents,
        )

        succeeded = sum(1 for r in result if r.succeeded)
        failed = sum(1 for r in result if not r.succeeded)

        return {
            "total": len(ids),
            "succeeded": succeeded,
            "failed": failed,
        }

    def _get_document_sync(
        self,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Synchronous get-document implementation."""
        try:
            result = self._retry_with_backoff(
                self._client.get_document,
                key=document_id,
            )
            return dict(result)
        except ResourceNotFoundError:
            return None

    def _get_document_count_sync(self) -> int:
        """Synchronous document count implementation."""
        return self._retry_with_backoff(self._client.get_document_count)

    def _health_check_sync(self) -> bool:
        """Synchronous health check implementation."""
        try:
            self._client.get_document_count()
            return True
        except Exception as exc:
            logger.warning("Azure Search health check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def vector_search(
        self,
        vector: List[float],
        top_k: int = 3,
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Pure vector search using the utterance_vector field.

        Args:
            vector: Query embedding vector.
            top_k: Maximum number of results to return.
            filters: Optional OData filter expression.

        Returns:
            List of matching documents with scores.
        """
        return await self._run_in_executor(
            self._vector_search_sync, vector, top_k, filters,
        )

    async def hybrid_search(
        self,
        query: str,
        vector: List[float],
        top_k: int = 3,
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining text and vector similarity.

        Args:
            query: Text query for keyword matching.
            vector: Query embedding vector.
            top_k: Maximum number of results to return.
            filters: Optional OData filter expression.

        Returns:
            List of matching documents with combined scores.
        """
        return await self._run_in_executor(
            self._hybrid_search_sync, query, vector, top_k, filters,
        )

    async def upload_documents(
        self,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Upload or merge documents to the index.

        Args:
            documents: List of document dicts (must include ``id`` field).

        Returns:
            Summary dict with total, succeeded, and failed counts.
        """
        return await self._run_in_executor(
            self._upload_documents_sync, documents,
        )

    async def delete_documents(
        self,
        ids: List[str],
    ) -> Dict[str, Any]:
        """Delete documents by ID.

        Args:
            ids: List of document IDs to delete.

        Returns:
            Summary dict with total, succeeded, and failed counts.
        """
        return await self._run_in_executor(
            self._delete_documents_sync, ids,
        )

    async def get_document(
        self,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a single document by ID.

        Args:
            document_id: The document key.

        Returns:
            Document dict or None if not found.
        """
        return await self._run_in_executor(
            self._get_document_sync, document_id,
        )

    async def get_document_count(self) -> int:
        """Get total document count in the index.

        Returns:
            Number of documents in the index.
        """
        return await self._run_in_executor(self._get_document_count_sync)

    async def health_check(self) -> bool:
        """Check if the search service is accessible.

        Returns:
            True if the service responds, False otherwise.
        """
        return await self._run_in_executor(self._health_check_sync)
