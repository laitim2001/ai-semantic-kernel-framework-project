#!/usr/bin/env python
# =============================================================================
# UAT Scenario Runner - 執行所有場景測試
# =============================================================================
# 統一執行 4 個核心業務場景的 UAT 驗證測試。
#
# Usage:
#   python -m scripts.uat.run_all_scenarios
#   python -m scripts.uat.run_all_scenarios --scenario 1
#   python -m scripts.uat.run_all_scenarios --base-url http://api.example.com:8000
#
# Author: IPA Platform Team
# Version: 1.0.0
# Created: 2025-12-18
# =============================================================================

"""
UAT Scenario Runner.

Executes all or selected UAT scenario tests and generates consolidated reports.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import ScenarioResult, ScenarioTestBase, TestStatus
from .scenario_001_it_triage import ITTriageScenarioTest
from .scenario_002_collaboration import CollaborationScenarioTest
from .scenario_003_reporting import ReportingScenarioTest
from .scenario_004_planning import PlanningScenarioTest


# =============================================================================
# Available Scenarios
# =============================================================================

SCENARIOS: Dict[int, Type[ScenarioTestBase]] = {
    1: ITTriageScenarioTest,
    2: CollaborationScenarioTest,
    3: ReportingScenarioTest,
    4: PlanningScenarioTest,
}

SCENARIO_NAMES = {
    1: "IT Ticket Triage",
    2: "Multi-Agent Collaboration",
    3: "Automated Reporting",
    4: "Autonomous Planning",
}


def safe_print(text: str):
    """Print text with fallback for encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))


# =============================================================================
# Runner Functions
# =============================================================================

async def run_single_scenario(
    scenario_class: Type[ScenarioTestBase],
    base_url: str,
    timeout: float,
    verbose: bool,
) -> ScenarioResult:
    """Run a single scenario test."""
    scenario = scenario_class(
        base_url=base_url,
        timeout=timeout,
        verbose=verbose,
    )
    return await scenario.run()


async def run_all_scenarios(
    base_url: str,
    timeout: float,
    verbose: bool,
    scenario_ids: Optional[List[int]] = None,
) -> List[ScenarioResult]:
    """
    Run all or selected scenario tests.

    Args:
        base_url: API base URL
        timeout: Request timeout
        verbose: Verbose output
        scenario_ids: List of scenario IDs to run (None = all)

    Returns:
        List of ScenarioResult
    """
    results = []

    scenarios_to_run = scenario_ids or list(SCENARIOS.keys())

    for scenario_id in scenarios_to_run:
        if scenario_id not in SCENARIOS:
            safe_print(f"[WARN] Unknown scenario ID: {scenario_id}, skipping")
            continue

        scenario_class = SCENARIOS[scenario_id]
        scenario_name = SCENARIO_NAMES.get(scenario_id, f"Scenario {scenario_id}")

        if verbose:
            safe_print(f"\n{'='*70}")
            safe_print(f" Running Scenario {scenario_id}: {scenario_name}")
            safe_print(f"{'='*70}")

        result = await run_single_scenario(
            scenario_class=scenario_class,
            base_url=base_url,
            timeout=timeout,
            verbose=verbose,
        )
        results.append(result)

    return results


def generate_summary_report(results: List[ScenarioResult]) -> Dict:
    """Generate consolidated summary report."""
    total_scenarios = len(results)
    passed_scenarios = sum(1 for r in results if r.status == TestStatus.PASSED)
    failed_scenarios = sum(1 for r in results if r.status in [TestStatus.FAILED, TestStatus.ERROR])

    total_tests = sum(r.total_tests for r in results)
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    total_skipped = sum(r.skipped for r in results)
    total_duration = sum(r.duration_ms for r in results)

    return {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "scenarios": {
                "total": total_scenarios,
                "passed": passed_scenarios,
                "failed": failed_scenarios,
                "pass_rate": passed_scenarios / total_scenarios if total_scenarios > 0 else 0,
            },
            "tests": {
                "total": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "pass_rate": total_passed / total_tests if total_tests > 0 else 0,
            },
            "total_duration_ms": total_duration,
            "total_duration_formatted": f"{total_duration / 1000:.2f}s",
        },
        "scenarios": [r.to_dict() for r in results],
    }


