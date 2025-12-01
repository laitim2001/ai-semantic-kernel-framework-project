"""
IPA Platform - Performance Optimization Module

This module provides performance optimization utilities including:
- Response compression middleware
- Request timing middleware
- Cache optimization helpers
- Database query optimization utilities

Author: IPA Platform Team
Version: 1.0.0
"""

from .middleware import (
    CompressionMiddleware,
    TimingMiddleware,
    ETagMiddleware,
)
from .cache_optimizer import CacheOptimizer
from .db_optimizer import QueryOptimizer

__all__ = [
    "CompressionMiddleware",
    "TimingMiddleware",
    "ETagMiddleware",
    "CacheOptimizer",
    "QueryOptimizer",
]
