"""
IPA Platform - Test Mocks Module

提供測試用的 Mock 實現和工具。

包含:
    - Agent Framework 組件的 Mock 實現
    - Pytest Fixtures
    - 測試輔助函數
"""

from .agent_framework_mocks import (
    # Mock classes
    MockExecutor,
    MockWorkflowContext,
    MockCheckpointStorage,
    MockWorkflow,
    MockWorkflowRunResult,
    # Helper functions
    create_test_workflow,
    create_test_executor,
    create_test_checkpoint,
    assert_workflow_result,
    # Pytest fixtures are auto-registered
)

__all__ = [
    # Mock classes
    "MockExecutor",
    "MockWorkflowContext",
    "MockCheckpointStorage",
    "MockWorkflow",
    "MockWorkflowRunResult",
    # Helper functions
    "create_test_workflow",
    "create_test_executor",
    "create_test_checkpoint",
    "assert_workflow_result",
]
