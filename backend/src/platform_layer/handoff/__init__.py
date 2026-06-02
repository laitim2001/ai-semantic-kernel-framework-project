"""platform_layer.handoff — Cat 11 HANDOFF control-transfer session-boot.

Sprint 57.68 (A-3b backend slice) introduces:
    - persona_registry: minimal target_agent → system_prompt stand-in
    - service: HandoffService.boot_handoff — atomic child-session boot,
      parent mark, audit (tenant-scoped, linked, persona in meta_data)
"""

from platform_layer.handoff.persona_registry import (
    PERSONA_REGISTRY,
    resolve_persona,
)
from platform_layer.handoff.service import (
    HandoffError,
    HandoffResult,
    HandoffService,
)

__all__ = [
    # persona_registry
    "PERSONA_REGISTRY",
    "resolve_persona",
    # service
    "HandoffError",
    "HandoffResult",
    "HandoffService",
]
