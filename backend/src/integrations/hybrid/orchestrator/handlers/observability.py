# =============================================================================
# IPA Platform - Observability Handler
# =============================================================================
# Sprint 132: Encapsulates metrics recording and audit logging extracted
#   from HybridOrchestratorV2.
# =============================================================================

import logging
from typing import Any, Dict, Optional

from src.integrations.hybrid.intent import ExecutionMode
from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
)

logger = logging.getLogger(__name__)


class ObservabilityHandler(Handler):
    """Handles metrics recording and audit logging.

    Encapsulates OrchestratorMetrics for:
    - Recording execution metrics (mode, framework, success, duration)
    - Providing metrics export
    - Metrics reset
    """

    def __init__(self, *, metrics: Optional[Any] = None):
        # Import here to avoid circular dependency at module level
        from src.integrations.hybrid.orchestrator_v2 import OrchestratorMetrics

        self._metrics = metrics or OrchestratorMetrics()

    @property
    def handler_type(self) -> HandlerType:
        return HandlerType.OBSERVABILITY

    @property
    def metrics(self) -> Any:
        """Get the underlying metrics instance."""
        return self._metrics

    async def handle(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Record execution metrics from the pipeline context."""
        try:
            mode = context.get("execution_mode", ExecutionMode.CHAT_MODE)
            if isinstance(mode, str):
                mode = ExecutionMode(mode)

            framework = context.get("framework_used", "unknown")
            success = context.get("execution_success", True)
            duration = context.get("execution_duration", 0.0)

            self._metrics.record_execution(
                mode=mode,
                framework=framework,
                success=success,
                duration=duration,
            )

            return HandlerResult(
                success=True,
                handler_type=HandlerType.OBSERVABILITY,
                data={
                    "recorded": True,
                    "execution_count": self._metrics.execution_count,
                },
            )
        except Exception as e:
            logger.warning(f"ObservabilityHandler: Failed to record metrics: {e}")
            return HandlerResult(
                success=True,
                handler_type=HandlerType.OBSERVABILITY,
                data={"recorded": False, "error": str(e)},
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Export current metrics."""
        return self._metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics.reset()
