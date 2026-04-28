# =============================================================================
# IPA Platform - Trial and Error Engine Unit Tests
# =============================================================================
# Sprint 10: S10-4 TrialAndErrorEngine Tests
#
# Tests for trial-and-error learning functionality including automatic retry,
# parameter adjustment, error pattern recognition, and learning insights.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from src.domain.orchestration.planning.trial_error import (
    TrialAndErrorEngine,
    TrialStatus,
    LearningType,
    Trial,
    LearningInsight,
    ErrorFix,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def engine():
    """Create a TrialAndErrorEngine."""
    return TrialAndErrorEngine(
        llm_service=None,
        max_retries=3,
        learning_threshold=5,
        timeout_seconds=300
    )


@pytest.fixture
def engine_with_llm():
    """Create a TrialAndErrorEngine with mock LLM."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value='{"new_params": {"timeout": 60}, "new_strategy": "aggressive", "analysis": "Increase timeout", "confidence": 0.8}')
    return TrialAndErrorEngine(
        llm_service=llm,
        max_retries=3,
        learning_threshold=3,
        timeout_seconds=300
    )


@pytest.fixture
def successful_fn():
    """Create an async function that always succeeds."""
    async def fn(**kwargs):
        return {"status": "success", "result": "done"}
    return fn


@pytest.fixture
def failing_fn():
    """Create an async function that always fails."""
    async def fn(**kwargs):
        raise Exception("Simulated failure")
    return fn


@pytest.fixture
def flaky_fn():
    """Create an async function that fails first, then succeeds."""
    attempts = {"count": 0}
    async def fn(**kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise Exception(f"Attempt {attempts['count']} failed")
        return {"status": "success", "attempt": attempts["count"]}
    return fn


# =============================================================================
# Trial Tests
# =============================================================================


class TestTrial:
    """Tests for Trial data class."""

    def test_create_trial(self):
        """Test creating a trial."""
        task_id = uuid4()
        trial = Trial(
            id=uuid4(),
            task_id=task_id,
            attempt_number=1,
            parameters={"timeout": 30},
            strategy="default"
        )

        assert trial.task_id == task_id
        assert trial.attempt_number == 1
        assert trial.status == TrialStatus.PENDING
        assert trial.parameters["timeout"] == 30

    def test_trial_mark_running(self):
        """Test marking a trial as running."""
        trial = Trial(
            id=uuid4(),
            task_id=uuid4(),
            attempt_number=1,
            parameters={},
            strategy="default"
        )

        trial.mark_running()

        assert trial.status == TrialStatus.RUNNING
        assert trial.started_at is not None

    def test_trial_mark_success(self):
        """Test marking a trial as successful."""
        trial = Trial(
            id=uuid4(),
            task_id=uuid4(),
            attempt_number=1,
            parameters={},
            strategy="default"
        )

        trial.mark_running()
        trial.mark_success({"result": "success"}, 1500)

        assert trial.status == TrialStatus.SUCCESS
        assert trial.completed_at is not None
        assert trial.result == {"result": "success"}
        assert trial.duration_ms == 1500

    def test_trial_mark_failure(self):
        """Test marking a trial as failed."""
        trial = Trial(
            id=uuid4(),
            task_id=uuid4(),
            attempt_number=1,
            parameters={},
            strategy="default"
        )

        trial.mark_running()
        trial.mark_failure("Connection timeout")

        assert trial.status == TrialStatus.FAILURE
        assert trial.error == "Connection timeout"
        assert trial.error_type == "timeout"

    def test_trial_error_classification(self):
        """Test error type classification."""
        trial = Trial(
            id=uuid4(),
            task_id=uuid4(),
            attempt_number=1,
            parameters={},
            strategy="default"
        )

        # Test various error types
        trial.mark_failure("Network connection refused")
        assert trial.error_type == "connection"

        trial2 = Trial(
            id=uuid4(),
            task_id=uuid4(),
            attempt_number=1,
            parameters={},
            strategy="default"
        )
        trial2.mark_failure("Out of memory error")
        assert trial2.error_type == "memory"

    def test_trial_to_dict(self):
        """Test converting trial to dictionary."""
        trial = Trial(
            id=uuid4(),
            task_id=uuid4(),
            attempt_number=2,
            parameters={"key": "value"},
            strategy="aggressive"
        )

        data = trial.to_dict()

        assert "id" in data
        assert "task_id" in data
        assert data["attempt_number"] == 2
        assert data["strategy"] == "aggressive"
        assert data["parameters"] == {"key": "value"}


# =============================================================================
# LearningInsight Tests
# =============================================================================


class TestLearningInsight:
    """Tests for LearningInsight data class."""

    def test_create_insight(self):
        """Test creating a learning insight."""
        insight = LearningInsight(
            id=uuid4(),
            learning_type=LearningType.SUCCESS_PATTERN,
            pattern="Retry with increased timeout succeeds",
            confidence=0.85,
            evidence=[uuid4(), uuid4()],
            recommendation="Increase timeout for similar tasks"
        )

        assert insight.learning_type == LearningType.SUCCESS_PATTERN
        assert insight.confidence == 0.85
        assert len(insight.evidence) == 2

    def test_insight_to_dict(self):
        """Test converting insight to dictionary."""
        insight = LearningInsight(
            id=uuid4(),
            learning_type=LearningType.PARAMETER_TUNING,
            pattern="Higher timeout reduces failures",
            confidence=0.9,
            evidence=[uuid4()],
            recommendation="Use 60s timeout"
        )

        data = insight.to_dict()

        assert "id" in data
        assert data["learning_type"] == "parameter_tuning"
        assert data["confidence"] == 0.9


# =============================================================================
# ErrorFix Tests
# =============================================================================


class TestErrorFix:
    """Tests for ErrorFix data class."""

    def test_create_error_fix(self):
        """Test creating an error fix."""
        fix = ErrorFix(
            pattern="timeout",
            fix_type="parameter",
            adjustments={"timeout": "increase", "factor": 1.5},
            success_rate=0.8
        )

        assert fix.pattern == "timeout"
        assert fix.fix_type == "parameter"
        assert fix.adjustments["factor"] == 1.5

    def test_error_fix_applied_count(self):
        """Test error fix applied count tracking."""
        fix = ErrorFix(
            pattern="connection",
            fix_type="strategy",
            adjustments={"strategy": "retry_with_backoff"},
            success_rate=0.7,
            applied_count=0
        )

        fix.applied_count += 1
        assert fix.applied_count == 1


# =============================================================================
# TrialAndErrorEngine Tests
# =============================================================================


class TestTrialAndErrorEngine:
    """Tests for TrialAndErrorEngine class."""

    @pytest.mark.asyncio
    async def test_execute_success(self, engine, successful_fn):
        """Test successful execution on first try."""
        result = await engine.execute_with_retry(
            task_id=uuid4(),
            execution_fn=successful_fn,
            initial_params={"timeout": 30}
        )

        assert result["success"] is True
        assert result["attempts"] == 1
        assert result["result"] == {"status": "success", "result": "done"}

    @pytest.mark.asyncio
    async def test_execute_with_retries(self, engine):
        """Test execution with retries until success."""
        attempts = {"count": 0}

        async def flaky_fn(**kwargs):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise Exception(f"Attempt {attempts['count']} failed")
            return {"status": "success", "attempt": attempts["count"]}

        result = await engine.execute_with_retry(
            task_id=uuid4(),
            execution_fn=flaky_fn,
            initial_params={"timeout": 30}
        )

        assert result["success"] is True
        assert result["attempts"] == 3

    @pytest.mark.asyncio
    async def test_execute_all_retries_fail(self, engine, failing_fn):
        """Test execution when all retries fail."""
        result = await engine.execute_with_retry(
            task_id=uuid4(),
            execution_fn=failing_fn,
            initial_params={"timeout": 30}
        )

        assert result["success"] is False
        assert result["attempts"] == 3  # max_retries
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_with_custom_strategy(self, engine, successful_fn):
        """Test execution with custom strategy."""
        result = await engine.execute_with_retry(
            task_id=uuid4(),
            execution_fn=successful_fn,
            initial_params={},
            strategy="aggressive"
        )

        assert result["success"] is True
        assert result["final_strategy"] == "aggressive"

    @pytest.mark.asyncio
    async def test_known_pattern_adjustment(self, engine):
        """Test automatic parameter adjustment using known patterns."""
        attempts = {"count": 0}

        async def timeout_then_success(**kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise Exception("Operation timeout")
            return {"success": True, "timeout_used": kwargs.get("timeout")}

        result = await engine.execute_with_retry(
            task_id=uuid4(),
            execution_fn=timeout_then_success,
            initial_params={"timeout": 30}
        )

        assert result["success"] is True
        # Timeout pattern should have been applied

    def test_get_trial_history(self, engine):
        """Test getting trial history."""
        import asyncio

        async def executor(**kwargs):
            return {"done": True}

        task_id = uuid4()
        asyncio.get_event_loop().run_until_complete(
            engine.execute_with_retry(task_id, executor, {})
        )

        history = engine.get_trial_history(task_id=task_id)
        assert len(history) >= 1

    def test_get_all_trials(self, engine):
        """Test getting all trials across tasks."""
        import asyncio

        async def executor(**kwargs):
            return {"done": True}

        asyncio.get_event_loop().run_until_complete(
            engine.execute_with_retry(uuid4(), executor, {})
        )
        asyncio.get_event_loop().run_until_complete(
            engine.execute_with_retry(uuid4(), executor, {})
        )

        all_trials = engine.get_trial_history()
        assert len(all_trials) >= 2

    def test_get_trial_history_by_status(self, engine):
        """Test filtering trials by status."""
        import asyncio

        async def executor(**kwargs):
            return {"done": True}

        asyncio.get_event_loop().run_until_complete(
            engine.execute_with_retry(uuid4(), executor, {})
        )

        success_trials = engine.get_trial_history(status=TrialStatus.SUCCESS)
        for trial in success_trials:
            assert trial["status"] == "success"

    def test_get_statistics(self, engine):
        """Test getting trial statistics."""
        import asyncio

        async def executor(**kwargs):
            return {"done": True}

        asyncio.get_event_loop().run_until_complete(
            engine.execute_with_retry(uuid4(), executor, {})
        )

        stats = engine.get_statistics()

        assert "total_trials" in stats
        assert "success_count" in stats
        assert "failure_count" in stats
        assert "success_rate" in stats
        assert "average_duration_ms" in stats
        assert "unique_tasks" in stats

    def test_clear_history(self, engine):
        """Test clearing trial history."""
        import asyncio

        async def executor(**kwargs):
            return {"done": True}

        task_id = uuid4()
        asyncio.get_event_loop().run_until_complete(
            engine.execute_with_retry(task_id, executor, {})
        )

        assert len(engine.get_trial_history(task_id=task_id)) > 0

        engine.clear_history(task_id)

        assert len(engine.get_trial_history(task_id=task_id)) == 0

    def test_clear_all_history(self, engine):
        """Test clearing all trial history."""
        import asyncio

        async def executor(**kwargs):
            return {"done": True}

        asyncio.get_event_loop().run_until_complete(
            engine.execute_with_retry(uuid4(), executor, {})
        )
        asyncio.get_event_loop().run_until_complete(
            engine.execute_with_retry(uuid4(), executor, {})
        )

        engine.clear_history()  # Clear all

        assert len(engine.get_trial_history()) == 0

    @pytest.mark.asyncio
    async def test_learn_from_history(self, engine):
        """Test learning from trial history."""
        async def executor(**kwargs):
            return {"done": True}

        # Execute multiple trials to meet learning threshold
        for _ in range(6):
            await engine.execute_with_retry(uuid4(), executor, {"param": "value"})

        insights = await engine.learn_from_history()

        # Should have generated some insights
        assert isinstance(insights, list)

    def test_get_recommendations(self, engine):
        """Test getting recommendations."""
        recommendations = engine.get_recommendations()

        assert isinstance(recommendations, list)

    def test_known_error_patterns_initialized(self, engine):
        """Test that known error patterns are initialized."""
        # Engine should have known patterns for common errors
        assert len(engine._error_patterns) > 0
        assert "timeout" in engine._error_patterns
        assert "rate limit" in engine._error_patterns
        assert "connection" in engine._error_patterns


# =============================================================================
# TrialStatus and LearningType Tests
# =============================================================================


class TestEnums:
    """Tests for enum classes."""

    def test_trial_status_values(self):
        """Test TrialStatus enum values."""
        assert TrialStatus.PENDING.value == "pending"
        assert TrialStatus.RUNNING.value == "running"
        assert TrialStatus.SUCCESS.value == "success"
        assert TrialStatus.FAILURE.value == "failure"
        assert TrialStatus.TIMEOUT.value == "timeout"

    def test_learning_type_values(self):
        """Test LearningType enum values."""
        assert LearningType.PARAMETER_TUNING.value == "parameter_tuning"
        assert LearningType.STRATEGY_SWITCH.value == "strategy_switch"
        assert LearningType.ERROR_PATTERN.value == "error_pattern"
        assert LearningType.SUCCESS_PATTERN.value == "success_pattern"
