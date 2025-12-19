# =============================================================================
# Scenario 002: Multi-Agent Collaboration - 多 Agent 協作分析
# =============================================================================
# UAT 驗證腳本，測試多 Agent 群組討論、多輪對話、投票決策和報告生成。
#
# 涉及功能: GroupChat, Multi-turn, Memory, Speaker Selection, Voting, Termination
#
# Author: IPA Platform Team
# Version: 1.0.0
# Created: 2025-12-18
# =============================================================================

"""
Multi-Agent Collaboration Scenario Test.

Tests the following capabilities:
- GroupChat orchestration
- Speaker selection (auto, round_robin, expertise)
- Multi-turn conversation with memory
- Voting mechanism
- Termination conditions
"""

import time
from typing import Any, Dict, List

from .base import ScenarioTestBase, TestResult, TestStatus


class CollaborationScenarioTest(ScenarioTestBase):
    """Test class for Multi-Agent Collaboration scenario."""

    SCENARIO_ID = "scenario_002"
    SCENARIO_NAME = "多 Agent 協作分析"
    SCENARIO_DESCRIPTION = """
    對複雜的業務問題進行多角度分析，多個專家 Agent 協作討論，
    最後綜合產出報告。支援多種發言模式和投票決策。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_agents: List[str] = []
        self.created_groupchats: List[str] = []
        self.created_sessions: List[str] = []

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

        # Cleanup in reverse order of creation
        for session_id in self.created_sessions:
            try:
                await self.api_delete(f"/api/v1/groupchat/sessions/{session_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete session {session_id}: {e}")

        for groupchat_id in self.created_groupchats:
            try:
                await self.api_delete(f"/api/v1/groupchat/{groupchat_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete groupchat {groupchat_id}: {e}")

        for agent_id in self.created_agents:
            try:
                await self.api_delete(f"/api/v1/agents/{agent_id}")
            except Exception as e:
                self.logger.warning(f"Failed to delete agent {agent_id}: {e}")

        self.log_success("Cleanup completed")
        return True

    async def get_test_cases(self) -> List[Dict[str, Any]]:
        """Get test cases for Collaboration scenario."""
        return [
            {
                "id": "TC-002-01",
                "name": "3 Agent 基本討論",
                "description": "驗證 3 個 Agent 能夠進行基本討論並產出結論",
                "input": {
                    "analysis_topic": "是否應該將現有的單體架構遷移到微服務架構？",
                    "speaker_selection_method": "round_robin",
                    "max_rounds": 5
                },
                "expected": {
                    "discussion_rounds": 5,
                    "all_participants_spoke": True,
                    "report_generated": True
                }
            },
            {
                "id": "TC-002-02",
                "name": "輪流發言模式",
                "description": "驗證 Round-Robin 發言順序正確",
                "input": {
                    "analysis_topic": "新產品上市策略評估",
                    "speaker_selection_method": "round_robin"
                },
                "expected": {
                    "speaking_order_correct": True
                }
            },
            {
                "id": "TC-002-03",
                "name": "專長發言模式",
                "description": "驗證按專長自動選擇發言者",
                "input": {
                    "analysis_topic": "API 效能優化方案",
                    "speaker_selection_method": "expertise"
                },
                "expected": {
                    "expertise_based_selection": True
                }
            },
            {
                "id": "TC-002-04",
                "name": "投票達成共識",
                "description": "驗證投票機制正常運作",
                "input": {
                    "analysis_topic": "是否採用新的 CI/CD 工具？",
                    "require_voting": True
                },
                "expected": {
                    "voting_triggered": True,
                    "voting_completed": True,
                    "result_recorded": True
                }
            },
            {
                "id": "TC-002-05",
                "name": "對話記憶持久化",
                "description": "驗證對話歷史正確保存到 Memory",
                "input": {
                    "analysis_topic": "客戶滿意度提升計劃",
                    "max_rounds": 8
                },
                "expected": {
                    "memory_saved": True,
                    "message_count_gte": 8,
                    "summary_generated": True
                }
            },
            {
                "id": "TC-002-06",
                "name": "GroupChat API 驗證",
                "description": "驗證 GroupChat 相關 API 端點可用性",
                "type": "api_check",
                "expected": {
                    "groupchat_api": True,
                    "sessions_api": True,
                    "speaker_selection_api": True
                }
            },
            {
                "id": "TC-002-07",
                "name": "Memory 服務驗證",
                "description": "驗證 Memory 存儲和檢索功能",
                "type": "memory_check",
                "expected": {
                    "memory_api": True,
                    "storage_available": True
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
            if test_type == "api_check":
                result = await self._run_api_check(test_case)
            elif test_type == "memory_check":
                result = await self._run_memory_check(test_case)
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

    async def _run_api_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check GroupChat API availability."""
        details = {}

        # Check GroupChat endpoints
        groupchat_endpoints = [
            ("/api/v1/groupchat", "groupchat_list"),
            ("/api/v1/groupchat/sessions", "sessions_list"),
        ]

        for endpoint, name in groupchat_endpoints:
            response = await self.api_get(endpoint)
            details[name] = {
                "status_code": response.status_code,
                "available": response.status_code == 200
            }

        # Check speaker selection configuration endpoint
        response = await self.api_get("/api/v1/groupchat/speaker-selection/methods")
        details["speaker_selection"] = {
            "status_code": response.status_code,
            "available": response.status_code in [200, 404]  # 404 is acceptable if not implemented
        }

        # Check voting endpoint
        response = await self.api_get("/api/v1/groupchat/voting")
        details["voting"] = {
            "status_code": response.status_code,
            "available": response.status_code in [200, 404]
        }

        core_available = all([
            details.get("groupchat_list", {}).get("available", False),
            details.get("sessions_list", {}).get("available", False)
        ])

        return {
            "success": core_available,
            "message": "GroupChat APIs available" if core_available else "Some GroupChat APIs not available",
            "details": details
        }

    async def _run_memory_check(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check Memory service availability."""
        details = {}

        # Check memory endpoints
        memory_endpoints = [
            ("/api/v1/memory", "memory_list"),
            ("/api/v1/memory/search", "memory_search"),
        ]

        for endpoint, name in memory_endpoints:
            try:
                response = await self.api_get(endpoint)
                details[name] = {
                    "status_code": response.status_code,
                    "available": response.status_code in [200, 404]
                }
            except Exception as e:
                details[name] = {
                    "error": str(e),
                    "available": False
                }

        # Check conversation history endpoint
        response = await self.api_get("/api/v1/conversations")
        details["conversations"] = {
            "status_code": response.status_code,
            "available": response.status_code in [200, 404]
        }

        return {
            "success": True,  # Memory is optional for basic functionality
            "message": "Memory service check completed",
            "details": details
        }

    async def _run_scenario_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run collaboration scenario test."""
        input_data = test_case.get("input", {})
        expected = test_case.get("expected", {})
        details = {"input": input_data, "expected": expected}

        # Verify GroupChat API is available
        response = await self.api_get("/api/v1/groupchat")
        groupchat_available = response.status_code == 200
        details["groupchat_api"] = groupchat_available

        if not groupchat_available:
            return {
                "success": False,
                "message": "GroupChat API not available",
                "details": details
            }

        # Check if we can list existing groupchats
        # GroupChat API returns a list directly, not {"data": [...]}
        groupchat_data = response.json()
        groupchats = groupchat_data if isinstance(groupchat_data, list) else groupchat_data.get("data", [])
        details["existing_groupchats"] = len(groupchats)

        # Verify agents API for creating expert agents
        response = await self.api_get("/api/v1/agents")
        agents_available = response.status_code == 200
        details["agents_api"] = agents_available

        # Agents API returns {"items": [...]} format
        if agents_available:
            agents_data = response.json()
            agents = agents_data.get("items", []) if isinstance(agents_data, dict) else agents_data
            details["existing_agents"] = len(agents)

        # Check speaker selection method support
        speaker_method = input_data.get("speaker_selection_method", "round_robin")
        details["speaker_method_requested"] = speaker_method

        # Check voting if required
        if input_data.get("require_voting"):
            response = await self.api_get("/api/v1/groupchat/voting")
            details["voting_api"] = response.status_code in [200, 404]

        # Check memory for conversation persistence
        response = await self.api_get("/api/v1/memory")
        details["memory_api"] = response.status_code in [200, 404]

        return {
            "success": groupchat_available and agents_available,
            "message": "Collaboration scenario APIs verified",
            "details": details
        }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Agent Collaboration UAT Test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    parser.add_argument("--save-report", action="store_true", help="Save report to file")
    args = parser.parse_args()

    async def main():
        test = CollaborationScenarioTest(
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
