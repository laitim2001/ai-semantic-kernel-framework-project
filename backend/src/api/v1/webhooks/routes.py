"""
Webhook API Routes

Provides REST API endpoints for webhook operations.
Sprint 2 - Story S2-1 (Inbound) & S2-2 (Outbound)

Note: Route order matters! Fixed paths must come before dynamic paths.
      e.g., /n8n/trigger must be defined before /n8n/{workflow_id}

Endpoints:
- GET  /api/v1/webhooks/health                - Webhook health check
- GET  /api/v1/webhooks/n8n/health            - Check n8n connection health (S2-2)
- GET  /api/v1/webhooks/n8n/workflows         - List n8n workflows (S2-2)
- POST /api/v1/webhooks/n8n/trigger           - Trigger n8n workflow (S2-2)
- POST /api/v1/webhooks/n8n/test              - Test n8n webhook endpoint (S2-1)
- POST /api/v1/webhooks/n8n/trigger/{id}      - Trigger n8n workflow by path (S2-2)
- POST /api/v1/webhooks/n8n/{workflow_id}     - Receive n8n webhook (S2-1)
- POST /api/v1/webhooks/generic/{source}      - Generic webhook endpoint
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.webhooks.n8n_service import N8nWebhookService
from src.domain.webhooks.n8n_client import N8nClient, get_n8n_client
from src.domain.webhooks.schemas import (
    WebhookResponse,
    WebhookTestResponse,
    N8nTriggerRequest,
    N8nTriggerResponse,
    N8nHealthResponse,
    N8nWorkflowListResponse,
)
from src.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ============================================
# Dependencies
# ============================================

def get_n8n_service(session: AsyncSession = Depends(get_session)) -> N8nWebhookService:
    """Get n8n webhook service dependency."""
    return N8nWebhookService(db=session)


def get_n8n_client_dep(session: AsyncSession = Depends(get_session)) -> N8nClient:
    """Get n8n client dependency."""
    return get_n8n_client(session)


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request, considering proxy headers."""
    # Check for forwarded headers (from reverse proxy)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take first IP in the list
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fallback to direct client
    if request.client:
        return request.client.host

    return None


# ============================================
# Health Check Endpoints
# ============================================

@router.get("/health")
async def webhook_health():
    """
    Webhook service health check.

    Returns basic health status for the webhook service.
    """
    return {
        "status": "healthy",
        "service": "webhooks",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/n8n/health", response_model=N8nHealthResponse)
async def check_n8n_health(
    client: N8nClient = Depends(get_n8n_client_dep),
):
    """
    Check n8n server health and connectivity.

    Returns:
        N8nHealthResponse with connection status
    """
    result = await client.health_check()

    return N8nHealthResponse(
        success=result.get("success", False),
        status=result.get("status", "unknown"),
        n8n_url=result.get("n8n_url", ""),
        error=result.get("error"),
    )


# ============================================
# S2-2: n8n Workflow Trigger (Outbound)
# IMPORTANT: These must be defined BEFORE /n8n/{workflow_id}
# ============================================

@router.get("/n8n/workflows", response_model=N8nWorkflowListResponse)
async def list_n8n_workflows(
    client: N8nClient = Depends(get_n8n_client_dep),
):
    """
    List available n8n workflows.

    Note: Requires n8n API key to be configured.

    Returns:
        N8nWorkflowListResponse with list of workflows
    """
    result = await client.list_workflows()

    if not result.get("success"):
        return N8nWorkflowListResponse(
            success=False,
            workflows=[],
            total=0,
            error=result.get("error"),
        )

    # Transform workflow data
    workflows = []
    for wf in result.get("workflows", []):
        workflows.append({
            "id": str(wf.get("id", "")),
            "name": wf.get("name", "Unknown"),
            "active": wf.get("active", False),
            "created_at": wf.get("createdAt"),
            "updated_at": wf.get("updatedAt"),
        })

    return N8nWorkflowListResponse(
        success=True,
        workflows=workflows,
        total=len(workflows),
    )


@router.post("/n8n/trigger", response_model=N8nTriggerResponse)
async def trigger_n8n_workflow(
    trigger_request: N8nTriggerRequest,
    request: Request,
    client: N8nClient = Depends(get_n8n_client_dep),
):
    """
    Trigger an n8n workflow from IPA platform.

    This endpoint allows IPA workflows to trigger external n8n workflows,
    enabling bidirectional integration between the two platforms.

    Args:
        trigger_request: Trigger configuration with workflow ID and data

    Returns:
        N8nTriggerResponse with trigger result

    Example:
        ```json
        POST /api/v1/webhooks/n8n/trigger
        {
            "n8n_workflow_id": "process-data",
            "data": {"items": [1, 2, 3]},
            "test_mode": false
        }
        ```
    """
    try:
        if trigger_request.test_mode:
            # Use test webhook endpoint
            result = await client.trigger_workflow_test(
                workflow_id=trigger_request.n8n_workflow_id,
                data=trigger_request.data,
            )
        else:
            # Use production webhook endpoint
            result = await client.trigger_workflow(
                workflow_id=trigger_request.n8n_workflow_id,
                data=trigger_request.data,
                webhook_path=trigger_request.webhook_path,
            )

        return N8nTriggerResponse(
            success=result.get("success", False),
            workflow_id=trigger_request.n8n_workflow_id,
            request_id=result.get("request_id", str(uuid.uuid4())),
            n8n_response=result.get("n8n_response"),
            error=result.get("error"),
            error_type=result.get("error_type"),
            duration_ms=result.get("duration_ms"),
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error triggering n8n workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering n8n workflow: {str(e)}"
        )


# ============================================
# S2-1: n8n Webhook (Inbound)
# ============================================

@router.post("/n8n/test", response_model=WebhookTestResponse)
async def test_n8n_webhook(
    request: Request,
    service: N8nWebhookService = Depends(get_n8n_service),
):
    """
    Test n8n webhook endpoint.

    This endpoint can be used to verify webhook configuration and
    signature validation without triggering actual workflow execution.

    Returns diagnostic information about the received request.
    """
    try:
        # Get raw body
        body = await request.body()

        # Parse JSON payload
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw_body": body.decode("utf-8", errors="replace")}

        # Extract headers (filter sensitive ones)
        safe_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ["authorization", "cookie"]
        }

        # Test webhook
        result = await service.test_webhook(
            payload=payload,
            headers=safe_headers,
            ip_address=get_client_ip(request),
        )

        return WebhookTestResponse(
            success=result["success"],
            message=result["message"],
            received_payload=result["received_payload"],
            headers_received=result["headers_received"],
            signature_info=result.get("signature_info"),
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error in webhook test: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test failed: {str(e)}"
        )


