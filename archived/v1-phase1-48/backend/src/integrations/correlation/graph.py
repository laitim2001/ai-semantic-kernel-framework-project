"""
Correlation Graph - 關聯圖譜

Sprint 82 - S82-2: 智能關聯與根因分析
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .types import (
    Correlation,
    CorrelationGraph,
    CorrelationType,
    Event,
    GraphEdge,
    GraphNode,
)

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    關聯圖譜構建器

    功能:
    - 從關聯列表構建圖譜
    - 圖譜分析和遍歷
    - 多種輸出格式
    """

    def __init__(self):
        self._graph: Optional[CorrelationGraph] = None

    def build_from_correlations(
        self,
        root_event: Event,
        correlations: List[Correlation],
        related_events: Dict[str, Event],
    ) -> CorrelationGraph:
        """
        從關聯列表構建圖譜

        Args:
            root_event: 根事件
            correlations: 關聯列表
            related_events: 相關事件字典 {event_id: Event}

        Returns:
            CorrelationGraph: 關聯圖譜
        """
        graph = CorrelationGraph(
            graph_id=f"graph_{uuid4().hex[:12]}",
            root_event_id=root_event.event_id,
        )

        # 添加根節點
        root_node = self._create_node_from_event(root_event, is_root=True)
        graph.add_node(root_node)

        # 添加關聯節點和邊
        for corr in correlations:
            target_event = related_events.get(corr.target_event_id)
            if target_event:
                # 添加目標節點
                target_node = self._create_node_from_event(target_event)
                graph.add_node(target_node)

                # 添加邊
                edge = self._create_edge_from_correlation(corr)
                graph.add_edge(edge)

        self._graph = graph
        return graph

    def _create_node_from_event(
        self,
        event: Event,
        is_root: bool = False,
    ) -> GraphNode:
        """從事件創建節點"""
        return GraphNode(
            node_id=event.event_id,
            node_type="event",
            label=event.title[:50],  # 截斷標籤
            severity=event.severity,
            timestamp=event.timestamp,
            metadata={
                "is_root": is_root,
                "event_type": event.event_type.value,
                "source_system": event.source_system,
                "affected_components": event.affected_components,
            },
        )

    def _create_edge_from_correlation(
        self,
        correlation: Correlation,
    ) -> GraphEdge:
        """從關聯創建邊"""
        return GraphEdge(
            edge_id=correlation.correlation_id,
            source_id=correlation.source_event_id,
            target_id=correlation.target_event_id,
            relation_type=correlation.correlation_type,
            weight=correlation.score,
            label=f"{correlation.correlation_type.value}",
            metadata={
                "confidence": correlation.confidence,
                "evidence": correlation.evidence,
            },
        )

    def find_critical_path(self) -> List[str]:
        """
        尋找關鍵路徑

        Returns:
            節點 ID 列表，按重要性排序
        """
        if not self._graph:
            return []

        # 計算節點重要性（PageRank 簡化版）
        importance: Dict[str, float] = {}

        for node in self._graph.nodes:
            # 基礎分數
            score = 1.0

            # 嚴重性加權
            if node.severity:
                severity_weights = {
                    "critical": 4.0,
                    "error": 3.0,
                    "warning": 2.0,
                    "info": 1.0,
                }
                score *= severity_weights.get(node.severity.value, 1.0)

            # 連接數加權
            connections = sum(
                1 for e in self._graph.edges
                if e.source_id == node.node_id or e.target_id == node.node_id
            )
            score *= (1 + connections * 0.2)

            # 根節點加權
            if node.metadata.get("is_root"):
                score *= 1.5

            importance[node.node_id] = score

        # 按重要性排序
        sorted_nodes = sorted(
            importance.keys(),
            key=lambda x: importance[x],
            reverse=True,
        )

        return sorted_nodes

    def get_subgraph(
        self,
        center_node_id: str,
        depth: int = 2,
    ) -> CorrelationGraph:
        """
        獲取以指定節點為中心的子圖

        Args:
            center_node_id: 中心節點 ID
            depth: 搜索深度

        Returns:
            子圖
        """
        if not self._graph:
            return CorrelationGraph(
                graph_id=f"subgraph_{uuid4().hex[:8]}",
                root_event_id=center_node_id,
            )

        # BFS 遍歷
        visited: Set[str] = {center_node_id}
        queue = [(center_node_id, 0)]
        nodes_to_include: Set[str] = {center_node_id}

        while queue:
            current, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue

            neighbors = self._graph.get_neighbors(current)
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    nodes_to_include.add(neighbor)
                    queue.append((neighbor, current_depth + 1))

        # 構建子圖
        subgraph = CorrelationGraph(
            graph_id=f"subgraph_{uuid4().hex[:8]}",
            root_event_id=center_node_id,
        )

        for node in self._graph.nodes:
            if node.node_id in nodes_to_include:
                subgraph.add_node(node)

        for edge in self._graph.edges:
            if edge.source_id in nodes_to_include and edge.target_id in nodes_to_include:
                subgraph.add_edge(edge)

        return subgraph

    def to_json(self) -> Dict[str, Any]:
        """
        導出為 JSON 格式（適合前端渲染）

        Returns:
            JSON 可序列化的字典
        """
        if not self._graph:
            return {"nodes": [], "edges": []}

        nodes = [
            {
                "id": node.node_id,
                "type": node.node_type,
                "label": node.label,
                "severity": node.severity.value if node.severity else None,
                "timestamp": node.timestamp.isoformat() if node.timestamp else None,
                "metadata": node.metadata,
            }
            for node in self._graph.nodes
        ]

        edges = [
            {
                "id": edge.edge_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.relation_type.value,
                "weight": edge.weight,
                "label": edge.label,
            }
            for edge in self._graph.edges
        ]

        return {
            "graph_id": self._graph.graph_id,
            "root_event_id": self._graph.root_event_id,
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        }

    def to_mermaid(self) -> str:
        """
        導出為 Mermaid 格式（適合文檔嵌入）

        Returns:
            Mermaid 格式字符串
        """
        if not self._graph:
            return "graph TD\n    A[No data]"

        lines = ["graph TD"]

        # 添加節點定義
        for node in self._graph.nodes:
            # 根據嚴重性選擇形狀
            shape_start = "["
            shape_end = "]"
            if node.severity:
                if node.severity.value in ["critical", "error"]:
                    shape_start = "(("
                    shape_end = "))"
                elif node.severity.value == "warning":
                    shape_start = "{"
                    shape_end = "}"

            safe_label = node.label.replace('"', "'")[:30]
            lines.append(f"    {node.node_id}{shape_start}\"{safe_label}\"{shape_end}")

        # 添加邊
        for edge in self._graph.edges:
            arrow = "-->"
            if edge.relation_type == CorrelationType.DEPENDENCY:
                arrow = "-..->"
            elif edge.relation_type == CorrelationType.SEMANTIC:
                arrow = "==>"

            label = f"|{edge.relation_type.value}:{edge.weight:.1f}|"
            lines.append(f"    {edge.source_id} {arrow}{label} {edge.target_id}")

        return "\n".join(lines)

    def to_dot(self) -> str:
        """
        導出為 DOT 格式（Graphviz）

        Returns:
            DOT 格式字符串
        """
        if not self._graph:
            return 'digraph G { "No data" }'

        lines = [
            "digraph CorrelationGraph {",
            "    rankdir=TB;",
            "    node [shape=box];",
        ]

        # 節點樣式
        severity_colors = {
            "critical": "red",
            "error": "orange",
            "warning": "yellow",
            "info": "lightblue",
        }

        for node in self._graph.nodes:
            color = "lightgray"
            if node.severity:
                color = severity_colors.get(node.severity.value, "lightgray")

            safe_label = node.label.replace('"', '\\"')[:40]
            lines.append(
                f'    "{node.node_id}" [label="{safe_label}", '
                f'fillcolor="{color}", style="filled"];'
            )

        # 邊樣式
        edge_styles = {
            CorrelationType.TIME: "solid",
            CorrelationType.DEPENDENCY: "dashed",
            CorrelationType.SEMANTIC: "dotted",
        }

        for edge in self._graph.edges:
            style = edge_styles.get(edge.relation_type, "solid")
            weight = int(edge.weight * 3) + 1

            lines.append(
                f'    "{edge.source_id}" -> "{edge.target_id}" '
                f'[label="{edge.relation_type.value}", '
                f'style="{style}", penwidth={weight}];'
            )

        lines.append("}")

        return "\n".join(lines)

    def analyze_clusters(self) -> List[Dict[str, Any]]:
        """
        分析圖中的集群

        Returns:
            集群信息列表
        """
        if not self._graph or not self._graph.nodes:
            return []

        # 簡單的連通分量分析
        visited: Set[str] = set()
        clusters: List[Set[str]] = []

        for node in self._graph.nodes:
            if node.node_id not in visited:
                cluster = self._dfs_component(node.node_id, visited)
                clusters.append(cluster)

        # 構建集群信息
        cluster_info = []
        for i, cluster in enumerate(clusters):
            nodes_in_cluster = [n for n in self._graph.nodes if n.node_id in cluster]

            cluster_info.append({
                "cluster_id": f"cluster_{i}",
                "size": len(cluster),
                "node_ids": list(cluster),
                "severity_distribution": self._count_severities(nodes_in_cluster),
                "has_root": self._graph.root_event_id in cluster,
            })

        return sorted(cluster_info, key=lambda x: x["size"], reverse=True)

    def _dfs_component(
        self,
        start_id: str,
        visited: Set[str],
    ) -> Set[str]:
        """DFS 遍歷連通分量"""
        component: Set[str] = set()
        stack = [start_id]

        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue

            visited.add(node_id)
            component.add(node_id)

            if self._graph:
                neighbors = self._graph.get_neighbors(node_id)
                for neighbor in neighbors:
                    if neighbor not in visited:
                        stack.append(neighbor)

        return component

    def _count_severities(
        self,
        nodes: List[GraphNode],
    ) -> Dict[str, int]:
        """統計嚴重性分佈"""
        counts: Dict[str, int] = {}
        for node in nodes:
            if node.severity:
                s = node.severity.value
                counts[s] = counts.get(s, 0) + 1
        return counts
