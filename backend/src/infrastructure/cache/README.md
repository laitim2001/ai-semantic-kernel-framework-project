# infrastructure/cache

Async Redis client (redis>=5.0). Used by:
- Cat 4 Context Mgmt: ephemeral compaction state
- Cat 7 State Mgmt: hot session state cache
- Platform.identity: JWT blacklist / rate limiting

**Implementation Phase**: 49.2
**Multi-tenant**: All keys MUST be prefixed `tenant:{uuid}:` per multi-tenant-data.md
