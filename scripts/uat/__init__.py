# =============================================================================
# UAT Validation Scripts Package
# =============================================================================
# 用於驗證 IPA Platform 功能的自動化測試腳本包。
#
# Author: IPA Platform Team
# Version: 1.0.0
# Created: 2025-12-18
# =============================================================================

"""
UAT Validation Scripts for IPA Platform.

This package contains automated test scripts for validating the 4 core
business scenarios of the IPA Platform:

1. IT Ticket Triage (scenario_001)
2. Multi-Agent Collaboration (scenario_002)
3. Automated Reporting (scenario_003)
4. Autonomous Planning (scenario_004)

Usage:
    # Run all scenarios
    python -m scripts.uat.run_all_scenarios

    # Run specific scenario
    python -m scripts.uat.scenario_001_it_triage

    # Run with pytest
    pytest scripts/uat/ -v
"""

from .base import ScenarioResult, ScenarioTestBase, TestResult, TestStatus
from .scenario_001_it_triage import ITTriageScenarioTest
from .scenario_002_collaboration import CollaborationScenarioTest
from .scenario_003_reporting import ReportingScenarioTest
from .scenario_004_planning import PlanningScenarioTest

__version__ = "1.0.0"
__all__ = [
    # Base classes
    "ScenarioTestBase",
    "ScenarioResult",
    "TestResult",
    "TestStatus",
    # Scenario tests
    "ITTriageScenarioTest",
    "CollaborationScenarioTest",
    "ReportingScenarioTest",
    "PlanningScenarioTest",
]
