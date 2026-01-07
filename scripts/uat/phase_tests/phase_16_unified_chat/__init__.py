"""
Phase 16: Unified Agentic Chat Interface Tests

此模組包含 Phase 16 統一聊天介面的 UAT 測試場景。

測試場景:
- PHASE16-001: SSE 連接管理
- PHASE16-002: 消息流式傳輸
- PHASE16-003: 模式切換
- PHASE16-004: 審批流程
- PHASE16-005: 檢查點恢復
- PHASE16-006: 執行指標
"""

from .mock_generator import MockSSEGenerator
from .unified_chat_client import UnifiedChatClient
from .scenario_sse_connection import SSEConnectionScenario
from .scenario_message_streaming import MessageStreamingScenario
from .scenario_mode_switching import ModeSwitchingScenario
from .scenario_approval_flow import ApprovalFlowScenario
from .scenario_checkpoint_restore import CheckpointRestoreScenario
from .scenario_execution_metrics import ExecutionMetricsScenario

__all__ = [
    # Core components
    "MockSSEGenerator",
    "UnifiedChatClient",
    # Test scenarios
    "SSEConnectionScenario",
    "MessageStreamingScenario",
    "ModeSwitchingScenario",
    "ApprovalFlowScenario",
    "CheckpointRestoreScenario",
    "ExecutionMetricsScenario",
]
