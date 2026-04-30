"""Filesystem sandbox with security controls.

Provides safe file operations with:
- Path validation and sandboxing
- Blocked file patterns (secrets, credentials)
- Size limits
- Permission enforcement
"""

import fnmatch
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Filesystem sandbox configuration.

    Attributes:
        allowed_paths: Directories that can be accessed (empty = current dir only)
        blocked_patterns: Glob patterns for blocked files
        max_file_size: Maximum file size for read/write (bytes)
        max_list_depth: Maximum directory listing depth
        allow_write: Enable write operations
        allow_delete: Enable delete operations
    """

    allowed_paths: List[str] = field(default_factory=list)
    blocked_patterns: Optional[List[str]] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_list_depth: int = 10
    allow_write: bool = True
    allow_delete: bool = False

    @classmethod
    def from_env(cls) -> "SandboxConfig":
        """Create config from environment variables.

        Environment variables:
            FS_ALLOWED_PATHS: Comma-separated list of allowed paths
            FS_MAX_FILE_SIZE: Maximum file size in bytes
            FS_MAX_LIST_DEPTH: Maximum directory listing depth
            FS_ALLOW_WRITE: Enable write operations (true/false)
            FS_ALLOW_DELETE: Enable delete operations (true/false)
        """
        allowed_paths_str = os.environ.get("FS_ALLOWED_PATHS", "")
        allowed_paths = [
            p.strip() for p in allowed_paths_str.split(",") if p.strip()
        ]

        return cls(
            allowed_paths=allowed_paths,
            max_file_size=int(os.environ.get("FS_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
            max_list_depth=int(os.environ.get("FS_MAX_LIST_DEPTH", "10")),
            allow_write=os.environ.get("FS_ALLOW_WRITE", "true").lower() == "true",
            allow_delete=os.environ.get("FS_ALLOW_DELETE", "false").lower() == "true",
        )


class FilesystemSandbox:
    """Sandboxed filesystem operations.

    Provides secure file operations with path validation,
    blocked patterns, and size limits.

    Example:
        >>> config = SandboxConfig(allowed_paths=["/home/user/projects"])
        >>> sandbox = FilesystemSandbox(config)
        >>> content = await sandbox.read_file("/home/user/projects/readme.md")
    """

    # Default blocked patterns (sensitive files)
    DEFAULT_BLOCKED_PATTERNS = [
        # Credentials and secrets
        "*.pem",
        "*.key",
        "*.pfx",
        "*.p12",
        "**/id_rsa*",
        "**/id_ed25519*",
        "**/.ssh/*",
        "**/.aws/credentials",
        "**/.aws/config",
        "**/credentials.json",
        "**/secrets.json",
        "**/secrets.yaml",
        "**/secrets.yml",
        # Environment files with secrets
        ".env",
        "*.env",
        ".env.*",
        "**/.env",
        "**/*.env",
        # Password files
        "**/.htpasswd",
        "**/passwd",
        "**/shadow",
        # Database files
        "*.sqlite",
        "*.db",
        # Keychain files
        "**/*.keychain",
        "**/login.keychain",
        # Config with potential secrets
        "**/config.json",
        "**/config.yaml",
        "**/config.yml",
    ]

    def __init__(self, config: SandboxConfig):
        """Initialize filesystem sandbox.

        Args:
            config: Sandbox configuration
        """
        self._config = config
        self._allowed_paths = self._normalize_paths(config.allowed_paths)
        self._blocked_patterns = (
            config.blocked_patterns
            if config.blocked_patterns is not None
            else self.DEFAULT_BLOCKED_PATTERNS
        )

        logger.info(
            f"FilesystemSandbox initialized: {len(self._allowed_paths)} allowed paths, "
            f"{len(self._blocked_patterns)} blocked patterns"
        )

    def _normalize_paths(self, paths: List[str]) -> Set[Path]:
        """Normalize and validate allowed paths.

        Args:
            paths: List of path strings

        Returns:
            Set of normalized Path objects
        """
        normalized = set()
        for path_str in paths:
            try:
                path = Path(path_str).resolve()
                if path.exists() and path.is_dir():
                    normalized.add(path)
                else:
                    logger.warning(f"Allowed path does not exist or is not a directory: {path}")
            except Exception as e:
                logger.warning(f"Invalid allowed path '{path_str}': {e}")

        # If no valid paths, use current directory
        if not normalized:
            cwd = Path.cwd()
            normalized.add(cwd)
            logger.info(f"No valid allowed paths, using current directory: {cwd}")

        return normalized

    def validate_path(self, path: str) -> Path:
        """Validate and normalize a file path.

        Args:
            path: Path to validate

        Returns:
            Normalized Path object

        Raises:
            ValueError: If path is blocked or outside sandbox
        """
        try:
            resolved = Path(path).resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")

        # Check if path is within allowed directories
        is_allowed = any(
            self._is_path_within(resolved, allowed)
            for allowed in self._allowed_paths
        )
        if not is_allowed:
            raise ValueError(
                f"Path '{resolved}' is outside allowed directories: "
                f"{[str(p) for p in self._allowed_paths]}"
            )

        # Check blocked patterns
        path_str = str(resolved)
        for pattern in self._blocked_patterns:
            if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(resolved.name, pattern):
                raise ValueError(f"Path matches blocked pattern: {pattern}")

        return resolved

    def _is_path_within(self, path: Path, parent: Path) -> bool:
        """Check if path is within parent directory.

        Args:
            path: Path to check
            parent: Parent directory

        Returns:
            True if path is within parent
        """
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    async def read_file(
        self,
        path: str,
        encoding: str = "utf-8",
        max_size: Optional[int] = None,
    ) -> str:
        """Read file contents.

        Args:
            path: File path
            encoding: File encoding
            max_size: Maximum bytes to read (None = use config default)

        Returns:
            File contents as string

        Raises:
            ValueError: If path is blocked or too large
            FileNotFoundError: If file doesn't exist
        """
        resolved = self.validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")

        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {resolved}")

        # Check file size
        file_size = resolved.stat().st_size
        size_limit = max_size or self._config.max_file_size
        if file_size > size_limit:
            raise ValueError(
                f"File size {file_size} bytes exceeds limit of {size_limit} bytes"
            )

        logger.info(f"Reading file: {resolved} ({file_size} bytes)")

        try:
            return resolved.read_text(encoding=encoding)
        except UnicodeDecodeError:
            # Try reading as binary and decode with error handling
            content = resolved.read_bytes()
            return content.decode(encoding, errors="replace")

    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = False,
    ) -> int:
        """Write content to file.

        Args:
            path: File path
            content: Content to write
            encoding: File encoding
            create_dirs: Create parent directories if needed

        Returns:
            Number of bytes written

        Raises:
            ValueError: If path is blocked or write not allowed
            PermissionError: If write operations are disabled
        """
        if not self._config.allow_write:
            raise PermissionError("Write operations are disabled")

        resolved = self.validate_path(path)

        # Check content size
        content_size = len(content.encode(encoding))
        if content_size > self._config.max_file_size:
            raise ValueError(
                f"Content size {content_size} bytes exceeds limit of "
                f"{self._config.max_file_size} bytes"
            )

        # Create parent directories if needed
        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        elif not resolved.parent.exists():
            raise FileNotFoundError(f"Parent directory does not exist: {resolved.parent}")

        logger.info(f"Writing file: {resolved} ({content_size} bytes)")

        resolved.write_text(content, encoding=encoding)
        return content_size

    async def list_directory(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
        max_depth: Optional[int] = None,
    ) -> List[dict]:
        """List directory contents.

        Args:
            path: Directory path
            pattern: Glob pattern to filter files
            recursive: Include subdirectories
            max_depth: Maximum recursion depth

        Returns:
            List of file/directory info dictionaries
        """
        resolved = self.validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {resolved}")

        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")

        depth_limit = max_depth if max_depth is not None else self._config.max_list_depth

        logger.info(f"Listing directory: {resolved} (pattern={pattern}, recursive={recursive})")

        results = []
        self._list_directory_recursive(
            resolved, pattern, recursive, 0, depth_limit, results
        )

        return results

    def _list_directory_recursive(
        self,
        directory: Path,
        pattern: str,
        recursive: bool,
        current_depth: int,
        max_depth: int,
        results: List[dict],
    ) -> None:
        """Recursively list directory contents.

        Args:
            directory: Directory to list
            pattern: Glob pattern
            recursive: Include subdirectories
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth
            results: Results list to append to
        """
        if current_depth > max_depth:
            return

        try:
            for item in directory.iterdir():
                # Skip blocked patterns
                try:
                    self.validate_path(str(item))
                except ValueError:
                    continue

                # Check pattern match
                if not fnmatch.fnmatch(item.name, pattern):
                    if not (item.is_dir() and recursive):
                        continue

                info = {
                    "name": item.name,
                    "path": str(item),
                    "is_file": item.is_file(),
                    "is_directory": item.is_dir(),
                }

                if item.is_file():
                    try:
                        stat = item.stat()
                        info["size"] = stat.st_size
                        info["modified"] = stat.st_mtime
                    except Exception:
                        pass

                if fnmatch.fnmatch(item.name, pattern):
                    results.append(info)

                # Recurse into subdirectories
                if recursive and item.is_dir():
                    self._list_directory_recursive(
                        item, pattern, recursive, current_depth + 1, max_depth, results
                    )

        except PermissionError as e:
            logger.warning(f"Permission denied listing directory: {directory}: {e}")

    async def delete_file(self, path: str) -> bool:
        """Delete a file.

        Args:
            path: File path to delete

        Returns:
            True if deleted successfully

        Raises:
            PermissionError: If delete operations are disabled
            FileNotFoundError: If file doesn't exist
        """
        if not self._config.allow_delete:
            raise PermissionError("Delete operations are disabled")

        resolved = self.validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")

        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {resolved}")

        logger.info(f"Deleting file: {resolved}")
        resolved.unlink()
        return True

    async def search_files(
        self,
        path: str,
        pattern: str,
        content_pattern: Optional[str] = None,
        max_results: int = 100,
    ) -> List[dict]:
        """Search for files matching patterns.

        Args:
            path: Directory to search in
            pattern: Filename glob pattern
            content_pattern: Optional content search pattern
            max_results: Maximum number of results

        Returns:
            List of matching file info dictionaries
        """
        resolved = self.validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {resolved}")

        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {resolved}")

        logger.info(f"Searching files: {resolved} (pattern={pattern})")

        results = []
        for item in resolved.rglob(pattern):
            if len(results) >= max_results:
                break

            try:
                self.validate_path(str(item))
            except ValueError:
                continue

            if not item.is_file():
                continue

            info = {
                "name": item.name,
                "path": str(item),
                "size": item.stat().st_size,
            }

            # Optional content search
            if content_pattern:
                try:
                    content = item.read_text(errors="ignore")
                    if content_pattern not in content:
                        continue
                    # Find line numbers with matches
                    lines = []
                    for i, line in enumerate(content.split("\n"), 1):
                        if content_pattern in line:
                            lines.append(i)
                    info["matching_lines"] = lines[:10]  # Limit line numbers
                except Exception:
                    continue

            results.append(info)

        return results

    async def get_file_info(self, path: str) -> dict:
        """Get detailed file information.

        Args:
            path: File path

        Returns:
            Dictionary with file metadata
        """
        resolved = self.validate_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"Path not found: {resolved}")

        stat = resolved.stat()

        info = {
            "name": resolved.name,
            "path": str(resolved),
            "is_file": resolved.is_file(),
            "is_directory": resolved.is_dir(),
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
        }

        if resolved.is_file():
            info["extension"] = resolved.suffix
            info["stem"] = resolved.stem

        return info
