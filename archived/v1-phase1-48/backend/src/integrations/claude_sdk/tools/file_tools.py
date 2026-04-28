"""File system tools for Claude SDK."""

import os
import glob as glob_module
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

from .base import Tool, ToolResult


class Read(Tool):
    """Read file contents."""

    name = "Read"
    description = "Read file contents. Supports reading specific line ranges."

    def __init__(self, max_chars: int = 100000):
        """
        Initialize Read tool.

        Args:
            max_chars: Maximum characters to read (default: 100000)
        """
        self.max_chars = max_chars

    async def execute(
        self,
        path: str,
        encoding: str = "utf-8",
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> ToolResult:
        """
        Read file contents.

        Args:
            path: File path (absolute or relative)
            encoding: Text encoding (default: utf-8)
            start_line: Start reading from this line (1-indexed)
            end_line: Stop reading at this line (inclusive)

        Returns:
            ToolResult with file content
        """
        try:
            abs_path = os.path.abspath(path)

            if not os.path.exists(abs_path):
                return ToolResult(
                    content="",
                    success=False,
                    error=f"File not found: {path}",
                )

            if os.path.isdir(abs_path):
                return ToolResult(
                    content="",
                    success=False,
                    error=f"Path is a directory, not a file: {path}",
                )

            with open(abs_path, "r", encoding=encoding, errors="replace") as f:
                if start_line is not None or end_line is not None:
                    lines = f.readlines()
                    start = (start_line or 1) - 1
                    end = end_line or len(lines)
                    content = "".join(lines[start:end])
                else:
                    content = f.read()

            if len(content) > self.max_chars:
                content = (
                    content[: self.max_chars]
                    + f"\n... (truncated at {self.max_chars} chars)"
                )

            return ToolResult(content=content)

        except UnicodeDecodeError as e:
            return ToolResult(
                content="",
                success=False,
                error=f"Encoding error: {e}. Try a different encoding.",
            )
        except Exception as e:
            return ToolResult(content="", success=False, error=str(e))

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Start line (1-indexed)",
                },
                "end_line": {
                    "type": "integer",
                    "description": "End line (inclusive)",
                },
            },
            "required": ["path"],
        }


class Write(Tool):
    """Write content to a file."""

    name = "Write"
    description = "Write content to a file. Can create parent directories."

    async def execute(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = False,
        overwrite: bool = True,
    ) -> ToolResult:
        """
        Write content to file.

        Args:
            path: File path
            content: Content to write
            encoding: Text encoding
            create_dirs: Create parent directories if needed
            overwrite: Overwrite if file exists

        Returns:
            ToolResult indicating success or failure
        """
        try:
            abs_path = os.path.abspath(path)

            if not overwrite and os.path.exists(abs_path):
                return ToolResult(
                    content="",
                    success=False,
                    error=f"File already exists: {path}",
                )

            parent_dir = os.path.dirname(abs_path)
            if not os.path.exists(parent_dir):
                if create_dirs:
                    os.makedirs(parent_dir, exist_ok=True)
                else:
                    return ToolResult(
                        content="",
                        success=False,
                        error=f"Parent directory does not exist: {parent_dir}",
                    )

            with open(abs_path, "w", encoding=encoding) as f:
                f.write(content)

            return ToolResult(
                content=f"Successfully wrote {len(content)} chars to {path}"
            )

        except Exception as e:
            return ToolResult(content="", success=False, error=str(e))

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
                "encoding": {"type": "string", "default": "utf-8"},
                "create_dirs": {
                    "type": "boolean",
                    "default": False,
                    "description": "Create parent directories if needed",
                },
                "overwrite": {
                    "type": "boolean",
                    "default": True,
                    "description": "Overwrite if file exists",
                },
            },
            "required": ["path", "content"],
        }


