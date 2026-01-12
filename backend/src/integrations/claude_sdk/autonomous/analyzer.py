# =============================================================================
# IPA Platform - Event Analyzer
# =============================================================================
# Sprint 79: S79-1 - Claude 自主規劃引擎 (13 pts)
#
# This module provides event analysis capabilities, including:
# - Event classification and severity assessment
# - Context extraction and historical correlation
# - Complexity estimation for budget_tokens allocation
# =============================================================================

import logging
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from .types import (
    AnalysisResult,
    EventComplexity,
    EventContext,
    EventSeverity,
    get_budget_tokens,
)

logger = logging.getLogger(__name__)


# Analysis prompt template for Extended Thinking
ANALYSIS_PROMPT_TEMPLATE = """You are an expert IT incident analyst. Analyze the following IT event and provide a structured assessment.

## Event Details
- Event ID: {event_id}
- Type: {event_type}
- Description: {description}
- Severity: {severity}
- Source System: {source_system}
- Affected Services: {affected_services}

## Your Analysis Tasks

1. **Root Cause Hypothesis**: What is the most likely root cause of this event?

2. **Affected Components**: List all systems, services, and components that may be affected.

3. **Complexity Assessment**: Rate the complexity (simple, moderate, complex, critical):
   - simple: Single service restart, clear fix
   - moderate: Configuration change, multiple services
   - complex: Multi-system issue, requires investigation
   - critical: Security incident, data loss risk, major outage

4. **Recommended Actions**: List 3-5 specific actions to resolve this event, in order of execution.

5. **Confidence Score**: Rate your confidence in this analysis (0.0 to 1.0).

## Response Format

Provide your analysis in the following JSON format:
```json
{{
    "complexity": "simple|moderate|complex|critical",
    "root_cause_hypothesis": "Your hypothesis here",
    "affected_components": ["component1", "component2"],
    "recommended_actions": ["action1", "action2", "action3"],
    "confidence_score": 0.85,
    "reasoning": "Your detailed reasoning..."
}}
```
"""


