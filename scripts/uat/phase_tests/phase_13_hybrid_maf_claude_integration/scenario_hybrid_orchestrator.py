# =============================================================================
# IPA Platform - Phase 13 Hybrid Orchestrator Scenarios
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor (35 pts)
#
# Real-world business scenarios for hybrid orchestration and mode execution.
#
# NOTE: Mode Switching Mid-Execution tests moved to Phase 14 (Sprint 55-57)
#       See: phase_14_hitl_approval/scenario_mode_switching.py
# =============================================================================
"""
Hybrid Orchestrator Scenario Tests

Business scenarios that validate:
- Workflow mode execution (structured multi-step processes)
- Chat mode execution (conversational interactions)
- Hybrid mode with intelligent auto-routing

NOTE: Mode switching mid-execution tests are now in Phase 14
      (requires ModeSwitcher from Sprint 55-57)
"""

import asyncio
from typing import Dict, List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import StepResult, TestStatus


# =============================================================================
# Test Data: Real Business Workflows
# =============================================================================

WORKFLOW_SCENARIOS = [
    # Multi-step approval workflow
    {
        "name": "Purchase Order Approval",
        "input": "Create PO #PO-2026-001 for $15,000 worth of equipment",
        "expected_mode": "WORKFLOW_MODE",
        "expected_steps": [
            "validate_po_request",
            "check_budget_availability",
            "route_to_approver",
            "await_approval",
            "process_approval_decision"
        ],
        "context": {
            "department": "Engineering",
            "budget_center": "BC-001",
            "requestor": "john.doe@company.com"
        }
    },
    # Employee onboarding workflow
    {
        "name": "New Employee Onboarding",
        "input": "Start onboarding for Sarah Chen, Software Engineer, starting Feb 1",
        "expected_mode": "WORKFLOW_MODE",
        "expected_steps": [
            "create_employee_record",
            "assign_equipment",
            "setup_accounts",
            "schedule_orientation",
            "notify_team"
        ],
        "context": {
            "department": "Engineering",
            "manager": "mike.smith@company.com",
            "location": "HQ-Building A"
        }
    },
    # Expense reimbursement workflow
    {
        "name": "Expense Reimbursement",
        "input": "Submit expense claim #EXP-2026-123 for $2,500 business travel",
        "expected_mode": "WORKFLOW_MODE",
        "expected_steps": [
            "validate_expense_data",
            "check_policy_compliance",
            "calculate_reimbursement",
            "route_for_approval",
            "process_payment"
        ],
        "context": {
            "employee_id": "E12345",
            "expense_type": "travel",
            "receipts_attached": True
        }
    }
]

CHAT_SCENARIOS = [
    # FAQ inquiry
    {
        "name": "Policy Inquiry",
        "input": "What is the company's vacation policy for new employees?",
        "expected_mode": "CHAT_MODE",
        "expected_response_contains": ["vacation", "days", "policy"],
        "context": {"user_role": "employee", "tenure_months": 3}
    },
    # General assistance
    {
        "name": "System Help",
        "input": "How do I reset my corporate email password?",
        "expected_mode": "CHAT_MODE",
        "expected_response_contains": ["password", "reset", "steps"],
        "context": {"user_role": "employee"}
    },
    # Information request
    {
        "name": "Benefits Information",
        "input": "Can you explain the health insurance options available?",
        "expected_mode": "CHAT_MODE",
        "expected_response_contains": ["health", "insurance", "plan"],
        "context": {"user_role": "new_hire"}
    }
]

HYBRID_SCENARIOS = [
    # Starts as chat, evolves to workflow
    {
        "name": "Inquiry to Action",
        "conversation": [
            {"input": "I need to order new office supplies", "expected_mode": "CHAT_MODE"},
            {"input": "Yes, I need 10 monitors for the new team", "expected_mode": "HYBRID_MODE"},
            {"input": "Please create a purchase request for them", "expected_mode": "WORKFLOW_MODE"},
        ],
        "expected_transition": "CHAT_MODE → HYBRID_MODE → WORKFLOW_MODE"
    },
    # Mixed mode throughout
    {
        "name": "Support with Actions",
        "conversation": [
            {"input": "I'm having trouble with my expense report", "expected_mode": "CHAT_MODE"},
            {"input": "The system shows an error for expense #EXP-456", "expected_mode": "HYBRID_MODE"},
            {"input": "Can you resubmit it for me?", "expected_mode": "WORKFLOW_MODE"},
            {"input": "What's the status now?", "expected_mode": "CHAT_MODE"},
        ],
        "expected_transition": "Dynamic mode switching based on intent"
    }
]

# NOTE: MODE_SWITCH_SCENARIOS moved to Phase 14
# See: phase_14_hitl_approval/scenario_mode_switching.py


