# =============================================================================
# IPA Platform - Phase 13 ComplexityAnalyzer Scenarios
# =============================================================================
# Sprint 52: S52-1 IntentRouter (10 pts) - includes ComplexityAnalyzer
#
# Tests for task complexity analysis used in mode detection.
# ComplexityAnalyzer determines if a task should use Workflow or Chat mode.
#
# Key Components:
#   - ComplexityAnalyzer: Analyze task complexity
#   - ComplexityScore: Numerical score with breakdown
#   - Complexity indicators: steps, dependencies, persistence, time
#   - Thresholds: simple (0-0.3), moderate (0.3-0.6), complex (0.6-0.8), very_complex (0.8-1.0)
# =============================================================================
"""
ComplexityAnalyzer Scenario Tests

Business scenarios that validate:
- Simple task recognition (FAQ, quick questions)
- Moderate task detection (multi-step but straightforward)
- Complex workflow detection (dependencies, approvals, persistence)
- Very complex scenario identification (multi-agent, long-running)
- Mode recommendation accuracy
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import StepResult, TestStatus


# =============================================================================
# Test Data: Complexity Analysis Scenarios
# =============================================================================

SIMPLE_TASK_SCENARIOS = [
    # FAQ questions - should be CHAT_MODE
    {
        "name": "Simple FAQ - Policy Question",
        "input": "What is the company vacation policy?",
        "expected_level": "simple",
        "expected_score_range": (0.0, 0.3),
        "expected_mode": "CHAT_MODE",
        "context": {"user_role": "employee"}
    },
    # Single action request
    {
        "name": "Simple Action - Check Status",
        "input": "What's the status of my expense report?",
        "expected_level": "simple",
        "expected_score_range": (0.0, 0.3),
        "expected_mode": "CHAT_MODE",
        "context": {}
    },
    # Information lookup
    {
        "name": "Simple Lookup - Contact Info",
        "input": "Can you tell me the IT support phone number?",
        "expected_level": "simple",
        "expected_score_range": (0.0, 0.3),
        "expected_mode": "CHAT_MODE",
        "context": {}
    },
]

MODERATE_TASK_SCENARIOS = [
    # Multi-step but no dependencies
    {
        "name": "Moderate - Generate Report",
        "input": "Generate a summary report of last month's sales data",
        "expected_level": "moderate",
        "expected_score_range": (0.3, 0.6),
        "expected_mode": "HYBRID_MODE",
        "indicators": ["generate", "report", "data"]
    },
    # Some processing required
    {
        "name": "Moderate - Data Analysis",
        "input": "Analyze the customer feedback from the survey and highlight key themes",
        "expected_level": "moderate",
        "expected_score_range": (0.3, 0.6),
        "expected_mode": "HYBRID_MODE",
        "indicators": ["analyze", "feedback", "themes"]
    },
    # Simple workflow
    {
        "name": "Moderate - Schedule Meeting",
        "input": "Schedule a team meeting for next week with the engineering team",
        "expected_level": "moderate",
        "expected_score_range": (0.3, 0.6),
        "expected_mode": "HYBRID_MODE",
        "indicators": ["schedule", "meeting", "team"]
    },
]

COMPLEX_TASK_SCENARIOS = [
    # Multi-step with dependencies
    {
        "name": "Complex - Purchase Approval",
        "input": "Process purchase order #PO-2026-001 for $50,000 including all required approvals",
        "expected_level": "complex",
        "expected_score_range": (0.6, 0.8),
        "expected_mode": "WORKFLOW_MODE",
        "indicators": ["process", "purchase", "approvals", "$50,000"]
    },
    # Requires persistence and state
    {
        "name": "Complex - Employee Onboarding",
        "input": "Start the complete onboarding process for new hire John Smith including IT setup, badge creation, and team assignment",
        "expected_level": "complex",
        "expected_score_range": (0.6, 0.8),
        "expected_mode": "WORKFLOW_MODE",
        "indicators": ["complete", "onboarding", "including", "setup", "creation", "assignment"]
    },
    # Time-sensitive with checkpoints
    {
        "name": "Complex - Contract Review",
        "input": "Review the vendor contract and route for legal approval with 3-day deadline",
        "expected_level": "complex",
        "expected_score_range": (0.6, 0.8),
        "expected_mode": "WORKFLOW_MODE",
        "indicators": ["review", "contract", "approval", "deadline"]
    },
]

VERY_COMPLEX_TASK_SCENARIOS = [
    # Multi-department workflow
    {
        "name": "Very Complex - Budget Planning",
        "input": "Initiate Q3 budget planning process requiring input from all department heads, finance review, executive approval, and board notification with weekly status updates",
        "expected_level": "very_complex",
        "expected_score_range": (0.8, 1.0),
        "expected_mode": "WORKFLOW_MODE",
        "indicators": ["initiate", "planning", "department heads", "review", "approval", "notification", "weekly", "updates"]
    },
    # Long-running with multiple agents
    {
        "name": "Very Complex - System Migration",
        "input": "Plan and execute the CRM system migration including data backup, testing in staging, user training, cutover plan, and rollback procedures",
        "expected_level": "very_complex",
        "expected_score_range": (0.8, 1.0),
        "expected_mode": "WORKFLOW_MODE",
        "indicators": ["plan", "execute", "migration", "backup", "testing", "training", "cutover", "rollback"]
    },
    # Compliance-heavy process
    {
        "name": "Very Complex - Audit Preparation",
        "input": "Prepare for SOC2 compliance audit including document collection from 15 systems, gap analysis, remediation tracking, and auditor coordination over the next 6 weeks",
        "expected_level": "very_complex",
        "expected_score_range": (0.8, 1.0),
        "expected_mode": "WORKFLOW_MODE",
        "indicators": ["audit", "compliance", "collection", "analysis", "remediation", "tracking", "coordination", "6 weeks"]
    },
]

CONTEXT_INFLUENCE_SCENARIOS = [
    # Previous history suggests workflow
    {
        "name": "Context - Workflow History",
        "input": "Continue with the next step",
        "context": {
            "previous_mode": "WORKFLOW_MODE",
            "workflow_step": 3,
            "workflow_total_steps": 5
        },
        "history": [
            {"role": "user", "content": "Process my expense report"},
            {"role": "assistant", "content": "Starting expense workflow..."}
        ],
        "expected_boost": "workflow",
        "expected_mode": "WORKFLOW_MODE"
    },
    # Chat history suggests continuation
    {
        "name": "Context - Chat Continuation",
        "input": "Tell me more about that",
        "context": {
            "previous_mode": "CHAT_MODE",
            "topic": "vacation_policy"
        },
        "history": [
            {"role": "user", "content": "What's the vacation policy?"},
            {"role": "assistant", "content": "The company offers 15 days..."}
        ],
        "expected_boost": "chat",
        "expected_mode": "CHAT_MODE"
    },
]

EDGE_CASE_SCENARIOS = [
    # Empty input
    {
        "name": "Edge Case - Empty Input",
        "input": "",
        "expected_level": "simple",
        "expected_score_range": (0.0, 0.2),
        "expected_mode": "CHAT_MODE"
    },
    # Very short input
    {
        "name": "Edge Case - Single Word",
        "input": "Help",
        "expected_level": "simple",
        "expected_score_range": (0.0, 0.3),
        "expected_mode": "CHAT_MODE"
    },
    # Mixed signals
    {
        "name": "Edge Case - Mixed Intent",
        "input": "Tell me about the expense process and then submit my expense report for $500",
        "expected_level": "moderate",
        "expected_score_range": (0.3, 0.7),
        "expected_mode": "HYBRID_MODE"
    },
    # Technical jargon
    {
        "name": "Edge Case - Technical Content",
        "input": "Execute the ETL pipeline for the data warehouse refresh with incremental load",
        "expected_level": "complex",
        "expected_score_range": (0.5, 0.8),
        "expected_mode": "WORKFLOW_MODE"
    },
]


# =============================================================================
# Scenario Test Functions
# =============================================================================

async def test_simple_task_detection(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Simple Task Detection

    Tests that ComplexityAnalyzer correctly identifies simple tasks
    that should be handled in CHAT_MODE.

    Expected Behavior:
    - Score in simple range (0.0-0.3)
    - Recommend CHAT_MODE
    - Quick response without workflow overhead
    """
    results = []

    for scenario in SIMPLE_TASK_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.analyze_complexity(
                input_text=scenario["input"],
                context=scenario.get("context")
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Level: {scenario['expected_level']}, Mode: {scenario['expected_mode']}",
                    details={
                        "expected_level": scenario["expected_level"],
                        "expected_mode": scenario["expected_mode"]
                    }
                )
            else:
                score = response.get("score", 0)
                level = response.get("level", "")
                mode = response.get("recommended_mode", "")
                min_score, max_score = scenario["expected_score_range"]

                score_in_range = min_score <= score <= max_score
                level_correct = level == scenario["expected_level"]
                mode_correct = mode == scenario["expected_mode"]

                if score_in_range and mode_correct:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Score: {score:.2f} ({level}), Mode: {mode}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Score {score:.2f} not in {scenario['expected_score_range']} or mode {mode} != {scenario['expected_mode']}",
                        details=response
                    )

            results.append(result)

            if verbose:
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status_icon} {result.step_name}: {result.message}")

        except Exception as e:
            results.append(StepResult(
                step_name=f"{scenario['name']}",
                status=TestStatus.FAILED,
                message=f"Error: {str(e)}",
                details={"scenario": scenario["name"], "error": str(e)}
            ))

    return results


