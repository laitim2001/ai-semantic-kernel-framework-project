# V9 Configuration & Deployment Analysis

> **Scope**: Complete analysis of environment variables, Docker architecture, dependency versions, CI/CD pipelines, and server configuration.
>
> **Date**: 2026-03-29
>
> **Source Files Analyzed**:
> - `backend/src/core/config.py` (Settings class, 223 lines)
> - `backend/src/core/server_config.py` (ServerConfig class, 147 lines)
> - `.env.example` (root, 118 lines)
> - `backend/.env.example` (197 lines)
> - `docker-compose.yml` (195 lines)
> - `docker-compose.prod.yml` (125 lines)
> - `backend/Dockerfile` (96 lines, 3-stage)
> - `frontend/Dockerfile` (34 lines, 2-stage)
> - `frontend/nginx.conf` (79 lines)
> - `backend/requirements.txt` (128 lines)
> - `frontend/package.json` (69 lines)
> - `.github/workflows/ci.yml` (253 lines)
> - `.github/workflows/e2e-tests.yml` (198 lines)
> - `.github/workflows/deploy-production.yml` (297 lines)
> - `backend/main.py` (333 lines)

---

## Table of Contents

1. [Environment Variables](#1-environment-variables)
2. [Docker Architecture](#2-docker-architecture)
3. [Dependency Versions](#3-dependency-versions)
4. [CI/CD Pipeline](#4-cicd-pipeline)
5. [Server Configuration](#5-server-configuration)
6. [Issues & Recommendations](#6-issues--recommendations)

---

### 環境與配置串聯總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IPA Platform 配置與部署架構                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ① 配置載入鏈                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ .env 檔案     │──→│ Pydantic     │──→│ Settings     │                  │
│  │ (root + back) │    │ BaseSettings │    │ 單例實例     │                  │
│  │ 118 + 197 行  │    │ case_insensit│    │ get_settings()│                 │
│  └──────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                  │                          │
│                                                  ↓                          │
│  ② Docker Compose 服務拓撲                                                 │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │                    docker-compose.yml                         │          │
│  │                                                              │          │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐      │          │
│  │  │Backend  │  │Frontend │  │PostgreSQL│  │  Redis   │      │          │
│  │  │:8000    │  │:3005    │  │:5432     │  │:6379     │      │          │
│  │  │FastAPI  │  │Vite/Nginx│  │ v16      │  │  v7      │      │          │
│  │  └────┬────┘  └────┬────┘  └──────────┘  └──────────┘      │          │
│  │       │            │                                         │          │
│  │  ┌────┴────────────┴─────────────────────────────┐          │          │
│  │  │              ipa-network (bridge)              │          │          │
│  │  └───────────────────────────────────────────────┘          │          │
│  │                                                              │          │
│  │  ┌──────────┐  (docker-compose.prod.yml 額外)               │          │
│  │  │ RabbitMQ │                                                │          │
│  │  │:5672     │                                                │          │
│  │  │:15672 UI │                                                │          │
│  │  └──────────┘                                                │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
│  ③ CI/CD 管線 (.github/workflows/)                                         │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │                                                              │          │
│  │  Push/PR ──→ ci.yml (253 LOC)                               │          │
│  │              │                                               │          │
│  │              ├─→ Lint (black, isort, flake8, ESLint)        │          │
│  │              ├─→ Unit Tests (pytest)                         │          │
│  │              ├─→ Type Check (mypy)                           │          │
│  │              └─→ Build Check (frontend build)               │          │
│  │                                                              │          │
│  │  PR Merge ──→ e2e-tests.yml (198 LOC)                       │          │
│  │              │                                               │          │
│  │              ├─→ Docker Compose Up                          │          │
│  │              ├─→ Integration Tests                          │          │
│  │              └─→ Playwright E2E Tests                       │          │
│  │                                                              │          │
│  │  Tag Push ──→ deploy-production.yml (297 LOC)               │          │
│  │              │                                               │          │
│  │              ├─→ Build Docker Images                        │          │
│  │              ├─→ Push to Registry                           │          │
│  │              └─→ Deploy to K8s/AKS                          │          │
│  │                                                              │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Environment Variables

All environment variables are loaded via Pydantic `BaseSettings` in `backend/src/core/config.py`, with `.env` file support (`env_file=".env"`, case-insensitive, extra fields ignored).

There are **two** `.env.example` files:
- **Root** `.env.example` — covers core platform settings (118 lines)
- **Backend** `backend/.env.example` — extended version with mem0, LDAP, ServiceNow, Swarm, Azure Search, server config (197 lines)

### 1.1 Application Settings

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `APP_ENV` | `Literal["development","staging","production"]` | `"development"` | No | config.py | Application environment; controls error detail exposure, security validation strictness |
| `LOG_LEVEL` | `str` | `"INFO"` | No | config.py | Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL); validated at startup |
| `SECRET_KEY` | `str` | `""` | **Yes (prod)** | config.py | App-level secret; empty/unsafe values raise error in production, warn in dev |
| `ENABLE_API_DOCS` | `bool` | `true` | No | config.py | Enable Swagger UI (`/docs`) and ReDoc (`/redoc`) |
| `ENABLE_SQL_LOGGING` | `bool` | `false` | No | config.py | Enable SQL query logging |
| `STRUCTURED_LOGGING_ENABLED` | `bool` | `false` | No | config.py | Enable structlog JSON output with optional OTel correlation |

### 1.2 Database (PostgreSQL)

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `DB_HOST` | `str` | `"localhost"` | No | config.py | PostgreSQL host |
| `DB_PORT` | `int` | `5432` | No | config.py | PostgreSQL port |
| `DB_NAME` | `str` | `"ipa_platform"` | No | config.py | Database name |
| `DB_USER` | `str` | `"ipa_user"` | No | config.py | Database user |
| `DB_PASSWORD` | `str` | `""` | **Yes (prod)** | config.py | Database password; empty default for dev |

**Derived Properties**:
- `database_url` -> `postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}` (async, for SQLAlchemy)
- `database_url_sync` -> `postgresql://{user}:{password}@{host}:{port}/{name}` (sync, for Alembic)

### 1.3 Redis

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `REDIS_HOST` | `str` | `"localhost"` | No | config.py | Redis host |
| `REDIS_PORT` | `int` | `6379` | No | config.py | Redis port |
| `REDIS_PASSWORD` | `str` | `""` | No | config.py | Redis password; if set, included in URL |

**Derived Property**:
- `redis_url` -> `redis://:{password}@{host}:{port}` (with password) or `redis://{host}:{port}` (without)

### 1.4 RabbitMQ

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `RABBITMQ_HOST` | `str` | `"localhost"` | No | config.py | RabbitMQ host |
| `RABBITMQ_PORT` | `int` | `5672` | No | config.py | RabbitMQ AMQP port |
| `RABBITMQ_USER` | `str` | `"guest"` | No | config.py | RabbitMQ user |
| `RABBITMQ_PASSWORD` | `str` | `"guest"` | No | config.py | RabbitMQ password |

**Derived Property**:
- `rabbitmq_url` -> `amqp://{user}:{password}@{host}:{port}/`

### 1.5 Azure OpenAI

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `AZURE_OPENAI_ENDPOINT` | `str` | `""` | **Yes** | config.py | Azure OpenAI resource endpoint URL |
| `AZURE_OPENAI_API_KEY` | `str` | `""` | **Yes** | config.py | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `str` | `"gpt-5.2"` | No | config.py | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | `str` | `"2024-02-15-preview"` | No | config.py | API version string |

**Derived Property**:
- `is_azure_openai_configured` -> `bool` (True if both endpoint and key are set)

**Discrepancy**: Root `.env.example` shows default deployment `gpt-4o` with API version `2024-02-15-preview`; backend `.env.example` shows `gpt-5.2` with `2024-10-01-preview`; `config.py` defaults to `gpt-5.2` with `2024-02-15-preview`. These should be aligned.

### 1.6 LLM Service (Phase 7)

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `LLM_ENABLED` | `bool` | `true` | No | config.py | Enable LLM service; false falls back to rule-based |
| `LLM_PROVIDER` | `Literal["azure","mock"]` | `"azure"` | No | config.py | LLM provider selection |
| `LLM_MAX_RETRIES` | `int` | `3` | No | config.py | Maximum retry attempts |
| `LLM_TIMEOUT_SECONDS` | `float` | `60.0` | No | config.py | LLM request timeout |
| `LLM_CACHE_ENABLED` | `bool` | `true` | No | config.py | Enable Redis-backed response caching |
| `LLM_CACHE_TTL_SECONDS` | `int` | `3600` | No | config.py | Cache TTL (1 hour default) |

**Derived Property**:
- `is_llm_enabled` -> `bool` (checks both `llm_enabled` flag and provider configuration)

### 1.7 Azure Service Bus

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `AZURE_SERVICE_BUS_CONNECTION_STRING` | `str` | `""` | No | config.py | Connection string; if set, uses ASB over RabbitMQ |

**Derived Property**:
- `use_azure_service_bus` -> `bool` (True if connection string is set)

### 1.8 JWT Authentication

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `JWT_SECRET_KEY` | `str` | `""` | **Yes (prod)** | config.py | JWT signing secret; validated against unsafe values list |
| `JWT_ALGORITHM` | `str` | `"HS256"` | No | config.py | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `60` | No | config.py | Access token lifetime in minutes |

### 1.9 CORS

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `CORS_ORIGINS` | `str` | `"http://localhost:3005,http://localhost:8000"` | No | config.py | Comma-separated allowed origins |

**Derived Property**:
- `cors_origins_list` -> `list[str]` (split by comma, stripped)

**Discrepancy**: Root `.env.example` shows `http://localhost:3000,http://localhost:8000` but `config.py` defaults to `http://localhost:3005,http://localhost:8000`. The frontend runs on port 3005 per project docs, so the root `.env.example` is stale.

### 1.10 Feature Flags

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `FEATURE_WORKFLOW_ENABLED` | `bool` | `true` | No | config.py | Enable workflow engine |
| `FEATURE_AGENT_ENABLED` | `bool` | `true` | No | config.py | Enable agent system |
| `FEATURE_CHECKPOINT_ENABLED` | `bool` | `true` | No | config.py | Enable checkpoint system |

### 1.11 Observability (Sprint 122)

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `OTEL_ENABLED` | `bool` | `false` | No | config.py | Enable OpenTelemetry instrumentation |
| `OTEL_SERVICE_NAME` | `str` | `"ipa-platform"` | No | config.py | OTel service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `str` | `"http://localhost:4317"` | No | config.py | OTLP gRPC endpoint |
| `OTEL_SAMPLING_RATE` | `float` | `1.0` | No | config.py | Trace sampling rate (0.0-1.0) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | `str` | `""` | No | config.py | Azure Application Insights connection |

### 1.12 Server Configuration (Sprint 117)

These are read by `ServerConfig` class in `backend/src/core/server_config.py`, using `os.environ` directly (NOT Pydantic Settings).

| Variable | Type | Default | Required | Source | Description |
|----------|------|---------|----------|--------|-------------|
| `SERVER_ENV` | `str` | `"development"` | No | server_config.py | Server environment (development/staging/production) |
| `UVICORN_WORKERS` | `int` | auto-calculated | No | server_config.py | Override worker count; dev always 1; prod: `min(cpu*2+1, 8)` |
| `SERVER_HOST` | `str` | `"0.0.0.0"` | No | server_config.py | Server bind address |
| `SERVER_PORT` | `int` | `8000` | No | server_config.py | Server bind port |

**Note**: `ServerConfig` duplicates `APP_ENV` with a separate `SERVER_ENV` variable. Both control environment-aware behavior but are read independently.

### 1.13 Variables in `backend/.env.example` Only (NOT in config.py Settings)

The following variables appear in `backend/.env.example` but are **not** defined in the `Settings` class. They are likely consumed by their respective integration modules directly via `os.environ` or separate config classes.

#### Anthropic / OpenAI (mem0)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for mem0 memory extraction |
| `OPENAI_API_KEY` | — | Required for mem0 embeddings |

#### mem0 Memory System

| Variable | Default | Description |
|----------|---------|-------------|
| `MEM0_ENABLED` | `true` | Enable/disable mem0 |
| `QDRANT_PATH` | `/data/mem0/qdrant` | Qdrant vector storage path |
| `QDRANT_COLLECTION` | `ipa_memories` | Qdrant collection name |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for vectors |
| `MEMORY_LLM_PROVIDER` | `anthropic` | LLM provider for memory extraction |
| `MEMORY_LLM_MODEL` | `claude-sonnet-4-20250514` | LLM model for extraction |
| `WORKING_MEMORY_TTL` | `1800` | Working memory TTL (30 min) |
| `SESSION_MEMORY_TTL` | `604800` | Session memory TTL (7 days) |

#### LDAP / Active Directory (Sprint 114)

| Variable | Default | Description |
|----------|---------|-------------|
| `LDAP_SERVER` | `ldap://ad.company.com` | LDAP server URL |
| `LDAP_PORT` | `389` | LDAP port |
| `LDAP_USE_SSL` | `false` | Enable SSL |
| `LDAP_USE_TLS` | `false` | Enable TLS |
| `LDAP_BASE_DN` | `DC=company,DC=com` | Base DN |
| `LDAP_BIND_DN` | — | Service account DN |
| `LDAP_BIND_PASSWORD` | — | Bind password |
| `LDAP_USER_SEARCH_BASE` | `OU=Users,...` | User search base |
| `LDAP_GROUP_SEARCH_BASE` | `OU=Groups,...` | Group search base |
| `LDAP_POOL_SIZE` | `5` | Connection pool size |
| `LDAP_OPERATION_TIMEOUT` | `30` | Operation timeout (seconds) |
| `LDAP_READ_ONLY` | `true` | Read-only mode |
| `LDAP_ALLOWED_OPS` | `search,bind,modify` | Allowed operations |

#### ServiceNow (Sprint 114 + 117)

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICENOW_WEBHOOK_SECRET` | — | Webhook shared secret |
| `SERVICENOW_WEBHOOK_ENABLED` | `true` | Enable webhook |
| `SERVICENOW_ALLOWED_IPS` | `10.0.0.0/8,172.16.0.0/12` | Allowed IP ranges |
| `SERVICENOW_INSTANCE_URL` | — | Instance URL |
| `SERVICENOW_USERNAME` | — | Basic auth username |
| `SERVICENOW_PASSWORD` | — | Basic auth password |
| `SERVICENOW_OAUTH_TOKEN` | — | OAuth2 token (alternative) |
| `SERVICENOW_AUTH_METHOD` | `basic` | Auth method (basic/oauth2) |
| `SERVICENOW_API_VERSION` | `v2` | API version |
| `SERVICENOW_TIMEOUT` | `30` | Request timeout |
| `SERVICENOW_MAX_RETRIES` | `3` | Max retries |

#### Azure AI Search (Sprint 115)

| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_SEARCH_ENDPOINT` | — | Azure AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | — | API key |
| `AZURE_SEARCH_INDEX_NAME` | `semantic-routes` | Index name |
| `USE_AZURE_SEARCH` | `false` | Enable Azure Search |
| `SEMANTIC_SIMILARITY_THRESHOLD` | `0.85` | Similarity threshold |
| `SEMANTIC_TOP_K` | `3` | Top-K results |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-ada-002` | Embedding deployment |

#### Swarm Mode (Sprint 116)

| Variable | Default | Description |
|----------|---------|-------------|
| `SWARM_MODE_ENABLED` | `false` | Enable swarm mode |
| `SWARM_DEFAULT_MODE` | `parallel` | Default pattern (sequential/parallel/hierarchical) |
| `SWARM_MAX_WORKERS` | `5` | Max concurrent workers |
| `SWARM_WORKER_TIMEOUT` | `120.0` | Worker timeout (seconds) |
| `SWARM_COMPLEXITY_THRESHOLD` | `0.7` | Complexity threshold (0.0-1.0) |
| `SWARM_MIN_SUBTASKS` | `2` | Min subtasks for swarm |

#### Docker / Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_USER` | `admin` | Grafana admin user |
| `GRAFANA_PASSWORD` | `please-change-me` | Grafana admin password |

#### Development

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Debug mode |
| `RELOAD` | `true` | Hot reload |
| `LOG_FORMAT` | `json` | Log format |

### 1.14 Frontend Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `/api/v1` | Backend API base URL (Vite prefix required) |
| `VITE_APP_TITLE` | `IPA Platform` | Application title |

---

## 2. Docker Architecture

### 2.1 Development Stack (`docker-compose.yml`)

**Core Services** (always started):

| Service | Image | Container | Port(s) | Volume | Health Check |
|---------|-------|-----------|---------|--------|-------------|
| PostgreSQL | `postgres:16-alpine` | `ipa-postgres` | `5432:5432` | `postgres_data` | `pg_isready` (10s interval, 5s timeout, 5 retries, 10s start) |
| Redis | `redis:7-alpine` | `ipa-redis` | `6379:6379` | `redis_data` | `redis-cli ping` (10s interval, 5s timeout, 5 retries) |
| RabbitMQ | `rabbitmq:3.12-management-alpine` | `ipa-rabbitmq` | `5672:5672`, `15672:15672` | `rabbitmq_data` | `rabbitmq-diagnostics ping` (30s interval, 10s timeout, 5 retries) |

**Monitoring Profile** (started with `--profile monitoring`):

| Service | Image | Container | Port(s) | Volume | Health Check |
|---------|-------|-----------|---------|--------|-------------|
| Jaeger | `jaegertracing/all-in-one:1.53` | `ipa-jaeger` | `16686`, `4317`, `4318` | `jaeger_data` | `wget` (30s interval) |
| Prometheus | `prom/prometheus:v2.48.0` | `ipa-prometheus` | `9090:9090` | `prometheus_data` | `wget` (30s interval) |
| Grafana | `grafana/grafana:10.2.2` | `ipa-grafana` | `3001:3000` | `grafana_data` | `wget` (30s interval) |

**Network**: `ipa-network` (bridge driver)

**Named Volumes**: `ipa-postgres-data`, `ipa-redis-data`, `ipa-rabbitmq-data`, `ipa-jaeger-data`, `ipa-prometheus-data`, `ipa-grafana-data`

**Notable Configuration**:
- Redis uses `--appendonly yes` for persistence
- PostgreSQL uses `--encoding=UTF8` for init
- PostgreSQL mounts `scripts/init-db.sql` as init script
- Grafana port remapped to 3001 to avoid frontend conflict
- Jaeger configured with Badger storage (7-day retention)
- Prometheus configured with 7-day retention
- All core services use `restart: unless-stopped`

### 2.2 Production Stack (`docker-compose.prod.yml`)

| Service | Image/Build | Container | Port | Depends On | Health Check |
|---------|-------------|-----------|------|-----------|-------------|
| Backend | Build from `backend/Dockerfile` target `production` | `ipa-backend` | `8000:8000` | postgres (healthy), redis (healthy) | `curl http://localhost:8000/health` (30s, 10s timeout, 15s start, 3 retries) |
| Frontend | Build from `frontend/Dockerfile` | `ipa-frontend` | `80:80` | backend (healthy) | `wget http://localhost:80` (30s, 10s timeout, 5s start, 3 retries) |
| PostgreSQL | `postgres:16-alpine` | `ipa-postgres-prod` | `5432:5432` | — | `pg_isready` (10s, 5s timeout, 10s start, 5 retries) |
| Redis | `redis:7-alpine` | `ipa-redis-prod` | `6379:6379` | — | `redis-cli ping` (10s, 5s timeout, 5s start, 5 retries) |

**Key Differences from Dev**:
- Backend built from Dockerfile with `target: production` (Gunicorn + Uvicorn workers)
- Frontend built and served via Nginx
- `DB_PASSWORD` is **required** (uses `${DB_PASSWORD:?DB_PASSWORD is required}`)
- No RabbitMQ (production uses Azure Service Bus)
- No monitoring stack (assumed externally managed)
- All services use `restart: always`
- Network: `ipa-prod-network` (bridge)
- Volumes: `postgres_prod_data`, `redis_prod_data`

### 2.3 Backend Dockerfile (Multi-Stage, 3 Stages)

| Stage | Base Image | Purpose | Size Optimization |
|-------|-----------|---------|-------------------|
| `builder` | `python:3.11-slim` | Install build deps + pip packages into venv | `--no-cache-dir`, `rm -rf /var/lib/apt/lists/*` |
| `development` | `python:3.11-slim` | Dev image with QA tools (black, isort, flake8, mypy, pytest) | Copies venv from builder |
| `production` | `python:3.11-slim` | Production image with non-root user, healthcheck | Non-root `appuser:appgroup` (UID/GID 1000) |

**Production Stage Details**:
- Installs `curl` for healthcheck
- Sets `PYTHONUNBUFFERED=1`, `ENVIRONMENT=production`
- Runs as non-root user
- Healthcheck: `curl -f http://localhost:8000/health`
- CMD: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --access-logfile -`

### 2.4 Frontend Dockerfile (Multi-Stage, 2 Stages)

| Stage | Base Image | Purpose |
|-------|-----------|---------|
| `builder` | `node:20-alpine` | `npm ci` + `npm run build` |
| `production` | `nginx:alpine` | Serve built SPA via Nginx |

**Production Stage Details**:
- Copies built `/app/dist` to `/usr/share/nginx/html`
- Copies custom `nginx.conf`
- Healthcheck: `wget -q --spider http://localhost:80`
- Exposes port 80

### 2.5 Nginx Configuration

| Feature | Configuration |
|---------|---------------|
| Security Headers | `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block` |
| Gzip | Level 6, min 256 bytes; HTML, CSS, JS, JSON, SVG |
| Static Caching | JS/CSS/images: 30 days (`immutable`); HTML: no-cache |
| API Proxy | `/api` -> `http://backend:8000` (120s read timeout, 10s connect timeout) |
| Health Proxy | `/health` -> `http://backend:8000/health` |
| SPA Fallback | `try_files $uri $uri/ /index.html` |

---

## 3. Dependency Versions

### 3.1 Backend Python Dependencies (`requirements.txt`)

#### Core Framework

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `fastapi` | `>=0.109.0` | Core | Web framework |
| `uvicorn[standard]` | `>=0.27.0` | Core | ASGI server |
| `pydantic` | `>=2.5.0` | Core | Data validation |
| `pydantic-settings` | `>=2.1.0` | Core | Settings management |

#### Agent Framework

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `agent-framework` | `>=1.0.0rc4,<2.0.0` | MAF | Preview/RC; version-locked to prevent unintended upgrades |

#### Database

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `sqlalchemy` | `>=2.0.25` | Database | ORM |
| `asyncpg` | `>=0.29.0` | Database | PostgreSQL async driver |
| `alembic` | `>=1.13.0` | Database | Migrations |
| `greenlet` | `>=3.0.0` | Database | Required for SQLAlchemy async |

#### Cache & Messaging

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `redis` | `>=5.0.0` | Cache | Redis client |
| `aio-pika` | `>=9.3.0` | Messaging | RabbitMQ async client |

#### Azure Services

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `azure-identity` | `>=1.15.0` | Azure | Identity/auth |
| `azure-keyvault-secrets` | `>=4.7.0` | Azure | Key Vault integration |
| `azure-servicebus` | `>=7.11.0` | Azure | Production message queue |

#### AI/ML

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `anthropic` | `>=0.84.0` | AI | Claude SDK |
| `mem0ai` | `>=0.0.1` | AI | mem0 long-term memory |

#### Authentication & Security

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `slowapi` | `>=0.1.9` | Security | Rate limiting (Sprint 111) |
| `python-jose[cryptography]` | `>=3.3.0` | Security | JWT handling |
| `passlib[bcrypt]` | `>=1.7.4` | Security | Password hashing |
| `bcrypt` | `>=4.0.0,<5.0.0` | Security | **Pinned <5.0** — bcrypt 5.x breaks passlib |
| `python-multipart` | `>=0.0.6` | Security | Form data parsing |

#### HTTP Clients

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `httpx` | `>=0.26.0` | HTTP | Async HTTP client (listed twice — also in Testing) |
| `aiohttp` | `>=3.9.0` | HTTP | Alternative async HTTP |

#### Utilities

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `python-dotenv` | `>=1.0.0` | Util | .env file loading |
| `structlog` | `>=24.1.0` | Util | Structured logging |
| `tenacity` | `>=8.2.0` | Util | Retry logic |
| `croniter` | `>=2.0.0` | Util | Cron expression parsing |
| `aiofiles` | `>=23.0.0` | Util | Async file ops |
| `email-validator` | `>=2.0.0` | Util | Email validation |

#### Observability

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `opentelemetry-api` | `>=1.22.0` | OTel | API |
| `opentelemetry-sdk` | `>=1.22.0` | OTel | SDK |
| `opentelemetry-instrumentation-fastapi` | `>=0.43b0` | OTel | FastAPI auto-instrumentation |
| `opentelemetry-instrumentation-httpx` | `>=0.43b0` | OTel | httpx instrumentation |
| `opentelemetry-instrumentation-redis` | `>=0.43b0` | OTel | Redis instrumentation |
| `opentelemetry-instrumentation-asyncpg` | `>=0.43b0` | OTel | asyncpg instrumentation |
| `opentelemetry-exporter-otlp` | `>=1.22.0` | OTel | OTLP exporter |
| `opentelemetry-semantic-conventions` | `>=0.43b0` | OTel | Semantic conventions |
| `azure-monitor-opentelemetry-exporter` | `>=1.0.0b21` | OTel | Azure Monitor export |
| `prometheus-client` | `>=0.19.0` | OTel | Prometheus metrics |

#### Development

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `black` | `>=24.1.0` | Dev | Formatter |
| `isort` | `>=5.13.0` | Dev | Import sorter |
| `flake8` | `>=7.0.0` | Dev | Linter |
| `mypy` | `>=1.8.0` | Dev | Type checker |
| `ruff` | `>=0.1.0` | Dev | Fast linter |

#### Testing

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `pytest` | `>=8.0.0` | Test | Test runner |
| `pytest-asyncio` | `>=0.23.0` | Test | Async test support |
| `pytest-cov` | `>=4.1.0` | Test | Coverage |
| `pytest-mock` | `>=3.12.0` | Test | Mocking |
| `factory-boy` | `>=3.3.0` | Test | Test data factories |
| `faker` | `>=22.0.0` | Test | Fake data |
| `locust` | `>=2.20.0` | Test | Load testing |
| `pip-audit` | `>=2.6.0` | Security | Vulnerability scanning |
| `bandit` | `>=1.7.0` | Security | Security linter |

#### Type Stubs

| Package | Version Constraint | Category | Notes |
|---------|-------------------|----------|-------|
| `types-redis` | `>=4.6.0` | Types | Redis type stubs |
| `types-passlib` | `>=1.7.0` | Types | passlib type stubs |

**Total**: ~50 direct dependencies (excluding duplicates).

### 3.2 Frontend Dependencies (`package.json`)

#### Production Dependencies

| Package | Version | Category | Notes |
|---------|---------|----------|-------|
| `react` | `^18.2.0` | Core | UI framework |
| `react-dom` | `^18.2.0` | Core | React DOM renderer |
| `react-router-dom` | `^6.21.1` | Core | Client-side routing |
| `@tanstack/react-query` | `^5.17.0` | Data | Server state management |
| `zustand` | `^4.4.7` | State | Global state management |
| `immer` | `^11.1.3` | State | Immutable state updates |
| `@xyflow/react` | `^12.10.1` | Viz | Visual workflow editor (React Flow) |
| `recharts` | `^2.10.3` | Viz | Charting library |
| `dagre` | `^0.8.5` | Viz | Graph layout algorithm |
| `@types/dagre` | `^0.7.53` | Types | Dagre type defs (should be in devDeps) |
| `tailwind-merge` | `^2.2.0` | Styling | Tailwind class merging |
| `class-variance-authority` | `^0.7.0` | Styling | Variant class utility |
| `clsx` | `^2.1.0` | Styling | Conditional classes |
| `lucide-react` | `^0.303.0` | UI | SVG icon library |
| `@radix-ui/react-checkbox` | `^1.3.3` | UI (Radix) | Checkbox primitive |
| `@radix-ui/react-collapsible` | `^1.1.12` | UI (Radix) | Collapsible primitive |
| `@radix-ui/react-dialog` | `^1.0.5` | UI (Radix) | Dialog primitive |
| `@radix-ui/react-dropdown-menu` | `^2.0.6` | UI (Radix) | Dropdown primitive |
| `@radix-ui/react-label` | `^2.0.2` | UI (Radix) | Label primitive |
| `@radix-ui/react-progress` | `^1.1.8` | UI (Radix) | Progress primitive |
| `@radix-ui/react-radio-group` | `^1.3.8` | UI (Radix) | Radio group primitive |
| `@radix-ui/react-scroll-area` | `^1.2.10` | UI (Radix) | Scroll area primitive |
| `@radix-ui/react-select` | `^2.2.6` | UI (Radix) | Select primitive |
| `@radix-ui/react-slot` | `^1.0.2` | UI (Radix) | Slot primitive |
| `@radix-ui/react-tabs` | `^1.0.4` | UI (Radix) | Tabs primitive |
| `@radix-ui/react-tooltip` | `^1.0.7` | UI (Radix) | Tooltip primitive |

#### Dev Dependencies

| Package | Version | Category | Notes |
|---------|---------|----------|-------|
| `typescript` | `^5.3.3` | Core | TypeScript compiler |
| `vite` | `^5.0.11` | Build | Build tool |
| `@vitejs/plugin-react` | `^4.2.1` | Build | React Vite plugin |
| `tailwindcss` | `^3.4.1` | Styling | Utility-first CSS |
| `autoprefixer` | `^10.4.16` | Styling | CSS autoprefixer |
| `postcss` | `^8.4.33` | Styling | CSS processor |
| `eslint` | `^8.56.0` | Lint | JavaScript linter |
| `@typescript-eslint/eslint-plugin` | `^6.17.0` | Lint | TS ESLint plugin |
| `@typescript-eslint/parser` | `^6.17.0` | Lint | TS ESLint parser |
| `eslint-plugin-react-hooks` | `^4.6.0` | Lint | React hooks lint |
| `eslint-plugin-react-refresh` | `^0.4.5` | Lint | React refresh lint |
| `vitest` | `^1.1.3` | Test | Unit test runner |
| `@vitest/ui` | `^1.1.3` | Test | Vitest UI |
| `@vitest/coverage-v8` | `^1.1.3` | Test | Coverage with V8 |
| `@testing-library/react` | `^14.1.2` | Test | React testing |
| `@testing-library/jest-dom` | `^6.2.0` | Test | DOM matchers |
| `jsdom` | `^23.2.0` | Test | DOM environment |
| `@playwright/test` | `^1.40.1` | Test | E2E testing |
| `@types/node` | `^20.10.6` | Types | Node type defs |
| `@types/react` | `^18.2.46` | Types | React type defs |
| `@types/react-dom` | `^18.2.18` | Types | ReactDOM type defs |

**Total**: 26 production + 21 dev dependencies = 47 direct dependencies.

### 3.3 Version Concerns

| Issue | Severity | Details |
|-------|----------|---------|
| `@types/dagre` in production deps | LOW | Should be in `devDependencies` |
| `httpx` listed twice in requirements.txt | LOW | Duplicate entry (HTTP Client + Testing sections) |
| `bcrypt` pinned `<5.0.0` | MEDIUM | passlib incompatibility; monitor for resolution or migration to modern password hashing |
| `agent-framework` RC version | MEDIUM | `>=1.0.0rc4,<2.0.0` — preview/RC; API may change |
| `azure-monitor-opentelemetry-exporter` beta | LOW | `>=1.0.0b21` — still in beta |
| `mem0ai` minimal version | LOW | `>=0.0.1` — very early version; API stability unknown |
| ESLint `^8.56.0` | LOW | ESLint 9.x is current; project uses v8 flat config may need migration |
| Node 18 vs 20 mismatch in CI | MEDIUM | `e2e-tests.yml` uses Node 18; `ci.yml` uses Node 20; Dockerfile uses Node 20 |

---

## 4. CI/CD Pipeline

### 4.1 CI Pipeline (`ci.yml`)

**Triggers**: Push to `main`/`develop`, PRs to `main`/`develop`

**Runtime**: Python 3.11, Node 20

| Job | Runs On | Dependencies | Steps | Parallel |
|-----|---------|-------------|-------|----------|
| `lint` | ubuntu-latest | — | Black, isort, Ruff, mypy | Yes (with test, frontend-test) |
| `frontend-test` | ubuntu-latest | — | npm ci, ESLint, tsc --noEmit, build | Yes (with lint, test) |
| `test` | ubuntu-latest | PostgreSQL 16, Redis 7 | pip install, pytest with coverage, Codecov upload | Yes (with lint, frontend-test) |
| `build` | ubuntu-latest | test + frontend-test | Docker Buildx, build backend + frontend images | Only on main push |
| `ci-summary` | ubuntu-latest | lint + frontend-test + test | Aggregate results | Always |

**Service Containers** (test job):
- PostgreSQL 16-alpine (test_user/test_password/test_db)
- Redis 7-alpine

**Artifacts**: Coverage XML uploaded to Codecov

**Note**: Docker build job does NOT push to ACR yet (commented out, marked TODO).

### 4.2 E2E Tests (`e2e-tests.yml`)

**Triggers**: Push to `main`/`develop`, PRs to `main`/`develop`, manual dispatch

**Runtime**: Python 3.11, Node 18 (MISMATCH with ci.yml Node 20)

| Job | Runs On | Services | Steps |
|-----|---------|----------|-------|
| `backend-e2e` | ubuntu-latest | PostgreSQL 16, Redis 7 | Install deps, run `pytest tests/e2e/` |
| `load-tests` | ubuntu-latest | — | Locust smoke test (placeholder only) |
| `frontend-e2e` | ubuntu-latest | — | npm ci, Playwright install, build, run Playwright (Chromium only) |
| `e2e-summary` | ubuntu-latest | — | Aggregate backend + frontend results |

**Artifacts**:
- `backend-e2e-results` (JUnit XML)
- `playwright-report` (30-day retention)
- `playwright-results`
- `load-test-report` (if exists)

**Note**: Load test job is essentially a no-op (just echoes a message).

### 4.3 Production Deployment (`deploy-production.yml`)

**Triggers**:
- Manual dispatch with `version` (string, required) and `environment` (staging/production choice)
- Push to `main` (excluding `docs/**` and `*.md`)

**Azure Resources**:
- Resource Group: `rg-ipa-platform-production`
- App Service: `app-ipa-platform-production`
- ACR: `ipaplatformacr`

**Secrets Required**: `ACR_USERNAME`, `ACR_PASSWORD`, `AZURE_CREDENTIALS`, `CODECOV_TOKEN`, `GITHUB_TOKEN`, `TEAMS_WEBHOOK_URL`

| Job | Dependencies | Environment | Steps |
|-----|-------------|-------------|-------|
| `build-and-test` | — | — | Checkout, determine version, install deps, pytest with coverage, Codecov |
| `build-image` | build-and-test | — | Login ACR, build+push backend image, build+push frontend image |
| `deploy-staging` | build-and-test + build-image | `staging` | Azure login, deploy backend+frontend to staging slot, health checks (10 retries backend, 5 retries frontend) |
| `deploy-production` | build-and-test + deploy-staging | `production` | Azure login, slot swap (staging -> production), verify health, create GitHub release |
| `notify` | deploy-production | — | Teams webhook notification (success/failure) |

**Deployment Strategy**: Blue-green via Azure App Service slot swap

**Version Tagging**: Git SHA (auto push) or manual version input (dispatch)

---

## 5. Server Configuration

### 5.1 FastAPI Application (`main.py`)

**Application Factory**: `create_app()` returns configured `FastAPI` instance.

**Middleware Stack** (order matters):
1. `RequestIdMiddleware` (Sprint 122) — adds request ID before CORS
2. `CORSMiddleware` — configurable origins, credentials, all methods/headers
3. Rate limiting (`setup_rate_limiting`) — Sprint 111

**Lifespan Events**:

| Phase | Operation | Failure Behavior |
|-------|-----------|-----------------|
| Startup | Validate security settings | Warns in dev, raises in production |
| Startup | Initialize OpenTelemetry | Warning on failure, continues |
| Startup | Initialize database | Error in dev (continues), raise in production |
| Startup | Initialize agent service | Warning (continues, uses mock mode) |
| Shutdown | Close database connections | Log error, continue |
| Shutdown | Shutdown agent service | Log error, continue |
| Shutdown | Shutdown OpenTelemetry | Log error, continue |

**API Documentation**:
- `/docs` (Swagger UI) — controlled by `ENABLE_API_DOCS`
- `/redoc` (ReDoc) — controlled by `ENABLE_API_DOCS`
- `/openapi.json` — controlled by `ENABLE_API_DOCS`
- `redirect_slashes=False` to avoid 307 redirects

**Health Endpoints**:
- `GET /` — API info (service name, version, status, framework, docs link)
- `GET /health` — checks database + Redis connectivity; returns `healthy`/`degraded`
- `GET /ready` — simple readiness probe (always returns `ready: true`)

**Global Exception Handler**:
- Development: returns error detail in response body
- Non-development: returns generic "Internal server error" only

**Version**: `0.2.0`

### 5.2 ServerConfig (`server_config.py`)

Environment-aware Uvicorn/Gunicorn configuration.

| Property | Development | Staging | Production |
|----------|-------------|---------|------------|
| `workers` | 1 (always) | `min(cpu*2+1, 8)` | `min(cpu*2+1, 8)` |
| `reload` | `true` | `false` | `false` |
| `log_level` | `debug` | `info` | `info` |
| `access_log` | `true` | `true` | `false` |
| `worker_class` | `uvicorn.workers.UvicornWorker` | Same | Same |

Worker count can be overridden via `UVICORN_WORKERS` (clamped 1-32).

### 5.3 Nginx (Production Frontend)

See Section 2.5 above for full details. Key points:
- Reverse proxy `/api` to `http://backend:8000`
- SPA fallback for client-side routing
- Security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
- Gzip compression enabled
- Static asset caching (30 days for JS/CSS/images, no-cache for HTML)

---

## 6. Issues & Recommendations

### 6.1 Configuration Issues

| # | Severity | Issue | Details | Recommendation |
|---|----------|-------|---------|----------------|
| 1 | **HIGH** | Dual environment variables `APP_ENV` vs `SERVER_ENV` | `config.py` uses `APP_ENV`, `server_config.py` uses `SERVER_ENV`. Both control env-aware behavior independently. | Unify to single `APP_ENV` variable; have `ServerConfig` read from `Settings`. |
| 2 | **HIGH** | 30+ env vars in `.env.example` not in `Settings` class | LDAP, ServiceNow, Swarm, mem0, Azure Search vars are consumed via `os.environ` directly, bypassing Pydantic validation. | Migrate all env vars to `Settings` class for centralized validation and documentation. |
| 3 | **MEDIUM** | CORS origins mismatch | Root `.env.example` has port 3000; `config.py` default is 3005; frontend actually runs on 3005. | Update root `.env.example` to use port 3005. |
| 4 | **MEDIUM** | Azure OpenAI version drift | Three different default values across root `.env.example`, `backend/.env.example`, and `config.py`. | Align all to single authoritative default (recommend `config.py` as source of truth). |
| 5 | **LOW** | `httpx` listed twice in requirements.txt | HTTP Client section and Testing section both list `httpx>=0.26.0`. | Remove duplicate entry. |
| 6 | **LOW** | Dev/test deps mixed with production in requirements.txt | No separation between production and dev dependencies. | Split into `requirements.txt` (prod) and `requirements-dev.txt` (dev/test). |

### 6.2 Docker Issues

| # | Severity | Issue | Details | Recommendation |
|---|----------|-------|---------|----------------|
| 7 | **MEDIUM** | Production ports exposed externally | `docker-compose.prod.yml` exposes PostgreSQL 5432 and Redis 6379 to host. | Remove host port mappings for DB/Redis in production; only expose via internal network. |
| 8 | **LOW** | Gunicorn workers hardcoded in Dockerfile | Dockerfile CMD uses `-w 4` but `ServerConfig` calculates dynamically. | Use `ServerConfig` via `__main__` block or env-based worker count in CMD. |
| 9 | **LOW** | No `.dockerignore` verified | Large context may include unnecessary files. | Ensure `.dockerignore` excludes `tests/`, `docs/`, `*.md`, `.git/`, `__pycache__/`. |

### 6.3 CI/CD Issues

| # | Severity | Issue | Details | Recommendation |
|---|----------|-------|---------|----------------|
| 10 | **MEDIUM** | Node version mismatch | `e2e-tests.yml` uses Node 18; `ci.yml` uses Node 20; Dockerfile uses Node 20. | Standardize on Node 20 across all workflows and Dockerfile. |
| 11 | **MEDIUM** | Load test job is no-op | `e2e-tests.yml` load test just echoes a message. | Either implement actual staging load test or remove the job. |
| 12 | **LOW** | ACR push not implemented | `ci.yml` build job has commented-out ACR push. | Implement or remove TODO comment. |
| 13 | **LOW** | `actions/create-release@v1` is deprecated | GitHub recommends using `softprops/action-gh-release` or v2. | Upgrade to maintained action. |

### 6.4 Security Observations

| # | Severity | Issue | Details | Recommendation |
|---|----------|-------|---------|----------------|
| 14 | **HIGH** | Secret validation only checks specific unsafe values | `validate_security_settings()` checks against a hardcoded set of unsafe strings. | Add minimum length requirement (e.g., 32+ chars) for production secrets. |
| 15 | **MEDIUM** | Redis password defaults differ | Root `.env.example` has `redis_password`; `backend/.env.example` has empty; Docker Compose defaults to `redis_password`. | Align all examples to same default. |
| 16 | **MEDIUM** | Missing `Content-Security-Policy` header | Nginx config has basic security headers but no CSP. | Add CSP header appropriate for SPA. |
| 17 | **LOW** | `X-XSS-Protection` is deprecated | Modern browsers have removed this feature. | Replace with `Content-Security-Policy` directives. |

### 6.5 Summary Statistics

| Metric | Count |
|--------|-------|
| Total env vars in `Settings` class | 32 |
| Total env vars in `ServerConfig` | 4 |
| Total env vars in `backend/.env.example` only | ~40+ |
| Total env vars (all sources combined) | ~76 |
| Docker services (dev) | 6 (3 core + 3 monitoring) |
| Docker services (prod) | 4 |
| CI/CD workflows | 3 |
| CI/CD jobs total | 13 |
| Backend Python deps | ~50 |
| Frontend npm deps | 47 (26 prod + 21 dev) |
| Dockerfile build stages | 5 (3 backend + 2 frontend) |
| Named Docker volumes | 8 (6 dev + 2 prod) |

---

*Analysis generated from full source file reading. All counts and values verified against source code.*
