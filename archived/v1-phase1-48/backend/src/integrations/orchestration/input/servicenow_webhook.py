"""
ServiceNow Webhook Receiver.

Sprint 114: AD 場景基礎建設 (Phase 32)
Receives and processes ServiceNow RITM (Requested Item) webhook events.

Features:
    - Shared secret authentication
    - IP whitelist validation
    - RITM payload parsing and validation
    - Idempotent event processing (duplicate detection)
    - Structured logging for audit trail
"""

import hashlib
import hmac
import ipaddress
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ServiceNowRITMEvent(BaseModel):
    """ServiceNow RITM Webhook Payload.

    Represents a Requested Item event from ServiceNow.

    Attributes:
        sys_id: ServiceNow unique record identifier
        number: RITM number (e.g., RITM0012345)
        state: RITM state code ("1"=Open, "2"=WIP, "3"=Closed Complete, etc.)
        cat_item: Catalog Item sys_id
        cat_item_name: Catalog Item display name (e.g., "AD Account Unlock")
        requested_for: User the request is for
        requested_by: User who submitted the request
        short_description: Brief description of the request
        description: Detailed description (optional)
        variables: Form variables from the catalog item
        priority: Priority level ("1"=Critical, "2"=High, "3"=Medium, "4"=Low)
        assignment_group: Assigned support group
        sys_created_on: Record creation timestamp
    """

    sys_id: str = Field(..., min_length=1, max_length=64)
    number: str = Field(..., min_length=1, max_length=32)
    state: str = Field(default="1")
    cat_item: str = Field(default="")
    cat_item_name: str = Field(default="")
    requested_for: str = Field(default="")
    requested_by: str = Field(default="")
    short_description: str = Field(default="")
    description: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(default="3")
    assignment_group: Optional[str] = None
    sys_created_on: Optional[str] = None

    @field_validator("sys_id")
    @classmethod
    def validate_sys_id(cls, v: str) -> str:
        """Validate sys_id is not empty."""
        if not v.strip():
            raise ValueError("sys_id cannot be empty")
        return v.strip()


class WebhookAuthConfig(BaseModel):
    """Webhook authentication configuration.

    Attributes:
        auth_type: Authentication method (shared_secret, hmac_sha256)
        shared_secret: Shared secret for request validation
        allowed_ips: List of allowed IP addresses/CIDRs
        enabled: Whether webhook is enabled
    """

    auth_type: str = Field(default="shared_secret")
    shared_secret: Optional[str] = None
    allowed_ips: List[str] = Field(default_factory=list)
    enabled: bool = True


