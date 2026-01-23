# =============================================================================
# IPA Platform - Guided Dialog API Routes
# =============================================================================
# Sprint 98: Phase 28 Integration - GuidedDialogEngine API
#
# REST API endpoints for guided dialog management.
# Supports multi-turn information gathering conversations.
#
# Endpoints:
#   POST /dialog/start - Start a new guided dialog session
#   POST /dialog/{dialog_id}/respond - Submit user response
#   GET /dialog/{dialog_id}/status - Get dialog status
#   DELETE /dialog/{dialog_id} - Cancel/close dialog session
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.integrations.orchestration import (
    GuidedDialogEngine,
    DialogResponse,
    DialogState,
    create_guided_dialog_engine,
    create_mock_dialog_engine,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class StartDialogRequest(BaseModel):
    """Request to start a new guided dialog session."""

    content: str = Field(
        ...,
        description="User's initial message or request",
        min_length=1,
        max_length=10000,
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user identifier",
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for correlation",
    )
    initial_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional initial context data",
    )


class DialogQuestionItem(BaseModel):
    """A question to be presented to the user."""

    question_id: str = Field(..., description="Unique question identifier")
    question: str = Field(..., description="The question text")
    field_name: str = Field(..., description="Field this question fills")
    options: Optional[List[str]] = Field(
        None,
        description="Optional list of suggested options",
    )
    required: bool = Field(True, description="Whether an answer is required")


class DialogStatusResponse(BaseModel):
    """Response with dialog status and questions."""

    dialog_id: str = Field(..., description="Unique dialog session ID")
    status: str = Field(
        ...,
        description="Dialog status (active, completed, cancelled)",
    )
    needs_more_info: bool = Field(
        ...,
        description="Whether more information is needed",
    )
    message: Optional[str] = Field(
        None,
        description="Message to display to user",
    )
    questions: Optional[List[DialogQuestionItem]] = Field(
        None,
        description="Questions for the user to answer",
    )
    current_intent: Optional[str] = Field(
        None,
        description="Current detected intent category",
    )
    completeness_score: float = Field(
        0.0,
        description="Information completeness score (0-1)",
        ge=0.0,
        le=1.0,
    )
    turn_count: int = Field(
        0,
        description="Number of conversation turns",
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Dialog creation timestamp",
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Last update timestamp",
    )


class RespondToDialogRequest(BaseModel):
    """Request to respond to dialog questions."""

    responses: Dict[str, Any] = Field(
        ...,
        description="Map of field_name to user response",
    )
    additional_message: Optional[str] = Field(
        None,
        description="Optional free-form additional message",
    )


class CancelDialogResponse(BaseModel):
    """Response after cancelling a dialog."""

    dialog_id: str = Field(..., description="The cancelled dialog ID")
    status: str = Field("cancelled", description="Status after cancellation")
    message: str = Field(..., description="Cancellation message")


# =============================================================================
# Global State
# =============================================================================

# In-memory dialog session storage (use Redis in production)
_dialog_sessions: Dict[str, Dict[str, Any]] = {}

# Global dialog engine instance
_dialog_engine: Optional[GuidedDialogEngine] = None


def get_dialog_engine() -> GuidedDialogEngine:
    """Get or create the dialog engine instance."""
    global _dialog_engine
    if _dialog_engine is None:
        try:
            # Try to create real engine, fall back to mock
            _dialog_engine = create_guided_dialog_engine()
        except Exception as e:
            logger.warning(f"Failed to create dialog engine, using mock: {e}")
            _dialog_engine = create_mock_dialog_engine()
    return _dialog_engine


# =============================================================================
# Router
# =============================================================================

dialog_router = APIRouter(prefix="/orchestration/dialog", tags=["Guided Dialog"])


# =============================================================================
# Endpoints
# =============================================================================


