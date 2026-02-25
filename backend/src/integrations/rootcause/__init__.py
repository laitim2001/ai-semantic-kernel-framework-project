"""
Root Cause Analysis System - 根因分析系統

Sprint 82 - S82-2: 智能關聯與根因分析
Sprint 130 - Story 130-2: 真實案例庫 + 案例匹配引擎

提供:
- RootCauseAnalyzer: 根因分析器
- CaseRepository: 歷史案例儲存庫
- CaseMatcher: 案例匹配引擎
- 分析相關類型定義
"""

from .analyzer import RootCauseAnalyzer
from .case_matcher import CaseMatcher, MatchResult
from .case_repository import CaseRepository
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
    # Sprint 130: Case repository
    "CaseRepository",
    "CaseMatcher",
    "MatchResult",
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
__version__ = "2.0.0"
__sprint__ = "130"
