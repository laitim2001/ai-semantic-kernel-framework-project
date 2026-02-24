"""
End-to-End Tests for IT Incident Processing Pipeline.

Sprint 126: Story 126-4 — IT Incident Processing (Phase 34)
Full pipeline tests: ServiceNow INC → IncidentHandler → Analyzer → Recommender → Executor

Tests the complete flow from webhook payload to execution result,
with various incident categories and severity levels.
"""

import pytest
from datetime import datetime
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
    RemediationActionType,
    RemediationRisk,
)
from src.integrations.correlation.types import (
    Correlation,
    CorrelationType,
    EventSeverity,
)
from src.integrations.rootcause.types import (
    AnalysisStatus,
    Recommendation,
    RecommendationType,
    RootCauseAnalysis,
    RootCauseHypothesis,
)


# ---------------------------------------------------------------------------
# Shared Mock Factories
# ---------------------------------------------------------------------------


def _make_mock_correlation_analyzer(correlations=None):
    """Create mocked CorrelationAnalyzer."""
    analyzer = MagicMock()
    analyzer.find_correlations = AsyncMock(return_value=correlations or [])
    return analyzer


def _make_mock_rootcause_analyzer(
    root_cause: str = "Unknown cause",
    confidence: float = 0.5,
    recommendations: list = None,
):
    """Create mocked RootCauseAnalyzer."""
    rca_result = RootCauseAnalysis(
        analysis_id="rca_e2e",
        event_id="evt_e2e_001",
        root_cause=root_cause,
        confidence=confidence,
        status=AnalysisStatus.COMPLETED,
        started_at=datetime(2026, 2, 25, 10, 0),
        completed_at=datetime(2026, 2, 25, 10, 5),
        contributing_factors=["factor_1"],
        hypotheses=[
            RootCauseHypothesis(
                hypothesis_id="hyp_e2e",
                description=root_cause,
                confidence=confidence,
                evidence=["e2e test evidence"],
            ),
        ],
        similar_historical_cases=[],
        recommendations=recommendations or [],
    )
    analyzer = MagicMock()
    analyzer.analyze_root_cause = AsyncMock(return_value=rca_result)
    return analyzer


def _make_mock_hitl_controller():
    """Create mocked HITL controller."""
    controller = MagicMock()
    approval_request = MagicMock()
    approval_request.request_id = "e2e-approval-001"
    controller.request_approval = AsyncMock(return_value=approval_request)
    return controller


def _make_inc_payload(
    number: str = "INC0050001",
    priority: str = "3",
    category: str = "",
    short_description: str = "Test incident",
    description: str = "Test incident description",
    cmdb_ci: str = "test-server",
    caller_id: str = "test.user",
) -> dict:
    """Create INC webhook payload."""
    return {
        "sys_id": f"e2e_{number.lower()}",
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
        "business_service": "E2E Test Service",
        "caller_id": caller_id,
        "assignment_group": "E2E Test Group",
        "sys_created_on": "2026-02-25T10:00:00Z",
    }


# ---------------------------------------------------------------------------
# E2E: Disk Space Incident → Auto-Cleanup
# ---------------------------------------------------------------------------


class TestDiskSpaceIncidentPipeline:
    """E2E: P4 disk space → auto-cleanup → resolved."""

    @pytest.mark.asyncio
    async def test_disk_space_full_auto_remediation(self) -> None:
        """Test full pipeline: disk space incident → auto-cleanup → success."""
        # 1. ServiceNow INC webhook payload
        payload = _make_inc_payload(
            number="INC0050001",
            priority="4",
            category="Storage",
            short_description="Disk space critical on srv-prod-01",
            description="/dev/sda1 at 97% capacity. Old log files consuming 50GB.",
            cmdb_ci="srv-prod-01",
        )

        # 2. IncidentHandler processes webhook
        handler = IncidentHandler()
        assert handler.can_handle(payload) is True
        routing_request = await handler.process(payload)
        assert routing_request.intent_hint == "incident"
        assert routing_request.context["risk_level"] == "low"
        assert routing_request.context["subcategory"] == "storage"

        # 3. Build IncidentContext from routing request
        context = IncidentContext(
            incident_number=routing_request.context["incident_number"],
            severity=IncidentSeverity.from_priority(payload["priority"]),
            category=IncidentCategory.STORAGE,
            short_description=payload["short_description"],
            description=payload["description"],
            affected_components=[payload["cmdb_ci"]],
            cmdb_ci=payload["cmdb_ci"],
        )

        # 4. Analyze incident
        analyzer = IncidentAnalyzer(
            correlation_analyzer=_make_mock_correlation_analyzer(),
            rootcause_analyzer=_make_mock_rootcause_analyzer(
                root_cause="Disk full due to accumulated log files",
                confidence=0.88,
            ),
        )
        analysis = await analyzer.analyze(context)
        assert analysis.incident_number == "INC0050001"
        assert analysis.root_cause_confidence > 0

        # 5. Recommend remediation actions
        recommender = ActionRecommender()
        actions = await recommender.recommend(analysis, context)
        assert len(actions) >= 1
        # Should have disk cleanup action
        disk_action = next(
            (a for a in actions if a.action_type == RemediationActionType.CLEAR_DISK_SPACE),
            None,
        )
        assert disk_action is not None
        assert disk_action.risk in (RemediationRisk.AUTO, RemediationRisk.LOW)

        # 6. Execute remediation
        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
        )
        results = await executor.execute(analysis, context, actions)
        assert len(results) >= 1
        # First action should be auto-executed (simulated)
        assert results[0].success is True
        assert results[0].status == ExecutionStatus.COMPLETED


