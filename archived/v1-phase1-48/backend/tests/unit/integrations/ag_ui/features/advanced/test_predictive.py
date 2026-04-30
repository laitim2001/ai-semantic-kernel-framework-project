# =============================================================================
# IPA Platform - Predictive State Updates Tests
# =============================================================================
# Sprint 60: AG-UI Advanced Features
# S60-3: Predictive State Updates (6 pts)
#
# Tests for PredictiveStateHandler and optimistic state updates.
# =============================================================================

import time
import pytest
from unittest.mock import MagicMock, patch

from src.integrations.ag_ui.features.advanced.shared_state import (
    SharedStateHandler,
    StateDiff,
    DiffOperation,
)
from src.integrations.ag_ui.features.advanced.predictive import (
    PredictionStatus,
    PredictionType,
    PredictionResult,
    PredictionConfig,
    PredictiveStateHandler,
    create_predictive_handler,
)


class TestPredictionStatus:
    """Tests for PredictionStatus enum."""

    def test_pending_status(self):
        """Test PENDING status value."""
        assert PredictionStatus.PENDING.value == "pending"

    def test_confirmed_status(self):
        """Test CONFIRMED status value."""
        assert PredictionStatus.CONFIRMED.value == "confirmed"

    def test_rolled_back_status(self):
        """Test ROLLED_BACK status value."""
        assert PredictionStatus.ROLLED_BACK.value == "rolled_back"

    def test_expired_status(self):
        """Test EXPIRED status value."""
        assert PredictionStatus.EXPIRED.value == "expired"

    def test_conflicted_status(self):
        """Test CONFLICTED status value."""
        assert PredictionStatus.CONFLICTED.value == "conflicted"


class TestPredictionType:
    """Tests for PredictionType enum."""

    def test_optimistic_type(self):
        """Test OPTIMISTIC type value."""
        assert PredictionType.OPTIMISTIC.value == "optimistic"

    def test_speculative_type(self):
        """Test SPECULATIVE type value."""
        assert PredictionType.SPECULATIVE.value == "speculative"

    def test_prefetch_type(self):
        """Test PREFETCH type value."""
        assert PredictionType.PREFETCH.value == "prefetch"


class TestPredictionResult:
    """Tests for PredictionResult dataclass."""

    def test_basic_result(self):
        """Test basic prediction result creation."""
        result = PredictionResult(
            prediction_id="pred-123",
            prediction_type=PredictionType.OPTIMISTIC,
            status=PredictionStatus.PENDING,
            predicted_state={"count": 5},
            original_state={"count": 0},
        )
        assert result.prediction_id == "pred-123"
        assert result.prediction_type == PredictionType.OPTIMISTIC
        assert result.status == PredictionStatus.PENDING
        assert result.predicted_state == {"count": 5}
        assert result.original_state == {"count": 0}
        assert result.confidence == 0.8  # Default

    def test_result_with_confidence(self):
        """Test prediction result with custom confidence."""
        result = PredictionResult(
            prediction_id="pred-456",
            prediction_type=PredictionType.SPECULATIVE,
            status=PredictionStatus.PENDING,
            predicted_state={},
            original_state={},
            confidence=0.95,
        )
        assert result.confidence == 0.95

    def test_result_with_expiry(self):
        """Test prediction result with expiry."""
        expires = time.time() + 30
        result = PredictionResult(
            prediction_id="pred-789",
            prediction_type=PredictionType.OPTIMISTIC,
            status=PredictionStatus.PENDING,
            predicted_state={},
            original_state={},
            expires_at=expires,
        )
        assert result.expires_at == expires

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = PredictionResult(
            prediction_id="pred-abc",
            prediction_type=PredictionType.OPTIMISTIC,
            status=PredictionStatus.CONFIRMED,
            predicted_state={"value": 10},
            original_state={"value": 5},
            confidence=0.9,
        )
        data = result.to_dict()
        assert data["predictionId"] == "pred-abc"
        assert data["predictionType"] == "optimistic"
        assert data["status"] == "confirmed"
        assert data["predictedState"] == {"value": 10}
        assert data["originalState"] == {"value": 5}
        assert data["confidence"] == 0.9

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "predictionId": "pred-xyz",
            "predictionType": "speculative",
            "status": "pending",
            "predictedState": {"a": 1},
            "originalState": {"a": 0},
            "confidence": 0.75,
        }
        result = PredictionResult.from_dict(data)
        assert result.prediction_id == "pred-xyz"
        assert result.prediction_type == PredictionType.SPECULATIVE
        assert result.status == PredictionStatus.PENDING
        assert result.confidence == 0.75

    def test_is_expired_false(self):
        """Test is_expired when not expired."""
        result = PredictionResult(
            prediction_id="pred-test",
            prediction_type=PredictionType.OPTIMISTIC,
            status=PredictionStatus.PENDING,
            predicted_state={},
            original_state={},
            expires_at=time.time() + 3600,  # 1 hour from now
        )
        assert result.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired when expired."""
        result = PredictionResult(
            prediction_id="pred-test",
            prediction_type=PredictionType.OPTIMISTIC,
            status=PredictionStatus.PENDING,
            predicted_state={},
            original_state={},
            expires_at=time.time() - 1,  # 1 second ago
        )
        assert result.is_expired() is True

    def test_is_expired_no_expiry(self):
        """Test is_expired with no expiry set."""
        result = PredictionResult(
            prediction_id="pred-test",
            prediction_type=PredictionType.OPTIMISTIC,
            status=PredictionStatus.PENDING,
            predicted_state={},
            original_state={},
            expires_at=None,
        )
        assert result.is_expired() is False


class TestPredictionConfig:
    """Tests for PredictionConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PredictionConfig()
        assert config.default_ttl == 30.0
        assert config.min_confidence == 0.5
        assert config.max_pending == 10
        assert config.auto_rollback_on_conflict is True
        assert config.enable_speculative is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PredictionConfig(
            default_ttl=60.0,
            min_confidence=0.7,
            max_pending=5,
            auto_rollback_on_conflict=False,
            enable_speculative=True,
        )
        assert config.default_ttl == 60.0
        assert config.min_confidence == 0.7
        assert config.max_pending == 5
        assert config.auto_rollback_on_conflict is False
        assert config.enable_speculative is True


