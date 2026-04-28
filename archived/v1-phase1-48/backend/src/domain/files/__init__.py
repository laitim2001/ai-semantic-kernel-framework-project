# =============================================================================
# IPA Platform - File Domain
# =============================================================================
# Sprint 75: File Upload Feature
# Phase 20: File Attachment Support
#
# Domain layer for file management.
# =============================================================================

from src.domain.files.service import FileService
from src.domain.files.storage import FileStorage

__all__ = ["FileService", "FileStorage"]
