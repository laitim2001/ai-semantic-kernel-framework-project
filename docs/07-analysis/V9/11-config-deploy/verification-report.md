# V9 Deep Semantic Verification — config-deploy.md

> **Verifier**: V9 Deep Verification Agent
> **Date**: 2026-03-31
> **Target**: `docs/07-analysis/V9/11-config-deploy/config-deploy.md`
> **Source Files Verified Against**: docker-compose.yml, docker-compose.prod.yml, docker-compose.override.yml, backend/Dockerfile, frontend/Dockerfile, frontend/nginx.conf, backend/src/core/config.py, backend/src/core/server_config.py, backend/main.py, backend/requirements.txt, .env.example, .github/workflows/ci.yml, .github/workflows/e2e-tests.yml, .github/workflows/deploy-production.yml

---

## Result Summary

| Category | Points | Pass | Fail | Warn |
|----------|--------|------|------|------|
| P1-P10: docker-compose.yml | 10 | 8 | 1 | 1 |
| P11-P20: Health check behaviour | 10 | 10 | 0 | 0 |
| P21-P30: CI/CD pipeline | 10 | 8 | 1 | 1 |
| P31-P40: Service dependencies | 10 | 9 | 1 | 0 |
| P41-P50: Configuration override | 10 | 10 | 0 | 0 |
| **TOTAL** | **50** | **45** | **3** | **2** |

---

## P1-P10: docker-compose.yml Service Definitions

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P1 | PostgreSQL image `postgres:16-alpine`, container `ipa-postgres`, port `5432:5432` | **PASS** | docker-compose.yml L23-25, L34-35 |
| P2 | Redis image `redis:7-alpine`, container `ipa-redis`, port `6379:6379` | **PASS** | docker-compose.yml L49-56 |
| P3 | RabbitMQ image `rabbitmq:3.12-management-alpine`, container `ipa-rabbitmq`, ports `5672:5672` + `15672:15672` | **PASS** | docker-compose.yml L69-79 |
| P4 | Jaeger image `jaegertracing/all-in-one:1.53`, ports 16686/4317/4318, monitoring profile | **PASS** | docker-compose.yml L94-118 |
| P5 | Prometheus image `prom/prometheus:v2.48.0`, port 9090, monitoring profile | **PASS** | docker-compose.yml L121-143 |
| P6 | Grafana image `grafana/grafana:10.2.2`, port `3001:3000`, monitoring profile | **PASS** | docker-compose.yml L146-169 |
| P7 | Network `ipa-network` with bridge driver | **PASS** | docker-compose.yml L191-194 |
| P8 | 6 named volumes: ipa-postgres-data, ipa-redis-data, ipa-rabbitmq-data, ipa-jaeger-data, ipa-prometheus-data, ipa-grafana-data | **PASS** | docker-compose.yml L174-186 |
| P9 | Overview diagram shows Backend and Frontend as docker-compose.yml core services | **FAIL** | docker-compose.yml does NOT define backend or frontend services. These are only in docker-compose.prod.yml. The overview diagram (lines 56-58) incorrectly places Backend:8000 and Frontend:3005 inside the docker-compose.yml box. Dev mode runs backend/frontend natively, not via Docker. |
| P10 | Overview diagram shows RabbitMQ as "docker-compose.prod.yml extra" | **WARN** | The diagram (line 67) says RabbitMQ is in docker-compose.prod.yml, but RabbitMQ is actually defined in docker-compose.yml (dev compose, L69-87) and is ABSENT from docker-compose.prod.yml. The doc body (Section 2.2, line 403) correctly states "No RabbitMQ" in prod, but the overview diagram is misleading. |

---

## P11-P20: Health Check Behaviour

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P11 | PostgreSQL: `pg_isready`, 10s interval, 5s timeout, 5 retries, 10s start_period | **PASS** | docker-compose.yml L37-41 |
| P12 | Redis: `redis-cli ping`, 10s interval, 5s timeout, 5 retries | **PASS** | docker-compose.yml L58-61 (note: no start_period defined, doc correctly omits it) |
| P13 | RabbitMQ: `rabbitmq-diagnostics ping`, 30s interval, 10s timeout, 5 retries | **PASS** | docker-compose.yml L81-84 |
| P14 | Jaeger: `wget`, 30s interval, 10s timeout, 3 retries | **PASS** | docker-compose.yml L112-115 |
| P15 | Prometheus: `wget`, 30s interval, 10s timeout, 3 retries | **PASS** | docker-compose.yml L137-140 |
| P16 | Grafana: `wget`, 30s interval, 10s timeout, 3 retries | **PASS** | docker-compose.yml L163-166 |
| P17 | Prod Backend: `curl http://localhost:8000/health`, 30s interval, 10s timeout, 15s start, 3 retries | **PASS** | docker-compose.prod.yml L32-36 |
| P18 | Prod Frontend: `wget http://localhost:80`, 30s interval, 10s timeout, 5s start, 3 retries | **PASS** | docker-compose.prod.yml L55-59 |
| P19 | Prod PostgreSQL: same as dev (pg_isready, 10s, 5s, 10s start, 5 retries) | **PASS** | docker-compose.prod.yml L79-83 |
| P20 | Prod Redis: `redis-cli ping`, 10s interval, 5s timeout, 5s start, 5 retries | **PASS** | docker-compose.prod.yml L103-107 |

