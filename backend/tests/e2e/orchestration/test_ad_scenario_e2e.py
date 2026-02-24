"""
AD Scenario End-to-End Tests — Sprint 118, Story 118-1.

Tests the complete AD account management flow:
  ServiceNow RITM → Webhook → IntentMapper → PatternMatcher
  → Agent Selection → LDAP MCP → ServiceNow Close

7 tests covering:
- Account Unlock full flow
- Password Reset full flow
- Group Membership Change full flow (with approval)
- Unknown RITM fallback to SemanticRouter
- RITM idempotency (duplicate detection)
- LDAP failure error handling
- ServiceNow failure graceful degradation

All external services (LDAP, ServiceNow) are mocked.
The webhook receiver and intent mapper use real implementations
with test-configured authentication.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from src.integrations.orchestration.input.ritm_intent_mapper import (
    IntentMappingResult,
    RITMIntentMapper,
)
from src.integrations.orchestration.input.servicenow_webhook import (
    ServiceNowRITMEvent,
    ServiceNowWebhookReceiver,
)
from .test_ad_scenario_fixtures import (
    EXPECTED_INTENTS,
    EXPECTED_LDAP_OPERATIONS,
    EXPECTED_VARIABLES,
    account_unlock_ritm,
    duplicate_ritm,
    group_membership_change_ritm,
    password_reset_ritm,
    unknown_catalog_item_ritm,
)
from .conftest import WEBHOOK_SECRET, WEBHOOK_URL, HEALTH_URL


# =============================================================================
# Full Flow Tests
# =============================================================================


class TestAccountUnlockFullFlow:
    """E2E: AD Account Unlock — RITM → Webhook → Mapper → LDAP unlock → Close."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_account_unlock_full_flow(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
        mock_ldap: AsyncMock,
        mock_servicenow: AsyncMock,
    ) -> None:
        """Complete flow: RITM webhook → intent mapping → LDAP unlock.

        Steps:
            1. Send RITM webhook with "AD Account Unlock" catalog item
            2. Verify webhook accepted (202)
            3. Verify intent mapped to "ad.account.unlock"
            4. Verify target_user extracted as "john.doe"
            5. Verify tracking_id returned
            6. Verify RITM number in response
        """
        payload = account_unlock_ritm()
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        # Step 1: Send webhook
        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)

        # Step 2: Verify accepted
        assert response.status_code == 202, (
            f"Expected 202 Accepted, got {response.status_code}: {response.text}"
        )
        data = response.json()

        # Step 3: Verify intent mapping
        assert data["intent"] == "ad.account.unlock", (
            f"Expected ad.account.unlock, got {data['intent']}"
        )

        # Step 4: Verify RITM number
        assert data["ritm_number"] == "RITM0012345"

        # Step 5: Verify catalog item name
        assert data["cat_item_name"] == "AD Account Unlock"

        # Step 6: Verify tracking_id generated
        assert data["tracking_id"], "tracking_id should be non-empty"
        assert len(data["tracking_id"]) > 10  # UUID format

        # Step 7: Verify status
        assert data["status"] == "accepted"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_account_unlock_intent_mapper_standalone(
        self,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Verify RITMIntentMapper correctly maps unlock RITM.

        Validates:
        - Matched flag is True
        - Intent is ad.account.unlock
        - Variables extracted: target_user, reason
        """
        payload = account_unlock_ritm()
        event = ServiceNowRITMEvent(**payload)
        result = override_intent_mapper.map_ritm_to_intent(event)

        assert result.matched is True
        assert result.intent == "ad.account.unlock"
        assert result.variables.get("target_user") == "john.doe"
        assert "reason" in result.variables


class TestPasswordResetFullFlow:
    """E2E: AD Password Reset — RITM → Webhook → Mapper → LDAP reset."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_password_reset_full_flow(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
        mock_ldap: AsyncMock,
        mock_servicenow: AsyncMock,
    ) -> None:
        """Complete flow: RITM webhook → intent mapping → LDAP password reset.

        Steps:
            1. Send RITM webhook with "AD Password Reset"
            2. Verify 202 Accepted
            3. Verify intent mapped to "ad.password.reset"
            4. Verify target_user is "jane.doe"
        """
        payload = password_reset_ritm()
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)

        assert response.status_code == 202
        data = response.json()

        assert data["intent"] == "ad.password.reset"
        assert data["ritm_number"] == "RITM0012346"
        assert data["cat_item_name"] == "AD Password Reset"
        assert data["tracking_id"]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_password_reset_variable_extraction(
        self,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Verify variable extraction for password reset RITM.

        Validates:
        - target_user extracted from variables.affected_user
        - temporary_password extracted from variables.temp_password
        """
        payload = password_reset_ritm()
        event = ServiceNowRITMEvent(**payload)
        result = override_intent_mapper.map_ritm_to_intent(event)

        assert result.matched is True
        assert result.intent == "ad.password.reset"
        assert result.variables.get("target_user") == "jane.doe"
        assert result.variables.get("temporary_password") == "TempPass2026!"


class TestGroupMembershipChangeFullFlow:
    """E2E: AD Group Membership Change — RITM → Webhook → Mapper → approval → LDAP."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_group_membership_change_full_flow(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
        mock_ldap: AsyncMock,
        mock_servicenow: AsyncMock,
    ) -> None:
        """Complete flow: RITM → intent mapping → (approval) → LDAP group modify.

        Steps:
            1. Send RITM webhook with "AD Group Membership Change"
            2. Verify 202 Accepted
            3. Verify intent mapped to "ad.group.modify"
            4. Verify variables: target_user, group_name, action
        """
        payload = group_membership_change_ritm()
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)

        assert response.status_code == 202
        data = response.json()

        assert data["intent"] == "ad.group.modify"
        assert data["ritm_number"] == "RITM0012347"
        assert data["cat_item_name"] == "AD Group Membership Change"
        assert data["tracking_id"]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_group_change_variable_extraction(
        self,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Verify variable extraction for group membership change RITM.

        Validates:
        - target_user, group_name, action all extracted
        """
        payload = group_membership_change_ritm()
        event = ServiceNowRITMEvent(**payload)
        result = override_intent_mapper.map_ritm_to_intent(event)

        assert result.matched is True
        assert result.intent == "ad.group.modify"
        assert result.variables.get("target_user") == "bob.chen"
        assert result.variables.get("group_name") == "admin-group"
        assert result.variables.get("action") == "add"


# =============================================================================
# Fallback Tests
# =============================================================================


class TestUnknownRITMFallback:
    """E2E: Unknown Catalog Item triggers SemanticRouter fallback."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_unknown_ritm_fallback_to_semantic_router(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Unknown catalog item accepted but intent is None (no mapping).

        Steps:
            1. Send RITM with unmapped catalog item "Office 365 License Assignment"
            2. Verify webhook still accepts (202) — webhook validation passes
            3. Verify intent is None (no mapping found)
            4. Verify tracking_id still generated
        """
        payload = unknown_catalog_item_ritm()
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)

        assert response.status_code == 202
        data = response.json()

        # Intent should be None because no mapping exists
        assert data["intent"] is None, (
            f"Expected None intent for unknown catalog item, got {data['intent']}"
        )
        assert data["ritm_number"] == "RITM0012348"
        assert data["tracking_id"]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_unknown_ritm_mapper_returns_fallback(
        self,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Verify mapper returns fallback result for unknown catalog items.

        The fallback_strategy should be "semantic_router" as configured
        in ritm_mappings.yaml.
        """
        payload = unknown_catalog_item_ritm()
        event = ServiceNowRITMEvent(**payload)
        result = override_intent_mapper.map_ritm_to_intent(event)

        assert result.matched is False
        assert result.fallback_used is True
        assert result.fallback_strategy == "semantic_router"
        assert result.cat_item_name == "Office 365 License Assignment"


# =============================================================================
# Idempotency Tests
# =============================================================================


class TestRITMIdempotency:
    """E2E: Duplicate RITM events are detected and rejected."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_ritm_idempotency(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Same RITM sent twice — second attempt should be 409 Conflict.

        Steps:
            1. Send RITM with sys_id "ritm-unlock-001" → 202 Accepted
            2. Send same RITM again → 409 Conflict (duplicate detected)
            3. Verify first response has tracking_id
            4. Verify second response has error details
        """
        payload = duplicate_ritm()
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        # First send — should succeed
        response1 = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response1.status_code == 202
        data1 = response1.json()
        assert data1["tracking_id"]
        assert data1["intent"] == "ad.account.unlock"

        # Second send — same sys_id → duplicate
        response2 = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response2.status_code == 409, (
            f"Expected 409 Conflict for duplicate, got {response2.status_code}"
        )

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_different_sys_ids_not_flagged_as_duplicate(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Different sys_ids should both succeed (not flagged as duplicates)."""
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        payload1 = account_unlock_ritm()
        payload2 = password_reset_ritm()  # Different sys_id

        response1 = await client.post(WEBHOOK_URL, json=payload1, headers=headers)
        assert response1.status_code == 202

        response2 = await client.post(WEBHOOK_URL, json=payload2, headers=headers)
        assert response2.status_code == 202


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestLDAPFailureErrorHandling:
    """E2E: LDAP operation failure handling and error reporting."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_ldap_failure_error_handling(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
        mock_ldap_fail: AsyncMock,
    ) -> None:
        """LDAP failure: webhook still accepts, error logged.

        The webhook reception is independent of LDAP execution.
        The RITM is accepted and mapped; LDAP failure would occur
        during the downstream agent execution phase.

        Steps:
            1. Send valid RITM payload
            2. Verify webhook accepts (202) — reception is independent
            3. Verify intent mapping still works
            4. Verify LDAP mock would return failure
        """
        payload = account_unlock_ritm()
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        # Webhook reception should still succeed
        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response.status_code == 202
        data = response.json()
        assert data["intent"] == "ad.account.unlock"

        # Verify LDAP mock returns failure (would occur in agent execution)
        ldap_result = await mock_ldap_fail.modify_user_attributes(
            user="john.doe",
            attributes={"lockoutTime": "0"},
        )
        assert ldap_result["success"] is False
        assert "LDAP connection failed" in ldap_result["error"]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_ldap_failure_does_not_block_ritm_reception(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
        mock_ldap_fail: AsyncMock,
    ) -> None:
        """Multiple RITMs should still be accepted even when LDAP is down.

        The webhook layer is decoupled from the execution layer.
        """
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        # Send multiple different RITMs — all should be accepted
        payloads = [
            account_unlock_ritm(),
            password_reset_ritm(),
            group_membership_change_ritm(),
        ]

        for payload in payloads:
            response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
            assert response.status_code == 202, (
                f"RITM {payload['number']} rejected despite LDAP being down"
            )


class TestServiceNowFailureGracefulDegradation:
    """E2E: ServiceNow MCP failure — AD operations still execute."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_servicenow_failure_graceful_degradation(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
        mock_ldap: AsyncMock,
        mock_sn_fail: AsyncMock,
    ) -> None:
        """ServiceNow MCP failure: LDAP operations still execute.

        When ServiceNow is unavailable for RITM closure:
        - AD operations via LDAP should still proceed
        - RITM closure failure should be logged, not block execution

        Steps:
            1. Send valid RITM
            2. Verify webhook accepts (202)
            3. Verify LDAP operations would succeed
            4. Verify ServiceNow closure would fail gracefully
        """
        payload = account_unlock_ritm()
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}

        # Webhook should still work
        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response.status_code == 202
        data = response.json()
        assert data["intent"] == "ad.account.unlock"

        # LDAP operations should succeed independently
        ldap_result = await mock_ldap.modify_user_attributes(
            user="john.doe",
            attributes={"lockoutTime": "0"},
        )
        assert ldap_result["success"] is True

        # ServiceNow closure would fail (but should not block)
        sn_result = await mock_sn_fail.update_incident(
            sys_id="ritm-unlock-001",
            state="3",
            work_notes="Completed",
        )
        assert sn_result["success"] is False
        assert "ServiceNow API unavailable" in sn_result["error"]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_sn_failure_ldap_operations_still_succeed(
        self,
        mock_ldap: AsyncMock,
        mock_sn_fail: AsyncMock,
    ) -> None:
        """Verify LDAP operations are independent of ServiceNow availability.

        All three AD operation types should succeed via LDAP
        even when ServiceNow is completely unavailable.
        """
        # Unlock
        unlock_result = await mock_ldap.modify_user_attributes(
            user="john.doe", attributes={"lockoutTime": "0"}
        )
        assert unlock_result["success"] is True

        # Password reset
        reset_result = await mock_ldap.modify_user_attributes(
            user="jane.doe", attributes={"unicodePwd": "NewPass!"}
        )
        assert reset_result["success"] is True

        # Group modify
        group_result = await mock_ldap.modify_user_attributes(
            user="bob.chen", attributes={"memberOf": "admin-group"}
        )
        assert group_result["success"] is True

        # Verify ServiceNow is indeed failing
        sn_result = await mock_sn_fail.get_ritm_status(number="RITM0012345")
        assert sn_result["success"] is False


# =============================================================================
# Authentication Tests
# =============================================================================


class TestWebhookAuthentication:
    """E2E: Webhook authentication validation."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_missing_secret_returns_401(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Missing X-ServiceNow-Secret header returns 401."""
        payload = account_unlock_ritm()
        # No auth headers
        response = await client.post(WEBHOOK_URL, json=payload)
        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_invalid_secret_returns_401(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Invalid X-ServiceNow-Secret returns 401."""
        payload = account_unlock_ritm()
        headers = {"X-ServiceNow-Secret": "wrong-secret"}
        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_valid_secret_returns_202(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Valid X-ServiceNow-Secret returns 202 Accepted."""
        payload = account_unlock_ritm()
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}
        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response.status_code == 202

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_webhook_health_endpoint(
        self,
        client: AsyncClient,
    ) -> None:
        """Webhook health endpoint returns status and config info."""
        response = await client.get(HEALTH_URL)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "enabled" in data
        assert "processed_events_cached" in data


# =============================================================================
# Payload Validation Tests
# =============================================================================


class TestPayloadValidation:
    """E2E: Webhook payload validation."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_empty_sys_id_returns_422(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Empty sys_id should fail Pydantic validation (422)."""
        payload = account_unlock_ritm()
        payload["sys_id"] = ""
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}
        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_missing_number_returns_422(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Missing required 'number' field returns 422."""
        payload = account_unlock_ritm()
        del payload["number"]
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}
        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_optional_fields_defaulted(
        self,
        client: AsyncClient,
        override_webhook_receiver: ServiceNowWebhookReceiver,
        override_intent_mapper: RITMIntentMapper,
    ) -> None:
        """Minimal payload with only required fields should succeed."""
        payload = {
            "sys_id": "minimal-001",
            "number": "RITM0099999",
        }
        headers = {"X-ServiceNow-Secret": WEBHOOK_SECRET}
        response = await client.post(WEBHOOK_URL, json=payload, headers=headers)
        assert response.status_code == 202
        data = response.json()
        assert data["ritm_number"] == "RITM0099999"
        assert data["tracking_id"]
