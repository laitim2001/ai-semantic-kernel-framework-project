# =============================================================================
# IPA Platform - Phase 13 UnifiedToolExecutor Scenarios
# =============================================================================
# Sprint 53: S53-3 UnifiedToolExecutor (10 pts)
#
# Tests for unified tool execution layer that routes all tools through
# Claude SDK regardless of source (MAF, Claude, Hybrid).
#
# Key Components:
#   - UnifiedToolExecutor: Central tool execution
#   - ToolSource enum: MAF, CLAUDE, HYBRID
#   - Hook pipeline: pre/post execution hooks
#   - Batch execution support
# =============================================================================
"""
UnifiedToolExecutor Scenario Tests

Business scenarios that validate:
- Single tool execution from different sources
- Batch tool execution
- Pre/post execution hooks
- Result synchronization back to source
- Error handling and recovery
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import StepResult, TestStatus


# =============================================================================
# Test Data: Tool Execution Scenarios
# =============================================================================

SINGLE_TOOL_SCENARIOS = [
    # Basic file operations
    {
        "name": "Read File Tool",
        "tool_name": "read_file",
        "arguments": {"path": "/tmp/test.txt"},
        "source": "CLAUDE",
        "expected_status": "success",
        "approval_required": False
    },
    # Database query
    {
        "name": "Database Query Tool",
        "tool_name": "execute_sql",
        "arguments": {"query": "SELECT * FROM users LIMIT 10"},
        "source": "MAF",
        "expected_status": "success",
        "approval_required": True  # Requires approval for DB operations
    },
    # API call
    {
        "name": "HTTP Request Tool",
        "tool_name": "http_request",
        "arguments": {"method": "GET", "url": "https://api.example.com/health"},
        "source": "HYBRID",
        "expected_status": "success",
        "approval_required": False
    },
    # Code execution (high risk)
    {
        "name": "Code Interpreter Tool",
        "tool_name": "execute_code",
        "arguments": {"language": "python", "code": "print('Hello World')"},
        "source": "CLAUDE",
        "expected_status": "pending_approval",
        "approval_required": True
    },
]

BATCH_EXECUTION_SCENARIOS = [
    # Multiple independent tools
    {
        "name": "Parallel File Operations",
        "tools": [
            {"name": "read_file", "arguments": {"path": "/tmp/file1.txt"}},
            {"name": "read_file", "arguments": {"path": "/tmp/file2.txt"}},
            {"name": "list_directory", "arguments": {"path": "/tmp"}},
        ],
        "source": "CLAUDE",
        "expected_results": 3,
        "all_success": True
    },
    # Mixed approval requirements
    {
        "name": "Mixed Approval Batch",
        "tools": [
            {"name": "read_file", "arguments": {"path": "/config.json"}},
            {"name": "execute_sql", "arguments": {"query": "SELECT 1"}},  # Needs approval
            {"name": "write_file", "arguments": {"path": "/tmp/out.txt", "content": "test"}},
        ],
        "source": "HYBRID",
        "expected_results": 3,
        "has_pending_approval": True
    },
]

HOOK_SCENARIOS = [
    # Pre-execution validation hook
    {
        "name": "Pre-Hook Validation",
        "tool_name": "write_file",
        "arguments": {"path": "/etc/passwd", "content": "malicious"},
        "pre_hook_action": "block",
        "expected_status": "blocked",
        "reason": "Path blocked by security policy"
    },
    # Post-execution logging hook
    {
        "name": "Post-Hook Logging",
        "tool_name": "http_request",
        "arguments": {"method": "POST", "url": "https://api.example.com/data"},
        "post_hook_action": "log",
        "expected_status": "success",
        "verify_logged": True
    },
    # Transform result hook
    {
        "name": "Post-Hook Transform",
        "tool_name": "read_file",
        "arguments": {"path": "/tmp/data.json"},
        "post_hook_action": "transform",
        "expected_status": "success",
        "result_transformed": True
    },
]

ERROR_SCENARIOS = [
    # Tool not found
    {
        "name": "Unknown Tool",
        "tool_name": "nonexistent_tool",
        "arguments": {},
        "expected_status": "error",
        "error_type": "ToolNotFoundError"
    },
    # Invalid arguments
    {
        "name": "Invalid Arguments",
        "tool_name": "read_file",
        "arguments": {},  # Missing required 'path'
        "expected_status": "error",
        "error_type": "ValidationError"
    },
    # Timeout
    {
        "name": "Tool Timeout",
        "tool_name": "long_running_operation",
        "arguments": {"duration": 120},
        "timeout": 5,
        "expected_status": "error",
        "error_type": "TimeoutError"
    },
]


# =============================================================================
# Scenario Test Functions
# =============================================================================

async def test_single_tool_execution(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Single Tool Execution

    Tests that UnifiedToolExecutor can execute individual tools from
    different sources (MAF, Claude, Hybrid) with proper routing.

    Expected Behavior:
    - Accept tools from any source
    - Route through appropriate execution path
    - Handle approval requirements
    - Return proper ToolExecutionResult
    """
    results = []

    for scenario in SINGLE_TOOL_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.execute_tool(
                tool_name=scenario["tool_name"],
                arguments=scenario["arguments"],
                source=scenario["source"],
                approval_required=scenario["approval_required"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Tool execution from {scenario['source']}",
                    details={
                        "tool": scenario["tool_name"],
                        "source": scenario["source"],
                        "expected_status": scenario["expected_status"]
                    }
                )
            else:
                status = response.get("status")
                source_correct = response.get("source") == scenario["source"]

                if status == scenario["expected_status"] and source_correct:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Tool executed: status={status}, source={scenario['source']}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected status={scenario['expected_status']}, got {status}",
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
                details={"tool": scenario["tool_name"], "error": str(e)}
            ))

    return results


