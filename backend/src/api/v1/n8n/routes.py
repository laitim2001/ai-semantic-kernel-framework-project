"""n8n Webhook API Routes.

REST API endpoints for n8n → IPA integration (Mode 2).
Provides webhook entry points for n8n workflows to trigger IPA processing,
plus connection management endpoints.

Endpoints:
    POST    /api/v1/n8n/webhook                 - General n8n webhook entry
    POST    /api/v1/n8n/webhook/{workflow_id}    - Workflow-specific webhook
    GET     /api/v1/n8n/status                   - Connection status check
    GET     /api/v1/n8n/config                   - Get n8n configuration
    PUT     /api/v1/n8n/config                   - Update n8n configuration

Security:
    - HMAC-SHA256 signature verification on webhook endpoints
    - JWT authentication on config endpoints (via protected_router)
"""

import hashlib
import hmac
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from .schemas import (
    N8nConfigResponse,
    N8nConfigUpdate,
    N8nConnectionStatus,
    N8nStatusResponse,
    N8nWebhookPayload,
    N8nWebhookResponse,
    WebhookVerificationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/n8n", tags=["n8n Integration"])

# ---------------------------------------------------------------------------
# Module-level state (managed per-process)
# ---------------------------------------------------------------------------

# Runtime config (initialized from environment, updatable via API)
_n8n_config: Dict[str, Any] = {
    "base_url": os.environ.get("N8N_BASE_URL", "http://localhost:5678"),
    "timeout": int(os.environ.get("N8N_TIMEOUT", "30")),
    "max_retries": int(os.environ.get("N8N_MAX_RETRIES", "3")),
}

# HMAC secret for webhook signature verification
_WEBHOOK_HMAC_SECRET = os.environ.get("N8N_WEBHOOK_HMAC_SECRET", "")


# ---------------------------------------------------------------------------
# HMAC Signature Verification
# ---------------------------------------------------------------------------


def _verify_hmac_signature(
    payload_bytes: bytes,
    signature: Optional[str],
) -> bool:
    """Verify HMAC-SHA256 signature of webhook payload.

    Args:
        payload_bytes: Raw request body bytes
        signature: X-N8N-Signature header value

    Returns:
        True if signature is valid or HMAC is not configured
    """
    # If HMAC secret is not configured, skip verification (dev mode)
    if not _WEBHOOK_HMAC_SECRET:
        logger.debug("HMAC verification skipped: N8N_WEBHOOK_HMAC_SECRET not configured")
        return True

    if not signature:
        logger.warning("HMAC verification failed: missing X-N8N-Signature header")
        return False

    # Compute expected signature
    expected = hmac.new(
        _WEBHOOK_HMAC_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(f"sha256={expected}", signature)


# ---------------------------------------------------------------------------
# Webhook processing logic
# ---------------------------------------------------------------------------


async def _process_webhook(payload: N8nWebhookPayload) -> Dict[str, Any]:
    """Process an incoming n8n webhook payload.

    Routes the payload to the appropriate IPA handler based on the action type.

    Args:
        payload: Validated webhook payload

    Returns:
        Processing result dictionary

    Note:
        This is the integration point where n8n connects to IPA's
        orchestration layer. Current implementation provides routing
        scaffolding; actual handler delegation will be connected when
        the orchestration module supports external triggers (Sprint 126).
    """
    action = payload.action
    data = payload.data

    logger.info(
        f"Processing n8n webhook: action={action}, "
        f"workflow_id={payload.workflow_id}, "
        f"execution_id={payload.execution_id}, "
        f"data_keys={list(data.keys())}"
    )

    # Route to appropriate handler based on action
    if action == "analyze":
        return await _handle_analyze(payload)
    elif action == "classify":
        return await _handle_classify(payload)
    elif action == "execute":
        return await _handle_execute(payload)
    elif action == "query":
        return await _handle_query(payload)
    elif action == "notify":
        return await _handle_notify(payload)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {action}",
        )


async def _handle_analyze(payload: N8nWebhookPayload) -> Dict[str, Any]:
    """Handle 'analyze' action — AI analysis of input data.

    Delegates to IPA's orchestration layer for intent analysis.
    """
    return {
        "action": "analyze",
        "analysis": {
            "intent": "pending_classification",
            "confidence": 0.0,
            "source_workflow": payload.workflow_id,
            "data_keys": list(payload.data.keys()),
        },
        "message": (
            "Analysis request received. "
            "Full orchestration integration available in Sprint 126."
        ),
    }


async def _handle_classify(payload: N8nWebhookPayload) -> Dict[str, Any]:
    """Handle 'classify' action — classify input into intent categories."""
    return {
        "action": "classify",
        "classification": {
            "category": "pending",
            "confidence": 0.0,
            "source_workflow": payload.workflow_id,
        },
        "message": (
            "Classification request received. "
            "Three-tier routing integration available in Sprint 126."
        ),
    }


async def _handle_execute(payload: N8nWebhookPayload) -> Dict[str, Any]:
    """Handle 'execute' action — execute an IPA workflow or action."""
    return {
        "action": "execute",
        "execution": {
            "status": "accepted",
            "source_workflow": payload.workflow_id,
            "data_keys": list(payload.data.keys()),
        },
        "message": (
            "Execution request accepted. "
            "Full execution pipeline integration available in Sprint 126."
        ),
    }


async def _handle_query(payload: N8nWebhookPayload) -> Dict[str, Any]:
    """Handle 'query' action — query IPA for information."""
    return {
        "action": "query",
        "query_result": {
            "status": "received",
            "source_workflow": payload.workflow_id,
            "query_data": payload.data,
        },
        "message": "Query request received.",
    }


async def _handle_notify(payload: N8nWebhookPayload) -> Dict[str, Any]:
    """Handle 'notify' action — receive notification from n8n."""
    logger.info(
        f"Notification from n8n workflow {payload.workflow_id}: "
        f"{payload.data.get('message', 'No message')}"
    )
    return {
        "action": "notify",
        "acknowledged": True,
        "source_workflow": payload.workflow_id,
    }


# ---------------------------------------------------------------------------
# Webhook Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/webhook",
    response_model=N8nWebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="General n8n webhook entry",
    description=(
        "Receives webhook calls from n8n workflows. "
        "Validates HMAC signature (if configured), parses payload, "
        "and routes to the appropriate IPA handler."
    ),
)
async def n8n_webhook(
    request: Request,
    payload: N8nWebhookPayload,
    x_n8n_signature: Optional[str] = Header(None, alias="X-N8N-Signature"),
) -> N8nWebhookResponse:
    """Handle general n8n webhook."""
    # Verify HMAC signature
    body = await request.body()
    if not _verify_hmac_signature(body, x_n8n_signature):
        logger.warning(
            f"Webhook HMAC verification failed for workflow {payload.workflow_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    request_id = str(uuid.uuid4())

    try:
        result = await _process_webhook(payload)

        return N8nWebhookResponse(
            success=True,
            request_id=request_id,
            action=payload.action.value,
            result=result,
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        return N8nWebhookResponse(
            success=False,
            request_id=request_id,
            action=payload.action.value,
            error=str(e),
            timestamp=datetime.utcnow(),
        )


@router.post(
    "/webhook/{workflow_id}",
    response_model=N8nWebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Workflow-specific n8n webhook",
    description=(
        "Receives webhook calls for a specific n8n workflow. "
        "The workflow_id in the URL is used to route and validate."
    ),
)
async def n8n_webhook_by_workflow(
    request: Request,
    workflow_id: str,
    payload: N8nWebhookPayload,
    x_n8n_signature: Optional[str] = Header(None, alias="X-N8N-Signature"),
) -> N8nWebhookResponse:
    """Handle workflow-specific n8n webhook."""
    # Verify HMAC signature
    body = await request.body()
    if not _verify_hmac_signature(body, x_n8n_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Override workflow_id from URL path
    payload_dict = payload.model_dump()
    payload_dict["workflow_id"] = workflow_id
    updated_payload = N8nWebhookPayload(**payload_dict)

    request_id = str(uuid.uuid4())

    try:
        result = await _process_webhook(updated_payload)

        return N8nWebhookResponse(
            success=True,
            request_id=request_id,
            action=payload.action.value,
            result=result,
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        return N8nWebhookResponse(
            success=False,
            request_id=request_id,
            action=payload.action.value,
            error=str(e),
            timestamp=datetime.utcnow(),
        )


# ---------------------------------------------------------------------------
# Connection Management Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=N8nStatusResponse,
    summary="n8n connection status",
    description="Check the current connection status to the n8n instance.",
)
async def get_n8n_status() -> N8nStatusResponse:
    """Get n8n connection status."""
    from src.integrations.mcp.servers.n8n.client import N8nApiClient, N8nConfig

    base_url = _n8n_config["base_url"]
    api_key = os.environ.get("N8N_API_KEY", "")

    if not api_key:
        return N8nStatusResponse(
            status=N8nConnectionStatus.DISCONNECTED,
            base_url=base_url,
            healthy=False,
            last_check=datetime.utcnow(),
            error="N8N_API_KEY not configured",
        )

    try:
        config = N8nConfig(
            base_url=base_url,
            api_key=api_key,
            timeout=_n8n_config["timeout"],
            max_retries=1,  # Quick check, only 1 attempt
        )
        async with N8nApiClient(config) as client:
            healthy = await client.health_check()

            return N8nStatusResponse(
                status=N8nConnectionStatus.CONNECTED if healthy else N8nConnectionStatus.ERROR,
                base_url=base_url,
                healthy=healthy,
                last_check=datetime.utcnow(),
                tools_count=6,  # 6 registered MCP tools
            )

    except Exception as e:
        logger.error(f"n8n status check failed: {e}")
        return N8nStatusResponse(
            status=N8nConnectionStatus.ERROR,
            base_url=base_url,
            healthy=False,
            last_check=datetime.utcnow(),
            error=str(e),
        )


@router.get(
    "/config",
    response_model=N8nConfigResponse,
    summary="Get n8n configuration",
    description="Get current n8n connection configuration (secrets masked).",
)
async def get_n8n_config() -> N8nConfigResponse:
    """Get n8n configuration (safe, no secrets)."""
    return N8nConfigResponse(
        base_url=_n8n_config["base_url"],
        timeout=_n8n_config["timeout"],
        max_retries=_n8n_config["max_retries"],
        api_key_configured=bool(os.environ.get("N8N_API_KEY", "")),
        webhook_hmac_configured=bool(_WEBHOOK_HMAC_SECRET),
    )


@router.put(
    "/config",
    response_model=N8nConfigResponse,
    summary="Update n8n configuration",
    description=(
        "Update non-secret n8n configuration settings. "
        "API key and HMAC secret must be set via environment variables."
    ),
)
async def update_n8n_config(update: N8nConfigUpdate) -> N8nConfigResponse:
    """Update n8n configuration (non-secret settings only)."""
    if update.base_url is not None:
        _n8n_config["base_url"] = update.base_url
        logger.info(f"n8n base_url updated to: {update.base_url}")

    if update.timeout is not None:
        _n8n_config["timeout"] = update.timeout
        logger.info(f"n8n timeout updated to: {update.timeout}")

    if update.max_retries is not None:
        _n8n_config["max_retries"] = update.max_retries
        logger.info(f"n8n max_retries updated to: {update.max_retries}")

    return N8nConfigResponse(
        base_url=_n8n_config["base_url"],
        timeout=_n8n_config["timeout"],
        max_retries=_n8n_config["max_retries"],
        api_key_configured=bool(os.environ.get("N8N_API_KEY", "")),
        webhook_hmac_configured=bool(_WEBHOOK_HMAC_SECRET),
    )
