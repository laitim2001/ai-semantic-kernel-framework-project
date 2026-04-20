# Sprint 176 Checklist — Active Retrieval: Multi-Strategy + Cohere Rerank

**Sprint**: 176
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-176-plan.md](sprint-176-plan.md)

---

## Backend — Multi-Strategy Engine

- [ ] `multi_strategy.py` — `retrieve(topic, scope, strategies, per_strategy_k)` function
- [ ] Embedding strategy wraps existing Qdrant search
- [ ] BM25 strategy calls `bm25_search.py`
- [ ] Importance strategy — top-N by importance × recency
- [ ] `asyncio.gather` for parallel execution
- [ ] Merge + de-dup by `memory_id`
- [ ] Source label retention per candidate

## Backend — BM25 Keyword Search

- [ ] `bm25_search.py` — PostgreSQL tsvector or pg_trgm query
- [ ] Keyword extraction from topic (simple tokenization + stop words)
- [ ] Alembic migration adds `content_tsvector tsvector GENERATED ALWAYS AS ...`
- [ ] GIN index on tsvector
- [ ] Scope filter in SQL WHERE
- [ ] Result limit per strategy config

## Backend — Cohere Rerank

- [ ] `reranker.py` — `rerank(query, candidates, top_n, scope)` function
- [ ] Cohere SDK integration (or raw HTTP if SDK unavailable)
- [ ] Model selection: `rerank-english-v3.0` default
- [ ] Timeout 5s; fallback to embedding order
- [ ] Result cache (Redis) 1min by `(scope_hash, topic_hash)`
- [ ] API key from `COHERE_API_KEY` env

## Backend — Pipeline Integration

- [ ] `step1_memory.py` — conditional multi-strategy path
- [ ] `search_query = topic` (from Sprint 175)
- [ ] `candidates = multi_strategy.retrieve(...)` if flag on
- [ ] `reranked = reranker.rerank(...)` if flag on
- [ ] Scope passed through every layer

## Backend — Feature Flags

- [ ] `MULTI_STRATEGY_RETRIEVAL_ENABLED` in settings
- [ ] `COHERE_RERANK_ENABLED` in settings
- [ ] `COHERE_API_KEY` in settings
- [ ] `COHERE_RERANK_MODEL` in settings
- [ ] `MULTI_STRATEGY_PER_STRATEGY_K` default 20
- [ ] `MULTI_STRATEGY_RERANK_TOP_N` default 5

## Backend — Observability

- [ ] `retrieval_strategy_latency_ms{strategy=embedding|bm25|importance}` histogram
- [ ] `retrieval_candidates_total{strategy}` counter
- [ ] `rerank_api_call_total{status=success|timeout|error}` counter
- [ ] `rerank_fallback_rate` gauge
- [ ] `rerank_cache_hit_rate` gauge

## Tests — Unit

- [ ] `test_multi_strategy_engine.py` — each strategy callable independently
- [ ] `test_multi_strategy_engine.py` — merge de-duplicates correctly
- [ ] `test_multi_strategy_engine.py` — source labels preserved
- [ ] `test_multi_strategy_engine.py` — parallel execution (timing test)
- [ ] `test_reranker.py` — API call with correct payload
- [ ] `test_reranker.py` — timeout → fallback preserves embedding order
- [ ] `test_reranker.py` — cache hit skips API call
- [ ] `test_bm25_keyword.py` — tsvector query finds expected matches
- [ ] `test_bm25_keyword.py` — scope filter enforces org boundary

## Tests — Integration

- [ ] `test_multi_strategy_precision.py` — seed 200-memory fixture → run baseline + multi-strategy → assert multi-strategy finds ≥ baseline memories
- [ ] `test_reranker_fallback.py` — mock Cohere 500 → system functional with embedding order
- [ ] `test_rerank_caching.py` — second identical query → no API call

## Benchmark

- [ ] `scripts/benchmark_retrieval_precision.py` script
- [ ] LongMemEval subset downloaded and filtered (multi-session + temporal pairs)
- [ ] Run against baseline / +multi / +rerank / +both
- [ ] Results in `claudedocs/5-status/sprint-176-benchmark-{config}.json`
- [ ] Precision@5 improvement ≥ 15% over Sprint 175 baseline
- [ ] Latency P95 ≤ 1500ms

## Verification

- [ ] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Alembic migration `upgrade head` + `downgrade -1`
- [ ] `pytest backend/tests/unit/integrations/memory/active_retrieval/ -v`
- [ ] `pytest backend/tests/integration/memory/test_multi_strategy_precision.py test_reranker_fallback.py test_rerank_caching.py -v`
- [ ] Manual: enable both flags → send 10 diverse queries → inspect rerank scores in logs
- [ ] Manual: disable Cohere flag → system still works (embedding-only rerank)
- [ ] Benchmark comparison committed in `claudedocs/5-status/`
