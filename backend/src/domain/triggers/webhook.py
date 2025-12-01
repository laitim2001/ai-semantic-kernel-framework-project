# =============================================================================
# IPA Platform - Webhook Trigger Service
# =============================================================================
# Sprint 3: 集成 & 可靠性 - n8n 觸發與錯誤處理
#
# Webhook 觸發服務實現，提供：
#   - HMAC-SHA256 簽名驗證
#   - 工作流觸發執行
#   - 指數退避重試機制
#   - 成功/失敗回調
# =============================================================================

import asyncio
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class WebhookStatus(str, Enum):
    """Webhook 請求狀態."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class SignatureAlgorithm(str, Enum):
    """支持的簽名算法."""

    HMAC_SHA256 = "hmac-sha256"
    HMAC_SHA512 = "hmac-sha512"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WebhookTriggerConfig:
    """
    Webhook 觸發配置.

    Attributes:
        id: 配置 ID
        workflow_id: 關聯的工作流 ID
        secret: 用於簽名驗證的密鑰
        callback_url: 回調 URL (可選)
        enabled: 是否啟用
        retry_enabled: 是否啟用重試
        max_retries: 最大重試次數
        retry_delay_seconds: 初始重試延遲（秒）
        algorithm: 簽名算法
        created_at: 創建時間
        updated_at: 更新時間
    """

    workflow_id: UUID
    secret: str
    id: UUID = field(default_factory=uuid4)
    callback_url: Optional[str] = None
    enabled: bool = True
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    algorithm: SignatureAlgorithm = SignatureAlgorithm.HMAC_SHA256
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id),
            "secret": "***",  # Don't expose secret
            "callback_url": self.callback_url,
            "enabled": self.enabled,
            "retry_enabled": self.retry_enabled,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "algorithm": self.algorithm.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class WebhookPayload:
    """
    Webhook 請求載荷.

    Attributes:
        data: 請求數據
        headers: 請求標頭
        signature: 請求簽名
        timestamp: 請求時間戳
        source: 來源標識
    """

    data: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)
    signature: Optional[str] = None
    timestamp: Optional[str] = None
    source: str = "n8n"

    @classmethod
    def from_request(
        cls,
        body: bytes,
        headers: Dict[str, str],
    ) -> "WebhookPayload":
        """
        從 HTTP 請求創建載荷.

        Args:
            body: 請求體
            headers: 請求標頭

        Returns:
            WebhookPayload 實例
        """
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {"raw": body.decode("utf-8", errors="replace")}

        return cls(
            data=data,
            headers=dict(headers),
            signature=headers.get("X-Webhook-Signature") or headers.get("x-webhook-signature"),
            timestamp=headers.get("X-Webhook-Timestamp") or headers.get("x-webhook-timestamp"),
            source=headers.get("X-Webhook-Source", "n8n"),
        )


@dataclass
class TriggerResult:
    """
    觸發結果.

    Attributes:
        success: 是否成功
        execution_id: 執行 ID
        message: 結果消息
        error: 錯誤信息
        retry_count: 重試次數
        duration_ms: 執行時長（毫秒）
    """

    success: bool
    execution_id: Optional[UUID] = None
    message: str = ""
    error: Optional[str] = None
    retry_count: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "message": self.message,
            "error": self.error,
            "retry_count": self.retry_count,
            "duration_ms": round(self.duration_ms, 2),
        }


# =============================================================================
# Exceptions
# =============================================================================


class WebhookError(Exception):
    """Webhook 相關錯誤基類."""

    def __init__(self, message: str, code: str = "WEBHOOK_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SignatureVerificationError(WebhookError):
    """簽名驗證失敗."""

    def __init__(self, message: str = "Invalid signature"):
        super().__init__(message, code="INVALID_SIGNATURE")


class WebhookConfigNotFoundError(WebhookError):
    """Webhook 配置未找到."""

    def __init__(self, workflow_id: UUID):
        super().__init__(
            f"Webhook config not found for workflow: {workflow_id}",
            code="CONFIG_NOT_FOUND",
        )


class WebhookDisabledError(WebhookError):
    """Webhook 已禁用."""

    def __init__(self, workflow_id: UUID):
        super().__init__(
            f"Webhook is disabled for workflow: {workflow_id}",
            code="WEBHOOK_DISABLED",
        )


class TriggerExecutionError(WebhookError):
    """觸發執行錯誤."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(message, code="TRIGGER_EXECUTION_ERROR")


# =============================================================================
# Webhook Trigger Service
# =============================================================================


