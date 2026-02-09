# Domain Layer

> Business logic layer — 20 modules, ~112 Python files

---

## Directory Structure

```
domain/
├── __init__.py
│
│  # Core Business Modules
├── agents/                 # Agent management (7 files)
│   ├── service.py          # AgentService
│   ├── models.py           # Domain models
│   └── tools/              # Agent tools
│
├── workflows/              # Workflow management (11 files)
│   ├── service.py          # WorkflowService
│   ├── state_machine.py    # Workflow state machine
│   └── executors/          # Execution strategies
│
├── executions/             # Execution lifecycle (2 files)
│   ├── service.py          # ExecutionService
│   └── state_machine.py    # Execution state machine
│
├── checkpoints/            # Human-in-the-loop checkpoints (3 files)
│   └── service.py          # CheckpointService
│
├── sessions/               # Phase 11: Agent-Session Integration (33 files - largest)
│   ├── models.py           # Session, Message, Attachment, ToolCall models
│   ├── service.py          # SessionService (lifecycle management)
│   ├── events.py           # SessionEventPublisher (15 event types)
│   ├── executor.py         # AgentExecutor (LLM interaction)
│   ├── streaming.py        # StreamingHandler (SSE support)
│   ├── tool_handler.py     # ToolCallHandler (with approval)
│   ├── error_handler.py    # SessionErrorHandler (24 error codes)
│   ├── recovery.py         # SessionRecoveryManager
│   └── metrics.py          # MetricsCollector (Prometheus-style)
│
│  # Supporting Modules
├── auth/                   # Authentication (3 files)
├── files/                  # File handling (3 files)
├── sandbox/                # Sandboxed execution (2 files)
├── templates/              # Workflow templates (3 files)
├── triggers/               # Triggers (2 files)
├── connectors/             # External connectors (6 files)
├── routing/                # Intelligent routing (2 files)
├── notifications/          # Notifications (2 files)
├── audit/                  # Audit logs (2 files)
├── versioning/             # Version control (2 files)
├── prompts/                # Prompt management (2 files)
├── learning/               # Learning system (2 files)
├── devtools/               # Developer tools (2 files)
│
└── orchestration/          # ⚠️ DEPRECATED - use integrations/agent_framework/
    ├── multiturn/          # → use MultiTurnAdapter
    ├── memory/             # → use Memory Adapters
    ├── planning/           # → use PlanningAdapter
    └── nested/             # → use NestedWorkflowAdapter
```

---

## ⚠️ IMPORTANT: Orchestration Deprecation

The `domain/orchestration/` directory is **DEPRECATED**.

All orchestration logic should use the official Agent Framework adapters:

| Old Location | New Location | Adapter |
|--------------|--------------|---------|
| `domain/orchestration/multiturn/` | `integrations/agent_framework/multiturn/` | MultiTurnAdapter |
| `domain/orchestration/memory/` | `integrations/agent_framework/memory/` | Memory Adapters |
| `domain/orchestration/planning/` | `integrations/agent_framework/builders/` | PlanningAdapter |
| `domain/orchestration/nested/` | `integrations/agent_framework/builders/` | NestedWorkflowAdapter |

---

## Service Pattern

### Standard Service Template

```python
# service.py template
from typing import List, Optional
from sqlalchemy.orm import Session

from src.infrastructure.database.repositories.{module}_repository import {Module}Repository
from src.infrastructure.database.models.{module} import {Module}Model
from src.core.logging import get_logger

logger = get_logger(__name__)


class {Module}Service:
    """
    Service for {Module} business logic.

    Responsibilities:
    - Business rule validation
    - Orchestrating repository operations
    - Domain event handling
    - Transaction management
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = {Module}Repository(db)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[{Module}Model]:
        """Get all {module}s with optional filtering."""
        return self.repository.get_all(skip=skip, limit=limit, **filters)

    def get_by_id(self, id: str) -> Optional[{Module}Model]:
        """Get {module} by ID."""
        return self.repository.get_by_id(id)

    def create(self, data: dict) -> {Module}Model:
        """
        Create new {module}.

        Args:
            data: Creation data

        Returns:
            Created {module}

        Raises:
            ValidationError: If data is invalid
            BusinessRuleError: If business rules violated
        """
        # 1. Validate business rules
        self._validate_create(data)

        # 2. Create via repository
        item = self.repository.create(data)

        # 3. Post-creation logic (events, notifications, etc.)
        logger.info(f"Created {module}: {item.id}")

        return item

    def update(self, id: str, data: dict) -> {Module}Model:
        """Update existing {module}."""
        item = self.get_by_id(id)
        if not item:
            raise NotFoundError(f"{Module} not found: {id}")

        self._validate_update(item, data)
        return self.repository.update(id, data)

    def delete(self, id: str) -> None:
        """Delete {module}."""
        item = self.get_by_id(id)
        if not item:
            raise NotFoundError(f"{Module} not found: {id}")

        self._validate_delete(item)
        self.repository.delete(id)
        logger.info(f"Deleted {module}: {id}")

    def _validate_create(self, data: dict) -> None:
        """Validate creation business rules."""
        pass

    def _validate_update(self, item, data: dict) -> None:
        """Validate update business rules."""
        pass

    def _validate_delete(self, item) -> None:
        """Validate deletion business rules."""
        pass
```

---

## State Machine Pattern

### Execution State Machine

