"""
IPA Platform - Concurrent Performance Tests

Sprint 30 S30-2: 效能測試
並行處理能力測試

效能指標:
- 10 並行執行 < 5000ms
- 50 並行執行 < 15000ms

Adapter Integration:
驗證 ConcurrentBuilderAdapter 和 WorkflowExecutorAdapter 並行效能

Author: IPA Platform Team
Version: 2.0.0 (Phase 5 Migration)
"""

import pytest
import pytest_asyncio
import asyncio
import time
from uuid import uuid4
from datetime import datetime
from typing import List, Dict, Any, Tuple
from statistics import mean, stdev
from dataclasses import dataclass
from httpx import AsyncClient, ASGITransport

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from main import app


# =============================================================================
# Concurrent Performance Metrics
# =============================================================================

@dataclass
class ConcurrentMetrics:
    """並行效能指標容器"""
    test_name: str
    concurrent_count: int
    total_duration_ms: float
    avg_individual_latency_ms: float
    max_individual_latency_ms: float
    success_count: int
    failure_count: int
    speedup_ratio: float  # 相對於順序執行的加速比

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "concurrent_count": self.concurrent_count,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "avg_individual_latency_ms": round(self.avg_individual_latency_ms, 2),
            "max_individual_latency_ms": round(self.max_individual_latency_ms, 2),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "speedup_ratio": round(self.speedup_ratio, 2),
        }


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
        timeout=60.0  # 較長超時用於並行測試
    ) as client:
        yield client


# =============================================================================
# Test Class: Concurrent Execution Performance
# =============================================================================

