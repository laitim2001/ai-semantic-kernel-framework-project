"""
Phase 11: Agent-Session Integration Tests

This module contains UAT test scenarios for Agent-Session Integration,
including tool execution, approval workflows, streaming responses,
and WebSocket communication.

Test Scenarios:
- scenario_tool_execution: Tool call execution with approval workflow
- scenario_streaming: Server-Sent Events streaming responses
- scenario_approval_workflow: Complete approval lifecycle
- scenario_error_recovery: Error handling and recovery

Author: IPA Platform Team
Phase: 11 - Agent-Session Integration
Sprint: 45-47 (90 Story Points)
"""

from .phase_11_agent_session_test import AgentSessionTestClient, run_all_scenarios

__all__ = ["AgentSessionTestClient", "run_all_scenarios"]
