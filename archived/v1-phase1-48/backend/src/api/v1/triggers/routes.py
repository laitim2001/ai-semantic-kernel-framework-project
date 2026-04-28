# =============================================================================
# IPA Platform - Triggers API Routes
# =============================================================================
# Sprint 3: 集成 & 可靠性 - n8n 觸發與錯誤處理
#
# REST API endpoints for Webhook trigger management:
#   - POST /triggers/webhook/{workflow_id} - 觸發工作流
#   - GET /triggers/webhooks - 列出配置
#   - POST /triggers/webhooks - 創建配置
#   - GET /triggers/webhooks/{workflow_id} - 獲取配置
#   - PUT /triggers/webhooks/{workflow_id} - 更新配置
#   - DELETE /triggers/webhooks/{workflow_id} - 刪除配置
#   - POST /triggers/webhooks/test-signature - 測試簽名
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from src.api.v1.triggers.schemas import (
    ErrorResponse,
    SignatureTestRequest,
    SignatureTestResponse,
    TriggerPayload,
    TriggerResponse,
    WebhookConfigCreateRequest,
    WebhookConfigResponse,
    WebhookConfigUpdateRequest,
    WebhookListResponse,
)
from src.domain.triggers.webhook import (
    SignatureAlgorithm,
    SignatureVerificationError,
    WebhookConfigNotFoundError,
    WebhookDisabledError,
    WebhookError,
    WebhookPayload,
    WebhookTriggerConfig,
    WebhookTriggerService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/triggers",
    tags=["triggers"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Dependency Injection
# =============================================================================

# Global service instance (in production, use proper DI)
_trigger_service: Optional[WebhookTriggerService] = None


def get_trigger_service() -> WebhookTriggerService:
    """Get or create trigger service."""
    global _trigger_service

    if _trigger_service is None:
        _trigger_service = WebhookTriggerService()

    return _trigger_service


# =============================================================================
# Webhook Trigger Endpoints
# =============================================================================


@router.post(
    "/webhook/{workflow_id}",
    response_model=TriggerResponse,
    summary="觸發工作流",
    description="透過 Webhook 觸發指定工作流執行",
)
async def trigger_workflow(
    workflow_id: UUID,
    request: Request,
    payload: Optional[TriggerPayload] = None,
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    x_webhook_timestamp: Optional[str] = Header(None, alias="X-Webhook-Timestamp"),
    x_webhook_source: str = Header("n8n", alias="X-Webhook-Source"),
    service: WebhookTriggerService = Depends(get_trigger_service),
) -> TriggerResponse:
    """
    觸發工作流執行.

    驗證簽名後觸發指定工作流，支持重試機制和回調通知。
    """
    try:
        # 獲取原始請求體
        raw_body = await request.body()

        # 構建載荷
        webhook_payload = WebhookPayload(
            data=payload.data if payload else {},
            headers=dict(request.headers),
            signature=x_webhook_signature,
            timestamp=x_webhook_timestamp,
            source=x_webhook_source,
        )

        # 觸發工作流
        result = await service.trigger(
            workflow_id=workflow_id,
            payload=webhook_payload,
            raw_body=raw_body,
        )

        return TriggerResponse(
            success=result.success,
            execution_id=result.execution_id,
            message=result.message,
            error=result.error,
            retry_count=result.retry_count,
            duration_ms=result.duration_ms,
        )

    except SignatureVerificationError as e:
        logger.warning(f"Signature verification failed for workflow {workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": str(e), "error_code": e.code},
        )

    except WebhookConfigNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": str(e), "error_code": e.code},
        )

    except WebhookDisabledError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": str(e), "error_code": e.code},
        )

    except WebhookError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "error_code": e.code},
        )

    except Exception as e:
        logger.error(f"Trigger error for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "error_code": "INTERNAL_ERROR"},
        )


# =============================================================================
# Webhook Configuration Endpoints
# =============================================================================


@router.get(
    "/webhooks",
    response_model=WebhookListResponse,
    summary="列出 Webhook 配置",
    description="獲取所有 Webhook 配置列表",
)
async def list_webhook_configs(
    service: WebhookTriggerService = Depends(get_trigger_service),
) -> WebhookListResponse:
    """列出所有 Webhook 配置."""
    configs = service.list_configs()

    return WebhookListResponse(
        items=[
            WebhookConfigResponse(
                id=config.id,
                workflow_id=config.workflow_id,
                callback_url=config.callback_url,
                enabled=config.enabled,
                retry_enabled=config.retry_enabled,
                max_retries=config.max_retries,
                retry_delay_seconds=config.retry_delay_seconds,
                algorithm=config.algorithm.value,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )
            for config in configs
        ],
        total=len(configs),
    )


