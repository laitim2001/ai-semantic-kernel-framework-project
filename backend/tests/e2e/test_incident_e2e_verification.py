"""
Extended End-to-End Verification Tests for IT Incident Processing.

Sprint 127: Story 127-2 — Incident E2E Verification (Phase 34)

Extends Sprint 126's test_incident_pipeline.py with deeper edge cases:
    - Webhook-level integration per severity (P1-P4)
    - Recommendation sorting and deduplication
    - Execution path routing (AUTO/HITL/medium configurable)
    - Chinese description classification
    - Category-specific recommendation coverage

All external I/O is mocked. No real ServiceNow/LDAP/LLM connections.
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from src.integrations.orchestration.input.incident_handler import (
    IncidentHandler,
    IncidentSubCategory,
    ServiceNowINCEvent,
)
from src.integrations.incident.analyzer import IncidentAnalyzer
from src.integrations.incident.executor import IncidentExecutor
from src.integrations.incident.recommender import ActionRecommender
from src.integrations.incident.types import (
    ExecutionResult,
    ExecutionStatus,
    IncidentAnalysis,
    IncidentCategory,
    IncidentContext,
    IncidentSeverity,
    RemediationAction,
    RemediationActionType,
    RemediationRisk,
)
from src.integrations.correlation.types import (
    Correlation,
    CorrelationType,
)
from src.integrations.rootcause.types import (
    AnalysisStatus,
    Recommendation,
    RecommendationType,
    RootCauseAnalysis,
    RootCauseHypothesis,
    HistoricalCase,
)


# ---------------------------------------------------------------------------
# Shared Mock Factories
# ---------------------------------------------------------------------------


def _make_mock_correlation_analyzer(correlations: Optional[List[Correlation]] = None) -> MagicMock:
    """Create a mocked CorrelationAnalyzer returning the given correlations."""
    analyzer = MagicMock()
    analyzer.find_correlations = AsyncMock(return_value=correlations or [])
    return analyzer


def _make_mock_rootcause_analyzer(
    root_cause: str = "Unknown cause",
    confidence: float = 0.5,
    recommendations: Optional[List[Recommendation]] = None,
) -> MagicMock:
    """Create a mocked RootCauseAnalyzer.

    Returns an analyzer whose analyze_root_cause method yields a RootCauseAnalysis
    with the supplied root cause, confidence, and recommendations.
    All required fields (event_id, started_at, completed_at) are populated.
    """
    rca_result = RootCauseAnalysis(
        analysis_id="rca_e2e_v2",
        event_id="evt_e2e_v2_001",
        root_cause=root_cause,
        confidence=confidence,
        status=AnalysisStatus.COMPLETED,
        started_at=datetime(2026, 2, 25, 10, 0),
        completed_at=datetime(2026, 2, 25, 10, 5),
        contributing_factors=["factor_1"],
        hypotheses=[
            RootCauseHypothesis(
                hypothesis_id="hyp_e2e_v2",
                description=root_cause,
                confidence=confidence,
                evidence=["e2e extended evidence"],
            ),
        ],
        similar_historical_cases=[],
        recommendations=recommendations or [],
    )
    analyzer = MagicMock()
    analyzer.analyze_root_cause = AsyncMock(return_value=rca_result)
    return analyzer


def _make_mock_hitl_controller() -> MagicMock:
    """Create a mocked HITL controller that auto-approves requests."""
    controller = MagicMock()
    approval_request = MagicMock()
    approval_request.request_id = "e2e-v2-approval-001"
    controller.request_approval = AsyncMock(return_value=approval_request)
    return controller


def _make_inc_payload(
    number: str = "INC0100001",
    priority: str = "3",
    category: str = "",
    short_description: str = "Test incident",
    description: str = "Test incident description",
    cmdb_ci: str = "test-server",
    caller_id: str = "test.user",
) -> Dict[str, Any]:
    """Create a ServiceNow INC webhook payload for testing."""
    return {
        "sys_id": f"e2e_v2_{number.lower()}",
        "number": number,
        "state": "1",
        "impact": "2",
        "urgency": "2",
        "priority": priority,
        "category": category,
        "subcategory": "",
        "short_description": short_description,
        "description": description,
        "cmdb_ci": cmdb_ci,
        "business_service": "E2E V2 Test Service",
        "caller_id": caller_id,
        "assignment_group": "E2E V2 Test Group",
        "sys_created_on": "2026-02-25T10:00:00Z",
    }


def _make_recommendation(
    title: str,
    rec_type: RecommendationType = RecommendationType.IMMEDIATE,
    priority: int = 1,
) -> Recommendation:
    """Create a RootCause Recommendation with all required fields."""
    return Recommendation(
        recommendation_id=f"rec_{title[:8].lower().replace(' ', '_')}",
        recommendation_type=rec_type,
        title=title,
        description=f"Detailed description for: {title}",
        priority=priority,
        estimated_effort="30 minutes",
        affected_components=["test-component"],
        steps=[f"Step 1 for {title}", f"Step 2 for {title}"],
    )


# ---------------------------------------------------------------------------
# E2E: Webhook Processing Per Severity
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestIncidentWebhookProcessing:
    """E2E: Process incidents at different severity levels via webhook payloads."""

    @pytest.mark.asyncio
    async def test_p1_server_crash_incident(self) -> None:
        """P1 server crash incident processes as critical risk with correct analysis."""
        payload = _make_inc_payload(
            number="INC0100001",
            priority="1",
            category="Hardware",
            short_description="Server crash on prod-app-01 — kernel panic",
            description="Critical production server crashed with kernel panic. "
                        "All services hosted on this server are offline.",
            cmdb_ci="prod-app-01",
        )

        handler = IncidentHandler()
        assert handler.can_handle(payload) is True
        routing_request = await handler.process(payload)

        assert routing_request.intent_hint == "incident"
        assert routing_request.context["risk_level"] == "critical"
        assert routing_request.context["subcategory"] == "server"

        context = IncidentContext(
            incident_number="INC0100001",
            severity=IncidentSeverity.P1,
            category=IncidentCategory.SERVER,
            short_description=payload["short_description"],
            description=payload["description"],
            affected_components=["prod-app-01"],
            cmdb_ci="prod-app-01",
        )

        analyzer = IncidentAnalyzer(
            correlation_analyzer=_make_mock_correlation_analyzer(),
            rootcause_analyzer=_make_mock_rootcause_analyzer(
                root_cause="Kernel panic due to memory corruption",
                confidence=0.85,
            ),
        )
        analysis = await analyzer.analyze(context)

        assert analysis.incident_number == "INC0100001"
        assert analysis.root_cause_confidence > 0.5

    @pytest.mark.asyncio
    async def test_p2_network_incident_with_correlations(self) -> None:
        """P2 network switch flapping incident with 3 correlated events."""
        payload = _make_inc_payload(
            number="INC0100002",
            priority="2",
            category="Network",
            short_description="Network switch flapping on edge-sw-01",
            description="Edge switch experiencing intermittent link up/down cycles. "
                        "Multiple VLANs affected.",
            cmdb_ci="edge-sw-01",
        )

        handler = IncidentHandler()
        routing_request = await handler.process(payload)
        assert routing_request.context["risk_level"] == "high"
        assert routing_request.context["subcategory"] == "network"

        correlations = [
            Correlation(
                correlation_id="corr_net_001",
                source_event_id="evt_sw_01",
                target_event_id="evt_sw_02",
                correlation_type=CorrelationType.TIME,
                score=0.92,
                confidence=0.88,
                evidence=["Events within 30-second window"],
            ),
            Correlation(
                correlation_id="corr_net_002",
                source_event_id="evt_sw_01",
                target_event_id="evt_vlan_01",
                correlation_type=CorrelationType.DEPENDENCY,
                score=0.85,
                confidence=0.80,
                evidence=["VLAN depends on switch port"],
            ),
            Correlation(
                correlation_id="corr_net_003",
                source_event_id="evt_sw_01",
                target_event_id="evt_alert_01",
                correlation_type=CorrelationType.CAUSAL,
                score=0.78,
                confidence=0.75,
                evidence=["Switch flapping caused downstream alert"],
            ),
        ]

        context = IncidentContext(
            incident_number="INC0100002",
            severity=IncidentSeverity.P2,
            category=IncidentCategory.NETWORK,
            short_description=payload["short_description"],
            description=payload["description"],
            affected_components=["edge-sw-01"],
        )

        analyzer = IncidentAnalyzer(
            correlation_analyzer=_make_mock_correlation_analyzer(correlations),
            rootcause_analyzer=_make_mock_rootcause_analyzer(
                root_cause="Switch port hardware failure causing link flapping",
                confidence=0.82,
            ),
        )
        analysis = await analyzer.analyze(context)

        assert analysis.correlations_found == 3
        assert analysis.root_cause_confidence > 0.5

    @pytest.mark.asyncio
    async def test_p3_database_replication_lag(self) -> None:
        """P3 database replication lag incident processes as medium risk."""
        payload = _make_inc_payload(
            number="INC0100003",
            priority="3",
            category="Database",
            short_description="Database replication lag on db-replica-02",
            description="Replication lag exceeds 60 seconds. Read queries may return stale data.",
            cmdb_ci="db-replica-02",
        )

        handler = IncidentHandler()
        routing_request = await handler.process(payload)
        assert routing_request.context["risk_level"] == "medium"
        assert routing_request.context["subcategory"] == "database"

        context = IncidentContext(
            incident_number="INC0100003",
            severity=IncidentSeverity.P3,
            category=IncidentCategory.DATABASE,
            short_description=payload["short_description"],
            description=payload["description"],
            cmdb_ci="db-replica-02",
        )

        analyzer = IncidentAnalyzer(
            correlation_analyzer=_make_mock_correlation_analyzer(),
            rootcause_analyzer=_make_mock_rootcause_analyzer(
                root_cause="Long-running transaction blocking replication",
                confidence=0.70,
            ),
        )
        analysis = await analyzer.analyze(context)
        assert analysis.incident_number == "INC0100003"
        assert analysis.root_cause_confidence > 0

    @pytest.mark.asyncio
    async def test_p4_performance_slowdown(self) -> None:
        """P4 performance slowdown -> LOW risk -> auto-remediation available."""
        payload = _make_inc_payload(
            number="INC0100004",
            priority="4",
            category="Performance",
            short_description="Slow response times on web-frontend-01",
            description="Response times degraded from 200ms to 2s average.",
            cmdb_ci="web-frontend-01",
        )

        handler = IncidentHandler()
        routing_request = await handler.process(payload)
        assert routing_request.context["risk_level"] == "low"
        assert routing_request.context["subcategory"] == "performance"

        context = IncidentContext(
            incident_number="INC0100004",
            severity=IncidentSeverity.P4,
            category=IncidentCategory.PERFORMANCE,
            short_description=payload["short_description"],
            cmdb_ci="web-frontend-01",
        )

        analysis = IncidentAnalysis(
            incident_number="INC0100004",
            root_cause_summary="Stale cache",
            root_cause_confidence=0.70,
        )

        recommender = ActionRecommender()
        actions = await recommender.recommend(analysis, context)
        assert len(actions) >= 1

        # Performance actions include cache clearing (LOW risk)
        cache_action = next(
            (a for a in actions if a.action_type == RemediationActionType.CLEAR_CACHE),
            None,
        )
        assert cache_action is not None
        assert cache_action.risk == RemediationRisk.LOW


# ---------------------------------------------------------------------------
# E2E: Recommendation Sorting and Coverage
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestIncidentRecommendationSorting:
    """E2E: Verify action recommendation sorting, coverage, and deduplication."""

    @pytest.mark.asyncio
    async def test_recommendations_sorted_by_confidence_risk(self) -> None:
        """Verify actions are sorted: highest confidence first, lowest risk for ties."""
        context = IncidentContext(
            incident_number="INC0110001",
            severity=IncidentSeverity.P3,
            category=IncidentCategory.APPLICATION,
            short_description="Application error",
        )

        # Provide multiple recommendations with varying confidence
        recs = [
            _make_recommendation("Low confidence fix", RecommendationType.LONG_TERM, priority=3),
            _make_recommendation("High confidence fix", RecommendationType.IMMEDIATE, priority=1),
            _make_recommendation("Medium confidence fix", RecommendationType.SHORT_TERM, priority=2),
        ]

        analyzer = IncidentAnalyzer(
            correlation_analyzer=_make_mock_correlation_analyzer(),
            rootcause_analyzer=_make_mock_rootcause_analyzer(
                root_cause="Memory leak",
                confidence=0.80,
                recommendations=recs,
            ),
        )
        analysis = await analyzer.analyze(context)

        recommender = ActionRecommender()
        actions = await recommender.recommend(analysis, context)

        # Actions should be sorted by confidence DESC
        for i in range(len(actions) - 1):
            if actions[i].confidence == actions[i + 1].confidence:
                # Same confidence: lower risk should come first
                risk_order = {
                    RemediationRisk.AUTO: 0, RemediationRisk.LOW: 1,
                    RemediationRisk.MEDIUM: 2, RemediationRisk.HIGH: 3,
                    RemediationRisk.CRITICAL: 4,
                }
                assert risk_order[actions[i].risk] <= risk_order[actions[i + 1].risk]
            else:
                assert actions[i].confidence >= actions[i + 1].confidence

    @pytest.mark.asyncio
    async def test_recommendations_per_category_coverage(self) -> None:
        """Verify rule-based recommendations exist for all 8 main categories."""
        categories = [
            IncidentCategory.NETWORK,
            IncidentCategory.SERVER,
            IncidentCategory.APPLICATION,
            IncidentCategory.DATABASE,
            IncidentCategory.SECURITY,
            IncidentCategory.STORAGE,
            IncidentCategory.PERFORMANCE,
            IncidentCategory.AUTHENTICATION,
        ]

        recommender = ActionRecommender()

        for cat in categories:
            context = IncidentContext(
                incident_number=f"INC_CAT_{cat.value.upper()}",
                severity=IncidentSeverity.P3,
                category=cat,
                short_description=f"Test {cat.value} incident",
            )
            analysis = IncidentAnalysis(
                incident_number=context.incident_number,
                root_cause_summary=f"Root cause for {cat.value}",
                root_cause_confidence=0.70,
            )

            actions = await recommender.recommend(analysis, context)
            assert len(actions) >= 1, (
                f"Category {cat.value} should have at least 1 recommendation"
            )

    @pytest.mark.asyncio
    async def test_recommendations_deduplication(self) -> None:
        """Same action title from rule-based and analysis should be deduplicated."""
        context = IncidentContext(
            incident_number="INC0110003",
            severity=IncidentSeverity.P3,
            category=IncidentCategory.APPLICATION,
            short_description="App service down",
        )

        # Analysis already has "Restart application service" from RCA
        analysis = IncidentAnalysis(
            incident_number="INC0110003",
            root_cause_summary="Service crashed",
            root_cause_confidence=0.80,
            recommended_actions=[
                RemediationAction(
                    action_type=RemediationActionType.RESTART_SERVICE,
                    title="Restart application service",
                    description="Restart the affected application service (from RCA)",
                    confidence=0.75,
                    risk=RemediationRisk.LOW,
                ),
            ],
        )

        recommender = ActionRecommender()
        actions = await recommender.recommend(analysis, context)

        # Should not have duplicate "Restart application service" titles
        titles = [a.title.lower().strip() for a in actions]
        assert titles.count("restart application service") == 1, (
            f"Duplicate action found: {titles}"
        )


# ---------------------------------------------------------------------------
# E2E: Execution Path Routing
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestIncidentExecutionPaths:
    """E2E: Verify execution routing based on risk level."""

    @pytest.mark.asyncio
    async def test_auto_execute_for_low_risk(self) -> None:
        """AUTO risk actions should be executed immediately and return COMPLETED."""
        context = IncidentContext(
            incident_number="INC0120001",
            severity=IncidentSeverity.P4,
            category=IncidentCategory.STORAGE,
            short_description="Disk full",
        )
        analysis = IncidentAnalysis(
            incident_number="INC0120001",
            root_cause_summary="Old logs",
            root_cause_confidence=0.85,
        )

        action = RemediationAction(
            action_type=RemediationActionType.CLEAR_DISK_SPACE,
            title="Clear temporary files",
            description="Remove old temp files",
            confidence=0.85,
            risk=RemediationRisk.AUTO,
            mcp_tool="shell:run_command",
        )

        executor = IncidentExecutor(hitl_controller=_make_mock_hitl_controller())
        results = await executor.execute(analysis, context, [action])

        assert len(results) == 1
        assert results[0].status == ExecutionStatus.COMPLETED
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_hitl_required_for_critical_risk(self) -> None:
        """CRITICAL risk actions should go through HITL and return AWAITING_APPROVAL."""
        context = IncidentContext(
            incident_number="INC0120002",
            severity=IncidentSeverity.P1,
            category=IncidentCategory.SECURITY,
            short_description="Security breach",
        )
        analysis = IncidentAnalysis(
            incident_number="INC0120002",
            root_cause_summary="Unauthorized access",
            root_cause_confidence=0.90,
        )

        action = RemediationAction(
            action_type=RemediationActionType.FIREWALL_RULE_CHANGE,
            title="Update firewall rules",
            description="Block suspicious IPs",
            confidence=0.80,
            risk=RemediationRisk.CRITICAL,
        )

        mock_hitl = _make_mock_hitl_controller()
        executor = IncidentExecutor(hitl_controller=mock_hitl)
        results = await executor.execute(analysis, context, [action])

        assert len(results) == 1
        assert results[0].status == ExecutionStatus.AWAITING_APPROVAL
        assert results[0].approval_request_id == "e2e-v2-approval-001"
        mock_hitl.request_approval.assert_called_once()

    @pytest.mark.asyncio
    async def test_medium_risk_configurable(self) -> None:
        """With auto_execute_medium=True, MEDIUM risk actions should auto-execute."""
        context = IncidentContext(
            incident_number="INC0120003",
            severity=IncidentSeverity.P3,
            category=IncidentCategory.DATABASE,
            short_description="DB connection pool exhausted",
        )
        analysis = IncidentAnalysis(
            incident_number="INC0120003",
            root_cause_summary="Connection pool leak",
            root_cause_confidence=0.65,
        )

        action = RemediationAction(
            action_type=RemediationActionType.RESTART_DATABASE,
            title="Restart database service",
            description="Restart to clear connection pool",
            confidence=0.65,
            risk=RemediationRisk.MEDIUM,
            mcp_tool="shell:run_command",
        )

        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            auto_execute_medium=True,
        )
        results = await executor.execute(analysis, context, [action])

        assert len(results) == 1
        assert results[0].status == ExecutionStatus.COMPLETED
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_medium_risk_default_hitl(self) -> None:
        """Without auto_execute_medium flag, MEDIUM risk goes to HITL."""
        context = IncidentContext(
            incident_number="INC0120004",
            severity=IncidentSeverity.P3,
            category=IncidentCategory.DATABASE,
            short_description="DB restart needed",
        )
        analysis = IncidentAnalysis(
            incident_number="INC0120004",
            root_cause_summary="Deadlock",
            root_cause_confidence=0.65,
        )

        action = RemediationAction(
            action_type=RemediationActionType.RESTART_DATABASE,
            title="Restart database service",
            description="Restart to clear deadlocks",
            confidence=0.65,
            risk=RemediationRisk.MEDIUM,
        )

        mock_hitl = _make_mock_hitl_controller()
        executor = IncidentExecutor(
            hitl_controller=mock_hitl,
            auto_execute_medium=False,
        )
        results = await executor.execute(analysis, context, [action])

        assert len(results) == 1
        assert results[0].status == ExecutionStatus.AWAITING_APPROVAL

    @pytest.mark.asyncio
    async def test_first_success_skips_remaining(self) -> None:
        """When the first auto-executed action succeeds, remaining actions are skipped."""
        context = IncidentContext(
            incident_number="INC0120005",
            severity=IncidentSeverity.P4,
            category=IncidentCategory.STORAGE,
            short_description="Disk full",
        )
        analysis = IncidentAnalysis(
            incident_number="INC0120005",
            root_cause_summary="Log accumulation",
            root_cause_confidence=0.85,
        )

        actions = [
            RemediationAction(
                action_type=RemediationActionType.CLEAR_DISK_SPACE,
                title="Clear temporary files",
                description="Remove temp files",
                confidence=0.85,
                risk=RemediationRisk.AUTO,
                mcp_tool="shell:run_command",
            ),
            RemediationAction(
                action_type=RemediationActionType.SCALE_RESOURCE,
                title="Scale storage",
                description="Add more disk",
                confidence=0.60,
                risk=RemediationRisk.LOW,
                mcp_tool="shell:run_command",
            ),
        ]

        executor = IncidentExecutor(hitl_controller=_make_mock_hitl_controller())
        results = await executor.execute(analysis, context, actions)

        assert len(results) == 2
        assert results[0].status == ExecutionStatus.COMPLETED
        assert results[0].success is True
        assert results[1].status == ExecutionStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_all_actions_fail_gracefully(self) -> None:
        """All actions failing should produce proper error results without crashing."""
        context = IncidentContext(
            incident_number="INC0120006",
            severity=IncidentSeverity.P3,
            category=IncidentCategory.APPLICATION,
            short_description="App crash",
        )
        analysis = IncidentAnalysis(
            incident_number="INC0120006",
            root_cause_summary="Unknown crash",
            root_cause_confidence=0.30,
        )

        # Shell executor that always fails
        failing_shell = MagicMock()
        failing_shell.execute = AsyncMock(side_effect=RuntimeError("Connection refused"))

        actions = [
            RemediationAction(
                action_type=RemediationActionType.RESTART_SERVICE,
                title="Restart app",
                description="Restart the application",
                confidence=0.60,
                risk=RemediationRisk.LOW,
                mcp_tool="shell:restart_service",
            ),
            RemediationAction(
                action_type=RemediationActionType.CLEAR_CACHE,
                title="Clear cache",
                description="Clear application cache",
                confidence=0.50,
                risk=RemediationRisk.LOW,
                mcp_tool="shell:clear_cache",
            ),
        ]

        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            shell_executor=failing_shell,
        )
        results = await executor.execute(analysis, context, actions)

        assert len(results) == 2
        # When shell executor is provided but the mcp_tool starts with "shell:",
        # the dispatch tries shell executor, which raises, causing FAILED
        for result in results:
            assert result.status == ExecutionStatus.FAILED
            assert result.success is False


# ---------------------------------------------------------------------------
# E2E: Chinese Description Classification
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestIncidentChineseDescriptions:
    """E2E: Verify Chinese-language descriptions classify to correct subcategories."""

    @pytest.mark.asyncio
    async def test_chinese_server_crash_description(self) -> None:
        """Chinese '伺服器當機' should classify as SERVER subcategory."""
        payload = _make_inc_payload(
            number="INC0130001",
            priority="1",
            short_description="伺服器當機 — prod-web-01 無法連線",
            description="主機 prod-web-01 於 10:00 完全無回應，ping 超時。",
        )

        handler = IncidentHandler()
        assert handler.can_handle(payload) is True
        routing_request = await handler.process(payload)

        assert routing_request.context["subcategory"] == IncidentSubCategory.SERVER.value

    @pytest.mark.asyncio
    async def test_chinese_database_description(self) -> None:
        """Chinese '資料庫連線異常' should classify as DATABASE subcategory."""
        payload = _make_inc_payload(
            number="INC0130002",
            priority="2",
            short_description="資料庫連線異常",
            description="資料庫 db-prod-01 連線數已達上限，新連線全部被拒。",
        )

        handler = IncidentHandler()
        routing_request = await handler.process(payload)

        assert routing_request.context["subcategory"] == IncidentSubCategory.DATABASE.value

    @pytest.mark.asyncio
    async def test_chinese_firewall_description(self) -> None:
        """Chinese '防火牆規則' should classify as NETWORK subcategory (via regex pattern)."""
        payload = _make_inc_payload(
            number="INC0130003",
            priority="2",
            short_description="防火牆規則異動導致外部連線中斷",
            description="今日 09:30 防火牆規則變更後，外部 API 呼叫全部失敗。",
        )

        handler = IncidentHandler()
        routing_request = await handler.process(payload)

        # "防火牆" matches the NETWORK regex pattern in the incident handler
        assert routing_request.context["subcategory"] == IncidentSubCategory.NETWORK.value
