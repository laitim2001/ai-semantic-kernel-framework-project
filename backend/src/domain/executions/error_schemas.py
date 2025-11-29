"""
Error handling schemas and types
"""
from enum import Enum
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ErrorType(str, Enum):
    """錯誤類型枚舉"""

    # Retryable errors (可重試)
    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_ERROR = "connection_error"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_DEADLOCK = "database_deadlock"
    TEMPORARY_FAILURE = "temporary_failure"

    # Non-retryable errors (不可重試)
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND_ERROR = "not_found_error"
    BUSINESS_LOGIC_ERROR = "business_logic_error"
    CONFIGURATION_ERROR = "configuration_error"

    # System errors
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(str, Enum):
    """錯誤嚴重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RetryConfig(BaseModel):
    """重試配置"""
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重試次數")
    base_delay_ms: int = Field(default=1000, ge=100, le=60000, description="基礎延遲時間(毫秒)")
    max_delay_ms: int = Field(default=30000, ge=1000, le=300000, description="最大延遲時間(毫秒)")
    jitter: bool = Field(default=True, description="是否添加隨機抖動")
    exponential_base: float = Field(default=2.0, ge=1.1, le=3.0, description="指數基數")

    model_config = ConfigDict(from_attributes=True)


class ErrorContext(BaseModel):
    """錯誤上下文"""
    error_type: ErrorType
    error_message: str
    error_code: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    stack_trace: Optional[str] = None
    timestamp: datetime
    attempt: int = Field(ge=0, description="第幾次嘗試 (0 = 首次)")
    retry_delay_ms: Optional[int] = Field(None, description="重試延遲(毫秒)")
    is_retryable: bool
    context_data: dict[str, Any] = Field(default_factory=dict, description="額外上下文數據")

    model_config = ConfigDict(from_attributes=True)


class CircuitBreakerConfig(BaseModel):
    """斷路器配置"""
    enabled: bool = Field(default=True, description="是否啟用斷路器")
    failure_threshold: int = Field(default=5, ge=1, description="失敗閾值")
    success_threshold: int = Field(default=2, ge=1, description="成功閾值(半開狀態)")
    timeout_ms: int = Field(default=60000, ge=1000, description="斷路器打開時間(毫秒)")
    half_open_max_calls: int = Field(default=1, ge=1, description="半開狀態允許的最大請求數")

    model_config = ConfigDict(from_attributes=True)


class CircuitBreakerState(str, Enum):
    """斷路器狀態"""
    CLOSED = "closed"      # 正常狀態
    OPEN = "open"          # 斷路器打開,拒絕請求
    HALF_OPEN = "half_open"  # 半開狀態,嘗試恢復


def classify_error(exception: Exception) -> ErrorType:
    """
    分類錯誤類型

    Args:
        exception: Python 異常對象

    Returns:
        ErrorType: 錯誤類型
    """
    exception_name = type(exception).__name__
    error_message = str(exception).lower()

    # Network and connection errors
    if "timeout" in error_message or "timed out" in error_message:
        return ErrorType.NETWORK_TIMEOUT

    if any(keyword in error_message for keyword in ["connection", "connect", "unreachable"]):
        return ErrorType.CONNECTION_ERROR

    # Rate limiting
    if "429" in error_message or "rate limit" in error_message or "too many requests" in error_message:
        return ErrorType.RATE_LIMIT

    # Service unavailable
    if "503" in error_message or "service unavailable" in error_message or "temporarily unavailable" in error_message:
        return ErrorType.SERVICE_UNAVAILABLE

    # Database errors
    if "deadlock" in error_message or "lock timeout" in error_message:
        return ErrorType.DATABASE_DEADLOCK

    # Authentication and authorization
    if "401" in error_message or "unauthorized" in error_message or "authentication" in error_message:
        return ErrorType.AUTHENTICATION_ERROR

    if "403" in error_message or "forbidden" in error_message or "permission" in error_message:
        return ErrorType.AUTHORIZATION_ERROR

    # Validation errors
    if "validation" in error_message or "invalid" in error_message or "400" in error_message:
        return ErrorType.VALIDATION_ERROR

    # Not found
    if "404" in error_message or "not found" in error_message:
        return ErrorType.NOT_FOUND_ERROR

    # Business logic errors (custom exceptions)
    if exception_name in ["BusinessLogicError", "BusinessException"]:
        return ErrorType.BUSINESS_LOGIC_ERROR

    # Configuration errors
    if "configuration" in error_message or "config" in error_message:
        return ErrorType.CONFIGURATION_ERROR

    # Default to unknown
    return ErrorType.UNKNOWN_ERROR


def is_retryable_error(error_type: ErrorType) -> bool:
    """
    判斷錯誤是否可重試

    Args:
        error_type: 錯誤類型

    Returns:
        bool: 是否可重試
    """
    retryable_errors = {
        ErrorType.NETWORK_TIMEOUT,
        ErrorType.CONNECTION_ERROR,
        ErrorType.RATE_LIMIT,
        ErrorType.SERVICE_UNAVAILABLE,
        ErrorType.DATABASE_DEADLOCK,
        ErrorType.TEMPORARY_FAILURE,
    }

    return error_type in retryable_errors


def get_error_severity(error_type: ErrorType) -> ErrorSeverity:
    """
    獲取錯誤嚴重程度

    Args:
        error_type: 錯誤類型

    Returns:
        ErrorSeverity: 錯誤嚴重程度
    """
    critical_errors = {
        ErrorType.DATABASE_DEADLOCK,
        ErrorType.CONFIGURATION_ERROR,
    }

    high_priority_errors = {
        ErrorType.AUTHENTICATION_ERROR,
        ErrorType.AUTHORIZATION_ERROR,
        ErrorType.BUSINESS_LOGIC_ERROR,
    }

    if error_type in critical_errors:
        return ErrorSeverity.CRITICAL
    elif error_type in high_priority_errors:
        return ErrorSeverity.ERROR
    elif error_type in {ErrorType.VALIDATION_ERROR, ErrorType.NOT_FOUND_ERROR}:
        return ErrorSeverity.WARNING
    else:
        return ErrorSeverity.ERROR
