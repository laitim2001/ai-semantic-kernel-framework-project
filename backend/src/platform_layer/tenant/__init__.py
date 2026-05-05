"""platform_layer.tenant — SaaS Stage 1 tenant lifecycle infrastructure.

Sprint 56.1 (Phase 56 SaaS Stage 1 / 1-of-3) introduces:
    - lifecycle: TenantLifecycle state machine + IllegalTransitionError
    - provisioning: ProvisioningWorkflow 8-step async runner
    - plans: PlanLoader (enterprise tier only)
    - quota: QuotaEnforcer Redis-backed daily counter middleware
    - onboarding: OnboardingTracker 6-step + health check
"""
