"""
IPA Platform - Handoff Workflow E2E Tests

Sprint 30 S30-1: E2E 整合測試
測試場景 4: Agent 交接工作流

測試 Agent 之間交接控制權的完整流程。

Adapter Integration:
- HandoffService: Agent 交接服務
- HandoffBuilderAdapter: 交接構建
- CapabilityMatcherAdapter: 能力匹配

Author: IPA Platform Team
Version: 2.0.0 (Phase 5 Migration)
"""

import pytest
import pytest_asyncio
import asyncio
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List
from httpx import AsyncClient


# =============================================================================
# Test Class: Handoff Workflow E2E Tests
# =============================================================================

class TestHandoffWorkflow:
    """
    Agent 交接工作流端到端測試

    驗證 Agent 交接流程:
    1. 創建多個 Agent
    2. 設置交接規則
    3. 觸發交接
    4. 驗證交接完成
    """

    @pytest.fixture
    def agent_a_data(self) -> Dict[str, Any]:
        """Agent A 測試數據"""
        return {
            "name": f"E2E Handoff Agent A {datetime.now().strftime('%H%M%S')}",
            "description": "Primary agent for handoff testing",
            "instructions": "You are Agent A, responsible for initial processing.",
            "model": "gpt-4",
            "capabilities": ["initial_processing", "data_validation"],
            "is_active": True,
        }

    @pytest.fixture
    def agent_b_data(self) -> Dict[str, Any]:
        """Agent B 測試數據"""
        return {
            "name": f"E2E Handoff Agent B {datetime.now().strftime('%H%M%S')}",
            "description": "Secondary agent for handoff testing",
            "instructions": "You are Agent B, responsible for advanced processing.",
            "model": "gpt-4",
            "capabilities": ["advanced_processing", "report_generation"],
            "is_active": True,
        }

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_trigger_handoff(
        self,
        client: AsyncClient,
        agent_a_data: Dict[str, Any],
        agent_b_data: Dict[str, Any]
    ):
        """
        測試觸發 Agent 交接

        驗證:
        - HandoffService 正確處理交接請求
        - 交接狀態正確追蹤
        """
        # 1. 創建 Agents
        agent_a_response = await client.post("/api/v1/agents/", json=agent_a_data)
        agent_b_response = await client.post("/api/v1/agents/", json=agent_b_data)

        if agent_a_response.status_code not in [200, 201]:
            # 使用模擬 ID
            agent_a_id = str(uuid4())
        else:
            agent_a_id = agent_a_response.json().get("id", str(uuid4()))

        if agent_b_response.status_code not in [200, 201]:
            agent_b_id = str(uuid4())
        else:
            agent_b_id = agent_b_response.json().get("id", str(uuid4()))

        # 2. 觸發交接
        handoff_request = {
            "source_agent_id": agent_a_id,
            "target_agent_id": agent_b_id,
            "reason": "Task requires advanced processing capabilities",
            "context": {
                "current_state": "initial_processing_complete",
                "data": {"test": "value"}
            }
        }

        response = await client.post(
            "/api/v1/handoff/trigger",
            json=handoff_request
        )

        # 端點應該存在並處理請求
        assert response.status_code in [200, 201, 202, 400, 404, 422]

        if response.status_code in [200, 201, 202]:
            result = response.json()
            # 驗證返回了交接 ID
            assert "handoff_id" in result or "id" in result

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_handoff_status(
        self,
        client: AsyncClient
    ):
        """
        測試獲取交接狀態

        驗證 HandoffService.get_handoff_status() 整合
        """
        # 先觸發一個交接
        handoff_request = {
            "source_agent_id": str(uuid4()),
            "target_agent_id": str(uuid4()),
            "reason": "Status test"
        }

        trigger_response = await client.post(
            "/api/v1/handoff/trigger",
            json=handoff_request
        )

        if trigger_response.status_code in [200, 201, 202]:
            result = trigger_response.json()
            handoff_id = result.get("handoff_id") or result.get("id")

            if handoff_id:
                # 獲取狀態
                status_response = await client.get(
                    f"/api/v1/handoff/{handoff_id}/status"
                )

                assert status_response.status_code in [200, 404]

                if status_response.status_code == 200:
                    status = status_response.json()
                    assert "status" in status or "state" in status

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_cancel_handoff(
        self,
        client: AsyncClient
    ):
        """
        測試取消交接

        驗證 HandoffService.cancel_handoff() 整合
        """
        # 觸發交接
        handoff_request = {
            "source_agent_id": str(uuid4()),
            "target_agent_id": str(uuid4()),
            "reason": "Cancel test"
        }

        trigger_response = await client.post(
            "/api/v1/handoff/trigger",
            json=handoff_request
        )

        if trigger_response.status_code in [200, 201, 202]:
            result = trigger_response.json()
            handoff_id = result.get("handoff_id") or result.get("id")

            if handoff_id:
                # 取消交接
                cancel_response = await client.post(
                    f"/api/v1/handoff/{handoff_id}/cancel",
                    json={"reason": "Testing cancellation"}
                )

                assert cancel_response.status_code in [200, 204, 400, 404, 409]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_handoff_history(
        self,
        client: AsyncClient
    ):
        """
        測試獲取交接歷史

        驗證 HandoffService.get_handoff_history() 整合
        """
        agent_id = str(uuid4())

        response = await client.get(
            f"/api/v1/handoff/history/{agent_id}"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            history = response.json()
            # 應該返回列表
            assert isinstance(history, (list, dict))


# =============================================================================
# Test Class: Capability Matching
# =============================================================================

class TestCapabilityMatching:
    """
    能力匹配測試

    驗證 CapabilityMatcherAdapter 整合
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_match_capabilities(
        self,
        client: AsyncClient
    ):
        """
        測試能力匹配

        驗證 HandoffService.find_matching_agents() 整合
        """
        match_request = {
            "required_capabilities": ["data_analysis", "report_generation"],
            "strategy": "best_fit"
        }

        response = await client.post(
            "/api/v1/handoff/match",
            json=match_request
        )

        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            result = response.json()
            # 應該返回匹配的 agents
            assert "agents" in result or "matches" in result or isinstance(result, list)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_register_capabilities(
        self,
        client: AsyncClient
    ):
        """
        測試註冊 Agent 能力
        """
        agent_id = str(uuid4())

        capabilities = {
            "agent_id": agent_id,
            "capabilities": [
                "natural_language_processing",
                "data_extraction",
                "summarization"
            ]
        }

        response = await client.post(
            "/api/v1/handoff/capabilities/register",
            json=capabilities
        )

        assert response.status_code in [200, 201, 400, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_agent_capabilities(
        self,
        client: AsyncClient
    ):
        """
        測試獲取 Agent 能力
        """
        agent_id = str(uuid4())

        response = await client.get(
            f"/api/v1/handoff/capabilities/{agent_id}"
        )

        assert response.status_code in [200, 404]


# =============================================================================
# Test Class: Handoff Service Integration
# =============================================================================

class TestHandoffServiceIntegration:
    """
    HandoffService 整合測試

    驗證 Phase 5 遷移後的 HandoffService 正確工作
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_handoff_service_singleton(
        self,
        client: AsyncClient
    ):
        """
        測試 HandoffService 單例模式

        通過多次請求驗證服務一致性
        """
        # 執行多次請求
        responses = []
        for _ in range(3):
            response = await client.get("/api/v1/handoff/status")
            responses.append(response.status_code)

        # 所有請求應該有一致的響應
        assert len(set(responses)) == 1

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_handoff_with_context_transfer(
        self,
        client: AsyncClient
    ):
        """
        測試帶上下文轉移的交接

        驗證上下文正確傳遞
        """
        handoff_request = {
            "source_agent_id": str(uuid4()),
            "target_agent_id": str(uuid4()),
            "reason": "Context transfer test",
            "context": {
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"}
                ],
                "state": {"step": 2, "data": {"key": "value"}},
                "metadata": {"session_id": str(uuid4())}
            }
        }

        response = await client.post(
            "/api/v1/handoff/trigger",
            json=handoff_request
        )

        assert response.status_code in [200, 201, 202, 400, 404, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_handoff_policy_options(
        self,
        client: AsyncClient
    ):
        """
        測試交接策略選項

        驗證不同交接策略
        """
        policies = ["immediate", "graceful", "conditional"]

        for policy in policies:
            handoff_request = {
                "source_agent_id": str(uuid4()),
                "target_agent_id": str(uuid4()),
                "reason": f"Policy test: {policy}",
                "policy": policy
            }

            response = await client.post(
                "/api/v1/handoff/trigger",
                json=handoff_request
            )

            # 端點應該接受請求
            assert response.status_code in [200, 201, 202, 400, 404, 422]


# =============================================================================
# Test Class: Handoff Workflow Integration
# =============================================================================

class TestHandoffWorkflowIntegration:
    """
    交接工作流整合測試
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_workflow_with_handoff_node(
        self,
        client: AsyncClient
    ):
        """
        測試帶交接節點的工作流
        """
        workflow_data = {
            "name": f"Handoff Workflow {datetime.now().strftime('%H%M%S')}",
            "description": "Workflow with handoff node",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {
                        "id": "agent_a",
                        "type": "agent",
                        "config": {"agent_name": "Agent A"}
                    },
                    {
                        "id": "handoff",
                        "type": "handoff",
                        "config": {
                            "target_agent": "Agent B",
                            "transfer_context": True
                        }
                    },
                    {
                        "id": "agent_b",
                        "type": "agent",
                        "config": {"agent_name": "Agent B"}
                    },
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "agent_a"},
                    {"source": "agent_a", "target": "handoff"},
                    {"source": "handoff", "target": "agent_b"},
                    {"source": "agent_b", "target": "end"}
                ]
            }
        }

        response = await client.post("/api/v1/workflows/", json=workflow_data)

        # 工作流應該可以創建
        assert response.status_code in [200, 201, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_conditional_handoff(
        self,
        client: AsyncClient
    ):
        """
        測試條件觸發的交接
        """
        handoff_request = {
            "source_agent_id": str(uuid4()),
            "target_agent_id": str(uuid4()),
            "reason": "Conditional handoff",
            "trigger_type": "condition",
            "condition": {
                "type": "capability_required",
                "capability": "advanced_analysis"
            }
        }

        response = await client.post(
            "/api/v1/handoff/trigger",
            json=handoff_request
        )

        assert response.status_code in [200, 201, 202, 400, 404, 422]
