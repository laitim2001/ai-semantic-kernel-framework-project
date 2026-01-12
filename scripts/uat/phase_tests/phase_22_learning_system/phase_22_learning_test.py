"""
Phase 22: Learning System & Autonomous Capabilities - Test Runner

Sprint 79-80 test execution for:
- S79-1: Claude Autonomous Planning Engine
- S79-2: mem0 Long-term Memory
- S80-1: Few-shot Learning System
- S80-2: Decision Audit Trail
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

from .scenario_fewshot_learning import FewshotLearningScenario
from .scenario_memory_system import MemorySystemScenario
from .scenario_autonomous_planning import AutonomousPlanningScenario


class Phase22TestRunner:
    """
    Phase 22 Test Runner

    Executes all learning system test scenarios.
    """

    def __init__(self, config: PhaseTestConfig = None):
        self.config = config or PhaseTestConfig()
        self.results: List[ScenarioResult] = []

    async def run_all(self) -> List[ScenarioResult]:
        """Run all Phase 22 test scenarios"""

        safe_print("\n" + "=" * 70)
        safe_print("  PHASE 22: LEARNING SYSTEM & AUTONOMOUS CAPABILITIES TESTS")
        safe_print("  Sprints 79-80: Few-shot Learning, Memory, Autonomous Planning")
        safe_print("=" * 70)

        scenarios = [
            FewshotLearningScenario(self.config),
            MemorySystemScenario(self.config),
            AutonomousPlanningScenario(self.config),
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
        safe_print("  PHASE 22 TEST SUMMARY")
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
    runner = Phase22TestRunner(config)
    results = await runner.run_all()

    # Exit with error code if any tests failed
    failed = sum(1 for r in results if r.status.value != "passed")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
