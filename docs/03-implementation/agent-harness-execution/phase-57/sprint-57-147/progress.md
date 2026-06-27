# Sprint 57.147 Progress — knowledge connector Slice 3a: per-tenant KB isolation

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-147-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-147-checklist.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch — 2026-06-27

### Three-prong verify (against `main` HEAD `91ade673`) — ALL GREEN, no scope shift

**Prong 1 — path verify** ✅
- 5 src edit targets exist: `business_domain/knowledge/{__init__,chunking,connector,tools,vector_index}.py`
- 2 test files exist (EDIT): `tests/unit/business_domain/knowledge/{test_vector_index,test_knowledge_tools}.py`
- `CHANGE-114` free (latest CHANGE-113) · design note `51-*` free (latest `50-knowledge-embedding-vector-design.md`)
- `tests/fixtures/knowledge/` does NOT exist → NEW (confirmed via Glob)

**Prong 2 — content verify (drift findings)**

| ID | Finding | Implication |
|----|---------|-------------|
| **D-loop-exec-ctx-tenant** (#1 RISK) | 🟢 GREEN — `loop.py:2925-2929` builds `ExecutionContext(tenant_id=ctx.tenant_id, user_id=ctx.user_id, session_id=…)` + `:2957-2959` `execute(tc, trace_context=ctx, context=exec_ctx)` on the MAIN in-loop tool path; `:3508-3515` same on the resume/approved path | The chat 主流量 passes a tenant-populated `ExecutionContext` → a dual-arity `knowledge_search` WILL receive a real `context.tenant_id`. Whole sprint viable. No pivot. |
| **D-handler-arity-dispatch** | 🟢 `executor.py:213` `if self._handler_takes_context(call.name, handler): handler(call, ctx)` — generic per-handler signature cache (`:308-320`), works for any handler in the dict incl. business-domain | Making `knowledge_search` dual-arity needs ZERO executor change |
| **D-memory-mirror** | 🟢 `memory_tools.py:81-119` `_detect_forged_scope_args` (tolerant: omit/equal/empty allowed) + `:262` dual-arity `(call, context)` — current, mirror-ready | Reuse the forgery-guard shape verbatim |
| **D-startup-ingest** | 🟢 `api/main.py:403-423` `_ingest_knowledge` calls `index.ingest()` with NO tenant_id | After `ingest(tenant_id)` this call site breaks → MUST rework to lazy (drop blocking startup ingest); flag-off no-op preserved. Already plan §3.3 EDIT. |
| **D-namespace-api** | 🟢 `qdrant_namespace.py:88` `collection_name(tid,"kb")` = `tenant_<16hex>_kb` · `:103` `payload_filter(tid)` · `qdrant_client.py:127` `models.Filter.model_validate(payload_filter)` already wired (default None) | All isolation building blocks present + unconsumed; just wire them |

**Prong 3 — schema verify**: N/A — no DB table / migration / ORM column (Qdrant collections only, no Postgres).

**Baselines** (re-verified Day-0): knowledge module `pytest tests/unit/business_domain/knowledge/` = **34 passed, 1 skipped** (0.86s). Full suite trusted from 57.146 closeout (pytest 2980 +6 skip · mypy 0/392 · run_all 11/11 · Vitest 922 · wire 26 · mockup 51) — full sweep at Day 2 / Day 4 gate.

**Go/no-go**: D-loop-exec-ctx-tenant GREEN → **GO**. No scope shift (0%). All 5 drift findings confirm the plan; D-startup-ingest already captured as a plan EDIT.

### Branch
- `git checkout -b feature/sprint-57-147-knowledge-per-tenant-isolation` from `main` `91ade673` ✅

---

## Day 1-2 — Isolation core + composition + tests (US-1/US-2/US-3) — 2026-06-27

### Code (parent-direct, agent_factor 1.0)

- **`vector_index.py`** — constructor now takes `docs_root` (was a single `connector`); `_collection_for(tenant_id)` (per-tenant `tenant_<hex>_kb` / shared `knowledge_local_docs` when None); `_connector_for(tenant_id)` (`<root>/<tenant_id>/` subfolder, shared-root fallback); `search(query, top_k, tenant_id)` lazily ingests then searches the tenant collection + `payload_filter(tenant_id)`; `ingest(tenant_id)` stamps `tenant_id` into every payload (defense-in-depth). tenant_id=None = 57.146 byte-identical.
- **`tools.py`** — `make_knowledge_search_handler` → **dual-arity** `(ToolCall, ExecutionContext)`; `_reject_forged_scope` guard (mirror `memory_tools._detect_forged_scope_args`); threads `context.tenant_id` into `vector_index.search`; keyword fail-soft preserved. Header docstring de-staled (was "Single-arity").
- **`knowledge_index.py`** — passes `settings.knowledge_docs_root` to the index (per-tenant connector resolved at search time); singleton shape unchanged.
- **`api/main.py`** — `_ingest_knowledge` → `_warm_knowledge_index` (drop blocking all-corpus startup ingest → lazy per-tenant on first search; flag-off no-op preserved).
- **`connector.py`** — **UNTOUCHED** (per-tenant resolution lives in `vector_index._connector_for` — one fewer file than planned).

### Scope reduction vs plan
- `connector.py` not edited (resolved in vector_index) — cleaner.
- Committed `tests/fixtures/knowledge/<tenant>/` files NOT created — unit tests use self-contained tempdir subfolders; the Day-3 drive-through creates per-tenant corpora under the dev `KNOWLEDGE_DOCS_ROOT/<real-tenant-uuid>/` at test time (tenant UUIDs are dynamic).

### Tests (+8 net: 34 → 42 knowledge module)
- `test_vector_index.py`: `_PerCollectionFakeStore` (collection-aware + honors payload_filter) + 5 new — per-tenant collection, lazy idempotent per-tenant, **A-cannot-retrieve-B**, payload-filter-rejects-cross-tenant-row, tenant_id=None→shared.
- `test_knowledge_tools.py`: dual-arity calls + 3 new — threads-context-tenant, rejects-forged-tenant-arg, allows-matching-tenant-arg + schema-has-no-tenant_id assertion.

### Full gate (Day 2 gate, run early) — ALL GREEN
- `pytest` (full backend) = **2988 passed, 6 skipped** (was 2980 +6 → +8 new; 134s)
- `mypy src` = **0 issues / 392 files**
- `run_all.py` v2 lints = **11/11 green** (incl. `check_llm_sdk_leak` — EmbeddingClient ABC keeps neutrality; `check_tool_descriptions` — knowledge_search params all described)
- `black` / `isort` / `flake8` = clean
- Frontend UNTOUCHED → Vitest 922 / wire 26 / mockup 51 unchanged

### Remaining
- Day 3: **MANDATORY 2-tenant drive-through** (real chat-v2 + real Azure embedding + real Qdrant) — needs Docker Qdrant + `KNOWLEDGE_VECTOR_ENABLED=1` + embedding deployment + 2 tenant corpora.
- Day 4: CHANGE-114 + design note 51 + retro + navigators + commit.

---

## Day 3 — Drive-through (US-4) — real chat-v2 + real Azure gpt-5.2 + real embedding + real Qdrant — 2026-06-27

### Setup
- 2 tenants via `dev-login` (auto-create by `tenant_code`): **alpha-corp** `428d81b6-2808-4f67-8727-9ec7d017940f` (alice@alpha.com) · **beta-corp** `54e4e584-1a7a-48ca-9098-c6b8f9be6268` (bob@beta.com).
- Per-tenant corpora under `KNOWLEDGE_DOCS_ROOT=C:/Users/Chris/AppData/Local/Temp/kb_dt_57147`: `<alpha-uuid>/falcon.md` (Project **Falcon**, routing-engine codename **Skyhook**) · `<beta-uuid>/condor.md` (Project **Condor**, scoring-model codename **Nightjar**). Distinct secrets → falsifiable isolation.
- **Clean restart (Risk Class E)**: `Win32_Process` sweep — single stale uvicorn (PID 57560, no `--reload` child), killed; port 8000 FREE, 0 python remaining; node (frontend@3007 + claude code) UNTOUCHED. Relaunched single-process (no `--reload`), `PYTHONPATH=src` + `KNOWLEDGE_VECTOR_ENABLED=1` + `QDRANT_URL=http://localhost:6333` + `KNOWLEDGE_DOCS_ROOT=...`. Startup log: `knowledge vector index built (model=text-embedding-3-large)` → `ready (lazy per-tenant ingest)` → `startup complete` (~1s — my `_warm_knowledge_index` no longer blocks on ingest vs 57.146's ~21s).

### Pre-UI sanity (real Azure embed + real Qdrant, programmatic)
- A asks Falcon → `falcon.md` (0.743). A asks Condor → only `falcon.md` (0.447), **never condor.md**. B asks Condor → `condor.md` (0.652). `ISOLATION SANITY: PASS`.

### THE drive-through (real chat-v2 UI via Playwright)
- **Leg 1 — alpha asks Falcon** (trace `2010cf4f8caf42e78dbd58ecb6258aaa`): agent `write_todos` plan → `knowledge_search {"query":"Project Falcon routing engine codename"}` TOOL_EXEC **2265ms** (real embed+Qdrant) → output **`count:2`, both `falcon.md`** (alpha collection only) → answer grounded "internal codename ... **Skyhook**" + cites `falcon.md`. **Bonus**: doc's "confidential" tripped per-tenant **output-ESCALATE HITL** (severity HIGH, `always_ask`) → Approve → `end_turn` (cache_hit 95%).
- **Leg 2 — alpha asks Condor (isolation A↛B)** (trace `15feab6d310b401fb9213a50ba52450e`): `knowledge_search` for Condor on alpha's collection → **0 condor.md** (returned falcon.md) → answer **"I did not find Project Condor"** → `verification_passed llm_judge score=0.98`. **`condor.md` occurrences across the ENTIRE alpha session: 0.**
- **Leg 3 — beta asks Condor (own doc + reverse isolation B↛A)**: re-login beta-corp → fresh session → `knowledge_search` → output **`condor.md` only** → answer "codename ... **Nightjar**" + cites `condor.md`. **`falcon.md` leak on beta's page: 0.**
- **Qdrant layer**: two distinct per-tenant collections created — `tenant_428d81b628084f67_kb` (alpha) + `tenant_54e4e5841a7a48ca_kb` (beta), matching each tenant_id's 16-hex prefix.
- Screenshot: `sprint-57-147-drivethrough-beta-condor-isolation.png` (playwright output dir; not committed — large binary, per 57.145/146 convention).

### AP-4 per-control walk — ALL PASS
- knowledge_search FIRES (real TOOL_EXEC span, not echo) · real snippets render · source paths real · answer grounded + cited · per-tenant retrieval (A↛B + B↛A both proven) · HITL approve flows · verification gate fires · NO fixture/DEMO leakage. **NOT gate-only.**

### Observed vs intended
- Intended: A retrieves only A's docs; B's unique doc invisible to A (and vice-versa), on the real path. Observed: exactly that — bidirectional isolation at the agent-answer layer AND the physical Qdrant-collection layer. Plus the per-tenant output-ESCALATE guardrail + verification gate fired as designed (unplanned bonus coverage).

---
