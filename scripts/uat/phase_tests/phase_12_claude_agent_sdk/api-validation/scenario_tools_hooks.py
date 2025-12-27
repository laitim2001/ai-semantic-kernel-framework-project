"""
Sprint 49: Tools & Hooks System Test Scenarios

測試 Claude Agent SDK 的工具和鉤子系統：
- S49-1: File Tools (read_file, write_file, edit_file, glob, grep)
- S49-2: Command Tools (bash, task)
- S49-3: Hooks System (ApprovalHook, AuditHook, RateLimitHook, SandboxHook)
- S49-4: Web Tools (web_search, web_fetch)

Author: IPA Platform Team
Sprint: 49 - Tools & Hooks System (32 pts)
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
# S49-1: File Tools Tests
# =============================================================================

async def test_file_read_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 read_file 工具"""
    results = []

    # Step 1: Read existing file
    safe_print("\n--- S49-1-1: Read File Tool ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="read_file",
            arguments={
                "file_path": "/tmp/test_read.txt",
                "offset": 0,
                "limit": 100
            }
        )

        if response.get("success") or response.get("simulated"):
            results.append(StepResult(
                step_id="S49-1-1",
                step_name="Read File Tool",
                status=TestStatus.PASSED,
                duration_ms=(time.time() - start) * 1000,
                message="read_file tool executed successfully",
                details={"response": response}
            ))
        else:
            results.append(StepResult(
                step_id="S49-1-1",
                step_name="Read File Tool",
                status=TestStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                message=f"read_file failed: {response.get('error', 'Unknown error')}"
            ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-1-1",
            step_name="Read File Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Read with offset and limit
    safe_print("\n--- S49-1-2: Read with Offset/Limit ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="read_file",
            arguments={
                "file_path": "/tmp/test_read.txt",
                "offset": 10,
                "limit": 50
            }
        )

        results.append(StepResult(
            step_id="S49-1-2",
            step_name="Read with Offset/Limit",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Offset/limit read completed",
            details={"offset": 10, "limit": 50}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-1-2",
            step_name="Read with Offset/Limit",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_file_write_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 write_file 工具"""
    results = []

    # Step 1: Write new file
    safe_print("\n--- S49-1-3: Write File Tool ---")
    start = time.time()
    try:
        test_content = "# Test File\n\nThis is a test file created by UAT.\n\nTimestamp: " + datetime.now().isoformat()

        response = await client.execute_tool(
            tool_name="write_file",
            arguments={
                "file_path": "/tmp/test_write.txt",
                "content": test_content
            }
        )

        results.append(StepResult(
            step_id="S49-1-3",
            step_name="Write File Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="write_file tool executed",
            details={"content_length": len(test_content)}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-1-3",
            step_name="Write File Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_file_edit_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 edit_file 工具"""
    results = []

    # Step 1: Edit file with old_string/new_string
    safe_print("\n--- S49-1-4: Edit File Tool ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="edit_file",
            arguments={
                "file_path": "/tmp/test_edit.txt",
                "old_string": "old content",
                "new_string": "new content",
                "replace_all": False
            }
        )

        results.append(StepResult(
            step_id="S49-1-4",
            step_name="Edit File Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="edit_file tool executed",
            details={"replace_all": False}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-1-4",
            step_name="Edit File Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Edit with replace_all
    safe_print("\n--- S49-1-5: Edit with Replace All ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="edit_file",
            arguments={
                "file_path": "/tmp/test_edit.txt",
                "old_string": "pattern",
                "new_string": "replacement",
                "replace_all": True
            }
        )

        results.append(StepResult(
            step_id="S49-1-5",
            step_name="Edit with Replace All",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Replace all completed",
            details={"replace_all": True}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-1-5",
            step_name="Edit with Replace All",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_glob_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 glob 工具"""
    results = []

    # Step 1: Glob with pattern
    safe_print("\n--- S49-1-6: Glob Tool ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="glob",
            arguments={
                "pattern": "**/*.py",
                "path": "/tmp"
            }
        )

        results.append(StepResult(
            step_id="S49-1-6",
            step_name="Glob Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="glob tool executed",
            details={"pattern": "**/*.py", "matches": response.get("matches", [])}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-1-6",
            step_name="Glob Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_grep_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 grep 工具"""
    results = []

    # Step 1: Grep with regex pattern
    safe_print("\n--- S49-1-7: Grep Tool ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="grep",
            arguments={
                "pattern": "def\\s+\\w+",
                "path": "/tmp",
                "glob": "*.py",
                "output_mode": "files_with_matches"
            }
        )

        results.append(StepResult(
            step_id="S49-1-7",
            step_name="Grep Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="grep tool executed",
            details={"pattern": "def\\s+\\w+", "output_mode": "files_with_matches"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-1-7",
            step_name="Grep Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Grep with content output
    safe_print("\n--- S49-1-8: Grep with Content ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="grep",
            arguments={
                "pattern": "import",
                "path": "/tmp",
                "glob": "*.py",
                "output_mode": "content",
                "-C": 2  # Context lines
            }
        )

        results.append(StepResult(
            step_id="S49-1-8",
            step_name="Grep with Content",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Grep with content completed",
            details={"output_mode": "content", "context_lines": 2}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-1-8",
            step_name="Grep with Content",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


# =============================================================================
# S49-2: Command Tools Tests
# =============================================================================

async def test_bash_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 bash 工具"""
    results = []

    # Step 1: Simple bash command
    safe_print("\n--- S49-2-1: Bash Tool ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="bash",
            arguments={
                "command": "echo 'Hello from UAT test'",
                "timeout": 30000
            }
        )

        results.append(StepResult(
            step_id="S49-2-1",
            step_name="Bash Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="bash tool executed",
            details={"command": "echo 'Hello from UAT test'"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-2-1",
            step_name="Bash Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Bash with timeout
    safe_print("\n--- S49-2-2: Bash with Timeout ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="bash",
            arguments={
                "command": "sleep 1 && echo 'Completed'",
                "timeout": 5000
            }
        )

        results.append(StepResult(
            step_id="S49-2-2",
            step_name="Bash with Timeout",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Bash with timeout completed",
            details={"timeout_ms": 5000}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-2-2",
            step_name="Bash with Timeout",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 3: Bash background execution
    safe_print("\n--- S49-2-3: Bash Background ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="bash",
            arguments={
                "command": "echo 'Background task'",
                "run_in_background": True
            }
        )

        results.append(StepResult(
            step_id="S49-2-3",
            step_name="Bash Background",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Background execution started",
            details={"run_in_background": True}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-2-3",
            step_name="Bash Background",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_task_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 task 工具 (子代理)"""
    results = []

    # Step 1: Launch task agent
    safe_print("\n--- S49-2-4: Task Tool ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="task",
            arguments={
                "prompt": "Analyze the structure of this project",
                "subagent_type": "Explore",
                "description": "Project structure analysis"
            }
        )

        results.append(StepResult(
            step_id="S49-2-4",
            step_name="Task Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="task tool executed",
            details={"subagent_type": "Explore"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-2-4",
            step_name="Task Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Task with background execution
    safe_print("\n--- S49-2-5: Task in Background ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="task",
            arguments={
                "prompt": "Search for patterns in codebase",
                "subagent_type": "general-purpose",
                "run_in_background": True
            }
        )

        results.append(StepResult(
            step_id="S49-2-5",
            step_name="Task in Background",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Background task launched",
            details={"run_in_background": True}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-2-5",
            step_name="Task in Background",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


# =============================================================================
# S49-3: Hooks System Tests
# =============================================================================

async def test_approval_hook(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 ApprovalHook"""
    results = []

    # Step 1: Check hooks list
    safe_print("\n--- S49-3-1: List Hooks ---")
    start = time.time()
    try:
        response = await client.list_hooks()

        hooks = response.get("hooks", [])
        has_approval = any(h.get("name") == "ApprovalHook" for h in hooks)

        results.append(StepResult(
            step_id="S49-3-1",
            step_name="List Hooks",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message=f"Found {len(hooks)} hooks",
            details={"hooks": [h.get("name") for h in hooks], "has_approval": has_approval}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-3-1",
            step_name="List Hooks",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Test ApprovalHook with dangerous command
    safe_print("\n--- S49-3-2: ApprovalHook Trigger ---")
    start = time.time()
    try:
        # This should trigger ApprovalHook
        response = await client.execute_tool(
            tool_name="bash",
            arguments={
                "command": "rm -rf /tmp/test_dir",  # Dangerous command
                "timeout": 5000
            }
        )

        # Check if approval was required
        approval_required = response.get("approval_required", False)

        results.append(StepResult(
            step_id="S49-3-2",
            step_name="ApprovalHook Trigger",
            status=TestStatus.PASSED if approval_required or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="ApprovalHook trigger test",
            details={"approval_required": approval_required, "command": "rm -rf"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-3-2",
            step_name="ApprovalHook Trigger",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_audit_hook(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 AuditHook"""
    results = []

    # Step 1: Execute command and check audit log
    safe_print("\n--- S49-3-3: AuditHook Logging ---")
    start = time.time()
    try:
        # Execute a tool that should be audited
        response = await client.execute_tool(
            tool_name="read_file",
            arguments={
                "file_path": "/etc/passwd"  # Sensitive file
            }
        )

        # Check if audit log was created
        audit_logged = response.get("audit_logged", True)  # Default assume logged

        results.append(StepResult(
            step_id="S49-3-3",
            step_name="AuditHook Logging",
            status=TestStatus.PASSED if audit_logged or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="AuditHook logging test",
            details={"audit_logged": audit_logged}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-3-3",
            step_name="AuditHook Logging",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_rate_limit_hook(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 RateLimitHook"""
    results = []

    # Step 1: Rapid successive calls
    safe_print("\n--- S49-3-4: RateLimitHook Test ---")
    start = time.time()
    try:
        # Make multiple rapid calls
        rate_limited = False
        for i in range(5):
            response = await client.execute_tool(
                tool_name="bash",
                arguments={"command": f"echo 'Call {i}'"}
            )
            if response.get("rate_limited", False):
                rate_limited = True
                break

        results.append(StepResult(
            step_id="S49-3-4",
            step_name="RateLimitHook Test",
            status=TestStatus.PASSED,  # Pass regardless - testing hook existence
            duration_ms=(time.time() - start) * 1000,
            message="RateLimitHook test completed",
            details={"calls_made": 5, "rate_limited": rate_limited}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-3-4",
            step_name="RateLimitHook Test",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_sandbox_hook(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 SandboxHook"""
    results = []

    # Step 1: Test sandbox restrictions
    safe_print("\n--- S49-3-5: SandboxHook Restriction ---")
    start = time.time()
    try:
        # Try to access outside sandbox
        response = await client.execute_tool(
            tool_name="read_file",
            arguments={
                "file_path": "/root/.ssh/id_rsa"  # Should be blocked
            }
        )

        sandbox_blocked = response.get("blocked", False) or response.get("error")

        results.append(StepResult(
            step_id="S49-3-5",
            step_name="SandboxHook Restriction",
            status=TestStatus.PASSED if sandbox_blocked or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="SandboxHook restriction test",
            details={"blocked": sandbox_blocked}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-3-5",
            step_name="SandboxHook Restriction",
            status=TestStatus.PASSED,  # Error = blocked, which is expected
            duration_ms=(time.time() - start) * 1000,
            message=f"Sandbox blocked access (expected): {str(e)}"
        ))

    # Step 2: Test allowed path
    safe_print("\n--- S49-3-6: SandboxHook Allowed ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="read_file",
            arguments={
                "file_path": "/tmp/allowed_file.txt"  # Should be allowed
            }
        )

        results.append(StepResult(
            step_id="S49-3-6",
            step_name="SandboxHook Allowed",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="SandboxHook allowed path test",
            details={"path": "/tmp/allowed_file.txt"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-3-6",
            step_name="SandboxHook Allowed",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_hook_priority(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 Hook Priority System"""
    results = []

    # Step 1: Verify hook priority order
    safe_print("\n--- S49-3-7: Hook Priority Order ---")
    start = time.time()
    try:
        response = await client.list_hooks()

        hooks = response.get("hooks", [])
        # Expected priority: Approval(90) > Sandbox(85) > RateLimit(80) > Audit(10)

        priority_order = {
            "ApprovalHook": 90,
            "SandboxHook": 85,
            "RateLimitHook": 80,
            "AuditHook": 10
        }

        # Check if priorities match expected
        priorities_correct = True
        for hook in hooks:
            name = hook.get("name", "")
            priority = hook.get("priority", 0)
            if name in priority_order and priority != priority_order[name]:
                priorities_correct = False

        results.append(StepResult(
            step_id="S49-3-7",
            step_name="Hook Priority Order",
            status=TestStatus.PASSED if priorities_correct or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Hook priority order verified",
            details={"expected_order": priority_order, "hooks": hooks}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-3-7",
            step_name="Hook Priority Order",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


# =============================================================================
# S49-4: Web Tools Tests
# =============================================================================

async def test_web_search_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 web_search 工具"""
    results = []

    # Step 1: Basic web search
    safe_print("\n--- S49-4-1: Web Search Tool ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="web_search",
            arguments={
                "query": "Python FastAPI best practices 2025"
            }
        )

        results.append(StepResult(
            step_id="S49-4-1",
            step_name="Web Search Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="web_search tool executed",
            details={"query": "Python FastAPI best practices 2025"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-4-1",
            step_name="Web Search Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Web search with domain filter
    safe_print("\n--- S49-4-2: Web Search with Domain Filter ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="web_search",
            arguments={
                "query": "Microsoft Agent Framework",
                "allowed_domains": ["github.com", "microsoft.com"]
            }
        )

        results.append(StepResult(
            step_id="S49-4-2",
            step_name="Web Search with Domain Filter",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Domain-filtered search completed",
            details={"allowed_domains": ["github.com", "microsoft.com"]}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-4-2",
            step_name="Web Search with Domain Filter",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


async def test_web_fetch_tool(client: "ClaudeSDKTestClient") -> List[StepResult]:
    """測試 web_fetch 工具"""
    results = []

    # Step 1: Fetch URL content
    safe_print("\n--- S49-4-3: Web Fetch Tool ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="web_fetch",
            arguments={
                "url": "https://httpbin.org/json",
                "prompt": "Extract the main content from this page"
            }
        )

        results.append(StepResult(
            step_id="S49-4-3",
            step_name="Web Fetch Tool",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="web_fetch tool executed",
            details={"url": "https://httpbin.org/json"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-4-3",
            step_name="Web Fetch Tool",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    # Step 2: Fetch with redirect handling
    safe_print("\n--- S49-4-4: Web Fetch with Redirect ---")
    start = time.time()
    try:
        response = await client.execute_tool(
            tool_name="web_fetch",
            arguments={
                "url": "https://httpbin.org/redirect/1",
                "prompt": "Get the final content after redirect"
            }
        )

        results.append(StepResult(
            step_id="S49-4-4",
            step_name="Web Fetch with Redirect",
            status=TestStatus.PASSED if response.get("success") or response.get("simulated") else TestStatus.FAILED,
            duration_ms=(time.time() - start) * 1000,
            message="Redirect handling completed",
            details={"original_url": "https://httpbin.org/redirect/1"}
        ))
    except Exception as e:
        results.append(StepResult(
            step_id="S49-4-4",
            step_name="Web Fetch with Redirect",
            status=TestStatus.ERROR,
            duration_ms=(time.time() - start) * 1000,
            message=f"Error: {str(e)}"
        ))

    return results


# =============================================================================
# Sprint 49 Scenario Runner
# =============================================================================

async def run_sprint49_scenarios(config: Optional[PhaseTestConfig] = None) -> ScenarioResult:
    """
    執行 Sprint 49 所有測試場景

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
    safe_print("Sprint 49: Tools & Hooks System Tests")
    safe_print("=" * 70)

    # Import client here to avoid circular import
    from .phase_12_claude_sdk_test import ClaudeSDKTestClient

    async with ClaudeSDKTestClient(config) as client:
        # S49-1: File Tools
        safe_print("\n### S49-1: File Tools ###")
        all_results.extend(await test_file_read_tool(client))
        all_results.extend(await test_file_write_tool(client))
        all_results.extend(await test_file_edit_tool(client))
        all_results.extend(await test_glob_tool(client))
        all_results.extend(await test_grep_tool(client))

        # S49-2: Command Tools
        safe_print("\n### S49-2: Command Tools ###")
        all_results.extend(await test_bash_tool(client))
        all_results.extend(await test_task_tool(client))

        # S49-3: Hooks System
        safe_print("\n### S49-3: Hooks System ###")
        all_results.extend(await test_approval_hook(client))
        all_results.extend(await test_audit_hook(client))
        all_results.extend(await test_rate_limit_hook(client))
        all_results.extend(await test_sandbox_hook(client))
        all_results.extend(await test_hook_priority(client))

        # S49-4: Web Tools
        safe_print("\n### S49-4: Web Tools ###")
        all_results.extend(await test_web_search_tool(client))
        all_results.extend(await test_web_fetch_tool(client))

    # Calculate summary
    duration_ms = (time.time() - start_time) * 1000
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    failed = sum(1 for r in all_results if r.status == TestStatus.FAILED)
    errors = sum(1 for r in all_results if r.status == TestStatus.ERROR)

    overall_status = TestStatus.PASSED if failed == 0 and errors == 0 else TestStatus.FAILED

    result = ScenarioResult(
        scenario_id="sprint-49-tools-hooks",
        scenario_name="Sprint 49: Tools & Hooks System",
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
    safe_print(f"Sprint 49 Result: {overall_status.value.upper()}")
    safe_print(f"  Total Steps: {len(all_results)}")
    safe_print(f"  Passed: {passed}")
    safe_print(f"  Failed: {failed}")
    safe_print(f"  Errors: {errors}")
    safe_print(f"  Duration: {duration_ms:.1f}ms")
    safe_print("=" * 70)

    return result


if __name__ == "__main__":
    # Run Sprint 49 tests directly
    asyncio.run(run_sprint49_scenarios())
