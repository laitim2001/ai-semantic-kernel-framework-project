"""Shell command executor with security controls.

Provides safe shell command execution with:
- Command validation (whitelist/blacklist)
- Timeout control
- Output size limiting
- Working directory isolation
"""

import asyncio
import logging
import os
import platform
import re
import shlex
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ShellType(Enum):
    """Shell type enumeration."""

    POWERSHELL = "powershell"
    BASH = "bash"
    CMD = "cmd"

    @classmethod
    def detect_default(cls) -> "ShellType":
        """Detect the default shell for the current platform."""
        if platform.system() == "Windows":
            return cls.POWERSHELL
        return cls.BASH


@dataclass
class ShellConfig:
    """Shell executor configuration.

    Attributes:
        shell_type: Type of shell to use
        timeout_seconds: Maximum execution time
        max_output_size: Maximum output size in bytes
        working_directory: Working directory for commands
        allowed_commands: Whitelist of allowed commands (None = all allowed)
        blocked_commands: Blacklist of blocked command patterns
        blocked_patterns: Regex patterns to block
        environment: Additional environment variables
    """

    shell_type: ShellType = field(default_factory=ShellType.detect_default)
    timeout_seconds: int = 60
    max_output_size: int = 1024 * 1024  # 1MB
    working_directory: Optional[str] = None
    allowed_commands: Optional[List[str]] = None
    blocked_commands: Optional[List[str]] = None
    blocked_patterns: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None

    @classmethod
    def from_env(cls) -> "ShellConfig":
        """Create config from environment variables.

        Environment variables:
            SHELL_TYPE: powershell, bash, or cmd
            SHELL_TIMEOUT: Timeout in seconds
            SHELL_MAX_OUTPUT: Max output size in bytes
            SHELL_WORKING_DIR: Working directory
        """
        shell_type_str = os.environ.get("SHELL_TYPE", "").lower()
        if shell_type_str == "powershell":
            shell_type = ShellType.POWERSHELL
        elif shell_type_str == "bash":
            shell_type = ShellType.BASH
        elif shell_type_str == "cmd":
            shell_type = ShellType.CMD
        else:
            shell_type = ShellType.detect_default()

        return cls(
            shell_type=shell_type,
            timeout_seconds=int(os.environ.get("SHELL_TIMEOUT", "60")),
            max_output_size=int(os.environ.get("SHELL_MAX_OUTPUT", str(1024 * 1024))),
            working_directory=os.environ.get("SHELL_WORKING_DIR"),
        )


@dataclass
class CommandResult:
    """Command execution result.

    Attributes:
        exit_code: Process exit code (-1 for timeout/error)
        stdout: Standard output
        stderr: Standard error
        execution_time: Execution time in seconds
        truncated: Whether output was truncated
        command: The command that was executed
    """

    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    truncated: bool = False
    command: Optional[str] = None


