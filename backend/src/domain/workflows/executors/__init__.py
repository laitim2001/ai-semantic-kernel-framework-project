# =============================================================================
# IPA Platform - Workflow Executors Module
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Workflow executor implementations providing:
#   - ApprovalGateway: Human approval step executor
#   - HumanApprovalRequest: Approval request data structure
#   - ConcurrentExecutor: Parallel task execution (Phase 2)
#   - ConcurrentStateManager: Parallel state management (Phase 2)
#
# Executors handle specific node types in workflow execution.
# =============================================================================

from src.domain.workflows.executors.approval import (
    ApprovalGateway,
    HumanApprovalRequest,
    ApprovalResponse,
)

from src.domain.workflows.executors.concurrent import (
    ConcurrentExecutor,
    ConcurrentMode,
    ConcurrentTask,
    ConcurrentResult,
    create_all_executor,
    create_any_executor,
    create_majority_executor,
    create_first_success_executor,
)

from src.domain.workflows.executors.concurrent_state import (
    BranchStatus,
    ParallelBranch,
    ConcurrentExecutionState,
    ConcurrentStateManager,
    get_state_manager,
    reset_state_manager,
)

from src.domain.workflows.executors.parallel_gateway import (
    JoinStrategy,
    MergeStrategy,
    ParallelGatewayConfig,
    ForkBranchConfig,
    ParallelForkGateway,
    ParallelJoinGateway,
)

__all__ = [
    # Approval Gateway (Sprint 2)
    "ApprovalGateway",
    "HumanApprovalRequest",
    "ApprovalResponse",
    # Concurrent Executor (Sprint 7)
    "ConcurrentExecutor",
    "ConcurrentMode",
    "ConcurrentTask",
    "ConcurrentResult",
    "create_all_executor",
    "create_any_executor",
    "create_majority_executor",
    "create_first_success_executor",
    # Concurrent State (Sprint 7)
    "BranchStatus",
    "ParallelBranch",
    "ConcurrentExecutionState",
    "ConcurrentStateManager",
    "get_state_manager",
    "reset_state_manager",
    # Parallel Gateway (Sprint 7)
    "JoinStrategy",
    "MergeStrategy",
    "ParallelGatewayConfig",
    "ForkBranchConfig",
    "ParallelForkGateway",
    "ParallelJoinGateway",
]
