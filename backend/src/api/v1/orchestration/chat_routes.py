"""
Chat Routes — Production SSE streaming endpoint for orchestration pipeline.

Replaces PoC /poc/agent-team/test-orchestrator with a proper production
endpoint at /orchestration/chat.

Endpoints:
    POST /orchestration/chat          — SSE stream of pipeline execution
    POST /orchestration/chat/resume   — Resume paused pipeline
    POST /orchestration/chat/dialog-respond — Respond to dialog questions
    GET  /orchestration/chat/session/{session_id} — Get session status

Phase 45: Orchestration Core (Sprint 156)
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .chat_schemas import (
    ChatRequest,
    DialogRespondRequest,
    ResumeRequest,
    SessionStatusResponse,
)

logger = logging.getLogger(__name__)

chat_router = APIRouter(
    prefix="/orchestration/chat",
    tags=["Orchestration Chat (Phase 45)"],
)


async def _sse_generator(
    event_queue: asyncio.Queue,
    timeout: float = 300.0,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from an asyncio queue.

    Yields SSE-formatted strings until PIPELINE_COMPLETE or PIPELINE_ERROR
    or timeout.

    Args:
        event_queue: Queue of PipelineEvent objects.
        timeout: Maximum seconds to wait for events.
    """
    try:
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                yield f"event: PIPELINE_ERROR\ndata: {json.dumps({'error': 'Pipeline timeout'})}\n\n"
                break

            sse_data = event.to_sse()
            yield f"event: {sse_data['event']}\ndata: {json.dumps(sse_data['data'])}\n\n"

            # Terminal events — only stop on truly final events
            is_final_complete = (
                sse_data["event"] == "PIPELINE_COMPLETE"
                and sse_data["data"].get("final", False)
            )
            if is_final_complete or sse_data["event"] in (
                "PIPELINE_ERROR",
                "HITL_REQUIRED",
                "DIALOG_REQUIRED",
            ):
                break
    except asyncio.CancelledError:
        yield f"event: PIPELINE_ERROR\ndata: {json.dumps({'error': 'Connection cancelled'})}\n\n"


