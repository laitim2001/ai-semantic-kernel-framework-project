"""Category 9: Guardrails & Safety. See README.md."""

from agent_harness.guardrails._abc import (
    Guardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailType,
    Tripwire,
)
from agent_harness.guardrails.audit import (
    AuditAppendError,
    ChainVerificationResult,
    WORMAuditLog,
    compute_entry_hash,
    verify_chain,
)
from agent_harness.guardrails.engine import GuardrailEngine
from agent_harness.guardrails.input.jailbreak_detector import JailbreakDetector
from agent_harness.guardrails.input.pii_detector import PIIDetector
from agent_harness.guardrails.output.sensitive_info_detector import (
    SensitiveInfoDetector,
)
from agent_harness.guardrails.output.toxicity_detector import ToxicityDetector
from agent_harness.guardrails.tool import (
    Capability,
    CapabilityMatrix,
    PermissionRule,
    ToolGuardrail,
)
from agent_harness.guardrails.tripwire import DefaultTripwire

__all__ = [
    "Guardrail",
    "Tripwire",
    "GuardrailType",
    "GuardrailAction",
    "GuardrailResult",
    "GuardrailEngine",
    "PIIDetector",
    "JailbreakDetector",
    "ToxicityDetector",
    "SensitiveInfoDetector",
    "Capability",
    "PermissionRule",
    "CapabilityMatrix",
    "ToolGuardrail",
    "DefaultTripwire",
    "WORMAuditLog",
    "AuditAppendError",
    "compute_entry_hash",
    "verify_chain",
    "ChainVerificationResult",
]
