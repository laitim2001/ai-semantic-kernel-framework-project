"""
Document Analyzer

Specialized analyzer for document files (PDF, Word, Text, Markdown).
"""

from typing import Optional, Dict, Any
from pathlib import Path
import logging

from ..models import Attachment, AttachmentType
from .analyzer import BaseAnalyzer
from .types import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    SUPPORTED_EXTENSIONS
)

logger = logging.getLogger(__name__)


class DocumentAnalyzer(BaseAnalyzer):
    """文檔分析器

    支援分析 PDF、Word、純文本、Markdown 等文檔格式。

    功能:
    - 文本提取
    - 摘要生成
    - 關鍵字提取
    - 問答分析
    """

    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS["document"]

    def __init__(self, llm_client: Optional[Any] = None):
        """
        初始化文檔分析器

        Args:
            llm_client: LLM 客戶端 (用於內容理解和摘要)
        """
        self._llm_client = llm_client

    def supports(self, attachment: Attachment) -> bool:
        """檢查是否支援此附件"""
        if attachment.attachment_type != AttachmentType.DOCUMENT:
            return False
        ext = self._get_file_extension(attachment.filename)
        return ext in self.SUPPORTED_EXTENSIONS

    async def analyze(
        self,
        attachment: Attachment,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """
        分析文檔

        Args:
            attachment: 附件對象
            request: 分析請求

        Returns:
            AnalysisResult: 分析結果
        """
        try:
            # 提取文本內容
            content = await self._extract_text(attachment)

            # 根據分析類型執行不同分析
            if request.analysis_type == AnalysisType.SUMMARY:
                return await self._analyze_summary(attachment, content, request)
            elif request.analysis_type == AnalysisType.EXTRACT:
                return await self._analyze_extract(attachment, content, request)
            elif request.analysis_type == AnalysisType.QUERY:
                return await self._analyze_query(attachment, content, request)
            elif request.analysis_type == AnalysisType.STATISTICS:
                return await self._analyze_statistics(attachment, content, request)
            else:
                return await self._analyze_summary(attachment, content, request)

        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return AnalysisResult.error_result(str(e), request.analysis_type)

    async def _extract_text(self, attachment: Attachment) -> str:
        """
        提取文檔文本內容

        Args:
            attachment: 附件對象

        Returns:
            str: 文本內容
        """
        ext = self._get_file_extension(attachment.filename)

        if ext == ".pdf":
            return await self._extract_pdf_text(attachment.storage_path)
        elif ext in [".docx", ".doc"]:
            return await self._extract_docx_text(attachment.storage_path)
        elif ext in [".txt", ".md"]:
            return await self._read_file_content(attachment.storage_path)
        elif ext == ".rtf":
            return await self._extract_rtf_text(attachment.storage_path)
        else:
            return await self._read_file_content(attachment.storage_path)

    async def _extract_pdf_text(self, path: str) -> str:
        """提取 PDF 文本"""
        try:
            import PyPDF2
            import aiofiles

            text_parts = []
            async with aiofiles.open(path, "rb") as f:
                content = await f.read()

            # 使用 PyPDF2 解析
            import io
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))

            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return "\n\n".join(text_parts)

        except ImportError:
            logger.warning("PyPDF2 not installed, falling back to basic extraction")
            return "[PDF content - PyPDF2 required for extraction]"
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise

    async def _extract_docx_text(self, path: str) -> str:
        """提取 Word 文檔文本"""
        try:
            from docx import Document as DocxDocument
            import aiofiles

            async with aiofiles.open(path, "rb") as f:
                content = await f.read()

            import io
            doc = DocxDocument(io.BytesIO(content))

            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            return "\n\n".join(text_parts)

        except ImportError:
            logger.warning("python-docx not installed")
            return "[DOCX content - python-docx required for extraction]"
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise

    async def _extract_rtf_text(self, path: str) -> str:
        """提取 RTF 文本"""
        try:
            from striprtf.striprtf import rtf_to_text

            content = await self._read_file_content(path)
            return rtf_to_text(content)

        except ImportError:
            logger.warning("striprtf not installed")
            return "[RTF content - striprtf required for extraction]"
        except Exception as e:
            logger.error(f"RTF extraction failed: {e}")
            raise

    async def _analyze_summary(
        self,
        attachment: Attachment,
        content: str,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """生成文檔摘要"""
        metadata = self._get_file_metadata(attachment)

        # 計算基本統計
        stats = self._compute_text_statistics(content)

        # 提取預覽
        preview_length = min(request.max_content_length, 2000)
        preview = content[:preview_length]
        if len(content) > preview_length:
            preview += "..."

        # 如果有 LLM 客戶端，生成智能摘要
        summary = None
        if self._llm_client:
            summary = await self._generate_llm_summary(content, request)

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.SUMMARY,
            content=summary or f"文檔包含 {stats['word_count']} 個字詞，{stats['paragraph_count']} 個段落。",
            data={
                "preview": preview,
                "statistics": stats,
                "summary": summary,
                "has_llm_summary": summary is not None
            },
            metadata=metadata
        )

    async def _analyze_extract(
        self,
        attachment: Attachment,
        content: str,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """提取文檔內容"""
        metadata = self._get_file_metadata(attachment)

        # 限制返回長度
        max_length = request.max_content_length
        truncated = len(content) > max_length
        extracted_content = content[:max_length]

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.EXTRACT,
            content=extracted_content,
            data={
                "full_length": len(content),
                "extracted_length": len(extracted_content),
                "truncated": truncated
            },
            metadata=metadata
        )

    async def _analyze_query(
        self,
        attachment: Attachment,
        content: str,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """基於文檔內容回答問題"""
        metadata = self._get_file_metadata(attachment)

        if not request.query:
            return AnalysisResult.error_result(
                "Query is required for QUERY analysis type",
                AnalysisType.QUERY
            )

        # 如果有 LLM 客戶端，執行問答
        if self._llm_client:
            answer = await self._query_with_llm(content, request.query, request)
            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.QUERY,
                content=answer,
                data={
                    "query": request.query,
                    "source_length": len(content)
                },
                metadata=metadata
            )

        # 無 LLM 時返回簡單搜索結果
        matches = self._simple_search(content, request.query)
        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.QUERY,
            content=f"找到 {len(matches)} 處相關內容",
            data={
                "query": request.query,
                "matches": matches[:10],  # 限制返回數量
                "total_matches": len(matches)
            },
            metadata=metadata
        )

    async def _analyze_statistics(
        self,
        attachment: Attachment,
        content: str,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """生成文檔統計"""
        metadata = self._get_file_metadata(attachment)
        stats = self._compute_text_statistics(content)

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.STATISTICS,
            content=f"文檔統計: {stats['word_count']} 字詞, {stats['char_count']} 字元",
            data={"statistics": stats},
            metadata=metadata
        )

    def _compute_text_statistics(self, content: str) -> Dict[str, Any]:
        """計算文本統計"""
        lines = content.split("\n")
        paragraphs = [p for p in content.split("\n\n") if p.strip()]
        words = content.split()

        return {
            "char_count": len(content),
            "char_count_no_spaces": len(content.replace(" ", "").replace("\n", "")),
            "word_count": len(words),
            "line_count": len(lines),
            "paragraph_count": len(paragraphs),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "avg_paragraph_length": len(words) / len(paragraphs) if paragraphs else 0
        }

    def _simple_search(self, content: str, query: str) -> list:
        """簡單文本搜索"""
        matches = []
        query_lower = query.lower()
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if query_lower in line.lower():
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                context = "\n".join(lines[start:end])
                matches.append({
                    "line": i + 1,
                    "context": context[:500]
                })

        return matches

    async def _generate_llm_summary(
        self,
        content: str,
        request: AnalysisRequest
    ) -> Optional[str]:
        """使用 LLM 生成摘要"""
        if not self._llm_client:
            return None

        try:
            # 截取內容以符合上下文長度限制
            max_content = content[:request.max_content_length]

            prompt = f"""請為以下文檔內容生成簡潔的摘要 (使用{request.language}):

{max_content}

摘要:"""

            # 調用 LLM
            response = await self._llm_client.generate(prompt)
            return response.strip()

        except Exception as e:
            logger.error(f"LLM summary generation failed: {e}")
            return None

    async def _query_with_llm(
        self,
        content: str,
        query: str,
        request: AnalysisRequest
    ) -> str:
        """使用 LLM 回答問題"""
        if not self._llm_client:
            return "LLM client not available"

        try:
            max_content = content[:request.max_content_length]

            prompt = f"""基於以下文檔內容回答問題 (使用{request.language}):

文檔內容:
{max_content}

問題: {query}

回答:"""

            response = await self._llm_client.generate(prompt)
            return response.strip()

        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return f"查詢處理失敗: {str(e)}"
