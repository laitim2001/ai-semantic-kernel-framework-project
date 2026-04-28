# =============================================================================
# IPA Platform - Cache API Schemas
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Redis Cache Implementation
#
# Pydantic schemas for Cache API endpoints.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CacheStatsResponse(BaseModel):
    """Response schema for cache statistics."""

    total_entries: int = Field(..., description="Total cached entries")
    total_hits: int = Field(..., description="Total cache hits")
    total_misses: int = Field(..., description="Total cache misses")
    hit_rate: float = Field(..., description="Cache hit rate (0.0-1.0)")
    hit_rate_percentage: float = Field(..., description="Cache hit rate as percentage")
    memory_usage_bytes: int = Field(..., description="Estimated memory usage")
    last_reset: datetime = Field(..., description="When stats were reset")
    enabled: bool = Field(..., description="Whether cache is enabled")


class CacheEntryResponse(BaseModel):
    """Response schema for a cache entry."""

    response: str = Field(..., description="Cached response content")
    model: str = Field(..., description="Model identifier")
    prompt_hash: str = Field(..., description="SHA256 hash of prompt")
    created_at: datetime = Field(..., description="When cached")
    hit_count: int = Field(..., description="Number of cache hits")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CacheSetRequest(BaseModel):
    """Request schema for setting a cache entry."""

    model: str = Field(..., description="Model identifier")
    prompt: str = Field(..., description="The prompt text")
    response: str = Field(..., description="The response to cache")
    ttl_seconds: Optional[int] = Field(None, description="TTL override")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CacheGetRequest(BaseModel):
    """Request schema for getting a cache entry."""

    model: str = Field(..., description="Model identifier")
    prompt: str = Field(..., description="The prompt text")


class CacheClearRequest(BaseModel):
    """Request schema for clearing cache."""

    pattern: Optional[str] = Field(None, description="Optional pattern to match")
    confirm: bool = Field(False, description="Confirmation flag")


class CacheClearResponse(BaseModel):
    """Response schema for cache clear operation."""

    success: bool = Field(..., description="Whether operation succeeded")
    entries_cleared: int = Field(..., description="Number of entries cleared")
    message: str = Field(..., description="Result message")


class CacheWarmRequest(BaseModel):
    """Request schema for warming cache."""

    entries: List[Dict[str, Any]] = Field(..., description="Entries to cache")


class CacheWarmResponse(BaseModel):
    """Response schema for cache warm operation."""

    success: bool = Field(..., description="Whether operation succeeded")
    entries_cached: int = Field(..., description="Number of entries cached")
    total_entries: int = Field(..., description="Total entries provided")


class CacheConfigResponse(BaseModel):
    """Response schema for cache configuration."""

    enabled: bool = Field(..., description="Whether cache is enabled")
    default_ttl_seconds: int = Field(..., description="Default TTL")
    key_prefix: str = Field(..., description="Cache key prefix")
