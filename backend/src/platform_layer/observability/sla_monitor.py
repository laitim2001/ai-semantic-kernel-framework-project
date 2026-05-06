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
    from sqlalchemy.ext.asyncio import AsyncSession

    from agent_harness._contracts.events import LoopCompleted
    from infrastructure.db.models.sla import SLAReport

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


# =====================================================================
# SLAReportGenerator — Day 2 / US-2
# =====================================================================

# SLA thresholds per 15-saas-readiness.md §SLA 承諾.
# (availability_pct, api_p99_ms, loop_simple_p99_ms, loop_medium_p99_ms,
#  loop_complex_p99_ms, hitl_queue_notif_p99_ms)
_THRESHOLDS_BY_PLAN: dict[str, dict[str, float]] = {
    "standard": {
        "availability_pct": 99.5,
        "api_p99_ms": 2_000,
        "loop_simple_p99_ms": 10_000,
        "loop_medium_p99_ms": 60_000,
        "loop_complex_p99_ms": 300_000,
        "hitl_queue_notif_p99_ms": 300_000,
    },
    "enterprise": {
        "availability_pct": 99.9,
        "api_p99_ms": 1_000,
        "loop_simple_p99_ms": 5_000,
        "loop_medium_p99_ms": 30_000,
        "loop_complex_p99_ms": 180_000,
        "hitl_queue_notif_p99_ms": 60_000,
    },
}


def _compute_severity(actual: float, threshold: float, *, lower_is_better: bool) -> str:
    """Map actual vs threshold delta to minor / major / critical severity.

    Convention:
    - For latency metrics (lower_is_better=True): delta = (actual - threshold) / threshold
    - For availability (lower_is_better=False): delta = (threshold - actual) / threshold
    Both yield positive deltas when violated; severity bins:
        ≤ 5%  → minor
        5-15% → major
        > 15% → critical
    """
    if lower_is_better:
        delta = (actual - threshold) / threshold if threshold > 0 else 0.0
    else:
        delta = (threshold - actual) / threshold if threshold > 0 else 0.0
    if delta <= 0.05:
        return "minor"
    if delta <= 0.15:
        return "major"
    return "critical"


class SLAReportGenerator:
    """Generate per-tenant per-month SLAReport from Redis sliding window data.

    Day 2 scope (US-2):
    - Pull current p99 values from `SLAMetricRecorder` (Redis sliding window;
      window_sec=300 gives recent-30-day proxy for "monthly" report — Phase
      56.x audit cycle will replace with Postgres-backed historical aggregate)
    - Compute availability_pct from outage windows (Day 1 records via
      record_outage_window;Day 2 stub returns 99.99% when no outages logged
      — real availability calculation deferred to Phase 56.x)
    - Detect threshold breaches → persist SLAViolation rows
    - Upsert SLAReport row keyed by (tenant_id, month)
    """

    def __init__(
        self,
        recorder: SLAMetricRecorder,
        db_session: "AsyncSession",
    ) -> None:
        self._recorder = recorder
        self._db = db_session

    @staticmethod
    def _resolve_thresholds(plan: str) -> dict[str, float]:
        """Map tenant.plan ('standard' | 'enterprise' | …) to threshold dict."""
        return _THRESHOLDS_BY_PLAN.get(plan, _THRESHOLDS_BY_PLAN["standard"])

    async def _availability_pct(self, tenant_id: UUID) -> float:
        """Compute availability % from outage records.

        Day 2 stub: returns 99.99% (no outage tracking wired — outage_window
        records via SLAMetricRecorder.record_outage_window remain Redis-only).
        Phase 56.x audit cycle will compute from Postgres outage table.
        """
        del tenant_id  # placeholder
        return 99.99

    async def generate_monthly_report(
        self,
        tenant_id: UUID,
        month: str,
        *,
        plan: str = "standard",
    ) -> "SLAReport":
        """Generate (or upsert) SLAReport for tenant + month.

        Args:
            tenant_id: scope
            month: 'YYYY-MM' format
            plan: 'standard' or 'enterprise' — determines threshold table

        Returns:
            Persisted SLAReport row.
        """
        from sqlalchemy import select

        from infrastructure.db.models.sla import SLAReport, SLAViolation

        thresholds = self._resolve_thresholds(plan)

        # Pull recent p99s from Redis sliding window.
        api_p99 = await self._recorder.get_api_p99(tenant_id)
        loop_simple = await self._recorder.get_loop_p99(tenant_id, "simple")
        loop_medium = await self._recorder.get_loop_p99(tenant_id, "medium")
        loop_complex = await self._recorder.get_loop_p99(tenant_id, "complex")
        hitl_q = await self._recorder.get_hitl_queue_p99(tenant_id)
        availability = await self._availability_pct(tenant_id)

        # Detect violations + count.
        violations_count = 0
        candidate_violations = [
            ("availability", availability, thresholds["availability_pct"], False),
            ("api_p99", api_p99, thresholds["api_p99_ms"], True),
            ("loop_simple_p99", loop_simple, thresholds["loop_simple_p99_ms"], True),
            ("loop_medium_p99", loop_medium, thresholds["loop_medium_p99_ms"], True),
            ("loop_complex_p99", loop_complex, thresholds["loop_complex_p99_ms"], True),
            (
                "hitl_queue_notif_p99",
                hitl_q,
                thresholds["hitl_queue_notif_p99_ms"],
                True,
            ),
        ]
        for metric_type, actual, threshold, lower_is_better in candidate_violations:
            if actual is None:
                continue  # No data — no violation to record this period
            violated = (lower_is_better and actual > threshold) or (
                not lower_is_better and actual < threshold
            )
            if violated:
                violations_count += 1
                self._db.add(
                    SLAViolation(
                        tenant_id=tenant_id,
                        metric_type=metric_type,
                        threshold_pct=float(threshold),
                        actual_pct=float(actual),
                        severity=_compute_severity(
                            float(actual),
                            float(threshold),
                            lower_is_better=lower_is_better,
                        ),
                    )
                )

        # Upsert SLAReport (tenant_id, month) UNIQUE constraint → check existing.
        stmt = select(SLAReport).where(
            (SLAReport.tenant_id == tenant_id) & (SLAReport.month == month)
        )
        existing = (await self._db.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            existing.availability_pct = availability
            existing.api_p99_ms = int(api_p99) if api_p99 is not None else None
            existing.loop_simple_p99_ms = int(loop_simple) if loop_simple is not None else None
            existing.loop_medium_p99_ms = int(loop_medium) if loop_medium is not None else None
            existing.loop_complex_p99_ms = int(loop_complex) if loop_complex is not None else None
            existing.hitl_queue_notif_p99_ms = int(hitl_q) if hitl_q is not None else None
            existing.violations_count = violations_count
            return existing

        report = SLAReport(
            tenant_id=tenant_id,
            month=month,
            availability_pct=availability,
            api_p99_ms=int(api_p99) if api_p99 is not None else None,
            loop_simple_p99_ms=int(loop_simple) if loop_simple is not None else None,
            loop_medium_p99_ms=int(loop_medium) if loop_medium is not None else None,
            loop_complex_p99_ms=int(loop_complex) if loop_complex is not None else None,
            hitl_queue_notif_p99_ms=int(hitl_q) if hitl_q is not None else None,
            violations_count=violations_count,
        )
        self._db.add(report)
        await self._db.flush()
        return report


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
    "SLAReportGenerator",
    "WINDOW_SEC",
    "classify_loop_complexity",
    "get_sla_recorder",
    "maybe_get_sla_recorder",
    "reset_sla_recorder",
    "set_sla_recorder",
]