```python
# executions/state_machine.py
from enum import Enum
from typing import Dict, Set


class ExecutionState(str, Enum):
    """Execution lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStateMachine:
    """
    State machine for execution lifecycle.

    State transitions:
    - pending → running
    - running → waiting_approval, completed, failed
    - waiting_approval → approved, rejected
    - approved → running
    - rejected → failed
    - any → cancelled
    """

    TRANSITIONS: Dict[ExecutionState, Set[ExecutionState]] = {
        ExecutionState.PENDING: {ExecutionState.RUNNING, ExecutionState.CANCELLED},
        ExecutionState.RUNNING: {
            ExecutionState.WAITING_APPROVAL,
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        },
        ExecutionState.WAITING_APPROVAL: {
            ExecutionState.APPROVED,
            ExecutionState.REJECTED,
            ExecutionState.CANCELLED,
        },
        ExecutionState.APPROVED: {ExecutionState.RUNNING},
        ExecutionState.REJECTED: {ExecutionState.FAILED},
        ExecutionState.COMPLETED: set(),  # Terminal state
        ExecutionState.FAILED: set(),     # Terminal state
        ExecutionState.CANCELLED: set(),  # Terminal state
    }

    @classmethod
    def can_transition(cls, from_state: ExecutionState, to_state: ExecutionState) -> bool:
        """Check if state transition is valid."""
        return to_state in cls.TRANSITIONS.get(from_state, set())

    @classmethod
    def transition(cls, from_state: ExecutionState, to_state: ExecutionState) -> ExecutionState:
        """
        Perform state transition.

        Raises:
            InvalidStateTransition: If transition is not allowed
        """
        if not cls.can_transition(from_state, to_state):
            raise InvalidStateTransition(
                f"Cannot transition from {from_state} to {to_state}"
            )
        return to_state
```

---

## Checkpoint System

### Human-in-the-Loop Approval

```python
# checkpoints/service.py
from datetime import datetime, timedelta
from typing import Optional

from src.domain.executions.state_machine import ExecutionState, ExecutionStateMachine


class CheckpointService:
    """
    Service for human-in-the-loop approvals.

    Features:
    - Approval/rejection workflow
    - Timeout handling
    - Escalation rules
    """

    def request_approval(
        self,
        execution_id: str,
        checkpoint_name: str,
        timeout_minutes: int = 60,
        escalation_config: Optional[dict] = None
    ) -> Checkpoint:
        """
        Request human approval for execution.

        Args:
            execution_id: Execution requiring approval
            checkpoint_name: Checkpoint identifier
            timeout_minutes: Auto-reject after this time
            escalation_config: Escalation rules

        Returns:
            Created checkpoint
        """
        # Update execution state
        self._update_execution_state(execution_id, ExecutionState.WAITING_APPROVAL)

        # Create checkpoint
        checkpoint = self.repository.create({
            "execution_id": execution_id,
            "name": checkpoint_name,
            "status": "pending",
            "timeout_at": datetime.utcnow() + timedelta(minutes=timeout_minutes),
            "escalation_config": escalation_config,
        })

        # Send notification
        self._notify_approvers(checkpoint)

        return checkpoint

    def approve(self, checkpoint_id: str, approver_id: str, comment: str = "") -> Checkpoint:
        """Approve checkpoint and resume execution."""
        checkpoint = self._get_checkpoint(checkpoint_id)
        checkpoint.status = "approved"
        checkpoint.approved_by = approver_id
        checkpoint.approved_at = datetime.utcnow()
        checkpoint.comment = comment

        # Resume execution
        self._update_execution_state(checkpoint.execution_id, ExecutionState.APPROVED)

        return checkpoint

    def reject(self, checkpoint_id: str, rejector_id: str, reason: str) -> Checkpoint:
        """Reject checkpoint and fail execution."""
        checkpoint = self._get_checkpoint(checkpoint_id)
        checkpoint.status = "rejected"
        checkpoint.rejected_by = rejector_id
        checkpoint.rejected_at = datetime.utcnow()
        checkpoint.rejection_reason = reason

        # Fail execution
        self._update_execution_state(checkpoint.execution_id, ExecutionState.REJECTED)

        return checkpoint
```

---

## Best Practices

### Do's

- Keep services focused on business logic
- Use repository pattern for data access
- Implement proper validation
- Log important operations
- Handle errors gracefully

### Don'ts

- Don't put HTTP/API logic in services
- Don't access database directly (use repositories)
- Don't implement orchestration here (use adapters)
- Don't mix concerns between services

---

## Sessions Module (Phase 11)

### Overview

The `sessions/` module provides Agent-Session integration for conversational AI:

| Component | Purpose |
|-----------|---------|
| `models.py` | Session, Message, Attachment, ToolCall domain models |
| `service.py` | SessionService for lifecycle management |
| `events.py` | Event publishing with 15 event types |
| `executor.py` | AgentExecutor for LLM interaction |
| `streaming.py` | StreamingHandler for SSE responses |
| `tool_handler.py` | ToolCallHandler with approval workflow |
| `error_handler.py` | 24 error codes with HTTP mapping |
| `recovery.py` | Checkpoint and event buffer recovery |
| `metrics.py` | Prometheus-style metrics collection |

### Session State Machine

```
CREATED → ACTIVE ↔ SUSPENDED → ENDED
```

### Key Features

- **Tool Approval**: Manual/auto approval modes for tool calls
- **SSE Streaming**: Real-time response streaming
- **Error Recovery**: Checkpoint-based session recovery
- **Metrics**: Counter, Histogram, Gauge metrics

---

**Last Updated**: 2026-02-09