class EventAnalyzer:
    """
    Analyzes IT events using Claude's Extended Thinking capability.

    The analyzer evaluates event severity, determines complexity,
    and provides root cause hypotheses with recommended actions.

    Example:
        analyzer = EventAnalyzer(client)
        result = await analyzer.analyze_event(event_context)
        print(f"Complexity: {result.complexity}")
        print(f"Root cause: {result.root_cause_hypothesis}")
    """

    def __init__(
        self,
        client: AsyncAnthropic,
        model: str = "claude-sonnet-4-20250514",
        default_budget_tokens: int = 8192,
    ):
        """
        Initialize the EventAnalyzer.

        Args:
            client: AsyncAnthropic client instance
            model: Model to use for analysis
            default_budget_tokens: Default budget for Extended Thinking
        """
        self._client = client
        self._model = model
        self._default_budget_tokens = default_budget_tokens

    async def analyze_event(
        self,
        event_context: EventContext,
        historical_events: Optional[List[Dict[str, Any]]] = None,
        budget_tokens: Optional[int] = None,
    ) -> AnalysisResult:
        """
        Analyze an IT event and generate structured assessment.

        Args:
            event_context: The event to analyze
            historical_events: Optional list of similar historical events
            budget_tokens: Override default budget_tokens for Extended Thinking

        Returns:
            AnalysisResult with complexity, root cause, and recommendations
        """
        logger.info(f"Analyzing event: {event_context.event_id}")

        # Build analysis prompt
        prompt = self._build_analysis_prompt(event_context, historical_events)

        # Use Extended Thinking for deep analysis
        tokens = budget_tokens or self._default_budget_tokens

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": tokens,
                },
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract analysis from response
            result = self._parse_analysis_response(event_context.event_id, response)

            logger.info(
                f"Event analysis complete: complexity={result.complexity.value}, "
                f"confidence={result.confidence_score}"
            )

            return result

        except Exception as e:
            logger.error(f"Event analysis failed: {e}")
            # Return a default analysis on error
            return AnalysisResult(
                event_id=event_context.event_id,
                complexity=self._estimate_complexity_from_severity(event_context.severity),
                root_cause_hypothesis="Analysis failed - manual investigation required",
                affected_components=[],
                recommended_actions=["Investigate manually", "Contact on-call engineer"],
                confidence_score=0.0,
                analysis_reasoning=f"Analysis error: {str(e)}",
                budget_tokens_recommended=tokens,
            )

    def _build_analysis_prompt(
        self,
        event_context: EventContext,
        historical_events: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build the analysis prompt from event context."""
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            event_id=event_context.event_id,
            event_type=event_context.event_type,
            description=event_context.description,
            severity=event_context.severity.value,
            source_system=event_context.source_system or "Unknown",
            affected_services=", ".join(event_context.affected_services) or "Unknown",
        )

        # Add historical context if available
        if historical_events:
            prompt += "\n\n## Historical Similar Events\n"
            for i, event in enumerate(historical_events[:5], 1):
                prompt += f"\n{i}. {event.get('description', 'No description')}"
                if event.get("resolution"):
                    prompt += f"\n   Resolution: {event['resolution']}"

        return prompt

    def _parse_analysis_response(
        self, event_id: str, response: Any
    ) -> AnalysisResult:
        """Parse the Claude response into an AnalysisResult."""
        import json

        # Extract text content from response
        content = ""
        thinking = ""

        for block in response.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                content = block.text

        # Try to parse JSON from response
        try:
            # Find JSON block in response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)

                complexity = EventComplexity(data.get("complexity", "moderate"))

                return AnalysisResult(
                    event_id=event_id,
                    complexity=complexity,
                    root_cause_hypothesis=data.get(
                        "root_cause_hypothesis", "Unable to determine"
                    ),
                    affected_components=data.get("affected_components", []),
                    recommended_actions=data.get("recommended_actions", []),
                    confidence_score=float(data.get("confidence_score", 0.5)),
                    analysis_reasoning=data.get("reasoning", thinking),
                    budget_tokens_recommended=get_budget_tokens(complexity),
                )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse analysis JSON: {e}")

        # Fallback: return basic result from text
        return AnalysisResult(
            event_id=event_id,
            complexity=EventComplexity.MODERATE,
            root_cause_hypothesis=content[:500] if content else "Analysis pending",
            affected_components=[],
            recommended_actions=["Review analysis output manually"],
            confidence_score=0.3,
            analysis_reasoning=thinking or content,
            budget_tokens_recommended=8192,
        )

    def _estimate_complexity_from_severity(
        self, severity: EventSeverity
    ) -> EventComplexity:
        """Estimate complexity from event severity as fallback."""
        severity_to_complexity = {
            EventSeverity.LOW: EventComplexity.SIMPLE,
            EventSeverity.MEDIUM: EventComplexity.MODERATE,
            EventSeverity.HIGH: EventComplexity.COMPLEX,
            EventSeverity.CRITICAL: EventComplexity.CRITICAL,
        }
        return severity_to_complexity.get(severity, EventComplexity.MODERATE)

    async def extract_context(
        self,
        event_context: EventContext,
    ) -> Dict[str, Any]:
        """
        Extract additional context from event description.

        Uses NLP to identify:
        - Mentioned systems and services
        - Error codes and messages
        - Timestamps and durations
        - User/customer impact indicators

        Args:
            event_context: The event to analyze

        Returns:
            Dictionary of extracted context
        """
        prompt = f"""Extract structured information from this IT event description:

Event: {event_context.description}

Extract and return as JSON:
{{
    "mentioned_systems": ["system names"],
    "error_codes": ["any error codes"],
    "affected_users": "none|few|many|all",
    "urgency_indicators": ["words indicating urgency"],
    "technical_terms": ["technical terms found"]
}}
"""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text if response.content else "{}"

            import json

            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])

        except Exception as e:
            logger.warning(f"Context extraction failed: {e}")

        return {}

    def estimate_complexity(self, event_context: EventContext) -> EventComplexity:
        """
        Quick complexity estimation without API call.

        Uses heuristics based on:
        - Event severity
        - Number of affected services
        - Keywords in description

        Args:
            event_context: The event to assess

        Returns:
            Estimated complexity level
        """
        # Start with severity-based estimate
        base_complexity = self._estimate_complexity_from_severity(event_context.severity)

        # Adjust based on affected services
        service_count = len(event_context.affected_services)
        if service_count > 5:
            base_complexity = EventComplexity.CRITICAL
        elif service_count > 2:
            base_complexity = max(base_complexity, EventComplexity.COMPLEX)

        # Check for critical keywords
        critical_keywords = [
            "security",
            "breach",
            "data loss",
            "outage",
            "down",
            "critical",
            "emergency",
        ]
        description_lower = event_context.description.lower()
        if any(kw in description_lower for kw in critical_keywords):
            base_complexity = max(base_complexity, EventComplexity.COMPLEX)

        return base_complexity
