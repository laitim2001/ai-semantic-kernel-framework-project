# =============================================================================
# IPA Platform - Complexity Analyzer
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Analyzes task complexity to determine if workflow mode is needed.
# High complexity tasks (multiple steps, dependencies, persistence)
# should use Microsoft Agent Framework for proper orchestration.
#
# Complexity Factors:
#   - Step count estimation
#   - Resource/data dependencies
#   - Time requirements
#   - Persistence needs
#   - Checkpoint requirements
#
# Dependencies:
#   - models.py (ComplexityScore)
# =============================================================================

import logging
import re
from typing import Dict, List, Optional, Pattern, Tuple

from src.integrations.hybrid.intent.models import (
    ComplexityScore,
    Message,
    SessionContext,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Complexity Indicators
# =============================================================================

# Words that indicate multiple steps
STEP_INDICATORS: List[str] = [
    # English
    "first", "then", "next", "after", "finally", "lastly",
    "step 1", "step 2", "step 3",
    "phase 1", "phase 2", "phase 3",
    "stage 1", "stage 2", "stage 3",
    "followed by", "subsequently",
    "before that", "after that",
    # Chinese
    "首先", "然後", "接著", "最後", "之後",
    "步驟一", "步驟二", "步驟三",
    "第一步", "第二步", "第三步",
    "階段一", "階段二", "階段三",
    "接下來",
]

# Patterns that indicate step counts
STEP_COUNT_PATTERNS: List[str] = [
    r"\b(\d+)\s+steps?\b",
    r"\b(\d+)\s+tasks?\b",
    r"\b(\d+)\s+phases?\b",
    r"\b(\d+)\s+stages?\b",
    r"\b(\d+)\s+個步驟\b",
    r"\b(\d+)\s+個任務\b",
    r"\b(\d+)\s+個階段\b",
]

# Words indicating dependencies or resources
DEPENDENCY_INDICATORS: List[str] = [
    # English
    "depends on", "requires", "needs", "based on",
    "using data from", "from the result",
    "after completing", "once finished",
    "prerequisite", "dependency",
    # Chinese
    "依賴", "需要", "基於", "根據",
    "使用數據", "從結果",
    "完成後", "完成之後",
    "前提", "依存",
]

# Words indicating persistence or checkpointing
PERSISTENCE_INDICATORS: List[str] = [
    # English
    "save", "store", "persist", "checkpoint",
    "remember", "maintain state",
    "long running", "long-running",
    "resume", "continue from",
    "rollback", "undo", "revert",
    # Chinese
    "儲存", "保存", "持久化", "檢查點",
    "記住", "維護狀態",
    "長時間運行", "恢復", "繼續",
    "回滾", "撤銷", "還原",
]

# Words indicating time-consuming operations
TIME_INDICATORS: List[str] = [
    # English
    "minutes", "hours", "days",
    "takes time", "time-consuming",
    "wait for", "waiting",
    "async", "asynchronous",
    "background", "scheduled",
    "batch processing", "bulk",
    # Chinese
    "分鐘", "小時", "天",
    "需要時間", "耗時",
    "等待", "異步",
    "背景", "排程",
    "批次處理", "大量",
]

# Words indicating complex operations
COMPLEX_OPERATION_INDICATORS: List[str] = [
    # English
    "analyze all", "process all", "scan entire",
    "comprehensive", "thorough", "complete",
    "every file", "all files", "all data",
    "entire database", "full scan",
    "generate report", "create report",
    "migrate", "transform", "convert all",
    # Chinese
    "分析所有", "處理所有", "掃描整個",
    "全面", "徹底", "完整",
    "每個檔案", "所有檔案", "所有數據",
    "整個資料庫", "完整掃描",
    "生成報告", "建立報告",
    "遷移", "轉換所有",
]


class ComplexityAnalyzer:
    """
    Analyzes task complexity to help determine execution mode.

    Uses heuristics based on keyword patterns to estimate:
    - Number of steps required
    - Resource dependencies
    - Time requirements
    - Persistence needs

    Higher complexity scores suggest workflow mode is more appropriate.

    Complexity Thresholds:
        - 0.0 - 0.3: Simple (chat mode)
        - 0.3 - 0.6: Moderate (could go either way)
        - 0.6 - 0.8: Complex (workflow recommended)
        - 0.8 - 1.0: Very Complex (workflow required)

    Example:
        >>> analyzer = ComplexityAnalyzer()
        >>> score = await analyzer.analyze("First, process all files. Then generate a report.")
        >>> print(f"Complexity: {score.total_score}, Steps: {score.step_count_estimate}")
    """

    def __init__(
        self,
        step_weight: float = 0.25,
        dependency_weight: float = 0.25,
        persistence_weight: float = 0.25,
        time_weight: float = 0.25,
    ):
        """
        Initialize the complexity analyzer.

        Args:
            step_weight: Weight for step count factor (0.0-1.0)
            dependency_weight: Weight for dependency factor (0.0-1.0)
            persistence_weight: Weight for persistence factor (0.0-1.0)
            time_weight: Weight for time factor (0.0-1.0)
        """
        # Normalize weights
        total = step_weight + dependency_weight + persistence_weight + time_weight
        self.step_weight = step_weight / total
        self.dependency_weight = dependency_weight / total
        self.persistence_weight = persistence_weight / total
        self.time_weight = time_weight / total

        # Compile patterns
        self.step_count_patterns: List[Pattern] = [
            re.compile(p, re.IGNORECASE) for p in STEP_COUNT_PATTERNS
        ]

        # Build keyword sets
        self.step_indicators = {s.lower() for s in STEP_INDICATORS}
        self.dependency_indicators = {d.lower() for d in DEPENDENCY_INDICATORS}
        self.persistence_indicators = {p.lower() for p in PERSISTENCE_INDICATORS}
        self.time_indicators = {t.lower() for t in TIME_INDICATORS}
        self.complex_op_indicators = {c.lower() for c in COMPLEX_OPERATION_INDICATORS}

        logger.debug("ComplexityAnalyzer initialized")

    async def analyze(
        self,
        input_text: str,
        context: Optional[SessionContext] = None,
        history: Optional[List[Message]] = None,
    ) -> ComplexityScore:
        """
        Analyze the complexity of a task described in the input text.

        Args:
            input_text: The user's input describing the task
            context: Optional session context for additional signals
            history: Optional conversation history

        Returns:
            ComplexityScore with detailed complexity analysis
        """
        if not input_text or not input_text.strip():
            return ComplexityScore(
                total_score=0.0,
                reasoning="Empty input has no complexity",
            )

        text_lower = input_text.lower()

        # Analyze each factor
        step_score, step_count = self._analyze_steps(input_text, text_lower)
        dep_score, dep_count = self._analyze_dependencies(text_lower)
        persist_score, requires_persist = self._analyze_persistence(text_lower)
        time_score, est_minutes = self._analyze_time(text_lower)
        complex_op_score = self._analyze_complex_operations(text_lower)

        # Calculate weighted total
        total_score = (
            step_score * self.step_weight +
            dep_score * self.dependency_weight +
            persist_score * self.persistence_weight +
            time_score * self.time_weight +
            complex_op_score * 0.15  # Bonus for complex operations
        )

        # Clamp to [0, 1]
        total_score = min(1.0, max(0.0, total_score))

        # Determine if multi-agent is needed
        requires_multi_agent = (
            step_count >= 5 or
            total_score >= 0.7 or
            (step_count >= 3 and dep_count >= 2)
        )

        # Build reasoning
        reasoning_parts = []
        if step_count > 1:
            reasoning_parts.append(f"~{step_count} steps detected")
        if dep_count > 0:
            reasoning_parts.append(f"{dep_count} dependencies")
        if requires_persist:
            reasoning_parts.append("persistence needed")
        if est_minutes > 0:
            reasoning_parts.append(f"~{est_minutes}min estimated")
        if complex_op_score > 0:
            reasoning_parts.append("complex operations")

        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Simple task"

        return ComplexityScore(
            total_score=total_score,
            step_count_estimate=step_count,
            resource_dependency_count=dep_count,
            estimated_duration_minutes=est_minutes if est_minutes > 0 else None,
            requires_persistence=requires_persist,
            requires_multi_agent=requires_multi_agent,
            reasoning=reasoning,
        )

    def _analyze_steps(self, text: str, text_lower: str) -> Tuple[float, int]:
        """
        Analyze step indicators and estimate step count.

        Returns:
            Tuple of (step_score, estimated_step_count)
        """
        step_count = 1  # Minimum 1 step

        # Check for explicit step counts in patterns
        for pattern in self.step_count_patterns:
            match = pattern.search(text)
            if match:
                try:
                    explicit_count = int(match.group(1))
                    step_count = max(step_count, explicit_count)
                except (ValueError, IndexError):
                    pass

        # Count step indicators
        indicator_count = sum(
            1 for indicator in self.step_indicators
            if indicator in text_lower
        )

        # Estimate steps from indicator count
        if indicator_count >= 5:
            step_count = max(step_count, 6)
        elif indicator_count >= 3:
            step_count = max(step_count, 4)
        elif indicator_count >= 2:
            step_count = max(step_count, 3)
        elif indicator_count >= 1:
            step_count = max(step_count, 2)

        # Calculate score (1 step = 0.0, 10+ steps = 1.0)
        score = min(1.0, (step_count - 1) / 9.0)

        return score, step_count

    def _analyze_dependencies(self, text_lower: str) -> Tuple[float, int]:
        """
        Analyze dependency indicators.

        Returns:
            Tuple of (dependency_score, dependency_count)
        """
        dep_count = sum(
            1 for dep in self.dependency_indicators
            if dep in text_lower
        )

        # Score: 0 deps = 0.0, 5+ deps = 1.0
        score = min(1.0, dep_count / 5.0)

        return score, dep_count

    def _analyze_persistence(self, text_lower: str) -> Tuple[float, bool]:
        """
        Analyze persistence requirements.

        Returns:
            Tuple of (persistence_score, requires_persistence)
        """
        persist_count = sum(
            1 for p in self.persistence_indicators
            if p in text_lower
        )

        requires_persist = persist_count >= 1

        # Score: 0 = 0.0, 1 = 0.5, 2+ = 1.0
        if persist_count >= 2:
            score = 1.0
        elif persist_count == 1:
            score = 0.5
        else:
            score = 0.0

        return score, requires_persist

    def _analyze_time(self, text_lower: str) -> Tuple[float, float]:
        """
        Analyze time requirements.

        Returns:
            Tuple of (time_score, estimated_minutes)
        """
        time_count = sum(
            1 for t in self.time_indicators
            if t in text_lower
        )

        # Estimate duration based on indicators
        estimated_minutes = 0.0
        if "hours" in text_lower or "小時" in text_lower:
            estimated_minutes = 60.0
        elif "minutes" in text_lower or "分鐘" in text_lower:
            estimated_minutes = 15.0
        elif "days" in text_lower or "天" in text_lower:
            estimated_minutes = 480.0  # 8 hours
        elif time_count > 0:
            estimated_minutes = 5.0

        # Score: 0 time indicators = 0.0, 3+ = 1.0
        score = min(1.0, time_count / 3.0)

        return score, estimated_minutes

    def _analyze_complex_operations(self, text_lower: str) -> float:
        """
        Analyze presence of complex operation indicators.

        Returns:
            Score from 0.0 to 1.0
        """
        complex_count = sum(
            1 for c in self.complex_op_indicators
            if c in text_lower
        )

        # Score: 0 = 0.0, 3+ = 1.0
        return min(1.0, complex_count / 3.0)

    def get_complexity_level(self, score: float) -> str:
        """
        Get human-readable complexity level from score.

        Args:
            score: Complexity score (0.0-1.0)

        Returns:
            Complexity level string
        """
        if score < 0.3:
            return "simple"
        elif score < 0.6:
            return "moderate"
        elif score < 0.8:
            return "complex"
        else:
            return "very_complex"

    def should_use_workflow(self, score: ComplexityScore) -> bool:
        """
        Determine if workflow mode should be used based on complexity.

        Args:
            score: ComplexityScore from analysis

        Returns:
            True if workflow mode is recommended
        """
        return (
            score.total_score >= 0.5 or
            score.step_count_estimate >= 3 or
            score.requires_persistence or
            score.requires_multi_agent
        )
