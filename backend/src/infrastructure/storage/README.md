# infrastructure/storage

Object storage (Azure Blob / S3 abstraction) + Qdrant vector DB client.

**Used by**:
- Cat 3 Memory layer (Vector DB namespace per tenant)
- Subagent FORK mode (full artifact pointer storage)
- Audit log archive (cold storage rotation)

**Implementation Phase**: 51.2 (alongside Memory layer)
**Multi-tenant**: Strict namespace isolation per tenant; never cross-tenant access.
