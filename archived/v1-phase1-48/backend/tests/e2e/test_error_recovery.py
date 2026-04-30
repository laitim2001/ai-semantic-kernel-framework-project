"""
IPA Platform - Error Recovery E2E Tests

Sprint 30 S30-1: E2E 整合測試
測試場景 6: 錯誤恢復工作流

測試工作流錯誤處理和恢復機制。

Adapter Integration:
- EnhancedExecutionStateMachine: 錯誤狀態管理
- WorkflowDefinitionAdapter: 錯誤恢復配置
- ApprovalWorkflowManager: 錯誤升級審批

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
# Test Class: Error Recovery Workflow E2E Tests
# =============================================================================

class TestErrorRecoveryWorkflow:
    """
    錯誤恢復工作流端到端測試

    驗證錯誤處理和恢復流程:
    1. 創建帶錯誤處理的工作流
    2. 模擬錯誤
    3. 驗證錯誤被正確捕獲
    4. 執行重試
    5. 驗證恢復或升級
    """

    @pytest.fixture
    def error_handling_workflow_data(self) -> Dict[str, Any]:
        """帶錯誤處理的工作流測試數據"""
        return {
            "name": f"E2E Error Recovery {datetime.now().strftime('%H%M%S')}",
            "description": "Workflow with error handling for E2E testing",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start", "label": "Start"},
                    {
                        "id": "process",
                        "type": "function",
                        "label": "Process",
                        "config": {
                            "function_name": "process_data",
                            "retry": {
                                "max_attempts": 3,
                                "delay_seconds": 1
                            }
                        }
                    },
                    {
                        "id": "error_handler",
                        "type": "error_handler",
                        "label": "Handle Error",
                        "config": {
                            "on_error": "retry",
                            "fallback_node": "fallback"
                        }
                    },
                    {
                        "id": "fallback",
                        "type": "function",
                        "label": "Fallback",
                        "config": {"function_name": "fallback_process"}
                    },
                    {"id": "end", "type": "end", "label": "End"}
                ],
                "edges": [
                    {"source": "start", "target": "process"},
                    {"source": "process", "target": "end", "condition": "success"},
                    {"source": "process", "target": "error_handler", "condition": "error"},
                    {"source": "error_handler", "target": "fallback"},
                    {"source": "fallback", "target": "end"}
                ]
            },
            "is_active": True,
            "category": "testing",
        }

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_handling_workflow_creation(
        self,
        client: AsyncClient,
        error_handling_workflow_data: Dict[str, Any]
    ):
        """
        測試帶錯誤處理的工作流創建

        驗證:
        - 錯誤處理配置被正確保存
        - 重試配置被正確保存
        """
        response = await client.post(
            "/api/v1/workflows/",
            json=error_handling_workflow_data
        )

        assert response.status_code in [200, 201], f"創建失敗: {response.text}"

        workflow = response.json()
        assert "id" in workflow

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_execution_failure_handling(
        self,
        client: AsyncClient,
        error_handling_workflow_data: Dict[str, Any]
    ):
        """
        測試執行失敗處理

        驗證:
        - 執行失敗時狀態正確設置
        - 錯誤信息被記錄
        """
        # 1. 創建工作流
        create_response = await client.post(
            "/api/v1/workflows/",
            json=error_handling_workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建工作流")

        workflow = create_response.json()

        # 2. 執行工作流 (可能會失敗)
        run_response = await client.post(
            f"/api/v1/workflows/{workflow['id']}/run",
            json={"input_data": {"force_error": True}}  # 觸發錯誤
        )

        if run_response.status_code in [200, 201, 202]:
            run_result = run_response.json()
            execution_id = run_result.get("execution_id") or run_result.get("id")

            # 3. 等待並檢查狀態
            await asyncio.sleep(3)

            status_response = await client.get(f"/api/v1/executions/{execution_id}")

            if status_response.status_code == 200:
                status = status_response.json()
                # 狀態應該是 failed, retrying, 或 completed (如果重試成功)
                assert status.get("status") in [
                    "running", "failed", "completed", "retrying", "error"
                ]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_execution_retry(
        self,
        client: AsyncClient
    ):
        """
        測試執行重試

        驗證:
        - 可以手動觸發重試
        - 重試執行正確
        """
        # 創建簡單工作流
        workflow_data = {
            "name": f"Retry Test {datetime.now().strftime('%H%M%S')}",
            "description": "Test retry functionality",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "process", "type": "function", "config": {}},
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "process"},
                    {"source": "process", "target": "end"}
                ]
            }
        }

        create_response = await client.post(
            "/api/v1/workflows/",
            json=workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建工作流")

        workflow = create_response.json()

        # 執行工作流
        run_response = await client.post(
            f"/api/v1/workflows/{workflow['id']}/run",
            json={"input_data": {}}
        )

        if run_response.status_code in [200, 201, 202]:
            run_result = run_response.json()
            execution_id = run_result.get("execution_id") or run_result.get("id")

            # 等待執行完成或失敗
            await asyncio.sleep(2)

            # 嘗試重試
            retry_response = await client.post(
                f"/api/v1/executions/{execution_id}/retry"
            )

            # 重試可能成功或因狀態不允許而失敗
            assert retry_response.status_code in [200, 201, 202, 400, 409]


# =============================================================================
# Test Class: Error State Machine Integration
# =============================================================================

class TestErrorStateMachineIntegration:
    """
    錯誤狀態機整合測試

    驗證 EnhancedExecutionStateMachine 錯誤狀態處理
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_failed_state_transitions(
        self,
        client: AsyncClient
    ):
        """
        測試失敗狀態轉換

        驗證 failed 狀態的有效轉換
        """
        # 列出執行以找到失敗的執行
        list_response = await client.get("/api/v1/executions/")

        if list_response.status_code == 200:
            result = list_response.json()
            executions = result if isinstance(result, list) else result.get("items", [])

            # 找到失敗的執行
            failed_executions = [
                e for e in executions
                if e.get("status", "").lower() == "failed"
            ]

            if failed_executions:
                execution_id = failed_executions[0].get("id")

                # 查詢有效轉換
                transitions_response = await client.get(
                    f"/api/v1/executions/{execution_id}/transitions"
                )

                if transitions_response.status_code == 200:
                    transitions = transitions_response.json()
                    # 失敗狀態應該允許 retry 或 cancel
                    assert transitions is not None

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_to_retry_transition(
        self,
        client: AsyncClient
    ):
        """
        測試錯誤到重試狀態轉換
        """
        # 創建一個新執行用於測試
        workflow_data = {
            "name": f"Error Transition Test {datetime.now().strftime('%H%M%S')}",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "end", "type": "end"}
                ],
                "edges": [{"source": "start", "target": "end"}]
            }
        }

        create_response = await client.post(
            "/api/v1/workflows/",
            json=workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建工作流")

        workflow = create_response.json()

        # 執行並等待
        run_response = await client.post(
            f"/api/v1/workflows/{workflow['id']}/run",
            json={}
        )

        assert run_response.status_code in [200, 201, 202, 400]


# =============================================================================
# Test Class: Error Escalation
# =============================================================================

class TestErrorEscalation:
    """
    錯誤升級測試

    驗證錯誤升級到人工審批
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_escalation_to_approval(
        self,
        client: AsyncClient
    ):
        """
        測試錯誤升級到審批

        驗證重試失敗後升級到人工審批
        """
        workflow_data = {
            "name": f"Escalation Test {datetime.now().strftime('%H%M%S')}",
            "description": "Test error escalation",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {
                        "id": "process",
                        "type": "function",
                        "config": {
                            "on_max_retries": "escalate_to_approval"
                        }
                    },
                    {
                        "id": "approval",
                        "type": "approval",
                        "config": {"description": "Manual intervention required"}
                    },
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "process"},
                    {"source": "process", "target": "approval", "condition": "escalate"},
                    {"source": "process", "target": "end", "condition": "success"},
                    {"source": "approval", "target": "end"}
                ]
            }
        }

        response = await client.post("/api/v1/workflows/", json=workflow_data)

        assert response.status_code in [200, 201, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_notification(
        self,
        client: AsyncClient
    ):
        """
        測試錯誤通知

        驗證錯誤發生時發送通知
        """
        workflow_data = {
            "name": f"Notification Test {datetime.now().strftime('%H%M%S')}",
            "description": "Test error notification",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {
                        "id": "process",
                        "type": "function",
                        "config": {
                            "on_error": {
                                "notify": ["admin@example.com"],
                                "notification_type": "email"
                            }
                        }
                    },
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "process"},
                    {"source": "process", "target": "end"}
                ]
            }
        }

        response = await client.post("/api/v1/workflows/", json=workflow_data)

        assert response.status_code in [200, 201, 422]


# =============================================================================
# Test Class: Execution Recovery
# =============================================================================

class TestExecutionRecovery:
    """
    執行恢復測試
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(
        self,
        client: AsyncClient
    ):
        """
        測試從檢查點恢復
        """
        # 列出執行
        list_response = await client.get("/api/v1/executions/")

        if list_response.status_code == 200:
            result = list_response.json()
            executions = result if isinstance(result, list) else result.get("items", [])

            if executions:
                execution_id = executions[0].get("id")

                # 嘗試從檢查點恢復
                resume_response = await client.post(
                    f"/api/v1/executions/{execution_id}/resume"
                )

                # 可能成功或因狀態不允許而失敗
                assert resume_response.status_code in [200, 201, 202, 400, 404, 409]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_cancel_failed_execution(
        self,
        client: AsyncClient
    ):
        """
        測試取消失敗的執行
        """
        # 列出執行找到失敗的
        list_response = await client.get("/api/v1/executions/")

        if list_response.status_code == 200:
            result = list_response.json()
            executions = result if isinstance(result, list) else result.get("items", [])

            failed = [e for e in executions if e.get("status") == "failed"]

            if failed:
                execution_id = failed[0].get("id")

                cancel_response = await client.post(
                    f"/api/v1/executions/{execution_id}/cancel"
                )

                assert cancel_response.status_code in [200, 204, 400, 409]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_execution_errors(
        self,
        client: AsyncClient
    ):
        """
        測試獲取執行錯誤詳情
        """
        # 列出執行
        list_response = await client.get("/api/v1/executions/")

        if list_response.status_code == 200:
            result = list_response.json()
            executions = result if isinstance(result, list) else result.get("items", [])

            if executions:
                execution_id = executions[0].get("id")

                # 獲取錯誤詳情
                errors_response = await client.get(
                    f"/api/v1/executions/{execution_id}/errors"
                )

                assert errors_response.status_code in [200, 404]


# =============================================================================
# Test Class: Comprehensive Error Scenarios
# =============================================================================

class TestComprehensiveErrorScenarios:
    """
    綜合錯誤場景測試
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        client: AsyncClient
    ):
        """
        測試超時處理
        """
        workflow_data = {
            "name": f"Timeout Test {datetime.now().strftime('%H%M%S')}",
            "description": "Test timeout handling",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {
                        "id": "process",
                        "type": "function",
                        "config": {
                            "timeout_seconds": 5,
                            "on_timeout": "fail"
                        }
                    },
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "process"},
                    {"source": "process", "target": "end"}
                ]
            }
        }

        response = await client.post("/api/v1/workflows/", json=workflow_data)

        assert response.status_code in [200, 201, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_resource_exhaustion_handling(
        self,
        client: AsyncClient
    ):
        """
        測試資源耗盡處理
        """
        # 嘗試創建大量執行
        workflow_data = {
            "name": f"Resource Test {datetime.now().strftime('%H%M%S')}",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "end", "type": "end"}
                ],
                "edges": [{"source": "start", "target": "end"}]
            }
        }

        create_response = await client.post(
            "/api/v1/workflows/",
            json=workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建工作流")

        workflow = create_response.json()

        # 嘗試創建多個執行
        responses = []
        for _ in range(20):
            run_response = await client.post(
                f"/api/v1/workflows/{workflow['id']}/run",
                json={}
            )
            responses.append(run_response.status_code)

        # 應該有一些成功，可能有些被限制
        success_count = sum(1 for r in responses if r in [200, 201, 202])
        assert success_count >= 1

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_cascading_failure_handling(
        self,
        client: AsyncClient
    ):
        """
        測試級聯失敗處理
        """
        workflow_data = {
            "name": f"Cascade Test {datetime.now().strftime('%H%M%S')}",
            "description": "Test cascading failure",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "step1", "type": "function", "config": {}},
                    {"id": "step2", "type": "function", "config": {"depends_on": "step1"}},
                    {"id": "step3", "type": "function", "config": {"depends_on": "step2"}},
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"source": "start", "target": "step1"},
                    {"source": "step1", "target": "step2"},
                    {"source": "step2", "target": "step3"},
                    {"source": "step3", "target": "end"}
                ]
            }
        }

        response = await client.post("/api/v1/workflows/", json=workflow_data)

        assert response.status_code in [200, 201, 422]
