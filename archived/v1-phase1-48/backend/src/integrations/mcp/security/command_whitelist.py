"""MCP Command Whitelist.

Sprint 113: S113-2 - Command whitelist for Shell and SSH MCP servers.

Provides three-tier command security:
  - allowed: Whitelisted commands execute immediately
  - blocked: Dangerous commands are rejected
  - requires_approval: Non-whitelisted commands trigger HITL approval

Configuration:
  MCP_ADDITIONAL_WHITELIST: Comma-separated additional allowed commands
"""

import logging
import os
import re
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


class CommandWhitelist:
    """MCP command whitelist manager.

    Commands are checked against three lists:
    1. BLOCKED_PATTERNS: Regex patterns for dangerous commands (always rejected)
    2. DEFAULT_WHITELIST: Safe read-only commands (always allowed)
    3. Everything else: Requires HITL approval

    Example:
        whitelist = CommandWhitelist()
        result = whitelist.check_command("ls -la")
        # result == "allowed"

        result = whitelist.check_command("rm -rf /")
        # result == "blocked"

        result = whitelist.check_command("apt-get install nginx")
        # result == "requires_approval"
    """

    DEFAULT_WHITELIST: List[str] = [
        # System information
        "whoami", "hostname", "date", "uptime", "uname",
        # File viewing (read-only)
        "ls", "dir", "cat", "head", "tail", "wc", "find", "grep",
        "file", "stat", "readlink", "realpath",
        # Network diagnostics
        "ping", "nslookup", "dig", "traceroute", "tracert",
        "curl", "wget", "netstat", "ss", "ip",
        # System status
        "ps", "top", "htop", "df", "du", "free", "vmstat",
        "iostat", "lsof", "who", "w", "last",
        # AD related (read-only)
        "dsquery", "dsget", "Get-ADUser", "Get-ADGroup",
        "Get-ADComputer", "Get-ADOrganizationalUnit",
        # Package info (read-only)
        "dpkg", "rpm", "pip", "npm", "which", "where",
        # Text processing
        "awk", "sed", "sort", "uniq", "cut", "tr", "tee",
        # Archive inspection
        "tar", "zip", "unzip", "gzip",
        # Environment
        "env", "printenv", "echo", "printf",
        # PowerShell read-only
        "Get-Process", "Get-Service", "Get-EventLog",
        "Get-ChildItem", "Get-Content", "Get-Item",
        "Get-WmiObject", "Get-CimInstance",
        "Test-Connection", "Test-Path",
        "Select-Object", "Where-Object", "Format-Table",
    ]

    BLOCKED_PATTERNS: List[str] = [
        r"rm\s+(-rf?|--recursive)\s+/",
        r"rm\s+(-rf?|--recursive)\s+\*",
        r"rm\s+(-rf?|--recursive)\s+\.",
        r"del\s+/[sfq]",
        r"format\s+[a-zA-Z]:",
        r"mkfs\.",
        r"dd\s+if=.*of=/dev",
        r">\s*/dev/sd",
        r"chmod\s+777\s+/",
        r"chown\s+.*\s+/$",
        r"curl.*\|\s*(ba)?sh",
        r"wget.*\|\s*(ba)?sh",
        r":\(\)\s*\{.*:\|:&\s*\}",
        r"shutdown\s",
        r"reboot\s*$",
        r"halt\s*$",
        r"poweroff\s*$",
        r"init\s+0",
        r"init\s+6",
        r">(\\\\|\s)*/dev/null\s+2>&1\s*&\s*$",
        r"Remove-Item\s+.*-Recurse\s+-Force",
        r"Clear-Content\s+.*\\\\Windows",
        r"Stop-Computer",
        r"Restart-Computer",
    ]

    def __init__(
        self,
        additional_whitelist: Optional[List[str]] = None,
        additional_blocked: Optional[List[str]] = None,
    ):
        """Initialize command whitelist.

        Args:
            additional_whitelist: Extra commands to allow
            additional_blocked: Extra patterns to block
        """
        self._whitelist: Set[str] = set(self.DEFAULT_WHITELIST)

        # Add from environment variable
        env_whitelist = os.environ.get("MCP_ADDITIONAL_WHITELIST", "")
        if env_whitelist:
            for cmd in env_whitelist.split(","):
                cmd = cmd.strip()
                if cmd:
                    self._whitelist.add(cmd)

        # Add from constructor parameter
        if additional_whitelist:
            self._whitelist.update(additional_whitelist)

        # Compile blocked patterns
        blocked = list(self.BLOCKED_PATTERNS)
        if additional_blocked:
            blocked.extend(additional_blocked)

        self._blocked_patterns: List[re.Pattern] = []
        for pattern in blocked:
            try:
                self._blocked_patterns.append(
                    re.compile(pattern, re.IGNORECASE)
                )
            except re.error as e:
                logger.warning(f"Invalid blocked pattern '{pattern}': {e}")

        logger.info(
            f"CommandWhitelist initialized: "
            f"{len(self._whitelist)} whitelisted, "
            f"{len(self._blocked_patterns)} blocked patterns"
        )

    def check_command(self, command: str) -> str:
        """Check command against whitelist and blocklist.

        Args:
            command: Full command string to check

        Returns:
            "allowed" - Whitelisted, execute immediately
            "blocked" - Dangerous, reject with error
            "requires_approval" - Needs HITL approval
        """
        if not command or not command.strip():
            return "blocked"

        command_stripped = command.strip()

        # Check blocked patterns first (highest priority)
        for pattern in self._blocked_patterns:
            if pattern.search(command_stripped):
                logger.warning(
                    f"COMMAND_BLOCKED: '{command_stripped[:80]}' "
                    f"matched pattern: {pattern.pattern}"
                )
                return "blocked"

        # Extract base command name
        cmd_name = self._extract_command_name(command_stripped)

        # Check whitelist
        if cmd_name in self._whitelist:
            logger.debug(f"COMMAND_ALLOWED: '{cmd_name}'")
            return "allowed"

        # Everything else requires approval
        logger.info(
            f"COMMAND_REQUIRES_APPROVAL: '{command_stripped[:80]}' "
            f"(base command: '{cmd_name}')"
        )
        return "requires_approval"

    def _extract_command_name(self, command: str) -> str:
        """Extract the base command name from a command string.

        Handles pipes, redirections, and common shell prefixes.

        Args:
            command: Full command string

        Returns:
            Base command name
        """
        # Remove common prefixes
        cmd = command.strip()
        for prefix in ("sudo ", "nohup ", "env ", "time "):
            if cmd.lower().startswith(prefix):
                cmd = cmd[len(prefix):].strip()

        # Get first token (the command name)
        parts = cmd.split()
        if not parts:
            return ""

        cmd_name = parts[0]

        # Handle path-prefixed commands (e.g., /usr/bin/ls)
        if "/" in cmd_name or "\\" in cmd_name:
            cmd_name = cmd_name.rsplit("/", 1)[-1]
            cmd_name = cmd_name.rsplit("\\", 1)[-1]

        return cmd_name

    @property
    def whitelist(self) -> Set[str]:
        """Get current whitelist (copy)."""
        return set(self._whitelist)

    @property
    def blocked_pattern_count(self) -> int:
        """Number of blocked patterns."""
        return len(self._blocked_patterns)
