"""
IPA Platform - Integrations Module

外部系統整合模組，包含:
- agent_framework: Microsoft Agent Framework 整合層
- 其他外部服務整合
"""

from .agent_framework import (
    # Base adapters
    BaseAdapter,
    BuilderAdapter,
    # Exceptions
    AdapterError,
    AdapterInitializationError,
    WorkflowBuildError,
    ExecutionError,
    CheckpointError,
    # Workflow
    WorkflowAdapter,
    WorkflowConfig,
)

__all__ = [
    # Base
    "BaseAdapter",
    "BuilderAdapter",
    # Exceptions
    "AdapterError",
    "AdapterInitializationError",
    "WorkflowBuildError",
    "ExecutionError",
    "CheckpointError",
    # Workflow
    "WorkflowAdapter",
    "WorkflowConfig",
]
