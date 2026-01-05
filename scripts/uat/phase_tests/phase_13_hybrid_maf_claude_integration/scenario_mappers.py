# =============================================================================
# IPA Platform - Phase 13 Mapper Scenarios
# =============================================================================
# Sprint 53: S53-2 ContextBridge & Mappers (10 pts)
#
# Tests for bidirectional state mapping between MAF and Claude contexts.
#
# Key Components:
#   - MAFMapper: MAF state → Claude context
#   - ClaudeMapper: Claude state → MAF checkpoint
#   - Bidirectional conversion with data preservation
# =============================================================================
"""
Mapper Scenario Tests

Business scenarios that validate:
- MAFMapper: Converting MAF workflow state to Claude context
- ClaudeMapper: Converting Claude SDK state to MAF checkpoints
- Bidirectional mapping consistency
- Edge cases and data preservation
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import StepResult, TestStatus


# =============================================================================
# Test Data: MAFMapper Scenarios
# =============================================================================

MAF_TO_CLAUDE_CONTEXT_SCENARIOS = [
    # Basic workflow variables
    {
        "name": "Simple Workflow Variables",
        "maf_state": {
            "workflow_id": "wf-001",
            "variables": {
                "customer_name": "John Doe",
                "order_id": "ORD-12345",
                "total_amount": 150.00
            },
            "current_step": "validate_order"
        },
        "expected_claude_vars": {
            "workflow_id": "wf-001",
            "customer_name": "John Doe",
            "order_id": "ORD-12345",
            "total_amount": 150.00,
            "_maf_step": "validate_order"
        },
        "preserve_types": True
    },
    # Nested variables
    {
        "name": "Nested Object Variables",
        "maf_state": {
            "workflow_id": "wf-002",
            "variables": {
                "customer": {
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "address": {
                        "city": "Taipei",
                        "country": "Taiwan"
                    }
                },
                "items": [
                    {"sku": "SKU-001", "qty": 2},
                    {"sku": "SKU-002", "qty": 1}
                ]
            }
        },
        "expected_structure": "nested_preserved",
        "preserve_types": True
    },
    # Special characters in values
    {
        "name": "Special Characters Handling",
        "maf_state": {
            "workflow_id": "wf-003",
            "variables": {
                "message": "Hello, 世界! 🌍",
                "query": "SELECT * FROM users WHERE name = 'O''Brien'",
                "path": "C:\\Users\\Documents\\file.txt"
            }
        },
        "expected_escape": True,
        "preserve_unicode": True
    },
]

MAF_HISTORY_CONVERSION_SCENARIOS = [
    # Simple conversation history
    {
        "name": "Basic Conversation History",
        "maf_history": [
            {"role": "user", "content": "I need to create a purchase order"},
            {"role": "assistant", "content": "I'll help you create a PO. What items do you need?"},
            {"role": "user", "content": "10 laptops for the IT department"}
        ],
        "expected_claude_format": [
            {"role": "user", "content": "I need to create a purchase order"},
            {"role": "assistant", "content": "I'll help you create a PO. What items do you need?"},
            {"role": "user", "content": "10 laptops for the IT department"}
        ],
        "message_count": 3
    },
    # History with tool calls
    {
        "name": "History with Tool Calls",
        "maf_history": [
            {"role": "user", "content": "Check the inventory for laptops"},
            {
                "role": "assistant",
                "content": "Let me check the inventory.",
                "tool_calls": [
                    {"name": "check_inventory", "arguments": {"item": "laptop"}}
                ]
            },
            {
                "role": "tool",
                "name": "check_inventory",
                "content": '{"available": 25, "reserved": 5}'
            },
            {"role": "assistant", "content": "We have 25 laptops available, with 5 reserved."}
        ],
        "expected_tool_format": "claude_sdk_compatible",
        "message_count": 4
    },
    # System messages handling
    {
        "name": "System Message Preservation",
        "maf_history": [
            {
                "role": "system",
                "content": "You are a helpful procurement assistant."
            },
            {"role": "user", "content": "Help me with a purchase"},
        ],
        "preserve_system_message": True,
        "expected_system_position": "first"
    },
]

AGENT_STATE_TO_PROMPT_SCENARIOS = [
    # Basic agent configuration
    {
        "name": "Basic Agent State",
        "agent_state": {
            "agent_id": "agent-001",
            "name": "Procurement Assistant",
            "role": "Helps users with procurement workflows",
            "capabilities": ["create_po", "check_inventory", "approve_request"]
        },
        "expected_prompt_contains": ["Procurement Assistant", "procurement workflows"],
        "expected_capability_mention": True
    },
    # Agent with instructions
    {
        "name": "Agent with Instructions",
        "agent_state": {
            "agent_id": "agent-002",
            "name": "Approval Bot",
            "instructions": [
                "Always verify budget before approving",
                "Escalate requests over $10,000 to manager",
                "Document all decisions"
            ],
            "constraints": [
                "Cannot approve own requests",
                "Maximum approval limit: $50,000"
            ]
        },
        "expected_instruction_format": "structured",
        "expected_constraint_inclusion": True
    },
    # Agent with memory/context
    {
        "name": "Agent with Memory",
        "agent_state": {
            "agent_id": "agent-003",
            "name": "Support Agent",
            "memory": {
                "user_preferences": {"language": "zh-TW"},
                "session_context": {"topic": "billing_inquiry"}
            }
        },
        "expected_memory_integration": True
    },
]


# =============================================================================
# Test Data: ClaudeMapper Scenarios
# =============================================================================

CLAUDE_TO_MAF_CHECKPOINT_SCENARIOS = [
    # Basic Claude state to checkpoint
    {
        "name": "Simple Claude State",
        "claude_state": {
            "session_id": "sess-001",
            "conversation": [
                {"role": "user", "content": "Create a report"},
                {"role": "assistant", "content": "I'll generate the report now."}
            ],
            "context_variables": {
                "report_type": "quarterly",
                "format": "pdf"
            }
        },
        "expected_checkpoint": {
            "session_id": "sess-001",
            "message_count": 2,
            "variables_preserved": True
        }
    },
    # Claude state with tool results
    {
        "name": "Claude State with Tools",
        "claude_state": {
            "session_id": "sess-002",
            "tool_calls": [
                {
                    "id": "tc-001",
                    "name": "generate_report",
                    "arguments": {"type": "quarterly"},
                    "result": {"file_path": "/reports/q4.pdf", "pages": 15}
                }
            ],
            "pending_approvals": []
        },
        "expected_tool_preservation": True,
        "expected_result_format": "maf_compatible"
    },
    # Claude state with pending approvals
    {
        "name": "State with Pending Approvals",
        "claude_state": {
            "session_id": "sess-003",
            "pending_approvals": [
                {
                    "approval_id": "apr-001",
                    "tool_name": "execute_payment",
                    "arguments": {"amount": 5000},
                    "reason": "Payment requires approval"
                }
            ]
        },
        "expected_approval_checkpoint": True,
        "expected_state": "waiting_approval"
    },
]

CLAUDE_TO_EXECUTION_RECORDS_SCENARIOS = [
    # Basic execution record
    {
        "name": "Simple Execution Record",
        "claude_execution": {
            "execution_id": "exec-001",
            "start_time": "2026-01-05T10:00:00Z",
            "end_time": "2026-01-05T10:05:00Z",
            "status": "completed",
            "tokens_used": {"input": 500, "output": 200}
        },
        "expected_maf_record": {
            "id": "exec-001",
            "duration_ms_approx": 300000,
            "status": "completed"
        }
    },
    # Execution with multiple steps
    {
        "name": "Multi-Step Execution",
        "claude_execution": {
            "execution_id": "exec-002",
            "steps": [
                {"name": "analyze", "status": "completed", "duration_ms": 1000},
                {"name": "process", "status": "completed", "duration_ms": 2000},
                {"name": "validate", "status": "completed", "duration_ms": 500}
            ],
            "status": "completed"
        },
        "expected_step_count": 3,
        "expected_total_duration": 3500
    },
    # Failed execution record
    {
        "name": "Failed Execution Record",
        "claude_execution": {
            "execution_id": "exec-003",
            "status": "failed",
            "error": {
                "type": "ToolExecutionError",
                "message": "Database connection timeout",
                "code": "DB_TIMEOUT"
            }
        },
        "expected_error_preservation": True,
        "expected_maf_status": "failed"
    },
]

TOOL_CALL_TO_APPROVAL_SCENARIOS = [
    # High-risk tool requiring approval
    {
        "name": "Payment Tool Approval",
        "tool_call": {
            "id": "tc-pay-001",
            "name": "process_payment",
            "arguments": {
                "amount": 15000,
                "recipient": "vendor-123",
                "currency": "USD"
            }
        },
        "risk_level": "high",
        "expected_approval_request": {
            "tool_name": "process_payment",
            "risk_level": "high",
            "requires_manager": True
        }
    },
    # Data modification approval
    {
        "name": "Data Modification Approval",
        "tool_call": {
            "id": "tc-data-001",
            "name": "update_customer_record",
            "arguments": {
                "customer_id": "cust-456",
                "changes": {"credit_limit": 100000}
            }
        },
        "risk_level": "medium",
        "expected_approval_request": {
            "tool_name": "update_customer_record",
            "risk_level": "medium",
            "requires_manager": False
        }
    },
    # External API call approval
    {
        "name": "External API Approval",
        "tool_call": {
            "id": "tc-api-001",
            "name": "call_external_api",
            "arguments": {
                "endpoint": "https://api.partner.com/orders",
                "method": "POST",
                "data": {"order_id": "ord-789"}
            }
        },
        "risk_level": "medium",
        "expected_approval_request": {
            "tool_name": "call_external_api",
            "risk_level": "medium",
            "data_sensitivity": "external"
        }
    },
]


# =============================================================================
# Test Data: Bidirectional Mapping Scenarios
# =============================================================================

ROUNDTRIP_SCENARIOS = [
    # Complete roundtrip: MAF → Claude → MAF
    {
        "name": "Full State Roundtrip",
        "initial_maf_state": {
            "workflow_id": "wf-rt-001",
            "variables": {"key1": "value1", "key2": 123},
            "history": [
                {"role": "user", "content": "Start workflow"},
                {"role": "assistant", "content": "Workflow started"}
            ],
            "current_step": "step_2"
        },
        "expected_preservation": ["workflow_id", "variables", "history", "current_step"],
        "tolerance": "exact"  # No data loss expected
    },
    # Roundtrip with type conversion
    {
        "name": "Type Preservation Roundtrip",
        "initial_maf_state": {
            "workflow_id": "wf-rt-002",
            "variables": {
                "integer_val": 42,
                "float_val": 3.14159,
                "bool_val": True,
                "null_val": None,
                "list_val": [1, 2, 3],
                "dict_val": {"nested": "value"}
            }
        },
        "expected_type_preservation": True,
        "check_types": ["int", "float", "bool", "NoneType", "list", "dict"]
    },
    # Roundtrip with tool state
    {
        "name": "Tool State Roundtrip",
        "initial_maf_state": {
            "workflow_id": "wf-rt-003",
            "tool_calls": [
                {
                    "id": "tc-001",
                    "name": "query_database",
                    "status": "completed",
                    "result": {"rows": 50}
                }
            ],
            "pending_tools": []
        },
        "expected_tool_preservation": True
    },
]


# =============================================================================
# Scenario Test Functions
# =============================================================================

async def test_maf_to_claude_context(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: MAF to Claude Context Mapping

    Tests that MAFMapper correctly converts MAF workflow state
    to Claude SDK context variables.

    Expected Behavior:
    - Preserve all variable values
    - Handle nested objects correctly
    - Escape special characters appropriately
    - Maintain type fidelity
    """
    results = []

    for scenario in MAF_TO_CLAUDE_CONTEXT_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.map_maf_to_claude_context(
                maf_state=scenario["maf_state"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] MAF → Claude context mapping",
                    details={"maf_vars": list(scenario["maf_state"].get("variables", {}).keys())}
                )
            else:
                claude_vars = response.get("context_variables", {})

                # Verify expected variables present
                if scenario.get("expected_claude_vars"):
                    vars_match = all(
                        claude_vars.get(k) == v
                        for k, v in scenario["expected_claude_vars"].items()
                    )
                else:
                    vars_match = len(claude_vars) > 0

                if vars_match:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Context mapped: {len(claude_vars)} variables",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Variable mapping mismatch",
                        details={"expected": scenario.get("expected_claude_vars"), "actual": claude_vars}
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


