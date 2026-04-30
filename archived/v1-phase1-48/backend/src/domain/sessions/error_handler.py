"""
Session Error Handler (S47-2)

Provides comprehensive error handling for Session-Agent integration:
- SessionErrorCode: Error codes enumeration
- SessionError: Error exception with metadata
- SessionErrorHandler: Error handling with retry logic
"""

from enum import Enum
from typing import Optional, Dict, Any, Callable, TypeVar, Awaitable
from datetime import datetime
import asyncio
import logging

from src.domain.sessions.events import ExecutionEvent, ExecutionEventType, ExecutionEventFactory

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SessionErrorCode(str, Enum):
    """Session error codes"""

    # Session related
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_NOT_ACTIVE = "SESSION_NOT_ACTIVE"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_SUSPENDED = "SESSION_SUSPENDED"

    # Agent related
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_CONFIG_ERROR = "AGENT_CONFIG_ERROR"
    AGENT_NOT_AVAILABLE = "AGENT_NOT_AVAILABLE"

    # LLM related
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_API_ERROR = "LLM_API_ERROR"
    LLM_CONTENT_FILTER = "LLM_CONTENT_FILTER"
    LLM_TOKEN_LIMIT = "LLM_TOKEN_LIMIT"

    # Tool related
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_PERMISSION_DENIED = "TOOL_PERMISSION_DENIED"
    TOOL_VALIDATION_ERROR = "TOOL_VALIDATION_ERROR"

    # Approval related
    APPROVAL_NOT_FOUND = "APPROVAL_NOT_FOUND"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    APPROVAL_ALREADY_PROCESSED = "APPROVAL_ALREADY_PROCESSED"

    # System related
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INVALID_REQUEST = "INVALID_REQUEST"


# Error code to HTTP status mapping
ERROR_CODE_TO_STATUS: Dict[SessionErrorCode, int] = {
    SessionErrorCode.SESSION_NOT_FOUND: 404,
    SessionErrorCode.SESSION_NOT_ACTIVE: 410,
    SessionErrorCode.SESSION_EXPIRED: 410,
    SessionErrorCode.SESSION_SUSPENDED: 409,
    SessionErrorCode.AGENT_NOT_FOUND: 404,
    SessionErrorCode.AGENT_CONFIG_ERROR: 500,
    SessionErrorCode.AGENT_NOT_AVAILABLE: 503,
    SessionErrorCode.LLM_TIMEOUT: 504,
    SessionErrorCode.LLM_RATE_LIMIT: 429,
    SessionErrorCode.LLM_API_ERROR: 502,
    SessionErrorCode.LLM_CONTENT_FILTER: 422,
    SessionErrorCode.LLM_TOKEN_LIMIT: 413,
    SessionErrorCode.TOOL_NOT_FOUND: 404,
    SessionErrorCode.TOOL_EXECUTION_ERROR: 500,
    SessionErrorCode.TOOL_TIMEOUT: 504,
    SessionErrorCode.TOOL_PERMISSION_DENIED: 403,
    SessionErrorCode.TOOL_VALIDATION_ERROR: 422,
    SessionErrorCode.APPROVAL_NOT_FOUND: 404,
    SessionErrorCode.APPROVAL_EXPIRED: 410,
    SessionErrorCode.APPROVAL_ALREADY_PROCESSED: 409,
    SessionErrorCode.INTERNAL_ERROR: 500,
    SessionErrorCode.RATE_LIMIT_EXCEEDED: 429,
    SessionErrorCode.SERVICE_UNAVAILABLE: 503,
    SessionErrorCode.INVALID_REQUEST: 400,
}


