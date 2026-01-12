# =============================================================================
# IPA Platform - Autonomous Planner
# =============================================================================
# Sprint 79: S79-1 - Claude 自主規劃引擎 (13 pts)
#
# This module provides autonomous planning capabilities, using Claude's
# Extended Thinking to generate structured execution plans for IT events.
# =============================================================================

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from .analyzer import EventAnalyzer
from .types import (
    AnalysisResult,
    AutonomousPlan,
    EventComplexity,
    EventContext,
    PlanStatus,
    PlanStep,
    RiskLevel,
    StepStatus,
    get_budget_tokens,
)

logger = logging.getLogger(__name__)


# Planning prompt template for Extended Thinking
PLANNING_PROMPT_TEMPLATE = """You are an expert IT operations planner. Based on the event analysis, create a detailed execution plan.

## Event Analysis
- Event ID: {event_id}
- Complexity: {complexity}
- Root Cause Hypothesis: {root_cause}
- Affected Components: {affected_components}
- Recommended Actions: {recommended_actions}

## Your Planning Tasks

Create a step-by-step execution plan with the following considerations:

1. **Safety First**: Include validation and rollback steps
2. **Minimal Impact**: Minimize service disruption
3. **Verification**: Include verification after each critical step
4. **Documentation**: Each step should be clearly documented

## Available Tools and Workflows

You can use these tools in your plan:
- `shell_command`: Execute shell commands on target systems
- `azure_vm`: Manage Azure VMs (restart, resize, etc.)
- `azure_monitor`: Query Azure Monitor metrics and logs
- `servicenow`: Update ServiceNow tickets
- `teams_notify`: Send Teams notifications
- `file_operation`: Read/write configuration files
- `database_query`: Execute database queries

## Response Format

Provide your plan in the following JSON format:
```json
{{
    "steps": [
        {{
            "step_number": 1,
            "action": "Brief action name",
            "description": "Detailed description of what this step does",
            "tool_or_workflow": "tool_name",
            "parameters": {{"param1": "value1"}},
            "expected_outcome": "What success looks like",
            "fallback_action": "What to do if this fails",
            "estimated_duration_seconds": 60,
            "requires_approval": false
        }}
    ],
    "risk_level": "low|medium|high|critical",
    "total_estimated_duration_seconds": 300,
    "preconditions": ["condition1", "condition2"],
    "success_criteria": ["criterion1", "criterion2"]
}}
```
"""


