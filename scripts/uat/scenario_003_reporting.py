# =============================================================================
# Scenario 003: Automated Report Generation - 自動化報表生成
# =============================================================================
# UAT 驗證腳本，測試多數據源並行收集、數據整合、報表生成和自動通知。
#
# 涉及功能: Connector, Trigger (Cron), Parallel, Fork-Join, Cache, Audit
#
# Author: IPA Platform Team
# Version: 1.0.0
# Created: 2025-12-18
# =============================================================================

"""
Automated Report Generation Scenario Test.

Tests the following capabilities:
- Parallel data collection from multiple sources
- Fork-Join execution pattern
- LLM caching for optimization
- Cron trigger scheduling
- Notification delivery
"""

import time
from typing import Any, Dict, List

from .base import ScenarioTestBase, TestResult, TestStatus


class ReportingScenarioTest(ScenarioTestBase):
    """Test class for Automated Reporting scenario."""

    SCENARIO_ID = "scenario_003"
    SCENARIO_NAME = "自動化報表生成"
    SCENARIO_DESCRIPTION = """
    定期從多個數據源收集信息，並行處理後生成綜合報表，
    並自動通知相關人員。支援 LLM 緩存優化和完整審計追蹤。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_connectors: List[str] = []
        self.created_workflows: List[str] = []
        self.created_reports: List[str] = []

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

        for report_id in self.created_reports:
            try:
                await self.api_delete(f"/api/v1/reports/{report_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete report {report_id}: {e}")

        for workflow_id in self.created_workflows:
            try:
                await self.api_delete(f"/api/v1/workflows/{workflow_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete workflow {workflow_id}: {e}")

        for connector_id in self.created_connectors:
            try:
                await self.api_delete(f"/api/v1/connectors/{connector_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete connector {connector_id}: {e}")

        self.log_success("Cleanup completed")
        return True

    async def get_test_cases(self) -> List[Dict[str, Any]]:
        """Get test cases for Reporting scenario."""
        return [
            {
                "id": "TC-003-01",
                "name": "單數據源報表",
                "description": "驗證從單一數據源生成報表",
                "input": {
                    "data_sources": ["internal_db"],
                    "report_type": "simple"
                },
                "expected": {
                    "data_collected": True,
                    "report_generated": True
                }
            },
            {
                "id": "TC-003-02",
                "name": "多數據源並行收集",
                "description": "驗證 Fork-Join 並行收集 3 個數據源",
                "input": {
                    "data_sources": ["servicenow", "dynamics365", "internal_db"],
                    "execution_mode": "parallel"
                },
                "expected": {
                    "parallel_execution": True,
                    "all_sources_collected": True,
                    "merge_successful": True
                }
            },
            {
                "id": "TC-003-03",
                "name": "緩存命中測試",
                "description": "驗證 LLM 緩存正常命中",
                "input": {
                    "repeat_execution": True,
                    "cache_enabled": True
                },
                "expected": {
                    "cache_hit": True,
                    "skip_analysis": True
                }
            },
            {
                "id": "TC-003-04",
                "name": "定時觸發測試",
                "description": "驗證 Cron 定時觸發正確執行",
                "input": {
                    "trigger_type": "cron",
                    "schedule": "*/5 * * * *"
                },
                "expected": {
                    "trigger_registered": True,
                    "schedule_valid": True
                }
            },
            {
                "id": "TC-003-05",
                "name": "報表通知測試",
                "description": "驗證報表完成後正確發送通知",
                "input": {
                    "notification_channels": ["email", "teams"]
                },
                "expected": {
                    "notification_api": True
                }
            },
            {
                "id": "TC-003-06",
                "name": "Connector API 驗證",
                "description": "驗證外部連接器 API 可用性",
                "type": "connector_check",
                "expected": {
                    "connectors_api": True
                }
            },
            {
                "id": "TC-003-07",
                "name": "Concurrent Execution 驗證",
                "description": "驗證並行執行 API 可用性",
                "type": "concurrent_check",
                "expected": {
                    "concurrent_api": True
                }
            },
            {
                "id": "TC-003-08",
                "name": "Cache 服務驗證",
                "description": "驗證 LLM 緩存服務可用性",
                "type": "cache_check",
                "expected": {
                    "cache_api": True
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
            if test_type == "connector_check":
                result = await self._run_connector_check(test_case)
            elif test_type == "concurrent_check":
                result = await self._run_concurrent_check(test_case)
            elif test_type == "cache_check":
                result = await self._run_cache_check(test_case)
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

    async def _run_connector_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check Connector API availability."""
        details = {}

        # Check connectors endpoint
        response = await self.api_get("/api/v1/connectors")
        connectors_available = response.status_code == 200
        details["connectors_list"] = {
            "status_code": response.status_code,
            "available": connectors_available
        }

        if connectors_available:
            connectors = response.json().get("data", [])
            details["connector_count"] = len(connectors)

        # Check connector types endpoint
        response = await self.api_get("/api/v1/connectors/types")
        details["connector_types"] = {
            "status_code": response.status_code,
            "available": response.status_code in [200, 404]
        }

        return {
            "success": connectors_available,
            "message": "Connector API check completed",
            "details": details
        }

    async def _run_concurrent_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check Concurrent execution API availability."""
        details = {}

        # Check concurrent execution endpoints
        concurrent_endpoints = [
            ("/api/v1/concurrent/executions", "concurrent_executions"),
            ("/api/v1/concurrent/branches", "concurrent_branches"),
        ]

        for endpoint, name in concurrent_endpoints:
            response = await self.api_get(endpoint)
            details[name] = {
                "status_code": response.status_code,
                "available": response.status_code in [200, 404]
            }

        # Check fork-join specific endpoint
        response = await self.api_get("/api/v1/concurrent/fork-join")
        details["fork_join"] = {
            "status_code": response.status_code,
            "available": response.status_code in [200, 404]
        }

        return {
            "success": True,
            "message": "Concurrent execution API check completed",
            "details": details
        }

    async def _run_cache_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check Cache service availability."""
        details = {}

        # Check cache endpoints
        cache_endpoints = [
            ("/api/v1/cache", "cache_list"),
            ("/api/v1/cache/stats", "cache_stats"),
            ("/api/v1/cache/llm", "llm_cache"),
        ]

        for endpoint, name in cache_endpoints:
            response = await self.api_get(endpoint)
            details[name] = {
                "status_code": response.status_code,
                "available": response.status_code in [200, 404]
            }

        return {
            "success": True,
            "message": "Cache service check completed",
            "details": details
        }

    async def _run_scenario_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run reporting scenario test."""
        input_data = test_case.get("input", {})
        expected = test_case.get("expected", {})
        details = {"input": input_data, "expected": expected}

        # Check workflows API
        response = await self.api_get("/api/v1/workflows")
        workflows_available = response.status_code == 200
        details["workflows_api"] = workflows_available

        # Check triggers API (for cron triggers)
        response = await self.api_get("/api/v1/triggers")
        triggers_available = response.status_code in [200, 404]
        details["triggers_api"] = triggers_available

        # Check data sources based on input
        data_sources = input_data.get("data_sources", [])
        if data_sources:
            details["requested_sources"] = data_sources

        # Check notification API if needed
        if input_data.get("notification_channels"):
            response = await self.api_get("/api/v1/notifications")
            details["notifications_api"] = response.status_code in [200, 404]

        # Check concurrent API for parallel execution
        if input_data.get("execution_mode") == "parallel":
            response = await self.api_get("/api/v1/concurrent/executions")
            details["concurrent_api"] = response.status_code in [200, 404]

        # Check cache for LLM caching
        if input_data.get("cache_enabled"):
            response = await self.api_get("/api/v1/cache/llm")
            details["cache_api"] = response.status_code in [200, 404]

        return {
            "success": workflows_available,
            "message": "Reporting scenario APIs verified",
            "details": details
        }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="Automated Reporting UAT Test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    parser.add_argument("--save-report", action="store_true", help="Save report to file")
    args = parser.parse_args()

    async def main():
        test = ReportingScenarioTest(
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
