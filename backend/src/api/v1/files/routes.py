# =============================================================================
# IPA Platform - File Upload Routes
# =============================================================================
# Sprint 75: File Upload Feature
# Phase 20: File Attachment Support
#
# RESTful API endpoints for file upload and management:
#   - POST /files/upload - Upload file
#   - GET /files/ - List user files
#   - GET /files/{id} - Get file metadata
#   - GET /files/{id}/content - Get file content
#   - DELETE /files/{id} - Delete file
# =============================================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from src.api.v1.auth.dependencies import get_current_user_id
from src.api.v1.files.schemas import (
    FileErrorResponse,
    FileListResponse,
    FileMetadata,
    FileUploadResponse,
)
from src.domain.files.service import (
    FileService,
    FileValidationError,
    get_file_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


# =============================================================================
# Dependencies
# =============================================================================


def get_service() -> FileService:
    """Dependency for FileService."""
    return get_file_service()


# =============================================================================
# Upload Endpoint
# =============================================================================


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload File",
    description="Upload a file for analysis. Supports text, images, and PDF files.",
    responses={
        400: {"model": FileErrorResponse, "description": "Validation error"},
        413: {"model": FileErrorResponse, "description": "File too large"},
    },
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    user_id: str = Depends(get_current_user_id),
    service: FileService = Depends(get_service),
) -> FileUploadResponse:
    """
    Upload a file for AI analysis.

    Supported file types:
    - **Text files**: .txt, .md, .csv, .json, .xml, .yaml, code files (max 10MB)
    - **Images**: .jpg, .png, .gif, .webp (max 20MB)
    - **PDF**: .pdf (max 25MB)

    Files are stored with user isolation and can be attached to chat messages.
    """
    try:
        # Read file content
        content = await file.read()

        # Upload and validate
        result = await service.upload_file(
            user_id=user_id,
            filename=file.filename or "unnamed",
            content=content,
            mime_type=file.content_type,
        )

        return result

    except FileValidationError as e:
        logger.warning(f"File validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.code, "message": e.message},
        )

    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "UPLOAD_FAILED", "message": "Failed to upload file"},
        )


# =============================================================================
# List & Get Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List User Files",
    description="List all files uploaded by the current user.",
)
async def list_files(
    session_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    service: FileService = Depends(get_service),
) -> FileListResponse:
    """
    List all files for the current user.

    Args:
        session_id: Optional session ID to filter files by session.
    """
    files = service.get_user_files(user_id, session_id=session_id)
    return FileListResponse(files=files, total=len(files))


@router.get(
    "/{file_id}",
    response_model=FileMetadata,
    summary="Get File Metadata",
    description="Get metadata for a specific file.",
    responses={
        404: {"model": FileErrorResponse, "description": "File not found"},
    },
)
async def get_file(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    service: FileService = Depends(get_service),
) -> FileMetadata:
    """Get file metadata by ID."""
    metadata = service.get_file_metadata(file_id)

    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "FILE_NOT_FOUND", "message": "File not found"},
        )

    # Check ownership
    if metadata.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "FILE_NOT_FOUND", "message": "File not found"},
        )

    return metadata


@router.get(
    "/{file_id}/content",
    summary="Get File Content",
    description="Download file content.",
    responses={
        404: {"model": FileErrorResponse, "description": "File not found"},
    },
)
async def get_file_content(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    service: FileService = Depends(get_service),
) -> Response:
    """Get file content by ID."""
    metadata = service.get_file_metadata(file_id)

    if not metadata or metadata.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "FILE_NOT_FOUND", "message": "File not found"},
        )

    content = service.get_file_content(file_id, user_id)

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "FILE_NOT_FOUND", "message": "File content not found"},
        )

    return Response(
        content=content,
        media_type=metadata.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{metadata.filename}"'},
    )


# Sprint 76: Alias endpoint for download
@router.get(
    "/{file_id}/download",
    summary="Download File",
    description="Download file content (alias for /content).",
    responses={
        404: {"model": FileErrorResponse, "description": "File not found"},
    },
)
async def download_file(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    service: FileService = Depends(get_service),
) -> Response:
    """Download file by ID (alias for get_file_content)."""
    return await get_file_content(file_id, user_id, service)


# =============================================================================
# Delete Endpoint
# =============================================================================


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete File",
    description="Delete a file.",
    responses={
        404: {"model": FileErrorResponse, "description": "File not found"},
    },
)
async def delete_file(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    service: FileService = Depends(get_service),
) -> None:
    """Delete a file by ID."""
    deleted = service.delete_file(file_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "FILE_NOT_FOUND", "message": "File not found"},
        )
