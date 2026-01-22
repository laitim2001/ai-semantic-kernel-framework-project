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
from src.integrations.ag_ui.features.human_in_loop import (
    HITLHandler,
    ToolCallInfo,
    get_hitl_handler,
    get_approval_storage,
    ApprovalStatus,
)
from src.integrations.claude_sdk.hooks.approval import ApprovalHook
from src.integrations.claude_sdk.types import ToolCallContext

logger = logging.getLogger(__name__)

# Global instances for connection pooling
_redis_client: Optional[aioredis.Redis] = None
_hybrid_bridge: Optional[HybridEventBridge] = None
_claude_client: Optional[Any] = None  # ClaudeSDKClient instance


async def _create_approval_callback(context: ToolCallContext) -> bool:
    """
    Approval callback for ApprovalHook.

    This callback is invoked when a tool call requires human approval.
    It creates an approval request and waits for user response.

    Args:
        context: ToolCallContext with tool_name and args

    Returns:
        True if approved, False if rejected

    Note:
        This callback is ONLY called for tools in DEFAULT_APPROVAL_TOOLS
        (Write, Edit, MultiEdit, Bash). Since the ApprovalHook has already
        decided these tools need approval, we ALWAYS require approval here
        regardless of the risk score. The risk assessment is used to inform
        the user about the risk level, not to override the approval requirement.
    """
    try:
        hitl = get_hitl_handler()

        # Create ToolCallInfo
        tool_call_info = ToolCallInfo(
            id=f"tc-{context.tool_name}-{os.urandom(4).hex()}",
            name=context.tool_name,
            arguments=context.args or {},
        )

        # Perform risk assessment for informational purposes
        # Note: We ALWAYS require approval since ApprovalHook already decided
        # this tool needs it. Risk assessment informs the user, not the decision.
        _needs_approval, assessment = await hitl.check_approval_needed(
            tool_call=tool_call_info,
            session_id=context.session_id,
            environment="development",
        )

        # ALWAYS require approval for tools that reach this callback
        # (Write, Edit, MultiEdit, Bash are already filtered by ApprovalHook)
        logger.info(
            f"[HITL] Tool {context.tool_name} requires approval "
            f"(risk_level={assessment.overall_level.value if assessment else 'unknown'})"
        )

        # Create a default HIGH risk assessment if none available
        if assessment is None:
            from src.integrations.hybrid.risk.models import RiskAssessment, RiskLevel
            assessment = RiskAssessment(
                overall_level=RiskLevel.HIGH,
                overall_score=0.8,
                factors=[],
                requires_approval=True,
                approval_reason=f"Tool {context.tool_name} requires approval",
            )

        # Create approval event (stores in ApprovalStorage)
        run_id = f"run-approval-{os.urandom(4).hex()}"
        event = await hitl.create_approval_event(
            tool_call=tool_call_info,
            assessment=assessment,
            run_id=run_id,
            session_id=context.session_id,
            timeout_seconds=120,  # 2 minutes for interactive approval
        )

        approval_id = event.payload["approval_id"]
        logger.info(
            f"[HITL] Approval required for {context.tool_name}: {approval_id}"
        )

        # Wait for approval (polls ApprovalStorage)
        try:
            request = await hitl.wait_for_approval(
                approval_id=approval_id,
                poll_interval_seconds=0.5,
            )

            approved = request.status == ApprovalStatus.APPROVED

            if approved:
                logger.info(f"[HITL] Tool {context.tool_name} approved: {approval_id}")
            else:
                logger.info(
                    f"[HITL] Tool {context.tool_name} rejected: {approval_id}, "
                    f"status={request.status.value}"
                )

            return approved

        except Exception as wait_error:
            logger.warning(f"[HITL] Approval wait failed: {wait_error}")
            return False

    except Exception as e:
        logger.error(f"[HITL] Approval callback error: {e}", exc_info=True)
        # Fail-safe: reject on error
        return False


def _try_create_claude_client():
    """
    Try to create ClaudeSDKClient for Claude API calls.

    Returns None if API key is not configured or dependencies unavailable.

    Sprint 59: Now includes ApprovalHook for Human-in-the-Loop (HITL) support.
    """
    try:
        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not configured, Claude SDK disabled")
            return None

        from src.integrations.claude_sdk.client import ClaudeSDKClient

        # Create ApprovalHook for HITL
        approval_hook = ApprovalHook(
            approval_callback=_create_approval_callback,
            auto_approve_reads=True,  # Auto-approve Read, Glob, Grep
            timeout=120.0,  # 2 minutes for interactive approval
        )

        client = ClaudeSDKClient(
            api_key=api_key,
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            timeout=300,
            hooks=[approval_hook],  # Enable HITL
        )
        logger.info("ClaudeSDKClient created successfully with ApprovalHook")
        return client

    except ImportError as e:
        logger.warning(f"Could not import ClaudeSDKClient: {e}")
        return None
    except Exception as e:
        logger.warning(f"Could not create ClaudeSDKClient: {e}")
        return None


async def _execute_multimodal(
    client,
    multimodal_content: List[Dict[str, Any]],
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    S75-5: Execute multimodal content (images, PDFs, text) via Claude API.

    This function directly calls the Anthropic API with proper multimodal
    content format for images and PDFs.

    Args:
        client: ClaudeSDKClient instance
        multimodal_content: List of content blocks (text, image, document)
        max_tokens: Maximum response tokens

    Returns:
        Dict with success, content, and tokens_used
    """
    try:
        # Access the underlying Anthropic client
        anthropic_client = client._client

        # Log content types for debugging
        content_types = [c.get("type") for c in multimodal_content]
        logger.info(f"[S75-5] Multimodal content types: {content_types}")

        # Call Claude API with multimodal content
        response = await anthropic_client.messages.create(
            model=client.config.model,
            max_tokens=max_tokens or 4096,
            messages=[{
                "role": "user",
                "content": multimodal_content,
            }],
        )

        # Extract response content
        final_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_content += block.text

        logger.info(f"[S75-5] Multimodal response received: {len(final_content)} chars")

        return {
            "success": True,
            "content": final_content,
            "tool_calls": [],
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[S75-5] Multimodal execution error: {error_msg}", exc_info=True)
        return {
            "success": False,
            "content": f"Multimodal API error: {error_msg}",
            "error": error_msg,
        }


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
        multimodal_content: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute prompt via Claude SDK with tool support.

        S75-5: Supports multimodal content for images, PDFs, and text files.

        Args:
            prompt: User prompt text
            history: Conversation history
            tools: Available tools
            max_tokens: Maximum response tokens
            multimodal_content: Claude API multimodal content blocks (S75-5)
        """
        try:
            # S75-5: Check if we have multimodal content (images, PDFs)
            if multimodal_content and len(multimodal_content) > 1:
                # Use direct Anthropic API for multimodal content
                logger.info(f"[S75-5] Using multimodal API with {len(multimodal_content)} content blocks")
                return await _execute_multimodal(
                    client, multimodal_content, max_tokens
                )

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
