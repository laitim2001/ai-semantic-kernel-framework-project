"""
MAF Anti-Corruption Layer (ACL)

Provides stable interfaces that isolate IPA Platform code from
Microsoft Agent Framework preview API breaking changes.

Architecture:
    IPA Platform Code
      → ACL Interfaces (stable, never change)
        → MAFAdapter (maps stable → current MAF API)
          → agent_framework package (preview, may break)

Sprint 128: Story 128-2 — MAF Anti-Corruption Layer
"""

from .interfaces import (
    AgentBuilderInterface,
    AgentConfig,
    AgentRunnerInterface,
    ToolInterface,
    WorkflowResult,
)
from .version_detector import (
    MAFVersionDetector,
    MAFVersionInfo,
)
from .adapter import (
    MAFAdapter,
    get_maf_adapter,
)

__all__ = [
    # Stable Interfaces
    "AgentBuilderInterface",
    "AgentRunnerInterface",
    "ToolInterface",
    # Immutable Data Types
    "AgentConfig",
    "WorkflowResult",
    # Version Detection
    "MAFVersionDetector",
    "MAFVersionInfo",
    # Adapter
    "MAFAdapter",
    "get_maf_adapter",
]
