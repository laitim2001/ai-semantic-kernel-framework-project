"""Tests for MemoryStep and KnowledgeStep."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.orchestration.pipeline.context import PipelineContext
from src.integrations.orchestration.pipeline.steps.step1_memory import MemoryStep
from src.integrations.orchestration.pipeline.steps.step2_knowledge import KnowledgeStep


class TestMemoryStep:
    """Tests for Step 1: Memory Read."""

    def _make_context(self) -> PipelineContext:
        return PipelineContext(
            user_id="test-user",
            session_id="test-session",
            task="Check VPN connectivity for Taipei office",
        )

    @pytest.mark.asyncio
    async def test_successful_memory_read(self):
        """Memory step populates context.memory_text when service available."""
        # Mock assembled context
        mock_assembled = MagicMock()
        mock_assembled.to_prompt_text.return_value = "## Pinned\nUser prefers concise answers"
        mock_assembled.pinned_count = 2
        mock_assembled.budget_used_pct = 45.0

        # Mock managers
        mock_mgr = AsyncMock()
        mock_budget = AsyncMock()
        mock_budget.assemble_context = AsyncMock(return_value=mock_assembled)

        step = MemoryStep(memory_manager=mock_mgr, budget_manager=mock_budget)
        ctx = self._make_context()

        result = await step._execute(ctx)

        assert result.memory_text == "## Pinned\nUser prefers concise answers"
        assert result.memory_metadata["pinned_count"] == 2
        assert result.memory_metadata["budget_used_pct"] == 45.0
        assert result.memory_metadata["status"] == "ok"

        mock_budget.assemble_context.assert_called_once_with(
            user_id="test-user",
            query="Check VPN connectivity for Taipei office",
            memory_manager=mock_mgr,
        )

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_failure(self):
        """Memory step sets empty text when service unavailable."""
        mock_mgr = AsyncMock()
        mock_budget = AsyncMock()
        mock_budget.assemble_context = AsyncMock(
            side_effect=ConnectionError("Redis unavailable")
        )

        step = MemoryStep(memory_manager=mock_mgr, budget_manager=mock_budget)
        ctx = self._make_context()

        result = await step._execute(ctx)

        assert result.memory_text == ""
        assert result.memory_metadata["status"] == "unavailable"
        assert "Redis unavailable" in result.memory_metadata["error"]

    def test_step_properties(self):
        step = MemoryStep()
        assert step.name == "memory_read"
        assert step.step_index == 0

    @pytest.mark.asyncio
    async def test_execute_records_latency(self):
        """The base class execute() wrapper records latency."""
        mock_assembled = MagicMock()
        mock_assembled.to_prompt_text.return_value = "memory"
        mock_assembled.pinned_count = 0
        mock_assembled.budget_used_pct = 0

        mock_mgr = AsyncMock()
        mock_budget = AsyncMock()
        mock_budget.assemble_context = AsyncMock(return_value=mock_assembled)

        step = MemoryStep(memory_manager=mock_mgr, budget_manager=mock_budget)
        ctx = self._make_context()

        result = await step.execute(ctx)  # use public execute(), not _execute()

        assert "memory_read" in result.completed_steps
        assert result.step_latencies["memory_read"] >= 0


class TestKnowledgeStep:
    """Tests for Step 2: Knowledge Search."""

    def _make_context(self) -> PipelineContext:
        return PipelineContext(
            user_id="test-user",
            session_id="test-session",
            task="Investigate ETL pipeline failure in production",
        )

    @pytest.mark.asyncio
    async def test_successful_knowledge_search(self):
        """Knowledge step populates context.knowledge_text with results."""
        step = KnowledgeStep()

        # Mock the internal methods
        mock_results = [
            {"source": "runbook", "content": "ETL restart procedure", "score": 0.95},
            {"source": "wiki", "content": "ETL architecture overview", "score": 0.88},
        ]

        with patch.object(step, "_get_embedding", return_value=[0.1] * 1536), \
             patch.object(step, "_search_qdrant", return_value=mock_results):

            ctx = self._make_context()
            result = await step._execute(ctx)

        assert "[runbook] (score=0.95) ETL restart procedure" in result.knowledge_text
        assert "[wiki] (score=0.88) ETL architecture overview" in result.knowledge_text
        assert result.knowledge_metadata["result_count"] == 2
        assert result.knowledge_metadata["status"] == "ok"

    @pytest.mark.asyncio
    async def test_no_results(self):
        """Knowledge step handles empty search results."""
        step = KnowledgeStep()

        with patch.object(step, "_get_embedding", return_value=[0.1] * 1536), \
             patch.object(step, "_search_qdrant", return_value=[]):

            ctx = self._make_context()
            result = await step._execute(ctx)

        assert result.knowledge_text == ""
        assert result.knowledge_metadata["result_count"] == 0
        assert result.knowledge_metadata["status"] == "no_results"

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_failure(self):
        """Knowledge step sets empty text when Qdrant unavailable."""
        step = KnowledgeStep()

        with patch.object(
            step, "_get_embedding", side_effect=ConnectionError("Qdrant down")
        ):
            ctx = self._make_context()
            result = await step._execute(ctx)

        assert result.knowledge_text == ""
        assert result.knowledge_metadata["status"] == "unavailable"
        assert "Qdrant down" in result.knowledge_metadata["error"]

    def test_step_properties(self):
        step = KnowledgeStep()
        assert step.name == "knowledge_search"
        assert step.step_index == 1

    def test_format_results(self):
        results = [
            {"source": "doc1", "content": "hello", "score": 0.9},
            {"source": "doc2", "content": "world", "score": 0.8},
        ]
        text = KnowledgeStep._format_results(results)
        assert "[doc1] (score=0.90) hello" in text
        assert "[doc2] (score=0.80) world" in text

    def test_format_results_empty(self):
        assert KnowledgeStep._format_results([]) == ""
