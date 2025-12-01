"""
Routing Domain Module
======================

This module provides cross-scenario routing capabilities for the IPA Platform,
enabling workflows to trigger other workflows across different business domains.

Sprint 3 - S3-5: Cross-Scenario Collaboration

Features:
- IT Operations to Customer Service routing
- Customer Service to IT Operations routing
- Execution relationship tracking
- Scenario-based workflow mapping

Author: IPA Platform Team
Created: 2025-11-30
"""

from src.domain.routing.scenario_router import (
    ExecutionRelation,
    RelationType,
    RoutingError,
    RoutingResult,
    Scenario,
    ScenarioConfig,
    ScenarioRouter,
)

__all__ = [
    # Types
    "Scenario",
    "RelationType",
    # Configuration
    "ScenarioConfig",
    # Results
    "RoutingResult",
    "ExecutionRelation",
    # Service
    "ScenarioRouter",
    # Exceptions
    "RoutingError",
]
