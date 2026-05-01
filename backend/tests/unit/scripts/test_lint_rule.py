"""AP-8 lint rule tests. Sprint 52.2 Day 4.2 — 5 tests.

Drives `scripts/check_promptbuilder_usage.py` against synthetic fixture trees
to verify:
  1. chat() without build() in same function -> exit 1
  2. chat() with prior build() in same function -> exit 0
  3. tests/ allowlist short-circuit
  4. _testing/ allowlist short-circuit
  5. --dry-run never exits non-zero
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

LINT_SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "scripts"
    / "check_promptbuilder_usage.py"
)


def _run_lint(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--root", str(root), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(body), encoding="utf-8")


def test_detects_chat_without_build(tmp_path: Path) -> None:
    """chat() without prior build() in same function -> exit 1."""
    _write(
        tmp_path / "loop_bad.py",
        """
        async def run(self):
            response = await self._chat_client.chat(request)
            return response
        """,
    )
    result = _run_lint(tmp_path)
    assert result.returncode == 1
    assert "AP-8 violation" in result.stdout
    assert "loop_bad.py" in result.stdout


def test_allows_chat_with_prior_build(tmp_path: Path) -> None:
    """chat() with build() in the same function -> exit 0."""
    _write(
        tmp_path / "loop_good.py",
        """
        async def run(self):
            artifact = await self._prompt_builder.build(state=state)
            response = await self._chat_client.chat(artifact.request)
            return response
        """,
    )
    result = _run_lint(tmp_path)
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "0 violations" in result.stdout


def test_allowlist_tests_directory(tmp_path: Path) -> None:
    """Files under tests/ are skipped even when chat() lacks build()."""
    _write(
        tmp_path / "tests" / "test_chat_direct.py",
        """
        async def test_something(client):
            return await client.chat(request)
        """,
    )
    result = _run_lint(tmp_path)
    assert result.returncode == 0
    assert "0 violations" in result.stdout


def test_allowlist_mock_clients(tmp_path: Path) -> None:
    """Files under _testing/ are skipped (mock chat clients)."""
    _write(
        tmp_path / "_testing" / "mock_clients.py",
        """
        async def chat(self, request):
            return canned_response
        async def caller():
            return await mock.chat(req)
        """,
    )
    result = _run_lint(tmp_path)
    assert result.returncode == 0
    assert "0 violations" in result.stdout


def test_dry_run_no_exit(tmp_path: Path) -> None:
    """--dry-run prints violations but exits 0."""
    _write(
        tmp_path / "loop_bad.py",
        """
        async def run(self):
            response = await self._chat_client.chat(request)
            return response
        """,
    )
    result = _run_lint(tmp_path, "--dry-run")
    assert result.returncode == 0
    assert "AP-8 violation" in result.stdout
    assert "[dry-run]" in result.stderr


def test_help_works() -> None:
    """Bonus sanity: --help renders without errors."""
    result = subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "AP-8 lint" in result.stdout
