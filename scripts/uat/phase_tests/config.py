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

    # Phase 11: Agent-Session Integration
    "agent_session": {
        # Chat endpoints
        "chat": "/sessions/{session_id}/chat",
        "chat_stream": "/sessions/{session_id}/chat/stream",

        # Tool call endpoints
        "tool_calls": "/sessions/{session_id}/tool-calls",
        "tool_call_status": "/sessions/{session_id}/tool-calls/{tool_call_id}",

        # Approval endpoints
        "approvals": "/sessions/{session_id}/approvals",
        "approve": "/sessions/{session_id}/approvals/{approval_id}/approve",
        "reject": "/sessions/{session_id}/approvals/{approval_id}/reject",

        # WebSocket
        "websocket": "/sessions/{session_id}/ws",

        # Metrics
        "metrics": "/sessions/{session_id}/metrics",
    },

    # Phase 12: Claude Agent SDK Integration
    "claude_sdk": {
        # Sprint 48: Core SDK
        "query": "/claude-sdk/query",
        "sessions": "/claude-sdk/sessions",
        "session": "/claude-sdk/sessions/{session_id}",
        "session_query": "/claude-sdk/sessions/{session_id}/query",
        "session_history": "/claude-sdk/sessions/{session_id}/history",
        "session_fork": "/claude-sdk/sessions/{session_id}/fork",

        # Sprint 49: Tools & Hooks (Integration Layer)
        "tools": "/claude-sdk/tools",
        "tool": "/claude-sdk/tools/{tool_name}",
        "hooks": "/claude-sdk/hooks",
        "hook": "/claude-sdk/hooks/{hook_id}",

        # Sprint 51: Tools API Routes (S51-1)
        "tools_list": "/claude-sdk/tools",
        "tool_get": "/claude-sdk/tools/{name}",
        "tool_execute": "/claude-sdk/tools/execute",
        "tool_validate": "/claude-sdk/tools/validate",

        # Sprint 51: Hooks API Routes (S51-2)
        "hooks_list": "/claude-sdk/hooks",
        "hook_get": "/claude-sdk/hooks/{hook_id}",
        "hook_register": "/claude-sdk/hooks/register",
        "hook_delete": "/claude-sdk/hooks/{hook_id}",
        "hook_enable": "/claude-sdk/hooks/{hook_id}/enable",
        "hook_disable": "/claude-sdk/hooks/{hook_id}/disable",

        # Sprint 51: MCP API Routes (S51-3)
        "mcp_servers": "/claude-sdk/mcp/servers",
        "mcp_connect": "/claude-sdk/mcp/servers/connect",
        "mcp_disconnect": "/claude-sdk/mcp/servers/{server_id}/disconnect",
        "mcp_health": "/claude-sdk/mcp/servers/{server_id}/health",
        "mcp_tools": "/claude-sdk/mcp/tools",
        "mcp_tool_execute": "/claude-sdk/mcp/tools/execute",

        # Sprint 51: Hybrid API Routes (S51-4)
        "hybrid_execute": "/claude-sdk/hybrid/execute",
        "hybrid_analyze": "/claude-sdk/hybrid/analyze",
        "hybrid_metrics": "/claude-sdk/hybrid/metrics",
        "hybrid_context_sync": "/claude-sdk/hybrid/context/sync",
        "hybrid_capabilities": "/claude-sdk/hybrid/capabilities",
    },
}
