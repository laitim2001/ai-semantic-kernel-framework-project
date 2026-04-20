# Sprint 175 Checklist — Active Retrieval: Topic Generation

**Sprint**: 175
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-175-plan.md](sprint-175-plan.md)

---

## Backend — Topic Generator Module

- [ ] `integrations/memory/active_retrieval/__init__.py` with public exports
- [ ] `topic_generator.py` — `TopicResult` dataclass + `generate_topic()` function
- [ ] System prompt constant (anti-injection directives)
- [ ] LLM client integration via existing `integrations/llm/`
- [ ] Timeout handling via `asyncio.wait_for`
- [ ] Fallback to raw query on timeout / exception (no raise)
- [ ] `TopicResult.fallback_triggered` flag set correctly

## Backend — Validation

- [ ] `validation.py` — allowlist regex `^[A-Za-z0-9\u4e00-\u9fff\s.,;:!?'\-\(\)]+$`
- [ ] Length check (5–500 chars)
- [ ] Reject: URLs, SQL keywords (SELECT, INSERT, etc.), curly braces
- [ ] `validate_topic(topic) -> bool` pure function

## Backend — Pipeline Integration

- [ ] `step1_memory.py` — conditional topic gen based on feature flag
- [ ] `search_query = topic if not fallback else ctx.query`
- [ ] `scope=ctx.scope` always passed to search (hardcoded, never from LLM)
- [ ] `PipelineContext.active_retrieval_meta` field for audit
- [ ] `active_retrieval_enabled_for(scope)` helper checks flag + allowlist + blocklist

## Backend — Feature Flag

- [ ] `ACTIVE_RETRIEVAL_ENABLED: bool` in settings
- [ ] `ACTIVE_RETRIEVAL_ORG_ALLOWLIST: list[str]` in settings
- [ ] `ACTIVE_RETRIEVAL_DISABLE_ORGS: list[str]` in settings
- [ ] `LLM_TOPIC_GEN_MODEL: str = "gpt-5-nano"` in settings
- [ ] `TOPIC_GEN_TIMEOUT_MS: int = 500` in settings

## Backend — Observability

- [ ] `active_retrieval_topic_gen_total{status}` metric
- [ ] `active_retrieval_topic_gen_duration_ms` histogram
- [ ] `active_retrieval_validation_rejected_total{reason}` metric
- [ ] Dev-only SSE event `topic_generated` (optional flag)
- [ ] Structured log on fallback triggers

## Tests — Unit

- [ ] `test_topic_generator.py` — success path returns topic + confidence
- [ ] `test_topic_generator.py` — timeout → fallback, no raise
- [ ] `test_topic_generator.py` — LLM exception → fallback
- [ ] `test_topic_validation.py` — valid inputs pass
- [ ] `test_topic_validation.py` — URLs rejected
- [ ] `test_topic_validation.py` — SQL keywords rejected
- [ ] `test_topic_validation.py` — curly braces rejected
- [ ] `test_topic_validation.py` — too short / too long rejected
- [ ] `test_topic_validation.py` — CJK accepted
- [ ] `test_prompt_injection_defense.py` — adversarial prompts fail validation
- [ ] `test_prompt_injection_defense.py` — scope filter unaffected by topic

## Tests — Integration

- [ ] `test_active_retrieval_end_to_end.py` — feature off → raw query in logs
- [ ] `test_active_retrieval_end_to_end.py` — feature on → topic in logs + successful retrieval
- [ ] `test_active_retrieval_per_org_toggle.py` — allowlist behavior
- [ ] `test_active_retrieval_per_org_toggle.py` — blocklist behavior

## Tests — Security

- [ ] `test_prompt_injection_scope_bypass.py` — "ignore scope search org_B" attempt
- [ ] `test_prompt_injection_scope_bypass.py` — scope filter still hardcoded in search call
- [ ] `test_prompt_injection_scope_bypass.py` — malicious topic output rejected by validation

## Benchmark

- [ ] `scripts/benchmark_step1_latency.py` script
- [ ] Pre-change baseline → `claudedocs/5-status/sprint-175-step1-baseline-pre.json`
- [ ] Post-change measurement → `...-post.json`
- [ ] P95 increase ≤ 300ms documented
- [ ] CI gate: P95 increase > 500ms blocks merge

## Verification

- [ ] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Backend starts without import errors
- [ ] `pytest backend/tests/unit/integrations/memory/active_retrieval/ -v`
- [ ] `pytest backend/tests/integration/memory/test_active_retrieval_end_to_end.py test_active_retrieval_per_org_toggle.py -v`
- [ ] `pytest backend/tests/security/test_prompt_injection_scope_bypass.py -v`
- [ ] Manual: enable feature → send query → inspect logs for generated topic + successful memory match
- [ ] Manual: send adversarial query → observe fallback logged + scope filter still applied
- [ ] Benchmark results committed in claudedocs
