# infrastructure/vector

Vector DB namespace abstractions (Qdrant client integration coming in Phase 51.2).

**Implementation Phase**: Sprint 49.3 ✅ COMPLETED (2026-04-29)

## Sprint 49.3 deliverables

### `qdrant_namespace.py`

| Component | Purpose |
|-----------|---------|
| `QdrantNamespaceStrategy.collection_name(tenant_id, layer)` | Build per-tenant per-layer collection name: `tenant_<16-hex>_<layer>` |
| `QdrantNamespaceStrategy.payload_filter(tenant_id)` | Qdrant `Filter` payload requiring `tenant_id` match: `{"must": [{"key": "tenant_id", "match": {"value": "<uuid>"}}]}` |

### Defense-in-depth model

Two independent isolation layers:

1. **Collection naming** — `tenant_<uuid_short>_user_memory` per tenant + layer.
   Even if a future bug picks a wrong collection, only same-tenant rows are addressable.
2. **Payload filter** — every `search` / `scroll` / `delete` includes `tenant_id` match.
   Even if a row's collection assignment is wrong, payload filter still rejects.

### `MemoryLayer` (Literal type)

`"user_memory" | "tenant_memory" | "session_memory" | "kb"`

Phase 51.2 may extend this set; for 49.3 the 5 memory tables in 09-db-schema-design.md cover the foreseeable layers.

## Phase 51.2 will add

- Qdrant client connection wrapper
- `upsert_embeddings(collection, payloads)` with auto-applied tenant_id payload
- `search(collection, query_vector, tenant_id, filter)` that auto-applies the namespace filter
- `delete_by_tenant(tenant_id)` GDPR right-to-erasure helper

## Usage (today, schema-only)

```python
from infrastructure.vector import QdrantNamespaceStrategy

coll = QdrantNamespaceStrategy.collection_name(tenant.id, "user_memory")
# → "tenant_a3f7c891b4d2_user_memory"

filter_payload = QdrantNamespaceStrategy.payload_filter(tenant.id)
# → {"must": [{"key": "tenant_id", "match": {"value": "a3f7c891-b4d2-..."}}]}

# Phase 51.2 will use these to call Qdrant client.
```

## Related

- `09-db-schema-design.md` — `memory_tenant.vector_id` / `memory_user.vector_id`
- `14-security-deep-dive.md` §multi-tenant data isolation
- `sprint-49-3-plan.md` §4 Qdrant Namespace
