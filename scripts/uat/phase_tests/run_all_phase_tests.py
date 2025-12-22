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
        }

    async def run_phase(self, phase: int) -> ScenarioResult:
        """執行單個 Phase 測試"""
        if phase not in self.scenarios:
            raise ValueError(f"Unknown phase: {phase}")

        name, scenario_class = self.scenarios[phase]
        print(f"\n{'='*60}")
        print(f"Running Phase {phase}: {name}")
        print(f"{'='*60}")

        scenario = scenario_class(self.config)
        result = await scenario.execute()
        self.results.append(result)

        return result

    async def run_all(self, phases: List[int] = None) -> Dict[str, Any]:
        """執行多個 Phase 測試"""
        if phases is None:
            phases = list(self.scenarios.keys())

        start_time = datetime.now()

        for phase in sorted(phases):
            try:
                await self.run_phase(phase)
            except Exception as e:
                print(f"❌ Phase {phase} failed with exception: {e}")
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
        passed_phases = sum(1 for r in self.results if r.success)
        total_phases = len(self.results)

        total_steps = sum(r.steps_total for r in self.results)
        passed_steps = sum(r.steps_passed for r in self.results)

        summary = {
            "run_time": datetime.now().isoformat(),
            "total_duration_seconds": total_duration,
            "config": {
                "use_real_llm": self.config.use_real_llm,
                "llm_provider": self.config.llm_provider,
                "llm_deployment": self.config.llm_deployment
            },
            "overall_results": {
                "phases_passed": passed_phases,
                "phases_total": total_phases,
                "steps_passed": passed_steps,
                "steps_total": total_steps,
                "success_rate": f"{(passed_phases/total_phases*100):.1f}%" if total_phases > 0 else "N/A"
            },
            "phase_results": [
                {
                    "phase": r.phase,
                    "scenario": r.scenario_name,
                    "success": r.success,
                    "steps_passed": r.steps_passed,
                    "steps_total": r.steps_total,
                    "duration_seconds": r.duration_seconds
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
    print(f"\n📊 Overall Results:")
    print(f"   Phases: {overall['phases_passed']}/{overall['phases_total']} passed")
    print(f"   Steps:  {overall['steps_passed']}/{overall['steps_total']} passed")
    print(f"   Success Rate: {overall['success_rate']}")
    print(f"   Total Duration: {summary['total_duration_seconds']:.2f}s")

    print(f"\n📋 Configuration:")
    config = summary["config"]
    print(f"   Use Real LLM: {config['use_real_llm']}")
    print(f"   LLM Provider: {config['llm_provider']}")
    print(f"   LLM Deployment: {config['llm_deployment']}")

    print(f"\n📑 Phase Results:")
    for result in summary["phase_results"]:
        status = "✅" if result["success"] else "❌"
        print(f"   {status} Phase {result['phase']}: {result['scenario']}")
        print(f"      Steps: {result['steps_passed']}/{result['steps_total']}, Duration: {result['duration_seconds']:.2f}s")

    # 總結狀態
    all_passed = all(r["success"] for r in summary["phase_results"])
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL PHASE TESTS PASSED!")
    else:
        failed = [r["phase"] for r in summary["phase_results"] if not r["success"]]
        print(f"⚠️  Some phases failed: {failed}")
    print("=" * 60)


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="Run Phase Tests")
    parser.add_argument(
        "--phase", "-p",
        type=int,
        nargs="+",
        help="Specific phase(s) to run (8, 9, 10)"
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
    print(f"\n📄 Results saved to: {output_file}")

    # 返回退出碼
    all_passed = all(r["success"] for r in summary["phase_results"])
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
