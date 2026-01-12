# =============================================================================
# IPA Platform - Result Verifier
# =============================================================================
# Sprint 79: S79-1 - Claude 自主規劃引擎 (13 pts)
#
# This module provides result verification capabilities, including:
# - Outcome validation against expected results
# - Quality scoring of execution results
# - Lessons learned extraction for mem0 storage
# =============================================================================

import logging
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from .types import (
    AutonomousPlan,
    PlanStatus,
    StepStatus,
    VerificationResult,
)

logger = logging.getLogger(__name__)


# Verification prompt template
VERIFICATION_PROMPT_TEMPLATE = """You are an IT operations quality assessor. Verify the execution results of an autonomous plan.

## Plan Summary
- Plan ID: {plan_id}
- Event ID: {event_id}
- Total Steps: {total_steps}
- Completed Steps: {completed_steps}
- Failed Steps: {failed_steps}

## Expected Outcomes
{expected_outcomes}

## Actual Results
{actual_results}

## Verification Tasks

1. **Outcome Validation**: For each expected outcome, determine if it was achieved.

2. **Quality Score**: Rate the overall execution quality (0.0 to 1.0):
   - 1.0: All outcomes achieved, no issues
   - 0.8: Most outcomes achieved, minor issues
   - 0.6: Some outcomes achieved, some issues
   - 0.4: Few outcomes achieved, significant issues
   - 0.2: Minimal success, major issues
   - 0.0: Complete failure

3. **Lessons Learned**: What can be improved for future similar events?

4. **Recommendations**: Any follow-up actions needed?

## Response Format

Provide your verification in the following JSON format:
```json
{{
    "success": true|false,
    "outcomes_met": ["outcome1", "outcome2"],
    "outcomes_failed": ["outcome3"],
    "quality_score": 0.85,
    "lessons_learned": ["lesson1", "lesson2"],
    "recommendations": ["recommendation1"]
}}
```
"""


