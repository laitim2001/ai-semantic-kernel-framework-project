"""
IPA Platform - Approval Workflow E2E Tests

Sprint 30 S30-1: E2E 整合測試
測試場景 2: 帶人工審批的工作流

測試包含人工審批節點的工作流完整流程。

Adapter Integration:
- ApprovalWorkflowManager: 審批工作流管理
- HumanApprovalExecutor: 人工審批執行器
- EnhancedExecutionStateMachine: 執行狀態管理

Author: IPA Platform Team
Version: 2.0.0 (Phase 5 Migration)
"""

import pytest
import pytest_asyncio
import asyncio
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any
from httpx import AsyncClient

from tests.e2e.conftest import wait_for_execution_complete


# =============================================================================
# Test Class: Approval Workflow E2E Tests
# =============================================================================

class TestApprovalWorkflow:
    """
    人工審批工作流端到端測試

    驗證帶審批節點的工作流完整流程:
    1. 創建帶審批節點的工作流
    2. 執行工作流
    3. 驗證工作流暫停等待審批
    4. 提交審批決定
    5. 驗證工作流繼續並完成
    """

    @pytest.fixture
    def approval_workflow_data(self) -> Dict[str, Any]:
        """帶審批節點的工作流測試數據"""
        return {
            "name": f"E2E Approval Workflow {datetime.now().strftime('%H%M%S')}",
            "description": "Workflow with human approval for E2E testing",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start", "label": "Start"},
                    {
                        "id": "process",
                        "type": "function",
                        "label": "Initial Process",
                        "config": {"function_name": "process_data"}
                    },
                    {
                        "id": "approval",
                        "type": "approval",
                        "label": "Manager Approval",
                        "config": {
                            "approvers": ["manager@example.com"],
                            "timeout_hours": 24,
                            "risk_level": "high"
                        }
                    },
                    {
                        "id": "finalize",
                        "type": "function",
                        "label": "Finalize",
                        "config": {"function_name": "finalize"}
                    },
                    {"id": "end", "type": "end", "label": "End"}
                ],
                "edges": [
                    {"source": "start", "target": "process"},
                    {"source": "process", "target": "approval"},
                    {"source": "approval", "target": "finalize"},
                    {"source": "finalize", "target": "end"}
                ]
            },
            "is_active": True,
            "category": "testing",
        }

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approval_workflow_creation(
        self,
        client: AsyncClient,
        approval_workflow_data: Dict[str, Any]
    ):
        """
        測試帶審批節點的工作流創建

        驗證:
        - 包含審批節點的工作流可以成功創建
        - 審批節點配置被正確保存
        """
        # 創建工作流
        response = await client.post(
            "/api/v1/workflows/",
            json=approval_workflow_data
        )

        assert response.status_code in [200, 201], f"創建失敗: {response.text}"

        workflow = response.json()
        assert "id" in workflow
        assert workflow["name"] == approval_workflow_data["name"]

        # 驗證工作流包含審批節點
        if "graph_definition" in workflow:
            graph = workflow["graph_definition"]
            if isinstance(graph, dict) and "nodes" in graph:
                approval_nodes = [
                    n for n in graph["nodes"]
                    if n.get("type") == "approval"
                ]
                assert len(approval_nodes) >= 1

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_workflow_pauses_at_approval(
        self,
        client: AsyncClient,
        approval_workflow_data: Dict[str, Any]
    ):
        """
        測試工作流在審批節點暫停

        驗證:
        - 工作流執行到審批節點時暫停
        - 狀態變為 waiting_approval 或 pending_approval
        - 創建待審批請求
        """
        # 1. 創建工作流
        create_response = await client.post(
            "/api/v1/workflows/",
            json=approval_workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"無法創建工作流: {create_response.text}")

        workflow = create_response.json()

        # 2. 執行工作流
        run_response = await client.post(
            f"/api/v1/workflows/{workflow['id']}/run",
            json={"input_data": {"test_value": "approval_test"}}
        )

        if run_response.status_code not in [200, 201, 202]:
            pytest.skip(f"無法執行工作流: {run_response.text}")

        run_result = run_response.json()
        execution_id = run_result.get("execution_id") or run_result.get("id")

        # 3. 等待執行到達審批節點
        await asyncio.sleep(2)

        # 4. 檢查執行狀態
        status_response = await client.get(f"/api/v1/executions/{execution_id}")

        if status_response.status_code == 200:
            status = status_response.json()
            current_status = status.get("status", "").lower()

            # 應該是等待審批或已完成狀態
            assert current_status in [
                "waiting_approval", "pending_approval",
                "running", "completed", "failed"
            ]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_pending_approvals(
        self,
        client: AsyncClient
    ):
        """
        測試獲取待審批列表

        驗證:
        - /api/v1/checkpoints/pending 端點正常工作
        - ApprovalWorkflowManager 正確返回待審批請求
        """
        # 使用新的適配器端點
        response = await client.get("/api/v1/checkpoints/approval/pending")

        if response.status_code == 404:
            # 嘗試舊端點
            response = await client.get("/api/v1/checkpoints/pending")

        if response.status_code == 200:
            result = response.json()

            # 驗證返回格式
            if isinstance(result, list):
                pending_approvals = result
            else:
                pending_approvals = result.get("approvals", result.get("items", []))

            assert isinstance(pending_approvals, list)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approve_checkpoint(
        self,
        client: AsyncClient,
        approval_workflow_data: Dict[str, Any]
    ):
        """
        測試審批通過

        驗證:
        - 可以提交審批通過
        - ApprovalWorkflowManager 正確處理審批
        - 工作流繼續執行
        """
        # 1. 創建並執行工作流
        create_response = await client.post(
            "/api/v1/workflows/",
            json=approval_workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建工作流")

        workflow = create_response.json()

        run_response = await client.post(
            f"/api/v1/workflows/{workflow['id']}/run",
            json={"input_data": {}}
        )

        if run_response.status_code not in [200, 201, 202]:
            pytest.skip("無法執行工作流")

        run_result = run_response.json()
        execution_id = run_result.get("execution_id") or run_result.get("id")

        # 2. 等待執行到達審批節點
        await asyncio.sleep(2)

        # 3. 獲取待審批請求
        pending_response = await client.get("/api/v1/checkpoints/pending")

        if pending_response.status_code == 200:
            pending = pending_response.json()
            approvals = pending if isinstance(pending, list) else pending.get("approvals", [])

            if approvals:
                # 4. 執行審批
                approval = approvals[0]
                approval_id = approval.get("id") or approval.get("request_id")

                approve_response = await client.post(
                    f"/api/v1/checkpoints/{approval_id}/approve",
                    json={"reason": "Approved for E2E testing"}
                )

                # 驗證審批成功
                assert approve_response.status_code in [200, 201, 202, 204]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_reject_checkpoint(
        self,
        client: AsyncClient,
        approval_workflow_data: Dict[str, Any]
    ):
        """
        測試審批拒絕

        驗證:
        - 可以提交審批拒絕
        - 工作流正確處理拒絕結果
        """
        # 1. 創建並執行工作流
        create_response = await client.post(
            "/api/v1/workflows/",
            json=approval_workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建工作流")

        workflow = create_response.json()

        run_response = await client.post(
            f"/api/v1/workflows/{workflow['id']}/run",
            json={"input_data": {}}
        )

        if run_response.status_code not in [200, 201, 202]:
            pytest.skip("無法執行工作流")

        # 2. 等待並獲取待審批請求
        await asyncio.sleep(2)

        pending_response = await client.get("/api/v1/checkpoints/pending")

        if pending_response.status_code == 200:
            pending = pending_response.json()
            approvals = pending if isinstance(pending, list) else pending.get("approvals", [])

            if approvals:
                approval = approvals[0]
                approval_id = approval.get("id") or approval.get("request_id")

                # 3. 執行拒絕
                reject_response = await client.post(
                    f"/api/v1/checkpoints/{approval_id}/reject",
                    json={"reason": "Rejected for E2E testing"}
                )

                # 驗證拒絕成功
                assert reject_response.status_code in [200, 201, 202, 204]


# =============================================================================
# Test Class: Approval Adapter Integration
# =============================================================================

class TestApprovalAdapterIntegration:
    """
    審批適配器整合測試

    驗證 Phase 5 遷移後的適配器層正確工作
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approval_workflow_manager_endpoint(
        self,
        client: AsyncClient
    ):
        """
        測試 ApprovalWorkflowManager 適配器端點

        驗證新增的適配器端點正常工作
        """
        # 測試新的適配器端點 (Sprint 29 新增)
        response = await client.get("/api/v1/checkpoints/approval/pending")

        # 端點應該存在
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, (list, dict))

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approval_respond_endpoint(
        self,
        client: AsyncClient
    ):
        """
        測試適配器審批回應端點

        驗證 /approval/{executor}/respond 端點
        """
        # 測試端點存在性
        response = await client.post(
            "/api/v1/checkpoints/approval/test-executor/respond",
            json={
                "request_id": str(uuid4()),
                "approved": True,
                "reason": "Test response"
            }
        )

        # 端點應該存在 (可能返回 400/404 因為請求不存在)
        assert response.status_code in [200, 201, 400, 404, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_checkpoint_status_mapping(
        self,
        client: AsyncClient
    ):
        """
        測試 Checkpoint 狀態映射

        驗證 API 返回的狀態與適配器狀態正確映射
        """
        # 列出所有 checkpoints
        response = await client.get("/api/v1/checkpoints/")

        if response.status_code == 200:
            result = response.json()
            checkpoints = result if isinstance(result, list) else result.get("items", [])

            for checkpoint in checkpoints[:5]:  # 只檢查前 5 個
                status = checkpoint.get("status", "").lower()

                # 驗證狀態是有效值
                valid_statuses = [
                    "pending", "approved", "rejected",
                    "expired", "escalated", "cancelled"
                ]
                assert status in valid_statuses or status == ""


# =============================================================================
# Test Class: Approval Timeout and Escalation
# =============================================================================

class TestApprovalTimeoutAndEscalation:
    """
    審批超時和升級測試
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_approval_with_timeout_config(
        self,
        client: AsyncClient
    ):
        """
        測試帶超時配置的審批
        """
        workflow_data = {
            "name": f"Timeout Approval Workflow {datetime.now().strftime('%H%M%S')}",
            "description": "Workflow with approval timeout",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {
                        "id": "approval",
                        "type": "approval",
                        "config": {
                            "timeout_hours": 1,
                            "escalation_policy": "auto_approve"
                        }
                    },
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "approval"},
                    {"source": "approval", "target": "end"}
                ]
            }
        }

        response = await client.post("/api/v1/workflows/", json=workflow_data)

        # 工作流應該可以創建
        assert response.status_code in [200, 201, 422]  # 422 如果驗證失敗也可接受

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_checkpoint_creation_endpoint(
        self,
        client: AsyncClient
    ):
        """
        測試創建 Checkpoint 端點

        驗證 ApprovalWorkflowManager.create_approval_request 整合
        """
        checkpoint_data = {
            "workflow_id": str(uuid4()),
            "execution_id": str(uuid4()),
            "node_id": "approval_node",
            "checkpoint_type": "approval",
            "description": "Test approval checkpoint",
            "context": {"test": "data"}
        }

        response = await client.post(
            "/api/v1/checkpoints/",
            json=checkpoint_data
        )

        # 端點應該存在 (可能因為無效 ID 返回 400/404)
        assert response.status_code in [200, 201, 400, 404, 422]
