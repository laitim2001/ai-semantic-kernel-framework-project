"""
Code Interpreter Assistant 模組

提供 Azure OpenAI Assistants API 整合，支援 Code Interpreter 功能。

主要組件:
- AssistantManagerService: 管理 Assistants 和執行代碼
- CodeExecutionResult: 執行結果數據類
- AssistantConfig: 配置類

Example:
    ```python
    from src.integrations.agent_framework.assistant import (
        AssistantManagerService,
        AssistantConfig,
        CodeExecutionResult,
    )

    # 創建服務
    manager = AssistantManagerService()

    # 創建 Assistant
    assistant = manager.create_assistant(
        name="CodeRunner",
        instructions="Execute Python code accurately.",
    )

    # 執行代碼
    result = manager.execute_code(
        assistant_id=assistant.id,
        code="print(2 + 2)"
    )

    print(result.output)  # "4"

    # 清理
    manager.delete_assistant(assistant.id)
    ```
"""

from .models import (
    CodeExecutionResult,
    ExecutionStatus,
    AssistantConfig,
    AssistantInfo,
    ThreadMessage,
    FileInfo,
)

from .exceptions import (
    AssistantError,
    ExecutionTimeoutError,
    AssistantNotFoundError,
    CodeExecutionError,
    AssistantCreationError,
    ThreadCreationError,
    RunError,
    ConfigurationError,
    RateLimitError,
)

from .manager import AssistantManagerService

# Sprint 38: File Storage Service
from .files import (
    FileStorageService,
    FileInfo as StoredFileInfo,
    get_file_service,
)

__all__ = [
    # Models
    "CodeExecutionResult",
    "ExecutionStatus",
    "AssistantConfig",
    "AssistantInfo",
    "ThreadMessage",
    "FileInfo",
    # Exceptions
    "AssistantError",
    "ExecutionTimeoutError",
    "AssistantNotFoundError",
    "CodeExecutionError",
    "AssistantCreationError",
    "ThreadCreationError",
    "RunError",
    "ConfigurationError",
    "RateLimitError",
    # Services
    "AssistantManagerService",
    # Sprint 38: File Storage
    "FileStorageService",
    "StoredFileInfo",
    "get_file_service",
]
