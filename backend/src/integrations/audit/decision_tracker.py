# =============================================================================
# IPA Platform - Decision Tracker
# =============================================================================
# Sprint 80: S80-2 - 自主決策審計追蹤 (8 pts)
#
# This module provides decision tracking and audit logging functionality.
# Records all AI decisions with full context and thinking process.
# =============================================================================

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .types import (
    AlternativeConsidered,
    AuditConfig,
    AuditQuery,
    DecisionAudit,
    DecisionContext,
    DecisionOutcome,
    DecisionType,
    QualityRating,
    ThinkingProcess,
    DEFAULT_AUDIT_CONFIG,
)


logger = logging.getLogger(__name__)


class DecisionTracker:
    """
    Tracks and audits AI decisions.

    Provides complete audit trail with:
    - Decision context and input
    - Thinking process (Extended Thinking output)
    - Selected action and alternatives
    - Outcome and quality scoring
    """

    def __init__(self, config: Optional[AuditConfig] = None):
        """
        Initialize the decision tracker.

        Args:
            config: Audit configuration. Uses defaults if not provided.
        """
        self.config = config or DEFAULT_AUDIT_CONFIG
        self._redis = None
        self._decisions: Dict[str, DecisionAudit] = {}  # In-memory store
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the tracker with Redis connection."""
        if self._initialized:
            return

        try:
            if self.config.enable_redis_cache:
                import os
                import redis.asyncio as redis

                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))

                self._redis = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                )

                await self._redis.ping()
                logger.info("Decision tracker connected to Redis")

        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory storage.")
            self._redis = None

        self._initialized = True
        logger.info("DecisionTracker initialized")

    def _ensure_initialized(self) -> None:
        """Ensure the tracker is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "DecisionTracker not initialized. Call initialize() first."
            )

    async def record_decision(
        self,
        decision_type: DecisionType,
        selected_action: str,
        action_details: Dict[str, Any],
        confidence_score: float,
        context: Optional[DecisionContext] = None,
        thinking_process: Optional[ThinkingProcess] = None,
        alternatives: Optional[List[AlternativeConsidered]] = None,
    ) -> DecisionAudit:
        """
        Record a new decision.

        Args:
            decision_type: Type of decision made.
            selected_action: The action that was selected.
            action_details: Details about the action.
            confidence_score: Confidence score (0.0 to 1.0).
            context: Decision context.
            thinking_process: AI thinking process record.
            alternatives: Alternatives that were considered.

        Returns:
            Created DecisionAudit record.
        """
        self._ensure_initialized()

        decision_id = str(uuid4())

        audit = DecisionAudit(
            decision_id=decision_id,
            decision_type=decision_type,
            timestamp=datetime.utcnow(),
            context=context or DecisionContext(),
            thinking_process=thinking_process or ThinkingProcess(),
            selected_action=selected_action,
            action_details=action_details,
            alternatives_considered=alternatives or [],
            confidence_score=confidence_score,
            outcome=DecisionOutcome.PENDING,
        )

        # Store in memory
        self._decisions[decision_id] = audit

        # Store in Redis if available
        if self._redis:
            try:
                key = f"audit:decision:{decision_id}"
                await self._redis.setex(
                    key,
                    self.config.cache_ttl_seconds,
                    json.dumps(audit.to_dict()),
                )
            except Exception as e:
                logger.warning(f"Failed to cache decision in Redis: {e}")

        logger.info(
            f"Recorded decision {decision_id}: {decision_type.value} - {selected_action}"
        )

        return audit

    async def update_outcome(
        self,
        decision_id: str,
        outcome: DecisionOutcome,
        outcome_details: Optional[str] = None,
    ) -> Optional[DecisionAudit]:
        """
        Update the outcome of a decision.

        Args:
            decision_id: ID of the decision to update.
            outcome: The outcome of the decision.
            outcome_details: Details about the outcome.

        Returns:
            Updated DecisionAudit or None if not found.
        """
        self._ensure_initialized()

        audit = await self.get_decision(decision_id)
        if not audit:
            logger.warning(f"Decision {decision_id} not found for outcome update")
            return None

        audit.outcome = outcome
        audit.outcome_details = outcome_details
        audit.updated_at = datetime.utcnow()

        # Auto-score if enabled
        if self.config.auto_score_outcomes:
            audit.quality_score = self._calculate_quality_score(audit)
            audit.quality_rating = self._get_quality_rating(audit.quality_score)

        # Update storage
        self._decisions[decision_id] = audit
        await self._update_redis(audit)

        logger.info(f"Updated outcome for decision {decision_id}: {outcome.value}")

        return audit

    async def add_feedback(
        self,
        decision_id: str,
        feedback: str,
        quality_score: Optional[float] = None,
    ) -> Optional[DecisionAudit]:
        """
        Add feedback to a decision.

        Args:
            decision_id: ID of the decision.
            feedback: Feedback text.
            quality_score: Optional manual quality score.

        Returns:
            Updated DecisionAudit or None if not found.
        """
        self._ensure_initialized()

        audit = await self.get_decision(decision_id)
        if not audit:
            return None

        audit.feedback = feedback
        audit.updated_at = datetime.utcnow()

        if quality_score is not None:
            audit.quality_score = quality_score
            audit.quality_rating = self._get_quality_rating(quality_score)

        # Update storage
        self._decisions[decision_id] = audit
        await self._update_redis(audit)

        logger.info(f"Added feedback to decision {decision_id}")

        return audit

    async def get_decision(self, decision_id: str) -> Optional[DecisionAudit]:
        """
        Get a decision by ID.

        Args:
            decision_id: The decision ID.

        Returns:
            DecisionAudit or None if not found.
        """
        self._ensure_initialized()

        # Check memory first
        if decision_id in self._decisions:
            return self._decisions[decision_id]

        # Check Redis
        if self._redis:
            try:
                key = f"audit:decision:{decision_id}"
                data = await self._redis.get(key)
                if data:
                    audit = DecisionAudit.from_dict(json.loads(data))
                    self._decisions[decision_id] = audit
                    return audit
            except Exception as e:
                logger.warning(f"Failed to get decision from Redis: {e}")

        return None

    async def query_decisions(self, query: AuditQuery) -> List[DecisionAudit]:
        """
        Query decisions based on criteria.

        Args:
            query: Query parameters.

        Returns:
            List of matching DecisionAudit records.
        """
        self._ensure_initialized()

        results = []

        for audit in self._decisions.values():
            if self._matches_query(audit, query):
                results.append(audit)

        # Sort by timestamp descending
        results.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply pagination
        return results[query.offset : query.offset + query.limit]

    def _matches_query(self, audit: DecisionAudit, query: AuditQuery) -> bool:
        """Check if an audit record matches query criteria."""
        if query.user_id and audit.context.user_id != query.user_id:
            return False
        if query.session_id and audit.context.session_id != query.session_id:
            return False
        if query.event_id and audit.context.event_id != query.event_id:
            return False
        if query.plan_id and audit.context.plan_id != query.plan_id:
            return False
        if query.decision_type and audit.decision_type != query.decision_type:
            return False
        if query.outcome and audit.outcome != query.outcome:
            return False
        if query.min_confidence and audit.confidence_score < query.min_confidence:
            return False
        if query.max_confidence and audit.confidence_score > query.max_confidence:
            return False
        if query.start_time and audit.timestamp < query.start_time:
            return False
        if query.end_time and audit.timestamp > query.end_time:
            return False
        return True

    def _calculate_quality_score(self, audit: DecisionAudit) -> float:
        """
        Calculate quality score based on outcome and other factors.

        Args:
            audit: The decision audit record.

        Returns:
            Quality score (0.0 to 1.0).
        """
        base_score = 0.5

        # Outcome factor
        outcome_scores = {
            DecisionOutcome.SUCCESS: 0.3,
            DecisionOutcome.PARTIAL_SUCCESS: 0.15,
            DecisionOutcome.FAILURE: -0.2,
            DecisionOutcome.PENDING: 0.0,
            DecisionOutcome.CANCELLED: -0.1,
        }
        base_score += outcome_scores.get(audit.outcome, 0.0)

        # Confidence alignment factor
        # High confidence + success = good, high confidence + failure = bad
        if audit.outcome == DecisionOutcome.SUCCESS:
            base_score += audit.confidence_score * 0.1
        elif audit.outcome == DecisionOutcome.FAILURE:
            base_score -= audit.confidence_score * 0.1

        # Alternatives consideration factor
        if audit.alternatives_considered:
            base_score += 0.05  # Bonus for considering alternatives

        # Thinking process factor
        if audit.thinking_process.raw_thinking:
            base_score += 0.05  # Bonus for documented thinking

        return max(0.0, min(1.0, base_score))

    def _get_quality_rating(self, score: float) -> QualityRating:
        """Convert quality score to rating."""
        if score >= 0.9:
            return QualityRating.EXCELLENT
        elif score >= 0.7:
            return QualityRating.GOOD
        elif score >= 0.5:
            return QualityRating.ACCEPTABLE
        elif score >= 0.3:
            return QualityRating.POOR
        else:
            return QualityRating.UNACCEPTABLE

    async def _update_redis(self, audit: DecisionAudit) -> None:
        """Update a decision in Redis."""
        if self._redis:
            try:
                key = f"audit:decision:{audit.decision_id}"
                await self._redis.setex(
                    key,
                    self.config.cache_ttl_seconds,
                    json.dumps(audit.to_dict()),
                )
            except Exception as e:
                logger.warning(f"Failed to update decision in Redis: {e}")

    async def get_statistics(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get audit statistics.

        Args:
            user_id: Optional user ID filter.
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            Dictionary with statistics.
        """
        query = AuditQuery(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        decisions = await self.query_decisions(query)

        if not decisions:
            return {
                "total_decisions": 0,
                "by_type": {},
                "by_outcome": {},
                "avg_confidence": 0.0,
                "avg_quality": 0.0,
            }

        # Calculate statistics
        by_type: Dict[str, int] = {}
        by_outcome: Dict[str, int] = {}
        confidence_sum = 0.0
        quality_sum = 0.0
        quality_count = 0

        for d in decisions:
            type_key = d.decision_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            outcome_key = d.outcome.value
            by_outcome[outcome_key] = by_outcome.get(outcome_key, 0) + 1

            confidence_sum += d.confidence_score

            if d.quality_score is not None:
                quality_sum += d.quality_score
                quality_count += 1

        return {
            "total_decisions": len(decisions),
            "by_type": by_type,
            "by_outcome": by_outcome,
            "avg_confidence": confidence_sum / len(decisions),
            "avg_quality": quality_sum / quality_count if quality_count > 0 else 0.0,
            "success_rate": by_outcome.get("success", 0) / len(decisions),
        }

    async def close(self) -> None:
        """Clean up resources."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._initialized = False
        logger.info("DecisionTracker closed")
