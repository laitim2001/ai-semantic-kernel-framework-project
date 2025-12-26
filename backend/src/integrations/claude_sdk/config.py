"""Claude SDK configuration management."""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import yaml

from .exceptions import AuthenticationError


@dataclass
class ClaudeSDKConfig:
    """Configuration for Claude SDK."""

    # API Configuration
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # Model Configuration
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    timeout: int = 300

    # Agent Configuration
    system_prompt: Optional[str] = None
    tools: List[str] = field(default_factory=list)

    # Bash Security
    allowed_commands: List[str] = field(default_factory=list)
    denied_commands: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate and apply defaults."""
        if self.api_key is None:
            self.api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise AuthenticationError("ANTHROPIC_API_KEY not configured")

        # Default denied commands for security
        if not self.denied_commands:
            self.denied_commands = [
                "rm -rf /",
                "sudo rm",
                ":(){ :|:& };:",  # Fork bomb
                "curl | bash",
                "wget | sh",
            ]

    @classmethod
    def from_env(cls) -> "ClaudeSDKConfig":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model=os.getenv("CLAUDE_SDK_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=int(os.getenv("CLAUDE_SDK_MAX_TOKENS", "4096")),
            timeout=int(os.getenv("CLAUDE_SDK_TIMEOUT", "300")),
        )

    @classmethod
    def from_yaml(cls, path: str) -> "ClaudeSDKConfig":
        """Create config from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
        }
