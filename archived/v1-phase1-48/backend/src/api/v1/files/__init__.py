# =============================================================================
# IPA Platform - File Upload API
# =============================================================================
# Sprint 75: File Upload Feature
# Phase 20: File Attachment Support
#
# RESTful API endpoints for file management:
#   - POST /files/upload - Upload file
#   - GET /files/{id} - Get file metadata
#   - DELETE /files/{id} - Delete file
# =============================================================================

from src.api.v1.files.routes import router

__all__ = ["router"]
