"""
Root Cause Analyzer - 根因分析器

Sprint 82 - S82-2: 智能關聯與根因分析
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..correlation import (
    Correlation,
    CorrelationAnalyzer,
    CorrelationGraph,
    Event,
)
from .types import (
    AnalysisContext,
    AnalysisRequest,
    AnalysisStatus,
    ANALYSIS_DEPTH_CONFIG,
    Evidence,
    EvidenceType,
    HistoricalCase,
    Recommendation,
    RecommendationType,
    RootCauseAnalysis,
    RootCauseHypothesis,
    calculate_overall_confidence,
)

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """
    根因分析器

    功能:
    - 基於關聯圖譜分析根因
    - Claude 驅動的智能推理
    - 歷史案例匹配
    - 修復建議生成
    """

    def __init__(
        self,
        claude_client: Optional[Any] = None,
        correlation_analyzer: Optional[CorrelationAnalyzer] = None,
        knowledge_base: Optional[Any] = None,
    ):
        self._claude_client = claude_client
        self._correlation_analyzer = correlation_analyzer or CorrelationAnalyzer()
        self._knowledge_base = knowledge_base

        # 分析配置
        self._default_depth = "standard"

    async def analyze_root_cause(
        self,
        event: Event,
        correlations: List[Correlation],
        graph: Optional[CorrelationGraph] = None,
    ) -> RootCauseAnalysis:
        """
        分析事件根因

        Args:
            event: 目標事件
            correlations: 關聯列表
            graph: 關聯圖譜

        Returns:
            RootCauseAnalysis: 根因分析結果
        """
        analysis_id = f"rca_{uuid4().hex[:12]}"
        started_at = datetime.utcnow()

        logger.info(f"Starting root cause analysis: {analysis_id} for event: {event.event_id}")

        try:
            # 1. 構建分析上下文
            context = await self._build_analysis_context(event, correlations, graph)

            # 2. 獲取歷史相似案例
            historical_cases = await self.get_similar_patterns(event)

            # 3. 生成根因假設
            hypotheses = await self._generate_hypotheses(context, historical_cases)

            # 4. 使用 Claude 分析根因
            root_cause, confidence, evidence_chain = await self._claude_analyze(
                event, context, hypotheses, historical_cases
            )

            # 5. 識別貢獻因素
            contributing_factors = self._identify_contributing_factors(
                correlations, hypotheses
            )

            # 6. 生成修復建議
            recommendations = await self._generate_recommendations(
                root_cause, contributing_factors, historical_cases
            )

            completed_at = datetime.utcnow()

            analysis = RootCauseAnalysis(
                analysis_id=analysis_id,
                event_id=event.event_id,
                status=AnalysisStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                root_cause=root_cause,
                confidence=confidence,
                hypotheses=hypotheses,
                evidence_chain=evidence_chain,
                contributing_factors=contributing_factors,
                recommendations=recommendations,
                similar_historical_cases=historical_cases,
                metadata={
                    "correlation_count": len(correlations),
                    "hypothesis_count": len(hypotheses),
                    "evidence_count": len(evidence_chain),
                },
            )

            logger.info(
                f"Root cause analysis completed: {analysis_id} "
                f"(Confidence: {confidence:.2%})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Root cause analysis failed: {analysis_id} - {e}")

            return RootCauseAnalysis(
                analysis_id=analysis_id,
                event_id=event.event_id,
                status=AnalysisStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                root_cause="Analysis failed",
                confidence=0.0,
                metadata={"error": str(e)},
            )

    async def _build_analysis_context(
        self,
        event: Event,
        correlations: List[Correlation],
        graph: Optional[CorrelationGraph],
    ) -> AnalysisContext:
        """構建分析上下文"""
        return AnalysisContext(
            event_id=event.event_id,
            event_data={
                "title": event.title,
                "description": event.description,
                "severity": event.severity.value,
                "type": event.event_type.value,
                "source": event.source_system,
                "components": event.affected_components,
                "timestamp": event.timestamp.isoformat(),
            },
            correlations=[
                {
                    "target_id": c.target_event_id,
                    "type": c.correlation_type.value,
                    "score": c.score,
                    "evidence": c.evidence,
                }
                for c in correlations
            ],
            graph_data={
                "node_count": graph.node_count if graph else 0,
                "edge_count": graph.edge_count if graph else 0,
                "root_id": graph.root_event_id if graph else event.event_id,
            },
            historical_patterns=[],
            system_context={
                "analysis_time": datetime.utcnow().isoformat(),
            },
        )

    async def get_similar_patterns(
        self,
        event: Event,
        max_results: int = 10,
    ) -> List[HistoricalCase]:
        """
        獲取歷史相似案例

        Args:
            event: 目標事件
            max_results: 最大返回數量

        Returns:
            歷史案例列表
        """
        # 模擬歷史案例查詢
        # 實際應該從知識庫或歷史數據庫查詢
        cases = [
            HistoricalCase(
                case_id="case_001",
                title="Database Connection Pool Exhaustion",
                description="Similar database connection issues causing service degradation",
                root_cause="Connection pool size too small for traffic spike",
                resolution="Increased connection pool size and added auto-scaling",
                occurred_at=datetime.utcnow(),
                resolved_at=datetime.utcnow(),
                similarity_score=0.85,
                lessons_learned=[
                    "Monitor connection pool utilization",
                    "Set up alerts for high connection usage",
                    "Implement connection timeout policies",
                ],
            ),
            HistoricalCase(
                case_id="case_002",
                title="Memory Leak in Service",
                description="Gradual memory increase leading to OOM",
                root_cause="Unclosed HTTP connections in client library",
                resolution="Updated client library and added explicit cleanup",
                occurred_at=datetime.utcnow(),
                resolved_at=datetime.utcnow(),
                similarity_score=0.72,
                lessons_learned=[
                    "Regular dependency updates",
                    "Memory profiling in staging",
                    "Set memory limits with proper restart policies",
                ],
            ),
        ]

        return cases[:max_results]

    async def _generate_hypotheses(
        self,
        context: AnalysisContext,
        historical_cases: List[HistoricalCase],
    ) -> List[RootCauseHypothesis]:
        """生成根因假設"""
        hypotheses: List[RootCauseHypothesis] = []

        # 基於關聯生成假設
        high_score_correlations = [
            c for c in context.correlations if c["score"] >= 0.7
        ]

        for i, corr in enumerate(high_score_correlations[:3]):
            hypothesis = RootCauseHypothesis(
                hypothesis_id=f"hyp_{uuid4().hex[:8]}",
                description=f"Root cause related to correlated event {corr['target_id']}",
                confidence=corr["score"] * 0.8,
                evidence=[
                    Evidence(
                        evidence_id=f"ev_{uuid4().hex[:8]}",
                        evidence_type=EvidenceType.CORRELATION,
                        description=f"High correlation ({corr['score']:.2%}) via {corr['type']}",
                        source="correlation_analysis",
                        timestamp=datetime.utcnow(),
                        relevance_score=corr["score"],
                        data=corr,
                    )
                ],
                supporting_events=[corr["target_id"]],
            )
            hypotheses.append(hypothesis)

        # 基於歷史案例生成假設
        for case in historical_cases[:2]:
            if case.similarity_score >= 0.7:
                hypothesis = RootCauseHypothesis(
                    hypothesis_id=f"hyp_{uuid4().hex[:8]}",
                    description=f"Similar to historical case: {case.root_cause}",
                    confidence=case.similarity_score * 0.7,
                    evidence=[
                        Evidence(
                            evidence_id=f"ev_{uuid4().hex[:8]}",
                            evidence_type=EvidenceType.PATTERN,
                            description=f"Similar to case {case.case_id}: {case.title}",
                            source="knowledge_base",
                            timestamp=datetime.utcnow(),
                            relevance_score=case.similarity_score,
                            data={
                                "case_id": case.case_id,
                                "resolution": case.resolution,
                            },
                        )
                    ],
                )
                hypotheses.append(hypothesis)

        # 按置信度排序
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)

        return hypotheses[:5]

    async def _claude_analyze(
        self,
        event: Event,
        context: AnalysisContext,
        hypotheses: List[RootCauseHypothesis],
        historical_cases: List[HistoricalCase],
    ) -> tuple[str, float, List[Evidence]]:
        """
        使用 Claude 分析根因

        Returns:
            (root_cause, confidence, evidence_chain)
        """
        if not self._claude_client:
            # 無 Claude 時使用基本分析
            return self._basic_analysis(hypotheses)

        try:
            # 構建分析提示
            prompt = self._build_analysis_prompt(
                event, context, hypotheses, historical_cases
            )

            # 調用 Claude
            response = await self._claude_client.send_message(
                message=prompt,
                system_prompt=(
                    "You are an expert system reliability engineer specializing in "
                    "root cause analysis. Analyze the provided evidence and determine "
                    "the most likely root cause. Be specific and actionable."
                ),
            )

            # 解析響應
            root_cause, confidence, evidence = self._parse_claude_response(response)
            return root_cause, confidence, evidence

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return self._basic_analysis(hypotheses)

    def _basic_analysis(
        self,
        hypotheses: List[RootCauseHypothesis],
    ) -> tuple[str, float, List[Evidence]]:
        """基本分析（無 Claude 時使用）"""
        if not hypotheses:
            return "Unable to determine root cause", 0.0, []

        top_hypothesis = hypotheses[0]
        confidence = calculate_overall_confidence(hypotheses)

        return (
            top_hypothesis.description,
            confidence,
            top_hypothesis.evidence,
        )

    def _build_analysis_prompt(
        self,
        event: Event,
        context: AnalysisContext,
        hypotheses: List[RootCauseHypothesis],
        historical_cases: List[HistoricalCase],
    ) -> str:
        """構建 Claude 分析提示"""
        hypothesis_text = "\n".join(
            f"- {h.description} (confidence: {h.confidence:.2%})"
            for h in hypotheses
        )

        historical_text = "\n".join(
            f"- {c.title}: {c.root_cause} (similarity: {c.similarity_score:.2%})"
            for c in historical_cases[:3]
        )

        return f"""
