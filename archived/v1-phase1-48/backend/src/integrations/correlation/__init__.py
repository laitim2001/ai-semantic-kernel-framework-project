"""
Correlation System - 關聯分析系統

Sprint 82 - S82-2: 智能關聯與根因分析
Sprint 130 - Story 130-1: 真實資料來源連接

提供:
- CorrelationAnalyzer: 關聯分析器
- GraphBuilder: 圖譜構建器
- EventDataSource: 事件資料來源（Azure Monitor / App Insights）
- EventCollector: 事件收集與聚合
- 關聯類型和圖譜數據結構
"""

from .analyzer import CorrelationAnalyzer
from .data_source import AzureMonitorConfig, EventDataSource
from .event_collector import CollectionConfig, EventCollector
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
    # Sprint 130: Data source
    "AzureMonitorConfig",
    "EventDataSource",
    "CollectionConfig",
    "EventCollector",
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
__version__ = "2.0.0"
__sprint__ = "130"
