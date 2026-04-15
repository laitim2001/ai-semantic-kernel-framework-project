---
name: microsoft-agent-framework
description: |
  CRITICAL development guide for Microsoft Agent Framework (MAF) v1.0.x GA in IPA Platform.

  MUST READ when working with:
  - Agents (Agent, AgentThread, Message)
  - Builders (ConcurrentBuilder, GroupChatBuilder, HandoffBuilder, MagenticBuilder)
  - Workflows (Executor, Edge, WorkflowExecutor)
  - Multi-agent orchestration
  - Any code in backend/src/integrations/agent_framework/builders/

  PREVENTS: Custom implementations instead of wrapping official API.
  REQUIRES: Import official classes, use Adapter pattern with self._builder = OfficialBuilder()

  Updated: 2026-04-11 (v1.0.1 GA)
---

# Microsoft Agent Framework - Development Guide

**Purpose**: This skill guides correct implementation of Microsoft Agent Framework (MAF) in this project. Always follow these patterns instead of creating custom implementations.

**Version**: 1.0.1 GA (released 2026-04-10)
**Install**: `pip install agent-framework` (no longer needs `--pre`)
**Python**: >= 3.10

## CRITICAL: Breaking Changes from rc4 to 1.0.x GA

If you see old rc4 code patterns, they MUST be updated:

| Old (rc4/beta) | New (1.0.x GA) |
|----------------|----------------|
| `ChatAgent` | **`Agent`** |
| `chat_client=` | **`client=`** |
| `ChatMessage` | **`Message`** |
| `model_id=` | **`model=`** |
| `@ai_function` | **`@tool`** |
| `BaseHistoryProvider` | **`HistoryProvider`** |
| `call_next(context)` | **`call_next()`** (no args) |
| `agent-framework-azure-ai` | merged into **`agent-framework-foundry`** |
| `pip install agent-framework --pre` | **`pip install agent-framework`** |

## CRITICAL RULES

