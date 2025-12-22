"""
Code Generator

Specialized generator for source code files.
"""

from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid
import logging

from ..models import Attachment, AttachmentType
from .generator import BaseGenerator
from .types import (
    GenerationType,
    GenerationRequest,
    GenerationResult,
    ExportFormat,
    LANGUAGE_EXTENSIONS,
    CONTENT_TYPE_MAP
)

logger = logging.getLogger(__name__)


class CodeGenerator(BaseGenerator):
    """程式碼生成器

    生成各種程式語言的源代碼文件。

    功能:
    - 多語言支援
    - 代碼格式化
    - 自動添加文件頭
    - 語法高亮標記
    """

    # 語言到擴展名映射
    LANGUAGE_TO_EXT = {
        "python": ".py",
        "javascript": ".js",
        "typescript": ".ts",
        "java": ".java",
        "go": ".go",
        "rust": ".rs",
        "cpp": ".cpp",
        "c": ".c",
        "csharp": ".cs",
        "ruby": ".rb",
        "php": ".php",
        "swift": ".swift",
        "kotlin": ".kt",
        "scala": ".scala",
        "r": ".r",
        "sql": ".sql",
        "bash": ".sh",
        "powershell": ".ps1",
        "html": ".html",
        "css": ".css"
    }

    # 語言文件頭模板
    HEADER_TEMPLATES = {
        "python": '''"""
{description}

Generated: {timestamp}
Session: {session_id}
"""

''',
        "javascript": '''/**
 * {description}
 *
 * Generated: {timestamp}
 * Session: {session_id}
 */

''',
        "typescript": '''/**
 * {description}
 *
 * Generated: {timestamp}
 * Session: {session_id}
 */

''',
        "java": '''/**
 * {description}
 *
 * Generated: {timestamp}
 * Session: {session_id}
 */

''',
        "go": '''/*
{description}

Generated: {timestamp}
Session: {session_id}
*/

''',
        "rust": '''//! {description}
//!
//! Generated: {timestamp}
//! Session: {session_id}

''',
        "cpp": '''/**
 * {description}
 *
 * Generated: {timestamp}
 * Session: {session_id}
 */

''',
        "c": '''/**
 * {description}
 *
 * Generated: {timestamp}
 * Session: {session_id}
 */

'''
    }

    def __init__(self, storage: Optional[Any] = None):
        """
        初始化程式碼生成器

        Args:
            storage: 存儲服務實例
        """
        self._storage = storage

    def supports(self, generation_type: GenerationType) -> bool:
        """檢查是否支援此生成類型"""
        return generation_type == GenerationType.CODE

    async def generate(
        self,
        session_id: str,
        request: GenerationRequest
    ) -> GenerationResult:
        """
        生成程式碼文件

        Args:
            session_id: Session ID
            request: 生成請求

        Returns:
            GenerationResult: 生成結果
        """
        try:
            # 獲取語言和擴展名
            language = request.language or "python"
            extension = self.LANGUAGE_TO_EXT.get(language, ".txt")

            # 生成文件名
            filename = request.filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_{timestamp}{extension}"
            elif not filename.endswith(extension):
                filename = f"{filename}{extension}"

            # 處理內容
            content = request.content

            # 添加文件頭 (如果選項中啟用)
            if request.options.get("add_header", True):
                header = self._generate_header(
                    language=language,
                    description=request.options.get("description", "Generated code file"),
                    session_id=session_id
                )
                content = header + content

            # 格式化代碼 (如果選項中啟用)
            if request.options.get("format", False):
                content = await self._format_code(content, language)

            # 獲取 MIME 類型
            content_type = CONTENT_TYPE_MAP.get(language, "text/plain")

            # 創建附件
            attachment_id = str(uuid.uuid4())
            size = len(content.encode("utf-8"))

            # 存儲文件
            if self._storage:
                storage_path = await self._storage.store_content(
                    session_id=session_id,
                    attachment_id=attachment_id,
                    content=content,
                    filename=filename
                )
            else:
                storage_path = f"/tmp/sessions/{session_id}/{attachment_id}/{filename}"

            logger.info(f"Generated code file: {filename} ({size} bytes)")

            return GenerationResult(
                success=True,
                generation_type=GenerationType.CODE,
                attachment_id=attachment_id,
                filename=filename,
                content_type=content_type,
                size=size
            )

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return GenerationResult(
                success=False,
                generation_type=GenerationType.CODE,
                error=str(e)
            )

    def _generate_header(
        self,
        language: str,
        description: str,
        session_id: str
    ) -> str:
        """生成文件頭"""
        template = self.HEADER_TEMPLATES.get(language)
        if not template:
            return ""

        return template.format(
            description=description,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            session_id=session_id
        )

    async def _format_code(self, content: str, language: str) -> str:
        """格式化代碼"""
        try:
            if language == "python":
                return await self._format_python(content)
            elif language in ["javascript", "typescript"]:
                return await self._format_javascript(content)
            else:
                return content
        except Exception as e:
            logger.warning(f"Code formatting failed: {e}")
            return content

    async def _format_python(self, content: str) -> str:
        """格式化 Python 代碼"""
        try:
            import black
            return black.format_str(content, mode=black.FileMode())
        except ImportError:
            logger.warning("black not installed, skipping Python formatting")
            return content
        except Exception as e:
            logger.warning(f"Python formatting failed: {e}")
            return content

    async def _format_javascript(self, content: str) -> str:
        """格式化 JavaScript/TypeScript 代碼"""
        # 這裡可以集成 prettier 或其他格式化工具
        # 目前返回原內容
        return content

    async def generate_code_file(
        self,
        session_id: str,
        code: str,
        filename: str,
        language: str = "python",
        description: str = "",
        add_header: bool = True,
        format_code: bool = False
    ) -> GenerationResult:
        """
        便捷方法：生成程式碼文件

        Args:
            session_id: Session ID
            code: 程式碼內容
            filename: 文件名
            language: 程式語言
            description: 文件描述
            add_header: 是否添加文件頭
            format_code: 是否格式化代碼

        Returns:
            GenerationResult: 生成結果
        """
        request = GenerationRequest(
            generation_type=GenerationType.CODE,
            content=code,
            filename=filename,
            language=language,
            options={
                "description": description,
                "add_header": add_header,
                "format": format_code
            }
        )

        return await self.generate(session_id, request)

    @classmethod
    def get_supported_languages(cls) -> list:
        """獲取支援的程式語言列表"""
        return list(cls.LANGUAGE_TO_EXT.keys())

    @classmethod
    def get_extension(cls, language: str) -> str:
        """獲取語言對應的擴展名"""
        return cls.LANGUAGE_TO_EXT.get(language, ".txt")
