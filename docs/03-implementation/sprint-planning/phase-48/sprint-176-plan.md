# Sprint 176 Plan — Active Retrieval: Multi-Strategy + Cohere Rerank

**Phase**: 48 — Memory System Improvements
**Sprint**: 176
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Plan Version**: **v2** (Batch 3 review — content delivery partial failure, applied known-risk principles)
**Depends on**: Sprint 175 (topic generator provides semantic query input)

---

## v2 Revision Notes

Batch 3 team review delivered YELLOW verdict but full findings lost. v2 applies known-risk principles.

Known-risk integrations:
- **[py] `asyncio.gather(..., return_exceptions=True)`** — partial strategy failure doesn't kill all
- **[py] merge+dedup O(N log N) via `dict`** — avoid O(N²) nested loops
- **[py] Cohere SDK** — sync or async? Use async via `httpx` if SDK sync only
- **[py] rerank cache — Redis preferred** over OrderedDict for cross-process invalidation
- **[py] Pydantic Settings `list[str]` env parsing** — use comma-separated or JSON env var convention
- **[sec] Cohere API PII exposure** — memory content sent to third-party vendor; need DPA + PII redaction option + opt-out per org
- **[sec] BM25 tsvector SQL injection** — use parameterized query, `plainto_tsquery()` not string concat
- **[sec] rerank cache timing leak** — use consistent-time compare or add noise
- **[sec] Cohere trust boundary** — NEVER trust Cohere response for tenant boundaries; scope filter applied BEFORE send + re-checked AFTER receive
- **[qa] LongMemEval subset reproducibility** — check subset script into repo; deterministic selection via seed
- **[qa] CI-without-Cohere** — mock-based test path for offline CI + real-Cohere nightly job

---

## Background

Sprint 175 delivers topic-first retrieval but still runs single-strategy (embedding only). Enterprise research Doc 08 §A.2 identifies two free-lunch quick wins:
1. **Cohere Rerank 3** — 15-30% precision gain via cross-encoder reranking (zero architecture change)
2. **Multi-strategy parallel retrieval** — combine topic embedding + BM25 keyword + recent/important filter, then rerank

This sprint implements both.

---

## User Stories

### US-1: Memory Retrieval Precision Significantly Improves
- **As** an IPA Platform user
- **I want** top-5 retrieved memories to consistently contain the most relevant ones
- **So that** agent responses use the right context and feel more accurate

### US-2: Retrieval Combines Complementary Strategies
- **As** a platform operator
- **I want** memory retrieval to run multiple query strategies in parallel (semantic, keyword, temporal)
- **So that** no relevant memory is missed due to single-method weakness

### US-3: Retrieval Quality Is Measurable
- **As** a platform operator
- **I want** Precision@5 tracked against LongMemEval benchmark subset
- **So that** regressions are detected before prod

---

## Technical Specifications

### Multi-Strategy Retrieval Engine

1. **New module**: `integrations/memory/active_retrieval/multi_strategy.py`
2. **Strategies** (run in parallel via `asyncio.gather`):
   - **Embedding Search**: topic → embedding → Qdrant semantic search (top-K, K=20)
   - **Keyword BM25**: extract keywords from topic → PostgreSQL `session_memory` full-text search (Postgres `tsvector` or `pg_trgm`)
   - **Importance/Recency**: top-N memories with `importance >= 0.6` AND `accessed_at > now() - 7d` within scope
3. **Merge**: union candidate sets, de-duplicate by `memory_id`, preserve source labels for rerank context

### Cohere Rerank Integration

4. **Client wrapper**: `integrations/memory/active_retrieval/reranker.py`
5. **API**: Cohere Rerank 3 (`rerank-english-v3.0` or `rerank-multilingual-v3.0` based on detected language)
6. **Input**: `{query: topic, documents: [m.content for m in candidates], top_n: 5}`
7. **Output**: reordered list with relevance scores; keep original `MemoryEntry` objects by mapping index
8. **Fallback**: if Cohere API timeout/error → fall back to original embedding rank
9. **Cost**: ~$1 per 1000 queries (search output); cache reranked results 1 min by `(scope_hash, topic_hash)`

### Pipeline Integration

10. **`step1_memory.py` enhancement**
    ```python
    if multi_strategy_enabled_for(ctx.scope):
        candidates = await multi_strategy.retrieve(
            topic=search_query,
            scope=ctx.scope,
            strategies=["embedding", "bm25", "importance"],
            per_strategy_k=20,
        )
        reranked = await reranker.rerank(
            query=search_query,
            candidates=candidates,
            top_n=5,
            scope=ctx.scope,
        )
        memories = reranked
    else:
        memories = await self.memory_manager.search(...)  # Sprint 175 path
    ```

### Feature Flags

11. **Config**
    - `MULTI_STRATEGY_RETRIEVAL_ENABLED: bool = False`
    - `COHERE_RERANK_ENABLED: bool = False`
    - `COHERE_API_KEY: str`
    - `COHERE_RERANK_MODEL: str = "rerank-english-v3.0"`
    - `MULTI_STRATEGY_PER_STRATEGY_K: int = 20`
    - `MULTI_STRATEGY_RERANK_TOP_N: int = 5`

