# =============================================================================
# IPA Platform - AG-UI API Dependencies
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
#
# Dependency injection providers for AG-UI API endpoints.
# Provides HybridEventBridge and related dependencies.
#
# Dependencies:
#   - HybridEventBridge (src.integrations.ag_ui.bridge)
#   - HybridOrchestratorV2 (src.integrations.hybrid.orchestrator_v2)
# =============================================================================

import logging
from typing import Optional

import redis.asyncio as aioredis
from fastapi import Depends

from src.core.config import get_settings
from src.integrations.ag_ui.bridge import (
    HybridEventBridge,
    BridgeConfig,
)

logger = logging.getLogger(__name__)

# Global instances for connection pooling
_redis_client: Optional[aioredis.Redis] = None
_hybrid_bridge: Optional[HybridEventBridge] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Get Redis client instance.

    Uses connection pooling for efficiency.

    Returns:
        Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password if settings.redis_password else None,
            decode_responses=True,
        )
        logger.info("AG-UI Redis client initialized")
    return _redis_client


async def get_hybrid_bridge(
    redis_client: aioredis.Redis = Depends(get_redis_client),
) -> HybridEventBridge:
    """
    Get HybridEventBridge instance.

    Creates or retrieves a configured HybridEventBridge for AG-UI
    protocol event streaming.

    Args:
        redis_client: Redis client for caching/session management

    Returns:
        Configured HybridEventBridge instance
    """
    global _hybrid_bridge

    if _hybrid_bridge is None:
        # Create bridge with default configuration
        config = BridgeConfig(
            chunk_size=100,
            include_metadata=True,
            emit_state_events=True,
            emit_custom_events=True,
        )

        _hybrid_bridge = HybridEventBridge(config=config)
        logger.info("AG-UI HybridEventBridge initialized")

    return _hybrid_bridge


async def get_current_thread_id() -> Optional[str]:
    """
    Get current thread ID from request context.

    This is a placeholder for session/auth middleware integration.

    Returns:
        Thread ID or None if not in thread context
    """
    return None


async def cleanup_dependencies() -> None:
    """
    Cleanup global dependencies.

    Called on application shutdown.
    """
    global _redis_client, _hybrid_bridge

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("AG-UI Redis client closed")

    _hybrid_bridge = None
    logger.info("AG-UI dependencies cleaned up")