# ============================================
# Dynamic path routes (must be AFTER fixed paths)
# ============================================

@router.post("/n8n/trigger/{workflow_id}", response_model=N8nTriggerResponse)
async def trigger_n8n_workflow_by_path(
    workflow_id: str,
    request: Request,
    client: N8nClient = Depends(get_n8n_client_dep),
):
    """
    Trigger an n8n workflow by workflow ID path.

    This is a simplified endpoint that accepts the workflow ID in the URL path
    and the data in the request body.

    Args:
        workflow_id: n8n workflow ID or webhook path

    Returns:
        N8nTriggerResponse with trigger result
    """
    try:
        # Parse request body
        body = await request.body()
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        result = await client.trigger_workflow(
            workflow_id=workflow_id,
            data=data,
        )

        return N8nTriggerResponse(
            success=result.get("success", False),
            workflow_id=workflow_id,
            request_id=result.get("request_id", str(uuid.uuid4())),
            n8n_response=result.get("n8n_response"),
            error=result.get("error"),
            error_type=result.get("error_type"),
            duration_ms=result.get("duration_ms"),
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error triggering n8n workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering n8n workflow: {str(e)}"
        )


@router.post("/n8n/{workflow_id}", response_model=WebhookResponse)
async def n8n_webhook(
    workflow_id: str,
    request: Request,
    service: N8nWebhookService = Depends(get_n8n_service),
):
    """
    Receive n8n webhook trigger.

    This endpoint receives webhook calls from n8n workflows and triggers
    corresponding IPA platform workflow executions.

    Args:
        workflow_id: Target workflow ID to trigger

    Headers:
        X-N8n-Signature: HMAC-SHA256 signature for payload verification
        Content-Type: application/json

    Returns:
        WebhookResponse with execution details
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    try:
        # Get raw body for signature verification
        body = await request.body()

        # Parse JSON payload
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in webhook payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )

        # Get signature from header
        signature = request.headers.get("x-n8n-signature", "")

        # Verify signature if provided
        if signature:
            if not service.verify_signature(body, signature):
                logger.warning(
                    f"Invalid webhook signature for workflow {workflow_id}, "
                    f"IP: {get_client_ip(request)}"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature"
                )
        else:
            # Log warning but allow unsigned webhooks in development
            # In production, this should be configurable
            logger.warning(
                f"Unsigned webhook received for workflow {workflow_id}, "
                f"IP: {get_client_ip(request)}"
            )

        # Extract headers for service
        headers = dict(request.headers)

        # Process webhook
        result = await service.handle_webhook(
            workflow_id=workflow_id,
            payload=payload,
            headers=headers,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        # Calculate duration
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return WebhookResponse(
            success=True,
            execution_id=result.get("execution_id"),
            message=result.get("message", "Webhook processed successfully"),
            timestamp=datetime.utcnow(),
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing n8n webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.post("/generic/{source}")
async def generic_webhook(
    source: str,
    request: Request,
    service: N8nWebhookService = Depends(get_n8n_service),
):
    """
    Generic webhook endpoint for other integrations.

    Args:
        source: Webhook source identifier (e.g., "github", "gitlab", "custom")

    Returns:
        Generic webhook response
    """
    request_id = str(uuid.uuid4())

    try:
        # Get raw body
        body = await request.body()

        # Parse JSON payload
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw_body": body.decode("utf-8", errors="replace")}

        # Log the webhook receipt
        logger.info(
            f"Generic webhook received from {source}, "
            f"IP: {get_client_ip(request)}, "
            f"Request ID: {request_id}"
        )

        return {
            "success": True,
            "message": f"Webhook from {source} received",
            "request_id": request_id,
            "source": source,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Generic webhook - no action taken. Configure specific handler for this source."
        }

    except Exception as e:
        logger.error(f"Error processing generic webhook from {source}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )
