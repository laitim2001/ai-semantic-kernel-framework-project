"""
Unit tests for Session Error Handler (S47-2)

Tests:
- SessionErrorCode enumeration
- SessionError exception class
- SessionErrorHandler error handling and retry logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
import asyncio

from src.domain.sessions.error_handler import (
    SessionErrorCode,
    SessionError,
    SessionErrorHandler,
    ERROR_CODE_TO_STATUS,
    create_error_handler,
)


# =============================================================================
# SessionErrorCode Tests
# =============================================================================

class TestSessionErrorCode:
    """Test SessionErrorCode enumeration"""

    def test_session_error_codes(self):
        """Test session-related error codes exist"""
        assert SessionErrorCode.SESSION_NOT_FOUND.value == "SESSION_NOT_FOUND"
        assert SessionErrorCode.SESSION_NOT_ACTIVE.value == "SESSION_NOT_ACTIVE"
        assert SessionErrorCode.SESSION_EXPIRED.value == "SESSION_EXPIRED"

    def test_agent_error_codes(self):
        """Test agent-related error codes exist"""
        assert SessionErrorCode.AGENT_NOT_FOUND.value == "AGENT_NOT_FOUND"
        assert SessionErrorCode.AGENT_CONFIG_ERROR.value == "AGENT_CONFIG_ERROR"

    def test_llm_error_codes(self):
        """Test LLM-related error codes exist"""
        assert SessionErrorCode.LLM_TIMEOUT.value == "LLM_TIMEOUT"
        assert SessionErrorCode.LLM_RATE_LIMIT.value == "LLM_RATE_LIMIT"
        assert SessionErrorCode.LLM_API_ERROR.value == "LLM_API_ERROR"
        assert SessionErrorCode.LLM_CONTENT_FILTER.value == "LLM_CONTENT_FILTER"

    def test_tool_error_codes(self):
        """Test tool-related error codes exist"""
        assert SessionErrorCode.TOOL_NOT_FOUND.value == "TOOL_NOT_FOUND"
        assert SessionErrorCode.TOOL_EXECUTION_ERROR.value == "TOOL_EXECUTION_ERROR"
        assert SessionErrorCode.TOOL_TIMEOUT.value == "TOOL_TIMEOUT"
        assert SessionErrorCode.TOOL_PERMISSION_DENIED.value == "TOOL_PERMISSION_DENIED"

    def test_all_codes_have_http_status(self):
        """Test all error codes have HTTP status mapping"""
        for code in SessionErrorCode:
            assert code in ERROR_CODE_TO_STATUS, f"Missing HTTP status for {code}"


# =============================================================================
# SessionError Tests
# =============================================================================

class TestSessionError:
    """Test SessionError exception class"""

    def test_create_error(self):
        """Test creating session error"""
        error = SessionError(
            code=SessionErrorCode.SESSION_NOT_FOUND,
            message="Session not found",
            details={"session_id": "test-123"},
            recoverable=False,
        )

        assert error.code == SessionErrorCode.SESSION_NOT_FOUND
        assert error.message == "Session not found"
        assert error.details == {"session_id": "test-123"}
        assert error.recoverable is False
        assert error.timestamp is not None

    def test_error_http_status(self):
        """Test HTTP status property"""
        error = SessionError(
            code=SessionErrorCode.SESSION_NOT_FOUND,
            message="Not found",
        )
        assert error.http_status == 404

        error2 = SessionError(
            code=SessionErrorCode.LLM_RATE_LIMIT,
            message="Rate limited",
        )
        assert error2.http_status == 429

    def test_error_to_dict(self):
        """Test converting error to dictionary"""
        error = SessionError(
            code=SessionErrorCode.LLM_TIMEOUT,
            message="Timeout occurred",
            details={"timeout": 30},
            recoverable=True,
            session_id="session-123",
            execution_id="exec-456",
        )

        data = error.to_dict()

        assert data["error_code"] == "LLM_TIMEOUT"
        assert data["message"] == "Timeout occurred"
        assert data["details"] == {"timeout": 30}
        assert data["recoverable"] is True
        assert data["session_id"] == "session-123"
        assert data["execution_id"] == "exec-456"
        assert "timestamp" in data

    def test_error_to_event(self):
        """Test converting error to execution event"""
        error = SessionError(
            code=SessionErrorCode.TOOL_EXECUTION_ERROR,
            message="Tool failed",
            session_id="session-123",
            execution_id="exec-456",
        )

        event = error.to_event()

        assert event.session_id == "session-123"
        assert event.execution_id == "exec-456"
        assert event.error == "Tool failed"
        assert event.error_code == "TOOL_EXECUTION_ERROR"

    def test_from_exception(self):
        """Test creating error from generic exception"""
        original = ValueError("Something went wrong")
        error = SessionError.from_exception(
            original,
            code=SessionErrorCode.INTERNAL_ERROR,
            session_id="session-123",
        )

        assert error.code == SessionErrorCode.INTERNAL_ERROR
        assert "Something went wrong" in error.message
        assert error.details["exception_type"] == "ValueError"
        assert error.session_id == "session-123"

    def test_error_is_exception(self):
        """Test SessionError is an exception"""
        error = SessionError(
            code=SessionErrorCode.SESSION_NOT_FOUND,
            message="Not found",
        )

        with pytest.raises(SessionError) as exc_info:
            raise error

        assert exc_info.value.code == SessionErrorCode.SESSION_NOT_FOUND


# =============================================================================
# SessionErrorHandler Tests
# =============================================================================

class TestSessionErrorHandler:
    """Test SessionErrorHandler class"""

    @pytest.fixture
    def handler(self):
        """Create error handler"""
        return SessionErrorHandler(
            max_retries=3,
            retry_delay=0.1,
            exponential_backoff=True,
        )

    @pytest.mark.asyncio
    async def test_handle_llm_timeout(self, handler):
        """Test handling LLM timeout error"""
        error = TimeoutError("Request timed out")
        result = await handler.handle_llm_error(error, {"session_id": "test"})

        assert result.code == SessionErrorCode.LLM_TIMEOUT
        assert result.recoverable is True
        assert "超時" in result.message

    @pytest.mark.asyncio
    async def test_handle_llm_rate_limit(self, handler):
        """Test handling LLM rate limit error"""
        error = Exception("Rate limit exceeded")
        result = await handler.handle_llm_error(error, {})

        assert result.code == SessionErrorCode.LLM_RATE_LIMIT
        assert result.recoverable is True

    @pytest.mark.asyncio
    async def test_handle_llm_content_filter(self, handler):
        """Test handling LLM content filter error"""
        error = Exception("Content filter triggered")
        result = await handler.handle_llm_error(error, {})

        assert result.code == SessionErrorCode.LLM_CONTENT_FILTER
        assert result.recoverable is False

    @pytest.mark.asyncio
    async def test_handle_llm_generic_error(self, handler):
        """Test handling generic LLM error"""
        error = Exception("Unknown API error")
        result = await handler.handle_llm_error(error, {})

        assert result.code == SessionErrorCode.LLM_API_ERROR
        assert result.recoverable is True

    @pytest.mark.asyncio
    async def test_handle_tool_timeout(self, handler):
        """Test handling tool timeout error"""
        error = TimeoutError("Tool execution timed out")
        result = await handler.handle_tool_error(error, "calculator", {})

        assert result.code == SessionErrorCode.TOOL_TIMEOUT
        assert result.recoverable is True
        assert "calculator" in result.message

    @pytest.mark.asyncio
    async def test_handle_tool_permission_denied(self, handler):
        """Test handling tool permission denied error"""
        error = PermissionError("Access denied")
        result = await handler.handle_tool_error(error, "file_write", {})

        assert result.code == SessionErrorCode.TOOL_PERMISSION_DENIED
        assert result.recoverable is False

    @pytest.mark.asyncio
    async def test_handle_tool_not_found(self, handler):
        """Test handling tool not found error"""
        error = Exception("Tool not found")
        result = await handler.handle_tool_error(error, "unknown_tool", {})

        assert result.code == SessionErrorCode.TOOL_NOT_FOUND
        assert result.recoverable is False

    @pytest.mark.asyncio
    async def test_handle_tool_validation_error(self, handler):
        """Test handling tool validation error"""
        error = ValueError("Invalid parameter")
        result = await handler.handle_tool_error(error, "calculator", {})

        assert result.code == SessionErrorCode.TOOL_VALIDATION_ERROR
        assert result.recoverable is False

    @pytest.mark.asyncio
    async def test_handle_tool_execution_error(self, handler):
        """Test handling generic tool error"""
        error = RuntimeError("Execution failed")
        result = await handler.handle_tool_error(error, "some_tool", {})

        assert result.code == SessionErrorCode.TOOL_EXECUTION_ERROR
        assert result.recoverable is True


# =============================================================================
# Retry Logic Tests
# =============================================================================

class TestRetryLogic:
    """Test retry logic"""

    @pytest.fixture
    def handler(self):
        """Create handler with fast retry for testing"""
        return SessionErrorHandler(
            max_retries=3,
            retry_delay=0.01,  # Fast for testing
            exponential_backoff=False,
        )

    @pytest.mark.asyncio
    async def test_with_retry_success_first_attempt(self, handler):
        """Test successful operation on first attempt"""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await handler.with_retry(
            operation,
            handler.handle_llm_error,
            {},
        )

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_with_retry_success_after_failures(self, handler):
        """Test successful operation after some failures"""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Timeout")
            return "success"

        result = await handler.with_retry(
            operation,
            handler.handle_llm_error,
            {},
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_with_retry_all_attempts_fail(self, handler):
        """Test all retry attempts failing"""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always timeout")

        with pytest.raises(SessionError) as exc_info:
            await handler.with_retry(
                operation,
                handler.handle_llm_error,
                {},
            )

        assert exc_info.value.code == SessionErrorCode.LLM_TIMEOUT
        assert call_count == 3  # max_retries

    @pytest.mark.asyncio
    async def test_with_retry_non_recoverable_no_retry(self, handler):
        """Test non-recoverable error does not retry"""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise Exception("Content filter blocked")

        with pytest.raises(SessionError) as exc_info:
            await handler.with_retry(
                operation,
                handler.handle_llm_error,
                {},
            )

        assert exc_info.value.code == SessionErrorCode.LLM_CONTENT_FILTER
        assert call_count == 1  # No retry for non-recoverable

    @pytest.mark.asyncio
    async def test_with_retry_callback(self, handler):
        """Test on_retry callback is called"""
        retry_attempts = []

        async def on_retry(attempt, error):
            retry_attempts.append(attempt)

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Timeout")
            return "success"

        await handler.with_retry(
            operation,
            handler.handle_llm_error,
            {},
            on_retry=on_retry,
        )

        assert retry_attempts == [0, 1]

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        handler = SessionErrorHandler(
            max_retries=3,
            retry_delay=1.0,
            exponential_backoff=True,
        )

        assert handler._calculate_delay(0) == 1.0
        assert handler._calculate_delay(1) == 2.0
        assert handler._calculate_delay(2) == 4.0

    @pytest.mark.asyncio
    async def test_linear_backoff(self):
        """Test linear backoff calculation"""
        handler = SessionErrorHandler(
            max_retries=3,
            retry_delay=1.0,
            exponential_backoff=False,
        )

        assert handler._calculate_delay(0) == 1.0
        assert handler._calculate_delay(1) == 1.0
        assert handler._calculate_delay(2) == 1.0


# =============================================================================
# Safe Execute Tests
# =============================================================================

class TestSafeExecute:
    """Test safe execute method"""

    @pytest.fixture
    def handler(self):
        """Create error handler"""
        return SessionErrorHandler()

    @pytest.mark.asyncio
    async def test_safe_execute_success(self, handler):
        """Test safe execute with successful operation"""
        async def operation():
            return "result"

        result = await handler.safe_execute(operation)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_safe_execute_failure_returns_default(self, handler):
        """Test safe execute returns default on failure"""
        async def operation():
            raise ValueError("Error")

        result = await handler.safe_execute(operation, default="default")
        assert result == "default"

    @pytest.mark.asyncio
    async def test_safe_execute_failure_returns_none(self, handler):
        """Test safe execute returns None on failure"""
        async def operation():
            raise ValueError("Error")

        result = await handler.safe_execute(operation)
        assert result is None


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Test factory function"""

    def test_create_error_handler_default(self):
        """Test creating handler with defaults"""
        handler = create_error_handler()
        assert handler._max_retries == 3
        assert handler._retry_delay == 1.0
        assert handler._exponential_backoff is True

    def test_create_error_handler_custom(self):
        """Test creating handler with custom values"""
        handler = create_error_handler(
            max_retries=5,
            retry_delay=0.5,
            exponential_backoff=False,
        )
        assert handler._max_retries == 5
        assert handler._retry_delay == 0.5
        assert handler._exponential_backoff is False
