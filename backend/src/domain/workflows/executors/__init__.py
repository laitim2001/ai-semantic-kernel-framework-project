# =============================================================================
# IPA Platform - Workflow Executors Module
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
# Sprint 7: Concurrent Execution Engine (Phase 2)
# Sprint 25: 清理和棄用警告
#
# DEPRECATED: Concurrent 相關類已遷移到適配器層
#
# 推薦使用:
#   from src.integrations.agent_framework.builders import (
#       ConcurrentBuilderAdapter,
#       ConcurrentExecutorAdapter,
#   )
#
# 或使用 API 服務:
#   from src.api.v1.concurrent.adapter_service import ConcurrentAPIService
#
# 保留的功能:
#   - ApprovalGateway: Human approval step executor (核心功能)
#
# 已棄用 (將在未來版本移除):
#   - ConcurrentExecutor -> ConcurrentBuilderAdapter
#   - ConcurrentStateManager -> 適配器內部狀態管理
#   - ParallelGateway -> ConcurrentBuilderAdapter.fan_out/fan_in
# =============================================================================

import warnings

from src.domain.workflows.executors.approval import (
    ApprovalGateway,
    HumanApprovalRequest,
    ApprovalResponse,
)

# 以下導入標記為棄用，請使用適配器替代
warnings.warn(
    "domain.workflows.executors 中的 Concurrent 相關類已棄用。"
    "請使用 integrations.agent_framework.builders.ConcurrentBuilderAdapter",
    DeprecationWarning,
    stacklevel=2,
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
