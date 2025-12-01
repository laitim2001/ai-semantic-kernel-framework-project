# =============================================================================
# IPA Platform - Triggers API Schemas
# =============================================================================
# Sprint 3: 集成 & 可靠性 - n8n 觸發與錯誤處理
#
# Pydantic schemas for Triggers API endpoints.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================


class WebhookConfigCreateRequest(BaseModel):
    """創建 Webhook 配置請求."""

    workflow_id: UUID = Field(..., description="工作流 ID")
    secret: str = Field(..., min_length=16, description="Webhook 密鑰 (最少 16 字符)")
    callback_url: Optional[str] = Field(None, description="回調 URL")
    enabled: bool = Field(True, description="是否啟用")
    retry_enabled: bool = Field(True, description="是否啟用重試")
    max_retries: int = Field(3, ge=0, le=10, description="最大重試次數")
    retry_delay_seconds: float = Field(1.0, ge=0.1, le=60.0, description="初始重試延遲")
    algorithm: str = Field("hmac-sha256", description="簽名算法")


class WebhookConfigUpdateRequest(BaseModel):
    """更新 Webhook 配置請求."""

    callback_url: Optional[str] = Field(None, description="回調 URL")
    enabled: Optional[bool] = Field(None, description="是否啟用")
    retry_enabled: Optional[bool] = Field(None, description="是否啟用重試")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="最大重試次數")
    retry_delay_seconds: Optional[float] = Field(None, ge=0.1, le=60.0, description="初始重試延遲")


class TriggerPayload(BaseModel):
    """觸發請求載荷."""

    data: Dict[str, Any] = Field(default_factory=dict, description="觸發數據")
    metadata: Optional[Dict[str, Any]] = Field(None, description="額外元數據")


# =============================================================================
# Response Schemas
# =============================================================================


class WebhookConfigResponse(BaseModel):
    """Webhook 配置響應."""

    id: UUID = Field(..., description="配置 ID")
    workflow_id: UUID = Field(..., description="工作流 ID")
    callback_url: Optional[str] = Field(None, description="回調 URL")
    enabled: bool = Field(..., description="是否啟用")
    retry_enabled: bool = Field(..., description="是否啟用重試")
    max_retries: int = Field(..., description="最大重試次數")
    retry_delay_seconds: float = Field(..., description="初始重試延遲")
    algorithm: str = Field(..., description="簽名算法")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")


class TriggerResponse(BaseModel):
    """觸發結果響應."""

    success: bool = Field(..., description="是否成功")
    execution_id: Optional[UUID] = Field(None, description="執行 ID")
    message: str = Field(..., description="結果消息")
    error: Optional[str] = Field(None, description="錯誤信息")
    retry_count: int = Field(0, description="重試次數")
    duration_ms: float = Field(0.0, description="執行時長（毫秒）")


class ErrorResponse(BaseModel):
    """錯誤響應."""

    success: bool = Field(False, description="是否成功")
    error: str = Field(..., description="錯誤信息")
    error_code: str = Field(..., description="錯誤代碼")
    workflow_id: Optional[UUID] = Field(None, description="工作流 ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="時間戳")


class WebhookListResponse(BaseModel):
    """Webhook 配置列表響應."""

    items: list[WebhookConfigResponse] = Field(..., description="配置列表")
    total: int = Field(..., description="總數")


class SignatureTestRequest(BaseModel):
    """簽名測試請求."""

    payload: str = Field(..., description="載荷內容")
    secret: str = Field(..., description="密鑰")
    signature: str = Field(..., description="待驗證簽名")
    algorithm: str = Field("hmac-sha256", description="簽名算法")


class SignatureTestResponse(BaseModel):
    """簽名測試響應."""

    valid: bool = Field(..., description="簽名是否有效")
    expected_signature: str = Field(..., description="期望的簽名")
    message: str = Field(..., description="結果消息")
