"""Unit tests for Claude SDK hooks system.

Sprint 49: S49-3 - Hooks System (10 pts)
Tests: Hook base class, HookChain, ApprovalHook, AuditHook,
       RateLimitHook, SandboxHook
"""

import asyncio
import logging
import os
import tempfile
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.claude_sdk.hooks import (
    Hook,
    HookChain,
    ApprovalHook,
    AuditHook,
    RateLimitHook,
    RateLimitConfig,
    SandboxHook,
    StrictSandboxHook,
)
from src.integrations.claude_sdk.types import (
    HookResult,
    QueryContext,
    ToolCallContext,
    ToolResultContext,
)


# ============================================================
# Test Hook Base Class
# ============================================================

class TestHookBase:
    """Tests for Hook base class."""

    def test_default_priority(self):
        """Test default priority is 50."""

        class TestHook(Hook):
            pass

        hook = TestHook()
        assert hook.priority == 50

    def test_custom_priority(self):
        """Test custom priority setting."""

        class TestHook(Hook):
            priority = 75

        hook = TestHook()
        assert hook.priority == 75

    def test_default_enabled(self):
        """Test hook is enabled by default."""

        class TestHook(Hook):
            pass

        hook = TestHook()
        assert hook.enabled is True

    @pytest.mark.asyncio
    async def test_default_on_tool_call_allows(self):
        """Test default on_tool_call returns ALLOW."""

        class TestHook(Hook):
            pass

        hook = TestHook()
        context = ToolCallContext(tool_name="Read", args={"path": "/tmp/test"})
        result = await hook.on_tool_call(context)
        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_default_on_query_start_allows(self):
        """Test default on_query_start returns ALLOW."""

        class TestHook(Hook):
            pass

        hook = TestHook()
        context = QueryContext(prompt="test query")
        result = await hook.on_query_start(context)
        assert result.is_allowed is True


# ============================================================
# Test HookChain
# ============================================================

class TestHookChain:
    """Tests for HookChain."""

    def test_add_hook(self):
        """Test adding hooks to chain."""
        chain = HookChain()

        class TestHook(Hook):
            name = "test"

        hook = TestHook()
        chain.add(hook)

        assert len(chain.hooks) == 1
        assert chain.hooks[0] == hook

    def test_priority_ordering(self):
        """Test hooks are ordered by priority (descending)."""
        chain = HookChain()

        class LowPriority(Hook):
            priority = 10

        class HighPriority(Hook):
            priority = 90

        class MediumPriority(Hook):
            priority = 50

        chain.add(LowPriority())
        chain.add(HighPriority())
        chain.add(MediumPriority())

        assert chain.hooks[0].priority == 90
        assert chain.hooks[1].priority == 50
        assert chain.hooks[2].priority == 10

    def test_remove_hook(self):
        """Test removing hooks from chain."""
        chain = HookChain()

        class TestHook(Hook):
            pass

        hook = TestHook()
        chain.add(hook)
        chain.remove(hook)

        assert len(chain.hooks) == 0

    def test_clear_hooks(self):
        """Test clearing all hooks."""
        chain = HookChain()

        class TestHook(Hook):
            pass

        chain.add(TestHook())
        chain.add(TestHook())
        chain.clear()

        assert len(chain.hooks) == 0

    @pytest.mark.asyncio
    async def test_run_tool_call_allows(self):
        """Test run_tool_call with allowing hooks."""
        chain = HookChain()

        class AllowHook(Hook):
            async def on_tool_call(self, context):
                return HookResult.ALLOW

        chain.add(AllowHook())
        chain.add(AllowHook())

        context = ToolCallContext(tool_name="Read", args={})
        result = await chain.run_tool_call(context)

        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_run_tool_call_rejects(self):
        """Test run_tool_call with rejecting hook."""
        chain = HookChain()

        class RejectHook(Hook):
            async def on_tool_call(self, context):
                return HookResult.reject("Not allowed")

        chain.add(RejectHook())

        context = ToolCallContext(tool_name="Write", args={})
        result = await chain.run_tool_call(context)

        assert result.is_rejected is True
        assert "Not allowed" in result.reason

    @pytest.mark.asyncio
    async def test_run_tool_call_stops_on_reject(self):
        """Test that chain stops after first rejection."""
        chain = HookChain()
        call_count = 0

        class CountingHook(Hook):
            priority = 50

            async def on_tool_call(self, context):
                nonlocal call_count
                call_count += 1
                return HookResult.ALLOW

        class RejectHook(Hook):
            priority = 90  # Higher priority, runs first

            async def on_tool_call(self, context):
                return HookResult.reject("Rejected")

        chain.add(CountingHook())
        chain.add(RejectHook())

        context = ToolCallContext(tool_name="Write", args={})
        result = await chain.run_tool_call(context)

        assert result.is_rejected is True
        assert call_count == 0  # CountingHook should not be called

    @pytest.mark.asyncio
    async def test_run_tool_call_passes_modified_args(self):
        """Test that modified args are passed to subsequent hooks."""
        chain = HookChain()
        received_args = None

        class ModifyHook(Hook):
            priority = 90

            async def on_tool_call(self, context):
                return HookResult.modify({"modified": True})

        class CheckHook(Hook):
            priority = 50

            async def on_tool_call(self, context):
                nonlocal received_args
                received_args = context.args
                return HookResult.ALLOW

        chain.add(ModifyHook())
        chain.add(CheckHook())

        context = ToolCallContext(tool_name="Read", args={"original": True})
        await chain.run_tool_call(context)

        assert received_args == {"modified": True}

    @pytest.mark.asyncio
    async def test_disabled_hooks_skipped(self):
        """Test that disabled hooks are skipped."""
        chain = HookChain()
        was_called = False

        class TestHook(Hook):
            enabled = False

            async def on_tool_call(self, context):
                nonlocal was_called
                was_called = True
                return HookResult.reject("Should not run")

        chain.add(TestHook())

        context = ToolCallContext(tool_name="Read", args={})
        result = await chain.run_tool_call(context)

        assert result.is_allowed is True
        assert was_called is False


