"""Sprint 166 — Dynamic Agent Count Tests.

Tests for complexity-aware TaskDecomposer and SubagentExecutor._infer_complexity().
"""

import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.swarm.task_decomposer import (
    DecomposedTask,
    TaskDecomposer,
    TaskDecomposition,
    MAX_SUBTASKS,
)


# ─── TaskDecomposer complexity_hint tests ───


class TestTaskDecomposerComplexityHint:
    """Verify that complexity_hint is wired into the LLM prompt."""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock(spec=["generate"])  # spec prevents auto-creating generate_structured
        llm.generate = AsyncMock()
        return llm

    @pytest.mark.asyncio
    async def test_simple_hint_included_in_prompt(self, mock_llm):
        """complexity_hint='simple' should appear in the LLM prompt."""
        mock_llm.generate.return_value = json.dumps({
            "mode": "parallel",
            "reasoning": "Simple task",
            "sub_tasks": [
                {"title": "DNS Check", "description": "Check DNS", "role": "general", "priority": 1, "tools_needed": []}
            ],
        })

        decomposer = TaskDecomposer(llm_service=mock_llm, tool_names=["search_knowledge"])
        await decomposer.decompose("Check DNS for example.com", complexity_hint="simple")

        call_args = mock_llm.generate.call_args
        prompt_text = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        assert "simple" in prompt_text
        assert "1-2" in prompt_text

    @pytest.mark.asyncio
    async def test_complex_hint_included_in_prompt(self, mock_llm):
        """complexity_hint='complex' should appear in the LLM prompt."""
        mock_llm.generate.return_value = json.dumps({
            "mode": "parallel",
            "reasoning": "Complex task",
            "sub_tasks": [
                {"title": "T1", "description": "D1", "role": "general", "priority": 1, "tools_needed": []},
                {"title": "T2", "description": "D2", "role": "general", "priority": 1, "tools_needed": []},
            ],
        })

        decomposer = TaskDecomposer(llm_service=mock_llm, tool_names=[])
        await decomposer.decompose("Multi-system outage", complexity_hint="complex")

        call_args = mock_llm.generate.call_args
        prompt_text = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        assert "complex" in prompt_text
        assert "4-8" in prompt_text

    @pytest.mark.asyncio
    async def test_auto_hint_default(self, mock_llm):
        """Default complexity_hint should be 'auto'."""
        mock_llm.generate.return_value = json.dumps({
            "mode": "parallel",
            "reasoning": "auto",
            "sub_tasks": [
                {"title": "T1", "description": "D1", "role": "general", "priority": 1, "tools_needed": []},
            ],
        })

        decomposer = TaskDecomposer(llm_service=mock_llm, tool_names=[])
        await decomposer.decompose("Some task")

        call_args = mock_llm.generate.call_args
        prompt_text = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        assert "auto" in prompt_text


# ─── MAX_SUBTASKS cap tests ───


class TestMaxSubtasksCap:
    """Verify _build_decomposition() caps at MAX_SUBTASKS."""

    def test_max_subtasks_constant(self):
        assert MAX_SUBTASKS == 10

    def test_cap_applied_when_exceeded(self):
        """LLM returning more than MAX_SUBTASKS should be truncated."""
        decomposer = TaskDecomposer(llm_service=MagicMock(), tool_names=[])

        # Simulate LLM returning 15 subtasks
        llm_result = {
            "mode": "parallel",
            "reasoning": "Many tasks",
            "sub_tasks": [
                {"title": f"Task-{i}", "description": f"Desc-{i}", "role": "general", "priority": 1, "tools_needed": []}
                for i in range(15)
            ],
        }

        with patch.object(decomposer, "_build_decomposition", wraps=decomposer._build_decomposition):
            result = decomposer._build_decomposition("test task", llm_result)

        assert len(result.sub_tasks) == MAX_SUBTASKS

    def test_no_cap_when_under_limit(self):
        """LLM returning fewer than MAX_SUBTASKS should not be truncated."""
        decomposer = TaskDecomposer(llm_service=MagicMock(), tool_names=[])

        llm_result = {
            "mode": "parallel",
            "reasoning": "Few tasks",
            "sub_tasks": [
                {"title": f"Task-{i}", "description": f"Desc-{i}", "role": "general", "priority": 1, "tools_needed": []}
                for i in range(3)
            ],
        }

        result = decomposer._build_decomposition("test task", llm_result)
        assert len(result.sub_tasks) == 3


# ─── SubagentExecutor._infer_complexity tests ───


class TestInferComplexity:
    """Test SubagentExecutor._infer_complexity() static method."""

    @pytest.fixture
    def make_request(self):
        from src.integrations.orchestration.dispatch.models import (
            DispatchRequest,
            ExecutionRoute,
        )

        def _make(risk_level: str = "low", intent_summary: str = ""):
            return DispatchRequest(
                route=ExecutionRoute.SUBAGENT,
                task="test task",
                user_id="test",
                session_id="test",
                risk_level=risk_level,
                intent_summary=intent_summary,
            )
        return _make

    def test_critical_risk_returns_complex(self, make_request):
        from src.integrations.orchestration.dispatch.executors.subagent import SubagentExecutor
        req = make_request(risk_level="CRITICAL", intent_summary="INCIDENT: network_failure")
        assert SubagentExecutor._infer_complexity(req) == "complex"

    def test_high_risk_returns_complex(self, make_request):
        from src.integrations.orchestration.dispatch.executors.subagent import SubagentExecutor
        req = make_request(risk_level="HIGH", intent_summary="REQUEST: vm_provision")
        assert SubagentExecutor._infer_complexity(req) == "complex"

    def test_incident_intent_returns_complex(self, make_request):
        from src.integrations.orchestration.dispatch.executors.subagent import SubagentExecutor
        req = make_request(risk_level="MEDIUM", intent_summary="INCIDENT: database_down")
        assert SubagentExecutor._infer_complexity(req) == "complex"

    def test_low_risk_query_returns_simple(self, make_request):
        from src.integrations.orchestration.dispatch.executors.subagent import SubagentExecutor
        req = make_request(risk_level="LOW", intent_summary="QUERY: general_info")
        assert SubagentExecutor._infer_complexity(req) == "simple"

    def test_medium_risk_returns_moderate(self, make_request):
        from src.integrations.orchestration.dispatch.executors.subagent import SubagentExecutor
        req = make_request(risk_level="MEDIUM", intent_summary="REQUEST: access_request")
        assert SubagentExecutor._infer_complexity(req) == "moderate"

    def test_change_intent_returns_moderate(self, make_request):
        from src.integrations.orchestration.dispatch.executors.subagent import SubagentExecutor
        req = make_request(risk_level="LOW", intent_summary="CHANGE: config_update")
        assert SubagentExecutor._infer_complexity(req) == "moderate"

    def test_empty_fields_returns_auto(self, make_request):
        from src.integrations.orchestration.dispatch.executors.subagent import SubagentExecutor
        req = make_request(risk_level="", intent_summary="")
        assert SubagentExecutor._infer_complexity(req) == "auto"

    def test_unknown_risk_returns_auto(self, make_request):
        from src.integrations.orchestration.dispatch.executors.subagent import SubagentExecutor
        req = make_request(risk_level="UNKNOWN", intent_summary="UNKNOWN: unclear")
        assert SubagentExecutor._infer_complexity(req) == "auto"
