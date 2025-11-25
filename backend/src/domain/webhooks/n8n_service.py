"""
n8n Webhook Service

Handles n8n webhook processing with HMAC-SHA256 signature verification.
Sprint 2 - Story S2-1
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.audit.service import AuditService
from src.infrastructure.database.models.audit_log import AuditAction

logger = logging.getLogger(__name__)


class N8nWebhookService:
    """
    Service class for n8n webhook operations.

    Provides methods to:
    - Verify webhook signatures (HMAC-SHA256)
    - Process webhook payloads
    - Trigger workflow executions
    - Log webhook events
    """

    def __init__(
        self,
        db: AsyncSession,
        secret_key: Optional[str] = None
    ):
        """
        Initialize N8nWebhookService.

        Args:
            db: SQLAlchemy async database session
            secret_key: Webhook secret key for signature verification.
                       Falls back to N8N_WEBHOOK_SECRET env var.
        """
        self.db = db
        self.secret_key = secret_key or os.getenv("N8N_WEBHOOK_SECRET", "default-secret-change-me")
        self.audit_service = AuditService(db)

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        algorithm: str = "sha256"
    ) -> bool:
        """
        Verify n8n webhook signature using HMAC.

        Args:
            payload: Raw request body bytes
            signature: Signature from X-N8n-Signature header
            algorithm: Hash algorithm (default: sha256)

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature:
            logger.warning("No signature provided for webhook")
            return False

        try:
            # Clean up signature - remove algorithm prefix if present
            # n8n typically sends: sha256=<signature>
            if "=" in signature:
                parts = signature.split("=", 1)
                if len(parts) == 2:
                    algorithm = parts[0].lower()
                    signature = parts[1]

            # Get hash function
            if algorithm == "sha256":
                hash_func = hashlib.sha256
            elif algorithm == "sha1":
                hash_func = hashlib.sha1
            else:
                logger.warning(f"Unsupported algorithm: {algorithm}")
                return False

            # Calculate expected signature
            expected_signature = hmac.new(
                self.secret_key.encode("utf-8"),
                payload,
                hash_func
            ).hexdigest()

            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(signature.lower(), expected_signature.lower())

        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

    def generate_signature(self, payload: bytes) -> str:
        """
        Generate a signature for a payload.

        Useful for testing and for generating signatures for outgoing webhooks.

        Args:
            payload: Raw payload bytes

        Returns:
            HMAC-SHA256 signature
        """
        return hmac.new(
            self.secret_key.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

    async def handle_webhook(
        self,
        workflow_id: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Process an n8n webhook request.

        Args:
            workflow_id: Target workflow ID
            payload: Webhook payload data
            headers: Request headers
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Response dictionary with execution details
        """
        request_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Extract n8n specific data
            n8n_execution_id = payload.get("execution_id")
            n8n_workflow_id = payload.get("workflow_id")
            trigger_data = payload.get("data", {})

            # Create trigger context
            trigger_context = {
                "source": "n8n",
                "n8n_workflow_id": n8n_workflow_id,
                "n8n_execution_id": n8n_execution_id,
                "target_workflow_id": workflow_id,
                "payload": trigger_data,
                "request_id": request_id,
                "timestamp": start_time.isoformat(),
            }

            # Log successful webhook receipt
            await self.audit_service.log(
                action=AuditAction.WEBHOOK_RECEIVED,
                resource_type="webhook",
                resource_name=f"n8n-{workflow_id}",
                changes=trigger_context,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # TODO: In future, integrate with ExecutionService to trigger workflow
            # For now, return success response indicating webhook was received
            # execution = await execution_service.create_execution(
            #     workflow_id=workflow_id,
            #     triggered_by="n8n-webhook",
            #     trigger_data=trigger_context
            # )

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return {
                "success": True,
                "message": "Webhook received successfully",
                "request_id": request_id,
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat(),
                "duration_ms": duration_ms,
                # "execution_id": execution.id,  # Future: actual execution ID
            }

        except Exception as e:
            logger.error(f"Error processing webhook for workflow {workflow_id}: {e}")

            # Log failed webhook processing
            try:
                await self.audit_service.log(
                    action=AuditAction.WEBHOOK_FAILED,
                    resource_type="webhook",
                    resource_name=f"n8n-{workflow_id}",
                    changes={"error": str(e), "request_id": request_id},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            except Exception as audit_error:
                logger.error(f"Failed to log audit entry: {audit_error}")

            raise

    async def test_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        ip_address: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Test webhook endpoint.

        Validates signature and returns diagnostic information.

        Args:
            payload: Test payload
            headers: Request headers
            ip_address: Client IP address

        Returns:
            Test result with diagnostic info
        """
        import json

        # Get signature from headers
        signature = headers.get("x-n8n-signature", "")

        # Calculate expected signature
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        expected_signature = self.generate_signature(payload_bytes)

        # Verify if signature was provided
        signature_valid = None
        if signature:
            signature_valid = self.verify_signature(payload_bytes, signature)

        return {
            "success": True,
            "message": "Webhook test endpoint reached successfully",
            "received_payload": payload,
            "headers_received": dict(headers),
            "signature_info": {
                "signature_provided": bool(signature),
                "signature_valid": signature_valid,
                "expected_signature_prefix": expected_signature[:16] + "...",
            },
            "server_timestamp": datetime.utcnow().isoformat(),
            "client_ip": ip_address,
        }


def get_n8n_webhook_service(
    db: AsyncSession,
    secret_key: Optional[str] = None
) -> N8nWebhookService:
    """
    Factory function to create N8nWebhookService.

    Args:
        db: Database session
        secret_key: Optional secret key override

    Returns:
        N8nWebhookService instance
    """
    return N8nWebhookService(db=db, secret_key=secret_key)
