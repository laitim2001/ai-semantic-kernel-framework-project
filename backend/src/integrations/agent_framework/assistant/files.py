"""
文件存儲服務

管理上傳到 Azure OpenAI 的文件，支援 Code Interpreter 文件處理。

Sprint 38: Phase 8 - Agent 整合與擴展
"""

from typing import Optional, List, BinaryIO, Union
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import logging
import mimetypes

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """文件信息。

    Attributes:
        id: 文件 ID
        filename: 文件名
        bytes: 文件大小 (bytes)
        created_at: 創建時間 (Unix timestamp)
        purpose: 文件用途
        status: 文件狀態
    """
    id: str
    filename: str
    bytes: int
    created_at: int
    purpose: str
    status: str = "processed"

    @property
    def created_datetime(self) -> datetime:
        """獲取創建時間的 datetime 對象。"""
        return datetime.fromtimestamp(self.created_at)

    @property
    def size_formatted(self) -> str:
        """獲取格式化的文件大小。"""
        if self.bytes < 1024:
            return f"{self.bytes} B"
        elif self.bytes < 1024 * 1024:
            return f"{self.bytes / 1024:.1f} KB"
        elif self.bytes < 1024 * 1024 * 1024:
            return f"{self.bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.bytes / (1024 * 1024 * 1024):.1f} GB"

    def to_dict(self) -> dict:
        """轉換為字典格式。"""
        return {
            "id": self.id,
            "filename": self.filename,
            "bytes": self.bytes,
            "created_at": self.created_at,
            "purpose": self.purpose,
            "status": self.status,
            "size_formatted": self.size_formatted,
        }


