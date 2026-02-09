# Agent Framework Integration Layer

> **This is the MOST CRITICAL directory in the entire project.**
> All code here MUST use official Microsoft Agent Framework API.

---

## Directory Purpose

This directory contains **Adapter implementations** that wrap the official Microsoft Agent Framework API.
The IPA Platform uses the Adapter Pattern to:
1. Provide a consistent internal interface
2. Add platform-specific features (logging, metrics, error handling)
3. Maintain compatibility when official API changes

---

## CRITICAL Rules

### MUST Do

1. **Import official classes from `agent_framework`**:
```python
from agent_framework import (
    # Core Workflow API
    WorkflowBuilder,
    Executor,
    Edge,
    Workflow,
    handler,

    # Builder API
    ConcurrentBuilder,
    GroupChatBuilder,
    HandoffBuilder,
    MagenticBuilder,

    # Agent API
    ChatAgent,
    BaseAgent,

    # Storage API
    CheckpointStorage,
)
```

2. **Every Adapter class MUST have an official Builder instance**:
```python
class GroupChatBuilderAdapter:
    def __init__(self, ...):
        self._builder = GroupChatBuilder()  # REQUIRED: Official instance
```

3. **build() method MUST call official API**:
```python
def build(self) -> Workflow:
    return self._builder.participants(...).build()  # REQUIRED: Official API call
```

### MUST NOT Do

- Do NOT create your own workflow logic without using `agent_framework` imports
- Do NOT skip `from agent_framework import ...` statements
- Do NOT implement similar functionality without calling official API
- Do NOT modify official API behavior in incompatible ways

---

## Directory Structure

```
agent_framework/
├── __init__.py           # Re-exports all adapters
├── CLAUDE.md             # This file
│
├── builders/             # Builder Adapters (wrap official Builder API)
│   ├── __init__.py
│   ├── groupchat.py      # GroupChatBuilderAdapter → GroupChatBuilder
│   ├── handoff.py        # HandoffBuilderAdapter → HandoffBuilder
│   ├── concurrent.py     # ConcurrentBuilderAdapter → ConcurrentBuilder
│   ├── nested_workflow.py # NestedWorkflowAdapter → WorkflowExecutor
│   ├── planning.py       # PlanningAdapter → MagenticBuilder
│   ├── magentic.py       # MagenticBuilderAdapter → MagenticBuilder
│   └── agent_executor.py # AgentExecutorAdapter
│
├── core/                 # Core Workflow Adapters (wrap Workflow API)
│   ├── __init__.py
│   ├── workflow.py       # WorkflowAdapter → WorkflowBuilder
│   ├── executor.py       # ExecutorAdapter → Executor
│   ├── edge.py           # Edge utilities
│   ├── events.py         # Event handling
│   ├── execution.py      # Execution management
│   ├── approval.py       # Human-in-the-loop approval
│   └── approval_workflow.py
│
├── multiturn/            # Multi-turn Conversation Support
│   ├── __init__.py
│   ├── adapter.py        # MultiTurnAdapter → CheckpointStorage
│   └── checkpoint_storage.py
│
└── memory/               # Memory Storage Adapters
    ├── __init__.py
    └── storage.py
```

---

## Adapter Pattern Implementation

### Standard Adapter Template

```python
"""
Module: xxx_adapter.py
Purpose: Wraps official XxxBuilder for IPA Platform integration

Official API: agent_framework.XxxBuilder
"""
from typing import Any, Dict, Optional
from agent_framework import XxxBuilder  # REQUIRED: Import official class

from backend.src.core.logging import get_logger

logger = get_logger(__name__)


class XxxBuilderAdapter:
    """
    Adapter for official Microsoft Agent Framework XxxBuilder.

    This adapter:
    1. Wraps official XxxBuilder API
    2. Adds IPA-specific logging and metrics
    3. Provides consistent error handling

    Official API Reference:
    - Class: agent_framework.XxxBuilder
    - Methods: .participants(), .build(), etc.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize adapter with official builder instance.

        Args:
            config: Platform-specific configuration
        """
        self._builder = XxxBuilder()  # REQUIRED: Create official instance
        self._config = config or {}
        logger.info(f"Initialized {self.__class__.__name__}")

    def build(self, **kwargs) -> Any:
        """
        Build using official API.

        Returns:
            Result from official builder.build()
        """
        # REQUIRED: Call official API
        result = self._builder.build(**kwargs)
        logger.info(f"Built workflow via official API")
        return result
```

---

## API Reference Quick Guide

### Core Workflow API

| Official Class | IPA Adapter | Purpose |
|----------------|-------------|---------|
| `WorkflowBuilder` | `WorkflowAdapter` | Build workflow definitions |
| `Executor` | `ExecutorAdapter` | Execute workflows |
| `@handler` | Used directly | Decorate node handlers |
| `Edge` | Used directly | Define workflow edges |

### Builder API

| Official Class | IPA Adapter | Purpose |
|----------------|-------------|---------|
| `GroupChatBuilder` | `GroupChatBuilderAdapter` | Multi-agent chat |
| `HandoffBuilder` | `HandoffBuilderAdapter` | Agent handoff |
| `ConcurrentBuilder` | `ConcurrentBuilderAdapter` | Parallel execution |
| `MagenticBuilder` | `MagenticBuilderAdapter` | Dynamic planning |

### Storage API

| Official Class | IPA Adapter | Purpose |
|----------------|-------------|---------|
| `CheckpointStorage` | `MultiTurnAdapter` | Conversation state |

---

## Verification

Before completing any work in this directory, run:

```bash
cd backend
python scripts/verify_official_api_usage.py
```

**All 5 checks must pass:**
1. Official imports present
2. Builder instance created
3. Official API called in build()
4. No custom workflow logic
5. Type hints match official API

---

## Common Mistakes to Avoid

### Wrong: Creating custom implementation

```python
# WRONG - No official import
class GroupChatBuilderAdapter:
    def __init__(self):
        self._participants = []  # Custom implementation

    def add_participant(self, agent):
        self._participants.append(agent)  # Not using official API
```

### Correct: Using official API

```python
# CORRECT - Uses official import and API
from agent_framework import GroupChatBuilder

class GroupChatBuilderAdapter:
    def __init__(self):
        self._builder = GroupChatBuilder()  # Official instance

    def add_participant(self, agent):
        self._builder.add_participant(agent)  # Official API call
```

---

## Beta Version Notes

The Agent Framework is currently in **Preview/Beta** (version `1.0.0b251204`).

- API may change between versions
- Check release notes before upgrading
- Reference source: `C:\Users\...\site-packages\agent_framework\`

---

## Cross-Phase Integration

### Phase 28: Three-tier Intent Routing

The orchestration layer (`integrations/orchestration/`) uses the agent framework for LLM-based intent classification (Tier 3). The `BusinessIntentRouter` delegates to agent framework adapters when LLM classification is needed.

### Phase 29: Agent Swarm Visualization

The swarm system (`integrations/swarm/`) coordinates multiple worker agents. Each worker may use agent framework adapters for task execution. The `SwarmTracker` monitors agent lifecycle events that originate from framework execution.

---

**Last Updated**: 2026-02-09