@dialog_router.post(
    "/start",
    response_model=DialogStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_dialog(request: StartDialogRequest) -> DialogStatusResponse:
    """
    Start a new guided dialog session.

    Initiates a multi-turn conversation to gather required information
    for intent classification and routing.

    Args:
        request: Initial dialog request with user content

    Returns:
        DialogStatusResponse with session info and initial questions
    """
    engine = get_dialog_engine()

    try:
        # Generate dialog ID
        dialog_id = str(uuid4())

        # Prepare initial context (stored in session for later use)
        initial_context = request.initial_context or {}
        if request.user_id:
            initial_context["user_id"] = request.user_id
        if request.session_id:
            initial_context["session_id"] = request.session_id

        # Start dialog (engine only accepts user_input)
        response = await engine.start_dialog(user_input=request.content)

        # Store session with context
        now = datetime.utcnow()
        _dialog_sessions[dialog_id] = {
            "engine_dialog_id": dialog_id,  # Use our generated ID
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "turn_count": 1,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "initial_context": initial_context,
        }

        # Convert questions to response format
        questions = None
        if response.questions:
            questions = [
                DialogQuestionItem(
                    question_id=str(uuid4()),
                    question=q.question if hasattr(q, "question") else str(q),
                    field_name=q.field_name if hasattr(q, "field_name") else "unknown",
                    options=q.options if hasattr(q, "options") else None,
                    required=q.required if hasattr(q, "required") else True,
                )
                for q in response.questions
            ]

        # Extract intent and completeness from state if available
        current_intent = None
        completeness_score = 0.0
        if response.state:
            if response.state.routing_decision:
                rd = response.state.routing_decision
                current_intent = rd.intent_category.value if rd.intent_category else None
                if rd.completeness:
                    completeness_score = rd.completeness.completeness_score

        return DialogStatusResponse(
            dialog_id=dialog_id,
            status="active",
            needs_more_info=response.should_continue,  # Use should_continue
            message=response.message,
            questions=questions,
            current_intent=current_intent,
            completeness_score=completeness_score,
            turn_count=1,
            created_at=now,
            updated_at=now,
        )

    except Exception as e:
        logger.error(f"Failed to start dialog: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start dialog: {str(e)}",
        )


@dialog_router.post(
    "/{dialog_id}/respond",
    response_model=DialogStatusResponse,
)
async def respond_to_dialog(
    dialog_id: str,
    request: RespondToDialogRequest,
) -> DialogStatusResponse:
    """
    Submit user responses to dialog questions.

    Processes user answers and returns next questions or completion status.

    Args:
        dialog_id: The dialog session ID
        request: User responses to questions

    Returns:
        DialogStatusResponse with updated status and next questions (if any)
    """
    # Check session exists
    if dialog_id not in _dialog_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dialog session not found: {dialog_id}",
        )

    session = _dialog_sessions[dialog_id]

    # Check session is active
    if session["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dialog session is not active: {session['status']}",
        )

    engine = get_dialog_engine()

    try:
        # Convert responses dict to a string format for the engine
        # The engine expects a single user_response string
        response_parts = []
        for field_name, value in request.responses.items():
            response_parts.append(f"{field_name}: {value}")
        if request.additional_message:
            response_parts.append(request.additional_message)
        user_response = "; ".join(response_parts) if response_parts else ""

        # Process response (engine only accepts user_response: str)
        response = await engine.process_response(user_response=user_response)

        # Update session
        now = datetime.utcnow()
        session["updated_at"] = now
        session["turn_count"] += 1

        # Check if dialog is complete (use should_continue from DialogResponse)
        if not response.should_continue:
            session["status"] = "completed"

        # Convert questions
        questions = None
        if response.questions:
            questions = [
                DialogQuestionItem(
                    question_id=str(uuid4()),
                    question=q.question if hasattr(q, "question") else str(q),
                    field_name=q.field_name if hasattr(q, "field_name") else "unknown",
                    options=q.options if hasattr(q, "options") else None,
                    required=q.required if hasattr(q, "required") else True,
                )
                for q in response.questions
            ]

        # Extract intent and completeness from state if available
        current_intent = None
        completeness_score = 0.0
        if response.state:
            if response.state.routing_decision:
                rd = response.state.routing_decision
                current_intent = rd.intent_category.value if rd.intent_category else None
                if rd.completeness:
                    completeness_score = rd.completeness.completeness_score

        return DialogStatusResponse(
            dialog_id=dialog_id,
            status=session["status"],
            needs_more_info=response.should_continue,  # Use should_continue
            message=response.message,
            questions=questions,
            current_intent=current_intent,
            completeness_score=completeness_score,
            turn_count=session["turn_count"],
            created_at=session["created_at"],
            updated_at=now,
        )

    except Exception as e:
        logger.error(f"Failed to process dialog response: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process response: {str(e)}",
        )


