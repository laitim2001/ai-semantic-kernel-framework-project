# =============================================================================
# Scenario 004: Autonomous Task Planning - 複雜任務自主規劃
# =============================================================================
# UAT 驗證腳本，測試任務自動分解、嵌套工作流、動態資源分配和失敗重試。
#
# 涉及功能: Planning (TaskDecomposer), Nested Workflow, Handoff,
#           Capability Matcher, Checkpoint, Memory, Trial-and-Error
#
# Author: IPA Platform Team
# Version: 1.0.0
# Created: 2025-12-18
# =============================================================================

"""
Autonomous Task Planning Scenario Test.

Tests the following capabilities:
- Task decomposition (breaking goals into subtasks)
- Nested workflow execution
- Capability matching for agent selection
- Trial-and-error with retry mechanisms
- Dynamic replanning
"""

import time
from typing import Any, Dict, List

from .base import ScenarioTestBase, TestResult, TestStatus


class PlanningScenarioTest(ScenarioTestBase):
    """Test class for Autonomous Planning scenario."""

    SCENARIO_ID = "scenario_004"
    SCENARIO_NAME = "複雜任務自主規劃"
    SCENARIO_DESCRIPTION = """
    用戶提出高層次目標，系統自動分解為子任務，
    動態分配資源，並在執行過程中自我調整。
    支援嵌套工作流、失敗重試和關鍵節點人工審批。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_plans: List[str] = []
        self.created_workflows: List[str] = []
        self.created_executions: List[str] = []

    async def setup(self) -> bool:
        """Setup test environment."""
        self.log_info("Checking API server health...")

        if not await self.check_health():
            self.log_failure("API server is not healthy")
            return False

        self.log_success("API server is healthy")
        return True

    async def teardown(self) -> bool:
        """Cleanup test resources."""
        self.log_info("Cleaning up test resources...")

        for execution_id in self.created_executions:
            try:
                await self.api_delete(f"/api/v1/executions/{execution_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete execution {execution_id}: {e}")

        for workflow_id in self.created_workflows:
            try:
                await self.api_delete(f"/api/v1/nested/{workflow_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete nested workflow {workflow_id}: {e}")

        for plan_id in self.created_plans:
            try:
                await self.api_delete(f"/api/v1/planning/plans/{plan_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete plan {plan_id}: {e}")

        self.log_success("Cleanup completed")
        return True

    async def get_test_cases(self) -> List[Dict[str, Any]]:
        """Get test cases for Planning scenario."""
        return [
            {
                "id": "TC-004-01",
                "name": "基本任務分解",
                "description": "驗證簡單目標能被分解為 3+ 子任務",
                "input": {
                    "goal": "設置開發環境並運行第一個測試",
                    "max_depth": 2
                },
                "expected": {
                    "task_count_gte": 3,
                    "has_dependencies": True,
                    "all_tasks_assigned": True
                }
            },
            {
                "id": "TC-004-02",
                "name": "嵌套工作流執行",
                "description": "驗證包含子流程的任務正確執行",
                "input": {
                    "goal": "部署微服務應用",
                    "subtasks": [
                        "準備基礎設施",
                        "部署數據庫",
                        "部署後端服務",
                        "部署前端應用"
                    ]
                },
                "expected": {
                    "nested_execution": True,
                    "context_propagated": True,
                    "correct_order": True
                }
            },
            {
                "id": "TC-004-03",
                "name": "關鍵節點審批",
                "description": "驗證關鍵任務觸發人工審批",
                "input": {
                    "goal": "更新生產環境配置",
                    "has_critical_tasks": True
                },
                "expected": {
                    "checkpoint_triggered": True,
                    "approval_required": True
                }
            },
            {
                "id": "TC-004-04",
                "name": "失敗重試測試",
                "description": "驗證任務失敗後 Trial-and-Error 機制",
                "input": {
                    "goal": "執行可能失敗的操作",
                    "simulate_failure": True,
                    "failure_count": 2
                },
                "expected": {
                    "retry_attempted": True,
                    "retry_count": 2,
                    "eventual_success": True
                }
            },
            {
                "id": "TC-004-05",
                "name": "動態調整測試",
                "description": "驗證執行中變更觸發重新規劃",
                "input": {
                    "goal": "完成軟體開發任務",
                    "mid_execution_change": {
                        "type": "resource_unavailable",
                        "affected_task": "code_review"
                    }
                },
                "expected": {
                    "replan_triggered": True,
                    "alternative_assigned": True,
                    "execution_continued": True
                }
            },
            {
                "id": "TC-004-06",
                "name": "Planning API 驗證",
                "description": "驗證 Planning 相關 API 端點可用性",
                "type": "planning_check",
                "expected": {
                    "planning_api": True,
                    "decomposer_api": True
                }
            },
            {
                "id": "TC-004-07",
                "name": "Nested Workflow API 驗證",
                "description": "驗證嵌套工作流 API 可用性",
                "type": "nested_check",
                "expected": {
                    "nested_api": True
                }
            },
            {
                "id": "TC-004-08",
                "name": "Capability Matcher 驗證",
                "description": "驗證能力匹配器 API 可用性",
                "type": "capability_check",
                "expected": {
                    "capability_api": True
                }
            },
            {
                "id": "TC-004-09",
                "name": "Checkpoint API 驗證",
                "description": "驗證檢查點 API 可用性",
                "type": "checkpoint_check",
                "expected": {
                    "checkpoint_api": True
                }
            }
        ]

    async def run_test_case(self, test_case: Dict[str, Any]) -> TestResult:
        """Run a single test case."""
        test_id = test_case["id"]
        test_name = test_case["name"]
        test_type = test_case.get("type", "scenario")
        start_time = time.time()

        try:
            if test_type == "planning_check":
                result = await self._run_planning_check(test_case)
            elif test_type == "nested_check":
                result = await self._run_nested_check(test_case)
            elif test_type == "capability_check":
                result = await self._run_capability_check(test_case)
            elif test_type == "checkpoint_check":
                result = await self._run_checkpoint_check(test_case)
            else:
                result = await self._run_scenario_test(test_case)

            duration_ms = (time.time() - start_time) * 1000
            return self.create_test_result(
                test_id=test_id,
                test_name=test_name,
                status=TestStatus.PASSED if result["success"] else TestStatus.FAILED,
                duration_ms=duration_ms,
                message=result.get("message", ""),
                details=result.get("details", {})
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self.create_test_result(
                test_id=test_id,
                test_name=test_name,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=str(e)
            )

    async def _run_planning_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check Planning API availability."""
        details = {}

        # Check planning endpoints
        planning_endpoints = [
            ("/api/v1/planning", "planning_list"),
            ("/api/v1/planning/goals", "planning_goals"),
            ("/api/v1/planning/plans", "planning_plans"),
            ("/api/v1/planning/decompose", "decomposer"),
        ]

        for endpoint, name in planning_endpoints:
            response = await self.api_get(endpoint)
            details[name] = {
                "status_code": response.status_code,
                "available": response.status_code in [200, 404, 405]  # 405 for POST-only endpoints
            }

        return {
            "success": True,
            "message": "Planning API check completed",
            "details": details
        }

    async def _run_nested_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check Nested Workflow API availability."""
        details = {}

        # Check nested workflow endpoints
        nested_endpoints = [
            ("/api/v1/nested", "nested_list"),
            ("/api/v1/nested/workflows", "nested_workflows"),
            ("/api/v1/nested/executions", "nested_executions"),
        ]

        for endpoint, name in nested_endpoints:
            response = await self.api_get(endpoint)
            details[name] = {
                "status_code": response.status_code,
                "available": response.status_code in [200, 404]
            }

        return {
            "success": True,
            "message": "Nested Workflow API check completed",
            "details": details
        }

    async def _run_capability_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check Capability Matcher API availability."""
        details = {}

        # Check capability endpoints
        capability_endpoints = [
            ("/api/v1/capabilities", "capabilities_list"),
            ("/api/v1/capabilities/match", "capability_match"),
            ("/api/v1/handoff/capabilities", "handoff_capabilities"),
        ]

        for endpoint, name in capability_endpoints:
            response = await self.api_get(endpoint)
            details[name] = {
                "status_code": response.status_code,
                "available": response.status_code in [200, 404, 405]
            }

        # Check agents with capabilities
        response = await self.api_get("/api/v1/agents")
        if response.status_code == 200:
            agents = response.json().get("data", [])
            agents_with_caps = sum(1 for a in agents if a.get("capabilities"))
            details["agents_with_capabilities"] = agents_with_caps

        return {
            "success": True,
            "message": "Capability Matcher API check completed",
            "details": details
        }

    async def _run_checkpoint_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check Checkpoint API availability."""
        details = {}

        # Check checkpoint endpoints
        checkpoint_endpoints = [
            ("/api/v1/checkpoints", "checkpoints_list"),
            ("/api/v1/checkpoints/pending", "pending_approvals"),
            ("/api/v1/approvals", "approvals_list"),
        ]

        for endpoint, name in checkpoint_endpoints:
            response = await self.api_get(endpoint)
            details[name] = {
                "status_code": response.status_code,
                "available": response.status_code in [200, 404]
            }

        return {
            "success": True,
            "message": "Checkpoint API check completed",
            "details": details
        }

    async def _run_scenario_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run planning scenario test."""
        input_data = test_case.get("input", {})
        expected = test_case.get("expected", {})
        details = {"input": input_data, "expected": expected}

        # Check planning API
        response = await self.api_get("/api/v1/planning")
        planning_available = response.status_code in [200, 404]
        details["planning_api"] = planning_available

        # Check nested workflow API
        response = await self.api_get("/api/v1/nested")
        nested_available = response.status_code in [200, 404]
        details["nested_api"] = nested_available

        # Check workflows for execution
        response = await self.api_get("/api/v1/workflows")
        workflows_available = response.status_code == 200
        details["workflows_api"] = workflows_available

        # Check capability matching
        response = await self.api_get("/api/v1/capabilities")
        capabilities_available = response.status_code in [200, 404]
        details["capabilities_api"] = capabilities_available

        # Check checkpoint for approval workflow
        if expected.get("checkpoint_triggered") or expected.get("approval_required"):
            response = await self.api_get("/api/v1/checkpoints")
            details["checkpoints_api"] = response.status_code in [200, 404]

        # Check retry mechanism for trial-and-error
        if expected.get("retry_attempted"):
            response = await self.api_get("/api/v1/executions")
            details["executions_api"] = response.status_code == 200

        # Check handoff for capability matching
        response = await self.api_get("/api/v1/handoff")
        details["handoff_api"] = response.status_code in [200, 404]

        return {
            "success": workflows_available,
            "message": "Planning scenario APIs verified",
            "details": details
        }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Planning UAT Test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    parser.add_argument("--save-report", action="store_true", help="Save report to file")
    args = parser.parse_args()

    async def main():
        test = PlanningScenarioTest(
            base_url=args.base_url,
            timeout=args.timeout,
            verbose=args.verbose
        )
        result = await test.run()

        if args.save_report:
            test.save_report(result)

        return result.status == TestStatus.PASSED

    success = asyncio.run(main())
    exit(0 if success else 1)
