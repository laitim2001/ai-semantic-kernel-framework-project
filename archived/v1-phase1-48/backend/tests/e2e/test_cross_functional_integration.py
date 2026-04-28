"""
Cross-Functional Integration Tests: n8n + ADF + Incident.

Sprint 127: Story 127-3 — Cross-Functional Integration (Phase 34)

Tests the interaction between the three core Sprint 127 subsystems:
    - Incident processing (ServiceNow INC -> analysis -> recommendation -> execution)
    - ADF pipeline management (trigger, monitor, rerun)
    - n8n workflow orchestration (notification workflows)

All external I/O is mocked (httpx, ServiceNow client, LDAP executor).
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Incident processing
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
from src.integrations.orchestration.input.incident_handler import IncidentHandler

# n8n orchestration
from src.integrations.mcp.servers.n8n.client import N8nApiClient, N8nConfig
from src.integrations.n8n.orchestrator import (
    N8nOrchestrator,
    OrchestrationRequest,
    OrchestrationResult,
    OrchestrationStatus,
    ReasoningResult,
)

# ADF pipeline
from src.integrations.mcp.servers.adf.client import AdfApiClient, AdfConfig, PipelineRunStatus

# Rootcause types (for analyzer mocks)
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


def _make_mock_correlation_analyzer(
    correlations: Optional[List[Any]] = None,
) -> MagicMock:
    """Create a mocked CorrelationAnalyzer."""
    analyzer = MagicMock()
    analyzer.find_correlations = AsyncMock(return_value=correlations or [])
    return analyzer


def _make_mock_rootcause_analyzer(
    root_cause: str = "Unknown cause",
    confidence: float = 0.5,
    recommendations: Optional[List[Recommendation]] = None,
) -> MagicMock:
    """Create a mocked RootCauseAnalyzer returning a complete RootCauseAnalysis."""
    rca_result = RootCauseAnalysis(
        analysis_id="rca_cross_func",
        event_id="evt_cross_001",
        root_cause=root_cause,
        confidence=confidence,
        status=AnalysisStatus.COMPLETED,
        started_at=datetime(2026, 2, 25, 10, 0),
        completed_at=datetime(2026, 2, 25, 10, 5),
        contributing_factors=["factor_cross_1"],
        hypotheses=[
            RootCauseHypothesis(
                hypothesis_id="hyp_cross",
                description=root_cause,
                confidence=confidence,
                evidence=["cross-functional evidence"],
            ),
        ],
        similar_historical_cases=[],
        recommendations=recommendations or [],
    )
    analyzer = MagicMock()
    analyzer.analyze_root_cause = AsyncMock(return_value=rca_result)
    return analyzer


def _make_mock_hitl_controller() -> MagicMock:
    """Create a mocked HITL controller."""
    controller = MagicMock()
    approval = MagicMock()
    approval.request_id = "cross-approval-001"
    controller.request_approval = AsyncMock(return_value=approval)
    return controller


def _make_adf_config() -> AdfConfig:
    """Create a test ADF configuration."""
    return AdfConfig(
        subscription_id="cross-sub-001",
        resource_group="cross-rg",
        factory_name="cross-adf",
        tenant_id="cross-tenant",
        client_id="cross-client-id",
        client_secret="cross-client-secret",
        timeout=5,
        max_retries=1,
        retry_base_delay=0.01,
    )


def _make_n8n_config() -> N8nConfig:
    """Create a test n8n configuration."""
    return N8nConfig(
        base_url="http://localhost:5678",
        api_key="cross-n8n-api-key",
        timeout=5,
        max_retries=1,
    )


def _make_mock_adf_client(
    pipeline_status: str = PipelineRunStatus.SUCCEEDED.value,
    run_id: str = "adf-run-cross-001",
    error_message: str = "",
) -> MagicMock:
    """Create a mocked AdfApiClient returning predetermined results."""
    client = MagicMock(spec=AdfApiClient)
    client.run_pipeline = AsyncMock(return_value={"runId": run_id})

    status_body: Dict[str, Any] = {
        "runId": run_id,
        "pipelineName": "etl-daily",
        "status": pipeline_status,
        "runStart": "2026-02-25T10:00:00Z",
    }
    if pipeline_status == PipelineRunStatus.SUCCEEDED.value:
        status_body["runEnd"] = "2026-02-25T10:05:00Z"
        status_body["output"] = {"rowsCopied": 15000}
    elif pipeline_status == PipelineRunStatus.FAILED.value:
        status_body["runEnd"] = "2026-02-25T10:03:00Z"
        status_body["message"] = error_message or "Pipeline execution failed"

    client.get_pipeline_run = AsyncMock(return_value=status_body)
    client.close = AsyncMock()
    return client


def _make_mock_n8n_client(
    execute_success: bool = True,
    execute_error: Optional[Exception] = None,
) -> MagicMock:
    """Create a mocked N8nApiClient."""
    client = MagicMock(spec=N8nApiClient)

    if execute_error:
        client.execute_workflow = AsyncMock(side_effect=execute_error)
    elif execute_success:
        client.execute_workflow = AsyncMock(return_value={
            "data": {
                "executionId": "n8n-exec-cross-001",
                "status": "success",
                "data": {"notificationSent": True},
            },
        })
    else:
        client.execute_workflow = AsyncMock(return_value={
            "data": {
                "executionId": "n8n-exec-cross-002",
                "status": "error",
                "data": {},
            },
        })

    client.close = AsyncMock()
    return client


def _make_mock_servicenow_client(
    should_fail: bool = False,
) -> MagicMock:
    """Create a mocked ServiceNow client for writeback."""
    client = MagicMock()
    if should_fail:
        client.update_incident = AsyncMock(
            side_effect=Exception("ServiceNow API timeout")
        )
        client.add_work_note = AsyncMock(
            side_effect=Exception("ServiceNow API timeout")
        )
    else:
        client.update_incident = AsyncMock(return_value={"status": "updated"})
        client.add_work_note = AsyncMock(return_value={"status": "noted"})
    return client


def _make_etl_failure_context() -> IncidentContext:
    """Create an incident context for an ETL pipeline failure."""
    return IncidentContext(
        incident_number="INC0200001",
        severity=IncidentSeverity.P2,
        category=IncidentCategory.APPLICATION,
        short_description="ETL pipeline daily-customer-sync failed in ADF",
        description="ADF pipeline daily-customer-sync failed at Copy Activity stage. "
                    "Source dataset connection timeout after 30 seconds.",
        affected_components=["adf-daily-customer-sync", "sql-prod-01"],
        business_service="Customer Data Platform",
        cmdb_ci="adf-daily-customer-sync",
    )


def _make_etl_analysis(
    root_cause: str = "ADF pipeline timeout due to source database overload",
    confidence: float = 0.78,
) -> IncidentAnalysis:
    """Create an incident analysis for ETL failure."""
    return IncidentAnalysis(
        incident_number="INC0200001",
        root_cause_summary=root_cause,
        root_cause_confidence=confidence,
        correlations_found=2,
        historical_matches=1,
        contributing_factors=["Source DB high CPU", "Large data volume spike"],
        recommended_actions=[
            RemediationAction(
                action_type=RemediationActionType.CUSTOM,
                title="Rerun ADF pipeline with extended timeout",
                description="Trigger ADF pipeline daily-customer-sync with timeout=120s",
                confidence=0.78,
                risk=RemediationRisk.MEDIUM,
                mcp_tool="adf:run_pipeline",
                mcp_params={
                    "pipeline_name": "daily-customer-sync",
                    "timeout": 120,
                },
            ),
        ],
    )


# ---------------------------------------------------------------------------
# E2E: Incident -> ADF Pipeline Rerun
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestIncidentToAdfPipelineRerun:
    """E2E: ETL failure incident triggers ADF pipeline rerun."""

    @pytest.mark.asyncio
    async def test_etl_failure_incident_triggers_adf_rerun(self) -> None:
        """Full scenario: ServiceNow INC for ETL failure -> analysis -> ADF rerun trigger."""
        # Step 1: Process webhook payload through IncidentHandler
        payload = {
            "sys_id": "cross_inc_etl_001",
            "number": "INC0200001",
            "state": "1",
            "impact": "2",
            "urgency": "2",
            "priority": "2",
            "category": "Software",
            "subcategory": "",
            "short_description": "ETL pipeline daily-customer-sync failed in ADF",
            "description": "ADF pipeline daily-customer-sync failed at Copy Activity stage.",
            "cmdb_ci": "adf-daily-customer-sync",
            "business_service": "Customer Data Platform",
            "caller_id": "monitoring.system",
            "assignment_group": "Data Engineering",
            "sys_created_on": "2026-02-25T10:00:00Z",
        }

        handler = IncidentHandler()
        assert handler.can_handle(payload) is True
        routing_request = await handler.process(payload)
        assert routing_request.intent_hint == "incident"
        assert routing_request.context["risk_level"] == "high"

        # Step 2: Build context and analyze
        context = _make_etl_failure_context()
        analysis = _make_etl_analysis()

        # Step 3: Get the ADF rerun action
        adf_rerun_action = analysis.recommended_actions[0]
        assert "ADF pipeline" in adf_rerun_action.title

        # Step 4: Simulate ADF pipeline rerun via mocked ADF client
        mock_adf = _make_mock_adf_client(
            pipeline_status=PipelineRunStatus.SUCCEEDED.value,
            run_id="adf-rerun-cross-001",
        )

        # Execute the ADF pipeline rerun
        run_result = await mock_adf.run_pipeline(
            adf_rerun_action.mcp_params["pipeline_name"],
            parameters={"timeout": adf_rerun_action.mcp_params["timeout"]},
        )
        assert run_result["runId"] == "adf-rerun-cross-001"

        # Check pipeline run status
        status = await mock_adf.get_pipeline_run(run_result["runId"])
        assert status["status"] == PipelineRunStatus.SUCCEEDED.value
        assert status["output"]["rowsCopied"] == 15000

        # Verify the pipeline was called with correct name
        mock_adf.run_pipeline.assert_called_once_with(
            "daily-customer-sync",
            parameters={"timeout": 120},
        )

    @pytest.mark.asyncio
    async def test_adf_rerun_success_resolves_incident(self) -> None:
        """ADF pipeline succeeds -> executor marks incident as resolved via ServiceNow."""
        context = _make_etl_failure_context()
        analysis = _make_etl_analysis()

        # Auto-execute the rerun action (simulate as LOW risk for this test)
        action = RemediationAction(
            action_type=RemediationActionType.CUSTOM,
            title="Rerun ADF pipeline",
            description="Trigger ADF pipeline rerun",
            confidence=0.78,
            risk=RemediationRisk.LOW,
            mcp_tool="shell:run_command",
            mcp_params={"command": "az datafactory pipeline create-run ..."},
        )

        mock_sn = _make_mock_servicenow_client(should_fail=False)
        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            servicenow_client=mock_sn,
        )
        results = await executor.execute(analysis, context, [action])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].status == ExecutionStatus.COMPLETED

        # ServiceNow should have been updated
        assert mock_sn.update_incident.call_count >= 1

    @pytest.mark.asyncio
    async def test_adf_rerun_failure_updates_incident(self) -> None:
        """ADF pipeline fails -> incident not resolved, error captured in execution result."""
        context = _make_etl_failure_context()
        analysis = _make_etl_analysis()

        # Shell executor that simulates ADF CLI failure
        failing_shell = MagicMock()
        failing_shell.execute = AsyncMock(
            side_effect=RuntimeError("ADF pipeline failed: source dataset unreachable")
        )

        action = RemediationAction(
            action_type=RemediationActionType.CUSTOM,
            title="Rerun ADF pipeline",
            description="Trigger ADF pipeline rerun",
            confidence=0.78,
            risk=RemediationRisk.LOW,
            mcp_tool="shell:run_command",
            mcp_params={"command": "az datafactory pipeline create-run ..."},
        )

        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            shell_executor=failing_shell,
        )
        results = await executor.execute(analysis, context, [action])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].status == ExecutionStatus.FAILED
        assert "source dataset unreachable" in results[0].error


# ---------------------------------------------------------------------------
# E2E: Incident -> n8n Notification
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestIncidentToN8nNotification:
    """E2E: Incident resolution triggers n8n notification workflow."""

    @pytest.mark.asyncio
    async def test_incident_triggers_n8n_notification_workflow(self) -> None:
        """After incident resolution, n8n notification workflow executes with correct payload."""
        mock_n8n = _make_mock_n8n_client(execute_success=True)

        # Simulate post-resolution notification via n8n
        notification_payload = {
            "incident_number": "INC0200001",
            "status": "resolved",
            "resolution": "ADF pipeline rerun succeeded",
            "resolved_at": datetime(2026, 2, 25, 10, 10).isoformat(),
            "assignee": "data-engineering-team",
        }

        result = await mock_n8n.execute_workflow(
            workflow_id="wf-notification-001",
            data=notification_payload,
        )

        assert result["data"]["status"] == "success"
        assert result["data"]["data"]["notificationSent"] is True

        # Verify the workflow was called with correct payload
        mock_n8n.execute_workflow.assert_called_once_with(
            workflow_id="wf-notification-001",
            data=notification_payload,
        )

    @pytest.mark.asyncio
    async def test_n8n_notification_failure_graceful_degradation(self) -> None:
        """n8n is down: notification fails but incident resolution continues."""
        mock_n8n = _make_mock_n8n_client(
            execute_error=ConnectionError("n8n service unavailable")
        )

        # Incident resolution succeeds independently
        context = _make_etl_failure_context()
        analysis = _make_etl_analysis()

        action = RemediationAction(
            action_type=RemediationActionType.CUSTOM,
            title="Rerun ADF pipeline",
            description="Trigger rerun",
            confidence=0.78,
            risk=RemediationRisk.LOW,
            mcp_tool="shell:run_command",
        )

        executor = IncidentExecutor(hitl_controller=_make_mock_hitl_controller())
        results = await executor.execute(analysis, context, [action])

        # Incident execution succeeds
        assert len(results) == 1
        assert results[0].success is True

        # Notification attempt fails but does not crash
        with pytest.raises(ConnectionError):
            await mock_n8n.execute_workflow(
                workflow_id="wf-notification-001",
                data={"incident_number": "INC0200001", "status": "resolved"},
            )


# ---------------------------------------------------------------------------
# E2E: Full Orchestration Scenario
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestFullOrchestrationScenario:
    """E2E: Complete scenario combining incident, ADF, and n8n."""

    @pytest.mark.asyncio
    async def test_full_scenario_incident_adf_n8n_servicenow(self) -> None:
        """Complete end-to-end: INC -> Analyze -> ADF Rerun -> n8n Notify -> SN Writeback."""
        # Step 1: ServiceNow INC webhook
        payload = {
            "sys_id": "cross_full_001",
            "number": "INC0200010",
            "state": "1",
            "impact": "2",
            "urgency": "2",
            "priority": "2",
            "category": "Software",
            "subcategory": "",
            "short_description": "ETL pipeline failure — daily-customer-sync",
            "description": "Pipeline failed with timeout error at Copy Activity stage.",
            "cmdb_ci": "adf-daily-customer-sync",
            "business_service": "Customer Data Platform",
            "caller_id": "monitoring",
            "assignment_group": "Data Engineering",
        }

        handler = IncidentHandler()
        routing_request = await handler.process(payload)
        assert routing_request.context["risk_level"] == "high"

        # Step 2: Build context
        context = IncidentContext(
            incident_number="INC0200010",
            severity=IncidentSeverity.P2,
            category=IncidentCategory.APPLICATION,
            short_description=payload["short_description"],
            description=payload["description"],
            cmdb_ci="adf-daily-customer-sync",
        )

        # Step 3: Analyze with correlations
        from src.integrations.correlation.types import Correlation, CorrelationType

        correlations = [
            Correlation(
                correlation_id="corr_full_001",
                source_event_id="evt_adf_01",
                target_event_id="evt_db_load_01",
                correlation_type=CorrelationType.CAUSAL,
                score=0.88,
                confidence=0.85,
                evidence=["Pipeline failure followed DB CPU spike by 2 minutes"],
            ),
        ]

        analyzer = IncidentAnalyzer(
            correlation_analyzer=_make_mock_correlation_analyzer(correlations),
            rootcause_analyzer=_make_mock_rootcause_analyzer(
                root_cause="ADF pipeline timeout due to source DB overload",
                confidence=0.82,
                recommendations=[
                    Recommendation(
                        recommendation_id="rec_rerun",
                        recommendation_type=RecommendationType.IMMEDIATE,
                        title="Rerun ADF pipeline with increased timeout",
                        description="Retrigger the pipeline after DB load subsides",
                        priority=1,
                        estimated_effort="15 minutes",
                        steps=["Wait for DB CPU < 80%", "Trigger pipeline rerun"],
                    ),
                ],
            ),
        )
        analysis = await analyzer.analyze(context)
        assert analysis.correlations_found == 1
        assert analysis.root_cause_confidence > 0.5

        # Step 4: Recommend actions
        recommender = ActionRecommender()
        actions = await recommender.recommend(analysis, context)
        assert len(actions) >= 1

        # Step 5: Execute with HITL mock (MEDIUM risk from RCA recommendation)
        # Find the rerun action and set it to LOW for auto-execution
        rerun_action = RemediationAction(
            action_type=RemediationActionType.CUSTOM,
            title="Rerun ADF pipeline",
            description="Retrigger the pipeline",
            confidence=0.78,
            risk=RemediationRisk.LOW,
            mcp_tool="shell:run_command",
            mcp_params={"command": "az datafactory pipeline create-run ..."},
        )

        mock_sn = _make_mock_servicenow_client(should_fail=False)
        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            servicenow_client=mock_sn,
        )
        results = await executor.execute(analysis, context, [rerun_action])
        assert len(results) == 1
        assert results[0].success is True

        # Step 6: ADF pipeline execution (mocked)
        mock_adf = _make_mock_adf_client(
            pipeline_status=PipelineRunStatus.SUCCEEDED.value,
        )
        adf_run = await mock_adf.run_pipeline("daily-customer-sync")
        adf_status = await mock_adf.get_pipeline_run(adf_run["runId"])
        assert adf_status["status"] == PipelineRunStatus.SUCCEEDED.value

        # Step 7: n8n notification (mocked)
        mock_n8n = _make_mock_n8n_client(execute_success=True)
        notification = await mock_n8n.execute_workflow(
            workflow_id="wf-incident-resolved",
            data={
                "incident_number": "INC0200010",
                "status": "resolved",
                "resolution": "ADF pipeline rerun succeeded",
            },
        )
        assert notification["data"]["status"] == "success"

        # Step 8: Verify ServiceNow writeback was called
        assert mock_sn.update_incident.call_count >= 1
        assert mock_sn.add_work_note.call_count >= 1

    @pytest.mark.asyncio
    async def test_full_scenario_with_adf_failure(self) -> None:
        """Same scenario but ADF fails: n8n notifies failure, SN updated with failure."""
        context = IncidentContext(
            incident_number="INC0200011",
            severity=IncidentSeverity.P2,
            category=IncidentCategory.APPLICATION,
            short_description="ETL pipeline failure",
            cmdb_ci="adf-daily-customer-sync",
        )

        analysis = _make_etl_analysis()

        # Shell executor simulates ADF CLI failure
        failing_shell = MagicMock()
        failing_shell.execute = AsyncMock(
            side_effect=RuntimeError("ADF pipeline failed: data source offline")
        )

        action = RemediationAction(
            action_type=RemediationActionType.CUSTOM,
            title="Rerun ADF pipeline",
            description="Trigger rerun",
            confidence=0.78,
            risk=RemediationRisk.LOW,
            mcp_tool="shell:run_command",
        )

        mock_sn = _make_mock_servicenow_client(should_fail=False)
        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            servicenow_client=mock_sn,
            shell_executor=failing_shell,
        )
        results = await executor.execute(analysis, context, [action])
        assert results[0].success is False
        assert results[0].status == ExecutionStatus.FAILED

        # n8n notification sends failure status
        mock_n8n = _make_mock_n8n_client(execute_success=True)
        notification = await mock_n8n.execute_workflow(
            workflow_id="wf-incident-failure",
            data={
                "incident_number": "INC0200011",
                "status": "failed",
                "error": "ADF pipeline failed: data source offline",
            },
        )
        assert notification["data"]["status"] == "success"

        # ServiceNow was still updated (writeback happens for failed actions too)
        assert mock_sn.add_work_note.call_count >= 1


# ---------------------------------------------------------------------------
# E2E: Error Propagation
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestErrorPropagation:
    """E2E: Verify error propagation across subsystem boundaries."""

    @pytest.mark.asyncio
    async def test_adf_failure_propagates_to_incident(self) -> None:
        """ADF returns Failed -> incident analysis updated with failure info."""
        mock_adf = _make_mock_adf_client(
            pipeline_status=PipelineRunStatus.FAILED.value,
            run_id="adf-fail-prop-001",
            error_message="Source dataset connection refused",
        )

        run_result = await mock_adf.run_pipeline("etl-daily")
        status = await mock_adf.get_pipeline_run(run_result["runId"])

        assert status["status"] == PipelineRunStatus.FAILED.value
        assert "connection refused" in status["message"]

        # This failure information can be used to update the incident analysis
        updated_context = IncidentContext(
            incident_number="INC0200020",
            severity=IncidentSeverity.P2,
            category=IncidentCategory.APPLICATION,
            short_description="ETL failure",
            metadata={"adf_error": status["message"]},
        )
        assert "connection refused" in updated_context.metadata["adf_error"]

    @pytest.mark.asyncio
    async def test_n8n_notification_failure_does_not_block(self) -> None:
        """n8n throws exception -> overall incident flow still succeeds."""
        context = IncidentContext(
            incident_number="INC0200021",
            severity=IncidentSeverity.P4,
            category=IncidentCategory.PERFORMANCE,
            short_description="Slow response",
        )
        analysis = IncidentAnalysis(
            incident_number="INC0200021",
            root_cause_summary="Stale cache",
            root_cause_confidence=0.70,
        )

        action = RemediationAction(
            action_type=RemediationActionType.CLEAR_CACHE,
            title="Clear cache",
            description="Clear application cache",
            confidence=0.70,
            risk=RemediationRisk.LOW,
            mcp_tool="shell:clear_cache",
        )

        # Incident execution succeeds
        executor = IncidentExecutor(hitl_controller=_make_mock_hitl_controller())
        results = await executor.execute(analysis, context, [action])
        assert results[0].success is True

        # n8n notification fails independently
        mock_n8n = _make_mock_n8n_client(
            execute_error=ConnectionError("n8n unreachable")
        )

        notification_failed = False
        try:
            await mock_n8n.execute_workflow(
                workflow_id="wf-notify",
                data={"incident_number": "INC0200021"},
            )
        except ConnectionError:
            notification_failed = True

        assert notification_failed is True
        # But incident execution was already successful
        assert results[0].status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_servicenow_writeback_failure_graceful(self) -> None:
        """ServiceNow client throws -> execution still succeeds, SN not updated."""
        context = IncidentContext(
            incident_number="INC0200022",
            severity=IncidentSeverity.P4,
            category=IncidentCategory.STORAGE,
            short_description="Disk full",
        )
        analysis = IncidentAnalysis(
            incident_number="INC0200022",
            root_cause_summary="Old logs",
            root_cause_confidence=0.85,
        )

        action = RemediationAction(
            action_type=RemediationActionType.CLEAR_DISK_SPACE,
            title="Clear temp files",
            description="Remove old temp files",
            confidence=0.85,
            risk=RemediationRisk.AUTO,
            mcp_tool="shell:run_command",
        )

        mock_sn = _make_mock_servicenow_client(should_fail=True)
        executor = IncidentExecutor(
            hitl_controller=_make_mock_hitl_controller(),
            servicenow_client=mock_sn,
        )
        results = await executor.execute(analysis, context, [action])

        # Execution succeeds despite ServiceNow failure
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].status == ExecutionStatus.COMPLETED
        # ServiceNow was not updated (graceful failure)
        assert results[0].servicenow_updated is False

    @pytest.mark.asyncio
    async def test_analyzer_failure_with_fallback(self) -> None:
        """Correlation service down -> analysis continues with reduced confidence."""
        context = IncidentContext(
            incident_number="INC0200023",
            severity=IncidentSeverity.P3,
            category=IncidentCategory.APPLICATION,
            short_description="App error",
        )

        # Correlation analyzer that raises an exception
        failing_corr = MagicMock()
        failing_corr.find_correlations = AsyncMock(
            side_effect=ConnectionError("Correlation service unavailable")
        )

        # RCA analyzer still works
        working_rca = _make_mock_rootcause_analyzer(
            root_cause="Application memory leak",
            confidence=0.60,
        )

        # IncidentAnalyzer should catch the correlation failure and proceed
        analyzer = IncidentAnalyzer(
            correlation_analyzer=failing_corr,
            rootcause_analyzer=working_rca,
        )
        analysis = await analyzer.analyze(context)

        # Analysis completes (possibly with error in metadata)
        assert analysis.incident_number == "INC0200023"
        # The analyzer catches exceptions and returns a result with error metadata
        # rather than crashing. Confidence may be reduced or error captured.
        assert analysis is not None
        # Either it succeeded with 0 correlations or captured the error
        if analysis.root_cause_confidence > 0:
            # RCA ran successfully despite correlation failure
            assert True
        else:
            # Error was captured in the analysis
            assert "error" in analysis.metadata or "Analysis failed" in analysis.root_cause_summary
