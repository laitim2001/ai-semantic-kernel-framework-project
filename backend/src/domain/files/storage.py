# =============================================================================
# IPA Platform - File Storage
# =============================================================================
# Sprint 75: File Upload Feature
# Phase 20: File Attachment Support
#
# File storage layer - handles file persistence and retrieval.
# =============================================================================

import logging
import os
import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Default upload directory relative to backend root
DEFAULT_UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "data" / "uploads"


class FileStorage:
    """
    File storage handler for user uploads.

    Storage structure:
        data/uploads/{user_id}/{file_id}.{ext}
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize file storage.

        Args:
            base_path: Base path for file storage. Defaults to backend/data/uploads.
        """
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Use backend/data/uploads as default
            self.base_path = DEFAULT_UPLOAD_DIR

        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileStorage initialized at: {self.base_path}")

    def get_user_dir(self, user_id: str) -> Path:
        """
        Get user-specific upload directory.

        Args:
            user_id: User identifier.

        Returns:
            Path to user's upload directory.
        """
        user_dir = self.base_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def generate_file_id(self) -> str:
        """Generate unique file ID."""
        return str(uuid4())

    def get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return Path(filename).suffix.lower()

    def save_file(
        self,
        user_id: str,
        file_id: str,
        filename: str,
        content: bytes,
    ) -> str:
        """
        Save file to user's directory.

        Args:
            user_id: User identifier.
            file_id: Unique file identifier.
            filename: Original filename.
            content: File content as bytes.

        Returns:
            Relative storage path.
        """
        user_dir = self.get_user_dir(user_id)
        extension = self.get_file_extension(filename)
        storage_filename = f"{file_id}{extension}"
        file_path = user_dir / storage_filename

        # Write file
        file_path.write_bytes(content)
        logger.info(f"File saved: {file_path}")

        # Return relative path
        return str(file_path.relative_to(self.base_path))

    def read_file(self, storage_path: str) -> bytes:
        """
        Read file from storage.

        Args:
            storage_path: Relative storage path.

        Returns:
            File content as bytes.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        file_path = self.base_path / storage_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        return file_path.read_bytes()

    def read_file_text(self, storage_path: str, encoding: str = "utf-8") -> str:
        """
        Read text file from storage.

        Args:
            storage_path: Relative storage path.
            encoding: File encoding.

        Returns:
            File content as string.
        """
        content = self.read_file(storage_path)
        return content.decode(encoding)

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage.

        Args:
            storage_path: Relative storage path.

        Returns:
            True if deleted, False if not found.
        """
        file_path = self.base_path / storage_path
        if file_path.exists():
            file_path.unlink()
            logger.info(f"File deleted: {file_path}")
            return True
        return False

    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists."""
        file_path = self.base_path / storage_path
        return file_path.exists()

    def get_full_path(self, storage_path: str) -> Path:
        """Get absolute file path."""
        return self.base_path / storage_path

    def get_file_size(self, storage_path: str) -> int:
        """Get file size in bytes."""
        file_path = self.base_path / storage_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        return file_path.stat().st_size

    def cleanup_user_files(self, user_id: str) -> int:
        """
        Delete all files for a user.

        Args:
            user_id: User identifier.

        Returns:
            Number of files deleted.
        """
        user_dir = self.base_path / user_id
        if not user_dir.exists():
            return 0

        count = 0
        for file_path in user_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
                count += 1

        # Remove empty directory
        if user_dir.exists() and not any(user_dir.iterdir()):
            user_dir.rmdir()

        logger.info(f"Cleaned up {count} files for user {user_id}")
        return count

    def list_user_files(self, user_id: str) -> list[str]:
        """
        List all files for a user.

        Args:
            user_id: User identifier.

        Returns:
            List of relative storage paths.
        """
        user_dir = self.base_path / user_id
        if not user_dir.exists():
            return []

        files = []
        for file_path in user_dir.iterdir():
            if file_path.is_file():
                files.append(str(file_path.relative_to(self.base_path)))
        return files


# Global storage instance
_storage: Optional[FileStorage] = None


def get_file_storage() -> FileStorage:
    """Get or create global file storage instance."""
    global _storage
    if _storage is None:
        _storage = FileStorage()
    return _storage
