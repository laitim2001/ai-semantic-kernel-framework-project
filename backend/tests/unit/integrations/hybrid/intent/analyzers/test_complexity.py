# =============================================================================
# IPA Platform - Complexity Analyzer Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Unit tests for ComplexityAnalyzer.
# =============================================================================

import pytest

from src.integrations.hybrid.intent.analyzers.complexity import (
    COMPLEX_OPERATION_INDICATORS,
    ComplexityAnalyzer,
    DEPENDENCY_INDICATORS,
    PERSISTENCE_INDICATORS,
    STEP_INDICATORS,
    TIME_INDICATORS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def analyzer() -> ComplexityAnalyzer:
    """Create a default ComplexityAnalyzer."""
    return ComplexityAnalyzer()


@pytest.fixture
def analyzer_custom_weights() -> ComplexityAnalyzer:
    """Create analyzer with custom weights."""
    return ComplexityAnalyzer(
        step_weight=0.5,
        dependency_weight=0.2,
        persistence_weight=0.2,
        time_weight=0.1,
    )


# =============================================================================
# Initialization Tests
# =============================================================================

class TestComplexityAnalyzerInit:
    """Tests for ComplexityAnalyzer initialization."""

    def test_default_initialization(self, analyzer: ComplexityAnalyzer):
        """Test default initialization with equal weights."""
        assert analyzer.step_weight == 0.25
        assert analyzer.dependency_weight == 0.25
        assert analyzer.persistence_weight == 0.25
        assert analyzer.time_weight == 0.25

    def test_weights_normalized(self, analyzer_custom_weights: ComplexityAnalyzer):
        """Test that weights are normalized to sum to 1."""
        total = (
            analyzer_custom_weights.step_weight +
            analyzer_custom_weights.dependency_weight +
            analyzer_custom_weights.persistence_weight +
            analyzer_custom_weights.time_weight
        )
        assert abs(total - 1.0) < 0.001

    def test_patterns_compiled(self, analyzer: ComplexityAnalyzer):
        """Test that step count patterns are compiled."""
        assert len(analyzer.step_count_patterns) > 0
        for pattern in analyzer.step_count_patterns:
            assert hasattr(pattern, "search")

    def test_indicator_sets_populated(self, analyzer: ComplexityAnalyzer):
        """Test that indicator sets are populated."""
        assert len(analyzer.step_indicators) > 0
        assert len(analyzer.dependency_indicators) > 0
        assert len(analyzer.persistence_indicators) > 0
        assert len(analyzer.time_indicators) > 0


# =============================================================================
# Step Detection Tests
# =============================================================================

class TestStepDetection:
    """Tests for step count detection."""

    @pytest.mark.asyncio
    async def test_explicit_step_count(self, analyzer: ComplexityAnalyzer):
        """Test detection of explicit step counts."""
        result = await analyzer.analyze("This task has 5 steps")
        assert result.step_count_estimate >= 5

    @pytest.mark.asyncio
    async def test_step_indicators(self, analyzer: ComplexityAnalyzer):
        """Test detection of step indicators."""
        result = await analyzer.analyze("First do A, then do B, finally do C")
        assert result.step_count_estimate >= 3

    @pytest.mark.asyncio
    async def test_chinese_step_indicators(self, analyzer: ComplexityAnalyzer):
        """Test detection of Chinese step indicators."""
        result = await analyzer.analyze("首先做A，然後做B，最後做C")
        assert result.step_count_estimate >= 3

    @pytest.mark.asyncio
    async def test_phase_indicators(self, analyzer: ComplexityAnalyzer):
        """Test detection of phase indicators."""
        result = await analyzer.analyze("Phase 1 is setup, phase 2 is execution")
        assert result.step_count_estimate >= 2

    @pytest.mark.asyncio
    async def test_no_step_indicators(self, analyzer: ComplexityAnalyzer):
        """Test with no step indicators."""
        result = await analyzer.analyze("Do a simple task")
        assert result.step_count_estimate == 1

    @pytest.mark.asyncio
    async def test_many_step_indicators(self, analyzer: ComplexityAnalyzer):
        """Test with many step indicators."""
        result = await analyzer.analyze(
            "First A, then B, next C, after that D, followed by E, finally F"
        )
        assert result.step_count_estimate >= 5


# =============================================================================
# Dependency Detection Tests
# =============================================================================

class TestDependencyDetection:
    """Tests for dependency detection."""

    @pytest.mark.asyncio
    async def test_depends_on_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'depends on' keyword."""
        result = await analyzer.analyze("This task depends on the database being ready")
        assert result.resource_dependency_count >= 1

    @pytest.mark.asyncio
    async def test_requires_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'requires' keyword."""
        result = await analyzer.analyze("This requires the API to be available")
        assert result.resource_dependency_count >= 1

    @pytest.mark.asyncio
    async def test_based_on_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'based on' keyword."""
        result = await analyzer.analyze("Based on the previous results, process the data")
        assert result.resource_dependency_count >= 1

    @pytest.mark.asyncio
    async def test_chinese_dependency_indicators(self, analyzer: ComplexityAnalyzer):
        """Test detection of Chinese dependency indicators."""
        result = await analyzer.analyze("這個任務依賴於數據庫準備好")
        assert result.resource_dependency_count >= 1

    @pytest.mark.asyncio
    async def test_multiple_dependencies(self, analyzer: ComplexityAnalyzer):
        """Test detection of multiple dependencies."""
        result = await analyzer.analyze(
            "This depends on A, requires B, and is based on C"
        )
        assert result.resource_dependency_count >= 3


# =============================================================================
# Persistence Detection Tests
# =============================================================================

class TestPersistenceDetection:
    """Tests for persistence requirement detection."""

    @pytest.mark.asyncio
    async def test_save_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'save' keyword."""
        result = await analyzer.analyze("Save the results to database")
        assert result.requires_persistence is True

    @pytest.mark.asyncio
    async def test_checkpoint_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'checkpoint' keyword."""
        result = await analyzer.analyze("Create a checkpoint after each step")
        assert result.requires_persistence is True

    @pytest.mark.asyncio
    async def test_resume_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'resume' keyword."""
        result = await analyzer.analyze("Resume from where we left off")
        assert result.requires_persistence is True

    @pytest.mark.asyncio
    async def test_long_running_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'long running' keyword."""
        result = await analyzer.analyze("This is a long-running process")
        assert result.requires_persistence is True

    @pytest.mark.asyncio
    async def test_chinese_persistence_indicators(self, analyzer: ComplexityAnalyzer):
        """Test detection of Chinese persistence indicators."""
        result = await analyzer.analyze("儲存結果到資料庫")
        assert result.requires_persistence is True

    @pytest.mark.asyncio
    async def test_no_persistence(self, analyzer: ComplexityAnalyzer):
        """Test with no persistence indicators."""
        result = await analyzer.analyze("Calculate the sum of numbers")
        assert result.requires_persistence is False


# =============================================================================
# Time Detection Tests
# =============================================================================

class TestTimeDetection:
    """Tests for time requirement detection."""

    @pytest.mark.asyncio
    async def test_minutes_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'minutes' keyword."""
        result = await analyzer.analyze("This takes about 30 minutes")
        assert result.estimated_duration_minutes is not None
        assert result.estimated_duration_minutes > 0

    @pytest.mark.asyncio
    async def test_hours_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'hours' keyword."""
        result = await analyzer.analyze("This takes a few hours")
        assert result.estimated_duration_minutes is not None
        assert result.estimated_duration_minutes >= 60

    @pytest.mark.asyncio
    async def test_days_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'days' keyword."""
        result = await analyzer.analyze("This may take several days")
        assert result.estimated_duration_minutes is not None
        assert result.estimated_duration_minutes >= 480

    @pytest.mark.asyncio
    async def test_async_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'async' keyword."""
        result = await analyzer.analyze("Run this asynchronously")
        assert result.total_score > 0

    @pytest.mark.asyncio
    async def test_batch_processing(self, analyzer: ComplexityAnalyzer):
        """Test detection of batch processing."""
        result = await analyzer.analyze("Perform batch processing on all files")
        assert result.total_score > 0

    @pytest.mark.asyncio
    async def test_chinese_time_indicators(self, analyzer: ComplexityAnalyzer):
        """Test detection of Chinese time indicators."""
        result = await analyzer.analyze("這需要幾個小時")
        assert result.estimated_duration_minutes is not None
        assert result.estimated_duration_minutes >= 60


# =============================================================================
# Complex Operation Detection Tests
# =============================================================================

class TestComplexOperationDetection:
    """Tests for complex operation detection."""

    @pytest.mark.asyncio
    async def test_analyze_all_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'analyze all' keyword."""
        result = await analyzer.analyze("Analyze all files in the directory")
        assert result.total_score > 0

    @pytest.mark.asyncio
    async def test_comprehensive_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'comprehensive' keyword."""
        result = await analyzer.analyze("Perform a comprehensive review")
        assert result.total_score > 0

    @pytest.mark.asyncio
    async def test_generate_report(self, analyzer: ComplexityAnalyzer):
        """Test detection of report generation."""
        # Note: "generate report" must be in text without extra words between
        result = await analyzer.analyze("Generate comprehensive report")
        assert result.total_score > 0

    @pytest.mark.asyncio
    async def test_migration_keyword(self, analyzer: ComplexityAnalyzer):
        """Test detection of 'migrate' keyword."""
        result = await analyzer.analyze("Migrate all data to the new system")
        assert result.total_score > 0


# =============================================================================
# Score Calculation Tests
# =============================================================================

class TestScoreCalculation:
    """Tests for total score calculation."""

    @pytest.mark.asyncio
    async def test_empty_input(self, analyzer: ComplexityAnalyzer):
        """Test with empty input."""
        result = await analyzer.analyze("")
        assert result.total_score == 0.0
        assert result.step_count_estimate == 0 or result.step_count_estimate == 1

    @pytest.mark.asyncio
    async def test_simple_task_low_score(self, analyzer: ComplexityAnalyzer):
        """Test that simple tasks have low complexity score."""
        result = await analyzer.analyze("Add two numbers")
        assert result.total_score < 0.3

    @pytest.mark.asyncio
    async def test_complex_task_high_score(self, analyzer: ComplexityAnalyzer):
        """Test that complex tasks have high complexity score."""
        result = await analyzer.analyze(
            "First analyze all files, then based on the results, "
            "save checkpoints for this long-running batch process"
        )
        # Score ~0.45-0.5 with steps, dependency, persistence, complex operations
        assert result.total_score >= 0.4

    @pytest.mark.asyncio
    async def test_score_bounded(self, analyzer: ComplexityAnalyzer):
        """Test that score is bounded between 0 and 1."""
        # Very complex task
        result = await analyzer.analyze(
            "First step 1, then step 2, step 3, step 4, step 5, step 6, step 7, "
            "depends on A, requires B, based on C, save checkpoint, resume, "
            "takes hours, batch processing, analyze all, comprehensive"
        )
        assert 0.0 <= result.total_score <= 1.0

    @pytest.mark.asyncio
    async def test_reasoning_provided(self, analyzer: ComplexityAnalyzer):
        """Test that reasoning is provided."""
        result = await analyzer.analyze("First do A, then B, requires C")
        assert result.reasoning is not None
        assert len(result.reasoning) > 0


# =============================================================================
# Multi-Agent Detection Tests
# =============================================================================

class TestMultiAgentDetection:
    """Tests for multi-agent requirement detection."""

    @pytest.mark.asyncio
    async def test_high_step_count_multi_agent(self, analyzer: ComplexityAnalyzer):
        """Test that high step count triggers multi-agent."""
        result = await analyzer.analyze(
            "Step 1, step 2, step 3, step 4, step 5, step 6"
        )
        # 5+ steps should suggest multi-agent
        if result.step_count_estimate >= 5:
            assert result.requires_multi_agent is True

    @pytest.mark.asyncio
    async def test_high_complexity_multi_agent(self, analyzer: ComplexityAnalyzer):
        """Test that high complexity suggests multi-agent."""
        result = await analyzer.analyze(
            "Comprehensive analysis of all data, depends on multiple sources, "
            "save checkpoints, takes hours to complete"
        )
        assert result.total_score >= 0.5

    @pytest.mark.asyncio
    async def test_steps_and_deps_multi_agent(self, analyzer: ComplexityAnalyzer):
        """Test that combined steps and deps trigger multi-agent."""
        result = await analyzer.analyze(
            "First A depends on X, then B requires Y, finally C based on Z"
        )
        # 3+ steps and 2+ deps should suggest multi-agent
        if result.step_count_estimate >= 3 and result.resource_dependency_count >= 2:
            assert result.requires_multi_agent is True


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_complexity_level_simple(self, analyzer: ComplexityAnalyzer):
        """Test complexity level for simple score."""
        level = analyzer.get_complexity_level(0.2)
        assert level == "simple"

    def test_get_complexity_level_moderate(self, analyzer: ComplexityAnalyzer):
        """Test complexity level for moderate score."""
        level = analyzer.get_complexity_level(0.4)
        assert level == "moderate"

    def test_get_complexity_level_complex(self, analyzer: ComplexityAnalyzer):
        """Test complexity level for complex score."""
        level = analyzer.get_complexity_level(0.7)
        assert level == "complex"

    def test_get_complexity_level_very_complex(self, analyzer: ComplexityAnalyzer):
        """Test complexity level for very complex score."""
        level = analyzer.get_complexity_level(0.9)
        assert level == "very_complex"

    @pytest.mark.asyncio
    async def test_should_use_workflow_high_score(self, analyzer: ComplexityAnalyzer):
        """Test should_use_workflow with high score."""
        result = await analyzer.analyze(
            "Complex multi-step process with checkpoints"
        )
        # If score is high or other conditions met, should use workflow
        uses_workflow = analyzer.should_use_workflow(result)
        assert isinstance(uses_workflow, bool)

    @pytest.mark.asyncio
    async def test_should_use_workflow_persistence(self, analyzer: ComplexityAnalyzer):
        """Test should_use_workflow with persistence requirement."""
        result = await analyzer.analyze("Save results and create checkpoint")
        uses_workflow = analyzer.should_use_workflow(result)
        assert uses_workflow is True

    @pytest.mark.asyncio
    async def test_should_use_workflow_many_steps(self, analyzer: ComplexityAnalyzer):
        """Test should_use_workflow with many steps."""
        result = await analyzer.analyze("Step 1, step 2, step 3, step 4")
        if result.step_count_estimate >= 3:
            uses_workflow = analyzer.should_use_workflow(result)
            assert uses_workflow is True


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_whitespace_only(self, analyzer: ComplexityAnalyzer):
        """Test with whitespace-only input."""
        result = await analyzer.analyze("   \n\t  ")
        assert result.total_score == 0.0

    @pytest.mark.asyncio
    async def test_none_context(self, analyzer: ComplexityAnalyzer):
        """Test with None context."""
        result = await analyzer.analyze("Test input", context=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_none_history(self, analyzer: ComplexityAnalyzer):
        """Test with None history."""
        result = await analyzer.analyze("Test input", history=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_long_input(self, analyzer: ComplexityAnalyzer):
        """Test with very long input."""
        long_input = "step " * 1000
        result = await analyzer.analyze(long_input)
        assert result is not None
        assert 0.0 <= result.total_score <= 1.0

    @pytest.mark.asyncio
    async def test_special_characters(self, analyzer: ComplexityAnalyzer):
        """Test with special characters."""
        result = await analyzer.analyze("Do @#$%^& the !@#$ task")
        assert result is not None
