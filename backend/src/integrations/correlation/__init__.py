"""
Correlation System - 關聯分析系統

Sprint 82 - S82-2: 智能關聯與根因分析

提供:
- CorrelationAnalyzer: 關聯分析器
- GraphBuilder: 圖譜構建器
- 關聯類型和圖譜數據結構
"""

from .analyzer import CorrelationAnalyzer
from .graph import GraphBuilder
from .types import (
    Correlation,
    CorrelationGraph,
    CorrelationResult,
    CorrelationType,
    DiscoveryQuery,
    Event,
    EventSeverity,
    EventType,
    GraphEdge,
    GraphNode,
    calculate_combined_score,
    CORRELATION_WEIGHTS,
)

__all__ = [
    # Core classes
    "CorrelationAnalyzer",
    "GraphBuilder",
    # Types
    "Event",
    "EventType",
    "EventSeverity",
    "Correlation",
    "CorrelationType",
    "CorrelationGraph",
    "CorrelationResult",
    "DiscoveryQuery",
    "GraphNode",
    "GraphEdge",
    # Utilities
    "calculate_combined_score",
    "CORRELATION_WEIGHTS",
]

# 版本信息
__version__ = "1.0.0"
__sprint__ = "82"