@chat_router.post("")
async def chat_stream(request: ChatRequest):
    """Execute the 8-step orchestration pipeline with SSE streaming.

    Returns a Server-Sent Events stream with pipeline progress events.
    The stream ends when the pipeline completes, pauses (HITL/Dialog),
    or encounters an error.

    SSE Event Types:
        PIPELINE_START, STEP_START, STEP_COMPLETE,
        ROUTING_COMPLETE, LLM_ROUTE_DECISION,
        DISPATCH_START, AGENT_THINKING, AGENT_COMPLETE, TEXT_DELTA,
        DIALOG_REQUIRED, HITL_REQUIRED,
        PIPELINE_COMPLETE, PIPELINE_ERROR
    """
    from src.integrations.orchestration.dispatch.models import (
        DispatchRequest,
        ExecutionRoute,
    )
    from src.integrations.orchestration.dispatch.service import DispatchService
    from src.integrations.orchestration.pipeline.context import PipelineContext
    from src.integrations.orchestration.pipeline.service import (
        PipelineEvent,
        PipelineEventType,
        create_default_pipeline,
    )
    from src.integrations.orchestration.pipeline.steps.step3_intent import IntentStep
    from src.integrations.orchestration.pipeline.steps.step4_risk import RiskStep
    from src.integrations.orchestration.pipeline.steps.step5_hitl import HITLGateStep
    from src.integrations.orchestration.pipeline.steps.step6_llm_route import (
        LLMRouteStep,
    )
    from src.integrations.orchestration.pipeline.steps.step8_postprocess import (
        PostProcessStep,
    )

    start_from_step = 0

    # Checkpoint resume: load state from Redis and continue from paused step
    if request.checkpoint_id:
        try:
            from src.integrations.agent_framework.ipa_checkpoint_storage import (
                IPACheckpointStorage,
            )

            storage = IPACheckpointStorage(user_id=request.user_id)
            checkpoint = await storage.load(request.checkpoint_id)
            context = PipelineContext.from_checkpoint_state(checkpoint.state)
            start_from_step = checkpoint.iteration_count + 1  # Next step after pause
            session_id = context.session_id

            logger.info(
                "Checkpoint resume: checkpoint=%s, session=%s, start_from=%d",
                request.checkpoint_id,
                session_id,
                start_from_step,
            )
        except Exception as e:
            logger.warning(
                "Checkpoint resume failed, falling back to full run: %s",
                str(e)[:100],
            )
            session_id = request.session_id or str(uuid.uuid4())
            context = PipelineContext(
                user_id=request.user_id,
                session_id=session_id,
                task=request.task,
                hitl_pre_approved=request.hitl_pre_approved,
            )
    else:
        session_id = request.session_id or str(uuid.uuid4())
        context = PipelineContext(
            user_id=request.user_id,
            session_id=session_id,
            task=request.task,
            hitl_pre_approved=request.hitl_pre_approved,
        )

    # Build full pipeline with all 8 steps
    pipeline = create_default_pipeline()
    pipeline.configure_steps([
        *pipeline._steps,  # Steps 1-2 from factory
        IntentStep(),       # Step 3
        RiskStep(),         # Step 4
        HITLGateStep(),     # Step 5
        LLMRouteStep(),     # Step 6
        PostProcessStep(),  # Step 8
    ])

    event_queue: asyncio.Queue = asyncio.Queue()

    async def _run_pipeline():
        """Run pipeline and dispatch in background."""
        try:
            result_ctx = await pipeline.run(
                context, event_queue=event_queue, start_from_step=start_from_step
            )

            # If pipeline completed without pause, run dispatch
            if not result_ctx.is_paused and result_ctx.selected_route:
                dispatch_svc = DispatchService()
                dispatch_req = DispatchRequest(
                    route=ExecutionRoute.from_string(result_ctx.selected_route),
                    task=result_ctx.task,
                    user_id=result_ctx.user_id,
                    session_id=result_ctx.session_id,
                    memory_text=result_ctx.memory_text,
                    knowledge_text=result_ctx.knowledge_text,
                    intent_summary=(
                        f"{result_ctx.routing_decision.intent_category.value}: "
                        f"{result_ctx.routing_decision.sub_intent}"
                        if result_ctx.routing_decision
                        else ""
                    ),
                    risk_level=(
                        result_ctx.risk_assessment.level.value
                        if result_ctx.risk_assessment
                        and hasattr(result_ctx.risk_assessment.level, "value")
                        else "low"
                    ),
                    route_reasoning=result_ctx.route_reasoning or "",
                )
                dispatch_result = await dispatch_svc.dispatch(
                    dispatch_req, event_queue=event_queue
                )
                result_ctx.dispatch_result = dispatch_result

                # Emit response text as TEXT_DELTA so frontend chat shows it
                response_text = dispatch_result.response_text or ""
                if response_text:
                    await event_queue.put(
                        PipelineEvent(
                            PipelineEventType.TEXT_DELTA,
                            {"content": response_text},
                            step_name="dispatch",
                        )
                    )

                # Run post-process step manually (Step 8)
                post_step = PostProcessStep()
                await post_step.execute(result_ctx)

                # Emit final pipeline complete (final=true stops SSE stream)
                await event_queue.put(
                    PipelineEvent(
                        PipelineEventType.PIPELINE_COMPLETE,
                        {
                            "session_id": session_id,
                            "selected_route": result_ctx.selected_route,
                            "total_ms": round(result_ctx.elapsed_ms, 1),
                            "completed_steps": result_ctx.completed_steps,
                            "checkpoint_id": result_ctx.checkpoint_id,
                            "final": True,
                        },
                    )
                )

        except Exception as e:
            logger.error("Pipeline execution failed: %s", str(e)[:200], exc_info=True)
            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.PIPELINE_ERROR,
                    {"error": str(e)[:200], "recoverable": False},
                )
            )

    # Start pipeline in background task
    asyncio.create_task(_run_pipeline())

    return StreamingResponse(
        _sse_generator(event_queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )


@chat_router.post("/resume")
async def chat_resume(request: ResumeRequest):
    """Resume a paused pipeline from checkpoint.

    Supports 3 resume scenarios:
        1. HITL approval/rejection
        2. Route override (re-route)
        3. Agent retry
    """
    try:
        from src.integrations.orchestration.resume.service import ResumeService

        resume_svc = ResumeService()

        resume_request = {
            "checkpoint_id": request.checkpoint_id,
            "user_id": request.user_id,
        }

        if request.approval_status:
            resume_request["approval_result"] = {
                "status": request.approval_status,
                "approver": request.approval_approver or "unknown",
            }

        if request.override_route:
            resume_request["overrides"] = {"route": request.override_route}

        if request.retry_agents:
            resume_request["retry_agents"] = request.retry_agents

        result = await resume_svc.resume(**resume_request)

        return {
            "status": result.status if hasattr(result, "status") else "ok",
            "resume_type": result.resume_type if hasattr(result, "resume_type") else "unknown",
            "resumed_from_step": result.resumed_from_step if hasattr(result, "resumed_from_step") else 0,
            "session_id": request.checkpoint_id,
        }

    except Exception as e:
        logger.error("Resume failed: %s", str(e)[:200])
        raise HTTPException(status_code=500, detail=f"Resume failed: {str(e)[:200]}")


@chat_router.post("/dialog-respond")
async def dialog_respond(request: DialogRespondRequest):
    """Submit user responses to guided dialog questions.

    After receiving DIALOG_REQUIRED event, the frontend collects
    user answers and submits them here. The pipeline resumes from
    Step 3 (intent analysis) with the additional information.
    """
    try:
        from src.integrations.orchestration.resume.service import ResumeService

        resume_svc = ResumeService()
        result = await resume_svc.resume(
            checkpoint_id=request.checkpoint_id,
            user_id=request.user_id,
            overrides={
                "dialog_responses": request.responses,
                "dialog_id": request.dialog_id,
            },
        )

        return {
            "status": result.status if hasattr(result, "status") else "ok",
            "resume_type": "dialog_continue",
            "session_id": request.checkpoint_id,
        }

    except Exception as e:
        logger.error("Dialog respond failed: %s", str(e)[:200])
        raise HTTPException(
            status_code=500, detail=f"Dialog respond failed: {str(e)[:200]}"
        )


@chat_router.get("/session/{session_id}")
async def get_session_status(session_id: str, user_id: str = "default-user"):
    """Get the current status of a pipeline session.

    Returns completed steps, pause status, selected route, etc.
    """
    try:
        from src.integrations.orchestration.transcript.service import TranscriptService

        transcript = TranscriptService()
        entries = await transcript.read(user_id=user_id, session_id=session_id)

        if not entries:
            raise HTTPException(status_code=404, detail="Session not found")

        completed_steps = [e.step_name for e in entries if e.entry_type == "step_complete"]
        paused_entries = [e for e in entries if e.entry_type in ("approval_required", "dialog_required")]

        status = "completed"
        paused_at = None
        if paused_entries:
            last_pause = paused_entries[-1]
            status = f"paused_{last_pause.entry_type.replace('_required', '')}"
            paused_at = last_pause.entry_type.replace("_required", "")

        # Find route decision
        route_entries = [e for e in entries if e.step_name == "llm_route_decision"]
        selected_route = None
        if route_entries:
            selected_route = route_entries[-1].output_summary.get("selected_route")

        return SessionStatusResponse(
            session_id=session_id,
            user_id=user_id,
            status=status,
            selected_route=selected_route,
            completed_steps=completed_steps,
            paused_at=paused_at,
            checkpoint_id=entries[-1].checkpoint_id if entries else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get session status failed: %s", str(e)[:200])
        raise HTTPException(
            status_code=500, detail=f"Failed to get session: {str(e)[:200]}"
        )
