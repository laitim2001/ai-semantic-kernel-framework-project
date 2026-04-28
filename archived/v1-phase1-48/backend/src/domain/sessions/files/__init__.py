"""
Session Files Module

Provides file analysis and generation functionality for Session mode.

Components:
- FileAnalyzer: Main entry point for file analysis (Strategy Pattern)
- DocumentAnalyzer: Analyze PDF, Word, Text, Markdown documents
- ImageAnalyzer: Analyze images with multimodal LLM support
- CodeAnalyzer: Analyze source code files
- DataAnalyzer: Analyze CSV, JSON, Excel data files
- FileGenerator: Main entry point for file generation (Factory Pattern)
- CodeGenerator: Generate source code files
- ReportGenerator: Generate report files (Markdown, HTML)
- DataExporter: Export data files (CSV, JSON, Excel, XML)

Usage:
    # File Analysis
    from src.domain.sessions.files import FileAnalyzer, AnalysisRequest

    analyzer = FileAnalyzer(llm_client=llm)
    result = await analyzer.analyze(attachment, AnalysisRequest(
        analysis_type=AnalysisType.SUMMARY
    ))

    # File Generation
    from src.domain.sessions.files import FileGenerator, GenerationRequest

    generator = FileGenerator(storage=storage)
    result = await generator.generate(session_id, GenerationRequest(
        generation_type=GenerationType.CODE,
        content=code,
        language="python"
    ))
"""

from .types import (
    AnalysisType,
    GenerationType,
    ExportFormat,
    AnalysisRequest,
    AnalysisResult,
    GenerationRequest,
    GenerationResult,
    SUPPORTED_EXTENSIONS,
    LANGUAGE_EXTENSIONS,
    CONTENT_TYPE_MAP
)

# Analyzers
from .analyzer import (
    FileAnalyzer,
    BaseAnalyzer,
    GenericAnalyzer
)
from .document_analyzer import DocumentAnalyzer
from .image_analyzer import ImageAnalyzer
from .code_analyzer import CodeAnalyzer
from .data_analyzer import DataAnalyzer

# Generators
from .generator import (
    FileGenerator,
    BaseGenerator
)
from .code_generator import CodeGenerator
from .report_generator import ReportGenerator
from .data_exporter import DataExporter

__all__ = [
    # Types
    "AnalysisType",
    "GenerationType",
    "ExportFormat",
    "AnalysisRequest",
    "AnalysisResult",
    "GenerationRequest",
    "GenerationResult",
    "SUPPORTED_EXTENSIONS",
    "LANGUAGE_EXTENSIONS",
    "CONTENT_TYPE_MAP",
    # Analyzers
    "FileAnalyzer",
    "BaseAnalyzer",
    "GenericAnalyzer",
    "DocumentAnalyzer",
    "ImageAnalyzer",
    "CodeAnalyzer",
    "DataAnalyzer",
    # Generators
    "FileGenerator",
    "BaseGenerator",
    "CodeGenerator",
    "ReportGenerator",
    "DataExporter",
]
