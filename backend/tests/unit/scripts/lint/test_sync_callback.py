"""Tests for scripts/lint/check_sync_callback.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module() -> object:
    repo_root = Path(__file__).resolve().parents[5]
    script = repo_root / "scripts" / "lint" / "check_sync_callback.py"
    spec = importlib.util.spec_from_file_location("check_sync", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _w(tmp: Path, p: str, body: str) -> None:
    (tmp / p).parent.mkdir(parents=True, exist_ok=True)
    (tmp / p).write_text(body, encoding="utf-8")


def test_async_concrete_matches_async_abstract_passes(tmp_path: Path) -> None:
    mod = _load_module()
    _w(
        tmp_path,
        "abc_def.py",
        "from abc import ABC, abstractmethod\n"
        "class MyABC(ABC):\n"
        "    @abstractmethod\n"
        "    async def chat(self) -> str: ...\n"
        "class MyImpl(MyABC):\n"
        "    async def chat(self) -> str:\n"
        "        return 'ok'\n",
    )
    violations = mod.find_violations(tmp_path)  # type: ignore[attr-defined]
    assert violations == []


def test_sync_concrete_overriding_async_abstract_fails(tmp_path: Path) -> None:
    mod = _load_module()
    _w(
        tmp_path,
        "abc_def.py",
        "from abc import ABC, abstractmethod\n"
        "class MyABC(ABC):\n"
        "    @abstractmethod\n"
        "    async def chat(self) -> str: ...\n"
        "class BadImpl(MyABC):\n"
        "    def chat(self) -> str:\n"
        "        return 'bad'\n",
    )
    violations = mod.find_violations(tmp_path)  # type: ignore[attr-defined]
    assert len(violations) == 1
    _path, _lineno, cls, method, kind = violations[0]
    assert cls == "BadImpl"
    assert method == "chat"
    assert "abstract async, concrete sync" == kind
