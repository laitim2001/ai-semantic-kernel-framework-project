# =============================================================================
# IPA Platform - Smart Fallback System
# =============================================================================
# Sprint 80: S80-3 - Trial-and-Error 智能回退 (6 pts)
#
# This module provides intelligent fallback mechanisms for autonomous
# operations, including failure analysis and alternative generation.
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

from .retry import (
    DEFAULT_RETRY_CONFIG,
    FailureType,
    RetryConfig,
    RetryPolicy,
    RetryResult,
)
from .types import PlanStep, StepStatus


logger = logging.getLogger(__name__)


class FallbackStrategy(str, Enum):
    """Available fallback strategies."""

    RETRY = "retry"  # Simple retry with backoff
    ALTERNATIVE = "alternative"  # Try alternative action
    SKIP = "skip"  # Skip the step
    ESCALATE = "escalate"  # Escalate to human
    ROLLBACK = "rollback"  # Rollback and retry earlier step
    ABORT = "abort"  # Abort the entire plan


@dataclass
class FailureAnalysis:
    """Analysis of a failure."""

    failure_type: FailureType
    error_category: str
    root_cause: str
    is_recoverable: bool
    recommended_strategy: FallbackStrategy
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "failure_type": self.failure_type.value,
            "error_category": self.error_category,
            "root_cause": self.root_cause,
            "is_recoverable": self.is_recoverable,
            "recommended_strategy": self.recommended_strategy.value,
            "confidence": self.confidence,
            "details": self.details,
        }


@dataclass
class FallbackAction:
    """An alternative action to take on failure."""

    strategy: FallbackStrategy
    action_description: str
    modified_parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_success_probability: float = 0.5
    risk_level: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy": self.strategy.value,
            "action_description": self.action_description,
            "modified_parameters": self.modified_parameters,
            "estimated_success_probability": self.estimated_success_probability,
            "risk_level": self.risk_level,
        }


@dataclass
class FailurePattern:
    """A recorded failure pattern for learning."""

    pattern_id: str
    error_signature: str
    failure_type: FailureType
    successful_recovery: Optional[FallbackStrategy] = None
    occurrence_count: int = 1
    last_seen: datetime = field(default_factory=datetime.utcnow)
    context_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "error_signature": self.error_signature,
            "failure_type": self.failure_type.value,
            "successful_recovery": self.successful_recovery.value if self.successful_recovery else None,
            "occurrence_count": self.occurrence_count,
            "last_seen": self.last_seen.isoformat(),
            "context_patterns": self.context_patterns,
        }


@dataclass
class FallbackResult:
    """Result of fallback execution."""

    success: bool
    strategy_used: FallbackStrategy
    attempts: int
    result: Optional[Any] = None
    error: Optional[str] = None
    fallback_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "strategy_used": self.strategy_used.value,
            "attempts": self.attempts,
            "error": self.error,
            "fallback_history": self.fallback_history,
        }


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""

    max_fallback_attempts: int = 3
    enable_alternative_generation: bool = True
    enable_pattern_learning: bool = True
    retry_config: RetryConfig = field(default_factory=lambda: DEFAULT_RETRY_CONFIG)
    escalation_threshold: int = 2  # Escalate after N failed fallbacks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_fallback_attempts": self.max_fallback_attempts,
            "enable_alternative_generation": self.enable_alternative_generation,
            "enable_pattern_learning": self.enable_pattern_learning,
            "retry_config": self.retry_config.to_dict(),
            "escalation_threshold": self.escalation_threshold,
        }


# Default configuration
DEFAULT_FALLBACK_CONFIG = FallbackConfig()


T = TypeVar("T")


