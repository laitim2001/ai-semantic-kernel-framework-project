"""
Sprint 127 Performance Benchmark Tests.

Story 127-4: Measures response times for key operations against target SLAs:
    - n8n workflow trigger: < 2s
    - ADF pipeline trigger: < 3s
    - Incident classification (Pattern): < 1s
    - Incident classification (LLM): < 5s
    - Full incident processing (Auto): < 30s
    - Full incident processing (Approval): < 5min

All tests use mocked external dependencies to isolate timing of internal
logic and serialization overhead. External network latency is NOT measured.

Sprint 127 (Phase 34)
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# n8n imports
# ---------------------------------------------------------------------------
from src.integrations.mcp.servers.n8n.client import N8nApiClient, N8nConfig
from src.integrations.n8n.orchestrator import (
    N8nOrchestrator,
    OrchestrationRequest,
    OrchestrationStatus,
    ReasoningResult,
)
from src.integrations.n8n.monitor import MonitorConfig

# ---------------------------------------------------------------------------
# ADF imports
# ---------------------------------------------------------------------------
from src.integrations.mcp.servers.adf.client import AdfApiClient, AdfConfig

# ---------------------------------------------------------------------------
# Incident imports
# ---------------------------------------------------------------------------
from src.integrations.orchestration.input.incident_handler import IncidentHandler
from src.integrations.incident.analyzer import IncidentAnalyzer
from src.integrations.incident.executor import IncidentExecutor
from src.integrations.incident.recommender import ActionRecommender
from src.integrations.incident.types import (
    IncidentAnalysis,
    IncidentCategory,
    IncidentContext,
    IncidentSeverity,
    ExecutionStatus,
    RemediationAction,
    RemediationActionType,
    RemediationRisk,
)
from src.integrations.rootcause.types import (
    AnalysisStatus,
    RootCauseAnalysis,
    RootCauseHypothesis,
)


# =============================================================================
# Shared Factories
# =============================================================================


def _make_inc_payload(
    number: str = "INC0080001",
    priority: str = "3",
    category: str = "",
    short_description: str = "Test",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Build a ServiceNow INC webhook payload for performance tests.

    Args:
        number: INC number
        priority: ServiceNow priority code
        category: Incident category
        short_description: Brief description
        **kwargs: Additional fields merged into payload

    Returns:
        Dict matching ServiceNowINCEvent schema
    """
    return {
        "sys_id": f"perf_{number.lower()}",
        "number": number,
        "state": "1",
        "impact": "2",
        "urgency": "2",
        "priority": priority,
        "category": category,
        "subcategory": "",
        "short_description": short_description,
        "description": "Performance test",
        "cmdb_ci": "test-server",
        "business_service": "Perf Service",
        "caller_id": "perf.user",
        "assignment_group": "Perf Group",
        "sys_created_on": "2026-02-25T12:00:00Z",
        **kwargs,
    }


def _make_mock_rootcause_analyzer(
    root_cause: str = "Test cause",
    confidence: float = 0.7,
) -> MagicMock:
    """Build a mocked RootCauseAnalyzer returning a completed RootCauseAnalysis.

    Args:
        root_cause: Root cause description
        confidence: Confidence score (0.0-1.0)

    Returns:
        MagicMock with async analyze_root_cause returning RootCauseAnalysis
    """
    rca_result = RootCauseAnalysis(
        analysis_id="rca_perf",
        event_id="evt_perf_001",
        root_cause=root_cause,
        confidence=confidence,
        status=AnalysisStatus.COMPLETED,
        started_at=datetime(2026, 2, 25, 12, 0),
        completed_at=datetime(2026, 2, 25, 12, 5),
        contributing_factors=["perf_factor"],
        hypotheses=[
            RootCauseHypothesis(
                hypothesis_id="hyp_perf",
                description=root_cause,
                confidence=confidence,
                evidence=[],
                supporting_events=["perf evidence"],
            ),
        ],
        similar_historical_cases=[],
        recommendations=[],
    )
    analyzer = MagicMock()
    analyzer.analyze_root_cause = AsyncMock(return_value=rca_result)
    return analyzer


