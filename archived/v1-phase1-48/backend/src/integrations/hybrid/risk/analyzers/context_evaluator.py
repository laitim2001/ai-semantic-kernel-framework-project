# =============================================================================
# IPA Platform - Context Evaluator
# =============================================================================
# Sprint 55: Risk Assessment Engine - S55-3
#
# Evaluates context-based risk factors including:
#   - User trust level assessment
#   - Environment risk multipliers
#   - Session context evaluation
#   - Historical behavior analysis
#
# Dependencies:
#   - RiskFactor, RiskFactorType, OperationContext
#     (src.integrations.hybrid.risk.models)
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from ..models import OperationContext, RiskFactor, RiskFactorType


class UserTrustLevel(str, Enum):
    """User trust levels for risk assessment."""

    NEW = "new"           # New user, no history (highest risk)
    LOW = "low"           # Limited history, some violations
    MEDIUM = "medium"     # Moderate history, few issues
    HIGH = "high"         # Long history, good behavior
    TRUSTED = "trusted"   # Verified trusted user (lowest risk)


@dataclass
class UserProfile:
    """User profile for trust assessment."""

    user_id: str
    trust_level: UserTrustLevel = UserTrustLevel.NEW
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    total_operations: int = 0
    successful_operations: int = 0
    violations: int = 0
    high_risk_operations: int = 0
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """Session context for evaluation."""

    session_id: str
    user_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    operation_count: int = 0
    sensitive_operation_count: int = 0
    high_risk_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    current_risk_level: str = "LOW"
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class ContextEvaluatorConfig:
    """Configuration for context evaluation."""

    # Trust level risk multipliers
    trust_multipliers: Dict[UserTrustLevel, float] = field(default_factory=lambda: {
        UserTrustLevel.NEW: 1.3,      # New users have higher risk
        UserTrustLevel.LOW: 1.2,
        UserTrustLevel.MEDIUM: 1.0,
        UserTrustLevel.HIGH: 0.85,
        UserTrustLevel.TRUSTED: 0.7,  # Trusted users have lower risk
    })

    # Environment risk multipliers
    environment_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "development": 0.8,   # Lower risk in development
        "staging": 1.0,       # Baseline
        "production": 1.3,    # Higher risk in production
        "testing": 0.7,       # Lowest risk in testing
    })

    # Session thresholds
    high_risk_session_threshold: int = 5  # Max high-risk operations per session
    sensitive_operation_threshold: int = 10  # Max sensitive operations per session

    # Trust level thresholds
    trust_upgrade_operations: int = 100  # Operations needed for trust upgrade
    trust_downgrade_violations: int = 3  # Violations for trust downgrade

    # Weight for context-based risk factors
    weight: float = 0.25


