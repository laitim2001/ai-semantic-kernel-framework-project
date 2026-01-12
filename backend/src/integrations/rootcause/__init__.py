"""
Root Cause Analysis System - 根因分析系統

Sprint 82 - S82-2: 智能關聯與根因分析

提供:
- RootCauseAnalyzer: 根因分析器
- 分析相關類型定義
"""

from .analyzer import RootCauseAnalyzer
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

__all__ = [
    # Core classes
    "RootCauseAnalyzer",
    # Types
    "AnalysisContext",
    "AnalysisRequest",
    "AnalysisStatus",
    "Evidence",
    "EvidenceType",
    "HistoricalCase",
    "Recommendation",
    "RecommendationType",
    "RootCauseAnalysis",
    "RootCauseHypothesis",
    # Config
    "ANALYSIS_DEPTH_CONFIG",
    # Utilities
    "calculate_overall_confidence",
]

# 版本信息
__version__ = "1.0.0"
__sprint__ = "82"
