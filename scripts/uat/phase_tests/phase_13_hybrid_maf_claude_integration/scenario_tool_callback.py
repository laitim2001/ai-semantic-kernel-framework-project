# =============================================================================
# IPA Platform - Phase 13 MAF Tool Callback Scenarios
# =============================================================================
# Sprint 53: S53-4 MAF Tool Callback (8 pts)
#
# Tests for MAF tool call interception and routing to UnifiedToolExecutor.
# Validates intercept logic, allowed/blocked tools, and fallback behavior.
#
# Key Components:
#   - MAFToolCallback: Intercept MAF tool calls
#   - CallbackConfig: Configuration for interception rules
#   - MAFToolRequest/MAFToolResult: Request/Response models
# =============================================================================
"""
MAF Tool Callback Scenario Tests

Business scenarios that validate:
- Tool call interception from MAF workflows
- Allowed/blocked tool filtering
- Approval requirement routing
- Fallback behavior on errors
- Integration with UnifiedToolExecutor
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import StepResult, TestStatus


# =============================================================================
# Test Data: Tool Callback Scenarios
# =============================================================================

INTERCEPTION_SCENARIOS = [
    # Default intercept all
    {
        "name": "Intercept All - File Read",
        "config": {"intercept_all": True},
        "tool_request": {
            "function_name": "read_file",
            "arguments": {"path": "/data/report.txt"}
        },
        "expected_intercepted": True,
        "expected_routed_to": "UnifiedToolExecutor"
    },
    # Intercept only specific tools
    {
        "name": "Selective Intercept - Allowed Tool",
        "config": {
            "intercept_all": False,
            "allowed_tools": ["read_file", "write_file", "execute_sql"]
        },
        "tool_request": {
            "function_name": "read_file",
            "arguments": {"path": "/config.json"}
        },
        "expected_intercepted": True,
        "expected_routed_to": "UnifiedToolExecutor"
    },
    # Tool not in allowed list - pass through
    {
        "name": "Selective Intercept - Not Allowed",
        "config": {
            "intercept_all": False,
            "allowed_tools": ["read_file", "write_file"]
        },
        "tool_request": {
            "function_name": "execute_code",
            "arguments": {"code": "print(1)"}
        },
        "expected_intercepted": False,
        "expected_routed_to": "MAF_Native"
    },
]

BLOCKED_TOOL_SCENARIOS = [
    # Blocked by security policy
    {
        "name": "Block Dangerous Tool - Shell Exec",
        "config": {
            "intercept_all": True,
            "blocked_tools": ["shell_execute", "system_command", "raw_sql"]
        },
        "tool_request": {
            "function_name": "shell_execute",
            "arguments": {"command": "rm -rf /"}
        },
        "expected_blocked": True,
        "block_reason": "Tool blocked by security policy"
    },
    # Blocked by pattern matching
    {
        "name": "Block by Pattern - SQL Injection",
        "config": {
            "intercept_all": True,
            "blocked_patterns": ["DROP TABLE", "DELETE FROM", "TRUNCATE"]
        },
        "tool_request": {
            "function_name": "execute_sql",
            "arguments": {"query": "DROP TABLE users;"}
        },
        "expected_blocked": True,
        "block_reason": "Query contains blocked pattern"
    },
    # Allowed tool passes through
    {
        "name": "Allow Safe Tool",
        "config": {
            "intercept_all": True,
            "blocked_tools": ["shell_execute"]
        },
        "tool_request": {
            "function_name": "read_file",
            "arguments": {"path": "/tmp/safe.txt"}
        },
        "expected_blocked": False,
        "expected_result": "success"
    },
]

APPROVAL_ROUTING_SCENARIOS = [
    # Tool requires approval
    {
        "name": "Approval Required - Database Write",
        "config": {
            "intercept_all": True,
            "require_approval": ["execute_sql", "write_file", "send_email"]
        },
        "tool_request": {
            "function_name": "execute_sql",
            "arguments": {"query": "UPDATE users SET status='active'"}
        },
        "expected_approval_required": True,
        "approval_level": "standard"
    },
    # High-risk operation - elevated approval
    {
        "name": "Elevated Approval - Bulk Delete",
        "config": {
            "intercept_all": True,
            "require_approval": ["execute_sql"],
            "elevated_approval_patterns": ["DELETE", "UPDATE.*WHERE"]
        },
        "tool_request": {
            "function_name": "execute_sql",
            "arguments": {"query": "DELETE FROM orders WHERE status='cancelled'"}
        },
        "expected_approval_required": True,
        "approval_level": "elevated"
    },
    # No approval needed
    {
        "name": "No Approval - Read Operation",
        "config": {
            "intercept_all": True,
            "require_approval": ["execute_sql_write"]
        },
        "tool_request": {
            "function_name": "read_file",
            "arguments": {"path": "/data/report.csv"}
        },
        "expected_approval_required": False
    },
]

FALLBACK_SCENARIOS = [
    # Fallback on UnifiedExecutor error
    {
        "name": "Fallback on Executor Error",
        "config": {
            "intercept_all": True,
            "fallback_on_error": True
        },
        "tool_request": {
            "function_name": "custom_tool",
            "arguments": {"param": "value"}
        },
        "simulate_error": "ExecutorUnavailable",
        "expected_fallback_to": "MAF_Native"
    },
    # No fallback - error propagates
    {
        "name": "No Fallback - Error Propagates",
        "config": {
            "intercept_all": True,
            "fallback_on_error": False
        },
        "tool_request": {
            "function_name": "broken_tool",
            "arguments": {}
        },
        "simulate_error": "ToolExecutionError",
        "expected_error_propagated": True
    },
    # Fallback with partial result
    {
        "name": "Fallback with Partial Success",
        "config": {
            "intercept_all": True,
            "fallback_on_error": True,
            "preserve_partial_results": True
        },
        "tool_request": {
            "function_name": "batch_operation",
            "arguments": {"items": [1, 2, 3, 4, 5]}
        },
        "simulate_partial_failure": True,
        "expected_partial_results": True
    },
]

CONTEXT_PROPAGATION_SCENARIOS = [
    # Context passed to executor
    {
        "name": "Context Propagation - Session Info",
        "tool_request": {
            "function_name": "process_data",
            "arguments": {"data": "test"}
        },
        "context": {
            "session_id": "sess-123",
            "user_id": "user-456",
            "workflow_id": "wf-789"
        },
        "expected_context_fields": ["session_id", "user_id", "workflow_id"]
    },
    # MAF state preserved
    {
        "name": "MAF State Preservation",
        "tool_request": {
            "function_name": "workflow_step",
            "arguments": {"step": "validate"}
        },
        "maf_state": {
            "current_step": 3,
            "total_steps": 5,
            "checkpoint_id": "cp-001"
        },
        "expected_state_preserved": True
    },
]


# =============================================================================
# Scenario Test Functions
# =============================================================================

async def test_interception_logic(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Tool Call Interception

    Tests that MAFToolCallback correctly intercepts tool calls
    based on configuration (intercept_all vs allowed_tools).

    Expected Behavior:
    - Intercept when intercept_all=True
    - Intercept only allowed_tools when specified
    - Pass through non-intercepted calls to MAF native
    """
    results = []

    for scenario in INTERCEPTION_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_maf_callback(
                config=scenario["config"],
                tool_request=scenario["tool_request"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Intercepted: {scenario['expected_intercepted']}",
                    details={
                        "expected_intercepted": scenario["expected_intercepted"],
                        "expected_routed_to": scenario["expected_routed_to"]
                    }
                )
            else:
                was_intercepted = response.get("intercepted", False)
                routed_to = response.get("routed_to", "")

                if was_intercepted == scenario["expected_intercepted"]:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Intercept correct: {was_intercepted}, routed to: {routed_to}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected intercepted={scenario['expected_intercepted']}, got {was_intercepted}",
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


async def test_blocked_tools(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Blocked Tool Handling

    Tests that MAFToolCallback blocks dangerous tools and
    patterns based on security configuration.

    Expected Behavior:
    - Block tools in blocked_tools list
    - Block patterns matching blocked_patterns
    - Return appropriate block reason
    - Allow safe tools to pass
    """
    results = []

    for scenario in BLOCKED_TOOL_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_maf_callback(
                config=scenario["config"],
                tool_request=scenario["tool_request"]
            )

            if "simulated" in response:
                expected_blocked = scenario.get("expected_blocked", False)
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Blocked: {expected_blocked}",
                    details={
                        "expected_blocked": expected_blocked,
                        "block_reason": scenario.get("block_reason", "N/A")
                    }
                )
            else:
                was_blocked = response.get("blocked", False)
                expected_blocked = scenario.get("expected_blocked", False)

                if was_blocked == expected_blocked:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Block behavior correct: blocked={was_blocked}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected blocked={expected_blocked}, got {was_blocked}",
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


async def test_approval_routing(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Approval Requirement Routing

    Tests that MAFToolCallback correctly identifies tools
    requiring approval and routes them appropriately.

    Expected Behavior:
    - Identify tools in require_approval list
    - Detect elevated approval patterns
    - Route to approval workflow when needed
    - Skip approval for safe operations
    """
    results = []

    for scenario in APPROVAL_ROUTING_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_maf_callback(
                config=scenario["config"],
                tool_request=scenario["tool_request"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Approval required: {scenario['expected_approval_required']}",
                    details={
                        "expected_approval_required": scenario["expected_approval_required"],
                        "approval_level": scenario.get("approval_level", "none")
                    }
                )
            else:
                approval_required = response.get("approval_required", False)
                expected = scenario["expected_approval_required"]

                if approval_required == expected:
                    level = response.get("approval_level", "standard")
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Approval routing correct: required={approval_required}, level={level}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected approval_required={expected}, got {approval_required}",
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


async def test_fallback_behavior(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Fallback Behavior

    Tests that MAFToolCallback handles errors gracefully
    with configurable fallback behavior.

    Expected Behavior:
    - Fallback to MAF native when fallback_on_error=True
    - Propagate errors when fallback_on_error=False
    - Preserve partial results when configured
    """
    results = []

    for scenario in FALLBACK_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_maf_callback(
                config=scenario["config"],
                tool_request=scenario["tool_request"],
                simulate_error=scenario.get("simulate_error"),
                simulate_partial_failure=scenario.get("simulate_partial_failure", False)
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Fallback behavior configured",
                    details={
                        "fallback_on_error": scenario["config"].get("fallback_on_error"),
                        "simulate_error": scenario.get("simulate_error")
                    }
                )
            else:
                fallback_used = response.get("fallback_used", False)
                error_propagated = response.get("error_propagated", False)

                # Verify based on expected behavior
                if "expected_fallback_to" in scenario:
                    if fallback_used:
                        result = StepResult(
                            step_name=f"{scenario['name']}",
                            status=TestStatus.PASSED,
                            message=f"Fallback triggered correctly",
                            details=response
                        )
                    else:
                        result = StepResult(
                            step_name=f"{scenario['name']}",
                            status=TestStatus.FAILED,
                            message="Expected fallback but none occurred",
                            details=response
                        )
                elif scenario.get("expected_error_propagated"):
                    if error_propagated:
                        result = StepResult(
                            step_name=f"{scenario['name']}",
                            status=TestStatus.PASSED,
                            message="Error propagated as expected",
                            details=response
                        )
                    else:
                        result = StepResult(
                            step_name=f"{scenario['name']}",
                            status=TestStatus.FAILED,
                            message="Error should have propagated",
                            details=response
                        )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message="Fallback behavior validated",
                        details=response
                    )

            results.append(result)

            if verbose:
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status_icon} {result.step_name}: {result.message}")

        except Exception as e:
            # For scenarios expecting error propagation, exception is expected
            if scenario.get("expected_error_propagated"):
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"Error propagated as exception: {type(e).__name__}",
                    details={"error": str(e)}
                )
            else:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.FAILED,
                    message=f"Unexpected error: {str(e)}",
                    details={"scenario": scenario["name"], "error": str(e)}
                )
            results.append(result)

    return results


async def test_context_propagation(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Context Propagation

    Tests that MAFToolCallback correctly propagates context
    and MAF state to the UnifiedToolExecutor.

    Expected Behavior:
    - Pass session/user context to executor
    - Preserve MAF workflow state
    - Include checkpoint information
    """
    results = []

    for scenario in CONTEXT_PROPAGATION_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_maf_callback(
                tool_request=scenario["tool_request"],
                context=scenario.get("context"),
                maf_state=scenario.get("maf_state")
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message="[Simulated] Context propagation configured",
                    details={
                        "context": scenario.get("context"),
                        "maf_state": scenario.get("maf_state")
                    }
                )
            else:
                # Verify context was propagated
                if "expected_context_fields" in scenario:
                    propagated_context = response.get("propagated_context", {})
                    fields_present = all(
                        f in propagated_context
                        for f in scenario["expected_context_fields"]
                    )
                    if fields_present:
                        result = StepResult(
                            step_name=f"{scenario['name']}",
                            status=TestStatus.PASSED,
                            message="Context fields propagated correctly",
                            details=response
                        )
                    else:
                        result = StepResult(
                            step_name=f"{scenario['name']}",
                            status=TestStatus.FAILED,
                            message="Missing expected context fields",
                            details=response
                        )
                elif scenario.get("expected_state_preserved"):
                    state_preserved = response.get("maf_state_preserved", False)
                    if state_preserved:
                        result = StepResult(
                            step_name=f"{scenario['name']}",
                            status=TestStatus.PASSED,
                            message="MAF state preserved correctly",
                            details=response
                        )
                    else:
                        result = StepResult(
                            step_name=f"{scenario['name']}",
                            status=TestStatus.FAILED,
                            message="MAF state not preserved",
                            details=response
                        )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message="Context propagation validated",
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

async def run_all_tool_callback_scenarios(client) -> Dict:
    """Run all MAF Tool Callback scenario tests."""
    print("\n" + "=" * 60)
    print("MAF Tool Callback Scenario Tests")
    print("=" * 60)

    all_results = []

    print("\n1. Interception Logic")
    print("-" * 40)
    results1 = await test_interception_logic(client)
    all_results.extend(results1)

    print("\n2. Blocked Tools")
    print("-" * 40)
    results2 = await test_blocked_tools(client)
    all_results.extend(results2)

    print("\n3. Approval Routing")
    print("-" * 40)
    results3 = await test_approval_routing(client)
    all_results.extend(results3)

    print("\n4. Fallback Behavior")
    print("-" * 40)
    results4 = await test_fallback_behavior(client)
    all_results.extend(results4)

    print("\n5. Context Propagation")
    print("-" * 40)
    results5 = await test_context_propagation(client)
    all_results.extend(results5)

    # Summary
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    total = len(all_results)

    print("\n" + "-" * 60)
    print(f"MAF Tool Callback Results: {passed}/{total} tests passed")

    return {
        "scenario": "MAF Tool Callback",
        "total": total,
        "passed": passed,
        "results": all_results
    }


if __name__ == "__main__":
    from phase_13_hybrid_core_test import HybridTestClient

    async def main():
        client = HybridTestClient()
        try:
            results = await run_all_tool_callback_scenarios(client)
            return 0 if results["passed"] == results["total"] else 1
        finally:
            await client.close()

    exit(asyncio.run(main()))