class ContextEvaluator:
    """
    Evaluates context-based risk factors.

    Analyzes user trust level, session behavior, and environment
    to contribute context-aware risk factors.

    Attributes:
        config: Configuration for evaluation
        user_profiles: Cached user profiles (in production, use database)
        sessions: Active session contexts

    Example:
        >>> evaluator = ContextEvaluator()
        >>> context = OperationContext(
        ...     tool_name="Bash",
        ...     user_id="user123",
        ...     session_id="sess456"
        ... )
        >>> factors = evaluator.analyze(context)
        >>> for factor in factors:
        ...     print(f"{factor.factor_type}: {factor.score}")
    """

    def __init__(self, config: Optional[ContextEvaluatorConfig] = None):
        """
        Initialize ContextEvaluator with configuration.

        Args:
            config: Configuration for evaluation
        """
        self.config = config or ContextEvaluatorConfig()
        self.user_profiles: Dict[str, UserProfile] = {}
        self.sessions: Dict[str, SessionContext] = {}

    def analyze(self, context: OperationContext) -> List[RiskFactor]:
        """
        Analyze operation context for risk factors.

        Evaluates user trust, session behavior, and environment
        to identify potential context-based risks.

        Args:
            context: The operation context to analyze

        Returns:
            List of identified risk factors
        """
        factors: List[RiskFactor] = []

        # Analyze user trust level
        user_factor = self._analyze_user_trust(context)
        if user_factor:
            factors.append(user_factor)

        # Analyze environment risk
        env_factor = self._analyze_environment(context)
        if env_factor:
            factors.append(env_factor)

        # Analyze session context
        session_factors = self._analyze_session(context)
        factors.extend(session_factors)

        return factors

    def _analyze_user_trust(self, context: OperationContext) -> Optional[RiskFactor]:
        """Analyze user trust level risk."""
        user_id = context.user_id
        if not user_id:
            # No user ID means unknown user - treat as new
            return RiskFactor(
                factor_type=RiskFactorType.USER,
                score=0.6,  # Higher score for unknown user
                weight=self.config.weight,
                description="Unknown user (no user ID provided)",
                metadata={"user_id": None, "trust_level": "unknown"}
            )

        # Get or create user profile
        profile = self._get_or_create_profile(user_id)

        # Calculate trust-based risk score
        trust_multiplier = self.config.trust_multipliers.get(
            profile.trust_level, 1.0
        )
        # Base score is 0.3 (neutral), adjusted by trust level
        base_score = 0.3
        adjusted_score = min(1.0, max(0.0, base_score * trust_multiplier))

        return RiskFactor(
            factor_type=RiskFactorType.USER,
            score=adjusted_score,
            weight=self.config.weight,
            description=f"User trust level: {profile.trust_level.value}",
            source=user_id,
            metadata={
                "user_id": user_id,
                "trust_level": profile.trust_level.value,
                "total_operations": profile.total_operations,
                "violations": profile.violations
            }
        )

    def _analyze_environment(self, context: OperationContext) -> Optional[RiskFactor]:
        """Analyze environment-based risk."""
        environment = context.environment or "development"
        multiplier = self.config.environment_multipliers.get(environment, 1.0)

        # Higher environments have higher base risk
        if environment == "production":
            base_score = 0.5
        elif environment == "staging":
            base_score = 0.3
        else:
            base_score = 0.15

        return RiskFactor(
            factor_type=RiskFactorType.ENVIRONMENT,
            score=base_score,
            weight=self.config.weight,
            description=f"Environment: {environment} (multiplier: {multiplier})",
            source=environment,
            metadata={
                "environment": environment,
                "multiplier": multiplier
            }
        )

    def _analyze_session(self, context: OperationContext) -> List[RiskFactor]:
        """Analyze session context for risk factors."""
        factors: List[RiskFactor] = []

        session_id = context.session_id
        if not session_id:
            return factors

        # Get or create session context
        session = self._get_or_create_session(session_id, context.user_id or "unknown")

        # Check for excessive high-risk operations
        if session.high_risk_count >= self.config.high_risk_session_threshold:
            factors.append(RiskFactor(
                factor_type=RiskFactorType.CONTEXT,
                score=0.7,
                weight=self.config.weight,
                description=f"Session has {session.high_risk_count} high-risk operations",
                source=session_id,
                metadata={
                    "session_id": session_id,
                    "high_risk_count": session.high_risk_count,
                    "threshold": self.config.high_risk_session_threshold
                }
            ))

        # Check for excessive sensitive operations
        if session.sensitive_operation_count >= self.config.sensitive_operation_threshold:
            factors.append(RiskFactor(
                factor_type=RiskFactorType.CONTEXT,
                score=0.5,
                weight=self.config.weight,
                description=f"Session has {session.sensitive_operation_count} sensitive operations",
                source=session_id,
                metadata={
                    "session_id": session_id,
                    "sensitive_count": session.sensitive_operation_count,
                    "threshold": self.config.sensitive_operation_threshold
                }
            ))

        # Check for high rejection rate
        if session.rejected_count > 0 and session.operation_count > 0:
            rejection_rate = session.rejected_count / session.operation_count
            if rejection_rate > 0.3:  # More than 30% rejected
                factors.append(RiskFactor(
                    factor_type=RiskFactorType.CONTEXT,
                    score=0.6,
                    weight=self.config.weight,
                    description=f"High rejection rate in session: {rejection_rate:.1%}",
                    source=session_id,
                    metadata={
                        "session_id": session_id,
                        "rejection_rate": rejection_rate,
                        "rejected_count": session.rejected_count
                    }
                ))

        return factors

    def _get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get or create a user profile."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id=user_id)
        return self.user_profiles[user_id]

    def _get_or_create_session(self, session_id: str, user_id: str) -> SessionContext:
        """Get or create a session context."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionContext(
                session_id=session_id,
                user_id=user_id
            )
        return self.sessions[session_id]

    def update_user_trust(
        self,
        user_id: str,
        operation_success: bool,
        is_violation: bool = False,
        is_high_risk: bool = False
    ) -> UserTrustLevel:
        """
        Update user trust level based on operation outcome.

        Args:
            user_id: User identifier
            operation_success: Whether operation succeeded
            is_violation: Whether operation was a policy violation
            is_high_risk: Whether operation was high-risk

        Returns:
            Updated trust level
        """
        profile = self._get_or_create_profile(user_id)
        profile.total_operations += 1
        profile.last_activity = datetime.utcnow()

        if operation_success:
            profile.successful_operations += 1
        if is_violation:
            profile.violations += 1
        if is_high_risk:
            profile.high_risk_operations += 1

        # Evaluate trust level changes
        self._evaluate_trust_change(profile)

        return profile.trust_level

    def _evaluate_trust_change(self, profile: UserProfile) -> None:
        """Evaluate and update user trust level."""
        # Check for downgrade due to violations
        if profile.violations >= self.config.trust_downgrade_violations:
            if profile.trust_level == UserTrustLevel.TRUSTED:
                profile.trust_level = UserTrustLevel.HIGH
            elif profile.trust_level == UserTrustLevel.HIGH:
                profile.trust_level = UserTrustLevel.MEDIUM
            elif profile.trust_level == UserTrustLevel.MEDIUM:
                profile.trust_level = UserTrustLevel.LOW
            profile.violations = 0  # Reset after downgrade

        # Check for upgrade based on operations
        if profile.total_operations >= self.config.trust_upgrade_operations:
            success_rate = profile.successful_operations / profile.total_operations
            if success_rate > 0.95 and profile.violations == 0:
                if profile.trust_level == UserTrustLevel.NEW:
                    profile.trust_level = UserTrustLevel.LOW
                elif profile.trust_level == UserTrustLevel.LOW:
                    profile.trust_level = UserTrustLevel.MEDIUM
                elif profile.trust_level == UserTrustLevel.MEDIUM:
                    profile.trust_level = UserTrustLevel.HIGH

    def update_session(
        self,
        session_id: str,
        is_sensitive: bool = False,
        is_high_risk: bool = False,
        is_approved: bool = True
    ) -> None:
        """
        Update session context with operation outcome.

        Args:
            session_id: Session identifier
            is_sensitive: Whether operation was sensitive
            is_high_risk: Whether operation was high-risk
            is_approved: Whether operation was approved
        """
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]
        session.operation_count += 1

        if is_sensitive:
            session.sensitive_operation_count += 1
        if is_high_risk:
            session.high_risk_count += 1
        if is_approved:
            session.approved_count += 1
        else:
            session.rejected_count += 1

    def get_user_trust_level(self, user_id: str) -> UserTrustLevel:
        """
        Get the trust level for a user.

        Args:
            user_id: User identifier

        Returns:
            User's trust level
        """
        profile = self._get_or_create_profile(user_id)
        return profile.trust_level

    def set_user_trust_level(self, user_id: str, trust_level: UserTrustLevel) -> None:
        """
        Manually set a user's trust level.

        Args:
            user_id: User identifier
            trust_level: New trust level
        """
        profile = self._get_or_create_profile(user_id)
        profile.trust_level = trust_level

    def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """
        Get session context by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session context or None if not found
        """
        return self.sessions.get(session_id)

    def clear_session(self, session_id: str) -> None:
        """
        Clear a session context.

        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_environment_multiplier(self, environment: str) -> float:
        """
        Get the risk multiplier for an environment.

        Args:
            environment: Environment name

        Returns:
            Risk multiplier for the environment
        """
        return self.config.environment_multipliers.get(environment, 1.0)
