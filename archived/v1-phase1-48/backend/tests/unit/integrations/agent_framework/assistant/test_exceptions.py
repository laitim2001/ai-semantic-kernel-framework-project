"""
Unit tests for Code Interpreter exceptions.

Sprint 37: Phase 8 - Code Interpreter Integration
"""

import pytest

from src.integrations.agent_framework.assistant.exceptions import (
    AssistantError,
    ExecutionTimeoutError,
    AssistantNotFoundError,
    CodeExecutionError,
    AssistantCreationError,
    ThreadCreationError,
    RunError,
    ConfigurationError,
    RateLimitError,
)


class TestAssistantError:
    """Tests for base AssistantError exception."""

    def test_basic_error(self):
        """Test creating a basic error."""
        error = AssistantError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details is None

    def test_error_with_details(self):
        """Test creating an error with details."""
        error = AssistantError(
            "Operation failed",
            details={"code": 500, "reason": "Internal error"}
        )
        assert "Operation failed" in str(error)
        assert "Details:" in str(error)
        assert error.details["code"] == 500

    def test_error_is_exception(self):
        """Test that AssistantError is an Exception."""
        with pytest.raises(AssistantError):
            raise AssistantError("Test error")


class TestExecutionTimeoutError:
    """Tests for ExecutionTimeoutError exception."""

    def test_default_timeout_error(self):
        """Test default timeout error."""
        error = ExecutionTimeoutError()
        assert "timed out" in str(error).lower()
        assert error.timeout == 60
        assert error.elapsed == 0

    def test_custom_timeout_error(self):
        """Test custom timeout error."""
        error = ExecutionTimeoutError(
            message="Code execution exceeded time limit",
            timeout=120,
            elapsed=125.5,
        )
        assert error.timeout == 120
        assert error.elapsed == 125.5
        assert "exceeded" in str(error)

    def test_timeout_error_inheritance(self):
        """Test that ExecutionTimeoutError inherits from AssistantError."""
        assert issubclass(ExecutionTimeoutError, AssistantError)


class TestAssistantNotFoundError:
    """Tests for AssistantNotFoundError exception."""

    def test_not_found_error(self):
        """Test assistant not found error."""
        error = AssistantNotFoundError("asst_abc123")
        assert error.assistant_id == "asst_abc123"
        assert "asst_abc123" in str(error)
        assert "not found" in str(error).lower()

    def test_not_found_error_inheritance(self):
        """Test that AssistantNotFoundError inherits from AssistantError."""
        assert issubclass(AssistantNotFoundError, AssistantError)


class TestCodeExecutionError:
    """Tests for CodeExecutionError exception."""

    def test_basic_execution_error(self):
        """Test basic code execution error."""
        error = CodeExecutionError("Syntax error in code")
        assert str(error) == "Syntax error in code"

    def test_execution_error_with_code(self):
        """Test execution error with code snippet."""
        error = CodeExecutionError(
            message="NameError: name 'x' is not defined",
            code="print(x)",
            error_type="NameError",
        )
        assert error.code == "print(x)"
        assert error.error_type == "NameError"

    def test_execution_error_inheritance(self):
        """Test that CodeExecutionError inherits from AssistantError."""
        assert issubclass(CodeExecutionError, AssistantError)


class TestAssistantCreationError:
    """Tests for AssistantCreationError exception."""

    def test_default_creation_error(self):
        """Test default creation error message."""
        error = AssistantCreationError()
        assert "create assistant" in str(error).lower()

    def test_custom_creation_error(self):
        """Test custom creation error message."""
        error = AssistantCreationError("Quota exceeded")
        assert str(error) == "Quota exceeded"

    def test_creation_error_inheritance(self):
        """Test that AssistantCreationError inherits from AssistantError."""
        assert issubclass(AssistantCreationError, AssistantError)


class TestThreadCreationError:
    """Tests for ThreadCreationError exception."""

    def test_default_thread_error(self):
        """Test default thread creation error message."""
        error = ThreadCreationError()
        assert "create thread" in str(error).lower()

    def test_custom_thread_error(self):
        """Test custom thread creation error message."""
        error = ThreadCreationError("Thread limit reached")
        assert str(error) == "Thread limit reached"

    def test_thread_error_inheritance(self):
        """Test that ThreadCreationError inherits from AssistantError."""
        assert issubclass(ThreadCreationError, AssistantError)


class TestRunError:
    """Tests for RunError exception."""

    def test_basic_run_error(self):
        """Test basic run error."""
        error = RunError("Run failed unexpectedly")
        assert str(error) == "Run failed unexpectedly"

    def test_run_error_with_details(self):
        """Test run error with run ID and status."""
        error = RunError(
            message="Run terminated with error",
            run_id="run_xyz123",
            run_status="failed",
        )
        assert error.run_id == "run_xyz123"
        assert error.run_status == "failed"

    def test_run_error_inheritance(self):
        """Test that RunError inherits from AssistantError."""
        assert issubclass(RunError, AssistantError)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_default_config_error(self):
        """Test default configuration error message."""
        error = ConfigurationError()
        assert "configuration" in str(error).lower()

    def test_custom_config_error(self):
        """Test custom configuration error message."""
        error = ConfigurationError("AZURE_OPENAI_API_KEY is required")
        assert "AZURE_OPENAI_API_KEY" in str(error)

    def test_config_error_inheritance(self):
        """Test that ConfigurationError inherits from AssistantError."""
        assert issubclass(ConfigurationError, AssistantError)


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_default_rate_limit_error(self):
        """Test default rate limit error message."""
        error = RateLimitError()
        assert "rate limit" in str(error).lower()
        assert error.retry_after is None

    def test_rate_limit_error_with_retry(self):
        """Test rate limit error with retry-after."""
        error = RateLimitError(
            message="Too many requests",
            retry_after=30,
        )
        assert error.retry_after == 30
        assert "Too many requests" in str(error)

    def test_rate_limit_error_inheritance(self):
        """Test that RateLimitError inherits from AssistantError."""
        assert issubclass(RateLimitError, AssistantError)


class TestExceptionHierarchy:
    """Tests for exception hierarchy and catching."""

    def test_catch_all_as_assistant_error(self):
        """Test that all exceptions can be caught as AssistantError."""
        exceptions = [
            ExecutionTimeoutError(),
            AssistantNotFoundError("test"),
            CodeExecutionError("test"),
            AssistantCreationError(),
            ThreadCreationError(),
            RunError("test"),
            ConfigurationError(),
            RateLimitError(),
        ]

        for exc in exceptions:
            try:
                raise exc
            except AssistantError as e:
                assert e is exc
            except Exception:
                pytest.fail(f"{type(exc).__name__} not caught as AssistantError")

    def test_specific_exception_before_base(self):
        """Test that specific exceptions are caught before base."""
        try:
            raise ExecutionTimeoutError(timeout=30, elapsed=35)
        except ExecutionTimeoutError as e:
            assert e.timeout == 30
            assert e.elapsed == 35
        except AssistantError:
            pytest.fail("Should have caught ExecutionTimeoutError")
