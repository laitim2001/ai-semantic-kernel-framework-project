# Sprint 57.147 Retrospective — knowledge connector Slice 3a: per-tenant KB isolation

**Sprint goal**: thread `tenant_id` end-to-end through the knowledge vector path so retrieval is per-tenant isolated (own collection + payload filter + own corpus), proven by a 2-tenant drive-through. Close the **isolation half** of `AD-Knowledge-Connector-RBAC-Citation-Slice3`.

**Outcome**: ✅ achieved. Drive-through PASS (real chat-v2 + real Azure gpt-5.2 + real `text-embedding-3-large` + real Qdrant): bidirectional isolation proven at BOTH the agent-answer layer (alpha can't retrieve beta's Condor doc, and vice-versa) AND the physical Qdrant-collection layer (2 distinct `tenant_<hex>_kb` collections).

---

## Q1 — What went well

- **Day-0 三-prong de-risked the #1 unknown cheaply**: the gating risk was "does the chat path thread a tenant-populated `ExecutionContext` to the executor?" — a 2-file read (`loop.py:2925` + `executor.py:213`) turned it GREEN before any code. The whole sprint hinged on that one fact.
- **"Mirror memory_search" was the right framing**: nearly every building block already existed (`QdrantNamespaceStrategy`, `payload_filter`, `QdrantVectorStore.search(payload_filter=)` was pre-wired in 57.146, the executor's arity auto-dispatch, the forgery-guard pattern). The new code was small; the value was in the wiring + the falsifiable drive-through.
- **Distinct per-tenant secrets made isolation falsifiable** (option A): "Skyhook" (alpha-only) and "Nightjar" (beta-only) codenames let the drive-through PROVE isolation, not just assert it — alpha asking for Condor returned 0 condor.md and the agent honestly said "I did not find Project Condor".
- **Bonus coverage surfaced**: the corpus docs' word "confidential" tripped the per-tenant **output-ESCALATE HITL** (57.93) and the **verification gate** (judge 0.98) fired on the honest "not found" answer — both unplanned, both correct, both on the real path.
- **`_warm_knowledge_index` is a real improvement**: dropping the blocking startup ingest cut startup from ~21s (57.146) to ~1s AND removed the 418-file/3818-section boot-time embedding risk; lazy per-tenant ingest is the more correct production shape.

## Q2 — Estimate accuracy (calibration)

- **Class**: `knowledge-per-tenant-isolation-spike` **0.55** (NEW, 1st data point). Parent-direct, **agent_factor 1.0**.
- **Plan**: bottom-up ~11 hr → class-calibrated commit ~6 hr (mult 0.55).
- **Actual**: ~6-7 hr equivalent. Day 0-2 (code + full gate) ran slightly UNDER (building blocks all existed; `connector.py` not needed; committed fixtures dropped for tempdirs). Day 3 drive-through ran roughly on-budget — the 2-tenant setup + clean restart + 3-leg Playwright drive took real time, but NO connection-shape bug surfaced (unlike 57.145/146) because (a) `QdrantVectorStore.search(payload_filter=)` was pre-tested in 57.146 and (b) the pre-UI programmatic sanity caught nothing to fix.
- **Ratio ≈ 1.0-1.15** (IN band). **KEEP 0.55** — single data point; the "wire existing pieces + mirror memory_search" shape genuinely is lighter than the 0.60 `knowledge-embedding-vector-spike` (no new ABC/infra). If a 2nd `knowledge-per-tenant-isolation-spike` (e.g. Slice 3b RBAC) lands > 1.20, re-point toward 0.65 (the multi-tenant drive-through setup is the variance driver).

## Q3 — What to improve

- **The forgery guard duplicates `memory_tools._detect_forged_scope_args`** (re-implemented locally to avoid a cross-module private import). If a 3rd tenant-scoped tool appears, promote a shared `reject_forged_scope` helper to a common location rather than copy a third time.
- **The keyword fail-soft path is NOT per-tenant** (stays shared root) — acceptable for a degraded fallback, but documented as a limitation; worth a per-tenant keyword folder if the fallback ever becomes load-bearing.

## Q4 — Lessons / ADs

- **Lesson (reusable)**: when a feature needs per-request scope on a process-wide singleton handler, check whether the executor already threads `ExecutionContext` (it does, by arity) BEFORE designing a new plumbing — Day-0 Prong-2 caught that "mirror memory_search" needed zero executor/loop change.
- **Lesson (drive-through)**: a per-tenant feature's drive-through MUST use 2 tenants with DISTINCT content to be falsifiable; identical corpora prove only structural separation (gate-only in disguise).
- Carryover ADs (next slices): `AD-Knowledge-Connector-RBAC-Citation-Slice3` RBAC half (3b) + citation governance (3c) + `AD-Knowledge-Connector-Ingest-Scale` + `AD-Knowledge-Connector-External-Sources` + `AD-Knowledge-Connector-Hybrid-Rerank` + Cat 3 memory semantic axis on this pattern (CARRY-026).

## Q5 — Anti-pattern self-check

- **AP-2** (side-track): ✅ reachable from chat main flow — drive-through ran knowledge_search dual-arity on the real path.
- **AP-4** (Potemkin): ✅ NOT — drive-through proved real per-tenant retrieval (TOOL_EXEC 2265ms) + bidirectional isolation at agent + Qdrant layers; the "I did not find Project Condor" answer is the falsification that a fake would fail.
- **AP-6** (speculative abstraction): ✅ no new abstraction — wires existing `QdrantNamespaceStrategy` + mirrors `memory_search`; `tenant_id=None` keeps 57.146 byte-identical (no premature generality).
- **AP-11** (naming): ✅ `_warm_knowledge_index` renamed from `_ingest_knowledge` to match new behavior (no longer ingests); `_collection_for`/`_connector_for`/`_reject_forged_scope` match behavior.
- **v2 lints**: 11/11 green (incl. `check_llm_sdk_leak`).

## Q6 — Carryover

- `AD-Knowledge-Connector-RBAC-Citation-Slice3` RBAC half (3b) + citation governance (3c) + `AD-Knowledge-Connector-Ingest-Scale` + `AD-Knowledge-Connector-Hybrid-Rerank` + `AD-Knowledge-Connector-External-Sources` + `AD-Knowledge-Connector-DocTypes` + Cat 3 memory semantic axis (CARRY-026). Recorded in `next-phase-candidates.md`.

## Q7 — Drive-through evidence

- 2 tenants: alpha-corp `428d81b6-2808-4f67-8727-9ec7d017940f` · beta-corp `54e4e584-1a7a-48ca-9098-c6b8f9be6268`.
- Leg 1 trace `2010cf4f8caf42e78dbd58ecb6258aaa` (alpha/Falcon, output-ESCALATE HITL). Leg 2 trace `15feab6d310b401fb9213a50ba52450e` (alpha/Condor isolation, judge 0.98). Leg 3 (beta/Condor, Nightjar, 0 falcon leak).
- Qdrant: `tenant_428d81b628084f67_kb` + `tenant_54e4e5841a7a48ca_kb`. Screenshot `sprint-57-147-drivethrough-beta-condor-isolation.png` (playwright dir; not committed). Full narrative: progress.md Day 3.

---

## Design Note Extract (spike sprint — §5.5)

**File**: `docs/03-implementation/agent-harness-planning/51-knowledge-per-tenant-isolation-design.md`
**Verified ratio (estimated)**: ~95% (every §3 invariant has file:line + a verification command or the real-Azure drive-through; §5 deferred items explicitly marked NOT verified)
**8-Point Quality Gate**:
- [x] 1. Section headers map to spike US (US-1..US-5 in §1)
- [x] 2. Each technical claim has file:line (§3 invariants 1-11)
- [x] 3. Decision rationale has comparison matrices (§2: tenant_id plumbing + corpus source + ingest timing)
- [x] 4. Verification commands reproducible (§3: pytest per invariant + the drive-through reproduce)
- [x] 5. Test fixture reference (§3: deterministic double + `_PerCollectionFakeStore` + the real 2-tenant corpora)
- [x] 6. Open invariants explicitly bounded (§5 verified-vs-deferred table + boundary statement)
- [x] 7. Rollback path (§6: tenant_id=None byte-identical + flag-off + full revert < 1 hr, no migration/sentinel)
- [x] 8. 17.md cross-ref (§4: no new contract — reuses QdrantNamespaceStrategy + dual-arity ToolHandler + loop ExecutionContext)

**Reviewer pass**: self-review (solo-dev).
