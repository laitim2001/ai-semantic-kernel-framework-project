"""
Business Metrics API Module

Sprint 3 - Story S3-7: Custom Business Metrics

Provides endpoints for:
- Business metrics summary
- Active user statistics
- LLM cost tracking
- Workflow execution statistics
"""
from .routes import router

__all__ = ["router"]
