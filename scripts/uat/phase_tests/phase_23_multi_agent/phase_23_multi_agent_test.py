"""
Phase 23: Multi-Agent Coordination - Test Runner

Sprint 81-82 test execution for:
- S81-1: Claude-led Multi-Agent Coordination
- S81-2: A2A Communication Protocol
- S82-1: Proactive Patrol Mode
- S82-2: Intelligent Correlation & Root Cause Analysis
"""

import asyncio
import sys
from pathlib import Path
from typing import List

# Support both module and script execution
try:
    from ..base import ScenarioResult, safe_print
    from ..config import PhaseTestConfig
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base import ScenarioResult, safe_print
    from config import PhaseTestConfig

from .scenario_a2a_protocol import A2AProtocolScenario
from .scenario_patrol_mode import PatrolModeScenario
from .scenario_correlation_analysis import CorrelationAnalysisScenario
from .scenario_rootcause_analysis import RootCauseAnalysisScenario


class Phase23TestRunner:
    """
    Phase 23 Test Runner

    Executes all multi-agent coordination test scenarios.
    """

    def __init__(self, config: PhaseTestConfig = None):
        self.config = config or PhaseTestConfig()
        self.results: List[ScenarioResult] = []

    async def run_all(self) -> List[ScenarioResult]:
        """Run all Phase 23 test scenarios"""

        safe_print("\n" + "=" * 70)
        safe_print("  PHASE 23: MULTI-AGENT COORDINATION TESTS")
        safe_print("  Sprints 81-82: A2A Protocol, Patrol, Correlation, Root Cause")
        safe_print("=" * 70)

        scenarios = [
            A2AProtocolScenario(self.config),
            PatrolModeScenario(self.config),
            CorrelationAnalysisScenario(self.config),
            RootCauseAnalysisScenario(self.config),
        ]

        for scenario in scenarios:
            result = await scenario.run()
            self.results.append(result)
            scenario.save_results()

        self._print_summary()
        return self.results

    def _print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status.value == "passed")
        failed = total - passed

        safe_print("\n" + "=" * 70)
        safe_print("  PHASE 23 TEST SUMMARY")
        safe_print("=" * 70)
        safe_print(f"  Total Scenarios: {total}")
        safe_print(f"  [PASS] Passed: {passed}")
        safe_print(f"  [FAIL] Failed: {failed}")
        safe_print("=" * 70)

        for result in self.results:
            status_icon = "[PASS]" if result.status.value == "passed" else "[FAIL]"
            safe_print(f"  {status_icon} {result.scenario_name}")
            safe_print(f"       Steps: {result.passed}/{result.total_steps} passed")
            safe_print(f"       Duration: {result.duration_ms:.1f}ms")


async def main():
    """Main entry point"""
    config = PhaseTestConfig()
    runner = Phase23TestRunner(config)
    results = await runner.run_all()

    # Exit with error code if any tests failed
    failed = sum(1 for r in results if r.status.value != "passed")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