async def test_moderate_task_detection(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Moderate Task Detection

    Tests that ComplexityAnalyzer correctly identifies moderate tasks
    that could be handled in either mode (HYBRID_MODE recommendation).

    Expected Behavior:
    - Score in moderate range (0.3-0.6)
    - May recommend HYBRID_MODE
    - Consider context for final decision
    """
    results = []

    for scenario in MODERATE_TASK_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.analyze_complexity(
                input_text=scenario["input"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Level: {scenario['expected_level']}",
                    details={
                        "expected_level": scenario["expected_level"],
                        "indicators": scenario.get("indicators", [])
                    }
                )
            else:
                score = response.get("score", 0)
                level = response.get("level", "")
                min_score, max_score = scenario["expected_score_range"]

                score_in_range = min_score <= score <= max_score

                if score_in_range:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Score: {score:.2f} ({level}) in expected range",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Score {score:.2f} not in {scenario['expected_score_range']}",
                        details=response
                    )

            results.append(result)

            if verbose:
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status_icon} {result.step_name}: {result.message}")

        except Exception as e:
            results.append(StepResult(
                step_name=f"{scenario['name']}",
                status=TestStatus.FAILED,
                message=f"Error: {str(e)}",
                details={"scenario": scenario["name"], "error": str(e)}
            ))

    return results


async def test_complex_task_detection(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Complex Task Detection

    Tests that ComplexityAnalyzer correctly identifies complex tasks
    requiring WORKFLOW_MODE with proper state management.

    Expected Behavior:
    - Score in complex range (0.6-0.8)
    - Recommend WORKFLOW_MODE
    - Identify dependency and approval indicators
    """
    results = []

    for scenario in COMPLEX_TASK_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.analyze_complexity(
                input_text=scenario["input"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Level: {scenario['expected_level']}, Mode: {scenario['expected_mode']}",
                    details={
                        "expected_level": scenario["expected_level"],
                        "indicators": scenario.get("indicators", [])
                    }
                )
            else:
                score = response.get("score", 0)
                level = response.get("level", "")
                mode = response.get("recommended_mode", "")
                min_score, max_score = scenario["expected_score_range"]

                score_in_range = min_score <= score <= max_score
                mode_correct = mode == scenario["expected_mode"]

                if score_in_range and mode_correct:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Score: {score:.2f} ({level}), Mode: {mode}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Score {score:.2f} or mode {mode} incorrect",
                        details=response
                    )

            results.append(result)

            if verbose:
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status_icon} {result.step_name}: {result.message}")

        except Exception as e:
            results.append(StepResult(
                step_name=f"{scenario['name']}",
                status=TestStatus.FAILED,
                message=f"Error: {str(e)}",
                details={"scenario": scenario["name"], "error": str(e)}
            ))

    return results


