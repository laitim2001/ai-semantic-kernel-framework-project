# Sprint 49.4 Progress

**Sprint**: 49.4 — Adapters + Worker Queue + OTel + Lint Rules
**Branch**: `feature/phase-49-sprint-4-adapters-otel-lint`
**Started**: 2026-04-29
**Closed**: 2026-04-29
**Plan**: [`sprint-49-4-plan.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-4-plan.md)
**Story Points**: 32 (planned) → all completed

---

## Day-by-Day estimate vs actual

| Day | Plan | Actual | Ratio | Notes |
|-----|------|--------|-------|-------|
| Day 1 — Adapters: ABC 4 methods + Azure adapter + 41 tests | 7h | ~135 min | 32% | 49.1 ABC stub already had 6 methods → mostly reorg; Azure adapter clean implementation |
| Day 2 — Worker queue spike + decision + agent_loop_worker + 5 tests | 7h | ~95 min | 23% | DocOps spike pattern; chose Temporal for HITL fit |
| Day 3 — OTel SDK + Tracer + 7 metrics + JSON logger + 15 tests | 7h | ~105 min | 25% | NoOp + OTel parallel impl; PHONE_RE greediness fix |
| Day 4 — 4 lint rules + pg_partman + 0010 + tool_calls FK + 13 tests | 6h | ~90 min | 25% | dataclass-via-importlib failed → NamedTuple; lint scripts stdlib-only |
| Day 5 — FastAPI + /health + production guide + closeout | 5h | ~80 min | 27% | TenantContextMiddleware skip-path; 0010 graceful skip; engine dispose fixture |
| **Total** | **32h** | **~8.4h (505 min)** | **26%** | Aligned with 49.2 (15%) / 49.3 (13%) — V2 plans保守是特色 |

---

## Daily highlights

### Day 1 (2026-04-29)
- `_base/pricing.py` + `_base/types.py` + `_base/errors.py` (ProviderError + AdapterException) extracted from 49.1 stub
- `azure_openai/adapter.py` 280 lines implementing ChatClient ABC全6方法 + lazy openai/tiktoken + cancellation + stream + finish_reason 5-row neutral mapping
- `_testing/mock_clients.py` MockChatClient (full ABC + injectable responses)
- 41 contract tests in 4 files (PASS in 0.79s)
- **Pytest path-shadowing trap**: `tests/unit/adapters/__init__.py` shadowed `src/adapters/`; deleted __init__ everywhere in tests/unit/
- Day 1 commit: `c342034`

### Day 2 (2026-04-29)
- `experimental/sprint-49-4-spike/` Celery + Temporal prototypes (DocOps; not run as benchmark)
- Decision report 5-axis comparison → **Temporal chosen** (40% weight on durable resume + HITL = decisive)
- `runtime/workers/queue_backend.py` ABC + MockQueueBackend (in-memory; no broker)
- `runtime/workers/agent_loop_worker.py` stub with retry + cancellation + pluggable handler
- 5 unit tests (PASS in 0.11s)
- **49.3 retro Action item #9 RESOLVED** ✅
- Day 2 commit: `86946c4`

### Day 3 (2026-04-29)
- OTel SDK pinned: opentelemetry-api/sdk/exporter-otlp/exporter-prometheus + 3 instrumentations + python-json-logger
- docker-compose.dev.yml + jaeger:1.62 + prometheus:v2.55.1 + docker/prometheus.yml
- `tracer.py`: NoOpTracer (default for tests/dev) + OTelTracer (lazy SDK; counter/histogram/gauge routing)
- `metrics.py`: REQUIRED_METRICS 7 metrics + emit() with KeyError on typo
- `exporter.py`: OTLP + Prometheus reader builders
- `platform_layer/observability/setup.py` idempotent + `logger.py` PIIRedactor + JSON formatter with auto trace_id injection
- 15 unit tests (PASS in 0.13s)
- **PHONE_RE greediness fix**: regex matched SSN/IPv4 first → reordered substitution
- Day 3 commit: `1f2a6fb`

### Day 4 (2026-04-29)
- 4 V2 lint scripts (stdlib only): duplicate-dataclass / cross-category-import / sync-callback / LLM SDK leak
- `.pre-commit-config.yaml` (4 V2 + black/isort/flake8) + `.github/workflows/lint.yml`
- `docker/Dockerfile.postgres` (postgres:16 full + postgresql-16-partman + bgw config)
- `docker-compose.dev.yml` postgres swap to build context
- `0010_pg_partman.py` migration (CREATE EXTENSION + ops runbook)
- `tool-calls-message-id-fk-decision.md` DEFER to PG 18 (carryover #4 RESOLVED)
- 13 unit tests (lint × 9 + partman × 4)
- **importlib + @dataclass(frozen=True) trap**: `cls.__module__` None in sys.modules → switched to NamedTuple
- Day 4 commit: `cc6f929`

### Day 5 (2026-04-29)
- `api/main.py` FastAPI app factory + lifespan (configure_json_logging + setup_opentelemetry + dispose_engine)
- `api/v1/health.py` upgraded to /health (liveness) + /health/ready (DB ping; 200 OR 503)
- `TenantContextMiddleware.EXEMPT_PATH_PREFIXES` for /api/v1/health (k8s probes免 tenant header)
- `13-deployment-and-devops.md` §Production App Role 5-section guide (NOLOGIN + GRANT CRUD + alarm rule); carryover #2 RESOLVED
- `0010_pg_partman.py` graceful skip when binary unavailable (alembic upgrade head safe on alpine + postgres:16 full both)
- 6 new tests (health × 2 + 1 new pg_partman + 3 docker-compose hookup verifications)
- **49.3 retro lesson重現**: FastAPI/httpx + shared engine → autouse dispose fixture in test_health.py
- 143/143 PASS in 3.68s (0 regression)

---

## Surprises / fixes recorded

1. **`tests/unit/adapters/__init__.py` shadows `src/adapters/`** (Day 1) — deleted; pytest auto-discovery works without
2. **PHONE_RE greedy regex matches SSN/IPv4** (Day 3) — reordered: email → SSN → IPv4 → phone
3. **`@dataclass(frozen=True)` fails under importlib dynamic load** (Day 4) — `cls.__module__` None in sys.modules → use NamedTuple
4. **`mypy` `node.lineno` control-flow narrowing** (Day 4) — used `getattr(node, "lineno", 0)`
5. **TenantContextMiddleware blocks /health for k8s** (Day 5) — added EXEMPT_PATH_PREFIXES
6. **0010 fails on alpine** (Day 5) — graceful skip via `pg_available_extensions` check
7. **engine dispose leak between FastAPI test files** (Day 5) — autouse dispose fixture (49.3 lesson重現)

---

## Cumulative branch state

```
feature/phase-49-sprint-4-adapters-otel-lint
├── dad8ac6 docs(sprint-49-4): plan + checklist
├── c342034 feat(adapters-azure-openai): Day 1 ABC + Azure adapter + 41 tests
├── 86946c4 feat(workers): Day 2 Temporal selection + agent_loop_worker + 5 tests
├── 1f2a6fb feat(observability): Day 3 OTel + 15 tests
├── cc6f929 feat(ci): Day 4 4 lint rules + pg_partman + 13 tests
└── (closeout commit, this) Day 5 — FastAPI + /health + Phase 49 4/4 = 100%
```

6 commits (incl. closeout). Branch sits ~37 commits ahead of `main` because it carries forward all 49.1 + 49.2 + 49.3 work.

---

## Quality gates (all green)

- pytest: **143/143 PASS** (49.3 73 + 49.4 70; 0 SKIPPED; 0 regression; 3.68s)
- mypy --strict: 0 issues across all 49.4 source files (adapters / runtime / observability / api / lint scripts)
- black + isort + flake8: clean
- 4 V2 lint rules on real codebase: all OK (51 dataclasses scanned / 0 cross-category violations / 0 sync mismatches / 0 LLM SDK leaks)
- LLM SDK leak grep on agent_harness/ + business_domain/ + platform_layer/ + runtime/ + api/: **0**
- alembic from-zero cycle: ✅ (`downgrade base` → `upgrade head` ends at `0010_pg_partman`)
- Multi-tenant rule check (4 conditions): ✅
