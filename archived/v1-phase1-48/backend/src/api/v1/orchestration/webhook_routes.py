"""
ServiceNow Webhook API Routes.

Sprint 114: AD 場景基礎建設 (Phase 32)
Sprint 126: IT Incident Handler (Phase 34)

Provides webhook endpoints for receiving ServiceNow events:
    POST /api/v1/orchestration/webhooks/servicenow          — RITM events
    POST /api/v1/orchestration/webhooks/servicenow/incident — INC events
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.integrations.orchestration.input.servicenow_webhook import (
    ServiceNowRITMEvent,
    ServiceNowWebhookReceiver,
    WebhookAuthConfig,
    WebhookValidationError,
)
from src.integrations.orchestration.input.ritm_intent_mapper import (
    RITMIntentMapper,
)
from src.integrations.orchestration.input.incident_handler import (
    IncidentHandler,
    ServiceNowINCEvent,
)
from src.api.v1.orchestration.schemas import (
    IncidentWebhookResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

webhook_router = APIRouter(
    prefix="/orchestration/webhooks",
    tags=["orchestration-webhooks"],
    responses={
        401: {"description": "Authentication failed"},
        403: {"description": "IP not allowed"},
        409: {"description": "Duplicate event"},
        503: {"description": "Webhook disabled"},
    },
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WebhookResponse(BaseModel):
    """Webhook acceptance response."""

    status: str = Field(..., description="Processing status")
    tracking_id: str = Field(..., description="Unique tracking identifier")
    ritm_number: str = Field(..., description="ServiceNow RITM number")
    cat_item_name: str = Field(default="", description="Catalog item name")
    intent: Optional[str] = Field(None, description="Mapped IPA intent")
    received_at: str = Field(..., description="Reception timestamp")


class WebhookErrorResponse(BaseModel):
    """Webhook error response."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error description")


# ---------------------------------------------------------------------------
# Service Singleton
# ---------------------------------------------------------------------------

_webhook_receiver: Optional[ServiceNowWebhookReceiver] = None
_intent_mapper: Optional[RITMIntentMapper] = None
_incident_handler: Optional[IncidentHandler] = None


def get_webhook_receiver() -> ServiceNowWebhookReceiver:
    """Get or create the webhook receiver singleton.

    Returns:
        Configured ServiceNowWebhookReceiver instance
    """
    global _webhook_receiver
    if _webhook_receiver is None:
        auth_config = WebhookAuthConfig(
            auth_type="shared_secret",
            shared_secret=os.environ.get("SERVICENOW_WEBHOOK_SECRET"),
            allowed_ips=[
                ip.strip()
                for ip in os.environ.get("SERVICENOW_ALLOWED_IPS", "").split(",")
                if ip.strip()
            ],
            enabled=os.environ.get("SERVICENOW_WEBHOOK_ENABLED", "true").lower()
            == "true",
        )
        _webhook_receiver = ServiceNowWebhookReceiver(auth_config)
    return _webhook_receiver


def get_intent_mapper() -> RITMIntentMapper:
    """Get or create the RITM intent mapper singleton.

    Returns:
        Configured RITMIntentMapper instance
    """
    global _intent_mapper
    if _intent_mapper is None:
        _intent_mapper = RITMIntentMapper()
    return _intent_mapper


def get_incident_handler() -> IncidentHandler:
    """Get or create the Incident handler singleton.

    Returns:
        Configured IncidentHandler instance
    """
    global _incident_handler
    if _incident_handler is None:
        _incident_handler = IncidentHandler()
    return _incident_handler


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@webhook_router.post(
    "/servicenow",
    response_model=WebhookResponse,
    summary="接收 ServiceNow RITM Webhook",
    description="接收並處理 ServiceNow Requested Item (RITM) 事件，"
    "自動映射到 IPA 業務意圖。",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_servicenow_webhook(
    request: Request,
    payload: ServiceNowRITMEvent,
    x_servicenow_secret: Optional[str] = Header(
        None, alias="X-ServiceNow-Secret"
    ),
) -> WebhookResponse:
    """Receive and process a ServiceNow RITM webhook event.

    Flow:
        1. Validate authentication (shared secret + IP)
        2. Parse RITM event payload
        3. Check idempotency (duplicate detection)
        4. Map RITM to IPA intent
        5. Return tracking ID

    Args:
        request: FastAPI request object
        payload: Validated RITM event data
        x_servicenow_secret: Shared secret header

    Returns:
        WebhookResponse with tracking ID and mapped intent

    Raises:
        HTTPException: On authentication failure, duplicate, or processing error
    """
    receiver = get_webhook_receiver()
    mapper = get_intent_mapper()

    # Extract client IP
    client_ip = None
    if request.client:
        client_ip = request.client.host

    try:
        # Validate request
        await receiver.validate_request(
            secret_header=x_servicenow_secret,
            client_ip=client_ip,
        )

        # Process event (includes idempotency check)
        result = await receiver.process_event(payload)

        # Map to IPA intent
        mapping_result = mapper.map_ritm_to_intent(payload)

        return WebhookResponse(
            status=result["status"],
            tracking_id=result["tracking_id"],
            ritm_number=result["ritm_number"],
            cat_item_name=result.get("cat_item_name", ""),
            intent=mapping_result.intent if mapping_result.matched else None,
            received_at=result["received_at"],
        )

    except WebhookValidationError as e:
        logger.warning(f"Webhook validation failed: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": "WEBHOOK_VALIDATION_ERROR", "message": str(e)},
        )
    except ValueError as e:
        logger.error(f"Payload parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_PAYLOAD", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROCESSING_ERROR", "message": "Internal error"},
        )


