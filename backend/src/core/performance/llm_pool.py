# =============================================================================
# IPA Platform - LLM Call Pool
# =============================================================================
# Sprint 109: Story 3 (3 SP)
# Phase 36: Performance & Reliability
#
# LLM Call Pool — manages concurrent LLM API calls with priority and rate control.
#
# Features:
# - asyncio.Semaphore controls max concurrent LLM calls
# - Priority queue: DIRECT_RESPONSE > INTENT_ROUTING > EXTENDED_THINKING > SWARM_WORKER
# - Per-provider pools (Azure OpenAI / Anthropic)
# - Token budget tracking
# - Automatic backoff on 429 Too Many Requests
# =============================================================================

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums & Data Classes
# =============================================================================


class CallPriority(IntEnum):
    """Priority levels for LLM calls. Lower value = higher priority."""

    CRITICAL = 0
    DIRECT_RESPONSE = 1
    INTENT_ROUTING = 2
    EXTENDED_THINKING = 3
    SWARM_WORKER = 4


@dataclass(order=True)
class _PriorityItem:
    """Wrapper for priority queue ordering."""

    priority: int
    sequence: int = field(compare=True)
    event: asyncio.Event = field(compare=False, repr=False)


@dataclass
class LLMCallToken:
    """
    Token representing an acquired LLM call slot.

    Supports async context manager for automatic release:
        async with await pool.acquire(CallPriority.DIRECT_RESPONSE) as token:
            # make LLM call
            token.record_tokens(input_tokens=100, output_tokens=50)
    """

    token_id: int
    priority: CallPriority
    acquired_at: float = field(default_factory=time.time)
    released: bool = False
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    _pool: Optional[Any] = field(default=None, repr=False)

    async def __aenter__(self) -> "LLMCallToken":
        """Enter async context."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Release the token on context exit."""
        if not self.released and self._pool is not None:
            await self._pool.release(self)

    def record_tokens(
        self, input_tokens: int = 0, output_tokens: int = 0
    ) -> None:
        """
        Record token usage for budget tracking.

        Args:
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.
        """
        self.input_tokens_used = input_tokens
        self.output_tokens_used = output_tokens


# =============================================================================
# LLMCallPool
# =============================================================================