@dialog_router.get(
    "/{dialog_id}/status",
    response_model=DialogStatusResponse,
)
async def get_dialog_status(dialog_id: str) -> DialogStatusResponse:
    """
    Get current status of a dialog session.

    Args:
        dialog_id: The dialog session ID

    Returns:
        DialogStatusResponse with current session status
    """
    # Check session exists
    if dialog_id not in _dialog_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dialog session not found: {dialog_id}",
        )

    session = _dialog_sessions[dialog_id]
    engine = get_dialog_engine()

    try:
        # Get current state from engine
        state = await engine.get_dialog_state(session["engine_dialog_id"])

        # Convert questions if available
        questions = None
        if state and hasattr(state, "pending_questions") and state.pending_questions:
            questions = [
                DialogQuestionItem(
                    question_id=str(uuid4()),
                    question=q.question if hasattr(q, "question") else str(q),
                    field_name=q.field_name if hasattr(q, "field_name") else "unknown",
                    options=q.options if hasattr(q, "options") else None,
                    required=q.required if hasattr(q, "required") else True,
                )
                for q in state.pending_questions
            ]

        return DialogStatusResponse(
            dialog_id=dialog_id,
            status=session["status"],
            needs_more_info=state.needs_more_info if state else False,
            message=state.last_message if state and hasattr(state, "last_message") else None,
            questions=questions,
            current_intent=state.intent_category.value
            if state and hasattr(state, "intent_category") and state.intent_category
            else None,
            completeness_score=state.completeness_score
            if state and hasattr(state, "completeness_score")
            else 0.0,
            turn_count=session["turn_count"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
        )

    except Exception as e:
        logger.warning(f"Failed to get dialog state: {e}")
        # Return basic session info if engine fails
        return DialogStatusResponse(
            dialog_id=dialog_id,
            status=session["status"],
            needs_more_info=session["status"] == "active",
            turn_count=session["turn_count"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
        )


@dialog_router.delete(
    "/{dialog_id}",
    response_model=CancelDialogResponse,
)
async def cancel_dialog(dialog_id: str) -> CancelDialogResponse:
    """
    Cancel/close a dialog session.

    Args:
        dialog_id: The dialog session ID to cancel

    Returns:
        CancelDialogResponse confirming cancellation
    """
    # Check session exists
    if dialog_id not in _dialog_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dialog session not found: {dialog_id}",
        )

    session = _dialog_sessions[dialog_id]

    # Update status
    session["status"] = "cancelled"
    session["updated_at"] = datetime.utcnow()

    # Optionally clean up engine state
    engine = get_dialog_engine()
    try:
        if hasattr(engine, "cancel_dialog"):
            await engine.cancel_dialog(session["engine_dialog_id"])
    except Exception as e:
        logger.warning(f"Failed to cancel dialog in engine: {e}")

    return CancelDialogResponse(
        dialog_id=dialog_id,
        status="cancelled",
        message="Dialog session cancelled successfully",
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "dialog_router",
    "StartDialogRequest",
    "RespondToDialogRequest",
    "DialogStatusResponse",
    "DialogQuestionItem",
    "CancelDialogResponse",
]
