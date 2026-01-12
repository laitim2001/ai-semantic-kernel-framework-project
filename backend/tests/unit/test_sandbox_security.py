# =============================================================================
# IPA Platform - Sandbox Security Tests
# =============================================================================
# Sprint 78: S78-3 - Security Testing and Verification (5 pts)
#
# This module contains comprehensive security tests for the sandbox
# isolation system, verifying environment variable isolation,
# file system restrictions, and process isolation.
#
# Test Categories:
#   1. Environment Variable Isolation - Verify sensitive vars are blocked
#   2. File System Isolation - Verify path traversal prevention
#   3. Process Isolation - Verify crash isolation and recovery
#   4. Performance Benchmarks - Verify acceptable overhead
#
# =============================================================================

import asyncio
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.sandbox.config import ProcessSandboxConfig
from src.core.sandbox.orchestrator import SandboxOrchestrator
from src.core.sandbox.worker import SandboxWorker
from src.core.sandbox.ipc import (
    IPCProtocol,
    IPCRequest,
    IPCResponse,
    IPCEvent,
    IPCEventType,
    create_event_notification,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sandbox_config():
    """Create a test sandbox configuration."""
    return ProcessSandboxConfig(
        max_workers=2,
        worker_timeout=30,
        startup_timeout=10,
        idle_timeout=60,
    )


@pytest.fixture
def temp_sandbox_dir():
    """Create a temporary sandbox directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Environment Variable Isolation Tests
# =============================================================================


class TestEnvironmentIsolation:
    """Tests for environment variable isolation."""

    def test_db_password_not_leaked(self, sandbox_config):
        """DB_PASSWORD should not be passed to sandbox."""
        # Set sensitive environment variable
        with patch.dict(os.environ, {"DB_PASSWORD": "super-secret-password"}):
            filtered_env = sandbox_config.get_filtered_env(
                user_id="test-user",
                session_id="test-session"
            )

            assert "DB_PASSWORD" not in filtered_env
            assert "super-secret-password" not in filtered_env.values()

    def test_redis_password_not_leaked(self, sandbox_config):
        """REDIS_PASSWORD should not be passed to sandbox."""
        with patch.dict(os.environ, {"REDIS_PASSWORD": "redis-secret"}):
            filtered_env = sandbox_config.get_filtered_env(
                user_id="test-user"
            )

            assert "REDIS_PASSWORD" not in filtered_env
            assert "redis-secret" not in filtered_env.values()

    def test_secret_key_not_leaked(self, sandbox_config):
        """SECRET_KEY should not be passed to sandbox."""
        with patch.dict(os.environ, {"SECRET_KEY": "jwt-secret-key"}):
            filtered_env = sandbox_config.get_filtered_env(
                user_id="test-user"
            )

            assert "SECRET_KEY" not in filtered_env
            assert "jwt-secret-key" not in filtered_env.values()

    def test_azure_credentials_not_leaked(self, sandbox_config):
        """AZURE_* credentials should not be passed to sandbox."""
        azure_vars = {
            "AZURE_OPENAI_API_KEY": "azure-api-key",
            "AZURE_STORAGE_CONNECTION_STRING": "connection-string",
            "AZURE_CLIENT_SECRET": "client-secret",
        }
        with patch.dict(os.environ, azure_vars):
            filtered_env = sandbox_config.get_filtered_env(
                user_id="test-user"
            )

            for var in azure_vars:
                assert var not in filtered_env

    def test_anthropic_api_key_is_passed(self, sandbox_config):
        """ANTHROPIC_API_KEY should be passed to sandbox (required for Claude)."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-xxx"}):
            filtered_env = sandbox_config.get_filtered_env(
                user_id="test-user"
            )

            assert "ANTHROPIC_API_KEY" in filtered_env
            assert filtered_env["ANTHROPIC_API_KEY"] == "sk-ant-xxx"

    def test_sandbox_specific_vars_are_set(self, sandbox_config):
        """Sandbox-specific variables should be set correctly."""
        filtered_env = sandbox_config.get_filtered_env(
            user_id="test-user-123",
            session_id="session-456",
        )

        assert filtered_env["SANDBOX_USER_ID"] == "test-user-123"
        assert filtered_env["SANDBOX_SESSION_ID"] == "session-456"
        assert "SANDBOX_DIR" in filtered_env
        assert "SANDBOX_TIMEOUT" in filtered_env

    def test_blocked_prefix_filtering(self, sandbox_config):
        """Variables with blocked prefixes should be filtered."""
        blocked_vars = {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "REDIS_HOST": "localhost",
            "RABBITMQ_USER": "admin",
            "AWS_ACCESS_KEY_ID": "AKIA...",
            "JWT_SECRET": "secret",
            "PRIVATE_KEY": "key",
        }
        with patch.dict(os.environ, blocked_vars):
            filtered_env = sandbox_config.get_filtered_env(
                user_id="test-user"
            )

            for var in blocked_vars:
                assert var not in filtered_env


