r"""
File: scripts/lint/check_rls_policies.py
Purpose: Enforce RLS coverage on every TenantScopedMixin ORM table.
Category: V2 Lint / CI / Quality (8th V2 lint)
Scope: Sprint 56.1 / Day 4 / US-5 RLS Hardening

Usage:
    python scripts/lint/check_rls_policies.py [--root backend/src]

What it enforces:
    For every `class X(Base, TenantScopedMixin)` in
    `backend/src/infrastructure/db/models/**/*.py`, the corresponding
    `__tablename__` must appear in at least one Alembic migration with
    BOTH:
        1. `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY` (or be in
           `RLS_TABLES` tuple of the bootstrap 0009 migration)
        2. A `CREATE POLICY ... ON <table> USING (tenant_id = ...)` clause

    Otherwise, the table accepts cross-tenant queries when callers do
    NOT manually filter by `tenant_id` — violating multi-tenant-data.md
    §Rule 3 and the §Server-Side First philosophy.

What it allows (whitelist):
    - Tables NOT inheriting TenantScopedMixin (registry / global / chain
      junctions): Tenant / FeatureFlag / ToolRegistry / MemorySystem /
      MemoryRole / MemorySessionSummary / Approval / RiskAssessment /
      GuardrailEvent / ToolResult / UserRole / RolePermission. These
      resolve tenant scope via FK chain (per 09-db-schema-design.md
      L18-19) or are documented registry tables.

Why this lint exists:
    Sprint 56.1 Day 4 §US-5 promotes the V2 baseline (0009 RLS bootstrap
    + 0012 incidents + 0013 hitl_policies) into a continuous-enforcement
    invariant. Without this lint, a future migration that adds a new
    TenantScopedMixin table without RLS would silently regress
    multi-tenant isolation.

    Pattern reuses 7th-lint check_sole_mutator.py shape (regex against
    file content; whitelist substrings; exit non-zero on violations).

Created: 2026-05-06 (Sprint 56.1 Day 4)

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.1 Day 4) — closes US-5

Related:
    - 09-db-schema-design.md §RLS Policies
    - 0009_rls_policies.py (bootstrap RLS_TABLES tuple)
    - .claude/rules/multi-tenant-data.md §Rule 3
    - 17-cross-category-interfaces.md §Contract 9 Identity / Auth
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Tables that are intentionally NOT TenantScopedMixin (registry / chain).
# These are NOT expected to have RLS; the lint will not flag them missing.
EXPLICIT_NON_RLS_WHITELIST: frozenset[str] = frozenset(
    {
        "tenants",  # registry root
        "feature_flags",  # registry / global config (Sprint 56.1 Day 3)
        "tools_registry",  # global tool metadata
        "tool_results",  # chain via tool_call_id
        "memory_system",  # global system layer
        "memory_role",  # chain via role_id
        "memory_session_summary",  # chain via session_id
        "approvals",  # chain via session_id
        "risk_assessments",  # chain via session_id
        "guardrail_events",  # chain via session_id
        "user_roles",  # junction
        "role_permissions",  # junction
        "alembic_version",  # Alembic bookkeeping
    }
)

CLASS_TENANT_SCOPED_RE = re.compile(
    r"^class\s+(\w+)\s*\(\s*Base\s*,\s*TenantScopedMixin\s*\)\s*:"
)
TABLENAME_RE = re.compile(r'^\s*__tablename__\s*=\s*[\'"]([\w_]+)[\'"]')

ENABLE_RLS_RE = re.compile(
    r"ALTER\s+TABLE\s+(\w+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY", re.IGNORECASE
)
CREATE_POLICY_RE = re.compile(r"CREATE\s+POLICY\s+\w+\s+ON\s+(\w+)", re.IGNORECASE)
RLS_TABLES_TUPLE_RE = re.compile(
    r"RLS_TABLES\s*:\s*tuple\[str,\s*\.\.\.\]\s*=\s*\(([^)]*)\)", re.DOTALL
)


def find_tenant_scoped_tables(models_dir: Path) -> dict[str, Path]:
    """Walk model files; map __tablename__ → file for every TenantScopedMixin class."""
    out: dict[str, Path] = {}
    for path in models_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        # Find class blocks that inherit (Base, TenantScopedMixin).
        in_target_class = False
        for line in text.splitlines():
            if CLASS_TENANT_SCOPED_RE.match(line):
                in_target_class = True
                continue
            if in_target_class:
                # First __tablename__ wins; reset target after capture.
                m = TABLENAME_RE.match(line)
                if m:
                    out[m.group(1)] = path
                    in_target_class = False
                # New class definition aborts current target.
                if line.startswith("class ") and not CLASS_TENANT_SCOPED_RE.match(line):
                    in_target_class = False
    return out


def find_rls_protected_tables(migrations_dir: Path) -> set[str]:
    """Walk migrations; collect tables covered by ENABLE RLS + CREATE POLICY."""
    enable_set: set[str] = set()
    policy_set: set[str] = set()
    for path in migrations_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for m in ENABLE_RLS_RE.finditer(text):
            enable_set.add(m.group(1))
        for m in CREATE_POLICY_RE.finditer(text):
            policy_set.add(m.group(1))
        # 0009 bootstrap: RLS_TABLES tuple iterated → table covered.
        tuple_match = RLS_TABLES_TUPLE_RE.search(text)
        if tuple_match:
            for raw in re.findall(r'[\'"]([\w_]+)[\'"]', tuple_match.group(1)):
                enable_set.add(raw)
                policy_set.add(raw)
    # A table is RLS-protected only if BOTH ENABLE and POLICY appear.
    return enable_set & policy_set


def main(root_arg: str) -> int:
    root = Path(root_arg).resolve()
    models_dir = root / "infrastructure" / "db" / "models"
    migrations_dir = root / "infrastructure" / "db" / "migrations" / "versions"
    if not models_dir.is_dir():
        print(f"ERROR: models dir not found at {models_dir}", file=sys.stderr)
        return 2
    if not migrations_dir.is_dir():
        print(
            f"ERROR: migrations dir not found at {migrations_dir}",
            file=sys.stderr,
        )
        return 2

    tenant_scoped = find_tenant_scoped_tables(models_dir)
    rls_protected = find_rls_protected_tables(migrations_dir)

    gaps = sorted(
        t
        for t in tenant_scoped
        if t not in rls_protected and t not in EXPLICIT_NON_RLS_WHITELIST
    )

    print(f"check_rls_policies: {len(tenant_scoped)} TenantScopedMixin tables")
    print(f"check_rls_policies: {len(rls_protected)} RLS-protected tables")
    print(
        f"check_rls_policies: {len(EXPLICIT_NON_RLS_WHITELIST)} whitelisted (registry/junction)"
    )

    if gaps:
        print(f"\nFAIL: {len(gaps)} TenantScopedMixin table(s) WITHOUT RLS:")
        for t in gaps:
            src = tenant_scoped[t]
            try:
                rel = src.resolve().relative_to(root)
                print(f"  - {t}  (defined in {rel})")
            except ValueError:
                print(f"  - {t}  (defined in {src})")
        print(
            "\nFix: add `op.execute('ALTER TABLE <t> ENABLE ROW LEVEL SECURITY')`"
            "\n     + `CREATE POLICY tenant_isolation_<t> ON <t> "
            "USING (tenant_id = current_setting('app.tenant_id')::uuid)`"
            "\n     in a new Alembic migration. See 0012_incidents.py for pattern."
        )
        return 1

    print("OK: all TenantScopedMixin tables have RLS coverage.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enforce RLS coverage on every TenantScopedMixin table."
    )
    parser.add_argument(
        "--root",
        default="backend/src",
        help="Project source root (default: backend/src)",
    )
    args = parser.parse_args()
    sys.exit(main(args.root))
