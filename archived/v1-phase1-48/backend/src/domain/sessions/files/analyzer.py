"""
File Analyzer - Main Entry Point

Strategy Pattern implementation for file analysis.
Routes to appropriate analyzer based on attachment type.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type
from pathlib import Path
import time
import logging

from ..models import Attachment, AttachmentType
from .types import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    SUPPORTED_EXTENSIONS
)

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """分析器基類

    所有專門分析器的抽象基類，定義統一的分析介面。
    """

    @abstractmethod
    async def analyze(
        self,
        attachment: Attachment,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """
        分析文件

        Args:
            attachment: 附件對象
            request: 分析請求

        Returns:
            AnalysisResult: 分析結果
        """
        pass

    @abstractmethod
    def supports(self, attachment: Attachment) -> bool:
        """
        檢查是否支援此附件類型

        Args:
            attachment: 附件對象

        Returns:
            bool: 是否支援
        """
        pass

    async def _read_file_content(self, path: str, max_size: int = 1024 * 1024) -> str:
        """
        讀取文件內容

        Args:
            path: 文件路徑
            max_size: 最大讀取大小 (bytes)

        Returns:
            str: 文件內容
        """
        try:
            import aiofiles
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read(max_size)
                return content
        except UnicodeDecodeError:
            # 嘗試以 binary 模式讀取
            async with aiofiles.open(path, "rb") as f:
                binary_content = await f.read(max_size)
                return binary_content.decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            raise

    def _get_file_extension(self, filename: str) -> str:
        """獲取文件擴展名 (小寫)"""
        return Path(filename).suffix.lower()

    def _get_file_metadata(self, attachment: Attachment) -> Dict[str, Any]:
        """獲取文件基本元數據"""
        return {
            "filename": attachment.filename,
            "content_type": attachment.content_type,
            "size": attachment.size,
            "size_human": self._format_size(attachment.size),
            "extension": self._get_file_extension(attachment.filename),
            "type": attachment.attachment_type.value,
            "uploaded_at": attachment.uploaded_at.isoformat()
        }

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class GenericAnalyzer(BaseAnalyzer):
    """通用分析器

    處理未知類型或不支援類型的文件。
    """

    async def analyze(
        self,
        attachment: Attachment,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """通用分析 - 返回基本文件信息"""
        metadata = self._get_file_metadata(attachment)

        return AnalysisResult(
            success=True,
            analysis_type=request.analysis_type,
            content=f"文件: {attachment.filename} ({metadata['size_human']})",
            data={
                "file_info": metadata,
                "supported": False,
                "message": "此文件類型暫不支援深度分析，僅提供基本信息。"
            },
            metadata=metadata
        )

    def supports(self, attachment: Attachment) -> bool:
        """通用分析器支援所有類型"""
        return True


class FileAnalyzer:
    """文件分析器

    策略模式入口點，根據文件類型路由到相應的分析器。

    使用方式:
        analyzer = FileAnalyzer()
        result = await analyzer.analyze(attachment, request)
    """

    def __init__(
        self,
        code_interpreter: Optional[Any] = None,
        llm_client: Optional[Any] = None
    ):
        """
        初始化文件分析器

        Args:
            code_interpreter: Code Interpreter 實例 (用於數據分析)
            llm_client: LLM 客戶端 (用於內容理解)
        """
        self._code_interpreter = code_interpreter
        self._llm_client = llm_client
        self._analyzers: Dict[AttachmentType, BaseAnalyzer] = {}
        self._generic_analyzer = GenericAnalyzer()

        # 延遲導入具體分析器，避免循環導入
        self._register_analyzers()

    def _register_analyzers(self) -> None:
        """註冊所有分析器"""
        # 導入具體分析器
        from .document_analyzer import DocumentAnalyzer
        from .image_analyzer import ImageAnalyzer
        from .code_analyzer import CodeAnalyzer
        from .data_analyzer import DataAnalyzer

        self._analyzers = {
            AttachmentType.DOCUMENT: DocumentAnalyzer(llm_client=self._llm_client),
            AttachmentType.IMAGE: ImageAnalyzer(llm_client=self._llm_client),
            AttachmentType.CODE: CodeAnalyzer(llm_client=self._llm_client),
            AttachmentType.DATA: DataAnalyzer(
                code_interpreter=self._code_interpreter,
                llm_client=self._llm_client
            ),
        }

    def register_analyzer(
        self,
        attachment_type: AttachmentType,
        analyzer: BaseAnalyzer
    ) -> None:
        """
        註冊自定義分析器

        Args:
            attachment_type: 附件類型
            analyzer: 分析器實例
        """
        self._analyzers[attachment_type] = analyzer

    def get_analyzer(self, attachment: Attachment) -> BaseAnalyzer:
        """
        獲取適合的分析器

        Args:
            attachment: 附件對象

        Returns:
            BaseAnalyzer: 分析器實例
        """
        analyzer = self._analyzers.get(attachment.attachment_type)
        if analyzer and analyzer.supports(attachment):
            return analyzer
        return self._generic_analyzer

    async def analyze(
        self,
        attachment: Attachment,
        request: Optional[AnalysisRequest] = None
    ) -> AnalysisResult:
        """
        分析文件

        根據附件類型自動選擇合適的分析器進行分析。

        Args:
            attachment: 附件對象
            request: 分析請求 (可選，默認使用摘要分析)

        Returns:
            AnalysisResult: 分析結果
        """
        if request is None:
            request = AnalysisRequest()

        start_time = time.time()

        try:
            # 獲取適合的分析器
            analyzer = self.get_analyzer(attachment)
            logger.info(
                f"Analyzing {attachment.filename} with {analyzer.__class__.__name__}"
            )

            # 執行分析
            result = await analyzer.analyze(attachment, request)

            # 計算處理時間
            processing_time = int((time.time() - start_time) * 1000)
            result.processing_time_ms = processing_time

            logger.info(
                f"Analysis completed in {processing_time}ms: {attachment.filename}"
            )

            return result

        except Exception as e:
            logger.error(f"Analysis failed for {attachment.filename}: {e}")
            processing_time = int((time.time() - start_time) * 1000)

            return AnalysisResult(
                success=False,
                analysis_type=request.analysis_type,
                error=str(e),
                processing_time_ms=processing_time,
                metadata={"filename": attachment.filename}
            )

    async def batch_analyze(
        self,
        attachments: list,
        request: Optional[AnalysisRequest] = None
    ) -> list:
        """
        批量分析文件

        Args:
            attachments: 附件列表
            request: 分析請求

        Returns:
            list[AnalysisResult]: 分析結果列表
        """
        import asyncio

        tasks = [
            self.analyze(attachment, request)
            for attachment in attachments
        ]

        return await asyncio.gather(*tasks)

    def is_supported(self, attachment: Attachment) -> bool:
        """
        檢查文件是否支援分析

        Args:
            attachment: 附件對象

        Returns:
            bool: 是否支援
        """
        analyzer = self._analyzers.get(attachment.attachment_type)
        return analyzer is not None and analyzer.supports(attachment)

    def get_supported_extensions(self) -> Dict[str, list]:
        """
        獲取所有支援的文件擴展名

        Returns:
            Dict: 按類型分組的擴展名列表
        """
        return SUPPORTED_EXTENSIONS.copy()

    @staticmethod
    def detect_attachment_type(filename: str, content_type: Optional[str] = None) -> AttachmentType:
        """
        檢測附件類型

        Args:
            filename: 文件名
            content_type: MIME 類型 (可選)

        Returns:
            AttachmentType: 附件類型
        """
        ext = Path(filename).suffix.lower()

        for type_name, extensions in SUPPORTED_EXTENSIONS.items():
            if ext in extensions:
                return AttachmentType(type_name.upper() if type_name != "document" else "document")

        # 根據 MIME 類型判斷
        if content_type:
            if content_type.startswith("image/"):
                return AttachmentType.IMAGE
            elif content_type.startswith("text/"):
                if "python" in content_type or "java" in content_type:
                    return AttachmentType.CODE
                return AttachmentType.DOCUMENT
            elif content_type in ["application/json", "text/csv"]:
                return AttachmentType.DATA

        return AttachmentType.OTHER