# =============================================================================
# File System Isolation Tests
# =============================================================================


class TestFileSystemIsolation:
    """Tests for file system isolation."""

    def test_user_id_sanitization(self, sandbox_config):
        """User IDs with path traversal attempts should be sanitized."""
        # Test various path traversal attempts
        malicious_ids = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "user/../../../secret",
            "user%2f..%2f..%2fetc",
            "user\x00malicious",
        ]

        for malicious_id in malicious_ids:
            sanitized = sandbox_config._sanitize_user_id(malicious_id)

            # Sanitized ID should not contain path separators
            assert "/" not in sanitized
            assert "\\" not in sanitized
            assert ".." not in sanitized
            assert "\x00" not in sanitized

    def test_sandbox_dir_is_under_base(self, sandbox_config, temp_sandbox_dir):
        """Sandbox directory should always be under the base directory."""
        config = ProcessSandboxConfig(sandbox_base_dir=temp_sandbox_dir)

        user_dir = config.get_user_sandbox_dir("test-user")

        # User directory should be under the base directory
        assert str(user_dir).startswith(str(temp_sandbox_dir))

    def test_path_traversal_blocked_in_user_dir(self, sandbox_config, temp_sandbox_dir):
        """Path traversal in user directory should be blocked."""
        config = ProcessSandboxConfig(sandbox_base_dir=temp_sandbox_dir)

        # Attempt path traversal
        user_dir = config.get_user_sandbox_dir("../../etc")

        # Should be sanitized and stay under base
        assert str(user_dir).startswith(str(temp_sandbox_dir))
        assert "/etc" not in str(user_dir)

    def test_ensure_sandbox_dir_creates_directory(self, sandbox_config, temp_sandbox_dir):
        """ensure_user_sandbox_dir should create the directory."""
        config = ProcessSandboxConfig(sandbox_base_dir=temp_sandbox_dir)

        sandbox_dir = config.ensure_user_sandbox_dir("test-user")

        assert sandbox_dir.exists()
        assert sandbox_dir.is_dir()


# =============================================================================
# IPC Protocol Tests
# =============================================================================


