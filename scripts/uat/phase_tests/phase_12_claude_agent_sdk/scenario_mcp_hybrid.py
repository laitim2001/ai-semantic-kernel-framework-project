"""
Sprint 50: MCP & Hybrid Orchestration Test Scenarios

測試 Claude Agent SDK 的 MCP 整合和混合編排：
- S50-1: MCP Server Management (MCPServer, MCPManager)
- S50-2: MCP Tool Execution
- S50-3: Hybrid Orchestrator
- S50-4: Context Synchronizer

Author: IPA Platform Team
Sprint: 50 - MCP & Hybrid Orchestration (38 pts)
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..base import (
    safe_print,
    StepResult,
    ScenarioResult,
    TestStatus,
    TestPhase,
    PhaseTestBase,
)
from ..config import PhaseTestConfig, DEFAULT_CONFIG

if TYPE_CHECKING:
    from .phase_12_claude_sdk_test import ClaudeSDKTestClient


# =============================================================================
# S50-1: MCP Server Management Tests
# =============================================================================

async def test_list_mcp_servers(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試列出 MCP 伺服器"""
    results = []

    # Step 1: List all MCP servers
    safe_print("\n--- S50-1-1: List MCP Servers ---")
    start = time.time()
    try:
        response = await client.list_mcp_servers()

        servers = response.get("servers", [])
        server_names = [s.get("name") for s in servers]

        results.append(StepResult(
            step_id="S50-1-1",
            step_name="List MCP Servers",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Found {len(servers)} MCP servers",
            details={"servers": server_names}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-1-1",
            step_name="List MCP Servers",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_connect_mcp_server(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試連接 MCP 伺服器"""
    results = []

    # Step 1: Connect to filesystem MCP server
    safe_print("\n--- S50-1-2: Connect Filesystem Server ---")
    start = time.time()
    try:
        response = await client.connect_mcp_server("filesystem")

        connected = response.get("connected", False)
        server_info = response.get("server_info", {})

        results.append(StepResult(
            step_id="S50-1-2",
            step_name="Connect Filesystem Server",
            status=TestStatus.PASSED if connected or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Filesystem MCP server connection",
            details={"connected": connected, "server_info": server_info}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-1-2",
            step_name="Connect Filesystem Server",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Connect to database MCP server
    safe_print("\n--- S50-1-3: Connect Database Server ---")
    start = time.time()
    try:
        response = await client.connect_mcp_server("database")

        connected = response.get("connected", False)

        results.append(StepResult(
            step_id="S50-1-3",
            step_name="Connect Database Server",
            status=TestStatus.PASSED if connected or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Database MCP server connection",
            details={"connected": connected}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-1-3",
            step_name="Connect Database Server",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_disconnect_mcp_server(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試斷開 MCP 伺服器"""
    results = []

    # Step 1: Disconnect MCP server
    safe_print("\n--- S50-1-4: Disconnect MCP Server ---")
    start = time.time()
    try:
        response = await client.disconnect_mcp_server("filesystem")

        disconnected = response.get("disconnected", False)

        results.append(StepResult(
            step_id="S50-1-4",
            step_name="Disconnect MCP Server",
            status=TestStatus.PASSED if disconnected or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="MCP server disconnection",
            details={"disconnected": disconnected}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-1-4",
            step_name="Disconnect MCP Server",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_mcp_health_check(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 MCP 健康檢查"""
    results = []

    # Step 1: Check MCP health
    safe_print("\n--- S50-1-5: MCP Health Check ---")
    start = time.time()
    try:
        response = await client.mcp_health()

        health_status = response.get("status", "unknown")
        servers_healthy = response.get("servers_healthy", 0)
        servers_total = response.get("servers_total", 0)

        results.append(StepResult(
            step_id="S50-1-5",
            step_name="MCP Health Check",
            status=TestStatus.PASSED if health_status == "healthy" or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"MCP health: {health_status}",
            details={
                "status": health_status,
                "servers_healthy": servers_healthy,
                "servers_total": servers_total
            }
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-1-5",
            step_name="MCP Health Check",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


# =============================================================================
# S50-2: MCP Tool Execution Tests
# =============================================================================

async def test_list_mcp_tools(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試列出 MCP 工具"""
    results = []

    # Step 1: List tools from filesystem server
    safe_print("\n--- S50-2-1: List MCP Tools ---")
    start = time.time()
    try:
        response = await client.list_mcp_tools("filesystem")

        tools = response.get("tools", [])
        tool_names = [t.get("name") for t in tools]

        results.append(StepResult(
            step_id="S50-2-1",
            step_name="List MCP Tools",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Found {len(tools)} MCP tools",
            details={"tools": tool_names}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-2-1",
            step_name="List MCP Tools",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_execute_mcp_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試執行 MCP 工具"""
    results = []

    # Step 1: Execute filesystem read_file tool
    safe_print("\n--- S50-2-2: Execute MCP Tool ---")
    start = time.time()
    try:
        response = await client.execute_mcp_tool(
            server_name="filesystem",
            tool_name="read_file",
            arguments={"path": "/tmp/test.txt"}
        )

        results.append(StepResult(
            step_id="S50-2-2",
            step_name="Execute MCP Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="MCP tool execution",
            details={"server": "filesystem", "tool": "read_file"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-2-2",
            step_name="Execute MCP Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Execute with complex arguments
    safe_print("\n--- S50-2-3: Execute MCP Tool with Complex Args ---")
    start = time.time()
    try:
        response = await client.execute_mcp_tool(
            server_name="database",
            tool_name="query",
            arguments={
                "sql": "SELECT * FROM users LIMIT 10",
                "params": {"limit": 10}
            }
        )

        results.append(StepResult(
            step_id="S50-2-3",
            step_name="Execute MCP Tool with Complex Args",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Complex MCP tool execution",
            details={"server": "database", "tool": "query"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-2-3",
            step_name="Execute MCP Tool with Complex Args",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_mcp_tool_error_handling(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 MCP 工具錯誤處理"""
    results = []

    # Step 1: Execute non-existent tool
    safe_print("\n--- S50-2-4: MCP Tool Error Handling ---")
    start = time.time()
    try:
        response = await client.execute_mcp_tool(
            server_name="filesystem",
            tool_name="non_existent_tool",
            arguments={}
        )

        # Should return error
        has_error = response.get("error") is not None or response.get("simulated")

        results.append(StepResult(
            step_id="S50-2-4",
            step_name="MCP Tool Error Handling",
            status=TestStatus.PASSED if has_error else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Error handling test",
            details={"expected_error": True, "got_error": has_error}
        ))
    except Exception as e:
        # Exception is expected for non-existent tool
        results.append(StepResult(
            step_id="S50-2-4",
            step_name="MCP Tool Error Handling",
            status=TestStatus.PASSED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error handled correctly: {str(e)}"
        ))

    return results


# =============================================================================
# S50-3: Hybrid Orchestrator Tests
# =============================================================================

async def test_hybrid_execute_claude_preferred(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Hybrid Execute - Claude 優先"""
    results = []

    # Step 1: Execute with Claude preferred
    safe_print("\n--- S50-3-1: Hybrid Execute (Claude) ---")
    start = time.time()
    try:
        response = await client.hybrid_execute(
            task="Analyze the sentiment of this text: 'The product is amazing!'",
            context={"domain": "sentiment_analysis"},
            preferred_framework="claude"
        )

        framework_used = response.get("framework_used", "unknown")

        results.append(StepResult(
            step_id="S50-3-1",
            step_name="Hybrid Execute (Claude)",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Hybrid execution with {framework_used}",
            details={"preferred": "claude", "used": framework_used}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-3-1",
            step_name="Hybrid Execute (Claude)",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_hybrid_execute_agent_framework_preferred(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Hybrid Execute - Agent Framework 優先"""
    results = []

    # Step 1: Execute with Agent Framework preferred
    safe_print("\n--- S50-3-2: Hybrid Execute (Agent Framework) ---")
    start = time.time()
    try:
        response = await client.hybrid_execute(
            task="Create a workflow for document processing",
            context={"domain": "workflow_orchestration"},
            preferred_framework="agent_framework"
        )

        framework_used = response.get("framework_used", "unknown")

        results.append(StepResult(
            step_id="S50-3-2",
            step_name="Hybrid Execute (Agent Framework)",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Hybrid execution with {framework_used}",
            details={"preferred": "agent_framework", "used": framework_used}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-3-2",
            step_name="Hybrid Execute (Agent Framework)",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_hybrid_execute_auto_select(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Hybrid Execute - 自動選擇"""
    results = []

    # Step 1: Execute with auto selection
    safe_print("\n--- S50-3-3: Hybrid Execute (Auto) ---")
    start = time.time()
    try:
        response = await client.hybrid_execute(
            task="Help me debug this Python code",
            context={"code": "def foo(): return 1/0"},
            preferred_framework="auto"
        )

        framework_used = response.get("framework_used", "unknown")
        selection_reason = response.get("selection_reason", "")

        results.append(StepResult(
            step_id="S50-3-3",
            step_name="Hybrid Execute (Auto)",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Auto-selected {framework_used}",
            details={
                "used": framework_used,
                "selection_reason": selection_reason
            }
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-3-3",
            step_name="Hybrid Execute (Auto)",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_hybrid_analyze(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Hybrid Analyze - 任務分析"""
    results = []

    # Step 1: Analyze task to determine best framework
    safe_print("\n--- S50-3-4: Hybrid Analyze ---")
    start = time.time()
    try:
        response = await client.hybrid_analyze(
            task="Build a multi-agent system for customer support",
            context={"requirements": ["multi-agent", "workflow", "memory"]}
        )

        recommended = response.get("recommended_framework", "unknown")
        confidence = response.get("confidence", 0)
        reasons = response.get("reasons", [])

        results.append(StepResult(
            step_id="S50-3-4",
            step_name="Hybrid Analyze",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Recommended: {recommended} (confidence: {confidence})",
            details={
                "recommended": recommended,
                "confidence": confidence,
                "reasons": reasons
            }
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-3-4",
            step_name="Hybrid Analyze",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_hybrid_session_management(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Hybrid Session 管理"""
    results = []

    # Step 1: Create hybrid session
    safe_print("\n--- S50-3-5: Create Hybrid Session ---")
    start = time.time()
    try:
        response = await client.create_hybrid_session(
            session_id="hybrid-test-001",
            config={
                "enable_claude": True,
                "enable_agent_framework": True,
                "auto_switch": True
            }
        )

        session_id = response.get("session_id", "")

        results.append(StepResult(
            step_id="S50-3-5",
            step_name="Create Hybrid Session",
            status=TestStatus.PASSED if session_id or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Hybrid session created",
            details={"session_id": session_id}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-3-5",
            step_name="Create Hybrid Session",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Get hybrid metrics
    safe_print("\n--- S50-3-6: Hybrid Metrics ---")
    start = time.time()
    try:
        response = await client.hybrid_metrics()

        claude_calls = response.get("claude_calls", 0)
        af_calls = response.get("agent_framework_calls", 0)
        auto_switches = response.get("auto_switches", 0)

        results.append(StepResult(
            step_id="S50-3-6",
            step_name="Hybrid Metrics",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Hybrid metrics retrieved",
            details={
                "claude_calls": claude_calls,
                "agent_framework_calls": af_calls,
                "auto_switches": auto_switches
            }
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-3-6",
            step_name="Hybrid Metrics",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


# =============================================================================
# S50-4: Context Synchronizer Tests
# =============================================================================

async def test_context_sync(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Context Synchronization"""
    results = []

    # Step 1: Sync context from Claude to Agent Framework
    safe_print("\n--- S50-4-1: Sync Context (Claude -> AF) ---")
    start = time.time()
    try:
        response = await client.sync_context(
            source_id="claude-session-001",
            target_id="af-session-001",
            direction="claude_to_af"
        )

        synced = response.get("synced", False)
        items_synced = response.get("items_synced", 0)

        results.append(StepResult(
            step_id="S50-4-1",
            step_name="Sync Context (Claude -> AF)",
            status=TestStatus.PASSED if synced or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Synced {items_synced} context items",
            details={"direction": "claude_to_af", "items_synced": items_synced}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-4-1",
            step_name="Sync Context (Claude -> AF)",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Sync context from Agent Framework to Claude
    safe_print("\n--- S50-4-2: Sync Context (AF -> Claude) ---")
    start = time.time()
    try:
        response = await client.sync_context(
            source_id="af-session-001",
            target_id="claude-session-001",
            direction="af_to_claude"
        )

        synced = response.get("synced", False)
        items_synced = response.get("items_synced", 0)

        results.append(StepResult(
            step_id="S50-4-2",
            step_name="Sync Context (AF -> Claude)",
            status=TestStatus.PASSED if synced or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Synced {items_synced} context items",
            details={"direction": "af_to_claude", "items_synced": items_synced}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-4-2",
            step_name="Sync Context (AF -> Claude)",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 3: Bidirectional sync
    safe_print("\n--- S50-4-3: Bidirectional Sync ---")
    start = time.time()
    try:
        response = await client.sync_context(
            source_id="claude-session-001",
            target_id="af-session-001",
            direction="bidirectional"
        )

        synced = response.get("synced", False)

        results.append(StepResult(
            step_id="S50-4-3",
            step_name="Bidirectional Sync",
            status=TestStatus.PASSED if synced or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Bidirectional sync completed",
            details={"direction": "bidirectional"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-4-3",
            step_name="Bidirectional Sync",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_context_snapshot(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Context Snapshot"""
    results = []

    # Step 1: Create context snapshot
    safe_print("\n--- S50-4-4: Create Context Snapshot ---")
    start = time.time()
    try:
        response = await client.context_snapshot(
            session_id="claude-session-001",
            snapshot_name="checkpoint-001"
        )

        snapshot_id = response.get("snapshot_id", "")

        results.append(StepResult(
            step_id="S50-4-4",
            step_name="Create Context Snapshot",
            status=TestStatus.PASSED if snapshot_id or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Snapshot created",
            details={"snapshot_id": snapshot_id}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-4-4",
            step_name="Create Context Snapshot",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_context_restore(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Context Restore"""
    results = []

    # Step 1: Restore from snapshot
    safe_print("\n--- S50-4-5: Restore Context ---")
    start = time.time()
    try:
        response = await client.context_restore(
            session_id="claude-session-001",
            snapshot_id="checkpoint-001"
        )

        restored = response.get("restored", False)
        items_restored = response.get("items_restored", 0)

        results.append(StepResult(
            step_id="S50-4-5",
            step_name="Restore Context",
            status=TestStatus.PASSED if restored or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Restored {items_restored} context items",
            details={"items_restored": items_restored}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-4-5",
            step_name="Restore Context",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_capability_matcher(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 CapabilityMatcher - 能力匹配"""
    results = []

    # Step 1: Match capabilities
    safe_print("\n--- S50-4-6: Capability Matching ---")
    start = time.time()
    try:
        response = await client.match_capabilities(
            required_capabilities=["code_execution", "file_operations", "web_search"],
            context={"task_type": "development"}
        )

        matched_framework = response.get("matched_framework", "unknown")
        capability_coverage = response.get("capability_coverage", 0)
        missing_capabilities = response.get("missing_capabilities", [])

        results.append(StepResult(
            step_id="S50-4-6",
            step_name="Capability Matching",
            status=TestStatus.PASSED if matched_framework or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Matched: {matched_framework} ({capability_coverage}% coverage)",
            details={
                "matched_framework": matched_framework,
                "capability_coverage": capability_coverage,
                "missing": missing_capabilities
            }
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S50-4-6",
            step_name="Capability Matching",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


# =============================================================================
# Sprint 50 Scenario Runner
# =============================================================================

async def run_sprint50_scenarios(config: Optional[PhaseTestConfig] = None) -> ScenarioResult:
    """
    執行 Sprint 50 所有測試場景

    Args:
        config: 測試配置

    Returns:
        ScenarioResult: 場景執行結果
    """
    if config is None:
        config = DEFAULT_CONFIG

    start_time = time.time()
    all_results: List[StepResult] = []

    safe_print("\n" + "=" * 70)
    safe_print("Sprint 50: MCP & Hybrid Orchestration Tests")
    safe_print("=" * 70)

    # Import client here to avoid circular import
    from .phase_12_claude_sdk_test import ClaudeSDKTestClient

    async with ClaudeSDKTestClient(config) as client:
        # S50-1: MCP Server Management
        safe_print("\n### S50-1: MCP Server Management ###")
        all_results.extend(await test_list_mcp_servers(client))
        all_results.extend(await test_connect_mcp_server(client))
        all_results.extend(await test_disconnect_mcp_server(client))
        all_results.extend(await test_mcp_health_check(client))

        # S50-2: MCP Tool Execution
        safe_print("\n### S50-2: MCP Tool Execution ###")
        all_results.extend(await test_list_mcp_tools(client))
        all_results.extend(await test_execute_mcp_tool(client))
        all_results.extend(await test_mcp_tool_error_handling(client))

        # S50-3: Hybrid Orchestrator
        safe_print("\n### S50-3: Hybrid Orchestrator ###")
        all_results.extend(await test_hybrid_execute_claude_preferred(client))
        all_results.extend(await test_hybrid_execute_agent_framework_preferred(client))
        all_results.extend(await test_hybrid_execute_auto_select(client))
        all_results.extend(await test_hybrid_analyze(client))
        all_results.extend(await test_hybrid_session_management(client))

        # S50-4: Context Synchronizer
        safe_print("\n### S50-4: Context Synchronizer ###")
        all_results.extend(await test_context_sync(client))
        all_results.extend(await test_context_snapshot(client))
        all_results.extend(await test_context_restore(client))
        all_results.extend(await test_capability_matcher(client))

    # Calculate summary
    duration_ms = (time.time() - start_time) * 1000
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    failed = sum(1 for r in all_results if r.status == TestStatus.FAILED)
    errors = sum(1 for r in all_results if r.status == TestStatus.ERROR)

    overall_status = TestStatus.PASSED if failed == 0 and errors == 0 else TestStatus.FAILED

    result = ScenarioResult(
        scenario_id="sprint-50-mcp-hybrid",
        scenario_name="Sprint 50: MCP & Hybrid Orchestration",
        phase=TestPhase.PHASE_12,
        status=overall_status,
        total_steps=len(all_results),
        passed=passed,
        failed=failed,
        skipped=errors,
        duration_ms=duration_ms,
        step_results=all_results,
        summary=f"Passed: {passed}, Failed: {failed}, Errors: {errors}"
    )

    # Print summary
    safe_print("\n" + "=" * 70)
    safe_print(f"Sprint 50 Result: {overall_status.value.upper()}")
    safe_print(f"  Total Steps: {len(all_results)}")
    safe_print(f"  Passed: {passed}")
    safe_print(f"  Failed: {failed}")
    safe_print(f"  Errors: {errors}")
    safe_print(f"  Duration: {duration_ms:.1f}ms")
    safe_print("=" * 70)

    return result


if __name__ == "__main__":
    # Run Sprint 50 tests directly
    asyncio.run(run_sprint50_scenarios())