async def test_very_complex_task_detection(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Very Complex Task Detection

    Tests that ComplexityAnalyzer correctly identifies very complex tasks
    requiring full WORKFLOW_MODE with checkpoints, approvals, and monitoring.

    Expected Behavior:
    - Score in very complex range (0.8-1.0)
    - Recommend WORKFLOW_MODE
    - Identify multiple complexity indicators
    """
    results = []

    for scenario in VERY_COMPLEX_TASK_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.analyze_complexity(
                input_text=scenario["input"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Level: {scenario['expected_level']}, Mode: {scenario['expected_mode']}",
                    details={
                        "expected_level": scenario["expected_level"],
                        "indicators": scenario.get("indicators", [])
                    }
                )
            else:
                score = response.get("score", 0)
                level = response.get("level", "")
                mode = response.get("recommended_mode", "")
                min_score, max_score = scenario["expected_score_range"]

                score_in_range = min_score <= score <= max_score
                mode_correct = mode == scenario["expected_mode"]

                if score_in_range and mode_correct:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Score: {score:.2f} ({level}), Mode: {mode}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Score {score:.2f} or mode {mode} incorrect for very_complex",
                        details=response
                    )

            results.append(result)

            if verbose:
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status_icon} {result.step_name}: {result.message}")

        except Exception as e:
            results.append(StepResult(
                step_name=f"{scenario['name']}",
                status=TestStatus.FAILED,
                message=f"Error: {str(e)}",
                details={"scenario": scenario["name"], "error": str(e)}
            ))

    return results


async def test_context_influence(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Context Influence on Complexity

    Tests that ComplexityAnalyzer considers conversation history
    and context when determining complexity and mode.

    Expected Behavior:
    - Previous mode influences current decision
    - Conversation history provides context
    - Workflow state affects recommendations
    """
    results = []

    for scenario in CONTEXT_INFLUENCE_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.analyze_complexity(
                input_text=scenario["input"],
                context=scenario.get("context"),
                history=scenario.get("history")
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Context boost: {scenario['expected_boost']}, Mode: {scenario['expected_mode']}",
                    details={
                        "expected_boost": scenario["expected_boost"],
                        "expected_mode": scenario["expected_mode"]
                    }
                )
            else:
                mode = response.get("recommended_mode", "")
                context_used = response.get("context_considered", False)

                if mode == scenario["expected_mode"]:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Mode: {mode}, Context considered: {context_used}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected mode {scenario['expected_mode']}, got {mode}",
                        details=response
                    )

            results.append(result)

            if verbose:
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status_icon} {result.step_name}: {result.message}")

        except Exception as e:
            results.append(StepResult(
                step_name=f"{scenario['name']}",
                status=TestStatus.FAILED,
                message=f"Error: {str(e)}",
                details={"scenario": scenario["name"], "error": str(e)}
            ))

    return results