class TestConcurrentExecutionPerformance:
    """
    並行執行效能測試

    目標:
    - 10 並行執行 < 5000ms
    - 50 並行執行 < 15000ms
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_10_concurrent_workflow_executions(self, perf_client: AsyncClient):
        """
        測試 10 個並行工作流執行

        目標: < 5000ms
        """
        # 創建測試工作流
        workflow_data = {
            "name": f"Concurrent Test {datetime.now().strftime('%H%M%S')}",
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

        create_response = await perf_client.post(
            "/api/v1/workflows/",
            json=workflow_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建測試工作流")

        workflow_id = create_response.json().get("id")

        # 並行執行函數
        async def run_workflow(index: int) -> Tuple[float, bool]:
            op_start = time.time()
            response = await perf_client.post(
                f"/api/v1/workflows/{workflow_id}/run",
                json={"input_data": {"index": index}}
            )
            latency = time.time() - op_start
            success = response.status_code in [200, 201, 202]
            return latency, success

        # 執行 10 個並行請求
        start_time = time.time()
        tasks = [run_workflow(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        # 計算指標
        latencies = []
        success_count = 0
        for result in results:
            if not isinstance(result, Exception):
                latencies.append(result[0])
                if result[1]:
                    success_count += 1

        metrics = ConcurrentMetrics(
            test_name="10_concurrent_workflows",
            concurrent_count=10,
            total_duration_ms=total_duration * 1000,
            avg_individual_latency_ms=mean(latencies) * 1000 if latencies else 0,
            max_individual_latency_ms=max(latencies) * 1000 if latencies else 0,
            success_count=success_count,
            failure_count=10 - success_count,
            speedup_ratio=sum(latencies) / total_duration if total_duration > 0 else 0,
        )

        print(f"\n10 並行執行效能: {metrics.to_dict()}")

        # 驗證效能指標
        assert metrics.total_duration_ms < 5000, \
            f"10 並行執行時間 {metrics.total_duration_ms}ms 超過 5000ms"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_50_concurrent_api_requests(self, perf_client: AsyncClient):
        """
        測試 50 個並行 API 請求

        目標: < 15000ms
        """
        async def make_request(index: int) -> Tuple[float, bool]:
            op_start = time.time()
            response = await perf_client.get("/api/v1/workflows/")
            latency = time.time() - op_start
            success = response.status_code == 200
            return latency, success

        # 執行 50 個並行請求
        start_time = time.time()
        tasks = [make_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        # 計算指標
        latencies = []
        success_count = 0
        for result in results:
            if not isinstance(result, Exception):
                latencies.append(result[0])
                if result[1]:
                    success_count += 1

        metrics = ConcurrentMetrics(
            test_name="50_concurrent_requests",
            concurrent_count=50,
            total_duration_ms=total_duration * 1000,
            avg_individual_latency_ms=mean(latencies) * 1000 if latencies else 0,
            max_individual_latency_ms=max(latencies) * 1000 if latencies else 0,
            success_count=success_count,
            failure_count=50 - success_count,
            speedup_ratio=sum(latencies) / total_duration if total_duration > 0 else 0,
        )

        print(f"\n50 並行請求效能: {metrics.to_dict()}")

        # 驗證效能指標
        assert metrics.total_duration_ms < 15000, \
            f"50 並行請求時間 {metrics.total_duration_ms}ms 超過 15000ms"
        assert metrics.success_count >= 45, \
            f"成功率過低: {metrics.success_count}/50"


# =============================================================================
# Test Class: Scalability Tests
# =============================================================================

class TestScalabilityPerformance:
    """
    可擴展性效能測試
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_scaling(self, perf_client: AsyncClient):
        """
        測試並行度擴展效能

        測試不同並行度 (1, 5, 10, 20, 50) 的效能
        """
        async def make_request() -> Tuple[float, bool]:
            op_start = time.time()
            response = await perf_client.get("/api/v1/workflows/")
            latency = time.time() - op_start
            return latency, response.status_code == 200

        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}

        for concurrency in concurrency_levels:
            start_time = time.time()
            tasks = [make_request() for _ in range(concurrency)]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            total_duration = time.time() - start_time

            latencies = []
            success_count = 0
            for result in task_results:
                if not isinstance(result, Exception):
                    latencies.append(result[0])
                    if result[1]:
                        success_count += 1

            results[concurrency] = {
                "total_duration_ms": total_duration * 1000,
                "avg_latency_ms": mean(latencies) * 1000 if latencies else 0,
                "success_rate": (success_count / concurrency) * 100,
            }

        # 輸出擴展性報告
        print("\n" + "=" * 50)
        print("並行度擴展效能報告")
        print("=" * 50)

        for concurrency, metrics in results.items():
            print(f"\n並行度 {concurrency}:")
            print(f"  總時間: {metrics['total_duration_ms']:.2f}ms")
            print(f"  平均延遲: {metrics['avg_latency_ms']:.2f}ms")
            print(f"  成功率: {metrics['success_rate']:.1f}%")

        # 驗證擴展性
        # 並行度增加不應導致延遲急劇增加
        if results[10]["avg_latency_ms"] > 0:
            ratio_10_to_1 = results[10]["avg_latency_ms"] / max(results[1]["avg_latency_ms"], 1)
            assert ratio_10_to_1 < 5, f"10 並行延遲比 1 並行增加過多: {ratio_10_to_1}x"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_mixed_operation_concurrency(self, perf_client: AsyncClient):
        """
        測試混合操作並行效能

        同時執行 GET 和 POST 操作
        """
        async def get_request(index: int) -> Tuple[str, float, bool]:
            op_start = time.time()
            response = await perf_client.get("/api/v1/workflows/")
            latency = time.time() - op_start
            return "GET", latency, response.status_code == 200

        async def post_request(index: int) -> Tuple[str, float, bool]:
            op_start = time.time()
            response = await perf_client.post(
                "/api/v1/workflows/validate",
                json={
                    "graph_definition": {
                        "nodes": [
                            {"id": "start", "type": "start"},
                            {"id": "end", "type": "end"}
                        ],
                        "edges": [{"source": "start", "target": "end"}]
                    }
                }
            )
            latency = time.time() - op_start
            return "POST", latency, response.status_code == 200

        # 混合 15 GET + 15 POST
        start_time = time.time()
        tasks = []
        for i in range(15):
            tasks.append(get_request(i))
            tasks.append(post_request(i))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        get_latencies = []
        post_latencies = []
        get_success = 0
        post_success = 0

        for result in results:
            if not isinstance(result, Exception):
                method, latency, success = result
                if method == "GET":
                    get_latencies.append(latency)
                    if success:
                        get_success += 1
                else:
                    post_latencies.append(latency)
                    if success:
                        post_success += 1

        print(f"\n混合操作並行效能:")
        print(f"  總時間: {total_duration * 1000:.2f}ms")
        print(f"  GET 平均延遲: {mean(get_latencies) * 1000:.2f}ms ({get_success}/15 成功)")
        print(f"  POST 平均延遲: {mean(post_latencies) * 1000:.2f}ms ({post_success}/15 成功)")

        # 驗證混合操作效能
        assert total_duration < 10  # 30 個請求應該在 10 秒內完成