Analyze the following incident and determine the root cause:

Event: {event.title}
Description: {event.description}
Severity: {event.severity.value}
Affected Components: {', '.join(event.affected_components)}

Correlated Events: {len(context.correlations)}
Graph Complexity: {context.graph_data.get('node_count', 0)} nodes, {context.graph_data.get('edge_count', 0)} edges

Current Hypotheses:
{hypothesis_text}

Similar Historical Cases:
{historical_text}

Please provide:
1. ROOT_CAUSE: The most likely root cause (one sentence)
2. CONFIDENCE: Your confidence level (0-100%)
3. EVIDENCE: Key evidence supporting this conclusion (bullet points)
4. CONTRIBUTING_FACTORS: Other factors that contributed

Format:
ROOT_CAUSE: <your analysis>
CONFIDENCE: <percentage>
EVIDENCE:
- <evidence 1>
- <evidence 2>
CONTRIBUTING_FACTORS:
- <factor 1>
- <factor 2>
"""

    def _parse_claude_response(
        self,
        response: str,
    ) -> tuple[str, float, List[Evidence]]:
        """解析 Claude 響應"""
        root_cause = "Unable to determine"
        confidence = 0.5
        evidence: List[Evidence] = []

        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("ROOT_CAUSE:"):
                root_cause = line.replace("ROOT_CAUSE:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    conf_str = line.replace("CONFIDENCE:", "").strip().replace("%", "")
                    confidence = float(conf_str) / 100.0
                except ValueError:
                    pass
            elif line.startswith("- ") and "EVIDENCE" in response[:response.find(line)]:
                evidence.append(Evidence(
                    evidence_id=f"ev_{uuid4().hex[:8]}",
                    evidence_type=EvidenceType.EXPERT,
                    description=line[2:],
                    source="claude_analysis",
                    timestamp=datetime.utcnow(),
                    relevance_score=confidence,
                ))

        return root_cause, confidence, evidence

    def _identify_contributing_factors(
        self,
        correlations: List[Correlation],
        hypotheses: List[RootCauseHypothesis],
    ) -> List[str]:
        """識別貢獻因素"""
        factors: List[str] = []

        # 從高關聯事件提取
        for corr in correlations[:5]:
            if corr.score >= 0.5:
                factors.append(
                    f"Correlated event: {corr.target_event_id} "
                    f"(score: {corr.score:.2%})"
                )

        # 從假設中提取
        for hyp in hypotheses[1:3]:  # 排除第一個（已作為主因）
            factors.append(f"Contributing hypothesis: {hyp.description}")

        return factors[:10]

    async def _generate_recommendations(
        self,
        root_cause: str,
        contributing_factors: List[str],
        historical_cases: List[HistoricalCase],
    ) -> List[Recommendation]:
        """生成修復建議"""
        recommendations: List[Recommendation] = []

        # 立即處理建議
        recommendations.append(Recommendation(
            recommendation_id=f"rec_{uuid4().hex[:8]}",
            recommendation_type=RecommendationType.IMMEDIATE,
            title="Immediate Mitigation",
            description=f"Address the identified root cause: {root_cause}",
            priority=1,
            estimated_effort="1-2 hours",
            steps=[
                "Verify the identified root cause",
                "Implement quick fix or workaround",
                "Monitor system stability",
            ],
        ))

        # 基於歷史案例的建議
        for case in historical_cases[:2]:
            recommendations.append(Recommendation(
                recommendation_id=f"rec_{uuid4().hex[:8]}",
                recommendation_type=RecommendationType.SHORT_TERM,
                title=f"Apply fix from similar case: {case.title}",
                description=case.resolution,
                priority=2,
                estimated_effort="4-8 hours",
                steps=case.lessons_learned,
                metadata={"source_case": case.case_id},
            ))

        # 預防措施
        recommendations.append(Recommendation(
            recommendation_id=f"rec_{uuid4().hex[:8]}",
            recommendation_type=RecommendationType.PREVENTIVE,
            title="Preventive Measures",
            description="Implement measures to prevent recurrence",
            priority=3,
            estimated_effort="1-2 weeks",
            steps=[
                "Add monitoring for early detection",
                "Update runbook with this incident",
                "Schedule post-incident review",
            ],
        ))

        return recommendations
