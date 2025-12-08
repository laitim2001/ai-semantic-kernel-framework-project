"""
IPA Platform - API Performance Tests

Sprint 30 S30-2: 效能測試
API 回應時間測試

效能指標:
- GET 端點 < 100ms
- POST 端點 < 500ms
- 列表端點 < 200ms

Adapter Integration:
驗證 Phase 5 遷移後 API 效能無退化

Author: IPA Platform Team
Version: 2.0.0 (Phase 5 Migration)
"""

import pytest
import pytest_asyncio
import asyncio
import time
from uuid import uuid4
from datetime import datetime
from typing import List, Dict, Any
from statistics import mean, stdev
from dataclasses import dataclass
from httpx import AsyncClient, ASGITransport

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from main import app


# =============================================================================
# Performance Metrics
# =============================================================================

@dataclass
class APIPerformanceMetrics:
    """API 效能指標容器"""
    endpoint: str
    method: str
    total_requests: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_rps: float
    success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "total_requests": self.total_requests,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "throughput_rps": round(self.throughput_rps, 2),
            "success_rate": round(self.success_rate, 2),
        }


def calculate_percentile(latencies: List[float], percentile: float) -> float:
    """計算百分位數"""
    if not latencies:
        return 0.0
    sorted_latencies = sorted(latencies)
    index = int(len(sorted_latencies) * percentile / 100)
    return sorted_latencies[min(index, len(sorted_latencies) - 1)]


def calculate_api_metrics(
    endpoint: str,
    method: str,
    latencies: List[float],
    success_count: int,
    total_duration: float
) -> APIPerformanceMetrics:
    """計算 API 效能指標"""
    total = len(latencies)
    latencies_ms = [l * 1000 for l in latencies]

    return APIPerformanceMetrics(
        endpoint=endpoint,
        method=method,
        total_requests=total,
        avg_latency_ms=mean(latencies_ms) if latencies_ms else 0,
        p50_latency_ms=calculate_percentile(latencies_ms, 50),
        p95_latency_ms=calculate_percentile(latencies_ms, 95),
        p99_latency_ms=calculate_percentile(latencies_ms, 99),
        min_latency_ms=min(latencies_ms) if latencies_ms else 0,
        max_latency_ms=max(latencies_ms) if latencies_ms else 0,
        throughput_rps=total / total_duration if total_duration > 0 else 0,
        success_rate=(success_count / total * 100) if total > 0 else 0,
    )


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def perf_client() -> AsyncClient:
    """Performance test HTTP client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0
    ) as client:
        yield client


# =============================================================================
# Test Class: GET Endpoint Performance
# =============================================================================

class TestGETEndpointPerformance:
    """
    GET 端點效能測試

    目標: 回應時間 < 100ms
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_get_workflows_list_performance(self, perf_client: AsyncClient):
        """
        測試 GET /api/v1/workflows/ 列表端點效能

        目標: < 200ms (列表端點標準)
        """
        latencies = []
        success_count = 0
        total_requests = 100

        start_time = time.time()
        for _ in range(total_requests):
            op_start = time.time()
            response = await perf_client.get("/api/v1/workflows/")
            latencies.append(time.time() - op_start)

            if response.status_code == 200:
                success_count += 1

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            "/api/v1/workflows/", "GET",
            latencies, success_count, total_duration
        )

        print(f"\n列表端點效能: {metrics.to_dict()}")

        # 驗證效能指標
        assert metrics.avg_latency_ms < 200, f"平均延遲 {metrics.avg_latency_ms}ms 超過 200ms"
        assert metrics.p95_latency_ms < 500, f"P95 延遲 {metrics.p95_latency_ms}ms 超過 500ms"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_get_single_workflow_performance(self, perf_client: AsyncClient):
        """
        測試 GET /api/v1/workflows/{id} 單個資源端點效能

        目標: < 100ms
        """
        # 先創建一個工作流用於測試
        workflow_data = {
            "name": f"Perf Test Workflow {datetime.now().strftime('%H%M%S')}",
            "description": "Performance testing",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "end", "type": "end"}
                ],
                "edges": [{"source": "start", "target": "end"}]
            }
        }

        create_response = await perf_client.post(
            "/api/v1/workflows/",
            json=workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建測試工作流")

        workflow_id = create_response.json().get("id")

        latencies = []
        success_count = 0
        total_requests = 100

        start_time = time.time()
        for _ in range(total_requests):
            op_start = time.time()
            response = await perf_client.get(f"/api/v1/workflows/{workflow_id}")
            latencies.append(time.time() - op_start)

            if response.status_code == 200:
                success_count += 1

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            f"/api/v1/workflows/{{id}}", "GET",
            latencies, success_count, total_duration
        )

        print(f"\n單個資源端點效能: {metrics.to_dict()}")

        # 驗證效能指標
        assert metrics.avg_latency_ms < 100, f"平均延遲 {metrics.avg_latency_ms}ms 超過 100ms"
        assert metrics.p95_latency_ms < 200, f"P95 延遲 {metrics.p95_latency_ms}ms 超過 200ms"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_get_executions_list_performance(self, perf_client: AsyncClient):
        """
        測試 GET /api/v1/executions/ 列表端點效能
        """
        latencies = []
        success_count = 0
        total_requests = 100

        start_time = time.time()
        for _ in range(total_requests):
            op_start = time.time()
            response = await perf_client.get("/api/v1/executions/")
            latencies.append(time.time() - op_start)

            if response.status_code == 200:
                success_count += 1

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            "/api/v1/executions/", "GET",
            latencies, success_count, total_duration
        )

        print(f"\n執行列表端點效能: {metrics.to_dict()}")

        assert metrics.avg_latency_ms < 200


