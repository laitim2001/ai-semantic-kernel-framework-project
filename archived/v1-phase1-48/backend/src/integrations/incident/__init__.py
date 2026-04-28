"""
IT Incident Handling Module.

Sprint 126: Phase 34 — IT Incident Processing Scenario

Provides intelligent IT incident analysis, remediation recommendation,
and automated/HITL execution with ServiceNow integration.

Components:
    - IncidentAnalyzer: Root cause analysis with correlation + LLM
    - ActionRecommender: Rule-based + LLM remediation suggestions
    - IncidentExecutor: Auto-execute + HITL approval + ServiceNow writeback

Data Types:
    - IncidentContext: Normalized incident information
    - IncidentAnalysis: Analysis result
    - RemediationAction: Remediation action with risk assessment
    - ExecutionResult: Execution outcome

Usage:
    >>> from src.integrations.incident import (
    ...     IncidentAnalyzer, ActionRecommender, IncidentExecutor,
    ...     IncidentContext, IncidentSeverity, IncidentCategory,
    ... )
    >>>
    >>> analyzer = IncidentAnalyzer()
    >>> analysis = await analyzer.analyze(context)
    >>>
    >>> recommender = ActionRecommender()
    >>> actions = await recommender.recommend(analysis, context)
    >>>
    >>> executor = IncidentExecutor()
    >>> results = await executor.execute(analysis, context, actions)
"""

from .analyzer import IncidentAnalyzer
from .executor import IncidentExecutor
from .recommender import ActionRecommender
from .types import (
    ExecutionResult,
    ExecutionStatus,
    IncidentAnalysis,
    IncidentCategory,
    IncidentContext,
    IncidentSeverity,
    RemediationAction,
    RemediationActionType,
    RemediationRisk,
)

__all__ = [
    # Core classes
    "IncidentAnalyzer",
    "ActionRecommender",
    "IncidentExecutor",
    # Data types
    "IncidentContext",
    "IncidentAnalysis",
    "RemediationAction",
    "ExecutionResult",
    # Enums
    "IncidentSeverity",
    "IncidentCategory",
    "RemediationRisk",
    "RemediationActionType",
    "ExecutionStatus",
]