class SessionError(Exception):
    """Session error with metadata"""

    def __init__(
        self,
        code: SessionErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        session_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable
        self.session_id = session_id
        self.execution_id = execution_id
        self.timestamp = datetime.utcnow()
        super().__init__(message)

    @property
    def http_status(self) -> int:
        """Get HTTP status code for this error"""
        return ERROR_CODE_TO_STATUS.get(self.code, 500)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
            "session_id": self.session_id,
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_event(self) -> ExecutionEvent:
        """Convert to ExecutionEvent"""
        return ExecutionEventFactory.error(
            session_id=self.session_id or "",
            execution_id=self.execution_id or "",
            error_message=self.message,
            error_code=self.code.value,
            # Extra data goes into metadata
            recoverable=self.recoverable,
            details=self.details,
        )

    @classmethod
    def from_exception(
        cls,
        error: Exception,
        code: SessionErrorCode = SessionErrorCode.INTERNAL_ERROR,
        session_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> "SessionError":
        """Create SessionError from generic exception"""
        return cls(
            code=code,
            message=str(error),
            details={"exception_type": type(error).__name__},
            recoverable=True,
            session_id=session_id,
            execution_id=execution_id,
        )


class SessionErrorHandler:
    """Session error handler with retry logic"""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
    ):
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._exponential_backoff = exponential_backoff

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        if self._exponential_backoff:
            return self._retry_delay * (2 ** attempt)
        return self._retry_delay

    async def handle_llm_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> SessionError:
        """Handle LLM errors and classify them"""
        context = context or {}
        error_str = str(error).lower()

        # Log the error
        logger.error(
            f"LLM error occurred: {error}",
            extra={"context": context, "error_type": type(error).__name__},
        )

        if "timeout" in error_str or "timed out" in error_str:
            return SessionError(
                code=SessionErrorCode.LLM_TIMEOUT,
                message="LLM 回應超時，請稍後重試",
                details={"original_error": str(error), **context},
                recoverable=True,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )
        elif "rate" in error_str and "limit" in error_str:
            return SessionError(
                code=SessionErrorCode.LLM_RATE_LIMIT,
                message="API 請求過於頻繁，請稍後重試",
                details={"original_error": str(error), **context},
                recoverable=True,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )
        elif "content_filter" in error_str or "content filter" in error_str:
            return SessionError(
                code=SessionErrorCode.LLM_CONTENT_FILTER,
                message="訊息內容被安全過濾器攔截",
                details={"original_error": str(error), **context},
                recoverable=False,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )
        elif "token" in error_str and ("limit" in error_str or "exceed" in error_str):
            return SessionError(
                code=SessionErrorCode.LLM_TOKEN_LIMIT,
                message="訊息過長，超出 Token 限制",
                details={"original_error": str(error), **context},
                recoverable=False,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )
        else:
            return SessionError(
                code=SessionErrorCode.LLM_API_ERROR,
                message="LLM 服務暫時不可用",
                details={"original_error": str(error), **context},
                recoverable=True,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )

    async def handle_tool_error(
        self,
        error: Exception,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SessionError:
        """Handle tool execution errors"""
        context = context or {}
        error_str = str(error).lower()

        # Log the error
        logger.error(
            f"Tool error occurred: {tool_name} - {error}",
            extra={"tool_name": tool_name, "context": context},
        )

        if "timeout" in error_str or "timed out" in error_str:
            return SessionError(
                code=SessionErrorCode.TOOL_TIMEOUT,
                message=f"工具 {tool_name} 執行超時",
                details={"tool_name": tool_name, "original_error": str(error), **context},
                recoverable=True,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )
        elif "permission" in error_str or "denied" in error_str or "forbidden" in error_str:
            return SessionError(
                code=SessionErrorCode.TOOL_PERMISSION_DENIED,
                message=f"無權限執行工具 {tool_name}",
                details={"tool_name": tool_name, "original_error": str(error), **context},
                recoverable=False,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )
        elif "not found" in error_str or "unknown" in error_str:
            return SessionError(
                code=SessionErrorCode.TOOL_NOT_FOUND,
                message=f"工具 {tool_name} 不存在",
                details={"tool_name": tool_name, "original_error": str(error), **context},
                recoverable=False,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )
        elif "validation" in error_str or "invalid" in error_str:
            return SessionError(
                code=SessionErrorCode.TOOL_VALIDATION_ERROR,
                message=f"工具 {tool_name} 參數驗證失敗",
                details={"tool_name": tool_name, "original_error": str(error), **context},
                recoverable=False,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )
        else:
            return SessionError(
                code=SessionErrorCode.TOOL_EXECUTION_ERROR,
                message=f"工具 {tool_name} 執行失敗",
                details={"tool_name": tool_name, "original_error": str(error), **context},
                recoverable=True,
                session_id=context.get("session_id"),
                execution_id=context.get("execution_id"),
            )

    async def with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        error_handler: Callable[[Exception, Dict[str, Any]], Awaitable[SessionError]],
        context: Optional[Dict[str, Any]] = None,
        on_retry: Optional[Callable[[int, Exception], Awaitable[None]]] = None,
    ) -> T:
        """Execute operation with retry logic"""
        context = context or {}
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries):
            try:
                return await operation()
            except SessionError:
                # Re-raise SessionError directly
                raise
            except Exception as e:
                last_error = e
                session_error = await error_handler(e, context)

                # Non-recoverable errors should not be retried
                if not session_error.recoverable:
                    logger.warning(
                        f"Non-recoverable error, not retrying: {session_error.code}",
                        extra={"error": str(e), "context": context},
                    )
                    raise session_error

                # Last attempt
                if attempt >= self._max_retries - 1:
                    logger.error(
                        f"All retry attempts failed after {self._max_retries} attempts",
                        extra={"error": str(e), "context": context},
                    )
                    raise session_error

                # Calculate delay and retry
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{self._max_retries}), "
                    f"retrying in {delay:.1f}s...",
                    extra={"error": str(e), "context": context, "delay": delay},
                )

                # Call on_retry callback if provided
                if on_retry:
                    await on_retry(attempt, e)

                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        if last_error:
            raise await error_handler(last_error, context)
        raise SessionError(
            code=SessionErrorCode.INTERNAL_ERROR,
            message="Unexpected error in retry logic",
        )

    async def safe_execute(
        self,
        operation: Callable[[], Awaitable[T]],
        default: Optional[T] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[T]:
        """Execute operation safely, returning default on error"""
        context = context or {}
        try:
            return await operation()
        except Exception as e:
            logger.error(
                f"Safe execute caught error: {e}",
                extra={"context": context, "error_type": type(e).__name__},
            )
            return default


def create_error_handler(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    exponential_backoff: bool = True,
) -> SessionErrorHandler:
    """Factory function for SessionErrorHandler"""
    return SessionErrorHandler(
        max_retries=max_retries,
        retry_delay=retry_delay,
        exponential_backoff=exponential_backoff,
    )
