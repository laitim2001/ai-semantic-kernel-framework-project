"""
Semantic Router Module

Provides vector-based semantic routing for IT service management intents.

- ``SemanticRouter``: Original Aurelio-based router (Sprint 92).
- ``AzureSemanticRouter``: Azure AI Search-based router (Sprint 115).
- ``AzureSearchClient``: Azure AI Search client wrapper.
- ``EmbeddingService``: Azure OpenAI embedding service with caching.

Sprint 92: Layer 2 of the three-layer routing architecture.
Sprint 115: Azure AI Search alternative implementation.
"""

from .azure_search_client import AzureSearchClient
from .azure_semantic_router import AzureSemanticRouter
from .embedding_service import EmbeddingService
from .router import SemanticRouter
from .routes import get_default_routes, IT_SEMANTIC_ROUTES

__all__ = [
    "SemanticRouter",
    "AzureSemanticRouter",
    "AzureSearchClient",
    "EmbeddingService",
    "get_default_routes",
    "IT_SEMANTIC_ROUTES",
]
