"""Sandbox Hook for Claude SDK.

Sprint 49: S49-3 - Hooks System (10 pts)
Sprint 68: S68-2 - UserSandboxHook for Per-User Isolation (5 pts)

Restricts file access to allowed paths and blocks dangerous operations.
Supports per-user sandbox isolation for secure agent operations.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Set

from .base import Hook
from ..types import HookResult, ToolCallContext


# Default blocked path patterns
DEFAULT_BLOCKED_PATTERNS: List[str] = [
    # System directories
    r"^/etc/",
    r"^/usr/",
    r"^/bin/",
    r"^/sbin/",
    r"^/boot/",
    r"^/sys/",
    r"^/proc/",
    r"^/dev/",

    # Windows system directories
    r"^[A-Za-z]:\\Windows\\",
    r"^[A-Za-z]:\\Program Files",
    r"^[A-Za-z]:\\ProgramData\\",

    # Home directory sensitive files
    r"\.ssh/",
    r"\.gnupg/",
    r"\.aws/",
    r"\.azure/",
    r"\.config/",

    # Sensitive files
    r"\.env$",
    r"\.env\.",
    r"credentials",
    r"secrets?\.ya?ml",
    r"\.pem$",
    r"\.key$",
    r"id_rsa",
    r"id_ed25519",
]

# Tools that access files
FILE_ACCESS_TOOLS: Set[str] = {
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Glob",
    "Grep",
}


class SandboxHook(Hook):
    """Hook that restricts file access to allowed paths.

    Provides two modes of operation:
    1. Allowlist mode: Only allow access to specified paths
    2. Blocklist mode: Block access to specified patterns

    Args:
        allowed_paths: List of allowed directory paths (None = all paths allowed)
        blocked_patterns: Additional regex patterns to block
        allow_reads: Whether to allow read operations outside allowed paths
        allow_temp: Whether to allow access to temp directory
        working_directory: Base directory for relative paths

    Example:
        # Only allow access to project directory
        hook = SandboxHook(allowed_paths=["/project"])

        # Block sensitive files but allow everything else
        hook = SandboxHook(
            allowed_paths=None,
            blocked_patterns=[r"\\.env$", r"secrets\\.yaml$"]
        )
    """

    name: str = "sandbox"
    priority: int = 85  # High priority - check early

    def __init__(
        self,
        allowed_paths: Optional[List[str]] = None,
        blocked_patterns: Optional[List[str]] = None,
        allow_reads: bool = True,
        allow_temp: bool = True,
        working_directory: Optional[str] = None,
    ):
        self.allowed_paths: Optional[List[Path]] = None
        if allowed_paths is not None:
            self.allowed_paths = [Path(p).resolve() for p in allowed_paths]

        self.allow_reads = allow_reads
        self.allow_temp = allow_temp
        self.working_directory = Path(working_directory).resolve() if working_directory else None

        # Compile blocked patterns
        patterns = DEFAULT_BLOCKED_PATTERNS.copy()
        if blocked_patterns:
            patterns.extend(blocked_patterns)
        self._blocked_patterns: List[Pattern] = [
            re.compile(p, re.IGNORECASE) for p in patterns
        ]

        # Get temp directory
        self._temp_dir = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp"))).resolve()

        # Write operation tools
        self._write_tools: Set[str] = {"Write", "Edit", "MultiEdit"}

    async def on_tool_call(self, context: ToolCallContext) -> HookResult:
        """Check if tool call is within sandbox."""
        tool_name = context.tool_name

        # Only check file access tools
        if tool_name not in FILE_ACCESS_TOOLS:
            return HookResult.ALLOW

        # Extract file path from args
        file_path = self._extract_path(context.args)
        if not file_path:
            return HookResult.ALLOW

        # Resolve path
        resolved_path = self._resolve_path(file_path)

        # Check if path is blocked
        block_result = self._check_blocked_patterns(str(resolved_path))
        if block_result:
            return HookResult.reject(
                f"Access blocked: path matches blocked pattern '{block_result}'"
            )

        # Check if in allowed paths
        if self.allowed_paths is not None:
            is_write = tool_name in self._write_tools

            # Allow reads outside sandbox if configured
            if not is_write and self.allow_reads:
                return HookResult.ALLOW

            # Allow temp directory if configured
            if self.allow_temp and self._is_temp_path(resolved_path):
                return HookResult.ALLOW

            # Check if in allowed paths
            if not self._is_in_allowed_paths(resolved_path):
                return HookResult.reject(
                    f"Access denied: '{file_path}' is outside allowed paths"
                )

        return HookResult.ALLOW

    def _extract_path(self, args: Dict) -> Optional[str]:
        """Extract file path from tool arguments."""
        # Common path argument names
        for key in ["file_path", "path", "pattern"]:
            if key in args:
                value = args[key]
                if isinstance(value, str):
                    return value

        # For MultiEdit, check edits
        if "edits" in args:
            edits = args["edits"]
            if isinstance(edits, list) and edits:
                first_edit = edits[0]
                if isinstance(first_edit, dict) and "file_path" in first_edit:
                    return first_edit["file_path"]

        return None

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a file path to absolute path."""
        path = Path(file_path)

        if not path.is_absolute():
            # Use working directory if set
            if self.working_directory:
                path = self.working_directory / path
            else:
                path = Path.cwd() / path

        return path.resolve()

    def _check_blocked_patterns(self, path_str: str) -> Optional[str]:
        """Check if path matches any blocked pattern.

        Returns the matching pattern or None.
        """
        # Normalize path for pattern matching
        normalized = path_str.replace("\\", "/")

        for pattern in self._blocked_patterns:
            if pattern.search(normalized):
                return pattern.pattern

        return None

    def _is_in_allowed_paths(self, path: Path) -> bool:
        """Check if path is within allowed paths."""
        if self.allowed_paths is None:
            return True

        for allowed in self.allowed_paths:
            try:
                # Check if path is under allowed path
                path.relative_to(allowed)
                return True
            except ValueError:
                continue

        return False

    def _is_temp_path(self, path: Path) -> bool:
        """Check if path is in temp directory."""
        try:
            path.relative_to(self._temp_dir)
            return True
        except ValueError:
            return False

    def add_allowed_path(self, path: str) -> None:
        """Add a path to the allowed list."""
        if self.allowed_paths is None:
            self.allowed_paths = []
        self.allowed_paths.append(Path(path).resolve())

    def remove_allowed_path(self, path: str) -> None:
        """Remove a path from the allowed list."""
        if self.allowed_paths is not None:
            resolved = Path(path).resolve()
            self.allowed_paths = [p for p in self.allowed_paths if p != resolved]

    def add_blocked_pattern(self, pattern: str) -> None:
        """Add a pattern to the block list."""
        self._blocked_patterns.append(re.compile(pattern, re.IGNORECASE))

    def set_working_directory(self, path: str) -> None:
        """Set the working directory for relative paths."""
        self.working_directory = Path(path).resolve()

    def get_allowed_paths(self) -> List[str]:
        """Get list of allowed paths."""
        if self.allowed_paths is None:
            return []
        return [str(p) for p in self.allowed_paths]

    def get_blocked_patterns(self) -> List[str]:
        """Get list of blocked patterns."""
        return [p.pattern for p in self._blocked_patterns]


