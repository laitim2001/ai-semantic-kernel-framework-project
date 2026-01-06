# =============================================================================
# IPA Platform - AG-UI API Dependencies
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
#
# Dependency injection providers for AG-UI API endpoints.
# Provides HybridEventBridge and related dependencies.
#
# Supports simulation mode for UAT testing when orchestrator is unavailable.
# Now supports real Claude API calls via ClaudeSDKClient.
#
# Dependencies:
#   - HybridEventBridge (src.integrations.ag_ui.bridge)
#   - HybridOrchestratorV2 (src.integrations.hybrid.orchestrator_v2)
#   - ClaudeSDKClient (src.integrations.claude_sdk.client)
# =============================================================================

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import Depends

# Load .env file from backend directory
_backend_dir = Path(__file__).parent.parent.parent.parent.parent
_env_file = _backend_dir / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

from src.core.config import get_settings
from src.integrations.ag_ui.bridge import (
    HybridEventBridge,
    BridgeConfig,
)

logger = logging.getLogger(__name__)

# Global instances for connection pooling
_redis_client: Optional[aioredis.Redis] = None
_hybrid_bridge: Optional[HybridEventBridge] = None
_claude_client: Optional[Any] = None  # ClaudeSDKClient instance


def _try_create_claude_client():
    """
    Try to create ClaudeSDKClient for Claude API calls.

    Returns None if API key is not configured or dependencies unavailable.
    """
    try:
        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not configured, Claude SDK disabled")
            return None

        from src.integrations.claude_sdk.client import ClaudeSDKClient

        client = ClaudeSDKClient(
            api_key=api_key,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            timeout=300,
        )
        logger.info("ClaudeSDKClient created successfully")
        return client

    except ImportError as e:
        logger.warning(f"Could not import ClaudeSDKClient: {e}")
        return None
    except Exception as e:
        logger.warning(f"Could not create ClaudeSDKClient: {e}")
        return None