class WebhookTriggerService:
    """
    Webhook 觸發服務.

    提供 HMAC 簽名驗證、工作流觸發、重試機制和回調功能。

    Attributes:
        _configs: Webhook 配置存儲
        _http_client: HTTP 客戶端
        _workflow_executor: 工作流執行函數
    """

    def __init__(
        self,
        workflow_executor: Optional[Callable] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        初始化服務.

        Args:
            workflow_executor: 工作流執行回調函數
            http_client: HTTP 客戶端 (可選)
        """
        self._configs: Dict[UUID, WebhookTriggerConfig] = {}
        self._workflow_executor = workflow_executor
        self._http_client = http_client

    # -------------------------------------------------------------------------
    # Configuration Management
    # -------------------------------------------------------------------------

    def register_config(self, config: WebhookTriggerConfig) -> None:
        """
        註冊 Webhook 配置.

        Args:
            config: Webhook 配置
        """
        self._configs[config.workflow_id] = config
        logger.info(f"Registered webhook config for workflow: {config.workflow_id}")

    def unregister_config(self, workflow_id: UUID) -> bool:
        """
        取消註冊 Webhook 配置.

        Args:
            workflow_id: 工作流 ID

        Returns:
            是否成功取消註冊
        """
        if workflow_id in self._configs:
            del self._configs[workflow_id]
            logger.info(f"Unregistered webhook config for workflow: {workflow_id}")
            return True
        return False

    def get_config(self, workflow_id: UUID) -> Optional[WebhookTriggerConfig]:
        """
        獲取 Webhook 配置.

        Args:
            workflow_id: 工作流 ID

        Returns:
            Webhook 配置或 None
        """
        return self._configs.get(workflow_id)

    def list_configs(self) -> List[WebhookTriggerConfig]:
        """
        列出所有 Webhook 配置.

        Returns:
            配置列表
        """
        return list(self._configs.values())

    # -------------------------------------------------------------------------
    # Signature Verification
    # -------------------------------------------------------------------------

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
        algorithm: SignatureAlgorithm = SignatureAlgorithm.HMAC_SHA256,
    ) -> bool:
        """
        驗證 HMAC 簽名.

        Args:
            payload: 請求載荷
            signature: 請求簽名
            secret: 密鑰
            algorithm: 簽名算法

        Returns:
            簽名是否有效
        """
        if not signature or not secret:
            return False

        try:
            # 選擇雜湊算法
            if algorithm == SignatureAlgorithm.HMAC_SHA256:
                hash_algo = hashlib.sha256
            elif algorithm == SignatureAlgorithm.HMAC_SHA512:
                hash_algo = hashlib.sha512
            else:
                logger.warning(f"Unsupported algorithm: {algorithm}")
                return False

            # 計算 HMAC
            expected = hmac.new(
                secret.encode("utf-8"),
                payload,
                hash_algo,
            ).hexdigest()

            # 處理可能的 "sha256=" 前綴
            actual = signature
            if "=" in signature:
                actual = signature.split("=", 1)[1]

            # 時間安全比較
            return hmac.compare_digest(expected.lower(), actual.lower())

        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    def generate_signature(
        self,
        payload: bytes,
        secret: str,
        algorithm: SignatureAlgorithm = SignatureAlgorithm.HMAC_SHA256,
    ) -> str:
        """
        生成 HMAC 簽名.

        Args:
            payload: 請求載荷
            secret: 密鑰
            algorithm: 簽名算法

        Returns:
            簽名字符串
        """
        if algorithm == SignatureAlgorithm.HMAC_SHA256:
            hash_algo = hashlib.sha256
            prefix = "sha256"
        elif algorithm == SignatureAlgorithm.HMAC_SHA512:
            hash_algo = hashlib.sha512
            prefix = "sha512"
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hash_algo,
        ).hexdigest()

        return f"{prefix}={signature}"

    # -------------------------------------------------------------------------
    # Trigger Execution
    # -------------------------------------------------------------------------

    async def trigger(
        self,
        workflow_id: UUID,
        payload: WebhookPayload,
        raw_body: Optional[bytes] = None,
    ) -> TriggerResult:
        """
        觸發工作流執行.

        Args:
            workflow_id: 工作流 ID
            payload: Webhook 載荷
            raw_body: 原始請求體 (用於簽名驗證)

        Returns:
            觸發結果

        Raises:
            WebhookConfigNotFoundError: 配置未找到
            WebhookDisabledError: Webhook 已禁用
            SignatureVerificationError: 簽名驗證失敗
        """
        start_time = time.time()

        # 獲取配置
        config = self.get_config(workflow_id)
        if not config:
            raise WebhookConfigNotFoundError(workflow_id)

        if not config.enabled:
            raise WebhookDisabledError(workflow_id)

        # 驗證簽名
        if payload.signature and raw_body:
            if not self.verify_signature(
                raw_body,
                payload.signature,
                config.secret,
                config.algorithm,
            ):
                raise SignatureVerificationError()

        # 執行工作流（帶重試）
        result = await self._execute_with_retry(
            workflow_id=workflow_id,
            payload=payload,
            config=config,
        )

        # 計算執行時長
        result.duration_ms = (time.time() - start_time) * 1000

        # 發送回調
        if config.callback_url:
            await self._send_callback(config.callback_url, result)

        return result

    async def _execute_with_retry(
        self,
        workflow_id: UUID,
        payload: WebhookPayload,
        config: WebhookTriggerConfig,
    ) -> TriggerResult:
        """
        帶重試的工作流執行.

        Args:
            workflow_id: 工作流 ID
            payload: Webhook 載荷
            config: Webhook 配置

        Returns:
            觸發結果
        """
        last_error: Optional[Exception] = None
        retry_count = 0
        max_retries = config.max_retries if config.retry_enabled else 0

        for attempt in range(max_retries + 1):
            try:
                # 執行工作流
                execution_id = await self._execute_workflow(workflow_id, payload)

                return TriggerResult(
                    success=True,
                    execution_id=execution_id,
                    message=f"Workflow triggered successfully",
                    retry_count=attempt,  # 重試次數等於嘗試次數
                )

            except Exception as e:
                last_error = e
                retry_count = attempt

                if attempt < max_retries:
                    # 指數退避
                    delay = config.retry_delay_seconds * (2 ** attempt)
                    logger.warning(
                        f"Trigger attempt {attempt + 1} failed, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Trigger failed after {max_retries + 1} attempts: {e}"
                    )

        # 所有重試都失敗
        return TriggerResult(
            success=False,
            message="Trigger failed after all retries",
            error=str(last_error) if last_error else "Unknown error",
            retry_count=retry_count,
        )

    async def _execute_workflow(
        self,
        workflow_id: UUID,
        payload: WebhookPayload,
    ) -> UUID:
        """
        執行工作流.

        Args:
            workflow_id: 工作流 ID
            payload: Webhook 載荷

        Returns:
            執行 ID
        """
        if self._workflow_executor:
            result = await self._workflow_executor(workflow_id, payload.data)
            return result.get("execution_id", uuid4())
        else:
            # Mock 執行 - 開發測試用
            logger.info(f"Mock executing workflow: {workflow_id}")
            return uuid4()

    # -------------------------------------------------------------------------
    # Callback Handling
    # -------------------------------------------------------------------------

    async def _send_callback(
        self,
        callback_url: str,
        result: TriggerResult,
    ) -> bool:
        """
        發送回調通知.

        Args:
            callback_url: 回調 URL
            result: 觸發結果

        Returns:
            是否發送成功
        """
        try:
            client = self._http_client or httpx.AsyncClient()
            should_close = self._http_client is None

            try:
                response = await client.post(
                    callback_url,
                    json={
                        "success": result.success,
                        "execution_id": str(result.execution_id) if result.execution_id else None,
                        "message": result.message,
                        "error": result.error,
                        "retry_count": result.retry_count,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    timeout=10.0,
                )

                if response.status_code >= 400:
                    logger.warning(
                        f"Callback failed with status {response.status_code}: "
                        f"{response.text}"
                    )
                    return False

                logger.info(f"Callback sent successfully to {callback_url}")
                return True

            finally:
                if should_close:
                    await client.aclose()

        except Exception as e:
            logger.error(f"Failed to send callback: {e}")
            return False

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    async def handle_error(
        self,
        workflow_id: UUID,
        error: Exception,
        payload: Optional[WebhookPayload] = None,
    ) -> Dict[str, Any]:
        """
        處理觸發錯誤.

        Args:
            workflow_id: 工作流 ID
            error: 錯誤
            payload: Webhook 載荷 (可選)

        Returns:
            錯誤響應
        """
        error_response = {
            "success": False,
            "workflow_id": str(workflow_id),
            "error": str(error),
            "error_code": getattr(error, "code", "UNKNOWN_ERROR"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 記錄錯誤
        logger.error(
            f"Webhook trigger error for workflow {workflow_id}: {error}",
            extra={"payload": payload.data if payload else None},
        )

        # 發送回調 (如果配置了)
        config = self.get_config(workflow_id)
        if config and config.callback_url:
            await self._send_callback(
                config.callback_url,
                TriggerResult(
                    success=False,
                    error=str(error),
                    message="Trigger failed",
                ),
            )

        return error_response
