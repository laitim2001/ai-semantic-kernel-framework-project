"""
Image Analyzer

Specialized analyzer for image files (PNG, JPEG, GIF, WebP, etc.).
Uses multimodal LLM for image understanding.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import base64
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


class ImageAnalyzer(BaseAnalyzer):
    """圖像分析器

    支援分析 PNG、JPEG、GIF、WebP 等圖片格式。
    使用多模態 LLM 進行圖像理解。

    功能:
    - 圖像描述
    - 物體識別
    - 文字提取 (OCR)
    - 圖像問答
    """

    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS["image"]

    def __init__(self, llm_client: Optional[Any] = None):
        """
        初始化圖像分析器

        Args:
            llm_client: 多模態 LLM 客戶端 (用於圖像理解)
        """
        self._llm_client = llm_client

    def supports(self, attachment: Attachment) -> bool:
        """檢查是否支援此附件"""
        if attachment.attachment_type != AttachmentType.IMAGE:
            return False
        ext = self._get_file_extension(attachment.filename)
        return ext in self.SUPPORTED_EXTENSIONS

    async def analyze(
        self,
        attachment: Attachment,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """
        分析圖像

        Args:
            attachment: 附件對象
            request: 分析請求

        Returns:
            AnalysisResult: 分析結果
        """
        try:
            # 讀取圖像數據
            image_data = await self._read_image(attachment)

            # 獲取圖像基本信息
            image_info = await self._get_image_info(attachment, image_data)

            # 根據分析類型執行不同分析
            if request.analysis_type == AnalysisType.SUMMARY:
                return await self._analyze_summary(attachment, image_data, image_info, request)
            elif request.analysis_type == AnalysisType.EXTRACT:
                return await self._analyze_extract(attachment, image_data, image_info, request)
            elif request.analysis_type == AnalysisType.QUERY:
                return await self._analyze_query(attachment, image_data, image_info, request)
            else:
                return await self._analyze_summary(attachment, image_data, image_info, request)

        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return AnalysisResult.error_result(str(e), request.analysis_type)

    async def _read_image(self, attachment: Attachment) -> bytes:
        """讀取圖像文件"""
        import aiofiles

        async with aiofiles.open(attachment.storage_path, "rb") as f:
            return await f.read()

    async def _get_image_info(
        self,
        attachment: Attachment,
        image_data: bytes
    ) -> Dict[str, Any]:
        """獲取圖像基本信息"""
        info = {
            "filename": attachment.filename,
            "size": len(image_data),
            "size_human": self._format_size(len(image_data)),
            "format": self._get_file_extension(attachment.filename).lstrip(".").upper(),
            "content_type": attachment.content_type
        }

        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            info.update({
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "format_detected": img.format,
                "has_transparency": img.mode in ("RGBA", "LA", "P"),
                "is_animated": getattr(img, "is_animated", False),
                "n_frames": getattr(img, "n_frames", 1)
            })

            # 獲取 EXIF 數據 (如果有)
            if hasattr(img, "_getexif") and img._getexif():
                exif = img._getexif()
                info["has_exif"] = True
                # 只提取安全的 EXIF 信息
                safe_exif = {}
                exif_tags = {
                    271: "make",
                    272: "model",
                    274: "orientation",
                    306: "datetime",
                    36867: "date_taken"
                }
                for tag_id, tag_name in exif_tags.items():
                    if tag_id in exif:
                        safe_exif[tag_name] = str(exif[tag_id])
                info["exif"] = safe_exif
            else:
                info["has_exif"] = False

        except ImportError:
            logger.warning("PIL not installed, skipping detailed image info")
        except Exception as e:
            logger.warning(f"Could not get detailed image info: {e}")

        return info

    async def _analyze_summary(
        self,
        attachment: Attachment,
        image_data: bytes,
        image_info: Dict[str, Any],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """生成圖像描述摘要"""
        metadata = self._get_file_metadata(attachment)
        metadata.update(image_info)

        # 如果有多模態 LLM，使用它描述圖像
        description = None
        if self._llm_client:
            description = await self._describe_with_llm(image_data, request)

        # 構建摘要
        dimensions = ""
        if "width" in image_info and "height" in image_info:
            dimensions = f"{image_info['width']}x{image_info['height']} 像素"

        summary_parts = []
        if dimensions:
            summary_parts.append(dimensions)
        summary_parts.append(f"{image_info['format']} 格式")
        summary_parts.append(f"大小: {image_info['size_human']}")

        base_summary = ", ".join(summary_parts)

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.SUMMARY,
            content=description or f"圖像: {base_summary}",
            data={
                "image_info": image_info,
                "description": description,
                "has_llm_description": description is not None,
                "base64_preview": self._create_thumbnail_base64(image_data, image_info)
            },
            metadata=metadata
        )

    async def _analyze_extract(
        self,
        attachment: Attachment,
        image_data: bytes,
        image_info: Dict[str, Any],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """提取圖像中的文字 (OCR)"""
        metadata = self._get_file_metadata(attachment)
        metadata.update(image_info)

        # 嘗試 OCR
        extracted_text = await self._extract_text_ocr(image_data)

        if extracted_text:
            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.EXTRACT,
                content=extracted_text,
                data={
                    "extracted_text": extracted_text,
                    "text_length": len(extracted_text),
                    "ocr_performed": True
                },
                metadata=metadata
            )

        # 如果 OCR 失敗或沒有文字，嘗試用 LLM
        if self._llm_client:
            llm_text = await self._extract_text_with_llm(image_data, request)
            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.EXTRACT,
                content=llm_text or "無法從圖像中提取文字",
                data={
                    "extracted_text": llm_text,
                    "ocr_performed": False,
                    "llm_extraction": True
                },
                metadata=metadata
            )

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.EXTRACT,
            content="未能從圖像中提取文字 (需要 OCR 庫或多模態 LLM)",
            data={"ocr_performed": False},
            metadata=metadata
        )

    async def _analyze_query(
        self,
        attachment: Attachment,
        image_data: bytes,
        image_info: Dict[str, Any],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """基於圖像內容回答問題"""
        metadata = self._get_file_metadata(attachment)
        metadata.update(image_info)

        if not request.query:
            return AnalysisResult.error_result(
                "Query is required for QUERY analysis type",
                AnalysisType.QUERY
            )

        if not self._llm_client:
            return AnalysisResult.error_result(
                "Multimodal LLM client required for image Q&A",
                AnalysisType.QUERY
            )

        answer = await self._query_with_llm(image_data, request.query, request)

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.QUERY,
            content=answer,
            data={
                "query": request.query,
                "image_info": image_info
            },
            metadata=metadata
        )

    async def _describe_with_llm(
        self,
        image_data: bytes,
        request: AnalysisRequest
    ) -> Optional[str]:
        """使用多模態 LLM 描述圖像"""
        if not self._llm_client:
            return None

        try:
            base64_image = base64.b64encode(image_data).decode("utf-8")

            prompt = f"請詳細描述這張圖像的內容 (使用{request.language}):"

            # 構建多模態請求
            response = await self._llm_client.generate_with_image(
                prompt=prompt,
                image_base64=base64_image
            )
            return response.strip()

        except Exception as e:
            logger.error(f"LLM image description failed: {e}")
            return None

    async def _extract_text_ocr(self, image_data: bytes) -> Optional[str]:
        """使用 OCR 提取圖像中的文字"""
        try:
            import pytesseract
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            text = pytesseract.image_to_string(img, lang="chi_tra+eng")
            return text.strip() if text.strip() else None

        except ImportError:
            logger.warning("pytesseract not installed")
            return None
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return None

    async def _extract_text_with_llm(
        self,
        image_data: bytes,
        request: AnalysisRequest
    ) -> Optional[str]:
        """使用 LLM 提取圖像中的文字"""
        if not self._llm_client:
            return None

        try:
            base64_image = base64.b64encode(image_data).decode("utf-8")

            prompt = f"請提取這張圖像中的所有文字內容 (使用{request.language})。如果沒有文字，請回答「無文字內容」:"

            response = await self._llm_client.generate_with_image(
                prompt=prompt,
                image_base64=base64_image
            )
            return response.strip()

        except Exception as e:
            logger.error(f"LLM text extraction failed: {e}")
            return None

    async def _query_with_llm(
        self,
        image_data: bytes,
        query: str,
        request: AnalysisRequest
    ) -> str:
        """使用多模態 LLM 回答圖像相關問題"""
        if not self._llm_client:
            return "多模態 LLM 客戶端不可用"

        try:
            base64_image = base64.b64encode(image_data).decode("utf-8")

            prompt = f"根據這張圖像回答問題 (使用{request.language}):\n問題: {query}\n回答:"

            response = await self._llm_client.generate_with_image(
                prompt=prompt,
                image_base64=base64_image
            )
            return response.strip()

        except Exception as e:
            logger.error(f"LLM image query failed: {e}")
            return f"圖像問答處理失敗: {str(e)}"

    def _create_thumbnail_base64(
        self,
        image_data: bytes,
        image_info: Dict[str, Any],
        max_size: int = 200
    ) -> Optional[str]:
        """創建縮略圖的 base64 編碼"""
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))

            # 計算縮略圖大小
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 轉換為 base64
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

        except Exception as e:
            logger.warning(f"Thumbnail creation failed: {e}")
            return None
