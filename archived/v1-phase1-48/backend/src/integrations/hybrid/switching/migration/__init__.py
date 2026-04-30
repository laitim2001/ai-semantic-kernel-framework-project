# =============================================================================
# IPA Platform - State Migration Module
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-3 State Migration
#
# Provides reliable state migration between execution modes.
#
# Key Components:
#   - StateMigrator: Core migration logic
#   - MigratedState: Migration result model
#   - MigrationValidator: Validation logic
#
# Dependencies:
#   - HybridContext (src.integrations.hybrid.context)
#   - ExecutionMode (src.integrations.hybrid.intent.models)
# =============================================================================

from .state_migrator import (
    MigratedState,
    MigrationConfig,
    MigrationError,
    MigrationValidator,
    StateMigrator,
)

__all__ = [
    "StateMigrator",
    "MigratedState",
    "MigrationConfig",
    "MigrationValidator",
    "MigrationError",
]
