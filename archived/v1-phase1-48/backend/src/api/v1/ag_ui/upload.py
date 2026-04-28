# =============================================================================
# IPA Platform - File Upload API
# =============================================================================
# Sprint 68: S68-3 - File Upload API (5 pts)
#
# REST API endpoints for file upload, listing, and deletion.
# Files are stored in per-user sandbox directories.
#
# Endpoints:
#   POST   /api/v1/ag-ui/upload       - Upload file
#   GET    /api/v1/ag-ui/upload/list  - List uploaded files
#   DELETE /api/v1/ag-ui/upload/{filename} - Delete file
#
# Dependencies:
#   - SandboxConfig (src.core.sandbox_config)
#   - get_user_id (dependencies.py)
# =============================================================================

import logging
from pathlib import Path
from typing import List

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from src.core.sandbox_config import SandboxConfig
from src.api.v1.ag_ui.dependencies import get_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["File Upload"])


# =============================================================================
# Schemas
# =============================================================================


class UploadResponse(BaseModel):
    """Response schema for file upload."""

    success: bool = True
    filename: str = Field(..., description="Uploaded filename")
    path: str = Field(..., description="Relative path for agent reference")
    size: int = Field(..., description="File size in bytes")


class FileInfo(BaseModel):
    """Schema for file information."""

    filename: str
    path: str
    size: int


class FileListResponse(BaseModel):
    """Response schema for file listing."""

    files: List[FileInfo]
    total_size: int = Field(..., description="Total size of all files in bytes")


class DeleteResponse(BaseModel):
    """Response schema for file deletion."""

    success: bool = True
    deleted: str = Field(..., description="Deleted filename")


# =============================================================================
# File Validation
# =============================================================================


def validate_file_extension(filename: str) -> None:
    """Validate file extension is allowed.

    Args:
        filename: Name of the file to validate

    Raises:
        HTTPException: If extension is not allowed
    """
    if not SandboxConfig.is_valid_extension(filename):
        ext = Path(filename).suffix.lower()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not allowed. Allowed extensions: {sorted(SandboxConfig.ALLOWED_EXTENSIONS)}",
        )


def validate_file_size(size: int) -> None:
    """Validate file size is within limits.

    Args:
        size: File size in bytes

    Raises:
        HTTPException: If file is too large
    """
    if size > SandboxConfig.MAX_UPLOAD_SIZE:
        max_mb = SandboxConfig.MAX_UPLOAD_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {max_mb}MB limit",
        )


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id),
) -> UploadResponse:
    """Upload a file to user's sandbox directory.

    Files are stored in data/uploads/{user_id}/ and can be accessed
    by agents during chat sessions.

    Args:
        file: File to upload
        user_id: User identifier from headers

    Returns:
        UploadResponse with file information

    Raises:
        HTTPException: If validation fails or upload errors
    """
    # Validate extension
    validate_file_extension(file.filename)

    # Read file content
    content = await file.read()

    # Validate size
    validate_file_size(len(content))

    # Get user upload directory
    upload_dir = SandboxConfig.get_user_dir(user_id, SandboxConfig.UPLOADS_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename and create path
    safe_filename = SandboxConfig._sanitize_filename(file.filename)
    file_path = upload_dir / safe_filename

    # Write file
    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # Get relative path for API response
    relative_path = SandboxConfig.get_relative_path(
        user_id, SandboxConfig.UPLOADS_DIR, safe_filename
    )

    logger.info(f"File uploaded: user={user_id}, file={safe_filename}, size={len(content)}")

    return UploadResponse(
        success=True,
        filename=safe_filename,
        path=relative_path,
        size=len(content),
    )


@router.get("/list", response_model=FileListResponse)
async def list_uploads(
    user_id: str = Depends(get_user_id),
) -> FileListResponse:
    """List all files in user's upload directory.

    Args:
        user_id: User identifier from headers

    Returns:
        FileListResponse with list of files and total size
    """
    upload_dir = SandboxConfig.get_user_dir(user_id, SandboxConfig.UPLOADS_DIR)

    if not upload_dir.exists():
        return FileListResponse(files=[], total_size=0)

    files = []
    total_size = 0

    for item in upload_dir.iterdir():
        if item.is_file() and item.name != ".gitkeep":
            size = item.stat().st_size
            files.append(
                FileInfo(
                    filename=item.name,
                    path=SandboxConfig.get_relative_path(
                        user_id, SandboxConfig.UPLOADS_DIR, item.name
                    ),
                    size=size,
                )
            )
            total_size += size

    # Sort by filename
    files.sort(key=lambda f: f.filename)

    return FileListResponse(files=files, total_size=total_size)


@router.delete("/{filename}", response_model=DeleteResponse)
async def delete_upload(
    filename: str,
    user_id: str = Depends(get_user_id),
) -> DeleteResponse:
    """Delete an uploaded file.

    Args:
        filename: Name of the file to delete
        user_id: User identifier from headers

    Returns:
        DeleteResponse confirming deletion

    Raises:
        HTTPException: If file not found
    """
    # Sanitize filename
    safe_filename = SandboxConfig._sanitize_filename(filename)

    # Get file path
    upload_dir = SandboxConfig.get_user_dir(user_id, SandboxConfig.UPLOADS_DIR)
    file_path = upload_dir / safe_filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found",
        )

    # Delete file
    try:
        file_path.unlink()
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}",
        )

    logger.info(f"File deleted: user={user_id}, file={safe_filename}")

    return DeleteResponse(success=True, deleted=safe_filename)


@router.get("/storage", response_model=dict)
async def get_storage_usage(
    user_id: str = Depends(get_user_id),
) -> dict:
    """Get storage usage for the user.

    Returns usage statistics for uploads, sandbox, and outputs directories.

    Args:
        user_id: User identifier from headers

    Returns:
        Storage usage by directory type
    """
    usage = SandboxConfig.get_user_storage_usage(user_id)

    # Format sizes for display
    def format_size(bytes_size: int) -> str:
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        else:
            return f"{bytes_size / (1024 * 1024):.1f} MB"

    return {
        "user_id": user_id,
        "usage": usage,
        "formatted": {k: format_size(v) for k, v in usage.items()},
        "limit_bytes": SandboxConfig.MAX_UPLOAD_SIZE,
        "limit_formatted": format_size(SandboxConfig.MAX_UPLOAD_SIZE),
    }
