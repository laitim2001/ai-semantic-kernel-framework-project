# =============================================================================
# IPA Platform - Predictive State Updates Handler
# =============================================================================
# Sprint 60: AG-UI Advanced Features
# S60-3: Predictive State Updates (6 pts)
#
# Provides optimistic state updates with prediction, confirmation, and rollback.
# Enables responsive UX by applying predicted changes immediately while
# waiting for server confirmation.
#
# Key Features:
#   - Predictive state updates based on user actions
#   - Confidence scoring for predictions
#   - Confirmation flow for successful predictions
#   - Rollback mechanism for failed predictions
#   - Version tracking to handle conflicts
#
# Dependencies:
#   - Shared State (src.integrations.ag_ui.features.advanced.shared_state)
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

import copy
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.integrations.ag_ui.events import (
    AGUIEventType,
    StateDeltaEvent,
    CustomEvent,
)
from src.integrations.ag_ui.features.advanced.shared_state import (
    SharedStateHandler,
    StateDiff,
    DiffOperation,
    StateVersion,
)

logger = logging.getLogger(__name__)


class PredictionStatus(str, Enum):
    """Status of a prediction."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    ROLLED_BACK = "rolled_back"
    EXPIRED = "expired"
    CONFLICTED = "conflicted"


class PredictionType(str, Enum):
    """Type of prediction being made."""

    OPTIMISTIC = "optimistic"  # Apply immediately, confirm later
    SPECULATIVE = "speculative"  # Predict based on patterns
    PREFETCH = "prefetch"  # Prefetch anticipated data


@dataclass
class PredictionResult:
    """
    Result of a prediction operation.

    Attributes:
        prediction_id: Unique prediction identifier
        prediction_type: Type of prediction
        status: Current status
        predicted_state: The predicted state changes
        original_state: State before prediction
        confidence: Confidence score (0.0 to 1.0)
        created_at: When prediction was created
        expires_at: When prediction expires
        metadata: Additional metadata
    """

    prediction_id: str
    prediction_type: PredictionType
    status: PredictionStatus
    predicted_state: Dict[str, Any]
    original_state: Dict[str, Any]
    confidence: float = 0.8
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "predictionId": self.prediction_id,
            "predictionType": self.prediction_type.value,
            "status": self.status.value,
            "predictedState": self.predicted_state,
            "originalState": self.original_state,
            "confidence": self.confidence,
            "createdAt": self.created_at,
            "expiresAt": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionResult":
        """Create from dictionary representation."""
        return cls(
            prediction_id=data.get("predictionId", f"pred-{uuid.uuid4().hex[:12]}"),
            prediction_type=PredictionType(data.get("predictionType", "optimistic")),
            status=PredictionStatus(data.get("status", "pending")),
            predicted_state=data.get("predictedState", {}),
            original_state=data.get("originalState", {}),
            confidence=data.get("confidence", 0.8),
            created_at=data.get("createdAt", time.time()),
            expires_at=data.get("expiresAt"),
            metadata=data.get("metadata", {}),
        )

    def is_expired(self) -> bool:
        """Check if the prediction has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class PredictionConfig:
    """
    Configuration for predictive state handling.

    Attributes:
        default_ttl: Default time-to-live for predictions in seconds
        min_confidence: Minimum confidence score to apply prediction
        max_pending: Maximum number of pending predictions per thread
        auto_rollback_on_conflict: Whether to auto-rollback on conflict
        enable_speculative: Whether to enable speculative predictions
    """

    default_ttl: float = 30.0
    min_confidence: float = 0.5
    max_pending: int = 10
    auto_rollback_on_conflict: bool = True
    enable_speculative: bool = False