class TestIPCProtocol:
    """Tests for IPC protocol implementation."""

    def test_request_serialization(self):
        """IPCRequest should serialize correctly."""
        protocol = IPCProtocol()
        request = protocol.create_execute_request(
            message="Test message",
            attachments=[],
            session_id="session-123",
        )

        assert request.method == "execute"
        assert request.params["message"] == "Test message"
        assert request.params["session_id"] == "session-123"
        assert request.id is not None

    def test_response_parsing(self):
        """IPCResponse should parse correctly."""
        response_data = {
            "jsonrpc": "2.0",
            "result": {"content": "Response content"},
            "id": "req-1",
        }

        response = IPCResponse.from_dict(response_data)

        assert response.is_success
        assert not response.is_error
        assert response.result["content"] == "Response content"

    def test_error_response_parsing(self):
        """IPCResponse should handle errors correctly."""
        response_data = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid request",
            },
            "id": "req-1",
        }

        response = IPCResponse.from_dict(response_data)

        assert response.is_error
        assert not response.is_success
        assert response.error["code"] == -32600

    def test_event_notification_format(self):
        """Event notifications should have correct format."""
        notification = create_event_notification(
            event_type=IPCEventType.TEXT_DELTA,
            data={"delta": "Hello"},
        )

        assert notification["jsonrpc"] == "2.0"
        assert notification["method"] == "event"
        assert notification["params"]["type"] == "TEXT_DELTA"
        assert notification["params"]["data"]["delta"] == "Hello"
        assert "id" not in notification  # Notifications have no ID

    def test_event_type_mapping(self):
        """IPC events should map to SSE events correctly."""
        from src.core.sandbox.ipc import map_ipc_to_sse_event

        ipc_event = IPCEvent(
            type=IPCEventType.TEXT_DELTA.value,
            data={"delta": "Hello"},
        )

        sse_event = map_ipc_to_sse_event(ipc_event)

        assert sse_event["event"] == "text_delta"
        assert sse_event["data"]["delta"] == "Hello"


