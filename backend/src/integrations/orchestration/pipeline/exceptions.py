"""
Pipeline Exceptions — Signal-based pause/resume control.

Pipeline steps raise these exceptions to interrupt execution cleanly.
The OrchestrationPipelineService catches them, serializes PipelineContext
to a checkpoint, and emits the appropriate SSE pause event.

On resume, ResumeService restores context from checkpoint and re-enters
the pipeline at the correct step index.

Phase 45: Orchestration Core
"""

from typing import Any, Dict, List, Optional


class PipelineError(Exception):
    """Base exception for pipeline errors.

    Attributes:
        step_name: Name of the step where the error occurred.
        message: Human-readable error description.
        recoverable: Whether the pipeline can be resumed after this error.
        context_snapshot: Partial PipelineContext state at the time of error.
    """

    def __init__(
        self,
        message: str,
        step_name: str = "",
        recoverable: bool = False,
        context_snapshot: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.step_name = step_name
        self.message = message
        self.recoverable = recoverable
        self.context_snapshot = context_snapshot or {}


class HITLPauseException(PipelineError):
    """Raised by HITLGateStep when human approval is required.

    The pipeline pauses at Step 5. A checkpoint is saved, an approval
    request is created, and an HITL_REQUIRED SSE event is emitted.

    On resume (after approval/rejection), ResumeService restores context
    from checkpoint and continues from Step 6 (LLM Route Decision).

    Attributes:
        approval_id: The created approval request ID.
        checkpoint_id: The saved checkpoint ID for resume.
        risk_level: The risk level that triggered HITL.
        approval_type: "single" or "multi" approval required.
    """

    def __init__(
        self,
        approval_id: str,
        checkpoint_id: str,
        risk_level: str,
        approval_type: str = "single",
        message: str = "Human approval required",
    ):
        super().__init__(
            message=message,
            step_name="hitl_gate",
            recoverable=True,
            context_snapshot={
                "approval_id": approval_id,
                "checkpoint_id": checkpoint_id,
                "risk_level": risk_level,
                "approval_type": approval_type,
            },
        )
        self.approval_id = approval_id
        self.checkpoint_id = checkpoint_id
        self.risk_level = risk_level
        self.approval_type = approval_type


class DialogPauseException(PipelineError):
    """Raised by IntentStep when user input is incomplete.

    The pipeline pauses at Step 3. A checkpoint is saved, guided dialog
    questions are returned, and a DIALOG_REQUIRED SSE event is emitted.

    On resume (after user responds), ResumeService restores context,
    merges the user's answers, and re-runs Step 3 (Intent + Completeness).

    Attributes:
        dialog_id: The guided dialog session ID.
        questions: List of questions for the user to answer.
        missing_fields: The fields that need to be provided.
        checkpoint_id: The saved checkpoint ID for resume.
        completeness_score: Current completeness score (0.0 - 1.0).
    """

    def __init__(
        self,
        dialog_id: str,
        questions: List[str],
        missing_fields: List[str],
        checkpoint_id: str,
        completeness_score: float = 0.0,
        message: str = "Additional information required",
    ):
        super().__init__(
            message=message,
            step_name="intent_analysis",
            recoverable=True,
            context_snapshot={
                "dialog_id": dialog_id,
                "questions": questions,
                "missing_fields": missing_fields,
                "checkpoint_id": checkpoint_id,
                "completeness_score": completeness_score,
            },
        )
        self.dialog_id = dialog_id
        self.questions = questions
        self.missing_fields = missing_fields
        self.checkpoint_id = checkpoint_id
        self.completeness_score = completeness_score
