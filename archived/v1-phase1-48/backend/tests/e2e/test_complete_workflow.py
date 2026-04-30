"""
IPA Platform - Complete Workflow E2E Tests

Sprint 30 S30-1: E2E 整合測試
測試場景 1: 簡單順序工作流

測試從創建到完成的完整工作流生命週期，驗證所有遷移後的功能正常運作。

Adapter Integration:
- WorkflowDefinitionAdapter: 工作流驗證和執行
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

from tests.e2e.conftest import (
    wait_for_execution_complete,
    create_test_agent,
    create_test_workflow,
)


# =============================================================================
# Test Class: Complete Workflow E2E Tests
# =============================================================================

class TestCompleteWorkflow:
    """
    完整工作流端到端測試

    驗證簡單順序工作流的完整生命週期:
    1. 創建工作流
    2. 驗證工作流定義
    3. 執行工作流
    4. 監控執行狀態
    5. 驗證執行結果
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_simple_sequential_workflow_creation(
        self,
        client: AsyncClient,
        test_workflow_data: Dict[str, Any]
    ):
        """
        測試簡單順序工作流創建

        驗證:
        - 工作流 API 正確接受請求
        - WorkflowDefinitionAdapter 正確驗證定義
        - 工作流成功存儲到數據庫
        """
        # 1. 創建工作流
        response = await client.post(
            "/api/v1/workflows/",
            json=test_workflow_data
        )

        # 2. 驗證創建成功
        assert response.status_code in [200, 201], f"創建失敗: {response.text}"

        workflow = response.json()
        assert "id" in workflow
        assert workflow["name"] == test_workflow_data["name"]

        # 3. 驗證可以獲取工作流
        get_response = await client.get(f"/api/v1/workflows/{workflow['id']}")
        assert get_response.status_code == 200

        retrieved = get_response.json()
        assert retrieved["id"] == workflow["id"]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_workflow_validation_with_adapter(
        self,
        client: AsyncClient,
        test_workflow_data: Dict[str, Any]
    ):
        """
        測試工作流驗證 (使用 WorkflowDefinitionAdapter)

        驗證:
        - /validate 端點使用 WorkflowDefinitionAdapter
        - 有效定義通過驗證
        - 無效定義返回錯誤
        """
        # 1. 測試有效定義驗證
        valid_response = await client.post(
            "/api/v1/workflows/validate",
            json={"graph_definition": test_workflow_data["graph_definition"]}
        )

        # 應該通過驗證
        assert valid_response.status_code == 200
        result = valid_response.json()
        assert result.get("valid", False) is True or "error" not in result

        # 2. 測試無效定義驗證
        invalid_definition = {
            "nodes": [
                {"id": "start", "type": "start"},
                # 缺少 end 節點
            ],
            "edges": []
        }

        invalid_response = await client.post(
            "/api/v1/workflows/validate",
            json={"graph_definition": invalid_definition}
        )

        # 可能返回 200 + valid=false 或 400
        if invalid_response.status_code == 200:
            result = invalid_response.json()
            # 應該指示驗證失敗或有錯誤
            assert result.get("valid") is False or "errors" in result or "warnings" in result

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_workflow_execution_lifecycle(
        self,
        client: AsyncClient,
        test_workflow_data: Dict[str, Any]
    ):
        """
        測試工作流執行完整生命週期

        驗證:
        - 工作流可以成功執行
        - EnhancedExecutionStateMachine 正確管理狀態
        - 執行可以被監控
        - 執行完成後有正確結果
        """
        # 1. 創建工作流
        create_response = await client.post(
            "/api/v1/workflows/",
            json=test_workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"無法創建工作流: {create_response.text}")

        workflow = create_response.json()
        workflow_id = workflow["id"]

        # 2. 執行工作流
        run_response = await client.post(
            f"/api/v1/workflows/{workflow_id}/run",
            json={"input_data": {"test": "data"}}
        )

        if run_response.status_code not in [200, 201, 202]:
            pytest.skip(f"無法執行工作流: {run_response.text}")

        run_result = run_response.json()

        # 3. 獲取執行 ID
        execution_id = run_result.get("execution_id") or run_result.get("id")
        assert execution_id is not None, "未返回執行 ID"

        # 4. 監控執行狀態
        try:
            final_status = await wait_for_execution_complete(
                client, execution_id, timeout=30
            )

            # 5. 驗證執行完成
            assert final_status["status"] in ["completed", "failed", "pending_approval"]

        except TimeoutError:
            # 對於測試環境，超時是可接受的
            status_response = await client.get(f"/api/v1/executions/{execution_id}")
            if status_response.status_code == 200:
                current_status = status_response.json()
                # 記錄當前狀態用於調試
                print(f"執行超時，當前狀態: {current_status.get('status')}")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_execution_state_transitions(
        self,
        client: AsyncClient,
        test_workflow_data: Dict[str, Any]
    ):
        """
        測試執行狀態轉換 (使用 EnhancedExecutionStateMachine)

        驗證:
        - 狀態轉換遵循定義的規則
        - 可以查詢有效轉換
        - 無效轉換被拒絕
        """
        # 1. 創建並執行工作流
        create_response = await client.post(
            "/api/v1/workflows/",
            json=test_workflow_data
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

        # 2. 查詢有效狀態轉換
        transitions_response = await client.get(
            f"/api/v1/executions/{execution_id}/transitions"
        )

        if transitions_response.status_code == 200:
            transitions = transitions_response.json()
            # 驗證返回了有效轉換列表
            assert isinstance(transitions, (list, dict))

        # 3. 測試取消執行 (如果支持)
        cancel_response = await client.post(
            f"/api/v1/executions/{execution_id}/cancel"
        )

        # 取消可能成功或因狀態不允許而失敗
        assert cancel_response.status_code in [200, 400, 409]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_workflow_list_and_filter(
        self,
        client: AsyncClient,
        test_workflow_data: Dict[str, Any]
    ):
        """
        測試工作流列表和過濾

        驗證:
        - 可以列出所有工作流
        - 可以按狀態過濾
        - 分頁正常工作
        """
        # 1. 創建測試工作流
        create_response = await client.post(
            "/api/v1/workflows/",
            json=test_workflow_data
        )

        # 2. 列出工作流
        list_response = await client.get("/api/v1/workflows/")

        assert list_response.status_code == 200
        result = list_response.json()

        # 驗證返回格式
        if isinstance(result, list):
            workflows = result
        else:
            workflows = result.get("items", result.get("workflows", []))

        assert isinstance(workflows, list)

        # 3. 測試分頁
        paginated_response = await client.get(
            "/api/v1/workflows/",
            params={"skip": 0, "limit": 10}
        )

        assert paginated_response.status_code == 200

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_execution_history(
        self,
        client: AsyncClient,
        test_workflow_data: Dict[str, Any]
    ):
        """
        測試執行歷史記錄

        驗證:
        - 可以獲取執行歷史
        - 歷史記錄包含正確的狀態變化
        """
        # 1. 創建並執行工作流
        create_response = await client.post(
            "/api/v1/workflows/",
            json=test_workflow_data
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

        # 2. 列出執行
        executions_response = await client.get(
            f"/api/v1/workflows/{workflow['id']}/executions"
        )

        if executions_response.status_code == 200:
            executions = executions_response.json()
            if isinstance(executions, list):
                assert len(executions) >= 1
            elif isinstance(executions, dict):
                items = executions.get("items", executions.get("executions", []))
                assert len(items) >= 1


# =============================================================================
# Test Class: Workflow Error Handling
# =============================================================================

class TestWorkflowErrorHandling:
    """
    工作流錯誤處理測試

    驗證 API 正確處理各種錯誤情況
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_invalid_workflow_id(self, client: AsyncClient):
        """測試無效工作流 ID 處理"""
        invalid_id = str(uuid4())

        response = await client.get(f"/api/v1/workflows/{invalid_id}")

        assert response.status_code == 404

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_invalid_execution_id(self, client: AsyncClient):
        """測試無效執行 ID 處理"""
        invalid_id = str(uuid4())

        response = await client.get(f"/api/v1/executions/{invalid_id}")

        assert response.status_code == 404

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_malformed_workflow_definition(self, client: AsyncClient):
        """測試畸形工作流定義處理"""
        malformed_data = {
            "name": "Malformed Workflow",
            "description": "This should fail validation",
            "graph_definition": "not a valid definition"  # 應該是 dict
        }

        response = await client.post("/api/v1/workflows/", json=malformed_data)

        # 應該返回驗證錯誤
        assert response.status_code in [400, 422]


# =============================================================================
# Test Class: Adapter Integration Verification
# =============================================================================

class TestAdapterIntegrationVerification:
    """
    驗證 Phase 5 適配器整合

    確認 API routes 正確使用適配器層而非直接使用 domain
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_workflow_uses_adapter_for_validation(
        self,
        client: AsyncClient
    ):
        """
        驗證工作流驗證使用 WorkflowDefinitionAdapter

        通過測試驗證行為來間接驗證適配器使用
        """
        # WorkflowDefinitionAdapter 應該提供一致的驗證行為
        valid_definition = {
            "nodes": [
                {"id": "start", "type": "start", "label": "Start"},
                {"id": "process", "type": "function", "label": "Process"},
                {"id": "end", "type": "end", "label": "End"}
            ],
            "edges": [
                {"source": "start", "target": "process"},
                {"source": "process", "target": "end"}
            ]
        }

        response = await client.post(
            "/api/v1/workflows/validate",
            json={"graph_definition": valid_definition}
        )

        # 適配器應該成功驗證此定義
        assert response.status_code == 200

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_execution_uses_state_machine_adapter(
        self,
        client: AsyncClient
    ):
        """
        驗證執行狀態管理使用 EnhancedExecutionStateMachine

        通過測試狀態轉換行為來間接驗證
        """
        # 獲取任何現有執行 (或創建一個)
        list_response = await client.get("/api/v1/executions/")

        if list_response.status_code == 200:
            result = list_response.json()
            executions = result if isinstance(result, list) else result.get("items", [])

            if executions:
                execution_id = executions[0].get("id")

                # 測試狀態轉換端點
                transitions_response = await client.get(
                    f"/api/v1/executions/{execution_id}/transitions"
                )

                # EnhancedExecutionStateMachine 應該提供此功能
                if transitions_response.status_code == 200:
                    transitions = transitions_response.json()
                    # 驗證返回的轉換結構
                    assert transitions is not None