# ---------------------------------------------------------------------------
# E2E: Critical Security Incident → HITL Approval
# ---------------------------------------------------------------------------


class TestCriticalSecurityIncidentPipeline:
    """E2E: P1 critical security → HITL approval → awaiting."""

    @pytest.mark.asyncio
    async def test_security_incident_requires_approval(self) -> None:
        """Test P1 security incident triggers HITL approval workflow."""
        # 1. INC payload
        payload = _make_inc_payload(
            number="INC0050002",
            priority="1",
            category="Security",
            short_description="Unauthorized access detected on web-server-01",
            description="Multiple failed SSH attempts from unknown IP range",
        )

        # 2. Handler
        handler = IncidentHandler()
        routing_request = await handler.process(payload)
        assert routing_request.context["risk_level"] == "critical"
        assert routing_request.context["subcategory"] == "security"

        # 3. Context
        context = IncidentContext(
            incident_number="INC0050002",
            severity=IncidentSeverity.P1,
            category=IncidentCategory.SECURITY,
            short_description=payload["short_description"],
            description=payload["description"],
        )

        # 4. Analyze
        analyzer = IncidentAnalyzer(
            correlation_analyzer=_make_mock_correlation_analyzer([
                Correlation(
                    correlation_id="sec_corr",
                    correlation_type=CorrelationType.TIME,
                    source_event_id="evt_sec_1",
                    target_event_id="evt_sec_2",
                    score=0.90,
                    confidence=0.90,
                    evidence=["Multiple IPs from same subnet"],
                ),
            ]),
            rootcause_analyzer=_make_mock_rootcause_analyzer(
                root_cause="Brute force SSH attack from external IP range",
                confidence=0.92,
            ),
        )
        analysis = await analyzer.analyze(context)
        assert analysis.correlations_found == 1

        # 5. Recommend
        recommender = ActionRecommender()
        actions = await recommender.recommend(analysis, context)
        # Security actions should be CRITICAL risk
        firewall_action = next(
            (a for a in actions if a.action_type == RemediationActionType.FIREWALL_RULE_CHANGE),
            None,
        )
        assert firewall_action is not None
        assert firewall_action.risk == RemediationRisk.CRITICAL

        # 6. Execute — should trigger HITL
        mock_hitl = _make_mock_hitl_controller()
        executor = IncidentExecutor(hitl_controller=mock_hitl)
        results = await executor.execute(analysis, context, [firewall_action])
        assert results[0].status == ExecutionStatus.AWAITING_APPROVAL
        assert results[0].approval_request_id == "e2e-approval-001"
        mock_hitl.request_approval.assert_called_once()


# ---------------------------------------------------------------------------
# E2E: Auth Incident → AD Unlock
# ---------------------------------------------------------------------------


class TestAuthIncidentPipeline:
    """E2E: Auth incident → AD account unlock → resolved."""

    @pytest.mark.asyncio
    async def test_auth_lockout_auto_unlock(self) -> None:
        """Test authentication lockout auto-unlock pipeline."""
        # 1. INC payload
        payload = _make_inc_payload(
            number="INC0050003",
            priority="4",
            short_description="Account locked out for user john.doe",
            description="User john.doe AD account locked after failed login attempts",
            caller_id="john.doe",
        )

        # 2. Handler
        handler = IncidentHandler()
        routing_request = await handler.process(payload)
        assert routing_request.context["subcategory"] == "authentication"

        # 3. Context
        context = IncidentContext(
            incident_number="INC0050003",
            severity=IncidentSeverity.P4,
            category=IncidentCategory.AUTHENTICATION,
            short_description=payload["short_description"],
            caller_id="john.doe",
        )

        # 4. Recommend
        analysis = IncidentAnalysis(
            analysis_id="ana_auth_e2e",
            incident_number="INC0050003",
            root_cause_summary="AD account locked due to password expiry",
            root_cause_confidence=0.90,
        )
        recommender = ActionRecommender()
        actions = await recommender.recommend(analysis, context)
        ad_unlock = next(
            (a for a in actions if a.action_type == RemediationActionType.AD_ACCOUNT_UNLOCK),
            None,
        )
        assert ad_unlock is not None
        assert ad_unlock.risk == RemediationRisk.AUTO

        # 5. Execute with mock LDAP
        mock_ldap = MagicMock()
        mock_ldap.execute = AsyncMock(return_value="Account john.doe unlocked")
        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            ldap_executor=mock_ldap,
        )
        results = await executor.execute(analysis, context, [ad_unlock])
        assert results[0].success is True
        assert "john.doe unlocked" in results[0].output


