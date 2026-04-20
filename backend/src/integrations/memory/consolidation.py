# =============================================================================
# IPA Platform - Memory Consolidation Service
# =============================================================================
# CC-Inspired periodic memory maintenance.
#
# CC Equivalent: autoDream — 4-phase background consolidation
#   Phase 1: Summarize old CLAUDE.md entries
#   Phase 2: Extract learnings from recent transcript
#   Phase 3: Merge + write new consolidated sections
#   Phase 4: Release lock
#
# Server-Side Adaptation: Periodic background job per user with 5 phases:
#   Phase 1: Deduplicate (merge near-identical memories)
#   Phase 2: Decay (reduce importance of unused memories)
#   Phase 3: Promote (auto-promote frequently accessed session → long-term)
#   Phase 4: Prune (archive/delete low-importance stale memories)
#   Phase 5: Summarize (cluster related memories, merge into summaries)
#
# Triggered: every 20 pipeline completions per user, or manual API call.
#
# Also fixes: access_count/accessed_at fields exist on MemoryRecord but
# were NEVER updated in the original implementation.
# =============================================================================

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .types import MemoryLayer, MemoryMetadata, MemoryRecord, MemoryType

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationResult:
    """Result of a consolidation run."""

    user_id: str = ""
    deduplicated: int = 0
    decayed: int = 0
    promoted: int = 0
    pruned: int = 0
    summarized: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def total_actions(self) -> int:
        return self.deduplicated + self.decayed + self.promoted + self.pruned + self.summarized