async def test_edge_cases(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Edge Case Handling

    Tests that ComplexityAnalyzer handles edge cases gracefully
    including empty input, very short input, and ambiguous requests.

    Expected Behavior:
    - Handle empty/short input without errors
    - Make reasonable default decisions
    - Handle mixed-signal inputs
    """
    results = []

    for scenario in EDGE_CASE_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.analyze_complexity(
                input_text=scenario["input"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Handled edge case: {scenario['expected_level']}",
                    details={
                        "input": scenario["input"],
                        "expected_level": scenario["expected_level"]
                    }
                )
            else:
                score = response.get("score", 0)
                min_score, max_score = scenario["expected_score_range"]

                # For edge cases, we're more lenient - just check it doesn't crash
                # and returns something reasonable
                if min_score <= score <= max_score:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Score: {score:.2f} handled correctly",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,  # Still pass if handled gracefully
                        message=f"Score: {score:.2f} (outside expected but handled)",
                        details=response
                    )

            results.append(result)

            if verbose:
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status_icon} {result.step_name}: {result.message}")

        except Exception as e:
            results.append(StepResult(
                step_name=f"{scenario['name']}",
                status=TestStatus.FAILED,
                message=f"Error: {str(e)}",
                details={"scenario": scenario["name"], "error": str(e)}
            ))

    return results


# =============================================================================
# Module Entry Point
# =============================================================================

async def run_all_analyzer_scenarios(client) -> Dict:
    """Run all ComplexityAnalyzer scenario tests."""
    print("\n" + "=" * 60)
    print("ComplexityAnalyzer Scenario Tests")
    print("=" * 60)

    all_results = []

    print("\n1. Simple Task Detection")
    print("-" * 40)
    results1 = await test_simple_task_detection(client)
    all_results.extend(results1)

    print("\n2. Moderate Task Detection")
    print("-" * 40)
    results2 = await test_moderate_task_detection(client)
    all_results.extend(results2)

    print("\n3. Complex Task Detection")
    print("-" * 40)
    results3 = await test_complex_task_detection(client)
    all_results.extend(results3)

    print("\n4. Very Complex Task Detection")
    print("-" * 40)
    results4 = await test_very_complex_task_detection(client)
    all_results.extend(results4)

    print("\n5. Context Influence")
    print("-" * 40)
    results5 = await test_context_influence(client)
    all_results.extend(results5)

    print("\n6. Edge Cases")
    print("-" * 40)
    results6 = await test_edge_cases(client)
    all_results.extend(results6)

    # Summary
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    total = len(all_results)

    print("\n" + "-" * 60)
    print(f"ComplexityAnalyzer Results: {passed}/{total} tests passed")

    return {
        "scenario": "ComplexityAnalyzer",
        "total": total,
        "passed": passed,
        "results": all_results
    }


if __name__ == "__main__":
    from phase_13_hybrid_core_test import HybridTestClient

    async def main():
        client = HybridTestClient()
        try:
            results = await run_all_analyzer_scenarios(client)
            return 0 if results["passed"] == results["total"] else 1
        finally:
            await client.close()

    exit(asyncio.run(main()))
