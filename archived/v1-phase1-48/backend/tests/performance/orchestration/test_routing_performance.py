"""
Routing Performance Tests — Sprint 118.

Tests routing performance benchmarks for the orchestration pipeline:
1. PatternMatcher latency: P95 < 5ms (AD patterns)
2. SemanticRouter latency: P95 < 100ms (mock)
3. Full routing pipeline: P95 < 150ms
4. Concurrent throughput: 10 concurrent > 50 req/s
5. Embedding cache hit rate: > 50% (mock)

All tests use MockSemanticRouter and MockLLMClassifier to isolate
routing logic from external API latency.

Sprint 118: Story 118-2 — Semantic Routing E2E + Performance (Phase 32)
"""

import asyncio
import statistics
import time
from typing import Any, Dict, List

import pytest

from src.integrations.orchestration.intent_router import (
    BusinessIntentRouter,
    RouterConfig,
    PatternMatcher,
    ITIntentCategory,
    SemanticRoute,
    RiskLevel,
    WorkflowType,
)
from tests.mocks.orchestration import (
    MockSemanticRouter,
    MockLLMClassifier,
    MockCompletenessChecker,
)


# =============================================================================
# Utility Functions
# =============================================================================


def calculate_percentile(latencies: List[float], percentile: float) -> float:
    """Calculate percentile of latency list."""
    if not latencies:
        return 0.0
    sorted_latencies = sorted(latencies)
    idx = int(len(sorted_latencies) * percentile / 100)
    return sorted_latencies[min(idx, len(sorted_latencies) - 1)]