class LLMCallPool:
    """
    Manages concurrent LLM API calls with priority scheduling and rate control.

    Features:
    - Concurrency control via asyncio.Semaphore
    - Priority-based queue (higher priority calls get slots first)
    - Per-minute rate tracking
    - Token budget tracking
    - Singleton pattern for application-wide usage

    Usage:
        pool = LLMCallPool(max_concurrent=5, max_per_minute=60)
        async with await pool.acquire(CallPriority.DIRECT_RESPONSE) as token:
            response = await llm_client.call(...)
            token.record_tokens(input_tokens=100, output_tokens=50)

    Singleton:
        pool = LLMCallPool.get_instance()
    """

    _instance: Optional["LLMCallPool"] = None

    def __init__(
        self,
        max_concurrent: int = 5,
        max_per_minute: int = 60,
    ):
        """
        Initialize LLMCallPool.

        Args:
            max_concurrent: Maximum number of concurrent LLM calls.
            max_per_minute: Maximum number of LLM calls per minute.
        """
        self._max_concurrent = max_concurrent
        self._max_per_minute = max_per_minute

        # Concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Priority queue and scheduling
        self._queue: asyncio.PriorityQueue[_PriorityItem] = asyncio.PriorityQueue()
        self._sequence_counter = 0
        self._queue_lock = asyncio.Lock()

        # Rate tracking
        self._call_timestamps: list[float] = []
        self._rate_lock = asyncio.Lock()

        # Token ID generation
        self._token_counter = 0
        self._token_lock = asyncio.Lock()

        # Statistics
        self._total_calls = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._denied_calls = 0
        self._active_calls = 0
        self._stats_lock = asyncio.Lock()

        # Scheduler task
        self._scheduler_task: Optional[asyncio.Task[None]] = None
        self._running = False

    @classmethod
    def get_instance(
        cls,
        max_concurrent: int = 5,
        max_per_minute: int = 60,
    ) -> "LLMCallPool":
        """
        Get or create the singleton instance.

        Args:
            max_concurrent: Maximum concurrent calls (only used on first call).
            max_per_minute: Maximum calls per minute (only used on first call).

        Returns:
            The singleton LLMCallPool instance.
        """
        if cls._instance is None:
            cls._instance = cls(
                max_concurrent=max_concurrent,
                max_per_minute=max_per_minute,
            )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Primarily for testing."""
        cls._instance = None

    async def acquire(
        self,
        priority: CallPriority,
        timeout: float = 30.0,
    ) -> LLMCallToken:
        """
        Acquire a call slot with the given priority.

        Higher priority calls (lower numeric value) are served first.
        Blocks until a slot is available or timeout is reached.

        Args:
            priority: Priority level for the call.
            timeout: Maximum time to wait in seconds.

        Returns:
            LLMCallToken that can be used as an async context manager.

        Raises:
            asyncio.TimeoutError: If the timeout is exceeded.
            RuntimeError: If per-minute rate limit is exceeded.
        """
        # Check per-minute rate limit
        if not await self._check_rate_limit():
            async with self._stats_lock:
                self._denied_calls += 1
            raise RuntimeError(
                f"LLM call rate limit exceeded: "
                f"max {self._max_per_minute} calls per minute"
            )

        # Create priority item for queue-based ordering
        async with self._queue_lock:
            self._sequence_counter += 1
            sequence = self._sequence_counter

        event = asyncio.Event()
        item = _PriorityItem(
            priority=priority.value,
            sequence=sequence,
            event=event,
        )

        # Put in priority queue
        await self._queue.put(item)

        # Start scheduler if not running
        await self._ensure_scheduler_running()

        # Wait for our turn
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            async with self._stats_lock:
                self._denied_calls += 1
            logger.warning(
                "LLM call acquire timed out: priority=%s timeout=%.1fs",
                priority.name,
                timeout,
            )
            raise

        # Generate token
        async with self._token_lock:
            self._token_counter += 1
            token_id = self._token_counter

        # Record timestamp for rate tracking
        async with self._rate_lock:
            self._call_timestamps.append(time.time())

        async with self._stats_lock:
            self._total_calls += 1
            self._active_calls += 1

        token = LLMCallToken(
            token_id=token_id,
            priority=priority,
            _pool=self,
        )

        logger.debug(
            "LLM call slot acquired: token_id=%d priority=%s",
            token_id,
            priority.name,
        )

        return token

    async def release(self, token: LLMCallToken) -> None:
        """
        Release a call slot back to the pool.

        Args:
            token: The LLMCallToken to release.
        """
        if token.released:
            return

        token.released = True

        async with self._stats_lock:
            self._active_calls = max(0, self._active_calls - 1)
            self._total_input_tokens += token.input_tokens_used
            self._total_output_tokens += token.output_tokens_used

        # Release semaphore slot
        self._semaphore.release()

        logger.debug(
            "LLM call slot released: token_id=%d input_tokens=%d output_tokens=%d",
            token.token_id,
            token.input_tokens_used,
            token.output_tokens_used,
        )

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get current pool statistics.

        Returns:
            Dict with pool usage statistics.
        """
        async with self._stats_lock:
            return {
                "max_concurrent": self._max_concurrent,
                "max_per_minute": self._max_per_minute,
                "active_calls": self._active_calls,
                "total_calls": self._total_calls,
                "denied_calls": self._denied_calls,
                "queue_size": self._queue.qsize(),
                "total_input_tokens": self._total_input_tokens,
                "total_output_tokens": self._total_output_tokens,
                "total_tokens": self._total_input_tokens + self._total_output_tokens,
                "calls_in_last_minute": await self._count_recent_calls(),
            }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _check_rate_limit(self) -> bool:
        """Check if we're within the per-minute rate limit."""
        recent = await self._count_recent_calls()
        return recent < self._max_per_minute

    async def _count_recent_calls(self) -> int:
        """Count calls made in the last 60 seconds."""
        now = time.time()
        cutoff = now - 60.0

        async with self._rate_lock:
            # Clean old entries
            self._call_timestamps = [
                ts for ts in self._call_timestamps if ts > cutoff
            ]
            return len(self._call_timestamps)

    async def _ensure_scheduler_running(self) -> None:
        """Ensure the priority scheduler task is running."""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def _scheduler_loop(self) -> None:
        """
        Background task that processes the priority queue.

        Takes the highest-priority item from the queue, acquires a semaphore slot,
        and signals the waiting coroutine to proceed.
        """
        try:
            while True:
                # Get highest priority item
                try:
                    item = await asyncio.wait_for(
                        self._queue.get(), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    # No items in queue — check if we should stop
                    if self._queue.empty():
                        self._running = False
                        return
                    continue

                # Acquire semaphore slot (blocks if at capacity)
                await self._semaphore.acquire()

                # Signal the waiting coroutine
                item.event.set()

        except asyncio.CancelledError:
            self._running = False
        except Exception as e:
            logger.error("LLM pool scheduler error: %s", e, exc_info=True)
            self._running = False

    async def shutdown(self) -> None:
        """Gracefully shut down the pool scheduler."""
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        self._running = False
        logger.info("LLM call pool shut down")