class Edit(Tool):
    """Edit existing file content."""

    name = "Edit"
    description = "Edit file by replacing text. Supports replace all occurrences."

    async def execute(
        self,
        path: str,
        old_text: str,
        new_text: str,
        replace_all: bool = False,
    ) -> ToolResult:
        """
        Edit file by replacing text.

        Args:
            path: File path
            old_text: Text to find
            new_text: Replacement text
            replace_all: Replace all occurrences

        Returns:
            ToolResult indicating success or failure
        """
        try:
            abs_path = os.path.abspath(path)

            if not os.path.exists(abs_path):
                return ToolResult(
                    content="",
                    success=False,
                    error=f"File not found: {path}",
                )

            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if old_text not in content:
                preview = old_text[:50] + "..." if len(old_text) > 50 else old_text
                return ToolResult(
                    content="",
                    success=False,
                    error=f"Text not found in file: {preview}",
                )

            if replace_all:
                count = content.count(old_text)
                new_content = content.replace(old_text, new_text)
            else:
                new_content = content.replace(old_text, new_text, 1)
                count = 1

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(content=f"Replaced {count} occurrence(s) in {path}")

        except Exception as e:
            return ToolResult(content="", success=False, error=str(e))

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "old_text": {"type": "string", "description": "Text to find"},
                "new_text": {"type": "string", "description": "Replacement text"},
                "replace_all": {
                    "type": "boolean",
                    "default": False,
                    "description": "Replace all occurrences",
                },
            },
            "required": ["path", "old_text", "new_text"],
        }


class MultiEdit(Tool):
    """Apply multiple edits atomically."""

    name = "MultiEdit"
    description = "Apply multiple edits to files atomically."

    async def execute(self, edits: List[Dict[str, str]]) -> ToolResult:
        """
        Apply multiple edits.

        Args:
            edits: List of edit operations, each with path, old_text, new_text

        Returns:
            ToolResult indicating success or failure
        """
        if not edits:
            return ToolResult(content="", success=False, error="No edits provided")

        edit_tool = Edit()
        results = []
        failed = []

        for i, edit in enumerate(edits):
            # Validate edit structure
            if not all(k in edit for k in ["path", "old_text", "new_text"]):
                failed.append(
                    f"Edit {i + 1}: Missing required fields (path, old_text, new_text)"
                )
                continue

            result = await edit_tool.execute(
                path=edit["path"],
                old_text=edit["old_text"],
                new_text=edit["new_text"],
                replace_all=edit.get("replace_all", False),
            )

            if result.success:
                results.append(f"Edit {i + 1}: {result.content}")
            else:
                failed.append(f"Edit {i + 1} failed: {result.error}")

        if failed:
            return ToolResult(
                content="\n".join(results + failed),
                success=False,
                error=f"{len(failed)} edit(s) failed",
            )

        return ToolResult(content=f"Applied {len(edits)} edits successfully")

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "old_text": {"type": "string"},
                            "new_text": {"type": "string"},
                            "replace_all": {"type": "boolean", "default": False},
                        },
                        "required": ["path", "old_text", "new_text"],
                    },
                    "description": "List of edit operations",
                },
            },
            "required": ["edits"],
        }