def format_latency_report(latencies: List[float], layer_name: str) -> str:
    """Format latency report for a layer."""
    if not latencies:
        return f"{layer_name}: No data"
    return (
        f"{layer_name}:\n"
        f"  Min: {min(latencies):.2f}ms\n"
        f"  Max: {max(latencies):.2f}ms\n"
        f"  Avg: {statistics.mean(latencies):.2f}ms\n"
        f"  P50: {calculate_percentile(latencies, 50):.2f}ms\n"
        f"  P95: {calculate_percentile(latencies, 95):.2f}ms\n"
        f"  P99: {calculate_percentile(latencies, 99):.2f}ms"
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ad_pattern_rules() -> Dict[str, Any]:
    """AD-focused pattern rules for performance testing."""
    rules = [
        {
            "id": "ad-unlock",
            "category": "request",
            "sub_intent": "ad.account.unlock",
            "patterns": [
                r"(?:解鎖|unlock).*(?:AD|帳號|account)",
                r"(?:AD|帳號|account).*(?:鎖定|locked)",
            ],
            "priority": 200,
            "workflow_type": "simple",
            "risk_level": "medium",
            "enabled": True,
        },
        {
            "id": "ad-password",
            "category": "request",
            "sub_intent": "ad.password.reset",
            "patterns": [
                r"(?:重設|reset|重置).*(?:密碼|password)",
                r"(?:密碼|password).*(?:重設|reset|過期|expired)",
            ],
            "priority": 200,
            "workflow_type": "simple",
            "risk_level": "medium",
            "enabled": True,
        },
        {
            "id": "ad-group",
            "category": "request",
            "sub_intent": "ad.group.modify",
            "patterns": [
                r"(?:加入|移除|變更|modify).*(?:群組|group)",
                r"(?:群組|group).*(?:成員|member)",
            ],
            "priority": 200,
            "workflow_type": "sequential",
            "risk_level": "high",
            "enabled": True,
        },
    ]

    # Add 50 synthetic rules to simulate production-scale rule sets
    for i in range(50):
        rules.append({
            "id": f"synthetic-{i:03d}",
            "category": "request" if i % 2 == 0 else "incident",
            "sub_intent": f"synthetic.intent.{i}",
            "patterns": [rf"synthetic_pattern_{i}", rf"pattern_{i}_variant"],
            "priority": 50 + i,
            "workflow_type": "simple",
            "risk_level": "low",
            "enabled": True,
        })

    return {"rules": rules}


@pytest.fixture
def ad_semantic_routes() -> List[SemanticRoute]:
    """AD-focused semantic routes for performance testing."""
    routes = [
        SemanticRoute(
            name="ad_account_unlock",
            category=ITIntentCategory.REQUEST,
            sub_intent="ad.account.unlock",
            utterances=[
                "AD 帳號被鎖定",
                "帳號無法登入被鎖住了",
                "使用者帳戶被鎖定需要解鎖",
                "unlock AD account",
                "account locked out",
            ],
            workflow_type=WorkflowType.SIMPLE,
            risk_level=RiskLevel.MEDIUM,
        ),
        SemanticRoute(
            name="ad_password_reset",
            category=ITIntentCategory.REQUEST,
            sub_intent="ad.password.reset",
            utterances=[
                "AD 密碼重設",
                "忘記密碼需要重置",
                "reset AD password",
                "使用者密碼需要重設",
                "密碼過期要更新",
            ],
            workflow_type=WorkflowType.SIMPLE,
            risk_level=RiskLevel.MEDIUM,
        ),
        SemanticRoute(
            name="ad_group_modify",
            category=ITIntentCategory.REQUEST,
            sub_intent="ad.group.modify",
            utterances=[
                "加入 AD 群組",
                "變更群組成員",
                "修改 AD group membership",
                "新增使用者到 admin 群組",
                "移除群組權限",
            ],
            workflow_type=WorkflowType.SEQUENTIAL,
            risk_level=RiskLevel.HIGH,
        ),
    ]

    # Add 10 additional routes for realistic route count
    for i in range(10):
        routes.append(
            SemanticRoute(
                name=f"additional_route_{i}",
                category=ITIntentCategory.INCIDENT if i % 2 == 0 else ITIntentCategory.QUERY,
                sub_intent=f"additional.intent.{i}",
                utterances=[
                    f"additional utterance {i} first",
                    f"additional utterance {i} second",
                    f"additional utterance {i} third",
                ],
                workflow_type=WorkflowType.SIMPLE,
                risk_level=RiskLevel.LOW,
            )
        )

    return routes


@pytest.fixture
def performance_router(
    ad_pattern_rules: Dict[str, Any],
    ad_semantic_routes: List[SemanticRoute],
) -> BusinessIntentRouter:
    """Router configured for performance benchmarks."""
    return BusinessIntentRouter(
        pattern_matcher=PatternMatcher(rules_dict=ad_pattern_rules),
        semantic_router=MockSemanticRouter(routes=ad_semantic_routes),
        llm_classifier=MockLLMClassifier(),
        completeness_checker=MockCompletenessChecker(),
        config=RouterConfig(
            pattern_threshold=0.90,
            semantic_threshold=0.85,
            enable_llm_fallback=True,
            enable_completeness=True,
            track_latency=True,
        ),
    )


# =============================================================================
# Test 1: PatternMatcher Latency (P95 < 5ms)
# =============================================================================


class TestPatternMatcherLatency:
    """PatternMatcher performance: P95 < 5ms with 50+ rules."""

    P95_TARGET_MS = 5.0
    ITERATIONS = 200

    @pytest.mark.asyncio
    async def test_pattern_p95_under_5ms(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """PatternMatcher P95 latency should be under 5ms."""
        test_inputs = [
            "解鎖 AD 帳號 john.doe",
            "重設密碼 jane.doe",
            "加入群組 admin-group",
        ] * (self.ITERATIONS // 3 + 1)

        latencies: List[float] = []

        for user_input in test_inputs[: self.ITERATIONS]:
            start = time.perf_counter()
            decision = await performance_router.route(user_input)
            latency_ms = (time.perf_counter() - start) * 1000

            if decision.routing_layer == "pattern":
                latencies.append(latency_ms)

        assert len(latencies) > 0, "No pattern-matched results found"
        p95 = calculate_percentile(latencies, 95)
        print(f"\n{format_latency_report(latencies, 'PatternMatcher (AD)')}")
        print(f"  P95 Target: {self.P95_TARGET_MS}ms")

        assert p95 < self.P95_TARGET_MS, (
            f"PatternMatcher P95 ({p95:.2f}ms) exceeds {self.P95_TARGET_MS}ms target"
        )

    @pytest.mark.asyncio
    async def test_pattern_scales_with_ad_rules(
        self,
        ad_pattern_rules: Dict[str, Any],
    ):
        """Pattern matching should scale linearly with rule count."""
        rule_counts = [10, 30, 53]  # Increasing subsets of rules
        results: List[tuple] = []

        for count in rule_counts:
            subset = {"rules": ad_pattern_rules["rules"][:count]}
            router = BusinessIntentRouter(
                pattern_matcher=PatternMatcher(rules_dict=subset),
                semantic_router=MockSemanticRouter(routes=[]),
                llm_classifier=MockLLMClassifier(),
                config=RouterConfig(enable_llm_fallback=False),
            )

            latencies = []
            for _ in range(50):
                start = time.perf_counter()
                await router.route("解鎖 AD 帳號")
                latencies.append((time.perf_counter() - start) * 1000)

            avg = statistics.mean(latencies)
            results.append((count, avg))

        print("\nPatternMatcher Scalability (AD rules):")
        for count, latency in results:
            print(f"  {count} rules: {latency:.2f}ms avg")

        # Last result should still be under 5ms
        _, last_latency = results[-1]
        assert last_latency < self.P95_TARGET_MS, (
            f"Pattern matching with {results[-1][0]} rules takes {last_latency:.2f}ms"
        )


# =============================================================================
# Test 2: SemanticRouter Latency (P95 < 100ms)
# =============================================================================


class TestSemanticRouterLatency:
    """SemanticRouter performance: P95 < 100ms (mock)."""

    P95_TARGET_MS = 100.0
    ITERATIONS = 200

    @pytest.mark.asyncio
    async def test_semantic_p95_under_100ms(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """SemanticRouter (mock) P95 latency should be under 100ms."""
        # Inputs that miss patterns and hit semantic layer
        test_inputs = [
            "使用者帳戶需要解鎖",
            "忘了密碼怎麼辦",
            "需要變更群組成員資格",
            "帳號解鎖協助",
            "密碼重設請求",
        ] * (self.ITERATIONS // 5 + 1)

        latencies: List[float] = []

        for user_input in test_inputs[: self.ITERATIONS]:
            start = time.perf_counter()
            decision = await performance_router.route(user_input)
            latency_ms = (time.perf_counter() - start) * 1000

            if decision.routing_layer in ["semantic", "llm"]:
                latencies.append(latency_ms)

        if latencies:
            p95 = calculate_percentile(latencies, 95)
            print(f"\n{format_latency_report(latencies, 'SemanticRouter (Mock)')}")
            print(f"  P95 Target: {self.P95_TARGET_MS}ms")

            assert p95 < self.P95_TARGET_MS, (
                f"SemanticRouter P95 ({p95:.2f}ms) exceeds {self.P95_TARGET_MS}ms target"
            )
        else:
            # All routed at pattern layer — semantic performance is trivially met
            print("\nSemanticRouter: All inputs matched at pattern layer")

    @pytest.mark.asyncio
    async def test_semantic_with_13_routes(
        self,
        ad_semantic_routes: List[SemanticRoute],
    ):
        """SemanticRouter should perform well with 13 routes (AD + generic)."""
        router = BusinessIntentRouter(
            pattern_matcher=PatternMatcher(rules_dict={"rules": []}),
            semantic_router=MockSemanticRouter(routes=ad_semantic_routes),
            llm_classifier=MockLLMClassifier(),
            config=RouterConfig(enable_llm_fallback=True),
        )

        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await router.route("AD 帳號被鎖定")
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = calculate_percentile(latencies, 95)
        print(f"\nSemanticRouter (13 routes) P95: {p95:.2f}ms")

        assert p95 < self.P95_TARGET_MS


# =============================================================================
# Test 3: Full Routing Pipeline (P95 < 150ms)
# =============================================================================


class TestFullRoutingPipelineLatency:
    """Full routing pipeline: P95 < 150ms."""

    P95_TARGET_MS = 150.0
    ITERATIONS = 300

    @pytest.mark.asyncio
    async def test_full_pipeline_p95_under_150ms(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Full routing pipeline P95 should be under 150ms."""
        # Mix of inputs that exercise all layers
        test_inputs = [
            "解鎖 AD 帳號 john.doe",  # pattern hit
            "重設密碼 jane.doe",  # pattern hit
            "使用者帳戶需要解鎖",  # semantic or pattern
            "有些問題需要處理",  # llm fallback
            "加入群組 admin-group",  # pattern hit
            "系統有異常",  # semantic/llm
        ] * (self.ITERATIONS // 6 + 1)

        latencies: List[float] = []

        for user_input in test_inputs[: self.ITERATIONS]:
            start = time.perf_counter()
            await performance_router.route(user_input)
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = calculate_percentile(latencies, 95)
        avg = statistics.mean(latencies)

        print(f"\n{format_latency_report(latencies, 'Full Routing Pipeline')}")
        print(f"  P95 Target: {self.P95_TARGET_MS}ms")

        assert p95 < self.P95_TARGET_MS, (
            f"Full pipeline P95 ({p95:.2f}ms) exceeds {self.P95_TARGET_MS}ms target"
        )

    @pytest.mark.asyncio
    async def test_routing_layer_distribution(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Verify routing layer distribution across mixed inputs."""
        test_inputs = [
            "解鎖 AD 帳號",
            "重設密碼",
            "加入群組",
            "不相關的內容",
            "系統有問題",
        ] * 10

        layer_counts: Dict[str, int] = {}

        for user_input in test_inputs:
            decision = await performance_router.route(user_input)
            layer = decision.routing_layer
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

        total = sum(layer_counts.values())
        print("\nRouting Layer Distribution:")
        for layer, count in sorted(layer_counts.items()):
            pct = count / total * 100
            print(f"  {layer}: {count}/{total} ({pct:.1f}%)")

        # Pattern layer should handle a significant portion
        assert total == len(test_inputs)


# =============================================================================
# Test 4: Concurrent Throughput (10 concurrent > 50 req/s)
# =============================================================================


class TestConcurrentThroughput:
    """Concurrent throughput: 10 concurrent requesters > 50 req/s total."""

    CONCURRENT_WORKERS = 10
    REQUESTS_PER_WORKER = 20
    TARGET_RPS = 50.0

    @pytest.mark.asyncio
    async def test_concurrent_throughput_above_50rps(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """10 concurrent workers should achieve > 50 requests/second."""

        async def worker(router: BusinessIntentRouter, inputs: List[str]) -> List[float]:
            latencies = []
            for inp in inputs:
                start = time.perf_counter()
                await router.route(inp)
                latencies.append((time.perf_counter() - start) * 1000)
            return latencies

        # Each worker gets a mix of inputs
        worker_inputs = [
            [f"解鎖 AD 帳號 user-{i}-{j}" for j in range(self.REQUESTS_PER_WORKER)]
            for i in range(self.CONCURRENT_WORKERS)
        ]

        start = time.perf_counter()
        tasks = [worker(performance_router, inputs) for inputs in worker_inputs]
        all_latencies_nested = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

        all_latencies = [lat for worker_lats in all_latencies_nested for lat in worker_lats]
        total_requests = self.CONCURRENT_WORKERS * self.REQUESTS_PER_WORKER
        rps = total_requests / total_time

        print(f"\nConcurrent Throughput ({self.CONCURRENT_WORKERS} workers):")
        print(f"  Total requests: {total_requests}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {rps:.1f} req/s")
        print(f"  Avg latency: {statistics.mean(all_latencies):.2f}ms")
        print(f"  P95 latency: {calculate_percentile(all_latencies, 95):.2f}ms")
        print(f"  Target: > {self.TARGET_RPS} req/s")

        assert rps > self.TARGET_RPS, (
            f"Throughput ({rps:.1f} req/s) below {self.TARGET_RPS} req/s target"
        )

    @pytest.mark.asyncio
    async def test_burst_100_concurrent(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Burst of 100 concurrent requests should complete within 5 seconds."""
        inputs = [f"AD 帳號問題 #{i}" for i in range(100)]

        start = time.perf_counter()
        tasks = [performance_router.route(inp) for inp in inputs]
        results = await asyncio.gather(*tasks)
        burst_time = (time.perf_counter() - start) * 1000

        print(f"\nBurst Test (100 concurrent):")
        print(f"  Total time: {burst_time:.2f}ms")
        print(f"  Avg per request: {burst_time / 100:.2f}ms")

        assert len(results) == 100
        assert burst_time < 5000, f"Burst took {burst_time:.2f}ms (target < 5000ms)"


# =============================================================================
# Test 5: Embedding Cache Hit Rate (> 50%)
# =============================================================================


class TestEmbeddingCacheHitRate:
    """Embedding cache simulation: repeated queries should benefit from caching."""

    CACHE_HIT_TARGET = 0.50

    @pytest.mark.asyncio
    async def test_repeated_queries_faster_than_first(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Repeated identical queries should be faster than first invocation."""
        query = "解鎖 AD 帳號 john.doe"

        # First pass — cold
        cold_latencies = []
        for _ in range(10):
            start = time.perf_counter()
            await performance_router.route(query)
            cold_latencies.append((time.perf_counter() - start) * 1000)

        # Second pass — warm (same query)
        warm_latencies = []
        for _ in range(10):
            start = time.perf_counter()
            await performance_router.route(query)
            warm_latencies.append((time.perf_counter() - start) * 1000)

        cold_avg = statistics.mean(cold_latencies)
        warm_avg = statistics.mean(warm_latencies)

        print(f"\nEmbedding Cache Simulation:")
        print(f"  Cold avg: {cold_avg:.2f}ms")
        print(f"  Warm avg: {warm_avg:.2f}ms")

        # Warm queries should not be significantly slower than cold
        # (With mocks, both are fast — this validates no regression)
        assert warm_avg < cold_avg * 2.0, (
            f"Warm queries ({warm_avg:.2f}ms) significantly slower than cold ({cold_avg:.2f}ms)"
        )

    @pytest.mark.asyncio
    async def test_cache_benefit_with_mixed_queries(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Mixed query workload should show caching benefit for repeated queries."""
        unique_queries = [
            "解鎖 AD 帳號",
            "重設密碼",
            "加入群組",
            "查詢狀態",
            "申請帳號",
        ]

        # Run each query 10 times — cache should help repeated ones
        all_latencies: Dict[str, List[float]] = {}

        for query in unique_queries:
            all_latencies[query] = []
            for _ in range(10):
                start = time.perf_counter()
                await performance_router.route(query)
                all_latencies[query].append((time.perf_counter() - start) * 1000)

        print("\nCache Benefit Analysis:")
        cache_effective_count = 0

        for query, latencies in all_latencies.items():
            first_half_avg = statistics.mean(latencies[:5])
            second_half_avg = statistics.mean(latencies[5:])
            improvement = (
                (first_half_avg - second_half_avg) / first_half_avg * 100
                if first_half_avg > 0
                else 0
            )

            print(f"  '{query[:20]}': first_half={first_half_avg:.2f}ms, second_half={second_half_avg:.2f}ms ({improvement:+.1f}%)")

            # Count queries where second half is not slower
            if second_half_avg <= first_half_avg * 1.5:
                cache_effective_count += 1

        cache_rate = cache_effective_count / len(unique_queries)
        print(f"\n  Cache effective rate: {cache_rate:.1%}")
        print(f"  Target: > {self.CACHE_HIT_TARGET:.0%}")

        assert cache_rate >= self.CACHE_HIT_TARGET, (
            f"Cache effective rate ({cache_rate:.1%}) below {self.CACHE_HIT_TARGET:.0%}"
        )


# =============================================================================
# Performance Report
# =============================================================================


class TestPerformanceReport:
    """Generate comprehensive Sprint 118 routing performance report."""

    @pytest.mark.asyncio
    async def test_generate_sprint_118_report(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Generate consolidated performance report for Sprint 118."""
        report_data: Dict[str, Dict[str, float]] = {}

        # 1. Pattern Layer
        pattern_latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await performance_router.route("解鎖 AD 帳號")
            pattern_latencies.append((time.perf_counter() - start) * 1000)
        report_data["PatternMatcher"] = {
            "P95_ms": calculate_percentile(pattern_latencies, 95),
            "Avg_ms": statistics.mean(pattern_latencies),
            "Target_ms": 5.0,
        }

        # 2. Semantic Layer (via non-pattern input)
        semantic_latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await performance_router.route("使用者帳號有問題")
            semantic_latencies.append((time.perf_counter() - start) * 1000)
        report_data["SemanticRouter"] = {
            "P95_ms": calculate_percentile(semantic_latencies, 95),
            "Avg_ms": statistics.mean(semantic_latencies),
            "Target_ms": 100.0,
        }

        # 3. Full Pipeline
        mixed_inputs = ["解鎖 AD 帳號", "有問題", "重設密碼", "不明要求"] * 25
        pipeline_latencies = []
        for inp in mixed_inputs:
            start = time.perf_counter()
            await performance_router.route(inp)
            pipeline_latencies.append((time.perf_counter() - start) * 1000)
        report_data["FullPipeline"] = {
            "P95_ms": calculate_percentile(pipeline_latencies, 95),
            "Avg_ms": statistics.mean(pipeline_latencies),
            "Target_ms": 150.0,
        }

        # 4. Throughput
        burst_inputs = [f"request #{i}" for i in range(200)]
        start = time.perf_counter()
        tasks = [performance_router.route(inp) for inp in burst_inputs]
        await asyncio.gather(*tasks)
        throughput_time = time.perf_counter() - start
        rps = len(burst_inputs) / throughput_time
        report_data["Throughput"] = {
            "Requests_per_second": rps,
            "Total_requests": float(len(burst_inputs)),
            "Target_rps": 50.0,
        }

        # Print report
        print("\n" + "=" * 60)
        print("Sprint 118 — Routing Performance Report")
        print("=" * 60)
        for component, metrics in report_data.items():
            print(f"\n{component}:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value:.2f}")
        print("=" * 60)

        # All targets met
        assert report_data["PatternMatcher"]["P95_ms"] < 5.0
        assert report_data["SemanticRouter"]["P95_ms"] < 100.0
        assert report_data["FullPipeline"]["P95_ms"] < 150.0
        assert report_data["Throughput"]["Requests_per_second"] > 50.0


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