@router.post(
    "/webhooks",
    response_model=WebhookConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="創建 Webhook 配置",
    description="為指定工作流創建 Webhook 配置",
)
async def create_webhook_config(
    request: WebhookConfigCreateRequest,
    service: WebhookTriggerService = Depends(get_trigger_service),
) -> WebhookConfigResponse:
    """創建 Webhook 配置."""
    try:
        # 檢查是否已存在
        existing = service.get_config(request.workflow_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Webhook config already exists for workflow: {request.workflow_id}",
            )

        # 解析算法
        try:
            algorithm = SignatureAlgorithm(request.algorithm)
        except ValueError:
            algorithm = SignatureAlgorithm.HMAC_SHA256

        # 創建配置
        config = WebhookTriggerConfig(
            workflow_id=request.workflow_id,
            secret=request.secret,
            callback_url=request.callback_url,
            enabled=request.enabled,
            retry_enabled=request.retry_enabled,
            max_retries=request.max_retries,
            retry_delay_seconds=request.retry_delay_seconds,
            algorithm=algorithm,
        )

        service.register_config(config)

        return WebhookConfigResponse(
            id=config.id,
            workflow_id=config.workflow_id,
            callback_url=config.callback_url,
            enabled=config.enabled,
            retry_enabled=config.retry_enabled,
            max_retries=config.max_retries,
            retry_delay_seconds=config.retry_delay_seconds,
            algorithm=config.algorithm.value,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error creating webhook config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create webhook config: {str(e)}",
        )


@router.get(
    "/webhooks/{workflow_id}",
    response_model=WebhookConfigResponse,
    summary="獲取 Webhook 配置",
    description="獲取指定工作流的 Webhook 配置",
)
async def get_webhook_config(
    workflow_id: UUID,
    service: WebhookTriggerService = Depends(get_trigger_service),
) -> WebhookConfigResponse:
    """獲取 Webhook 配置."""
    config = service.get_config(workflow_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook config not found for workflow: {workflow_id}",
        )

    return WebhookConfigResponse(
        id=config.id,
        workflow_id=config.workflow_id,
        callback_url=config.callback_url,
        enabled=config.enabled,
        retry_enabled=config.retry_enabled,
        max_retries=config.max_retries,
        retry_delay_seconds=config.retry_delay_seconds,
        algorithm=config.algorithm.value,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.put(
    "/webhooks/{workflow_id}",
    response_model=WebhookConfigResponse,
    summary="更新 Webhook 配置",
    description="更新指定工作流的 Webhook 配置",
)
async def update_webhook_config(
    workflow_id: UUID,
    request: WebhookConfigUpdateRequest,
    service: WebhookTriggerService = Depends(get_trigger_service),
) -> WebhookConfigResponse:
    """更新 Webhook 配置."""
    config = service.get_config(workflow_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook config not found for workflow: {workflow_id}",
        )

    # 更新字段
    if request.callback_url is not None:
        config.callback_url = request.callback_url
    if request.enabled is not None:
        config.enabled = request.enabled
    if request.retry_enabled is not None:
        config.retry_enabled = request.retry_enabled
    if request.max_retries is not None:
        config.max_retries = request.max_retries
    if request.retry_delay_seconds is not None:
        config.retry_delay_seconds = request.retry_delay_seconds

    config.updated_at = datetime.utcnow()

    return WebhookConfigResponse(
        id=config.id,
        workflow_id=config.workflow_id,
        callback_url=config.callback_url,
        enabled=config.enabled,
        retry_enabled=config.retry_enabled,
        max_retries=config.max_retries,
        retry_delay_seconds=config.retry_delay_seconds,
        algorithm=config.algorithm.value,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete(
    "/webhooks/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除 Webhook 配置",
    description="刪除指定工作流的 Webhook 配置",
)
async def delete_webhook_config(
    workflow_id: UUID,
    service: WebhookTriggerService = Depends(get_trigger_service),
) -> None:
    """刪除 Webhook 配置."""
    if not service.unregister_config(workflow_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook config not found for workflow: {workflow_id}",
        )


# =============================================================================
# Utility Endpoints
# =============================================================================


@router.post(
    "/webhooks/test-signature",
    response_model=SignatureTestResponse,
    summary="測試簽名",
    description="測試 HMAC 簽名驗證",
)
async def test_signature(
    request: SignatureTestRequest,
    service: WebhookTriggerService = Depends(get_trigger_service),
) -> SignatureTestResponse:
    """測試簽名驗證."""
    try:
        algorithm = SignatureAlgorithm(request.algorithm)
    except ValueError:
        algorithm = SignatureAlgorithm.HMAC_SHA256

    payload_bytes = request.payload.encode("utf-8")

    # 生成期望簽名
    expected = service.generate_signature(
        payload_bytes,
        request.secret,
        algorithm,
    )

    # 驗證簽名
    is_valid = service.verify_signature(
        payload_bytes,
        request.signature,
        request.secret,
        algorithm,
    )

    return SignatureTestResponse(
        valid=is_valid,
        expected_signature=expected,
        message="Signature is valid" if is_valid else "Signature is invalid",
    )


@router.get(
    "/health",
    summary="健康檢查",
    description="Trigger 服務健康檢查",
)
async def health_check(
    service: WebhookTriggerService = Depends(get_trigger_service),
) -> Dict[str, Any]:
    """健康檢查."""
    configs = service.list_configs()

    return {
        "status": "healthy",
        "service": "triggers",
        "config_count": len(configs),
        "enabled_count": sum(1 for c in configs if c.enabled),
        "timestamp": datetime.utcnow().isoformat(),
    }
