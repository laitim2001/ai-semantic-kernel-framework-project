# infrastructure/messaging

Async messaging client. Backed by RabbitMQ (Celery) or Temporal —
selection deferred to Phase 49.4 PoC (see `platform/workers/README.md`).

**Used by**:
- Cat 11 Subagent (FORK mode background spawn)
- Cat 3 Memory (memory_extract worker)
- Future: business_domain async tasks