@webhook_router.get(
    "/servicenow/health",
    summary="ServiceNow Webhook 健康檢查",
    description="檢查 Webhook 接收器的運行狀態。",
)
async def webhook_health() -> Dict[str, Any]:
    """Check webhook receiver health status.

    Returns:
        Health status including enabled state and cache size
    """
    receiver = get_webhook_receiver()
    return {
        "status": "ok",
        "enabled": receiver._auth_config.enabled,
        "processed_events_cached": len(receiver._processed_events),
        "auth_type": receiver._auth_config.auth_type,
        "ip_whitelist_configured": len(receiver._auth_config.allowed_ips) > 0,
    }


# ---------------------------------------------------------------------------
# Sprint 126: Incident (INC) Webhook Endpoint
# ---------------------------------------------------------------------------


@webhook_router.post(
    "/servicenow/incident",
    response_model=IncidentWebhookResponse,
    summary="接收 ServiceNow Incident (INC) Webhook",
    description=(
        "接收並處理 ServiceNow Incident (INC) 事件，"
        "自動分類事件子類別、評估風險等級，"
        "並觸發 IPA 事件分析管線。"
    ),
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_servicenow_incident(
    request: Request,
    payload: ServiceNowINCEvent,
    x_servicenow_secret: Optional[str] = Header(
        None, alias="X-ServiceNow-Secret"
    ),
) -> IncidentWebhookResponse:
    """Receive and process a ServiceNow Incident webhook event.

    Flow:
        1. Validate authentication (shared secret + IP)
        2. Parse INC event payload via IncidentHandler
        3. Classify incident subcategory
        4. Map priority to risk level
        5. Return tracking ID + classification results

    Args:
        request: FastAPI request object
        payload: Validated INC event data
        x_servicenow_secret: Shared secret header

    Returns:
        IncidentWebhookResponse with tracking ID, subcategory, risk level

    Raises:
        HTTPException: On authentication failure or processing error
    """
    receiver = get_webhook_receiver()
    handler = get_incident_handler()

    # Extract client IP
    client_ip = None
    if request.client:
        client_ip = request.client.host

    try:
        # Validate request (reuse RITM auth infrastructure)
        await receiver.validate_request(
            secret_header=x_servicenow_secret,
            client_ip=client_ip,
        )

        # Verify handler can process this payload
        if not handler.can_handle(payload.model_dump()):
            raise ValueError(
                f"Payload does not look like a ServiceNow INC event: "
                f"number={payload.number}"
            )

        # Process via IncidentHandler → RoutingRequest
        routing_request = await handler.process(payload.model_dump())

        # Build response from routing request context
        ctx = routing_request.context or {}
        tracking_id = routing_request.request_id or str(uuid.uuid4())
        now_str = datetime.utcnow().isoformat() + "Z"

        logger.info(
            f"Incident webhook accepted: {payload.number} → "
            f"tracking_id={tracking_id}, "
            f"subcategory={ctx.get('subcategory', '')}, "
            f"risk_level={ctx.get('risk_level', 'medium')}"
        )

        return IncidentWebhookResponse(
            status="accepted",
            tracking_id=tracking_id,
            incident_number=payload.number,
            subcategory=ctx.get("subcategory", ""),
            risk_level=ctx.get("risk_level", "medium"),
            intent="incident",
            received_at=now_str,
        )

    except WebhookValidationError as e:
        logger.warning(f"Incident webhook validation failed: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": "WEBHOOK_VALIDATION_ERROR", "message": str(e)},
        )
    except ValueError as e:
        logger.error(f"Incident payload processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_PAYLOAD", "message": str(e)},
        )
    except Exception as e:
        logger.error(
            f"Incident webhook processing failed: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROCESSING_ERROR", "message": "Internal error"},
        )