def _make_incident_context(
    incident_number: str = "INC0080001",
    category: IncidentCategory = IncidentCategory.APPLICATION,
    severity: IncidentSeverity = IncidentSeverity.P3,
) -> IncidentContext:
    """Build an IncidentContext for performance tests.

    Args:
        incident_number: INC number
        category: Incident category
        severity: Incident severity

    Returns:
        IncidentContext instance
    """
    return IncidentContext(
        incident_number=incident_number,
        severity=severity,
        category=category,
        short_description="Performance test incident",
        description="Application error for perf bench",
        affected_components=["test-server"],
        business_service="Perf Service",
        cmdb_ci="test-server",
        assignment_group="Perf Group",
        caller_id="perf.user",
    )


def _make_n8n_config() -> N8nConfig:
    """Build N8nConfig for performance tests."""
    return N8nConfig(
        base_url="http://localhost:5678",
        api_key="test-perf-key",
        timeout=30,
        max_retries=1,
    )


def _make_adf_config() -> AdfConfig:
    """Build AdfConfig for performance tests."""
    return AdfConfig(
        subscription_id="perf-sub-id",
        resource_group="perf-rg",
        factory_name="perf-factory",
        tenant_id="perf-tenant",
        client_id="perf-client",
        client_secret="perf-secret",
        timeout=30,
        max_retries=1,
    )


# =============================================================================
# n8n Performance Benchmarks
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.performance
class TestN8nPerformanceBenchmarks:
    """Performance benchmarks for n8n workflow operations.

    Targets:
        - Single workflow trigger: < 2s
        - Workflow list: < 1s
        - Orchestration reasoning: < 2s
        - 10 concurrent triggers: < 5s
    """

    async def test_n8n_workflow_trigger_under_2s(self) -> None:
        """Verify that a single n8n workflow trigger completes in under 2 seconds.

        Mocks the underlying HTTP call so only internal serialization and
        client logic overhead is measured.
        """
        config = _make_n8n_config()
        client = N8nApiClient(config)
        client._client = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"executionId": "exec-perf-001", "status": "success"},
        }
        client._client.request = AsyncMock(return_value=mock_response)

        target = 2.0
        start = time.perf_counter()
        result = await client.execute_workflow(
            workflow_id="wf-perf-001",
            data={"incident": "INC0080001", "action": "restart_service"},
        )
        elapsed = time.perf_counter() - start

        assert result is not None
        assert elapsed < target, (
            f"n8n workflow trigger took {elapsed:.3f}s, target: {target}s"
        )

    async def test_n8n_workflow_list_under_1s(self) -> None:
        """Verify that listing n8n workflows completes in under 1 second."""
        config = _make_n8n_config()
        client = N8nApiClient(config)
        client._client = MagicMock()

        workflows_response = {
            "data": [
                {"id": f"wf-{i}", "name": f"Workflow {i}", "active": True}
                for i in range(50)
            ],
            "nextCursor": None,
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = workflows_response
        client._client.request = AsyncMock(return_value=mock_response)

        target = 1.0
        start = time.perf_counter()
        result = await client.list_workflows(limit=50)
        elapsed = time.perf_counter() - start

        assert len(result["data"]) == 50
        assert elapsed < target, (
            f"n8n workflow list took {elapsed:.3f}s, target: {target}s"
        )

    async def test_n8n_orchestration_reasoning_under_2s(self) -> None:
        """Verify that the IPA reasoning phase of orchestration completes in under 2 seconds.

        Uses the default keyword-based reasoning function (no LLM call).
        The n8n client and monitor are mocked to isolate reasoning time.
        """
        config = _make_n8n_config()

        async def fast_reasoning(user_input: str, context: Dict[str, Any]) -> ReasoningResult:
            """Simulated reasoning function that returns immediately."""
            return ReasoningResult(
                intent="INCIDENT",
                sub_intent="system_failure",
                confidence=0.85,
                recommended_workflow="wf-incident-001",
                workflow_input={"original_input": user_input},
                risk_level="medium",
                requires_approval=False,
            )

        orchestrator = N8nOrchestrator(config, reasoning_fn=fast_reasoning)

        # Mock the client execute_workflow to return immediately
        orchestrator._client.execute_workflow = AsyncMock(return_value={
            "data": {"executionId": "exec-perf-002", "status": "success", "data": {}},
        })

        request = OrchestrationRequest(
            user_input="Server is down and unresponsive",
            context={"environment": "production"},
            workflow_id="wf-incident-001",
        )

        target = 2.0
        start = time.perf_counter()
        result = await orchestrator.orchestrate(request)
        elapsed = time.perf_counter() - start

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.reasoning is not None
        assert result.reasoning.intent == "INCIDENT"
        assert elapsed < target, (
            f"n8n orchestration reasoning took {elapsed:.3f}s, target: {target}s"
        )

    async def test_n8n_10_concurrent_triggers_under_5s(self) -> None:
        """Verify that 10 concurrent workflow triggers complete in under 5 seconds total.

        All mocked to return immediately; measures coroutine scheduling overhead.
        """
        config = _make_n8n_config()
        client = N8nApiClient(config)
        client._client = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"executionId": "exec-concurrent", "status": "success"},
        }
        client._client.request = AsyncMock(return_value=mock_response)

        target = 5.0

        async def trigger_one(idx: int) -> Dict[str, Any]:
            """Trigger a single workflow execution."""
            return await client.execute_workflow(
                workflow_id=f"wf-concurrent-{idx}",
                data={"index": idx},
            )

        start = time.perf_counter()
        results = await asyncio.gather(*[trigger_one(i) for i in range(10)])
        elapsed = time.perf_counter() - start

        assert len(results) == 10
        for r in results:
            assert "data" in r
        assert elapsed < target, (
            f"10 concurrent n8n triggers took {elapsed:.3f}s, target: {target}s"
        )


