"""SLAReportGenerator tests (Sprint 56.3 Day 2 / US-2)."""

from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.sla import SLAReport, SLAViolation
from platform_layer.observability.sla_monitor import (
    SLAMetricRecorder,
    SLAReportGenerator,
)
from tests.conftest import seed_tenant


@pytest.fixture
async def fake_redis():  # type: ignore[no-untyped-def]
    client = FakeRedis(decode_responses=False)
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_generate_monthly_report_persists_row(
    db_session: AsyncSession,
    fake_redis: FakeRedis,
) -> None:
    """Generator persists SLAReport row in (tenant_id, month) — happy path."""
    t = await seed_tenant(db_session, code="SLA_GEN_1")
    recorder = SLAMetricRecorder(redis_client=fake_redis)
    # Seed one fast loop completion (10 ms) — well under standard threshold.
    await recorder.record_loop_completion(
        tenant_id=t.id, latency_ms=10, complexity_category="simple"
    )

    gen = SLAReportGenerator(recorder=recorder, db_session=db_session)
    report = await gen.generate_monthly_report(tenant_id=t.id, month="2026-05", plan="enterprise")
    assert report.tenant_id == t.id
    assert report.month == "2026-05"
    assert report.violations_count == 0
    assert report.loop_simple_p99_ms == 10


@pytest.mark.asyncio
async def test_generate_monthly_report_writes_violation_when_below_threshold(
    db_session: AsyncSession,
    fake_redis: FakeRedis,
) -> None:
    """If loop_simple p99 > enterprise threshold (5000 ms) → SLAViolation row written."""
    t = await seed_tenant(db_session, code="SLA_GEN_2")
    recorder = SLAMetricRecorder(redis_client=fake_redis)
    # 8000 ms exceeds enterprise threshold (5000 ms)
    await recorder.record_loop_completion(
        tenant_id=t.id, latency_ms=8_000, complexity_category="simple"
    )

    gen = SLAReportGenerator(recorder=recorder, db_session=db_session)
    report = await gen.generate_monthly_report(tenant_id=t.id, month="2026-05", plan="enterprise")
    assert report.violations_count >= 1

    violations = (
        (await db_session.execute(select(SLAViolation).where(SLAViolation.tenant_id == t.id)))
        .scalars()
        .all()
    )
    metric_types = {v.metric_type for v in violations}
    assert "loop_simple_p99" in metric_types


@pytest.mark.asyncio
async def test_generate_monthly_report_upserts_existing_row(
    db_session: AsyncSession,
    fake_redis: FakeRedis,
) -> None:
    """Re-generating the same (tenant, month) updates the row in place."""
    t = await seed_tenant(db_session, code="SLA_GEN_3")
    recorder = SLAMetricRecorder(redis_client=fake_redis)

    gen = SLAReportGenerator(recorder=recorder, db_session=db_session)
    r1 = await gen.generate_monthly_report(tenant_id=t.id, month="2026-05", plan="enterprise")
    # Add data after first generation.
    await recorder.record_loop_completion(
        tenant_id=t.id, latency_ms=42, complexity_category="medium"
    )
    r2 = await gen.generate_monthly_report(tenant_id=t.id, month="2026-05", plan="enterprise")
    # Same row id (UNIQUE constraint enforced via upsert).
    assert r1.id == r2.id
    # Updated content.
    assert r2.loop_medium_p99_ms == 42

    rows = (
        (
            await db_session.execute(
                select(SLAReport).where(
                    (SLAReport.tenant_id == t.id) & (SLAReport.month == "2026-05")
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_generate_monthly_report_no_data_no_violations(
    db_session: AsyncSession,
    fake_redis: FakeRedis,
) -> None:
    """Empty Redis sliding window → no violations recorded (None p99 skipped)."""
    t = await seed_tenant(db_session, code="SLA_GEN_4")
    recorder = SLAMetricRecorder(redis_client=fake_redis)
    gen = SLAReportGenerator(recorder=recorder, db_session=db_session)
    report = await gen.generate_monthly_report(tenant_id=t.id, month="2026-05", plan="standard")
    assert report.violations_count == 0
    # All p99 fields None (no data).
    assert report.api_p99_ms is None
    assert report.loop_simple_p99_ms is None
