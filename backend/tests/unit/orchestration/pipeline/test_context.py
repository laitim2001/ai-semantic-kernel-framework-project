"""Tests for PipelineContext dataclass."""

import time

import pytest

from src.integrations.orchestration.pipeline.context import PipelineContext


class TestPipelineContext:
    """Tests for PipelineContext initialization and methods."""

    def _make_context(self, **kwargs) -> PipelineContext:
        defaults = {
            "user_id": "test-user",
            "session_id": "test-session",
            "task": "Check VPN connectivity",
        }
        defaults.update(kwargs)
        return PipelineContext(**defaults)

    def test_creation_with_required_fields(self):
        ctx = self._make_context()
        assert ctx.user_id == "test-user"
        assert ctx.session_id == "test-session"
        assert ctx.task == "Check VPN connectivity"
        assert ctx.request_id  # auto-generated UUID

    def test_defaults_are_empty(self):
        ctx = self._make_context()
        assert ctx.memory_text == ""
        assert ctx.knowledge_text == ""
        assert ctx.routing_decision is None
        assert ctx.risk_assessment is None
        assert ctx.selected_route is None
        assert ctx.dispatch_result is None
        assert ctx.paused_at is None
        assert ctx.completed_steps == []
        assert ctx.step_latencies == {}

    def test_mark_step_complete(self):
        ctx = self._make_context()
        ctx.mark_step_complete("memory_read", 45.2)
        ctx.mark_step_complete("knowledge_search", 120.5)

        assert ctx.completed_steps == ["memory_read", "knowledge_search"]
        assert ctx.step_latencies["memory_read"] == 45.2
        assert ctx.step_latencies["knowledge_search"] == 120.5

    def test_current_step_index(self):
        ctx = self._make_context()
        assert ctx.current_step_index == 0

        ctx.mark_step_complete("memory_read", 10)
        assert ctx.current_step_index == 1

        ctx.mark_step_complete("knowledge_search", 20)
        assert ctx.current_step_index == 2

    def test_is_paused(self):
        ctx = self._make_context()
        assert ctx.is_paused is False

        ctx.paused_at = "hitl"
        assert ctx.is_paused is True

        ctx.paused_at = None
        assert ctx.is_paused is False

    def test_elapsed_ms(self):
        ctx = self._make_context()
        # Should be a small positive number
        time.sleep(0.01)
        assert ctx.elapsed_ms > 5  # at least 5ms

    def test_to_checkpoint_state(self):
        ctx = self._make_context()
        ctx.memory_text = "Some memory"
        ctx.knowledge_text = "Some knowledge"
        ctx.selected_route = "direct_answer"
        ctx.completed_steps = ["memory_read"]

        state = ctx.to_checkpoint_state()

        assert state["user_id"] == "test-user"
        assert state["session_id"] == "test-session"
        assert state["task"] == "Check VPN connectivity"
        assert state["memory_text"] == "Some memory"
        assert state["selected_route"] == "direct_answer"
        assert state["completed_steps"] == ["memory_read"]

    def test_to_checkpoint_state_truncates_long_text(self):
        ctx = self._make_context()
        ctx.memory_text = "x" * 1000
        ctx.knowledge_text = "y" * 1000

        state = ctx.to_checkpoint_state()

        assert len(state["memory_text"]) == 500
        assert len(state["knowledge_text"]) == 500

    def test_to_sse_summary(self):
        ctx = self._make_context()
        ctx.mark_step_complete("memory_read", 50)
        ctx.selected_route = "team"

        summary = ctx.to_sse_summary()

        assert summary["session_id"] == "test-session"
        assert summary["completed_steps"] == ["memory_read"]
        assert summary["current_step_index"] == 1
        assert summary["selected_route"] == "team"
        assert summary["paused_at"] is None
        assert isinstance(summary["elapsed_ms"], float)

    def test_metadata_is_independent(self):
        """Ensure each context instance has its own mutable containers."""
        ctx1 = self._make_context()
        ctx2 = self._make_context()

        ctx1.completed_steps.append("step1")
        ctx1.step_latencies["step1"] = 10

        assert ctx2.completed_steps == []
        assert ctx2.step_latencies == {}
