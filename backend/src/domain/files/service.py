# =============================================================================
# IPA Platform - File Service
# =============================================================================
# Sprint 75: File Upload Feature
# Phase 20: File Attachment Support
#
# Business logic for file operations.
# =============================================================================

import base64
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.api.v1.files.schemas import (
    EXTENSION_TO_MIME,
    FileCategory,
    FileMetadata,
    FileStatus,
    FileUploadResponse,
    get_file_category,
    get_max_size_for_mime,
    is_allowed_mime_type,
)
from src.domain.files.storage import FileStorage, get_file_storage

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """File validation error."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class FileService:
    """
    File service for upload, validation, and management.

    Handles:
        - File type validation
        - File size validation
        - User isolation
        - File metadata management
    """

    def __init__(self, storage: Optional[FileStorage] = None):
        """
        Initialize file service.

        Args:
            storage: File storage instance. Defaults to global storage.
        """
        self.storage = storage or get_file_storage()
        self._file_metadata: dict[str, FileMetadata] = {}

    def validate_file(
        self,
        filename: str,
        content: bytes,
        mime_type: Optional[str] = None,
    ) -> tuple[str, FileCategory]:
        """
        Validate file type and size.

        Args:
            filename: Original filename.
            content: File content as bytes.
            mime_type: Optional MIME type from upload.

        Returns:
            Tuple of (validated_mime_type, category).

        Raises:
            FileValidationError: If validation fails.
        """
        file_size = len(content)

        # Determine MIME type
        if not mime_type:
            # Try to get from extension
            extension = Path(filename).suffix.lower()
            mime_type = EXTENSION_TO_MIME.get(extension)
            if not mime_type:
                # Fallback to mimetypes library
                guessed_type, _ = mimetypes.guess_type(filename)
                mime_type = guessed_type

        if not mime_type:
            raise FileValidationError(
                "UNKNOWN_FILE_TYPE",
                f"Cannot determine file type for: {filename}",
            )

        # Check if MIME type is allowed
        if not is_allowed_mime_type(mime_type):
            raise FileValidationError(
                "FILE_TYPE_NOT_ALLOWED",
                f"File type not allowed: {mime_type}. Supported: text, images, PDF.",
            )

        # Get category and check size
        category = get_file_category(mime_type)
        max_size = get_max_size_for_mime(mime_type)

        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            raise FileValidationError(
                "FILE_TOO_LARGE",
                f"File size ({file_size_mb:.1f}MB) exceeds limit ({max_size_mb:.0f}MB) for {category.value} files.",
            )

        return mime_type, category

    async def upload_file(
        self,
        user_id: str,
        filename: str,
        content: bytes,
        mime_type: Optional[str] = None,
    ) -> FileUploadResponse:
        """
        Upload and store a file.

        Args:
            user_id: User identifier.
            filename: Original filename.
            content: File content as bytes.
            mime_type: Optional MIME type from upload.

        Returns:
            FileUploadResponse with file metadata.

        Raises:
            FileValidationError: If validation fails.
        """
        # Validate file
        validated_mime_type, category = self.validate_file(filename, content, mime_type)

        # Generate file ID and save
        file_id = self.storage.generate_file_id()
        storage_path = self.storage.save_file(user_id, file_id, filename, content)

        # Create metadata
        metadata = FileMetadata(
            id=file_id,
            user_id=user_id,
            filename=filename,
            size=len(content),
            mime_type=validated_mime_type,
            category=category,
            storage_path=storage_path,
            created_at=datetime.utcnow(),
        )

        # Store metadata in memory (in production, use database)
        self._file_metadata[file_id] = metadata

        logger.info(f"File uploaded: {filename} ({category.value}) for user {user_id}")

        return FileUploadResponse(
            id=file_id,
            filename=filename,
            size=len(content),
            mime_type=validated_mime_type,
            category=category,
            status=FileStatus.UPLOADED,
            message="File uploaded successfully",
        )

    def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID."""
        return self._file_metadata.get(file_id)

    def get_user_files(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> list[FileMetadata]:
        """
        Get all files for a user.

        Args:
            user_id: User identifier.
            session_id: Optional session ID to filter files.

        Returns:
            List of FileMetadata for the user.
        """
        files = [
            meta for meta in self._file_metadata.values() if meta.user_id == user_id
        ]

        # Sprint 76: Filter by session_id if provided
        if session_id:
            files = [
                f for f in files
                if hasattr(f, 'session_id') and f.session_id == session_id
            ]

        return files

    def delete_file(self, file_id: str, user_id: str) -> bool:
        """
        Delete file if owned by user.

        Args:
            file_id: File identifier.
            user_id: User identifier.

        Returns:
            True if deleted, False if not found or not owned.
        """
        metadata = self._file_metadata.get(file_id)
        if not metadata:
            return False

        if metadata.user_id != user_id:
            logger.warning(f"User {user_id} tried to delete file {file_id} owned by {metadata.user_id}")
            return False

        # Delete from storage
        self.storage.delete_file(metadata.storage_path)

        # Remove metadata
        del self._file_metadata[file_id]

        logger.info(f"File deleted: {file_id} by user {user_id}")
        return True

    def get_file_content(self, file_id: str, user_id: str) -> Optional[bytes]:
        """
        Get file content if owned by user.

        Args:
            file_id: File identifier.
            user_id: User identifier.

        Returns:
            File content as bytes, or None if not found/authorized.
        """
        metadata = self._file_metadata.get(file_id)
        if not metadata or metadata.user_id != user_id:
            return None

        return self.storage.read_file(metadata.storage_path)

    def get_file_content_text(
        self,
        file_id: str,
        user_id: str,
        encoding: str = "utf-8",
    ) -> Optional[str]:
        """
        Get text file content if owned by user.

        Args:
            file_id: File identifier.
            user_id: User identifier.
            encoding: File encoding.

        Returns:
            File content as string, or None if not found/authorized.
        """
        content = self.get_file_content(file_id, user_id)
        if content:
            return content.decode(encoding)
        return None

    def get_file_base64(self, file_id: str, user_id: str) -> Optional[str]:
        """
        Get file content as base64 string.

        Args:
            file_id: File identifier.
            user_id: User identifier.

        Returns:
            Base64 encoded file content, or None if not found/authorized.
        """
        content = self.get_file_content(file_id, user_id)
        if content:
            return base64.b64encode(content).decode("utf-8")
        return None

    def is_image_file(self, file_id: str) -> bool:
        """Check if file is an image."""
        metadata = self._file_metadata.get(file_id)
        return metadata is not None and metadata.category == FileCategory.IMAGE

    def is_text_file(self, file_id: str) -> bool:
        """Check if file is a text file."""
        metadata = self._file_metadata.get(file_id)
        return metadata is not None and metadata.category == FileCategory.TEXT

    def is_pdf_file(self, file_id: str) -> bool:
        """Check if file is a PDF."""
        metadata = self._file_metadata.get(file_id)
        return metadata is not None and metadata.category == FileCategory.PDF


# Global service instance
_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """Get or create global file service instance."""
    global _service
    if _service is None:
        _service = FileService()
    return _service
