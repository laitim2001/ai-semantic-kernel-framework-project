# =============================================================================
# IPA Platform - Unified Context Synchronizer
# =============================================================================
# Sprint 53: Context Bridge & Sync (original)
# Sprint 119: Redis Distributed Lock upgrade + unified implementation
#
# Implements synchronization between MAF and Claude contexts with:
#   - Redis Distributed Lock (multi-worker safe)
#   - Optimistic locking (version control)
#   - Conflict detection and resolution
#   - Sync event publishing
#   - Rollback support
#   - Fallback to asyncio.Lock when Redis is unavailable
#
# This is the UNIFIED ContextSynchronizer — Sprint 119 merged the
# hybrid and claude_sdk implementations into this single module.
# =============================================================================

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from ..models import (
    ClaudeContext,
    Conflict,
    HybridContext,
    MAFContext,
    SyncDirection,
    SyncResult,
    SyncStatus,
    SyncStrategy,
)
from .conflict import ConflictResolver
from .events import SyncEventPublisher

logger = logging.getLogger(__name__)


class SyncError(Exception):
    """Base exception for sync errors."""

    def __init__(self, message: str, recoverable: bool = True):
        super().__init__(message)
        self.recoverable = recoverable


class VersionConflictError(SyncError):
    """Raised when version conflict cannot be auto-resolved."""

    def __init__(self, local_version: int, remote_version: int):
        super().__init__(
            f"Version conflict: local={local_version}, remote={remote_version}",
            recoverable=True,
        )
        self.local_version = local_version
        self.remote_version = remote_version


class SyncTimeoutError(SyncError):
    """Raised when sync operation times out."""

    def __init__(self, timeout_ms: int):
        super().__init__(f"Sync operation timed out after {timeout_ms}ms", recoverable=True)
        self.timeout_ms = timeout_ms


# =============================================================================
# Lock Abstraction — supports both Redis Distributed Lock and asyncio.Lock
# =============================================================================


class _AsyncioLockAdapter:
    """Adapts asyncio.Lock to the DistributedLock interface."""

    def __init__(self):
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[None, None]:
        async with self._lock:
            yield


async def _create_lock(lock_name: str = "context_sync"):
    """Create a distributed lock, with asyncio.Lock fallback."""
    try:
        from src.infrastructure.distributed_lock import create_distributed_lock
        return await create_distributed_lock(
            lock_name=lock_name,
            timeout=30,
            blocking_timeout=10,
        )
    except Exception as e:
        logger.warning(
            f"Distributed lock unavailable for '{lock_name}': {e}. "
            f"Using asyncio.Lock fallback (single-process only)."
        )
        return _AsyncioLockAdapter()


