"""
Correlation API Routes - 關聯分析 API 路由

Sprint 82 - S82-2: 智能關聯與根因分析

API Endpoints:
- POST   /api/v1/correlation/analyze     # 分析事件關聯
- GET    /api/v1/correlation/{event_id}  # 獲取事件關聯
- POST   /api/v1/rootcause/analyze       # 根因分析
- GET    /api/v1/rootcause/{analysis_id} # 獲取根因分析結果
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/correlation", tags=["correlation"])


# ============================================================================
# Request/Response Models
# ============================================================================


class EventModel(BaseModel):
    """事件模型"""
    event_id: str
    event_type: str
    title: str
    description: str
    severity: str
    timestamp: datetime
    source_system: str
    affected_components: List[str] = []
    tags: List[str] = []


class CorrelationModel(BaseModel):
    """關聯模型"""
    correlation_id: str
    source_event_id: str
    target_event_id: str
    correlation_type: str
    score: float
    confidence: float
    evidence: List[str]


class GraphNodeModel(BaseModel):
    """圖節點模型"""
    id: str
    type: str
    label: str
    severity: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class GraphEdgeModel(BaseModel):
    """圖邊模型"""
    id: str
    source: str
    target: str
    type: str
    weight: float
    label: str = ""


class GraphModel(BaseModel):
    """關聯圖譜模型"""
    graph_id: str
    root_event_id: str
    nodes: List[GraphNodeModel]
    edges: List[GraphEdgeModel]
    statistics: Dict[str, int]


class CorrelationAnalyzeRequest(BaseModel):
    """關聯分析請求"""
    event_id: str
    time_window_hours: int = Field(1, ge=1, le=168, description="時間窗口（小時）")
    correlation_types: Optional[List[str]] = Field(
        None,
        description="關聯類型",
        example=["time", "dependency", "semantic"],
    )
    min_score: float = Field(0.3, ge=0.0, le=1.0, description="最小關聯分數")
    max_results: int = Field(50, ge=1, le=200, description="最大返回數量")
    include_graph: bool = Field(True, description="是否包含圖譜")


class CorrelationAnalyzeResponse(BaseModel):
    """關聯分析響應"""
    event: EventModel
    correlations: List[CorrelationModel]
    graph: Optional[GraphModel] = None
    analysis_time_ms: int
    total_events_scanned: int
    summary: str


class RootCauseAnalyzeRequest(BaseModel):
    """根因分析請求"""
    event_id: str
    include_historical: bool = True
    max_hypotheses: int = Field(5, ge=1, le=10)
    analysis_depth: str = Field("standard", description="分析深度: quick/standard/deep")


class EvidenceModel(BaseModel):
    """證據模型"""
    evidence_id: str
    evidence_type: str
    description: str
    source: str
    timestamp: datetime
    relevance_score: float


class RecommendationModel(BaseModel):
    """建議模型"""
    recommendation_id: str
    recommendation_type: str
    title: str
    description: str
    priority: int
    estimated_effort: str
    steps: List[str]


class HistoricalCaseModel(BaseModel):
    """歷史案例模型"""
    case_id: str
    title: str
    root_cause: str
    resolution: str
    similarity_score: float


class RootCauseAnalyzeResponse(BaseModel):
    """根因分析響應"""
    analysis_id: str
    event_id: str
    status: str
    root_cause: str
    confidence: float
    evidence_chain: List[EvidenceModel]
    contributing_factors: List[str]
    recommendations: List[RecommendationModel]
    similar_historical_cases: List[HistoricalCaseModel]
    analysis_time_ms: int


# ============================================================================
# In-Memory Storage
# ============================================================================

_correlation_cache: Dict[str, Dict[str, Any]] = {}
_rootcause_cache: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Correlation API Endpoints
# ============================================================================


@router.post("/analyze", response_model=CorrelationAnalyzeResponse)
async def analyze_correlation(request: CorrelationAnalyzeRequest) -> CorrelationAnalyzeResponse:
    """
    分析事件關聯

    根據指定事件尋找相關聯的事件，並構建關聯圖譜。
    """
    logger.info(f"Analyzing correlations for event: {request.event_id}")
    start_time = datetime.utcnow()

    # 模擬事件
    event = EventModel(
        event_id=request.event_id,
        event_type="alert",
        title=f"Alert for {request.event_id}",
        description="System alert requiring attention",
        severity="warning",
        timestamp=datetime.utcnow(),
        source_system="monitoring",
        affected_components=["service-a", "service-b"],
    )

    # 模擬關聯
    correlations = [
        CorrelationModel(
            correlation_id=f"corr_{uuid4().hex[:8]}",
            source_event_id=request.event_id,
            target_event_id=f"event_time_{i}",
            correlation_type="time",
            score=0.8 - i * 0.1,
            confidence=0.7,
            evidence=[
                f"Events occurred within {i * 10} minutes",
                "Same affected component",
            ],
        )
        for i in range(3)
    ] + [
        CorrelationModel(
            correlation_id=f"corr_{uuid4().hex[:8]}",
            source_event_id=request.event_id,
            target_event_id=f"event_dep_{i}",
            correlation_type="dependency",
            score=0.7 - i * 0.1,
            confidence=0.8,
            evidence=[
                "System dependency relationship",
                f"Distance: {i + 1} hop",
            ],
        )
        for i in range(2)
    ]

    # 過濾
    correlations = [c for c in correlations if c.score >= request.min_score]
    correlations = correlations[:request.max_results]

    # 構建圖譜
    graph = None
    if request.include_graph:
        nodes = [
            GraphNodeModel(
                id=event.event_id,
                type="event",
                label=event.title[:30],
                severity=event.severity,
                timestamp=event.timestamp,
                metadata={"is_root": True},
            )
        ]

        edges = []
        for corr in correlations:
            nodes.append(GraphNodeModel(
                id=corr.target_event_id,
                type="event",
                label=f"Event {corr.target_event_id}",
                severity="warning",
                timestamp=datetime.utcnow(),
            ))
            edges.append(GraphEdgeModel(
                id=corr.correlation_id,
                source=corr.source_event_id,
                target=corr.target_event_id,
                type=corr.correlation_type,
                weight=corr.score,
                label=f"{corr.correlation_type}: {corr.score:.2f}",
            ))

        graph = GraphModel(
            graph_id=f"graph_{uuid4().hex[:8]}",
            root_event_id=event.event_id,
            nodes=nodes,
            edges=edges,
            statistics={
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        )

    analysis_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    # 緩存結果
    _correlation_cache[request.event_id] = {
        "event": event.model_dump(),
        "correlations": [c.model_dump() for c in correlations],
        "graph": graph.model_dump() if graph else None,
        "timestamp": datetime.utcnow().isoformat(),
    }

    return CorrelationAnalyzeResponse(
        event=event,
        correlations=correlations,
        graph=graph,
        analysis_time_ms=analysis_time,
        total_events_scanned=len(correlations) + 1,
        summary=f"Found {len(correlations)} correlated events for '{event.title}'.",
    )


@router.get("/{event_id}", response_model=CorrelationAnalyzeResponse)
async def get_event_correlations(
    event_id: str,
    refresh: bool = Query(False, description="是否重新分析"),
) -> CorrelationAnalyzeResponse:
    """
    獲取事件關聯

    獲取指定事件的關聯分析結果（使用緩存或重新分析）。
    """
    if not refresh and event_id in _correlation_cache:
        cached = _correlation_cache[event_id]
        return CorrelationAnalyzeResponse(
            event=EventModel(**cached["event"]),
            correlations=[CorrelationModel(**c) for c in cached["correlations"]],
            graph=GraphModel(**cached["graph"]) if cached["graph"] else None,
            analysis_time_ms=0,
            total_events_scanned=len(cached["correlations"]) + 1,
            summary=f"Retrieved cached analysis for event {event_id}.",
        )

    # 執行新分析
    return await analyze_correlation(CorrelationAnalyzeRequest(event_id=event_id))


# ============================================================================
# Root Cause Analysis API Endpoints
# ============================================================================


@router.post("/rootcause/analyze", response_model=RootCauseAnalyzeResponse)
async def analyze_root_cause(request: RootCauseAnalyzeRequest) -> RootCauseAnalyzeResponse:
    """
    根因分析

    對指定事件執行 Claude 驅動的根因分析。
    """
    logger.info(f"Analyzing root cause for event: {request.event_id}")
    start_time = datetime.utcnow()

    analysis_id = f"rca_{uuid4().hex[:12]}"

    # 模擬證據
    evidence_chain = [
        EvidenceModel(
            evidence_id=f"ev_{uuid4().hex[:8]}",
            evidence_type="correlation",
            description="High correlation with database timeout events",
            source="correlation_analysis",
            timestamp=datetime.utcnow(),
            relevance_score=0.85,
        ),
        EvidenceModel(
            evidence_id=f"ev_{uuid4().hex[:8]}",
            evidence_type="metric",
            description="Database connection pool utilization at 95%",
            source="metrics_system",
            timestamp=datetime.utcnow(),
            relevance_score=0.90,
        ),
        EvidenceModel(
            evidence_id=f"ev_{uuid4().hex[:8]}",
            evidence_type="log",
            description="Multiple 'connection timeout' errors in application logs",
            source="log_analysis",
            timestamp=datetime.utcnow(),
            relevance_score=0.88,
        ),
    ]

    # 模擬建議
    recommendations = [
        RecommendationModel(
            recommendation_id=f"rec_{uuid4().hex[:8]}",
            recommendation_type="immediate",
            title="Increase Connection Pool Size",
            description="Immediately increase the database connection pool size to handle current load",
            priority=1,
            estimated_effort="30 minutes",
            steps=[
                "Update database connection pool configuration",
                "Restart affected services",
                "Verify connection pool utilization decreases",
            ],
        ),
        RecommendationModel(
            recommendation_id=f"rec_{uuid4().hex[:8]}",
            recommendation_type="short_term",
            title="Implement Connection Pool Monitoring",
            description="Add monitoring and alerting for connection pool utilization",
            priority=2,
            estimated_effort="2-4 hours",
            steps=[
                "Add connection pool metrics to monitoring system",
                "Create alerts for >80% utilization",
                "Document runbook for connection pool issues",
            ],
        ),
        RecommendationModel(
            recommendation_id=f"rec_{uuid4().hex[:8]}",
            recommendation_type="preventive",
            title="Review Database Connection Management",
            description="Review and optimize database connection handling across services",
            priority=3,
            estimated_effort="1-2 weeks",
            steps=[
                "Audit connection usage patterns",
                "Implement connection pooling best practices",
                "Add automated scaling for connection pools",
            ],
        ),
    ]

    # 模擬歷史案例
    historical_cases = [
        HistoricalCaseModel(
            case_id="case_001",
            title="Database Connection Pool Exhaustion",
            root_cause="Connection pool size too small for traffic spike",
            resolution="Increased connection pool size and added auto-scaling",
            similarity_score=0.85,
        ),
        HistoricalCaseModel(
            case_id="case_002",
            title="Connection Leak in Application",
            root_cause="Unclosed connections in error handling path",
            resolution="Fixed connection cleanup in exception handlers",
            similarity_score=0.72,
        ),
    ]

    analysis_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    result = RootCauseAnalyzeResponse(
        analysis_id=analysis_id,
        event_id=request.event_id,
        status="completed",
        root_cause=(
            "Database connection pool exhaustion due to traffic spike. "
            "The connection pool reached 95% utilization, causing connection "
            "timeouts and cascading failures in dependent services."
        ),
        confidence=0.87,
        evidence_chain=evidence_chain,
        contributing_factors=[
            "Unexpected traffic increase of 150%",
            "Connection pool size not scaled with load",
            "Missing connection pool monitoring alerts",
        ],
        recommendations=recommendations,
        similar_historical_cases=historical_cases if request.include_historical else [],
        analysis_time_ms=analysis_time,
    )

    # 緩存結果
    _rootcause_cache[analysis_id] = result.model_dump()

    return result


@router.get("/rootcause/{analysis_id}", response_model=RootCauseAnalyzeResponse)
async def get_root_cause_analysis(analysis_id: str) -> RootCauseAnalyzeResponse:
    """
    獲取根因分析結果

    根據分析 ID 獲取根因分析詳細結果。
    """
    if analysis_id in _rootcause_cache:
        return RootCauseAnalyzeResponse(**_rootcause_cache[analysis_id])

    raise HTTPException(status_code=404, detail=f"Analysis not found: {analysis_id}")


@router.get("/graph/{event_id}/mermaid")
async def get_correlation_graph_mermaid(event_id: str) -> Dict[str, str]:
    """
    獲取 Mermaid 格式的關聯圖譜

    返回可嵌入 Markdown 的 Mermaid 圖譜代碼。
    """
    if event_id not in _correlation_cache:
        # 先執行分析
        await analyze_correlation(CorrelationAnalyzeRequest(event_id=event_id))

    cached = _correlation_cache.get(event_id)
    if not cached or not cached.get("graph"):
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = cached["graph"]

    # 生成 Mermaid 代碼
    lines = ["graph TD"]

    for node in graph["nodes"]:
        shape_start = "[["
        shape_end = "]]"
        if node.get("metadata", {}).get("is_root"):
            shape_start = "(("
            shape_end = "))"

        safe_label = node["label"].replace('"', "'")[:30]
        lines.append(f"    {node['id']}{shape_start}\"{safe_label}\"{shape_end}")

    for edge in graph["edges"]:
        lines.append(f"    {edge['source']} -->|{edge['type']}| {edge['target']}")

    mermaid_code = "\n".join(lines)

    return {
        "event_id": event_id,
        "format": "mermaid",
        "code": mermaid_code,
    }


@router.get("/graph/{event_id}/json")
async def get_correlation_graph_json(event_id: str) -> Dict[str, Any]:
    """
    獲取 JSON 格式的關聯圖譜

    返回圖譜的完整 JSON 結構，適用於前端視覺化。
    """
    if event_id not in _correlation_cache:
        # 先執行分析
        await analyze_correlation(CorrelationAnalyzeRequest(event_id=event_id))

    cached = _correlation_cache.get(event_id)
    if not cached or not cached.get("graph"):
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = cached["graph"]

    return {
        "event_id": event_id,
        "format": "json",
        "graph": {
            "graph_id": graph["graph_id"],
            "root_event_id": graph["root_event_id"],
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "statistics": graph["statistics"],
        },
    }


@router.get("/graph/{event_id}/dot")
async def get_correlation_graph_dot(event_id: str) -> Dict[str, str]:
    """
    獲取 DOT (Graphviz) 格式的關聯圖譜

    返回 Graphviz DOT 語言格式，可用於生成 PNG/SVG 圖像。
    """
    if event_id not in _correlation_cache:
        # 先執行分析
        await analyze_correlation(CorrelationAnalyzeRequest(event_id=event_id))

    cached = _correlation_cache.get(event_id)
    if not cached or not cached.get("graph"):
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = cached["graph"]

    # 生成 DOT 代碼
    lines = [
        "digraph correlation_graph {",
        "    rankdir=TB;",
        "    node [shape=box, style=rounded];",
        "",
    ]

    # 添加節點
    for node in graph["nodes"]:
        safe_label = node["label"].replace('"', '\\"')[:30]
        color = "lightblue"
        if node.get("metadata", {}).get("is_root"):
            color = "lightgreen"
        elif node.get("severity") == "critical":
            color = "lightcoral"
        elif node.get("severity") == "warning":
            color = "lightyellow"

        lines.append(f'    "{node["id"]}" [label="{safe_label}", fillcolor={color}, style=filled];')

    lines.append("")

    # 添加邊
    for edge in graph["edges"]:
        label = f'{edge["type"]}: {edge["weight"]:.2f}'
        lines.append(f'    "{edge["source"]}" -> "{edge["target"]}" [label="{label}"];')

    lines.append("}")

    dot_code = "\n".join(lines)

    return {
        "event_id": event_id,
        "format": "dot",
        "code": dot_code,
    }
