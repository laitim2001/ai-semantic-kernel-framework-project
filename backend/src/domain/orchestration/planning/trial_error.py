# =============================================================================
# IPA Platform - Trial and Error Engine
# =============================================================================
# Sprint 10: S10-4 TrialAndErrorEngine (5 points)
#
# Learning engine that executes tasks with retry capability, analyzes failures,
# and learns from both successes and failures to improve over time.
#
# Features:
# - Automatic retry with adaptive parameter adjustment
# - Error pattern recognition and known-fix application
# - Success pattern learning
# - Parameter effectiveness analysis
# - Learning insights extraction
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol
from uuid import UUID, uuid4
import json
import time


class TrialStatus(str, Enum):
    """Trial execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"


class LearningType(str, Enum):
    """Types of learning insights."""
    PARAMETER_TUNING = "parameter_tuning"    # Parameter adjustment recommendations
    STRATEGY_SWITCH = "strategy_switch"      # Strategy change recommendations
    ERROR_PATTERN = "error_pattern"          # Recognized error patterns
    SUCCESS_PATTERN = "success_pattern"      # Recognized success patterns


class LLMServiceProtocol(Protocol):
    """Protocol for LLM service interface."""

    async def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate text from a prompt."""
        ...


@dataclass
class Trial:
    """
    Represents a single trial execution.

    Tracks parameters, strategy, result, and timing information.
    """
    id: UUID
    task_id: UUID
    attempt_number: int
    parameters: Dict[str, Any]
    strategy: str
    status: TrialStatus = TrialStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert trial to dictionary."""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "attempt_number": self.attempt_number,
            "parameters": self.parameters,
            "strategy": self.strategy,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "error_type": self.error_type,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    def mark_running(self) -> None:
        """Mark trial as running."""
        self.status = TrialStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_success(self, result: Any, duration_ms: int) -> None:
        """Mark trial as successful."""
        self.status = TrialStatus.SUCCESS
        self.result = result
        self.duration_ms = duration_ms
        self.completed_at = datetime.utcnow()

    def mark_failure(self, error: str, error_type: Optional[str] = None) -> None:
        """Mark trial as failed."""
        self.status = TrialStatus.FAILURE
        self.error = error
        self.error_type = error_type or self._classify_error(error)
        self.completed_at = datetime.utcnow()

    def _classify_error(self, error: str) -> str:
        """Classify error type from error message."""
        error_lower = error.lower()
        if "timeout" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "connection"
        elif "memory" in error_lower or "oom" in error_lower:
            return "memory"
        elif "permission" in error_lower or "access" in error_lower:
            return "permission"
        elif "not found" in error_lower or "404" in error_lower:
            return "not_found"
        elif "rate limit" in error_lower or "throttl" in error_lower:
            return "rate_limit"
        else:
            return "unknown"


@dataclass
class LearningInsight:
    """
    A learning insight extracted from trial history.

    Contains pattern recognition results and recommendations.
    """
    id: UUID
    learning_type: LearningType
    pattern: str
    confidence: float  # 0-1
    evidence: List[UUID]  # Related trial IDs
    recommendation: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert insight to dictionary."""
        return {
            "id": str(self.id),
            "learning_type": self.learning_type.value,
            "pattern": self.pattern,
            "confidence": self.confidence,
            "evidence": [str(e) for e in self.evidence],
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ErrorFix:
    """A known fix for an error pattern."""
    pattern: str
    fix_type: str  # "parameter", "strategy", "retry", "escalate"
    adjustments: Dict[str, Any]
    success_rate: float = 0.0
    applied_count: int = 0


class TrialAndErrorEngine:
    """
    Trial and Error Learning Engine.

    Responsible for:
    - Managing trial execution with retries
    - Analyzing failure patterns
    - Automatic strategy/parameter adjustment
    - Learning from history and improving
    """

    def __init__(
        self,
        llm_service: Optional[LLMServiceProtocol] = None,
        max_retries: int = 3,
        learning_threshold: int = 5,
        timeout_seconds: int = 300
    ):
        """
        Initialize the trial and error engine.

        Args:
            llm_service: LLM service for intelligent analysis
            max_retries: Maximum retry attempts
            learning_threshold: Minimum trials before learning
            timeout_seconds: Default timeout for trial execution
        """
        self.llm_service = llm_service
        self.max_retries = max_retries
        self.learning_threshold = learning_threshold
        self.timeout_seconds = timeout_seconds

        # Trial history: task_id -> trials
        self._trials: Dict[UUID, List[Trial]] = {}

        # Learning insights
        self._insights: List[LearningInsight] = []

        # Error pattern cache: error_keyword -> fixes
        self._error_patterns: Dict[str, List[ErrorFix]] = {}

        # Success strategy cache: task_type -> successful params
        self._success_strategies: Dict[str, Dict[str, Any]] = {}

        # Initialize known error patterns
        self._init_known_patterns()

    def _init_known_patterns(self) -> None:
        """Initialize known error patterns and fixes."""
        known_fixes = [
            ErrorFix(
                pattern="timeout",
                fix_type="parameter",
                adjustments={"timeout": "increase", "factor": 1.5}
            ),
            ErrorFix(
                pattern="rate limit",
                fix_type="parameter",
                adjustments={"delay": "increase", "factor": 2.0}
            ),
            ErrorFix(
                pattern="memory",
                fix_type="parameter",
                adjustments={"batch_size": "decrease", "factor": 0.5}
            ),
            ErrorFix(
                pattern="connection",
                fix_type="strategy",
                adjustments={"strategy": "retry_with_backoff", "backoff_base": 2}
            ),
            ErrorFix(
                pattern="not found",
                fix_type="escalate",
                adjustments={"action": "check_prerequisites"}
            ),
        ]

        for fix in known_fixes:
            if fix.pattern not in self._error_patterns:
                self._error_patterns[fix.pattern] = []
            self._error_patterns[fix.pattern].append(fix)

    async def execute_with_retry(
        self,
        task_id: UUID,
        execution_fn: Callable[..., Any],
        initial_params: Dict[str, Any],
        strategy: str = "default"
    ) -> Dict[str, Any]:
        """
        Execute a task with automatic retry and learning.

        Args:
            task_id: Unique task identifier
            execution_fn: Async function to execute
            initial_params: Initial parameters
            strategy: Execution strategy name

        Returns:
            Execution result with trial history
        """
        if task_id not in self._trials:
            self._trials[task_id] = []

        params = initial_params.copy()
        current_strategy = strategy
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            trial = Trial(
                id=uuid4(),
                task_id=task_id,
                attempt_number=attempt,
                parameters=params.copy(),
                strategy=current_strategy
            )

            trial.mark_running()

            try:
                start_time = time.time()

                # Execute the function
                result = await execution_fn(**params)

                duration_ms = int((time.time() - start_time) * 1000)
                trial.mark_success(result, duration_ms)
                self._trials[task_id].append(trial)

                # Record successful strategy
                self._record_success(task_id, params, current_strategy)

                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt,
                    "final_params": params,
                    "final_strategy": current_strategy,
                    "total_duration_ms": duration_ms,
                }

            except Exception as e:
                trial.mark_failure(str(e))
                self._trials[task_id].append(trial)
                last_error = e

                # Analyze and adjust for next attempt
                if attempt < self.max_retries:
                    adjustment = await self._analyze_and_adjust(
                        task_id, trial, params, current_strategy
                    )
                    params = adjustment.get("new_params", params)
                    current_strategy = adjustment.get("new_strategy", current_strategy)

        # All retries exhausted
        return {
            "success": False,
            "error": str(last_error),
            "error_type": self._classify_error_type(str(last_error)),
            "attempts": self.max_retries,
            "trials": [t.to_dict() for t in self._trials[task_id]],
            "final_params": params,
            "final_strategy": current_strategy,
        }

    def _classify_error_type(self, error: str) -> str:
        """Classify error type from error message."""
        error_lower = error.lower()
        for pattern in self._error_patterns.keys():
            if pattern in error_lower:
                return pattern
        return "unknown"

    async def _analyze_and_adjust(
        self,
        task_id: UUID,
        failed_trial: Trial,
        current_params: Dict[str, Any],
        current_strategy: str
    ) -> Dict[str, Any]:
        """Analyze failure and determine adjustments."""
        # Check known patterns first
        known_fix = self._check_known_patterns(failed_trial.error or "")
        if known_fix:
            return self._apply_known_fix(known_fix, current_params, current_strategy)

        # Use LLM for intelligent analysis
        if self.llm_service:
            previous_trials = self._trials.get(task_id, [])[:-1]

            prompt = f"""
            Analyze this execution failure and suggest adjustments:

            Task ID: {task_id}
            Attempt: {failed_trial.attempt_number}
            Current Parameters: {json.dumps(current_params, ensure_ascii=False)}
            Current Strategy: {current_strategy}
            Error: {failed_trial.error}

            Previous Attempts:
            {json.dumps([t.to_dict() for t in previous_trials], indent=2)}

            Suggest:
            1. Parameter adjustments
            2. Strategy change if needed
            3. Root cause analysis

            Return JSON:
            {{
                "new_params": {{}},
                "new_strategy": "strategy_name",
                "analysis": "Root cause analysis",
                "confidence": 0.8
            }}
            """

            try:
                response = await self.llm_service.generate(
                    prompt=prompt,
                    max_tokens=500
                )

                # Extract JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    adjustment = json.loads(response[json_start:json_end])

                    # Merge with current params
                    new_params = current_params.copy()
                    new_params.update(adjustment.get("new_params", {}))

                    # Record error pattern
                    self._record_error_pattern(
                        failed_trial.error or "",
                        adjustment.get("analysis", ""),
                        adjustment.get("new_params", {})
                    )

                    return {
                        "new_params": new_params,
                        "new_strategy": adjustment.get("new_strategy", current_strategy),
                        "analysis": adjustment.get("analysis"),
                    }
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: simple parameter adjustment
        return {
            "new_params": self._simple_param_adjustment(current_params),
            "new_strategy": current_strategy
        }

    def _check_known_patterns(
        self,
        error: str
    ) -> Optional[ErrorFix]:
        """Check for known error patterns and fixes."""
        error_lower = error.lower()

        for pattern, fixes in self._error_patterns.items():
            if pattern in error_lower:
                # Return the fix with highest success rate
                if fixes:
                    return max(fixes, key=lambda f: f.success_rate)

        return None

    def _apply_known_fix(
        self,
        fix: ErrorFix,
        current_params: Dict[str, Any],
        current_strategy: str
    ) -> Dict[str, Any]:
        """Apply a known fix to parameters/strategy."""
        new_params = current_params.copy()
        new_strategy = current_strategy

        if fix.fix_type == "parameter":
            for param, action in fix.adjustments.items():
                if param == "timeout" and "timeout" in new_params:
                    factor = fix.adjustments.get("factor", 1.5)
                    new_params["timeout"] = new_params["timeout"] * factor
                elif param == "delay" and "delay" in new_params:
                    factor = fix.adjustments.get("factor", 2.0)
                    new_params["delay"] = new_params["delay"] * factor
                elif param == "batch_size" and "batch_size" in new_params:
                    factor = fix.adjustments.get("factor", 0.5)
                    new_params["batch_size"] = int(new_params["batch_size"] * factor)

        elif fix.fix_type == "strategy":
            new_strategy = fix.adjustments.get("strategy", current_strategy)

        # Update fix usage statistics
        fix.applied_count += 1

        return {
            "new_params": new_params,
            "new_strategy": new_strategy,
            "fix_applied": fix.pattern,
        }

    def _simple_param_adjustment(
        self,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make simple automatic parameter adjustments."""
        adjusted = params.copy()

        for key, value in list(adjusted.items()):
            if isinstance(value, (int, float)):
                # Increase numeric values by 20%
                adjusted[key] = value * 1.2
            elif isinstance(value, bool):
                # Toggle boolean values
                adjusted[key] = not value

        return adjusted

    def _record_success(
        self,
        task_id: UUID,
        params: Dict[str, Any],
        strategy: str
    ) -> None:
        """Record a successful execution strategy."""
        key = self._generate_task_key(task_id)
        self._success_strategies[key] = {
            "params": params.copy(),
            "strategy": strategy,
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": str(task_id),
        }

    def _record_error_pattern(
        self,
        error: str,
        analysis: str,
        fix: Dict[str, Any]
    ) -> None:
        """Record an error pattern for future learning."""
        keywords = self._extract_error_keywords(error)

        for keyword in keywords:
            if keyword not in self._error_patterns:
                self._error_patterns[keyword] = []

            # Check if similar fix exists
            existing = next(
                (f for f in self._error_patterns[keyword]
                 if f.adjustments == fix),
                None
            )

            if existing:
                existing.applied_count += 1
            else:
                self._error_patterns[keyword].append(
                    ErrorFix(
                        pattern=keyword,
                        fix_type="learned",
                        adjustments=fix,
                        success_rate=0.5,  # Initial estimate
                        applied_count=1,
                    )
                )

    def _extract_error_keywords(self, error: str) -> List[str]:
        """Extract keywords from error message."""
        keywords = []
        error_lower = error.lower()

        # Common error indicators
        indicators = [
            "timeout", "connection", "memory", "permission",
            "not found", "invalid", "failed", "error", "exception",
            "rate limit", "throttle", "quota", "unauthorized",
        ]

        for keyword in indicators:
            if keyword in error_lower:
                keywords.append(keyword)

        return keywords if keywords else ["unknown"]

    def _generate_task_key(self, task_id: UUID) -> str:
        """Generate a key for task categorization."""
        return str(task_id)

    async def learn_from_history(self) -> List[LearningInsight]:
        """
        Analyze trial history and extract learning insights.

        Returns insights about patterns, parameter effects, and recommendations.
        """
        total_trials = sum(len(trials) for trials in self._trials.values())
        if total_trials < self.learning_threshold:
            return []

        insights = []

        # Analyze success patterns
        success_insight = await self._analyze_success_patterns()
        if success_insight:
            insights.append(success_insight)

        # Analyze failure patterns
        failure_insight = await self._analyze_failure_patterns()
        if failure_insight:
            insights.append(failure_insight)

        # Analyze parameter effects
        param_insight = await self._analyze_parameter_effects()
        if param_insight:
            insights.append(param_insight)

        # Analyze strategy effectiveness
        strategy_insight = await self._analyze_strategy_effectiveness()
        if strategy_insight:
            insights.append(strategy_insight)

        self._insights.extend(insights)
        return insights

    async def _analyze_success_patterns(self) -> Optional[LearningInsight]:
        """Analyze patterns in successful trials."""
        successful_trials = [
            trial
            for trials in self._trials.values()
            for trial in trials
            if trial.status == TrialStatus.SUCCESS
        ]

        if len(successful_trials) < 3:
            return None

        # Find common parameters
        common_params = self._find_common_parameters(
            [t.parameters for t in successful_trials]
        )

        if common_params:
            return LearningInsight(
                id=uuid4(),
                learning_type=LearningType.SUCCESS_PATTERN,
                pattern=f"Successful executions share parameters: {list(common_params.keys())}",
                confidence=min(len(common_params) / 5, 1.0),
                evidence=[t.id for t in successful_trials[:5]],
                recommendation=f"Consider using parameters: {common_params}",
                metadata={"common_params": common_params}
            )

        return None

    async def _analyze_failure_patterns(self) -> Optional[LearningInsight]:
        """Analyze patterns in failed trials."""
        failed_trials = [
            trial
            for trials in self._trials.values()
            for trial in trials
            if trial.status == TrialStatus.FAILURE
        ]

        if len(failed_trials) < 3:
            return None

        # Count error types
        error_counts: Dict[str, int] = {}
        for trial in failed_trials:
            error_type = trial.error_type or "unknown"
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        if error_counts:
            most_common = max(error_counts.items(), key=lambda x: x[1])
            error_type, count = most_common

            return LearningInsight(
                id=uuid4(),
                learning_type=LearningType.ERROR_PATTERN,
                pattern=f"Most common error: {error_type} ({count} occurrences)",
                confidence=count / len(failed_trials),
                evidence=[t.id for t in failed_trials if t.error_type == error_type][:5],
                recommendation=f"Prioritize handling {error_type} errors",
                metadata={"error_counts": error_counts}
            )

        return None

    async def _analyze_parameter_effects(self) -> Optional[LearningInsight]:
        """Analyze how parameters affect success/failure."""
        all_trials = [
            trial
            for trials in self._trials.values()
            for trial in trials
        ]

        if len(all_trials) < 5:
            return None

        success_params = [
            t.parameters for t in all_trials
            if t.status == TrialStatus.SUCCESS
        ]
        failure_params = [
            t.parameters for t in all_trials
            if t.status == TrialStatus.FAILURE
        ]

        if not success_params or not failure_params:
            return None

        # Find parameter differences
        differences = self._find_parameter_differences(
            success_params, failure_params
        )

        if differences:
            return LearningInsight(
                id=uuid4(),
                learning_type=LearningType.PARAMETER_TUNING,
                pattern=f"Parameters affecting success: {list(differences.keys())}",
                confidence=0.7,
                evidence=[t.id for t in all_trials[:5]],
                recommendation=f"Tune parameters: {differences}",
                metadata={"parameter_analysis": differences}
            )

        return None

    async def _analyze_strategy_effectiveness(self) -> Optional[LearningInsight]:
        """Analyze effectiveness of different strategies."""
        strategy_stats: Dict[str, Dict[str, int]] = {}

        for trials in self._trials.values():
            for trial in trials:
                if trial.strategy not in strategy_stats:
                    strategy_stats[trial.strategy] = {"success": 0, "failure": 0}

                if trial.status == TrialStatus.SUCCESS:
                    strategy_stats[trial.strategy]["success"] += 1
                elif trial.status == TrialStatus.FAILURE:
                    strategy_stats[trial.strategy]["failure"] += 1

        if not strategy_stats:
            return None

        # Calculate success rates
        strategy_rates = {}
        for strategy, stats in strategy_stats.items():
            total = stats["success"] + stats["failure"]
            if total > 0:
                strategy_rates[strategy] = stats["success"] / total

        if strategy_rates:
            best_strategy = max(strategy_rates.items(), key=lambda x: x[1])
            strategy_name, success_rate = best_strategy

            return LearningInsight(
                id=uuid4(),
                learning_type=LearningType.STRATEGY_SWITCH,
                pattern=f"Most effective strategy: {strategy_name} ({success_rate:.0%} success rate)",
                confidence=success_rate,
                evidence=[],
                recommendation=f"Prefer using '{strategy_name}' strategy",
                metadata={"strategy_rates": strategy_rates}
            )

        return None

    def _find_common_parameters(
        self,
        param_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Find parameters common to all entries."""
        if not param_list:
            return {}

        common = {}
        first = param_list[0]

        for key, value in first.items():
            if all(p.get(key) == value for p in param_list):
                common[key] = value

        return common

    def _find_parameter_differences(
        self,
        success_params: List[Dict[str, Any]],
        failure_params: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Find parameter differences between success and failure cases."""
        differences = {}

        # Get all parameter keys
        all_keys = set()
        for p in success_params + failure_params:
            all_keys.update(p.keys())

        for key in all_keys:
            success_values = [p.get(key) for p in success_params if key in p]
            failure_values = [p.get(key) for p in failure_params if key in p]

            if success_values and failure_values:
                # Compare value distributions
                success_set = set(str(v) for v in success_values)
                failure_set = set(str(v) for v in failure_values)

                if success_set != failure_set:
                    # Calculate average for numeric values
                    if all(isinstance(v, (int, float)) for v in success_values + failure_values):
                        success_avg = sum(success_values) / len(success_values)
                        failure_avg = sum(failure_values) / len(failure_values)
                        differences[key] = {
                            "success_avg": success_avg,
                            "failure_avg": failure_avg,
                            "recommendation": "higher" if success_avg > failure_avg else "lower"
                        }
                    else:
                        differences[key] = {
                            "success_common": success_values[0] if success_values else None,
                            "failure_common": failure_values[0] if failure_values else None
                        }

        return differences

    def get_recommendations(
        self,
        task_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on learning history.

        Args:
            task_type: Optional filter by task type

        Returns:
            List of recommendations sorted by confidence
        """
        recommendations = []

        for insight in self._insights:
            rec = {
                "id": str(insight.id),
                "type": insight.learning_type.value,
                "pattern": insight.pattern,
                "recommendation": insight.recommendation,
                "confidence": insight.confidence,
                "created_at": insight.created_at.isoformat(),
            }
            recommendations.append(rec)

        # Sort by confidence descending
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)

        return recommendations

    def get_trial_history(
        self,
        task_id: Optional[UUID] = None,
        status: Optional[TrialStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get trial history with optional filters.

        Args:
            task_id: Filter by specific task
            status: Filter by trial status
            limit: Maximum number of trials to return

        Returns:
            List of trial dictionaries
        """
        if task_id:
            trials = self._trials.get(task_id, [])
        else:
            trials = [t for trials in self._trials.values() for t in trials]

        if status:
            trials = [t for t in trials if t.status == status]

        # Sort by started_at descending
        trials = sorted(
            trials,
            key=lambda t: t.started_at or datetime.min,
            reverse=True
        )

        return [t.to_dict() for t in trials[:limit]]

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall execution statistics."""
        all_trials = [t for trials in self._trials.values() for t in trials]

        success_count = sum(1 for t in all_trials if t.status == TrialStatus.SUCCESS)
        failure_count = sum(1 for t in all_trials if t.status == TrialStatus.FAILURE)
        total = len(all_trials)

        # Calculate average duration for successful trials
        durations = [t.duration_ms for t in all_trials if t.status == TrialStatus.SUCCESS]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_trials": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / total if total > 0 else 0,
            "average_duration_ms": avg_duration,
            "unique_tasks": len(self._trials),
            "insights_count": len(self._insights),
            "known_patterns": len(self._error_patterns),
        }

    def clear_history(self, task_id: Optional[UUID] = None) -> None:
        """
        Clear trial history.

        Args:
            task_id: If provided, only clear history for this task
        """
        if task_id:
            if task_id in self._trials:
                del self._trials[task_id]
        else:
            self._trials.clear()