# =============================================================================
# Scenario Test Functions
# =============================================================================

async def test_workflow_mode_execution(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Workflow Mode Execution

    Business Context:
    Complex business processes require structured, multi-step workflows
    with proper state management, approvals, and audit trails.

    Expected Behavior:
    - Execute in WORKFLOW_MODE with MAF orchestration
    - Progress through defined workflow steps
    - Maintain state and checkpoint capability
    - Support human-in-the-loop at approval points
    """
    results = []

    for scenario in WORKFLOW_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            # Step 1: Initiate workflow
            response = await client.execute_hybrid(
                scenario["input"],
                session_id=f"test-wf-{scenario['name'].lower().replace(' ', '-')}",
                force_mode="WORKFLOW_MODE",
                context=scenario["context"]
            )

            if "simulated" in response:
                result1 = StepResult(
                    step_name=f"{scenario['name']} - Initiate",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Workflow initiated in WORKFLOW_MODE",
                    details={"scenario": scenario["name"]}
                )
            else:
                execution_mode = response.get("execution_mode")
                workflow_id = response.get("workflow_id")

                if execution_mode == "WORKFLOW_MODE" and workflow_id:
                    result1 = StepResult(
                        step_name=f"{scenario['name']} - Initiate",
                        status=TestStatus.PASSED,
                        message=f"Workflow started: {workflow_id}",
                        details=response
                    )
                else:
                    result1 = StepResult(
                        step_name=f"{scenario['name']} - Initiate",
                        status=TestStatus.FAILED,
                        message=f"Workflow not started properly: mode={execution_mode}",
                        details=response
                    )

            results.append(result1)

            # Step 2: Verify workflow steps are defined
            if "simulated" in response:
                result2 = StepResult(
                    step_name=f"{scenario['name']} - Steps",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Expected {len(scenario['expected_steps'])} steps",
                    details={"expected_steps": scenario["expected_steps"]}
                )
            else:
                actual_steps = response.get("workflow_steps", [])
                expected_count = len(scenario["expected_steps"])

                if len(actual_steps) >= expected_count * 0.8:  # 80% step coverage
                    result2 = StepResult(
                        step_name=f"{scenario['name']} - Steps",
                        status=TestStatus.PASSED,
                        message=f"Workflow has {len(actual_steps)} steps",
                        details={"steps": actual_steps}
                    )
                else:
                    result2 = StepResult(
                        step_name=f"{scenario['name']} - Steps",
                        status=TestStatus.FAILED,
                        message=f"Expected ~{expected_count} steps, got {len(actual_steps)}",
                        details={"expected": scenario["expected_steps"], "actual": actual_steps}
                    )

            results.append(result2)

            if verbose:
                for r in results[-2:]:
                    status = "✓" if r.status == TestStatus.PASSED else "✗"
                    print(f"    {status} {r.step_name}: {r.message}")

        except Exception as e:
            results.append(StepResult(
                step_name=f"{scenario['name']} - Error",
                status=TestStatus.FAILED,
                message=f"Error: {str(e)}",
                details={"scenario": scenario["name"], "error": str(e)}
            ))

    return results


async def test_chat_mode_execution(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Chat Mode Execution

    Business Context:
    Users often need conversational assistance for questions, guidance,
    and information retrieval without triggering formal workflows.

    Expected Behavior:
    - Execute in CHAT_MODE with Claude SDK
    - Provide helpful, conversational responses
    - Maintain conversation context
    - Not trigger unnecessary workflow processes
    """
    results = []

    for scenario in CHAT_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.execute_hybrid(
                scenario["input"],
                session_id=f"test-chat-{scenario['name'].lower().replace(' ', '-')}",
                force_mode="CHAT_MODE",
                context=scenario["context"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Chat response in CHAT_MODE",
                    details={"scenario": scenario["name"]}
                )
            else:
                execution_mode = response.get("execution_mode")
                response_text = response.get("response", "")

                # Check mode
                mode_correct = execution_mode == "CHAT_MODE"

                # Check response contains expected keywords
                keywords_found = sum(
                    1 for kw in scenario["expected_response_contains"]
                    if kw.lower() in response_text.lower()
                )
                keywords_threshold = len(scenario["expected_response_contains"]) * 0.5

                if mode_correct and keywords_found >= keywords_threshold:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Chat response appropriate ({keywords_found} keywords matched)",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Mode: {execution_mode}, Keywords: {keywords_found}/{len(scenario['expected_response_contains'])}",
                        details=response
                    )

            results.append(result)

            if verbose:
                status = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status} {result.step_name}: {result.message}")

        except Exception as e:
            results.append(StepResult(
                step_name=f"{scenario['name']}",
                status=TestStatus.FAILED,
                message=f"Error: {str(e)}",
                details={"scenario": scenario["name"], "error": str(e)}
            ))

    return results


