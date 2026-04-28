"""
Azure AI Search Index Setup for Semantic Router

Idempotent script to create or update the Azure AI Search index
used by the SemanticRouter for vector-based intent routing.

Sprint 115: Story 115-1 - Azure AI Search Integration

Usage:
    # Standalone CLI
    python -m src.integrations.orchestration.intent_router.semantic_router.setup_index

    # Programmatic
    from src.integrations.orchestration.intent_router.semantic_router.setup_index import (
        setup_index,
        verify_connection,
    )
    setup_index(endpoint, api_key, "semantic-routes")
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Path to the index schema JSON file (sibling of this module)
_SCHEMA_PATH = Path(__file__).parent / "index_schema.json"

# Flag to track if azure-search-documents is available
_AZURE_SEARCH_AVAILABLE = False
_SearchIndexClient = None
_SearchIndex = None
_SearchField = None
_VectorSearch = None
_HnswAlgorithmConfiguration = None
_VectorSearchProfile = None

try:
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        HnswParameters,
        SearchField,
        SearchIndex,
        VectorSearch,
        VectorSearchProfile,
    )
    from azure.core.credentials import AzureKeyCredential
    from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

    _SearchIndexClient = SearchIndexClient
    _SearchIndex = SearchIndex
    _SearchField = SearchField
    _VectorSearch = VectorSearch
    _HnswAlgorithmConfiguration = HnswAlgorithmConfiguration
    _VectorSearchProfile = VectorSearchProfile
    _AZURE_SEARCH_AVAILABLE = True
    logger.info("azure-search-documents library loaded successfully")
except ImportError:
    logger.warning(
        "azure-search-documents library not installed. "
        "Install with: pip install azure-search-documents"
    )


def _load_schema(schema_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load the index schema from the JSON file.

    Args:
        schema_path: Path to the schema file. Defaults to the bundled schema.

    Returns:
        Parsed schema dictionary.

    Raises:
        FileNotFoundError: If the schema file does not exist.
        json.JSONDecodeError: If the schema file contains invalid JSON.
    """
    path = schema_path or _SCHEMA_PATH
    if not path.exists():
        raise FileNotFoundError(f"Index schema file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    logger.info(f"Loaded index schema from {path} ({len(schema.get('fields', []))} fields)")
    return schema


def _build_search_fields(schema: Dict[str, Any]) -> list:
    """
    Build SearchField objects from the schema definition.

    Args:
        schema: Parsed index schema dictionary.

    Returns:
        List of SearchField instances.
    """
    fields = []
    for field_def in schema.get("fields", []):
        kwargs: Dict[str, Any] = {
            "name": field_def["name"],
            "type": field_def["type"],
        }

        # Boolean attributes
        for attr in ("key", "filterable", "searchable", "sortable", "facetable"):
            if attr in field_def:
                kwargs[attr] = field_def[attr]

        # Vector search attributes
        if "vectorSearchProfile" in field_def:
            kwargs["vector_search_profile_name"] = field_def["vectorSearchProfile"]
        if "dimensions" in field_def:
            kwargs["vector_search_dimensions"] = field_def["dimensions"]

        fields.append(_SearchField(**kwargs))

    return fields


def _build_vector_search(schema: Dict[str, Any]) -> Any:
    """
    Build VectorSearch configuration from the schema definition.

    Args:
        schema: Parsed index schema dictionary.

    Returns:
        VectorSearch instance configured with algorithms and profiles.
    """
    vs_config = schema.get("vectorSearch", {})

    # Build algorithm configurations
    algorithms = []
    for algo_def in vs_config.get("algorithms", []):
        hnsw_params_def = algo_def.get("hnswParameters", {})
        hnsw_params = HnswParameters(
            m=hnsw_params_def.get("m", 4),
            ef_construction=hnsw_params_def.get("efConstruction", 400),
            ef_search=hnsw_params_def.get("efSearch", 500),
            metric=hnsw_params_def.get("metric", "cosine"),
        )
        algorithms.append(
            _HnswAlgorithmConfiguration(
                name=algo_def["name"],
                parameters=hnsw_params,
            )
        )

    # Build vector search profiles
    profiles = []
    for profile_def in vs_config.get("profiles", []):
        profiles.append(
            _VectorSearchProfile(
                name=profile_def["name"],
                algorithm_configuration_name=profile_def["algorithmConfigurationName"],
            )
        )

    return _VectorSearch(
        algorithms=algorithms,
        profiles=profiles,
    )


def verify_connection(endpoint: str, api_key: str) -> bool:
    """
    Verify connectivity to the Azure AI Search service.

    Tests that the provided endpoint and API key can successfully
    authenticate and communicate with the search service.

    Args:
        endpoint: Azure AI Search endpoint URL.
        api_key: Azure AI Search admin API key.

    Returns:
        True if connection is successful, False otherwise.
    """
    if not _AZURE_SEARCH_AVAILABLE:
        logger.error("azure-search-documents library is not installed")
        return False

    if not endpoint or not api_key:
        logger.error("Endpoint and API key are required for connection verification")
        return False

    try:
        credential = AzureKeyCredential(api_key)
        client = _SearchIndexClient(endpoint=endpoint, credential=credential)

        # List indexes to verify connectivity (lightweight call)
        indexes = list(client.list_index_names())
        logger.info(
            f"Connection verified. Service has {len(indexes)} existing index(es): "
            f"{', '.join(indexes) if indexes else '(none)'}"
        )
        return True

    except HttpResponseError as e:
        logger.error(f"Azure Search HTTP error during connection verify: {e.message}")
        return False
    except Exception as e:
        logger.error(f"Connection verification failed: {e}")
        return False


def setup_index(
    endpoint: str,
    api_key: str,
    index_name: Optional[str] = None,
    schema_path: Optional[Path] = None,
) -> bool:
    """
    Create or update the Azure AI Search index (idempotent).

    If the index already exists, it will be updated with the current schema.
    If it does not exist, a new index will be created.

    Args:
        endpoint: Azure AI Search endpoint URL.
        api_key: Azure AI Search admin API key.
        index_name: Name of the index. Defaults to the name in schema JSON.
        schema_path: Path to the schema JSON file. Defaults to bundled schema.

    Returns:
        True if the index was created or updated successfully, False otherwise.
    """
    if not _AZURE_SEARCH_AVAILABLE:
        logger.error(
            "azure-search-documents library is not installed. "
            "Install with: pip install azure-search-documents"
        )
        return False

    if not endpoint or not api_key:
        logger.error("Endpoint and API key are required")
        return False

    try:
        # Load schema
        schema = _load_schema(schema_path)
        resolved_name = index_name or schema.get("name", "semantic-routes")

        # Build index components
        fields = _build_search_fields(schema)
        vector_search = _build_vector_search(schema)

        # Build the SearchIndex object
        search_index = _SearchIndex(
            name=resolved_name,
            fields=fields,
            vector_search=vector_search,
        )

        # Connect to Azure AI Search
        credential = AzureKeyCredential(api_key)
        client = _SearchIndexClient(endpoint=endpoint, credential=credential)

        # Check if index already exists
        existing_names = list(client.list_index_names())
        index_exists = resolved_name in existing_names

        if index_exists:
            logger.info(f"Index '{resolved_name}' already exists, updating...")
        else:
            logger.info(f"Index '{resolved_name}' does not exist, creating...")

        # create_or_update_index is idempotent: creates if missing, updates if present
        result = client.create_or_update_index(search_index)

        logger.info(
            f"Index '{result.name}' {'updated' if index_exists else 'created'} successfully "
            f"with {len(result.fields)} fields"
        )
        return True

    except HttpResponseError as e:
        logger.error(f"Azure Search HTTP error: {e.message}")
        return False
    except FileNotFoundError as e:
        logger.error(f"Schema file error: {e}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Schema JSON parse error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during index setup: {e}")
        return False


def _verify_index(endpoint: str, api_key: str, index_name: str) -> bool:
    """
    Verify the index was created and has the expected fields.

    Args:
        endpoint: Azure AI Search endpoint URL.
        api_key: Azure AI Search admin API key.
        index_name: Name of the index to verify.

    Returns:
        True if index exists and has expected fields.
    """
    try:
        credential = AzureKeyCredential(api_key)
        client = _SearchIndexClient(endpoint=endpoint, credential=credential)

        index = client.get_index(index_name)
        field_names = [f.name for f in index.fields]

        expected_fields = {
            "id", "route_name", "category", "sub_intent", "utterance",
            "utterance_vector", "workflow_type", "risk_level", "description",
            "enabled", "created_at", "updated_at",
        }

        missing = expected_fields - set(field_names)
        if missing:
            logger.warning(f"Index '{index_name}' is missing fields: {missing}")
            return False

        logger.info(
            f"Index '{index_name}' verified: {len(index.fields)} fields, "
            f"all expected fields present"
        )
        return True

    except ResourceNotFoundError:
        logger.error(f"Index '{index_name}' not found")
        return False
    except Exception as e:
        logger.error(f"Index verification failed: {e}")
        return False


def main() -> None:
    """
    CLI entry point for setting up the Azure AI Search index.

    Reads configuration from environment variables:
        - AZURE_SEARCH_ENDPOINT: Azure AI Search service endpoint
        - AZURE_SEARCH_API_KEY: Admin API key
        - AZURE_SEARCH_INDEX_NAME: Index name (default: 'semantic-routes')
    """
    # Configure logging for CLI output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("Azure AI Search - Semantic Routes Index Setup")
    print("=" * 60)

    # Read configuration from environment
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    api_key = os.getenv("AZURE_SEARCH_API_KEY", "")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "semantic-routes")

    if not endpoint:
        print("[ERROR] AZURE_SEARCH_ENDPOINT environment variable is not set")
        sys.exit(1)

    if not api_key:
        print("[ERROR] AZURE_SEARCH_API_KEY environment variable is not set")
        sys.exit(1)

    print(f"  Endpoint:   {endpoint}")
    print(f"  Index Name: {index_name}")
    print()

    # Step 1: Verify connection
    print("[Step 1/3] Verifying connection to Azure AI Search...")
    if not verify_connection(endpoint, api_key):
        print("[FAILED] Could not connect to Azure AI Search service")
        sys.exit(1)
    print("[OK] Connection verified")
    print()

    # Step 2: Create or update index
    print("[Step 2/3] Creating/updating index...")
    if not setup_index(endpoint, api_key, index_name):
        print("[FAILED] Index setup failed")
        sys.exit(1)
    print("[OK] Index setup completed")
    print()

    # Step 3: Verify index
    print("[Step 3/3] Verifying index...")
    if not _verify_index(endpoint, api_key, index_name):
        print("[WARNING] Index verification found issues (see logs above)")
    else:
        print("[OK] Index verified successfully")

    print()
    print("=" * 60)
    print("Setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
