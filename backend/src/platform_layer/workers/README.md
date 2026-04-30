# platform/workers

Async worker queue. Sprint 49.4 PoC compares:

| Option | Pros | Cons |
|--------|------|------|
| Celery (with RabbitMQ) | Mature, simple, broad ecosystem | No native workflow durability |
| Temporal | Workflow-native, durable, replay | More complex, separate cluster |

**Decision lock**: Phase 49.4 retrospective.

## Subagent + memory_extract relevance

Cat 11 (Subagent) FORK mode + Cat 3 memory_extract tool both spawn
async background work. Choice here directly shapes their impl approach.
