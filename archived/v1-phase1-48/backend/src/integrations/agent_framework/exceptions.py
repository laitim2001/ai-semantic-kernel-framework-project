"""
Agent Framework Integration - Custom Exceptions

定義 Agent Framework 整合層的自定義異常類別。
這些異常提供清晰的錯誤分類和上下文信息，便於調試和錯誤處理。

異常層次:
    AdapterError (基礎異常)
    ├── AdapterInitializationError  # 初始化失敗
    ├── WorkflowBuildError          # 工作流構建失敗
    ├── ExecutionError              # 執行失敗
    └── CheckpointError             # 檢查點操作失敗

使用範例:
    try:
        workflow = adapter.build()
    except WorkflowBuildError as e:
        logger.error(f"Build failed: {e.message}")
        logger.debug(f"Context: {e.context}")
"""

from typing import Any, Dict, Optional


class AdapterError(Exception):
    """
    Agent Framework 適配器的基礎異常類。

    所有適配器相關的異常都應該繼承自此類。

    Attributes:
        message: 錯誤訊息
        context: 額外的上下文信息字典
        original_error: 原始異常（如果有）

    Example:
        raise AdapterError(
            "Operation failed",
            context={"adapter": "ConcurrentBuilder", "input": data},
            original_error=original_exception
        )
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化異常。

        Args:
            message: 錯誤訊息
            context: 可選的上下文信息字典
            original_error: 可選的原始異常
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_error = original_error

    def __str__(self) -> str:
        parts = [self.message]
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"[Context: {context_str}]")
        if self.original_error:
            parts.append(f"[Caused by: {type(self.original_error).__name__}: {self.original_error}]")
        return " ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"context={self.context!r}, "
            f"original_error={self.original_error!r})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        將異常轉換為字典格式。

        用於 API 響應或日誌記錄。

        Returns:
            包含異常信息的字典
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None,
        }


class AdapterInitializationError(AdapterError):
    """
    適配器初始化失敗時拋出的異常。

    當適配器無法完成初始化過程時使用，例如：
    - 缺少必要的配置
    - 無法建立外部連接
    - 依賴服務不可用

    Example:
        raise AdapterInitializationError(
            "Failed to initialize ConcurrentBuilderAdapter",
            context={"reason": "missing required config", "config_key": "max_workers"}
        )
    """

    def __init__(
        self,
        message: str,
        adapter_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化異常。

        Args:
            message: 錯誤訊息
            adapter_name: 失敗的適配器名稱
            context: 可選的上下文信息
            original_error: 可選的原始異常
        """
        ctx = context or {}
        if adapter_name:
            ctx["adapter_name"] = adapter_name
        super().__init__(message, context=ctx, original_error=original_error)
        self.adapter_name = adapter_name


class WorkflowBuildError(AdapterError):
    """
    工作流構建失敗時拋出的異常。

    當 Builder 無法構建有效的工作流時使用，例如：
    - 配置無效
    - 缺少必要的執行器
    - 邊連接不正確
    - 驗證失敗

    Example:
        raise WorkflowBuildError(
            "Failed to build workflow: invalid edge configuration",
            workflow_id="my-workflow",
            context={"source": "executor-1", "target": "non-existent"}
        )
    """

    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化異常。

        Args:
            message: 錯誤訊息
            workflow_id: 失敗的工作流 ID
            context: 可選的上下文信息
            original_error: 可選的原始異常
        """
        ctx = context or {}
        if workflow_id:
            ctx["workflow_id"] = workflow_id
        super().__init__(message, context=ctx, original_error=original_error)
        self.workflow_id = workflow_id


class ExecutionError(AdapterError):
    """
    工作流執行失敗時拋出的異常。

    當工作流在執行過程中遇到錯誤時使用，例如：
    - 執行器錯誤
    - 超時
    - 資源不足
    - 外部服務失敗

    Example:
        raise ExecutionError(
            "Workflow execution failed: timeout",
            workflow_id="my-workflow",
            executor_id="slow-executor",
            context={"timeout_seconds": 30, "elapsed": 35}
        )
    """

    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        executor_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化異常。

        Args:
            message: 錯誤訊息
            workflow_id: 執行的工作流 ID
            executor_id: 失敗的執行器 ID
            context: 可選的上下文信息
            original_error: 可選的原始異常
        """
        ctx = context or {}
        if workflow_id:
            ctx["workflow_id"] = workflow_id
        if executor_id:
            ctx["executor_id"] = executor_id
        super().__init__(message, context=ctx, original_error=original_error)
        self.workflow_id = workflow_id
        self.executor_id = executor_id


