"""
Agent Swarm Integration Module

This module provides the core infrastructure for Agent Swarm visualization,
enabling real-time monitoring of multi-agent collaboration.

Key Components:
- Data Models: WorkerExecution, AgentSwarmStatus, ToolCallInfo, ThinkingContent
- SwarmTracker: State management for swarm execution
- SwarmIntegration: Integration layer for ClaudeCoordinator

Example Usage:
    from src.integrations.swarm import (
        SwarmTracker,
        SwarmMode,
        WorkerType,
        AgentSwarmStatus,
    )

    # Create tracker
    tracker = SwarmTracker()

    # Create a new swarm
    swarm = tracker.create_swarm(
        swarm_id="swarm-123",
        mode=SwarmMode.PARALLEL,
    )

    # Start a worker
    worker = tracker.start_worker(
        swarm_id="swarm-123",
        worker_id="worker-1",
        worker_name="Research Agent",
        worker_type=WorkerType.RESEARCH,
        role="Gather information",
    )
"""

from .models import (
    # Enums
    WorkerType,
    WorkerStatus,
    SwarmMode,
    SwarmStatus,
    ToolCallStatus,
    # Data classes
    ToolCallInfo,
    ThinkingContent,
    WorkerMessage,
    WorkerExecution,
    AgentSwarmStatus,
)

from .tracker import (
    SwarmTracker,
    SwarmNotFoundError,
    WorkerNotFoundError,
    ToolCallNotFoundError,
    get_swarm_tracker,
    set_swarm_tracker,
)

from .swarm_integration import (
    SwarmIntegration,
    create_swarm_integration,
)

from .events import (
    # Event types
    SwarmEventNames,
    SwarmCreatedPayload,
    SwarmStatusUpdatePayload,
    SwarmCompletedPayload,
    WorkerStartedPayload,
    WorkerProgressPayload,
    WorkerThinkingPayload,
    WorkerToolCallPayload,
    WorkerMessagePayload,
    WorkerCompletedPayload,
    # Emitter
    SwarmEventEmitter,
    create_swarm_emitter,
)

__all__ = [
    # Enums
    "WorkerType",
    "WorkerStatus",
    "SwarmMode",
    "SwarmStatus",
    "ToolCallStatus",
    # Data classes
    "ToolCallInfo",
    "ThinkingContent",
    "WorkerMessage",
    "WorkerExecution",
    "AgentSwarmStatus",
    # Tracker
    "SwarmTracker",
    "SwarmNotFoundError",
    "WorkerNotFoundError",
    "ToolCallNotFoundError",
    "get_swarm_tracker",
    "set_swarm_tracker",
    # Integration
    "SwarmIntegration",
    "create_swarm_integration",
    # Event types (Sprint 101)
    "SwarmEventNames",
    "SwarmCreatedPayload",
    "SwarmStatusUpdatePayload",
    "SwarmCompletedPayload",
    "WorkerStartedPayload",
    "WorkerProgressPayload",
    "WorkerThinkingPayload",
    "WorkerToolCallPayload",
    "WorkerMessagePayload",
    "WorkerCompletedPayload",
    # Emitter (Sprint 101)
    "SwarmEventEmitter",
    "create_swarm_emitter",
]

# Version info
__version__ = "1.0.0"
