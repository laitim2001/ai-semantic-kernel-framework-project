"""Checkpoint provider adapters.

Each adapter wraps an existing checkpoint system to implement CheckpointProvider.

Sprint 121 adds 3 adapters for the remaining checkpoint systems:
- AgentFrameworkCheckpointAdapter: Wraps BaseCheckpointStorage (Redis/Postgres/FS)
- DomainCheckpointAdapter: Wraps DatabaseCheckpointStorage (PostgreSQL)
- SessionRecoveryCheckpointAdapter: Wraps SessionRecoveryManager (Cache/Redis)
"""

from src.infrastructure.checkpoint.adapters.agent_framework_adapter import (
    AgentFrameworkCheckpointAdapter,
)
from src.infrastructure.checkpoint.adapters.domain_adapter import DomainCheckpointAdapter
from src.infrastructure.checkpoint.adapters.hybrid_adapter import HybridCheckpointAdapter
from src.infrastructure.checkpoint.adapters.session_recovery_adapter import (
    SessionRecoveryCheckpointAdapter,
)

__all__ = [
    "AgentFrameworkCheckpointAdapter",
    "DomainCheckpointAdapter",
    "HybridCheckpointAdapter",
    "SessionRecoveryCheckpointAdapter",
]