class FileStorageService:
    """文件存儲服務。

    管理上傳到 Azure OpenAI 的文件，支援 Code Interpreter 文件處理。

    Supported File Types:
        - CSV (.csv)
        - Excel (.xlsx, .xls)
        - JSON (.json)
        - Text (.txt)
        - Python (.py)
        - Markdown (.md)
        - PDF (.pdf)
        - Images (.png, .jpg, .jpeg, .gif)

    Example:
        ```python
        service = FileStorageService()

        # 上傳文件
        file_info = service.upload(
            file=open("data.csv", "rb"),
            filename="data.csv",
            purpose="assistants"
        )
        print(f"Uploaded: {file_info.id}")

        # 列出文件
        files = service.list_files()
        for f in files:
            print(f"  {f.filename}: {f.size_formatted}")

        # 下載文件
        content = service.download(file_info.id)
        with open("downloaded.csv", "wb") as f:
            f.write(content)

        # 刪除文件
        service.delete(file_info.id)
        ```
    """

    # 支援的文件類型
    SUPPORTED_EXTENSIONS = {
        ".csv", ".xlsx", ".xls", ".json", ".txt", ".py", ".md",
        ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".html", ".xml",
    }

    # 文件用途
    PURPOSE_ASSISTANTS = "assistants"
    PURPOSE_FINE_TUNE = "fine-tune"

    def __init__(self, client=None):
        """初始化文件服務。

        Args:
            client: Azure OpenAI 客戶端 (如果為 None，將懶加載)
        """
        self._client = client
        self._logger = logging.getLogger(f"{__name__}.FileStorageService")

    @property
    def client(self):
        """獲取 Azure OpenAI 客戶端 (懶加載)。"""
        if self._client is None:
            from openai import AzureOpenAI
            from src.core.config import get_settings

            settings = get_settings()
            self._client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=getattr(settings, 'azure_openai_api_version', '2024-05-01-preview'),
            )
        return self._client

    def _validate_file_type(self, filename: str) -> bool:
        """驗證文件類型是否支援。

        Args:
            filename: 文件名

        Returns:
            是否為支援的文件類型
        """
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def _get_mime_type(self, filename: str) -> str:
        """獲取文件的 MIME 類型。

        Args:
            filename: 文件名

        Returns:
            MIME 類型字符串
        """
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    def upload(
        self,
        file: BinaryIO,
        filename: str,
        purpose: str = "assistants",
    ) -> FileInfo:
        """上傳文件。

        Args:
            file: 文件對象 (必須是二進制模式)
            filename: 文件名
            purpose: 文件用途 (assistants, fine-tune)

        Returns:
            FileInfo 包含上傳後的文件信息

        Raises:
            ValueError: 當文件類型不支援時
        """
        if not self._validate_file_type(filename):
            raise ValueError(
                f"Unsupported file type: {Path(filename).suffix}. "
                f"Supported types: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        self._logger.info(f"Uploading file: {filename}")

        result = self.client.files.create(
            file=(filename, file),
            purpose=purpose,
        )

        file_info = FileInfo(
            id=result.id,
            filename=result.filename,
            bytes=result.bytes,
            created_at=result.created_at,
            purpose=result.purpose,
            status=getattr(result, 'status', 'processed'),
        )

        self._logger.info(f"Uploaded file: {file_info.id} ({file_info.size_formatted})")
        return file_info

    def upload_from_path(
        self,
        path: Union[str, Path],
        purpose: str = "assistants",
    ) -> FileInfo:
        """從路徑上傳文件。

        Args:
            path: 文件路徑
            purpose: 文件用途

        Returns:
            FileInfo 包含上傳後的文件信息
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, "rb") as f:
            return self.upload(f, path.name, purpose)

    def upload_from_bytes(
        self,
        content: bytes,
        filename: str,
        purpose: str = "assistants",
    ) -> FileInfo:
        """從 bytes 上傳文件。

        Args:
            content: 文件內容
            filename: 文件名
            purpose: 文件用途

        Returns:
            FileInfo 包含上傳後的文件信息
        """
        import io
        return self.upload(io.BytesIO(content), filename, purpose)

    def list_files(
        self,
        purpose: Optional[str] = None,
    ) -> List[FileInfo]:
        """列出文件。

        Args:
            purpose: 可選的用途過濾

        Returns:
            FileInfo 列表
        """
        self._logger.debug(f"Listing files (purpose={purpose})")

        files = self.client.files.list()

        result = []
        for f in files.data:
            if purpose is None or f.purpose == purpose:
                result.append(FileInfo(
                    id=f.id,
                    filename=f.filename,
                    bytes=f.bytes,
                    created_at=f.created_at,
                    purpose=f.purpose,
                    status=getattr(f, 'status', 'processed'),
                ))

        self._logger.debug(f"Found {len(result)} files")
        return result

    def get_file(self, file_id: str) -> Optional[FileInfo]:
        """獲取單個文件信息。

        Args:
            file_id: 文件 ID

        Returns:
            FileInfo 或 None (如果文件不存在)
        """
        try:
            f = self.client.files.retrieve(file_id)
            return FileInfo(
                id=f.id,
                filename=f.filename,
                bytes=f.bytes,
                created_at=f.created_at,
                purpose=f.purpose,
                status=getattr(f, 'status', 'processed'),
            )
        except Exception as e:
            self._logger.warning(f"File not found: {file_id} - {e}")
            return None

    def download(self, file_id: str) -> bytes:
        """下載文件內容。

        Args:
            file_id: 文件 ID

        Returns:
            文件內容 (bytes)

        Raises:
            Exception: 當下載失敗時
        """
        self._logger.info(f"Downloading file: {file_id}")
        content = self.client.files.content(file_id)
        return content.read()

    def download_to_path(
        self,
        file_id: str,
        path: Union[str, Path],
    ) -> Path:
        """下載文件到指定路徑。

        Args:
            file_id: 文件 ID
            path: 目標路徑

        Returns:
            保存的文件路徑
        """
        path = Path(path)
        content = self.download(file_id)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

        self._logger.info(f"Downloaded to: {path}")
        return path

    def delete(self, file_id: str) -> bool:
        """刪除文件。

        Args:
            file_id: 文件 ID

        Returns:
            是否刪除成功
        """
        try:
            self.client.files.delete(file_id)
            self._logger.info(f"Deleted file: {file_id}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    def delete_all(self, purpose: Optional[str] = None) -> int:
        """刪除所有文件。

        Args:
            purpose: 可選的用途過濾

        Returns:
            刪除的文件數量
        """
        files = self.list_files(purpose=purpose)
        deleted = 0

        for f in files:
            if self.delete(f.id):
                deleted += 1

        self._logger.info(f"Deleted {deleted} files")
        return deleted


# 全局文件服務實例
_global_file_service: Optional[FileStorageService] = None


def get_file_service() -> FileStorageService:
    """獲取全局文件服務實例。

    Returns:
        FileStorageService 實例
    """
    global _global_file_service
    if _global_file_service is None:
        _global_file_service = FileStorageService()
    return _global_file_service