class StrictSandboxHook(SandboxHook):
    """Stricter sandbox that requires explicit path allowlist.

    This variant:
    - Requires allowed_paths to be set
    - Blocks all reads outside allowed paths
    - Blocks temp directory access by default
    """

    name: str = "strict_sandbox"

    def __init__(
        self,
        allowed_paths: List[str],
        blocked_patterns: Optional[List[str]] = None,
        working_directory: Optional[str] = None,
    ):
        if not allowed_paths:
            raise ValueError("StrictSandboxHook requires at least one allowed path")

        super().__init__(
            allowed_paths=allowed_paths,
            blocked_patterns=blocked_patterns,
            allow_reads=False,
            allow_temp=False,
            working_directory=working_directory,
        )


# =============================================================================
# Sprint 68: Per-User Sandbox Isolation
# =============================================================================

# Source code directories to block (absolute block, no read or write)
SOURCE_CODE_BLOCKED_PATTERNS: List[str] = [
    # Backend source
    r"^backend/",
    r"backend/src/",
    r"backend/tests/",
    # Frontend source
    r"^frontend/",
    r"frontend/src/",
    r"frontend/node_modules/",
    # General source
    r"^src/",
    r"^scripts/",
    r"^docs/",
    r"^tests/",
    # Configuration
    r"^\.claude/",
    r"^\.git/",
    r"^\.github/",
    # Config files
    r"\.env$",
    r"\.env\.",
    r"pyproject\.toml$",
    r"package\.json$",
    r"tsconfig\.json$",
    r"alembic\.ini$",
    r"docker-compose",
    r"Dockerfile",
    r"requirements\.txt$",
]