class SmartFallback:
    """
    Smart fallback system for autonomous operations.

    Provides intelligent error handling with:
    - Failure analysis and classification
    - Alternative action generation
    - Pattern learning from past failures
    - Multi-strategy fallback chains
    """

    def __init__(self, config: Optional[FallbackConfig] = None):
        """
        Initialize smart fallback.

        Args:
            config: Fallback configuration. Uses defaults if not provided.
        """
        self.config = config or DEFAULT_FALLBACK_CONFIG
        self._retry_policy = RetryPolicy(self.config.retry_config)
        self._failure_patterns: Dict[str, FailurePattern] = {}
        self._fallback_history: List[Dict[str, Any]] = []

    def analyze_failure(
        self,
        error: Exception,
        step: Optional[PlanStep] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureAnalysis:
        """
        Analyze a failure to determine best recovery strategy.

        Args:
            error: The exception that occurred.
            step: The plan step that failed (if applicable).
            context: Additional context about the failure.

        Returns:
            FailureAnalysis with recommended strategy.
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Classify failure type
        failure_type = self._retry_policy.classify_failure(error)

        # Determine error category
        error_category = self._categorize_error(error_str, error_type)

        # Analyze root cause
        root_cause = self._analyze_root_cause(error_str, error_category, context)

        # Determine if recoverable
        is_recoverable = failure_type != FailureType.FATAL

        # Get recommended strategy
        strategy, confidence = self._recommend_strategy(
            failure_type, error_category, step, context
        )

        return FailureAnalysis(
            failure_type=failure_type,
            error_category=error_category,
            root_cause=root_cause,
            is_recoverable=is_recoverable,
            recommended_strategy=strategy,
            confidence=confidence,
            details={
                "error_type": error_type,
                "error_message": str(error),
                "step_action": step.action if step else None,
            },
        )

    def _categorize_error(self, error_str: str, error_type: str) -> str:
        """Categorize error into high-level category."""
        categories = {
            "network": ["connection", "timeout", "network", "socket", "dns"],
            "authentication": ["auth", "token", "credential", "permission", "forbidden"],
            "resource": ["not_found", "404", "missing", "unavailable"],
            "rate_limit": ["rate", "limit", "429", "throttle", "quota"],
            "validation": ["invalid", "validation", "parameter", "format"],
            "service": ["service", "500", "503", "504", "internal"],
            "configuration": ["config", "setting", "environment"],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in error_str or keyword in error_type.lower():
                    return category

        return "unknown"

    def _analyze_root_cause(
        self,
        error_str: str,
        error_category: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Analyze and describe root cause."""
        root_causes = {
            "network": "網絡連接問題，可能是暫時性的網絡不穩定或目標服務不可達",
            "authentication": "認證失敗，可能是憑證過期或權限不足",
            "resource": "請求的資源不存在或已被刪除",
            "rate_limit": "請求過於頻繁，已觸發速率限制",
            "validation": "請求參數驗證失敗，需要檢查輸入數據",
            "service": "目標服務內部錯誤，可能是暫時性問題",
            "configuration": "配置錯誤，需要檢查系統設置",
        }

        return root_causes.get(error_category, f"未知錯誤: {error_str[:100]}")

    def _recommend_strategy(
        self,
        failure_type: FailureType,
        error_category: str,
        step: Optional[PlanStep],
        context: Optional[Dict[str, Any]],
    ) -> tuple[FallbackStrategy, float]:
        """Recommend fallback strategy based on analysis."""
        # Check learned patterns first
        if self.config.enable_pattern_learning:
            pattern_strategy = self._check_learned_patterns(error_category)
            if pattern_strategy:
                return pattern_strategy, 0.8

        # Default strategy recommendations
        strategy_map = {
            "network": (FallbackStrategy.RETRY, 0.9),
            "rate_limit": (FallbackStrategy.RETRY, 0.95),
            "service": (FallbackStrategy.RETRY, 0.85),
            "authentication": (FallbackStrategy.ESCALATE, 0.9),
            "resource": (FallbackStrategy.ALTERNATIVE, 0.7),
            "validation": (FallbackStrategy.ALTERNATIVE, 0.8),
            "configuration": (FallbackStrategy.ESCALATE, 0.85),
        }

        # Check if step has a defined fallback
        if step and step.fallback_action:
            return FallbackStrategy.ALTERNATIVE, 0.85

        # Fatal errors should abort
        if failure_type == FailureType.FATAL:
            return FallbackStrategy.ABORT, 0.95

        return strategy_map.get(error_category, (FallbackStrategy.RETRY, 0.6))

    def _check_learned_patterns(self, error_category: str) -> Optional[FallbackStrategy]:
        """Check if we have a learned pattern for this error."""
        for pattern in self._failure_patterns.values():
            if error_category in pattern.context_patterns and pattern.successful_recovery:
                return pattern.successful_recovery
        return None

    def generate_alternative(
        self,
        original_step: PlanStep,
        analysis: FailureAnalysis,
    ) -> FallbackAction:
        """
        Generate an alternative action based on failure analysis.

        Args:
            original_step: The step that failed.
            analysis: Analysis of the failure.

        Returns:
            FallbackAction with alternative approach.
        """
        if not self.config.enable_alternative_generation:
            return FallbackAction(
                strategy=FallbackStrategy.RETRY,
                action_description="重試原始操作",
            )

        # Use step's defined fallback if available
        if original_step.fallback_action:
            return FallbackAction(
                strategy=FallbackStrategy.ALTERNATIVE,
                action_description=original_step.fallback_action,
                estimated_success_probability=0.7,
            )

        # Generate based on error category
        alternatives = {
            "network": FallbackAction(
                strategy=FallbackStrategy.RETRY,
                action_description="等待後重試網絡操作",
                modified_parameters={"timeout": original_step.estimated_duration_seconds * 2},
                estimated_success_probability=0.8,
            ),
            "rate_limit": FallbackAction(
                strategy=FallbackStrategy.RETRY,
                action_description="延長等待時間後重試",
                modified_parameters={"delay_multiplier": 2.0},
                estimated_success_probability=0.9,
            ),
            "resource": FallbackAction(
                strategy=FallbackStrategy.SKIP,
                action_description="跳過此步驟，繼續執行後續操作",
                estimated_success_probability=0.6,
                risk_level="medium",
            ),
            "validation": FallbackAction(
                strategy=FallbackStrategy.ALTERNATIVE,
                action_description="使用默認參數重試",
                modified_parameters={"use_defaults": True},
                estimated_success_probability=0.7,
            ),
            "authentication": FallbackAction(
                strategy=FallbackStrategy.ESCALATE,
                action_description="需要人工介入更新憑證",
                estimated_success_probability=0.95,
                risk_level="low",
            ),
        }

        return alternatives.get(
            analysis.error_category,
            FallbackAction(
                strategy=FallbackStrategy.RETRY,
                action_description="重試原始操作",
                estimated_success_probability=0.5,
            ),
        )

    def record_failure_pattern(
        self,
        error: Exception,
        analysis: FailureAnalysis,
        recovery_success: bool,
        recovery_strategy: FallbackStrategy,
    ) -> None:
        """
        Record a failure pattern for future learning.

        Args:
            error: The exception that occurred.
            analysis: Analysis of the failure.
            recovery_success: Whether recovery was successful.
            recovery_strategy: Strategy that was used.
        """
        if not self.config.enable_pattern_learning:
            return

        error_signature = f"{type(error).__name__}:{analysis.error_category}"
        pattern_id = f"pattern_{error_signature}"

        if pattern_id in self._failure_patterns:
            # Update existing pattern
            pattern = self._failure_patterns[pattern_id]
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.utcnow()

            if recovery_success:
                pattern.successful_recovery = recovery_strategy
        else:
            # Create new pattern
            self._failure_patterns[pattern_id] = FailurePattern(
                pattern_id=pattern_id,
                error_signature=error_signature,
                failure_type=analysis.failure_type,
                successful_recovery=recovery_strategy if recovery_success else None,
                context_patterns=[analysis.error_category],
            )

        logger.debug(
            f"Recorded failure pattern: {pattern_id} "
            f"(success={recovery_success}, strategy={recovery_strategy.value})"
        )

    async def execute_with_fallback(
        self,
        primary_action: Callable[[], T],
        step: Optional[PlanStep] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FallbackResult:
        """
        Execute operation with smart fallback handling.

        Args:
            primary_action: Primary async callable to execute.
            step: Plan step being executed (if applicable).
            context: Additional context for fallback decisions.

        Returns:
            FallbackResult with execution status.
        """
        fallback_history = []
        last_error: Optional[Exception] = None
        last_analysis: Optional[FailureAnalysis] = None

        for attempt in range(1, self.config.max_fallback_attempts + 1):
            try:
                logger.debug(f"Fallback attempt {attempt}/{self.config.max_fallback_attempts}")

                # Try with retry policy first
                retry_result = await self._retry_policy.execute_with_retry(
                    primary_action,
                    operation_name=step.action if step else "operation",
                )

                if retry_result.success:
                    # Success! Record pattern if we recovered
                    if last_analysis:
                        self.record_failure_pattern(
                            error=last_error,
                            analysis=last_analysis,
                            recovery_success=True,
                            recovery_strategy=FallbackStrategy.RETRY,
                        )

                    return FallbackResult(
                        success=True,
                        strategy_used=FallbackStrategy.RETRY,
                        attempts=attempt,
                        result=retry_result.result,
                        fallback_history=fallback_history,
                    )

                # Retry failed, analyze and try fallback
                if retry_result.final_error:
                    last_error = Exception(retry_result.final_error)
                    last_analysis = self.analyze_failure(last_error, step, context)

                    fallback_history.append({
                        "attempt": attempt,
                        "strategy": "retry",
                        "analysis": last_analysis.to_dict(),
                        "success": False,
                    })

                    # Check if should escalate
                    if attempt >= self.config.escalation_threshold:
                        if last_analysis.recommended_strategy == FallbackStrategy.ESCALATE:
                            return FallbackResult(
                                success=False,
                                strategy_used=FallbackStrategy.ESCALATE,
                                attempts=attempt,
                                error="需要人工介入",
                                fallback_history=fallback_history,
                            )

                    # Generate alternative
                    alternative = self.generate_alternative(step, last_analysis)

                    if alternative.strategy == FallbackStrategy.SKIP:
                        return FallbackResult(
                            success=True,  # Skip is considered success
                            strategy_used=FallbackStrategy.SKIP,
                            attempts=attempt,
                            fallback_history=fallback_history,
                        )

                    if alternative.strategy == FallbackStrategy.ABORT:
                        return FallbackResult(
                            success=False,
                            strategy_used=FallbackStrategy.ABORT,
                            attempts=attempt,
                            error=str(last_error),
                            fallback_history=fallback_history,
                        )

            except Exception as e:
                last_error = e
                last_analysis = self.analyze_failure(e, step, context)

                fallback_history.append({
                    "attempt": attempt,
                    "strategy": "fallback",
                    "error": str(e),
                    "analysis": last_analysis.to_dict(),
                    "success": False,
                })

                logger.warning(
                    f"Fallback attempt {attempt} failed: {e} "
                    f"(category={last_analysis.error_category})"
                )

                if not last_analysis.is_recoverable:
                    break

        # All attempts failed
        if last_analysis:
            self.record_failure_pattern(
                error=last_error,
                analysis=last_analysis,
                recovery_success=False,
                recovery_strategy=FallbackStrategy.RETRY,
            )

        return FallbackResult(
            success=False,
            strategy_used=FallbackStrategy.ABORT,
            attempts=self.config.max_fallback_attempts,
            error=str(last_error) if last_error else "All fallback attempts failed",
            fallback_history=fallback_history,
        )

    def get_failure_patterns(self) -> List[FailurePattern]:
        """Get all recorded failure patterns."""
        return list(self._failure_patterns.values())

    def get_statistics(self) -> Dict[str, Any]:
        """Get fallback system statistics."""
        patterns = self.get_failure_patterns()

        successful_recoveries = sum(
            1 for p in patterns if p.successful_recovery is not None
        )

        return {
            "total_patterns": len(patterns),
            "successful_recoveries": successful_recoveries,
            "recovery_rate": successful_recoveries / len(patterns) if patterns else 0.0,
            "most_common_failures": [
                p.to_dict() for p in sorted(
                    patterns, key=lambda x: x.occurrence_count, reverse=True
                )[:5]
            ],
        }

    def clear_patterns(self) -> None:
        """Clear all recorded failure patterns."""
        self._failure_patterns.clear()
        logger.info("Cleared all failure patterns")
