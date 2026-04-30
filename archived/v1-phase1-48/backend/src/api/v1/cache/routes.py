# =============================================================================
# IPA Platform - Cache API Routes
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Redis Cache Implementation
#
# REST API endpoints for LLM cache management.
# Provides:
#   - GET /cache/stats - Get cache statistics
#   - GET /cache/config - Get cache configuration
#   - POST /cache/enable - Enable caching
#   - POST /cache/disable - Disable caching
#   - POST /cache/get - Get cached entry
#   - POST /cache/set - Set cache entry
#   - POST /cache/clear - Clear cache
#   - POST /cache/warm - Warm cache with entries
#   - POST /cache/reset-stats - Reset statistics
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.v1.cache.schemas import (
    CacheClearRequest,
    CacheClearResponse,
    CacheConfigResponse,
    CacheEntryResponse,
    CacheGetRequest,
    CacheSetRequest,
    CacheStatsResponse,
    CacheWarmRequest,
    CacheWarmResponse,
)
from src.infrastructure.cache import LLMCacheService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cache",
    tags=["cache"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Dependency Injection
# =============================================================================

# Global cache service instance (in production, use proper DI with Redis)
_cache_service: Optional[LLMCacheService] = None


async def get_cache_service() -> LLMCacheService:
    """
    Get or create cache service.

    In production, this would use dependency injection with
    a properly configured Redis client.
    """
    global _cache_service

    if _cache_service is None:
        # Create mock Redis client for development
        # In production, inject actual Redis client
        try:
            import redis.asyncio as redis
            client = redis.Redis(
                host="localhost",
                port=6379,
                password="redis_password",
                decode_responses=True,
            )
            _cache_service = LLMCacheService(client)
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using mock service.")
            # Create a disabled cache service for development
            from unittest.mock import AsyncMock
            mock_client = AsyncMock()
            _cache_service = LLMCacheService(mock_client, enabled=False)

    return _cache_service


# =============================================================================
# Statistics
# =============================================================================


@router.get(
    "/stats",
    response_model=CacheStatsResponse,
    summary="Get cache statistics",
    description="Get current cache statistics including hits, misses, and hit rate",
)
async def get_cache_stats(
    cache: LLMCacheService = Depends(get_cache_service),
) -> CacheStatsResponse:
    """
    Get cache statistics.

    Returns hit/miss counts, hit rate, and memory usage.
    """
    try:
        stats = await cache.get_stats()

        return CacheStatsResponse(
            total_entries=stats.total_entries,
            total_hits=stats.total_hits,
            total_misses=stats.total_misses,
            hit_rate=stats.hit_rate,
            hit_rate_percentage=round(stats.hit_rate * 100, 2),
            memory_usage_bytes=stats.memory_usage_bytes,
            last_reset=stats.last_reset,
            enabled=cache.enabled,
        )

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}",
        )


# =============================================================================
# Configuration
# =============================================================================


@router.get(
    "/config",
    response_model=CacheConfigResponse,
    summary="Get cache configuration",
    description="Get current cache configuration settings",
)
async def get_cache_config(
    cache: LLMCacheService = Depends(get_cache_service),
) -> CacheConfigResponse:
    """
    Get cache configuration.
    """
    return CacheConfigResponse(
        enabled=cache.enabled,
        default_ttl_seconds=cache._ttl_seconds,
        key_prefix=cache.KEY_PREFIX,
    )


@router.post(
    "/enable",
    response_model=Dict[str, Any],
    summary="Enable caching",
    description="Enable the LLM response cache",
)
async def enable_cache(
    cache: LLMCacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Enable caching.
    """
    cache.enable()
    return {
        "success": True,
        "message": "Cache enabled",
        "enabled": cache.enabled,
    }


@router.post(
    "/disable",
    response_model=Dict[str, Any],
    summary="Disable caching",
    description="Disable the LLM response cache",
)
async def disable_cache(
    cache: LLMCacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Disable caching.
    """
    cache.disable()
    return {
        "success": True,
        "message": "Cache disabled",
        "enabled": cache.enabled,
    }


# =============================================================================
# Cache Operations
# =============================================================================


@router.post(
    "/get",
    response_model=Optional[CacheEntryResponse],
    summary="Get cached entry",
    description="Retrieve a cached LLM response",
)
async def get_cache_entry(
    request: CacheGetRequest,
    cache: LLMCacheService = Depends(get_cache_service),
) -> Optional[CacheEntryResponse]:
    """
    Get a cached entry by model and prompt.

    Returns None if not found or cache is disabled.
    """
    try:
        entry = await cache.get(
            model=request.model,
            prompt=request.prompt,
        )

        if entry is None:
            return None

        return CacheEntryResponse(
            response=entry.response,
            model=entry.model,
            prompt_hash=entry.prompt_hash,
            created_at=entry.created_at,
            hit_count=entry.hit_count,
            metadata=entry.metadata,
        )

    except Exception as e:
        logger.error(f"Error getting cache entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache entry: {str(e)}",
        )


@router.post(
    "/set",
    response_model=Dict[str, Any],
    summary="Set cache entry",
    description="Cache an LLM response",
)
async def set_cache_entry(
    request: CacheSetRequest,
    cache: LLMCacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Set a cache entry.
    """
    try:
        success = await cache.set(
            model=request.model,
            prompt=request.prompt,
            response=request.response,
            ttl_seconds=request.ttl_seconds,
            metadata=request.metadata,
        )

        return {
            "success": success,
            "message": "Entry cached" if success else "Cache disabled or error",
            "model": request.model,
        }

    except Exception as e:
        logger.error(f"Error setting cache entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set cache entry: {str(e)}",
        )


@router.post(
    "/clear",
    response_model=CacheClearResponse,
    summary="Clear cache",
    description="Clear cache entries (optionally by pattern)",
)
async def clear_cache(
    request: CacheClearRequest,
    cache: LLMCacheService = Depends(get_cache_service),
) -> CacheClearResponse:
    """
    Clear cache entries.

    Requires confirmation flag to prevent accidental clearing.
    """
    if not request.confirm:
        return CacheClearResponse(
            success=False,
            entries_cleared=0,
            message="Confirmation required. Set confirm=true to clear cache.",
        )

    try:
        cleared = await cache.clear(pattern=request.pattern)

        return CacheClearResponse(
            success=True,
            entries_cleared=cleared,
            message=f"Cleared {cleared} cache entries",
        )

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        )


@router.post(
    "/warm",
    response_model=CacheWarmResponse,
    summary="Warm cache",
    description="Pre-populate cache with entries",
)
async def warm_cache(
    request: CacheWarmRequest,
    cache: LLMCacheService = Depends(get_cache_service),
) -> CacheWarmResponse:
    """
    Warm cache with pre-defined entries.
    """
    try:
        cached = await cache.warm_cache(request.entries)

        return CacheWarmResponse(
            success=True,
            entries_cached=cached,
            total_entries=len(request.entries),
        )

    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to warm cache: {str(e)}",
        )


@router.post(
    "/reset-stats",
    response_model=Dict[str, Any],
    summary="Reset statistics",
    description="Reset cache statistics counters",
)
async def reset_cache_stats(
    cache: LLMCacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Reset cache statistics.
    """
    try:
        await cache.reset_stats()

        return {
            "success": True,
            "message": "Cache statistics reset",
            "reset_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error resetting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset cache stats: {str(e)}",
        )
