"""Shell MCP tools.

Provides tool definitions for shell command execution.

Tools:
    - run_command: Execute a shell command
    - run_script: Execute a script file
"""

import logging
from typing import Any, Dict, List, Optional

from ...core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from .executor import ShellExecutor

logger = logging.getLogger(__name__)


class ShellTools:
    """Shell tools for MCP Server.

    Provides safe shell command execution tools with
    proper security controls.

    Permission Levels:
        - run_command: Level 3 (HIGH) - Requires human approval
        - run_script: Level 3 (HIGH) - Requires human approval

    Example:
        >>> executor = ShellExecutor(config)
        >>> tools = ShellTools(executor)
        >>> result = await tools.run_command("echo hello")
        >>> print(result.content)
    """

    # Permission levels for tools
    PERMISSION_LEVELS = {
        "run_command": 3,  # HIGH - requires human approval
        "run_script": 3,  # HIGH - requires human approval
    }

    def __init__(self, executor: ShellExecutor):
        """Initialize Shell tools.

        Args:
            executor: Shell executor instance
        """
        self._executor = executor

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all Shell tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="run_command",
                description="Execute a shell command. Commands are validated against security rules before execution.",
                parameters=[
                    ToolParameter(
                        name="command",
                        type=ToolInputType.STRING,
                        description="The shell command to execute",
                        required=True,
                    ),
                    ToolParameter(
                        name="timeout",
                        type=ToolInputType.INTEGER,
                        description="Timeout in seconds (default: 60, max: 300)",
                        required=False,
                    ),
                    ToolParameter(
                        name="working_directory",
                        type=ToolInputType.STRING,
                        description="Working directory for command execution",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="run_script",
                description="Execute a script file. Supports .ps1, .sh, .bat, .cmd, .py files.",
                parameters=[
                    ToolParameter(
                        name="script_path",
                        type=ToolInputType.STRING,
                        description="Path to the script file",
                        required=True,
                    ),
                    ToolParameter(
                        name="arguments",
                        type=ToolInputType.ARRAY,
                        description="Script arguments as array of strings",
                        required=False,
                    ),
                    ToolParameter(
                        name="timeout",
                        type=ToolInputType.INTEGER,
                        description="Timeout in seconds (default: 60, max: 300)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="get_shell_info",
                description="Get information about the shell configuration",
                parameters=[],
            ),
        ]

    async def run_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_directory: Optional[str] = None,
    ) -> ToolResult:
        """Execute a shell command.

        Args:
            command: Command to execute
            timeout: Timeout in seconds (max 300)
            working_directory: Working directory (if allowed)

        Returns:
            ToolResult with command output
        """
        try:
            # Validate timeout
            effective_timeout = min(timeout or 60, 300)

            logger.info(f"Executing command: {command[:100]}...")

            result = await self._executor.execute(
                command=command,
                timeout=effective_timeout,
            )

            return ToolResult(
                success=result.exit_code == 0,
                content={
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": round(result.execution_time, 3),
                    "truncated": result.truncated,
                },
                error=result.stderr if result.exit_code != 0 else None,
                metadata={
                    "command": command,
                    "timeout": effective_timeout,
                },
            )

        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def run_script(
        self,
        script_path: str,
        arguments: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """Execute a script file.

        Args:
            script_path: Path to script file
            arguments: Script arguments
            timeout: Timeout in seconds (max 300)

        Returns:
            ToolResult with script output
        """
        try:
            # Validate timeout
            effective_timeout = min(timeout or 60, 300)

            logger.info(f"Executing script: {script_path}")

            result = await self._executor.execute_script(
                script_path=script_path,
                arguments=arguments,
                timeout=effective_timeout,
            )

            return ToolResult(
                success=result.exit_code == 0,
                content={
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": round(result.execution_time, 3),
                    "truncated": result.truncated,
                },
                error=result.stderr if result.exit_code != 0 else None,
                metadata={
                    "script_path": script_path,
                    "arguments": arguments or [],
                    "timeout": effective_timeout,
                },
            )

        except Exception as e:
            logger.error(f"Failed to execute script: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_shell_info(self) -> ToolResult:
        """Get shell configuration information.

        Returns:
            ToolResult with shell info
        """
        config = self._executor._config

        return ToolResult(
            success=True,
            content={
                "shell_type": config.shell_type.value,
                "timeout_seconds": config.timeout_seconds,
                "max_output_size": config.max_output_size,
                "working_directory": config.working_directory,
                "has_whitelist": config.allowed_commands is not None,
                "has_blacklist": config.blocked_commands is not None,
            },
        )
