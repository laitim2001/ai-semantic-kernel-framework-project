"""Hybrid Orchestration Module.

Sprint 50: S50-3/S50-4 - Hybrid Orchestrator & Context Synchronizer

This module provides hybrid orchestration between Microsoft Agent Framework
and Claude Agent SDK, enabling intelligent task routing based on capabilities.

Key Components:
- HybridOrchestrator: Main orchestration class for task execution
- CapabilityMatcher: Analyzes tasks to identify required capabilities
- FrameworkSelector: Selects optimal framework for execution
- ContextSynchronizer: Synchronizes context between frameworks
- Type definitions for hybrid operations

Example Usage:
    from src.integrations.claude_sdk.hybrid import (
        HybridOrchestrator,
        ContextSynchronizer,
        create_orchestrator,
        create_synchronizer,
    )

    # Create orchestrator
    orchestrator = create_orchestrator(
        primary_framework="claude_sdk",
        auto_switch=True,
    )

    # Execute task
    result = await orchestrator.execute("Search for Python tutorials")

    # Create synchronizer for context management
    synchronizer = create_synchronizer()
    context = synchronizer.create_context(system_prompt="You are a helpful assistant")
    context.add_message("user", "Hello!")

    # Check result
    print(f"Framework used: {result.framework_used}")
    print(f"Response: {result.content}")
"""

from .capability import (
    CapabilityMatcher,
    CapabilityScore,
    create_matcher,
)
from .orchestrator import (
    ExecutionContext,
    HybridOrchestrator,
    create_orchestrator,
)
from .selector import (
    FrameworkSelector,
    SelectionContext,
    SelectionResult,
    SelectionStrategy,
    create_selector,
)
from .synchronizer import (
    ConflictResolution,
    ContextDiff,
    ContextFormat,
    ContextSnapshot,
    ContextState,
    ContextSynchronizer,
    Message,
    SyncDirection,
    create_synchronizer,
)
from .types import (
    Framework,
    HybridResult,
    HybridSessionConfig,
    TaskAnalysis,
    TaskCapability,
    ToolCall,
)

__all__ = [
    # Main orchestrator
    "HybridOrchestrator",
    "create_orchestrator",
    "ExecutionContext",
    # Capability matching
    "CapabilityMatcher",
    "CapabilityScore",
    "create_matcher",
    # Framework selection
    "FrameworkSelector",
    "SelectionContext",
    "SelectionResult",
    "SelectionStrategy",
    "create_selector",
    # Context synchronization
    "ContextSynchronizer",
    "ContextState",
    "ContextDiff",
    "ContextSnapshot",
    "ContextFormat",
    "ConflictResolution",
    "SyncDirection",
    "Message",
    "create_synchronizer",
    # Types
    "Framework",
    "HybridResult",
    "HybridSessionConfig",
    "TaskAnalysis",
    "TaskCapability",
    "ToolCall",
]
