"""
File: backend/src/agent_harness/guardrails/_factory.py
Purpose: build_default_guardrail_engine() — instantiate + register default detector chain.
Category: 範疇 9 (Guardrails)
Scope: Phase 57+ Sprint 57.2 (Audit Cycle Lvl 2 — closes AD-Cat9-1-WireDetectors)

Description:
    Day 0 D9+D10 (Sprint 57.2) finding: Stage 1 active gate is already
    wired at engine + AgentLoop level since Sprint 53.3+55.4 (loop.py
    L421-422 / L478-479 / L698-699 invoke check_input/check_output/
    check_tool_call). The gap closing AD-Cat9-1-WireDetectors is the
    chat router NOT instantiating GuardrailEngine + registering default
    detectors — pre-tool/output detection runs as no-op when engine is
    None (which it always was per Day 0 探勘).

    This factory builds a production-ready engine with the 4 default
    Stage-0-promoted-to-Stage-1 detectors:
      - PIIDetector (input chain, priority 10)
      - JailbreakDetector (input chain, priority 20)
      - ToxicityDetector (output chain, priority 10)
      - SensitiveInfoDetector (output chain, priority 20)

    Tool-chain detectors (ToolGuardrail) require CapabilityMatrix tenant
    config and are NOT registered by default factory; tool-call gating
    is per-tenant policy and wired separately.

Key Components:
    - build_default_guardrail_engine(): no-arg factory returning ready
      GuardrailEngine with 4 detectors registered

Created: 2026-05-07 (Sprint 57.2 Day 4)
Last Modified: 2026-05-07

Modification History (newest-first):
    - 2026-05-07: Sprint 57.2 Day 4 — initial creation (closes AD-Cat9-1-WireDetectors)

Related:
    - 17-cross-category-interfaces.md §Cat 9 GuardrailEngine
    - loop.py L421+L478+L698 — pre-existing Stage 1 invoke sites
    - guardrails/engine.py register() — chain registration API
"""

from __future__ import annotations

from .engine import GuardrailEngine
from .input.jailbreak_detector import JailbreakDetector
from .input.pii_detector import PIIDetector
from .output.sensitive_info_detector import SensitiveInfoDetector
from .output.toxicity_detector import ToxicityDetector

__all__ = ["build_default_guardrail_engine"]


def build_default_guardrail_engine() -> GuardrailEngine:
    """Construct a GuardrailEngine with the 4 default detectors registered.

    Detector chain priorities (lower runs first per engine.register):
      - input chain:  PII (10) → Jailbreak (20)
      - output chain: Toxicity (10) → SensitiveInfo (20)

    Returns:
        GuardrailEngine ready to wire into AgentLoop via guardrail_engine ctor param.
    """
    engine = GuardrailEngine()
    engine.register(PIIDetector(), priority=10)
    engine.register(JailbreakDetector(), priority=20)
    engine.register(ToxicityDetector(), priority=10)
    engine.register(SensitiveInfoDetector(), priority=20)
    return engine
