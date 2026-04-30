"""
IT Incident Handler — ServiceNow INC Webhook Input Processor.

Sprint 126: Story 126-1 — Receives ServiceNow Incident (INC) webhook events,
normalizes them into RoutingRequest format, and classifies incident subcategory.

Implements InputProcessorProtocol from L4a contracts.
"""

import logging
import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ..contracts import InputSource, RoutingRequest
from .contracts import InputProcessorProtocol

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class IncidentSubCategory(str, Enum):
    """IT Incident sub-categories for PatternMatcher routing.

    Based on ITIL incident categorization:
        NETWORK: Network device/connectivity issues
        SERVER: Server hardware/OS issues
        APPLICATION: Application crashes/errors
        DATABASE: Database service issues
        SECURITY: Security events/breaches
        STORAGE: Disk space/storage issues
        PERFORMANCE: Performance degradation
        AUTHENTICATION: Login/AD account issues
        OTHER: Uncategorized incidents
    """

    NETWORK = "network"
    SERVER = "server"
    APPLICATION = "application"
    DATABASE = "database"
    SECURITY = "security"
    STORAGE = "storage"
    PERFORMANCE = "performance"
    AUTHENTICATION = "authentication"
    OTHER = "other"


# =============================================================================
# ServiceNow INC Event Model
# =============================================================================


class ServiceNowINCEvent(BaseModel):
    """ServiceNow Incident (INC) Webhook Payload.

    Represents an Incident record event from ServiceNow.

    Attributes:
        sys_id: ServiceNow unique record identifier
        number: INC number (e.g., INC0012345)
        state: Incident state code ("1"=New, "2"=InProgress, "3"=OnHold, "6"=Resolved, "7"=Closed)
        impact: Impact level ("1"=High, "2"=Medium, "3"=Low)
        urgency: Urgency level ("1"=High, "2"=Medium, "3"=Low)
        priority: Calculated priority ("1"=Critical, "2"=High, "3"=Moderate, "4"=Low)
        category: ServiceNow category (e.g., "Hardware", "Software", "Network")
        subcategory: ServiceNow subcategory
        short_description: Brief incident description
        description: Full incident description
        cmdb_ci: Configuration Item display value
        business_service: Business Service display value
        caller_id: Reporting user display value
        assignment_group: Assignment group display value
        work_notes: Latest work notes
        sys_created_on: Record creation timestamp
        sys_updated_on: Record update timestamp
    """

    sys_id: str = Field(..., min_length=1, max_length=64)
    number: str = Field(..., min_length=1, max_length=32)
    state: str = Field(default="1")
    impact: str = Field(default="2")
    urgency: str = Field(default="2")
    priority: str = Field(default="3")
    category: str = Field(default="")
    subcategory: str = Field(default="")
    short_description: str = Field(default="")
    description: Optional[str] = None
    cmdb_ci: str = Field(default="")
    business_service: str = Field(default="")
    caller_id: str = Field(default="")
    assignment_group: Optional[str] = None
    work_notes: Optional[str] = None
    sys_created_on: Optional[str] = None
    sys_updated_on: Optional[str] = None

    @field_validator("sys_id")
    @classmethod
    def validate_sys_id(cls, v: str) -> str:
        """Validate sys_id is not empty."""
        if not v.strip():
            raise ValueError("sys_id cannot be empty")
        return v.strip()

    @field_validator("number")
    @classmethod
    def validate_number(cls, v: str) -> str:
        """Validate INC number format."""
        if not v.strip():
            raise ValueError("number cannot be empty")
        return v.strip()


# =============================================================================
# Priority / Risk Level Mapping
# =============================================================================

# ServiceNow Priority to IPA RiskLevel string mapping
_PRIORITY_TO_RISK: Dict[str, str] = {
    "1": "critical",  # P1 Critical
    "2": "high",  # P2 High
    "3": "medium",  # P3 Moderate
    "4": "low",  # P4 Low
}

# Priority to numeric value for RoutingRequest.priority
_PRIORITY_TO_INT: Dict[str, int] = {
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
}


# =============================================================================
# Category Classification Patterns
# =============================================================================

# ServiceNow category to IncidentSubCategory mapping
_CATEGORY_MAP: Dict[str, IncidentSubCategory] = {
    "network": IncidentSubCategory.NETWORK,
    "hardware": IncidentSubCategory.SERVER,
    "software": IncidentSubCategory.APPLICATION,
    "database": IncidentSubCategory.DATABASE,
    "security": IncidentSubCategory.SECURITY,
    "storage": IncidentSubCategory.STORAGE,
    "performance": IncidentSubCategory.PERFORMANCE,
    "authentication": IncidentSubCategory.AUTHENTICATION,
    "login": IncidentSubCategory.AUTHENTICATION,
    "access": IncidentSubCategory.AUTHENTICATION,
}

