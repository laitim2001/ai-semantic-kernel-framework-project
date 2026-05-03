"""WORM audit log facade for Cat 9 (Sprint 53.3 US-6).

Wraps the existing append-only `audit_log` table (Sprint 49.3) with a
Cat 9-friendly API: WORMAuditLog.append() for guardrail/tripwire events,
and verify_chain() for tamper detection.

Schema reused (NOT duplicated): see infrastructure/db/models/audit.py.
"""

from agent_harness.guardrails.audit.chain_verifier import (
    ChainVerificationResult,
    verify_chain,
)
from agent_harness.guardrails.audit.worm_log import (
    AuditAppendError,
    WORMAuditLog,
    compute_entry_hash,
)

__all__ = [
    "WORMAuditLog",
    "AuditAppendError",
    "compute_entry_hash",
    "verify_chain",
    "ChainVerificationResult",
]
