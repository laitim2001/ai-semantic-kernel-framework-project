"""Tests for Claude SDK configuration."""

import pytest
import os
from unittest.mock import patch, mock_open

from src.integrations.claude_sdk.config import ClaudeSDKConfig
from src.integrations.claude_sdk.exceptions import AuthenticationError


class TestClaudeSDKConfig:
    """Tests for ClaudeSDKConfig."""

    def test_init_with_api_key(self):
        """Test config initialization with API key."""
        config = ClaudeSDKConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_tokens == 4096
        assert config.timeout == 300

    def test_init_from_env(self, monkeypatch):
        """Test config initialization from environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-test-key")
        config = ClaudeSDKConfig()
        assert config.api_key == "env-test-key"

    def test_init_without_api_key_raises_error(self, monkeypatch):
        """Test that missing API key raises AuthenticationError."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(AuthenticationError) as exc_info:
            ClaudeSDKConfig()
        assert "ANTHROPIC_API_KEY not configured" in str(exc_info.value)

    def test_custom_model(self):
        """Test config with custom model."""
        config = ClaudeSDKConfig(
            api_key="test-key", model="claude-opus-4-20250514"
        )
        assert config.model == "claude-opus-4-20250514"

    def test_custom_max_tokens(self):
        """Test config with custom max_tokens."""
        config = ClaudeSDKConfig(api_key="test-key", max_tokens=8192)
        assert config.max_tokens == 8192

    def test_custom_timeout(self):
        """Test config with custom timeout."""
        config = ClaudeSDKConfig(api_key="test-key", timeout=600)
        assert config.timeout == 600

    def test_system_prompt(self):
        """Test config with system prompt."""
        config = ClaudeSDKConfig(
            api_key="test-key",
            system_prompt="You are a helpful assistant.",
        )
        assert config.system_prompt == "You are a helpful assistant."

    def test_default_denied_commands(self):
        """Test that default denied commands are set."""
        config = ClaudeSDKConfig(api_key="test-key")
        assert "rm -rf /" in config.denied_commands
        assert "curl | bash" in config.denied_commands

    def test_custom_denied_commands(self):
        """Test config with custom denied commands."""
        config = ClaudeSDKConfig(
            api_key="test-key",
            denied_commands=["dangerous_command"],
        )
        assert config.denied_commands == ["dangerous_command"]

    def test_from_env(self, monkeypatch):
        """Test from_env class method."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        monkeypatch.setenv("CLAUDE_SDK_MODEL", "claude-opus-4-20250514")
        monkeypatch.setenv("CLAUDE_SDK_MAX_TOKENS", "16384")
        monkeypatch.setenv("CLAUDE_SDK_TIMEOUT", "600")

        config = ClaudeSDKConfig.from_env()
        assert config.api_key == "env-key"
        assert config.model == "claude-opus-4-20250514"
        assert config.max_tokens == 16384
        assert config.timeout == 600

    def test_from_yaml(self, tmp_path):
        """Test from_yaml class method."""
        yaml_content = """
api_key: yaml-key
model: claude-sonnet-4-20250514
max_tokens: 4096
timeout: 300
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        config = ClaudeSDKConfig.from_yaml(str(yaml_file))
        assert config.api_key == "yaml-key"
        assert config.model == "claude-sonnet-4-20250514"

    def test_to_dict(self):
        """Test to_dict method."""
        config = ClaudeSDKConfig(
            api_key="test-key",
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            timeout=300,
            system_prompt="Test prompt",
            tools=["Read", "Write"],
        )
        result = config.to_dict()

        assert result["model"] == "claude-sonnet-4-20250514"
        assert result["max_tokens"] == 4096
        assert result["timeout"] == 300
        assert result["system_prompt"] == "Test prompt"
        assert result["tools"] == ["Read", "Write"]
        # API key should not be in dict for security
        assert "api_key" not in result
