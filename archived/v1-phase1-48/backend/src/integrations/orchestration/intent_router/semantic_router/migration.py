"""
Migration script: Sync predefined routes from Python to Azure AI Search.

Reads the 15 predefined SemanticRoute definitions, generates embedding
vectors for each utterance, and uploads the resulting documents to the
Azure AI Search index.

Sprint 115: Story 115-3 - Route Management API and Data Migration

Can be run standalone::

    python -m src.integrations.orchestration.intent_router.semantic_router.migration

Or imported and used programmatically::

    from src.integrations.orchestration.intent_router.semantic_router.migration import (
        migrate_routes,
        verify_migration,
    )
    result = await migrate_routes(search_client, embedding_service)
"""

import argparse
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def migrate_routes(
    search_client: "AzureSearchClient",
    embedding_service: "EmbeddingService",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Migrate all predefined routes to Azure AI Search.

    Reads routes from ``get_default_routes()``, generates embedding
    vectors for every utterance, and batch-uploads the resulting
    documents.  With ``dry_run=True`` validation runs but no upload
    is performed.

    Args:
        search_client: Azure Search client instance.
        embedding_service: Embedding service for vector generation.
        dry_run: If True, only validate without uploading.

    Returns:
        Migration result dictionary with stats.
    """
    from .routes import get_default_routes

    default_routes = get_default_routes()
    total_utterances = sum(len(r.utterances) for r in default_routes)

    logger.info(
        f"Migration started — {len(default_routes)} routes, "
        f"{total_utterances} utterances (dry_run={dry_run})"
    )

    all_documents: List[Dict[str, Any]] = []
    errors: List[str] = []

    for route in default_routes:
        # Validate route data
        if not route.name:
            errors.append(f"Route missing name: {route}")
            continue
        if not route.utterances:
            errors.append(f"Route '{route.name}' has no utterances")
            continue

        try:
            vectors = await embedding_service.get_embeddings_batch(route.utterances)
        except Exception as e:
            errors.append(f"Embedding failed for route '{route.name}': {e}")
            continue

        now = datetime.now(timezone.utc).isoformat()
        for idx, (utterance, vector) in enumerate(zip(route.utterances, vectors)):
            doc_id = f"{route.name}_{idx}_{uuid.uuid4().hex[:8]}"
            document = {
                "id": doc_id,
                "route_name": route.name,
                "category": route.category.value,
                "sub_intent": route.sub_intent,
                "utterance": utterance,
                "utterance_vector": vector,
                "workflow_type": route.workflow_type.value,
                "risk_level": route.risk_level.value,
                "description": route.description,
                "enabled": route.enabled,
                "created_at": now,
                "updated_at": now,
            }
            all_documents.append(document)

    if errors:
        logger.warning(f"Migration validation found {len(errors)} error(s): {errors}")

    if dry_run:
        logger.info(
            f"Dry run complete — would upload {len(all_documents)} documents"
        )
        return {
            "routes_processed": len(default_routes),
            "documents_prepared": len(all_documents),
            "errors": errors,
            "dry_run": True,
            "status": "dry_run_complete",
        }

    # Batch upload
    await search_client.upload_documents(all_documents)

    # Verify document count
    doc_count = await search_client.get_document_count()

    # Run sample search to validate
    sample_valid = False
    try:
        sample_vector = await embedding_service.get_embedding("ETL job failure")
        sample_results = await search_client.vector_search(
            vector=sample_vector, top_k=3
        )
        sample_valid = len(sample_results) > 0
    except Exception as e:
        logger.warning(f"Sample search validation failed: {e}")

    logger.info(
        f"Migration complete — {len(all_documents)} documents uploaded, "
        f"{doc_count} total in index, sample_search_valid={sample_valid}"
    )

    return {
        "routes_processed": len(default_routes),
        "documents_uploaded": len(all_documents),
        "documents_in_index": doc_count,
        "errors": errors,
        "sample_search_valid": sample_valid,
        "dry_run": False,
        "status": "success",
    }


async def verify_migration(
    search_client: "AzureSearchClient",
    embedding_service: "EmbeddingService",
) -> Dict[str, Any]:
    """Verify migration completeness.

    Checks:
        1. Document count matches expected (56 utterances across 15 routes).
        2. All 15 route names are present in the index.
        3. Sample search returns reasonable results.

    Args:
        search_client: Azure Search client instance.
        embedding_service: Embedding service for vector generation.

    Returns:
        Verification result dictionary.
    """
    from .routes import get_default_routes

    default_routes = get_default_routes()
    expected_utterances = sum(len(r.utterances) for r in default_routes)
    expected_route_names = {r.name for r in default_routes}

    issues: List[str] = []

    # Check 1: Document count
    doc_count = await search_client.get_document_count()
    if doc_count < expected_utterances:
        issues.append(
            f"Document count mismatch: expected >= {expected_utterances}, got {doc_count}"
        )

    # Check 2: All route names present
    results = await search_client.hybrid_search(
        query="*", vector=None, filters=None, top_k=1000
    )
    found_names = {doc.get("route_name", "") for doc in results}
    missing_routes = expected_route_names - found_names
    if missing_routes:
        issues.append(f"Missing routes: {missing_routes}")

    # Check 3: Sample search quality
    sample_results_valid = False
    try:
        sample_vector = await embedding_service.get_embedding("system is down")
        sample_results = await search_client.vector_search(
            vector=sample_vector, top_k=3
        )
        if sample_results:
            top_route = sample_results[0].get("route_name", "")
            if "incident" in top_route.lower() or "system" in top_route.lower():
                sample_results_valid = True
            else:
                issues.append(
                    f"Sample search top result '{top_route}' may not be relevant"
                )
    except Exception as e:
        issues.append(f"Sample search failed: {e}")

    is_valid = len(issues) == 0

    logger.info(
        f"Migration verification: valid={is_valid}, "
        f"docs={doc_count}/{expected_utterances}, "
        f"routes={len(found_names)}/{len(expected_route_names)}, "
        f"issues={len(issues)}"
    )

    return {
        "valid": is_valid,
        "document_count": doc_count,
        "expected_utterances": expected_utterances,
        "routes_found": len(found_names),
        "expected_routes": len(expected_route_names),
        "missing_routes": list(missing_routes) if missing_routes else [],
        "sample_search_valid": sample_results_valid,
        "issues": issues,
    }


def main() -> None:
    """CLI entry point for migration.

    Reads configuration from environment variables and runs the
    migration (or verification with ``--verify``).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Migrate predefined semantic routes to Azure AI Search",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only, do not upload",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing migration instead of running one",
    )
    args = parser.parse_args()

    # Read configuration from environment
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    api_key = os.getenv("AZURE_SEARCH_API_KEY", "")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "semantic-routes")
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    openai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    embedding_deployment = os.getenv(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
    )

    if not endpoint:
        print("[ERROR] AZURE_SEARCH_ENDPOINT is not set")
        sys.exit(1)
    if not api_key:
        print("[ERROR] AZURE_SEARCH_API_KEY is not set")
        sys.exit(1)
    if not openai_endpoint:
        print("[ERROR] AZURE_OPENAI_ENDPOINT is not set")
        sys.exit(1)
    if not openai_key:
        print("[ERROR] AZURE_OPENAI_API_KEY is not set")
        sys.exit(1)

    print("=" * 60)
    print("Semantic Routes Migration")
    print("=" * 60)
    print(f"  Search Endpoint:     {endpoint}")
    print(f"  Index Name:          {index_name}")
    print(f"  Embedding Deployment:{embedding_deployment}")
    print(f"  Dry Run:             {args.dry_run}")
    print(f"  Verify Only:         {args.verify}")
    print()

    # Lazy import to avoid import errors when azure SDK is not installed
    from .azure_search_client import AzureSearchClient
    from .embedding_service import EmbeddingService

    search_client = AzureSearchClient(
        endpoint=endpoint,
        api_key=api_key,
        index_name=index_name,
    )
    embedding_service = EmbeddingService(
        endpoint=openai_endpoint,
        api_key=openai_key,
        deployment=embedding_deployment,
    )

    async def _run() -> None:
        if args.verify:
            print("[Step 1/1] Verifying migration...")
            result = await verify_migration(search_client, embedding_service)
        else:
            print(f"[Step 1/1] Running migration (dry_run={args.dry_run})...")
            result = await migrate_routes(
                search_client, embedding_service, dry_run=args.dry_run
            )

        print()
        print("Result:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        print()

        status_val = result.get("status", result.get("valid", "unknown"))
        if status_val in ("success", "dry_run_complete", True):
            print("[OK] Migration completed successfully")
        else:
            print("[WARNING] Migration completed with issues")
            sys.exit(1)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
