"""
Phase 21: Sandbox Security Architecture - Test Runner

Sprint 77-78 test execution for:
- S77-1: Sandbox Orchestrator
- S77-2: Sandbox Worker
- S78-1: IPC Protocol
- S78-2: Security Isolation
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

from .scenario_sandbox_lifecycle import SandboxLifecycleScenario
from .scenario_security_isolation import SecurityIsolationScenario


class Phase21TestRunner:
    """
    Phase 21 Test Runner

    Executes all sandbox security test scenarios.
    """

    def __init__(self, config: PhaseTestConfig = None):
        self.config = config or PhaseTestConfig()
        self.results: List[ScenarioResult] = []

    async def run_all(self) -> List[ScenarioResult]:
        """Run all Phase 21 test scenarios"""

        safe_print("\n" + "=" * 70)
        safe_print("  PHASE 21: SANDBOX SECURITY ARCHITECTURE TESTS")
        safe_print("  Sprints 77-78: Isolated Execution Environment")
        safe_print("=" * 70)

        scenarios = [
            SandboxLifecycleScenario(self.config),
            SecurityIsolationScenario(self.config),
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
        safe_print("  PHASE 21 TEST SUMMARY")
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
    runner = Phase21TestRunner(config)
    results = await runner.run_all()

    # Exit with error code if any tests failed
    failed = sum(1 for r in results if r.status.value != "passed")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
