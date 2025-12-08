"""
Agent Framework Builders - Adapter Implementations

此模組包含各種 Agent Framework Builder 的適配器實現。

模組結構:
    builders/
    ├── __init__.py           # 本文件 - 統一導出
    ├── concurrent.py         # ConcurrentBuilderAdapter (Sprint 14)
    ├── handoff.py            # HandoffBuilderAdapter (Sprint 15)
    ├── handoff_policy.py     # HandoffPolicyAdapter (Sprint 21 S21-1)
    ├── handoff_capability.py # CapabilityMatcherAdapter (Sprint 21 S21-2)
    ├── handoff_context.py    # ContextTransferAdapter (Sprint 21 S21-3)
    ├── handoff_service.py    # HandoffService (Sprint 21 S21-4)
    ├── groupchat.py          # GroupChatBuilderAdapter (Sprint 16)
    ├── groupchat_voting.py   # GroupChatVotingAdapter (Sprint 20)
    ├── magentic.py           # MagenticBuilderAdapter (Sprint 17)
    ├── workflow_executor.py  # WorkflowExecutorAdapter (Sprint 18)
    ├── nested_workflow.py    # NestedWorkflowAdapter (Sprint 23)
    └── planning.py           # PlanningAdapter (Sprint 24)

    multiturn/                # MultiTurn 模組 (Sprint 24)
    ├── __init__.py           # 統一導出
    ├── adapter.py            # MultiTurnAdapter
    └── checkpoint_storage.py # CheckpointStorage 實現

實現進度:
    - Sprint 14: ConcurrentBuilder 重構
    - Sprint 15: HandoffBuilder 重構
    - Sprint 16: GroupChatBuilder 重構
    - Sprint 17: MagenticBuilder 重構
    - Sprint 18: WorkflowExecutor 整合
    - Sprint 20: GroupChatVotingAdapter 投票擴展
    - Sprint 21: Handoff 完整遷移 (政策映射、能力匹配、上下文傳輸)
    - Sprint 23: NestedWorkflow 適配器
    - Sprint 24: Planning & Multi-turn 整合

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
# Sprint 22: Gateway 整合擴展
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
    # Sprint 22: Gateway 類型和配置
    GatewayType,
    JoinCondition,
    MergeStrategy,
    GatewayConfig,
    NOfMAggregator,
    MergeStrategyAggregator,
    # Sprint 22: Gateway 工廠函數
    create_parallel_split_gateway,
    create_parallel_join_gateway,
    create_n_of_m_gateway,
    create_inclusive_gateway,
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
# Sprint 20: 添加 PRIORITY 和 EXPERTISE 選擇方法，終止條件整合
from .groupchat import (
    GroupChatBuilderAdapter,
    GroupChatParticipant,
    GroupChatMessage,
    GroupChatState,
    GroupChatTurn,
    GroupChatResult,
    GroupChatStatus,
    SpeakerSelectionMethod,
    MessageRole,
    SpeakerSelectionResult,
    create_groupchat_adapter,
    create_round_robin_chat,
    create_auto_managed_chat,
    create_custom_selector_chat,
    create_round_robin_selector,
    create_random_selector,
    create_last_speaker_different_selector,
    # Sprint 20: S20-2 新增選擇器
    create_priority_selector,
    create_expertise_selector,
    create_priority_chat,
    create_expertise_chat,
    # Sprint 20: S20-3 終止條件
    TerminationType,
    DEFAULT_TERMINATION_KEYWORDS,
    create_max_rounds_termination,
    create_max_messages_termination,
    create_keyword_termination,
    create_timeout_termination,
    create_consensus_termination,
    create_no_progress_termination,
    create_combined_termination,
)

# Sprint 20: S20-4 GroupChatVotingAdapter 投票系統擴展
from .groupchat_voting import (
    GroupChatVotingAdapter,
    VotingMethod,
    VotingStatus,
    VotingConfig,
    Vote,
    VotingResult,
    create_voting_selector,
    create_majority_selector,
    create_unanimous_selector,
    create_ranked_selector,
    create_weighted_selector,
    create_approval_selector,
    create_voting_chat,
    create_majority_voting_chat,
    create_unanimous_voting_chat,
    create_ranked_voting_chat,
)

# Sprint 16: GroupChatOrchestrator (S16-3 & S16-4)
from .groupchat_orchestrator import (
    ManagerSelectionRequest,
    ManagerSelectionResponse,
    GroupChatDirective,
    OrchestratorState,
    OrchestratorPhase,
    GroupChatOrchestrator,
    create_orchestrator,
    create_manager_selection_request,
    create_manager_selection_response,
)

# Sprint 16: GroupChatManager 遷移層
from .groupchat_migration import (
    GroupChatManagerAdapter,
    GroupParticipantLegacy,
    GroupMessageLegacy,
    GroupChatContextLegacy,
    GroupChatResultLegacy,
    SpeakerSelectionMethodLegacy,
    GroupChatStateLegacy,
    convert_selection_method_to_new,
    convert_selection_method_from_new,
    convert_state_to_legacy,
    convert_state_from_legacy,
    convert_participant_to_new,
    convert_participant_from_new,
    convert_message_to_new,
    convert_message_from_new,
    convert_result_to_legacy,
    migrate_groupchat_manager,
    create_groupchat_manager_adapter,
    create_priority_chat_manager,
    create_weighted_chat_manager,
    create_priority_selector,
    create_weighted_selector,
)

# Sprint 17: MagenticBuilder 適配器 (Magentic One)
from .magentic import (
    MagenticBuilderAdapter,
    MagenticManagerBase,
    StandardMagenticManager,
    MagenticStatus,
    HumanInterventionKind,
    HumanInterventionDecision,
    MagenticMessage,
    MagenticParticipant,
    MagenticContext,
    TaskLedger,
    ProgressLedger,
    ProgressLedgerItem,
    HumanInterventionRequest,
    HumanInterventionReply,
    MagenticRound,
    MagenticResult,
    MAGENTIC_MANAGER_NAME,
    create_magentic_adapter,
    create_research_workflow,
    create_coding_workflow,
)

# Sprint 17: MagenticBuilder 遷移層
from .magentic_migration import (
    MagenticManagerAdapter,
    HumanInterventionHandler,
    DynamicPlannerStateLegacy,
    PlannerActionTypeLegacy,
    PlanStepLegacy,
    DynamicPlanLegacy,
    ProgressEvaluationLegacy,
    DynamicPlannerContextLegacy,
    DynamicPlannerResultLegacy,
    convert_legacy_state_to_magentic,
    convert_magentic_status_to_legacy,
    convert_legacy_context_to_magentic,
    convert_magentic_context_to_legacy,
    convert_legacy_plan_to_task_ledger,
    convert_task_ledger_to_legacy_plan,
    convert_legacy_progress_to_ledger,
    convert_progress_ledger_to_legacy,
    convert_magentic_result_to_legacy,
    migrate_dynamic_planner,
    create_intervention_handler,
)

# Sprint 18: WorkflowExecutor 適配器
from .workflow_executor import (
    WorkflowExecutorAdapter,
    WorkflowExecutorStatus,
    WorkflowRunState,
    RequestInfoEvent,
    SubWorkflowRequestMessage,
    SubWorkflowResponseMessage,
    ExecutionContext,
    WorkflowOutput,
    WorkflowRunResult,
    WorkflowExecutorResult,
    WorkflowProtocol,
    SimpleWorkflow,
    create_workflow_executor,
    create_simple_workflow,
    create_nested_workflow_executor,
)

# Sprint 18: WorkflowExecutor 遷移層
from .workflow_executor_migration import (
    NestedWorkflowTypeLegacy,
    WorkflowScopeLegacy,
    NestedExecutionStatusLegacy,
    NestedWorkflowConfigLegacy,
    SubWorkflowReferenceLegacy,
    NestedExecutionContextLegacy,
    NestedWorkflowResultLegacy,
    convert_legacy_status_to_executor,
    convert_executor_status_to_legacy,
    convert_legacy_context_to_execution,
    convert_execution_to_legacy_context,
    convert_legacy_config_to_executor_config,
    convert_executor_config_to_legacy,
    convert_executor_result_to_legacy,
    convert_legacy_result_to_executor,
    convert_sub_workflow_reference_to_executor,
    NestedWorkflowManagerAdapter,
    migrate_nested_workflow_manager,
    create_nested_executor_from_legacy,
    create_migration_context,
)

# Sprint 21: S21-1 Handoff 政策映射層
from .handoff_policy import (
    LegacyHandoffPolicy,
    AdaptedPolicyConfig,
    HandoffPolicyAdapter,
    create_keyword_condition,
    create_round_limit_condition,
    create_composite_condition,
    adapt_policy,
    adapt_immediate,
    adapt_graceful,
    adapt_conditional,
    adapt_conditional_with_keywords,
)

# Sprint 21: S21-2 Handoff 能力匹配適配器
from .handoff_capability import (
    CapabilityCategory,
    AgentStatus,
    MatchStrategy,
    AgentCapabilityInfo,
    CapabilityRequirementInfo,
    AgentAvailabilityInfo,
    CapabilityMatchResult,
    BUILTIN_CAPABILITIES,
    CapabilityMatcherAdapter,
    create_capability_matcher,
    create_capability_requirement,
    create_agent_capability,
)

# Sprint 21: S21-3 Handoff 上下文傳輸適配器
from .handoff_context import (
    ContextTransferError,
    ContextValidationError,
    TransferContextInfo,
    TransformationRuleInfo,
    TransferResult,
    ContextTransferAdapter,
    create_context_transfer_adapter,
    create_transfer_context,
    create_transformation_rule,
)

# Sprint 21: S21-4 Handoff 服務整合層
from .handoff_service import (
    HandoffServiceStatus,
    HandoffRequest as ServiceHandoffRequest,
    HandoffRecord,
    HandoffTriggerResult,
    HandoffStatusResult,
    HandoffCancelResult,
    HandoffService,
    create_handoff_service,
)

# Sprint 23: NestedWorkflow 適配器
from .nested_workflow import (
    NestedWorkflowAdapter,
    ContextPropagationStrategy,
    ExecutionMode,
    RecursionStatus,
    ContextConfig,
    RecursionConfig,
    RecursionState,
    SubWorkflowInfo,
    NestedExecutionResult,
    ContextPropagator,
    RecursiveDepthController,
    create_nested_workflow_adapter,
    create_sequential_nested_workflow,
    create_parallel_nested_workflow,
    create_conditional_nested_workflow,
)

# Sprint 24: S24-2 PlanningAdapter (Planning 整合)
from .planning import (
    PlanningAdapter,
    DecompositionStrategy,
    PlanningMode,
    PlanStatus,
    DecisionRule,
    PlanningConfig,
    PlanningResult,
    create_planning_adapter,
    create_simple_planner,
    create_decomposed_planner,
    create_full_planner,
)

# Sprint 31: S31-2 AgentExecutorAdapter (Agent 執行器整合)
from .agent_executor import (
    AgentExecutorAdapter,
    AgentExecutorConfig,
    AgentExecutorResult,
    create_agent_executor_adapter,
    create_initialized_adapter,
    get_agent_executor_adapter,
    set_agent_executor_adapter,
)

# Sprint 24: S24-3 MultiTurnAdapter (Multi-turn 整合)
from ..multiturn import (
    MultiTurnAdapter,
    TurnResult,
    SessionState,
    create_multiturn_adapter,
    create_redis_multiturn_adapter,
    # Checkpoint 存儲
    RedisCheckpointStorage,
    PostgresCheckpointStorage,
    FileCheckpointStorage,
)

__all__ = [
    # Sprint 14: ConcurrentBuilder 適配器
    # Sprint 22: Gateway 整合擴展
    "ConcurrentBuilderAdapter",
    "ConcurrentMode",
    "ConcurrentTaskConfig",
    "TaskResult",
    "ConcurrentExecutionResult",
    "create_all_concurrent",
    "create_any_concurrent",
    "create_majority_concurrent",
    "create_first_success_concurrent",
    # Sprint 22: Gateway 類型和配置
    "GatewayType",
    "JoinCondition",
    "MergeStrategy",
    "GatewayConfig",
    "NOfMAggregator",
    "MergeStrategyAggregator",
    # Sprint 22: Gateway 工廠函數
    "create_parallel_split_gateway",
    "create_parallel_join_gateway",
    "create_n_of_m_gateway",
    "create_inclusive_gateway",
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
    # Sprint 20: 添加 PRIORITY 和 EXPERTISE 選擇方法，終止條件整合
    "GroupChatBuilderAdapter",
    "GroupChatParticipant",
    "GroupChatMessage",
    "GroupChatState",
    "GroupChatTurn",
    "GroupChatResult",
    "GroupChatStatus",
    "SpeakerSelectionMethod",
    "MessageRole",
    "SpeakerSelectionResult",
    "create_groupchat_adapter",
    "create_round_robin_chat",
    "create_auto_managed_chat",
    "create_custom_selector_chat",
    "create_round_robin_selector",
    "create_random_selector",
    "create_last_speaker_different_selector",
    # Sprint 20: S20-2 新增選擇器
    "create_priority_selector",
    "create_expertise_selector",
    "create_priority_chat",
    "create_expertise_chat",
    # Sprint 20: S20-3 終止條件
    "TerminationType",
    "DEFAULT_TERMINATION_KEYWORDS",
    "create_max_rounds_termination",
    "create_max_messages_termination",
    "create_keyword_termination",
    "create_timeout_termination",
    "create_consensus_termination",
    "create_no_progress_termination",
    "create_combined_termination",
    # Sprint 20: S20-4 GroupChatVotingAdapter 投票系統擴展
    "GroupChatVotingAdapter",
    "VotingMethod",
    "VotingStatus",
    "VotingConfig",
    "Vote",
    "VotingResult",
    "create_voting_selector",
    "create_majority_selector",
    "create_unanimous_selector",
    "create_ranked_selector",
    "create_weighted_selector",
    "create_approval_selector",
    "create_voting_chat",
    "create_majority_voting_chat",
    "create_unanimous_voting_chat",
    "create_ranked_voting_chat",
    # Sprint 16: GroupChatOrchestrator (S16-3 & S16-4)
    "ManagerSelectionRequest",
    "ManagerSelectionResponse",
    "GroupChatDirective",
    "OrchestratorState",
    "OrchestratorPhase",
    "GroupChatOrchestrator",
    "create_orchestrator",
    "create_manager_selection_request",
    "create_manager_selection_response",
    # Sprint 16: GroupChatManager 遷移層
    "GroupChatManagerAdapter",
    "GroupParticipantLegacy",
    "GroupMessageLegacy",
    "GroupChatContextLegacy",
    "GroupChatResultLegacy",
    "SpeakerSelectionMethodLegacy",
    "GroupChatStateLegacy",
    "convert_selection_method_to_new",
    "convert_selection_method_from_new",
    "convert_state_to_legacy",
    "convert_state_from_legacy",
    "convert_participant_to_new",
    "convert_participant_from_new",
    "convert_message_to_new",
    "convert_message_from_new",
    "convert_result_to_legacy",
    "migrate_groupchat_manager",
    "create_groupchat_manager_adapter",
    "create_priority_chat_manager",
    "create_weighted_chat_manager",
    "create_priority_selector",
    "create_weighted_selector",
    # Sprint 17: MagenticBuilder 適配器 (Magentic One)
    "MagenticBuilderAdapter",
    "MagenticManagerBase",
    "StandardMagenticManager",
    "MagenticStatus",
    "HumanInterventionKind",
    "HumanInterventionDecision",
    "MagenticMessage",
    "MagenticParticipant",
    "MagenticContext",
    "TaskLedger",
    "ProgressLedger",
    "ProgressLedgerItem",
    "HumanInterventionRequest",
    "HumanInterventionReply",
    "MagenticRound",
    "MagenticResult",
    "MAGENTIC_MANAGER_NAME",
    "create_magentic_adapter",
    "create_research_workflow",
    "create_coding_workflow",
    # Sprint 17: MagenticBuilder 遷移層
    "MagenticManagerAdapter",
    "HumanInterventionHandler",
    "DynamicPlannerStateLegacy",
    "PlannerActionTypeLegacy",
    "PlanStepLegacy",
    "DynamicPlanLegacy",
    "ProgressEvaluationLegacy",
    "DynamicPlannerContextLegacy",
    "DynamicPlannerResultLegacy",
    "convert_legacy_state_to_magentic",
    "convert_magentic_status_to_legacy",
    "convert_legacy_context_to_magentic",
    "convert_magentic_context_to_legacy",
    "convert_legacy_plan_to_task_ledger",
    "convert_task_ledger_to_legacy_plan",
    "convert_legacy_progress_to_ledger",
    "convert_progress_ledger_to_legacy",
    "convert_magentic_result_to_legacy",
    "migrate_dynamic_planner",
    "create_intervention_handler",
    # Sprint 18: WorkflowExecutor 適配器
    "WorkflowExecutorAdapter",
    "WorkflowExecutorStatus",
    "WorkflowRunState",
    "RequestInfoEvent",
    "SubWorkflowRequestMessage",
    "SubWorkflowResponseMessage",
    "ExecutionContext",
    "WorkflowOutput",
    "WorkflowRunResult",
    "WorkflowExecutorResult",
    "WorkflowProtocol",
    "SimpleWorkflow",
    "create_workflow_executor",
    "create_simple_workflow",
    "create_nested_workflow_executor",
    # Sprint 18: WorkflowExecutor 遷移層
    "NestedWorkflowTypeLegacy",
    "WorkflowScopeLegacy",
    "NestedExecutionStatusLegacy",
    "NestedWorkflowConfigLegacy",
    "SubWorkflowReferenceLegacy",
    "NestedExecutionContextLegacy",
    "NestedWorkflowResultLegacy",
    "convert_legacy_status_to_executor",
    "convert_executor_status_to_legacy",
    "convert_legacy_context_to_execution",
    "convert_execution_to_legacy_context",
    "convert_legacy_config_to_executor_config",
    "convert_executor_config_to_legacy",
    "convert_executor_result_to_legacy",
    "convert_legacy_result_to_executor",
    "convert_sub_workflow_reference_to_executor",
    "NestedWorkflowManagerAdapter",
    "migrate_nested_workflow_manager",
    "create_nested_executor_from_legacy",
    "create_migration_context",
    # Sprint 21: S21-1 Handoff 政策映射層
    "LegacyHandoffPolicy",
    "AdaptedPolicyConfig",
    "HandoffPolicyAdapter",
    "create_keyword_condition",
    "create_round_limit_condition",
    "create_composite_condition",
    "adapt_policy",
    "adapt_immediate",
    "adapt_graceful",
    "adapt_conditional",
    "adapt_conditional_with_keywords",
    # Sprint 21: S21-2 Handoff 能力匹配適配器
    "CapabilityCategory",
    "AgentStatus",
    "MatchStrategy",
    "AgentCapabilityInfo",
    "CapabilityRequirementInfo",
    "AgentAvailabilityInfo",
    "CapabilityMatchResult",
    "BUILTIN_CAPABILITIES",
    "CapabilityMatcherAdapter",
    "create_capability_matcher",
    "create_capability_requirement",
    "create_agent_capability",
    # Sprint 21: S21-3 Handoff 上下文傳輸適配器
    "ContextTransferError",
    "ContextValidationError",
    "TransferContextInfo",
    "TransformationRuleInfo",
    "TransferResult",
    "ContextTransferAdapter",
    "create_context_transfer_adapter",
    "create_transfer_context",
    "create_transformation_rule",
    # Sprint 21: S21-4 Handoff 服務整合層
    "HandoffServiceStatus",
    "ServiceHandoffRequest",
    "HandoffRecord",
    "HandoffTriggerResult",
    "HandoffStatusResult",
    "HandoffCancelResult",
    "HandoffService",
    "create_handoff_service",
    # Sprint 23: NestedWorkflow 適配器
    "NestedWorkflowAdapter",
    "ContextPropagationStrategy",
    "ExecutionMode",
    "RecursionStatus",
    "ContextConfig",
    "RecursionConfig",
    "RecursionState",
    "SubWorkflowInfo",
    "NestedExecutionResult",
    "ContextPropagator",
    "RecursiveDepthController",
    "create_nested_workflow_adapter",
    "create_sequential_nested_workflow",
    "create_parallel_nested_workflow",
    "create_conditional_nested_workflow",
    # Sprint 24: S24-2 PlanningAdapter (Planning 整合)
    "PlanningAdapter",
    "DecompositionStrategy",
    "PlanningMode",
    "PlanStatus",
    "DecisionRule",
    "PlanningConfig",
    "PlanningResult",
    "create_planning_adapter",
    "create_simple_planner",
    "create_decomposed_planner",
    "create_full_planner",
    # Sprint 24: S24-3 MultiTurnAdapter (Multi-turn 整合)
    "MultiTurnAdapter",
    "TurnResult",
    "SessionState",
    "create_multiturn_adapter",
    "create_redis_multiturn_adapter",
    "RedisCheckpointStorage",
    "PostgresCheckpointStorage",
    "FileCheckpointStorage",
    # Sprint 31: S31-2 AgentExecutorAdapter (Agent 執行器整合)
    "AgentExecutorAdapter",
    "AgentExecutorConfig",
    "AgentExecutorResult",
    "create_agent_executor_adapter",
    "create_initialized_adapter",
    "get_agent_executor_adapter",
    "set_agent_executor_adapter",
]
