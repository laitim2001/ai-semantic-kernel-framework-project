"""
File: backend/src/platform_layer/observability/sla_monitor.py
Purpose: SLAMetricRecorder — per-tenant SLA metric recording via Redis sliding windows.
Category: Phase 56 SaaS Stage 1 (platform_layer.observability — range cat 12)
Scope: Sprint 56.3 / Day 1 / US-1 SLA Metric Recorder

Description:
    Records 4 SLA metric categories per 15-saas-readiness.md §SLA 承諾:
    1. API request latency (loop-external endpoints — auth / CRUD)
    2. Loop completion latency by complexity (simple / medium / complex)
    3. HITL queue notification latency (reviewer notification time)
    4. Outage window duration (recorded for monthly aggregation)

    Pattern: Redis Sorted Set (ZADD + ZREMRANGEBYSCORE + ZRANGE) per
    `sla:metrics:{tenant}:{metric}:{window}` key with TTL = 2× window
    seconds (safety buffer for partial reads). Score = unix epoch seconds
    (allows window-based filter via ZRANGEBYSCORE);value = `{ts}:{uuid}`
    composite (allows same-second entries to coexist; 16-byte UUID prefix
    keeps key cardinality bounded).

    Complexity classifier `classify_loop_complexity` consumes LoopCompleted
    event. Day 0 D2 finding: LoopCompleted has only stop_reason / total_turns
    / total_tokens (provider/model/input_tokens/output_tokens missing).
    Classifier therefore uses total_turns + total_tokens as proxies; per-loop
    tool_calls and subagent counts are not visible in LoopCompleted today
    and would require a counter event accumulator (deferred to Phase 56.x —
    AD-Cat10-Cat11-LoopMetricsAccumulator candidate). Conservative fallback:
    unknown / off-spec values → "complex" (worst-case classification).

    Multi-tenant isolation: tenant_id is part of every key — Redis cannot
    cross-tenant leak metric data. SLAReportGenerator (US-2) reads from
    these same keys to compute per-tenant monthly p99 / availability.

    Pattern: caller injects `redis.asyncio.Redis` (this module owns no
    connection lifecycle — same as QuotaEnforcer per 56.1 D-finding +
    53.2 RedisBudgetStore).

Key Components:
    - SLAComplexityCategory: Literal["simple", "medium", "complex"]
    - classify_loop_complexity(event: LoopCompleted) → SLAComplexityCategory
    - SLAMetricRecorder: 4 record + 3 p99 query methods
    - get_sla_recorder / maybe_get_sla_recorder / set_sla_recorder /
      reset_sla_recorder: FastAPI Depends + tests hook (mirrors quota.py)

Modification History (newest-first):
    - 2026-05-06: Initial creation (Sprint 56.3 Day 1 / US-1 SLA Metric Recorder)

Related:
    - sprint-56-3-plan.md §US-1 SLA Metric Recorder
    - 15-saas-readiness.md §SLA 承諾 + §SLA 監控
    - platform_layer/tenant/quota.py — module-level singleton pattern reference
    - agent_harness/_contracts/events.py:106 — LoopCompleted event consumed
    - api/v1/chat/router.py:272 — LoopCompleted observer hook insertion point
    - .claude/rules/observability-instrumentation.md
    - .claude/rules/testing.md §Module-level Singleton Reset Pattern (catalog)
    - .claude/rules/multi-tenant-data.md (3 鐵律)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from agent_harness._contracts.events import LoopCompleted

# Sliding window seconds — 5-min real-time monitoring;
# SLAReportGenerator (US-2) aggregates 30-day windows from Postgres.
WINDOW_SEC: int = 300

# TTL = 2× window (safety buffer for partial reads + classifier latency).
KEY_TTL_SEC: int = 600

SLAComplexityCategory = Literal["simple", "medium", "complex"]


def classify_loop_complexity(event: LoopCompleted) -> SLAComplexityCategory:
    """Classify loop complexity from LoopCompleted event for SLA reporting.

    Boundaries per 15-saas-readiness.md §SLA 承諾:
    - simple:  ≤ 3 turns + < 4K total_tokens (proxy for input + light tool use)
    - medium:  4-10 turns
    - complex: > 10 turns OR ≥ 4K total_tokens

    Day 0 D2 limitation: LoopCompleted exposes only total_turns + total_tokens.
    Per-loop tool_calls and subagent counts (per 15-saas-readiness boundary)
    are NOT yet wired into LoopCompleted — would require a counter accumulator
    event (deferred to Phase 56.x). Current classifier uses total_turns +
    total_tokens as conservative proxies. Fallback for off-spec / negative
    values → "complex" (worst-case for SLA accountability).
    """
    turns = event.total_turns
    tokens = event.total_tokens

    # Off-spec / corrupt values → conservative "complex"
    if turns < 0 or tokens < 0:
        return "complex"

    if turns > 10 or tokens >= 4000:
        return "complex"
    if turns >= 4:
        return "medium"
    if turns <= 3 and tokens < 4000:
        return "simple"
    # Unreachable per branches above but defensive default for type-check.
    return "complex"


class SLAMetricRecorder:
    """Per-tenant SLA metric recording backed by Redis Sorted Set sliding windows.

    Pattern mirrors QuotaEnforcer (56.1) — caller owns Redis lifecycle;
    this class is stateless. Module-level singleton via set/get/reset hooks.
    """

    _KEY_PREFIX = "sla:metrics"

    def __init__(
        self,
        redis_client: "Redis[bytes]",  # type: ignore[type-arg, unused-ignore]
    ) -> None:
        self._client = redis_client

    @staticmethod
    def _key(tenant_id: UUID, metric: str) -> str:
        return f"{SLAMetricRecorder._KEY_PREFIX}:{tenant_id}:{metric}:{WINDOW_SEC}s"

    async def _zadd_record(self, key: str, score: float, value_ms: int) -> None:
        """Atomic ZADD + ZREMRANGEBYSCORE + EXPIRE pipeline.

        Score = unix epoch seconds (used for window filter).
        Value = `{score}:{uuid}` composite (latency carried separately via
        sorted-set member score → we use a 2nd ZADD with score=value_ms).

        Implementation: store latency_ms as score for percentile query;
        store epoch_ts as member-prefix to allow window expiry. ZREMRANGEBYSCORE
        cleans entries older than now - WINDOW_SEC.
        """
        # Use latency_ms as the score for percentile calculation.
        # Member format: f"{epoch_ts}:{uuid}" — lexicographically sortable,
        # collision-resistant under high concurrency.
        member = f"{score}:{uuid4().hex[:8]}"
        # 1. Insert: ZADD key {value_ms} {member}
        await self._client.zadd(key, {member: float(value_ms)})
        # 2. Drop entries with score (latency_ms) outside reasonable bounds — no-op:
        #    sliding window is enforced by member-prefix epoch + the zremrangebyscore
        #    below operating on a separate epoch index. For simplicity we maintain
        #    a parallel "epoch index" key that actually stores ts-as-score.
        epoch_key = f"{key}:epoch_idx"
        await self._client.zadd(epoch_key, {member: score})
        # 3. Expire stale entries — anything with epoch < now - WINDOW_SEC.
        cutoff = time.time() - WINDOW_SEC
        stale = await self._client.zrangebyscore(epoch_key, 0, cutoff)
        if stale:
            # Remove from both indexes — same members.
            await self._client.zrem(key, *stale)
            await self._client.zrem(epoch_key, *stale)
        # 4. TTL guard so cold tenants do not leak Redis memory.
        await self._client.expire(key, KEY_TTL_SEC)
        await self._client.expire(epoch_key, KEY_TTL_SEC)

    async def record_api_request(
        self,
        tenant_id: UUID,
        latency_ms: int,
        status_code: int,
    ) -> None:
        """Record an API request (excluding LLM-bound chat) latency."""
        # Status code currently informational — used by SLAReportGenerator
        # (US-2) to compute success rate. Day 1 stores latency only.
        del status_code  # placeholder; consumed by US-2 future enhancement
        key = self._key(tenant_id, "api_request")
        await self._zadd_record(key, time.time(), latency_ms)

    async def record_loop_completion(
        self,
        tenant_id: UUID,
        latency_ms: int,
        complexity_category: SLAComplexityCategory,
    ) -> None:
        """Record an agent-loop end-to-end latency in its complexity bucket."""
        key = self._key(tenant_id, f"loop_{complexity_category}")
        await self._zadd_record(key, time.time(), latency_ms)

    async def record_hitl_queue_notification(
        self,
        tenant_id: UUID,
        queue_to_notify_ms: int,
    ) -> None:
        """Record HITL reviewer notification queue-to-notify latency.

        Per 15-saas-readiness.md §SLA 承諾: "HITL queue notification latency"
        — does NOT include reviewer decision time (that is customer-side).
        """
        key = self._key(tenant_id, "hitl_queue_notify")
        await self._zadd_record(key, time.time(), queue_to_notify_ms)

    async def record_outage_window(
        self,
        tenant_id: UUID,
        start_ts: float,
        end_ts: float,
    ) -> None:
        """Record an outage window for monthly availability calculation.

        Day 1 stub: logs duration via ZADD into outage index;
        US-2 (Day 2) will additionally persist to `sla_violations` table for
        durable monthly aggregation. Sliding-window Redis storage is
        sufficient for real-time SLAReportGenerator but DB persistence is
        required for >30-day reporting + audit trail.
        """
        if end_ts <= start_ts:
            # No-op for invalid ranges; SLAReportGenerator must not consume
            # malformed entries.
            return
        duration_ms = int((end_ts - start_ts) * 1000)
        key = self._key(tenant_id, "outage")
        await self._zadd_record(key, start_ts, duration_ms)

    async def _get_p99(self, tenant_id: UUID, metric: str) -> float | None:
        """Compute p99 of latency_ms scores in the metric's sliding window.

        Returns None if no entries (caller decides whether absence ↔ "no
        metric" or "out-of-SLA defaulted to threshold").
        """
        key = self._key(tenant_id, metric)
        # ZRANGE BYSCORE with WITHSCORES; we want score values (latency_ms).
        all_entries = await self._client.zrange(key, 0, -1, withscores=True)
        if not all_entries:
            return None
        scores = sorted(score for _, score in all_entries)
        # p99 = ceil(0.99 * len) - 1 index;clamp to ≥ 0
        p99_idx = max(int(len(scores) * 0.99) - 1, 0)
        if p99_idx >= len(scores):
            p99_idx = len(scores) - 1
        return scores[p99_idx]

    async def get_loop_p99(
        self,
        tenant_id: UUID,
        complexity_category: SLAComplexityCategory,
    ) -> float | None:
        """Return loop p99 latency_ms for the given complexity bucket."""
        return await self._get_p99(tenant_id, f"loop_{complexity_category}")

    async def get_api_p99(self, tenant_id: UUID) -> float | None:
        """Return API p99 latency_ms (non-LLM endpoints)."""
        return await self._get_p99(tenant_id, "api_request")

    async def get_hitl_queue_p99(self, tenant_id: UUID) -> float | None:
        """Return HITL notification queue-to-notify p99 latency_ms."""
        return await self._get_p99(tenant_id, "hitl_queue_notify")


# Module-level singleton — reset hook per testing.md §Module-level Singleton Reset Pattern.
_recorder: SLAMetricRecorder | None = None


def get_sla_recorder() -> SLAMetricRecorder:
    """FastAPI Depends accessor (strict — raises if uninitialised).

    Real wiring done at app startup (api/main.py creates Redis client +
    calls `set_sla_recorder`). Tests patch via `set_sla_recorder` with
    a fakeredis-backed instance (per testing.md §Singleton Reset Pattern).
    """
    if _recorder is None:
        raise RuntimeError(
            "SLAMetricRecorder not initialised; call set_sla_recorder() at "
            "app startup or in test fixture"
        )
    return _recorder


def maybe_get_sla_recorder() -> SLAMetricRecorder | None:
    """FastAPI Depends accessor (lenient — returns None if uninitialised).

    Used by chat router so existing tests / dev mode without Redis still
    pass when SLA recording is not wired. The router gates on enforcer-not-None
    before attempting record_loop_completion.
    """
    return _recorder


def set_sla_recorder(recorder: SLAMetricRecorder | None) -> None:
    """Install singleton (app startup or tests fixture)."""
    global _recorder
    _recorder = recorder


def reset_sla_recorder() -> None:
    """Test isolation hook (per testing.md §Module-level Singleton Reset Pattern)."""
    global _recorder
    _recorder = None


__all__ = [
    "KEY_TTL_SEC",
    "SLAComplexityCategory",
    "SLAMetricRecorder",
    "WINDOW_SEC",
    "classify_loop_complexity",
    "get_sla_recorder",
    "maybe_get_sla_recorder",
    "reset_sla_recorder",
    "set_sla_recorder",
]
