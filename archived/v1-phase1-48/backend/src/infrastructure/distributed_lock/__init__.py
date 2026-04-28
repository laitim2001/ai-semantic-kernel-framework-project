"""
Distributed Lock Infrastructure — Sprint 119

Provides Redis-based distributed locking for multi-worker environments.

Usage:
    from src.infrastructure.distributed_lock import DistributedLock, create_distributed_lock

    lock = await create_distributed_lock("context_sync")
    async with lock.acquire():
        # Critical section
        await do_something()
"""

from src.infrastructure.distributed_lock.redis_lock import (
    DistributedLock,
    InMemoryLock,
    RedisDistributedLock,
    create_distributed_lock,
)

__all__ = [
    "DistributedLock",
    "RedisDistributedLock",
    "InMemoryLock",
    "create_distributed_lock",
]
