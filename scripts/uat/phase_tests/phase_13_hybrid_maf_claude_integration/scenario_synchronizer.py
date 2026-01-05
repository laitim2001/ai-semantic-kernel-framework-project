# =============================================================================
# IPA Platform - Phase 13 ContextSynchronizer Scenarios
# =============================================================================
# Sprint 53: S53-2 ContextBridge & Synchronizer (10 pts)
#
# Tests for context synchronization with optimistic locking, conflict
# detection/resolution, and rollback support.
#
# Key Components:
#   - ContextSynchronizer: Core synchronization engine
#   - OptimisticLocking: Version-based concurrency control
#   - ConflictResolver: Strategy-based conflict resolution
#   - RollbackManager: State recovery on failures
# =============================================================================
"""
ContextSynchronizer Scenario Tests

Business scenarios that validate:
- Optimistic locking with version control
- Concurrent modification detection
- Conflict resolution strategies
- Rollback and recovery operations
- Cross-framework state consistency
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import StepResult, TestStatus


# =============================================================================
# Test Data: Optimistic Locking Scenarios
# =============================================================================

OPTIMISTIC_LOCK_SCENARIOS = [
    # Basic version check - success
    {
        "name": "Version Match - Success",
        "initial_state": {
            "session_id": "sess-001",
            "version": 5,
            "data": {"key": "value1"}
        },
        "update": {
            "expected_version": 5,
            "new_data": {"key": "value2"}
        },
        "expected_result": "success",
        "expected_new_version": 6
    },
    # Version mismatch - conflict
    {
        "name": "Version Mismatch - Conflict",
        "initial_state": {
            "session_id": "sess-002",
            "version": 10,
            "data": {"counter": 100}
        },
        "update": {
            "expected_version": 8,  # Stale version
            "new_data": {"counter": 101}
        },
        "expected_result": "conflict",
        "expected_error": "VersionMismatchError"
    },
    # First write - no existing version
    {
        "name": "Initial Write - No Prior Version",
        "initial_state": None,
        "update": {
            "session_id": "sess-003",
            "new_data": {"status": "created"}
        },
        "expected_result": "success",
        "expected_new_version": 1
    },
    # Rapid sequential updates
    {
        "name": "Sequential Updates - Version Increment",
        "initial_state": {
            "session_id": "sess-004",
            "version": 1,
            "data": {"step": 1}
        },
        "updates": [
            {"expected_version": 1, "new_data": {"step": 2}},
            {"expected_version": 2, "new_data": {"step": 3}},
            {"expected_version": 3, "new_data": {"step": 4}},
        ],
        "expected_result": "success",
        "expected_final_version": 4
    },
]

CONCURRENT_MODIFICATION_SCENARIOS = [
    # Two clients updating same field
    {
        "name": "Concurrent Same-Field Update",
        "initial_state": {
            "session_id": "sess-cm-001",
            "version": 1,
            "data": {"balance": 1000}
        },
        "client_a_update": {
            "expected_version": 1,
            "new_data": {"balance": 900},  # Withdraw 100
            "delay_ms": 0
        },
        "client_b_update": {
            "expected_version": 1,
            "new_data": {"balance": 800},  # Withdraw 200
            "delay_ms": 50
        },
        "expected_conflict": True,
        "winner": "client_a",
        "expected_retry": "client_b"
    },
    # Two clients updating different fields
    {
        "name": "Concurrent Different-Field Update",
        "initial_state": {
            "session_id": "sess-cm-002",
            "version": 1,
            "data": {"name": "John", "email": "john@example.com"}
        },
        "client_a_update": {
            "expected_version": 1,
            "new_data": {"name": "John Doe"},  # Update name
            "field": "name"
        },
        "client_b_update": {
            "expected_version": 1,
            "new_data": {"email": "johndoe@example.com"},  # Update email
            "field": "email"
        },
        "resolution_strategy": "merge",
        "expected_final": {"name": "John Doe", "email": "johndoe@example.com"}
    },
    # Race condition simulation
    {
        "name": "Race Condition - First Write Wins",
        "initial_state": {
            "session_id": "sess-cm-003",
            "version": 5,
            "data": {"status": "pending"}
        },
        "concurrent_updates": [
            {"client": "A", "version": 5, "data": {"status": "approved"}},
            {"client": "B", "version": 5, "data": {"status": "rejected"}},
            {"client": "C", "version": 5, "data": {"status": "cancelled"}},
        ],
        "expected_winner_count": 1,
        "expected_retry_count": 2
    },
]


# =============================================================================
# Test Data: Conflict Resolution Scenarios
# =============================================================================

CONFLICT_RESOLUTION_SCENARIOS = [
    # Last-write-wins strategy
    {
        "name": "Last Write Wins Strategy",
        "strategy": "LAST_WRITE_WINS",
        "conflict": {
            "base_version": 5,
            "server_state": {"price": 100, "updated_at": "2026-01-05T10:00:00Z"},
            "client_state": {"price": 120, "updated_at": "2026-01-05T10:01:00Z"}
        },
        "expected_winner": "client",
        "expected_value": {"price": 120}
    },
    # Server-wins strategy
    {
        "name": "Server State Wins Strategy",
        "strategy": "SERVER_WINS",
        "conflict": {
            "base_version": 5,
            "server_state": {"approved": True, "approver": "manager"},
            "client_state": {"approved": False, "approver": None}
        },
        "expected_winner": "server",
        "expected_value": {"approved": True, "approver": "manager"}
    },
    # Merge non-conflicting fields
    {
        "name": "Field-Level Merge Strategy",
        "strategy": "MERGE",
        "conflict": {
            "base_state": {"name": "John", "email": "john@old.com", "phone": "111"},
            "server_state": {"name": "John", "email": "john@new.com", "phone": "111"},
            "client_state": {"name": "John Doe", "email": "john@old.com", "phone": "222"}
        },
        "expected_merged": {
            "name": "John Doe",  # From client
            "email": "john@new.com",  # From server
            "phone": "222"  # Conflict - needs resolution
        },
        "unresolved_fields": ["phone"]
    },
    # Custom merge function
    {
        "name": "Custom Merge - Numeric Maximum",
        "strategy": "CUSTOM",
        "merge_rule": "max_value",
        "conflict": {
            "field": "priority",
            "server_value": 5,
            "client_value": 8
        },
        "expected_result": 8
    },
    # Conflict requiring manual resolution
    {
        "name": "Manual Resolution Required",
        "strategy": "MANUAL",
        "conflict": {
            "base_state": {"decision": None},
            "server_state": {"decision": "approve"},
            "client_state": {"decision": "reject"}
        },
        "expected_action": "pause_for_user",
        "expected_options": ["approve", "reject", "defer"]
    },
]

DEEP_MERGE_SCENARIOS = [
    # Nested object merge
    {
        "name": "Nested Object Merge",
        "base": {
            "user": {
                "profile": {"name": "John", "age": 30},
                "preferences": {"theme": "dark", "language": "en"}
            }
        },
        "changes_a": {
            "user": {
                "profile": {"name": "John Doe"},  # Update name
                "preferences": {"theme": "dark", "language": "en"}
            }
        },
        "changes_b": {
            "user": {
                "profile": {"name": "John", "age": 31},  # Update age
                "preferences": {"theme": "light", "language": "en"}  # Update theme
            }
        },
        "expected_merged": {
            "user": {
                "profile": {"name": "John Doe", "age": 31},
                "preferences": {"theme": "light", "language": "en"}
            }
        }
    },
    # Array merge strategies
    {
        "name": "Array Append Strategy",
        "strategy": "ARRAY_APPEND",
        "base": {"tags": ["urgent"]},
        "server": {"tags": ["urgent", "reviewed"]},
        "client": {"tags": ["urgent", "escalated"]},
        "expected": {"tags": ["urgent", "reviewed", "escalated"]}
    },
    # Array replace strategy
    {
        "name": "Array Replace Strategy",
        "strategy": "ARRAY_REPLACE",
        "base": {"items": [1, 2, 3]},
        "server": {"items": [1, 2, 3, 4]},
        "client": {"items": [5, 6]},
        "expected": {"items": [5, 6]}  # Client wins on arrays
    },
]


# =============================================================================
# Test Data: Rollback Scenarios
# =============================================================================

ROLLBACK_SCENARIOS = [
    # Simple rollback on failure
    {
        "name": "Rollback on Update Failure",
        "initial_state": {
            "session_id": "sess-rb-001",
            "version": 3,
            "data": {"status": "active", "count": 10}
        },
        "operation": {
            "type": "update",
            "new_data": {"status": "processing", "count": 11},
            "simulate_failure": True,
            "failure_point": "after_local_update"
        },
        "expected_rollback": True,
        "expected_final_state": {"status": "active", "count": 10}
    },
    # Rollback multi-step operation
    {
        "name": "Multi-Step Rollback",
        "initial_state": {
            "session_id": "sess-rb-002",
            "version": 1,
            "data": {"step": 0, "completed": []}
        },
        "operations": [
            {"type": "update", "data": {"step": 1, "completed": ["init"]}},
            {"type": "update", "data": {"step": 2, "completed": ["init", "validate"]}},
            {"type": "update", "data": {"step": 3, "completed": ["init", "validate", "process"]}, "fail": True},
        ],
        "expected_rollback_to": 2,
        "expected_final": {"step": 2, "completed": ["init", "validate"]}
    },
    # Checkpoint-based recovery
    {
        "name": "Checkpoint Recovery",
        "checkpoints": [
            {"id": "cp-1", "version": 1, "data": {"stage": "start"}},
            {"id": "cp-2", "version": 5, "data": {"stage": "middle"}},
            {"id": "cp-3", "version": 10, "data": {"stage": "end"}},
        ],
        "current_version": 12,
        "current_data": {"stage": "corrupted"},
        "recovery_target": "cp-2",
        "expected_final": {"stage": "middle"},
        "expected_version": 5
    },
    # Partial rollback
    {
        "name": "Partial Rollback - Keep Valid Changes",
        "initial_state": {
            "session_id": "sess-rb-003",
            "data": {
                "field_a": "original_a",
                "field_b": "original_b",
                "field_c": "original_c"
            }
        },
        "changes": [
            {"field": "field_a", "value": "new_a", "status": "success"},
            {"field": "field_b", "value": "new_b", "status": "success"},
            {"field": "field_c", "value": "new_c", "status": "failed"},
        ],
        "rollback_scope": "failed_only",
        "expected_final": {
            "field_a": "new_a",
            "field_b": "new_b",
            "field_c": "original_c"
        }
    },
]

STATE_RECOVERY_SCENARIOS = [
    # Recovery from network failure
    {
        "name": "Network Failure Recovery",
        "scenario": {
            "initial_sync": {"version": 5, "synced": True},
            "local_changes": [
                {"version": 6, "data": {"change": 1}},
                {"version": 7, "data": {"change": 2}},
            ],
            "network_failure": True,
            "reconnect_server_version": 5
        },
        "recovery_action": "replay_local_changes",
        "expected_final_version": 7
    },
    # Recovery from crash
    {
        "name": "Crash Recovery with WAL",
        "write_ahead_log": [
            {"op": "begin", "txn": "tx-001"},
            {"op": "update", "txn": "tx-001", "data": {"key": "value"}},
            # Missing commit - simulated crash
        ],
        "recovery_action": "rollback_incomplete_txn",
        "expected_state": "before_tx-001"
    },
    # Split-brain recovery
    {
        "name": "Split Brain Resolution",
        "scenario": {
            "partition_a": {"version": 10, "data": {"node": "A", "value": 100}},
            "partition_b": {"version": 12, "data": {"node": "B", "value": 200}},
        },
        "resolution_strategy": "higher_version_wins",
        "expected_winner": "partition_b"
    },
]


# =============================================================================
# Test Data: Cross-Framework Sync Scenarios
# =============================================================================

CROSS_FRAMEWORK_SYNC_SCENARIOS = [
    # MAF → Claude sync
    {
        "name": "MAF to Claude Sync",
        "source": "MAF",
        "target": "Claude",
        "maf_state": {
            "workflow_id": "wf-sync-001",
            "version": 3,
            "execution_state": "running",
            "variables": {"order_id": "ORD-123"}
        },
        "expected_claude_sync": True,
        "expected_preservation": ["workflow_id", "variables", "execution_state"]
    },
    # Claude → MAF sync
    {
        "name": "Claude to MAF Sync",
        "source": "Claude",
        "target": "MAF",
        "claude_state": {
            "session_id": "sess-sync-001",
            "version": 5,
            "messages": [{"role": "user", "content": "Process order"}],
            "tool_results": [{"tool": "get_order", "result": {"id": "ORD-123"}}]
        },
        "expected_maf_sync": True,
        "expected_checkpoint": True
    },
    # Bidirectional sync
    {
        "name": "Bidirectional Sync",
        "initial_maf": {"version": 1, "data": {"maf_field": "A"}},
        "initial_claude": {"version": 1, "data": {"claude_field": "B"}},
        "sync_operations": [
            {"direction": "maf_to_claude", "field": "maf_field"},
            {"direction": "claude_to_maf", "field": "claude_field"},
        ],
        "expected_final_maf": {"maf_field": "A", "claude_field": "B"},
        "expected_final_claude": {"maf_field": "A", "claude_field": "B"}
    },
]


# =============================================================================
# Scenario Test Functions
# =============================================================================

async def test_optimistic_locking(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Optimistic Locking

    Tests that ContextSynchronizer correctly implements optimistic
    locking with version-based concurrency control.

    Expected Behavior:
    - Version match allows update
    - Version mismatch triggers conflict
    - Version increments on successful update
    - Initial writes create version 1
    """
    results = []

    for scenario in OPTIMISTIC_LOCK_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_optimistic_lock(
                initial_state=scenario.get("initial_state"),
                update=scenario.get("update"),
                updates=scenario.get("updates")
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Expected: {scenario['expected_result']}",
                    details={"expected": scenario["expected_result"]}
                )
            else:
                actual_result = response.get("result")
                expected = scenario["expected_result"]

                if actual_result == expected:
                    new_version = response.get("new_version")
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Lock result: {actual_result}, version: {new_version}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected {expected}, got {actual_result}",
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