---

## P21-P30: CI/CD Pipeline Descriptions

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P21 | ci.yml triggers: push to main/develop, PRs to main/develop | **PASS** | ci.yml L17-20 |
| P22 | ci.yml lint job steps: Black, isort, flake8, mypy | **FAIL** | ci.yml L52-70: actual steps are Black, isort, **Ruff**, mypy. Doc says "flake8" but source uses "Ruff". The lint job installs both flake8 and ruff (L49) but only runs ruff (L64-65). Config-deploy.md Section 4.1 says "Black, isort, Ruff, mypy" which is correct, but Section 2 overview diagram (L78) says "Lint (black, isort, flake8, ESLint)" — the flake8 reference in the overview diagram is wrong. |
| P23 | ci.yml test job uses PostgreSQL 16-alpine + Redis 7-alpine service containers | **PASS** | ci.yml L114-138 |
| P24 | ci.yml build job: only on main push, needs test + frontend-test | **PASS** | ci.yml L190-191 |
| P25 | ci.yml build job does NOT push to ACR (commented out TODO) | **PASS** | ci.yml L216-227 |
| P26 | e2e-tests.yml triggers: push main/develop, PRs main/develop, manual dispatch | **PASS** | e2e-tests.yml L13-17 |
| P27 | e2e-tests.yml uses Node 18 (mismatch with ci.yml Node 20) | **PASS** | e2e-tests.yml L21 `NODE_VERSION: '18'` vs ci.yml L24 `NODE_VERSION: "20"` |
| P28 | deploy-production.yml: manual dispatch with version+environment, push to main | **PASS** | deploy-production.yml L17-37 |
| P29 | deploy-production.yml: blue-green via Azure App Service slot swap | **PASS** | deploy-production.yml L210-216 |
| P30 | deploy-production.yml: load test job is no-op placeholder | **WARN** | e2e-tests.yml L110-116: the load test echoes a message and has locust command commented out. Doc says "essentially a no-op" which is accurate, but marking as WARN since it does install locust (L109) — not purely a no-op from a resource perspective. |

---

## P31-P40: Service Dependencies & Startup Order

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P31 | Prod backend depends_on: postgres (healthy), redis (healthy) | **PASS** | docker-compose.prod.yml L27-30 |
| P32 | Prod frontend depends_on: backend (healthy) | **PASS** | docker-compose.prod.yml L51-53 |
| P33 | Prod PostgreSQL and Redis have no depends_on (independent) | **PASS** | docker-compose.prod.yml L67-110: no depends_on for either |
| P34 | Dev Grafana depends_on: prometheus + jaeger | **PASS** | docker-compose.yml L159-161 |
| P35 | Dev core services (postgres, redis, rabbitmq) have no depends_on | **PASS** | docker-compose.yml: none of the 3 core services have depends_on |
| P36 | Prod uses `restart: always`; dev uses `restart: unless-stopped` | **PASS** | docker-compose.prod.yml L37,60,84,108 all `always`; docker-compose.yml L44,64,87 all `unless-stopped` |
| P37 | Prod network: `ipa-prod-network` (bridge) | **PASS** | docker-compose.prod.yml L115-117 |
| P38 | Prod volumes: `postgres_prod_data`, `redis_prod_data` | **PASS** | docker-compose.prod.yml L122-124 |
| P39 | Prod DB_PASSWORD is required via `${DB_PASSWORD:?...}` | **PASS** | docker-compose.prod.yml L73 |
| P40 | Overview diagram startup order: Backend->PostgreSQL->Redis->RabbitMQ | **FAIL** | The overview diagram (lines 56-60) shows all services at the same level without indicating startup order. The actual prod startup order is: PostgreSQL+Redis start first (independent), then Backend (depends on both healthy), then Frontend (depends on Backend healthy). RabbitMQ is NOT in prod at all. The doc body text (Section 2.2) is correct, but the overview diagram does not accurately represent startup dependencies. |

---

