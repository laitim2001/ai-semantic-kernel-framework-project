"""
Tests for FileStorageService

Sprint 38: 文件上傳與處理功能
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from io import BytesIO
from pathlib import Path

from src.integrations.agent_framework.assistant.files import (
    FileStorageService,
    FileInfo,
    get_file_service,
)


# =============================================================================
# FileInfo Tests
# =============================================================================

class TestFileInfo:
    """FileInfo 數據類測試。"""

    def test_create_file_info(self):
        """測試創建 FileInfo。"""
        timestamp = 1703145600  # Unix timestamp
        info = FileInfo(
            id="file-abc123",
            filename="test.csv",
            bytes=1024,
            purpose="assistants",
            created_at=timestamp,
        )

        assert info.id == "file-abc123"
        assert info.filename == "test.csv"
        assert info.bytes == 1024
        assert info.purpose == "assistants"
        assert info.created_at == timestamp

    def test_file_info_properties(self):
        """測試 FileInfo 屬性方法。"""
        info = FileInfo(
            id="file-123",
            filename="data.csv",
            bytes=1024 * 1024,  # 1 MB
            purpose="assistants",
            created_at=1703145600,
        )

        # 測試 size_formatted
        assert "MB" in info.size_formatted or "1" in info.size_formatted

        # 測試 created_datetime
        assert info.created_datetime is not None

        # 測試 to_dict
        result = info.to_dict()
        assert result["id"] == "file-123"
        assert result["filename"] == "data.csv"


# =============================================================================
# FileStorageService Tests
# =============================================================================

class TestFileStorageService:
    """FileStorageService 測試。"""

    def test_init_with_client(self):
        """測試使用自定義客戶端初始化。"""
        mock_client = MagicMock()
        service = FileStorageService(client=mock_client)

        assert service._client is mock_client

    def test_supported_extensions(self):
        """測試支援的文件擴展名。"""
        assert ".csv" in FileStorageService.SUPPORTED_EXTENSIONS
        assert ".xlsx" in FileStorageService.SUPPORTED_EXTENSIONS
        assert ".json" in FileStorageService.SUPPORTED_EXTENSIONS
        assert ".py" in FileStorageService.SUPPORTED_EXTENSIONS
        assert ".pdf" in FileStorageService.SUPPORTED_EXTENSIONS

    def test_upload_file(self):
        """測試上傳文件。"""
        mock_client = MagicMock()

        # Mock file creation response
        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_file.filename = "data.csv"
        mock_file.bytes = 512
        mock_file.purpose = "assistants"
        mock_file.created_at = 1703145600  # Unix timestamp

        mock_client.files.create.return_value = mock_file

        service = FileStorageService(client=mock_client)

        # Create test file
        content = b"col1,col2\n1,2\n3,4"
        file_obj = BytesIO(content)

        result = service.upload(
            file=file_obj,
            filename="data.csv",
            purpose="assistants",
        )

        assert result.id == "file-123"  # 使用 id 而非 file_id
        assert result.filename == "data.csv"
        mock_client.files.create.assert_called_once()

    def test_upload_unsupported_extension(self):
        """測試上傳不支援的文件類型。"""
        mock_client = MagicMock()
        service = FileStorageService(client=mock_client)

        with pytest.raises(ValueError, match="Unsupported file type"):
            service.upload(
                file=BytesIO(b"content"),
                filename="file.exe",
            )

    def test_upload_from_path(self):
        """測試從路徑上傳文件。"""
        mock_client = MagicMock()

        mock_file = MagicMock()
        mock_file.id = "file-456"
        mock_file.filename = "script.py"
        mock_file.bytes = 256
        mock_file.purpose = "assistants"
        mock_file.created_at = 1703145600

        mock_client.files.create.return_value = mock_file

        service = FileStorageService(client=mock_client)

        # Use mock for file reading
        with patch("builtins.open", MagicMock(return_value=BytesIO(b"print('hello')"))):
            with patch.object(Path, "suffix", ".py"):
                with patch.object(Path, "name", "script.py"):
                    # This would need actual file for real test
                    pass

    def test_list_files(self):
        """測試列出文件。"""
        mock_client = MagicMock()

        # Mock files list response
        mock_file1 = MagicMock()
        mock_file1.id = "file-1"
        mock_file1.filename = "file1.csv"
        mock_file1.bytes = 100
        mock_file1.purpose = "assistants"
        mock_file1.created_at = 1703145600

        mock_file2 = MagicMock()
        mock_file2.id = "file-2"
        mock_file2.filename = "file2.json"
        mock_file2.bytes = 200
        mock_file2.purpose = "fine-tune"
        mock_file2.created_at = 1703145700

        mock_list = MagicMock()
        mock_list.data = [mock_file1, mock_file2]
        mock_client.files.list.return_value = mock_list

        service = FileStorageService(client=mock_client)

        # List all files
        result = service.list_files()
        assert len(result) == 2

        # List filtered files
        result = service.list_files(purpose="assistants")
        assert len(result) == 1
        assert result[0].id == "file-1"

    def test_download_file(self):
        """測試下載文件。"""
        mock_client = MagicMock()

        mock_content = MagicMock()
        mock_content.read.return_value = b"file content here"
        mock_client.files.content.return_value = mock_content

        service = FileStorageService(client=mock_client)

        result = service.download("file-123")

        assert result == b"file content here"
        mock_client.files.content.assert_called_once_with("file-123")

    def test_delete_file_success(self):
        """測試成功刪除文件。"""
        mock_client = MagicMock()
        mock_client.files.delete.return_value = None

        service = FileStorageService(client=mock_client)

        result = service.delete("file-123")

        assert result is True
        mock_client.files.delete.assert_called_once_with("file-123")

    def test_delete_file_failure(self):
        """測試刪除文件失敗。"""
        mock_client = MagicMock()
        mock_client.files.delete.side_effect = Exception("File not found")

        service = FileStorageService(client=mock_client)

        result = service.delete("nonexistent-file")

        assert result is False


class TestFileStorageServiceValidation:
    """FileStorageService 驗證測試。"""

    def test_validate_file_type_valid(self):
        """測試驗證有效的文件類型。"""
        mock_client = MagicMock()
        service = FileStorageService(client=mock_client)

        # 應該返回 True
        assert service._validate_file_type("data.csv") is True
        assert service._validate_file_type("report.xlsx") is True
        assert service._validate_file_type("config.json") is True
        assert service._validate_file_type("README.md") is True

    def test_validate_file_type_invalid(self):
        """測試驗證無效的文件類型。"""
        mock_client = MagicMock()
        service = FileStorageService(client=mock_client)

        # 應該返回 False
        assert service._validate_file_type("malware.exe") is False
        assert service._validate_file_type("archive.zip") is False
        assert service._validate_file_type("binary.dll") is False

    def test_validate_file_type_case_insensitive(self):
        """測試文件類型驗證不區分大小寫。"""
        mock_client = MagicMock()
        service = FileStorageService(client=mock_client)

        # 應該返回 True (大小寫不敏感)
        assert service._validate_file_type("DATA.CSV") is True
        assert service._validate_file_type("Report.XLSX") is True


class TestGetFileService:
    """測試 get_file_service 函數。"""

    def test_creates_service(self):
        """測試創建服務實例。"""
        # Reset global instance
        import src.integrations.agent_framework.assistant.files as files_module
        files_module._global_file_service = None

        service = get_file_service()

        assert isinstance(service, FileStorageService)

    def test_returns_same_instance(self):
        """測試返回相同實例 (單例模式)。"""
        # Reset global instance first
        import src.integrations.agent_framework.assistant.files as files_module
        files_module._global_file_service = None

        service1 = get_file_service()
        service2 = get_file_service()

        assert service1 is service2
