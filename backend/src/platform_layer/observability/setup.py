"""
File: backend/src/platform_layer/observability/setup.py
Purpose: One-shot OTel SDK init — TracerProvider + MeterProvider + auto-instrumentations.
Category: Platform / Observability (range cat 12 — process boundary)
Scope: Phase 49 / Sprint 49.4 Day 3

Description:
    Called once at FastAPI app startup (Phase 49.4 Day 5 lifespan event):

        from platform_layer.observability import setup_opentelemetry
        setup_opentelemetry(app)

    Wires:
    - TracerProvider (OTLP/gRPC → Jaeger on :4317)
    - MeterProvider (Prometheus reader → /metrics endpoint)
    - FastAPI auto-instrumentation (HTTP requests/responses)
    - SQLAlchemy auto-instrumentation (DB query spans)
    - Redis auto-instrumentation (cache spans)

    Idempotent: setup_opentelemetry() can be called twice safely (second call
    is a no-op). Tests should NOT call this; they use NoOpTracer directly.

Created: 2026-04-29 (Sprint 49.4 Day 3)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4 Day 3)

Related:
    - agent_harness/observability/exporter.py — provider builders
    - agent_harness/observability/tracer.py — OTelTracer (consumer)
    - .claude/rules/observability-instrumentation.md
"""

from __future__ import annotations

import logging
import os
from typing import Any

from agent_harness.observability.exporter import OTelExporterConfig

logger = logging.getLogger(__name__)


_INITIALIZED = False


def _build_config() -> OTelExporterConfig:
    """Read env vars; fall back to dev defaults."""
    return OTelExporterConfig(
        service_name=os.environ.get("OTEL_SERVICE_NAME", "ipa-v2-backend"),
        otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        otlp_insecure=os.environ.get("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true",
        enable_console_export=os.environ.get("OTEL_CONSOLE_EXPORT", "false").lower() == "true",
    )


def setup_opentelemetry(fastapi_app: Any | None = None) -> None:
    """Idempotent OTel SDK init. Safe to call multiple times.

    Args:
        fastapi_app: optional FastAPI app to auto-instrument. If None, only
                     SDK providers are registered (no HTTP middleware).
    """
    global _INITIALIZED
    if _INITIALIZED:
        logger.debug("setup_opentelemetry already initialized; skipping")
        return

    config = _build_config()

    # Lazy SDK imports to keep test paths free of OTel SDK overhead.
    from opentelemetry import metrics as ot_metrics
    from opentelemetry import trace as ot_trace

    from agent_harness.observability.exporter import (
        build_meter_provider,
        build_tracer_provider,
    )

    tracer_provider = build_tracer_provider(config)
    meter_provider = build_meter_provider(config)
    ot_trace.set_tracer_provider(tracer_provider)
    ot_metrics.set_meter_provider(meter_provider)
    logger.info(
        "OTel SDK initialized: service=%s otlp=%s",
        config.service_name,
        config.otlp_endpoint,
    )

    if fastapi_app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(fastapi_app)
            logger.info("FastAPI auto-instrumentation enabled")
        except Exception:  # noqa: BLE001
            logger.exception("FastAPI auto-instrumentation failed (non-fatal)")

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy auto-instrumentation enabled")
    except Exception:  # noqa: BLE001
        logger.exception("SQLAlchemy auto-instrumentation failed (non-fatal)")

    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
        logger.info("Redis auto-instrumentation enabled")
    except Exception:  # noqa: BLE001
        logger.exception("Redis auto-instrumentation failed (non-fatal)")

    _INITIALIZED = True


async def shutdown_opentelemetry() -> None:
    """Flush + close OTel SDK providers. Call from FastAPI lifespan shutdown.

    Best-effort: any errors are logged but do not raise (don't block shutdown).
    """
    global _INITIALIZED
    if not _INITIALIZED:
        return

    try:
        from opentelemetry import trace as ot_trace

        provider = ot_trace.get_tracer_provider()
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            shutdown()
    except Exception:  # noqa: BLE001
        logger.exception("OTel tracer shutdown failed (non-fatal)")

    try:
        from opentelemetry import metrics as ot_metrics

        meter_provider = ot_metrics.get_meter_provider()
        meter_shutdown = getattr(meter_provider, "shutdown", None)
        if callable(meter_shutdown):
            meter_shutdown()
    except Exception:  # noqa: BLE001
        logger.exception("OTel meter shutdown failed (non-fatal)")

    _INITIALIZED = False
    logger.info("OTel SDK shut down")


__all__ = ["setup_opentelemetry", "shutdown_opentelemetry"]
