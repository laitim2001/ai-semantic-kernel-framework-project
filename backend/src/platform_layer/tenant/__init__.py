"""platform_layer.tenant — SaaS Stage 1 tenant lifecycle infrastructure.

Sprint 56.1 (Phase 56 SaaS Stage 1 / 1-of-3) introduces:
    - lifecycle: TenantLifecycle state machine + IllegalTransitionError
    - provisioning: ProvisioningWorkflow 8-step async runner
    - plans: PlanLoader (enterprise tier only)
    - quota: QuotaEnforcer Redis-backed daily counter middleware
    - onboarding: OnboardingTracker 6-step + health check (US-3 part 1)
"""

from platform_layer.tenant.lifecycle import (
    IllegalTransitionError,
    TenantLifecycle,
)
from platform_layer.tenant.onboarding import (
    VALID_STEPS,
    InvalidOnboardingStepError,
    OnboardingTracker,
)
from platform_layer.tenant.plans import (
    Plan,
    PlanFeatures,
    PlanLoader,
    PlanNotFoundError,
    PlanQuota,
    get_plan_loader,
    reset_plan_loader,
)
from platform_layer.tenant.provisioning import (
    PROVISIONING_STEPS,
    ProvisioningError,
    ProvisioningWorkflow,
)
from platform_layer.tenant.quota import (
    QuotaEnforcer,
    QuotaExceededError,
    get_quota_enforcer,
    maybe_get_quota_enforcer,
    reset_quota_enforcer,
    set_quota_enforcer,
)

__all__ = [
    # lifecycle
    "IllegalTransitionError",
    "TenantLifecycle",
    # provisioning
    "PROVISIONING_STEPS",
    "ProvisioningError",
    "ProvisioningWorkflow",
    # plans
    "Plan",
    "PlanFeatures",
    "PlanLoader",
    "PlanNotFoundError",
    "PlanQuota",
    "get_plan_loader",
    "reset_plan_loader",
    # quota
    "QuotaEnforcer",
    "QuotaExceededError",
    "get_quota_enforcer",
    "maybe_get_quota_enforcer",
    "reset_quota_enforcer",
    "set_quota_enforcer",
    # onboarding
    "VALID_STEPS",
    "InvalidOnboardingStepError",
    "OnboardingTracker",
]
