"""
Security Testing API Module

Sprint 3 - Story S3-9: Security Penetration Testing

Provides endpoints for:
- OWASP Top 10 vulnerability checks
- SQL injection testing
- XSS testing
- CSRF testing
- Security test reporting
"""
from .routes import router

__all__ = ["router"]
