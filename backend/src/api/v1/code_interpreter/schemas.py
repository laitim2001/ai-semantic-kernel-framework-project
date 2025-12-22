"""
Code Interpreter API Schemas

定義 Code Interpreter API 請求和響應的數據模型。
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================

class CodeExecuteRequest(BaseModel):
    """執行 Python 代碼請求。"""
    code: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="要執行的 Python 代碼"
    )
    timeout: Optional[int] = Field(
        default=60,
        ge=1,
        le=300,
        description="執行超時時間 (秒)，默認 60 秒，最大 300 秒"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="可選的會話 ID，用於復用 Assistant"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": "print(sum(range(1, 101)))",
                "timeout": 60,
                "session_id": None
            }
        }


class TaskAnalyzeRequest(BaseModel):
    """分析任務請求。"""
    task: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="任務描述"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可選的上下文信息"
    )
    timeout: Optional[int] = Field(
        default=60,
        ge=1,
        le=300,
        description="執行超時時間 (秒)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="可選的會話 ID"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task": "Calculate the factorial of 10",
                "context": {"precision": "high"},
                "timeout": 60
            }
        }


class SessionCreateRequest(BaseModel):
    """創建會話請求。"""
    name: Optional[str] = Field(
        default="IPA-CodeInterpreter",
        max_length=100,
        description="會話名稱"
    )
    instructions: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="自定義系統指令"
    )
    timeout: Optional[int] = Field(
        default=60,
        ge=1,
        le=300,
        description="默認執行超時時間"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Data Analysis Session",
                "instructions": "You are a data analysis expert.",
                "timeout": 120
            }
        }


# =============================================================================
# Response Schemas
# =============================================================================

class FileOutput(BaseModel):
    """生成的文件信息。"""
    type: str = Field(..., description="文件類型 (file, image)")
    file_id: str = Field(..., description="文件 ID")
    filename: Optional[str] = Field(default=None, description="文件名")


class CodeOutput(BaseModel):
    """代碼執行輸出 (Responses API 格式)。"""
    id: Optional[str] = Field(default=None, description="執行 ID")
    code: Optional[str] = Field(default=None, description="執行的代碼")

    class Config:
        extra = "allow"  # Allow additional fields


class ExecutionMetadata(BaseModel):
    """執行元數據。"""
    status: str = Field(..., description="執行狀態")
    code_outputs: Optional[List[Any]] = Field(
        default_factory=list,
        description="代碼執行輸出 (支援字串或 dict 格式)"
    )
    api_mode: Optional[str] = Field(default=None, description="API 模式 (responses/assistants)")
    response_id: Optional[str] = Field(default=None, description="Responses API 回應 ID")


class CodeExecuteResponse(BaseModel):
    """代碼執行響應。"""
    success: bool = Field(..., description="是否成功")
    output: str = Field(..., description="輸出內容")
    execution_time: float = Field(..., description="執行耗時 (秒)")
    files: List[FileOutput] = Field(
        default_factory=list,
        description="生成的文件列表"
    )
    error: Optional[str] = Field(default=None, description="錯誤信息")
    metadata: Optional[ExecutionMetadata] = Field(
        default=None,
        description="執行元數據"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "output": "The result is 5050",
                "execution_time": 2.5,
                "files": [],
                "error": None,
                "metadata": {
                    "status": "success",
                    "code_outputs": []
                }
            }
        }


class TaskAnalyzeResponse(BaseModel):
    """任務分析響應。"""
    success: bool = Field(..., description="是否成功")
    output: str = Field(..., description="分析結果")
    execution_time: float = Field(..., description="執行耗時 (秒)")
    files: List[FileOutput] = Field(
        default_factory=list,
        description="生成的文件列表"
    )
    error: Optional[str] = Field(default=None, description="錯誤信息")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "output": "The factorial of 10 is 3628800",
                "execution_time": 3.2,
                "files": [],
                "error": None
            }
        }


class SessionInfo(BaseModel):
    """會話信息。"""
    session_id: str = Field(..., description="會話 ID")
    assistant_id: str = Field(..., description="Assistant ID")
    name: str = Field(..., description="會話名稱")
    created_at: datetime = Field(..., description="創建時間")
    is_active: bool = Field(default=True, description="是否活躍")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "assistant_id": "asst_xyz789",
                "name": "Data Analysis Session",
                "created_at": "2025-12-21T10:30:00Z",
                "is_active": True
            }
        }


class SessionCreateResponse(BaseModel):
    """創建會話響應。"""
    session: SessionInfo = Field(..., description="會話信息")
    message: str = Field(default="Session created successfully")


class SessionDeleteResponse(BaseModel):
    """刪除會話響應。"""
    success: bool = Field(..., description="是否成功刪除")
    message: str = Field(..., description="操作信息")


class HealthCheckResponse(BaseModel):
    """健康檢查響應。"""
    status: str = Field(..., description="服務狀態")
    azure_openai_configured: bool = Field(
        ...,
        description="Azure OpenAI 是否已配置"
    )
    message: Optional[str] = Field(default=None, description="附加信息")


# =============================================================================
# File Storage Schemas (Sprint 38)
# =============================================================================

class FileUploadResponse(BaseModel):
    """文件上傳響應。"""
    file_id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    bytes: int = Field(..., description="文件大小 (bytes)")
    purpose: str = Field(..., description="文件用途")
    created_at: datetime = Field(..., description="創建時間")
    message: str = Field(default="File uploaded successfully")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file-abc123",
                "filename": "data.csv",
                "bytes": 1024,
                "purpose": "assistants",
                "created_at": "2025-12-22T10:30:00Z",
                "message": "File uploaded successfully"
            }
        }


class StoredFileInfo(BaseModel):
    """存儲的文件信息。"""
    file_id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    bytes: int = Field(..., description="文件大小 (bytes)")
    purpose: str = Field(..., description="文件用途")
    created_at: datetime = Field(..., description="創建時間")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file-abc123",
                "filename": "data.csv",
                "bytes": 1024,
                "purpose": "assistants",
                "created_at": "2025-12-22T10:30:00Z"
            }
        }


class FileListResponse(BaseModel):
    """文件列表響應。"""
    files: List[StoredFileInfo] = Field(default_factory=list, description="文件列表")
    total: int = Field(..., description="總數")

    class Config:
        json_schema_extra = {
            "example": {
                "files": [
                    {
                        "file_id": "file-abc123",
                        "filename": "data.csv",
                        "bytes": 1024,
                        "purpose": "assistants",
                        "created_at": "2025-12-22T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }


class FileDeleteResponse(BaseModel):
    """文件刪除響應。"""
    success: bool = Field(..., description="是否成功刪除")
    file_id: str = Field(..., description="文件 ID")
    message: str = Field(default="File deleted successfully")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "file_id": "file-abc123",
                "message": "File deleted successfully"
            }
        }
