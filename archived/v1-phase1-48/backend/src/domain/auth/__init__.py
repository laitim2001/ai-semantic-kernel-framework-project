# =============================================================================
# IPA Platform - Auth Domain Module
# =============================================================================
# Sprint 70: S70-2 - UserRepository + AuthService
# Phase 18: Authentication System
#
# Authentication domain providing registration, login, and token management.
#
# Exports:
#   - AuthService: Core authentication service
#   - Schemas: Request/response models
# =============================================================================

from src.domain.auth.service import AuthService
from src.domain.auth.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefresh,
)

__all__ = [
    "AuthService",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "TokenRefresh",
]
