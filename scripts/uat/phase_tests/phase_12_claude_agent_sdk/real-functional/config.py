"""
Phase 12 Real Functional Test Configuration
真實功能測試配置
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class TestConfig:
    """測試配置類"""

    # Anthropic API
    anthropic_api_key: str
    model_name: str = "claude-haiku-4-5"  # Default: Haiku 4.5 (fast & cost-effective)
    max_tokens: int = 1024

    # Backend API
    backend_url: str = "http://localhost:8000"
    api_version: str = "v1"

    # Timeouts
    request_timeout: int = 120
    tool_execution_timeout: int = 60
    mcp_connection_timeout: int = 30

    # Logging
    log_level: str = "INFO"

    # Feature Flags
    enable_tool_tests: bool = True
    enable_mcp_tests: bool = True
    enable_hybrid_tests: bool = True

    @property
    def api_base_url(self) -> str:
        return f"{self.backend_url}/api/{self.api_version}"

    @classmethod
    def from_env(cls) -> "TestConfig":
        """從環境變數載入配置"""
        # 嘗試載入 .env 文件
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            _load_dotenv(env_path)

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Set it via environment variable or .env file."
            )

        return cls(
            anthropic_api_key=api_key,
            model_name=os.getenv("MODEL_NAME", "claude-haiku-4-5"),
            max_tokens=int(os.getenv("MAX_TOKENS", "1024")),
            backend_url=os.getenv("BACKEND_URL", "http://localhost:8000"),
            request_timeout=int(os.getenv("TEST_TIMEOUT", "120")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_tool_tests=os.getenv("ENABLE_TOOL_TESTS", "true").lower() == "true",
            enable_mcp_tests=os.getenv("ENABLE_MCP_TESTS", "true").lower() == "true",
            enable_hybrid_tests=os.getenv("ENABLE_HYBRID_TESTS", "true").lower() == "true",
        )


def _load_dotenv(env_path: Path) -> None:
    """簡單的 .env 文件載入器"""
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ.setdefault(key, value)
    except Exception as e:
        print(f"Warning: Failed to load .env file: {e}")


# 測試工具定義
CLAUDE_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file at the specified path",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to write to"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and directories in the specified path",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "execute_command",
        "description": "Execute a shell command and return the output",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "calculator",
        "description": "Perform mathematical calculations",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
    }
]


# 測試場景定義
TEST_SCENARIOS = {
    "A": {
        "name": "Real LLM Conversation",
        "description": "測試真實的 Claude LLM 對話功能",
        "tests": [
            "test_simple_conversation",
            "test_multi_turn_conversation",
            "test_system_prompt",
            "test_streaming_response",
        ]
    },
    "B": {
        "name": "Real Tool Execution",
        "description": "測試真實的工具調用和執行",
        "tests": [
            "test_tool_call_generation",
            "test_file_read_tool",
            "test_file_write_tool",
            "test_command_execution_tool",
            "test_calculator_tool",
        ]
    },
    "C": {
        "name": "Real MCP Integration",
        "description": "測試真實的 MCP Server 整合",
        "tests": [
            "test_mcp_server_connection",
            "test_mcp_tool_discovery",
            "test_mcp_tool_execution",
            "test_mcp_resource_access",
        ]
    },
    "D": {
        "name": "End-to-End Use Cases",
        "description": "完整的端到端使用案例",
        "tests": [
            "test_code_review_assistant",
            "test_file_analysis_workflow",
            "test_multi_step_task",
            "test_error_handling_recovery",
        ]
    }
}