class PredictiveStateHandler:
    """
    Handler for predictive/optimistic state updates.

    Provides optimistic UI updates by predicting state changes and applying
    them immediately, with confirmation and rollback mechanisms for when
    the actual result differs from the prediction.

    Key Features:
    - Apply optimistic updates immediately
    - Track prediction status and confidence
    - Confirm or rollback based on actual results
    - Handle version conflicts gracefully
    - Emit appropriate events for UI synchronization

    Example:
        >>> handler = PredictiveStateHandler(shared_state_handler)
        >>> # Apply an optimistic update
        >>> prediction = handler.predict_state(
        ...     thread_id="thread-123",
        ...     run_id="run-456",
        ...     predicted_changes={"count": 5},
        ... )
        >>> # Later, confirm or rollback
        >>> if actual_result_matches:
        ...     handler.confirm_prediction(prediction.prediction_id, thread_id, run_id)
        >>> else:
        ...     handler.rollback_prediction(prediction.prediction_id, thread_id, run_id)
    """

    def __init__(
        self,
        state_handler: SharedStateHandler,
        *,
        config: Optional[PredictionConfig] = None,
    ):
        """
        Initialize PredictiveStateHandler.

        Args:
            state_handler: SharedStateHandler for state management
            config: Optional prediction configuration
        """
        self._state_handler = state_handler
        self._config = config or PredictionConfig()

        # Prediction storage: prediction_id -> PredictionResult
        self._predictions: Dict[str, PredictionResult] = {}
        # Thread predictions: thread_id -> list of prediction_ids
        self._thread_predictions: Dict[str, List[str]] = {}
        # Pattern learning: action_type -> confidence adjustment
        self._pattern_confidence: Dict[str, float] = {}

        logger.info(
            f"PredictiveStateHandler initialized: "
            f"default_ttl={self._config.default_ttl}s, "
            f"min_confidence={self._config.min_confidence}"
        )

    @property
    def config(self) -> PredictionConfig:
        """Get the prediction configuration."""
        return self._config

    @property
    def state_handler(self) -> SharedStateHandler:
        """Get the state handler."""
        return self._state_handler

    def get_prediction(self, prediction_id: str) -> Optional[PredictionResult]:
        """Get a prediction by ID."""
        return self._predictions.get(prediction_id)

    def list_pending_predictions(self, thread_id: str) -> List[PredictionResult]:
        """List all pending predictions for a thread."""
        prediction_ids = self._thread_predictions.get(thread_id, [])
        return [
            self._predictions[pid]
            for pid in prediction_ids
            if pid in self._predictions
            and self._predictions[pid].status == PredictionStatus.PENDING
        ]

    def _calculate_confidence(
        self,
        action_type: str,
        predicted_changes: Dict[str, Any],
        *,
        base_confidence: float = 0.8,
    ) -> float:
        """
        Calculate confidence score for a prediction.

        Args:
            action_type: Type of action being predicted
            predicted_changes: The predicted state changes
            base_confidence: Base confidence score

        Returns:
            Calculated confidence score (0.0 to 1.0)
        """
        confidence = base_confidence

        # Adjust based on learned patterns
        if action_type in self._pattern_confidence:
            confidence = (confidence + self._pattern_confidence[action_type]) / 2

        # Adjust based on change complexity
        change_count = self._count_changes(predicted_changes)
        if change_count > 10:
            confidence *= 0.8  # Complex changes are less predictable
        elif change_count > 5:
            confidence *= 0.9

        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))

    def _count_changes(self, changes: Dict[str, Any], depth: int = 0) -> int:
        """Count the number of changes in a dict recursively."""
        if depth > 5:
            return 1

        count = 0
        for value in changes.values():
            if isinstance(value, dict):
                count += self._count_changes(value, depth + 1)
            else:
                count += 1
        return count

    def _update_pattern_confidence(
        self,
        action_type: str,
        success: bool,
    ) -> None:
        """Update pattern confidence based on prediction outcome."""
        current = self._pattern_confidence.get(action_type, 0.8)

        if success:
            # Increase confidence slightly
            self._pattern_confidence[action_type] = min(0.95, current + 0.02)
        else:
            # Decrease confidence more significantly
            self._pattern_confidence[action_type] = max(0.3, current - 0.1)

    def predict_state(
        self,
        thread_id: str,
        run_id: str,
        predicted_changes: Dict[str, Any],
        *,
        action_type: str = "generic",
        prediction_type: PredictionType = PredictionType.OPTIMISTIC,
        confidence: Optional[float] = None,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[PredictionResult, StateDeltaEvent]:
        """
        Create and apply a predictive state update.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            predicted_changes: Predicted state changes to apply
            action_type: Type of action for pattern learning
            prediction_type: Type of prediction
            confidence: Optional override for confidence score
            ttl: Time-to-live in seconds
            metadata: Additional metadata

        Returns:
            Tuple of (PredictionResult, StateDeltaEvent)

        Raises:
            ValueError: If too many pending predictions or confidence too low
        """
        # Check pending predictions limit
        pending = self.list_pending_predictions(thread_id)
        if len(pending) >= self._config.max_pending:
            raise ValueError(
                f"Too many pending predictions for thread {thread_id}: "
                f"{len(pending)} >= {self._config.max_pending}"
            )

        # Calculate confidence if not provided
        if confidence is None:
            confidence = self._calculate_confidence(action_type, predicted_changes)

        # Check minimum confidence
        if confidence < self._config.min_confidence:
            raise ValueError(
                f"Confidence {confidence:.2f} below minimum {self._config.min_confidence}"
            )

        # Get current state
        current_state = self._state_handler.get_state(thread_id) or {}

        # Create prediction
        prediction_id = f"pred-{uuid.uuid4().hex[:12]}"
        expires_at = time.time() + (ttl or self._config.default_ttl)

        prediction = PredictionResult(
            prediction_id=prediction_id,
            prediction_type=prediction_type,
            status=PredictionStatus.PENDING,
            predicted_state=copy.deepcopy(predicted_changes),
            original_state=copy.deepcopy(current_state),
            confidence=confidence,
            expires_at=expires_at,
            metadata={
                **(metadata or {}),
                "actionType": action_type,
                "threadId": thread_id,
                "runId": run_id,
            },
        )

        # Store prediction
        self._predictions[prediction_id] = prediction
        if thread_id not in self._thread_predictions:
            self._thread_predictions[thread_id] = []
        self._thread_predictions[thread_id].append(prediction_id)

        # Apply predicted changes to state
        event = self._state_handler.update_state(
            thread_id=thread_id,
            run_id=run_id,
            updates=predicted_changes,
            merge=True,
        )

        logger.info(
            f"Prediction created: {prediction_id} for thread {thread_id}, "
            f"confidence={confidence:.2f}"
        )

        return prediction, event

    def confirm_prediction(
        self,
        prediction_id: str,
        thread_id: str,
        run_id: str,
        *,
        actual_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[PredictionResult, Optional[StateDeltaEvent]]:
        """
        Confirm a prediction was correct.

        Args:
            prediction_id: Prediction ID to confirm
            thread_id: Thread ID
            run_id: Run ID
            actual_state: Optional actual state to merge

        Returns:
            Tuple of (updated PredictionResult, optional StateDeltaEvent)

        Raises:
            ValueError: If prediction not found or not pending
        """
        prediction = self._predictions.get(prediction_id)
        if not prediction:
            raise ValueError(f"Prediction not found: {prediction_id}")

        if prediction.status != PredictionStatus.PENDING:
            raise ValueError(
                f"Prediction {prediction_id} is not pending: {prediction.status.value}"
            )

        # Update status
        prediction.status = PredictionStatus.CONFIRMED

        # Update pattern confidence
        action_type = prediction.metadata.get("actionType", "generic")
        self._update_pattern_confidence(action_type, success=True)

        event = None
        # If actual state provided and differs, update state
        if actual_state is not None:
            current = self._state_handler.get_state(thread_id) or {}
            if actual_state != current:
                event = self._state_handler.update_state(
                    thread_id=thread_id,
                    run_id=run_id,
                    updates=actual_state,
                    merge=False,
                )

        logger.info(f"Prediction confirmed: {prediction_id}")

        return prediction, event

    def rollback_prediction(
        self,
        prediction_id: str,
        thread_id: str,
        run_id: str,
        *,
        reason: Optional[str] = None,
    ) -> Tuple[PredictionResult, StateDeltaEvent]:
        """
        Rollback a prediction to the original state.

        Args:
            prediction_id: Prediction ID to rollback
            thread_id: Thread ID
            run_id: Run ID
            reason: Optional reason for rollback

        Returns:
            Tuple of (updated PredictionResult, StateDeltaEvent)

        Raises:
            ValueError: If prediction not found or not pending
        """
        prediction = self._predictions.get(prediction_id)
        if not prediction:
            raise ValueError(f"Prediction not found: {prediction_id}")

        if prediction.status not in (PredictionStatus.PENDING, PredictionStatus.CONFLICTED):
            raise ValueError(
                f"Prediction {prediction_id} cannot be rolled back: {prediction.status.value}"
            )

        # Update status
        prediction.status = PredictionStatus.ROLLED_BACK
        if reason:
            prediction.metadata["rollbackReason"] = reason

        # Update pattern confidence
        action_type = prediction.metadata.get("actionType", "generic")
        self._update_pattern_confidence(action_type, success=False)

        # Restore original state
        event = self._state_handler.update_state(
            thread_id=thread_id,
            run_id=run_id,
            updates=prediction.original_state,
            merge=False,
        )

        logger.info(f"Prediction rolled back: {prediction_id}, reason={reason}")

        return prediction, event

    def check_and_expire_predictions(
        self,
        thread_id: str,
        run_id: str,
    ) -> List[Tuple[PredictionResult, StateDeltaEvent]]:
        """
        Check for expired predictions and handle them.

        Args:
            thread_id: Thread ID
            run_id: Run ID

        Returns:
            List of (expired prediction, rollback event) tuples
        """
        expired: List[Tuple[PredictionResult, StateDeltaEvent]] = []

        prediction_ids = self._thread_predictions.get(thread_id, []).copy()
        for pred_id in prediction_ids:
            prediction = self._predictions.get(pred_id)
            if prediction and prediction.status == PredictionStatus.PENDING:
                if prediction.is_expired():
                    # Rollback expired prediction (status will be set to ROLLED_BACK)
                    result, event = self.rollback_prediction(
                        pred_id, thread_id, run_id, reason="expired"
                    )
                    # Add expiration metadata
                    result.metadata["expiredAt"] = time.time()
                    expired.append((result, event))

        return expired

    def handle_server_update(
        self,
        thread_id: str,
        run_id: str,
        server_state: Dict[str, Any],
    ) -> List[Tuple[PredictionResult, Optional[StateDeltaEvent]]]:
        """
        Handle a server state update and reconcile with pending predictions.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            server_state: Actual state from server

        Returns:
            List of (prediction, optional event) tuples for conflicts resolved
        """
        results: List[Tuple[PredictionResult, Optional[StateDeltaEvent]]] = []

        pending = self.list_pending_predictions(thread_id)
        for prediction in pending:
            # Check if prediction conflicts with server state
            has_conflict = self._check_conflict(
                prediction.predicted_state,
                server_state,
            )

            if has_conflict:
                prediction.status = PredictionStatus.CONFLICTED

                if self._config.auto_rollback_on_conflict:
                    # Auto-rollback conflicting prediction
                    result, event = self.rollback_prediction(
                        prediction.prediction_id,
                        thread_id,
                        run_id,
                        reason="server_conflict",
                    )
                    results.append((result, event))
                else:
                    # Mark as conflicted but don't rollback
                    results.append((prediction, None))

        return results

    def _check_conflict(
        self,
        predicted: Dict[str, Any],
        actual: Dict[str, Any],
        path: str = "",
    ) -> bool:
        """Check if predicted state conflicts with actual state."""
        for key, pred_val in predicted.items():
            current_path = f"{path}.{key}" if path else key

            if key not in actual:
                # Key missing in actual - potential conflict
                continue

            actual_val = actual[key]

            if isinstance(pred_val, dict) and isinstance(actual_val, dict):
                if self._check_conflict(pred_val, actual_val, current_path):
                    return True
            elif pred_val != actual_val:
                # Values differ - conflict
                logger.debug(f"Conflict at {current_path}: {pred_val} != {actual_val}")
                return True

        return False

    def emit_prediction_event(
        self,
        prediction: PredictionResult,
        event_type: str = "prediction_update",
    ) -> CustomEvent:
        """
        Emit a custom event for prediction status.

        Args:
            prediction: The prediction result
            event_type: Type of event

        Returns:
            CustomEvent with prediction data
        """
        return CustomEvent(
            type=AGUIEventType.CUSTOM,
            event_name=event_type,
            payload=prediction.to_dict(),
        )

    def cleanup_completed_predictions(
        self,
        thread_id: str,
        *,
        keep_count: int = 10,
    ) -> int:
        """
        Cleanup completed predictions for a thread.

        Args:
            thread_id: Thread ID
            keep_count: Number of recent completed predictions to keep

        Returns:
            Number of predictions removed
        """
        prediction_ids = self._thread_predictions.get(thread_id, [])

        # Separate pending from completed
        pending_ids = []
        completed_ids = []

        for pred_id in prediction_ids:
            pred = self._predictions.get(pred_id)
            if pred:
                if pred.status == PredictionStatus.PENDING:
                    pending_ids.append(pred_id)
                else:
                    completed_ids.append(pred_id)

        # Keep only recent completed
        to_remove = completed_ids[:-keep_count] if len(completed_ids) > keep_count else []

        for pred_id in to_remove:
            if pred_id in self._predictions:
                del self._predictions[pred_id]

        # Update thread predictions list
        self._thread_predictions[thread_id] = pending_ids + completed_ids[-keep_count:]

        removed_count = len(to_remove)
        if removed_count > 0:
            logger.debug(f"Cleaned up {removed_count} predictions for thread {thread_id}")

        return removed_count

    def clear_thread_predictions(self, thread_id: str) -> None:
        """Clear all predictions for a thread."""
        prediction_ids = self._thread_predictions.get(thread_id, [])
        for pred_id in prediction_ids:
            if pred_id in self._predictions:
                del self._predictions[pred_id]

        if thread_id in self._thread_predictions:
            del self._thread_predictions[thread_id]

        logger.info(f"Cleared all predictions for thread: {thread_id}")

    def clear_all(self) -> None:
        """Clear all predictions."""
        self._predictions.clear()
        self._thread_predictions.clear()
        self._pattern_confidence.clear()
        logger.info("Cleared all predictions")


def create_predictive_handler(
    state_handler: SharedStateHandler,
    *,
    default_ttl: float = 30.0,
    min_confidence: float = 0.5,
    max_pending: int = 10,
    auto_rollback: bool = True,
) -> PredictiveStateHandler:
    """
    Factory function to create PredictiveStateHandler.

    Args:
        state_handler: SharedStateHandler for state management
        default_ttl: Default time-to-live for predictions
        min_confidence: Minimum confidence to apply predictions
        max_pending: Maximum pending predictions per thread
        auto_rollback: Whether to auto-rollback on conflict

    Returns:
        Configured PredictiveStateHandler instance
    """
    config = PredictionConfig(
        default_ttl=default_ttl,
        min_confidence=min_confidence,
        max_pending=max_pending,
        auto_rollback_on_conflict=auto_rollback,
    )
    return PredictiveStateHandler(state_handler, config=config)
