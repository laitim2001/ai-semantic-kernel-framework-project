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

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import (
    MemoryConfig,
    MemoryLayer,
    MemoryMetadata,
    MemoryRecord,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryType,
    DEFAULT_MEMORY_CONFIG,
)


logger = logging.getLogger(__name__)


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

    async def initialize(self) -> None:
        """
        Initialize the mem0 Memory instance.

        Creates connections to Qdrant and configures embedding/LLM providers.
        """
        if self._initialized:
            return

        try:
            # Import mem0 SDK
            from mem0 import Memory

            # Configure mem0
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "path": self.config.qdrant_path,
                        "collection_name": self.config.qdrant_collection,
                    },
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": self.config.embedding_model,
                    },
                },
                "llm": {
                    "provider": self.config.llm_provider,
                    "config": {
                        "model": self.config.llm_model,
                    },
                },
            }

            # Create Memory instance
            self._memory = Memory.from_config(config)
            self._initialized = True
            logger.info("mem0 client initialized successfully")

        except ImportError:
            logger.warning(
                "mem0 SDK not installed. Install with: pip install mem0ai"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize mem0 client: {e}")
            raise

    def _ensure_initialized(self) -> None:
        """Ensure the client is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "Mem0Client not initialized. Call initialize() first."
            )

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
                mem0_metadata.update({
                    "source": metadata.source,
                    "event_id": metadata.event_id,
                    "session_id": metadata.session_id,
                    "importance": metadata.importance,
                    "tags": metadata.tags,
                })

            # Add memory using mem0
            result = self._memory.add(
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
            # Perform semantic search
            results = self._memory.search(
                query=query.query,
                user_id=query.user_id,
                limit=query.limit,
            )

            # Convert to MemorySearchResult objects
            search_results = []
            for item in results:
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
            # Get all memories for user
            results = self._memory.get_all(user_id=user_id)

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
            result = self._memory.get(memory_id)

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
            result = self._memory.update(memory_id=memory_id, data=content)

            if result:
                return await self.get_memory(memory_id)

            return None

        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return None

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
            self._memory.delete(memory_id=memory_id)
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
            self._memory.delete_all(user_id=user_id)
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
            return self._memory.history(memory_id=memory_id)
        except Exception as e:
            logger.error(f"Failed to get history for memory {memory_id}: {e}")
            return []

    async def close(self) -> None:
        """Clean up resources."""
        if self._memory:
            # mem0 doesn't have explicit cleanup, but we reset state
            self._memory = None
            self._initialized = False
            logger.info("mem0 client closed")
