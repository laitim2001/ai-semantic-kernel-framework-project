"""
Phase 12: Claude Agent SDK Integration Tests

Test scenarios for Claude Agent SDK integration:
- Sprint 48: Core SDK Integration (35 pts)
- Sprint 49: Tools & Hooks System (32 pts)
- Sprint 50: MCP & Hybrid Orchestration (38 pts)

Author: IPA Platform Team
Phase: 12 - Claude Agent SDK Integration
"""

# Main test client and runners
from .phase_12_claude_sdk_test import (
    ClaudeSDKTestClient,
    run_core_sdk_scenario,
    run_tools_hooks_scenario,
    run_mcp_hybrid_scenario,
    main,
)

# Sprint 48: Core SDK Integration scenarios
from .scenario_core_sdk import (
    run_sprint48_scenarios,
    test_sdk_initialization,
    test_basic_query,
    test_streaming_query,
    test_session_create,
    test_session_query,
    test_session_fork,
    test_multi_turn_conversation,
    test_context_window_management,
)

# Sprint 49: Tools & Hooks System scenarios
from .scenario_tools_hooks import (
    run_sprint49_scenarios,
    test_file_read_tool,
    test_file_write_tool,
    test_file_edit_tool,
    test_glob_tool,
    test_grep_tool,
    test_bash_tool,
    test_task_tool,
    test_approval_hook,
    test_audit_hook,
    test_rate_limit_hook,
    test_sandbox_hook,
    test_hook_priority,
    test_web_search_tool,
    test_web_fetch_tool,
)

# Sprint 50: MCP & Hybrid Orchestration scenarios
from .scenario_mcp_hybrid import (
    run_sprint50_scenarios,
    test_list_mcp_servers,
    test_connect_mcp_server,
    test_disconnect_mcp_server,
    test_mcp_health_check,
    test_list_mcp_tools,
    test_execute_mcp_tool,
    test_mcp_tool_error_handling,
    test_hybrid_execute_claude_preferred,
    test_hybrid_execute_agent_framework_preferred,
    test_hybrid_execute_auto_select,
    test_hybrid_analyze,
    test_hybrid_session_management,
    test_context_sync,
    test_context_snapshot,
    test_context_restore,
    test_capability_matcher,
)

__all__ = [
    # Main client and runners
    "ClaudeSDKTestClient",
    "run_core_sdk_scenario",
    "run_tools_hooks_scenario",
    "run_mcp_hybrid_scenario",
    "main",
    # Sprint 48 scenarios
    "run_sprint48_scenarios",
    "test_sdk_initialization",
    "test_basic_query",
    "test_streaming_query",
    "test_session_create",
    "test_session_query",
    "test_session_fork",
    "test_multi_turn_conversation",
    "test_context_window_management",
    # Sprint 49 scenarios
    "run_sprint49_scenarios",
    "test_file_read_tool",
    "test_file_write_tool",
    "test_file_edit_tool",
    "test_glob_tool",
    "test_grep_tool",
    "test_bash_tool",
    "test_task_tool",
    "test_approval_hook",
    "test_audit_hook",
    "test_rate_limit_hook",
    "test_sandbox_hook",
    "test_hook_priority",
    "test_web_search_tool",
    "test_web_fetch_tool",
    # Sprint 50 scenarios
    "run_sprint50_scenarios",
    "test_list_mcp_servers",
    "test_connect_mcp_server",
    "test_disconnect_mcp_server",
    "test_mcp_health_check",
    "test_list_mcp_tools",
    "test_execute_mcp_tool",
    "test_mcp_tool_error_handling",
    "test_hybrid_execute_claude_preferred",
    "test_hybrid_execute_agent_framework_preferred",
    "test_hybrid_execute_auto_select",
    "test_hybrid_analyze",
    "test_hybrid_session_management",
    "test_context_sync",
    "test_context_snapshot",
    "test_context_restore",
    "test_capability_matcher",
]
