# =============================================================================
# IPA Platform - Resume Service
# =============================================================================
# Orchestrates checkpoint resume across three scenarios:
#   1. HITL Approval  — Manager approves, pipeline continues from decision point
#   2. Re-Route       — User overrides the route choice, re-executes from there
#   3. Agent Retry    — Only re-run failed subagents, keep completed results
#
# This is IPA's own design — not using MAF's builder-based checkpoint restore.
# Uses MAF-compatible WorkflowCheckpoint format via IPACheckpointStorage.
# =============================================================================

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from agent_framework import WorkflowCheckpoint

from src.integrations.agent_framework.ipa_checkpoint_storage import IPACheckpointStorage
from src.integrations.orchestration.transcript import TranscriptService, TranscriptEntry

logger = logging.getLogger(__name__)


@dataclass
class ResumeRequest:
    """Request to resume from a checkpoint."""
    checkpoint_id: str
    user_id: str
    # Scenario 1: HITL approval
    approval_result: Optional[dict] = None   # {"status": "approved", "approver": "manager-1"}
    # Scenario 2: Agent retry
    retry_agents: Optional[list[str]] = None
    reuse_completed: bool = True
    # Scenario 3: Re-route override
    overrides: Optional[dict] = None         # {"route": "team"}


@dataclass
class ResumeResult:
    """Result of a resume operation."""
    status: str                 # "ok" | "error" | "rejected"
    resume_type: str            # "hitl" | "reroute" | "agent_retry"
    resumed_from_step: int
    checkpoint_id: str
    session_id: str
    original_route: Optional[str] = None
    new_route: Optional[str] = None
    steps_executed: list[dict] = field(default_factory=list)
    orchestrator_response: str = ""
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class ResumeService:
    """Orchestrates checkpoint resume for IPA orchestrator pipeline."""

    def __init__(
        self,
        checkpoint_storage: IPACheckpointStorage,
        transcript_service: TranscriptService,
    ):
        self._storage = checkpoint_storage
        self._transcript = transcript_service

    async def resume(self, request: ResumeRequest) -> ResumeResult:
        """Resume execution from a checkpoint.

        Determines the resume scenario from the request parameters,
        loads the checkpoint, validates it, and dispatches to the
        appropriate handler.
        """
        # Load checkpoint
        try:
            checkpoint = await self._storage.load(request.checkpoint_id)
        except KeyError:
            return ResumeResult(
                status="error",
                resume_type="unknown",
                resumed_from_step=-1,
                checkpoint_id=request.checkpoint_id,
                session_id="",
                error=f"Checkpoint not found: {request.checkpoint_id}",
            )

        # Verify user ownership
        cp_user = checkpoint.metadata.get("user_id", "")
        if cp_user and cp_user != request.user_id:
            return ResumeResult(
                status="error",
                resume_type="unknown",
                resumed_from_step=-1,
                checkpoint_id=request.checkpoint_id,
                session_id=checkpoint.workflow_name,
                error="Checkpoint belongs to a different user",
            )

        state = checkpoint.state
        session_id = checkpoint.workflow_name

        # Determine resume type
        if request.approval_result:
            return await self._resume_hitl(request, checkpoint, state, session_id)
        elif request.overrides and "route" in request.overrides:
            return await self._resume_reroute(request, checkpoint, state, session_id)
        elif request.retry_agents:
            return await self._resume_agent_retry(request, checkpoint, state, session_id)
        else:
            # Default: resume from where it stopped
            return await self._resume_continue(request, checkpoint, state, session_id)

    # ── Scenario 1: HITL Approval Resume ──────────────────────────────

    async def _resume_hitl(
        self, request: ResumeRequest, checkpoint: WorkflowCheckpoint,
        state: dict, session_id: str,
    ) -> ResumeResult:
        """Resume after HITL approval. Continues from the decision step."""
        approval = request.approval_result
        approval_status = approval.get("status", "")

        if approval_status == "rejected":
            # Record rejection in transcript
            await self._transcript.append(TranscriptEntry(
                user_id=request.user_id, session_id=session_id,
                step_name="hitl_approval", step_index=state.get("pipeline_step", 3),
                entry_type="step_complete",
                output_summary={"approval": "rejected", "reason": approval.get("reason", "")},
            ))
            return ResumeResult(
                status="rejected",
                resume_type="hitl",
                resumed_from_step=state.get("pipeline_step", 3),
                checkpoint_id=request.checkpoint_id,
                session_id=session_id,
                error=f"Approval rejected: {approval.get('reason', 'no reason given')}",
            )

        if approval_status != "approved":
            return ResumeResult(
                status="error", resume_type="hitl",
                resumed_from_step=-1, checkpoint_id=request.checkpoint_id,
                session_id=session_id,
                error=f"Invalid approval status: {approval_status}",
            )

        # Record approval in transcript
        await self._transcript.append(TranscriptEntry(
            user_id=request.user_id, session_id=session_id,
            step_name="hitl_approval", step_index=state.get("pipeline_step", 3),
            entry_type="step_complete",
            output_summary={
                "approval": "approved",
                "approver": approval.get("approver", "unknown"),
            },
        ))

        # Resume from next step after the checkpoint
        pipeline_step = state.get("pipeline_step", 3)
        return ResumeResult(
            status="ok",
            resume_type="hitl",
            resumed_from_step=pipeline_step,
            checkpoint_id=request.checkpoint_id,
            session_id=session_id,
            original_route=state.get("route_decision"),
            steps_executed=[{"step": "hitl_approval", "status": "approved"}],
            metadata={
                "approver": approval.get("approver", "unknown"),
                "restored_state": {
                    "memory_context": state.get("memory_context", "")[:100],
                    "knowledge_results": state.get("knowledge_results", "")[:100],
                    "intent_analysis": state.get("intent_analysis", ""),
                    "route_decision": state.get("route_decision"),
                },
            },
        )

    # ── Scenario 2: Re-Route Override ─────────────────────────────────

    async def _resume_reroute(
        self, request: ResumeRequest, checkpoint: WorkflowCheckpoint,
        state: dict, session_id: str,
    ) -> ResumeResult:
        """Resume with a different route. Skips steps 1-4, re-executes from step 5."""
        original_route = state.get("route_decision", "unknown")
        new_route = request.overrides["route"]

        # Record reroute in transcript
        await self._transcript.append(TranscriptEntry(
            user_id=request.user_id, session_id=session_id,
            step_name="reroute_override", step_index=4,
            entry_type="decision",
            output_summary={
                "original_route": original_route,
                "new_route": new_route,
                "override_by": "user",
            },
            checkpoint_id=request.checkpoint_id,
        ))

        return ResumeResult(
            status="ok",
            resume_type="reroute",
            resumed_from_step=4,
            checkpoint_id=request.checkpoint_id,
            session_id=session_id,
            original_route=original_route,
            new_route=new_route,
            steps_executed=[{
                "step": "reroute_override",
                "original": original_route,
                "new": new_route,
            }],
            metadata={
                "restored_state": {
                    "memory_context": state.get("memory_context", "")[:100],
                    "knowledge_results": state.get("knowledge_results", "")[:100],
                    "intent_analysis": state.get("intent_analysis", ""),
                },
            },
        )

    # ── Scenario 3: Agent Retry ───────────────────────────────────────

    async def _resume_agent_retry(
        self, request: ResumeRequest, checkpoint: WorkflowCheckpoint,
        state: dict, session_id: str,
    ) -> ResumeResult:
        """Retry specific failed agents while keeping completed results."""
        subagent_states = state.get("subagent_states", {})

        # Record retry intent
        await self._transcript.append(TranscriptEntry(
            user_id=request.user_id, session_id=session_id,
            step_name="agent_retry", step_index=6,
            entry_type="decision",
            output_summary={
                "retry_agents": request.retry_agents,
                "reuse_completed": request.reuse_completed,
                "existing_states": subagent_states,
            },
            checkpoint_id=request.checkpoint_id,
        ))

        return ResumeResult(
            status="ok",
            resume_type="agent_retry",
            resumed_from_step=6,
            checkpoint_id=request.checkpoint_id,
            session_id=session_id,
            original_route=state.get("route_decision"),
            steps_executed=[{
                "step": "agent_retry",
                "retry": request.retry_agents,
                "kept": [
                    name for name, s in subagent_states.items()
                    if s == "complete" and name not in request.retry_agents
                ],
            }],
            metadata={
                "subagent_states": subagent_states,
                "retry_agents": request.retry_agents,
            },
        )

    # ── Default: Continue from interruption ───────────────────────────

    async def _resume_continue(
        self, request: ResumeRequest, checkpoint: WorkflowCheckpoint,
        state: dict, session_id: str,
    ) -> ResumeResult:
        """Generic resume — continue from wherever execution stopped."""
        pipeline_step = state.get("pipeline_step", 0)

        await self._transcript.append(TranscriptEntry(
            user_id=request.user_id, session_id=session_id,
            step_name="resume_continue", step_index=pipeline_step,
            entry_type="step_complete",
            output_summary={"resumed_from": pipeline_step},
            checkpoint_id=request.checkpoint_id,
        ))

        return ResumeResult(
            status="ok",
            resume_type="continue",
            resumed_from_step=pipeline_step,
            checkpoint_id=request.checkpoint_id,
            session_id=session_id,
            original_route=state.get("route_decision"),
            metadata={
                "restored_state": {
                    "memory_context": state.get("memory_context", "")[:100],
                    "intent_analysis": state.get("intent_analysis", ""),
                    "route_decision": state.get("route_decision"),
                },
            },
        )

    # ── Session Status Detection ──────────────────────────────────────

    async def get_session_status(
        self, user_id: str, session_id: str,
    ) -> dict:
        """Detect session status: complete, interrupted, pending approval, etc.

        Combines transcript analysis with checkpoint info.
        """
        # Transcript-based detection
        interruption = await self._transcript.detect_interruption(user_id, session_id)

        # Find available checkpoints for this session
        try:
            checkpoints = await self._storage.list_checkpoints(
                workflow_name=session_id
            )
            checkpoint_summaries = [
                {
                    "id": cp.checkpoint_id,
                    "step": cp.state.get("pipeline_step", "?"),
                    "route": cp.state.get("route_decision", "?"),
                    "reason": cp.state.get("resume_reason"),
                    "timestamp": cp.timestamp,
                }
                for cp in checkpoints
            ]
        except Exception:
            checkpoint_summaries = []

        return {
            **interruption,
            "session_id": session_id,
            "user_id": user_id,
            "checkpoints": checkpoint_summaries,
            "can_resume": len(checkpoint_summaries) > 0,
        }
