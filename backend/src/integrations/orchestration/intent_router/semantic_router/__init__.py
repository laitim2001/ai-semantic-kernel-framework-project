"""
Semantic Router Module

Provides vector-based semantic routing for IT service management intents.
Uses Aurelio Semantic Router for efficient semantic matching.

Sprint 92: Layer 2 of the three-layer routing architecture.
"""

from .router import SemanticRouter
from .routes import get_default_routes, IT_SEMANTIC_ROUTES

__all__ = [
    "SemanticRouter",
    "get_default_routes",
    "IT_SEMANTIC_ROUTES",
]
