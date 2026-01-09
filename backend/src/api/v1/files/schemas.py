# =============================================================================
# IPA Platform - File Upload Schemas
# =============================================================================
# Sprint 75: File Upload Feature
# Phase 20: File Attachment Support
#
# Pydantic schemas for file operations.
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FileCategory(str, Enum):
    """File category for size limits."""

    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"


class FileStatus(str, Enum):
    """File upload status."""

    PENDING = "pending"
    UPLOADED = "uploaded"
    ERROR = "error"


class FileMetadata(BaseModel):
    """File metadata schema."""

    id: str = Field(..., description="Unique file identifier")
    user_id: str = Field(..., description="Owner user ID")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., ge=0, description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    category: FileCategory = Field(..., description="File category")
    storage_path: str = Field(..., description="Storage path")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    """Response after successful file upload."""

    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., ge=0, description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    category: FileCategory = Field(..., description="File category")
    status: FileStatus = Field(default=FileStatus.UPLOADED)
    message: str = Field(default="File uploaded successfully")


class FileListResponse(BaseModel):
    """Response for listing files."""

    files: list[FileMetadata] = Field(default_factory=list)
    total: int = Field(default=0)


class FileErrorResponse(BaseModel):
    """Error response for file operations."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = None


# =============================================================================
# File Type Configuration
# =============================================================================

# Allowed MIME types by category
ALLOWED_MIME_TYPES: dict[FileCategory, set[str]] = {
    FileCategory.TEXT: {
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/html",
        "text/css",
        "text/javascript",
        "application/json",
        "application/xml",
        "application/x-yaml",
    },
    FileCategory.IMAGE: {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    },
    FileCategory.PDF: {
        "application/pdf",
    },
}

# Maximum file sizes by category (in bytes)
MAX_FILE_SIZES: dict[FileCategory, int] = {
    FileCategory.TEXT: 10 * 1024 * 1024,  # 10MB
    FileCategory.IMAGE: 20 * 1024 * 1024,  # 20MB
    FileCategory.PDF: 25 * 1024 * 1024,  # 25MB
}

# File extension to MIME type mapping
EXTENSION_TO_MIME: dict[str, str] = {
    # Text files
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".ts": "text/javascript",
    ".json": "application/json",
    ".xml": "application/xml",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".py": "text/plain",
    ".java": "text/plain",
    ".cpp": "text/plain",
    ".c": "text/plain",
    ".h": "text/plain",
    ".go": "text/plain",
    ".rs": "text/plain",
    ".rb": "text/plain",
    ".php": "text/plain",
    ".sql": "text/plain",
    ".sh": "text/plain",
    ".bat": "text/plain",
    ".ps1": "text/plain",
    # Images
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    # PDF
    ".pdf": "application/pdf",
}


def get_file_category(mime_type: str) -> Optional[FileCategory]:
    """Get file category from MIME type."""
    for category, mime_types in ALLOWED_MIME_TYPES.items():
        if mime_type in mime_types:
            return category
    return None


def is_allowed_mime_type(mime_type: str) -> bool:
    """Check if MIME type is allowed."""
    return get_file_category(mime_type) is not None


def get_max_size_for_mime(mime_type: str) -> int:
    """Get max file size for MIME type."""
    category = get_file_category(mime_type)
    if category:
        return MAX_FILE_SIZES[category]
    return 0
