# Sprint 49.2 Retrospective

**Sprint**: 49.2 — DB Schema + Async ORM 核心
**Branch**: `feature/phase-49-sprint-2-db-orm`
**Started**: 2026-04-29
**Closed**: 2026-04-29
**Plan**: [`sprint-49-2-plan.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-2-plan.md)
**Story Points**: 22 (planned) → all completed

---

## Outcome summary

Sprint 49.2 delivered the **complete async ORM + 4 migrations + AC-3/4/5 verification suite** that all subsequent business sprints (Phase 50+) depend on:

| Deliverable | Status |
|-------------|--------|
| Alembic system (env.py async pattern + 4 migrations) | ✅ |
| 13 ORM models registered against `Base.metadata` | ✅ |
| `TenantScopedMixin` enforcing 鐵律 1 NOT NULL `tenant_id` | ✅ |
| Async engine + session factory + dispose_engine | ✅ |
| FastAPI dependency `get_db_session` | ✅ |
| `StateConflictError` + `compute_state_hash` + `append_snapshot` | ✅ |
| Messages / message_events Partition Day 1 (3 months) | ✅ |
| state_snapshots append-only PG trigger + DBAPIError catch | ✅ |
| StateVersion 雙因子 race (5x parametrize, 0 flake) | ✅ |
| 29 unit tests + 1 skipped (TRUNCATE → 49.3) | ✅ |
| Real docker compose PostgreSQL throughout (AP-10 對策) | ✅ |
| CI 升級：services postgres + alembic step + strict flake8 | ✅ |
| 49.1 retro action items 清算（platform_layer 同步）22 處 | ✅ |

---

## Estimates vs Actual

| Day | Plan | Actual | Ratio |
|-----|------|--------|-------|
| Day 1 — Alembic + Identity migration + ORM | 5h | ~50 min | 17% |
| Day 2 — Sessions partition + ORM + CRUD | 5h | ~45 min | 15% |
| Day 3 — Tools migration + ORM + CRUD | 4h | ~25 min | 10% |
| Day 4 — State + append-only + StateVersion race | 6h | ~50 min | 14% |
| Day 5 — Settings + 文件同步 + 整合驗收 + closeout | 5h | ~60 min | 20% |
| **Total** | **25h** | **~3.8h** | **15%** |

Plan estimates carried generous buffer; actual was ~6.5x faster, consistent with 49.1's 24% ratio (49.2 went smaller because partition + race test design were trickier but Days 1/2/3 were near-templated).

---

## What went well

### 1. AC-3 StateVersion race condition rock-solid
The `asyncio.Barrier(2)` + 2-worker pattern + 5x parametrize iterations all passed without any flakiness. This is the most important test in Sprint 49.2 because it validates the foundational concurrency model that all 範疇 7 (State Management) work in 53.1 will rely on.

### 2. Real docker compose PostgreSQL pytest fixture (NO SQLite)
Per `.claude/rules/testing.md` AP-10 對策, all tests use the real `ipa_v2_postgres` container. The fixture pattern (`db_session` per-test rollback + `dispose_engine()` teardown) handles pytest-asyncio's per-test event loop correctly.

### 3. Migration cycle proven idempotent end-to-end
Day 5.3 verified the **complete cycle from absolute zero**: alembic downgrade base → 1 row (alembic_version) → upgrade head → 20 tables + 1 function + 1 trigger. Every migration has working `downgrade()`.

### 4. Multi-tenant rule strictly enforced via mixin
`TenantScopedMixin` via `@declared_attr @classmethod` ensures every subclass gets its own `tenant_id` Column with FK to `tenants(id)` ON DELETE CASCADE + index. 8 of the 13 ORM tables use it; the 5 exclusions (tenants, tools_registry, user_roles, role_permissions, tool_results) are explicitly documented as intentional global / junction tables.

### 5. 49.1 retro action items closed
Sprint 49.1 retrospective listed 4 action items. All 4 closed in 49.2 Day 5.2:
- ✅ 02-architecture-design.md `platform/` → `platform_layer/`
- ✅ 06-phase-roadmap.md same
- ✅ Other planning docs (03/04/05) swept (22 total replacements)
- ✅ `.gitignore` Python build artifacts already covered

---

## What surprised us / what to improve

### 1. ⚠️ Bash CWD persistence trap
**Severity**: Cost ~10 minutes + spurious `backend/backend/` directory tree.

Early Day 1 used `cd backend && python ...` for one command. CWD persisted across subsequent Bash tool calls. The next `mkdir -p backend/src/...` materialized at `backend/backend/src/...`. Detected via `git ls-files` returning empty for the expected real path. Fix: clean spurious dirs + always use absolute paths or subshell `(cd ... && cmd)` pattern.

**Action item**: include explicit reminder in Sprint plans / SITUATION-V2-SESSION-START prompt that Bash CWD persists.

### 2. ⚠️ Windows cp950 encoding bites alembic
**Severity**: Blocked Day 1.6 alembic upgrade until em-dash removed.

`alembic.ini` originally contained an em-dash `—` (U+2014, UTF-8 0xE2 0x80 0x94). Alembic reads .ini with `encoding="locale"` which on Windows is cp950, choking on UTF-8 bytes. Fix: removed em-dash, all .ini files now ASCII-only.

**Action item**: Sprint 49.4 lint rules should include "all .ini files ASCII-only" check OR project-wide `PYTHONUTF8=1` env var in CI + dev guidance.

### 3. ⚠️ Import style mismatch: `from src.x` vs `from x`
**Severity**: Cost ~5 minutes batch-replace across 7 files.

49.1 imports look like `from agent_harness.x import …` (no `src.` prefix). Day 1 wrote `from src.infrastructure.db.x import …` causing mypy "Source file found twice" errors. Fixed via Python regex script.

**Action item**: SITUATION-V2-SESSION-START prompt should mention import style convention.

### 4. ⚠️ flake8 default 79 chars vs black 100
**Severity**: One-time fix; created `backend/.flake8` for alignment.

49.1 didn't ship a flake8 config. flake8 default = 79 chars conflicts with black target = 100. Sprint 49.2 added `backend/.flake8` (max-line-length=100, extend-ignore E203/W503, per-file F401 for `__init__.py`).

### 5. ⚠️ `tool_calls.message_id` cannot have FK in PG 16
**Severity**: Schema deviation from 09.md L335.

09-db-schema-design.md declared `tool_calls.message_id REFERENCES messages(id)`. But messages is partitioned with composite PK `(id, created_at)` so single-column FK is unsupported in PG 16. **Decision**: keep as plain UUID column without FK. Documented in model + migration docstrings. Could revisit in Sprint 49.3 with composite (id, created_at) reference, or wait for PG 18 partial-partition FK feature.

### 6. ⚠️ Default NOW() partition routing
**Severity**: Day 2 alembic re-cycle (~5 min).

Originally migration 0002 only created 2026-05 + 2026-06 partitions, but docker postgres NOW() = 2026-04-29 fell outside any partition. Fix: added 2026-04 partition (current month) + 05 + 06.

**Action item**: Sprint 49.3 pg_partman automation should pre-create rolling +6 months partitions to avoid this on every clock advance.

### 7. ⚠️ pytest-asyncio per-test event loop + module engine singleton
**Severity**: Day 2 fixture redesign (~10 min).

pytest-asyncio defaults to per-test event loops. The module-level singleton AsyncEngine is bound to the loop where it was first created. Test 2+ runs in new loops and gets `RuntimeError: Event loop is closed` on pooled connections. Fix: `db_session` fixture teardown calls `await dispose_engine()` so each test gets a fresh engine on its own loop. Trade-off: ~10 ms per test for correctness.

### 8. ⚠️ asyncpg trigger exception type
**Severity**: Day 4.4 test rewrite (~5 min).

PostgreSQL `RAISE EXCEPTION` from a trigger surfaces in SQLAlchemy as `sqlalchemy.exc.DBAPIError` (wrapping `asyncpg.exceptions.RaiseError`), NOT `InternalError` or `ProgrammingError` as plan §技術設計 §5 sample suggested. Tests now catch `DBAPIError` and assert message substring.

### 9. ⚠️ TRUNCATE bypasses ROW-level trigger
**Severity**: Test skipped, gap documented.

09-db-schema-design.md L702-705 best practice calls for STATEMENT-level TRUNCATE trigger. Sprint 49.2 only ships ROW-level UPDATE/DELETE trigger. ROW triggers don't fire on TRUNCATE. **Deferred to Sprint 49.3** (audit_log + state_snapshots both gain it together as part of the audit-log security tightening).

---

## Cumulative branch state

```
feature/phase-49-sprint-2-db-orm
├── b414e7c docs(sprint-49-2): plan + checklist
├── 6573033 feat(infrastructure-db, sprint-49-2): Day 1 alembic + identity migration + ORM core
├── 6671615 feat(infrastructure-db, sprint-49-2): Day 2 sessions partition + ORM + CRUD test
├── 2566b97 feat(infrastructure-db, sprint-49-2): Day 3 tools registry/calls/results + CRUD tests
├── 234cca0 feat(infrastructure-db, sprint-49-2): Day 4 state snapshots + append-only + StateVersion race
├── de29d85 docs(sprint-49-2): mark Day 4 checklist DONE (post-commit patch)
└── (closeout commit, this) Day 5 closeout
```

7 commits on the branch (this closeout brings it to 8). Branch sits 24+ commits ahead of `main` because it carries forward the unmerged `feature/phase-49-sprint-1-v2-foundation` work.

---

## Sprint 49.3 prerequisites unblocked

- ✅ All 13 ORM models accessible via `from infrastructure.db.models import …`
- ✅ Alembic migration 0005+ can build on top (0004 is current head)
- ✅ `TenantScopedMixin` ready for new tables
- ✅ pytest fixture + seed helpers pattern established for new test files
- ✅ Real PostgreSQL CI service in place
- ✅ `state_snapshots` append-only trigger pattern reusable for `audit_log`

Sprint 49.3 plan + checklist creation: **NEXT** (rolling planning per `.claude/rules/sprint-workflow.md`).

---

## Action items for Sprint 49.3+ (carry forward)

1. **TRUNCATE trigger**: install STATEMENT-level trigger on `state_snapshots` AND `audit_log` (49.3 audit migration).
2. **pg_partman automation**: pre-create rolling +6 months partitions for messages / message_events / audit_log.
3. **CI lint .ini ASCII-only**: prevent another em-dash incident; Sprint 49.4 lint rules.
4. **`tool_calls.message_id` FK**: revisit either via composite (id, created_at) or wait for PG 18 partial-partition FK.
5. **session.py coverage**: `get_db_session` FastAPI dependency at 43% — add an integration test in 49.3 or when first FastAPI endpoint lands.
6. **Branch protection rule**: still pending user setup in GitHub UI (carried from 49.1 retro).
7. **npm audit 2 moderate vulnerabilities**: still pending (carried from 49.1).

---

## Approvals & sign-off

- [x] All checklist items closed (or explicitly deferred with `🚧` annotation)
- [x] All linters pass (black / isort / flake8 / mypy strict 89 files)
- [x] 29 PASS + 1 SKIPPED (skipped is TRUNCATE deferred to 49.3)
- [x] Migration cycle from zero proven (downgrade base → upgrade head → 20 tables)
- [x] Real PostgreSQL via docker compose throughout
- [x] LLM SDK leak grep: 0 imports
- [x] CI workflow updated with postgres service + alembic step
- [x] Phase 49 README created (option B per 49.2 plan)
- [x] V2 planning docs synced (`platform/` → `platform_layer/` 22 replacements)

**Sprint 49.2 status**: ✅ DONE