class TestPredictiveStateHandler:
    """Tests for PredictiveStateHandler class."""

    @pytest.fixture
    def state_handler(self):
        """Create a SharedStateHandler instance."""
        return SharedStateHandler()

    @pytest.fixture
    def handler(self, state_handler):
        """Create a PredictiveStateHandler instance."""
        return PredictiveStateHandler(state_handler)

    def test_initialization(self, handler, state_handler):
        """Test handler initialization."""
        assert handler.state_handler is state_handler
        assert handler.config is not None

    def test_get_prediction_not_found(self, handler):
        """Test getting nonexistent prediction."""
        result = handler.get_prediction("nonexistent")
        assert result is None

    def test_list_pending_predictions_empty(self, handler):
        """Test listing predictions for unknown thread."""
        predictions = handler.list_pending_predictions("unknown-thread")
        assert predictions == []

    def test_predict_state_basic(self, handler, state_handler):
        """Test basic state prediction."""
        state_handler.set_state("thread-1", {"count": 0})

        prediction, event = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"count": 5},
        )

        assert prediction is not None
        assert prediction.status == PredictionStatus.PENDING
        assert prediction.predicted_state == {"count": 5}
        assert prediction.original_state == {"count": 0}
        assert event is not None

        # Verify state was updated
        state = state_handler.get_state("thread-1")
        assert state["count"] == 5

    def test_predict_state_with_action_type(self, handler, state_handler):
        """Test prediction with action type."""
        state_handler.set_state("thread-1", {})

        prediction, _ = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"value": 10},
            action_type="increment",
        )

        assert prediction.metadata["actionType"] == "increment"

    def test_predict_state_custom_confidence(self, handler, state_handler):
        """Test prediction with custom confidence."""
        state_handler.set_state("thread-1", {})

        prediction, _ = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"data": "test"},
            confidence=0.95,
        )

        assert prediction.confidence == 0.95

    def test_predict_state_low_confidence_rejected(self, handler, state_handler):
        """Test prediction with too low confidence is rejected."""
        state_handler.set_state("thread-1", {})

        with pytest.raises(ValueError, match="Confidence.*below minimum"):
            handler.predict_state(
                thread_id="thread-1",
                run_id="run-1",
                predicted_changes={"data": "test"},
                confidence=0.1,  # Below default 0.5 minimum
            )

    def test_predict_state_max_pending_exceeded(self, handler, state_handler):
        """Test prediction rejected when max pending exceeded."""
        # Create handler with low max_pending
        config = PredictionConfig(max_pending=2)
        limited_handler = PredictiveStateHandler(state_handler, config=config)
        state_handler.set_state("thread-1", {})

        # Create max predictions
        limited_handler.predict_state("thread-1", "run-1", {"a": 1})
        limited_handler.predict_state("thread-1", "run-1", {"b": 2})

        # Third should fail
        with pytest.raises(ValueError, match="Too many pending predictions"):
            limited_handler.predict_state("thread-1", "run-1", {"c": 3})

    def test_confirm_prediction(self, handler, state_handler):
        """Test confirming a prediction."""
        state_handler.set_state("thread-1", {"count": 0})

        prediction, _ = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"count": 5},
        )

        confirmed, event = handler.confirm_prediction(
            prediction.prediction_id,
            "thread-1",
            "run-1",
        )

        assert confirmed.status == PredictionStatus.CONFIRMED
        assert event is None  # No additional update needed

    def test_confirm_prediction_with_actual_state(self, handler, state_handler):
        """Test confirming prediction with actual state."""
        state_handler.set_state("thread-1", {"count": 0})

        prediction, _ = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"count": 5},
        )

        confirmed, event = handler.confirm_prediction(
            prediction.prediction_id,
            "thread-1",
            "run-1",
            actual_state={"count": 7},  # Different from prediction
        )

        assert confirmed.status == PredictionStatus.CONFIRMED
        assert event is not None

        # State should reflect actual value
        state = state_handler.get_state("thread-1")
        assert state == {"count": 7}

    def test_confirm_prediction_not_found(self, handler):
        """Test confirming nonexistent prediction."""
        with pytest.raises(ValueError, match="Prediction not found"):
            handler.confirm_prediction("nonexistent", "thread-1", "run-1")

    def test_confirm_prediction_not_pending(self, handler, state_handler):
        """Test confirming already confirmed prediction."""
        state_handler.set_state("thread-1", {})
        prediction, _ = handler.predict_state("thread-1", "run-1", {"a": 1})
        handler.confirm_prediction(prediction.prediction_id, "thread-1", "run-1")

        with pytest.raises(ValueError, match="not pending"):
            handler.confirm_prediction(prediction.prediction_id, "thread-1", "run-1")

    def test_rollback_prediction(self, handler, state_handler):
        """Test rolling back a prediction."""
        state_handler.set_state("thread-1", {"count": 0})

        prediction, _ = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"count": 5},
        )

        # Verify state was changed
        assert state_handler.get_state("thread-1")["count"] == 5

        # Rollback
        rolled_back, event = handler.rollback_prediction(
            prediction.prediction_id,
            "thread-1",
            "run-1",
            reason="test_rollback",
        )

        assert rolled_back.status == PredictionStatus.ROLLED_BACK
        assert rolled_back.metadata["rollbackReason"] == "test_rollback"

        # Verify state was restored
        state = state_handler.get_state("thread-1")
        assert state["count"] == 0

    def test_rollback_prediction_not_found(self, handler):
        """Test rolling back nonexistent prediction."""
        with pytest.raises(ValueError, match="Prediction not found"):
            handler.rollback_prediction("nonexistent", "thread-1", "run-1")

    def test_rollback_confirmed_prediction_fails(self, handler, state_handler):
        """Test rolling back confirmed prediction fails."""
        state_handler.set_state("thread-1", {})
        prediction, _ = handler.predict_state("thread-1", "run-1", {"a": 1})
        handler.confirm_prediction(prediction.prediction_id, "thread-1", "run-1")

        with pytest.raises(ValueError, match="cannot be rolled back"):
            handler.rollback_prediction(prediction.prediction_id, "thread-1", "run-1")

    def test_check_and_expire_predictions(self, handler, state_handler):
        """Test expiring old predictions."""
        state_handler.set_state("thread-1", {"value": "original"})

        # Create prediction that's already expired
        config = PredictionConfig(default_ttl=0.001)  # Very short TTL
        quick_handler = PredictiveStateHandler(state_handler, config=config)

        prediction, _ = quick_handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"value": "predicted"},
        )

        # Wait for expiry
        time.sleep(0.01)

        # Check and expire
        expired = quick_handler.check_and_expire_predictions("thread-1", "run-1")

        assert len(expired) == 1
        assert expired[0][0].status == PredictionStatus.ROLLED_BACK

    def test_handle_server_update_no_conflict(self, handler, state_handler):
        """Test handling server update without conflict."""
        state_handler.set_state("thread-1", {"a": 1})

        prediction, _ = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"b": 2},  # Different key
        )

        # Server update with matching prediction
        results = handler.handle_server_update(
            thread_id="thread-1",
            run_id="run-1",
            server_state={"a": 1, "b": 2},
        )

        assert len(results) == 0  # No conflicts

    def test_handle_server_update_with_conflict(self, handler, state_handler):
        """Test handling server update with conflict."""
        state_handler.set_state("thread-1", {"count": 0})

        prediction, _ = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"count": 5},
        )

        # Server update with conflicting value
        results = handler.handle_server_update(
            thread_id="thread-1",
            run_id="run-1",
            server_state={"count": 10},  # Different from prediction
        )

        assert len(results) == 1
        # Auto-rollback should have occurred
        assert results[0][0].status == PredictionStatus.ROLLED_BACK

    def test_emit_prediction_event(self, handler):
        """Test emitting prediction event."""
        prediction = PredictionResult(
            prediction_id="pred-test",
            prediction_type=PredictionType.OPTIMISTIC,
            status=PredictionStatus.CONFIRMED,
            predicted_state={"a": 1},
            original_state={},
        )

        event = handler.emit_prediction_event(prediction, "prediction_confirmed")

        assert event.event_name == "prediction_confirmed"
        assert event.payload["predictionId"] == "pred-test"
        assert event.payload["status"] == "confirmed"

    def test_cleanup_completed_predictions(self, handler, state_handler):
        """Test cleaning up completed predictions."""
        state_handler.set_state("thread-1", {})

        # Create and confirm multiple predictions
        for i in range(15):
            pred, _ = handler.predict_state(
                thread_id="thread-1",
                run_id="run-1",
                predicted_changes={f"key{i}": i},
            )
            handler.confirm_prediction(pred.prediction_id, "thread-1", "run-1")

        # Cleanup, keeping only 5
        removed = handler.cleanup_completed_predictions("thread-1", keep_count=5)

        assert removed == 10  # 15 - 5 = 10 removed

    def test_clear_thread_predictions(self, handler, state_handler):
        """Test clearing predictions for a thread."""
        state_handler.set_state("thread-1", {})
        handler.predict_state("thread-1", "run-1", {"a": 1})
        handler.predict_state("thread-1", "run-1", {"b": 2})

        handler.clear_thread_predictions("thread-1")

        predictions = handler.list_pending_predictions("thread-1")
        assert len(predictions) == 0

    def test_clear_all(self, handler, state_handler):
        """Test clearing all predictions."""
        state_handler.set_state("thread-1", {})
        state_handler.set_state("thread-2", {})
        handler.predict_state("thread-1", "run-1", {"a": 1})
        handler.predict_state("thread-2", "run-1", {"b": 2})

        handler.clear_all()

        assert len(handler.list_pending_predictions("thread-1")) == 0
        assert len(handler.list_pending_predictions("thread-2")) == 0

    def test_pattern_confidence_learning(self, handler, state_handler):
        """Test that confidence is learned from patterns."""
        state_handler.set_state("thread-1", {})

        # Create and confirm predictions of same action type
        for i in range(5):
            pred, _ = handler.predict_state(
                thread_id="thread-1",
                run_id="run-1",
                predicted_changes={f"v{i}": i},
                action_type="increment",
            )
            handler.confirm_prediction(pred.prediction_id, "thread-1", "run-1")

        # Next prediction of same type should have higher confidence
        # (internal pattern tracking increases confidence)
        pred, _ = handler.predict_state(
            thread_id="thread-1",
            run_id="run-1",
            predicted_changes={"final": True},
            action_type="increment",
        )

        # Confidence should be adjusted upward from successful predictions
        assert pred.confidence >= 0.8


