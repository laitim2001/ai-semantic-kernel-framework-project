"""
Retry policy implementation with exponential backoff
"""
import random
import logging
from datetime import datetime
from typing import Optional
import traceback

from .error_schemas import (
    RetryConfig,
    ErrorContext,
    ErrorType,
    ErrorSeverity,
    classify_error,
    is_retryable_error,
    get_error_severity,
)

logger = logging.getLogger(__name__)


class RetryPolicy:
    """
    重試策略類

    實現指數退避算法和錯誤分類
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        初始化重試策略

        Args:
            config: 重試配置,如果未提供則使用默認值
        """
        self.config = config or RetryConfig()

    def calculate_backoff(self, attempt: int) -> int:
        """
        計算指數退避延遲時間

        Formula: delay = min(base_delay * (exponential_base ** attempt), max_delay)
        With jitter: delay * (0.5 + random() * 0.5)

        Args:
            attempt: 重試次數 (從 0 開始)

        Returns:
            int: 延遲時間 (毫秒)
        """
        # Base exponential calculation
        delay = min(
            self.config.base_delay_ms * (self.config.exponential_base ** attempt),
            self.config.max_delay_ms
        )

        # Add jitter to prevent thundering herd problem
        if self.config.jitter:
            jitter_factor = 0.5 + random.random() * 0.5
            delay = delay * jitter_factor

        return int(delay)

    def should_retry(
        self,
        exception: Exception,
        current_attempt: int
    ) -> tuple[bool, ErrorType]:
        """
        判斷是否應該重試

        Args:
            exception: 捕獲的異常
            current_attempt: 當前嘗試次數 (從 0 開始)

        Returns:
            tuple[bool, ErrorType]: (是否應該重試, 錯誤類型)
        """
        # Classify error
        error_type = classify_error(exception)

        # Check if error is retryable
        if not is_retryable_error(error_type):
            logger.info(
                f"Error {error_type} is not retryable: {exception}"
            )
            return False, error_type

        # Check if max retries exceeded
        if current_attempt >= self.config.max_retries:
            logger.warning(
                f"Max retries ({self.config.max_retries}) exceeded for {error_type}: {exception}"
            )
            return False, error_type

        logger.info(
            f"Error {error_type} is retryable, attempt {current_attempt + 1}/{self.config.max_retries}"
        )
        return True, error_type

    def create_error_context(
        self,
        exception: Exception,
        attempt: int,
        retry_delay_ms: Optional[int] = None,
        context_data: Optional[dict] = None
    ) -> ErrorContext:
        """
        創建錯誤上下文

        Args:
            exception: 異常對象
            attempt: 嘗試次數
            retry_delay_ms: 重試延遲 (毫秒)
            context_data: 額外上下文數據

        Returns:
            ErrorContext: 錯誤上下文對象
        """
        error_type = classify_error(exception)
        is_retryable = is_retryable_error(error_type)
        severity = get_error_severity(error_type)

        # Get stack trace
        stack_trace = "".join(traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__
        ))

        # Get error code if available
        error_code = getattr(exception, "code", None)
        if error_code is None:
            error_code = getattr(exception, "status_code", None)

        return ErrorContext(
            error_type=error_type,
            error_message=str(exception),
            error_code=str(error_code) if error_code else None,
            severity=severity,
            stack_trace=stack_trace,
            timestamp=datetime.utcnow(),
            attempt=attempt,
            retry_delay_ms=retry_delay_ms,
            is_retryable=is_retryable,
            context_data=context_data or {}
        )

    def execute_with_retry(
        self,
        func,
        *args,
        context_data: Optional[dict] = None,
        **kwargs
    ):
        """
        執行函數並在失敗時自動重試

        Args:
            func: 要執行的函數
            *args: 函數位置參數
            context_data: 錯誤上下文數據
            **kwargs: 函數關鍵字參數

        Returns:
            函數執行結果

        Raises:
            最後一次嘗試的異常
        """
        last_exception = None
        error_history = []

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"Executing attempt {attempt + 1}/{self.config.max_retries + 1}")
                result = func(*args, **kwargs)
                logger.info(f"Function succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_exception = e

                # Create error context
                error_ctx = self.create_error_context(
                    e,
                    attempt,
                    context_data=context_data
                )
                error_history.append(error_ctx)

                # Determine if we should retry
                should_retry, error_type = self.should_retry(e, attempt)

                if not should_retry:
                    logger.error(
                        f"Function failed with non-retryable error {error_type} "
                        f"on attempt {attempt + 1}: {e}"
                    )
                    raise

                # Calculate backoff delay
                delay_ms = self.calculate_backoff(attempt)
                error_ctx.retry_delay_ms = delay_ms

                logger.warning(
                    f"Function failed on attempt {attempt + 1} with {error_type}, "
                    f"retrying in {delay_ms}ms: {e}"
                )

                # Wait before retry (in real implementation, use async sleep)
                import time
                time.sleep(delay_ms / 1000.0)

        # All retries exhausted
        logger.error(
            f"Function failed after {self.config.max_retries + 1} attempts. "
            f"Error history: {len(error_history)} errors"
        )
        raise last_exception


# Default retry policy instance
default_retry_policy = RetryPolicy()


def with_retry(
    max_retries: int = 3,
    base_delay_ms: int = 1000,
    max_delay_ms: int = 30000,
    jitter: bool = True
):
    """
    重試裝飾器

    Args:
        max_retries: 最大重試次數
        base_delay_ms: 基礎延遲
        max_delay_ms: 最大延遲
        jitter: 是否添加抖動

    Example:
        @with_retry(max_retries=3, base_delay_ms=1000)
        def fetch_data():
            # ... may fail with network error
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay_ms=base_delay_ms,
                max_delay_ms=max_delay_ms,
                jitter=jitter
            )
            policy = RetryPolicy(config)
            return policy.execute_with_retry(func, *args, **kwargs)

        return wrapper

    return decorator
