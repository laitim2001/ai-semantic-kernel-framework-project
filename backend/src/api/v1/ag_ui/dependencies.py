# =============================================================================
# IPA Platform - AG-UI API Dependencies
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
# Sprint 66: S66-1 - Fix tool parameter passing to Claude SDK
# Sprint 68: S68-3 - User identification for sandbox isolation
#
# Dependency injection providers for AG-UI API endpoints.
# Provides HybridEventBridge and related dependencies.
#
# Supports simulation mode for UAT testing when orchestrator is unavailable.
# Now supports real Claude API calls via ClaudeSDKClient with tool execution.
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
from fastapi import Depends, Header, HTTPException, status

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
            model="claude-haiku-4-5-20251001",
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
        """Execute prompt via Claude SDK with tool support."""
        try:
            # Build messages from history if available
            messages = []
            if history:
                for msg in history[-10:]:  # Last 10 messages for context
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    })

            # Extract tool names from tool definitions
            # Claude SDK expects tool names as List[str], not full definitions
            tool_names: List[str] = []
            if tools:
                for tool in tools:
                    tool_name = tool.get("name") if isinstance(tool, dict) else str(tool)
                    if tool_name:
                        tool_names.append(tool_name)
                logger.info(f"Claude executor using tools: {tool_names}")

            # Execute query with tools
            # S67-BF-1: Increase timeout to 180s to handle Rate Limit retries
            result = await client.query(
                prompt=prompt,
                tools=tool_names if tool_names else None,
                max_tokens=max_tokens or 4096,
                timeout=180,  # 3 minutes to allow for 429 retry backoff
            )

            # Extract tool calls from result
            tool_calls_data = []
            if hasattr(result, "tool_calls") and result.tool_calls:
                for tc in result.tool_calls:
                    tool_calls_data.append({
                        "id": getattr(tc, "id", None),
                        "name": getattr(tc, "name", None),
                        "args": getattr(tc, "args", {}),
                    })

            return {
                "success": True,
                "content": result.content if hasattr(result, "content") else str(result),
                "tool_calls": tool_calls_data,
                "tokens_used": getattr(result, "tokens_used", 0),
            }

        except Exception as e:
            # S67-BF-1: Enhanced error logging for debugging
            error_type = type(e).__name__
            error_msg = str(e)

            # Check for common error types
            if "429" in error_msg or "rate" in error_msg.lower():
                logger.warning(f"Claude API Rate Limited: {error_msg}")
            elif "timeout" in error_msg.lower():
                logger.warning(f"Claude API Timeout (180s): {error_msg}")
            else:
                logger.error(f"Claude executor error ({error_type}): {error_msg}", exc_info=True)

            return {
                "success": False,
                "content": f"Claude API error: {error_msg}",
                "error": error_msg,
                "error_type": error_type,
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


# =============================================================================
# Sprint 68: User Identification for Sandbox Isolation
# Sprint 72: S72-1 - Integrated with auth system (get_current_user_optional)
# =============================================================================

from src.api.v1.dependencies import get_current_user_optional
from src.infrastructure.database.models.user import User


async def get_user_id_or_guest(
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_guest_id: Optional[str] = Header(None),
) -> str:
    """Get user ID from auth or guest header.

    Sprint 72: Now integrates with authentication system.
    Prioritizes authenticated users over guest IDs.

    Args:
        current_user: Authenticated user from JWT token (optional)
        x_guest_id: Guest user ID from header (for unauthenticated users)

    Returns:
        User identifier string (either user UUID or guest-xxx format)

    Raises:
        HTTPException: If no user identification is provided
    """
    if current_user:
        return str(current_user.id)
    if x_guest_id:
        return x_guest_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User identification required. Login or provide X-Guest-Id header.",
    )


async def get_user_id(
    x_user_id: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None),
) -> str:
    """Get user ID from request headers (legacy support).

    Supports both authenticated users (X-User-Id) and guest users (X-Guest-Id).
    Phase 17 uses guest IDs; Phase 18 added authenticated user support.

    Note: Prefer get_user_id_or_guest which integrates with auth system.

    Args:
        x_user_id: Authenticated user ID (from auth middleware, Phase 18)
        x_guest_id: Guest user ID (from frontend, Phase 17)

    Returns:
        User identifier string

    Raises:
        HTTPException: If no user identification is provided
    """
    if x_user_id:
        return x_user_id
    if x_guest_id:
        return x_guest_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User identification required. Provide X-User-Id or X-Guest-Id header.",
    )


async def get_user_id_optional(
    x_user_id: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None),
) -> Optional[str]:
    """Get user ID from request headers (optional).

    Same as get_user_id but returns None instead of raising exception
    if no user identification is provided.

    Args:
        x_user_id: Authenticated user ID
        x_guest_id: Guest user ID

    Returns:
        User identifier string or None
    """
    if x_user_id:
        return x_user_id
    if x_guest_id:
        return x_guest_id
    return None


async def get_user_and_guest_id(
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_guest_id: Optional[str] = Header(None),
) -> tuple[Optional[str], Optional[str]]:
    """Get both user ID and guest ID for migration support.

    Sprint 72: Returns both authenticated user ID and guest ID.
    Used by session service to properly associate sessions.

    Args:
        current_user: Authenticated user from JWT token (optional)
        x_guest_id: Guest user ID from header (for unauthenticated users)

    Returns:
        Tuple of (user_id, guest_id) - both can be None or set
    """
    user_id = str(current_user.id) if current_user else None
    guest_id = x_guest_id

    return (user_id, guest_id)