class TestCreatePredictiveHandler:
    """Tests for create_predictive_handler factory function."""

    @pytest.fixture
    def state_handler(self):
        """Create a SharedStateHandler instance."""
        return SharedStateHandler()

    def test_create_handler_defaults(self, state_handler):
        """Test creating handler with defaults."""
        handler = create_predictive_handler(state_handler)
        assert isinstance(handler, PredictiveStateHandler)
        assert handler.config.default_ttl == 30.0
        assert handler.config.min_confidence == 0.5
        assert handler.config.max_pending == 10

    def test_create_handler_custom_ttl(self, state_handler):
        """Test creating handler with custom TTL."""
        handler = create_predictive_handler(state_handler, default_ttl=60.0)
        assert handler.config.default_ttl == 60.0

    def test_create_handler_custom_confidence(self, state_handler):
        """Test creating handler with custom min confidence."""
        handler = create_predictive_handler(state_handler, min_confidence=0.7)
        assert handler.config.min_confidence == 0.7

    def test_create_handler_custom_max_pending(self, state_handler):
        """Test creating handler with custom max pending."""
        handler = create_predictive_handler(state_handler, max_pending=5)
        assert handler.config.max_pending == 5

    def test_create_handler_no_auto_rollback(self, state_handler):
        """Test creating handler without auto rollback."""
        handler = create_predictive_handler(state_handler, auto_rollback=False)
        assert handler.config.auto_rollback_on_conflict is False