## P41-P50: Configuration Override Mechanism

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P41 | Settings uses Pydantic BaseSettings with `env_file=".env"`, `case_sensitive=False`, `extra="ignore"` | **PASS** | config.py L17-22 |
| P42 | ServerConfig uses `os.environ` directly (NOT Pydantic Settings) | **PASS** | server_config.py L46, L63, L82, L87, L99 all use `os.environ.get()` |
| P43 | `get_settings()` uses `@lru_cache()` for singleton | **PASS** | config.py L215-222 |
| P44 | CORS default in config.py: `http://localhost:3005,http://localhost:8000` | **PASS** | config.py L138 |
| P45 | CORS in root .env.example: `http://localhost:3000,http://localhost:8000` (stale) | **PASS** | .env.example L80 — correctly identified as stale discrepancy |
| P46 | Azure OpenAI deployment default in config.py: `gpt-5.2` | **PASS** | config.py L91 |
| P47 | Azure OpenAI deployment in root .env.example: `gpt-4o` | **PASS** | .env.example L49 — correctly identified as version drift |
| P48 | Dual env vars: APP_ENV (config.py L27) vs SERVER_ENV (server_config.py L46) | **PASS** | Both verified in source; correctly flagged as Issue #1 |
| P49 | docker-compose.yml env_file not used (services use `environment:` block) | **PASS** | docker-compose.yml: postgres (L27-30), redis (L52 command), rabbitmq (L73-74) all use `environment:` or `command:` directly; no `env_file:` directive |
| P50 | docker-compose.prod.yml backend uses `env_file: .env` | **PASS** | docker-compose.prod.yml L23 |

---

## Corrections Required

### FAIL #1 (P9): Overview diagram Backend/Frontend placement

**Location**: config-deploy.md lines 56-60 (overview diagram)

**Problem**: Diagram shows Backend:8000 and Frontend:3005 inside the docker-compose.yml service topology, but these services are NOT defined in docker-compose.yml. They only exist in docker-compose.prod.yml (and run natively in dev mode).

**Fix**: Move Backend and Frontend out of the docker-compose.yml box in the overview diagram, or label them as "native dev / docker-compose.prod.yml".

### FAIL #2 (P22): Overview diagram lint tool name

**Location**: config-deploy.md line 78 (overview diagram)

**Problem**: Overview diagram says `Lint (black, isort, flake8, ESLint)` but ci.yml actually runs Ruff, not flake8. Section 4.1 correctly says "Black, isort, Ruff, mypy" — only the overview diagram is wrong.

**Fix**: Change line 78 from `flake8` to `ruff`.

### FAIL #3 (P40): Overview diagram does not represent startup order

**Location**: config-deploy.md lines 56-60 (overview diagram)

**Problem**: The overview diagram places all services at the same visual level without indicating depends_on chains. Combined with FAIL #1, the diagram misrepresents both service membership and startup dependencies.

**Fix**: Restructure the overview diagram to show: (1) docker-compose.yml only contains infra services, (2) docker-compose.prod.yml adds backend+frontend with dependency arrows.

---

## Warnings

### WARN #1 (P10): RabbitMQ placement in overview diagram

The overview diagram (line 67) labels RabbitMQ as "docker-compose.prod.yml extra" but RabbitMQ is actually in docker-compose.yml (dev) and ABSENT from prod. The doc body text (Section 2.2 line 403) correctly states "No RabbitMQ" in prod.

### WARN #2 (P30): Load test "no-op" characterization

The load test job is described as "essentially a no-op" which is functionally accurate (it echoes a message), but the job does install locust, consuming CI resources. Minor accuracy concern.

---

## Verified Correct (No Changes Needed)

- All 6 docker-compose.yml service definitions (images, containers, ports, volumes): **100% accurate**
- All 10 health check descriptions (commands, intervals, timeouts, retries): **100% accurate**
- All docker-compose.prod.yml service definitions: **100% accurate**
- Backend Dockerfile 3-stage build description: **100% accurate** (builder/development/production stages, non-root user, gunicorn CMD)
- Frontend Dockerfile 2-stage build: **100% accurate** (node:20-alpine builder, nginx:alpine production)
- Nginx config description (security headers, gzip, caching, API proxy, SPA fallback): **100% accurate**
- CI/CD job descriptions (Section 4.1-4.3): **100% accurate** (except overview diagram)
- All config.py Settings class fields and derived properties: **100% accurate**
- ServerConfig environment-aware properties: **100% accurate**
- main.py middleware stack, lifespan events, health endpoints: **100% accurate**
- All discrepancy callouts (CORS stale, Azure version drift, mem0 defaults): **correctly identified**
- All issue severity ratings: **appropriate**
- Summary statistics (Section 6.5): **100% accurate**

---

*Verification completed: 45/50 PASS, 3 FAIL, 2 WARN. All 3 failures are in the overview ASCII diagram (lines 40-98). The detailed body text (Sections 2-6) is 100% accurate.*
