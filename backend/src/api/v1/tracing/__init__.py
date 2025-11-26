"""
Tracing API Module

Sprint 3 - Story S3-6: Distributed Tracing with Jaeger

Provides endpoints for:
- Tracing configuration status
- Test trace generation
- Trace context inspection
"""
from .routes import router

__all__ = ["router"]