# File extensions blocked for write operations
BLOCKED_WRITE_EXTENSIONS: Set[str] = {
    # Code files
    ".py", ".pyx", ".pyi",
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".java", ".kt", ".scala",
    ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".cs", ".fs",
    # Shell scripts
    ".sh", ".bash", ".zsh", ".fish",
    ".bat", ".cmd", ".ps1", ".psm1",
    # Config files
    ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".json",  # Only block write, allow read
    # Database
    ".sql", ".db", ".sqlite", ".sqlite3",
    # Markup (code)
    ".vue", ".svelte", ".astro",
}


class UserSandboxHook(SandboxHook):
    """Per-user sandbox hook for secure agent operations.

    Automatically configures:
    - Allowed paths: user's data directories (uploads, sandbox, outputs)
    - Blocked patterns: source code directories and sensitive files
    - Write restrictions: code files and configuration

    This is the recommended sandbox hook for agentic chat operations.

    Args:
        user_id: User identifier (e.g., "guest-abc-123" or authenticated user ID)
        data_base_dir: Base directory for data (default: "data")
        block_source_code: Whether to block access to source code (default: True)
        allow_temp: Whether to allow temp directory access (default: True)

    Example:
        # Create per-user sandbox
        hook = UserSandboxHook(user_id="guest-abc-123")

        # Add to Claude SDK client
        client = ClaudeSDKClient(hooks=[hook])
    """

    name: str = "user_sandbox"

    def __init__(
        self,
        user_id: str,
        data_base_dir: str = "data",
        block_source_code: bool = True,
        allow_temp: bool = True,
    ):
        self.user_id = user_id
        self.data_base_dir = data_base_dir

        # Calculate user's allowed paths
        base = Path.cwd() / data_base_dir
        user_dirs = [
            str(base / "uploads" / user_id),
            str(base / "sandbox" / user_id),
            str(base / "outputs" / user_id),
        ]

        # Add temp directory if allowed
        if allow_temp:
            user_dirs.append(str(base / "temp"))

        # Build blocked patterns
        blocked = []
        if block_source_code:
            blocked.extend(SOURCE_CODE_BLOCKED_PATTERNS)

        super().__init__(
            allowed_paths=user_dirs,
            blocked_patterns=blocked,
            allow_reads=False,  # Strict mode - only allow sandbox paths
            allow_temp=allow_temp,
            working_directory=str(base / "sandbox" / user_id),
        )

        # Store blocked write extensions
        self._blocked_write_extensions = BLOCKED_WRITE_EXTENSIONS.copy()

    async def on_tool_call(self, context: ToolCallContext) -> HookResult:
        """Check if tool call is within user sandbox.

        Extends base implementation with:
        - Write extension restrictions
        - Logging of blocked attempts
        """
        tool_name = context.tool_name

        # Only check file access tools
        if tool_name not in FILE_ACCESS_TOOLS:
            return HookResult.ALLOW

        # Extract file path from args
        file_path = self._extract_path(context.args)
        if not file_path:
            return HookResult.ALLOW

        # Check write extension restrictions
        if tool_name in self._write_tools:
            ext = Path(file_path).suffix.lower()
            if ext in self._blocked_write_extensions:
                return HookResult.reject(
                    f"Writing to '{ext}' files is not allowed for security reasons"
                )

        # Delegate to parent for path validation
        result = await super().on_tool_call(context)

        # Log blocked attempts (could integrate with audit hook)
        if result.action == "reject":
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Sandbox blocked: user={self.user_id}, "
                f"tool={tool_name}, path={file_path}, reason={result.message}"
            )

        return result

    def ensure_user_dirs(self) -> Dict[str, Path]:
        """Create user directories if they don't exist.

        Returns:
            Dictionary mapping directory type to Path
        """
        from src.core.sandbox_config import SandboxConfig
        return SandboxConfig.ensure_user_dirs(self.user_id)

    def get_user_dir(self, dir_type: str) -> Path:
        """Get a specific user directory.

        Args:
            dir_type: "uploads", "sandbox", or "outputs"

        Returns:
            Path to user directory
        """
        from src.core.sandbox_config import SandboxConfig
        return SandboxConfig.get_user_dir(self.user_id, dir_type)

    @classmethod
    def for_guest(cls, guest_id: str) -> "UserSandboxHook":
        """Create sandbox hook for guest user.

        Convenience factory for guest users.

        Args:
            guest_id: Guest user ID (e.g., "guest-abc-123")

        Returns:
            Configured UserSandboxHook
        """
        return cls(user_id=guest_id, block_source_code=True)

    @classmethod
    def for_authenticated(cls, user_id: str) -> "UserSandboxHook":
        """Create sandbox hook for authenticated user.

        Same as guest but with potential for extended permissions.

        Args:
            user_id: Authenticated user ID

        Returns:
            Configured UserSandboxHook
        """
        return cls(user_id=user_id, block_source_code=True)
