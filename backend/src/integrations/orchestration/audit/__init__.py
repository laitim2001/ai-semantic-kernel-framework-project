"""
Audit Module for Intent Router

Provides structured audit logging for routing decisions.
Supports JSON format for integration with log aggregation tools.

Sprint 91: Pattern Matcher + Rule Definition (Phase 28)
"""

from .logger import AuditLogger, AuditEntry

__all__ = ["AuditLogger", "AuditEntry"]
