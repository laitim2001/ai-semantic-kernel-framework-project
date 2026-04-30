"""platform_layer.observability — process-wide OTel SDK init + JSON logger.

Single-source map:
- setup_opentelemetry / shutdown_opentelemetry: setup.py
- get_json_logger / configure_json_logging: logger.py
- PIIRedactor: logger.py
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

__all__ = [
    "PIIRedactor",
    "configure_json_logging",
    "get_json_logger",
    "setup_opentelemetry",
    "shutdown_opentelemetry",
]
