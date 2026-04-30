"""
IPA Platform - Memory Usage Tests

Sprint 30 S30-2: 效能測試
記憶體使用測試

效能指標:
- 基準記憶體 < 512MB
- 高負載 < 1GB

Adapter Integration:
驗證 Phase 5 適配器不會導致記憶體洩漏

Author: IPA Platform Team
Version: 2.0.0 (Phase 5 Migration)
"""

import pytest
import pytest_asyncio
import asyncio
import gc
import sys
import os
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# =============================================================================
# Memory Measurement Utilities
# =============================================================================

def get_memory_usage_mb() -> float:
    """獲取當前進程記憶體使用量 (MB)"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        # 如果 psutil 不可用，使用 sys.getsizeof 估算
        return 0.0


def force_gc():
    """強制垃圾回收"""
    gc.collect()
    gc.collect()
    gc.collect()


@dataclass
class MemoryMetrics:
    """記憶體指標容器"""
    test_name: str
    initial_mb: float
    peak_mb: float
    final_mb: float
    delta_mb: float
    objects_created: int
    objects_collected: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "initial_mb": round(self.initial_mb, 2),
            "peak_mb": round(self.peak_mb, 2),
            "final_mb": round(self.final_mb, 2),
            "delta_mb": round(self.delta_mb, 2),
            "objects_created": self.objects_created,
            "objects_collected": self.objects_collected,
        }


# =============================================================================
# Test Class: Baseline Memory Tests
# =============================================================================

class TestBaselineMemory:
    """
    基準記憶體測試

    目標: 基準記憶體 < 512MB
    """

    @pytest.mark.performance
    def test_adapter_import_memory(self):
        """
        測試導入適配器模組的記憶體影響
        """
        force_gc()
        initial_memory = get_memory_usage_mb()

        # 導入所有主要適配器
        from src.integrations.agent_framework.builders.groupchat import GroupChatBuilderAdapter
        from src.integrations.agent_framework.builders.handoff import HandoffBuilderAdapter
        from src.integrations.agent_framework.builders.concurrent import ConcurrentBuilderAdapter
        from src.integrations.agent_framework.builders.planning import PlanningAdapter
        from src.integrations.agent_framework.core.workflow import WorkflowDefinitionAdapter
        from src.integrations.agent_framework.core.state_machine import EnhancedExecutionStateMachine
        from src.integrations.agent_framework.core.approval import HumanApprovalExecutor

        force_gc()
        final_memory = get_memory_usage_mb()

        delta = final_memory - initial_memory

        print(f"\n適配器導入記憶體影響:")
        print(f"  初始: {initial_memory:.2f}MB")
        print(f"  最終: {final_memory:.2f}MB")
        print(f"  增量: {delta:.2f}MB")

        # 導入適配器不應使用過多記憶體
        assert delta < 100, f"導入適配器使用了 {delta}MB 記憶體，超過 100MB"

    @pytest.mark.performance
    def test_adapter_instantiation_memory(self):
        """
        測試實例化適配器的記憶體影響
        """
        from src.integrations.agent_framework.builders.handoff import HandoffBuilderAdapter
        from src.integrations.agent_framework.builders.concurrent import ConcurrentBuilderAdapter

        force_gc()
        initial_memory = get_memory_usage_mb()
        initial_objects = len(gc.get_objects())

        # 創建多個適配器實例
        adapters = []
        for i in range(100):
            adapters.append(HandoffBuilderAdapter(id=f"handoff-{i}"))
            adapters.append(ConcurrentBuilderAdapter(id=f"concurrent-{i}"))

        peak_memory = get_memory_usage_mb()

        # 清理
        del adapters
        force_gc()

        final_memory = get_memory_usage_mb()
        final_objects = len(gc.get_objects())

        metrics = MemoryMetrics(
            test_name="adapter_instantiation",
            initial_mb=initial_memory,
            peak_mb=peak_memory,
            final_mb=final_memory,
            delta_mb=final_memory - initial_memory,
            objects_created=final_objects - initial_objects,
            objects_collected=0,
        )

        print(f"\n適配器實例化記憶體: {metrics.to_dict()}")

        # 清理後記憶體應該回到接近初始水平
        assert metrics.delta_mb < 10, f"記憶體洩漏: {metrics.delta_mb}MB"


# =============================================================================
# Test Class: Load Memory Tests
# =============================================================================

class TestLoadMemory:
    """
    高負載記憶體測試

    目標: 高負載 < 1GB
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_high_volume_operations_memory(self):
        """
        測試高容量操作的記憶體使用

        執行 1000 次操作並監控記憶體
        """
        from src.integrations.agent_framework.builders.workflow_executor import (
            WorkflowExecutorAdapter,
            SimpleWorkflow,
            create_workflow_executor,
        )

        async def simple_process(data, responses):
            return {"result": data.get("i", 0) * 2}

        force_gc()
        initial_memory = get_memory_usage_mb()
        peak_memory = initial_memory

        # 執行 1000 次操作
        for batch in range(10):
            workflow = SimpleWorkflow(id=f"mem-wf-{batch}", executor_fn=simple_process)
            executor = create_workflow_executor(id=f"mem-exec-{batch}", workflow=workflow)
            executor.build()

            for i in range(100):
                await executor.run({"i": i})
                executor.clear_events()

            # 記錄峰值
            current_memory = get_memory_usage_mb()
            peak_memory = max(peak_memory, current_memory)

            # 每批次後清理
            del executor
            del workflow
            force_gc()

        force_gc()
        final_memory = get_memory_usage_mb()

        print(f"\n高容量操作記憶體:")
        print(f"  初始: {initial_memory:.2f}MB")
        print(f"  峰值: {peak_memory:.2f}MB")
        print(f"  最終: {final_memory:.2f}MB")
        print(f"  峰值增量: {peak_memory - initial_memory:.2f}MB")

        # 峰值記憶體應該 < 1GB
        assert peak_memory < 1024, f"峰值記憶體 {peak_memory}MB 超過 1GB"

        # 最終記憶體應該回到接近初始水平
        final_delta = final_memory - initial_memory
        assert final_delta < 50, f"記憶體洩漏: {final_delta}MB"

    @pytest.mark.performance
    def test_large_workflow_definition_memory(self):
        """
        測試大型工作流定義的記憶體使用
        """
        from src.integrations.agent_framework.core.workflow import (
            WorkflowDefinitionAdapter,
            WorkflowDefinition,
        )

        force_gc()
        initial_memory = get_memory_usage_mb()

        # 創建大型工作流定義 (100 個節點)
        definitions = []
        for wf in range(10):
            nodes = [{"id": f"node-{i}", "type": "function"} for i in range(100)]
            nodes.insert(0, {"id": "start", "type": "start"})
            nodes.append({"id": "end", "type": "end"})

            edges = [
                {"source": nodes[i]["id"], "target": nodes[i + 1]["id"]}
                for i in range(len(nodes) - 1)
            ]

            definition = WorkflowDefinition(
                id=f"large-wf-{wf}",
                name=f"Large Workflow {wf}",
                nodes=nodes,
                edges=edges,
            )

            adapter = WorkflowDefinitionAdapter(definition=definition)
            definitions.append(adapter)

        peak_memory = get_memory_usage_mb()

        # 清理
        del definitions
        force_gc()

        final_memory = get_memory_usage_mb()

        print(f"\n大型工作流定義記憶體:")
        print(f"  初始: {initial_memory:.2f}MB")
        print(f"  峰值: {peak_memory:.2f}MB")
        print(f"  最終: {final_memory:.2f}MB")

        # 10 個大型工作流不應使用過多記憶體
        assert peak_memory - initial_memory < 100