class WebhookValidationError(Exception):
    """Raised when webhook request validation fails."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Webhook Receiver
# ---------------------------------------------------------------------------


class ServiceNowWebhookReceiver:
    """ServiceNow Webhook event receiver.

    Handles incoming webhook requests from ServiceNow,
    validates authentication, parses RITM events, and ensures
    idempotent processing.

    Attributes:
        _auth_config: Authentication configuration
        _processed_events: Set of processed event sys_ids for idempotency
        _max_cache_size: Maximum number of cached event IDs
    """

    MAX_CACHE_SIZE = 10000

    def __init__(self, auth_config: WebhookAuthConfig) -> None:
        """Initialize the webhook receiver.

        Args:
            auth_config: Authentication and security configuration
        """
        self._auth_config = auth_config
        self._processed_events: Set[str] = set()
        self._event_timestamps: Dict[str, float] = {}

    def validate_shared_secret(
        self,
        provided_secret: Optional[str],
    ) -> bool:
        """Validate the shared secret from request header.

        Args:
            provided_secret: Secret from X-ServiceNow-Secret header

        Returns:
            True if secret matches

        Raises:
            WebhookValidationError: If validation fails
        """
        if not self._auth_config.shared_secret:
            logger.warning("No shared secret configured, skipping validation")
            return True

        if not provided_secret:
            raise WebhookValidationError(
                "Missing X-ServiceNow-Secret header", status_code=401
            )

        if not hmac.compare_digest(
            provided_secret, self._auth_config.shared_secret
        ):
            raise WebhookValidationError(
                "Invalid shared secret", status_code=401
            )

        return True

    def validate_hmac(
        self,
        body: bytes,
        signature: Optional[str],
    ) -> bool:
        """Validate HMAC-SHA256 signature of request body.

        Args:
            body: Raw request body bytes
            signature: HMAC signature from header

        Returns:
            True if signature is valid

        Raises:
            WebhookValidationError: If validation fails
        """
        if not self._auth_config.shared_secret:
            return True

        if not signature:
            raise WebhookValidationError(
                "Missing HMAC signature header", status_code=401
            )

        expected = hmac.new(
            self._auth_config.shared_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            raise WebhookValidationError(
                "Invalid HMAC signature", status_code=401
            )

        return True

    def validate_ip(self, client_ip: str) -> bool:
        """Validate client IP against whitelist.

        Args:
            client_ip: Client's IP address

        Returns:
            True if IP is allowed

        Raises:
            WebhookValidationError: If IP is not allowed
        """
        if not self._auth_config.allowed_ips:
            return True

        client_addr = ipaddress.ip_address(client_ip)

        for allowed in self._auth_config.allowed_ips:
            try:
                if "/" in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if client_addr in network:
                        return True
                else:
                    if client_addr == ipaddress.ip_address(allowed):
                        return True
            except ValueError:
                logger.warning(f"Invalid IP/CIDR in whitelist: {allowed}")
                continue

        raise WebhookValidationError(
            f"IP address not allowed: {client_ip}", status_code=403
        )

    async def validate_request(
        self,
        secret_header: Optional[str] = None,
        client_ip: Optional[str] = None,
        body: Optional[bytes] = None,
        hmac_header: Optional[str] = None,
    ) -> bool:
        """Validate the complete webhook request.

        Args:
            secret_header: Value of X-ServiceNow-Secret header
            client_ip: Client IP address
            body: Raw request body (for HMAC validation)
            hmac_header: HMAC signature header value

        Returns:
            True if all validation passes

        Raises:
            WebhookValidationError: If any validation fails
        """
        if not self._auth_config.enabled:
            raise WebhookValidationError(
                "Webhook is disabled", status_code=503
            )

        # IP validation
        if client_ip:
            self.validate_ip(client_ip)

        # Secret validation
        if self._auth_config.auth_type == "shared_secret":
            self.validate_shared_secret(secret_header)
        elif self._auth_config.auth_type == "hmac_sha256" and body is not None:
            self.validate_hmac(body, hmac_header)

        return True

    def parse_ritm_event(
        self, payload: Dict[str, Any]
    ) -> ServiceNowRITMEvent:
        """Parse and validate RITM event from webhook payload.

        Args:
            payload: JSON payload from ServiceNow

        Returns:
            Validated ServiceNowRITMEvent

        Raises:
            ValueError: If payload is invalid
        """
        try:
            event = ServiceNowRITMEvent(**payload)
            logger.info(
                f"Parsed RITM event: {event.number} "
                f"(cat_item={event.cat_item_name}, state={event.state})"
            )
            return event
        except Exception as e:
            logger.error(f"Failed to parse RITM event: {e}")
            raise ValueError(f"Invalid RITM payload: {e}")

    def is_duplicate(self, sys_id: str) -> bool:
        """Check if event has already been processed (idempotency).

        Args:
            sys_id: ServiceNow record sys_id

        Returns:
            True if event was already processed
        """
        return sys_id in self._processed_events

    def mark_processed(self, sys_id: str) -> None:
        """Mark an event as processed.

        Maintains a bounded cache to prevent memory growth.

        Args:
            sys_id: ServiceNow record sys_id
        """
        if len(self._processed_events) >= self.MAX_CACHE_SIZE:
            # Evict oldest entries
            oldest_keys = sorted(
                self._event_timestamps,
                key=self._event_timestamps.get,
            )[: self.MAX_CACHE_SIZE // 2]
            for key in oldest_keys:
                self._processed_events.discard(key)
                self._event_timestamps.pop(key, None)

        self._processed_events.add(sys_id)
        self._event_timestamps[sys_id] = time.time()

    async def process_event(
        self,
        event: ServiceNowRITMEvent,
    ) -> Dict[str, Any]:
        """Process a validated RITM event.

        Checks for duplicates, marks as processed, and returns
        a tracking result.

        Args:
            event: Validated RITM event

        Returns:
            Processing result with tracking_id and status

        Raises:
            WebhookValidationError: If event is a duplicate (409 Conflict)
        """
        # Idempotency check
        if self.is_duplicate(event.sys_id):
            logger.warning(
                f"Duplicate event detected: {event.number} ({event.sys_id})"
            )
            raise WebhookValidationError(
                f"Duplicate event: {event.number}", status_code=409
            )

        # Generate tracking ID
        tracking_id = str(uuid.uuid4())

        # Mark as processed
        self.mark_processed(event.sys_id)

        logger.info(
            f"Processing RITM event: {event.number} → tracking_id={tracking_id}"
        )

        return {
            "status": "accepted",
            "tracking_id": tracking_id,
            "ritm_number": event.number,
            "cat_item_name": event.cat_item_name,
            "received_at": datetime.utcnow().isoformat(),
        }