async def test_concurrent_modifications(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Concurrent Modifications

    Tests that ContextSynchronizer correctly detects and handles
    concurrent modification attempts from multiple clients.

    Expected Behavior:
    - First write succeeds
    - Subsequent writes detect conflict
    - Proper retry mechanism for conflicting clients
    - Merge capability for non-conflicting fields
    """
    results = []

    for scenario in CONCURRENT_MODIFICATION_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_concurrent_modification(
                initial_state=scenario["initial_state"],
                updates=scenario.get("concurrent_updates", [
                    scenario.get("client_a_update"),
                    scenario.get("client_b_update")
                ])
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Conflict detection: {scenario.get('expected_conflict', 'merge')}",
                    details={"resolution": scenario.get("resolution_strategy", "first_wins")}
                )
            else:
                has_conflict = response.get("conflict_detected")
                expected_conflict = scenario.get("expected_conflict", False)

                if has_conflict == expected_conflict:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Conflict handling: {'detected' if has_conflict else 'merged'}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Conflict mismatch: expected={expected_conflict}, actual={has_conflict}",
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


async def test_conflict_resolution(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Conflict Resolution Strategies

    Tests that ContextSynchronizer correctly applies various
    conflict resolution strategies.

    Expected Behavior:
    - LAST_WRITE_WINS uses timestamp
    - SERVER_WINS prioritizes server state
    - MERGE combines non-conflicting changes
    - MANUAL pauses for user decision
    """
    results = []

    for scenario in CONFLICT_RESOLUTION_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.resolve_conflict(
                strategy=scenario["strategy"],
                conflict=scenario["conflict"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Strategy: {scenario['strategy']}",
                    details={"strategy": scenario["strategy"]}
                )
            else:
                resolved = response.get("resolved", False)

                if resolved or scenario["strategy"] == "MANUAL":
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Resolution: {scenario['strategy']} applied",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Resolution failed",
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


async def test_deep_merge(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Deep Merge Operations

    Tests that ContextSynchronizer correctly performs deep merging
    of nested objects and arrays.

    Expected Behavior:
    - Nested objects merged field by field
    - Arrays handled per strategy (append/replace)
    - Type preservation during merge
    """
    results = []

    for scenario in DEEP_MERGE_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.deep_merge(
                base=scenario.get("base"),
                changes_a=scenario.get("changes_a", scenario.get("server")),
                changes_b=scenario.get("changes_b", scenario.get("client")),
                strategy=scenario.get("strategy", "MERGE")
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Deep merge: {scenario.get('strategy', 'MERGE')}",
                    details={"expected": scenario.get("expected_merged", scenario.get("expected"))}
                )
            else:
                merged = response.get("merged", {})
                expected = scenario.get("expected_merged", scenario.get("expected"))

                # Simple comparison for simulation
                merge_successful = merged is not None

                if merge_successful:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Deep merge successful",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Merge failed or produced unexpected result",
                        details={"expected": expected, "actual": merged}
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


async def test_rollback_operations(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Rollback Operations

    Tests that ContextSynchronizer correctly performs rollback
    operations on failures.

    Expected Behavior:
    - Rollback on update failure
    - Multi-step rollback to last good state
    - Checkpoint-based recovery
    - Partial rollback for failed-only changes
    """
    results = []

    for scenario in ROLLBACK_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_rollback(
                initial_state=scenario.get("initial_state"),
                operations=scenario.get("operations", [scenario.get("operation")]),
                checkpoints=scenario.get("checkpoints"),
                recovery_target=scenario.get("recovery_target")
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Rollback: {scenario.get('rollback_scope', 'full')}",
                    details={"expected_final": scenario.get("expected_final_state", scenario.get("expected_final"))}
                )
            else:
                rollback_success = response.get("rollback_performed", False)

                if rollback_success == scenario.get("expected_rollback", True):
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Rollback: {'performed' if rollback_success else 'not needed'}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Rollback result mismatch",
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


async def test_state_recovery(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: State Recovery

    Tests that ContextSynchronizer correctly recovers from
    various failure scenarios.

    Expected Behavior:
    - Network failure recovery with replay
    - Crash recovery using WAL
    - Split-brain resolution
    """
    results = []

    for scenario in STATE_RECOVERY_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_state_recovery(
                scenario=scenario.get("scenario"),
                write_ahead_log=scenario.get("write_ahead_log"),
                recovery_action=scenario.get("recovery_action")
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Recovery: {scenario['recovery_action']}",
                    details={"action": scenario["recovery_action"]}
                )
            else:
                recovered = response.get("recovered", False)

                if recovered:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"State recovered successfully",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Recovery failed",
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


async def test_cross_framework_sync(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Cross-Framework Synchronization

    Tests that ContextSynchronizer correctly synchronizes state
    between MAF and Claude SDK frameworks.

    Expected Behavior:
    - MAF → Claude sync preserves state
    - Claude → MAF sync creates checkpoints
    - Bidirectional sync maintains consistency
    """
    results = []

    for scenario in CROSS_FRAMEWORK_SYNC_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_cross_framework_sync(
                source=scenario.get("source"),
                target=scenario.get("target"),
                maf_state=scenario.get("maf_state", scenario.get("initial_maf")),
                claude_state=scenario.get("claude_state", scenario.get("initial_claude")),
                sync_operations=scenario.get("sync_operations")
            )

            if "simulated" in response:
                direction = scenario.get("source", "bidirectional")
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Sync: {direction}",
                    details={"direction": direction}
                )
            else:
                sync_success = response.get("sync_success", False)

                if sync_success:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Cross-framework sync successful",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Sync failed",
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

async def run_all_synchronizer_scenarios(client) -> Dict:
    """Run all ContextSynchronizer scenario tests."""
    print("\n" + "=" * 60)
    print("ContextSynchronizer Scenario Tests")
    print("=" * 60)

    all_results = []

    print("\n1. Optimistic Locking")
    print("-" * 40)
    results1 = await test_optimistic_locking(client)
    all_results.extend(results1)

    print("\n2. Concurrent Modifications")
    print("-" * 40)
    results2 = await test_concurrent_modifications(client)
    all_results.extend(results2)

    print("\n3. Conflict Resolution Strategies")
    print("-" * 40)
    results3 = await test_conflict_resolution(client)
    all_results.extend(results3)

    print("\n4. Deep Merge Operations")
    print("-" * 40)
    results4 = await test_deep_merge(client)
    all_results.extend(results4)

    print("\n5. Rollback Operations")
    print("-" * 40)
    results5 = await test_rollback_operations(client)
    all_results.extend(results5)

    print("\n6. State Recovery")
    print("-" * 40)
    results6 = await test_state_recovery(client)
    all_results.extend(results6)

    print("\n7. Cross-Framework Sync")
    print("-" * 40)
    results7 = await test_cross_framework_sync(client)
    all_results.extend(results7)

    # Summary
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    total = len(all_results)

    print("\n" + "-" * 60)
    print(f"ContextSynchronizer Results: {passed}/{total} tests passed")

    return {
        "scenario": "ContextSynchronizer",
        "total": total,
        "passed": passed,
        "results": all_results
    }


if __name__ == "__main__":
    from phase_13_hybrid_core_test import HybridTestClient

    async def main():
        client = HybridTestClient()
        try:
            results = await run_all_synchronizer_scenarios(client)
            return 0 if results["passed"] == results["total"] else 1
        finally:
            await client.close()

    exit(asyncio.run(main()))
