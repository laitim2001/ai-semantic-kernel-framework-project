"""
File: backend/tests/unit/test_chaos_dummy_53_7.py
Purpose: AI-22 chaos test — intentional fail to verify enforce_admins blocks
    admin merge of red-CI PR. NEVER MERGE; this branch + PR will be deleted
    after the chaos test result is documented.
Category: Tests / Chaos verification
Scope: Sprint 53.7 US-3 / closes AI-22

Created: 2026-05-04
"""


def test_intentional_fail_for_chaos_verification() -> None:
    """Intentional assert False to fail CI; goal: verify branch protection blocks merge."""
    assert 1 == 2, "Sprint 53.7 AI-22 chaos test: this fail is intentional."