class Glob(Tool):
    """Find files by pattern."""

    name = "Glob"
    description = "Find files matching a glob pattern."

    def __init__(self, max_files: int = 10000):
        """
        Initialize Glob tool.

        Args:
            max_files: Maximum files to return (default: 10000)
        """
        self.max_files = max_files

    async def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        exclude: Optional[List[str]] = None,
        include_hidden: bool = False,
    ) -> ToolResult:
        """
        Find files by pattern.

        Args:
            pattern: Glob pattern (e.g., **/*.py)
            path: Base directory
            exclude: Patterns to exclude
            include_hidden: Include hidden files

        Returns:
            ToolResult with matching file paths
        """
        try:
            base_path = os.path.abspath(path or ".")
            full_pattern = os.path.join(base_path, pattern)

            files = glob_module.glob(full_pattern, recursive=True)

            # Filter excludes
            if exclude:
                excluded_files = set()
                for exc in exclude:
                    exc_pattern = os.path.join(base_path, exc)
                    excluded_files.update(
                        glob_module.glob(exc_pattern, recursive=True)
                    )
                files = [f for f in files if f not in excluded_files]

            # Filter hidden files
            if not include_hidden:
                files = [
                    f
                    for f in files
                    if not any(part.startswith(".") for part in Path(f).parts)
                ]

            # Filter directories (only return files)
            files = [f for f in files if os.path.isfile(f)]

            # Sort by modification time (most recent first)
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            # Limit results
            truncated = len(files) > self.max_files
            if truncated:
                files = files[: self.max_files]

            result = "\n".join(files) if files else "No matching files found"
            if truncated:
                result += f"\n... (truncated at {self.max_files} files)"

            return ToolResult(content=result)

        except Exception as e:
            return ToolResult(content="", success=False, error=str(e))

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., **/*.py)",
                },
                "path": {
                    "type": "string",
                    "description": "Base directory (default: current directory)",
                },
                "exclude": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Patterns to exclude",
                },
                "include_hidden": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include hidden files",
                },
            },
            "required": ["pattern"],
        }


class Grep(Tool):
    """Search file contents."""

    name = "Grep"
    description = "Search for patterns in file contents."

    def __init__(self, max_matches: int = 1000):
        """
        Initialize Grep tool.

        Args:
            max_matches: Maximum matches to return (default: 1000)
        """
        self.max_matches = max_matches

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        regex: bool = False,
        case_sensitive: bool = True,
        before: int = 0,
        after: int = 0,
        max_matches: Optional[int] = None,
        file_pattern: Optional[str] = None,
    ) -> ToolResult:
        """
        Search file contents.

        Args:
            pattern: Search pattern
            path: File or directory path
            regex: Use regex matching
            case_sensitive: Case sensitive search
            before: Context lines before match
            after: Context lines after match
            max_matches: Limit results
            file_pattern: Glob pattern for files to search

        Returns:
            ToolResult with matching lines
        """
        try:
            abs_path = os.path.abspath(path)
            limit = max_matches or self.max_matches
            matches = []

            # Get files to search
            if os.path.isfile(abs_path):
                files = [abs_path]
            else:
                if file_pattern:
                    full_pattern = os.path.join(abs_path, file_pattern)
                    files = glob_module.glob(full_pattern, recursive=True)
                else:
                    files = glob_module.glob(
                        os.path.join(abs_path, "**/*"), recursive=True
                    )
                files = [f for f in files if os.path.isfile(f)]

            # Compile pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            if regex:
                try:
                    compiled = re.compile(pattern, flags)
                except re.error as e:
                    return ToolResult(
                        content="",
                        success=False,
                        error=f"Invalid regex pattern: {e}",
                    )
            else:
                compiled = re.compile(re.escape(pattern), flags)

            for filepath in files:
                if len(matches) >= limit:
                    break

                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        if compiled.search(line):
                            match_lines = []

                            # Add context before
                            start = max(0, i - before)
                            for j in range(start, i):
                                match_lines.append(f"  {j + 1}: {lines[j].rstrip()}")

                            # Add match line
                            match_lines.append(f"→ {i + 1}: {line.rstrip()}")

                            # Add context after
                            end = min(len(lines), i + after + 1)
                            for j in range(i + 1, end):
                                match_lines.append(f"  {j + 1}: {lines[j].rstrip()}")

                            matches.append(f"{filepath}:\n" + "\n".join(match_lines))

                            if len(matches) >= limit:
                                break

                except Exception:
                    # Skip files that can't be read
                    continue

            result = "\n\n".join(matches) if matches else "No matches found"
            if len(matches) >= limit:
                result += f"\n\n... (limited to {limit} matches)"

            return ToolResult(content=result)

        except Exception as e:
            return ToolResult(content="", success=False, error=str(e))

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search pattern"},
                "path": {
                    "type": "string",
                    "default": ".",
                    "description": "File or directory path",
                },
                "regex": {
                    "type": "boolean",
                    "default": False,
                    "description": "Use regex matching",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "default": True,
                    "description": "Case sensitive search",
                },
                "before": {
                    "type": "integer",
                    "default": 0,
                    "description": "Context lines before match",
                },
                "after": {
                    "type": "integer",
                    "default": 0,
                    "description": "Context lines after match",
                },
                "max_matches": {
                    "type": "integer",
                    "description": "Limit number of matches",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern for files to search",
                },
            },
            "required": ["pattern"],
        }
