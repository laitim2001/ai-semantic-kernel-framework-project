# =============================================================================
# IPA Platform - Sandbox Configuration
# =============================================================================
# Sprint 68: S68-1 - Sandbox Directory Structure (3 pts)
#
# Configuration for per-user sandbox directory isolation.
# Manages user-scoped directories for uploads, sandbox, and outputs.
#
# Directory Structure:
#   data/
#   ├── uploads/{user_id}/      # User uploaded files
#   ├── sandbox/{user_id}/      # Agent working directory
#   ├── outputs/{user_id}/      # Agent generated outputs
#   └── temp/                   # Temporary files (no user scope)
#
# Dependencies:
#   - pathlib (standard library)
# =============================================================================

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class SandboxConfig:
    """Configuration for sandbox directory isolation.

    Provides per-user directory management for secure agent operations.

    Attributes:
        BASE_DATA_DIR: Base directory for all data storage
        UPLOADS_DIR: Directory type for user uploads
        SANDBOX_DIR: Directory type for agent working files
        OUTPUTS_DIR: Directory type for agent outputs
        TEMP_DIR: Directory type for temporary files

    Example:
        # Get user's upload directory
        upload_dir = SandboxConfig.get_user_dir("guest-abc-123", "uploads")

        # Ensure all user directories exist
        dirs = SandboxConfig.ensure_user_dirs("guest-abc-123")
    """

    # Base data directory (relative to project root)
    BASE_DATA_DIR: Path = Path("data")

    # User-scoped directory types
    UPLOADS_DIR: str = "uploads"
    SANDBOX_DIR: str = "sandbox"
    OUTPUTS_DIR: str = "outputs"
    TEMP_DIR: str = "temp"

    # All user-scoped directory types
    USER_DIR_TYPES: List[str] = [UPLOADS_DIR, SANDBOX_DIR, OUTPUTS_DIR]

    # Maximum file size for uploads (10MB)
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS: set = {
        # Text files
        ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml",
        # Documents
        ".pdf", ".docx", ".xlsx", ".pptx",
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
        # Data files
        ".log", ".html", ".css", ".sql",
    }

    # Directory cleanup settings
    CLEANUP_AGE_DAYS: int = 30  # Clean up directories older than this

    @classmethod
    def get_base_dir(cls) -> Path:
        """Get the base data directory as absolute path."""
        return Path.cwd() / cls.BASE_DATA_DIR

    @classmethod
    def get_user_dir(cls, user_id: str, dir_type: str) -> Path:
        """Get user-scoped directory path.

        Args:
            user_id: User identifier (e.g., "guest-abc-123" or UUID)
            dir_type: Directory type (uploads, sandbox, outputs)

        Returns:
            Absolute path to user's directory

        Raises:
            ValueError: If dir_type is not a valid user directory type
        """
        if dir_type not in cls.USER_DIR_TYPES and dir_type != cls.TEMP_DIR:
            raise ValueError(
                f"Invalid directory type: {dir_type}. "
                f"Must be one of: {cls.USER_DIR_TYPES}"
            )

        if dir_type == cls.TEMP_DIR:
            # Temp directory is not user-scoped
            return cls.get_base_dir() / cls.TEMP_DIR

        # Sanitize user_id to prevent path traversal
        safe_user_id = cls._sanitize_user_id(user_id)
        return cls.get_base_dir() / dir_type / safe_user_id

    @classmethod
    def ensure_user_dirs(cls, user_id: str) -> Dict[str, Path]:
        """Create all user directories if they don't exist.

        Args:
            user_id: User identifier

        Returns:
            Dictionary mapping directory type to Path
        """
        dirs = {}
        for dir_type in cls.USER_DIR_TYPES:
            path = cls.get_user_dir(user_id, dir_type)
            path.mkdir(parents=True, exist_ok=True)
            dirs[dir_type] = path
        return dirs

    @classmethod
    def ensure_temp_dir(cls) -> Path:
        """Create temp directory if it doesn't exist.

        Returns:
            Path to temp directory
        """
        temp_dir = cls.get_base_dir() / cls.TEMP_DIR
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    @classmethod
    def get_user_file_path(
        cls,
        user_id: str,
        dir_type: str,
        filename: str
    ) -> Path:
        """Get full path for a user file.

        Args:
            user_id: User identifier
            dir_type: Directory type
            filename: File name

        Returns:
            Full path to the file
        """
        user_dir = cls.get_user_dir(user_id, dir_type)
        # Sanitize filename to prevent path traversal
        safe_filename = cls._sanitize_filename(filename)
        return user_dir / safe_filename

    @classmethod
    def get_relative_path(cls, user_id: str, dir_type: str, filename: str) -> str:
        """Get relative path string for API responses.

        Args:
            user_id: User identifier
            dir_type: Directory type
            filename: File name

        Returns:
            Relative path string (e.g., "data/uploads/guest-abc/file.txt")
        """
        safe_user_id = cls._sanitize_user_id(user_id)
        safe_filename = cls._sanitize_filename(filename)
        return f"data/{dir_type}/{safe_user_id}/{safe_filename}"

    @classmethod
    def is_valid_extension(cls, filename: str) -> bool:
        """Check if file extension is allowed.

        Args:
            filename: File name to check

        Returns:
            True if extension is allowed
        """
        ext = Path(filename).suffix.lower()
        return ext in cls.ALLOWED_EXTENSIONS

    @classmethod
    def cleanup_inactive_users(
        cls,
        max_age_days: Optional[int] = None
    ) -> List[str]:
        """Remove user directories older than max_age_days.

        Args:
            max_age_days: Maximum age in days (default: CLEANUP_AGE_DAYS)

        Returns:
            List of cleaned up user IDs
        """
        max_age = max_age_days or cls.CLEANUP_AGE_DAYS
        cutoff = datetime.now() - timedelta(days=max_age)
        cleaned = []

        for dir_type in cls.USER_DIR_TYPES:
            type_dir = cls.get_base_dir() / dir_type
            if not type_dir.exists():
                continue

            for user_dir in type_dir.iterdir():
                if not user_dir.is_dir():
                    continue

                # Check modification time
                mtime = datetime.fromtimestamp(user_dir.stat().st_mtime)
                if mtime < cutoff:
                    shutil.rmtree(user_dir, ignore_errors=True)
                    if user_dir.name not in cleaned:
                        cleaned.append(user_dir.name)

        return cleaned

    @classmethod
    def get_user_storage_usage(cls, user_id: str) -> Dict[str, int]:
        """Get storage usage for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with storage usage per directory type
        """
        usage = {}
        for dir_type in cls.USER_DIR_TYPES:
            dir_path = cls.get_user_dir(user_id, dir_type)
            if dir_path.exists():
                total = sum(
                    f.stat().st_size
                    for f in dir_path.rglob("*")
                    if f.is_file()
                )
                usage[dir_type] = total
            else:
                usage[dir_type] = 0
        usage["total"] = sum(usage.values())
        return usage

    @classmethod
    def _sanitize_user_id(cls, user_id: str) -> str:
        """Sanitize user ID to prevent path traversal.

        Args:
            user_id: Raw user ID

        Returns:
            Sanitized user ID
        """
        # Remove path separators and dangerous characters
        sanitized = user_id.replace("/", "_").replace("\\", "_")
        sanitized = sanitized.replace("..", "_")

        # Only allow alphanumeric, dash, underscore
        import re
        sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "_", sanitized)

        # Ensure it's not empty
        if not sanitized:
            sanitized = "unknown"

        return sanitized

    @classmethod
    def _sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent path traversal.

        Args:
            filename: Raw filename

        Returns:
            Sanitized filename
        """
        # Get just the filename, remove any path components
        name = Path(filename).name

        # Remove dangerous characters
        import re
        sanitized = re.sub(r"[^a-zA-Z0-9\-_\.]", "_", name)

        # Ensure it's not empty
        if not sanitized or sanitized.startswith("."):
            sanitized = "file_" + sanitized

        return sanitized


def init_sandbox_directories() -> None:
    """Initialize the base sandbox directory structure.

    Creates the data/ directory with all subdirectories and .gitkeep files.
    Call this during application startup.
    """
    base = SandboxConfig.get_base_dir()

    # Create base directory
    base.mkdir(parents=True, exist_ok=True)

    # Create subdirectories with .gitkeep
    for dir_type in [*SandboxConfig.USER_DIR_TYPES, SandboxConfig.TEMP_DIR]:
        subdir = base / dir_type
        subdir.mkdir(parents=True, exist_ok=True)

        # Create .gitkeep to preserve directory in git
        gitkeep = subdir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    # Create base .gitkeep
    base_gitkeep = base / ".gitkeep"
    if not base_gitkeep.exists():
        base_gitkeep.touch()
