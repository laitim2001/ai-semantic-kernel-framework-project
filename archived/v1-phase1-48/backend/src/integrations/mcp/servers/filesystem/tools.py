"""Filesystem MCP tools.

Provides tool definitions for filesystem operations.

Tools:
    - read_file: Read file contents
    - write_file: Write content to file
    - list_directory: List directory contents
    - search_files: Search for files
    - get_file_info: Get file metadata
    - delete_file: Delete a file (requires permission)
"""

import logging
from typing import Any, Dict, List, Optional

from ...core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from .sandbox import FilesystemSandbox

logger = logging.getLogger(__name__)


class FilesystemTools:
    """Filesystem tools for MCP Server.

    Provides safe filesystem operations through the MCP protocol.

    Permission Levels:
        - read_file: Level 1 (READ) - Low risk
        - list_directory: Level 1 (READ) - Low risk
        - search_files: Level 1 (READ) - Low risk
        - get_file_info: Level 1 (READ) - Low risk
        - write_file: Level 2 (EXECUTE) - Requires approval
        - delete_file: Level 3 (HIGH) - Requires human approval

    Example:
        >>> sandbox = FilesystemSandbox(config)
        >>> tools = FilesystemTools(sandbox)
        >>> result = await tools.read_file(path="/path/to/file.txt")
    """

    PERMISSION_LEVELS = {
        "read_file": 1,       # READ - low risk
        "list_directory": 1,  # READ - low risk
        "search_files": 1,    # READ - low risk
        "get_file_info": 1,   # READ - low risk
        "write_file": 2,      # EXECUTE - requires approval
        "delete_file": 3,     # HIGH - requires human approval
    }

    def __init__(self, sandbox: FilesystemSandbox):
        """Initialize Filesystem tools.

        Args:
            sandbox: Filesystem sandbox instance
        """
        self._sandbox = sandbox

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all Filesystem tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="read_file",
                description="Read the contents of a file. Returns the file content as text.",
                parameters=[
                    ToolParameter(
                        name="path",
                        type=ToolInputType.STRING,
                        description="Path to the file to read",
                        required=True,
                    ),
                    ToolParameter(
                        name="encoding",
                        type=ToolInputType.STRING,
                        description="File encoding (default: utf-8)",
                        required=False,
                    ),
                    ToolParameter(
                        name="max_size",
                        type=ToolInputType.INTEGER,
                        description="Maximum bytes to read (default: 10MB)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="write_file",
                description="Write content to a file. Creates the file if it doesn't exist.",
                parameters=[
                    ToolParameter(
                        name="path",
                        type=ToolInputType.STRING,
                        description="Path to the file to write",
                        required=True,
                    ),
                    ToolParameter(
                        name="content",
                        type=ToolInputType.STRING,
                        description="Content to write to the file",
                        required=True,
                    ),
                    ToolParameter(
                        name="encoding",
                        type=ToolInputType.STRING,
                        description="File encoding (default: utf-8)",
                        required=False,
                    ),
                    ToolParameter(
                        name="create_dirs",
                        type=ToolInputType.BOOLEAN,
                        description="Create parent directories if needed (default: false)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="list_directory",
                description="List contents of a directory.",
                parameters=[
                    ToolParameter(
                        name="path",
                        type=ToolInputType.STRING,
                        description="Path to the directory to list",
                        required=True,
                    ),
                    ToolParameter(
                        name="pattern",
                        type=ToolInputType.STRING,
                        description="Glob pattern to filter files (default: *)",
                        required=False,
                    ),
                    ToolParameter(
                        name="recursive",
                        type=ToolInputType.BOOLEAN,
                        description="Include subdirectories (default: false)",
                        required=False,
                    ),
                    ToolParameter(
                        name="max_depth",
                        type=ToolInputType.INTEGER,
                        description="Maximum recursion depth (default: 10)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="search_files",
                description="Search for files matching a pattern. Optionally search within file contents.",
                parameters=[
                    ToolParameter(
                        name="path",
                        type=ToolInputType.STRING,
                        description="Directory to search in",
                        required=True,
                    ),
                    ToolParameter(
                        name="pattern",
                        type=ToolInputType.STRING,
                        description="Filename glob pattern (e.g., '*.py', 'config*')",
                        required=True,
                    ),
                    ToolParameter(
                        name="content_pattern",
                        type=ToolInputType.STRING,
                        description="Search for this text within file contents",
                        required=False,
                    ),
                    ToolParameter(
                        name="max_results",
                        type=ToolInputType.INTEGER,
                        description="Maximum number of results (default: 100)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="get_file_info",
                description="Get detailed information about a file or directory.",
                parameters=[
                    ToolParameter(
                        name="path",
                        type=ToolInputType.STRING,
                        description="Path to the file or directory",
                        required=True,
                    ),
                ],
            ),
            ToolSchema(
                name="delete_file",
                description="Delete a file. Requires delete permission to be enabled.",
                parameters=[
                    ToolParameter(
                        name="path",
                        type=ToolInputType.STRING,
                        description="Path to the file to delete",
                        required=True,
                    ),
                ],
            ),
        ]

    async def read_file(
        self,
        path: str,
        encoding: str = "utf-8",
        max_size: Optional[int] = None,
    ) -> ToolResult:
        """Read file contents.

        Args:
            path: File path
            encoding: File encoding
            max_size: Maximum bytes to read

        Returns:
            ToolResult with file contents
        """
        try:
            content = await self._sandbox.read_file(
                path=path,
                encoding=encoding,
                max_size=max_size,
            )

            return ToolResult(
                success=True,
                content={
                    "path": path,
                    "content": content,
                    "size": len(content),
                    "encoding": encoding,
                },
            )

        except FileNotFoundError as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except (ValueError, PermissionError) as e:
            logger.warning(f"Read file blocked: {path} - {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Read error: {e}",
            )

    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = False,
    ) -> ToolResult:
        """Write content to file.

        Args:
            path: File path
            content: Content to write
            encoding: File encoding
            create_dirs: Create parent directories if needed

        Returns:
            ToolResult with write status
        """
        try:
            bytes_written = await self._sandbox.write_file(
                path=path,
                content=content,
                encoding=encoding,
                create_dirs=create_dirs,
            )

            return ToolResult(
                success=True,
                content={
                    "path": path,
                    "bytes_written": bytes_written,
                    "message": f"Successfully wrote {bytes_written} bytes",
                },
            )

        except (PermissionError, ValueError) as e:
            logger.warning(f"Write file blocked: {path} - {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Write error: {e}",
            )

    async def list_directory(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
        max_depth: Optional[int] = None,
    ) -> ToolResult:
        """List directory contents.

        Args:
            path: Directory path
            pattern: Glob pattern to filter
            recursive: Include subdirectories
            max_depth: Maximum recursion depth

        Returns:
            ToolResult with directory listing
        """
        try:
            items = await self._sandbox.list_directory(
                path=path,
                pattern=pattern,
                recursive=recursive,
                max_depth=max_depth,
            )

            return ToolResult(
                success=True,
                content={
                    "path": path,
                    "pattern": pattern,
                    "recursive": recursive,
                    "count": len(items),
                    "items": items,
                },
            )

        except (FileNotFoundError, ValueError) as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Failed to list directory: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"List error: {e}",
            )

    async def search_files(
        self,
        path: str,
        pattern: str,
        content_pattern: Optional[str] = None,
        max_results: int = 100,
    ) -> ToolResult:
        """Search for files.

        Args:
            path: Directory to search
            pattern: Filename glob pattern
            content_pattern: Content search pattern
            max_results: Maximum results

        Returns:
            ToolResult with search results
        """
        try:
            results = await self._sandbox.search_files(
                path=path,
                pattern=pattern,
                content_pattern=content_pattern,
                max_results=max_results,
            )

            return ToolResult(
                success=True,
                content={
                    "path": path,
                    "pattern": pattern,
                    "content_pattern": content_pattern,
                    "count": len(results),
                    "results": results,
                },
            )

        except (FileNotFoundError, ValueError) as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Failed to search files: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Search error: {e}",
            )

    async def get_file_info(self, path: str) -> ToolResult:
        """Get file information.

        Args:
            path: File path

        Returns:
            ToolResult with file metadata
        """
        try:
            info = await self._sandbox.get_file_info(path)

            return ToolResult(
                success=True,
                content=info,
            )

        except (FileNotFoundError, ValueError) as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Info error: {e}",
            )

    async def delete_file(self, path: str) -> ToolResult:
        """Delete a file.

        Args:
            path: File path to delete

        Returns:
            ToolResult with deletion status
        """
        try:
            await self._sandbox.delete_file(path)

            return ToolResult(
                success=True,
                content={
                    "path": path,
                    "message": "File deleted successfully",
                },
            )

        except (PermissionError, FileNotFoundError, ValueError) as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Delete error: {e}",
            )
