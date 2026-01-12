"""
Phase Tests Runner - 統一執行所有 Phase 測試

執行方式：
    python run_all_phase_tests.py              # 執行所有測試
    python run_all_phase_tests.py --phase 8    # 只執行 Phase 8
    python run_all_phase_tests.py --phase 9 10 # 執行 Phase 9 和 10
    python run_all_phase_tests.py --no-llm     # 不使用真實 LLM
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import List, Dict, Any

from config import PhaseTestConfig
from base import ScenarioResult

# Phase 測試模組
from phase_8_code_interpreter.scenario_financial_analysis import FinancialAnalysisScenario
from phase_9_mcp_architecture.scenario_infra_diagnostics import InfraDiagnosticsScenario
from phase_10_session_mode.scenario_tech_support import TechSupportSessionScenario

# Phase 21-23 測試模組
from phase_21_sandbox_security.scenario_sandbox_lifecycle import SandboxLifecycleScenario
from phase_21_sandbox_security.scenario_security_isolation import SecurityIsolationScenario
from phase_22_learning_system.scenario_fewshot_learning import FewshotLearningScenario
from phase_22_learning_system.scenario_memory_system import MemorySystemScenario
from phase_22_learning_system.scenario_autonomous_planning import AutonomousPlanningScenario
from phase_23_multi_agent.scenario_a2a_protocol import A2AProtocolScenario
from phase_23_multi_agent.scenario_patrol_mode import PatrolModeScenario
from phase_23_multi_agent.scenario_correlation_analysis import CorrelationAnalysisScenario
from phase_23_multi_agent.scenario_rootcause_analysis import RootCauseAnalysisScenario


class PhaseTestRunner:
    """Phase 測試執行器"""

    def __init__(self, config: PhaseTestConfig):
        self.config = config
        self.results: List[ScenarioResult] = []

        # 註冊所有測試場景
        self.scenarios = {
            8: ("Code Interpreter - Financial Analysis", FinancialAnalysisScenario),
            9: ("MCP Architecture - Infrastructure Diagnostics", InfraDiagnosticsScenario),
            10: ("Session Mode - Technical Support", TechSupportSessionScenario),
            # Phase 21: Sandbox Security
            21: ("Sandbox Security - Lifecycle & Isolation", [
                SandboxLifecycleScenario,
                SecurityIsolationScenario,
            ]),
            # Phase 22: Learning System
            22: ("Learning System - Few-shot, Memory, Autonomous", [
                FewshotLearningScenario,
                MemorySystemScenario,
                AutonomousPlanningScenario,
            ]),
            # Phase 23: Multi-Agent Coordination
            23: ("Multi-Agent - A2A, Patrol, Correlation, RCA", [
                A2AProtocolScenario,
                PatrolModeScenario,
                CorrelationAnalysisScenario,
                RootCauseAnalysisScenario,
            ]),
        }

    async def run_phase(self, phase: int) -> List[ScenarioResult]:
        """執行單個 Phase 測試"""
        if phase not in self.scenarios:
            raise ValueError(f"Unknown phase: {phase}")

        name, scenario_classes = self.scenarios[phase]
        print(f"\n{'='*60}")
        print(f"Running Phase {phase}: {name}")
        print(f"{'='*60}")

        phase_results = []

        # 處理單個場景或多個場景列表
        if isinstance(scenario_classes, list):
            for scenario_class in scenario_classes:
                scenario = scenario_class(self.config)
                result = await scenario.run()
                phase_results.append(result)
                self.results.append(result)
        else:
            scenario = scenario_classes(self.config)
            result = await scenario.execute()
            phase_results.append(result)
            self.results.append(result)

        return phase_results

    async def run_all(self, phases: List[int] = None) -> Dict[str, Any]:
        """執行多個 Phase 測試"""
        if phases is None:
            phases = list(self.scenarios.keys())

        start_time = datetime.now()

        for phase in sorted(phases):
            try:
                await self.run_phase(phase)
            except Exception as e:
                print(f"[FAIL] Phase {phase} failed with exception: {e}")
                # 創建失敗結果
                self.results.append(ScenarioResult(
                    scenario_name=f"Phase {phase}",
                    phase=phase,
                    success=False,
                    steps=[],
                    steps_passed=0,
                    steps_total=0,
                    duration_seconds=0,
                    metadata={"error": str(e)}
                ))

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        return self._generate_summary(total_duration)

    def _generate_summary(self, total_duration: float) -> Dict[str, Any]:
        """生成測試摘要"""
        # 支援新舊兩種 ScenarioResult 格式
        def is_passed(r):
            if hasattr(r, 'success'):
                return r.success
            elif hasattr(r, 'status'):
                return r.status.value == 'passed'
            return False

        def get_steps_total(r):
            if hasattr(r, 'steps_total'):
                return r.steps_total
            elif hasattr(r, 'total_steps'):
                return r.total_steps
            return 0

        def get_steps_passed(r):
            if hasattr(r, 'steps_passed'):
                return r.steps_passed
            elif hasattr(r, 'passed'):
                return r.passed
            return 0

        def get_duration(r):
            if hasattr(r, 'duration_seconds'):
                return r.duration_seconds
            elif hasattr(r, 'duration_ms'):
                return r.duration_ms / 1000
            return 0

        def get_phase(r):
            if hasattr(r, 'phase'):
                if hasattr(r.phase, 'value'):
                    # Extract phase number from enum value like "phase_21_sandbox_security"
                    phase_str = r.phase.value
                    parts = phase_str.split('_')
                    for part in parts:
                        if part.isdigit():
                            return int(part)
                return r.phase
            return 0

        passed_scenarios = sum(1 for r in self.results if is_passed(r))
        total_scenarios = len(self.results)

        total_steps = sum(get_steps_total(r) for r in self.results)
        passed_steps = sum(get_steps_passed(r) for r in self.results)

        summary = {
            "run_time": datetime.now().isoformat(),
            "total_duration_seconds": total_duration,
            "config": {
                "use_real_llm": self.config.use_real_llm,
                "llm_provider": self.config.llm_provider,
                "llm_deployment": self.config.llm_deployment
            },
            "overall_results": {
                "scenarios_passed": passed_scenarios,
                "scenarios_total": total_scenarios,
                "steps_passed": passed_steps,
                "steps_total": total_steps,
                "success_rate": f"{(passed_scenarios/total_scenarios*100):.1f}%" if total_scenarios > 0 else "N/A"
            },
            "phase_results": [
                {
                    "phase": get_phase(r),
                    "scenario": r.scenario_name,
                    "success": is_passed(r),
                    "steps_passed": get_steps_passed(r),
                    "steps_total": get_steps_total(r),
                    "duration_seconds": get_duration(r)
                }
                for r in self.results
            ]
        }

        return summary


def print_summary(summary: Dict[str, Any]):
    """打印測試摘要"""
    print("\n" + "=" * 60)
    print("PHASE TESTS SUMMARY")
    print("=" * 60)

    overall = summary["overall_results"]
    print(f"\n[DATA] Overall Results:")
    # Support both old and new keys
    scenarios_passed = overall.get('scenarios_passed', overall.get('phases_passed', 0))
    scenarios_total = overall.get('scenarios_total', overall.get('phases_total', 0))
    print(f"   Scenarios: {scenarios_passed}/{scenarios_total} passed")
    print(f"   Steps:  {overall['steps_passed']}/{overall['steps_total']} passed")
    print(f"   Success Rate: {overall['success_rate']}")
    print(f"   Total Duration: {summary['total_duration_seconds']:.2f}s")

    print(f"\n[CONFIG] Configuration:")
    config = summary["config"]
    print(f"   Use Real LLM: {config['use_real_llm']}")
    print(f"   LLM Provider: {config['llm_provider']}")
    print(f"   LLM Deployment: {config['llm_deployment']}")

    print(f"\n[RESULTS] Phase Results:")
    for result in summary["phase_results"]:
        status = "[PASS]" if result["success"] else "[FAIL]"
        print(f"   {status} Phase {result['phase']}: {result['scenario']}")
        print(f"      Steps: {result['steps_passed']}/{result['steps_total']}, Duration: {result['duration_seconds']:.2f}s")

    # 總結狀態
    all_passed = all(r["success"] for r in summary["phase_results"])
    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] ALL PHASE TESTS PASSED!")
    else:
        failed = [r["phase"] for r in summary["phase_results"] if not r["success"]]
        print(f"[WARNING] Some phases failed: {failed}")
    print("=" * 60)


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="Run Phase Tests")
    parser.add_argument(
        "--phase", "-p",
        type=int,
        nargs="+",
        help="Specific phase(s) to run (8, 9, 10, 21, 22, 23)"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable real LLM calls (use simulation)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for results (JSON)"
    )

    args = parser.parse_args()

    # 配置
    config = PhaseTestConfig(
        use_real_llm=not args.no_llm,
        llm_provider="azure",
        llm_deployment="gpt-5.2"
    )

    # 創建執行器
    runner = PhaseTestRunner(config)

    # 執行測試
    phases = args.phase if args.phase else None
    summary = await runner.run_all(phases)

    # 打印摘要
    print_summary(summary)

    # 保存結果
    output_file = args.output or f"phase_tests_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n[FILE] Results saved to: {output_file}")

    # 返回退出碼
    all_passed = all(r["success"] for r in summary["phase_results"])
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