# =============================================================================
# Test Class: POST Endpoint Performance
# =============================================================================

class TestPOSTEndpointPerformance:
    """
    POST 端點效能測試

    目標: 回應時間 < 500ms
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_post_workflow_creation_performance(self, perf_client: AsyncClient):
        """
        測試 POST /api/v1/workflows/ 創建端點效能

        目標: < 500ms
        """
        latencies = []
        success_count = 0
        total_requests = 50

        start_time = time.time()
        for i in range(total_requests):
            workflow_data = {
                "name": f"Perf Test {i} {datetime.now().strftime('%H%M%S')}",
                "description": "Performance testing",
                "graph_definition": {
                    "nodes": [
                        {"id": "start", "type": "start"},
                        {"id": "process", "type": "function"},
                        {"id": "end", "type": "end"}
                    ],
                    "edges": [
                        {"source": "start", "target": "process"},
                        {"source": "process", "target": "end"}
                    ]
                }
            }

            op_start = time.time()
            response = await perf_client.post(
                "/api/v1/workflows/",
                json=workflow_data
            )
            latencies.append(time.time() - op_start)

            if response.status_code in [200, 201]:
                success_count += 1

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            "/api/v1/workflows/", "POST",
            latencies, success_count, total_duration
        )

        print(f"\n創建端點效能: {metrics.to_dict()}")

        # 驗證效能指標
        assert metrics.avg_latency_ms < 500, f"平均延遲 {metrics.avg_latency_ms}ms 超過 500ms"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_post_workflow_run_performance(self, perf_client: AsyncClient):
        """
        測試 POST /api/v1/workflows/{id}/run 執行端點效能
        """
        # 先創建工作流
        workflow_data = {
            "name": f"Run Perf Test {datetime.now().strftime('%H%M%S')}",
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "end", "type": "end"}
                ],
                "edges": [{"source": "start", "target": "end"}]
            }
        }

        create_response = await perf_client.post(
            "/api/v1/workflows/",
            json=workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建測試工作流")

        workflow_id = create_response.json().get("id")

        latencies = []
        success_count = 0
        total_requests = 30

        start_time = time.time()
        for i in range(total_requests):
            op_start = time.time()
            response = await perf_client.post(
                f"/api/v1/workflows/{workflow_id}/run",
                json={"input_data": {"test": i}}
            )
            latencies.append(time.time() - op_start)

            if response.status_code in [200, 201, 202]:
                success_count += 1

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            f"/api/v1/workflows/{{id}}/run", "POST",
            latencies, success_count, total_duration
        )

        print(f"\n執行端點效能: {metrics.to_dict()}")

        assert metrics.avg_latency_ms < 500

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_post_handoff_trigger_performance(self, perf_client: AsyncClient):
        """
        測試 POST /api/v1/handoff/trigger 端點效能
        """
        latencies = []
        success_count = 0
        total_requests = 30

        start_time = time.time()
        for i in range(total_requests):
            handoff_request = {
                "source_agent_id": str(uuid4()),
                "target_agent_id": str(uuid4()),
                "reason": f"Performance test {i}"
            }

            op_start = time.time()
            response = await perf_client.post(
                "/api/v1/handoff/trigger",
                json=handoff_request
            )
            latencies.append(time.time() - op_start)

            if response.status_code in [200, 201, 202]:
                success_count += 1

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            "/api/v1/handoff/trigger", "POST",
            latencies, success_count, total_duration
        )

        print(f"\n交接觸發端點效能: {metrics.to_dict()}")

        assert metrics.avg_latency_ms < 500


# =============================================================================
# Test Class: Adapter Integration Performance
# =============================================================================

class TestAdapterPerformance:
    """
    Phase 5 適配器效能測試

    驗證適配器層不會引入顯著效能開銷
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_workflow_validation_performance(self, perf_client: AsyncClient):
        """
        測試工作流驗證效能 (使用 WorkflowDefinitionAdapter)
        """
        valid_definition = {
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "process", "type": "function"},
                {"id": "end", "type": "end"}
            ],
            "edges": [
                {"source": "start", "target": "process"},
                {"source": "process", "target": "end"}
            ]
        }

        latencies = []
        success_count = 0
        total_requests = 50

        start_time = time.time()
        for _ in range(total_requests):
            op_start = time.time()
            response = await perf_client.post(
                "/api/v1/workflows/validate",
                json={"graph_definition": valid_definition}
            )
            latencies.append(time.time() - op_start)

            if response.status_code == 200:
                success_count += 1

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            "/api/v1/workflows/validate", "POST",
            latencies, success_count, total_duration
        )

        print(f"\n驗證端點效能 (適配器): {metrics.to_dict()}")

        # 適配器不應顯著影響效能
        assert metrics.avg_latency_ms < 200

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_checkpoint_operations_performance(self, perf_client: AsyncClient):
        """
        測試 Checkpoint 操作效能 (使用 ApprovalWorkflowManager)
        """
        latencies = []
        success_count = 0
        total_requests = 50

        start_time = time.time()
        for _ in range(total_requests):
            op_start = time.time()
            response = await perf_client.get("/api/v1/checkpoints/pending")
            latencies.append(time.time() - op_start)

            if response.status_code in [200, 404]:
                success_count += 1

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            "/api/v1/checkpoints/pending", "GET",
            latencies, success_count, total_duration
        )

        print(f"\nCheckpoint 端點效能: {metrics.to_dict()}")

        assert metrics.avg_latency_ms < 200


