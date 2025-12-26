"""Sandbox Hook for Claude SDK.

Sprint 49: S49-3 - Hooks System (10 pts)
Restricts file access to allowed paths and blocks dangerous operations.
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