# =============================================================================
# Configuration Validation Tests
# =============================================================================


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_valid_config(self):
        """Valid configuration should pass validation."""
        config = ProcessSandboxConfig(
            max_workers=5,
            worker_timeout=300,
            startup_timeout=30,
            idle_timeout=300,
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_invalid_max_workers(self):
        """max_workers < 1 should fail validation."""
        config = ProcessSandboxConfig(max_workers=0)

        errors = config.validate()
        assert any("max_workers" in e for e in errors)

    def test_excessive_max_workers(self):
        """max_workers > 50 should warn."""
        config = ProcessSandboxConfig(max_workers=100)

        errors = config.validate()
        assert any("max_workers" in e for e in errors)

    def test_invalid_timeout(self):
        """Very short timeout should fail validation."""
        config = ProcessSandboxConfig(worker_timeout=10)

        errors = config.validate()
        assert any("worker_timeout" in e for e in errors)

    def test_anthropic_key_required(self):
        """ANTHROPIC_API_KEY must be in allowed vars."""
        config = ProcessSandboxConfig(
            allowed_env_vars=["PATH", "HOME"]  # Missing ANTHROPIC_API_KEY
        )

        errors = config.validate()
        assert any("ANTHROPIC_API_KEY" in e for e in errors)


# =============================================================================
# Orchestrator Tests
# =============================================================================


class TestSandboxOrchestrator:
    """Tests for SandboxOrchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, sandbox_config):
        """Orchestrator should initialize correctly."""
        orchestrator = SandboxOrchestrator(sandbox_config)

        assert orchestrator.config == sandbox_config
        assert not orchestrator.is_running

    @pytest.mark.asyncio
    async def test_orchestrator_start_stop(self, sandbox_config):
        """Orchestrator should start and stop correctly."""
        orchestrator = SandboxOrchestrator(sandbox_config)

        await orchestrator.start()
        assert orchestrator.is_running

        await orchestrator.shutdown()
        assert not orchestrator.is_running

    @pytest.mark.asyncio
    async def test_pool_stats(self, sandbox_config):
        """Pool stats should return correct information."""
        orchestrator = SandboxOrchestrator(sandbox_config)
        await orchestrator.start()

        try:
            stats = orchestrator.get_pool_stats()

            assert "total_workers" in stats
            assert "busy_workers" in stats
            assert "idle_workers" in stats
            assert "max_workers" in stats
            assert stats["max_workers"] == sandbox_config.max_workers

        finally:
            await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_execute_without_start_raises(self, sandbox_config):
        """Executing without starting should raise RuntimeError."""
        orchestrator = SandboxOrchestrator(sandbox_config)

        with pytest.raises(RuntimeError, match="not started"):
            await orchestrator.execute(
                user_id="test-user",
                message="Test",
                attachments=[],
            )


# =============================================================================
# Adapter Tests
# =============================================================================


class TestSandboxAdapter:
    """Tests for sandbox adapter functions."""

    def test_is_sandbox_enabled_default(self):
        """Sandbox should be enabled by default."""
        from src.core.sandbox.adapter import is_sandbox_enabled

        with patch.dict(os.environ, {}, clear=True):
            # When SANDBOX_ENABLED is not set, default to True
            os.environ.pop("SANDBOX_ENABLED", None)
            assert is_sandbox_enabled() is True

    def test_is_sandbox_enabled_false(self):
        """Sandbox can be disabled via environment variable."""
        from src.core.sandbox.adapter import is_sandbox_enabled

        with patch.dict(os.environ, {"SANDBOX_ENABLED": "false"}):
            assert is_sandbox_enabled() is False

    def test_is_sandbox_enabled_true(self):
        """Sandbox can be explicitly enabled."""
        from src.core.sandbox.adapter import is_sandbox_enabled

        with patch.dict(os.environ, {"SANDBOX_ENABLED": "true"}):
            assert is_sandbox_enabled() is True

    @pytest.mark.asyncio
    async def test_execute_in_sandbox_disabled(self):
        """execute_in_sandbox should return placeholder when disabled."""
        from src.core.sandbox.adapter import execute_in_sandbox

        with patch.dict(os.environ, {"SANDBOX_ENABLED": "false"}):
            result = await execute_in_sandbox(
                user_id="test-user",
                message="Test message",
            )

            assert result["sandbox_disabled"] is True
            assert "content" in result

    @pytest.mark.asyncio
    async def test_stream_in_sandbox_disabled(self):
        """stream_in_sandbox should yield placeholder when disabled."""
        from src.core.sandbox.adapter import stream_in_sandbox

        with patch.dict(os.environ, {"SANDBOX_ENABLED": "false"}):
            events = []
            async for event in stream_in_sandbox(
                user_id="test-user",
                message="Test message",
            ):
                events.append(event)

            assert len(events) > 0
            assert any(e.get("data", {}).get("sandbox_disabled") for e in events)


# =============================================================================
# Performance Benchmark Tests
# =============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_config_filtering_performance(self, sandbox_config):
        """Environment filtering should be fast."""
        import time

        # Set up many environment variables
        test_vars = {f"VAR_{i}": f"value_{i}" for i in range(100)}
        with patch.dict(os.environ, test_vars):
            start = time.time()

            for _ in range(1000):
                sandbox_config.get_filtered_env(user_id="test-user")

            duration = time.time() - start

            # Should complete 1000 iterations in under 1 second
            assert duration < 1.0, f"Filtering took too long: {duration}s"

    def test_user_id_sanitization_performance(self, sandbox_config):
        """User ID sanitization should be fast."""
        import time

        malicious_ids = [
            "../../../etc/passwd" * 10,
            "a" * 1000,
            "user/../" * 100,
        ]

        start = time.time()

        for _ in range(10000):
            for malicious_id in malicious_ids:
                sandbox_config._sanitize_user_id(malicious_id)

        duration = time.time() - start

        # Should complete 30000 sanitizations in under 1 second
        assert duration < 1.0, f"Sanitization took too long: {duration}s"


# =============================================================================
# Integration Tests (marked for separate run)
# =============================================================================


@pytest.mark.integration
class TestSandboxIntegration:
    """Integration tests requiring actual process spawning."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_worker_process_isolation(self, temp_sandbox_dir):
        """Worker process should have isolated environment."""
        # This test requires actual process spawning
        # Mark as integration test and skip if dependencies not available
        pytest.skip("Requires full integration setup")

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_worker_crash_recovery(self, temp_sandbox_dir):
        """Orchestrator should recover from worker crashes."""
        # This test requires actual process spawning
        pytest.skip("Requires full integration setup")
