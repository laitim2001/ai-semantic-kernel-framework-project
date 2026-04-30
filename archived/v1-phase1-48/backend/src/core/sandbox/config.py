# =============================================================================
# IPA Platform - Process Sandbox Configuration
# =============================================================================
# Sprint 77: S77-1 - Sandbox Architecture Design & Orchestrator (13 pts)
#
# Configuration for process-level sandbox isolation.
# Defines environment variable filtering, resource limits, and timeouts.
#
# Security Principles:
#   - Least Privilege: Only pass necessary environment variables
#   - Explicit Allowlist: Must explicitly list allowed variables
#   - Process Isolation: Subprocess has restricted access
#
# =============================================================================

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set


@dataclass
class ProcessSandboxConfig:
    """Configuration for process-level sandbox isolation.

    This configuration controls how sandbox subprocesses are created and
    managed, including environment variable filtering, resource limits,
    and timeout settings.

    Attributes:
        sandbox_base_dir: Base directory for sandbox files (per-user)
        max_workers: Maximum number of concurrent worker processes
        worker_timeout: Maximum execution time per request (seconds)
        startup_timeout: Maximum time to start a worker process (seconds)
        idle_timeout: Time before idle worker is recycled (seconds)
        max_requests_per_worker: Max requests before worker restart
        allowed_env_vars: Environment variables passed to sandbox
        blocked_env_prefix: Prefixes that are always blocked

    Example:
        config = ProcessSandboxConfig(
            max_workers=5,
            worker_timeout=600,
        )
        orchestrator = SandboxOrchestrator(config)
    """

    # Directory configuration
    sandbox_base_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("SANDBOX_BASE_DIR", "data/sandbox")
        )
    )

    # Process pool configuration
    max_workers: int = field(
        default_factory=lambda: int(os.getenv("SANDBOX_MAX_WORKERS", "10"))
    )
    worker_timeout: int = field(
        default_factory=lambda: int(os.getenv("SANDBOX_WORKER_TIMEOUT", "300"))
    )
    startup_timeout: int = field(
        default_factory=lambda: int(os.getenv("SANDBOX_STARTUP_TIMEOUT", "30"))
    )
    idle_timeout: int = field(
        default_factory=lambda: int(os.getenv("SANDBOX_IDLE_TIMEOUT", "300"))
    )
    max_requests_per_worker: int = field(
        default_factory=lambda: int(os.getenv("SANDBOX_MAX_REQUESTS", "100"))
    )

    # Environment variable configuration
    allowed_env_vars: List[str] = field(default_factory=lambda: [
        # Claude API - Required for Claude SDK
        "ANTHROPIC_API_KEY",

        # Python environment - Required for execution
        "PYTHONPATH",
        "PATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",

        # Locale settings
        "LANG",
        "LC_ALL",
        "LC_CTYPE",

        # Sandbox identification (set by orchestrator)
        "SANDBOX_USER_ID",
        "SANDBOX_DIR",
        "SANDBOX_SESSION_ID",
        "SANDBOX_TIMEOUT",

        # System identification
        "COMPUTERNAME",
        "USERNAME",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",

        # Windows specific
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
    ])

    # Environment variable prefixes that are always blocked
    blocked_env_prefix: Set[str] = field(default_factory=lambda: {
        # Database
        "DB_",
        "DATABASE_",
        "POSTGRES_",
        "MYSQL_",

        # Redis
        "REDIS_",

        # Message Queue
        "RABBITMQ_",
        "AMQP_",

        # Azure (except specific allowed ones)
        "AZURE_",

        # AWS
        "AWS_",

        # Security
        "SECRET_",
        "JWT_",
        "API_KEY_",
        "PRIVATE_",
        "CREDENTIAL_",

        # Internal
        "IPA_INTERNAL_",
    })

    def get_filtered_env(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        sandbox_dir: Optional[Path] = None
    ) -> dict:
        """Get filtered environment variables for sandbox process.

        Creates a new environment dictionary containing only allowed
        variables and adding sandbox-specific settings.

        Args:
            user_id: User identifier for the sandbox
            session_id: Optional session identifier
            sandbox_dir: Optional override for sandbox directory

        Returns:
            Dictionary of environment variables for subprocess
        """
        filtered_env = {}
        current_env = os.environ

        # Add allowed environment variables
        for var in self.allowed_env_vars:
            if var in current_env:
                # Double-check against blocked prefixes
                if not self._is_blocked_prefix(var):
                    filtered_env[var] = current_env[var]

        # Add sandbox-specific variables
        sandbox_path = sandbox_dir or self.get_user_sandbox_dir(user_id)
        filtered_env["SANDBOX_USER_ID"] = user_id
        filtered_env["SANDBOX_DIR"] = str(sandbox_path)
        filtered_env["SANDBOX_TIMEOUT"] = str(self.worker_timeout)

        if session_id:
            filtered_env["SANDBOX_SESSION_ID"] = session_id

        return filtered_env

    def _is_blocked_prefix(self, var_name: str) -> bool:
        """Check if variable name starts with a blocked prefix.

        Args:
            var_name: Environment variable name

        Returns:
            True if the variable should be blocked
        """
        upper_name = var_name.upper()
        for prefix in self.blocked_env_prefix:
            if upper_name.startswith(prefix):
                return True
        return False

    def get_user_sandbox_dir(self, user_id: str) -> Path:
        """Get sandbox directory for a specific user.

        Args:
            user_id: User identifier

        Returns:
            Path to user's sandbox directory
        """
        # Sanitize user_id to prevent path traversal
        safe_user_id = self._sanitize_user_id(user_id)
        return Path(self.sandbox_base_dir) / safe_user_id

    def ensure_user_sandbox_dir(self, user_id: str) -> Path:
        """Ensure user's sandbox directory exists.

        Args:
            user_id: User identifier

        Returns:
            Path to user's sandbox directory
        """
        sandbox_dir = self.get_user_sandbox_dir(user_id)
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        return sandbox_dir

    @staticmethod
    def _sanitize_user_id(user_id: str) -> str:
        """Sanitize user ID to prevent path traversal.

        Args:
            user_id: Raw user ID

        Returns:
            Sanitized user ID safe for filesystem paths
        """
        import re

        # Remove path separators and dangerous characters
        sanitized = user_id.replace("/", "_").replace("\\", "_")
        sanitized = sanitized.replace("..", "_")

        # Only allow alphanumeric, dash, underscore
        sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "_", sanitized)

        # Ensure it's not empty
        if not sanitized:
            sanitized = "unknown"

        return sanitized

    def validate(self) -> List[str]:
        """Validate configuration settings.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if self.max_workers < 1:
            errors.append("max_workers must be at least 1")

        if self.max_workers > 50:
            errors.append("max_workers should not exceed 50")

        if self.worker_timeout < 30:
            errors.append("worker_timeout should be at least 30 seconds")

        if self.startup_timeout < 5:
            errors.append("startup_timeout should be at least 5 seconds")

        if self.idle_timeout < 60:
            errors.append("idle_timeout should be at least 60 seconds")

        if "ANTHROPIC_API_KEY" not in self.allowed_env_vars:
            errors.append("ANTHROPIC_API_KEY must be in allowed_env_vars")

        return errors


# Default configuration instance
default_sandbox_config = ProcessSandboxConfig()
