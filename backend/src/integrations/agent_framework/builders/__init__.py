"""
Agent Framework Builders - Adapter Implementations

此模組包含各種 Agent Framework Builder 的適配器實現。

模組結構:
    builders/
    ├── __init__.py           # 本文件 - 統一導出
    ├── concurrent.py         # ConcurrentBuilderAdapter (Sprint 14)
    ├── handoff.py            # HandoffBuilderAdapter (Sprint 15)
    ├── groupchat.py          # GroupChatBuilderAdapter (Sprint 16)
    ├── magentic.py           # MagenticBuilderAdapter (Sprint 17)
    └── workflow_executor.py  # WorkflowExecutorAdapter (Sprint 18)

實現進度:
    - Sprint 14: ConcurrentBuilder 重構
    - Sprint 15: HandoffBuilder 重構
    - Sprint 16: GroupChatBuilder 重構
    - Sprint 17: MagenticBuilder 重構
    - Sprint 18: WorkflowExecutor 整合

使用範例 (Sprint 14 完成後):
    from src.integrations.agent_framework.builders import (
        ConcurrentBuilderAdapter,
    )

    adapter = ConcurrentBuilderAdapter(
        id="parallel-workflow",
        executors=[exec1, exec2, exec3],
    )
    workflow = adapter.build()
    result = await adapter.run(input_data)
"""

# Sprint 14: ConcurrentBuilder 適配器
from .concurrent import (
    ConcurrentBuilderAdapter,
    ConcurrentMode,
    ConcurrentTaskConfig,
    TaskResult,
    ConcurrentExecutionResult,
    create_all_concurrent,
    create_any_concurrent,
    create_majority_concurrent,
    create_first_success_concurrent,
)

# Sprint 14: ConcurrentExecutor 遷移層
from .concurrent_migration import (
    ConcurrentExecutorAdapter,
    ConcurrentTask,
    ConcurrentResult,
    BranchStatus,
    ParallelBranch,
    create_all_executor,
    create_any_executor,
    create_majority_executor,
    create_first_success_executor,
    migrate_concurrent_executor,
)

# Sprint 14: FanOut/FanIn Edge Routing
from .edge_routing import (
    Edge,
    EdgeGroup,
    FanOutEdgeGroup,
    FanInEdgeGroup,
    FanOutStrategy,
    FanOutConfig,
    FanOutRouter,
    FanInStrategy,
    FanInConfig,
    FanInAggregator,
    RouteCondition,
    ConditionalRouter,
    create_broadcast_fan_out,
    create_collect_all_fan_in,
    create_parallel_routing,
)

# Sprint 15: HandoffBuilder 適配器
from .handoff import (
    HandoffBuilderAdapter,
    HandoffMode,
    HandoffStatus,
    HandoffRoute,
    HandoffParticipant,
    UserInputRequest,
    HandoffExecutionResult,
    create_handoff_adapter,
    create_autonomous_handoff,
    create_human_in_loop_handoff,
)

# Sprint 15: HandoffController 遷移層
from .handoff_migration import (
    HandoffControllerAdapter,
    HandoffPolicyLegacy,
    HandoffStatusLegacy,
    HandoffContextLegacy,
    HandoffRequestLegacy,
    HandoffResultLegacy,
    convert_status_to_legacy,
    convert_status_from_legacy,
    convert_policy_to_mode,
    migrate_handoff_controller,
    create_handoff_controller_adapter,
)

# Sprint 15: Handoff HITL (Human-in-the-Loop)
from .handoff_hitl import (
    HITLSessionStatus,
    HITLInputType,
    HITLInputRequest,
    HITLInputResponse,
    HITLSession,
    HITLCallback,
    DefaultHITLCallback,
    HITLManager,
    HITLCheckpointAdapter,
    create_hitl_manager,
    create_hitl_checkpoint_adapter,
)

# Sprint 16: GroupChatBuilder 適配器
# from .groupchat import GroupChatBuilderAdapter

# Sprint 17: MagenticBuilder 適配器
# from .magentic import MagenticBuilderAdapter

# Sprint 18: WorkflowExecutor 適配器
# from .workflow_executor import WorkflowExecutorAdapter

__all__ = [
    # Sprint 14: ConcurrentBuilder 適配器
    "ConcurrentBuilderAdapter",
    "ConcurrentMode",
    "ConcurrentTaskConfig",
    "TaskResult",
    "ConcurrentExecutionResult",
    "create_all_concurrent",
    "create_any_concurrent",
    "create_majority_concurrent",
    "create_first_success_concurrent",
    # Sprint 14: ConcurrentExecutor 遷移層
    "ConcurrentExecutorAdapter",
    "ConcurrentTask",
    "ConcurrentResult",
    "BranchStatus",
    "ParallelBranch",
    "create_all_executor",
    "create_any_executor",
    "create_majority_executor",
    "create_first_success_executor",
    "migrate_concurrent_executor",
    # Sprint 14: FanOut/FanIn Edge Routing
    "Edge",
    "EdgeGroup",
    "FanOutEdgeGroup",
    "FanInEdgeGroup",
    "FanOutStrategy",
    "FanOutConfig",
    "FanOutRouter",
    "FanInStrategy",
    "FanInConfig",
    "FanInAggregator",
    "RouteCondition",
    "ConditionalRouter",
    "create_broadcast_fan_out",
    "create_collect_all_fan_in",
    "create_parallel_routing",
    # Sprint 15: HandoffBuilder 適配器
    "HandoffBuilderAdapter",
    "HandoffMode",
    "HandoffStatus",
    "HandoffRoute",
    "HandoffParticipant",
    "UserInputRequest",
    "HandoffExecutionResult",
    "create_handoff_adapter",
    "create_autonomous_handoff",
    "create_human_in_loop_handoff",
    # Sprint 15: HandoffController 遷移層
    "HandoffControllerAdapter",
    "HandoffPolicyLegacy",
    "HandoffStatusLegacy",
    "HandoffContextLegacy",
    "HandoffRequestLegacy",
    "HandoffResultLegacy",
    "convert_status_to_legacy",
    "convert_status_from_legacy",
    "convert_policy_to_mode",
    "migrate_handoff_controller",
    "create_handoff_controller_adapter",
    # Sprint 15: Handoff HITL (Human-in-the-Loop)
    "HITLSessionStatus",
    "HITLInputType",
    "HITLInputRequest",
    "HITLInputResponse",
    "HITLSession",
    "HITLCallback",
    "DefaultHITLCallback",
    "HITLManager",
    "HITLCheckpointAdapter",
    "create_hitl_manager",
    "create_hitl_checkpoint_adapter",
    # Sprint 16: GroupChatBuilder 適配器
    # "GroupChatBuilderAdapter",
    # Sprint 17: MagenticBuilder 適配器
    # "MagenticBuilderAdapter",
    # Sprint 18: WorkflowExecutor 適配器
    # "WorkflowExecutorAdapter",
]
