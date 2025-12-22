"""
Phase Tests Configuration

共用配置檔案，包含 API 端點、超時設定、LLM 配置等。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PhaseTestConfig:
    """Phase 測試的共用配置"""

    # API 配置
    base_url: str = "http://localhost:8000/api/v1"
    timeout_seconds: float = 60.0

    # LLM 配置 - 使用真實 AI 模型
    use_real_llm: bool = True
    llm_provider: str = "azure"
    llm_deployment: str = "gpt-5.2"
    llm_max_retries: int = 3
    llm_timeout_seconds: float = 120.0

    # Azure 配置 (Phase 9)
    azure_subscription_id: Optional[str] = None
    azure_resource_group: Optional[str] = None

    # 測試輸出
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    verbose: bool = True

    def __post_init__(self):
        """從環境變數載入配置"""
        # Azure OpenAI
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.llm_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.2")

        # Azure Resources (Phase 9)
        self.azure_subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        self.azure_resource_group = os.getenv("AZURE_RESOURCE_GROUP")

    @property
    def is_azure_configured(self) -> bool:
        """檢查 Azure OpenAI 是否已配置"""
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def is_azure_resources_configured(self) -> bool:
        """檢查 Azure 資源是否已配置 (Phase 9)"""
        return bool(self.azure_subscription_id and self.azure_resource_group)


# 預設配置實例
DEFAULT_CONFIG = PhaseTestConfig()


# API 端點映射
API_ENDPOINTS = {
    # Phase 8: Code Interpreter
    "code_interpreter": {
        "execute": "/code-interpreter/execute",
        "analyze": "/code-interpreter/analyze",
        "files_upload": "/code-interpreter/files/upload",
        "files_list": "/code-interpreter/files",
        "files_delete": "/code-interpreter/files/{file_id}",
        "visualizations": "/code-interpreter/visualizations/{file_id}",
        "visualizations_generate": "/code-interpreter/visualizations/generate",
    },

    # Phase 9: MCP Architecture
    "mcp": {
        "servers": "/mcp/servers",
        "connect": "/mcp/servers/{name}/connect",
        "disconnect": "/mcp/servers/{name}/disconnect",
        "tools": "/mcp/servers/{name}/tools",
        "call_tool": "/mcp/servers/{name}/tools/{tool_name}/call",
        "audit": "/mcp/audit",
    },

    # Phase 10: Session Mode
    "sessions": {
        "create": "/sessions",
        "get": "/sessions/{session_id}",
        "delete": "/sessions/{session_id}",
        "messages": "/sessions/{session_id}/messages",
        "send_message": "/sessions/{session_id}/messages",
        "attachments": "/sessions/{session_id}/attachments",
        "attachments_upload": "/sessions/{session_id}/attachments",
        "history": "/sessions/{session_id}/history",
        "search": "/sessions/{session_id}/search",
    },
}
