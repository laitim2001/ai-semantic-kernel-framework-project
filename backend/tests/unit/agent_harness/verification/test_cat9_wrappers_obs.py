"""
File: backend/tests/unit/agent_harness/verification/test_cat9_wrappers_obs.py
Purpose: Sentinel tests enforcing 54.2 D19 reuse-inner-tracer design for Cat 9 wrappers.
Category: 範疇 10 (Verification Loops) / Tests
Scope: Sprint 55.5 Day 2 — closes AD-Cat10-Obs-Cat9Wrappers

Description:
    Per 54.2 D19 + 55.5 AD-Cat10-Obs-Cat9Wrappers validation: Cat 9 wrappers
    `LLMJudgeFallbackGuardrail` (cat9_fallback.py) and `LLMVerifyMutateGuardrail`
    (cat9_mutator.py) intentionally REUSE the inner LLMJudgeVerifier's
    `verification_span` — they do NOT emit an independent wrapper-level span.

    Rationale (recorded in cat9_fallback.py + cat9_mutator.py docstrings):
    - Single span per verify invocation matches Cat 12 helpers minimal-overhead
      philosophy
    - Wrapper logic (judge fallback / mutation) does not warrant separate span
    - Avoids double-instrumentation noise in distributed traces

    These sentinel tests enforce the invariant at AST level (NOT string-search:
    docstrings legitimately reference `verification_span` to explain the design;
    Day 2 D8 drift caught the over-strict approach). The check walks the AST
    looking for actual `from ... import verification_span` statements and
    `verification_span(...)` call nodes — those would represent real wrapper-level
    span emission. AST-level enforcement runs in <10ms and catches the failure
    mode at the only place it can manifest (import or call expression).

Created: 2026-05-05 (Sprint 55.5 Day 2)
Last Modified: 2026-05-05

Modification History (newest-first):
    - 2026-05-05: Sprint 55.5 — initial sentinel via AST walk (D8 drift response)
"""

from __future__ import annotations

import ast
import inspect
from types import ModuleType

from agent_harness.verification import cat9_fallback, cat9_mutator


def _find_verification_span_usage(module: ModuleType) -> list[str]:
    """Walk module AST + return list of `verification_span` import or call sites.

    Returns an empty list when the module does NOT use verification_span
    (the D19 reuse-inner invariant). Returns non-empty list of locations
    (e.g., "import line 12", "call line 45") on violation.

    Docstring / comment mentions of the name are NOT counted because they
    don't appear as AST Import / ImportFrom / Call nodes.
    """
    source = inspect.getsource(module)
    tree = ast.parse(source)
    findings: list[str] = []

    for node in ast.walk(tree):
        # Direct: `from agent_harness.verification._obs import verification_span`
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "verification_span":
                    findings.append(f"import-from line {node.lineno}")
        # Direct: `import verification_span` (rare; would not work as bare module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "verification_span":
                    findings.append(f"import line {node.lineno}")
        # Call: `verification_span(...)`
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "verification_span":
                findings.append(f"name call line {node.lineno}")
            elif isinstance(func, ast.Attribute) and func.attr == "verification_span":
                findings.append(f"attr call line {node.lineno}")

    return findings


class TestCat9WrappersReuseInnerSpan:
    """AD-Cat10-Obs-Cat9Wrappers — enforce 54.2 D19 reuse-inner invariant via AST walk."""

    def test_cat9_fallback_does_not_import_verification_span(self) -> None:
        """cat9_fallback.py must NOT directly import or call verification_span.

        Per 54.2 D19 design: the wrapper relies on the inner LLMJudgeVerifier
        emitting its own span via _obs.verification_span; adding a wrapper-level
        span would double-instrument every Cat 9 fallback verify invocation.
        """
        findings = _find_verification_span_usage(cat9_fallback)
        assert findings == [], (
            f"cat9_fallback.py imports/calls verification_span at {findings} — "
            "violates 54.2 D19 reuse-inner-tracer design. If wrapper-level span "
            "is genuinely needed (double-instrumentation justified by audit/SLA), "
            "update D19 decision in 17.md §Cat 10 + AD-Cat10-Obs-Cat9Wrappers + "
            "this sentinel."
        )

    def test_cat9_mutator_does_not_import_verification_span(self) -> None:
        """cat9_mutator.py must NOT directly import or call verification_span.

        Same rationale as test_cat9_fallback: wrapper reuses inner judge's span;
        no double-instrumentation.
        """
        findings = _find_verification_span_usage(cat9_mutator)
        assert findings == [], (
            f"cat9_mutator.py imports/calls verification_span at {findings} — "
            "violates 54.2 D19 reuse-inner-tracer design. See cat9_fallback test "
            "for remediation guide."
        )

    def test_cat9_wrappers_docstrings_document_reuse_inner_design(self) -> None:
        """Both wrapper module docstrings must explicitly document D19 reuse-inner.

        This protects against silent removal of the design rationale during future
        refactors — if someone removes the docstring section, this test fails and
        forces them to either restore the rationale or re-validate AD-Cat10-Obs-Cat9Wrappers
        with a new design decision.
        """
        fallback_doc = cat9_fallback.__doc__ or ""
        mutator_doc = cat9_mutator.__doc__ or ""

        # Each docstring must mention BOTH the design name AND the AD ref so the
        # rationale stays linked to the audit trail
        for doc, name in [(fallback_doc, "cat9_fallback"), (mutator_doc, "cat9_mutator")]:
            assert "Observability Design" in doc, (
                f"{name}.py docstring missing 'Observability Design' section "
                f"(54.2 D19 + 55.5 AD-Cat10-Obs-Cat9Wrappers rationale)"
            )
            assert (
                "D19" in doc
            ), f"{name}.py docstring missing D19 reference to 54.2 retro design decision"
            assert "AD-Cat10-Obs-Cat9Wrappers" in doc, (
                f"{name}.py docstring missing AD-Cat10-Obs-Cat9Wrappers reference "
                f"(audit cycle closure trail)"
            )
