"""
Semantic Router Module

Provides vector-based semantic routing for IT service management intents.
Uses Aurelio Semantic Router for efficient semantic matching.

Sprint 92: Layer 2 of the three-layer routing architecture.
Sprint 93: Added MockSemanticRouter for testing.
"""

from .router import SemanticRouter, MockSemanticRouter
from .routes import get_default_routes, IT_SEMANTIC_ROUTES

__all__ = [
    "SemanticRouter",
    "MockSemanticRouter",
    "get_default_routes",
    "IT_SEMANTIC_ROUTES",
]
