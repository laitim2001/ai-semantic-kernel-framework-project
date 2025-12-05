"""
Agent Framework Integration Layer

提供與 Microsoft Agent Framework 的整合介面。
此模組作為適配層，隔離 Agent Framework API 變更的影響。

架構概念:
┌─────────────────────────────────────────────────────────────────┐
│                    IPA Platform 應用層                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │               Adapter Layer (本模組)                        ││
│  │  - ConcurrentBuilderAdapter                                 ││
│  │  - GroupChatBuilderAdapter                                  ││
│  │  - HandoffBuilderAdapter                                    ││
│  │  - MagenticBuilderAdapter                                   ││
│  │  - WorkflowExecutorAdapter                                  ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Agent Framework Core API                       ││
│  │  ConcurrentBuilder, GroupChatBuilder, HandoffBuilder,       ││
│  │  MagenticBuilder, WorkflowExecutor, CheckpointStorage       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

使用範例:
    from src.integrations.agent_framework import (
        WorkflowAdapter,
        WorkflowConfig,
    )

    config = WorkflowConfig(id="my-workflow", name="My Workflow")
    adapter = WorkflowAdapter(config)
    adapter.add_executor(my_executor)
    workflow = adapter.build()
    result = await workflow.run(input_data)

版本相容性:
    - Agent Framework: >= 0.1.0 (Preview)
    - Python: >= 3.11

模組結構:
    agent_framework/
    ├── __init__.py           # 本文件 - 統一導出
    ├── base.py               # 基礎適配器類
    ├── exceptions.py         # 自定義異常
    ├── workflow.py           # WorkflowAdapter
    ├── checkpoint.py         # CheckpointStorage 適配器
    └── builders/             # 各種 Builder 適配器
        ├── __init__.py
        ├── concurrent.py     # Sprint 14
        ├── handoff.py        # Sprint 15
        ├── groupchat.py      # Sprint 16
        ├── magentic.py       # Sprint 17
        └── workflow_executor.py  # Sprint 18
"""

__version__ = "0.1.0"
__agent_framework_version__ = "0.1.0-preview"

# Base classes
from .base import (
    BaseAdapter,
    BuilderAdapter,
)

# Exceptions
from .exceptions import (
    AdapterError,
    AdapterInitializationError,
    WorkflowBuildError,
    ExecutionError,
    CheckpointError,
)

# Workflow adapter
from .workflow import (
    WorkflowAdapter,
    WorkflowConfig,
)

# Checkpoint storage (將在 S13-3 完善)
from .checkpoint import (
    CheckpointStorageAdapter,
    PostgresCheckpointStorage,
    RedisCheckpointCache,
    CachedCheckpointStorage,
)

# Builder adapters (Sprint 14-18 逐步實現)
from .builders import (
    # Sprint 14: ConcurrentBuilder 適配器
    ConcurrentBuilderAdapter,
    ConcurrentMode,
    ConcurrentTaskConfig,
    TaskResult,
    ConcurrentExecutionResult,
    create_all_concurrent,
    create_any_concurrent,
    create_majority_concurrent,
    create_first_success_concurrent,
    # Sprint 14: ConcurrentExecutor 遷移層
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
    # Sprint 15: HandoffBuilder 適配器 (待實現)
    # HandoffBuilderAdapter,
    # Sprint 16: GroupChatBuilder 適配器 (待實現)
    # GroupChatBuilderAdapter,
    # Sprint 17: MagenticBuilder 適配器 (待實現)
    # MagenticBuilderAdapter,
    # Sprint 18: WorkflowExecutor 適配器 (待實現)
    # WorkflowExecutorAdapter,
)

__all__ = [
    # Version info
    "__version__",
    "__agent_framework_version__",
    # Base classes
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
    # Checkpoint
    "CheckpointStorageAdapter",
    "PostgresCheckpointStorage",
    "RedisCheckpointCache",
    "CachedCheckpointStorage",
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
]
