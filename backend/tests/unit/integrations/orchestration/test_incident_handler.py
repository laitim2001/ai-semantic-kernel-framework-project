"""
Unit Tests for IncidentHandler (ServiceNow INC Webhook Input Processor).

Sprint 126: Story 126-4 — IT Incident Processing (Phase 34)
Tests INC event parsing, priority mapping, subcategory classification,
can_handle detection, and RoutingRequest building.
"""

import pytest

from src.integrations.orchestration.input.incident_handler import (
    IncidentHandler,
    IncidentSubCategory,
    ServiceNowINCEvent,
    _CATEGORY_MAP,
    _PRIORITY_TO_RISK,
)
from src.integrations.orchestration.contracts import InputSource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def handler() -> IncidentHandler:
    """Create IncidentHandler instance."""
    return IncidentHandler()


@pytest.fixture
def valid_inc_payload() -> dict:
    """Create valid ServiceNow INC event payload."""
    return {
        "sys_id": "abc123def456",
        "number": "INC0012345",
        "state": "1",
        "impact": "2",
        "urgency": "2",
        "priority": "2",
        "category": "Network",
        "subcategory": "Switch",
        "short_description": "Core switch failure causing VLAN outage",
        "description": "Switch core-sw-01 port Gi0/1 flapping on VLAN 100",
        "cmdb_ci": "core-sw-01",
        "business_service": "ERP System",
        "caller_id": "john.doe",
        "assignment_group": "Network Operations",
        "sys_created_on": "2026-02-25T08:30:00Z",
    }


@pytest.fixture
def minimal_inc_payload() -> dict:
    """Create minimal valid INC payload."""
    return {
        "sys_id": "min123",
        "number": "INC0099999",
    }


# ---------------------------------------------------------------------------
# ServiceNowINCEvent Model Tests
# ---------------------------------------------------------------------------


class TestServiceNowINCEvent:
    """Tests for ServiceNowINCEvent Pydantic model."""

    def test_valid_event(self, valid_inc_payload: dict) -> None:
        """Test creating valid INC event from payload."""
        event = ServiceNowINCEvent(**valid_inc_payload)
        assert event.sys_id == "abc123def456"
        assert event.number == "INC0012345"
        assert event.priority == "2"
        assert event.category == "Network"
        assert event.short_description == "Core switch failure causing VLAN outage"

    def test_minimal_event(self, minimal_inc_payload: dict) -> None:
        """Test creating event with only required fields."""
        event = ServiceNowINCEvent(**minimal_inc_payload)
        assert event.sys_id == "min123"
        assert event.number == "INC0099999"
        assert event.state == "1"  # default
        assert event.priority == "3"  # default

    def test_empty_sys_id_rejected(self) -> None:
        """Test that empty sys_id is rejected."""
        with pytest.raises(Exception):
            ServiceNowINCEvent(sys_id="", number="INC001")

    def test_whitespace_sys_id_rejected(self) -> None:
        """Test that whitespace-only sys_id is rejected."""
        with pytest.raises(Exception):
            ServiceNowINCEvent(sys_id="   ", number="INC001")

    def test_empty_number_rejected(self) -> None:
        """Test that empty number is rejected."""
        with pytest.raises(Exception):
            ServiceNowINCEvent(sys_id="abc123", number="")

    def test_sys_id_trimmed(self) -> None:
        """Test that sys_id is trimmed."""
        event = ServiceNowINCEvent(sys_id="  abc123  ", number="INC001")
        assert event.sys_id == "abc123"


# ---------------------------------------------------------------------------
# can_handle Tests
# ---------------------------------------------------------------------------


