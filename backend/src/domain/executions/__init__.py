# =============================================================================
# IPA Platform - Executions Domain Module
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Execution domain module providing:
#   - ExecutionStatus: Status enumeration
#   - ExecutionStateMachine: State transition management
#   - State transition validation utilities
#
# Usage:
#   from src.domain.executions import ExecutionStatus, ExecutionStateMachine
#
#   machine = ExecutionStateMachine(execution_id)
#   machine.start()
#   machine.complete(llm_calls=5, llm_tokens=1000, llm_cost=0.015)
# =============================================================================

from src.domain.executions.state_machine import (
    ExecutionStateMachine,
    ExecutionStatus,
    InvalidStateTransitionError,
    TERMINAL_STATES,
    TRANSITIONS,
    create_execution_state_machine,
    validate_transition,
)

__all__ = [
    "ExecutionStatus",
    "ExecutionStateMachine",
    "InvalidStateTransitionError",
    "TRANSITIONS",
    "TERMINAL_STATES",
    "create_execution_state_machine",
    "validate_transition",
]
