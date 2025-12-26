"""Command execution tools for Claude SDK.

Sprint 49: S49-2 - Bash and Task Tools (6 pts)
"""

import asyncio
import os
import re
from typing import Optional, List, Dict, Any

from .base import Tool, ToolResult


class Bash(Tool):
    """Execute shell commands with security controls."""

    name = "Bash"
    description = "Execute shell commands with security controls."

    # Default dangerous patterns
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",
        r":()\s*{\s*:|:&\s*};\s*:",  # Fork bomb
        r">\s*/dev/sd",
        r"mkfs\.",
        r"dd\s+if=",
        r"curl\s+.*\|\s*bash",
        r"wget\s+.*\|\s*sh",
        r"format\s+[a-z]:",  # Windows format command
        r"del\s+/[fqs]",  # Windows dangerous delete
    ]

    def __init__(
        self,
        allowed_commands: Optional[List[str]] = None,
        denied_commands: Optional[List[str]] = None,
        timeout: int = 120,
        max_output: int = 100000,
    ):
        """
        Initialize Bash tool.

        Args:
            allowed_commands: Whitelist of allowed command prefixes
            denied_commands: Blacklist of denied command patterns
            timeout: Default timeout in seconds
            max_output: Maximum output characters
        """
        self.allowed_commands = allowed_commands
        self.denied_commands = denied_commands or []
        self.timeout = timeout
        self.max_output = max_output

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ToolResult:
        """
        Execute a shell command.

        Args:
            command: Command to execute
            cwd: Working directory
            timeout: Timeout in seconds
            env: Environment variables

        Returns:
            ToolResult with stdout, stderr, and exit code
        """
        try:
            # Security checks
            security_result = self._check_security(command)
            if not security_result.success:
                return security_result

            # Set up environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)

            # Set working directory
            working_dir = cwd or os.getcwd()
            if not os.path.isdir(working_dir):
                return ToolResult(
                    content="",
                    success=False,
                    error=f"Working directory not found: {working_dir}",
                )

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=exec_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout or self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    content="",
                    success=False,
                    error=f"Command timed out after {timeout or self.timeout}s",
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Truncate if needed
            if len(stdout_str) > self.max_output:
                stdout_str = stdout_str[: self.max_output] + "\n... (truncated)"
            if len(stderr_str) > self.max_output:
                stderr_str = stderr_str[: self.max_output] + "\n... (truncated)"

            output = f"Exit code: {process.returncode}\n"
            if stdout_str:
                output += f"\nSTDOUT:\n{stdout_str}"
            if stderr_str:
                output += f"\nSTDERR:\n{stderr_str}"

            return ToolResult(
                content=output,
                success=process.returncode == 0,
            )

        except Exception as e:
            return ToolResult(content="", success=False, error=str(e))

    def _check_security(self, command: str) -> ToolResult:
        """Check command against security rules."""
        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return ToolResult(
                    content="",
                    success=False,
                    error=f"Blocked dangerous command pattern: {pattern}",
                )

        # Check denied commands
        for denied in self.denied_commands:
            if denied in command:
                return ToolResult(
                    content="",
                    success=False,
                    error=f"Command denied: {denied}",
                )

        # Check allowed commands (if specified)
        if self.allowed_commands:
            cmd_parts = command.split()
            if cmd_parts and cmd_parts[0] not in self.allowed_commands:
                return ToolResult(
                    content="",
                    success=False,
                    error=f"Command not in allowed list: {cmd_parts[0]}",
                )

        return ToolResult(content="", success=True)

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to execute"},
                "cwd": {
                    "type": "string",
                    "description": "Working directory for command execution",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 120)",
                },
                "env": {
                    "type": "object",
                    "description": "Additional environment variables",
                },
            },
            "required": ["command"],
        }


class Task(Tool):
    """Delegate subtasks to specialized subagents."""

    name = "Task"
    description = "Delegate complex subtasks to specialized subagents."

    def __init__(
        self,
        default_tools: Optional[List[str]] = None,
        max_tokens: int = 8192,
        default_timeout: int = 300,
    ):
        """
        Initialize Task tool.

        Args:
            default_tools: Default tools available to subagents
            max_tokens: Default max tokens for subagent
            default_timeout: Default timeout in seconds
        """
        self.default_tools = default_tools or []
        self.max_tokens = max_tokens
        self.default_timeout = default_timeout

    async def execute(
        self,
        prompt: str,
        tools: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """
        Delegate a subtask to a subagent.

        Args:
            prompt: Task description for the subagent
            tools: Tools available to the subagent
            agent_type: Specialized agent type (e.g., 'code', 'research')
            system_prompt: Custom system instructions for subagent
            max_tokens: Maximum tokens for subagent response
            timeout: Timeout in seconds

        Returns:
            ToolResult with subagent response
        """
        try:
            # Import here to avoid circular dependency
            from ..client import ClaudeSDKClient

            # Prepare tools list
            task_tools = tools if tools is not None else self.default_tools

            # Prepare system prompt based on agent type
            effective_system_prompt = system_prompt
            if agent_type and not system_prompt:
                effective_system_prompt = self._get_agent_type_prompt(agent_type)

            # Create subagent client
            client = ClaudeSDKClient(
                system_prompt=effective_system_prompt,
                tools=task_tools,
            )

            # Execute query
            result = await client.query(
                prompt=prompt,
                max_tokens=max_tokens or self.max_tokens,
                timeout=timeout or self.default_timeout,
            )

            return ToolResult(
                content=result.content,
                success=result.successful,
                error=result.error if hasattr(result, "error") else None,
            )

        except ImportError as e:
            return ToolResult(
                content="",
                success=False,
                error=f"ClaudeSDKClient not available: {str(e)}",
            )
        except Exception as e:
            return ToolResult(content="", success=False, error=str(e))

    def _get_agent_type_prompt(self, agent_type: str) -> str:
        """Get system prompt for specific agent type."""
        agent_prompts = {
            "code": (
                "You are a specialized code assistant. Focus on writing clean, "
                "well-documented, and efficient code. Follow best practices and "
                "consider edge cases."
            ),
            "research": (
                "You are a research assistant. Focus on gathering accurate "
                "information, analyzing sources, and providing well-structured "
                "summaries with citations."
            ),
            "analysis": (
                "You are an analysis assistant. Focus on breaking down complex "
                "problems, identifying patterns, and providing actionable insights."
            ),
            "writing": (
                "You are a writing assistant. Focus on clear, engaging, and "
                "well-structured content that meets the specified requirements."
            ),
            "debug": (
                "You are a debugging specialist. Focus on identifying root causes, "
                "analyzing error patterns, and suggesting fixes with explanations."
            ),
        }

        return agent_prompts.get(
            agent_type,
            f"You are a specialized {agent_type} assistant. Focus on completing "
            "the assigned task efficiently and accurately.",
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Task description for the subagent",
                },
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tools available to the subagent",
                },
                "agent_type": {
                    "type": "string",
                    "description": "Specialized agent type (code, research, analysis, writing, debug)",
                    "enum": ["code", "research", "analysis", "writing", "debug"],
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Custom system instructions for subagent",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens for subagent response",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds",
                },
            },
            "required": ["prompt"],
        }
