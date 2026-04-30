"""
Route Manager for Azure AI Search Semantic Routes.

Provides CRUD operations for semantic routes stored in Azure AI Search.
Each route has multiple utterances; each utterance is stored as a separate
document with its embedding vector, sharing the same ``route_name``.

Sprint 115: Story 115-3 - Route Management API and Data Migration
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .azure_search_client import AzureSearchClient
from .embedding_service import EmbeddingService
from .routes import get_default_routes

logger = logging.getLogger(__name__)


class RouteDocument:
    """Represents a single utterance document in the Azure AI Search index.

    One *route* maps to many documents (one per utterance), all sharing the
    same ``route_name``.
    """

    def __init__(
        self,
        *,
        doc_id: str,
        route_name: str,
        category: str,
        sub_intent: str,
        utterance: str,
        utterance_vector: List[float],
        workflow_type: str = "simple",
        risk_level: str = "medium",
        description: str = "",
        enabled: bool = True,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> None:
        self.id = doc_id
        self.route_name = route_name
        self.category = category
        self.sub_intent = sub_intent
        self.utterance = utterance
        self.utterance_vector = utterance_vector
        self.workflow_type = workflow_type
        self.risk_level = risk_level
        self.description = description
        self.enabled = enabled

        now = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary suitable for Azure AI Search upload."""
        return {
            "id": self.id,
            "route_name": self.route_name,
            "category": self.category,
            "sub_intent": self.sub_intent,
            "utterance": self.utterance,
            "utterance_vector": self.utterance_vector,
            "workflow_type": self.workflow_type,
            "risk_level": self.risk_level,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouteDocument":
        """Deserialize from a dictionary (e.g. Azure Search result)."""
        return cls(
            doc_id=data["id"],
            route_name=data["route_name"],
            category=data["category"],
            sub_intent=data["sub_intent"],
            utterance=data["utterance"],
            utterance_vector=data.get("utterance_vector", []),
            workflow_type=data.get("workflow_type", "simple"),
            risk_level=data.get("risk_level", "medium"),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


def _generate_doc_id(route_name: str, index: int) -> str:
    """Generate a deterministic document ID from route name and utterance index."""
    return f"{route_name}_{index}_{uuid.uuid4().hex[:8]}"


class RouteManager:
    """Manages semantic routes in Azure AI Search.

    Provides CRUD operations for routes with automatic embedding generation.
    Each route can have multiple utterances; each utterance becomes a separate
    search document sharing the same ``route_name``.
    """

    def __init__(
        self,
        search_client: AzureSearchClient,
        embedding_service: EmbeddingService,
    ) -> None:
        self._search_client = search_client
        self._embedding_service = embedding_service

    # -----------------------------------------------------------------
    # Create
    # -----------------------------------------------------------------

    async def create_route(
        self,
        route_name: str,
        category: str,
        sub_intent: str,
        utterances: List[str],
        description: str = "",
        workflow_type: str = "simple",
        risk_level: str = "medium",
    ) -> Dict[str, Any]:
        """Create a new route with auto-generated embeddings.

        For each utterance, generates an embedding vector and creates a
        separate document in the search index.

        Args:
            route_name: Unique name for the route.
            category: Intent category (incident, request, change, query).
            sub_intent: More specific intent classification.
            utterances: Example utterances for this route.
            description: Human-readable route description.
            workflow_type: Workflow type for handling the intent.
            risk_level: Risk level classification.

        Returns:
            Route metadata including document count.

        Raises:
            ValueError: If a route with the same name already exists.
            RuntimeError: If embedding generation or upload fails.
        """
        # Check if route already exists
        existing = await self._get_documents_by_route(route_name)
        if existing:
            raise ValueError(f"Route '{route_name}' already exists with {len(existing)} documents")

        logger.info(f"Creating route '{route_name}' with {len(utterances)} utterances")

        # Generate embeddings for all utterances
        vectors = await self._embedding_service.get_embeddings_batch(utterances)

        # Build documents
        documents = []
        for idx, (utterance, vector) in enumerate(zip(utterances, vectors)):
            doc = RouteDocument(
                doc_id=_generate_doc_id(route_name, idx),
                route_name=route_name,
                category=category,
                sub_intent=sub_intent,
                utterance=utterance,
                utterance_vector=vector,
                workflow_type=workflow_type,
                risk_level=risk_level,
                description=description,
                enabled=True,
            )
            documents.append(doc.to_dict())

        # Upload to Azure AI Search
        await self._search_client.upload_documents(documents)

        logger.info(f"Route '{route_name}' created with {len(documents)} documents")
        return {
            "route_name": route_name,
            "category": category,
            "sub_intent": sub_intent,
            "utterance_count": len(utterances),
            "workflow_type": workflow_type,
            "risk_level": risk_level,
            "description": description,
            "enabled": True,
            "status": "created",
        }

    # -----------------------------------------------------------------
    # Read
    # -----------------------------------------------------------------

    async def get_routes(
        self,
        category: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """List all routes, optionally filtered.

        Groups documents by ``route_name`` and returns aggregated info.

        Args:
            category: Filter by intent category.
            enabled: Filter by enabled/disabled status.

        Returns:
            List of route summaries.
        """
        # Build filter expression
        filters: List[str] = []
        if category is not None:
            filters.append(f"category eq '{category}'")
        if enabled is not None:
            filters.append(f"enabled eq {str(enabled).lower()}")

        filter_expr = " and ".join(filters) if filters else None

        # Retrieve all documents (using a wildcard text search)
        results = await self._search_client.hybrid_search(
            query="*",
            vector=None,
            filters=filter_expr,
            top_k=1000,
        )

        # Group by route_name
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for doc in results:
            name = doc.get("route_name", "")
            grouped.setdefault(name, []).append(doc)

        # Build route summaries
        route_list: List[Dict[str, Any]] = []
        for name, docs in sorted(grouped.items()):
            first = docs[0]
            route_list.append({
                "route_name": name,
                "category": first.get("category", ""),
                "sub_intent": first.get("sub_intent", ""),
                "utterance_count": len(docs),
                "workflow_type": first.get("workflow_type", "simple"),
                "risk_level": first.get("risk_level", "medium"),
                "description": first.get("description", ""),
                "enabled": first.get("enabled", True),
            })

        return route_list

    async def get_route(self, route_name: str) -> Optional[Dict[str, Any]]:
        """Get a single route by name with all its utterance documents.

        Args:
            route_name: Name of the route to retrieve.

        Returns:
            Route detail with utterances, or None if not found.
        """
        docs = await self._get_documents_by_route(route_name)
        if not docs:
            return None

        first = docs[0]
        utterances = [d.get("utterance", "") for d in docs]

        return {
            "route_name": route_name,
            "category": first.get("category", ""),
            "sub_intent": first.get("sub_intent", ""),
            "utterances": utterances,
            "utterance_count": len(docs),
            "workflow_type": first.get("workflow_type", "simple"),
            "risk_level": first.get("risk_level", "medium"),
            "description": first.get("description", ""),
            "enabled": first.get("enabled", True),
            "document_ids": [d["id"] for d in docs],
        }

    # -----------------------------------------------------------------
    # Update
    # -----------------------------------------------------------------

    async def update_route(
        self,
        route_name: str,
        utterances: Optional[List[str]] = None,
        description: Optional[str] = None,
        workflow_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a route. Regenerates embeddings if utterances change.

        If utterances are provided the old documents are deleted and new
        ones (with fresh embeddings) are uploaded.  If only metadata fields
        change the existing documents are updated in-place.

        Args:
            route_name: Name of the route to update.
            utterances: New utterances (triggers re-embedding).
            description: Updated description.
            workflow_type: Updated workflow type.
            risk_level: Updated risk level.
            enabled: Updated enabled flag.

        Returns:
            Updated route metadata.

        Raises:
            ValueError: If the route does not exist.
        """
        existing_docs = await self._get_documents_by_route(route_name)
        if not existing_docs:
            raise ValueError(f"Route '{route_name}' not found")

        first = existing_docs[0]

        if utterances is not None:
            # Full replacement: delete old, create new with embeddings
            doc_ids = [d["id"] for d in existing_docs]
            await self._search_client.delete_documents(doc_ids)

            vectors = await self._embedding_service.get_embeddings_batch(utterances)

            new_docs: List[Dict[str, Any]] = []
            now = datetime.now(timezone.utc).isoformat()
            for idx, (utt, vec) in enumerate(zip(utterances, vectors)):
                doc = RouteDocument(
                    doc_id=_generate_doc_id(route_name, idx),
                    route_name=route_name,
                    category=first.get("category", ""),
                    sub_intent=first.get("sub_intent", ""),
                    utterance=utt,
                    utterance_vector=vec,
                    workflow_type=workflow_type or first.get("workflow_type", "simple"),
                    risk_level=risk_level or first.get("risk_level", "medium"),
                    description=description if description is not None else first.get("description", ""),
                    enabled=enabled if enabled is not None else first.get("enabled", True),
                    created_at=first.get("created_at"),
                    updated_at=now,
                )
                new_docs.append(doc.to_dict())

            await self._search_client.upload_documents(new_docs)
            utterance_count = len(utterances)
            logger.info(f"Route '{route_name}' utterances replaced ({utterance_count} new)")
        else:
            # Metadata-only update: patch every document in-place
            now = datetime.now(timezone.utc).isoformat()
            updated_docs: List[Dict[str, Any]] = []
            for doc in existing_docs:
                patched = dict(doc)
                if description is not None:
                    patched["description"] = description
                if workflow_type is not None:
                    patched["workflow_type"] = workflow_type
                if risk_level is not None:
                    patched["risk_level"] = risk_level
                if enabled is not None:
                    patched["enabled"] = enabled
                patched["updated_at"] = now
                updated_docs.append(patched)

            await self._search_client.upload_documents(updated_docs)
            utterance_count = len(existing_docs)
            logger.info(f"Route '{route_name}' metadata updated ({utterance_count} documents)")

        return {
            "route_name": route_name,
            "utterance_count": utterance_count,
            "status": "updated",
        }

    # -----------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------

    async def delete_route(self, route_name: str) -> Dict[str, Any]:
        """Delete a route and all its utterance documents.

        Args:
            route_name: Name of the route to delete.

        Returns:
            Deletion summary.

        Raises:
            ValueError: If the route does not exist.
        """
        docs = await self._get_documents_by_route(route_name)
        if not docs:
            raise ValueError(f"Route '{route_name}' not found")

        doc_ids = [d["id"] for d in docs]
        await self._search_client.delete_documents(doc_ids)

        logger.info(f"Route '{route_name}' deleted ({len(doc_ids)} documents)")
        return {
            "route_name": route_name,
            "documents_deleted": len(doc_ids),
            "status": "deleted",
        }

    # -----------------------------------------------------------------
    # Sync / Migration
    # -----------------------------------------------------------------

    async def sync_from_yaml(self) -> Dict[str, Any]:
        """Sync routes from predefined Python definitions to Azure AI Search.

        Reads routes from ``get_default_routes()`` (the 15 predefined
        routes), generates embeddings, and uploads to Azure AI Search.

        Returns:
            Migration statistics.
        """
        default_routes = get_default_routes()
        total_utterances = sum(len(r.utterances) for r in default_routes)

        logger.info(
            f"Starting sync: {len(default_routes)} routes, "
            f"{total_utterances} utterances"
        )

        all_documents: List[Dict[str, Any]] = []
        synced_routes = 0

        for route in default_routes:
            vectors = await self._embedding_service.get_embeddings_batch(route.utterances)

            for idx, (utterance, vector) in enumerate(zip(route.utterances, vectors)):
                doc = RouteDocument(
                    doc_id=_generate_doc_id(route.name, idx),
                    route_name=route.name,
                    category=route.category.value,
                    sub_intent=route.sub_intent,
                    utterance=utterance,
                    utterance_vector=vector,
                    workflow_type=route.workflow_type.value,
                    risk_level=route.risk_level.value,
                    description=route.description,
                    enabled=route.enabled,
                )
                all_documents.append(doc.to_dict())

            synced_routes += 1

        # Batch upload all documents
        await self._search_client.upload_documents(all_documents)

        # Verify upload count
        doc_count = await self._search_client.get_document_count()

        logger.info(
            f"Sync complete: {synced_routes} routes, "
            f"{len(all_documents)} documents uploaded, "
            f"{doc_count} documents in index"
        )

        return {
            "routes_synced": synced_routes,
            "utterances_synced": len(all_documents),
            "documents_in_index": doc_count,
            "status": "success",
        }

    # -----------------------------------------------------------------
    # Search Test
    # -----------------------------------------------------------------

    async def search_test(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Test search functionality with a query string.

        Generates an embedding for the query, performs vector search,
        and returns results with scores.

        Args:
            query: The search query text.
            top_k: Maximum number of results to return.

        Returns:
            List of search results with scores.
        """
        vector = await self._embedding_service.get_embedding(query)
        results = await self._search_client.vector_search(
            vector=vector,
            top_k=top_k,
        )

        formatted: List[Dict[str, Any]] = []
        for result in results:
            formatted.append({
                "route_name": result.get("route_name", ""),
                "category": result.get("category", ""),
                "sub_intent": result.get("sub_intent", ""),
                "utterance": result.get("utterance", ""),
                "score": result.get("@search.score", 0.0),
                "workflow_type": result.get("workflow_type", ""),
                "risk_level": result.get("risk_level", ""),
            })

        return formatted

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    async def _get_documents_by_route(
        self,
        route_name: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve all documents belonging to a given route.

        Args:
            route_name: The route name to filter by.

        Returns:
            List of raw document dictionaries from the index.
        """
        results = await self._search_client.hybrid_search(
            query="*",
            vector=None,
            filters=f"route_name eq '{route_name}'",
            top_k=500,
        )
        return results
