# Sprint 57.113 Progress — Skills System (thin vertical, model-invoked lazy-load)

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-113-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-113-checklist.md)

---

## Day 0 — 2026-06-13 — Plan-vs-Repo Verify + Branch

Branch `feature/sprint-57-113-skills-system-spike` from `main` `e133d92f` (post-#287).

### Prong 1 — path verify (all GREEN)

NEW absent (Glob-0): `agent_harness/skills/` (whole dir) · `backend/config/skills/` · `31-skills-system-spike.md` · `CHANGE-080-*.md` · `tests/unit/agent_harness/skills/`. EDIT present (Glob-1): `_register_all.py` · `handler.py` · `router.py` · `prompt_builder/builder.py` · `_contracts/tools.py` · `tools/registry.py` · `capability_matrix.py`. Design note 31 free; CHANGE 080 free.

### Prong 2 — content verify (drift findings)

- **D1 — D-system-prompt-seam = 🟢 GREEN (CRITICAL, no pivot)**: traced `system_prompt` → the LLM. `loop.py:1899-1901` prepends `Message(role="system", content=self._system_prompt)` to the local `messages`, passed to `_run_turns(messages=…)` → into `state.transient.messages`. The per-turn LLM call uses `artifact.messages` (`loop.py:2293` `chat_messages = list(artifact.messages)` → `:2374 ChatRequest(messages=chat_messages)`), and the builder's `_extract_conversation(state, user_msg)` (`builder.py:529-536`) returns `state.transient.messages` minus the current user msg — so the persona system message rides into the conversation section of `artifact.messages`. The builder's own `_build_system_section` uses `SYSTEM_ROLE_TEMPLATE` (`builder.py:421-437`, `make_chat_prompt_builder` passes no `system_role_text`), but the **persona reaches the LLM via the `system_prompt` → conversation path** (proven transitively: personas + harness-policy visibly change behavior, 57.106). → **Appending the "## Available Skills" block to `system_prompt` at `build_handler` reaches the LLM.** No PromptBuilder rewire (plan §8-risk-1 fallback NOT triggered).
- **D2 — D-capability-gate = 🟢 GREEN, but DRIFT (drop a planned edit)**: `tool_guardrail.py:97-103` is default-DENY (an unknown tool → `BLOCK` HIGH). BUT the chat path does NOT use `capability_matrix.yaml` — `handler.py:555-563` builds the matrix from the LIVE registry: `tool_rules = {spec.name: PermissionRule(requires_approval=spec.name in escalate_tools) for spec in registry.list()}`. Every registered tool gets a PASS rule (approval only for `CHAT_HITL_ESCALATE_TOOLS = {"echo_tool"}`). The registry is built at `make_default_executor` (`handler.py:470`) BEFORE `:555` iterates it → once `read_skill` is registered in the registry, it AUTO-gets a PASS rule. **→ NO `capability_matrix.yaml` edit needed** (plan File Change List #9 DROPPED). Implication: simpler scope.
- **D3 — D-tool-handler-convention = 🟢 GREEN**: `ToolHandler = Callable[[ToolCall], Awaitable[str | dict]]` (or dual-arity with `ExecutionContext`) — `executor.py:101-104`; ASYNC; reads args via `call.arguments.get(...)`; returns `str | dict`. `echo_handler` (`echo_tool.py:55-57`): `async def echo_handler(call: ToolCall) -> str: return str(call.arguments.get("text", ""))`. Invoked at `executor.py:225-228` (`await handler(call)` or `await handler(call, ctx)`). → `make_read_skill_handler` returns `async def handler(call: ToolCall) -> str` reading `call.arguments.get("name")`.
- **D4 — D-register-echo-block = 🟢 GREEN**: echo registers at `_register_all.py:256-258` (`registry.register(ECHO_TOOL_SPEC); handlers["echo_tool"] = echo_handler`); `ECHO_TOOL_SPEC` in `echo_tool.py:29-52`. Opt-in precedent (`handoff_targets`) `_register_all.py:281-284`: `if handoff_targets is not None: … registry.register(spec); handlers[spec.name] = _adapt_subagent_handler(handler)`. → mirror for `if skill_registry is not None: registry.register(READ_SKILL_TOOL_SPEC); handlers["read_skill"] = make_read_skill_handler(skill_registry)`.
- **D5 — D-config-path = 🟡 DRIFT (repoint bundled dir)**: `CapabilityMatrix.from_yaml` takes an EXPLICIT path from callers (`capability_matrix.py:135`); the chat path never loads the yaml (D2). No `core/config` field / env var resolves `backend/config/`. Rather than introduce a fragile `parents[N]` walk to `backend/config/skills/`, **co-locate the bundled skills INSIDE the package**: `agent_harness/skills/bundled/{code-review,summarize}.md`, resolved via `Path(__file__).parent / "bundled"` — robust (no CWD/layout dependence), packaged with the code, and matches CC's `skills/bundled/` naming. **→ plan File Change List #4/#5 repoint from `backend/config/skills/` to `agent_harness/skills/bundled/`.**
- **D6 — D-yaml = 🟡 DRIFT (add a dep)**: `import yaml  # type: ignore[import-untyped, unused-ignore]` is used (`capability_matrix.py:57`) and works at runtime, but **PyYAML is NOT declared in `requirements.txt`** (transitive only). The `from_dir` frontmatter loader uses `yaml.safe_load` (matches the capability-matrix convention; robust for description strings with colons) → **ADD `PyYAML` to `requirements.txt`** (hygiene + the loader needs it; the 57.112 `pyotp` precedent). Mirror the cross-platform `# type: ignore[import-untyped, unused-ignore]`.
- **D7 — D-import-cycle = 🟢 GREEN**: `agent_harness/skills/` importing `ToolSpec`/`RiskLevel`/`ToolHITLPolicy` from `_contracts/tools.py` is a Cat 5 → contracts import (contracts are the shared bottom layer; no reverse import). Use `from __future__ import annotations` for forward refs.

### Prong 3 — schema verify

N/A this spike — NO DB / NO migration / NO new table / NO ORM change.

### Existing-test scan (convert-not-delete)

No assertion on the exact built-in tool COUNT or on `DEMO_SYSTEM_PROMPT` content found (the one `len(registry) == 1` in `test_chat_category_activation_wiring.py` is the verifier_registry, not the tool registry — unaffected). `read_skill` + the catalog block only appear when `skill_registry` is passed → non-skills tests are unaffected by default.

### Go/no-go: 🟢 GO

3 scope adjustments, all net-neutral-or-simpler (< 20% shift): DROP capability_matrix.yaml edit (D2), ADD requirements.txt PyYAML (D6), repoint bundled dir to `agent_harness/skills/bundled/` (D5). The critical D1 confirms the append-to-`system_prompt` injection works → no PromptBuilder rewire. Proceeding to Day 1.

---

## Day 1 — 2026-06-13 — SkillRegistry + loader + bundled skills (US-1) ✅

**Shipped**: `agent_harness/skills/registry.py` (`Skill` frozen dataclass + `SkillRegistry` register/get/list + `from_dir` frontmatter loader + `get_default_skill_registry` singleton + `render_catalog_block`) · `tool.py` (`READ_SKILL_TOOL_SPEC` + `make_read_skill_handler` — written Day 1 so `__init__` re-exports cleanly) · `__init__.py` re-exports · 2 REAL bundled skills `skills/bundled/{code-review,summarize}.md` · `requirements.txt` += `PyYAML>=6.0,<7.0` (D6) · `tests/unit/agent_harness/skills/test_registry.py` ×10.

**Loader design**: `_parse_frontmatter` splits `---` with `maxsplit=2` (keeps `---` inside the body — markdown rules / table separators — intact) + `yaml.safe_load` for the name/description (robust for descriptions with `:`). A malformed / frontmatter-less / missing-field file is SKIPPED with a logged warning (never raises) so a bad bundled file can't crash chat startup. Bundled dir resolved via `Path(__file__).parent / "bundled"` (D5 — co-located, no CWD dependence).

**Gate**: ✅ 10/10 unit pass (0.13s) · mypy `src` 0 (3 files) · black/isort/flake8 0 · PyYAML 6.0.3 (already installed transitively). No DB / no wire / no FE touched.

**Est vs actual**: registry+loader+tool+bundled+tests ~3 hr est → actual ~2.5 hr (the from_dir loader + 2 real skill bodies were the bulk; the tool.py spec mirrored echo_tool.py directly).

---
