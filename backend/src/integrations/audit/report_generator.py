# =============================================================================
# IPA Platform - Audit Report Generator
# =============================================================================
# Sprint 80: S80-2 - 自主決策審計追蹤 (8 pts)
#
# This module generates explanatory reports for audited decisions.
# Provides human-readable explanations of AI decision-making.
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import (
    AuditReport,
    DecisionAudit,
    DecisionOutcome,
    DecisionType,
    QualityRating,
)


logger = logging.getLogger(__name__)


class AuditReportGenerator:
    """
    Generates explanatory reports for audited decisions.

    Creates human-readable reports that explain:
    - What decision was made and why
    - What alternatives were considered
    - What risks were identified
    - Recommendations for improvement
    """

    def __init__(self):
        """Initialize the report generator."""
        pass

    def generate_report(self, audit: DecisionAudit) -> AuditReport:
        """
        Generate a comprehensive report for a decision.

        Args:
            audit: The decision audit record.

        Returns:
            Generated AuditReport.
        """
        title = self._generate_title(audit)
        summary = self._generate_summary(audit)
        detailed_explanation = self._generate_detailed_explanation(audit)
        key_factors = self._extract_key_factors(audit)
        risk_analysis = self._generate_risk_analysis(audit)
        recommendations = self._generate_recommendations(audit)

        return AuditReport(
            decision_id=audit.decision_id,
            title=title,
            summary=summary,
            detailed_explanation=detailed_explanation,
            key_factors=key_factors,
            risk_analysis=risk_analysis,
            recommendations=recommendations,
        )

    def _generate_title(self, audit: DecisionAudit) -> str:
        """Generate report title."""
        type_names = {
            DecisionType.PLAN_GENERATION: "規劃生成",
            DecisionType.STEP_EXECUTION: "步驟執行",
            DecisionType.TOOL_SELECTION: "工具選擇",
            DecisionType.FALLBACK_SELECTION: "回退選擇",
            DecisionType.RISK_ASSESSMENT: "風險評估",
            DecisionType.APPROVAL_REQUEST: "審批請求",
            DecisionType.OTHER: "其他",
        }

        type_name = type_names.get(audit.decision_type, "決策")
        return f"{type_name}審計報告 - {audit.decision_id[:8]}"

    def _generate_summary(self, audit: DecisionAudit) -> str:
        """Generate a brief summary of the decision."""
        outcome_text = {
            DecisionOutcome.SUCCESS: "成功",
            DecisionOutcome.PARTIAL_SUCCESS: "部分成功",
            DecisionOutcome.FAILURE: "失敗",
            DecisionOutcome.PENDING: "待定",
            DecisionOutcome.CANCELLED: "已取消",
        }

        confidence_level = (
            "高" if audit.confidence_score >= 0.8
            else "中" if audit.confidence_score >= 0.5
            else "低"
        )

        summary_parts = [
            f"決策類型: {audit.decision_type.value}",
            f"選擇的行動: {audit.selected_action}",
            f"信心度: {audit.confidence_score:.1%} ({confidence_level})",
            f"結果: {outcome_text.get(audit.outcome, audit.outcome.value)}",
        ]

        if audit.quality_rating:
            summary_parts.append(f"品質評級: {audit.quality_rating.value}")

        return "\n".join(summary_parts)

    def _generate_detailed_explanation(self, audit: DecisionAudit) -> str:
        """Generate detailed explanation of the decision."""
        sections = []

        # Decision overview
        sections.append("## 決策概述\n")
        sections.append(f"在 {audit.timestamp.strftime('%Y-%m-%d %H:%M:%S')} 做出了此決策。")

        if audit.context.event_id:
            sections.append(f"相關事件 ID: {audit.context.event_id}")

        # Selected action explanation
        sections.append("\n## 選擇的行動\n")
        sections.append(f"**{audit.selected_action}**\n")

        if audit.action_details:
            sections.append("行動詳情:")
            for key, value in audit.action_details.items():
                sections.append(f"  - {key}: {value}")

        # Thinking process
        if audit.thinking_process.raw_thinking:
            sections.append("\n## AI 思考過程\n")
            thinking_excerpt = audit.thinking_process.raw_thinking[:2000]
            if len(audit.thinking_process.raw_thinking) > 2000:
                thinking_excerpt += "...(truncated)"
            sections.append(thinking_excerpt)

        # Key considerations
        if audit.thinking_process.key_considerations:
            sections.append("\n## 關鍵考量\n")
            for consideration in audit.thinking_process.key_considerations:
                sections.append(f"- {consideration}")

        # Alternatives considered
        if audit.alternatives_considered:
            sections.append("\n## 考慮過的替代方案\n")
            for i, alt in enumerate(audit.alternatives_considered, 1):
                sections.append(f"### 替代方案 {i}: {alt.description}")
                sections.append(f"- 未選擇原因: {alt.reason_not_selected}")
                sections.append(f"- 預估風險: {alt.estimated_risk:.1%}")
                sections.append(
                    f"- 預估成功概率: {alt.estimated_success_probability:.1%}"
                )

        # Outcome
        sections.append("\n## 結果\n")
        sections.append(f"結果狀態: {audit.outcome.value}")
        if audit.outcome_details:
            sections.append(f"詳情: {audit.outcome_details}")

        # Quality assessment
        if audit.quality_score is not None:
            sections.append("\n## 品質評估\n")
            sections.append(f"品質分數: {audit.quality_score:.2f}")
            if audit.quality_rating:
                sections.append(f"品質評級: {audit.quality_rating.value}")

        # Feedback
        if audit.feedback:
            sections.append("\n## 反饋\n")
            sections.append(audit.feedback)

        return "\n".join(sections)

    def _extract_key_factors(self, audit: DecisionAudit) -> List[str]:
        """Extract key factors that influenced the decision."""
        factors = []

        # From thinking process
        factors.extend(audit.thinking_process.key_considerations)

        # Add confidence factor
        if audit.confidence_score >= 0.8:
            factors.append(f"高信心度決策 ({audit.confidence_score:.1%})")
        elif audit.confidence_score < 0.5:
            factors.append(f"低信心度決策 ({audit.confidence_score:.1%})")

        # Add alternatives factor
        if len(audit.alternatives_considered) >= 3:
            factors.append(f"考慮了 {len(audit.alternatives_considered)} 個替代方案")

        # Add context factors
        if audit.context.event_id:
            factors.append(f"與事件 {audit.context.event_id[:8]} 相關")

        return factors[:10]  # Limit to 10 factors

    def _generate_risk_analysis(self, audit: DecisionAudit) -> str:
        """Generate risk analysis section."""
        risks = []

        # From thinking process
        for risk in audit.thinking_process.risks_identified:
            risks.append(f"- {risk}")

        # From alternatives
        for alt in audit.alternatives_considered:
            if alt.estimated_risk > 0.7:
                risks.append(
                    f"- 替代方案「{alt.description[:30]}...」風險較高 ({alt.estimated_risk:.1%})"
                )

        # Confidence-based risk
        if audit.confidence_score < 0.5:
            risks.append("- 決策信心度較低，建議人工複核")

        # Outcome-based risk
        if audit.outcome == DecisionOutcome.FAILURE:
            risks.append("- 此決策已失敗，需要分析失敗原因")

        if not risks:
            return "未識別到顯著風險。"

        return "已識別的風險:\n" + "\n".join(risks)

    def _generate_recommendations(self, audit: DecisionAudit) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations = []

        # Based on outcome
        if audit.outcome == DecisionOutcome.FAILURE:
            recommendations.append("建議分析失敗原因並更新決策模型")
            recommendations.append("考慮是否需要調整類似場景的處理策略")

        if audit.outcome == DecisionOutcome.PARTIAL_SUCCESS:
            recommendations.append("建議識別部分成功和部分失敗的原因")

        # Based on confidence
        if audit.confidence_score < 0.5:
            recommendations.append("建議收集更多資訊以提高決策信心")
            recommendations.append("考慮諮詢專家意見")

        # Based on alternatives
        if not audit.alternatives_considered:
            recommendations.append("建議在未來決策中考慮更多替代方案")

        # Based on thinking process
        if not audit.thinking_process.raw_thinking:
            recommendations.append("建議啟用 Extended Thinking 以獲得更深入的分析")

        # Based on quality
        if audit.quality_score is not None and audit.quality_score < 0.5:
            recommendations.append("建議對此類決策進行額外審核")

        # Always recommend feedback
        if not audit.feedback:
            recommendations.append("建議添加反饋以改進未來決策")

        return recommendations[:5]  # Limit to 5 recommendations

    def generate_summary_report(
        self,
        audits: List[DecisionAudit],
    ) -> Dict[str, Any]:
        """
        Generate a summary report for multiple decisions.

        Args:
            audits: List of decision audits.

        Returns:
            Summary report dictionary.
        """
        if not audits:
            return {
                "total_decisions": 0,
                "period": None,
                "summary": "No decisions to report.",
            }

        # Calculate statistics
        success_count = sum(1 for a in audits if a.outcome == DecisionOutcome.SUCCESS)
        failure_count = sum(1 for a in audits if a.outcome == DecisionOutcome.FAILURE)
        avg_confidence = sum(a.confidence_score for a in audits) / len(audits)

        quality_scores = [a.quality_score for a in audits if a.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        # Time period
        timestamps = [a.timestamp for a in audits]
        start_time = min(timestamps)
        end_time = max(timestamps)

        # Group by type
        by_type: Dict[str, int] = {}
        for audit in audits:
            type_key = audit.decision_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

        return {
            "total_decisions": len(audits),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "statistics": {
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": success_count / len(audits),
                "avg_confidence": avg_confidence,
                "avg_quality": avg_quality,
            },
            "by_type": by_type,
            "summary": self._generate_summary_text(
                len(audits), success_count, failure_count, avg_confidence
            ),
        }

    def _generate_summary_text(
        self,
        total: int,
        success: int,
        failure: int,
        avg_confidence: float,
    ) -> str:
        """Generate summary text."""
        success_rate = success / total if total > 0 else 0

        text = f"共 {total} 個決策，成功率 {success_rate:.1%}，平均信心度 {avg_confidence:.1%}。"

        if success_rate >= 0.9:
            text += " 整體表現優秀。"
        elif success_rate >= 0.7:
            text += " 整體表現良好。"
        elif success_rate >= 0.5:
            text += " 整體表現尚可，有改進空間。"
        else:
            text += " 需要關注決策品質。"

        return text
