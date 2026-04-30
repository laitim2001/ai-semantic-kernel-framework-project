"""
Root Cause Analysis Types - 根因分析類型定義

Sprint 82 - S82-2: 智能關聯與根因分析
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AnalysisStatus(str, Enum):
    """分析狀態"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceType(str, Enum):
    """證據類型"""
    LOG = "log"
    METRIC = "metric"
    TRACE = "trace"
    CORRELATION = "correlation"
    PATTERN = "pattern"
    EXPERT = "expert"


class RecommendationType(str, Enum):
    """建議類型"""
    IMMEDIATE = "immediate"  # 立即處理
    SHORT_TERM = "short_term"  # 短期修復
    LONG_TERM = "long_term"  # 長期優化
    PREVENTIVE = "preventive"  # 預防措施


@dataclass
class Evidence:
    """證據"""
    evidence_id: str
    evidence_type: EvidenceType
    description: str
    source: str
    timestamp: datetime
    relevance_score: float  # 0-1 相關性分數
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    """修復建議"""
    recommendation_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    priority: int  # 1-5, 1 最高
    estimated_effort: str  # 估計工時
    affected_components: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoricalCase:
    """歷史相似案例"""
    case_id: str
    title: str
    description: str
    root_cause: str
    resolution: str
    occurred_at: datetime
    resolved_at: Optional[datetime]
    similarity_score: float  # 0-1 相似度
    lessons_learned: List[str] = field(default_factory=list)


@dataclass
class RootCauseHypothesis:
    """根因假設"""
    hypothesis_id: str
    description: str
    confidence: float  # 0-1 置信度
    evidence: List[Evidence] = field(default_factory=list)
    supporting_events: List[str] = field(default_factory=list)
    contradicting_events: List[str] = field(default_factory=list)


@dataclass
class RootCauseAnalysis:
    """根因分析結果"""
    analysis_id: str
    event_id: str
    status: AnalysisStatus
    started_at: datetime
    completed_at: Optional[datetime]
    root_cause: str
    confidence: float  # 0-1 整體置信度
    hypotheses: List[RootCauseHypothesis] = field(default_factory=list)
    evidence_chain: List[Evidence] = field(default_factory=list)
    contributing_factors: List[str] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    similar_historical_cases: List[HistoricalCase] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """分析持續時間"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def evidence_count(self) -> int:
        """證據數量"""
        return len(self.evidence_chain)

    @property
    def recommendation_count(self) -> int:
        """建議數量"""
        return len(self.recommendations)


@dataclass
class AnalysisRequest:
    """分析請求"""
    event_id: str
    include_historical: bool = True
    max_hypotheses: int = 5
    min_confidence: float = 0.3
    analysis_depth: str = "standard"  # quick / standard / deep
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisContext:
    """分析上下文"""
    event_id: str
    event_data: Dict[str, Any]
    correlations: List[Dict[str, Any]]
    graph_data: Dict[str, Any]
    historical_patterns: List[Dict[str, Any]]
    system_context: Dict[str, Any] = field(default_factory=dict)


# 分析深度配置
ANALYSIS_DEPTH_CONFIG = {
    "quick": {
        "max_correlations": 10,
        "max_historical": 3,
        "timeout_seconds": 30,
    },
    "standard": {
        "max_correlations": 50,
        "max_historical": 10,
        "timeout_seconds": 120,
    },
    "deep": {
        "max_correlations": 100,
        "max_historical": 20,
        "timeout_seconds": 300,
    },
}


def calculate_overall_confidence(
    hypotheses: List[RootCauseHypothesis],
) -> float:
    """
    計算整體置信度

    基於最高置信假設和證據支持度
    """
    if not hypotheses:
        return 0.0

    # 取最高置信假設
    max_confidence = max(h.confidence for h in hypotheses)

    # 考慮證據數量
    top_hypothesis = max(hypotheses, key=lambda h: h.confidence)
    evidence_factor = min(1.0, len(top_hypothesis.evidence) / 5)

    # 考慮矛盾證據
    contradiction_penalty = 0.0
    if top_hypothesis.contradicting_events:
        contradiction_penalty = min(0.3, len(top_hypothesis.contradicting_events) * 0.1)

    return max(0.0, (max_confidence * 0.7 + evidence_factor * 0.3) - contradiction_penalty)