### Benchmark Harness

12. **LongMemEval Subset**
    - Download LongMemEval dataset (500 Q-A pairs) — see paper
    - Extract subset relevant to IPA (multi-session, temporal reasoning)
    - Script: `scripts/benchmark_retrieval_precision.py`
    - Measures: Precision@5, Recall@10, MRR, Latency P95
    - Output: `claudedocs/5-status/sprint-176-benchmark-{strategy}.json`

13. **Comparison Matrix**
    | Config | P@5 | R@10 | Latency P95 |
    |--------|-----|------|-------------|
    | Baseline (Sprint 175) | X | Y | Z |
    | +Multi-strategy | — | — | — |
    | +Rerank | — | — | — |
    | +Both | — | — | — |

### Testing

14. **Unit Tests**
    - `test_multi_strategy_engine.py` — each strategy correctness, merge/dedup
    - `test_reranker.py` — API call mock, fallback on error, caching
    - `test_bm25_keyword.py` — tsvector query correctness

15. **Integration Test**
    - `test_multi_strategy_precision.py` — seeded memory dataset → compare Sprint 175 vs Sprint 176 results
    - `test_reranker_fallback.py` — Cohere API down → fall back gracefully

16. **Benchmark Test**
    - Run `scripts/benchmark_retrieval_precision.py` against seeded fixture
    - Assert P@5 ≥ 15% improvement vs Sprint 175 baseline

---

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `backend/src/integrations/memory/active_retrieval/multi_strategy.py` | Create | Multi-strategy engine |
| `backend/src/integrations/memory/active_retrieval/reranker.py` | Create | Cohere Rerank wrapper |
| `backend/src/integrations/memory/active_retrieval/bm25_search.py` | Create | PostgreSQL tsvector/pg_trgm keyword search |
| `backend/alembic/versions/XXX_add_session_memory_tsvector.py` | Create | Add tsvector column + index |
| `backend/src/integrations/orchestration/pipeline/steps/step1_memory.py` | Modify | Integrate multi-strategy + rerank |
| `backend/src/core/settings.py` | Modify | Feature flags + Cohere config |
| `backend/scripts/benchmark_retrieval_precision.py` | Create | LongMemEval subset benchmark |
| `backend/tests/unit/integrations/memory/active_retrieval/test_multi_strategy_engine.py` | Create | Engine tests |
| `backend/tests/unit/integrations/memory/active_retrieval/test_reranker.py` | Create | Rerank tests |
| `backend/tests/unit/integrations/memory/active_retrieval/test_bm25_keyword.py` | Create | BM25 tests |
| `backend/tests/integration/memory/test_multi_strategy_precision.py` | Create | Precision E2E |
| `backend/tests/integration/memory/test_reranker_fallback.py` | Create | Fallback test |

---

## Acceptance Criteria

