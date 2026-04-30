"""
Session Files Types

Type definitions for file analysis and generation functionality.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AnalysisType(str, Enum):
    """分析類型枚舉"""
    SUMMARY = "summary"          # 摘要生成
    EXTRACT = "extract"          # 內容提取
    TRANSFORM = "transform"      # 格式轉換
    QUERY = "query"              # 問題解答
    VISUALIZE = "visualize"      # 視覺化分析
    STATISTICS = "statistics"    # 統計分析


class GenerationType(str, Enum):
    """生成類型枚舉"""
    CODE = "code"                # 程式碼生成
    REPORT = "report"            # 報告生成
    DATA = "data"                # 數據導出
    DIAGRAM = "diagram"          # 圖表生成
    IMAGE = "image"              # 圖片生成


class ExportFormat(str, Enum):
    """導出格式枚舉"""
    CSV = "csv"
    JSON = "json"
    EXCEL = "xlsx"
    XML = "xml"
    MARKDOWN = "md"
    HTML = "html"
    TEXT = "txt"
    PDF = "pdf"


@dataclass
class AnalysisRequest:
    """分析請求

    定義文件分析的請求參數。
    """
    analysis_type: AnalysisType = AnalysisType.SUMMARY
    query: Optional[str] = None              # 用戶問題或查詢
    options: Dict[str, Any] = field(default_factory=dict)
    max_content_length: int = 10000          # 最大處理內容長度
    include_metadata: bool = True            # 是否包含元數據
    language: str = "zh-TW"                  # 輸出語言

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "analysis_type": self.analysis_type.value,
            "query": self.query,
            "options": self.options,
            "max_content_length": self.max_content_length,
            "include_metadata": self.include_metadata,
            "language": self.language
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisRequest":
        """從字典創建"""
        return cls(
            analysis_type=AnalysisType(data.get("analysis_type", "summary")),
            query=data.get("query"),
            options=data.get("options", {}),
            max_content_length=data.get("max_content_length", 10000),
            include_metadata=data.get("include_metadata", True),
            language=data.get("language", "zh-TW")
        )


@dataclass
class AnalysisResult:
    """分析結果

    文件分析的輸出結果。
    """
    success: bool = True
    analysis_type: AnalysisType = AnalysisType.SUMMARY
    content: str = ""                        # 主要分析內容
    data: Dict[str, Any] = field(default_factory=dict)  # 結構化數據
    metadata: Dict[str, Any] = field(default_factory=dict)  # 文件元數據
    error: Optional[str] = None              # 錯誤訊息
    processing_time_ms: int = 0              # 處理時間 (毫秒)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "success": self.success,
            "analysis_type": self.analysis_type.value,
            "content": self.content,
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """從字典創建"""
        return cls(
            success=data.get("success", True),
            analysis_type=AnalysisType(data.get("analysis_type", "summary")),
            content=data.get("content", ""),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
            error=data.get("error"),
            processing_time_ms=data.get("processing_time_ms", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow()
        )

    @classmethod
    def error_result(cls, error: str, analysis_type: AnalysisType = AnalysisType.SUMMARY) -> "AnalysisResult":
        """創建錯誤結果"""
        return cls(
            success=False,
            analysis_type=analysis_type,
            error=error
        )


@dataclass
class GenerationRequest:
    """生成請求

    定義文件生成的請求參數。
    """
    generation_type: GenerationType = GenerationType.CODE
    content: str = ""                        # 要生成的內容
    filename: Optional[str] = None           # 指定文件名
    format: ExportFormat = ExportFormat.TEXT # 輸出格式
    options: Dict[str, Any] = field(default_factory=dict)
    language: str = "python"                 # 程式語言 (用於程式碼生成)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "generation_type": self.generation_type.value,
            "content": self.content,
            "filename": self.filename,
            "format": self.format.value,
            "options": self.options,
            "language": self.language
        }


@dataclass
class GenerationResult:
    """生成結果

    文件生成的輸出結果。
    """
    success: bool = True
    generation_type: GenerationType = GenerationType.CODE
    attachment_id: Optional[str] = None      # 生成的附件 ID
    filename: str = ""                       # 文件名
    content_type: str = ""                   # MIME 類型
    size: int = 0                            # 文件大小 (bytes)
    download_url: Optional[str] = None       # 下載 URL
    error: Optional[str] = None              # 錯誤訊息
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "success": self.success,
            "generation_type": self.generation_type.value,
            "attachment_id": self.attachment_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "download_url": self.download_url,
            "error": self.error,
            "created_at": self.created_at.isoformat()
        }


# 支援的文件擴展名映射
SUPPORTED_EXTENSIONS = {
    "document": [".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"],
    "image": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"],
    "code": [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".cs", ".rb", ".php"],
    "data": [".csv", ".json", ".xml", ".xlsx", ".xls", ".yaml", ".yml", ".parquet"]
}


# 程式語言檢測映射
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".sql": "sql",
    ".sh": "bash",
    ".ps1": "powershell"
}


# MIME 類型映射
CONTENT_TYPE_MAP = {
    "python": "text/x-python",
    "javascript": "application/javascript",
    "typescript": "application/typescript",
    "java": "text/x-java",
    "go": "text/x-go",
    "rust": "text/x-rust",
    "cpp": "text/x-c++src",
    "c": "text/x-csrc",
    "csharp": "text/x-csharp",
    "ruby": "text/x-ruby",
    "php": "text/x-php",
    "markdown": "text/markdown",
    "html": "text/html",
    "css": "text/css",
    "json": "application/json",
    "xml": "application/xml",
    "csv": "text/csv",
    "text": "text/plain"
}