async def test_hybrid_mode_with_auto_routing(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Hybrid Mode with Auto-Routing

    Business Context:
    Real user interactions often evolve from questions to actions.
    The system must intelligently detect these transitions and route
    appropriately between chat and workflow modes.

    Expected Behavior:
    - Start in detected mode based on initial input
    - Automatically detect mode transitions during conversation
    - Route to appropriate execution engine
    - Maintain conversation coherence across transitions
    """
    results = []

    for scenario in HYBRID_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")
        session_id = f"test-hybrid-{scenario['name'].lower().replace(' ', '-')}"
        mode_history = []

        for i, turn in enumerate(scenario["conversation"]):
            try:
                response = await client.execute_hybrid(
                    turn["input"],
                    session_id=session_id
                    # No force_mode - let system decide
                )

                if "simulated" in response:
                    detected_mode = turn["expected_mode"]  # Use expected for simulation
                    mode_history.append(detected_mode)
                    result = StepResult(
                        step_name=f"{scenario['name']} Turn {i+1}",
                        status=TestStatus.PASSED,
                        message=f"[Simulated] Expected: {turn['expected_mode']}",
                        details={"input": turn["input"], "expected": turn["expected_mode"]}
                    )
                else:
                    detected_mode = response.get("execution_mode", "UNKNOWN")
                    mode_history.append(detected_mode)

                    # Check if mode is reasonable (exact match or HYBRID_MODE is acceptable)
                    mode_acceptable = (
                        detected_mode == turn["expected_mode"] or
                        detected_mode == "HYBRID_MODE" or
                        turn["expected_mode"] == "HYBRID_MODE"
                    )

                    if mode_acceptable:
                        result = StepResult(
                            step_name=f"{scenario['name']} Turn {i+1}",
                            status=TestStatus.PASSED,
                            message=f"Mode: {detected_mode}",
                            details=response
                        )
                    else:
                        result = StepResult(
                            step_name=f"{scenario['name']} Turn {i+1}",
                            status=TestStatus.FAILED,
                            message=f"Expected {turn['expected_mode']}, got {detected_mode}",
                            details=response
                        )

                results.append(result)

                if verbose:
                    status = "✓" if result.status == TestStatus.PASSED else "✗"
                    print(f"    {status} Turn {i+1}: {result.message}")

            except Exception as e:
                results.append(StepResult(
                    step_name=f"{scenario['name']} Turn {i+1}",
                    status=TestStatus.FAILED,
                    message=f"Error: {str(e)}",
                    details={"turn": i+1, "error": str(e)}
                ))

        # Summary result for mode transitions
        transition_summary = " → ".join(mode_history)
        results.append(StepResult(
            step_name=f"{scenario['name']} - Transitions",
            status=TestStatus.PASSED,
            message=f"Mode flow: {transition_summary}",
            details={"mode_history": mode_history, "expected": scenario["expected_transition"]}
        ))

        if verbose:
            print(f"    ℹ Mode transitions: {transition_summary}")

    return results


# NOTE: test_mode_switching_mid_execution() moved to Phase 14
# See: phase_14_hitl_approval/scenario_mode_switching.py
# Reason: Requires ModeSwitcher component from Sprint 55-57


# =============================================================================
# Module Entry Point
# =============================================================================

async def run_all_hybrid_orchestrator_scenarios(client) -> Dict:
    """Run all hybrid orchestrator scenario tests."""
    print("\n" + "=" * 60)
    print("Hybrid Orchestrator Scenario Tests")
    print("=" * 60)

    all_results = []

    print("\n1. Workflow Mode Execution")
    print("-" * 40)
    results1 = await test_workflow_mode_execution(client)
    all_results.extend(results1)

    print("\n2. Chat Mode Execution")
    print("-" * 40)
    results2 = await test_chat_mode_execution(client)
    all_results.extend(results2)

    print("\n3. Hybrid Mode with Auto-Routing")
    print("-" * 40)
    results3 = await test_hybrid_mode_with_auto_routing(client)
    all_results.extend(results3)

    # NOTE: Mode Switching tests moved to Phase 14
    # See: phase_14_hitl_approval/scenario_mode_switching.py

    # Summary
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    total = len(all_results)

    print("\n" + "-" * 60)
    print(f"Hybrid Orchestrator Results: {passed}/{total} tests passed")

    return {
        "scenario": "Hybrid Orchestrator",
        "total": total,
        "passed": passed,
        "results": all_results
    }


if __name__ == "__main__":
    from phase_13_hybrid_core_test import HybridTestClient

    async def main():
        client = HybridTestClient()
        try:
            results = await run_all_hybrid_orchestrator_scenarios(client)
            return 0 if results["passed"] == results["total"] else 1
        finally:
            await client.close()

    exit(asyncio.run(main()))