class ResultVerifier:
    """
    Verifies the results of autonomous plan execution.

    Uses Claude to analyze execution outcomes, generate quality scores,
    and extract lessons learned for continuous improvement.

    Example:
        verifier = ResultVerifier(client)
        result = await verifier.verify(plan)
        print(f"Success: {result.success}")
        print(f"Quality: {result.quality_score}")
    """

    def __init__(
        self,
        client: AsyncAnthropic,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the ResultVerifier.

        Args:
            client: AsyncAnthropic client instance
            model: Model to use for verification
        """
        self._client = client
        self._model = model

    async def verify(
        self,
        plan: AutonomousPlan,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """
        Verify the execution results of a plan.

        Args:
            plan: The executed plan to verify
            additional_context: Optional additional verification context

        Returns:
            VerificationResult with success status, quality score, and insights
        """
        logger.info(f"Verifying plan {plan.id}")

        # Quick verification for incomplete plans
        if plan.status not in [PlanStatus.COMPLETED, PlanStatus.VERIFYING]:
            return self._create_incomplete_result(plan)

        # Build verification prompt
        prompt = self._build_verification_prompt(plan, additional_context)

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse verification response
            result = self._parse_verification_response(plan.id, response)

            # Update plan with verification
            plan.verification_result = result.to_dict()
            plan.status = PlanStatus.COMPLETED if result.success else PlanStatus.FAILED

            logger.info(
                f"Verification complete: success={result.success}, "
                f"quality={result.quality_score}"
            )

            return result

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return self._create_error_result(plan.id, str(e))

    def _build_verification_prompt(
        self,
        plan: AutonomousPlan,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the verification prompt."""
        # Collect expected outcomes
        expected_outcomes = "\n".join(
            f"- Step {s.step_number}: {s.expected_outcome}"
            for s in plan.steps
            if s.expected_outcome
        )

        # Collect actual results
        actual_results = "\n".join(
            f"- Step {s.step_number} ({s.status.value}): {s.result or s.error or 'No result'}"
            for s in plan.steps
        )

        prompt = VERIFICATION_PROMPT_TEMPLATE.format(
            plan_id=plan.id,
            event_id=plan.event_id,
            total_steps=len(plan.steps),
            completed_steps=len([s for s in plan.steps if s.status == StepStatus.COMPLETED]),
            failed_steps=len([s for s in plan.steps if s.status == StepStatus.FAILED]),
            expected_outcomes=expected_outcomes or "No specific outcomes defined",
            actual_results=actual_results,
        )

        if additional_context:
            prompt += f"\n\n## Additional Context\n{additional_context}"

        return prompt

    def _parse_verification_response(
        self, plan_id: str, response: Any
    ) -> VerificationResult:
        """Parse the verification response."""
        import json

        content = response.content[0].text if response.content else "{}"

        try:
            # Find JSON block
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(content[json_start:json_end])

                return VerificationResult(
                    plan_id=plan_id,
                    success=data.get("success", False),
                    expected_outcomes_met=data.get("outcomes_met", []),
                    expected_outcomes_failed=data.get("outcomes_failed", []),
                    actual_results={},  # Populated from plan steps
                    quality_score=float(data.get("quality_score", 0.5)),
                    lessons_learned=data.get("lessons_learned", []),
                    recommendations=data.get("recommendations", []),
                )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse verification JSON: {e}")

        # Fallback result
        return VerificationResult(
            plan_id=plan_id,
            success=False,
            expected_outcomes_met=[],
            expected_outcomes_failed=["Unable to verify outcomes"],
            actual_results={},
            quality_score=0.0,
            lessons_learned=["Verification parsing failed"],
            recommendations=["Review execution manually"],
        )

    def _create_incomplete_result(self, plan: AutonomousPlan) -> VerificationResult:
        """Create a result for incomplete plans."""
        return VerificationResult(
            plan_id=plan.id,
            success=False,
            expected_outcomes_met=[],
            expected_outcomes_failed=["Plan not completed"],
            actual_results={"status": plan.status.value, "error": plan.error},
            quality_score=0.0,
            lessons_learned=[],
            recommendations=["Investigate plan failure", "Review execution logs"],
        )

    def _create_error_result(self, plan_id: str, error: str) -> VerificationResult:
        """Create a result for verification errors."""
        return VerificationResult(
            plan_id=plan_id,
            success=False,
            expected_outcomes_met=[],
            expected_outcomes_failed=["Verification failed"],
            actual_results={"verification_error": error},
            quality_score=0.0,
            lessons_learned=[],
            recommendations=["Retry verification", "Check API connectivity"],
        )

    async def verify_step(
        self,
        plan: AutonomousPlan,
        step_number: int,
    ) -> Dict[str, Any]:
        """
        Verify a specific step's execution.

        Args:
            plan: The plan containing the step
            step_number: The step number to verify

        Returns:
            Dictionary with step verification details
        """
        step = next(
            (s for s in plan.steps if s.step_number == step_number), None
        )

        if not step:
            return {"error": f"Step {step_number} not found"}

        return {
            "step_number": step_number,
            "action": step.action,
            "status": step.status.value,
            "expected_outcome": step.expected_outcome,
            "actual_result": step.result,
            "success": step.status == StepStatus.COMPLETED,
            "error": step.error,
            "duration_seconds": (
                (step.completed_at - step.started_at).total_seconds()
                if step.completed_at and step.started_at
                else None
            ),
        }

    def calculate_quality_score(self, plan: AutonomousPlan) -> float:
        """
        Calculate quality score based on step results.

        This is a quick heuristic calculation without API call.
        """
        if not plan.steps:
            return 0.0

        total = len(plan.steps)
        completed = len([s for s in plan.steps if s.status == StepStatus.COMPLETED])
        failed = len([s for s in plan.steps if s.status == StepStatus.FAILED])

        # Base score from completion rate
        completion_rate = completed / total

        # Penalty for failures
        failure_penalty = failed / total * 0.3

        # Calculate final score
        score = max(0.0, min(1.0, completion_rate - failure_penalty))

        return round(score, 2)

    def extract_lessons(self, plan: AutonomousPlan) -> List[str]:
        """
        Extract lessons learned from plan execution.

        This is a heuristic extraction without API call.
        """
        lessons = []

        # Check for failed steps
        failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]
        for step in failed_steps:
            if step.error:
                lessons.append(
                    f"Step '{step.action}' failed: Consider alternative approach or "
                    f"add better error handling for: {step.error[:100]}"
                )

        # Check for slow steps
        for step in plan.steps:
            if step.started_at and step.completed_at:
                duration = (step.completed_at - step.started_at).total_seconds()
                if duration > step.estimated_duration_seconds * 2:
                    lessons.append(
                        f"Step '{step.action}' took {duration:.0f}s "
                        f"(expected {step.estimated_duration_seconds}s). "
                        "Consider optimizing or increasing timeout."
                    )

        # Check overall execution
        if plan.started_at and plan.completed_at:
            total_duration = (plan.completed_at - plan.started_at).total_seconds()
            if total_duration > plan.estimated_duration_seconds * 1.5:
                lessons.append(
                    f"Plan took {total_duration:.0f}s "
                    f"(estimated {plan.estimated_duration_seconds}s). "
                    "Review step estimates for accuracy."
                )

        return lessons