# ============================================================
# Test ApprovalHook
# ============================================================

class TestApprovalHook:
    """Tests for ApprovalHook."""

    def test_default_approval_tools(self):
        """Test default approval tools."""
        hook = ApprovalHook()
        assert "Write" in hook.approval_tools
        assert "Edit" in hook.approval_tools
        assert "Bash" in hook.approval_tools

    @pytest.mark.asyncio
    async def test_read_auto_approved(self):
        """Test read operations are auto-approved."""
        hook = ApprovalHook(auto_approve_reads=True)
        context = ToolCallContext(tool_name="Read", args={"path": "/tmp/test"})
        result = await hook.on_tool_call(context)
        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_write_requires_approval(self):
        """Test write operations require approval."""
        approved = False

        async def callback(ctx):
            return approved

        hook = ApprovalHook(approval_callback=callback)
        context = ToolCallContext(tool_name="Write", args={"file_path": "/tmp/test"})

        # Should be rejected when not approved
        result = await hook.on_tool_call(context)
        assert result.is_rejected is True

    @pytest.mark.asyncio
    async def test_approval_granted(self):
        """Test operation proceeds when approved."""

        async def callback(ctx):
            return True

        hook = ApprovalHook(approval_callback=callback)
        context = ToolCallContext(tool_name="Write", args={"file_path": "/tmp/test"})

        result = await hook.on_tool_call(context)
        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_approval_remembers_session(self):
        """Test approval is remembered for same operation."""

        call_count = 0

        async def callback(ctx):
            nonlocal call_count
            call_count += 1
            return True

        hook = ApprovalHook(approval_callback=callback)
        context = ToolCallContext(
            tool_name="Write",
            args={"file_path": "/tmp/test"},
            session_id="test-session",
        )

        # First call should request approval
        await hook.on_tool_call(context)
        # Second call should use cached approval
        await hook.on_tool_call(context)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_no_callback_rejects(self):
        """Test that no callback configured rejects by default."""
        hook = ApprovalHook(approval_callback=None)
        context = ToolCallContext(tool_name="Write", args={})

        result = await hook.on_tool_call(context)
        assert result.is_rejected is True
        assert "no callback configured" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_timeout_rejects(self):
        """Test timeout results in rejection."""

        async def slow_callback(ctx):
            await asyncio.sleep(2)
            return True

        hook = ApprovalHook(approval_callback=slow_callback, timeout=0.1)
        context = ToolCallContext(tool_name="Write", args={})

        result = await hook.on_tool_call(context)
        assert result.is_rejected is True
        assert "timeout" in result.reason.lower()

    def test_add_approval_tool(self):
        """Test adding approval tool."""
        hook = ApprovalHook()
        hook.add_approval_tool("CustomTool")
        assert "CustomTool" in hook.approval_tools

    def test_remove_approval_tool(self):
        """Test removing approval tool."""
        hook = ApprovalHook()
        hook.remove_approval_tool("Write")
        assert "Write" not in hook.approval_tools

    @pytest.mark.asyncio
    async def test_session_clear_on_end(self):
        """Test approved operations cleared on session end."""
        hook = ApprovalHook()
        hook._approved_operations.add("Write:/tmp/test")

        await hook.on_session_end("test-session")

        assert len(hook._approved_operations) == 0