# ---------------------------------------------------------------------------
# E2E: LLM Unavailable Fallback
# ---------------------------------------------------------------------------


class TestLLMUnavailableFallback:
    """E2E: LLM service unavailable → rule-based only analysis and recommendations."""

    @pytest.mark.asyncio
    async def test_pipeline_works_without_llm(self) -> None:
        """Test pipeline works end-to-end without LLM."""
        payload = _make_inc_payload(
            number="INC0050004",
            priority="3",
            category="Application",
            short_description="Application crash on app-server-01",
            description="OutOfMemoryError in Java application",
        )

        handler = IncidentHandler()
        routing_request = await handler.process(payload)

        context = IncidentContext(
            incident_number="INC0050004",
            severity=IncidentSeverity.P3,
            category=IncidentCategory.APPLICATION,
            short_description=payload["short_description"],
        )

        # Failing LLM
        failing_llm = MagicMock()
        failing_llm.generate_structured = AsyncMock(
            side_effect=Exception("LLM API timeout")
        )

        analyzer = IncidentAnalyzer(
            correlation_analyzer=_make_mock_correlation_analyzer(),
            rootcause_analyzer=_make_mock_rootcause_analyzer(
                root_cause="Memory leak in application",
                confidence=0.70,
            ),
            llm_service=failing_llm,
        )
        analysis = await analyzer.analyze(context)
        assert analysis.llm_enhanced is False
        assert analysis.root_cause_confidence > 0

        recommender = ActionRecommender(llm_service=failing_llm)
        actions = await recommender.recommend(analysis, context)
        assert len(actions) >= 1
        assert any(
            a.action_type == RemediationActionType.RESTART_SERVICE for a in actions
        )


# ---------------------------------------------------------------------------
# E2E: Multiple Concurrent Incidents
# ---------------------------------------------------------------------------


class TestMultipleConcurrentIncidents:
    """E2E: Process multiple incidents in sequence."""

    @pytest.mark.asyncio
    async def test_multiple_incidents_processed(self) -> None:
        """Test multiple incidents can be processed independently."""
        handler = IncidentHandler()
        incidents = [
            _make_inc_payload(
                number="INC0060001",
                priority="4",
                category="Storage",
                short_description="Disk full on backup-srv",
            ),
            _make_inc_payload(
                number="INC0060002",
                priority="2",
                category="Network",
                short_description="Router failure on edge-rtr-01",
            ),
            _make_inc_payload(
                number="INC0060003",
                priority="3",
                short_description="Database replication lag on db-replica-02",
            ),
        ]

        results = []
        for payload in incidents:
            routing = await handler.process(payload)
            results.append(routing)

        assert len(results) == 3
        assert results[0].context["risk_level"] == "low"
        assert results[1].context["risk_level"] == "high"
        assert results[2].context["risk_level"] == "medium"

        # All should be incident intent
        for r in results:
            assert r.intent_hint == "incident"


# ---------------------------------------------------------------------------
# E2E: ServiceNow Writeback Failure (Graceful Degradation)
# ---------------------------------------------------------------------------


class TestServiceNowWritebackFailure:
    """E2E: ServiceNow writeback failure → graceful degradation."""

    @pytest.mark.asyncio
    async def test_execution_succeeds_despite_sn_failure(self) -> None:
        """Test execution completes even when ServiceNow writeback fails."""
        context = IncidentContext(
            incident_number="INC0070001",
            severity=IncidentSeverity.P4,
            category=IncidentCategory.PERFORMANCE,
            short_description="Slow response on web-app-01",
        )

        analysis = IncidentAnalysis(
            analysis_id="ana_perf_e2e",
            incident_number="INC0070001",
            root_cause_summary="Stale cache entries",
            root_cause_confidence=0.75,
        )

        recommender = ActionRecommender()
        actions = await recommender.recommend(analysis, context)
        assert len(actions) >= 1

        # ServiceNow client that always fails
        failing_sn = MagicMock()
        failing_sn.update_incident = AsyncMock(side_effect=Exception("SN timeout"))
        failing_sn.add_work_note = AsyncMock(side_effect=Exception("SN timeout"))

        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            servicenow_client=failing_sn,
        )
        results = await executor.execute(analysis, context, actions)

        # Execution should still succeed despite SN failure
        assert any(r.success for r in results)
        # But SN should not be marked as updated
        for r in results:
            if r.success:
                assert r.servicenow_updated is False