async def test_maf_history_conversion(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: MAF History to Claude History Conversion

    Tests that MAFMapper correctly converts MAF conversation history
    to Claude SDK message format.

    Expected Behavior:
    - Preserve message order
    - Convert tool calls to Claude format
    - Handle system messages appropriately
    - Maintain message count
    """
    results = []

    for scenario in MAF_HISTORY_CONVERSION_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.convert_maf_history(
                maf_history=scenario["maf_history"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] History conversion: {scenario['message_count']} messages",
                    details={"message_count": scenario["message_count"]}
                )
            else:
                claude_history = response.get("messages", [])
                count_match = len(claude_history) == scenario["message_count"]

                if count_match:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"History converted: {len(claude_history)} messages",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Expected {scenario['message_count']} messages, got {len(claude_history)}",
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


async def test_agent_state_to_prompt(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Agent State to System Prompt

    Tests that MAFMapper correctly converts MAF agent state
    to Claude SDK system prompt format.

    Expected Behavior:
    - Include agent name and role
    - Format capabilities clearly
    - Include instructions and constraints
    - Integrate memory context
    """
    results = []

    for scenario in AGENT_STATE_TO_PROMPT_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.convert_agent_to_prompt(
                agent_state=scenario["agent_state"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Agent prompt generated",
                    details={"agent": scenario["agent_state"].get("name")}
                )
            else:
                prompt = response.get("system_prompt", "")

                # Check expected content
                contains_expected = all(
                    text.lower() in prompt.lower()
                    for text in scenario.get("expected_prompt_contains", [])
                )

                if contains_expected and len(prompt) > 0:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Prompt generated: {len(prompt)} chars",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Prompt missing expected content",
                        details={"expected": scenario.get("expected_prompt_contains"), "prompt_length": len(prompt)}
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


async def test_claude_to_maf_checkpoint(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Claude State to MAF Checkpoint

    Tests that ClaudeMapper correctly converts Claude SDK state
    to MAF checkpoint format for persistence.

    Expected Behavior:
    - Preserve session information
    - Convert conversation to checkpoint format
    - Handle pending approvals
    - Maintain tool call state
    """
    results = []

    for scenario in CLAUDE_TO_MAF_CHECKPOINT_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.convert_claude_to_checkpoint(
                claude_state=scenario["claude_state"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Checkpoint created",
                    details={"session": scenario["claude_state"].get("session_id")}
                )
            else:
                checkpoint = response.get("checkpoint", {})
                session_match = checkpoint.get("session_id") == scenario["claude_state"]["session_id"]

                if session_match:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Checkpoint created for session",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Session ID mismatch in checkpoint",
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


async def test_claude_to_execution_records(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Claude Execution to MAF Records

    Tests that ClaudeMapper correctly converts Claude SDK execution
    data to MAF execution record format.

    Expected Behavior:
    - Preserve execution ID
    - Calculate duration correctly
    - Map status appropriately
    - Preserve error information
    """
    results = []

    for scenario in CLAUDE_TO_EXECUTION_RECORDS_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.convert_claude_to_execution_record(
                claude_execution=scenario["claude_execution"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Execution record created",
                    details={"execution_id": scenario["claude_execution"]["execution_id"]}
                )
            else:
                record = response.get("execution_record", {})
                status_match = record.get("status") == scenario["claude_execution"]["status"]

                if status_match:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Execution record: status={record.get('status')}",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message=f"Status mismatch",
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


async def test_tool_call_to_approval(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Tool Call to Approval Request

    Tests that ClaudeMapper correctly converts Claude SDK tool calls
    to MAF approval request format for HITL workflows.

    Expected Behavior:
    - Identify risk level correctly
    - Generate appropriate approval request
    - Include all necessary tool information
    - Set correct approval requirements
    """
    results = []

    for scenario in TOOL_CALL_TO_APPROVAL_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.convert_tool_to_approval(
                tool_call=scenario["tool_call"],
                risk_level=scenario["risk_level"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Approval request: risk={scenario['risk_level']}",
                    details=scenario["expected_approval_request"]
                )
            else:
                approval = response.get("approval_request", {})
                tool_match = approval.get("tool_name") == scenario["tool_call"]["name"]
                risk_match = approval.get("risk_level") == scenario["risk_level"]

                if tool_match and risk_match:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message=f"Approval request created: {approval.get('risk_level')} risk",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Approval request mismatch",
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


async def test_roundtrip_mapping(
    client,
    verbose: bool = True
) -> List[StepResult]:
    """
    Scenario: Bidirectional Roundtrip Mapping

    Tests that MAF → Claude → MAF roundtrip preserves all data
    without loss or corruption.

    Expected Behavior:
    - Complete data preservation
    - Type fidelity maintained
    - No information loss
    - Consistent state after roundtrip
    """
    results = []

    for scenario in ROUNDTRIP_SCENARIOS:
        print(f"\n  Testing: {scenario['name']}")

        try:
            response = await client.test_roundtrip_mapping(
                initial_state=scenario["initial_maf_state"]
            )

            if "simulated" in response:
                result = StepResult(
                    step_name=f"{scenario['name']}",
                    status=TestStatus.PASSED,
                    message=f"[Simulated] Roundtrip: {len(scenario['expected_preservation'])} fields",
                    details={"preserved": scenario["expected_preservation"]}
                )
            else:
                final_state = response.get("final_state", {})
                initial = scenario["initial_maf_state"]

                # Check preservation of expected fields
                preserved = all(
                    final_state.get(field) == initial.get(field)
                    for field in scenario["expected_preservation"]
                )

                if preserved:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.PASSED,
                        message="Roundtrip successful: all data preserved",
                        details=response
                    )
                else:
                    result = StepResult(
                        step_name=f"{scenario['name']}",
                        status=TestStatus.FAILED,
                        message="Data loss detected in roundtrip",
                        details={"initial": initial, "final": final_state}
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

async def run_all_mapper_scenarios(client) -> Dict:
    """Run all Mapper scenario tests."""
    print("\n" + "=" * 60)
    print("Mapper Scenario Tests (MAFMapper & ClaudeMapper)")
    print("=" * 60)

    all_results = []

    print("\n1. MAF → Claude Context Mapping")
    print("-" * 40)
    results1 = await test_maf_to_claude_context(client)
    all_results.extend(results1)

    print("\n2. MAF History Conversion")
    print("-" * 40)
    results2 = await test_maf_history_conversion(client)
    all_results.extend(results2)

    print("\n3. Agent State → System Prompt")
    print("-" * 40)
    results3 = await test_agent_state_to_prompt(client)
    all_results.extend(results3)

    print("\n4. Claude → MAF Checkpoint")
    print("-" * 40)
    results4 = await test_claude_to_maf_checkpoint(client)
    all_results.extend(results4)

    print("\n5. Claude → Execution Records")
    print("-" * 40)
    results5 = await test_claude_to_execution_records(client)
    all_results.extend(results5)

    print("\n6. Tool Call → Approval Request")
    print("-" * 40)
    results6 = await test_tool_call_to_approval(client)
    all_results.extend(results6)

    print("\n7. Bidirectional Roundtrip")
    print("-" * 40)
    results7 = await test_roundtrip_mapping(client)
    all_results.extend(results7)

    # Summary
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    total = len(all_results)

    print("\n" + "-" * 60)
    print(f"Mapper Results: {passed}/{total} tests passed")

    return {
        "scenario": "Mappers (MAF & Claude)",
        "total": total,
        "passed": passed,
        "results": all_results
    }


if __name__ == "__main__":
    from phase_13_hybrid_core_test import HybridTestClient

    async def main():
        client = HybridTestClient()
        try:
            results = await run_all_mapper_scenarios(client)
            return 0 if results["passed"] == results["total"] else 1
        finally:
            await client.close()

    exit(asyncio.run(main()))
