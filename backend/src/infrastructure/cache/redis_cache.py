"""
Redis cache wrapper - Re-export CacheService as RedisCache for compatibility
"""
from .cache_service import CacheService as RedisCache
from .redis_manager import get_redis

__all__ = ["RedisCache", "get_redis"]


def get_cache() -> RedisCache:
    """
    Get Redis cache instance

    Returns:
        RedisCache instance
    """
    return RedisCache()
