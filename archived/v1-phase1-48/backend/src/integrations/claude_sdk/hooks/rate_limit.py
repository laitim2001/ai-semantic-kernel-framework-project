"""Rate Limit Hook for Claude SDK.

Sprint 49: S49-3 - Hooks System (10 pts)
Limits tool execution rate and concurrent operations.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from .base import Hook
from ..types import HookResult, ToolCallContext, ToolResultContext


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Maximum calls per minute (0 = unlimited)
    calls_per_minute: int = 60

    # Maximum concurrent calls (0 = unlimited)
    max_concurrent: int = 10

    # Cooldown period after hitting limit (seconds)
    cooldown_seconds: float = 5.0

    # Whether to queue requests instead of rejecting
    queue_on_limit: bool = False

    # Maximum queue wait time (seconds)
    max_queue_wait: float = 30.0


@dataclass
class RateLimitStats:
    """Statistics for rate limiting."""

    total_calls: int = 0
    rejected_calls: int = 0
    queued_calls: int = 0
    current_concurrent: int = 0
    calls_this_minute: int = 0
    minute_start_time: float = field(default_factory=time.time)

    def reset_minute(self) -> None:
        """Reset minute counter."""
        self.calls_this_minute = 0
        self.minute_start_time = time.time()


class RateLimitHook(Hook):
    """Hook that limits tool execution rate.

    Provides two types of rate limiting:
    1. Calls per minute - prevents excessive API usage
    2. Concurrent calls - prevents resource exhaustion

    Args:
        calls_per_minute: Max calls per minute (0 = unlimited)
        max_concurrent: Max concurrent calls (0 = unlimited)
        cooldown_seconds: Wait time after hitting limit
        queue_on_limit: Queue requests instead of rejecting
        per_tool_limits: Optional per-tool rate limits

    Example:
        # Global limit of 30 calls/min, max 5 concurrent
        hook = RateLimitHook(calls_per_minute=30, max_concurrent=5)

        # Per-tool limits
        hook = RateLimitHook(
            calls_per_minute=60,
            per_tool_limits={
                "Bash": RateLimitConfig(calls_per_minute=10, max_concurrent=2),
            }
        )
    """

    name: str = "rate_limit"
    priority: int = 80  # High priority - check early

    def __init__(
        self,
        calls_per_minute: int = 60,
        max_concurrent: int = 10,
        cooldown_seconds: float = 5.0,
        queue_on_limit: bool = False,
        max_queue_wait: float = 30.0,
        per_tool_limits: Optional[Dict[str, RateLimitConfig]] = None,
    ):
        self.default_config = RateLimitConfig(
            calls_per_minute=calls_per_minute,
            max_concurrent=max_concurrent,
            cooldown_seconds=cooldown_seconds,
            queue_on_limit=queue_on_limit,
            max_queue_wait=max_queue_wait,
        )

        self.per_tool_limits = per_tool_limits or {}

        # Statistics per session
        self._session_stats: Dict[str, RateLimitStats] = defaultdict(RateLimitStats)

        # Per-tool statistics
        self._tool_stats: Dict[str, RateLimitStats] = defaultdict(RateLimitStats)

        # Active calls tracking
        self._active_calls: Dict[str, Set[str]] = defaultdict(set)

        # Semaphore for concurrent limit
        self._semaphore: Optional[asyncio.Semaphore] = None
        if max_concurrent > 0:
            self._semaphore = asyncio.Semaphore(max_concurrent)

        # Per-tool semaphores
        self._tool_semaphores: Dict[str, asyncio.Semaphore] = {}

        # Call timestamps for rate calculation
        self._call_timestamps: list[float] = []

    async def on_session_start(self, session_id: str) -> None:
        """Initialize session rate limit state."""
        self._session_stats[session_id] = RateLimitStats()
        self._active_calls[session_id] = set()

    async def on_session_end(self, session_id: str) -> None:
        """Clean up session rate limit state."""
        self._session_stats.pop(session_id, None)
        self._active_calls.pop(session_id, None)

    async def on_tool_call(self, context: ToolCallContext) -> HookResult:
        """Check rate limits before tool execution."""
        tool_name = context.tool_name
        session_id = context.session_id or "default"

        # Get config for this tool
        config = self.per_tool_limits.get(tool_name, self.default_config)

        # Check per-minute rate
        if config.calls_per_minute > 0:
            result = await self._check_rate_limit(config, session_id, tool_name)
            if result.is_rejected:
                return result

        # Check concurrent limit
        if config.max_concurrent > 0:
            result = await self._check_concurrent_limit(config, session_id, tool_name)
            if result.is_rejected:
                return result

        # Track this call
        call_id = f"{session_id}:{tool_name}:{time.time()}"
        self._active_calls[session_id].add(call_id)
        self._call_timestamps.append(time.time())

        # Update stats
        stats = self._session_stats[session_id]
        stats.total_calls += 1
        stats.calls_this_minute += 1
        stats.current_concurrent += 1

        tool_stats = self._tool_stats[tool_name]
        tool_stats.total_calls += 1
        tool_stats.calls_this_minute += 1
        tool_stats.current_concurrent += 1

        return HookResult.ALLOW

    async def on_tool_result(self, context: ToolResultContext) -> None:
        """Update rate limit state after tool execution."""
        session_id = context.session_id or "default"
        tool_name = context.tool_name

        # Update concurrent counts
        stats = self._session_stats.get(session_id)
        if stats:
            stats.current_concurrent = max(0, stats.current_concurrent - 1)

        tool_stats = self._tool_stats.get(tool_name)
        if tool_stats:
            tool_stats.current_concurrent = max(0, tool_stats.current_concurrent - 1)

        # Release semaphore if using one
        if self._semaphore:
            self._semaphore.release()

        tool_sem = self._tool_semaphores.get(tool_name)
        if tool_sem:
            tool_sem.release()

    async def _check_rate_limit(
        self,
        config: RateLimitConfig,
        session_id: str,
        tool_name: str,
    ) -> HookResult:
        """Check per-minute rate limit."""
        current_time = time.time()

        # Clean old timestamps (older than 1 minute)
        self._call_timestamps = [
            ts for ts in self._call_timestamps
            if current_time - ts < 60
        ]

        # Check session stats
        stats = self._session_stats[session_id]

        # Reset minute counter if needed
        if current_time - stats.minute_start_time >= 60:
            stats.reset_minute()

        # Check if at limit
        if len(self._call_timestamps) >= config.calls_per_minute:
            stats.rejected_calls += 1

            if config.queue_on_limit:
                # Wait for cooldown
                stats.queued_calls += 1
                await asyncio.sleep(config.cooldown_seconds)

                # Recheck after wait
                if len(self._call_timestamps) >= config.calls_per_minute:
                    return HookResult.reject(
                        f"Rate limit exceeded: {config.calls_per_minute} calls/min "
                        f"(queued {config.cooldown_seconds}s, still at limit)"
                    )
            else:
                return HookResult.reject(
                    f"Rate limit exceeded: {config.calls_per_minute} calls/min"
                )

        return HookResult.ALLOW

    async def _check_concurrent_limit(
        self,
        config: RateLimitConfig,
        session_id: str,
        tool_name: str,
    ) -> HookResult:
        """Check concurrent execution limit."""
        stats = self._session_stats[session_id]

        if stats.current_concurrent >= config.max_concurrent:
            if config.queue_on_limit:
                # Try to acquire semaphore with timeout
                semaphore = self._get_semaphore(tool_name, config.max_concurrent)
                try:
                    await asyncio.wait_for(
                        semaphore.acquire(),
                        timeout=config.max_queue_wait,
                    )
                    return HookResult.ALLOW
                except asyncio.TimeoutError:
                    stats.rejected_calls += 1
                    return HookResult.reject(
                        f"Concurrent limit exceeded: {config.max_concurrent} "
                        f"(waited {config.max_queue_wait}s)"
                    )
            else:
                stats.rejected_calls += 1
                return HookResult.reject(
                    f"Concurrent limit exceeded: {config.max_concurrent} active calls"
                )

        # Acquire semaphore
        semaphore = self._get_semaphore(tool_name, config.max_concurrent)
        await semaphore.acquire()

        return HookResult.ALLOW

    def _get_semaphore(self, tool_name: str, limit: int) -> asyncio.Semaphore:
        """Get or create semaphore for a tool."""
        if tool_name not in self._tool_semaphores:
            self._tool_semaphores[tool_name] = asyncio.Semaphore(limit)
        return self._tool_semaphores[tool_name]

    def get_stats(self, session_id: Optional[str] = None) -> Dict:
        """Get rate limit statistics."""
        if session_id:
            stats = self._session_stats.get(session_id)
            if stats:
                return {
                    "session_id": session_id,
                    "total_calls": stats.total_calls,
                    "rejected_calls": stats.rejected_calls,
                    "queued_calls": stats.queued_calls,
                    "current_concurrent": stats.current_concurrent,
                    "calls_this_minute": stats.calls_this_minute,
                }
            return {}

        # All sessions
        return {
            session_id: {
                "total_calls": s.total_calls,
                "rejected_calls": s.rejected_calls,
                "current_concurrent": s.current_concurrent,
            }
            for session_id, s in self._session_stats.items()
        }

    def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict:
        """Get per-tool statistics."""
        if tool_name:
            stats = self._tool_stats.get(tool_name)
            if stats:
                return {
                    "tool_name": tool_name,
                    "total_calls": stats.total_calls,
                    "current_concurrent": stats.current_concurrent,
                }
            return {}

        return {
            name: {
                "total_calls": s.total_calls,
                "current_concurrent": s.current_concurrent,
            }
            for name, s in self._tool_stats.items()
        }

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._session_stats.clear()
        self._tool_stats.clear()
        self._call_timestamps.clear()