# Regex-based fallback classification patterns
_CLASSIFICATION_PATTERNS: List[tuple] = [
    # Network patterns
    (
        re.compile(
            r"(switch|router|firewall|dns|dhcp|vpn|vlan|bandwidth|latency|"
            r"packet.loss|connectivity|network.down|port.*down|link.*down|"
            r"交換機|路由器|防火牆|網路)", re.IGNORECASE
        ),
        IncidentSubCategory.NETWORK,
    ),
    # Server patterns
    (
        re.compile(
            r"(server.*down|cpu.*high|memory.*full|disk.*fail|hardware|"
            r"reboot|crash|kernel.panic|out.of.memory|oom|vm.*unresponsive|"
            r"伺服器|主機)", re.IGNORECASE
        ),
        IncidentSubCategory.SERVER,
    ),
    # Application patterns
    (
        re.compile(
            r"(application.*error|app.*crash|service.*unavailable|"
            r"500.error|timeout|exception|null.pointer|stack.trace|"
            r"deployment.fail|應用程式|服務中斷)", re.IGNORECASE
        ),
        IncidentSubCategory.APPLICATION,
    ),
    # Database patterns
    (
        re.compile(
            r"(database|db.*down|sql.*error|connection.pool|deadlock|"
            r"replication.*lag|backup.*fail|table.*lock|資料庫)", re.IGNORECASE
        ),
        IncidentSubCategory.DATABASE,
    ),
    # Security patterns
    (
        re.compile(
            r"(security|breach|malware|virus|unauthorized|intrusion|"
            r"suspicious|phishing|ransomware|vulnerability|安全|入侵)", re.IGNORECASE
        ),
        IncidentSubCategory.SECURITY,
    ),
    # Storage patterns
    (
        re.compile(
            r"(disk.*full|storage.*capacity|quota.*exceeded|"
            r"磁碟.*滿|space.*low|volume.*full|nas|san|"
            r"磁碟空間|儲存)", re.IGNORECASE
        ),
        IncidentSubCategory.STORAGE,
    ),
    # Performance patterns
    (
        re.compile(
            r"(slow|performance|degradation|high.load|response.time|"
            r"latency|bottleneck|throttle|效能|緩慢)", re.IGNORECASE
        ),
        IncidentSubCategory.PERFORMANCE,
    ),
    # Authentication patterns
    (
        re.compile(
            r"(login.*fail|account.*lock|password.*reset|ad.*account|"
            r"ldap|sso|mfa|authentication|authorization|"
            r"登入|帳號.*鎖|密碼)", re.IGNORECASE
        ),
        IncidentSubCategory.AUTHENTICATION,
    ),
]


# =============================================================================
# Incident Handler
# =============================================================================