class ShellExecutor:
    """Safe shell command executor.

    Provides command execution with security controls:
    - Blocked command patterns (fork bombs, destructive commands)
    - Optional command whitelist
    - Timeout control
    - Output truncation
    - Working directory isolation

    Example:
        >>> config = ShellConfig(timeout_seconds=30)
        >>> executor = ShellExecutor(config)
        >>> result = await executor.execute("echo 'Hello World'")
        >>> print(result.stdout)
        Hello World

    Security:
        - Commands are validated against blacklist before execution
        - Dangerous patterns like fork bombs are blocked
        - Output is truncated to prevent memory exhaustion
    """

    # Default blocked command patterns (dangerous operations)
    DEFAULT_BLOCKED_PATTERNS = [
        r"rm\s+-rf\s+/",  # rm -rf /
        r"rm\s+-rf\s+\*",  # rm -rf *
        r"rm\s+-rf\s+\.",  # rm -rf .
        r"del\s+/s\s+/q",  # del /s /q (Windows)
        r"format\s+[a-zA-Z]:",  # format C:
        r"shutdown",  # shutdown
        r"reboot",  # reboot
        r"halt",  # halt
        r":\(\)\{\s*:\|\:&\s*\}\s*;",  # Fork bomb
        r">\s*/dev/sda",  # Write to disk
        r"mkfs\.",  # Format filesystem
        r"dd\s+if=.*of=/dev",  # dd to device
        r"wget.*\|.*sh",  # Download and execute
        r"curl.*\|.*sh",  # Download and execute
        r"chmod\s+777\s+/",  # chmod 777 /
        r"chown\s+.*\s+/",  # chown /
    ]

    # Default blocked commands
    DEFAULT_BLOCKED_COMMANDS = [
        "rm -rf /",
        "rm -rf /*",
        "format c:",
        "del /s /q c:\\",
        ":(){:|:&};:",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
    ]

    def __init__(self, config: ShellConfig):
        """Initialize shell executor.

        Args:
            config: Shell configuration
        """
        self._config = config
        self._blocked_patterns = self._compile_blocked_patterns()
        self._validate_config()

        logger.info(
            f"ShellExecutor initialized: shell={config.shell_type.value}, "
            f"timeout={config.timeout_seconds}s"
        )

    def _compile_blocked_patterns(self) -> List[re.Pattern]:
        """Compile blocked regex patterns."""
        patterns = self.DEFAULT_BLOCKED_PATTERNS.copy()
        if self._config.blocked_patterns:
            patterns.extend(self._config.blocked_patterns)

        compiled = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid blocked pattern '{pattern}': {e}")

        return compiled

    def _validate_config(self) -> None:
        """Validate configuration."""
        if self._config.working_directory:
            if not os.path.isdir(self._config.working_directory):
                raise ValueError(
                    f"Working directory does not exist: {self._config.working_directory}"
                )

        if self._config.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")

        if self._config.max_output_size <= 0:
            raise ValueError("Max output size must be positive")

    def validate_command(self, command: str) -> None:
        """Validate command before execution.

        Args:
            command: Command to validate

        Raises:
            ValueError: If command is blocked or not allowed
        """
        command_lower = command.lower().strip()

        # Check blocked commands
        blocked = self._config.blocked_commands or self.DEFAULT_BLOCKED_COMMANDS
        for blocked_cmd in blocked:
            if blocked_cmd.lower() in command_lower:
                raise ValueError(f"Blocked command pattern: {blocked_cmd}")

        # Check blocked patterns
        for pattern in self._blocked_patterns:
            if pattern.search(command):
                raise ValueError(f"Command matches blocked pattern: {pattern.pattern}")

        # Check whitelist if configured
        if self._config.allowed_commands:
            try:
                # Extract the base command
                if self._config.shell_type == ShellType.POWERSHELL:
                    parts = command.split()
                else:
                    parts = shlex.split(command)

                if parts:
                    base_cmd = parts[0].lower()
                    allowed_lower = [c.lower() for c in self._config.allowed_commands]
                    if base_cmd not in allowed_lower:
                        raise ValueError(f"Command not in whitelist: {base_cmd}")
            except ValueError as e:
                if "whitelist" in str(e):
                    raise
                # shlex parsing failed, check the first word
                first_word = command.split()[0].lower() if command.split() else ""
                allowed_lower = [c.lower() for c in self._config.allowed_commands]
                if first_word not in allowed_lower:
                    raise ValueError(f"Command not in whitelist: {first_word}")

    async def execute(
        self,
        command: str,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """Execute a shell command.

        Args:
            command: Command to execute
            env: Additional environment variables
            timeout: Override timeout (seconds)

        Returns:
            CommandResult with execution details

        Example:
            >>> result = await executor.execute("echo hello")
            >>> print(result.exit_code, result.stdout)
            0 hello
        """
        # Validate command
        try:
            self.validate_command(command)
        except ValueError as e:
            logger.warning(f"Command blocked: {command} - {e}")
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=0.0,
                command=command,
            )

        # Build shell command
        shell_cmd = self._build_shell_command(command)

        # Prepare environment
        full_env = os.environ.copy()
        if self._config.environment:
            full_env.update(self._config.environment)
        if env:
            full_env.update(env)

        # Execute command
        effective_timeout = timeout or self._config.timeout_seconds
        start_time = asyncio.get_event_loop().time()

        try:
            process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._config.working_directory,
                env=full_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=effective_timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time = asyncio.get_event_loop().time() - start_time
                logger.warning(f"Command timed out after {effective_timeout}s: {command}")
                return CommandResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {effective_timeout} seconds",
                    execution_time=execution_time,
                    command=command,
                )

            execution_time = asyncio.get_event_loop().time() - start_time

            # Process output
            stdout_str, stdout_truncated = self._truncate_output(
                stdout.decode("utf-8", errors="replace")
            )
            stderr_str, stderr_truncated = self._truncate_output(
                stderr.decode("utf-8", errors="replace")
            )

            logger.info(
                f"Command completed: exit_code={process.returncode}, "
                f"time={execution_time:.2f}s, truncated={stdout_truncated or stderr_truncated}"
            )

            return CommandResult(
                exit_code=process.returncode or 0,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time=execution_time,
                truncated=stdout_truncated or stderr_truncated,
                command=command,
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Command execution failed: {e}")
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {e}",
                execution_time=execution_time,
                command=command,
            )

    def _build_shell_command(self, command: str) -> str:
        """Build the full shell command.

        Args:
            command: User command

        Returns:
            Full shell command with shell invocation
        """
        if self._config.shell_type == ShellType.POWERSHELL:
            # Escape for PowerShell
            escaped = command.replace('"', '`"')
            return f'powershell -NoProfile -NonInteractive -Command "{escaped}"'
        elif self._config.shell_type == ShellType.BASH:
            # Escape for Bash
            escaped = command.replace("'", "'\"'\"'")
            return f"bash -c '{escaped}'"
        else:
            # CMD
            return f'cmd /c "{command}"'

    def _truncate_output(self, output: str) -> Tuple[str, bool]:
        """Truncate output if too large.

        Args:
            output: Output string

        Returns:
            Tuple of (possibly truncated output, was_truncated)
        """
        if len(output.encode("utf-8")) > self._config.max_output_size:
            # Find a safe truncation point
            truncated = output[: self._config.max_output_size // 2]
            return truncated + "\n...[output truncated]...", True
        return output, False

    async def execute_script(
        self,
        script_path: str,
        arguments: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """Execute a script file.

        Args:
            script_path: Path to the script
            arguments: Script arguments
            env: Additional environment variables
            timeout: Override timeout

        Returns:
            CommandResult with execution details
        """
        # Validate script path
        if not os.path.isfile(script_path):
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"Script not found: {script_path}",
                execution_time=0.0,
            )

        # Build command based on script type
        args_str = " ".join(arguments or [])

        if script_path.endswith(".ps1"):
            command = f'& "{script_path}" {args_str}'
        elif script_path.endswith(".sh"):
            command = f'bash "{script_path}" {args_str}'
        elif script_path.endswith(".bat") or script_path.endswith(".cmd"):
            command = f'"{script_path}" {args_str}'
        elif script_path.endswith(".py"):
            command = f'python "{script_path}" {args_str}'
        else:
            command = f'"{script_path}" {args_str}'

        return await self.execute(command, env=env, timeout=timeout)
