# =============================================================================
# IPA Platform - AG-UI Advanced Features
# =============================================================================
# Sprint 60: AG-UI Advanced Features (5-7) + Integration
#
# Advanced AG-UI features including:
#   - Tool-based Generative UI (S60-1)
#   - Shared State (S60-2)
#   - Predictive State Updates (S60-3)
#
# Dependencies:
#   - AG-UI Events (src.integrations.ag_ui.events)
#   - AG-UI Bridge (src.integrations.ag_ui.bridge)
#   - AG-UI Thread (src.integrations.ag_ui.thread)
# =============================================================================

from src.integrations.ag_ui.features.advanced.tool_ui import (
    UIComponentType,
    UIComponentDefinition,
    UIComponentSchema,
    ToolBasedUIHandler,
    create_tool_ui_handler,
)
from src.integrations.ag_ui.features.advanced.shared_state import (
    SharedStateHandler,
    StateSyncManager,
    StateDiff,
    create_shared_state_handler,
)
from src.integrations.ag_ui.features.advanced.predictive import (
    PredictiveStateHandler,
    PredictionResult,
    PredictionStatus,
    create_predictive_handler,
)

__all__ = [
    # S60-1: Tool-based Generative UI
    "UIComponentType",
    "UIComponentDefinition",
    "UIComponentSchema",
    "ToolBasedUIHandler",
    "create_tool_ui_handler",
    # S60-2: Shared State
    "SharedStateHandler",
    "StateSyncManager",
    "StateDiff",
    "create_shared_state_handler",
    # S60-3: Predictive State Updates
    "PredictiveStateHandler",
    "PredictionResult",
    "PredictionStatus",
    "create_predictive_handler",
]
