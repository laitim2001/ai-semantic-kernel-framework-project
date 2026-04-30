"""
Performance Tests for BusinessIntentRouter

Tests latency requirements for each routing layer:
- Pattern Layer: P95 < 10ms
- Semantic Layer: P95 < 100ms (Mock)
- LLM Layer: P95 < 2000ms (Mock)
- Overall P95 (no LLM): < 500ms

Sprint 93: Story 93-5 - Performance Benchmark Tests (Phase 28)
"""

import asyncio
import pytest
import statistics
import time
from typing import Any, Dict, List

from src.integrations.orchestration.intent_router import (
    BusinessIntentRouter,
    MockBusinessIntentRouter,
    RouterConfig,
    PatternMatcher,
    MockSemanticRouter,
    MockLLMClassifier,
    CompletenessChecker,
    MockCompletenessChecker,
    ITIntentCategory,
    SemanticRoute,
    RiskLevel,
    WorkflowType,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def large_pattern_rules() -> Dict[str, Any]:
    """Large set of pattern rules for performance testing."""
    rules = []

    # Generate 100 incident rules
    for i in range(100):
        rules.append({
            "id": f"incident-{i:03d}",
            "category": "incident",
            "sub_intent": f"incident_type_{i}",
            "patterns": [
                rf"故障類型{i}",
                rf"問題代碼{i}",
                rf"錯誤編號{i}",
            ],
            "priority": 100 + i,
            "workflow_type": "sequential",
            "risk_level": "medium",
            "enabled": True,
        })

    # Generate 50 request rules
    for i in range(50):
        rules.append({
            "id": f"request-{i:03d}",
            "category": "request",
            "sub_intent": f"request_type_{i}",
            "patterns": [
                rf"申請類型{i}",
                rf"請求代碼{i}",
            ],
            "priority": 50 + i,
            "workflow_type": "simple",
            "risk_level": "low",
            "enabled": True,
        })

    # Add high-priority rules that should match test inputs
    rules.append({
        "id": "incident-etl-main",
        "category": "incident",
        "sub_intent": "etl_failure",
        "patterns": [r"ETL.*(?:失敗|錯誤|fail)", r"資料同步.*(?:問題|異常)"],
        "priority": 300,
        "workflow_type": "sequential",
        "risk_level": "high",
        "enabled": True,
    })

    rules.append({
        "id": "request-account-main",
        "category": "request",
        "sub_intent": "account_creation",
        "patterns": [r"(?:申請|開通|建立).*帳號"],
        "priority": 250,
        "workflow_type": "simple",
        "risk_level": "medium",
        "enabled": True,
    })

    return {"rules": rules}


@pytest.fixture
def semantic_routes() -> List[SemanticRoute]:
    """Semantic routes for performance testing."""
    routes = []

    # Create 20 routes with 5 utterances each
    categories = [
        (ITIntentCategory.INCIDENT, "incident"),
        (ITIntentCategory.REQUEST, "request"),
        (ITIntentCategory.CHANGE, "change"),
        (ITIntentCategory.QUERY, "query"),
    ]

    for i in range(20):
        cat, cat_str = categories[i % 4]
        routes.append(
            SemanticRoute(
                name=f"{cat_str}_route_{i}",
                category=cat,
                sub_intent=f"{cat_str}_sub_{i}",
                utterances=[
                    f"{cat_str} 範例語句 {i} 第一句",
                    f"{cat_str} 範例語句 {i} 第二句",
                    f"{cat_str} 範例語句 {i} 第三句",
                    f"{cat_str} 範例語句 {i} 第四句",
                    f"{cat_str} 範例語句 {i} 第五句",
                ],
                workflow_type=WorkflowType.SIMPLE,
                risk_level=RiskLevel.MEDIUM,
            )
        )

    return routes


@pytest.fixture
def performance_router(
    large_pattern_rules: Dict[str, Any],
    semantic_routes: List[SemanticRoute],
) -> BusinessIntentRouter:
    """Router configured for performance testing."""
    return BusinessIntentRouter(
        pattern_matcher=PatternMatcher(rules_dict=large_pattern_rules),
        semantic_router=MockSemanticRouter(routes=semantic_routes),
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
# Pattern Layer Performance Tests
# =============================================================================

class TestPatternLayerPerformance:
    """Performance tests for Pattern Matcher (Layer 1)."""

    # Target: P95 < 10ms
    PATTERN_P95_TARGET = 10.0

    @pytest.mark.asyncio
    async def test_pattern_layer_p95_latency(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test Pattern Layer P95 latency is under 10ms."""
        # Test inputs that will match pattern rules
        test_inputs = [
            "ETL 今天跑失敗了",
            "申請新帳號給張三",
            "ETL 錯誤需要處理",
            "建立新帳號",
            "資料同步出現問題",
        ] * 20  # 100 iterations

        latencies = []

        for user_input in test_inputs:
            start = time.perf_counter()
            decision = await performance_router.route(user_input)
            latency_ms = (time.perf_counter() - start) * 1000

            # Only count pattern layer matches
            if decision.routing_layer == "pattern":
                latencies.append(latency_ms)

        if latencies:
            p95 = calculate_percentile(latencies, 95)
            print(f"\n{format_latency_report(latencies, 'Pattern Layer')}")
            print(f"  P95 Target: {self.PATTERN_P95_TARGET}ms")

            assert p95 < self.PATTERN_P95_TARGET, (
                f"Pattern Layer P95 ({p95:.2f}ms) exceeds target "
                f"({self.PATTERN_P95_TARGET}ms)"
            )

    @pytest.mark.asyncio
    async def test_pattern_matching_scales_with_rules(
        self,
        large_pattern_rules: Dict[str, Any],
    ):
        """Test pattern matching performance scales with rule count."""
        # Test with increasing rule counts
        rule_counts = [10, 50, 100, 150]
        results = []

        for count in rule_counts:
            # Create subset of rules
            subset_rules = {"rules": large_pattern_rules["rules"][:count]}
            router = BusinessIntentRouter(
                pattern_matcher=PatternMatcher(rules_dict=subset_rules),
                semantic_router=MockSemanticRouter(routes=[]),
                llm_classifier=MockLLMClassifier(),
                config=RouterConfig(enable_llm_fallback=False),
            )

            # Measure latency
            latencies = []
            for _ in range(50):
                start = time.perf_counter()
                await router.route("ETL 今天跑失敗了")
                latencies.append((time.perf_counter() - start) * 1000)

            avg_latency = statistics.mean(latencies)
            results.append((count, avg_latency))

        print("\nPattern Matching Scalability:")
        for count, latency in results:
            print(f"  {count} rules: {latency:.2f}ms avg")

        # Performance should not degrade significantly
        # Allow 10x latency increase for 15x rule increase (still sub-millisecond)
        if len(results) >= 2:
            first_latency = results[0][1]
            last_latency = results[-1][1]
            # As long as absolute latency is still under 5ms, acceptable
            assert last_latency < 5.0 or last_latency < first_latency * 10, (
                f"Pattern matching degraded too much: "
                f"{first_latency:.2f}ms -> {last_latency:.2f}ms"
            )


# =============================================================================
# Semantic Layer Performance Tests
# =============================================================================

class TestSemanticLayerPerformance:
    """Performance tests for Semantic Router (Layer 2)."""

    # Target: P95 < 100ms (using mock)
    SEMANTIC_P95_TARGET = 100.0

    @pytest.mark.asyncio
    async def test_semantic_layer_p95_latency(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test Semantic Layer P95 latency is under 100ms (mock)."""
        # Inputs that won't match patterns but will go to semantic
        test_inputs = [
            "網路連線有點問題",
            "VPN 好像連不上",
            "檔案同步很慢",
            "系統反應遲緩",
            "伺服器負載高",
        ] * 20

        latencies = []

        for user_input in test_inputs:
            start = time.perf_counter()
            decision = await performance_router.route(user_input)
            latency_ms = (time.perf_counter() - start) * 1000

            if decision.routing_layer in ["semantic", "llm"]:
                latencies.append(latency_ms)

        if latencies:
            p95 = calculate_percentile(latencies, 95)
            print(f"\n{format_latency_report(latencies, 'Semantic Layer')}")
            print(f"  P95 Target: {self.SEMANTIC_P95_TARGET}ms")

            assert p95 < self.SEMANTIC_P95_TARGET, (
                f"Semantic Layer P95 ({p95:.2f}ms) exceeds target "
                f"({self.SEMANTIC_P95_TARGET}ms)"
            )


# =============================================================================
# LLM Layer Performance Tests
# =============================================================================

class TestLLMLayerPerformance:
    """Performance tests for LLM Classifier (Layer 3)."""

    # Target: P95 < 2000ms (using mock, real LLM would be slower)
    LLM_P95_TARGET = 2000.0
    MOCK_LLM_P95_TARGET = 100.0  # Mock should be fast

    @pytest.mark.asyncio
    async def test_llm_layer_p95_latency_mock(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test LLM Layer P95 latency (mock) is under 100ms."""
        # Ambiguous inputs that will go to LLM
        test_inputs = [
            "有些問題需要處理",
            "這個東西好像不太對",
            "想要做一些調整",
            "請幫我看看",
            "有個事情要問",
        ] * 20

        latencies = []

        for user_input in test_inputs:
            start = time.perf_counter()
            decision = await performance_router.route(user_input)
            latency_ms = (time.perf_counter() - start) * 1000

            if decision.routing_layer == "llm":
                latencies.append(latency_ms)

        if latencies:
            p95 = calculate_percentile(latencies, 95)
            print(f"\n{format_latency_report(latencies, 'LLM Layer (Mock)')}")
            print(f"  P95 Target: {self.MOCK_LLM_P95_TARGET}ms")

            assert p95 < self.MOCK_LLM_P95_TARGET, (
                f"LLM Layer (Mock) P95 ({p95:.2f}ms) exceeds target "
                f"({self.MOCK_LLM_P95_TARGET}ms)"
            )


# =============================================================================
# Overall Performance Tests
# =============================================================================

class TestOverallPerformance:
    """Overall routing performance tests."""

    # Target: Overall P95 (no LLM) < 500ms
    OVERALL_P95_TARGET = 500.0
    OVERALL_P95_NO_LLM_TARGET = 100.0  # With mock

    @pytest.mark.asyncio
    async def test_overall_p95_no_llm(
        self,
        large_pattern_rules: Dict[str, Any],
        semantic_routes: List[SemanticRoute],
    ):
        """Test overall P95 latency without LLM is under target."""
        router = BusinessIntentRouter(
            pattern_matcher=PatternMatcher(rules_dict=large_pattern_rules),
            semantic_router=MockSemanticRouter(routes=semantic_routes),
            llm_classifier=MockLLMClassifier(),
            config=RouterConfig(enable_llm_fallback=False),  # Disable LLM
        )

        # Mixed inputs
        test_inputs = [
            "ETL 今天跑失敗了",
            "申請新帳號",
            "網路連線問題",
            "查詢系統狀態",
            "部署版本更新",
            "這是個模糊的問題",
        ] * 20

        latencies = []

        for user_input in test_inputs:
            start = time.perf_counter()
            await router.route(user_input)
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = calculate_percentile(latencies, 95)
        print(f"\n{format_latency_report(latencies, 'Overall (No LLM)')}")
        print(f"  P95 Target: {self.OVERALL_P95_NO_LLM_TARGET}ms")

        assert p95 < self.OVERALL_P95_NO_LLM_TARGET, (
            f"Overall P95 (no LLM) ({p95:.2f}ms) exceeds target "
            f"({self.OVERALL_P95_NO_LLM_TARGET}ms)"
        )

    @pytest.mark.asyncio
    async def test_throughput(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test routing throughput (requests per second)."""
        test_inputs = [
            "ETL 失敗了",
            "申請帳號",
            "系統故障",
            "查詢進度",
        ] * 50

        start = time.perf_counter()
        tasks = [performance_router.route(inp) for inp in test_inputs]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

        requests_per_second = len(test_inputs) / total_time
        print(f"\nThroughput: {requests_per_second:.1f} requests/second")
        print(f"Total requests: {len(test_inputs)}")
        print(f"Total time: {total_time:.2f}s")

        # Should handle at least 100 requests/second with mock
        assert requests_per_second > 100, (
            f"Throughput ({requests_per_second:.1f} req/s) below target (100 req/s)"
        )


# =============================================================================
# Completeness Checker Performance Tests
# =============================================================================

class TestCompletenessPerformance:
    """Performance tests for completeness checking."""

    COMPLETENESS_P95_TARGET = 5.0  # 5ms target

    @pytest.mark.asyncio
    async def test_completeness_check_performance(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test completeness checking doesn't add significant latency."""
        # Create router without completeness
        router_no_check = BusinessIntentRouter(
            pattern_matcher=performance_router.pattern_matcher,
            semantic_router=performance_router.semantic_router,
            llm_classifier=performance_router.llm_classifier,
            config=RouterConfig(enable_completeness=False),
        )

        test_input = "ETL 今天跑失敗了，很緊急"

        # Measure with completeness
        latencies_with = []
        for _ in range(100):
            start = time.perf_counter()
            await performance_router.route(test_input)
            latencies_with.append((time.perf_counter() - start) * 1000)

        # Measure without completeness
        latencies_without = []
        for _ in range(100):
            start = time.perf_counter()
            await router_no_check.route(test_input)
            latencies_without.append((time.perf_counter() - start) * 1000)

        avg_with = statistics.mean(latencies_with)
        avg_without = statistics.mean(latencies_without)
        overhead = avg_with - avg_without

        print(f"\nCompleteness Check Overhead:")
        print(f"  With: {avg_with:.2f}ms avg")
        print(f"  Without: {avg_without:.2f}ms avg")
        print(f"  Overhead: {overhead:.2f}ms")
        print(f"  Target: {self.COMPLETENESS_P95_TARGET}ms")

        assert overhead < self.COMPLETENESS_P95_TARGET, (
            f"Completeness overhead ({overhead:.2f}ms) exceeds target "
            f"({self.COMPLETENESS_P95_TARGET}ms)"
        )


# =============================================================================
# Memory Usage Tests
# =============================================================================

class TestMemoryUsage:
    """Memory usage tests for the router."""

    @pytest.mark.asyncio
    async def test_metrics_memory_bounded(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test that metrics don't grow unbounded."""
        # Route many requests
        for i in range(1500):
            await performance_router.route(f"測試訊息 {i}")

        metrics = performance_router.get_metrics()

        # Latencies should be bounded to last 1000
        assert len(performance_router._metrics.latencies) <= 1000

        print(f"\nMetrics after 1500 requests:")
        print(f"  Total requests: {metrics['total_requests']}")
        print(f"  Latency samples: {len(performance_router._metrics.latencies)}")

    @pytest.mark.asyncio
    async def test_router_reset(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test metrics can be reset."""
        # Route some requests
        for _ in range(100):
            await performance_router.route("測試")

        # Reset
        performance_router.reset_metrics()

        metrics = performance_router.get_metrics()
        assert metrics["total_requests"] == 0
        assert len(performance_router._metrics.latencies) == 0


# =============================================================================
# Stress Tests
# =============================================================================

class TestStressConditions:
    """Stress tests for the router."""

    @pytest.mark.asyncio
    async def test_burst_load(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test handling burst load."""
        # Simulate burst of 100 concurrent requests
        test_inputs = [f"緊急問題 {i}" for i in range(100)]

        start = time.perf_counter()
        tasks = [performance_router.route(inp) for inp in test_inputs]
        results = await asyncio.gather(*tasks)
        burst_time = (time.perf_counter() - start) * 1000

        print(f"\nBurst Load Test (100 concurrent):")
        print(f"  Total time: {burst_time:.2f}ms")
        print(f"  Avg per request: {burst_time / 100:.2f}ms")

        # All requests should complete
        assert len(results) == 100

        # Burst should complete in reasonable time (< 5 seconds)
        assert burst_time < 5000

    @pytest.mark.asyncio
    async def test_sustained_load(
        self,
        performance_router: BusinessIntentRouter,
    ):
        """Test handling sustained load over time."""
        duration_seconds = 2  # Run for 2 seconds
        request_count = 0
        latencies = []

        start = time.perf_counter()
        while (time.perf_counter() - start) < duration_seconds:
            req_start = time.perf_counter()
            await performance_router.route(f"持續測試 {request_count}")
            latencies.append((time.perf_counter() - req_start) * 1000)
            request_count += 1

        avg_latency = statistics.mean(latencies)
        requests_per_second = request_count / duration_seconds

        print(f"\nSustained Load Test ({duration_seconds}s):")
        print(f"  Total requests: {request_count}")
        print(f"  Requests/second: {requests_per_second:.1f}")
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  P95 latency: {calculate_percentile(latencies, 95):.2f}ms")

        # Should maintain reasonable throughput
        assert requests_per_second > 50
