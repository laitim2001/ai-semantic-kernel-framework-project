"""
IPA Platform - Test Mocks Module

提供測試用的 Mock 實現和工具。

包含:
    - Agent Framework 組件的 Mock 實現
    - Orchestration 組件的 Mock 實現 (Sprint 112)
    - LLM 服務的 Mock 實現 (Sprint 112)
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

# Sprint 112: Orchestration Mock classes (migrated from production code)
from .orchestration import (
    # Mock Classes
    MockSemanticRouter,
    MockLLMClassifier,
    MockCompletenessChecker,
    MockBusinessIntentRouter,
    MockQuestionGenerator,
    MockLLMClient,
    MockConversationContextManager,
    MockGuidedDialogEngine,
    MockSchemaValidator,
    MockBaseHandler,
    MockServiceNowHandler,
    MockPrometheusHandler,
    MockUserInputHandler,
    MockInputGateway,
    MockNotificationService,
    # Factory Functions
    create_mock_router,
    create_mock_dialog_engine,
    create_mock_context_manager,
    create_mock_generator,
    create_mock_llm_generator,
    create_mock_checker,
    create_mock_gateway,
    create_mock_hitl_controller,
)

# Sprint 112: LLM Mock class (migrated from production code)
from .llm import MockLLMService

__all__ = [
    # Agent Framework Mocks
    "MockExecutor",
    "MockWorkflowContext",
    "MockCheckpointStorage",
    "MockWorkflow",
    "MockWorkflowRunResult",
    "create_test_workflow",
    "create_test_executor",
    "create_test_checkpoint",
    "assert_workflow_result",
    # Orchestration Mocks (Sprint 112)
    "MockSemanticRouter",
    "MockLLMClassifier",
    "MockCompletenessChecker",
    "MockBusinessIntentRouter",
    "MockQuestionGenerator",
    "MockLLMClient",
    "MockConversationContextManager",
    "MockGuidedDialogEngine",
    "MockSchemaValidator",
    "MockBaseHandler",
    "MockServiceNowHandler",
    "MockPrometheusHandler",
    "MockUserInputHandler",
    "MockInputGateway",
    "MockNotificationService",
    "create_mock_router",
    "create_mock_dialog_engine",
    "create_mock_context_manager",
    "create_mock_generator",
    "create_mock_llm_generator",
    "create_mock_checker",
    "create_mock_gateway",
    "create_mock_hitl_controller",
    # LLM Mock (Sprint 112)
    "MockLLMService",
]
