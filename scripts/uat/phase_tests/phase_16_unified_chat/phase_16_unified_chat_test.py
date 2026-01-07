"""
Phase 16: Unified Agentic Chat Interface - UAT Test Runner

主測試執行器，運行所有 Phase 16 測試場景。

使用方式:
    # 使用模擬模式（默認）
    python phase_16_unified_chat_test.py

    # 使用真實 API
    python phase_16_unified_chat_test.py --use-real-api

    # 執行單個場景
    python phase_16_unified_chat_test.py --scenario PHASE16-001

    # 詳細輸出
    python phase_16_unified_chat_test.py --verbose
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Support both module and script execution
try:
    from ..base import TestPhase, TestStatus, ScenarioResult, safe_print
    from ..config import PhaseTestConfig
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base import TestPhase, TestStatus, ScenarioResult, safe_print
    from config import PhaseTestConfig

# Import scenarios
try:
    from .scenario_sse_connection import SSEConnectionScenario
    from .scenario_message_streaming import MessageStreamingScenario
    from .scenario_mode_switching import ModeSwitchingScenario
    from .scenario_approval_flow import ApprovalFlowScenario
    from .scenario_checkpoint_restore import CheckpointRestoreScenario
    from .scenario_execution_metrics import ExecutionMetricsScenario
except ImportError:
    from scenario_sse_connection import SSEConnectionScenario
    from scenario_message_streaming import MessageStreamingScenario
    from scenario_mode_switching import ModeSwitchingScenario
    from scenario_approval_flow import ApprovalFlowScenario
    from scenario_checkpoint_restore import CheckpointRestoreScenario
    from scenario_execution_metrics import ExecutionMetricsScenario


# Scenario Registry
SCENARIOS = {
    "PHASE16-001": {
        "class": SSEConnectionScenario,
        "name": "SSE Connection Management",
        "description": "驗證 SSE 連接的建立、斷線重連和事件接收",
    },
    "PHASE16-002": {
        "class": MessageStreamingScenario,
        "name": "Message Streaming",
        "description": "驗證完整的消息發送和接收流程",
    },
    "PHASE16-003": {
        "class": ModeSwitchingScenario,
        "name": "Mode Switching",
        "description": "驗證 Chat/Workflow 模式的自動檢測和手動切換",
    },
    "PHASE16-004": {
        "class": ApprovalFlowScenario,
        "name": "Approval Flow",
        "description": "驗證工具呼叫的 HITL 審批機制",
    },
    "PHASE16-005": {
        "class": CheckpointRestoreScenario,
        "name": "Checkpoint Restore",
        "description": "驗證檢查點的創建和恢復功能",
    },
    "PHASE16-006": {
        "class": ExecutionMetricsScenario,
        "name": "Execution Metrics",
        "description": "驗證 Token 使用、執行時間和工具統計的追蹤",
    },
}


class Phase16TestRunner:
    """
    Phase 16 UAT 測試執行器

    運行所有或指定的測試場景並生成報告。
    """

    def __init__(
        self,
        config: Optional[PhaseTestConfig] = None,
        use_simulation: bool = True,
        verbose: bool = False,
    ):
        """
        初始化測試執行器

        Args:
            config: 測試配置
            use_simulation: 是否使用模擬模式
            verbose: 是否詳細輸出
        """
        self.config = config or PhaseTestConfig()
        self.use_simulation = use_simulation
        self.verbose = verbose
        self.results: List[ScenarioResult] = []

    async def run_scenario(self, scenario_id: str) -> Optional[ScenarioResult]:
        """
        運行單個測試場景

        Args:
            scenario_id: 場景 ID

        Returns:
            測試結果或 None
        """
        if scenario_id not in SCENARIOS:
            safe_print(f"❌ Unknown scenario: {scenario_id}")
            return None

        scenario_info = SCENARIOS[scenario_id]
        scenario_class = scenario_info["class"]

        safe_print(f"\n{'=' * 70}")
        safe_print(f"🧪 Running: {scenario_id} - {scenario_info['name']}")
        safe_print(f"   Description: {scenario_info['description']}")
        safe_print(f"   Simulation Mode: {self.use_simulation}")
        safe_print(f"{'=' * 70}")

        try:
            scenario = scenario_class(
                config=self.config,
                use_simulation=self.use_simulation,
            )
            result = await scenario.run()
            self.results.append(result)
            return result

        except Exception as e:
            safe_print(f"💥 Error running scenario {scenario_id}: {e}")
            return None

    async def run_all(self) -> List[ScenarioResult]:
        """
        運行所有測試場景

        Returns:
            所有測試結果
        """
        safe_print("\n" + "=" * 70)
        safe_print("🚀 Phase 16: Unified Agentic Chat Interface UAT")
        safe_print(f"   Total Scenarios: {len(SCENARIOS)}")
        safe_print(f"   Simulation Mode: {self.use_simulation}")
        safe_print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        safe_print("=" * 70)

        for scenario_id in SCENARIOS:
            await self.run_scenario(scenario_id)

        return self.results

    async def run_selected(self, scenario_ids: List[str]) -> List[ScenarioResult]:
        """
        運行選定的測試場景

        Args:
            scenario_ids: 場景 ID 列表

        Returns:
            測試結果
        """
        for scenario_id in scenario_ids:
            await self.run_scenario(scenario_id)

        return self.results

    def print_summary(self):
        """打印測試摘要"""
        if not self.results:
            safe_print("\n❌ No test results available")
            return

        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)

        total_steps = sum(r.total_steps for r in self.results)
        passed_steps = sum(r.passed for r in self.results)
        total_duration = sum(r.duration_ms for r in self.results)

        safe_print("\n" + "=" * 70)
        safe_print("📊 Phase 16 UAT Test Summary")
        safe_print("=" * 70)

        safe_print("\n📋 Scenario Results:")
        for result in self.results:
            status_icon = "✅" if result.status == TestStatus.PASSED else "❌"
            safe_print(f"   {status_icon} {result.scenario_id}: {result.scenario_name}")
            safe_print(f"      Steps: {result.passed}/{result.total_steps} passed, {result.duration_ms:.0f}ms")

        safe_print("\n📈 Overall Statistics:")
        safe_print(f"   Scenarios: {passed}/{total} passed ({passed/total*100:.0f}%)")
        safe_print(f"   Steps: {passed_steps}/{total_steps} passed")
        safe_print(f"   Duration: {total_duration:.0f}ms ({total_duration/1000:.1f}s)")

        if failed > 0 or errors > 0:
            safe_print(f"\n⚠️ Issues:")
            if failed > 0:
                safe_print(f"   Failed: {failed} scenario(s)")
            if errors > 0:
                safe_print(f"   Errors: {errors} scenario(s)")

        # Overall status
        if passed == total:
            safe_print("\n🎉 All tests passed!")
        else:
            safe_print(f"\n❌ {total - passed} test(s) did not pass")

        safe_print("=" * 70)

    def save_results(self, output_dir: Optional[Path] = None) -> Path:
        """
        保存測試結果到 JSON 文件

        Args:
            output_dir: 輸出目錄

        Returns:
            結果文件路徑
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "test_results"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"phase_16_results_{timestamp}.json"

        report = {
            "phase": "Phase 16: Unified Agentic Chat Interface",
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "simulation_mode": self.use_simulation,
                "base_url": self.config.base_url,
            },
            "summary": {
                "total_scenarios": len(self.results),
                "passed": sum(1 for r in self.results if r.status == TestStatus.PASSED),
                "failed": sum(1 for r in self.results if r.status == TestStatus.FAILED),
                "errors": sum(1 for r in self.results if r.status == TestStatus.ERROR),
                "total_duration_ms": sum(r.duration_ms for r in self.results),
            },
            "scenarios": [r.to_dict() for r in self.results],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        safe_print(f"\n📁 Results saved to: {output_file}")
        return output_file


def parse_args():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(
        description="Phase 16: Unified Agentic Chat Interface UAT Tests"
    )

    parser.add_argument(
        "--scenario",
        type=str,
        help="Run specific scenario (e.g., PHASE16-001)",
    )

    parser.add_argument(
        "--use-real-api",
        action="store_true",
        help="Use real API instead of simulation",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available scenarios",
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file",
    )

    return parser.parse_args()


async def main():
    """主入口函數"""
    args = parse_args()

    # 列出場景
    if args.list:
        safe_print("\n📋 Available Scenarios:")
        safe_print("-" * 60)
        for scenario_id, info in SCENARIOS.items():
            safe_print(f"   {scenario_id}: {info['name']}")
            safe_print(f"      {info['description']}")
        return

    # 創建執行器
    runner = Phase16TestRunner(
        use_simulation=not args.use_real_api,
        verbose=args.verbose,
    )

    # 執行測試
    if args.scenario:
        await runner.run_scenario(args.scenario)
    else:
        await runner.run_all()

    # 打印摘要
    runner.print_summary()

    # 保存結果
    if not args.no_save:
        runner.save_results()

    # 返回狀態碼
    all_passed = all(r.status == TestStatus.PASSED for r in runner.results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
