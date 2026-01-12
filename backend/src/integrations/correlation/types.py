"""
Correlation Types - 關聯分析類型定義

Sprint 82 - S82-2: 智能關聯與根因分析
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class CorrelationType(str, Enum):
    """關聯類型"""
    TIME = "time"  # 時間關聯
    DEPENDENCY = "dependency"  # 系統依賴關聯
    SEMANTIC = "semantic"  # 語義相似關聯
    CAUSAL = "causal"  # 因果關聯


class EventSeverity(str, Enum):
    """事件嚴重性"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(str, Enum):
    """事件類型"""
    ALERT = "alert"
    INCIDENT = "incident"
    CHANGE = "change"
    DEPLOYMENT = "deployment"
    METRIC_ANOMALY = "metric_anomaly"
    LOG_PATTERN = "log_pattern"
    SECURITY = "security"


@dataclass
class Event:
    """事件定義"""
    event_id: str
    event_type: EventType
    title: str
    description: str
    severity: EventSeverity
    timestamp: datetime
    source_system: str
    affected_components: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class Correlation:
    """關聯關係"""
    correlation_id: str
    source_event_id: str
    target_event_id: str
    correlation_type: CorrelationType
    score: float  # 0-1 關聯強度
    confidence: float  # 0-1 置信度
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphNode:
    """圖節點"""
    node_id: str
    node_type: str  # event / service / component
    label: str
    severity: Optional[EventSeverity] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """圖邊"""
    edge_id: str
    source_id: str
    target_id: str
    relation_type: CorrelationType
    weight: float
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationGraph:
    """關聯圖譜"""
    graph_id: str
    root_event_id: str
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: GraphNode) -> None:
        """添加節點"""
        if not any(n.node_id == node.node_id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        """添加邊"""
        if not any(e.edge_id == edge.edge_id for e in self.edges):
            self.edges.append(edge)

    def get_neighbors(self, node_id: str) -> List[str]:
        """獲取鄰居節點"""
        neighbors = set()
        for edge in self.edges:
            if edge.source_id == node_id:
                neighbors.add(edge.target_id)
            elif edge.target_id == node_id:
                neighbors.add(edge.source_id)
        return list(neighbors)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


@dataclass
class DiscoveryQuery:
    """關聯發現查詢"""
    event_id: str
    time_window: timedelta = field(default_factory=lambda: timedelta(hours=1))
    correlation_types: List[CorrelationType] = field(default_factory=list)
    min_score: float = 0.3
    max_results: int = 50
    include_indirect: bool = True  # 包含間接關聯
    metadata_filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationResult:
    """關聯分析結果"""
    query: DiscoveryQuery
    event: Event
    correlations: List[Correlation]
    graph: CorrelationGraph
    analysis_time_ms: int
    total_events_scanned: int
    summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# 關聯權重配置
CORRELATION_WEIGHTS = {
    CorrelationType.TIME: 0.40,
    CorrelationType.DEPENDENCY: 0.35,
    CorrelationType.SEMANTIC: 0.25,
}


def calculate_combined_score(
    time_score: float,
    dependency_score: float,
    semantic_score: float,
) -> float:
    """
    計算綜合關聯分數

    Args:
        time_score: 時間關聯分數 (0-1)
        dependency_score: 依賴關聯分數 (0-1)
        semantic_score: 語義關聯分數 (0-1)

    Returns:
        綜合分數 (0-1)
    """
    return (
        time_score * CORRELATION_WEIGHTS[CorrelationType.TIME] +
        dependency_score * CORRELATION_WEIGHTS[CorrelationType.DEPENDENCY] +
        semantic_score * CORRELATION_WEIGHTS[CorrelationType.SEMANTIC]
    )
