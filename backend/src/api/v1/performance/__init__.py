"""
Performance Monitoring API Module

Sprint 3 - Story S3-8: Performance Dashboard

Provides endpoints for:
- API latency metrics
- Request throughput
- Error rates
- Resource utilization
"""
from .routes import router

__all__ = ["router"]
