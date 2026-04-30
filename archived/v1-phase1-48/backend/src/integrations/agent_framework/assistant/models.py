"""
Code Interpreter 數據模型

定義 Code Interpreter 服務使用的數據類型。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ExecutionStatus(str, Enum):
    """執行狀態枚舉。"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class CodeExecutionResult:
    """程式碼執行結果。

    Attributes:
        status: 執行狀態 (success, error, timeout)
        output: 執行輸出或錯誤訊息
        execution_time: 執行耗時 (秒)
        files: 生成的文件列表
        code_outputs: 代碼執行的原始輸出
    """
    status: ExecutionStatus
    output: str
    execution_time: float
    files: List[Dict[str, Any]] = field(default_factory=list)
    code_outputs: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """檢查是否執行成功。"""
        return self.status == ExecutionStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "status": self.status.value,
            "output": self.output,
            "execution_time": self.execution_time,
            "files": self.files,
            "code_outputs": self.code_outputs,
        }


@dataclass
class AssistantConfig:
    """Assistant 配置。

    Attributes:
        name: Assistant 名稱
        instructions: 系統指令
        model: 模型部署名稱 (可選，默認使用環境配置)
        timeout: 執行超時時間 (秒)
        max_retries: 最大重試次數
    """
    name: str = "IPA-CodeInterpreter"
    instructions: str = (
        "You are a Python code execution assistant. "
        "Execute code accurately and return results. "
        "When given code, execute it and provide the output. "
        "When given a task, write appropriate Python code to solve it."
    )
    model: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3


@dataclass
class ThreadMessage:
    """Thread 消息。

    Attributes:
        role: 消息角色 (user, assistant)
        content: 消息內容
        file_ids: 關聯的文件 ID
    """
    role: str
    content: str
    file_ids: List[str] = field(default_factory=list)


@dataclass
class AssistantInfo:
    """Assistant 信息。

    Attributes:
        id: Assistant ID
        name: Assistant 名稱
        model: 使用的模型
        tools: 啟用的工具列表
        created_at: 創建時間戳
    """
    id: str
    name: str
    model: str
    tools: List[str]
    created_at: int

    @classmethod
    def from_api_response(cls, response: Any) -> "AssistantInfo":
        """從 API 響應創建實例。"""
        tools = [t.type for t in response.tools] if response.tools else []
        return cls(
            id=response.id,
            name=response.name or "",
            model=response.model,
            tools=tools,
            created_at=response.created_at,
        )


@dataclass
class FileInfo:
    """文件信息。

    Attributes:
        id: 文件 ID
        filename: 文件名
        bytes: 文件大小 (字節)
        created_at: 創建時間戳
        purpose: 文件用途
    """
    id: str
    filename: str
    bytes: int
    created_at: int
    purpose: str

    @classmethod
    def from_api_response(cls, response: Any) -> "FileInfo":
        """從 API 響應創建實例。"""
        return cls(
            id=response.id,
            filename=response.filename,
            bytes=response.bytes,
            created_at=response.created_at,
            purpose=response.purpose,
        )
