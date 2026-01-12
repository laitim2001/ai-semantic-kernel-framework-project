"""
Correlation Analyzer - 關聯分析器

Sprint 82 - S82-2: 智能關聯與根因分析
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

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
)

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    關聯分析器

    功能:
    - 時間關聯分析
    - 系統依賴關聯分析
    - 語義相似關聯分析
    - 綜合關聯評分
    """

    def __init__(
        self,
        event_store: Optional[Any] = None,
        cmdb_client: Optional[Any] = None,
        memory_client: Optional[Any] = None,
    ):
        self._event_store = event_store
        self._cmdb_client = cmdb_client  # CMDB 客戶端
        self._memory_client = memory_client  # mem0 客戶端

        # 配置
        self._time_decay_factor = 0.1  # 時間衰減因子
        self._semantic_threshold = 0.6  # 語義相似度閾值

    async def find_correlations(
        self,
        event: Event,
        time_window: timedelta = timedelta(hours=1),
        correlation_types: Optional[List[CorrelationType]] = None,
        min_score: float = 0.3,
        max_results: int = 50,
    ) -> List[Correlation]:
        """
        尋找事件關聯

        Args:
            event: 目標事件
            time_window: 時間窗口
            correlation_types: 關聯類型列表
            min_score: 最小關聯分數
            max_results: 最大返回數量

        Returns:
            關聯列表
        """
        correlations: List[Correlation] = []
        types = correlation_types or [
            CorrelationType.TIME,
            CorrelationType.DEPENDENCY,
            CorrelationType.SEMANTIC,
        ]

        # 並行執行各類關聯分析
        tasks = []

        if CorrelationType.TIME in types:
            tasks.append(self._time_correlation(event, time_window))

        if CorrelationType.DEPENDENCY in types:
            tasks.append(self._dependency_correlation(event))

        if CorrelationType.SEMANTIC in types:
            tasks.append(self._semantic_correlation(event))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Correlation analysis failed: {result}")
            elif isinstance(result, list):
                correlations.extend(result)

        # 合併重複事件的關聯
        merged = self._merge_correlations(correlations)

        # 過濾和排序
        filtered = [c for c in merged if c.score >= min_score]
        filtered.sort(key=lambda c: c.score, reverse=True)

        return filtered[:max_results]

    async def _time_correlation(
        self,
        event: Event,
        time_window: timedelta,
    ) -> List[Correlation]:
        """
        時間關聯分析

        在指定時間窗口內查找相關事件
        """
        correlations: List[Correlation] = []

        # 計算時間範圍
        start_time = event.timestamp - time_window
        end_time = event.timestamp + time_window

        # 獲取時間窗口內的事件（模擬）
        nearby_events = await self._get_events_in_range(start_time, end_time)

        for other_event in nearby_events:
            if other_event.event_id == event.event_id:
                continue

            # 計算時間距離
            time_diff = abs((other_event.timestamp - event.timestamp).total_seconds())
            max_seconds = time_window.total_seconds()

            # 時間越近分數越高
            time_score = 1.0 - (time_diff / max_seconds)
            time_score = max(0.0, time_score)

            # 應用衰減
            time_score = time_score * (1.0 - self._time_decay_factor * (time_diff / 3600))

            if time_score > 0.1:
                correlation = Correlation(
                    correlation_id=f"corr_time_{uuid4().hex[:8]}",
                    source_event_id=event.event_id,
                    target_event_id=other_event.event_id,
                    correlation_type=CorrelationType.TIME,
                    score=time_score,
                    confidence=0.7,
                    evidence=[
                        f"Events occurred within {time_diff:.0f} seconds",
                        f"Time window: {time_window}",
                    ],
                    metadata={
                        "time_diff_seconds": time_diff,
                        "target_event_title": other_event.title,
                    },
                )
                correlations.append(correlation)

        return correlations

    async def _dependency_correlation(
        self,
        event: Event,
    ) -> List[Correlation]:
        """
        系統依賴關聯分析

        基於 CMDB 系統依賴關係查找相關事件
        """
        correlations: List[Correlation] = []

        # 獲取受影響組件的依賴關係
        dependencies = await self._get_dependencies(event.affected_components)

        # 查找依賴組件的相關事件
        for dep in dependencies:
            dep_events = await self._get_events_for_component(dep["component_id"])

            for other_event in dep_events:
                if other_event.event_id == event.event_id:
                    continue

                # 根據依賴距離計算分數
                dep_distance = dep.get("distance", 1)
                dep_score = 1.0 / (dep_distance + 1)

                # 根據依賴類型調整
                if dep.get("type") == "critical":
                    dep_score *= 1.2

                dep_score = min(1.0, dep_score)

                correlation = Correlation(
                    correlation_id=f"corr_dep_{uuid4().hex[:8]}",
                    source_event_id=event.event_id,
                    target_event_id=other_event.event_id,
                    correlation_type=CorrelationType.DEPENDENCY,
                    score=dep_score,
                    confidence=0.8,
                    evidence=[
                        f"Dependency relationship: {dep.get('relationship', 'unknown')}",
                        f"Dependency distance: {dep_distance}",
                    ],
                    metadata={
                        "dependency_type": dep.get("type"),
                        "component_id": dep["component_id"],
                    },
                )
                correlations.append(correlation)

        return correlations

    async def _semantic_correlation(
        self,
        event: Event,
    ) -> List[Correlation]:
        """
        語義相似關聯分析

        使用 mem0 向量搜索找出語義相似的事件
        """
        correlations: List[Correlation] = []

        # 構建搜索文本
        search_text = f"{event.title} {event.description}"

        # 使用 mem0 進行向量搜索
        similar_events = await self._search_similar_events(search_text)

        for item in similar_events:
            other_event = item["event"]
            similarity = item["similarity"]

            if other_event.event_id == event.event_id:
                continue

            if similarity < self._semantic_threshold:
                continue

            correlation = Correlation(
                correlation_id=f"corr_sem_{uuid4().hex[:8]}",
                source_event_id=event.event_id,
                target_event_id=other_event.event_id,
                correlation_type=CorrelationType.SEMANTIC,
                score=similarity,
                confidence=similarity * 0.9,
                evidence=[
                    f"Semantic similarity: {similarity:.2%}",
                    f"Similar description patterns detected",
                ],
                metadata={
                    "similarity_score": similarity,
                    "target_event_title": other_event.title,
                },
            )
            correlations.append(correlation)

        return correlations

    def _merge_correlations(
        self,
        correlations: List[Correlation],
    ) -> List[Correlation]:
        """合併同一目標事件的多種關聯"""
        merged: Dict[str, Correlation] = {}

        for corr in correlations:
            key = f"{corr.source_event_id}_{corr.target_event_id}"

            if key in merged:
                existing = merged[key]

                # 計算綜合分數
                time_score = 0.0
                dep_score = 0.0
                sem_score = 0.0

                for c in [existing, corr]:
                    if c.correlation_type == CorrelationType.TIME:
                        time_score = max(time_score, c.score)
                    elif c.correlation_type == CorrelationType.DEPENDENCY:
                        dep_score = max(dep_score, c.score)
                    elif c.correlation_type == CorrelationType.SEMANTIC:
                        sem_score = max(sem_score, c.score)

                combined_score = calculate_combined_score(time_score, dep_score, sem_score)

                # 更新現有關聯
                existing.score = combined_score
                existing.evidence.extend(corr.evidence)
                existing.metadata.update(corr.metadata)
            else:
                merged[key] = corr

        return list(merged.values())

    async def analyze(
        self,
        query: DiscoveryQuery,
    ) -> CorrelationResult:
        """
        執行完整的關聯分析

        Args:
            query: 分析查詢

        Returns:
            關聯分析結果
        """
        start_time = datetime.utcnow()

        # 獲取目標事件
        event = await self._get_event(query.event_id)
        if not event:
            raise ValueError(f"Event not found: {query.event_id}")

        # 尋找關聯
        correlations = await self.find_correlations(
            event=event,
            time_window=query.time_window,
            correlation_types=query.correlation_types or None,
            min_score=query.min_score,
            max_results=query.max_results,
        )

        # 構建關聯圖譜
        graph = await self._build_graph(event, correlations)

        # 計算分析時間
        analysis_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # 生成摘要
        summary = self._generate_summary(event, correlations)

        return CorrelationResult(
            query=query,
            event=event,
            correlations=correlations,
            graph=graph,
            analysis_time_ms=analysis_time,
            total_events_scanned=len(correlations) + 1,
            summary=summary,
        )

    async def _build_graph(
        self,
        event: Event,
        correlations: List[Correlation],
    ) -> CorrelationGraph:
        """構建關聯圖譜"""
        graph = CorrelationGraph(
            graph_id=f"graph_{uuid4().hex[:12]}",
            root_event_id=event.event_id,
        )

        # 添加根節點
        root_node = GraphNode(
            node_id=event.event_id,
            node_type="event",
            label=event.title,
            severity=event.severity,
            timestamp=event.timestamp,
            metadata={"is_root": True},
        )
        graph.add_node(root_node)

        # 添加關聯事件節點和邊
        for corr in correlations:
            target_event = await self._get_event(corr.target_event_id)
            if target_event:
                node = GraphNode(
                    node_id=target_event.event_id,
                    node_type="event",
                    label=target_event.title,
                    severity=target_event.severity,
                    timestamp=target_event.timestamp,
                )
                graph.add_node(node)

                edge = GraphEdge(
                    edge_id=f"edge_{uuid4().hex[:8]}",
                    source_id=event.event_id,
                    target_id=target_event.event_id,
                    relation_type=corr.correlation_type,
                    weight=corr.score,
                    label=f"{corr.correlation_type.value}: {corr.score:.2f}",
                )
                graph.add_edge(edge)

        return graph

    def _generate_summary(
        self,
        event: Event,
        correlations: List[Correlation],
    ) -> str:
        """生成分析摘要"""
        if not correlations:
            return f"No significant correlations found for event '{event.title}'."

        # 統計關聯類型
        type_counts = {}
        for corr in correlations:
            t = corr.correlation_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        type_summary = ", ".join(f"{t}: {c}" for t, c in type_counts.items())

        high_score_count = sum(1 for c in correlations if c.score >= 0.7)

        return (
            f"Found {len(correlations)} correlated events for '{event.title}'. "
            f"Correlation types: {type_summary}. "
            f"{high_score_count} events have high correlation score (>=0.7)."
        )

    # ========================================================================
    # Helper methods (模擬實現，實際應連接真實數據源)
    # ========================================================================

    async def _get_event(self, event_id: str) -> Optional[Event]:
        """獲取事件（模擬）"""
        # 模擬事件數據
        return Event(
            event_id=event_id,
            event_type=EventType.ALERT,
            title=f"Event {event_id}",
            description=f"Description for event {event_id}",
            severity=EventSeverity.WARNING,
            timestamp=datetime.utcnow(),
            source_system="monitoring",
            affected_components=["service-a", "service-b"],
        )

    async def _get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Event]:
        """獲取時間範圍內的事件（模擬）"""
        # 模擬一些事件
        events = []
        for i in range(5):
            events.append(Event(
                event_id=f"event_time_{i}",
                event_type=EventType.ALERT,
                title=f"Related Event {i}",
                description=f"Description {i}",
                severity=EventSeverity.WARNING,
                timestamp=start_time + timedelta(minutes=i * 10),
                source_system="monitoring",
            ))
        return events

    async def _get_dependencies(
        self,
        components: List[str],
    ) -> List[Dict[str, Any]]:
        """獲取組件依賴（模擬）"""
        dependencies = []
        for comp in components:
            dependencies.append({
                "component_id": f"{comp}_downstream",
                "relationship": "depends_on",
                "type": "critical",
                "distance": 1,
            })
        return dependencies

    async def _get_events_for_component(
        self,
        component_id: str,
    ) -> List[Event]:
        """獲取組件相關事件（模擬）"""
        return [Event(
            event_id=f"event_dep_{component_id}",
            event_type=EventType.ALERT,
            title=f"Event for {component_id}",
            description=f"Component event",
            severity=EventSeverity.WARNING,
            timestamp=datetime.utcnow(),
            source_system="monitoring",
            affected_components=[component_id],
        )]

    async def _search_similar_events(
        self,
        search_text: str,
    ) -> List[Dict[str, Any]]:
        """搜索語義相似事件（模擬）"""
        # 模擬語義搜索結果
        return [
            {
                "event": Event(
                    event_id="event_sem_1",
                    event_type=EventType.ALERT,
                    title="Similar Event 1",
                    description="Similar description",
                    severity=EventSeverity.WARNING,
                    timestamp=datetime.utcnow(),
                    source_system="monitoring",
                ),
                "similarity": 0.85,
            },
            {
                "event": Event(
                    event_id="event_sem_2",
                    event_type=EventType.INCIDENT,
                    title="Similar Event 2",
                    description="Another similar event",
                    severity=EventSeverity.ERROR,
                    timestamp=datetime.utcnow(),
                    source_system="alerting",
                ),
                "similarity": 0.72,
            },
        ]
