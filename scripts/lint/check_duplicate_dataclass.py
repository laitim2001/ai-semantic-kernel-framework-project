"""
File: scripts/lint/check_duplicate_dataclass.py
Purpose: Detect duplicate @dataclass / @dataclass(frozen=True) class names across agent_harness/.
Category: V2 Lint / CI / Quality
Scope: Phase 49 / Sprint 49.4 Day 4 (rule from 17.md §8.1)

Usage:
    python -m scripts.lint.check_duplicate_dataclass [--root backend/src]

Exit codes:
    0 — no duplicates found
    1 — at least one duplicate (printed file:line + class name)
    2 — argparse / IO error

Why:
    V1 had MultiTenantContext defined in 4 places, ToolCall in 3 places (Cat 2
    spec + 2 sub-modules). Single-source rule (17.md §1) requires every dataclass
    name to be unique within a scope. This lint detects accidental shadowing or
    forgotten import that re-defines the same dataclass.

Per .claude/rules/anti-patterns-checklist.md AP-3 (Cross-Directory Scattering)
and 17.md §1.1 (single-source dataclass registry).
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path


def find_dataclasses_in_file(path: Path) -> list[tuple[str, int]]:
    """Return list of (class_name, lineno) for every @dataclass-decorated class."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for dec in node.decorator_list:
            if _is_dataclass_decorator(dec):
                out.append((node.name, node.lineno))
                break
    return out


def _is_dataclass_decorator(node: ast.expr) -> bool:
    """Match @dataclass / @dataclass(...) / @dataclasses.dataclass(...) ."""
    if isinstance(node, ast.Name):
        return node.id == "dataclass"
    if isinstance(node, ast.Attribute):
        return node.attr == "dataclass"
    if isinstance(node, ast.Call):
        return _is_dataclass_decorator(node.func)
    return False


def scan_directory(root: Path) -> dict[str, list[tuple[Path, int]]]:
    """Walk root; return {class_name: [(path, lineno), ...]} for all @dataclass classes."""
    found: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    for py_file in root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        for cls_name, lineno in find_dataclasses_in_file(py_file):
            found[cls_name].append((py_file, lineno))
    return dict(found)


def find_duplicates(
    occurrences: dict[str, list[tuple[Path, int]]],
) -> dict[str, list[tuple[Path, int]]]:
    return {name: locs for name, locs in occurrences.items() if len(locs) > 1}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="backend/src/agent_harness",
        help="Directory to scan (default: backend/src/agent_harness)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: --root path not found: {root}", file=sys.stderr)
        return 2

    occurrences = scan_directory(root)
    duplicates = find_duplicates(occurrences)

    if not duplicates:
        print(
            f"OK: no duplicate @dataclass names in {root} ({len(occurrences)} classes scanned)"
        )
        return 0

    print(
        f"FAIL: {len(duplicates)} duplicate @dataclass name(s) in {root}:",
        file=sys.stderr,
    )
    for name, locs in sorted(duplicates.items()):
        print(f"  - {name}: defined in {len(locs)} places", file=sys.stderr)
        for path, lineno in locs:
            print(f"      {path}:{lineno}", file=sys.stderr)
    print(
        "\nFIX: Move to single-source per 17.md §1; import from owner instead of re-defining.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