class CheckpointError(AdapterError):
    """
    檢查點操作失敗時拋出的異常。

    當檢查點的保存、載入或刪除操作失敗時使用，例如：
    - 存儲不可用
    - 數據序列化失敗
    - 檢查點不存在
    - 權限不足

    Example:
        raise CheckpointError(
            "Failed to save checkpoint: storage full",
            checkpoint_id="cp-123",
            operation="save",
            context={"storage_type": "postgres", "size_bytes": 1000000}
        )
    """

    def __init__(
        self,
        message: str,
        checkpoint_id: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化異常。

        Args:
            message: 錯誤訊息
            checkpoint_id: 檢查點 ID
            operation: 失敗的操作類型 (save/load/delete/list)
            context: 可選的上下文信息
            original_error: 可選的原始異常
        """
        ctx = context or {}
        if checkpoint_id:
            ctx["checkpoint_id"] = checkpoint_id
        if operation:
            ctx["operation"] = operation
        super().__init__(message, context=ctx, original_error=original_error)
        self.checkpoint_id = checkpoint_id
        self.operation = operation


class ValidationError(AdapterError):
    """
    驗證失敗時拋出的異常。

    當工作流配置或輸入數據驗證失敗時使用。

    Example:
        raise ValidationError(
            "Invalid workflow configuration",
            validation_errors=["missing start executor", "cyclic dependency detected"]
        )
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化異常。

        Args:
            message: 錯誤訊息
            validation_errors: 驗證錯誤列表
            context: 可選的上下文信息
            original_error: 可選的原始異常
        """
        ctx = context or {}
        if validation_errors:
            ctx["validation_errors"] = validation_errors
        super().__init__(message, context=ctx, original_error=original_error)
        self.validation_errors = validation_errors or []


class ConfigurationError(AdapterError):
    """
    配置錯誤時拋出的異常。

    當適配器配置無效或缺失時使用。

    Example:
        raise ConfigurationError(
            "Missing required configuration",
            missing_keys=["api_key", "endpoint"],
            config_source="environment"
        )
    """

    def __init__(
        self,
        message: str,
        missing_keys: Optional[list] = None,
        invalid_keys: Optional[Dict[str, str]] = None,
        config_source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化異常。

        Args:
            message: 錯誤訊息
            missing_keys: 缺失的配置鍵列表
            invalid_keys: 無效配置鍵及原因的字典
            config_source: 配置來源描述
            context: 可選的上下文信息
            original_error: 可選的原始異常
        """
        ctx = context or {}
        if missing_keys:
            ctx["missing_keys"] = missing_keys
        if invalid_keys:
            ctx["invalid_keys"] = invalid_keys
        if config_source:
            ctx["config_source"] = config_source
        super().__init__(message, context=ctx, original_error=original_error)
        self.missing_keys = missing_keys or []
        self.invalid_keys = invalid_keys or {}
        self.config_source = config_source


class RecursionError(AdapterError):
    """
    遞歸深度超過限制時拋出的異常。

    當嵌套工作流的遞歸深度超過配置的最大值時使用。

    Example:
        raise RecursionError(
            "Maximum recursion depth exceeded",
            max_depth=5,
            current_depth=6,
            workflow_id="nested-workflow-1"
        )
    """

    def __init__(
        self,
        message: str,
        max_depth: Optional[int] = None,
        current_depth: Optional[int] = None,
        workflow_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化異常。

        Args:
            message: 錯誤訊息
            max_depth: 配置的最大遞歸深度
            current_depth: 當前遞歸深度
            workflow_id: 觸發異常的工作流 ID
            context: 可選的上下文信息
            original_error: 可選的原始異常
        """
        ctx = context or {}
        if max_depth is not None:
            ctx["max_depth"] = max_depth
        if current_depth is not None:
            ctx["current_depth"] = current_depth
        if workflow_id:
            ctx["workflow_id"] = workflow_id
        super().__init__(message, context=ctx, original_error=original_error)
        self.max_depth = max_depth
        self.current_depth = current_depth
        self.workflow_id = workflow_id
