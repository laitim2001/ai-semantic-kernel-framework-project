r"""
File: scripts/lint/check_sole_mutator.py
Purpose: Forbid ad-hoc LoopState mutation outside the Cat 7 reducer (sole-mutator pattern).
Category: V2 Lint / CI / Quality
Scope: Sprint 55.3 (closes AD-Cat7-1)

Usage:
    python scripts/lint/check_sole_mutator.py [--root backend/src]

What it forbids:
    Direct mutation of `state.messages`, `state.scratchpad`, `state.tool_calls`,
    or `state.user_input` anywhere in production code OUTSIDE the Cat 7
    reducer module(s). The Cat 7 single-mutator contract is:

        LoopState should only be evolved through `DefaultReducer.apply(state, event)`
        which returns a NEW LoopState (immutable replace via dataclasses.replace
        or equivalent). Ad-hoc `state.messages.append(...)` etc. violates this
        contract and bypasses observability / checkpoint / time-travel.

    Forbidden patterns (regex):
        - `state\.messages\.append`            ad-hoc message append
        - `state\.scratchpad\[.*\]\s*=`        ad-hoc scratchpad write
        - `state\.tool_calls\.append`          ad-hoc tool_calls append
        - `state\.user_input\s*=`              ad-hoc user_input rebind

What it allows (whitelist):
    - `backend/src/agent_harness/state_mgmt/reducer.py`        (sole owner)
    - `backend/src/agent_harness/state_mgmt/decision_reducers.py`  (sub-reducer)
    - any `tests/` directory under root                       (fixture setup)
    - `__pycache__/`                                          (compiled)

Why:
    Per Sprint 53.1 retrospective Q5 (AD-Cat7-1 origin) + 17.md §Contract 7
    + 04-anti-patterns.md AP-3 (cross-directory scattering of state mutation).
    Sprint 55.3 Day 0 grep confirmed grep-zero across full backend/src/ tree;
    this lint is the *enforcement* gate to keep that property as new code lands.

Created: 2026-05-04 (Sprint 55.3 Day 2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.3) — closes AD-Cat7-1

Related:
    - 17-cross-category-interfaces.md §Contract 7 (Reducer single-mutator)
    - 01-eleven-categories-spec.md §範疇 7
    - 04-anti-patterns.md §AP-3 Cross-Directory Scattering
    - .claude/rules/category-boundaries.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Forbidden mutation patterns (regex). Match against raw line text.
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bstate\.messages\.append\b", "ad-hoc state.messages.append (use reducer)"),
    (r"\bstate\.scratchpad\[.*\]\s*=", "ad-hoc state.scratchpad[...] = (use reducer)"),
    (r"\bstate\.tool_calls\.append\b", "ad-hoc state.tool_calls.append (use reducer)"),
    (r"\bstate\.user_input\s*=(?!=)", "ad-hoc state.user_input = (use reducer)"),
)

# Files / dirs allowed to contain mutation patterns. Paths are matched as
# substrings against the relative posix path from --root.
WHITELIST_SUBSTRINGS: tuple[str, ...] = (
    "agent_harness/state_mgmt/reducer.py",
    "agent_harness/state_mgmt/decision_reducers.py",
    "/tests/",
    "__pycache__",
)


def _is_whitelisted(rel_posix: str) -> bool:
    return any(w in rel_posix for w in WHITELIST_SUBSTRINGS)


def find_violations(root: Path) -> list[tuple[Path, int, str, str]]:
    """Return list of (file, lineno, matched_text, reason) violating sole-mutator rule."""
    violations: list[tuple[Path, int, str, str]] = []
    compiled = [(re.compile(p), reason) for p, reason in FORBIDDEN_PATTERNS]

    for py_file in root.rglob("*.py"):
        rel_posix = py_file.relative_to(root).as_posix()
        if _is_whitelisted(rel_posix):
            continue
        try:
            text = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            # Skip pure comments to avoid false-flagging documentation prose.
            if stripped.startswith("#"):
                continue
            for pattern, reason in compiled:
                m = pattern.search(line)
                if m:
                    violations.append((py_file, lineno, m.group(0), reason))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="backend/src",
        help="Root path to scan (default: backend/src)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: --root not found: {root}", file=sys.stderr)
        return 2

    violations = find_violations(root)
    if not violations:
        print(f"OK: no sole-mutator violations under {root}")
        return 0

    print(
        f"FAIL: {len(violations)} sole-mutator violation(s):",
        file=sys.stderr,
    )
    for path, lineno, matched, reason in violations:
        print(f"  {path}:{lineno}  {matched!r}  -- {reason}", file=sys.stderr)
    print(
        "\nFIX: Route LoopState mutation through Cat 7 DefaultReducer.apply(state, event).\n"
        "     See 17-cross-category-interfaces.md §Contract 7 + reducer.py.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
