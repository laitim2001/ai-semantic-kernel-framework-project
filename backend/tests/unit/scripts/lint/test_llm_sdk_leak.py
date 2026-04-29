"""Tests for scripts/lint/check_llm_sdk_leak.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module() -> object:
    repo_root = Path(__file__).resolve().parents[5]
    script = repo_root / "scripts" / "lint" / "check_llm_sdk_leak.py"
    spec = importlib.util.spec_from_file_location("check_leak", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _w(tmp: Path, p: str, body: str) -> None:
    (tmp / p).parent.mkdir(parents=True, exist_ok=True)
    (tmp / p).write_text(body, encoding="utf-8")


def test_no_leak_in_agent_harness_passes(tmp_path: Path) -> None:
    mod = _load_module()
    # agent_harness uses ChatClient ABC, no SDK
    _w(
        tmp_path,
        "agent_harness/orchestrator_loop/loop.py",
        "from adapters._base import ChatClient\n",
    )
    # adapter for openai SDK is allowed
    _w(
        tmp_path,
        "adapters/azure_openai/adapter.py",
        "from openai import AsyncAzureOpenAI\n",
    )
    violations = mod.find_violations(tmp_path)  # type: ignore[attr-defined]
    assert violations == []


def test_leak_in_agent_harness_fails(tmp_path: Path) -> None:
    mod = _load_module()
    _w(
        tmp_path,
        "agent_harness/orchestrator_loop/loop.py",
        "import openai\n",  # forbidden!
    )
    violations = mod.find_violations(tmp_path)  # type: ignore[attr-defined]
    assert len(violations) == 1
    v = violations[0]
    assert v.sdk == "openai"
    assert "loop.py" in str(v.file)


def test_leak_in_business_domain_fails(tmp_path: Path) -> None:
    mod = _load_module()
    _w(
        tmp_path,
        "business_domain/patrol/runner.py",
        "from anthropic import Anthropic\n",
    )
    violations = mod.find_violations(tmp_path)  # type: ignore[attr-defined]
    assert len(violations) == 1
    assert violations[0].sdk == "anthropic"
