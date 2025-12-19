---
paths: backend/src/integrations/agent_framework/**/*
---

# Agent Framework API Rules

> 🔴 **CRITICAL**: These rules MUST be followed when working in the Agent Framework integration layer.

## Mandatory Requirements

### 1. Always Import Official API

```python
# REQUIRED: Import from agent_framework
from agent_framework import (
    WorkflowBuilder, Executor, Edge, Workflow, handler,
    ConcurrentBuilder, GroupChatBuilder, HandoffBuilder, MagenticBuilder,
    ChatAgent, BaseAgent, CheckpointStorage,
)
```

### 2. Always Create Official Builder Instance

```python
class XxxBuilderAdapter:
    def __init__(self):
        self._builder = OfficialBuilder()  # REQUIRED
```

### 3. Always Call Official API in build()

```python
def build(self):
    return self._builder.build()  # REQUIRED: Call official API
```

## Prohibited Actions

- ❌ Creating custom workflow logic without `agent_framework` imports
- ❌ Skipping `from agent_framework import` statements
- ❌ Implementing similar functionality without calling official API
- ❌ Modifying official API behavior incompatibly

## Verification Command

```bash
cd backend && python scripts/verify_official_api_usage.py
```

All 5 checks MUST pass before completing any work.

## Quick Reference

| Official Class | IPA Adapter |
|----------------|-------------|
| `GroupChatBuilder` | `GroupChatBuilderAdapter` |
| `HandoffBuilder` | `HandoffBuilderAdapter` |
| `ConcurrentBuilder` | `ConcurrentBuilderAdapter` |
| `MagenticBuilder` | `MagenticBuilderAdapter` |
| `WorkflowExecutor` | `NestedWorkflowAdapter` |
| `CheckpointStorage` | `MultiTurnAdapter` |