# ============================================================
# Test AuditHook
# ============================================================

class TestAuditHook:
    """Tests for AuditHook."""

    def test_default_priority(self):
        """Test audit hook has low priority (runs last)."""
        hook = AuditHook()
        assert hook.priority == 10

    @pytest.mark.asyncio
    async def test_session_logging(self):
        """Test session start/end logging."""
        hook = AuditHook()

        await hook.on_session_start("test-session")
        log = hook.get_session_log("test-session")
        assert log is not None
        assert log.session_id == "test-session"
        assert len(log.entries) == 1

    @pytest.mark.asyncio
    async def test_tool_call_logging(self):
        """Test tool call is logged."""
        hook = AuditHook()
        await hook.on_session_start("test-session")

        context = ToolCallContext(
            tool_name="Read",
            args={"path": "/tmp/test"},
            session_id="test-session",
        )
        await hook.on_tool_call(context)

        log = hook.get_session_log("test-session")
        # session_start + tool_call
        assert len(log.entries) == 2
        assert log.entries[1].event_type == "tool_call"

    @pytest.mark.asyncio
    async def test_allows_operations(self):
        """Test audit hook always allows operations."""
        hook = AuditHook()

        context = ToolCallContext(tool_name="Write", args={})
        result = await hook.on_tool_call(context)

        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_redaction_api_key(self):
        """Test API key is redacted."""
        hook = AuditHook()

        # Check redaction
        text = "api_key: sk-12345678901234567890"
        redacted = hook._redact_string(text)
        assert "sk-" not in redacted
        assert "REDACTED" in redacted

    @pytest.mark.asyncio
    async def test_redaction_dict_keys(self):
        """Test sensitive dict keys are redacted."""
        hook = AuditHook()

        data = {"username": "test", "password": "secret123", "token": "abc"}
        redacted = hook._redact_dict(data)

        assert redacted["username"] == "test"
        assert redacted["password"] == "[REDACTED]"
        assert redacted["token"] == "[REDACTED]"

    def test_clear_logs(self):
        """Test clearing logs."""
        hook = AuditHook()
        hook._session_logs["test1"] = MagicMock()
        hook._session_logs["test2"] = MagicMock()

        hook.clear_logs("test1")
        assert "test1" not in hook._session_logs
        assert "test2" in hook._session_logs

        hook.clear_logs()
        assert len(hook._session_logs) == 0

    @pytest.mark.asyncio
    async def test_custom_callback(self):
        """Test custom log callback is called."""
        entries = []

        def callback(entry):
            entries.append(entry)

        hook = AuditHook(log_callback=callback)
        await hook.on_session_start("test-session")

        assert len(entries) == 1


# ============================================================
# Test RateLimitHook
# ============================================================