# =============================================================================
# Test Class: Adapter Concurrent Performance
# =============================================================================

class TestAdapterConcurrentPerformance:
    """
    Phase 5 適配器並行效能測試
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_handoff_operations(self, perf_client: AsyncClient):
        """
        測試並行 Handoff 操作 (使用 HandoffService)
        """
        async def trigger_handoff(index: int) -> Tuple[float, bool]:
            op_start = time.time()
            response = await perf_client.post(
                "/api/v1/handoff/trigger",
                json={
                    "source_agent_id": str(uuid4()),
                    "target_agent_id": str(uuid4()),
                    "reason": f"Concurrent test {index}"
                }
            )
            latency = time.time() - op_start
            return latency, response.status_code in [200, 201, 202]

        # 10 並行 handoff
        start_time = time.time()
        tasks = [trigger_handoff(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        latencies = [r[0] for r in results if not isinstance(r, Exception)]
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r[1])

        print(f"\n並行 Handoff 效能:")
        print(f"  總時間: {total_duration * 1000:.2f}ms")
        print(f"  平均延遲: {mean(latencies) * 1000:.2f}ms")
        print(f"  成功: {success_count}/10")

        assert total_duration < 5  # 10 並行應該在 5 秒內完成

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_checkpoint_operations(self, perf_client: AsyncClient):
        """
        測試並行 Checkpoint 操作 (使用 ApprovalWorkflowManager)
        """
        async def get_pending(index: int) -> Tuple[float, bool]:
            op_start = time.time()
            response = await perf_client.get("/api/v1/checkpoints/pending")
            latency = time.time() - op_start
            return latency, response.status_code in [200, 404]

        # 20 並行 checkpoint 查詢
        start_time = time.time()
        tasks = [get_pending(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        latencies = [r[0] for r in results if not isinstance(r, Exception)]
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r[1])

        print(f"\n並行 Checkpoint 查詢效能:")
        print(f"  總時間: {total_duration * 1000:.2f}ms")
        print(f"  平均延遲: {mean(latencies) * 1000:.2f}ms")
        print(f"  成功: {success_count}/20")

        assert total_duration < 5


# =============================================================================
# Test Class: Stress Tests
# =============================================================================

class TestConcurrentStress:
    """
    並行壓力測試
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_concurrent_load(self, perf_client: AsyncClient):
        """
        測試持續並行負載

        連續 5 秒內每秒發送 10 個並行請求
        """
        all_latencies = []
        all_success = 0
        all_requests = 0

        async def make_request() -> Tuple[float, bool]:
            op_start = time.time()
            response = await perf_client.get("/api/v1/workflows/")
            latency = time.time() - op_start
            return latency, response.status_code == 200

        start_time = time.time()
        while time.time() - start_time < 5:  # 5 秒
            # 每秒發送 10 個並行請求
            tasks = [make_request() for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if not isinstance(result, Exception):
                    all_latencies.append(result[0])
                    if result[1]:
                        all_success += 1
                all_requests += 1

            await asyncio.sleep(0.5)  # 每 0.5 秒一批

        total_duration = time.time() - start_time

        print(f"\n持續並行負載效能:")
        print(f"  總時間: {total_duration:.2f}s")
        print(f"  總請求: {all_requests}")
        print(f"  成功請求: {all_success}")
        print(f"  平均延遲: {mean(all_latencies) * 1000:.2f}ms")
        print(f"  吞吐量: {all_requests / total_duration:.2f} RPS")

        # 驗證系統在持續負載下穩定
        success_rate = (all_success / all_requests) * 100 if all_requests > 0 else 0
        assert success_rate > 90, f"成功率 {success_rate}% 低於 90%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