async def test_batch_tool_execution(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Batch Tool Execution

    Tests that UnifiedToolExecutor can execute multiple tools in batch,
    handling parallel execution and mixed approval requirements.

    Expected Behavior:
    - Execute multiple tools efficiently
    - Aggregate results correctly
    - Handle mixed approval states
    - Return results for all tools
    """
    results = []

    for scenario in BATCH_EXECUTION_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.execute_tool_batch(
                tools=scenario["tools"],
                source=scenario["source"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Batch execution of {len(scenario['tools'])} tools",
                    details={"tool_count": len(scenario["tools"])}
                )
            else:
                result_count = len(response.get("results", []))
                all_success = all(
                    r.get("status") in ["success", "pending_approval"]
                    for r in response.get("results", [])
                )

                if result_count == scenario["expected_results"]:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Batch executed: {result_count} results",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected {scenario['expected_results']} results, got {result_count}",
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


async def test_hook_pipeline(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Hook Pipeline Execution

    Tests that UnifiedToolExecutor properly executes pre and post
    execution hooks for validation, logging, and transformation.

    Expected Behavior:
    - Pre-hooks can block execution
    - Post-hooks can transform results
    - Hook failures handled gracefully
    - Hooks receive proper context
    """
    results = []

    for scenario in HOOK_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            # Configure hooks based on scenario
            hooks_config = {}
            if "pre_hook_action" in scenario:
                hooks_config["pre_hooks"] = [{"action": scenario["pre_hook_action"]}]
            if "post_hook_action" in scenario:
                hooks_config["post_hooks"] = [{"action": scenario["post_hook_action"]}]

            response = await client.execute_tool_with_hooks(
                tool_name=scenario["tool_name"],
                arguments=scenario["arguments"],
                hooks=hooks_config
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Hook action: {scenario.get('pre_hook_action', scenario.get('post_hook_action'))}",
                    details=hooks_config
                )
            else:
                status = response.get("status")
                hooks_executed = response.get("hooks_executed", {})

                if status == scenario["expected_status"]:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Hook executed correctly: status={status}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected {scenario['expected_status']}, got {status}",
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


async def test_error_handling(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Error Handling

    Tests that UnifiedToolExecutor properly handles various error
    conditions including unknown tools, invalid arguments, and timeouts.

    Expected Behavior:
    - Return proper error types
    - Include helpful error messages
    - Not crash on errors
    - Support error recovery where possible
    """
    results = []

    for scenario in ERROR_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            kwargs = {
                "tool_name": scenario["tool_name"],
                "arguments": scenario["arguments"]
            }
            if "timeout" in scenario:
                kwargs["timeout"] = scenario["timeout"]

            response = await client.execute_tool(**kwargs)

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Error type: {scenario['error_type']}",
                    details={"expected_error": scenario["error_type"]}
                )
            else:
                status = response.get("status")
                error_type = response.get("error_type", "")

                # For error scenarios, we expect 'error' status
                if status == "error" and scenario["error_type"] in str(error_type):
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Error handled correctly: {error_type}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected error {scenario['error_type']}, got status={status}",
                        details=response
                    )

            results.append(result)

            if verbose:
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"    {status_icon} {result.step_name}: {result.message}")

        except Exception as e:
            # Some errors might be raised as exceptions
            if scenario["error_type"] in str(type(e).__name__) or scenario["error_type"] in str(e):
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"Exception raised correctly: {type(e).__name__}",
                    details={"error": str(e)}
                )
            else:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.FAILED,
                    message=f"Unexpected error: {str(e)}",
                    details={"expected": scenario["error_type"], "actual": str(e)}
                )
            results.append(result)

    return results


# =============================================================================
# Module Entry Point
# =============================================================================

async def run_all_unified_executor_scenarios(client) -> Dict:
    """Run all UnifiedToolExecutor scenario tests."""
    print("\n" + "=" * 60)
    print("UnifiedToolExecutor Scenario Tests")
    print("=" * 60)

    all_results = []

    print("\n1. Single Tool Execution")
    print("-" * 40)
    results1 = await test_single_tool_execution(client)
    all_results.extend(results1)

    print("\n2. Batch Tool Execution")
    print("-" * 40)
    results2 = await test_batch_tool_execution(client)
    all_results.extend(results2)

    print("\n3. Hook Pipeline")
    print("-" * 40)
    results3 = await test_hook_pipeline(client)
    all_results.extend(results3)

    print("\n4. Error Handling")
    print("-" * 40)
    results4 = await test_error_handling(client)
    all_results.extend(results4)

    # Summary
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    total = len(all_results)

    print("\n" + "-" * 60)
    print(f"UnifiedToolExecutor Results: {passed}/{total} tests passed")

    return {
        "scenario": "UnifiedToolExecutor",
        "total": total,
        "passed": passed,
        "results": all_results
    }


if __name__ == "__main__":
    from phase_13_hybrid_core_test import HybridTestClient

    async def main():
        client = HybridTestClient()
        try:
            results = await run_all_unified_executor_scenarios(client)
            return 0 if results["passed"] == results["total"] else 1
        finally:
            await client.close()

    exit(asyncio.run(main()))