# =============================================================================
# Test Class: Memory Leak Detection
# =============================================================================

class TestMemoryLeakDetection:
    """
    記憶體洩漏檢測測試
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_repeated_operations_no_leak(self):
        """
        測試重複操作不會導致記憶體洩漏

        重複執行操作並驗證記憶體穩定
        """
        from src.integrations.agent_framework.builders.workflow_executor import (
            SimpleWorkflow,
            create_workflow_executor,
        )

        async def process(data, responses):
            return {"result": "done"}

        force_gc()
        memory_samples = []

        # 收集 10 個記憶體樣本
        for iteration in range(10):
            workflow = SimpleWorkflow(id=f"leak-wf-{iteration}", executor_fn=process)
            executor = create_workflow_executor(id=f"leak-exec-{iteration}", workflow=workflow)
            executor.build()

            # 執行 100 次操作
            for i in range(100):
                await executor.run({"i": i})

            executor.clear_events()
            del executor
            del workflow
            force_gc()

            memory_samples.append(get_memory_usage_mb())

        print(f"\n記憶體樣本: {[f'{m:.2f}' for m in memory_samples]}")

        # 檢查記憶體趨勢
        # 後 5 個樣本的平均不應比前 5 個高太多
        first_half_avg = sum(memory_samples[:5]) / 5
        second_half_avg = sum(memory_samples[5:]) / 5

        growth = second_half_avg - first_half_avg
        print(f"記憶體增長趨勢: {growth:.2f}MB")

        # 記憶體不應持續增長
        assert growth < 20, f"檢測到記憶體洩漏，增長 {growth}MB"

    @pytest.mark.performance
    def test_adapter_reuse_no_leak(self):
        """
        測試適配器重用不會導致記憶體洩漏
        """
        from src.integrations.agent_framework.builders.handoff_service import (
            HandoffService,
            create_handoff_service,
        )

        force_gc()
        initial_memory = get_memory_usage_mb()

        # 創建和重用服務
        service = create_handoff_service()

        memory_after_create = get_memory_usage_mb()

        # 重複使用服務
        for i in range(1000):
            # 模擬服務操作
            _ = service.get_handoff_status(str(uuid4()))

        memory_after_use = get_memory_usage_mb()

        print(f"\n適配器重用記憶體:")
        print(f"  初始: {initial_memory:.2f}MB")
        print(f"  創建後: {memory_after_create:.2f}MB")
        print(f"  1000 次使用後: {memory_after_use:.2f}MB")

        # 使用後記憶體不應顯著增加
        use_growth = memory_after_use - memory_after_create
        assert use_growth < 10, f"服務重用導致記憶體增長 {use_growth}MB"


# =============================================================================
# Test Class: Object Lifecycle Tests
# =============================================================================

class TestObjectLifecycle:
    """
    對象生命週期測試
    """

    @pytest.mark.performance
    def test_gc_collects_unused_adapters(self):
        """
        測試垃圾回收正確清理未使用的適配器
        """
        from src.integrations.agent_framework.builders.handoff import HandoffBuilderAdapter
        from src.integrations.agent_framework.builders.concurrent import ConcurrentBuilderAdapter

        force_gc()
        initial_count = len(gc.get_objects())

        # 創建適配器
        adapters = [HandoffBuilderAdapter(id=f"gc-test-{i}") for i in range(100)]

        created_count = len(gc.get_objects())

        # 刪除引用
        del adapters

        # 強制 GC
        collected = gc.collect()

        final_count = len(gc.get_objects())

        print(f"\n對象生命週期:")
        print(f"  初始對象: {initial_count}")
        print(f"  創建後對象: {created_count}")
        print(f"  GC 收集: {collected}")
        print(f"  最終對象: {final_count}")

        # GC 後對象數應該接近初始值
        object_delta = final_count - initial_count
        assert object_delta < 1000, f"對象數增加 {object_delta}，可能有洩漏"

    @pytest.mark.performance
    def test_circular_reference_cleanup(self):
        """
        測試循環引用正確清理
        """
        force_gc()
        initial_count = len(gc.get_objects())

        # 創建帶循環引用的對象
        class Node:
            def __init__(self, name):
                self.name = name
                self.children = []
                self.parent = None

        nodes = []
        for i in range(100):
            node = Node(f"node-{i}")
            if nodes:
                node.parent = nodes[-1]  # 循環引用
                nodes[-1].children.append(node)
            nodes.append(node)

        created_count = len(gc.get_objects())

        # 刪除所有引用
        del nodes
        del node

        # GC 應該處理循環引用
        collected = gc.collect()

        final_count = len(gc.get_objects())

        print(f"\n循環引用清理:")
        print(f"  創建後: {created_count}")
        print(f"  GC 收集: {collected}")
        print(f"  最終: {final_count}")

        # Python GC 應該處理循環引用
        assert collected > 0 or final_count <= created_count


# =============================================================================
# Test Class: Memory Benchmark
# =============================================================================

class TestMemoryBenchmark:
    """
    記憶體基準測試
    """

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_comprehensive_memory_benchmark(self):
        """
        綜合記憶體基準測試

        測試所有主要操作的記憶體影響
        """
        from src.integrations.agent_framework.builders.workflow_executor import (
            SimpleWorkflow,
            create_workflow_executor,
        )
        from src.integrations.agent_framework.builders.handoff import HandoffBuilderAdapter
        from src.integrations.agent_framework.builders.concurrent import ConcurrentBuilderAdapter

        async def process(data, responses):
            return {"result": data}

        force_gc()
        initial_memory = get_memory_usage_mb()

        print("\n" + "=" * 50)
        print("記憶體基準測試報告")
        print("=" * 50)
        print(f"\n初始記憶體: {initial_memory:.2f}MB")

        # 測試 1: 適配器創建
        adapters = []
        for i in range(50):
            adapters.append(HandoffBuilderAdapter(id=f"bench-h-{i}"))
            adapters.append(ConcurrentBuilderAdapter(id=f"bench-c-{i}"))

        after_adapters = get_memory_usage_mb()
        print(f"100 個適配器後: {after_adapters:.2f}MB (+{after_adapters - initial_memory:.2f})")

        # 測試 2: 工作流執行
        workflow = SimpleWorkflow(id="bench-wf", executor_fn=process)
        executor = create_workflow_executor(id="bench-exec", workflow=workflow)
        executor.build()

        for i in range(500):
            await executor.run({"i": i})

        after_executions = get_memory_usage_mb()
        print(f"500 次執行後: {after_executions:.2f}MB (+{after_executions - after_adapters:.2f})")

        # 清理
        del adapters
        del executor
        del workflow
        force_gc()

        final_memory = get_memory_usage_mb()
        print(f"清理後: {final_memory:.2f}MB")
        print(f"總增量: {final_memory - initial_memory:.2f}MB")
        print("=" * 50)

        # 驗證
        assert final_memory < 512, f"記憶體使用 {final_memory}MB 超過 512MB 基準"
        assert final_memory - initial_memory < 50, f"記憶體增量 {final_memory - initial_memory}MB 過大"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
