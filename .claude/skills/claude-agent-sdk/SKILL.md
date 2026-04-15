---
name: claude-agent-sdk
description: |
  Development guide for Claude Agent SDK integration in IPA Platform.

  Use when:
  - Building autonomous AI agents with Claude
  - Implementing agents that need to make independent decisions
  - Creating agents with tool usage, MCP integration, or subagent delegation
  - Integrating Claude SDK with existing Microsoft Agent Framework
  - Working with code in backend/src/integrations/claude_sdk/

  Provides: query(), ClaudeAgentOptions, hooks (HookMatcher), MCP, subagents (AgentDefinition).

  Updated: 2026-04-11 (claude-agent-sdk v0.1.54)
---

# Claude Agent SDK - Development Guide

**Purpose**: This skill guides correct implementation of Claude Agent SDK for autonomous AI agents in IPA Platform.

**Package**: `claude-agent-sdk` (renamed from `claude-code-sdk` in Sep 2025)
**Install**: `pip install claude-agent-sdk`
**Import**: `from claude_agent_sdk import ...` (note: underscores in import)
**Latest Version**: 0.1.54

## CRITICAL: Package Name Change

```python
# WRONG (old name)
from claude_sdk import query  # ModuleNotFoundError

# CORRECT (current name)
from claude_agent_sdk import query, ClaudeAgentOptions
```

## When to Use Claude Agent SDK

| Scenario | Use Claude SDK | Use Agent Framework |
|----------|---------------|---------------------|
| Autonomous reasoning | Yes | No |
| Structured workflows | No | Yes |
| Independent decisions | Yes | No |
| Predefined sequences | No | Yes |
| Tool usage + reasoning | Yes | Limited |
| GroupChat/Handoff | No | Yes |

## Quick Start

### query() — One-shot Execution

**IMPORTANT**: `query()` returns an **AsyncIterator**, NOT a direct result. Use `async for`:

```python
from claude_agent_sdk import query, ClaudeAgentOptions
import anyio

async def main():
    async for message in query(
        prompt="Analyze this error and suggest fixes",
        options=ClaudeAgentOptions(
            allowed_tools=["Bash", "Glob", "Read"],
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)

anyio.run(main)
```

**WRONG (old pattern):**
```python
# NEVER DO THIS - query() is NOT awaitable
result = await query(prompt="...")  # TypeError!
```

### ClaudeAgentOptions

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
    allowed_commands=["python", "pytest", "git"],  # Bash restrictions
    max_tokens=16384,
)
```

## Built-in Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `Read` | Read file contents | Read a source file |
| `Write` | Write/create files | Create new file |
| `Edit` | Edit existing files | Modify code |
| `Bash` | Execute commands | Run tests |
| `Grep` | Search file contents | Find patterns |
| `Glob` | Find files by pattern | List Python files |
| `WebSearch` | Search the web | Research topics |
| `WebFetch` | Fetch URL content | Get docs |
| `Agent` | Delegate to subagent | Spawn specialist |

**Note**: Subagent tool is `Agent`, NOT `Task`.

## Hooks System (Function-based)

**IMPORTANT**: Hooks use function callbacks + `HookMatcher`, NOT class inheritance.

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

# Define hook function
async def check_bash(input_data, tool_use_id, context):
    command = input_data.get("tool_input", {}).get("command", "")
    if "rm -rf" in command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked",
            }
        }
    return {}

# Audit logger hook
async def audit_logger(input_data, tool_use_id, context):
    print(f"Tool used: {input_data.get('tool_name')}")
    return {}

# Attach hooks via options
options = ClaudeAgentOptions(
    allowed_tools=["Bash", "Read"],
    hooks={
        "PreToolUse": [HookMatcher(matcher="Bash", hooks=[check_bash])],
        "PostToolUse": [HookMatcher(matcher=None, hooks=[audit_logger])],
    }
)
```

**WRONG (old class-based pattern):**
```python
# NEVER DO THIS - class-based hooks are gone
class ApprovalHook(Hook):  # Hook class doesn't exist
    async def on_tool_call(self, ...):
        ...
```

### Hook Events

| Event | When |
|-------|------|
| `PreToolUse` | Before tool execution |
| `PostToolUse` | After successful tool execution |
| `PostToolUseFailure` | After failed tool execution |
| `UserPromptSubmit` | When user sends prompt |
| `Stop` | Agent stopping |
| `SubagentStop` | Subagent stopping |
| `PreCompact` | Before context compaction |
| `Notification` | Agent notification |
| `SubagentStart` | Subagent starting |
| `PermissionRequest` | Permission needed |

## MCP Integration

### In-process MCP Server (New)

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions

@tool("query_db", "Query the database", {"sql": str})
async def query_db(args):
    return {"content": [{"type": "text", "text": run_query(args["sql"])}]}

server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[query_db]
)
```

### External MCP Server

External MCP servers are supported via stdio, SSE, or HTTP transport.

**MCP tool naming format**: `mcp__<server_name>__<action>`

## Subagents (Delegation)

Use `AgentDefinition` + include `Agent` in `allowed_tools`:

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

async for message in query(
    prompt="Use the code-reviewer agent to review this codebase",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Agent"],  # Agent, NOT Task
        agents={
            "code-reviewer": AgentDefinition(
                description="Expert code reviewer for quality and security.",
                prompt="Analyze code quality and suggest improvements.",
                tools=["Read", "Glob", "Grep"],
            ),
            "test-writer": AgentDefinition(
                description="Test writer for unit and integration tests.",
                prompt="Write comprehensive tests for the codebase.",
                tools=["Read", "Write", "Bash"],
            ),
        },
    ),
):
    if hasattr(message, "result"):
        print(message.result)
```

**Note**: Subagents CANNOT include `Agent` in their tools (no recursive spawning).

## Current Model IDs

| Model | API ID | Released |
|-------|--------|---------|
| Claude Opus 4.6 | `claude-opus-4-6` | 2026-02-05 |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 2026-02-17 |
| Claude Opus 4.5 | `claude-opus-4-5-20251101` | 2025-11 |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | 2025-09-29 |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | 2025-10-15 |

## Integration with Agent Framework

```python
from agent_framework import Agent, ConcurrentBuilder
from claude_agent_sdk import query, ClaudeAgentOptions

class HybridOrchestrator:
    """Combine structured workflows with autonomous agents."""

    async def execute(self, task: str):
        if self._is_structured_task(task):
            # Use MAF for structured workflows
            workflow = ConcurrentBuilder(participants=[...]).build()
            return await workflow.run(task)

        # Use Claude Agent SDK for autonomous reasoning
        async for message in query(
            prompt=task,
            options=ClaudeAgentOptions(allowed_tools=["Read", "Bash"]),
        ):
            if hasattr(message, "result"):
                return message.result
```

## Reference Documentation

- [PYTHON-SDK.md](PYTHON-SDK.md) - Python SDK complete reference
- [TYPESCRIPT-SDK.md](TYPESCRIPT-SDK.md) - TypeScript SDK complete reference
- [TOOLS-API.md](TOOLS-API.md) - Built-in tools detailed reference
- [HOOKS-API.md](HOOKS-API.md) - Hooks system patterns
- [MCP-INTEGRATION.md](MCP-INTEGRATION.md) - MCP server integration
- [HYBRID-ARCHITECTURE.md](HYBRID-ARCHITECTURE.md) - Integration with Agent Framework

## Version History

- v0.1.54 (2026-04): Latest release
- Renamed from `claude-code-sdk` to `claude-agent-sdk` (2025-09-29)
- v1.0.0 (2025-12-25): Initial skill file created for IPA Platform
