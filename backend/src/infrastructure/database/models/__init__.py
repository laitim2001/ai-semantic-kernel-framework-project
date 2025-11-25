"""
Database Models for IPA Platform
"""
from .base import Base, BaseModel
from .audit_log import AuditLog, AuditAction

__all__ = [
    "Base",
    "BaseModel",
    "AuditLog",
    "AuditAction",
]
