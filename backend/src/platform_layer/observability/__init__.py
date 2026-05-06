"""platform_layer.observability — process-wide OTel SDK init + JSON logger + Tracer factory.

Single-source map:
- setup_opentelemetry / shutdown_opentelemetry: setup.py
- get_json_logger / configure_json_logging: logger.py
- PIIRedactor: logger.py
- get_tracer: tracer.py (Sprint 56.2 — closes AD-Cat12-BusinessObs)
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
from platform_layer.observability.tracer import get_tracer

__all__ = [
    "PIIRedactor",
    "configure_json_logging",
    "get_json_logger",
    "get_tracer",
    "setup_opentelemetry",
    "shutdown_opentelemetry",
]