class TestCanHandle:
    """Tests for IncidentHandler.can_handle()."""

    def test_can_handle_inc_prefix(self, handler: IncidentHandler) -> None:
        """Test can_handle detects INC-prefixed numbers."""
        assert handler.can_handle({"number": "INC0012345", "sys_id": "abc"}) is True

    def test_can_handle_inc_lowercase(self, handler: IncidentHandler) -> None:
        """Test can_handle detects lowercase inc prefix."""
        assert handler.can_handle({"number": "inc0012345", "sys_id": "abc"}) is True

    def test_cannot_handle_ritm(self, handler: IncidentHandler) -> None:
        """Test can_handle rejects RITM-prefixed numbers."""
        assert handler.can_handle({"number": "RITM0012345"}) is False

    def test_can_handle_inc_event_object(
        self, handler: IncidentHandler, valid_inc_payload: dict
    ) -> None:
        """Test can_handle accepts ServiceNowINCEvent objects."""
        event = ServiceNowINCEvent(**valid_inc_payload)
        assert handler.can_handle(event) is True

    def test_can_handle_sys_id_with_priority(self, handler: IncidentHandler) -> None:
        """Test can_handle detects sys_id + priority combo."""
        payload = {
            "sys_id": "abc123",
            "priority": "2",
            "short_description": "Some issue",
        }
        assert handler.can_handle(payload) is True

    def test_cannot_handle_string(self, handler: IncidentHandler) -> None:
        """Test can_handle rejects string input."""
        assert handler.can_handle("INC0012345") is False

    def test_cannot_handle_empty_dict(self, handler: IncidentHandler) -> None:
        """Test can_handle rejects empty dict."""
        assert handler.can_handle({}) is False


# ---------------------------------------------------------------------------
# Priority Mapping Tests
# ---------------------------------------------------------------------------


class TestPriorityMapping:
    """Tests for priority to risk level mapping."""

    def test_p1_maps_to_critical(self, handler: IncidentHandler) -> None:
        """Test P1 maps to critical risk."""
        assert handler._map_priority_to_risk("1") == "critical"

    def test_p2_maps_to_high(self, handler: IncidentHandler) -> None:
        """Test P2 maps to high risk."""
        assert handler._map_priority_to_risk("2") == "high"

    def test_p3_maps_to_medium(self, handler: IncidentHandler) -> None:
        """Test P3 maps to medium risk."""
        assert handler._map_priority_to_risk("3") == "medium"

    def test_p4_maps_to_low(self, handler: IncidentHandler) -> None:
        """Test P4 maps to low risk."""
        assert handler._map_priority_to_risk("4") == "low"

    def test_unknown_priority_defaults_to_medium(self, handler: IncidentHandler) -> None:
        """Test unknown priority defaults to medium."""
        assert handler._map_priority_to_risk("5") == "medium"
        assert handler._map_priority_to_risk("unknown") == "medium"


# ---------------------------------------------------------------------------
# Subcategory Classification Tests
# ---------------------------------------------------------------------------


class TestSubcategoryClassification:
    """Tests for incident subcategory classification."""

    def test_classify_from_category_field(self, handler: IncidentHandler) -> None:
        """Test classification from ServiceNow category field."""
        event = ServiceNowINCEvent(
            sys_id="abc", number="INC001", category="network"
        )
        result = handler._classify_subcategory(event)
        assert result == IncidentSubCategory.NETWORK

    def test_classify_from_subcategory_field(self, handler: IncidentHandler) -> None:
        """Test classification from ServiceNow subcategory field."""
        event = ServiceNowINCEvent(
            sys_id="abc", number="INC001", category="", subcategory="database"
        )
        result = handler._classify_subcategory(event)
        assert result == IncidentSubCategory.DATABASE

    def test_classify_from_description_network(self, handler: IncidentHandler) -> None:
        """Test regex classification from description (network)."""
        event = ServiceNowINCEvent(
            sys_id="abc", number="INC001",
            short_description="Switch failure on core-sw-01",
        )
        result = handler._classify_subcategory(event)
        assert result == IncidentSubCategory.NETWORK

    def test_classify_from_description_server(self, handler: IncidentHandler) -> None:
        """Test regex classification from description (server)."""
        event = ServiceNowINCEvent(
            sys_id="abc", number="INC001",
            short_description="Server crash and kernel panic on srv-01",
        )
        result = handler._classify_subcategory(event)
        assert result == IncidentSubCategory.SERVER

    def test_classify_from_description_security(self, handler: IncidentHandler) -> None:
        """Test regex classification from description (security)."""
        event = ServiceNowINCEvent(
            sys_id="abc", number="INC001",
            short_description="Unauthorized access detected on web server",
        )
        result = handler._classify_subcategory(event)
        assert result == IncidentSubCategory.SECURITY

    def test_classify_from_chinese_description(self, handler: IncidentHandler) -> None:
        """Test regex classification from Chinese description."""
        event = ServiceNowINCEvent(
            sys_id="abc", number="INC001",
            short_description="伺服器當機無法回應",
        )
        result = handler._classify_subcategory(event)
        assert result == IncidentSubCategory.SERVER

    def test_classify_defaults_to_other(self, handler: IncidentHandler) -> None:
        """Test unclassifiable incidents default to OTHER."""
        event = ServiceNowINCEvent(
            sys_id="abc", number="INC001",
            short_description="General issue needs investigation",
        )
        result = handler._classify_subcategory(event)
        assert result == IncidentSubCategory.OTHER


