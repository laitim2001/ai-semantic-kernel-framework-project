"""
PipelineExecutionPersistenceService — Non-blocking persistence of pipeline runs.

Translates PipelineContext into an OrchestrationExecutionLog ORM record.
Uses DatabaseSession() (standalone context manager) for background writes
that outlive the HTTP request lifecycle.

Sprint 169 — Phase 47: Pipeline execution persistence.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PipelineExecutionPersistenceService:
    """Persist pipeline execution context to PostgreSQL.

    All methods are defensive (never raise) so the SSE stream is unaffected.
    """

    async def save(
        self,
        context: Any,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> Optional[str]:
        """Persist a PipelineContext to the database.

        Args:
            context: PipelineContext from the completed pipeline run.
            status: Execution outcome (completed/failed/paused_hitl/paused_dialog).
            error: Error message if status is failed.

        Returns:
            Record UUID string, or None on failure.
        """
        try:
            from src.infrastructure.database.session import get_session_factory
            from src.infrastructure.database.repositories.orchestration_execution_log import (
                OrchestrationExecutionLogRepository,
            )

            session_factory = get_session_factory()
            async with session_factory() as session:
                async with session.begin():
                    repo = OrchestrationExecutionLogRepository(session)

                    # Dedup check — prevent double-writes on SSE retry
                    request_id = getattr(context, "request_id", None) or ""
                    if request_id:
                        existing = await repo.get_by_request_id(request_id)
                        if existing:
                            logger.debug(
                                "Pipeline execution already persisted: %s", existing.id
                            )
                            return str(existing.id)

                    record = await repo.create(
                        request_id=request_id,
                        session_id=getattr(context, "session_id", ""),
                        user_id=getattr(context, "user_id", "default-user"),
                        user_input=getattr(context, "task", ""),
                        routing_decision=self._serialize_obj(
                            getattr(context, "routing_decision", None)
                        ),
                        risk_assessment=self._serialize_obj(
                            getattr(context, "risk_assessment", None)
                        ),
                        completeness_info=self._serialize_completeness(
                            getattr(context, "completeness_info", None)
                        ),
                        selected_route=getattr(context, "selected_route", None),
                        route_reasoning=getattr(context, "route_reasoning", None),
                        pipeline_steps=self._build_pipeline_steps(context),
                        agent_events=self._extract_agent_events(context),
                        final_response=self._extract_final_response(context),
                        dispatch_result=self._serialize_obj(
                            getattr(context, "dispatch_result", None)
                        ),
                        status=status,
                        error=error,
                        started_at=self._get_started_at(context),
                        completed_at=datetime.now(tz=timezone.utc),
                        total_ms=round(getattr(context, "elapsed_ms", 0), 1),
                        fast_path_applied=getattr(context, "fast_path_applied", False),
                    )

                    logger.info(
                        "Pipeline execution persisted: id=%s, session=%s, route=%s, status=%s",
                        record.id,
                        record.session_id,
                        record.selected_route,
                        record.status,
                    )
                    return str(record.id)

        except Exception as e:
            logger.warning(
                "Pipeline persistence failed (non-blocking): %s", str(e)[:200]
            )
            return None

    @staticmethod
    def _serialize_obj(obj: Any) -> Optional[Dict[str, Any]]:
        """Safely serialize an object to a JSON-compatible dict."""
        if obj is None:
            return None
        if hasattr(obj, "to_dict"):
            try:
                return obj.to_dict()
            except Exception:
                pass
        if isinstance(obj, dict):
            return obj
        # Last resort: string representation
        return {"_raw": str(obj)[:500]}

    @staticmethod
    def _serialize_completeness(ci: Any) -> Optional[Dict[str, Any]]:
        """Serialize CompletenessInfo to a dict."""
        if ci is None:
            return None
        return {
            "is_complete": getattr(ci, "is_complete", True),
            "completeness_score": getattr(ci, "completeness_score", 1.0),
            "missing_fields": list(getattr(ci, "missing_fields", [])),
        }

    @staticmethod
    def _build_pipeline_steps(context: Any) -> Dict[str, Any]:
        """Build pipeline steps summary from context."""
        steps: Dict[str, Any] = {}
        completed = getattr(context, "completed_steps", [])
        latencies = getattr(context, "step_latencies", {})

        for step_name in completed:
            step_data: Dict[str, Any] = {
                "status": "completed",
                "latency_ms": latencies.get(step_name, 0),
            }

            # Attach per-step metadata from context so the UI history panel
            # can render the same detail it shows during a live run.
            if step_name == "memory_read":
                mm = getattr(context, "memory_metadata", None)
                if mm:
                    step_data["metadata"] = mm
            elif step_name == "knowledge_search":
                km = getattr(context, "knowledge_metadata", None)
                if km:
                    step_data["metadata"] = km

            steps[step_name] = step_data
        return steps

    @staticmethod
    def _extract_final_response(context: Any) -> Optional[str]:
        """Extract final response text from dispatch result."""
        dr = getattr(context, "dispatch_result", None)
        if dr is None:
            return None
        return getattr(dr, "response_text", None)

    @staticmethod
    def _extract_agent_events(context: Any) -> Optional[List[Any]]:
        """Extract agent events from dispatch result."""
        dr = getattr(context, "dispatch_result", None)
        if dr is None:
            return None

        # Try agent_results first (SubagentExecutor / TeamExecutor)
        agent_results = getattr(dr, "agent_results", None)
        if agent_results:
            events = []
            for r in agent_results:
                events.append({
                    "agent_name": getattr(r, "agent_name", "unknown"),
                    "role": getattr(r, "role", ""),
                    "status": getattr(r, "status", ""),
                    "output": (getattr(r, "output", "") or "")[:500],
                    "duration_ms": getattr(r, "duration_ms", 0),
                })
            return events

        return None

    @staticmethod
    def _get_started_at(context: Any) -> Optional[datetime]:
        """Extract pipeline start time from context."""
        start_time = getattr(context, "total_start_time", None)
        if start_time is not None:
            try:
                return datetime.fromtimestamp(start_time, tz=timezone.utc)
            except (OSError, ValueError):
                pass
        return None