# =============================================================================
# Test Class: Throughput Tests
# =============================================================================

class TestAPIThroughput:
    """
    API 吞吐量測試
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_load(self, perf_client: AsyncClient):
        """
        測試持續負載下的 API 效能

        模擬 100 個請求持續 10 秒
        """
        latencies = []
        success_count = 0

        start_time = time.time()
        while time.time() - start_time < 10:  # 10 秒持續負載
            op_start = time.time()
            response = await perf_client.get("/api/v1/workflows/")
            latencies.append(time.time() - op_start)

            if response.status_code == 200:
                success_count += 1

            # 短暫延遲避免過度負載
            await asyncio.sleep(0.05)

        total_duration = time.time() - start_time

        metrics = calculate_api_metrics(
            "/api/v1/workflows/", "GET (sustained)",
            latencies, success_count, total_duration
        )

        print(f"\n持續負載效能: {metrics.to_dict()}")

        # 驗證效能不隨時間退化
        assert metrics.success_rate > 95  # 成功率 > 95%
        assert metrics.throughput_rps > 5  # 至少 5 RPS

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_burst_load(self, perf_client: AsyncClient):
        """
        測試突發負載下的 API 效能

        同時發送 20 個請求
        """
        async def make_request():
            op_start = time.time()
            response = await perf_client.get("/api/v1/workflows/")
            latency = time.time() - op_start
            return latency, response.status_code == 200

        # 突發 20 個請求
        start_time = time.time()
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        latencies = []
        success_count = 0
        for result in results:
            if not isinstance(result, Exception):
                latencies.append(result[0])
                if result[1]:
                    success_count += 1

        metrics = calculate_api_metrics(
            "/api/v1/workflows/", "GET (burst)",
            latencies, success_count, total_duration
        )

        print(f"\n突發負載效能: {metrics.to_dict()}")

        # 突發負載下效能應該可接受
        assert metrics.success_rate > 90  # 成功率 > 90%


# =============================================================================
# Performance Summary
# =============================================================================

class TestPerformanceSummary:
    """
    效能測試總結
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_comprehensive_api_performance(self, perf_client: AsyncClient):
        """
        綜合 API 效能測試

        測試所有主要端點並生成報告
        """
        endpoints = [
            ("GET", "/api/v1/workflows/", None),
            ("GET", "/api/v1/executions/", None),
            ("GET", "/api/v1/agents/", None),
            ("GET", "/api/v1/checkpoints/", None),
            ("GET", "/api/v1/groupchat/", None),
        ]

        results = []

        for method, endpoint, body in endpoints:
            latencies = []
            success_count = 0

            start_time = time.time()
            for _ in range(30):
                op_start = time.time()

                if method == "GET":
                    response = await perf_client.get(endpoint)
                else:
                    response = await perf_client.post(endpoint, json=body or {})

                latencies.append(time.time() - op_start)

                if response.status_code in [200, 201, 202, 404]:
                    success_count += 1

            total_duration = time.time() - start_time

            metrics = calculate_api_metrics(
                endpoint, method,
                latencies, success_count, total_duration
            )
            results.append(metrics)

        # 輸出效能報告
        print("\n" + "=" * 60)
        print("API 效能測試報告")
        print("=" * 60)

        for metrics in results:
            print(f"\n{metrics.method} {metrics.endpoint}")
            print(f"  平均延遲: {metrics.avg_latency_ms:.2f}ms")
            print(f"  P95 延遲: {metrics.p95_latency_ms:.2f}ms")
            print(f"  吞吐量: {metrics.throughput_rps:.2f} RPS")
            print(f"  成功率: {metrics.success_rate:.1f}%")

        print("\n" + "=" * 60)

        # 驗證所有端點效能
        for metrics in results:
            assert metrics.avg_latency_ms < 500, f"{metrics.endpoint} 延遲過高"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