# ---------------------------------------------------------------------------
# process() Tests
# ---------------------------------------------------------------------------


class TestProcess:
    """Tests for IncidentHandler.process()."""

    @pytest.mark.asyncio
    async def test_process_valid_payload(
        self, handler: IncidentHandler, valid_inc_payload: dict
    ) -> None:
        """Test processing valid INC payload returns RoutingRequest."""
        result = await handler.process(valid_inc_payload)
        assert result.intent_hint == "incident"
        assert result.source == InputSource.WEBHOOK_SERVICENOW
        assert result.context["incident_number"] == "INC0012345"
        assert result.context["risk_level"] == "high"  # priority 2 → high

    @pytest.mark.asyncio
    async def test_process_sets_priority(
        self, handler: IncidentHandler, valid_inc_payload: dict
    ) -> None:
        """Test process sets correct numeric priority."""
        result = await handler.process(valid_inc_payload)
        assert result.priority == 2  # P2

    @pytest.mark.asyncio
    async def test_process_classifies_subcategory(
        self, handler: IncidentHandler, valid_inc_payload: dict
    ) -> None:
        """Test process classifies incident subcategory."""
        result = await handler.process(valid_inc_payload)
        assert result.context["subcategory"] == "network"

    @pytest.mark.asyncio
    async def test_process_builds_query(
        self, handler: IncidentHandler, valid_inc_payload: dict
    ) -> None:
        """Test process builds query from short_description + description."""
        result = await handler.process(valid_inc_payload)
        assert "Core switch failure" in result.query
        assert "Switch core-sw-01" in result.query

    @pytest.mark.asyncio
    async def test_process_generates_request_id(
        self, handler: IncidentHandler, valid_inc_payload: dict
    ) -> None:
        """Test process generates unique request_id."""
        result = await handler.process(valid_inc_payload)
        assert result.request_id is not None
        assert len(result.request_id) > 0

    @pytest.mark.asyncio
    async def test_process_invalid_payload_raises(
        self, handler: IncidentHandler
    ) -> None:
        """Test process raises ValueError for invalid payload."""
        with pytest.raises(ValueError, match="Invalid INC payload"):
            await handler.process({"bad": "data"})

    @pytest.mark.asyncio
    async def test_process_string_input_raises(
        self, handler: IncidentHandler
    ) -> None:
        """Test process raises ValueError for string input."""
        with pytest.raises(ValueError, match="Expected dict or ServiceNowINCEvent"):
            await handler.process("not a dict")

    @pytest.mark.asyncio
    async def test_process_accepts_event_object(
        self, handler: IncidentHandler, valid_inc_payload: dict
    ) -> None:
        """Test process accepts ServiceNowINCEvent directly."""
        event = ServiceNowINCEvent(**valid_inc_payload)
        result = await handler.process(event)
        assert result.intent_hint == "incident"
        assert result.context["incident_number"] == "INC0012345"

    def test_get_source_type(self, handler: IncidentHandler) -> None:
        """Test get_source_type returns WEBHOOK_SERVICENOW."""
        assert handler.get_source_type() == InputSource.WEBHOOK_SERVICENOW
