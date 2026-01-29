# =============================================================================
# IPA Platform - Swarm Events Package
# =============================================================================
# Sprint 101: Swarm Event System + SSE Integration
#
# Package exports for Swarm event types and emitter.
#
# Usage:
#     from src.integrations.swarm.events import (
#         SwarmEventNames,
#         SwarmCreatedPayload,
#         WorkerProgressPayload,
#         SwarmEventEmitter,
#         create_swarm_emitter,
#     )
# =============================================================================

from .types import (
    # Swarm lifecycle payloads
    SwarmCreatedPayload,
    SwarmStatusUpdatePayload,
    SwarmCompletedPayload,
    # Worker lifecycle payloads
    WorkerStartedPayload,
    WorkerProgressPayload,
    WorkerThinkingPayload,
    WorkerToolCallPayload,
    WorkerMessagePayload,
    WorkerCompletedPayload,
    # Event names
    SwarmEventNames,
)
from .emitter import (
    SwarmEventEmitter,
    create_swarm_emitter,
)

__all__ = [
    # Swarm lifecycle payloads
    "SwarmCreatedPayload",
    "SwarmStatusUpdatePayload",
    "SwarmCompletedPayload",
    # Worker lifecycle payloads
    "WorkerStartedPayload",
    "WorkerProgressPayload",
    "WorkerThinkingPayload",
    "WorkerToolCallPayload",
    "WorkerMessagePayload",
    "WorkerCompletedPayload",
    # Event names
    "SwarmEventNames",
    # Emitter
    "SwarmEventEmitter",
    "create_swarm_emitter",
]