class TestRateLimitHook:
    """Tests for RateLimitHook."""

    def test_default_config(self):
        """Test default rate limit configuration."""
        hook = RateLimitHook()
        assert hook.default_config.calls_per_minute == 60
        assert hook.default_config.max_concurrent == 10

    @pytest.mark.asyncio
    async def test_allows_under_limit(self):
        """Test operations allowed under rate limit."""
        hook = RateLimitHook(calls_per_minute=100)

        context = ToolCallContext(
            tool_name="Read",
            args={},
            session_id="test-session",
        )
        await hook.on_session_start("test-session")

        result = await hook.on_tool_call(context)
        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_rejects_over_limit(self):
        """Test operations rejected over rate limit."""
        hook = RateLimitHook(calls_per_minute=2, max_concurrent=10)
        await hook.on_session_start("test-session")

        context = ToolCallContext(
            tool_name="Read",
            args={},
            session_id="test-session",
        )

        # First two should be allowed
        await hook.on_tool_call(context)
        await hook.on_tool_result(ToolResultContext(
            tool_name="Read", result="ok", success=True, session_id="test-session"
        ))
        await hook.on_tool_call(context)
        await hook.on_tool_result(ToolResultContext(
            tool_name="Read", result="ok", success=True, session_id="test-session"
        ))

        # Third should be rejected
        result = await hook.on_tool_call(context)
        assert result.is_rejected is True
        assert "rate limit" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_per_tool_limits(self):
        """Test per-tool rate limits."""
        hook = RateLimitHook(
            calls_per_minute=100,
            per_tool_limits={
                "Bash": RateLimitConfig(calls_per_minute=1, max_concurrent=1),
            },
        )
        await hook.on_session_start("test-session")

        context = ToolCallContext(
            tool_name="Bash",
            args={"command": "echo test"},
            session_id="test-session",
        )

        # First should be allowed
        result = await hook.on_tool_call(context)
        assert result.is_allowed is True

        await hook.on_tool_result(ToolResultContext(
            tool_name="Bash", result="ok", success=True, session_id="test-session"
        ))

        # Second should be rejected (1/min limit)
        result = await hook.on_tool_call(context)
        assert result.is_rejected is True

    def test_get_stats(self):
        """Test getting rate limit statistics."""
        hook = RateLimitHook()
        stats = hook.get_stats()
        assert isinstance(stats, dict)

    def test_reset_stats(self):
        """Test resetting statistics."""
        hook = RateLimitHook()
        hook._session_stats["test"] = MagicMock()
        hook.reset_stats()
        assert len(hook._session_stats) == 0


# ============================================================
# Test SandboxHook
# ============================================================

