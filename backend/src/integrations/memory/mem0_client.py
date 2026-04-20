# =============================================================================
# IPA Platform - mem0 Client Wrapper
# =============================================================================
# Sprint 79: S79-2 - mem0 長期記憶整合 (10 pts)
#
# This module wraps the mem0 SDK to provide a consistent interface for
# long-term memory operations with local Qdrant storage.
#
# Architecture:
#   Mem0Client
#   ├── add_memory()      - Store new memory with automatic extraction
#   ├── search_memory()   - Semantic search across memories
#   ├── get_all()         - Get all memories for a user
#   ├── get_memory()      - Get specific memory by ID
#   ├── update_memory()   - Update existing memory
#   └── delete_memory()   - Remove memory
# =============================================================================

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional

from .types import (
    DEFAULT_MEMORY_CONFIG,
    MemoryConfig,
    MemoryLayer,
    MemoryMetadata,
    MemoryRecord,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryType,
)

logger = logging.getLogger(__name__)


class Mem0LockTimeout(RuntimeError):
    """Raised when a mem0 mutation cannot acquire the serialisation lock
    within the configured ``MEM0_MUTATION_LOCK_TIMEOUT`` (Sprint 172)."""


class Mem0Client:
    """
    Wrapper for mem0 SDK providing long-term memory operations.

    Uses local Qdrant for vector storage and OpenAI embeddings.
    Memory extraction is powered by Claude for semantic understanding.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        Initialize the mem0 client.

        Args:
            config: Memory configuration. Uses defaults if not provided.
        """
        self.config = config or DEFAULT_MEMORY_CONFIG
        self._memory = None
        self._initialized = False
        # Sprint 172: shared ThreadPoolExecutor wraps ALL sync mem0 SDK calls
        # (search / get / get_all / add / update / delete / delete_all / history).
        # Mutation ops additionally acquire _mutation_lock with timeout.
        self._executor: Optional[ThreadPoolExecutor] = None
        self._mutation_lock: Optional[asyncio.Lock] = None

    def _ensure_resources(self) -> None:
        """Lazy-init executor + mutation lock on first async call."""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self.config.mem0_executor_workers,
                thread_name_prefix="mem0",
            )
        if self._mutation_lock is None:
            self._mutation_lock = asyncio.Lock()

    async def _run_read(self, fn, /, *args, **kwargs):
        """Run a sync mem0 READ op in the executor (no lock — reads parallel)."""
        self._ensure_resources()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, partial(fn, *args, **kwargs))

    async def _run_mutate(self, fn, /, *args, **kwargs):
        """Run a sync mem0 WRITE op in the executor with serialised mutation lock.

        Timeout via ``asyncio.wait_for(lock.acquire())`` — the HIGH finding
        from v2 review. ``asyncio.Lock`` has no native timeout parameter.
        """
        self._ensure_resources()
        assert self._mutation_lock is not None  # nosec B101 — set by _ensure
        timeout = self.config.mem0_mutation_lock_timeout
        try:
            await asyncio.wait_for(self._mutation_lock.acquire(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise Mem0LockTimeout(
                f"Could not acquire mem0 mutation lock within {timeout}s"
            ) from exc
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self._executor, partial(fn, *args, **kwargs))
        finally:
            self._mutation_lock.release()

    def _build_embedder_config(self) -> Dict[str, Any]:
        """Build embedder config based on provider setting.

        mem0 Azure OpenAI uses ``azure_kwargs`` (an ``AzureConfig`` dict)
        inside the embedder config, not top-level keys.
        """
        provider = self.config.embedding_provider

        if provider == "azure_openai":
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            return {
                "provider": "azure_openai",
                "config": {
                    "model": self.config.embedding_model,
                    "azure_kwargs": {
                        "api_key": azure_key,
                        "azure_deployment": self.config.azure_embedding_deployment,
                        "azure_endpoint": azure_endpoint,
                        "api_version": os.getenv(
                            "AZURE_OPENAI_EMBEDDING_API_VERSION", "2024-02-01"
                        ),
                    },
                },
            }
        else:
            # Default: openai provider
            return {
                "provider": "openai",
                "config": {
                    "model": self.config.embedding_model,
                },
            }

    def _build_llm_config(self) -> Dict[str, Any]:
        """Build LLM config for mem0.

        Anthropic requires either temperature OR top_p, not both.
        Azure OpenAI is used as fallback if configured.
        """
        provider = self.config.llm_provider

        if provider == "azure_openai":
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")
            return {
                "provider": "azure_openai",
                "config": {
                    "model": deployment,
                    "azure_kwargs": {
                        "api_key": azure_key,
                        "azure_deployment": deployment,
                        "azure_endpoint": azure_endpoint,
                        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
                    },
                },
            }
        elif provider == "anthropic":
            # Fix: Anthropic API rejects temperature + top_p together.
            # Set top_p to None so only temperature is sent.
            return {
                "provider": "anthropic",
                "config": {
                    "model": self.config.llm_model,
                    "temperature": 0.1,
                    "top_p": None,
                },
            }
        else:
            return {
                "provider": provider,
                "config": {
                    "model": self.config.llm_model,
                },
            }

    async def initialize(self) -> None:
        """
        Initialize the mem0 Memory instance.

        Creates connections to Qdrant and configures embedding/LLM providers.
        """
        if self._initialized:
            return

        try:
            # Import mem0 SDK
            # Configure mem0 — use Docker Qdrant if QDRANT_HOST is set, else local path
            import os

            from mem0 import Memory

            qdrant_host = os.getenv("QDRANT_HOST")
            qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
            if qdrant_host:
                qdrant_config = {
                    "host": qdrant_host,
                    "port": qdrant_port,
                    "collection_name": self.config.qdrant_collection,
                    "embedding_model_dims": self.config.embedding_dims,
                }
            else:
                qdrant_config = {
                    "path": self.config.qdrant_path,
                    "collection_name": self.config.qdrant_collection,
                    "embedding_model_dims": self.config.embedding_dims,
                }
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": qdrant_config,
                },
                "embedder": self._build_embedder_config(),
                "llm": self._build_llm_config(),
            }

            # Create Memory instance
            self._memory = Memory.from_config(config)
            self._initialized = True
            logger.info("mem0 client initialized successfully")

        except ImportError:
            logger.warning("mem0 SDK not installed. Install with: pip install mem0ai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize mem0 client: {e}")
            raise

    def _ensure_initialized(self) -> None:
        """Ensure the client is initialized."""
        if not self._initialized:
            raise RuntimeError("Mem0Client not initialized. Call initialize() first.")

    async def add_memory(
        self,
        content: str,
        user_id: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        metadata: Optional[MemoryMetadata] = None,
    ) -> MemoryRecord:
        """
        Add a new memory.

        mem0 will automatically extract and structure the memory content
        using its built-in LLM capabilities.

        Args:
            content: The memory content to store.
            user_id: User identifier for memory isolation.
            memory_type: Type of memory being stored.
            metadata: Additional metadata.

        Returns:
            The created MemoryRecord.
        """
        self._ensure_initialized()

        try:
            # Prepare metadata for mem0
            mem0_metadata = {
                "memory_type": memory_type.value,
                "created_at": datetime.utcnow().isoformat(),
            }

            if metadata:
                mem0_metadata.update(
                    {
                        "source": metadata.source,
                        "event_id": metadata.event_id,
                        "session_id": metadata.session_id,
                        "importance": metadata.importance,
                        "tags": metadata.tags,
                    }
                )

            # Add memory using mem0 (Sprint 172: wrapped in executor + mutation lock)
            result = await self._run_mutate(
                self._memory.add,
                messages=content,
                user_id=user_id,
                metadata=mem0_metadata,
            )

            # Extract memory ID from result
            memory_id = result.get("id", "") if isinstance(result, dict) else str(result)

            # Create MemoryRecord
            record = MemoryRecord(
                id=memory_id,
                user_id=user_id,
                content=content,
                memory_type=memory_type,
                layer=MemoryLayer.LONG_TERM,
                metadata=metadata or MemoryMetadata(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            logger.info(f"Memory added: {memory_id} for user {user_id}")
            return record

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise

    async def search_memory(
        self,
        query: MemorySearchQuery,
    ) -> List[MemorySearchResult]:
        """
        Search memories using semantic similarity.

        Args:
            query: Search query parameters.

        Returns:
            List of matching MemorySearchResult objects.
        """
        self._ensure_initialized()

        try:
            # Perform semantic search (Sprint 172: executor-wrapped, no lock — read)
            results = await self._run_read(
                self._memory.search,
                query=query.query,
                user_id=query.user_id,
                limit=max(1, query.limit),
            )

            # Convert to MemorySearchResult objects
            search_results = []

            # mem0 v1.0.5+ may return {"results": [...]} or list directly
            logger.debug(
                f"mem0 raw search result type={type(results).__name__}, value={str(results)[:200]}"
            )
            if isinstance(results, dict):
                results = results.get("results", results.get("memories", []))
            if not isinstance(results, list):
                logger.warning(f"mem0 search returned unexpected type: {type(results).__name__}")
                return []

            for item in results:
                # Skip non-dict items (mem0 format may vary)
                if not isinstance(item, dict):
                    logger.debug(
                        f"Skipping non-dict search result item: {type(item).__name__}={str(item)[:80]}"
                    )
                    continue
                # Extract memory data
                memory_data = item.get("memory", {})
                metadata_data = item.get("metadata", {})

                # Create MemoryRecord
                record = MemoryRecord(
                    id=item.get("id", ""),
                    user_id=query.user_id or "",
                    content=memory_data if isinstance(memory_data, str) else str(memory_data),
                    memory_type=MemoryType(
                        metadata_data.get("memory_type", MemoryType.CONVERSATION.value)
                    ),
                    layer=MemoryLayer.LONG_TERM,
                    metadata=MemoryMetadata(
                        source=metadata_data.get("source", ""),
                        event_id=metadata_data.get("event_id"),
                        session_id=metadata_data.get("session_id"),
                        importance=metadata_data.get("importance", 0.5),
                        tags=metadata_data.get("tags", []),
                    ),
                )

                # Create search result with score
                result = MemorySearchResult(
                    memory=record,
                    score=item.get("score", 0.0),
                )
                search_results.append(result)

            logger.info(
                f"Memory search returned {len(search_results)} results "
                f"for query: {query.query[:50]}..."
            )
            return search_results

        except Exception as e:
            logger.error(f"Failed to search memory: {e}")
            raise

    async def get_all(
        self,
        user_id: str,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> List[MemoryRecord]:
        """
        Get all memories for a user.

        Args:
            user_id: User identifier.
            memory_types: Optional filter by memory types.

        Returns:
            List of MemoryRecord objects.
        """
        self._ensure_initialized()

        try:
            # Get all memories for user (Sprint 172: executor-wrapped, no lock — read)
            raw_results = await self._run_read(self._memory.get_all, user_id=user_id)

            # mem0 may return dict {"results": [...]} or plain list
            if isinstance(raw_results, dict):
                results = raw_results.get("results", [])
            elif isinstance(raw_results, list):
                results = raw_results
            else:
                results = []

            # Convert to MemoryRecord objects
            records = []
            for item in results:
                metadata_data = item.get("metadata", {})
                memory_type = MemoryType(
                    metadata_data.get("memory_type", MemoryType.CONVERSATION.value)
                )

                # Filter by memory type if specified
                if memory_types and memory_type not in memory_types:
                    continue

                record = MemoryRecord(
                    id=item.get("id", ""),
                    user_id=user_id,
                    content=item.get("memory", ""),
                    memory_type=memory_type,
                    layer=MemoryLayer.LONG_TERM,
                    metadata=MemoryMetadata(
                        source=metadata_data.get("source", ""),
                        event_id=metadata_data.get("event_id"),
                        session_id=metadata_data.get("session_id"),
                        importance=metadata_data.get("importance", 0.5),
                        tags=metadata_data.get("tags", []),
                    ),
                    created_at=datetime.fromisoformat(
                        metadata_data.get("created_at", datetime.utcnow().isoformat())
                    ),
                )
                records.append(record)

            logger.info(f"Retrieved {len(records)} memories for user {user_id}")
            return records

        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            raise

    async def get_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        """
        Get a specific memory by ID.

        Args:
            memory_id: The memory identifier.

        Returns:
            MemoryRecord if found, None otherwise.
        """
        self._ensure_initialized()

        try:
            # Sprint 172: executor-wrapped, no lock — read op
            result = await self._run_read(self._memory.get, memory_id)

            if not result:
                return None

            metadata_data = result.get("metadata", {})

            record = MemoryRecord(
                id=result.get("id", memory_id),
                user_id=result.get("user_id", ""),
                content=result.get("memory", ""),
                memory_type=MemoryType(
                    metadata_data.get("memory_type", MemoryType.CONVERSATION.value)
                ),
                layer=MemoryLayer.LONG_TERM,
                metadata=MemoryMetadata(
                    source=metadata_data.get("source", ""),
                    event_id=metadata_data.get("event_id"),
                    session_id=metadata_data.get("session_id"),
                    importance=metadata_data.get("importance", 0.5),
                    tags=metadata_data.get("tags", []),
                ),
            )

            return record

        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    async def update_memory(
        self,
        memory_id: str,
        content: str,
    ) -> Optional[MemoryRecord]:
        """
        Update an existing memory.

        Args:
            memory_id: The memory identifier.
            content: New content for the memory.

        Returns:
            Updated MemoryRecord if successful, None otherwise.
        """
        self._ensure_initialized()

        try:
            # Sprint 172: executor-wrapped, mutation lock serialises writes
            result = await self._run_mutate(self._memory.update, memory_id=memory_id, data=content)

            if result:
                return await self.get_memory(memory_id)

            return None

        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return None

    async def update_access_metadata(
        self,
        memory_id: str,
        count: int,
        accessed_at: datetime,
    ) -> bool:
        """Update access tracking metadata on a LONG_TERM memory (Sprint 170).

        Wraps synchronous `mem0.update()` via dedicated ThreadPoolExecutor
        serialized by asyncio.Lock. Rationale: mem0 SDK is not guaranteed
        thread-safe — concurrent updates can corrupt internal Qdrant state
        (v2 review finding).

        Args:
            memory_id: Target memory identifier.
            count: Current access count after increment.
            accessed_at: Timestamp of most recent access.

        Returns:
            True if update call returned truthy, False otherwise.

        Raises:
            Exceptions from mem0 propagate — caller (background task manager)
            routes failures to dead-letter log.
        """
        self._ensure_initialized()
        metadata = {
            "access_count": count,
            "accessed_at": accessed_at.isoformat(),
        }
        result = await self._run_mutate(
            self._memory.update,
            memory_id=memory_id,
            metadata=metadata,
        )
        return bool(result)

    async def update_importance_metadata(
        self,
        memory_id: str,
        new_importance: float,
    ) -> bool:
        """Update importance metadata on a LONG_TERM memory (Sprint 171).

        Reuses the Sprint 170 thread-safe wrapper pattern. Separate from
        ``update_access_metadata`` to keep call sites explicit and to avoid
        accidentally overwriting access counters during decay.

        Args:
            memory_id: Target memory identifier.
            new_importance: New importance score (clamped to [0.0, 1.0]).

        Returns:
            True if update call returned truthy.
        """
        self._ensure_initialized()
        clamped = max(0.0, min(1.0, new_importance))
        metadata = {"importance": clamped}
        result = await self._run_mutate(
            self._memory.update,
            memory_id=memory_id,
            metadata=metadata,
        )
        return bool(result)

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: The memory identifier.

        Returns:
            True if deleted successfully, False otherwise.
        """
        self._ensure_initialized()

        try:
            # Sprint 172: executor-wrapped, mutation lock serialises writes
            await self._run_mutate(self._memory.delete, memory_id=memory_id)
            logger.info(f"Memory deleted: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def delete_all(self, user_id: str) -> bool:
        """
        Delete all memories for a user.

        Args:
            user_id: User identifier.

        Returns:
            True if deleted successfully, False otherwise.
        """
        self._ensure_initialized()

        try:
            # Sprint 172: executor-wrapped, mutation lock serialises writes
            await self._run_mutate(self._memory.delete_all, user_id=user_id)
            logger.info(f"All memories deleted for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete all memories for user {user_id}: {e}")
            return False

    async def get_history(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        Get the history of a memory.

        Args:
            memory_id: The memory identifier.

        Returns:
            List of historical states.
        """
        self._ensure_initialized()

        try:
            # Sprint 172: executor-wrapped, no lock — read-only history op
            return await self._run_read(self._memory.history, memory_id=memory_id)
        except Exception as e:
            logger.error(f"Failed to get history for memory {memory_id}: {e}")
            return []

    async def close(self) -> None:
        """Clean up resources — Sprint 172 shuts down the shared executor."""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
        self._mutation_lock = None
        if self._memory:
            # mem0 doesn't have explicit cleanup, but we reset state
            self._memory = None
            self._initialized = False
            logger.info("mem0 client closed")
