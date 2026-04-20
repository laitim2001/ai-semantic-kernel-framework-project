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

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .background_tasks import MemoryBackgroundTaskManager
from .embeddings import EmbeddingService
from .mem0_client import Mem0Client
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

        # Sprint 170: safe fire-and-forget manager for access tracking
        self._background_tasks = MemoryBackgroundTaskManager(
            max_concurrency=self.config.memory_background_concurrency
        )

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
            redis_password = os.getenv("REDIS_PASSWORD")

            self._redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password or None,
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
            raise RuntimeError("UnifiedMemoryManager not initialized. Call initialize() first.")

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
        # Pinned knowledge always goes to PINNED layer
        if memory_type == MemoryType.PINNED_KNOWLEDGE:
            return MemoryLayer.PINNED

        # High importance or specific types go to long-term
        if importance >= 0.8:
            return MemoryLayer.LONG_TERM

        if memory_type in [
            MemoryType.EVENT_RESOLUTION,
            MemoryType.BEST_PRACTICE,
            MemoryType.SYSTEM_KNOWLEDGE,
        ]:
            return MemoryLayer.LONG_TERM

        # Extracted types go to long-term
        if memory_type in [
            MemoryType.EXTRACTED_FACT,
            MemoryType.EXTRACTED_PREFERENCE,
            MemoryType.EXTRACTED_PATTERN,
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
        if target_layer == MemoryLayer.PINNED:
            await self._store_pinned_memory(record)
        elif target_layer == MemoryLayer.WORKING:
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
            f"Memory added to {target_layer.value} layer: " f"{memory_id[:8]}... for user {user_id}"
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
            working_results = await self._search_working_memory(query, user_id, memory_types, limit)
            results.extend(working_results)

        # Search session memory
        if MemoryLayer.SESSION in search_layers:
            session_results = await self._search_session_memory(query, user_id, memory_types, limit)
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

        final_results = unique_results[:limit]

        # Sprint 170: merge live counter values (source of truth) + schedule
        # fire-and-forget access tracking. Both are best-effort and do NOT
        # block the search response.
        if final_results:
            await self._merge_counters_into_results(final_results)
            self._background_tasks.fire_and_forget(
                self._track_access_batch(final_results, operation="search_hit"),
                context={
                    "operation": "search_hit",
                    "user_id": user_id,
                    "hit_count": len(final_results),
                },
            )

        return final_results

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

            for key in keys[: limit * 2]:  # Get more than limit for filtering
                data = await self._redis.get(key)
                if data:
                    record_dict = json.loads(data)
                    record = MemoryRecord.from_dict(record_dict)

                    # Filter by memory type
                    if memory_types and record.memory_type not in memory_types:
                        continue

                    # Calculate similarity
                    content_embedding = await self._embedding_service.embed_text(record.content)
                    score = EmbeddingService.compute_similarity(query_embedding, content_embedding)

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

            for key in keys[: limit * 2]:
                data = await self._redis.get(key)
                if data:
                    record_dict = json.loads(data)
                    record = MemoryRecord.from_dict(record_dict)

                    # Filter by memory type
                    if memory_types and record.memory_type not in memory_types:
                        continue

                    # Calculate similarity
                    content_embedding = await self._embedding_service.embed_text(record.content)
                    score = EmbeddingService.compute_similarity(query_embedding, content_embedding)

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

        Priority order (CC-inspired):
        1. PINNED — always loaded, like CC's CLAUDE.md (not counted against limit)
        2. WORKING — recent short-term context
        3. SESSION — medium-term context
        4. LONG_TERM — semantic search results

        Args:
            user_id: User identifier.
            session_id: Optional session identifier.
            query: Optional query for semantic search.
            limit: Maximum non-pinned memories to return.

        Returns:
            List of relevant MemoryRecord objects (pinned first, then others).
        """
        self._ensure_initialized()

        memories: List[MemoryRecord] = []

        # Priority 1: PINNED — always loaded, not counted against limit
        pinned = await self.get_pinned(user_id)
        memories.extend(pinned)

        # Priority 2: Recent working memories
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

        # Priority 3: Recent session memories
        if self._redis:
            try:
                session_pattern = f"memory:session:{user_id}:*"
                session_keys = []
                async for key in self._redis.scan_iter(match=session_pattern, count=50):
                    session_keys.append(key)

                for key in session_keys[:5]:  # Get 5 most recent
                    data = await self._redis.get(key)
                    if data:
                        record = MemoryRecord.from_dict(json.loads(data))
                        memories.append(record)

            except Exception as e:
                logger.warning(f"Failed to get session memory context: {e}")

        # Priority 4: Semantic search for relevant long-term memories
        non_pinned_count = len(memories) - len(pinned)
        remaining = limit - non_pinned_count
        if query and remaining > 0:
            search_results = await self.search(
                query=query,
                user_id=user_id,
                layers=[MemoryLayer.LONG_TERM],
                limit=max(1, remaining),
            )
            memories.extend([r.memory for r in search_results])

        return memories

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
            f"Memory {memory_id[:8]}... promoted from " f"{from_layer.value} to {to_layer.value}"
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
            if target_layer == MemoryLayer.PINNED and self._redis:
                hash_key = self._pinned_hash_key(user_id)
                result = await self._redis.hdel(hash_key, memory_id)
                if result:
                    deleted = True

            elif target_layer == MemoryLayer.WORKING and self._redis:
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

        # Get from pinned memory
        if MemoryLayer.PINNED in target_layers:
            pinned = await self.get_pinned(user_id)
            for record in pinned:
                if not memory_types or record.memory_type in memory_types:
                    memories.append(record)

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

    # ── Pinned Knowledge Layer (CC's CLAUDE.md equivalent) ──────────────

    def _pinned_hash_key(self, user_id: str) -> str:
        """Redis hash key for a user's pinned memories."""
        return f"memory:pinned:{user_id}"

    async def _store_pinned_memory(self, record: MemoryRecord) -> None:
        """Store a memory in the pinned layer (Redis hash, no TTL)."""
        if not self._redis:
            logger.warning("Redis unavailable — pinned memory stored to long-term instead")
            await self._mem0_client.add_memory(
                content=record.content,
                user_id=record.user_id,
                memory_type=record.memory_type,
                metadata=record.metadata,
            )
            return

        hash_key = self._pinned_hash_key(record.user_id)

        # Enforce per-user limit
        current_count = await self._redis.hlen(hash_key)
        if current_count >= self.config.max_pinned_per_user:
            raise ValueError(
                f"Pinned memory limit reached ({self.config.max_pinned_per_user}). "
                f"Unpin existing memories before adding new ones."
            )

        await self._redis.hset(hash_key, record.id, json.dumps(record.to_dict()))
        logger.info(
            f"Pinned memory stored: {record.id[:8]}... for user {record.user_id} "
            f"({current_count + 1}/{self.config.max_pinned_per_user})"
        )

    async def pin_memory(
        self,
        content: str,
        user_id: str,
        memory_type: MemoryType = MemoryType.PINNED_KNOWLEDGE,
        metadata: Optional[MemoryMetadata] = None,
    ) -> MemoryRecord:
        """Pin a memory — it will ALWAYS be injected into context.

        This is the server-side equivalent of CC's CLAUDE.md: knowledge that
        the system should always have available regardless of semantic relevance.

        Args:
            content: The knowledge to pin.
            user_id: User identifier.
            memory_type: Defaults to PINNED_KNOWLEDGE.
            metadata: Optional metadata.

        Returns:
            The pinned MemoryRecord.

        Raises:
            ValueError: If pinned limit reached.
        """
        return await self.add(
            content=content,
            user_id=user_id,
            memory_type=memory_type,
            metadata=metadata,
            layer=MemoryLayer.PINNED,
        )

    async def unpin_memory(
        self,
        memory_id: str,
        user_id: str,
        demote_to: MemoryLayer = MemoryLayer.LONG_TERM,
    ) -> bool:
        """Unpin a memory. Optionally demotes it to another layer.

        Args:
            memory_id: Memory to unpin.
            user_id: User identifier.
            demote_to: Layer to move the memory to (default: LONG_TERM).

        Returns:
            True if successfully unpinned.
        """
        self._ensure_initialized()

        if not self._redis:
            return False

        hash_key = self._pinned_hash_key(user_id)
        data = await self._redis.hget(hash_key, memory_id)
        if not data:
            return False

        # Remove from pinned
        await self._redis.hdel(hash_key, memory_id)

        # Demote to target layer
        record = MemoryRecord.from_dict(json.loads(data))
        record.layer = demote_to
        record.updated_at = datetime.utcnow()

        if demote_to == MemoryLayer.LONG_TERM:
            await self._mem0_client.add_memory(
                content=record.content,
                user_id=record.user_id,
                memory_type=record.memory_type,
                metadata=record.metadata,
            )
        elif demote_to == MemoryLayer.SESSION:
            await self._store_session_memory(record)

        logger.info(
            f"Memory unpinned: {memory_id[:8]}... → {demote_to.value} " f"for user {user_id}"
        )
        return True

    async def get_pinned(self, user_id: str) -> List[MemoryRecord]:
        """Get ALL pinned memories for a user. No search needed — always returned.

        This is the core mechanism: pinned memories are unconditionally
        injected into every pipeline context, like CC's CLAUDE.md.

        Args:
            user_id: User identifier.

        Returns:
            List of all pinned MemoryRecord objects.
        """
        self._ensure_initialized()

        if not self._redis:
            return []

        try:
            hash_key = self._pinned_hash_key(user_id)
            all_data = await self._redis.hgetall(hash_key)

            records = []
            for mem_id, data in all_data.items():
                try:
                    record = MemoryRecord.from_dict(json.loads(data))
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse pinned memory {mem_id}: {e}")

            # Sort by created_at (newest first)
            records.sort(key=lambda r: r.created_at, reverse=True)
            return records

        except Exception as e:
            logger.warning(f"Failed to get pinned memories for {user_id}: {e}")
            return []

    async def update_pinned(
        self,
        memory_id: str,
        user_id: str,
        content: Optional[str] = None,
        metadata: Optional[MemoryMetadata] = None,
    ) -> Optional[MemoryRecord]:
        """Update a pinned memory's content or metadata.

        Args:
            memory_id: Memory to update.
            user_id: User identifier.
            content: New content (if updating).
            metadata: New metadata (if updating).

        Returns:
            Updated MemoryRecord, or None if not found.
        """
        self._ensure_initialized()

        if not self._redis:
            return None

        hash_key = self._pinned_hash_key(user_id)
        data = await self._redis.hget(hash_key, memory_id)
        if not data:
            return None

        record = MemoryRecord.from_dict(json.loads(data))

        if content is not None:
            record.content = content
        if metadata is not None:
            record.metadata = metadata
        record.updated_at = datetime.utcnow()

        await self._redis.hset(hash_key, memory_id, json.dumps(record.to_dict()))
        logger.info(f"Pinned memory updated: {memory_id[:8]}... for user {user_id}")
        return record

    async def get_pinned_count(self, user_id: str) -> int:
        """Get the number of pinned memories for a user."""
        if not self._redis:
            return 0
        hash_key = self._pinned_hash_key(user_id)
        return await self._redis.hlen(hash_key)

    # ── Updated get_context with Pinned layer ────────────────────────

    # ── Sprint 170: Access Tracking (counter keys + fire-and-forget) ──

    @staticmethod
    def _counter_key(layer: MemoryLayer, user_id: str, memory_id: str) -> str:
        """Redis key for access counter. Independent of memory entry storage."""
        return f"memory:counter:{layer.value}:{user_id}:{memory_id}"

    @staticmethod
    def _accessed_at_key(layer: MemoryLayer, user_id: str, memory_id: str) -> str:
        """Redis key for last-accessed ISO8601 timestamp."""
        return f"memory:accessed_at:{layer.value}:{user_id}:{memory_id}"

    def _ttl_for_layer(self, layer: MemoryLayer) -> Optional[int]:
        """TTL (seconds) matching source memory tier; None = no TTL."""
        if layer == MemoryLayer.WORKING:
            return self.config.working_memory_ttl
        if layer == MemoryLayer.SESSION:
            return self.config.session_memory_ttl
        # PINNED and LONG_TERM have no TTL
        return None

    async def _track_access_single(
        self,
        *,
        memory_id: str,
        layer: MemoryLayer,
        user_id: str,
        operation: str,
    ) -> None:
        """Increment counter + update accessed_at for a single access.

        Raises exceptions — caller wraps in fire_and_forget for DLQ capture.
        """
        now = datetime.now(timezone.utc)
        new_count = 0

        # Redis-backed counter for PINNED / WORKING / SESSION
        if self._redis and layer != MemoryLayer.LONG_TERM:
            counter_key = self._counter_key(layer, user_id, memory_id)
            accessed_key = self._accessed_at_key(layer, user_id, memory_id)
            ttl = self._ttl_for_layer(layer)

            # INCR is atomic — survives races (validated by AC-1 concurrent test)
            new_count = await self._redis.incr(counter_key)
            await self._redis.set(accessed_key, now.isoformat())

            # Align TTL with source memory (if any). PINNED has no TTL — skip.
            if ttl is not None:
                await self._redis.expire(counter_key, ttl)
                await self._redis.expire(accessed_key, ttl)

        # LONG_TERM: propagate to mem0 metadata via thread-safe wrapper.
        # Read-modify-write race is acceptable for Sprint 170 scope (v2 plan).
        if layer == MemoryLayer.LONG_TERM:
            current = 0
            record = await self._mem0_client.get_memory(memory_id)
            if record and record.metadata and record.metadata.custom:
                current = int(record.metadata.custom.get("access_count", 0) or 0)
            new_count = current + 1
            await self._mem0_client.update_access_metadata(memory_id, new_count, now)

        # Structured log event (AC-9)
        logger.info(
            "memory_access_tracked",
            extra={
                "event": "memory_access_tracked",
                "memory_id": memory_id,
                "new_count": new_count,
                "layer": layer.value,
                "tenant_id": user_id,
                "operation": operation,
                "ts": now.isoformat(),
            },
        )

    async def _track_access_batch(
        self,
        hits: List[MemorySearchResult],
        *,
        operation: str,
    ) -> None:
        """Track access for all hits in a search result batch (best-effort)."""
        for hit in hits:
            try:
                await self._track_access_single(
                    memory_id=hit.memory.id,
                    layer=hit.memory.layer,
                    user_id=hit.memory.user_id,
                    operation=operation,
                )
            except Exception as exc:  # noqa: BLE001 — per-hit tolerance
                logger.warning(
                    "per_hit_access_tracking_failed",
                    extra={
                        "memory_id": hit.memory.id,
                        "layer": hit.memory.layer.value,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )

    async def _merge_counters_into_results(self, results: List[MemorySearchResult]) -> None:
        """Fetch live counter values and merge into record.access_count.

        Uses asyncio.gather for parallel Redis reads. Best-effort: any
        individual failure leaves that record's access_count as-is.
        """
        if not self._redis or not results:
            return

        redis_targets: List[tuple[int, str]] = []
        for idx, hit in enumerate(results):
            if hit.memory.layer == MemoryLayer.LONG_TERM:
                continue  # LONG_TERM reads count from mem0 metadata directly
            key = self._counter_key(hit.memory.layer, hit.memory.user_id, hit.memory.id)
            redis_targets.append((idx, key))

        if not redis_targets:
            return

        try:
            raw_values = await asyncio.gather(
                *(self._redis.get(key) for _, key in redis_targets),
                return_exceptions=True,
            )
        except Exception:  # noqa: BLE001 — outer gather safety net
            return

        for (idx, _key), value in zip(redis_targets, raw_values):
            if isinstance(value, Exception) or value is None:
                continue
            try:
                results[idx].memory.access_count = int(value)
            except (ValueError, TypeError):
                continue

    async def get(
        self,
        memory_id: str,
        user_id: str,
        layer: Optional[MemoryLayer] = None,
    ) -> Optional[MemoryRecord]:
        """Retrieve a memory by id with access tracking (Sprint 170 AC-3).

        Searches tiers WORKING → SESSION → LONG_TERM unless ``layer`` specified.
        Increments counter on hit; no increment on miss.

        Args:
            memory_id: Target memory identifier.
            user_id: Owner user id — required for tier key lookup.
            layer: If provided, restrict lookup to that tier only.

        Returns:
            MemoryRecord if found, None otherwise.
        """
        self._ensure_initialized()

        tiers_to_check: List[MemoryLayer] = (
            [layer]
            if layer is not None
            else [
                MemoryLayer.WORKING,
                MemoryLayer.SESSION,
                MemoryLayer.LONG_TERM,
            ]
        )

        for tier in tiers_to_check:
            record = await self._get_from_tier(memory_id, user_id, tier)
            if record is None:
                continue

            self._background_tasks.fire_and_forget(
                self._track_access_single(
                    memory_id=memory_id,
                    layer=tier,
                    user_id=user_id,
                    operation="get_hit",
                ),
                context={
                    "memory_id": memory_id,
                    "layer": tier.value,
                    "user_id": user_id,
                    "operation": "get_hit",
                },
            )
            return record

        return None

    async def _get_from_tier(
        self, memory_id: str, user_id: str, tier: MemoryLayer
    ) -> Optional[MemoryRecord]:
        """Retrieve a memory from a specific tier without triggering tracking."""
        if tier == MemoryLayer.LONG_TERM:
            return await self._mem0_client.get_memory(memory_id)

        if not self._redis:
            return None

        if tier == MemoryLayer.WORKING:
            key = f"memory:working:{user_id}:{memory_id}"
        elif tier == MemoryLayer.SESSION:
            key = f"memory:session:{user_id}:{memory_id}"
        else:
            return None  # PINNED uses hash-based storage; out of scope for get()

        data = await self._redis.get(key)
        if not data:
            return None

        try:
            record = MemoryRecord.from_dict(json.loads(data))
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning(f"Malformed memory record at {key}: {exc}")
            return None

        # Merge live counter value (source of truth) into record
        try:
            counter_key = self._counter_key(tier, user_id, memory_id)
            value = await self._redis.get(counter_key)
            if value is not None:
                record.access_count = int(value)
        except Exception:  # noqa: BLE001 — best-effort merge
            pass

        return record

    # ── Sprint 171: Consolidation Phase 2 Decay support ──────────────

    async def update_importance(
        self,
        memory_id: str,
        user_id: str,
        layer: MemoryLayer,
        new_importance: float,
    ) -> bool:
        """Write back a new importance score to the source tier.

        Used by consolidation Phase 2 Decay. Clamps to [0.0, 1.0].

        - WORKING / SESSION: read JSON from Redis, mutate
          ``metadata.importance``, re-SETEX preserving original TTL.
        - LONG_TERM: delegate to mem0_client via thread executor.
        - PINNED: out of scope (decay doesn't apply — user-pinned).

        Returns True on success, False on any failure (logged, not raised).
        """
        self._ensure_initialized()
        clamped = max(0.0, min(1.0, new_importance))

        if layer == MemoryLayer.LONG_TERM:
            try:
                return await self._mem0_client.update_importance_metadata(memory_id, clamped)
            except Exception as exc:  # noqa: BLE001 — logged for consolidation
                logger.warning(
                    "update_importance_long_term_failed",
                    extra={"memory_id": memory_id, "error": str(exc)},
                )
                return False

        if layer == MemoryLayer.PINNED:
            logger.debug(
                "update_importance_skipped_pinned",
                extra={"memory_id": memory_id},
            )
            return False

        if not self._redis:
            return False

        key = (
            f"memory:working:{user_id}:{memory_id}"
            if layer == MemoryLayer.WORKING
            else f"memory:session:{user_id}:{memory_id}"
        )
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return False
            record = MemoryRecord.from_dict(json.loads(raw))
            record.metadata.importance = clamped
            record.updated_at = datetime.now(timezone.utc)

            ttl = await self._redis.ttl(key)
            if ttl is None or ttl < 0:
                # Key missing TTL (persistent) or expired — use layer default
                ttl = self._ttl_for_layer(layer) or 0

            if ttl > 0:
                await self._redis.setex(key, ttl, json.dumps(record.to_dict()))
            else:
                await self._redis.set(key, json.dumps(record.to_dict()))
            return True
        except Exception as exc:  # noqa: BLE001 — decay should not crash loop
            logger.warning(
                "update_importance_redis_failed",
                extra={
                    "memory_id": memory_id,
                    "layer": layer.value,
                    "error": str(exc),
                },
            )
            return False

    async def close(self) -> None:
        """Clean up all resources."""
        # Sprint 170: drain background tracking tasks before releasing Redis
        await self._background_tasks.close()

        await self._mem0_client.close()
        await self._embedding_service.close()

        if self._redis:
            await self._redis.close()
            self._redis = None

        self._initialized = False
        logger.info("UnifiedMemoryManager closed")