class AutonomousPlanner:
    """
    Autonomous planning engine for IT event handling.

    Uses Claude's Extended Thinking capability to generate
    structured, executable plans for resolving IT incidents.

    Example:
        planner = AutonomousPlanner(client)
        plan = await planner.generate_plan(event_context)
        print(f"Plan has {len(plan.steps)} steps")
        print(f"Risk level: {plan.risk_level}")
    """

    def __init__(
        self,
        client: AsyncAnthropic,
        model: str = "claude-sonnet-4-20250514",
        analyzer: Optional[EventAnalyzer] = None,
    ):
        """
        Initialize the AutonomousPlanner.

        Args:
            client: AsyncAnthropic client instance
            model: Model to use for planning
            analyzer: Optional EventAnalyzer instance (created if not provided)
        """
        self._client = client
        self._model = model
        self._analyzer = analyzer or EventAnalyzer(client, model)
        self._plans: Dict[str, AutonomousPlan] = {}

    async def generate_plan(
        self,
        event_context: EventContext,
        analysis: Optional[AnalysisResult] = None,
        budget_tokens: Optional[int] = None,
    ) -> AutonomousPlan:
        """
        Generate an autonomous execution plan for an IT event.

        Args:
            event_context: The event to plan for
            analysis: Pre-computed analysis (will analyze if not provided)
            budget_tokens: Override default budget_tokens for Extended Thinking

        Returns:
            AutonomousPlan with steps, risk assessment, and metadata
        """
        plan_id = str(uuid.uuid4())
        logger.info(f"Generating plan {plan_id} for event {event_context.event_id}")

        # Create initial plan
        plan = AutonomousPlan(
            id=plan_id,
            event_id=event_context.event_id,
            event_context=event_context,
            complexity=EventComplexity.MODERATE,
            status=PlanStatus.ANALYZING,
        )
        self._plans[plan_id] = plan

        try:
            # Phase 1: Analysis (if not provided)
            if analysis is None:
                analysis = await self._analyzer.analyze_event(event_context)

            plan.analysis = analysis
            plan.complexity = analysis.complexity
            plan.status = PlanStatus.PLANNED

            # Phase 2: Planning with Extended Thinking
            tokens = budget_tokens or get_budget_tokens(analysis.complexity)
            plan_data = await self._generate_plan_steps(analysis, tokens)

            # Update plan with generated steps
            plan.steps = plan_data["steps"]
            plan.risk_level = plan_data["risk_level"]
            plan.estimated_duration_seconds = plan_data["total_duration"]
            plan.thinking_output = plan_data.get("thinking", "")
            plan.updated_at = datetime.utcnow()

            logger.info(
                f"Plan {plan_id} generated: {len(plan.steps)} steps, "
                f"risk={plan.risk_level.value}, duration={plan.estimated_duration_seconds}s"
            )

            return plan

        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            plan.status = PlanStatus.FAILED
            plan.error = str(e)
            plan.updated_at = datetime.utcnow()
            return plan

    async def _generate_plan_steps(
        self,
        analysis: AnalysisResult,
        budget_tokens: int,
    ) -> Dict[str, Any]:
        """Generate plan steps using Extended Thinking."""
        prompt = PLANNING_PROMPT_TEMPLATE.format(
            event_id=analysis.event_id,
            complexity=analysis.complexity.value,
            root_cause=analysis.root_cause_hypothesis,
            affected_components=", ".join(analysis.affected_components),
            recommended_actions="\n".join(
                f"- {action}" for action in analysis.recommended_actions
            ),
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=16000,
            thinking={
                "type": "enabled",
                "budget_tokens": budget_tokens,
            },
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract content and thinking
        content = ""
        thinking = ""
        for block in response.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                content = block.text

        # Parse plan from response
        return self._parse_plan_response(content, thinking)

    def _parse_plan_response(
        self, content: str, thinking: str
    ) -> Dict[str, Any]:
        """Parse the planning response into structured data."""
        import json

        result = {
            "steps": [],
            "risk_level": RiskLevel.MEDIUM,
            "total_duration": 300,
            "thinking": thinking,
        }

        try:
            # Find JSON block in response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)

                # Parse steps
                for step_data in data.get("steps", []):
                    step = PlanStep(
                        step_number=step_data.get("step_number", 0),
                        action=step_data.get("action", "Unknown"),
                        description=step_data.get("description", ""),
                        tool_or_workflow=step_data.get("tool_or_workflow", ""),
                        parameters=step_data.get("parameters", {}),
                        expected_outcome=step_data.get("expected_outcome", ""),
                        fallback_action=step_data.get("fallback_action"),
                        estimated_duration_seconds=step_data.get(
                            "estimated_duration_seconds", 60
                        ),
                        requires_approval=step_data.get("requires_approval", False),
                        status=StepStatus.PENDING,
                    )
                    result["steps"].append(step)

                # Parse risk level
                risk_str = data.get("risk_level", "medium").lower()
                try:
                    result["risk_level"] = RiskLevel(risk_str)
                except ValueError:
                    result["risk_level"] = RiskLevel.MEDIUM

                # Total duration
                result["total_duration"] = data.get(
                    "total_estimated_duration_seconds", 300
                )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse plan JSON: {e}")
            # Create a fallback step
            result["steps"] = [
                PlanStep(
                    step_number=1,
                    action="Manual Investigation",
                    description="Plan generation failed. Manual investigation required.",
                    tool_or_workflow="manual",
                    expected_outcome="Issue resolved",
                    requires_approval=True,
                )
            ]

        return result

    def get_plan(self, plan_id: str) -> Optional[AutonomousPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(
        self,
        event_id: Optional[str] = None,
        status: Optional[PlanStatus] = None,
    ) -> List[AutonomousPlan]:
        """List plans with optional filtering."""
        plans = list(self._plans.values())

        if event_id:
            plans = [p for p in plans if p.event_id == event_id]

        if status:
            plans = [p for p in plans if p.status == status]

        return sorted(plans, key=lambda p: p.created_at, reverse=True)

    def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan by ID."""
        if plan_id in self._plans:
            del self._plans[plan_id]
            return True
        return False

    async def estimate_complexity(
        self, event_context: EventContext
    ) -> EventComplexity:
        """
        Quick complexity estimation for an event.

        Uses heuristics without API call for fast estimation.
        """
        return self._analyzer.estimate_complexity(event_context)

    async def estimate_resources(
        self, event_context: EventContext
    ) -> Dict[str, Any]:
        """
        Estimate resources needed for handling an event.

        Returns:
            Dictionary with estimated budget_tokens, time, and tools
        """
        complexity = await self.estimate_complexity(event_context)

        return {
            "complexity": complexity.value,
            "budget_tokens": get_budget_tokens(complexity),
            "estimated_duration_seconds": self._estimate_duration(complexity),
            "suggested_tools": self._suggest_tools(event_context),
        }

    def _estimate_duration(self, complexity: EventComplexity) -> int:
        """Estimate duration based on complexity."""
        duration_map = {
            EventComplexity.SIMPLE: 300,  # 5 minutes
            EventComplexity.MODERATE: 900,  # 15 minutes
            EventComplexity.COMPLEX: 1800,  # 30 minutes
            EventComplexity.CRITICAL: 3600,  # 1 hour
        }
        return duration_map.get(complexity, 900)

    def _suggest_tools(self, event_context: EventContext) -> List[str]:
        """Suggest tools based on event context."""
        tools = ["servicenow", "teams_notify"]  # Always include these

        description_lower = event_context.description.lower()

        if "azure" in description_lower or "vm" in description_lower:
            tools.extend(["azure_vm", "azure_monitor"])

        if "database" in description_lower or "sql" in description_lower:
            tools.append("database_query")

        if "config" in description_lower or "setting" in description_lower:
            tools.append("file_operation")

        if "server" in description_lower or "service" in description_lower:
            tools.append("shell_command")

        return list(set(tools))
