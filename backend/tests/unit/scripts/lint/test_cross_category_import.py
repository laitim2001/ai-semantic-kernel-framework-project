"""Tests for scripts/lint/check_cross_category_import.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module() -> object:
    repo_root = Path(__file__).resolve().parents[5]
    script = repo_root / "scripts" / "lint" / "check_cross_category_import.py"
    spec = importlib.util.spec_from_file_location("check_cross", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _w(tmp: Path, p: str, body: str) -> None:
    (tmp / p).parent.mkdir(parents=True, exist_ok=True)
    (tmp / p).write_text(body, encoding="utf-8")


def test_legal_imports_pass(tmp_path: Path) -> None:
    mod = _load_module()
    # Cat 1 importing public surface (Cat 2 package or _contracts) is fine.
    _w(
        tmp_path,
        "orchestrator_loop/loop.py",
        "from agent_harness.tools import ToolRegistry\n"
        "from agent_harness._contracts import ChatRequest\n",
    )
    _w(tmp_path, "tools/__init__.py", "")
    violations = mod.find_violations(tmp_path)  # type: ignore[attr-defined]
    assert violations == []


def test_private_cross_category_import_fails(tmp_path: Path) -> None:
    mod = _load_module()
    # Cat 1 reaches into Cat 2's private internal module — forbidden.
    _w(
        tmp_path,
        "orchestrator_loop/loop.py",
        "from agent_harness.tools.registry_internals import _PrivateClass\n",
    )
    _w(tmp_path, "tools/registry_internals.py", "class _PrivateClass: ...\n")
    violations = mod.find_violations(tmp_path)  # type: ignore[attr-defined]
    assert len(violations) == 1
    path, lineno, target = violations[0]
    assert path.name == "loop.py"
    assert "registry_internals" in target
