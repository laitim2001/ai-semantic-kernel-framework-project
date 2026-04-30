"""
File: scripts/lint/check_sync_callback.py
Purpose: Detect sync method overrides of async ABC methods (and vice versa).
Category: V2 Lint / CI / Quality
Scope: Phase 49 / Sprint 49.4 Day 4 (rule from 17.md §8.3)

Usage:
    python -m scripts.lint.check_sync_callback [--root backend/src]

What it forbids:
    Any subclass that overrides an `@abstractmethod async def foo(...)` with a
    plain `def foo(...)` (or the reverse). Mixing breaks await-chain integrity
    and silently changes behavior.

Detection strategy (within a single file):
    1. Find ABC classes — classes inheriting from `ABC` or `abc.ABC`.
    2. For each abstract method on the ABC, record (method_name, is_async).
    3. Find subclasses (in the SAME file or another file under --root) that
       inherit from the ABC.
    4. Compare each override against the abstract method's async-ness.

Limitations:
    - Inheritance is resolved by name only (no full type-resolution); subclasses
      must reference the ABC name directly (`class X(MyABC):`). Indirect
      subclassing across modules with rename / alias is not caught.
    - This is intentional — keeps the lint fast + understandable. Cases the
      rule misses are caught by mypy --strict in CI.

Per 17.md §8.3 (sync-callback prohibition).
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path


def _is_abc_base(base: ast.expr) -> bool:
    """Return True if a base class refers to ABC or abc.ABC."""
    if isinstance(base, ast.Name):
        return base.id == "ABC"
    if isinstance(base, ast.Attribute):
        return base.attr == "ABC"
    return False


def _is_abstractmethod_decorator(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "abstractmethod"
    if isinstance(node, ast.Attribute):
        return node.attr == "abstractmethod"
    if isinstance(node, ast.Call):
        return _is_abstractmethod_decorator(node.func)
    return False


def _abstract_methods(cls: ast.ClassDef) -> dict[str, bool]:
    """Return {method_name: is_async} for abstract methods of cls."""
    out: dict[str, bool] = {}
    for stmt in cls.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(_is_abstractmethod_decorator(d) for d in stmt.decorator_list):
                out[stmt.name] = isinstance(stmt, ast.AsyncFunctionDef)
    return out


def _concrete_methods(cls: ast.ClassDef) -> dict[str, bool]:
    """Return {method_name: is_async} for non-abstract methods of cls."""
    out: dict[str, bool] = {}
    for stmt in cls.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not any(_is_abstractmethod_decorator(d) for d in stmt.decorator_list):
                # also tolerate property/staticmethod (they don't override abstract async)
                out[stmt.name] = isinstance(stmt, ast.AsyncFunctionDef)
    return out


def _direct_base_names(cls: ast.ClassDef) -> list[str]:
    names: list[str] = []
    for base in cls.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def _scan_classes(root: Path) -> tuple[
    dict[str, dict[str, bool]],
    list[tuple[Path, ast.ClassDef]],
]:
    """First pass: collect ABC abstract method maps + all class defs (subclass candidates)."""
    abc_map: dict[str, dict[str, bool]] = {}
    all_classes: list[tuple[Path, ast.ClassDef]] = []

    for py_file in root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            all_classes.append((py_file, node))
            if any(_is_abc_base(b) for b in node.bases):
                abc_map[node.name] = _abstract_methods(node)
    return abc_map, all_classes


def find_violations(
    root: Path,
) -> list[tuple[Path, int, str, str, str]]:
    """Return list of (file, lineno, class_name, method_name, mismatch_kind)."""
    abc_map, all_classes = _scan_classes(root)
    violations: list[tuple[Path, int, str, str, str]] = []

    for path, cls in all_classes:
        # Match against any DIRECT base that is a known ABC.
        for base_name in _direct_base_names(cls):
            if base_name not in abc_map:
                continue
            abstract = abc_map[base_name]
            concrete = _concrete_methods(cls)
            for m_name, is_async_concrete in concrete.items():
                if m_name not in abstract:
                    continue
                is_async_abstract = abstract[m_name]
                if is_async_abstract != is_async_concrete:
                    kind = (
                        "abstract async, concrete sync"
                        if is_async_abstract
                        else "abstract sync, concrete async"
                    )
                    # find the method's lineno
                    for stmt in cls.body:
                        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if stmt.name == m_name:
                                violations.append(
                                    (path, stmt.lineno, cls.name, m_name, kind)
                                )
                                break
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="backend/src")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: --root not found: {root}", file=sys.stderr)
        return 2

    violations = find_violations(root)
    if not violations:
        print(f"OK: no sync/async mismatches in {root}")
        return 0

    print(
        f"FAIL: {len(violations)} sync/async ABC override mismatch(es):",
        file=sys.stderr,
    )
    by_file: dict[Path, list[tuple[int, str, str, str]]] = defaultdict(list)
    for path, lineno, cls, method, kind in violations:
        by_file[path].append((lineno, cls, method, kind))
    for path, items in sorted(by_file.items()):
        for lineno, cls, method, kind in sorted(items):
            print(f"  {path}:{lineno}  {cls}.{method}  [{kind}]", file=sys.stderr)
    print(
        "\nFIX: Make the override match the abstract method's async-ness.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