class ContextSynchronizer:
    """
    統一上下文同步器 — Sprint 119 Unified Implementation

    實現 MAF 和 Claude 上下文之間的雙向同步。
    使用 Redis Distributed Lock 確保多 Worker 環境下的並發安全。

    Features:
    - Redis Distributed Lock（多進程安全）
    - 樂觀鎖版本控制
    - 衝突檢測與解決
    - 同步事件發布
    - 回滾支持
    - 異步操作
    - Redis 不可用時自動降級為 asyncio.Lock

    Example:
        synchronizer = await ContextSynchronizer.create()
        result = await synchronizer.sync(
            source=hybrid_context,
            target_type="maf",
            strategy=SyncStrategy.MERGE,
        )

        if not result.success:
            # Handle failure or conflicts
            pass
    """

    def __init__(
        self,
        conflict_resolver: Optional[ConflictResolver] = None,
        event_publisher: Optional[SyncEventPublisher] = None,
        max_retries: int = 3,
        timeout_ms: int = 30000,
        auto_resolve_conflicts: bool = True,
        distributed_lock: Optional[Any] = None,
    ):
        """
        Initialize ContextSynchronizer.

        Args:
            conflict_resolver: Resolver for handling conflicts
            event_publisher: Publisher for sync events
            max_retries: Maximum retry attempts for recoverable errors
            timeout_ms: Sync operation timeout in milliseconds
            auto_resolve_conflicts: Whether to auto-resolve conflicts
            distributed_lock: Optional pre-configured lock (for testing/DI).
                              If None, uses asyncio.Lock as default.
                              Call initialize_lock() to upgrade to Redis.
        """
        self._conflict_resolver = conflict_resolver or ConflictResolver()
        self._event_publisher = event_publisher or SyncEventPublisher()
        self._max_retries = max_retries
        self._timeout_ms = timeout_ms
        self._auto_resolve_conflicts = auto_resolve_conflicts

        # Sprint 119: Distributed lock (defaults to asyncio.Lock, upgradeable)
        self._lock = distributed_lock or _AsyncioLockAdapter()

        # Version tracking per context
        self._context_versions: Dict[str, int] = {}

        # Rollback snapshots
        self._rollback_snapshots: Dict[str, List[HybridContext]] = {}
        self._max_snapshots = 5

    @classmethod
    async def create(
        cls,
        conflict_resolver: Optional[ConflictResolver] = None,
        event_publisher: Optional[SyncEventPublisher] = None,
        max_retries: int = 3,
        timeout_ms: int = 30000,
        auto_resolve_conflicts: bool = True,
        lock_name: str = "context_sync",
    ) -> "ContextSynchronizer":
        """
        Async factory method that creates a ContextSynchronizer with Redis lock.

        Use this instead of __init__ for production code to get distributed locking.

        Args:
            conflict_resolver: Resolver for handling conflicts
            event_publisher: Publisher for sync events
            max_retries: Maximum retry attempts
            timeout_ms: Sync operation timeout in milliseconds
            auto_resolve_conflicts: Whether to auto-resolve conflicts
            lock_name: Name for the distributed lock

        Returns:
            ContextSynchronizer with Redis distributed lock (or asyncio.Lock fallback)
        """
        lock = await _create_lock(lock_name)
        return cls(
            conflict_resolver=conflict_resolver,
            event_publisher=event_publisher,
            max_retries=max_retries,
            timeout_ms=timeout_ms,
            auto_resolve_conflicts=auto_resolve_conflicts,
            distributed_lock=lock,
        )

    async def initialize_lock(self, lock_name: str = "context_sync") -> None:
        """
        Initialize or upgrade the distributed lock.

        Call this after construction if Redis becomes available later.
        """
        self._lock = await _create_lock(lock_name)
        logger.info(f"Lock initialized/upgraded for '{lock_name}'")

    async def sync(
        self,
        source: HybridContext,
        target_type: str,
        strategy: SyncStrategy = SyncStrategy.MERGE,
    ) -> SyncResult:
        """
        Synchronize context to target type.

        Args:
            source: Source hybrid context
            target_type: Target type ("maf" or "claude")
            strategy: Sync strategy to use

        Returns:
            SyncResult with success status and synced context
        """
        start_time = time.time()
        context_id = source.context_id
        correlation_id = f"sync-{context_id}-{int(start_time * 1000)}"

        logger.info(
            f"Starting sync for context {context_id} "
            f"to {target_type} with strategy {strategy}"
        )

        # Determine sync direction
        direction = (
            SyncDirection.CLAUDE_TO_MAF
            if target_type.lower() == "maf"
            else SyncDirection.MAF_TO_CLAUDE
        )

        # Publish sync started event
        await self._event_publisher.publish_sync_started(
            session_id=context_id,
            strategy=strategy,
            correlation_id=correlation_id,
        )

        try:
            # Save snapshot for rollback (under distributed lock)
            async with self._lock.acquire():
                self._save_snapshot(source)

            # Perform sync with retry logic
            result = await self._sync_with_retry(
                source=source,
                target_type=target_type,
                strategy=strategy,
                direction=direction,
                correlation_id=correlation_id,
            )

            # Update version tracking (under distributed lock)
            if result.success:
                async with self._lock.acquire():
                    self._context_versions[context_id] = result.target_version

            # Calculate duration
            result.duration_ms = int((time.time() - start_time) * 1000)
            result.completed_at = datetime.utcnow()

            # Publish completion event
            if result.success:
                await self._event_publisher.publish_sync_completed(
                    session_id=context_id,
                    result=result,
                    correlation_id=correlation_id,
                )

            return result

        except SyncError as e:
            logger.error(f"Sync error: {e}")
            await self._event_publisher.publish_sync_failed(
                session_id=context_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return SyncResult(
                success=False,
                direction=direction,
                strategy=strategy,
                source_version=source.version,
                target_version=source.version,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.exception(f"Unexpected sync error: {e}")
            await self._event_publisher.publish_sync_failed(
                session_id=context_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return SyncResult(
                success=False,
                direction=direction,
                strategy=strategy,
                source_version=source.version,
                target_version=source.version,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def _sync_with_retry(
        self,
        source: HybridContext,
        target_type: str,
        strategy: SyncStrategy,
        direction: SyncDirection,
        correlation_id: str,
    ) -> SyncResult:
        """Perform sync with retry logic."""
        last_error = None

        for attempt in range(self._max_retries):
            try:
                return await self._do_sync(
                    source=source,
                    target_type=target_type,
                    strategy=strategy,
                    direction=direction,
                    correlation_id=correlation_id,
                )
            except SyncError as e:
                last_error = e
                if not e.recoverable:
                    raise
                logger.warning(f"Sync attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

        raise last_error or SyncError("Sync failed after max retries")

    async def _do_sync(
        self,
        source: HybridContext,
        target_type: str,
        strategy: SyncStrategy,
        direction: SyncDirection,
        correlation_id: str,
    ) -> SyncResult:
        """Perform the actual sync operation."""
        # Prepare synced context based on direction
        if direction == SyncDirection.CLAUDE_TO_MAF:
            synced_context = await self._sync_to_maf(source, strategy)
            changes_applied = self._count_maf_items(synced_context)
        else:
            synced_context = await self._sync_to_claude(source, strategy)
            changes_applied = self._count_claude_items(synced_context)

        # Increment version
        new_version = source.version + 1
        synced_context.version = new_version
        synced_context.last_sync_at = datetime.utcnow()
        synced_context.sync_status = SyncStatus.SYNCED

        # Update version event
        await self._event_publisher.publish_version_updated(
            session_id=source.context_id,
            old_version=source.version,
            new_version=new_version,
            correlation_id=correlation_id,
        )

        return SyncResult(
            success=True,
            direction=direction,
            strategy=strategy,
            source_version=source.version,
            target_version=new_version,
            changes_applied=changes_applied,
            hybrid_context=synced_context,
        )

    async def _sync_to_maf(
        self,
        source: HybridContext,
        strategy: SyncStrategy,
    ) -> HybridContext:
        """Sync context to MAF format."""
        maf_context = source.maf

        if not maf_context:
            session_id = source.claude.session_id if source.claude else source.context_id
            maf_context = MAFContext(
                workflow_id=session_id,
                workflow_name=f"session-{session_id[:8]}",
            )

        if source.claude:
            checkpoint_data = dict(maf_context.checkpoint_data or {})

            if source.claude.context_variables:
                for key, value in source.claude.context_variables.items():
                    if key.startswith("maf_"):
                        clean_key = key[4:]
                        checkpoint_data[clean_key] = value
                    elif not key.startswith("claude_"):
                        checkpoint_data[key] = value

            maf_context = MAFContext(
                workflow_id=maf_context.workflow_id,
                workflow_name=maf_context.workflow_name,
                current_step=maf_context.current_step,
                total_steps=maf_context.total_steps,
                agent_states=maf_context.agent_states,
                checkpoint_data=checkpoint_data,
                pending_approvals=maf_context.pending_approvals,
                execution_history=maf_context.execution_history,
                metadata=maf_context.metadata,
                last_updated=datetime.utcnow(),
            )

        return HybridContext(
            context_id=source.context_id,
            maf=maf_context,
            claude=source.claude,
            primary_framework=source.primary_framework,
            version=source.version,
        )

    async def _sync_to_claude(
        self,
        source: HybridContext,
        strategy: SyncStrategy,
    ) -> HybridContext:
        """Sync context to Claude format."""
        claude_context = source.claude

        if not claude_context:
            claude_context = ClaudeContext(
                session_id=source.context_id,
            )

        if source.maf:
            context_vars = dict(claude_context.context_variables or {})

            if source.maf.checkpoint_data:
                for key, value in source.maf.checkpoint_data.items():
                    if not key.startswith("_"):
                        context_vars[f"maf_{key}"] = value

            context_vars["maf_workflow_id"] = source.maf.workflow_id

            if source.maf.current_step is not None:
                context_vars["maf_current_step"] = source.maf.current_step

            claude_context = ClaudeContext(
                session_id=claude_context.session_id,
                conversation_history=claude_context.conversation_history,
                tool_call_history=claude_context.tool_call_history,
                current_system_prompt=claude_context.current_system_prompt,
                context_variables=context_vars,
                active_hooks=claude_context.active_hooks,
                mcp_server_states=claude_context.mcp_server_states,
                metadata=claude_context.metadata,
                last_updated=datetime.utcnow(),
            )

        return HybridContext(
            context_id=source.context_id,
            maf=source.maf,
            claude=claude_context,
            primary_framework=source.primary_framework,
            version=source.version,
        )

    def _count_maf_items(self, context: HybridContext) -> int:
        """Count items synced to MAF."""
        count = 0
        if context.maf:
            if context.maf.checkpoint_data:
                count += len(context.maf.checkpoint_data)
            if context.maf.agent_states:
                count += len(context.maf.agent_states)
            if context.maf.execution_history:
                count += len(context.maf.execution_history)
        return count

    def _count_claude_items(self, context: HybridContext) -> int:
        """Count items synced to Claude."""
        count = 0
        if context.claude:
            if context.claude.conversation_history:
                count += len(context.claude.conversation_history)
            if context.claude.context_variables:
                count += len(context.claude.context_variables)
            if context.claude.tool_call_history:
                count += len(context.claude.tool_call_history)
        return count

    async def detect_conflict(
        self,
        local: HybridContext,
        remote: HybridContext,
    ) -> Optional[Conflict]:
        """Detect conflicts between local and remote contexts."""
        return self._conflict_resolver.detect_conflicts(local, remote)

    async def resolve_conflict(
        self,
        local: HybridContext,
        remote: HybridContext,
        conflict: Conflict,
        strategy: Optional[SyncStrategy] = None,
    ) -> SyncResult:
        """Resolve a conflict between contexts."""
        start_time = time.time()
        strategy = strategy or SyncStrategy.MERGE
        correlation_id = f"resolve-{conflict.conflict_id}"

        logger.info(f"Resolving conflict {conflict.conflict_id} with strategy {strategy}")

        try:
            resolved = self._conflict_resolver.resolve(
                conflict=conflict,
                local=local,
                remote=remote,
                strategy=strategy,
            )

            await self._event_publisher.publish_conflict_resolved(
                session_id=local.context_id,
                conflict=conflict,
                strategy_used=strategy,
                correlation_id=correlation_id,
            )

            return SyncResult(
                success=True,
                direction=SyncDirection.BIDIRECTIONAL,
                strategy=strategy,
                source_version=local.version,
                target_version=resolved.version,
                conflicts_resolved=1,
                hybrid_context=resolved,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.exception(f"Failed to resolve conflict: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.BIDIRECTIONAL,
                strategy=strategy,
                source_version=local.version,
                target_version=local.version,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def rollback(
        self,
        context_id: str,
        to_version: Optional[int] = None,
    ) -> SyncResult:
        """Rollback to a previous context version."""
        start_time = time.time()

        async with self._lock.acquire():
            snapshots = self._rollback_snapshots.get(context_id, [])

            if not snapshots:
                return SyncResult(
                    success=False,
                    direction=SyncDirection.BIDIRECTIONAL,
                    strategy=SyncStrategy.SOURCE_WINS,
                    source_version=0,
                    target_version=0,
                    error="No snapshots available for rollback",
                    duration_ms=0,
                )

            if to_version is not None:
                target = next(
                    (s for s in snapshots if s.version == to_version),
                    None,
                )
                if not target:
                    return SyncResult(
                        success=False,
                        direction=SyncDirection.BIDIRECTIONAL,
                        strategy=SyncStrategy.SOURCE_WINS,
                        source_version=0,
                        target_version=0,
                        error=f"Version {to_version} not found in snapshots",
                        duration_ms=0,
                    )
            else:
                target = snapshots[-1]

            current_version = self._context_versions.get(context_id, 0)

        await self._event_publisher.publish_rollback_started(
            session_id=context_id,
            from_version=current_version,
            to_version=target.version,
        )

        try:
            async with self._lock.acquire():
                self._context_versions[context_id] = target.version

            await self._event_publisher.publish_rollback_completed(
                session_id=context_id,
                version=target.version,
            )

            return SyncResult(
                success=True,
                direction=SyncDirection.BIDIRECTIONAL,
                strategy=SyncStrategy.SOURCE_WINS,
                source_version=current_version,
                target_version=target.version,
                changes_applied=1,
                hybrid_context=target,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.exception(f"Rollback failed: {e}")
            return SyncResult(
                success=False,
                direction=SyncDirection.BIDIRECTIONAL,
                strategy=SyncStrategy.SOURCE_WINS,
                source_version=current_version,
                target_version=current_version,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    def _save_snapshot(self, context: HybridContext) -> None:
        """Save a context snapshot for rollback."""
        context_id = context.context_id

        if context_id not in self._rollback_snapshots:
            self._rollback_snapshots[context_id] = []

        snapshots = self._rollback_snapshots[context_id]
        snapshots.append(context)

        if len(snapshots) > self._max_snapshots:
            self._rollback_snapshots[context_id] = snapshots[-self._max_snapshots:]

    async def get_version(self, context_id: str) -> int:
        """Get current version for a context."""
        async with self._lock.acquire():
            return self._context_versions.get(context_id, 0)

    async def get_snapshots(self, context_id: str) -> List[HybridContext]:
        """Get available snapshots for a context."""
        async with self._lock.acquire():
            return self._rollback_snapshots.get(context_id, []).copy()

    async def clear_snapshots(self, context_id: str) -> None:
        """Clear snapshots for a context."""
        async with self._lock.acquire():
            if context_id in self._rollback_snapshots:
                del self._rollback_snapshots[context_id]

    @property
    def event_publisher(self) -> SyncEventPublisher:
        """Get the event publisher."""
        return self._event_publisher

    @property
    def conflict_resolver(self) -> ConflictResolver:
        """Get the conflict resolver."""
        return self._conflict_resolver