- [ ] **AC-1**: Multi-strategy engine runs 3 strategies in parallel via `asyncio.gather`
- [ ] **AC-2**: Candidate union de-duplicated by `memory_id`; each retains source label
- [ ] **AC-3**: Cohere Rerank 3 called with `{query: topic, documents, top_n}`; scope filter applied to input candidates (rerank doesn't cross tenants)
- [ ] **AC-4**: API timeout/error → fallback to original embedding rank; fallback rate logged
- [ ] **AC-5**: Rerank results cached 1min by `(scope_hash, topic_hash)`
- [ ] **AC-6**: `session_memory` tsvector column + GIN index created via migration
- [ ] **AC-7**: BM25 search filters by scope (no cross-tenant leak)
- [ ] **AC-8**: Feature flags `MULTI_STRATEGY_RETRIEVAL_ENABLED` + `COHERE_RERANK_ENABLED` independent (can enable either separately)
- [ ] **AC-9**: Benchmark script runs against LongMemEval subset and produces comparison JSON
- [ ] **AC-10**: Precision@5 improvement ≥ 15% vs Sprint 175 baseline (on same fixture)
- [ ] **AC-11**: Latency P95 ≤ 1500ms (Cohere API adds ~300-500ms acceptable)
- [ ] **AC-12**: All unit + integration + benchmark tests pass

---

## Out of Scope

- HyDE (hypothetical answer embedding) — future enhancement
- Reciprocal Rank Fusion (RRF) for merge — simple de-dup sufficient for MVP
- Multi-language rerank model auto-selection — single model for v1
- Rerank result explanation to users — not needed internally
- Full LongMemEval run (115K tokens/convo expensive) — subset only

---

## v2 Implementation Notes (known-risk integrations)

### asyncio.gather with partial failure

```python
async def retrieve(self, topic, scope, strategies, per_strategy_k=20):
    results = await asyncio.gather(
        self._embedding_search(topic, scope, per_strategy_k),
        self._bm25_search(topic, scope, per_strategy_k),
        self._importance_recency(scope, per_strategy_k),
        return_exceptions=True  # CRITICAL: partial failure tolerance
    )

    candidates = []
    for strategy_name, result in zip(["embedding", "bm25", "importance"], results):
        if isinstance(result, Exception):
            logger.warning("strategy_failed", extra={"strategy": strategy_name, "error": str(result)})
            continue
        candidates.extend((c, strategy_name) for c in result)

    # Dedup via dict (O(N log N))
    deduped = {}
    for candidate, source in candidates:
        if candidate.memory_id not in deduped:
            deduped[candidate.memory_id] = (candidate, [source])
        else:
            deduped[candidate.memory_id][1].append(source)  # track all sources
    return [(c, sources) for c, sources in deduped.values()]
```

### Cohere PII Redaction + Opt-Out

```python
# settings.py
class Settings(BaseSettings):
    COHERE_RERANK_ENABLED: bool = False
    COHERE_DISABLED_ORGS: list[str] = []  # orgs opting out of third-party processing
    COHERE_PII_REDACT_ENABLED: bool = True  # redact emails/phones before send

# reranker.py
async def rerank(self, query, candidates, top_n, scope):
    if scope.org_id in settings.COHERE_DISABLED_ORGS:
        return self._fallback_rerank(candidates)[:top_n]

    if settings.COHERE_PII_REDACT_ENABLED:
        docs = [redact_pii(c.content) for c in candidates]
    else:
        docs = [c.content for c in candidates]

    # Pre-send scope re-check: confirm all candidates within scope
    for c in candidates:
        assert c.scope_hash == scope.as_hashed_key_prefix(), "scope leak attempt"

    response = await self._cohere_api.rerank(query=query, documents=docs, top_n=top_n)
    # Post-receive: map indices back, re-verify scope
    reranked = [candidates[r.index] for r in response.results]
    for r in reranked:
        assert r.scope_hash == scope.as_hashed_key_prefix()
    return reranked
```

### BM25 SQL Injection Defense

```python
# bm25_search.py — use parameterized tsquery
async def search(self, topic, scope, limit):
    # Extract keywords via simple tokenizer (not raw topic into SQL)
    keywords = tokenize_stop_words_removed(topic)
    if not keywords:
        return []
    tsquery_str = " & ".join(keywords)  # Prepared for plainto_tsquery

    # Parameterized query via SQLAlchemy
    stmt = select(SessionMemory).where(
        SessionMemory.org_id == scope.org_id,  # scope enforce
        SessionMemory.workspace_id == scope.workspace_id,
        SessionMemory.content_tsvector.op("@@")(func.plainto_tsquery(tsquery_str))
    ).limit(limit)

    result = await self.session.execute(stmt)
    return result.scalars().all()
```

### Rerank Cache via Redis (not OrderedDict)

```python
# reranker.py
async def rerank(self, query, candidates, top_n, scope):
    cache_key = f"rerank:{scope.as_hashed_key_prefix()[:12]}:{hash_query(query)}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await self._cohere_call(...)
    await redis.setex(cache_key, 60, json.dumps(result))
    return result
```

### Settings list[str] parsing

```python
# Pydantic v2 Settings:
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    COHERE_DISABLED_ORGS: list[str] = []

    @field_validator("COHERE_DISABLED_ORGS", mode="before")
    @classmethod
    def parse_csv(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

# In .env: COHERE_DISABLED_ORGS=org_gov,org_hipaa,org_eu
```

### LongMemEval Subset Reproducibility

```python
# scripts/create_longmemeval_subset.py
import random
random.seed(42)  # Deterministic

def select_subset(full_dataset, size=100):
    # Filter: multi-session + temporal reasoning questions
    candidates = [q for q in full_dataset if q.type in ("multi_session", "temporal")]
    return random.sample(candidates, min(size, len(candidates)))

# Save subset manifest (question IDs) to repo:
# backend/tests/fixtures/longmemeval_subset_v1.json
```

### CI Without Cohere Key

```python
# Two test modes:
# 1. Offline CI: mock Cohere responses via `responses` lib or `httpx.MockTransport`
#    Every PR runs this
# 2. Nightly real-Cohere: tagged pytest marker `@pytest.mark.real_cohere`, run in scheduled workflow only
#    with Cohere API key from secrets

@pytest.fixture
def mock_cohere_responses():
    with responses.RequestsMock() as r:
        r.add_callback(responses.POST, "https://api.cohere.ai/v1/rerank", deterministic_rerank)
        yield

def test_multi_strategy_offline(mock_cohere_responses):
    result = multi_strategy.retrieve(...)
    assert len(result) == 5

@pytest.mark.real_cohere
def test_multi_strategy_real_api():
    result = multi_strategy.retrieve(...)
    assert len(result) >= 3
```

---

## Open Item

Batch 3 review body was not captured in full. Before Sprint 176 coding kickoff:
- Re-run focused agent-team review on Sprint 176 v2
- Use file-based consensus delivery
- Specific focus: Cohere DPA requirement, PII redaction effectiveness, LongMemEval subset quality
