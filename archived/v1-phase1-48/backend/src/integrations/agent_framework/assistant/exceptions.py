"""
Code Interpreter 自定義異常

定義 Code Interpreter 服務使用的異常類型。
"""

from typing import Optional, Any


class AssistantError(Exception):
    """Assistant 服務基礎異常。

    所有 Assistant 相關異常的基類。

    Attributes:
        message: 錯誤訊息
        details: 額外的錯誤詳情
    """

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ExecutionTimeoutError(AssistantError):
    """執行超時異常。

    當代碼執行超過指定超時時間時拋出。

    Attributes:
        timeout: 超時時間 (秒)
        elapsed: 實際經過時間 (秒)
    """

    def __init__(
        self,
        message: str = "Code execution timed out",
        timeout: int = 60,
        elapsed: float = 0,
    ):
        super().__init__(message, {"timeout": timeout, "elapsed": elapsed})
        self.timeout = timeout
        self.elapsed = elapsed


class AssistantNotFoundError(AssistantError):
    """Assistant 不存在異常。

    當指定的 Assistant ID 不存在時拋出。

    Attributes:
        assistant_id: 不存在的 Assistant ID
    """

    def __init__(self, assistant_id: str):
        super().__init__(
            f"Assistant not found: {assistant_id}",
            {"assistant_id": assistant_id}
        )
        self.assistant_id = assistant_id


class CodeExecutionError(AssistantError):
    """代碼執行異常。

    當代碼執行過程中發生錯誤時拋出。

    Attributes:
        code: 執行的代碼
        error_type: 錯誤類型
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        error_type: Optional[str] = None,
    ):
        details = {}
        if code is not None:
            details["code"] = code
        if error_type is not None:
            details["error_type"] = error_type
        super().__init__(message, details if details else None)
        self.code = code
        self.error_type = error_type


class AssistantCreationError(AssistantError):
    """Assistant 創建異常。

    當創建 Assistant 失敗時拋出。
    """

    def __init__(self, message: str = "Failed to create assistant"):
        super().__init__(message)


class ThreadCreationError(AssistantError):
    """Thread 創建異常。

    當創建對話 Thread 失敗時拋出。
    """

    def __init__(self, message: str = "Failed to create thread"):
        super().__init__(message)


class RunError(AssistantError):
    """Run 執行異常。

    當 Assistant Run 執行失敗時拋出。

    Attributes:
        run_id: Run ID
        run_status: Run 狀態
    """

    def __init__(
        self,
        message: str,
        run_id: Optional[str] = None,
        run_status: Optional[str] = None,
    ):
        details = {}
        if run_id is not None:
            details["run_id"] = run_id
        if run_status is not None:
            details["run_status"] = run_status
        super().__init__(message, details if details else None)
        self.run_id = run_id
        self.run_status = run_status


class ConfigurationError(AssistantError):
    """配置異常。

    當配置無效或缺失時拋出。
    """

    def __init__(self, message: str = "Invalid or missing configuration"):
        super().__init__(message)


class RateLimitError(AssistantError):
    """速率限制異常。

    當 API 調用超過速率限制時拋出。

    Attributes:
        retry_after: 建議的重試等待時間 (秒)
    """

    def __init__(
        self,
        message: str = "API rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        details = {"retry_after": retry_after} if retry_after is not None else None
        super().__init__(message, details)
        self.retry_after = retry_after