# =============================================================================
# ADF Performance Benchmarks
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.performance
class TestAdfPerformanceBenchmarks:
    """Performance benchmarks for Azure Data Factory operations.

    Targets:
        - Pipeline trigger (including token acquisition): < 3s
        - Pipeline list: < 2s
        - Pipeline status check: < 1s
    """

    async def test_adf_pipeline_trigger_under_3s(self) -> None:
        """Verify that ADF pipeline trigger (token + run) completes in under 3 seconds.

        Mocks both the OAuth token endpoint and the pipeline createRun endpoint
        to measure internal serialization and auth-flow overhead only.
        """
        config = _make_adf_config()
        client = AdfApiClient(config)
        client._client = MagicMock()

        # Mock token response
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "perf-token-abc",
            "expires_in": 3600,
        }

        # Mock pipeline run response
        run_response = MagicMock()
        run_response.status_code = 200
        run_response.json.return_value = {"runId": "run-perf-001"}

        call_count = 0

        async def mock_request(*args: Any, **kwargs: Any) -> MagicMock:
            """Return token response first, then pipeline response."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return token_response
            return run_response

        async def mock_post(*args: Any, **kwargs: Any) -> MagicMock:
            """Mock post for token acquisition."""
            return token_response

        client._client.request = mock_request  # type: ignore[assignment]
        client._client.post = mock_post  # type: ignore[assignment]
        # Force token re-acquisition
        client._access_token = None
        client._token_expiry = 0.0

        target = 3.0
        start = time.perf_counter()
        result = await client.run_pipeline(
            pipeline_name="perf-pipeline",
            parameters={"env": "test"},
        )
        elapsed = time.perf_counter() - start

        assert result is not None
        assert elapsed < target, (
            f"ADF pipeline trigger took {elapsed:.3f}s, target: {target}s"
        )

    async def test_adf_pipeline_list_under_2s(self) -> None:
        """Verify that listing ADF pipelines completes in under 2 seconds."""
        config = _make_adf_config()
        client = AdfApiClient(config)
        client._client = MagicMock()

        # Pre-set token so _ensure_token skips network call
        client._access_token = "perf-token-cached"
        client._token_expiry = time.time() + 3600

        pipelines_response = {
            "value": [
                {"name": f"pipeline-{i}", "type": "Microsoft.DataFactory/factories/pipelines"}
                for i in range(30)
            ],
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = pipelines_response
        client._client.request = AsyncMock(return_value=mock_response)

        target = 2.0
        start = time.perf_counter()
        result = await client.list_pipelines()
        elapsed = time.perf_counter() - start

        assert len(result["value"]) == 30
        assert elapsed < target, (
            f"ADF pipeline list took {elapsed:.3f}s, target: {target}s"
        )

    async def test_adf_pipeline_status_check_under_1s(self) -> None:
        """Verify that checking a pipeline run status completes in under 1 second."""
        config = _make_adf_config()
        client = AdfApiClient(config)
        client._client = MagicMock()

        # Pre-set token
        client._access_token = "perf-token-cached"
        client._token_expiry = time.time() + 3600

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "runId": "run-perf-001",
            "status": "Succeeded",
            "pipelineName": "perf-pipeline",
            "runStart": "2026-02-25T12:00:00Z",
            "runEnd": "2026-02-25T12:05:00Z",
        }
        client._client.request = AsyncMock(return_value=mock_response)

        target = 1.0
        start = time.perf_counter()
        result = await client.get_pipeline_run(run_id="run-perf-001")
        elapsed = time.perf_counter() - start

        assert result["status"] == "Succeeded"
        assert elapsed < target, (
            f"ADF pipeline status check took {elapsed:.3f}s, target: {target}s"
        )


# =============================================================================
# Incident Classification Benchmarks
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.performance
class TestIncidentClassificationBenchmarks:
    """Performance benchmarks for incident classification operations.

    Targets:
        - Single pattern classification: < 1s
        - 10 sequential classifications: < 3s
        - LLM classification: < 5s
        - can_handle check: < 10ms
    """

    async def test_pattern_classification_under_1s(self) -> None:
        """Verify that pattern-based incident classification completes in under 1 second.

        Uses IncidentHandler.process() with a payload that matches regex patterns.
        """
        handler = IncidentHandler()
        payload = _make_inc_payload(
            number="INC0080001",
            priority="2",
            category="network",
            short_description="Switch port down on core-sw-01",
        )

        target = 1.0
        start = time.perf_counter()
        routing_request = await handler.process(payload)
        elapsed = time.perf_counter() - start

        assert routing_request.intent_hint == "incident"
        assert routing_request.context["subcategory"] == "network"
        assert elapsed < target, (
            f"Pattern classification took {elapsed:.3f}s, target: {target}s"
        )

    async def test_pattern_classification_10_incidents_under_3s(self) -> None:
        """Verify that 10 sequential incident classifications complete in under 3 seconds."""
        handler = IncidentHandler()
        categories = [
            ("network", "Switch failure on edge router"),
            ("hardware", "Server memory ECC errors"),
            ("software", "Application 500 error on prod"),
            ("database", "SQL deadlock in transaction processing"),
            ("security", "Unauthorized access attempt detected"),
            ("storage", "Disk full on file server NAS-01"),
            ("performance", "Slow response times on API gateway"),
            ("login", "User account locked after failed attempts"),
            ("network", "DNS resolution failure for internal domains"),
            ("hardware", "CPU high on web-server-05"),
        ]

        payloads = [
            _make_inc_payload(
                number=f"INC008{i:04d}",
                category=cat,
                short_description=desc,
            )
            for i, (cat, desc) in enumerate(categories)
        ]

        target = 3.0
        start = time.perf_counter()
        results = []
        for payload in payloads:
            result = await handler.process(payload)
            results.append(result)
        elapsed = time.perf_counter() - start

        assert len(results) == 10
        for r in results:
            assert r.intent_hint == "incident"
        assert elapsed < target, (
            f"10 sequential classifications took {elapsed:.3f}s, target: {target}s"
        )

    async def test_llm_classification_under_5s(self) -> None:
        """Verify that LLM-enhanced incident analysis completes in under 5 seconds.

        Uses IncidentAnalyzer with mocked CorrelationAnalyzer and RootCauseAnalyzer.
        A small asyncio.sleep(0.1) simulates LLM network round-trip latency.
        """
        mock_correlation = MagicMock()
        mock_correlation.find_correlations = AsyncMock(return_value=[])

        mock_rca = _make_mock_rootcause_analyzer(
            root_cause="Application memory leak", confidence=0.75
        )

        # Simulate LLM with a small delay
        async def mock_llm_generate(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            """Simulate LLM response with network delay."""
            await asyncio.sleep(0.1)
            return {
                "root_cause_summary": "Memory leak in connection pool manager",
                "root_cause_confidence": 0.82,
                "contributing_factors": ["Connection pool exhaustion", "GC pressure"],
                "analysis_notes": "LLM-enhanced analysis",
                "suggested_category_correction": None,
            }

        mock_llm = MagicMock()
        mock_llm.generate_structured = mock_llm_generate

        analyzer = IncidentAnalyzer(
            correlation_analyzer=mock_correlation,
            rootcause_analyzer=mock_rca,
            llm_service=mock_llm,
        )

        context = _make_incident_context(
            incident_number="INC0080010",
            category=IncidentCategory.APPLICATION,
            severity=IncidentSeverity.P2,
        )

        target = 5.0
        start = time.perf_counter()
        analysis = await analyzer.analyze(context)
        elapsed = time.perf_counter() - start

        assert analysis.incident_number == "INC0080010"
        assert analysis.llm_enhanced is True
        assert elapsed < target, (
            f"LLM classification took {elapsed:.3f}s, target: {target}s"
        )

    async def test_handler_can_handle_check_under_10ms(self) -> None:
        """Verify that IncidentHandler.can_handle() completes in under 10 milliseconds.

        This is a synchronous check with no I/O, should be near-instantaneous.
        """
        handler = IncidentHandler()
        payload = _make_inc_payload(number="INC0080099")

        target_ms = 10.0
        start = time.perf_counter()
        result = handler.can_handle(payload)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result is True
        assert elapsed_ms < target_ms, (
            f"can_handle check took {elapsed_ms:.3f}ms, target: {target_ms}ms"
        )


# =============================================================================
# Full Incident Processing Benchmarks
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.performance
class TestFullIncidentProcessingBenchmarks:
    """Performance benchmarks for the full incident processing pipeline.

    Targets:
        - Auto-remediation pipeline: < 30s
        - HITL approval request: < 5s
        - Multiple action execution: < 30s
        - 5 concurrent incidents: < 60s
    """

    async def test_auto_remediation_under_30s(self) -> None:
        """Verify that a full auto-remediation pipeline completes in under 30 seconds.

        Pipeline: handler.process() -> analyzer.analyze() -> recommender.recommend()
                  -> executor.execute() with AUTO-risk action.
        All external calls are mocked.
        """
        # Step 1: Handler
        handler = IncidentHandler()
        payload = _make_inc_payload(
            number="INC0080020",
            priority="3",
            category="storage",
            short_description="Disk full on app-server-03",
        )

        # Step 2: Analyzer with mocked dependencies
        mock_correlation = MagicMock()
        mock_correlation.find_correlations = AsyncMock(return_value=[])
        mock_rca = _make_mock_rootcause_analyzer(
            root_cause="Disk space exhausted by log accumulation", confidence=0.85
        )
        analyzer = IncidentAnalyzer(
            correlation_analyzer=mock_correlation,
            rootcause_analyzer=mock_rca,
        )

        # Step 3: Recommender (rule-based, no LLM)
        recommender = ActionRecommender()

        # Step 4: Executor with mocked dependencies
        mock_hitl = MagicMock()
        mock_hitl.request_approval = AsyncMock()
        mock_risk_assessor = MagicMock()
        executor = IncidentExecutor(
            hitl_controller=mock_hitl,
            risk_assessor=mock_risk_assessor,
        )

        target = 30.0
        start = time.perf_counter()

        # Full pipeline
        routing_request = await handler.process(payload)

        context = _make_incident_context(
            incident_number="INC0080020",
            category=IncidentCategory.STORAGE,
            severity=IncidentSeverity.P3,
        )

        analysis = await analyzer.analyze(context)
        actions = await recommender.recommend(analysis, context)
        results = await executor.execute(analysis, context, actions)

        elapsed = time.perf_counter() - start

        assert routing_request.intent_hint == "incident"
        assert analysis.incident_number == "INC0080020"
        assert len(actions) > 0
        assert len(results) > 0
        assert elapsed < target, (
            f"Auto-remediation pipeline took {elapsed:.3f}s, target: {target}s"
        )

    async def test_hitl_request_under_5s(self) -> None:
        """Verify that the pipeline up to HITL approval request completes in under 5 seconds.

        Pipeline runs up through executor creating the HITL approval request.
        Does NOT wait for actual human approval.
        """
        handler = IncidentHandler()
        payload = _make_inc_payload(
            number="INC0080021",
            priority="1",
            category="security",
            short_description="Unauthorized firewall rule change detected",
        )

        mock_correlation = MagicMock()
        mock_correlation.find_correlations = AsyncMock(return_value=[])
        mock_rca = _make_mock_rootcause_analyzer(
            root_cause="Unauthorized firewall modification", confidence=0.9
        )
        analyzer = IncidentAnalyzer(
            correlation_analyzer=mock_correlation,
            rootcause_analyzer=mock_rca,
        )

        recommender = ActionRecommender()

        # Mock HITL controller to return approval request immediately
        mock_approval_request = MagicMock()
        mock_approval_request.request_id = "approval-perf-001"
        mock_hitl = MagicMock()
        mock_hitl.request_approval = AsyncMock(return_value=mock_approval_request)
        mock_risk_assessor = MagicMock()

        executor = IncidentExecutor(
            hitl_controller=mock_hitl,
            risk_assessor=mock_risk_assessor,
        )

        target = 5.0
        start = time.perf_counter()

        routing_request = await handler.process(payload)

        context = _make_incident_context(
            incident_number="INC0080021",
            category=IncidentCategory.SECURITY,
            severity=IncidentSeverity.P1,
        )

        analysis = await analyzer.analyze(context)
        actions = await recommender.recommend(analysis, context)
        results = await executor.execute(analysis, context, actions)

        elapsed = time.perf_counter() - start

        # Security actions should go through HITL
        has_awaiting = any(
            r.status == ExecutionStatus.AWAITING_APPROVAL for r in results
        )
        assert has_awaiting, "Expected at least one action to require HITL approval"
        assert elapsed < target, (
            f"HITL request pipeline took {elapsed:.3f}s, target: {target}s"
        )

    async def test_multiple_action_execution_under_30s(self) -> None:
        """Verify that executing 3 remediation actions sequentially completes in under 30 seconds.

        Uses IncidentExecutor with AUTO-risk actions that simulate execution
        via the fallback path (no MCP executor configured).
        """
        mock_hitl = MagicMock()
        mock_hitl.request_approval = AsyncMock()
        mock_risk_assessor = MagicMock()
        executor = IncidentExecutor(
            hitl_controller=mock_hitl,
            risk_assessor=mock_risk_assessor,
        )

        context = _make_incident_context(
            incident_number="INC0080022",
            category=IncidentCategory.PERFORMANCE,
            severity=IncidentSeverity.P3,
        )

        analysis = IncidentAnalysis(
            analysis_id="ana_perf_multi",
            incident_number="INC0080022",
            root_cause_summary="Cache corruption causing slow responses",
            root_cause_confidence=0.7,
        )

        actions = [
            RemediationAction(
                action_type=RemediationActionType.CLEAR_CACHE,
                title=f"Clear cache layer {i + 1}",
                description=f"Clear cache layer {i + 1} to resolve stale data",
                confidence=0.75,
                risk=RemediationRisk.AUTO,
                mcp_tool="",
                estimated_duration_seconds=15,
            )
            for i in range(3)
        ]

        target = 30.0
        start = time.perf_counter()
        results = await executor.execute(analysis, context, actions)
        elapsed = time.perf_counter() - start

        assert len(results) >= 1
        assert elapsed < target, (
            f"Multiple action execution took {elapsed:.3f}s, target: {target}s"
        )

    async def test_concurrent_incident_processing_under_60s(self) -> None:
        """Verify that processing 5 incidents concurrently completes in under 60 seconds.

        Each incident goes through the full classification pipeline with
        mocked external dependencies.
        """
        handler = IncidentHandler()
        mock_correlation = MagicMock()
        mock_correlation.find_correlations = AsyncMock(return_value=[])
        mock_rca = _make_mock_rootcause_analyzer()

        categories_data = [
            ("INC0080030", "network", "Router down in building A"),
            ("INC0080031", "software", "Application crash on web-01"),
            ("INC0080032", "database", "SQL deadlock on prod-db"),
            ("INC0080033", "storage", "Disk 95% full on file-srv"),
            ("INC0080034", "performance", "Slow API response times"),
        ]

        async def process_single_incident(
            number: str,
            category: str,
            description: str,
        ) -> Dict[str, Any]:
            """Process a single incident through the full pipeline."""
            payload = _make_inc_payload(
                number=number,
                category=category,
                short_description=description,
            )
            routing_request = await handler.process(payload)

            local_analyzer = IncidentAnalyzer(
                correlation_analyzer=mock_correlation,
                rootcause_analyzer=mock_rca,
            )
            context = _make_incident_context(
                incident_number=number,
                category=IncidentCategory.from_string(category),
            )
            analysis = await local_analyzer.analyze(context)

            recommender = ActionRecommender()
            actions = await recommender.recommend(analysis, context)

            return {
                "number": number,
                "routing": routing_request.intent_hint,
                "analysis_id": analysis.analysis_id,
                "action_count": len(actions),
            }

        target = 60.0
        start = time.perf_counter()
        results = await asyncio.gather(*[
            process_single_incident(num, cat, desc)
            for num, cat, desc in categories_data
        ])
        elapsed = time.perf_counter() - start

        assert len(results) == 5
        for r in results:
            assert r["routing"] == "incident"
            assert r["action_count"] >= 0
        assert elapsed < target, (
            f"5 concurrent incidents took {elapsed:.3f}s, target: {target}s"
        )


# =============================================================================
# Throughput Benchmarks
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.performance
class TestThroughputBenchmarks:
    """Throughput benchmarks measuring operations per second.

    These tests establish baseline throughput for high-volume operations
    rather than enforcing strict pass/fail targets.
    """

    async def test_incident_handler_throughput(self) -> None:
        """Measure incidents/second for 100 IncidentHandler.process() calls.

        Establishes throughput baseline for the incident handler with
        pattern-based classification. Asserts at least 10 incidents/second
        as a reasonable floor.
        """
        handler = IncidentHandler()
        payloads = [
            _make_inc_payload(
                number=f"INC009{i:04d}",
                category="network" if i % 2 == 0 else "software",
                short_description=f"Throughput test incident {i}",
            )
            for i in range(100)
        ]

        start = time.perf_counter()
        for payload in payloads:
            await handler.process(payload)
        elapsed = time.perf_counter() - start

        throughput = 100.0 / elapsed if elapsed > 0 else float("inf")

        # Assert a reasonable minimum throughput
        min_throughput = 10.0
        assert throughput > min_throughput, (
            f"Handler throughput {throughput:.1f} inc/s below minimum "
            f"{min_throughput} inc/s (total time: {elapsed:.3f}s)"
        )

    async def test_recommendation_throughput(self) -> None:
        """Measure recommendations/second for 50 ActionRecommender.recommend() calls.

        Uses rule-based recommendation only (no LLM), establishing a
        throughput baseline. Asserts at least 5 recommendations/second.
        """
        recommender = ActionRecommender()
        context = _make_incident_context(
            incident_number="INC0090000",
            category=IncidentCategory.APPLICATION,
            severity=IncidentSeverity.P3,
        )
        analysis = IncidentAnalysis(
            analysis_id="ana_throughput",
            incident_number="INC0090000",
            root_cause_summary="Throughput test root cause",
            root_cause_confidence=0.7,
        )

        start = time.perf_counter()
        for _ in range(50):
            await recommender.recommend(analysis, context)
        elapsed = time.perf_counter() - start

        throughput = 50.0 / elapsed if elapsed > 0 else float("inf")

        min_throughput = 5.0
        assert throughput > min_throughput, (
            f"Recommender throughput {throughput:.1f} rec/s below minimum "
            f"{min_throughput} rec/s (total time: {elapsed:.3f}s)"
        )
