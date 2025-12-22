"""
File Generator - Main Entry Point

Factory Pattern implementation for file generation.
Routes to appropriate generator based on generation type.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import hashlib
import hmac
import time
import logging

from ..models import Attachment, AttachmentType
from .types import (
    GenerationType,
    GenerationRequest,
    GenerationResult,
    ExportFormat,
    CONTENT_TYPE_MAP
)

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """生成器基類

    所有專門生成器的抽象基類，定義統一的生成介面。
    """

    @abstractmethod
    async def generate(
        self,
        session_id: str,
        request: GenerationRequest
    ) -> GenerationResult:
        """
        生成文件

        Args:
            session_id: Session ID
            request: 生成請求

        Returns:
            GenerationResult: 生成結果
        """
        pass

    @abstractmethod
    def supports(self, generation_type: GenerationType) -> bool:
        """
        檢查是否支援此生成類型

        Args:
            generation_type: 生成類型

        Returns:
            bool: 是否支援
        """
        pass


class FileGenerator:
    """文件生成器

    工廠模式入口點，根據生成類型路由到相應的生成器。

    使用方式:
        generator = FileGenerator(storage=storage)
        result = await generator.generate(session_id, request)
    """

    def __init__(
        self,
        storage: Optional[Any] = None,
        download_url_prefix: str = "/api/v1/sessions",
        secret_key: str = "default-secret-key"
    ):
        """
        初始化文件生成器

        Args:
            storage: 存儲服務實例
            download_url_prefix: 下載 URL 前綴
            secret_key: 用於生成下載 token 的密鑰
        """
        self._storage = storage
        self._url_prefix = download_url_prefix
        self._secret_key = secret_key
        self._generators: Dict[GenerationType, BaseGenerator] = {}

        # 延遲導入具體生成器
        self._register_generators()

    def _register_generators(self) -> None:
        """註冊所有生成器"""
        from .code_generator import CodeGenerator
        from .report_generator import ReportGenerator
        from .data_exporter import DataExporter

        self._generators = {
            GenerationType.CODE: CodeGenerator(storage=self._storage),
            GenerationType.REPORT: ReportGenerator(storage=self._storage),
            GenerationType.DATA: DataExporter(storage=self._storage),
        }

    def register_generator(
        self,
        generation_type: GenerationType,
        generator: BaseGenerator
    ) -> None:
        """
        註冊自定義生成器

        Args:
            generation_type: 生成類型
            generator: 生成器實例
        """
        self._generators[generation_type] = generator

    def get_generator(self, generation_type: GenerationType) -> Optional[BaseGenerator]:
        """
        獲取適合的生成器

        Args:
            generation_type: 生成類型

        Returns:
            BaseGenerator: 生成器實例或 None
        """
        generator = self._generators.get(generation_type)
        if generator and generator.supports(generation_type):
            return generator
        return None

    async def generate(
        self,
        session_id: str,
        request: GenerationRequest
    ) -> GenerationResult:
        """
        生成文件

        根據生成類型自動選擇合適的生成器進行生成。

        Args:
            session_id: Session ID
            request: 生成請求

        Returns:
            GenerationResult: 生成結果
        """
        start_time = time.time()

        try:
            # 獲取適合的生成器
            generator = self.get_generator(request.generation_type)
            if not generator:
                return GenerationResult(
                    success=False,
                    generation_type=request.generation_type,
                    error=f"Unsupported generation type: {request.generation_type}"
                )

            logger.info(
                f"Generating {request.generation_type.value} file for session {session_id}"
            )

            # 執行生成
            result = await generator.generate(session_id, request)

            # 生成下載 URL
            if result.success and result.attachment_id:
                result.download_url = self.get_download_url(
                    session_id,
                    result.attachment_id
                )

            processing_time = int((time.time() - start_time) * 1000)
            logger.info(
                f"Generation completed in {processing_time}ms: {result.filename}"
            )

            return result

        except Exception as e:
            logger.error(f"File generation failed: {e}")
            return GenerationResult(
                success=False,
                generation_type=request.generation_type,
                error=str(e)
            )

    async def generate_file(
        self,
        session_id: str,
        content: str,
        filename: str,
        content_type: str = "text/plain"
    ) -> Attachment:
        """
        直接生成文件 (簡化介面)

        Args:
            session_id: Session ID
            content: 文件內容
            filename: 文件名
            content_type: MIME 類型

        Returns:
            Attachment: 生成的附件對象
        """
        # 創建附件
        attachment = Attachment(
            id=str(uuid.uuid4()),
            filename=filename,
            content_type=content_type,
            size=len(content.encode("utf-8")),
            attachment_type=self._detect_type(filename)
        )

        # 存儲內容
        if self._storage:
            storage_path = await self._storage.store_content(
                session_id=session_id,
                attachment_id=attachment.id,
                content=content,
                filename=filename
            )
            attachment.storage_path = storage_path
        else:
            # 無存儲服務時使用臨時路徑
            attachment.storage_path = f"/tmp/sessions/{session_id}/{attachment.id}/{filename}"

        return attachment

    def get_download_url(
        self,
        session_id: str,
        attachment_id: str,
        expires_in: int = 3600
    ) -> str:
        """
        獲取下載 URL

        Args:
            session_id: Session ID
            attachment_id: 附件 ID
            expires_in: 過期時間 (秒)

        Returns:
            下載 URL
        """
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        token = self._generate_download_token(
            session_id=session_id,
            attachment_id=attachment_id,
            expires_at=expires_at
        )

        return f"{self._url_prefix}/{session_id}/attachments/{attachment_id}/download?token={token}"

    def _generate_download_token(
        self,
        session_id: str,
        attachment_id: str,
        expires_at: datetime
    ) -> str:
        """生成下載 token"""
        expires_timestamp = int(expires_at.timestamp())
        message = f"{session_id}:{attachment_id}:{expires_timestamp}"

        signature = hmac.new(
            self._secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:32]

        return f"{expires_timestamp}.{signature}"

    def verify_download_token(
        self,
        session_id: str,
        attachment_id: str,
        token: str
    ) -> bool:
        """
        驗證下載 token

        Args:
            session_id: Session ID
            attachment_id: 附件 ID
            token: 下載 token

        Returns:
            bool: 是否有效
        """
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return False

            expires_timestamp = int(parts[0])
            provided_signature = parts[1]

            # 檢查過期
            if datetime.utcnow().timestamp() > expires_timestamp:
                return False

            # 驗證簽名
            message = f"{session_id}:{attachment_id}:{expires_timestamp}"
            expected_signature = hmac.new(
                self._secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()[:32]

            return hmac.compare_digest(provided_signature, expected_signature)

        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return False

    def _detect_type(self, filename: str) -> AttachmentType:
        """檢測文件類型"""
        ext = Path(filename).suffix.lower()

        code_extensions = [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c"]
        data_extensions = [".csv", ".json", ".xml", ".xlsx", ".xls"]
        doc_extensions = [".md", ".txt", ".html", ".pdf", ".docx"]
        image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]

        if ext in code_extensions:
            return AttachmentType.CODE
        elif ext in data_extensions:
            return AttachmentType.DATA
        elif ext in doc_extensions:
            return AttachmentType.DOCUMENT
        elif ext in image_extensions:
            return AttachmentType.IMAGE
        else:
            return AttachmentType.OTHER

    @staticmethod
    def get_content_type(format: ExportFormat) -> str:
        """獲取 MIME 類型"""
        content_types = {
            ExportFormat.CSV: "text/csv",
            ExportFormat.JSON: "application/json",
            ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ExportFormat.XML: "application/xml",
            ExportFormat.MARKDOWN: "text/markdown",
            ExportFormat.HTML: "text/html",
            ExportFormat.TEXT: "text/plain",
            ExportFormat.PDF: "application/pdf"
        }
        return content_types.get(format, "application/octet-stream")
