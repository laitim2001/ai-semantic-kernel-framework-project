# =============================================================================
# IPA Platform - Operation Analyzer
# =============================================================================
# Sprint 55: Risk Assessment Engine - S55-2
#
# Analyzes operations for risk factors including:
#   - Tool base risk matrix
#   - Sensitive path detection
#   - Dangerous command detection
#   - Batch operation risk calculation
#
# Dependencies:
#   - RiskFactor, RiskFactorType, OperationContext
#     (src.integrations.hybrid.risk.models)
# =============================================================================

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Set

from ..models import OperationContext, RiskFactor, RiskFactorType


@dataclass
class ToolRiskConfig:
    """Configuration for tool-based risk assessment."""

    # Base risk scores for different tool types (0.0 - 1.0)
    base_risk: Dict[str, float] = field(default_factory=lambda: {
        # Read-only tools (lowest risk)
        "Read": 0.1,
        "Glob": 0.1,
        "Grep": 0.1,
        "LSP": 0.15,
        "WebFetch": 0.2,
        "WebSearch": 0.2,
        # Modification tools (medium risk)
        "Write": 0.4,
        "Edit": 0.4,
        "MultiEdit": 0.5,
        "NotebookEdit": 0.5,
        # Execution tools (higher risk)
        "Bash": 0.6,
        "Task": 0.5,
        # Unknown tools (default)
        "unknown": 0.5,
    })

    # Weight for tool-based risk factor
    weight: float = 0.4


@dataclass
class PathRiskConfig:
    """Configuration for path-based risk assessment."""

    # Sensitive path patterns (regex patterns)
    sensitive_patterns: List[str] = field(default_factory=lambda: [
        r"^/etc/",           # System configuration
        r"^/root/",          # Root home directory
        r"^/var/log/",       # Log files
        r"^/usr/bin/",       # System binaries
        r"^/usr/sbin/",      # System administration binaries
        r"^C:\\Windows\\",   # Windows system (case insensitive)
        r"^C:\\Program Files\\",  # Windows programs
        r"\.env$",           # Environment files
        r"\.env\.",          # Environment files with suffix
        r"password",         # Password files
        r"secret",           # Secret files
        r"credential",       # Credential files
        r"\.pem$",           # PEM certificates
        r"\.key$",           # Private keys
        r"\.crt$",           # Certificates
        r"id_rsa",           # SSH keys
        r"authorized_keys",  # SSH authorized keys
        r"\.ssh/",           # SSH directory
        r"\.aws/",           # AWS credentials
        r"\.kube/",          # Kubernetes config
    ])

    # Risk score for sensitive paths
    sensitive_score: float = 0.7

    # Weight for path-based risk factor
    weight: float = 0.3


@dataclass
class CommandRiskConfig:
    """Configuration for command-based risk assessment."""

    # Dangerous command patterns (regex patterns)
    dangerous_patterns: List[str] = field(default_factory=lambda: [
        # Destructive commands
        r"rm\s+(-[rf]+\s+)*[/~]",   # rm -rf / or rm -rf ~
        r"rm\s+-rf\s+\*",           # rm -rf *
        r"rm\s+-rf\s+\.",           # rm -rf .
        r"del\s+/[sq]",             # Windows del /s /q
        r"rmdir\s+/[sq]",           # Windows rmdir /s /q
        r"format\s+[a-z]:",         # Windows format drive
        # Privilege escalation
        r"^sudo\s+",                # sudo commands
        r"chmod\s+777",             # World-writable permissions
        r"chmod\s+\+s",             # SetUID bit
        r"chown\s+root",            # Change owner to root
        # Remote execution
        r"curl\s+.*\|\s*(bash|sh)", # Piping curl to shell
        r"wget\s+.*\|\s*(bash|sh)", # Piping wget to shell
        r"curl\s+.*-o\s+-\s*\|",    # Piping curl output
        # Dangerous redirects
        r">\s*/dev/sd[a-z]",        # Write to disk device
        r"dd\s+.*of=/dev/",         # dd to device
        # Fork bombs and resource exhaustion
        r":\(\)\{:\|:&\};:",        # Fork bomb
        r"while\s+true.*do",        # Infinite loops
        # Network reconnaissance
        r"nmap\s+",                 # Port scanning
        r"netcat\s+.*-l",           # Listening netcat
        r"nc\s+.*-l",               # Listening nc
        # Credential theft
        r"cat\s+.*/etc/passwd",     # Reading passwd
        r"cat\s+.*/etc/shadow",     # Reading shadow
    ])

    # Critical command patterns (maximum risk)
    critical_patterns: List[str] = field(default_factory=lambda: [
        r"rm\s+-rf\s+/\s*$",         # rm -rf /
        r"rm\s+-rf\s+/\*",           # rm -rf /*
        r"mkfs\.",                   # Format filesystem
        r"dd\s+if=/dev/zero",        # Wipe with zeros
        r">\s*/dev/sda",             # Direct disk write
    ])

    # Risk scores - Increased to ensure dangerous commands trigger HIGH risk
    # With HYBRID scoring (70% avg + 30% max), dangerous commands need higher
    # scores to reliably exceed the 0.7 HIGH threshold after context adjustment
    dangerous_score: float = 0.85  # Increased from 0.75
    critical_score: float = 0.95

    # Weight for command-based risk factor - Increased to give more influence
    # to dangerous command detection in the overall risk calculation
    weight: float = 0.65  # Increased from 0.5


