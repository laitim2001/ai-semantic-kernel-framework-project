# =============================================================================
# IPA Platform - Unified Memory Manager
# =============================================================================
# Sprint 79: S79-2 - mem0 長期記憶整合 (10 pts)
#
# This module provides a unified interface for the three-layer memory system:
#   Layer 1: Working Memory (Redis) - Short-term, TTL 30 min
#   Layer 2: Session Memory (PostgreSQL) - Medium-term, TTL 7 days
#   Layer 3: Long-term Memory (mem0 + Qdrant) - Permanent
#
# Architecture:
#   UnifiedMemoryManager
#   ├── add()             - Add memory with automatic layer selection
#   ├── search()          - Search across all layers
#   ├── get_context()     - Get relevant memories for current context
#   ├── promote()         - Move memory to higher layer
#   └── consolidate()     - Merge and summarize memories
# =============================================================================

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

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
from .mem0_client import Mem0Client
from .embeddings import EmbeddingService


logger = logging.getLogger(__name__)


class UnifiedMemoryManager:
    """
    Unified interface for the three-layer memory system.

    Manages memory across:
    - Working Memory (Redis) - Fast, short-lived context
    - Session Memory (PostgreSQL) - Medium-term persistence
    - Long-term Memory (mem0) - Permanent semantic storage

    Provides automatic layer selection, promotion, and consolidation.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        Initialize the memory manager.

        Args:
            config: Memory configuration. Uses defaults if not provided.
        """
        self.config = config or DEFAULT_MEMORY_CONFIG

        # Initialize components
        self._mem0_client = Mem0Client(config)
        self._embedding_service = EmbeddingService(config)

        # Redis and PostgreSQL connections (lazy initialization)
        self._redis = None
        self._db_session = None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all memory layers."""
        if self._initialized:
            return

        try:
            # Initialize mem0 client
            await self._mem0_client.initialize()

            # Initialize embedding service
            await self._embedding_service.initialize()

            # Initialize Redis connection (optional)
            await self._initialize_redis()

            self._initialized = True
            logger.info("UnifiedMemoryManager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize UnifiedMemoryManager: {e}")
            raise

    async def _initialize_redis(self) -> None:
        """Initialize Redis connection for working memory."""
        try:
            import os
            import redis.asyncio as redis

            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))

            self._redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()
            logger.info("Redis connection established for working memory")

        except ImportError:
            logger.warning("redis package not installed. Working memory disabled.")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Working memory disabled.")
            self._redis = None

    def _ensure_initialized(self) -> None:
        """Ensure the manager is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "UnifiedMemoryManager not initialized. Call initialize() first."
            )

    def _select_layer(
        self,
        memory_type: MemoryType,
        importance: float,
    ) -> MemoryLayer:
        """
        Select appropriate memory layer based on type and importance.

        Args:
            memory_type: Type of memory.
            importance: Importance score (0.0 to 1.0).

        Returns:
            Selected memory layer.
        """
        # High importance or specific types go to long-term
        if importance >= 0.8:
            return MemoryLayer.LONG_TERM

        if memory_type in [
            MemoryType.EVENT_RESOLUTION,
            MemoryType.BEST_PRACTICE,
            MemoryType.SYSTEM_KNOWLEDGE,
        ]:
            return MemoryLayer.LONG_TERM

        # User preferences go to long-term for persistence
        if memory_type == MemoryType.USER_PREFERENCE:
            return MemoryLayer.LONG_TERM

        # Feedback goes to session for review before promotion
        if memory_type == MemoryType.FEEDBACK:
            return MemoryLayer.SESSION

        # Conversation snippets start in working memory
        if memory_type == MemoryType.CONVERSATION:
            if importance >= 0.5:
                return MemoryLayer.SESSION
            return MemoryLayer.WORKING

        # Default to session memory
        return MemoryLayer.SESSION

    async def add(
        self,
        content: str,
        user_id: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        metadata: Optional[MemoryMetadata] = None,
        layer: Optional[MemoryLayer] = None,
    ) -> MemoryRecord:
        """
        Add a new memory.

        Automatically selects appropriate layer based on type and importance,
        or uses specified layer.

        Args:
            content: The memory content.
            user_id: User identifier.
            memory_type: Type of memory.
            metadata: Additional metadata.
            layer: Optional explicit layer selection.

        Returns:
            The created MemoryRecord.
        """
        self._ensure_initialized()

        # Use metadata or create default
        if metadata is None:
            metadata = MemoryMetadata()

        # Select layer
        target_layer = layer or self._select_layer(memory_type, metadata.importance)

        # Generate ID
        memory_id = str(uuid4())

        # Create record
        record = MemoryRecord(
            id=memory_id,
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            layer=target_layer,
            metadata=metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Store in appropriate layer
        if target_layer == MemoryLayer.WORKING:
            await self._store_working_memory(record)
        elif target_layer == MemoryLayer.SESSION:
            await self._store_session_memory(record)
        else:  # LONG_TERM
            record = await self._mem0_client.add_memory(
                content=content,
                user_id=user_id,
                memory_type=memory_type,
                metadata=metadata,
            )

        logger.info(
            f"Memory added to {target_layer.value} layer: "
            f"{memory_id[:8]}... for user {user_id}"
        )
        return record

    async def _store_working_memory(self, record: MemoryRecord) -> None:
        """Store memory in Redis working memory."""
        if not self._redis:
            # Fall back to session memory
            await self._store_session_memory(record)
            return

        try:
            key = f"memory:working:{record.user_id}:{record.id}"
            await self._redis.setex(
                key,
                self.config.working_memory_ttl,
                json.dumps(record.to_dict()),
            )
        except Exception as e:
            logger.warning(f"Failed to store working memory: {e}")
            # Fall back to session memory
            await self._store_session_memory(record)

    async def _store_session_memory(self, record: MemoryRecord) -> None:
        """Store memory in PostgreSQL session memory."""
        if not self._redis:
            # Use mem0 as fallback
            await self._mem0_client.add_memory(
                content=record.content,
                user_id=record.user_id,
                memory_type=record.memory_type,
                metadata=record.metadata,
            )
            return

        try:
            # Use Redis with longer TTL for session memory
            # In production, this would use PostgreSQL
            key = f"memory:session:{record.user_id}:{record.id}"
            await self._redis.setex(
                key,
                self.config.session_memory_ttl,
                json.dumps(record.to_dict()),
            )
        except Exception as e:
            logger.warning(f"Failed to store session memory: {e}")
            # Fall back to long-term memory
            await self._mem0_client.add_memory(
                content=record.content,
                user_id=record.user_id,
                memory_type=record.memory_type,
                metadata=record.metadata,
            )

    async def search(
        self,
        query: str,
        user_id: str,
        memory_types: Optional[List[MemoryType]] = None,
        layers: Optional[List[MemoryLayer]] = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> List[MemorySearchResult]:
        """
        Search memories across specified layers.

        Args:
            query: Search query text.
            user_id: User identifier.
            memory_types: Optional filter by memory types.
            layers: Optional filter by layers. Defaults to all.
            min_importance: Minimum importance score.
            limit: Maximum results per layer.

        Returns:
            List of MemorySearchResult objects, sorted by relevance.
        """
        self._ensure_initialized()

        results: List[MemorySearchResult] = []
        search_layers = layers or [
            MemoryLayer.WORKING,
            MemoryLayer.SESSION,
            MemoryLayer.LONG_TERM,
        ]

        # Search working memory
        if MemoryLayer.WORKING in search_layers:
            working_results = await self._search_working_memory(
                query, user_id, memory_types, limit
            )
            results.extend(working_results)

        # Search session memory
        if MemoryLayer.SESSION in search_layers:
            session_results = await self._search_session_memory(
                query, user_id, memory_types, limit
            )
            results.extend(session_results)

        # Search long-term memory
        if MemoryLayer.LONG_TERM in search_layers:
            search_query = MemorySearchQuery(
                query=query,
                user_id=user_id,
                memory_types=memory_types,
                min_importance=min_importance,
                limit=limit,
            )
            long_term_results = await self._mem0_client.search_memory(search_query)
            results.extend(long_term_results)

        # Sort by score and deduplicate
        results.sort(key=lambda x: x.score, reverse=True)

        # Remove duplicates based on content similarity
        seen_contents = set()
        unique_results = []
        for result in results:
            content_key = result.memory.content[:100]  # Use first 100 chars as key
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                unique_results.append(result)

        return unique_results[:limit]

    async def _search_working_memory(
        self,
        query: str,
        user_id: str,
        memory_types: Optional[List[MemoryType]],
        limit: int,
    ) -> List[MemorySearchResult]:
        """Search working memory (Redis)."""
        if not self._redis:
            return []

        results = []
        try:
            pattern = f"memory:working:{user_id}:*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            # Get query embedding for similarity comparison
            query_embedding = await self._embedding_service.embed_text(query)

            for key in keys[:limit * 2]:  # Get more than limit for filtering
                data = await self._redis.get(key)
                if data:
                    record_dict = json.loads(data)
                    record = MemoryRecord.from_dict(record_dict)

                    # Filter by memory type
                    if memory_types and record.memory_type not in memory_types:
                        continue

                    # Calculate similarity
                    content_embedding = await self._embedding_service.embed_text(
                        record.content
                    )
                    score = EmbeddingService.compute_similarity(
                        query_embedding, content_embedding
                    )

                    results.append(MemorySearchResult(memory=record, score=score))

            # Sort by score
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]

        except Exception as e:
            logger.warning(f"Failed to search working memory: {e}")
            return []

    async def _search_session_memory(
        self,
        query: str,
        user_id: str,
        memory_types: Optional[List[MemoryType]],
        limit: int,
    ) -> List[MemorySearchResult]:
        """Search session memory (Redis/PostgreSQL)."""
        if not self._redis:
            return []

        results = []
        try:
            pattern = f"memory:session:{user_id}:*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            # Get query embedding for similarity comparison
            query_embedding = await self._embedding_service.embed_text(query)

            for key in keys[:limit * 2]:
                data = await self._redis.get(key)
                if data:
                    record_dict = json.loads(data)
                    record = MemoryRecord.from_dict(record_dict)

                    # Filter by memory type
                    if memory_types and record.memory_type not in memory_types:
                        continue

                    # Calculate similarity
                    content_embedding = await self._embedding_service.embed_text(
                        record.content
                    )
                    score = EmbeddingService.compute_similarity(
                        query_embedding, content_embedding
                    )

                    results.append(MemorySearchResult(memory=record, score=score))

            # Sort by score
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]

        except Exception as e:
            logger.warning(f"Failed to search session memory: {e}")
            return []

    async def get_context(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryRecord]:
        """
        Get relevant memories for the current context.

        Combines recent working memory with relevant long-term memories.

        Args:
            user_id: User identifier.
            session_id: Optional session identifier.
            query: Optional query for semantic search.
            limit: Maximum memories to return.

        Returns:
            List of relevant MemoryRecord objects.
        """
        self._ensure_initialized()

        memories: List[MemoryRecord] = []

        # Get recent working memories
        if self._redis:
            try:
                pattern = f"memory:working:{user_id}:*"
                keys = []
                async for key in self._redis.scan_iter(match=pattern, count=50):
                    keys.append(key)

                for key in keys[:5]:  # Get 5 most recent
                    data = await self._redis.get(key)
                    if data:
                        record = MemoryRecord.from_dict(json.loads(data))
                        memories.append(record)

            except Exception as e:
                logger.warning(f"Failed to get working memory context: {e}")

        # If query provided, search for relevant memories
        if query:
            search_results = await self.search(
                query=query,
                user_id=user_id,
                layers=[MemoryLayer.LONG_TERM],
                limit=limit - len(memories),
            )
            memories.extend([r.memory for r in search_results])

        return memories[:limit]

    async def promote(
        self,
        memory_id: str,
        user_id: str,
        from_layer: MemoryLayer,
        to_layer: MemoryLayer,
    ) -> Optional[MemoryRecord]:
        """
        Promote a memory to a higher layer.

        Args:
            memory_id: Memory identifier.
            user_id: User identifier.
            from_layer: Source layer.
            to_layer: Target layer.

        Returns:
            The promoted MemoryRecord, or None if failed.
        """
        self._ensure_initialized()

        # Get memory from source layer
        record = None

        if from_layer == MemoryLayer.WORKING and self._redis:
            key = f"memory:working:{user_id}:{memory_id}"
            data = await self._redis.get(key)
            if data:
                record = MemoryRecord.from_dict(json.loads(data))

        elif from_layer == MemoryLayer.SESSION and self._redis:
            key = f"memory:session:{user_id}:{memory_id}"
            data = await self._redis.get(key)
            if data:
                record = MemoryRecord.from_dict(json.loads(data))

        if not record:
            logger.warning(f"Memory {memory_id} not found in {from_layer.value}")
            return None

        # Store in target layer
        record.layer = to_layer
        record.updated_at = datetime.utcnow()

        if to_layer == MemoryLayer.LONG_TERM:
            promoted = await self._mem0_client.add_memory(
                content=record.content,
                user_id=record.user_id,
                memory_type=record.memory_type,
                metadata=record.metadata,
            )
            return promoted

        logger.info(
            f"Memory {memory_id[:8]}... promoted from "
            f"{from_layer.value} to {to_layer.value}"
        )
        return record

    async def delete(
        self,
        memory_id: str,
        user_id: str,
        layer: Optional[MemoryLayer] = None,
    ) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: Memory identifier.
            user_id: User identifier.
            layer: Optional layer specification.

        Returns:
            True if deleted successfully.
        """
        self._ensure_initialized()

        deleted = False

        # Try to delete from all layers if layer not specified
        layers = [layer] if layer else list(MemoryLayer)

        for target_layer in layers:
            if target_layer == MemoryLayer.WORKING and self._redis:
                key = f"memory:working:{user_id}:{memory_id}"
                result = await self._redis.delete(key)
                if result:
                    deleted = True

            elif target_layer == MemoryLayer.SESSION and self._redis:
                key = f"memory:session:{user_id}:{memory_id}"
                result = await self._redis.delete(key)
                if result:
                    deleted = True

            elif target_layer == MemoryLayer.LONG_TERM:
                result = await self._mem0_client.delete_memory(memory_id)
                if result:
                    deleted = True

        return deleted

    async def get_user_memories(
        self,
        user_id: str,
        memory_types: Optional[List[MemoryType]] = None,
        layers: Optional[List[MemoryLayer]] = None,
    ) -> List[MemoryRecord]:
        """
        Get all memories for a user.

        Args:
            user_id: User identifier.
            memory_types: Optional filter by memory types.
            layers: Optional filter by layers.

        Returns:
            List of MemoryRecord objects.
        """
        self._ensure_initialized()

        memories: List[MemoryRecord] = []
        target_layers = layers or list(MemoryLayer)

        # Get from working memory
        if MemoryLayer.WORKING in target_layers and self._redis:
            try:
                pattern = f"memory:working:{user_id}:*"
                async for key in self._redis.scan_iter(match=pattern, count=100):
                    data = await self._redis.get(key)
                    if data:
                        record = MemoryRecord.from_dict(json.loads(data))
                        if not memory_types or record.memory_type in memory_types:
                            memories.append(record)
            except Exception as e:
                logger.warning(f"Failed to get working memories: {e}")

        # Get from session memory
        if MemoryLayer.SESSION in target_layers and self._redis:
            try:
                pattern = f"memory:session:{user_id}:*"
                async for key in self._redis.scan_iter(match=pattern, count=100):
                    data = await self._redis.get(key)
                    if data:
                        record = MemoryRecord.from_dict(json.loads(data))
                        if not memory_types or record.memory_type in memory_types:
                            memories.append(record)
            except Exception as e:
                logger.warning(f"Failed to get session memories: {e}")

        # Get from long-term memory
        if MemoryLayer.LONG_TERM in target_layers:
            long_term = await self._mem0_client.get_all(
                user_id=user_id,
                memory_types=memory_types,
            )
            memories.extend(long_term)

        return memories

    async def close(self) -> None:
        """Clean up all resources."""
        await self._mem0_client.close()
        await self._embedding_service.close()

        if self._redis:
            await self._redis.close()
            self._redis = None

        self._initialized = False
        logger.info("UnifiedMemoryManager closed")