class IncidentHandler(InputProcessorProtocol):
    """ServiceNow Incident webhook input processor.

    Implements InputProcessorProtocol to:
        1. Parse ServiceNow INC webhook payloads
        2. Map priority to risk level
        3. Classify incident subcategory
        4. Build RoutingRequest for the intent routing system

    Example:
        >>> handler = IncidentHandler()
        >>> if handler.can_handle(raw_payload):
        ...     routing_request = await handler.process(raw_payload)
        ...     print(routing_request.intent_hint)  # "incident"
    """

    async def process(self, raw_input: Any) -> RoutingRequest:
        """Process a ServiceNow INC webhook payload.

        Args:
            raw_input: Raw payload (dict or ServiceNowINCEvent)

        Returns:
            Normalized RoutingRequest for the intent routing system

        Raises:
            ValueError: If payload is invalid
        """
        # Parse event
        event = self._parse_event(raw_input)

        # Map priority to risk level
        risk_level = self._map_priority_to_risk(event.priority)

        # Classify subcategory
        subcategory = self._classify_subcategory(event)

        # Build routing request
        routing_request = self._build_routing_request(
            event, risk_level, subcategory
        )

        logger.info(
            f"Incident processed: {event.number} → "
            f"risk={risk_level}, subcategory={subcategory.value}, "
            f"priority={event.priority}"
        )

        return routing_request

    def can_handle(self, raw_input: Any) -> bool:
        """Check if this processor can handle the input.

        Detects ServiceNow INC payloads by checking for 'number' field
        with INC prefix, or 'sys_id' with incident markers.

        Args:
            raw_input: Raw input to check

        Returns:
            True if input looks like a ServiceNow INC event
        """
        if isinstance(raw_input, ServiceNowINCEvent):
            return True

        if isinstance(raw_input, dict):
            number = raw_input.get("number", "")
            if isinstance(number, str) and number.upper().startswith("INC"):
                return True
            # Also check for sys_id + incident-like fields
            if "sys_id" in raw_input and "priority" in raw_input:
                category = raw_input.get("category", "")
                short_desc = raw_input.get("short_description", "")
                if category or short_desc:
                    return True

        return False

    def get_source_type(self) -> InputSource:
        """Return the input source type.

        Returns:
            InputSource.WEBHOOK_SERVICENOW
        """
        return InputSource.WEBHOOK_SERVICENOW

    def _parse_event(self, raw_input: Any) -> ServiceNowINCEvent:
        """Parse raw input into ServiceNowINCEvent.

        Args:
            raw_input: Dict or ServiceNowINCEvent

        Returns:
            Validated ServiceNowINCEvent

        Raises:
            ValueError: If parsing fails
        """
        if isinstance(raw_input, ServiceNowINCEvent):
            return raw_input

        if isinstance(raw_input, dict):
            try:
                return ServiceNowINCEvent(**raw_input)
            except Exception as e:
                raise ValueError(f"Invalid INC payload: {e}")

        raise ValueError(
            f"Expected dict or ServiceNowINCEvent, got {type(raw_input).__name__}"
        )

    def _map_priority_to_risk(self, priority: str) -> str:
        """Map ServiceNow priority to IPA risk level.

        Args:
            priority: ServiceNow priority ("1"=Critical, "2"=High, "3"=Moderate, "4"=Low)

        Returns:
            Risk level string ("critical", "high", "medium", "low")
        """
        return _PRIORITY_TO_RISK.get(str(priority).strip(), "medium")

    def _classify_subcategory(self, event: ServiceNowINCEvent) -> IncidentSubCategory:
        """Classify incident into a subcategory.

        Uses two-stage classification:
            1. Direct mapping from ServiceNow category field
            2. Regex-based classification from short_description/description

        Args:
            event: ServiceNow INC event

        Returns:
            Classified IncidentSubCategory
        """
        # Stage 1: Category field mapping
        category_lower = event.category.strip().lower()
        if category_lower in _CATEGORY_MAP:
            return _CATEGORY_MAP[category_lower]

        # Also check subcategory field
        subcategory_lower = event.subcategory.strip().lower()
        if subcategory_lower in _CATEGORY_MAP:
            return _CATEGORY_MAP[subcategory_lower]

        # Stage 2: Regex-based classification from description
        search_text = f"{event.short_description} {event.description or ''}"
        for pattern, sub_cat in _CLASSIFICATION_PATTERNS:
            if pattern.search(search_text):
                return sub_cat

        return IncidentSubCategory.OTHER

    def _build_routing_request(
        self,
        event: ServiceNowINCEvent,
        risk_level: str,
        subcategory: IncidentSubCategory,
    ) -> RoutingRequest:
        """Build a RoutingRequest from parsed INC event.

        Args:
            event: Parsed INC event
            risk_level: Mapped risk level string
            subcategory: Classified subcategory

        Returns:
            RoutingRequest ready for the intent routing system
        """
        # Build query from description
        query = event.short_description
        if event.description:
            query = f"{event.short_description}. {event.description}"

        # Parse timestamp
        timestamp = datetime.utcnow()
        if event.sys_created_on:
            try:
                timestamp = datetime.fromisoformat(
                    event.sys_created_on.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return RoutingRequest(
            query=query,
            intent_hint="incident",
            context={
                "incident_number": event.number,
                "sys_id": event.sys_id,
                "state": event.state,
                "impact": event.impact,
                "urgency": event.urgency,
                "priority": event.priority,
                "category": event.category,
                "subcategory": subcategory.value,
                "cmdb_ci": event.cmdb_ci,
                "business_service": event.business_service,
                "caller_id": event.caller_id,
                "assignment_group": event.assignment_group or "",
                "risk_level": risk_level,
            },
            source=InputSource.WEBHOOK_SERVICENOW,
            request_id=str(uuid.uuid4()),
            timestamp=timestamp,
            metadata={
                "source_type": "servicenow_incident",
                "incident_number": event.number,
                "servicenow_sys_id": event.sys_id,
                "subcategory": subcategory.value,
            },
            priority=_PRIORITY_TO_INT.get(str(event.priority).strip(), 3),
        )
