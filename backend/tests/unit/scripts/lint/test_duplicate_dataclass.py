"""Tests for scripts/lint/check_duplicate_dataclass.py — PASS + FAIL cases."""

from __future__ import annotations

# Import the script directly using importlib because it lives outside src/.
import importlib.util
from pathlib import Path


def _load_lint_module() -> object:
    repo_root = (
        Path(__file__).resolve().parents[5]
    )  # …/backend/tests/unit/scripts/lint -> repo
    script = repo_root / "scripts" / "lint" / "check_duplicate_dataclass.py"
    spec = importlib.util.spec_from_file_location("check_dup", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(tmp: Path, name: str, content: str) -> None:
    (tmp / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp / name).write_text(content, encoding="utf-8")


def test_no_duplicate_passes(tmp_path: Path) -> None:
    mod = _load_lint_module()
    _write(
        tmp_path,
        "tools/spec.py",
        "from dataclasses import dataclass\n@dataclass\nclass ToolSpec: ...\n",
    )
    _write(
        tmp_path,
        "memory/types.py",
        "from dataclasses import dataclass\n@dataclass\nclass MemoryHint: ...\n",
    )
    occurrences = mod.scan_directory(tmp_path)  # type: ignore[attr-defined]
    duplicates = mod.find_duplicates(occurrences)  # type: ignore[attr-defined]
    assert duplicates == {}


def test_duplicate_fails(tmp_path: Path) -> None:
    mod = _load_lint_module()
    _write(
        tmp_path,
        "tools/spec.py",
        "from dataclasses import dataclass\n@dataclass\nclass ToolSpec: ...\n",
    )
    _write(
        tmp_path,
        "subagent/tools.py",  # same dataclass name in another category
        "from dataclasses import dataclass\n@dataclass\nclass ToolSpec: ...\n",
    )
    occurrences = mod.scan_directory(tmp_path)  # type: ignore[attr-defined]
    duplicates = mod.find_duplicates(occurrences)  # type: ignore[attr-defined]
    assert "ToolSpec" in duplicates
    assert len(duplicates["ToolSpec"]) == 2