class TestSandboxHook:
    """Tests for SandboxHook."""

    def test_default_blocked_patterns(self):
        """Test default blocked patterns exist."""
        hook = SandboxHook()
        patterns = hook.get_blocked_patterns()
        assert len(patterns) > 0

    @pytest.mark.asyncio
    async def test_allows_safe_paths(self):
        """Test allows access to safe paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook = SandboxHook(allowed_paths=[tmpdir])

            context = ToolCallContext(
                tool_name="Read",
                args={"path": os.path.join(tmpdir, "test.txt")},
            )
            result = await hook.on_tool_call(context)
            assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_blocks_outside_allowed(self):
        """Test blocks access outside allowed paths."""
        hook = SandboxHook(allowed_paths=["/safe"], allow_reads=False)

        context = ToolCallContext(
            tool_name="Read",
            args={"path": "/etc/passwd"},
        )
        result = await hook.on_tool_call(context)
        assert result.is_rejected is True

    @pytest.mark.asyncio
    async def test_blocks_sensitive_files(self):
        """Test blocks access to sensitive files."""
        hook = SandboxHook()

        context = ToolCallContext(
            tool_name="Read",
            args={"path": "/home/user/.ssh/id_rsa"},
        )
        result = await hook.on_tool_call(context)
        assert result.is_rejected is True
        assert "blocked pattern" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_blocks_env_files(self):
        """Test blocks .env files."""
        hook = SandboxHook()

        context = ToolCallContext(
            tool_name="Read",
            args={"path": "/project/.env"},
        )
        result = await hook.on_tool_call(context)
        assert result.is_rejected is True

    @pytest.mark.asyncio
    async def test_allows_temp_when_configured(self):
        """Test allows temp directory when configured."""
        hook = SandboxHook(allowed_paths=["/project"], allow_temp=True)

        temp_dir = os.environ.get("TEMP", os.environ.get("TMP", "/tmp"))
        context = ToolCallContext(
            tool_name="Write",
            args={"file_path": os.path.join(temp_dir, "test.txt")},
        )
        result = await hook.on_tool_call(context)
        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_allows_reads_outside_when_configured(self):
        """Test allows reads outside allowed paths when configured."""
        hook = SandboxHook(allowed_paths=["/project"], allow_reads=True)

        context = ToolCallContext(
            tool_name="Read",
            args={"path": "/other/file.txt"},
        )
        result = await hook.on_tool_call(context)
        # Should allow (unless blocked by pattern)
        # Note: /other may match a blocked pattern
        # Use a path that doesn't match any blocked pattern
        context2 = ToolCallContext(
            tool_name="Read",
            args={"path": "/data/file.txt"},
        )
        result = await hook.on_tool_call(context2)
        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_non_file_tools_allowed(self):
        """Test non-file tools are always allowed."""
        hook = SandboxHook(allowed_paths=["/project"])

        context = ToolCallContext(
            tool_name="Task",
            args={"prompt": "do something"},
        )
        result = await hook.on_tool_call(context)
        assert result.is_allowed is True

    def test_add_allowed_path(self):
        """Test adding allowed path."""
        hook = SandboxHook(allowed_paths=["/project"])
        hook.add_allowed_path("/data")

        paths = hook.get_allowed_paths()
        assert len(paths) == 2

    def test_add_blocked_pattern(self):
        """Test adding blocked pattern."""
        hook = SandboxHook()
        initial_count = len(hook.get_blocked_patterns())

        hook.add_blocked_pattern(r"\.secret$")

        assert len(hook.get_blocked_patterns()) == initial_count + 1


class TestStrictSandboxHook:
    """Tests for StrictSandboxHook."""

    def test_requires_allowed_paths(self):
        """Test strict sandbox requires allowed paths."""
        with pytest.raises(ValueError):
            StrictSandboxHook(allowed_paths=[])

    def test_blocks_reads_outside(self):
        """Test strict sandbox blocks reads outside allowed paths."""
        hook = StrictSandboxHook(allowed_paths=["/project"])
        assert hook.allow_reads is False

    def test_blocks_temp(self):
        """Test strict sandbox blocks temp directory."""
        hook = StrictSandboxHook(allowed_paths=["/project"])
        assert hook.allow_temp is False


# ============================================================
# Test Integration
# ============================================================

class TestHooksIntegration:
    """Integration tests for multiple hooks."""

    @pytest.mark.asyncio
    async def test_chain_with_multiple_hooks(self):
        """Test hook chain with multiple hook types."""
        chain = HookChain()

        # Add sandbox (high priority)
        with tempfile.TemporaryDirectory() as tmpdir:
            chain.add(SandboxHook(allowed_paths=[tmpdir]))

            # Add rate limit
            chain.add(RateLimitHook(calls_per_minute=100))

            # Add audit (low priority)
            chain.add(AuditHook())

            await chain.run_session_start("test-session")

            context = ToolCallContext(
                tool_name="Read",
                args={"path": os.path.join(tmpdir, "test.txt")},
                session_id="test-session",
            )

            result = await chain.run_tool_call(context)
            assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_sandbox_blocks_before_rate_limit(self):
        """Test sandbox blocks before rate limit is checked."""
        chain = HookChain()

        # Sandbox with high priority should block first
        chain.add(SandboxHook(allowed_paths=["/safe"], allow_reads=False))
        chain.add(RateLimitHook(calls_per_minute=100))

        context = ToolCallContext(
            tool_name="Write",
            args={"file_path": "/etc/passwd"},
        )

        result = await chain.run_tool_call(context)
        assert result.is_rejected is True
        # Could be blocked by pattern OR by being outside allowed paths
        assert "blocked" in result.reason.lower() or "denied" in result.reason.lower()