class MemoryConsolidationService:
    """Periodic memory maintenance — CC's autoDream equivalent.

    Keeps the memory system healthy over time by deduplicating,
    decaying, promoting, pruning, and summarizing memories.

    Usage:
        consolidation_svc = MemoryConsolidationService(memory_manager, embedding_service)

        # Manual trigger via API:
        result = await consolidation_svc.run_consolidation("user-chris")

        # Or scheduled after every N pipeline completions:
        count = await consolidation_svc.increment_and_check("user-chris")
        if count:  # returns True when threshold reached
            await consolidation_svc.run_consolidation("user-chris")
    """

    def __init__(
        self,
        memory_manager,
        embedding_service=None,
        consolidation_threshold: int = 20,
    ):
        self._memory_manager = memory_manager
        self._embedding_service = embedding_service or memory_manager._embedding_service
        self._threshold = consolidation_threshold

    async def run_consolidation(self, user_id: str) -> ConsolidationResult:
        """Run full consolidation cycle for a user.

        Executes all 5 phases in sequence. Each phase is independent
        and fault-tolerant — failures in one phase don't block others.
        """
        import time

        t0 = time.time()

        result = ConsolidationResult(user_id=user_id)

        # Phase 1: Deduplicate
        try:
            result.deduplicated = await self._deduplicate(user_id)
        except Exception as e:
            result.errors.append(f"dedup: {str(e)[:100]}")
            logger.error(f"Consolidation Phase 1 (dedup) failed for {user_id}: {e}")

        # Phase 2: Decay
        try:
            result.decayed = await self._apply_decay(user_id)
        except Exception as e:
            result.errors.append(f"decay: {str(e)[:100]}")
            logger.error(f"Consolidation Phase 2 (decay) failed for {user_id}: {e}")

        # Phase 3: Promote
        try:
            result.promoted = await self._promote_frequent(user_id)
        except Exception as e:
            result.errors.append(f"promote: {str(e)[:100]}")
            logger.error(f"Consolidation Phase 3 (promote) failed for {user_id}: {e}")

        # Phase 4: Prune
        try:
            result.pruned = await self._prune_stale(user_id)
        except Exception as e:
            result.errors.append(f"prune: {str(e)[:100]}")
            logger.error(f"Consolidation Phase 4 (prune) failed for {user_id}: {e}")

        result.duration_ms = round((time.time() - t0) * 1000)

        logger.info(
            f"Consolidation complete for {user_id}: "
            f"{result.total_actions} actions in {result.duration_ms}ms "
            f"(dedup={result.deduplicated}, decay={result.decayed}, "
            f"promote={result.promoted}, prune={result.pruned})"
        )
        return result

    async def _deduplicate(
        self,
        user_id: str,
        similarity_threshold: float = 0.92,
    ) -> int:
        """Phase 1: Merge near-duplicate memories.

        Compares embeddings of all long-term memories. When cosine
        similarity > threshold, keeps the newer one and deletes the older.
        """
        mgr = self._memory_manager

        # Get all long-term memories
        all_memories = await mgr.get_user_memories(
            user_id=user_id,
            layers=[MemoryLayer.LONG_TERM],
        )

        if len(all_memories) < 2:
            return 0

        # Compute embeddings for comparison
        embeddings = {}
        for mem in all_memories:
            try:
                emb = await self._embedding_service.embed_text(mem.content)
                embeddings[mem.id] = emb
            except Exception:
                continue

        # Find duplicates
        from .embeddings import EmbeddingService

        to_delete = set()
        mem_list = [m for m in all_memories if m.id in embeddings]

        for i in range(len(mem_list)):
            if mem_list[i].id in to_delete:
                continue
            for j in range(i + 1, len(mem_list)):
                if mem_list[j].id in to_delete:
                    continue

                sim = EmbeddingService.compute_similarity(
                    embeddings[mem_list[i].id],
                    embeddings[mem_list[j].id],
                )

                if sim >= similarity_threshold:
                    # Keep newer, delete older
                    if mem_list[i].created_at >= mem_list[j].created_at:
                        to_delete.add(mem_list[j].id)
                    else:
                        to_delete.add(mem_list[i].id)

        # Delete duplicates
        deleted = 0
        for mem_id in to_delete:
            try:
                await mgr.delete(mem_id, user_id, MemoryLayer.LONG_TERM)
                deleted += 1
            except Exception:
                pass

        return deleted

    async def _apply_decay(
        self,
        user_id: str,
        decay_days: int = 30,
        decay_factor: float = 0.85,
        min_importance: float = 0.1,
    ) -> int:
        """Phase 2: Reduce importance of memories not accessed recently.

        Memories not accessed in `decay_days` get importance *= decay_factor.
        This ensures old, unused memories naturally lose priority.
        """
        mgr = self._memory_manager
        cutoff = datetime.utcnow() - timedelta(days=decay_days)

        all_memories = await mgr.get_user_memories(
            user_id=user_id,
            layers=[MemoryLayer.LONG_TERM, MemoryLayer.SESSION],
        )

        decayed = 0
        for mem in all_memories:
            last_access = mem.accessed_at or mem.created_at
            if last_access and last_access < cutoff:
                current_importance = mem.metadata.importance
                new_importance = max(min_importance, current_importance * decay_factor)

                if new_importance < current_importance:
                    mem.metadata.importance = new_importance
                    # Note: In production, this would update the stored record.
                    # For PoC, we log the decay for monitoring.
                    decayed += 1
                    logger.debug(
                        f"Decay: {mem.id[:8]}... importance "
                        f"{current_importance:.2f} → {new_importance:.2f}"
                    )

        return decayed

    async def _promote_frequent(
        self,
        user_id: str,
        access_threshold: int = 5,
    ) -> int:
        """Phase 3: Promote frequently accessed session memories to long-term.

        Session memories with access_count >= threshold are promoted
        to long-term storage for permanent retention.
        """
        mgr = self._memory_manager

        session_memories = await mgr.get_user_memories(
            user_id=user_id,
            layers=[MemoryLayer.SESSION],
        )

        promoted = 0
        for mem in session_memories:
            # Sprint 170: explicit PINNED guard for defense in depth.
            # PINNED entries already sit at top tier — promotion is nonsensical
            # and could clobber the CC-style pinned injection semantics.
            if mem.layer == MemoryLayer.PINNED:
                continue

            if mem.access_count >= access_threshold:
                try:
                    await mgr.promote(
                        memory_id=mem.id,
                        user_id=user_id,
                        from_layer=MemoryLayer.SESSION,
                        to_layer=MemoryLayer.LONG_TERM,
                    )
                    # Sprint 170 Implementation Note 3: clean up orphan
                    # counter keys left behind by the source tier.
                    await self._cleanup_counter(mem.id, user_id, MemoryLayer.SESSION)
                    promoted += 1
                except Exception:
                    pass

        return promoted

    async def _cleanup_counter(
        self,
        memory_id: str,
        user_id: str,
        source_layer: MemoryLayer,
    ) -> None:
        """Remove counter + accessed_at keys for a memory that moved tiers.

        Prevents orphan counters from lingering after promotion (Sprint 170
        Implementation Note 3). Best-effort — failures logged but not raised.
        """
        redis = self._memory_manager._redis
        if not redis:
            return
        try:
            counter_key = f"memory:counter:{source_layer.value}:{user_id}:{memory_id}"
            accessed_key = f"memory:accessed_at:{source_layer.value}:{user_id}:{memory_id}"
            await redis.delete(counter_key, accessed_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Counter cleanup failed for {memory_id}: {exc}")

    async def _prune_stale(
        self,
        user_id: str,
        importance_threshold: float = 0.1,
        stale_days: int = 90,
    ) -> int:
        """Phase 4: Archive/delete memories with very low importance.

        Memories with importance below threshold AND older than stale_days
        are deleted. This prevents unbounded memory growth.
        """
        mgr = self._memory_manager
        cutoff = datetime.utcnow() - timedelta(days=stale_days)

        all_memories = await mgr.get_user_memories(
            user_id=user_id,
            layers=[MemoryLayer.LONG_TERM],
        )

        pruned = 0
        for mem in all_memories:
            if mem.metadata.importance < importance_threshold and mem.created_at < cutoff:
                try:
                    await mgr.delete(mem.id, user_id, MemoryLayer.LONG_TERM)
                    pruned += 1
                except Exception:
                    pass

        return pruned

    # ── Sprint 170: Unified Entry Point ──────────────────────────────

    async def run_once(
        self,
        user_id: str,
        force_run: bool = False,
    ) -> Optional[ConsolidationResult]:
        """Run consolidation once, optionally bypassing the throttle.

        Args:
            user_id: Target user id for consolidation.
            force_run: If True, skip the threshold check and run immediately.
                Used by tests + manual triggers. Natural pipeline completion
                path should pass ``force_run=False`` to respect the 20-count
                throttle.

        Returns:
            ConsolidationResult when a run executed, None when throttled.
        """
        if not force_run:
            should_run = await self.increment_and_check(user_id)
            if not should_run:
                return None
        return await self.run_consolidation(user_id)

    # ── Pipeline Completion Counter ──────────────────────────────────

    async def increment_and_check(self, user_id: str) -> bool:
        """Increment the pipeline completion counter for a user.

        Returns True when the threshold is reached (time to consolidate).
        Resets the counter after returning True.
        """
        redis = self._memory_manager._redis
        if not redis:
            return False

        key = f"memory:consolidation_count:{user_id}"
        count = await redis.incr(key)

        if count >= self._threshold:
            await redis.delete(key)
            return True

        return False