def _create_claude_executor(client):
    """
    Create a Claude executor function for HybridOrchestratorV2.

    Args:
        client: ClaudeSDKClient instance

    Returns:
        Async callable that executes prompts via Claude API
    """
    async def claude_executor(
        prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute prompt via Claude SDK."""
        try:
            # Build messages from history if available
            messages = []
            if history:
                for msg in history[-10:]:  # Last 10 messages for context
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    })

            # Execute query
            result = await client.query(
                prompt=prompt,
                max_tokens=max_tokens or 4096,
            )

            return {
                "success": True,
                "content": result.content if hasattr(result, "content") else str(result),
                "tool_calls": getattr(result, "tool_calls", []),
                "tokens_used": getattr(result, "tokens_used", 0),
            }

        except Exception as e:
            logger.error(f"Claude executor error: {e}")
            return {
                "success": False,
                "content": f"Claude API error: {str(e)}",
                "error": str(e),
            }

    return claude_executor


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


def _try_create_orchestrator():
    """
    Try to create HybridOrchestratorV2 with Claude executor.

    Returns None if dependencies are not available.
    The orchestrator will use Claude API for real LLM calls when ANTHROPIC_API_KEY is set.
    """
    global _claude_client

    try:
        from src.integrations.hybrid.orchestrator_v2 import (
            HybridOrchestratorV2,
            OrchestratorConfig,
            OrchestratorMode,
        )

        # Check if we're in simulation mode (for UAT testing)
        if os.getenv("AG_UI_SIMULATION_MODE", "").lower() == "true":
            logger.info("AG-UI running in simulation mode (orchestrator disabled)")
            return None

        # Try to create Claude client and executor
        claude_executor = None
        if not _claude_client:
            _claude_client = _try_create_claude_client()

        if _claude_client:
            claude_executor = _create_claude_executor(_claude_client)
            logger.info("Claude executor created for AG-UI orchestrator")
        else:
            logger.warning("Claude executor not available, will use simulation responses")

        # Try to create orchestrator with minimal config
        config = OrchestratorConfig(
            mode=OrchestratorMode.V2_MINIMAL,
            primary_framework="claude_sdk",
            auto_switch=False,
            enable_metrics=False,
        )

        orchestrator = HybridOrchestratorV2(
            config=config,
            claude_executor=claude_executor,
        )
        logger.info(
            f"HybridOrchestratorV2 created for AG-UI bridge "
            f"(claude_executor={'enabled' if claude_executor else 'disabled'})"
        )
        return orchestrator

    except ImportError as e:
        logger.warning(f"Could not import HybridOrchestratorV2: {e}")
        return None
    except Exception as e:
        logger.warning(f"Could not create HybridOrchestratorV2: {e}")
        return None


async def get_hybrid_bridge(
    redis_client: aioredis.Redis = Depends(get_redis_client),
) -> HybridEventBridge:
    """
    Get HybridEventBridge instance.

    Creates or retrieves a configured HybridEventBridge for AG-UI
    protocol event streaming.

    If HybridOrchestratorV2 cannot be created (missing dependencies or config),
    the bridge operates in "simulation mode" - API routes will work but
    return simulated responses.

    Set AG_UI_SIMULATION_MODE=true to force simulation mode for testing.

    Args:
        redis_client: Redis client for caching/session management

    Returns:
        Configured HybridEventBridge instance
    """
    global _hybrid_bridge

    if _hybrid_bridge is None:
        # Create bridge configuration
        config = BridgeConfig(
            chunk_size=100,
            include_metadata=True,
            emit_state_events=True,
            emit_custom_events=True,
        )

        # Try to create orchestrator
        orchestrator = _try_create_orchestrator()

        _hybrid_bridge = HybridEventBridge(
            orchestrator=orchestrator,
            config=config,
        )

        if orchestrator:
            logger.info("AG-UI HybridEventBridge initialized with orchestrator")
        else:
            logger.info("AG-UI HybridEventBridge initialized in simulation mode")

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
    global _redis_client, _hybrid_bridge, _claude_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("AG-UI Redis client closed")

    _hybrid_bridge = None
    _claude_client = None
    logger.info("AG-UI dependencies cleaned up")


def reset_hybrid_bridge() -> Dict[str, Any]:
    """
    Reset HybridEventBridge and related global state.

    Forces re-creation of orchestrator with fresh Claude executor.
    Useful when environment variables change or for debugging.

    Returns:
        Dict with reset status and diagnostics
    """
    global _hybrid_bridge, _claude_client

    # Clear cached instances
    old_bridge = _hybrid_bridge
    old_client = _claude_client

    _hybrid_bridge = None
    _claude_client = None

    # Check API key status
    api_key = os.getenv("ANTHROPIC_API_KEY")
    api_key_status = f"SET (starts with {api_key[:15]}...)" if api_key else "NOT SET"

    # Try to create new Claude client
    new_client = _try_create_claude_client()

    result = {
        "reset": True,
        "api_key_status": api_key_status,
        "claude_client_created": new_client is not None,
        "old_bridge_existed": old_bridge is not None,
        "old_client_existed": old_client is not None,
    }

    if new_client:
        _claude_client = new_client
        result["message"] = "Reset complete. Claude SDK ready for next request."
    else:
        result["message"] = "Reset complete. Claude SDK not available (check ANTHROPIC_API_KEY)."

    logger.info(f"HybridEventBridge reset: {result}")
    return result


def get_bridge_status() -> Dict[str, Any]:
    """
    Get current status of HybridEventBridge and related components.

    Returns:
        Dict with current status information
    """
    global _hybrid_bridge, _claude_client

    api_key = os.getenv("ANTHROPIC_API_KEY")

    status = {
        "api_key_configured": bool(api_key),
        "api_key_preview": f"{api_key[:15]}..." if api_key else None,
        "claude_client_initialized": _claude_client is not None,
        "bridge_initialized": _hybrid_bridge is not None,
        "orchestrator_configured": False,
        "claude_executor_enabled": False,
    }

    if _hybrid_bridge:
        orchestrator = _hybrid_bridge.orchestrator
        status["orchestrator_configured"] = orchestrator is not None
        if orchestrator:
            status["claude_executor_enabled"] = hasattr(orchestrator, "_claude_executor") and orchestrator._claude_executor is not None

    return status
