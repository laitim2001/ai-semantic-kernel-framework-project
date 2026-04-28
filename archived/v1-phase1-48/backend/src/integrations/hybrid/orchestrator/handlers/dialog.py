# =============================================================================
# IPA Platform - Dialog Handler
# =============================================================================
# Sprint 132: Encapsulates GuidedDialogEngine logic extracted from
#   HybridOrchestratorV2._handle_guided_dialog().
# =============================================================================

import logging
from typing import Any, Dict, Optional

from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
)

logger = logging.getLogger(__name__)


class DialogHandler(Handler):
    """Handles guided dialog for missing information.

    Encapsulates GuidedDialogEngine interactions for gathering
    additional information when routing completeness is insufficient.
    """

    def __init__(self, *, guided_dialog: Optional[Any] = None):
        self._guided_dialog = guided_dialog

    @property
    def handler_type(self) -> HandlerType:
        return HandlerType.DIALOG

    def can_handle(self, request: OrchestratorRequest, context: Dict[str, Any]) -> bool:
        """Only handle when dialog is needed and engine is available."""
        return bool(
            self._guided_dialog
            and context.get("needs_dialog", False)
        )

    async def handle(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Start guided dialog for missing information.

        Returns a short-circuit result if more info is needed from the user.
        """
        if not self._guided_dialog:
            return HandlerResult(
                success=True,
                handler_type=HandlerType.DIALOG,
                data={"skipped": True, "reason": "GuidedDialogEngine not configured"},
            )

        routing_decision = context.get("routing_decision")
        if not routing_decision:
            return HandlerResult(
                success=True,
                handler_type=HandlerType.DIALOG,
                data={"skipped": True, "reason": "No routing decision available"},
            )

        try:
            logger.info("DialogHandler: Starting guided dialog for missing info")

            source_request = request.source_request
            source_type = "unknown"
            if source_request and hasattr(source_request, "source_type"):
                source_type = (
                    source_request.source_type.value
                    if hasattr(source_request.source_type, "value")
                    else str(source_request.source_type)
                )

            response = await self._guided_dialog.start_dialog(
                request.content,
                initial_context={
                    "routing_decision": routing_decision,
                    "source_type": source_type,
                    "session_id": request.session_id or "",
                },
            )

            if response.needs_more_info:
                return HandlerResult(
                    success=True,
                    handler_type=HandlerType.DIALOG,
                    should_short_circuit=True,
                    short_circuit_response={
                        "content": response.message,
                        "dialog_id": response.dialog_id,
                        "questions": [
                            q.dict() if hasattr(q, "dict") else str(q)
                            for q in (response.questions or [])
                        ],
                        "status": "pending_info",
                    },
                    data={"needs_more_info": True, "dialog_response": response},
                )

            # Dialog resolved — update routing decision if available
            if response.routing_decision:
                context["routing_decision"] = response.routing_decision

            return HandlerResult(
                success=True,
                handler_type=HandlerType.DIALOG,
                data={"resolved": True, "dialog_response": response},
            )

        except Exception as e:
            logger.error(f"DialogHandler error: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                handler_type=HandlerType.DIALOG,
                error=str(e),
            )
