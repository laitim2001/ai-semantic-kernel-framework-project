# =============================================================================
# IPA Platform - Hybrid API Dependencies
# =============================================================================
# Phase 13 Hotfix: LLM 連接修復
#
# 提供 ClaudeSDKClient 和相關依賴的懶加載和生命週期管理。
# 當 ANTHROPIC_API_KEY 未配置時，自動 fallback 到模擬模式。
#
# Dependencies:
#   - ClaudeSDKClient (src.integrations.claude_sdk.client)
# =============================================================================

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Singleton instances
_claude_client: Optional[Any] = None
_claude_executor: Optional[Callable] = None


async def get_claude_client():
    """
    Get or create ClaudeSDKClient singleton.

    Returns None if ANTHROPIC_API_KEY not configured (fallback to simulation).
    """
    global _claude_client
    if _claude_client is None:
        try:
            from src.integrations.claude_sdk.client import ClaudeSDKClient
            _claude_client = ClaudeSDKClient()
            logger.info("ClaudeSDKClient initialized successfully")
        except Exception as e:
            logger.warning(f"ClaudeSDKClient not available: {e} (will use simulation mode)")
            _claude_client = False  # Sentinel to avoid repeated attempts

    return _claude_client if _claude_client else None


def get_claude_executor() -> Optional[Callable]:
    """
    Get Claude executor function for HybridOrchestratorV2.

    Returns an async function that:
    - Calls Claude API via ClaudeSDKClient
    - Returns dict compatible with HybridResultV2

    Returns:
        Async callable that executes prompts via Claude SDK,
        or None if SDK not available.
    """
    global _claude_executor

    if _claude_executor is not None:
        return _claude_executor

    async def claude_executor(
        prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute prompt via Claude SDK.

        Args:
            prompt: User prompt to execute
            history: Optional conversation history
            tools: Optional list of available tools
            max_tokens: Maximum tokens for response
            **kwargs: Additional arguments

        Returns:
            Dict with success, content, error, tokens_used, metadata
        """
        client = await get_claude_client()
        if not client:
            # Fallback to simulation if client not available
            logger.debug(f"Claude executor using SIMULATION mode for prompt: {prompt[:50]}...")
            return {
                "success": True,
                "content": f"[SIMULATION] {prompt[:100]}...",
                "tokens_used": 0,
                "metadata": {"simulation": True},
            }

        try:
            # Call Claude API via SDK
            result = await client.query(
                prompt=prompt,
                max_tokens=max_tokens or 4096,
            )

            logger.debug(
                f"Claude executor completed: status={result.status}, "
                f"tokens={result.tokens_used}, duration={result.duration:.2f}s"
            )

            return {
                "success": result.status == "success",
                "content": result.content or "",
                "error": result.error,
                "tokens_used": result.tokens_used or 0,
                "metadata": {
                    "status": result.status,
                    "duration": result.duration,
                    "tool_calls_count": len(result.tool_calls) if result.tool_calls else 0,
                },
            }
        except Exception as e:
            logger.error(f"Claude executor error: {e}", exc_info=True)
            return {
                "success": False,
                "content": "",
                "error": str(e),
                "tokens_used": 0,
            }

    _claude_executor = claude_executor
    return _claude_executor


async def cleanup_hybrid_dependencies() -> None:
    """
    Cleanup hybrid dependencies on shutdown.

    Should be called during application shutdown to clean up resources.
    """
    global _claude_client, _claude_executor
    _claude_client = None
    _claude_executor = None
    logger.info("Hybrid dependencies cleaned up")


def reset_dependencies() -> None:
    """
    Reset dependencies for testing purposes.

    This allows tests to reset the singleton state between test runs.
    """
    global _claude_client, _claude_executor
    _claude_client = None
    _claude_executor = None
