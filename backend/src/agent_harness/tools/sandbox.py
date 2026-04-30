"""
File: backend/src/agent_harness/tools/sandbox.py
Purpose: Sandbox backend — isolated subprocess execution for python_sandbox tool.
Category: 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 3.1 + 3.2

Description:
    `SandboxBackend` is an ABC for sandboxed code execution. Sprint 51.1
    ships `SubprocessSandbox` (best-effort isolation via OS primitives);
    `DockerSandbox` lands in 51.x or Phase 53.x (CARRY-022).

    SubprocessSandbox isolation guarantees (51.1 scope):
      1. WALL-TIME TIMEOUT — `asyncio.wait_for()` kills runaway processes.
         Exit reflected in `SandboxResult.killed_by_timeout`.
      2. MEMORY LIMIT (POSIX only) — `RLIMIT_AS` via `preexec_fn`. Excess
         allocation triggers process death (exit_code != 0). Windows
         skipped in 51.1 (Job Object support is CARRY-022).
      3. CPU LIMIT (POSIX only) — `RLIMIT_CPU` set to 2x timeout_seconds
         as a backstop in case wall-time wait_for is delayed.
      4. ISOLATED CWD — every execution runs inside a fresh
         `tempfile.TemporaryDirectory()` cleaned up on completion. This
         contains relative-path writes; absolute-path filesystem
         isolation requires namespaces (CARRY-022 Docker).

    Out of scope (51.1):
      - Network blocking (`network_blocked` param accepted but not
        enforced — requires netns / iptables / Docker. Doc-only knob).
      - Filesystem chroot / namespacing.
      - User namespace remapping.

Key Components:
    - SandboxBackend: ABC `execute(code, ...) -> SandboxResult`.
    - SandboxResult: stdout / stderr / exit_code / duration / killed_by_timeout.
    - SubprocessSandbox: production impl using asyncio.subprocess.

Owner: 01-eleven-categories-spec.md §範疇 2
Single-source: 17.md §2.1

Created: 2026-04-30 (Sprint 51.1 Day 3.1)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 51.1 Day 3.1+3.2) — ABC +
      SandboxResult + SubprocessSandbox with POSIX rlimit + tempdir CWD
      + asyncio.wait_for timeout.

Related:
    - .exec_tools (Day 3.4 python_sandbox ToolSpec + handler consumes this)
    - sprint-51-1-plan.md §決策 3 / §決策 4
    - .claude/rules/observability-instrumentation.md (sandbox does NOT
      emit metrics directly; ToolExecutorImpl wraps the call and emits
      tool_execution_duration_seconds with tool_name=python_sandbox)
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SandboxResult:
    """Outcome of `SandboxBackend.execute()`. All sandboxes return this shape."""

    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    killed_by_timeout: bool


class SandboxBackend(ABC):
    """Abstract sandbox: run user code with isolation + resource limits."""

    @abstractmethod
    async def execute(
        self,
        code: str,
        *,
        timeout_seconds: float,
        memory_mb: int,
        network_blocked: bool = True,
    ) -> SandboxResult: ...


class SubprocessSandbox(SandboxBackend):
    """Best-effort sandbox: subprocess + tempdir cwd + POSIX rlimit + wall timeout.

    Trade-off vs Docker: simpler/faster bring-up, weaker isolation. Acceptable
    for 51.1 (LLM-generated python eval); Phase 53.x replaces with Docker.
    """

    async def execute(
        self,
        code: str,
        *,
        timeout_seconds: float,
        memory_mb: int,
        network_blocked: bool = True,  # noqa: ARG002 — 51.1 unenforced; CARRY-022
    ) -> SandboxResult:
        with tempfile.TemporaryDirectory(prefix="sbx_") as cwd:
            code_file = Path(cwd) / "main.py"
            code_file.write_text(code, encoding="utf-8")

            popen_kwargs: dict[str, Any] = {}
            if sys.platform != "win32":
                popen_kwargs["preexec_fn"] = _make_posix_limiter(memory_mb, timeout_seconds)

            t0 = time.monotonic()
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(code_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                **popen_kwargs,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_seconds
                )
                killed = False
            except asyncio.TimeoutError:
                process.kill()
                # drain pipes after kill so the OS releases handles
                stdout_b, stderr_b = await process.communicate()
                killed = True

            duration = time.monotonic() - t0
            exit_code = process.returncode if process.returncode is not None else -1
            return SandboxResult(
                stdout=stdout_b.decode("utf-8", errors="replace"),
                stderr=stderr_b.decode("utf-8", errors="replace"),
                exit_code=exit_code,
                duration_seconds=duration,
                killed_by_timeout=killed,
            )


def _make_posix_limiter(memory_mb: int, timeout_seconds: float) -> Any:
    """Build a `preexec_fn` that applies RLIMIT_AS + RLIMIT_CPU on POSIX.

    Returned closure is invoked in the forked child before the spawned
    interpreter starts; errors here propagate as failed startup which
    surfaces as exit_code != 0.
    """

    def _apply() -> None:
        import resource  # POSIX-only; mypy on Windows lacks attrs.

        mem_bytes = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))  # type: ignore[attr-defined]
        cpu_seconds = max(1, int(timeout_seconds * 2))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))  # type: ignore[attr-defined]

    return _apply
