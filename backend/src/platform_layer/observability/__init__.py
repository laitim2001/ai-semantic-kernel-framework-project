"""platform_layer.observability — OTel SDK init + JSON logger + Tracer + SLA recorder.

Single-source map:
- setup_opentelemetry / shutdown_opentelemetry: setup.py
- get_json_logger / configure_json_logging: logger.py
- PIIRedactor: logger.py
- get_tracer: tracer.py (Sprint 56.2 — closes AD-Cat12-BusinessObs)
- SLAMetricRecorder + classify_loop_complexity + get/set/reset: sla_monitor.py (Sprint 56.3 US-1)
"""

from platform_layer.observability.logger import (
    PIIRedactor,
    configure_json_logging,
    get_json_logger,
)
from platform_layer.observability.setup import (
    setup_opentelemetry,
    shutdown_opentelemetry,
)
from platform_layer.observability.sla_monitor import (
    SLAComplexityCategory,
    SLAMetricRecorder,
    classify_loop_complexity,
    get_sla_recorder,
    maybe_get_sla_recorder,
    reset_sla_recorder,
    set_sla_recorder,
)
from platform_layer.observability.tracer import get_tracer

__all__ = [
    "PIIRedactor",
    "SLAComplexityCategory",
    "SLAMetricRecorder",
    "classify_loop_complexity",
    "configure_json_logging",
    "get_json_logger",
    "get_sla_recorder",
    "get_tracer",
    "maybe_get_sla_recorder",
    "reset_sla_recorder",
    "set_sla_recorder",
    "setup_opentelemetry",
    "shutdown_opentelemetry",
]
