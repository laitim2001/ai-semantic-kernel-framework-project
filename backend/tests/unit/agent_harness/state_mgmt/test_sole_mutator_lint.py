"""
File: backend/tests/unit/agent_harness/state_mgmt/test_sole_mutator_lint.py
Purpose: AD-Cat7-1 closure — verify check_sole_mutator.py CI lint script behavior.
Category: Tests / 範疇 7 (State Mgmt) × V2 Lint
Scope: Sprint 55.3 Day 2

Description:
    3 tests for `scripts/lint/check_sole_mutator.py`:
    1. Real codebase passes (regression — guards future violation introduction)
    2. Injected violation in temp dir triggers exit 1 + violation message
    3. Whitelist (reducer.py / decision_reducers.py / tests/) permits mutation

Created: 2026-05-04 (Sprint 55.3)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Project root resolved from this file's path:
# backend/tests/unit/agent_harness/state_mgmt/<this file>
# parents[5] -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_LINT_SCRIPT = _PROJECT_ROOT / "scripts" / "lint" / "check_sole_mutator.py"


def _run_lint(root: Path) -> tuple[int, str]:
    """Run check_sole_mutator.py with given --root; return (exit_code, stderr)."""
    cp = subprocess.run(
        [sys.executable, str(_LINT_SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
    )
    return cp.returncode, cp.stderr


def test_lint_passes_on_real_codebase() -> None:
    """Real backend/src must currently be sole-mutator clean (Sprint 55.3 Day 0 grep-zero baseline)."""
    backend_src = _PROJECT_ROOT / "backend" / "src"
    rc, stderr = _run_lint(backend_src)
    assert rc == 0, f"sole-mutator regression on real codebase:\n{stderr}"


def test_lint_fails_on_injected_violation(tmp_path: Path) -> None:
    """Inject a violation into a temp file; lint must exit 1 + report it."""
    bad_file = tmp_path / "bad_caller.py"
    bad_file.write_text(
        "def append_msg(state, msg):\n"
        "    state.messages.append(msg)\n"  # forbidden
    )
    rc, stderr = _run_lint(tmp_path)
    assert rc == 1
    assert "state.messages.append" in stderr
    assert "bad_caller.py" in stderr


def test_lint_whitelists_reducer(tmp_path: Path) -> None:
    """Mutation inside agent_harness/state_mgmt/reducer.py must NOT trigger violation."""
    reducer_dir = tmp_path / "agent_harness" / "state_mgmt"
    reducer_dir.mkdir(parents=True)
    reducer = reducer_dir / "reducer.py"
    reducer.write_text(
        "def apply(state, event):\n"
        "    state.messages.append(event)  # legitimate sole-mutator path\n"
        "    return state\n"
    )
    rc, stderr = _run_lint(tmp_path)
    assert rc == 0, f"whitelist failed; stderr:\n{stderr}"


@pytest.mark.parametrize(
    "pattern,line",
    [
        ("state.scratchpad", "state.scratchpad['key'] = 'value'\n"),
        ("state.tool_calls.append", "state.tool_calls.append(tc)\n"),
        ("state.user_input =", "state.user_input = 'new'\n"),
    ],
)
def test_lint_catches_other_forbidden_patterns(tmp_path: Path, pattern: str, line: str) -> None:
    """All 4 forbidden patterns are caught (parametric coverage of remaining 3)."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text(line)
    rc, stderr = _run_lint(tmp_path)
    assert rc == 1, f"pattern {pattern!r} not caught"
    assert pattern in stderr or pattern.replace(" =", "") in stderr