1. **NEVER create custom agent base classes** - Use `Agent`
2. **NEVER invent custom orchestration** - Use MAF's `Workflow` with `Executor` and `Edge`
3. **NEVER create custom tool abstractions** - Use MAF's `@tool` decorator or MCP tools
4. **NEVER implement Builder classes from scratch** - Use official `ConcurrentBuilder`, `GroupChatBuilder`, `HandoffBuilder`, `MagenticBuilder`
5. **ALWAYS use Adapter pattern** - Wrap official builders with `self._builder = OfficialBuilder()`
6. **ALWAYS check references/** for correct API signatures before implementing

## Builder API (MOST IMPORTANT FOR THIS PROJECT)

```python
# REQUIRED IMPORTS - 1.0.x GA
from agent_framework import (
    Agent,                       # NOT ChatAgent
    Message,                     # NOT ChatMessage
    ConcurrentBuilder,
    GroupChatBuilder,
    HandoffBuilder,
    MagenticBuilder,
    WorkflowExecutor,
    MagenticManagerBase,
    StandardMagenticManager,
    tool,                        # @tool decorator
)
```

**Adapter Pattern (MUST FOLLOW):**
```python
class MyBuilderAdapter:
    def __init__(self):
        self._builder = OfficialBuilder()  # MUST have this line

    def build(self):
        return self._builder.build()  # MUST call official API
```

**Verification Command:**
```bash
cd backend && python scripts/verify_official_api_usage.py
# Expected: 5/5 checks passed
```

See **`references/builders-api.md`** for complete Builder API documentation.

## Creating an Agent (1.0.x GA)

```python
from agent_framework import Agent, tool

# Function tool with @tool decorator
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a given location."""
    return f"The weather in {location} is cloudy with a high of 15C."

# Create agent
agent = Agent(
    client=client,           # NOT chat_client=
    name="weather-agent",
    instructions="You are a weather assistant.",
    tools=[get_weather],
)

# Run
response = await agent.run("What's the weather in Taipei?")
```

**WRONG (old rc4 patterns):**
```python
# NEVER DO THIS - rc4 syntax
agent = ChatAgent(chat_client=client, ...)  # ChatAgent is gone
agent = Agent(chat_client=client, ...)      # chat_client is gone
```

## Tool System (1.0.x GA)

```python
from agent_framework import tool
from typing import Annotated

# Method 1: @tool decorator (recommended)
@tool
def search_database(
    query: Annotated[str, "The search query"],
    limit: Annotated[int, "Max results"] = 10
) -> str:
    """Search the database for matching records."""
    return f"Found {limit} results for: {query}"

# Method 2: Plain function (auto-parsed from type hints + docstring)
def analyze_logs(filepath: str, severity: str = "ERROR") -> str:
    """Analyze log files for issues."""
    return f"Analyzed {filepath} for {severity} entries"

# Both work as tools
agent = Agent(client=client, tools=[search_database, analyze_logs])
```

## MCP Tools (1.0.x GA)

```python
from agent_framework import MCPStdioTool, MCPStreamableHTTPTool

# Stdio-based MCP server
async with MCPStdioTool(
    name="filesystem",
    command="uvx",
    args=["mcp-server-filesystem", "--root", "/data"]
) as mcp:
    result = await agent.run("List files", tools=mcp)

# HTTP-based MCP server
async with MCPStreamableHTTPTool(
    name="database",
    url="http://localhost:3000/mcp"
) as mcp:
    result = await agent.run("Query users", tools=mcp)
```

## ConcurrentBuilder (Parallel Execution)

```python
from agent_framework.orchestrations import ConcurrentBuilder

# Create parallel workflow
workflow = ConcurrentBuilder(participants=[agent1, agent2, agent3]).build()

# Execute (supports streaming)
result = await workflow.run(message="Check all systems", stream=True)

# Process streaming events
async for event in workflow.run(message="Check systems", stream=True):
    # Handle events
    pass
```

## Middleware (1.0.x GA)

```python
# NOTE: call_next() takes NO arguments in 1.0.x
async def logging_middleware(context, call_next):
    print(f"Before: {context.agent.name}")
    await call_next()  # NOT call_next(context)
    print(f"After: {context.agent.name}")

agent = Agent(client=client, middleware=[logging_middleware])
```

## HITL (Human-in-the-Loop) in Workflows

```python
from agent_framework import ToolApprovalRequestContent, RequestInfoEvent

# Workflows support pause/resume for human approval
# All orchestration modes support checkpoints
```

## A2A (Agent-to-Agent Protocol)

```python
# Separate package
pip install agent-framework-a2a
```

## Package Ecosystem (1.0.x)

| Package | Purpose |
|---------|---------|
| `agent-framework` | Core framework (Agent, tools, orchestrations) |
| `agent-framework-foundry` | Azure Foundry integration (replaces azure-ai) |
| `agent-framework-a2a` | Agent-to-Agent protocol |
| `agent-framework-purview` | Microsoft Purview integration |

## Conversation State

```python
from agent_framework import AgentThread

thread = AgentThread()
result1 = await agent.run("Hello", thread=thread)
result2 = await agent.run("Follow up", thread=thread)  # Has context
```

## Self-Hosted Deployment

```python
from agent_framework.openai import OpenAIChatClient

# For Azure OpenAI
from agent_framework.openai import AzureOpenAIResponsesClient

client = AzureOpenAIResponsesClient(
    azure_endpoint="https://xxx.openai.azure.com/",
    api_key="xxx",
    model="gpt-5.4-mini",
    api_version="2025-03-01-preview",
)
```

## Quick Reference

| Need | Use This | NOT This |
|------|----------|----------|
| Create agent | `Agent` | ~~ChatAgent~~, custom class |
| Add tools | `@tool` + function | ~~@ai_function~~, custom wrapper |
| Multi-agent | `Workflow` + `Executor` | Custom orchestrator |
| Parallel exec | `ConcurrentBuilder` | Custom parallel runner |
| Group chat | `GroupChatBuilder` | Custom group logic |
| Agent handoff | `HandoffBuilder` | Custom handoff |
| External tools | `MCPStdioTool` | Direct API calls |
| Conversation | `AgentThread` | Custom message list |
| Streaming | `agent.run(stream=True)` | Custom streaming |

## Before Implementing, Check:

1. **`references/builders-api.md`** - Builder patterns
2. **`references/python-api.md`** - Python class signatures
3. **`references/workflows-api.md`** - Workflow patterns
4. **`references/common-mistakes.md`** - Anti-patterns to avoid

## Version History

- v1.0.1 (2026-04-10): Patch release
- v1.0.0 (2026-04-02): GA release - major renames (ChatAgent→Agent, etc.)
- v1.0.0rc4 (2026-03-11): Release candidate (IPA currently uses this)
- v1.0.0b251204 (2025-12-04): Beta (original reference/ snapshot)
