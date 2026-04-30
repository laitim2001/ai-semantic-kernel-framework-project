"""n8n Integration Module — Bidirectional Collaboration (Mode 3).

Sprint 125: n8n Mode 3 — IPA reasoning + n8n orchestration

Provides the orchestration layer for bidirectional collaboration between
IPA and n8n. IPA handles reasoning and decision-making, n8n handles
workflow orchestration and execution.

Components:
    - N8nOrchestrator: Coordinates IPA reasoning → n8n execution → monitoring
    - ExecutionMonitor: Polls execution status, handles timeout & failure
    - CallbackHandler: Processes async callback notifications from n8n

Flow:
    User Request → IPA Reasoning → n8n Workflow Execution → IPA Monitoring → User Response
"""

from .orchestrator import (
    N8nOrchestrator,
    OrchestrationRequest,
    OrchestrationResult,
    OrchestrationStatus,
)
from .monitor import (
    ExecutionMonitor,
    MonitorConfig,
    ExecutionState,
    ExecutionProgress,
)

__all__ = [
    "N8nOrchestrator",
    "OrchestrationRequest",
    "OrchestrationResult",
    "OrchestrationStatus",
    "ExecutionMonitor",
    "MonitorConfig",
    "ExecutionState",
    "ExecutionProgress",
]