class OperationAnalyzer:
    """
    Analyzes operations for risk factors.

    Evaluates tool usage, file paths, and commands to identify
    potential risks in operations.

    Attributes:
        tool_config: Configuration for tool-based risk
        path_config: Configuration for path-based risk
        command_config: Configuration for command-based risk

    Example:
        >>> analyzer = OperationAnalyzer()
        >>> context = OperationContext(
        ...     tool_name="Bash",
        ...     command="rm -rf /tmp/test",
        ...     target_paths=["/tmp/test"]
        ... )
        >>> factors = analyzer.analyze(context)
        >>> for factor in factors:
        ...     print(f"{factor.factor_type}: {factor.score}")
    """

    def __init__(
        self,
        tool_config: Optional[ToolRiskConfig] = None,
        path_config: Optional[PathRiskConfig] = None,
        command_config: Optional[CommandRiskConfig] = None,
    ):
        """
        Initialize OperationAnalyzer with configurations.

        Args:
            tool_config: Configuration for tool risk assessment
            path_config: Configuration for path risk assessment
            command_config: Configuration for command risk assessment
        """
        self.tool_config = tool_config or ToolRiskConfig()
        self.path_config = path_config or PathRiskConfig()
        self.command_config = command_config or CommandRiskConfig()

        # Compile regex patterns for efficiency
        self._sensitive_path_patterns = self._compile_patterns(
            self.path_config.sensitive_patterns
        )
        self._dangerous_cmd_patterns = self._compile_patterns(
            self.command_config.dangerous_patterns
        )
        self._critical_cmd_patterns = self._compile_patterns(
            self.command_config.critical_patterns
        )

    def _compile_patterns(self, patterns: List[str]) -> List[Pattern]:
        """Compile regex patterns for efficient matching."""
        compiled = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                # Skip invalid patterns
                pass
        return compiled

    def analyze(self, context: OperationContext) -> List[RiskFactor]:
        """
        Analyze operation context for risk factors.

        Evaluates tool type, file paths, and commands to identify
        potential risks.

        Args:
            context: The operation context to analyze

        Returns:
            List of identified risk factors
        """
        factors: List[RiskFactor] = []

        # Analyze tool risk
        tool_factor = self._analyze_tool(context)
        if tool_factor:
            factors.append(tool_factor)

        # Analyze path risks
        path_factors = self._analyze_paths(context)
        factors.extend(path_factors)

        # Analyze command risks
        command_factors = self._analyze_command(context)
        factors.extend(command_factors)

        return factors

    def _analyze_tool(self, context: OperationContext) -> Optional[RiskFactor]:
        """Analyze tool-based risk."""
        tool_name = context.tool_name
        base_risk = self.tool_config.base_risk.get(
            tool_name,
            self.tool_config.base_risk.get("unknown", 0.5)
        )

        return RiskFactor(
            factor_type=RiskFactorType.OPERATION,
            score=base_risk,
            weight=self.tool_config.weight,
            description=f"Tool '{tool_name}' base risk",
            source=tool_name,
            metadata={"tool_name": tool_name}
        )

    def _analyze_paths(self, context: OperationContext) -> List[RiskFactor]:
        """Analyze path-based risks."""
        factors: List[RiskFactor] = []
        analyzed_paths: Set[str] = set()

        for path in context.target_paths:
            # Skip duplicate paths
            if path in analyzed_paths:
                continue
            analyzed_paths.add(path)

            # Check against sensitive patterns
            for pattern in self._sensitive_path_patterns:
                if pattern.search(path):
                    factors.append(RiskFactor(
                        factor_type=RiskFactorType.PATH,
                        score=self.path_config.sensitive_score,
                        weight=self.path_config.weight,
                        description=f"Sensitive path detected: {path}",
                        source=path,
                        metadata={
                            "path": path,
                            "pattern": pattern.pattern
                        }
                    ))
                    break  # One match per path is enough

        return factors

    def _analyze_command(self, context: OperationContext) -> List[RiskFactor]:
        """Analyze command-based risks."""
        factors: List[RiskFactor] = []

        if not context.command:
            return factors

        command = context.command

        # Check for critical commands first
        for pattern in self._critical_cmd_patterns:
            if pattern.search(command):
                factors.append(RiskFactor(
                    factor_type=RiskFactorType.COMMAND,
                    score=self.command_config.critical_score,
                    weight=self.command_config.weight,
                    description=f"Critical command detected",
                    source=command[:100],  # Truncate for safety
                    metadata={
                        "pattern": pattern.pattern,
                        "severity": "critical"
                    }
                ))
                return factors  # Critical command overrides others

        # Check for dangerous commands
        for pattern in self._dangerous_cmd_patterns:
            if pattern.search(command):
                factors.append(RiskFactor(
                    factor_type=RiskFactorType.COMMAND,
                    score=self.command_config.dangerous_score,
                    weight=self.command_config.weight,
                    description=f"Dangerous command pattern detected",
                    source=command[:100],
                    metadata={
                        "pattern": pattern.pattern,
                        "severity": "dangerous"
                    }
                ))
                break  # One match is enough

        return factors

    def analyze_batch(
        self,
        contexts: List[OperationContext]
    ) -> List[List[RiskFactor]]:
        """
        Analyze multiple operation contexts.

        Adds cumulative risk factors for batch operations.

        Args:
            contexts: List of operation contexts to analyze

        Returns:
            List of risk factor lists, one per context
        """
        results: List[List[RiskFactor]] = []

        for i, context in enumerate(contexts):
            factors = self.analyze(context)

            # Add batch risk factor for subsequent operations
            if i > 0:
                batch_risk = min(0.1 * i, 0.5)  # Cap at 0.5
                factors.append(RiskFactor(
                    factor_type=RiskFactorType.FREQUENCY,
                    score=batch_risk,
                    weight=0.2,
                    description=f"Batch operation #{i + 1}",
                    metadata={"batch_index": i}
                ))

            results.append(factors)

        return results

    def get_tool_risk(self, tool_name: str) -> float:
        """
        Get the base risk score for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Base risk score (0.0 - 1.0)
        """
        return self.tool_config.base_risk.get(
            tool_name,
            self.tool_config.base_risk.get("unknown", 0.5)
        )

    def is_sensitive_path(self, path: str) -> bool:
        """
        Check if a path is considered sensitive.

        Args:
            path: File path to check

        Returns:
            True if path matches any sensitive pattern
        """
        for pattern in self._sensitive_path_patterns:
            if pattern.search(path):
                return True
        return False

    def is_dangerous_command(self, command: str) -> bool:
        """
        Check if a command is considered dangerous.

        Args:
            command: Command string to check

        Returns:
            True if command matches any dangerous pattern
        """
        for pattern in self._dangerous_cmd_patterns:
            if pattern.search(command):
                return True
        for pattern in self._critical_cmd_patterns:
            if pattern.search(command):
                return True
        return False

    def get_command_severity(self, command: str) -> Optional[str]:
        """
        Get the severity level of a dangerous command.

        Args:
            command: Command string to check

        Returns:
            Severity level ("critical", "dangerous") or None if safe
        """
        for pattern in self._critical_cmd_patterns:
            if pattern.search(command):
                return "critical"

        for pattern in self._dangerous_cmd_patterns:
            if pattern.search(command):
                return "dangerous"

        return None
