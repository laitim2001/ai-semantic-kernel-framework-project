# Sprint 57.113 — Checklist (Skills System, thin vertical / model-invoked lazy-load: a system-global `SkillRegistry` loads bundled `SKILL.md` files, a cheap "## Available Skills" block rides the `system_prompt` persona seam, and a `read_skill` tool lazy-loads a skill's full instructions on-demand — the first spike of the Skills System epic, cc-parity row 9; per-tenant catalogs / slash command / wire event deferred)

[Plan](./sprint-57-113-plan.md)

---

## Day 0 — Plan-vs-Repo Verify + Branch ✅

### 0.1 Three-prong Day-0 verify (against `main` HEAD `e133d92f`) — DONE, catalogued in progress.md D1-D7
- [x] **Prong 1 — path verify**: NEW absent (Glob-0) — `agent_harness/skills/` · `backend/config/skills/` · `31-skills-system-spike.md` · CHANGE-080 · test files; EDIT present (Glob-1) — all 7 targets; design note 31 + CHANGE 080 free
- [x] **Prong 2 — content verify** (drift findings in progress.md):
  - [x] **D1 D-system-prompt-seam (CRITICAL) = 🟢 GREEN**: `loop.py:1899-1901` prepends `system_prompt` → `_run_turns` → `state.transient.messages` → builder `_extract_conversation` (`builder.py:529-536`) → `artifact.messages` → chat call (`loop.py:2293/2374`). Persona rides this path (proven by 57.106) → **append-to-`system_prompt` reaches the LLM; NO PromptBuilder rewire**
  - [x] **D2 D-capability-gate = 🟢 GREEN + DRIFT**: chat path builds the matrix from the LIVE registry (`handler.py:555-563` `tool_rules = {spec.name: PermissionRule(...) for spec in registry.list()}`) — NOT from `capability_matrix.yaml` → `read_skill` auto-gets a PASS rule once registered → **DROP the yaml edit (FCL #9)**
  - [x] **D3 D-tool-handler-convention = 🟢 GREEN**: `ToolHandler = Callable[[ToolCall], Awaitable[str|dict]]` async (`executor.py:101-104`); echo `async def echo_handler(call: ToolCall) -> str: return str(call.arguments.get("text",""))` (`echo_tool.py:55-57`); invoked `executor.py:225-228`
  - [x] **D4 D-register-echo-block = 🟢 GREEN**: echo `_register_all.py:256-258`; opt-in precedent (handoff) `:281-284` → mirror `if skill_registry is not None:`
  - [x] **D5 D-config-path = 🟡 DRIFT**: no `core/config` field resolves `backend/config/` → **co-locate bundled skills in `agent_harness/skills/bundled/*.md`** (resolve via `Path(__file__).parent/"bundled"`; robust, packaged-with-code, matches CC `skills/bundled/`)
  - [x] **D6 D-yaml = 🟡 DRIFT**: PyYAML used (`capability_matrix.py:57`) but NOT in `requirements.txt` → **ADD `PyYAML`** (the loader needs `yaml.safe_load`; 57.112 pyotp precedent)
  - [x] **D7 D-import-cycle = 🟢 GREEN**: `skills/` → `_contracts/tools.py` is a clean Cat 5 → contracts import; `from __future__ import annotations`
- [x] **Prong 3 — schema verify**: N/A (NO DB / NO migration this spike) — noted in progress.md
- [x] **Catalog drift** findings in progress.md Day 0 (D1-D7 + implications)
- [x] **Go/no-go**: 🟢 GO — D1 confirms the append works (no pivot); 3 adjustments net-neutral-or-simpler (DROP yaml edit / ADD PyYAML / repoint bundled dir); < 20% shift

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-113-skills-system-spike` (from `main` `e133d92f`)

---

## Day 1 — Backend: SkillRegistry + loader + bundled skills (US-1) ✅

### 1.1 Skill model + SkillRegistry + from_dir loader
- [x] **`requirements.txt`** (D6): added `PyYAML>=6.0,<7.0`; smoke-tested (`yaml 6.0.3` already installed transitively)
- [x] **`agent_harness/skills/registry.py`** (NEW): `Skill` frozen dataclass; `SkillRegistry` (`register` dup→ValueError + `get` + `list`); `from_dir(path)` — sorted `*.md`, `_parse_frontmatter` split `---` maxsplit=2 + `yaml.safe_load`, require name+description+body, **skips malformed with a logged warning (never raises)**; `get_default_skill_registry()` singleton (lazy `from_dir(Path(__file__).parent/"bundled")` per D5); `render_catalog_block` (empty → `""`); file header + WHY
- [x] **`agent_harness/skills/__init__.py`** (NEW): re-exports `Skill`/`SkillRegistry`/`get_default_skill_registry`/`render_catalog_block`/`READ_SKILL_TOOL_SPEC`/`make_read_skill_handler`
  - DoD: ✅ mypy `src` 0 (3 files); black/isort/flake8 0

### 1.2 Bundled skills (REAL, not stubs — AP-4) — co-located `agent_harness/skills/bundled/` (D5)
- [x] **`agent_harness/skills/bundled/code-review.md`** (NEW): frontmatter + body — Summary + Risks table (`| Severity | Issue | Location |`, security>correctness>perf) + Suggested fixes; "no praise/filler"
- [x] **`agent_harness/skills/bundled/summarize.md`** (NEW): frontmatter + body — Decisions / Action Items (owner — task) / Open Questions
  - DoD: ✅ both load via `get_default_skill_registry()` (names `code-review`+`summarize`, non-empty instructions; test_bundled_skills_load asserts len(instructions)>50)

### 1.3 Unit tests (US-1)
- [x] **`tests/unit/agent_harness/skills/test_registry.py`** (NEW, ×10): valid parse · malformed/frontmatter-less skipped (not crash) · missing-dir → empty · dup → ValueError · get hit/miss · `list` deterministic (sorted glob) · 2 bundled load · `render_catalog_block([])` → "" · catalog lists names+descriptions+read_skill instruction · singleton identity stable
  - DoD: ✅ **10 passed**; mypy `src` 0; black/isort/flake8 0

---

## Day 2 — Backend: read_skill tool + main-flow wiring (US-2)

### 2.1 read_skill tool
- [ ] **`agent_harness/skills/tool.py`** (NEW): `READ_SKILL_TOOL_SPEC` (`ToolSpec` name=`read_skill`, `input_schema {name:str, required, additionalProperties:false}`, `risk_level=LOW`, `hitl_policy=AUTO`, `tags=("skills",)`); `make_read_skill_handler(registry)` — closure matching the `ToolHandler` convention (per D-tool-handler-convention); known skill → `f"# Skill: {name}\n\n{instructions}\n\nFollow these instructions for the current task."`; unknown → recoverable "Unknown skill '{name}'. Available: {names}" (NOT an exception); read-only, no DB; re-export from `__init__.py`; file header
- [ ] **Unit tests ADD** `tests/unit/agent_harness/skills/test_tool.py` (NEW): handler returns framed instructions for a known skill · unknown → recoverable message (no raise) · `READ_SKILL_TOOL_SPEC.input_schema` survives `ToolRegistryImpl.register` (valid Draft-2012 schema)
  - DoD: all pass; mypy `src` 0; black/isort/flake8 0

### 2.2 make_default_executor opt-in + build_handler + router wiring
- [ ] **`business_domain/_register_all.py`**: `make_default_executor(..., skill_registry: "SkillRegistry | None" = None)` — after built-ins, `if skill_registry is not None: registry.register(READ_SKILL_TOOL_SPEC); handlers["read_skill"] = make_read_skill_handler(skill_registry)` (mirror echo :257-258 + teammate_mailbox opt-in); MHist 1-line
- [ ] **`api/v1/chat/handler.py`**: `build_handler(..., skill_registry: "SkillRegistry | None" = None)` — (a) `if skill_registry: block = render_catalog_block(skill_registry.list()); if block: system_prompt = f"{system_prompt}\n\n{block}"` before the loop ctor; (b) pass `skill_registry=skill_registry` to `make_default_executor(...)`; MHist 1-line
- [ ] **`api/v1/chat/router.py`**: pass `skill_registry=get_default_skill_registry()` to `build_handler(...)`; MHist 1-line
- [x] ~~`capability_matrix.yaml` allowlist~~ — DROPPED (D2: chat path derives the matrix from the live registry → `read_skill` auto-PASSes once registered)
- [ ] **Integration tests ADD** `tests/integration/api/test_skills_wiring.py` (NEW): `make_default_executor(skill_registry=reg)` → `read_skill` in `registry.list()` · `build_handler(skill_registry=reg)` → constructed loop system text contains "## Available Skills" + both skill names · `build_handler(skill_registry=None)` → system_prompt byte-identical (no-skills regression) · a stubbed-LLM chat emitting `read_skill` → tool result carries the framed instructions
  - DoD: all pass; mypy `src` 0 (all edits); black/isort/flake8 0; `loop.py`/wire/codegen/migrations UNTOUCHED

---

## Day 3 — Full gates + drive-through (US-3) + CHANGE-080

### 3.1 Full gate sweep
- [ ] mypy `src` 0 · black/isort/flake8 0 (full `src tests` CI-identical) · run_all 10/10 (count 24 — no codegen diff; `check_event_schema_sync`+`check_llm_sdk_leak`+`check_cross_category_import` green) · full pytest 2546+N (0 del) · Vitest 840 (unchanged — no FE) · mockup-fidelity 51 (no FE/CSS) · `loop.py`/wire diff empty

### 3.2 Drive-through (US-3 — real chat-v2 :3007 + fresh single-process backend + real Azure LLM; Risk Class E clean restart + startup probe logging loaded skill names)
- [ ] **Clean restart + probe**: kill stale `--reload` workers (`Win32_Process` PID/PPID/StartTime sweep); fresh no-reload backend sole owner of :8000; startup probe confirms `agent_harness/skills/bundled/` loaded (`code-review`+`summarize`)
- [ ] **Leg A (discover+load+follow)**: chat-v2 "Review this function: `<small buggy snippet>`" → model emits `read_skill("code-review")` (Inspector tool view) → tool result = full instructions → assistant output in structured shape (Summary + Risks table w/ severities + Fixes)
- [ ] **Leg B (2nd skill)**: "Summarize this thread: `<few decision lines>`" → `read_skill("summarize")` → Decisions / Action Items / Open Questions
- [ ] **Leg C (no false trigger)**: "What's 2+2 and why?" → NO `read_skill` call
- [ ] Screenshots `artifacts/dt57113-*.png` (tool call + structured output) + observed-vs-intended in progress.md; no dead control / no fixture / no mislabeled output
  - DoD: discover→load→follow drivable e2e on real UI+backend+LLM; output shape proves the skill was followed (not just called); no false trigger

### 3.3 CHANGE-080
- [ ] `claudedocs/4-changes/feature-changes/CHANGE-080-skills-system-spike.md` (1-page)

---

## Day 4 — Closeout

### 4.1 Closeout
- [ ] retrospective.md Q1-Q7 + calibration (NEW `skills-system-spike` 0.60 1st data point — record ratio; agent-delegated: no) + progress.md final
- [ ] **Spike design note `31-skills-system-spike.md`** (§5.5) — 8-point quality gate all ✓, verified ratio recorded (retro Q6)
- [ ] Navigators: CLAUDE.md Current-Sprint row + Last-Updated; MEMORY.md quality pointer + memory subfile `project_phase57_113_skills_system_spike.md`; next-phase-candidates — Skills System epic OPENED (this spike DONE) + deferred ADs (per-tenant catalog / slash command / Inspector affordance / authoring UI / bundled-scripts); sprint-workflow matrix NEW `skills-system-spike` 0.60 1st data point; 17.md — add `read_skill` Cat 2 spec / catalog-block seam if it warrants a contract, else note N/A
- [ ] **Anti-pattern self-check** (retro Q7): AP-4 ✅ real drivable skills (output shape proves followed, not stub); AP-2 ✅ reachable from main flow (router→build_handler→executor), no dead code; AP-8 ✅ rides the proven system_prompt seam (no second prompt-assembly path); AP-3 ✅ skills concentrated in `agent_harness/skills/` + the tool registration in the established `_register_all.py` home
- [ ] PR (push + open on user authorization)
