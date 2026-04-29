"""
File: scripts/lint/check_cross_category_import.py
Purpose: Forbid private cross-category imports inside agent_harness/.
Category: V2 Lint / CI / Quality
Scope: Phase 49 / Sprint 49.4 Day 4 (rules from 17.md §8.2 + category-boundaries.md)

Usage:
    python -m scripts.lint.check_cross_category_import [--root backend/src/agent_harness]

What it forbids:
    Inside agent_harness/<cat_a>/, NO module may import a private symbol from
    agent_harness/<cat_b>/ (private = file inside <cat_b>/ that is NOT explicitly
    re-exported via <cat_b>/__init__.py).

What it allows:
    - import from agent_harness._contracts (single-source contracts)
    - import from agent_harness.<other_cat>          (top-level package)
    - import from agent_harness.<other_cat>.__init__ (same)

Why:
    Prevents Anti-Pattern 3 (Cross-Directory Scattering): if Cat 1 reaches into
    Cat 4's internal compactor module, Cat 4 can't refactor without breaking Cat 1.
    Public surface = __init__.py re-exports.

Per .claude/rules/category-boundaries.md.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Top-level packages within agent_harness/ that count as "categories".
# Imports BETWEEN these are checked.
KNOWN_CATEGORIES: tuple[str, ...] = (
    "orchestrator_loop",
    "tools",
    "memory",
    "context_mgmt",
    "prompt_builder",
    "output_parser",
    "state_mgmt",
    "error_handling",
    "guardrails",
    "verification",
    "subagent",
    "observability",
    "hitl",
)

# Modules that ARE allowed cross-category access (public surface).
# Anything under these prefixes within a category is treated as public.
PUBLIC_PREFIXES: tuple[str, ...] = ("_contracts",)


def _own_category(file_path: Path, root: Path) -> str | None:
    """Return the category name a file belongs to, or None if not under one."""
    try:
        rel = file_path.relative_to(root).parts
    except ValueError:
        return None
    if not rel:
        return None
    return rel[0] if rel[0] in KNOWN_CATEGORIES else None


def _import_target_category(module: str) -> tuple[str | None, bool]:
    """
    Given an import target like 'agent_harness.tools.spec', return
    (target_category, is_private).

    is_private = True iff the import reaches BELOW the category's __init__.py
                       AND not in PUBLIC_PREFIXES.
    """
    parts = module.split(".")
    # only check imports that descend into agent_harness
    if len(parts) < 2 or parts[0] != "agent_harness":
        return None, False

    sub = parts[1]
    if sub in PUBLIC_PREFIXES:
        return None, False

    if sub not in KNOWN_CATEGORIES:
        return None, False

    # 'agent_harness.tools'        → public (the package's __init__)
    # 'agent_harness.tools.spec'   → private
    is_private = len(parts) > 2
    return sub, is_private


def find_violations(root: Path) -> list[tuple[Path, int, str]]:
    """Return list of (file, lineno, import_module) violating the rule."""
    violations: list[tuple[Path, int, str]] = []
    for py_file in root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        own_cat = _own_category(py_file, root)
        if own_cat is None:
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            module: str | None = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            # `import agent_harness.x.y` form
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target_cat, is_private = _import_target_category(alias.name)
                    if target_cat and target_cat != own_cat and is_private:
                        violations.append((py_file, node.lineno, alias.name))
                continue

            if module is None:
                continue
            target_cat, is_private = _import_target_category(module)
            if target_cat and target_cat != own_cat and is_private:
                lineno = getattr(node, "lineno", 0)
                violations.append((py_file, lineno, module))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="backend/src/agent_harness",
        help="agent_harness/ root (default: backend/src/agent_harness)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: --root not found: {root}", file=sys.stderr)
        return 2

    violations = find_violations(root)
    if not violations:
        print(f"OK: no private cross-category imports under {root}")
        return 0

    print(
        f"FAIL: {len(violations)} private cross-category import(s):",
        file=sys.stderr,
    )
    for path, lineno, mod in violations:
        print(f"  {path}:{lineno}  imports {mod!r}", file=sys.stderr)
    print(
        "\nFIX: Either re-export from <category>/__init__.py, or move shared type "
        "to agent_harness/_contracts/ per 17.md §1.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