def print_summary(results: List[ScenarioResult]):
    """Print summary to console."""
    safe_print("\n" + "=" * 70)
    safe_print(" UAT EXECUTION SUMMARY")
    safe_print("=" * 70)

    total_scenarios = len(results)
    passed_scenarios = sum(1 for r in results if r.status == TestStatus.PASSED)
    failed_scenarios = total_scenarios - passed_scenarios

    total_tests = sum(r.total_tests for r in results)
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    total_duration = sum(r.duration_ms for r in results)

    safe_print(f"\n Scenarios: {passed_scenarios}/{total_scenarios} passed")
    safe_print(f" Tests:     {total_passed}/{total_tests} passed")
    safe_print(f" Duration:  {total_duration / 1000:.2f}s")

    safe_print("\n" + "-" * 70)
    safe_print(" SCENARIO RESULTS:")
    safe_print("-" * 70)

    for result in results:
        status_icon = "[PASS]" if result.status == TestStatus.PASSED else "[FAIL]"
        safe_print(f" {status_icon} {result.scenario_name}")
        safe_print(f"    Tests: {result.passed}/{result.total_tests} passed | Duration: {result.duration_ms:.0f}ms")

    safe_print("\n" + "-" * 70)
    overall_status = "ALL SCENARIOS PASSED" if failed_scenarios == 0 else f"{failed_scenarios} SCENARIO(S) FAILED"
    safe_print(f" {overall_status}")
    safe_print("-" * 70 + "\n")


def save_report(report: Dict, output_dir: str = "claudedocs/uat/sessions") -> str:
    """Save report to file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"uat_full_report_{timestamp}.json"
    filepath = output_path / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    safe_print(f"[INFO] Full report saved to: {filepath}")
    return str(filepath)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="IPA Platform UAT Scenario Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run all scenarios:
    python -m scripts.uat.run_all_scenarios

  Run specific scenario:
    python -m scripts.uat.run_all_scenarios --scenario 1

  Run multiple scenarios:
    python -m scripts.uat.run_all_scenarios --scenario 1 --scenario 2

  Run with custom API URL:
    python -m scripts.uat.run_all_scenarios --base-url http://api.example.com:8000

  Save report to file:
    python -m scripts.uat.run_all_scenarios --save-report

Available Scenarios:
  1 - IT 工單智能分派 (IT Ticket Triage)
  2 - 多 Agent 協作分析 (Multi-Agent Collaboration)
  3 - 自動化報表生成 (Automated Reporting)
  4 - 複雜任務自主規劃 (Autonomous Planning)
        """,
    )

    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--scenario",
        type=int,
        action="append",
        dest="scenarios",
        help="Scenario ID(s) to run (1-4). Can be specified multiple times.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output (default: True)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save report to file",
    )
    parser.add_argument(
        "--output-dir",
        default="claudedocs/uat/sessions",
        help="Output directory for reports (default: claudedocs/uat/sessions)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Handle verbose/quiet
    verbose = args.verbose and not args.quiet

    # Print header
    if verbose:
        safe_print("\n" + "=" * 70)
        safe_print(" IPA Platform - UAT Scenario Validation")
        safe_print(f" Target: {args.base_url}")
        safe_print(f" Timestamp: {datetime.now().isoformat()}")
        safe_print("=" * 70)

    # Run scenarios
    async def run():
        return await run_all_scenarios(
            base_url=args.base_url,
            timeout=args.timeout,
            verbose=verbose,
            scenario_ids=args.scenarios,
        )

    results = asyncio.run(run())

    # Generate report
    report = generate_summary_report(results)

    # Output results
    if args.json:
        safe_print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_summary(results)

    # Save report if requested
    if args.save_report:
        save_report(report, args.output_dir)

    # Exit with appropriate code
    all_passed = all(r.status == TestStatus.PASSED for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
