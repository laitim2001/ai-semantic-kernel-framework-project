"""
IT Incident Analyzer — Intelligent Root Cause Analysis.

Sprint 126: Story 126-2 — IncidentAnalyzer integrates CorrelationAnalyzer,
RootCauseAnalyzer, and optional LLM enhancement to produce comprehensive
incident analysis with recommended remediation actions.

Dependencies:
    - CorrelationAnalyzer (integrations/correlation/)
    - RootCauseAnalyzer (integrations/rootcause/)
    - LLMServiceProtocol (integrations/llm/) [optional]
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..correlation.analyzer import CorrelationAnalyzer
from ..correlation.types import (
    Correlation,
    Event,
    EventSeverity,
    EventType,
)
from ..rootcause.analyzer import RootCauseAnalyzer
from ..rootcause.types import RootCauseAnalysis
from .prompts import INCIDENT_ANALYSIS_PROMPT
from .types import (
    IncidentAnalysis,
    IncidentCategory,
    IncidentContext,
    IncidentSeverity,
    RemediationAction,
    RemediationActionType,
    RemediationRisk,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Severity to EventSeverity mapping
# =============================================================================

_SEVERITY_MAP: Dict[IncidentSeverity, EventSeverity] = {
    IncidentSeverity.P1: EventSeverity.CRITICAL,
    IncidentSeverity.P2: EventSeverity.ERROR,
    IncidentSeverity.P3: EventSeverity.WARNING,
    IncidentSeverity.P4: EventSeverity.INFO,
}


class IncidentAnalyzer:
    """Analyzes IT incidents using correlation, root cause analysis, and LLM enhancement.

    The analysis pipeline:
        1. Convert IncidentContext to a correlation Event
        2. Find correlated events via CorrelationAnalyzer
        3. Perform root cause analysis via RootCauseAnalyzer
        4. (Optional) Enhance analysis with LLM for deeper insights
        5. Merge results into IncidentAnalysis with recommended actions

    Example:
        >>> analyzer = IncidentAnalyzer()
        >>> analysis = await analyzer.analyze(incident_context)
        >>> print(analysis.root_cause_summary)
        >>> print(len(analysis.recommended_actions))
    """

    def __init__(
        self,
        correlation_analyzer: Optional[CorrelationAnalyzer] = None,
        rootcause_analyzer: Optional[RootCauseAnalyzer] = None,
        llm_service: Optional[Any] = None,
    ) -> None:
        """Initialize IncidentAnalyzer.

        Args:
            correlation_analyzer: Correlation analysis engine (creates default if None)
            rootcause_analyzer: Root cause analysis engine (creates default if None)
            llm_service: Optional LLM service implementing LLMServiceProtocol
        """
        self._correlation_analyzer = correlation_analyzer or CorrelationAnalyzer()
        self._rootcause_analyzer = rootcause_analyzer or RootCauseAnalyzer(
            correlation_analyzer=self._correlation_analyzer
        )
        self._llm_service = llm_service

    async def analyze(self, context: IncidentContext) -> IncidentAnalysis:
        """Perform comprehensive incident analysis.

        Args:
            context: Normalized incident context

        Returns:
            IncidentAnalysis with root cause, correlations, and recommended actions
        """
        analysis_id = f"ana_{uuid4().hex[:12]}"
        start_time = datetime.utcnow()

        logger.info(
            f"Starting incident analysis: {analysis_id} "
            f"for {context.incident_number} ({context.severity.value})"
        )

        try:
            # Step 1: Convert to correlation Event
            event = self._context_to_event(context)

            # Step 2: Find correlated events
            correlations = await self._correlation_analyzer.find_correlations(event)

            # Step 3: Root cause analysis
            rca_result = await self._rootcause_analyzer.analyze_root_cause(
                event=event,
                correlations=correlations,
            )

            # Step 4: LLM enhancement (optional)
            llm_enhanced = False
            llm_root_cause = ""
            llm_confidence = 0.0
            llm_factors: List[str] = []

            if self._llm_service is not None:
                try:
                    llm_result = await self._enhance_with_llm(
                        context, correlations, rca_result
                    )
                    if llm_result:
                        llm_enhanced = True
                        llm_root_cause = llm_result.get("root_cause_summary", "")
                        llm_confidence = float(
                            llm_result.get("root_cause_confidence", 0.0)
                        )
                        llm_factors = llm_result.get("contributing_factors", [])
                except Exception as e:
                    logger.warning(
                        f"LLM enhancement failed for {analysis_id}, "
                        f"using rule-based analysis only: {e}"
                    )

            # Step 5: Merge results
            root_cause_summary = self._merge_root_cause(
                rca_result, llm_root_cause, llm_enhanced
            )
            root_cause_confidence = self._merge_confidence(
                rca_result.confidence, llm_confidence, llm_enhanced
            )
            contributing_factors = self._merge_factors(
                rca_result.contributing_factors, llm_factors, llm_enhanced
            )

            # Convert RCA recommendations to RemediationActions
            recommended_actions = self._convert_recommendations(
                rca_result, context
            )

            analysis_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            analysis = IncidentAnalysis(
                analysis_id=analysis_id,
                incident_number=context.incident_number,
                root_cause_summary=root_cause_summary,
                root_cause_confidence=root_cause_confidence,
                correlations_found=len(correlations),
                historical_matches=len(rca_result.similar_historical_cases),
                contributing_factors=contributing_factors,
                recommended_actions=recommended_actions,
                analysis_duration_ms=analysis_time,
                llm_enhanced=llm_enhanced,
                metadata={
                    "correlation_types": self._summarize_correlations(correlations),
                    "rca_status": rca_result.status.value,
                    "rca_hypothesis_count": len(rca_result.hypotheses),
                },
            )

            logger.info(
                f"Incident analysis completed: {analysis_id} "
                f"(root_cause_confidence: {root_cause_confidence:.2%}, "
                f"actions: {len(recommended_actions)}, "
                f"duration: {analysis_time}ms)"
            )

            return analysis

        except Exception as e:
            analysis_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            logger.error(
                f"Incident analysis failed: {analysis_id} - {e}", exc_info=True
            )
            return IncidentAnalysis(
                analysis_id=analysis_id,
                incident_number=context.incident_number,
                root_cause_summary=f"Analysis failed: {str(e)}",
                root_cause_confidence=0.0,
                analysis_duration_ms=analysis_time,
                metadata={"error": str(e)},
            )

    def _context_to_event(self, context: IncidentContext) -> Event:
        """Convert IncidentContext to a correlation Event.

        Args:
            context: Incident context to convert

        Returns:
            Event suitable for CorrelationAnalyzer
        """
        severity = _SEVERITY_MAP.get(context.severity, EventSeverity.WARNING)

        return Event(
            event_id=f"inc_{context.incident_number}",
            event_type=EventType.INCIDENT,
            title=context.short_description,
            description=context.description or context.short_description,
            severity=severity,
            timestamp=context.created_at,
            source_system="servicenow",
            affected_components=context.affected_components,
            tags=[context.category.value, context.severity.value],
            metadata={
                "incident_number": context.incident_number,
                "business_service": context.business_service,
                "cmdb_ci": context.cmdb_ci,
                "assignment_group": context.assignment_group,
            },
        )

    async def _enhance_with_llm(
        self,
        context: IncidentContext,
        correlations: List[Correlation],
        rca_result: RootCauseAnalysis,
    ) -> Optional[Dict[str, Any]]:
        """Enhance analysis using LLM.

        Args:
            context: Incident context
            correlations: Found correlations
            rca_result: Rule-based RCA result

        Returns:
            LLM analysis result dict, or None on failure
        """
        if not self._llm_service:
            return None

        # Build correlation summary
        correlation_summary = "No correlated events found."
        if correlations:
            lines = []
            for c in correlations[:10]:
                lines.append(
                    f"- {c.correlation_type.value} correlation "
                    f"(score: {c.score:.2f}): {'; '.join(c.evidence[:2])}"
                )
            correlation_summary = "\n".join(lines)

        # Build RCA summary
        rca_summary = f"Root cause: {rca_result.root_cause}\n"
        rca_summary += f"Confidence: {rca_result.confidence:.2%}\n"
        if rca_result.contributing_factors:
            rca_summary += "Contributing factors:\n"
            for f in rca_result.contributing_factors[:5]:
                rca_summary += f"- {f}\n"

        # Build historical cases summary
        hist_lines = []
        for case in rca_result.similar_historical_cases[:3]:
            hist_lines.append(
                f"- {case.title} (similarity: {case.similarity_score:.2%}): "
                f"{case.root_cause}"
            )
        historical_cases = (
            "\n".join(hist_lines) if hist_lines else "No similar historical cases found."
        )

        # Format prompt
        prompt = INCIDENT_ANALYSIS_PROMPT.format(
            incident_number=context.incident_number,
            severity=context.severity.value,
            category=context.category.value,
            short_description=context.short_description,
            description=context.description or "(not provided)",
            affected_components=", ".join(context.affected_components) or "(none)",
            business_service=context.business_service or "(not specified)",
            cmdb_ci=context.cmdb_ci or "(not specified)",
            correlation_summary=correlation_summary,
            rca_summary=rca_summary,
            historical_cases=historical_cases,
        )

        # Call LLM
        response = await self._llm_service.generate_structured(
            prompt=prompt,
            output_schema={
                "root_cause_summary": "string",
                "root_cause_confidence": "number",
                "contributing_factors": ["string"],
                "analysis_notes": "string",
                "suggested_category_correction": "string|null",
            },
            max_tokens=1000,
            temperature=0.3,
        )

        return response

    def _merge_root_cause(
        self,
        rca_result: RootCauseAnalysis,
        llm_root_cause: str,
        llm_enhanced: bool,
    ) -> str:
        """Merge rule-based and LLM root cause summaries.

        Prefers LLM summary if available and non-empty.

        Args:
            rca_result: Rule-based RCA result
            llm_root_cause: LLM-generated root cause
            llm_enhanced: Whether LLM was used

        Returns:
            Final root cause summary
        """
        if llm_enhanced and llm_root_cause:
            return llm_root_cause
        return rca_result.root_cause

    def _merge_confidence(
        self,
        rca_confidence: float,
        llm_confidence: float,
        llm_enhanced: bool,
    ) -> float:
        """Merge rule-based and LLM confidence scores.

        Uses weighted average: 40% rule-based + 60% LLM when both available.

        Args:
            rca_confidence: Rule-based confidence (0.0-1.0)
            llm_confidence: LLM confidence (0.0-1.0)
            llm_enhanced: Whether LLM was used

        Returns:
            Merged confidence score (0.0-1.0)
        """
        if llm_enhanced and llm_confidence > 0:
            return min(1.0, rca_confidence * 0.4 + llm_confidence * 0.6)
        return rca_confidence

    def _merge_factors(
        self,
        rca_factors: List[str],
        llm_factors: List[str],
        llm_enhanced: bool,
    ) -> List[str]:
        """Merge contributing factors from both sources, deduplicating.

        Args:
            rca_factors: Rule-based contributing factors
            llm_factors: LLM-identified factors
            llm_enhanced: Whether LLM was used

        Returns:
            Deduplicated list of contributing factors
        """
        seen = set()
        merged: List[str] = []

        for factor in rca_factors:
            key = factor.lower().strip()
            if key not in seen:
                seen.add(key)
                merged.append(factor)

        if llm_enhanced:
            for factor in llm_factors:
                key = factor.lower().strip()
                if key not in seen:
                    seen.add(key)
                    merged.append(factor)

        return merged[:15]  # Cap at 15 factors

    def _convert_recommendations(
        self,
        rca_result: RootCauseAnalysis,
        context: IncidentContext,
    ) -> List[RemediationAction]:
        """Convert RCA recommendations to RemediationActions.

        Args:
            rca_result: Root cause analysis result
            context: Incident context for category-specific actions

        Returns:
            List of RemediationAction objects
        """
        actions: List[RemediationAction] = []

        for rec in rca_result.recommendations:
            # Map recommendation type to risk level
            risk = RemediationRisk.MEDIUM
            if rec.recommendation_type.value == "immediate":
                risk = RemediationRisk.LOW
            elif rec.recommendation_type.value == "preventive":
                risk = RemediationRisk.HIGH

            action = RemediationAction(
                action_type=RemediationActionType.CUSTOM,
                title=rec.title,
                description=rec.description,
                confidence=min(1.0, rca_result.confidence * 0.8),
                risk=risk,
                rollback_steps=rec.steps,
                metadata={
                    "source": "rootcause_analyzer",
                    "recommendation_id": rec.recommendation_id,
                    "recommendation_type": rec.recommendation_type.value,
                    "priority": rec.priority,
                },
            )
            actions.append(action)

        return actions

    def _summarize_correlations(
        self,
        correlations: List[Correlation],
    ) -> Dict[str, int]:
        """Summarize correlations by type.

        Args:
            correlations: List of correlations

        Returns:
            Dict mapping correlation type to count
        """
        summary: Dict[str, int] = {}
        for c in correlations:
            key = c.correlation_type.value
            summary[key] = summary.get(key, 0) + 1
        return summary
