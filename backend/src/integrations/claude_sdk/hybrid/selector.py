"""Framework selection for Hybrid Orchestrator.

Sprint 50: S50-3 - Hybrid Orchestrator (12 pts)

This module provides intelligent framework selection logic
based on task type, capabilities, and execution context.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .capability import CapabilityMatcher
from .types import Framework, TaskAnalysis, TaskCapability


class SelectionStrategy(Enum):
    """Framework selection strategy."""

    # Always prefer one framework
    PREFER_CLAUDE = "prefer_claude"
    PREFER_MICROSOFT = "prefer_microsoft"

    # Dynamic selection based on task
    CAPABILITY_BASED = "capability_based"

    # Cost-optimized selection
    COST_OPTIMIZED = "cost_optimized"

    # Performance-optimized selection
    PERFORMANCE_OPTIMIZED = "performance_optimized"


@dataclass
class SelectionContext:
    """Context for framework selection decision."""

    # Task analysis results
    task_analysis: Optional[TaskAnalysis] = None

    # Current session state
    session_framework: Optional[str] = None
    session_message_count: int = 0

    # Resource constraints
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[float] = None

    # Feature flags
    allow_framework_switch: bool = True
    prefer_consistency: bool = False

    # Cost tracking
    cost_weight: float = 0.5
    performance_weight: float = 0.5


@dataclass
class SelectionResult:
    """Result of framework selection."""

    framework: str
    confidence: float
    reason: str
    alternative: Optional[str] = None
    switch_recommended: bool = False
    warnings: List[str] = field(default_factory=list)


class FrameworkSelector:
    """Selects the optimal framework for task execution.

    Uses task analysis, context, and strategy to determine
    which framework should handle a given task.
    """

    # Task type to framework mapping
    TASK_FRAMEWORK_MAP: Dict[str, str] = {
        # Multi-agent patterns → Microsoft
        "multi_agent_collaboration": "microsoft_agent_framework",
        "agent_handoff": "microsoft_agent_framework",
        "task_planning": "microsoft_agent_framework",
        "workflow_orchestration": "microsoft_agent_framework",

        # Tool-heavy patterns → Claude SDK
        "file_manipulation": "claude_sdk",
        "code_execution": "claude_sdk",
        "web_browsing": "claude_sdk",
        "document_analysis": "claude_sdk",

        # Conversation patterns → Claude SDK
        "general_conversation": "claude_sdk",
        "question_answering": "claude_sdk",
        "explanation": "claude_sdk",
    }

    # Framework characteristics
    FRAMEWORK_PROFILES: Dict[str, Dict[str, Any]] = {
        "microsoft_agent_framework": {
            "strengths": [
                "multi-agent coordination",
                "complex workflows",
                "enterprise integration",
                "structured planning",
            ],
            "avg_latency_ms": 2000,
            "cost_per_1k_tokens": 0.015,
            "supports_streaming": True,
            "max_agents": 10,
        },
        "claude_sdk": {
            "strengths": [
                "file operations",
                "code execution",
                "web search",
                "natural conversation",
            ],
            "avg_latency_ms": 1500,
            "cost_per_1k_tokens": 0.012,
            "supports_streaming": True,
            "max_tools": 50,
        },
    }

    def __init__(
        self,
        strategy: SelectionStrategy = SelectionStrategy.CAPABILITY_BASED,
        *,
        capability_matcher: Optional[CapabilityMatcher] = None,
        switch_threshold: float = 0.7,
        consistency_bonus: float = 0.1,
    ):
        """Initialize the framework selector.

        Args:
            strategy: Selection strategy to use.
            capability_matcher: Matcher for capability analysis.
            switch_threshold: Confidence threshold to recommend switching.
            consistency_bonus: Bonus for staying with current framework.
        """
        self._strategy = strategy
        self._matcher = capability_matcher or CapabilityMatcher()
        self._switch_threshold = switch_threshold
        self._consistency_bonus = consistency_bonus

        # Custom selection rules
        self._custom_rules: List[Callable[[str, SelectionContext], Optional[str]]] = []

    @property
    def strategy(self) -> SelectionStrategy:
        """Get current selection strategy."""
        return self._strategy

    @strategy.setter
    def strategy(self, value: SelectionStrategy) -> None:
        """Set selection strategy."""
        self._strategy = value

    def select(
        self,
        prompt: str,
        context: Optional[SelectionContext] = None,
    ) -> SelectionResult:
        """Select the best framework for a task.

        Args:
            prompt: The task prompt or description.
            context: Optional selection context.

        Returns:
            SelectionResult with framework choice and reasoning.
        """
        context = context or SelectionContext()

        # Get task analysis
        if context.task_analysis:
            analysis = context.task_analysis
        else:
            analysis = self._matcher.analyze(prompt)
            context.task_analysis = analysis

        # Apply selection strategy
        if self._strategy == SelectionStrategy.PREFER_CLAUDE:
            return self._select_prefer_claude(analysis, context)
        elif self._strategy == SelectionStrategy.PREFER_MICROSOFT:
            return self._select_prefer_microsoft(analysis, context)
        elif self._strategy == SelectionStrategy.COST_OPTIMIZED:
            return self._select_cost_optimized(analysis, context)
        elif self._strategy == SelectionStrategy.PERFORMANCE_OPTIMIZED:
            return self._select_performance_optimized(analysis, context)
        else:
            return self._select_capability_based(analysis, context)

    def _select_capability_based(
        self,
        analysis: TaskAnalysis,
        context: SelectionContext,
    ) -> SelectionResult:
        """Select based on capability matching."""
        # Check custom rules first
        for rule in self._custom_rules:
            custom_result = rule(analysis.recommended_framework, context)
            if custom_result:
                return SelectionResult(
                    framework=custom_result,
                    confidence=0.9,
                    reason="Custom rule match",
                )

        framework = analysis.recommended_framework
        confidence = analysis.confidence

        # Apply consistency bonus if we should stay with current framework
        if (
            context.prefer_consistency
            and context.session_framework
            and context.session_framework == framework
        ):
            confidence = min(0.95, confidence + self._consistency_bonus)

        # Determine if switch is recommended
        switch_recommended = False
        if context.session_framework and context.session_framework != framework:
            if confidence >= self._switch_threshold and context.allow_framework_switch:
                switch_recommended = True

        # Build reason
        if analysis.capabilities:
            cap_names = [c.value for c in list(analysis.capabilities)[:3]]
            reason = f"Capabilities detected: {', '.join(cap_names)}"
        else:
            reason = "Default selection (no specific capabilities detected)"

        # Check for warnings
        warnings = []
        if analysis.complexity > 0.8:
            warnings.append("High complexity task - may require extended processing")
        if switch_recommended:
            warnings.append(f"Framework switch from {context.session_framework}")

        # Determine alternative
        alternative = (
            "microsoft_agent_framework"
            if framework == "claude_sdk"
            else "claude_sdk"
        )

        return SelectionResult(
            framework=framework,
            confidence=confidence,
            reason=reason,
            alternative=alternative,
            switch_recommended=switch_recommended,
            warnings=warnings,
        )

    def _select_prefer_claude(
        self,
        analysis: TaskAnalysis,
        context: SelectionContext,
    ) -> SelectionResult:
        """Always prefer Claude SDK unless strong MS indicators."""
        # Only switch to MS for strong multi-agent needs
        if analysis.requires_multi_agent() and analysis.confidence > 0.8:
            return SelectionResult(
                framework="microsoft_agent_framework",
                confidence=analysis.confidence,
                reason="Strong multi-agent requirement detected",
                alternative="claude_sdk",
            )

        return SelectionResult(
            framework="claude_sdk",
            confidence=0.85,
            reason="Claude SDK preferred (strategy: prefer_claude)",
            alternative="microsoft_agent_framework",
        )

    def _select_prefer_microsoft(
        self,
        analysis: TaskAnalysis,
        context: SelectionContext,
    ) -> SelectionResult:
        """Always prefer Microsoft unless strong Claude indicators."""
        # Only switch to Claude for strong tool/file needs
        claude_strong = (
            TaskCapability.FILE_OPERATIONS in analysis.capabilities
            or TaskCapability.CODE_EXECUTION in analysis.capabilities
        ) and analysis.confidence > 0.8

        if claude_strong:
            return SelectionResult(
                framework="claude_sdk",
                confidence=analysis.confidence,
                reason="Strong file/code requirement detected",
                alternative="microsoft_agent_framework",
            )

        return SelectionResult(
            framework="microsoft_agent_framework",
            confidence=0.85,
            reason="Microsoft Agent Framework preferred (strategy: prefer_microsoft)",
            alternative="claude_sdk",
        )

    def _select_cost_optimized(
        self,
        analysis: TaskAnalysis,
        context: SelectionContext,
    ) -> SelectionResult:
        """Select based on cost optimization."""
        # Get cost profiles
        claude_cost = self.FRAMEWORK_PROFILES["claude_sdk"]["cost_per_1k_tokens"]
        ms_cost = self.FRAMEWORK_PROFILES["microsoft_agent_framework"]["cost_per_1k_tokens"]

        # Calculate weighted score (lower cost = better)
        if claude_cost <= ms_cost:
            framework = "claude_sdk"
            cost_advantage = (ms_cost - claude_cost) / ms_cost
        else:
            framework = "microsoft_agent_framework"
            cost_advantage = (claude_cost - ms_cost) / claude_cost

        # Override if capabilities strongly indicate other framework
        if framework == "claude_sdk" and analysis.requires_multi_agent():
            framework = "microsoft_agent_framework"
            cost_advantage = 0.0  # Reset advantage

        confidence = 0.7 + (cost_advantage * 0.2)

        return SelectionResult(
            framework=framework,
            confidence=confidence,
            reason=f"Cost optimized selection ({cost_advantage:.1%} advantage)",
            alternative=(
                "microsoft_agent_framework"
                if framework == "claude_sdk"
                else "claude_sdk"
            ),
        )

    def _select_performance_optimized(
        self,
        analysis: TaskAnalysis,
        context: SelectionContext,
    ) -> SelectionResult:
        """Select based on performance optimization."""
        # Get latency profiles
        claude_latency = self.FRAMEWORK_PROFILES["claude_sdk"]["avg_latency_ms"]
        ms_latency = self.FRAMEWORK_PROFILES["microsoft_agent_framework"]["avg_latency_ms"]

        # Calculate weighted score (lower latency = better)
        if claude_latency <= ms_latency:
            framework = "claude_sdk"
            perf_advantage = (ms_latency - claude_latency) / ms_latency
        else:
            framework = "microsoft_agent_framework"
            perf_advantage = (claude_latency - ms_latency) / claude_latency

        # Override if capabilities strongly indicate other framework
        if framework == "claude_sdk" and analysis.requires_multi_agent():
            framework = "microsoft_agent_framework"
            perf_advantage = 0.0

        confidence = 0.7 + (perf_advantage * 0.2)

        return SelectionResult(
            framework=framework,
            confidence=confidence,
            reason=f"Performance optimized selection ({perf_advantage:.1%} faster)",
            alternative=(
                "microsoft_agent_framework"
                if framework == "claude_sdk"
                else "claude_sdk"
            ),
        )

    def add_custom_rule(
        self,
        rule: Callable[[str, SelectionContext], Optional[str]],
    ) -> None:
        """Add a custom selection rule.

        Rules are evaluated in order. First non-None result wins.

        Args:
            rule: Function taking (recommended_framework, context) and
                  returning framework name or None.
        """
        self._custom_rules.append(rule)

    def remove_custom_rules(self) -> None:
        """Remove all custom rules."""
        self._custom_rules.clear()

    def get_framework_profile(self, framework: str) -> Dict[str, Any]:
        """Get profile information for a framework.

        Args:
            framework: Framework name.

        Returns:
            Profile dictionary with characteristics.
        """
        return self.FRAMEWORK_PROFILES.get(framework, {})

    def get_task_type_framework(self, task_type: str) -> Optional[str]:
        """Get recommended framework for a task type.

        Args:
            task_type: The task type key.

        Returns:
            Framework name or None if not mapped.
        """
        return self.TASK_FRAMEWORK_MAP.get(task_type)

    def compare_frameworks(
        self,
        prompt: str,
    ) -> Dict[str, SelectionResult]:
        """Compare all frameworks for a given prompt.

        Args:
            prompt: The task prompt.

        Returns:
            Dictionary mapping framework names to selection results.
        """
        analysis = self._matcher.analyze(prompt)
        context = SelectionContext(task_analysis=analysis)

        results = {}
        for strategy in SelectionStrategy:
            original_strategy = self._strategy
            self._strategy = strategy
            try:
                result = self.select(prompt, context)
                results[strategy.value] = result
            finally:
                self._strategy = original_strategy

        return results


def create_selector(
    strategy: SelectionStrategy = SelectionStrategy.CAPABILITY_BASED,
    *,
    switch_threshold: float = 0.7,
) -> FrameworkSelector:
    """Factory function to create a FrameworkSelector.

    Args:
        strategy: Selection strategy to use.
        switch_threshold: Confidence threshold for switching.

    Returns:
        Configured FrameworkSelector instance.
    """
    return FrameworkSelector(
        strategy=strategy,
        switch_threshold=switch_threshold,
    )
