# =============================================================================
# IPA Platform - Triggers Domain Module
# =============================================================================
# Sprint 3: 集成 & 可靠性 - n8n 觸發與錯誤處理
#
# 提供 Webhook 觸發服務，支持：
#   - HMAC 簽名驗證
#   - 工作流觸發
#   - 錯誤處理和重試
#   - 回調機制
# =============================================================================

from src.domain.triggers.webhook import (
    WebhookError,
    WebhookPayload,
    WebhookTriggerConfig,
    WebhookTriggerService,
)

__all__ = [
    "WebhookTriggerConfig",
    "WebhookTriggerService",
    "WebhookPayload",
    "WebhookError",
]
