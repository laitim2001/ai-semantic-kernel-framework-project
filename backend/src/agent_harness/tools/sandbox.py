"""
File: backend/src/agent_harness/tools/sandbox.py
Purpose: Sandbox backend — isolated execution for python_sandbox tool.
Category: 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 3.1 + 3.2 — Sprint 52.5 P0 #17 (DockerSandbox)

Description:
    `SandboxBackend` is an ABC for sandboxed code execution. Two
    implementations now ship side-by-side:

    - `DockerSandbox` (Sprint 52.5 P0 #17, RECOMMENDED): real isolation
      via short-lived containers. Cross-platform (Windows / macOS /
      Linux via Docker daemon). Per-exec hardening:
          --memory --cpus --network none|bridge --read-only
          --cap-drop ALL --user 65534:65534 --pids-limit 64
      Builds against `docker/sandbox/Dockerfile` (python:3.12-slim).

    - `SubprocessSandbox` (Sprint 51.1, LEGACY): best-effort via OS
      primitives. KEPT FOR DEV/TEST environments WITHOUT Docker
      daemon. POSIX rlimit + tempdir cwd + wall-time timeout.
      Audit (W4P-3) confirmed: decorative on Windows
      (resource.setrlimit POSIX-only); `os.listdir("C:/")` from
      inside the "sandbox" succeeded; network_blocked was a
      `# noqa: ARG002` doc-only flag. PRODUCTION DEPLOY MUST USE
      DockerSandbox.

    Default factory `default_sandbox()` returns DockerSandbox when
    Docker daemon is reachable; falls back to SubprocessSandbox + logs
    a WARNING when not (test environments / CI without Docker-in-
    Docker).

    DockerSandbox isolation guarantees:
      1. WALL-TIME TIMEOUT — container killed via `kill()` after
         `timeout_seconds`. Exit reflected in
         `SandboxResult.killed_by_timeout`.
      2. MEMORY LIMIT — Docker `mem_limit` enforced by cgroup; OOM kill
         surfaces as exit_code != 0 with stderr noting OOM.
      3. CPU LIMIT — Docker `cpu_quota` / `cpu_period`; kernel-enforced.
      4. FILESYSTEM ISOLATION — `read_only=True` rootfs + tmpfs `/tmp`.
         Host paths are NOT visible (no bind mounts). `os.listdir("/")`
         from inside the container returns container fs only.
      5. NETWORK ISOLATION — `network_mode="none"` blocks all egress
         when `network_blocked=True`; `bridge` allows when False.
      6. CAPABILITY DROP — `cap_drop=["ALL"]`. Container can't load
         kernel modules / mount fs / change uids.
      7. NON-ROOT — runs as uid 65534 (nobody). RCE in user code can't
         escalate within the container.
      8. PID LIMIT — `pids_limit=64` blocks fork bombs.

    SubprocessSandbox isolation (LEGACY, weaker):
      1. WALL-TIME TIMEOUT — `asyncio.wait_for()` kills runaway processes.
      2. MEMORY LIMIT (POSIX only) — `RLIMIT_AS` via `preexec_fn`.
         Windows: NOT ENFORCED.
      3. CPU LIMIT (POSIX only) — `RLIMIT_CPU` 2x timeout backstop.
      4. ISOLATED CWD — fresh `tempfile.TemporaryDirectory()`.
      ✗ Network blocking — UNENFORCED. PRODUCTION-UNSAFE.
      ✗ Filesystem chroot — host fs visible.

Key Components:
    - SandboxBackend: ABC `execute(code, ...) -> SandboxResult`.
    - SandboxResult: stdout / stderr / exit_code / duration / killed_by_timeout.
    - DockerSandbox: production impl using docker SDK (Sprint 52.5 P0 #17).
    - SubprocessSandbox: legacy impl using asyncio.subprocess (51.1).
    - default_sandbox(): factory choosing Docker when reachable.

Owner: 01-eleven-categories-spec.md §範疇 2
Single-source: 17.md §2.1

Created: 2026-04-30 (Sprint 51.1 Day 3.1)
Last Modified: 2026-05-01

Modification History (newest-first):
    - 2026-05-01: Sprint 52.5 P0 #17 (W4P-3 audit): add DockerSandbox
      class with --memory --cpus --network=none --read-only --cap-drop=ALL
      hardening; add default_sandbox() factory; mark SubprocessSandbox
      LEGACY (not production-safe — kept for dev/CI without Docker).
      CARRY-022 closed.
    - 2026-04-30: Initial creation (Sprint 51.1 Day 3.1+3.2) — ABC +
      SandboxResult + SubprocessSandbox with POSIX rlimit + tempdir CWD
      + asyncio.wait_for timeout.

Related:
    - .exec_tools (Day 3.4 python_sandbox ToolSpec + handler consumes this)
    - docker/sandbox/Dockerfile — python:3.12-slim + non-root user image.
    - sprint-51-1-plan.md §決策 3 / §決策 4
    - claudedocs/5-status/V2-AUDIT-W4P-3-PHASE51-1.md (audit source for #17)
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


# =====================================================================
# DockerSandbox — Sprint 52.5 P0 #17 (production-safe, cross-platform)
# =====================================================================

# Default image tag built from docker/sandbox/Dockerfile. Operators can
# override via DOCKER_SANDBOX_IMAGE env var or DockerSandbox(image=...).
_DEFAULT_IMAGE = "ipa-v2-sandbox:latest"


class DockerSandbox(SandboxBackend):
    """Production sandbox: short-lived Docker container per execution.

    Hardening (per `.claude/rules/observability-instrumentation.md` and
    Sprint 52.5 P0 #17 spec):

    - mem_limit + cpu_quota: enforced by cgroup (kernel-level)
    - network_mode="none" or "bridge" (per `network_blocked` flag)
    - read_only=True rootfs; tmpfs /tmp (writable but capped at 64 MB)
    - cap_drop=["ALL"]: no capabilities at all
    - user="65534:65534" (nobody): non-root child
    - pids_limit=64: blocks fork bombs
    - security_opt=["no-new-privileges"]: prevents setuid escalation
    - auto_remove=True: container deletes after exec; no residual state

    Cross-platform: works on Windows / macOS / Linux via Docker daemon.
    `os.listdir("C:/")` from inside (Windows host) returns the container's
    `/` contents, NOT the host fs.

    Constructor lazy-initialises the docker client; clients without a
    reachable daemon raise on first `execute()` call (callers should
    use `default_sandbox()` to fall back to SubprocessSandbox).
    """

    def __init__(
        self,
        *,
        image: str | None = None,
        client: Any | None = None,
    ) -> None:
        # `image` defaults to DOCKER_SANDBOX_IMAGE env or _DEFAULT_IMAGE.
        # Operators wire this via deployment manifest; tests pin to a known
        # locally-built tag.
        import os

        self._image = image or os.environ.get("DOCKER_SANDBOX_IMAGE", _DEFAULT_IMAGE)
        # `client` injection point for tests; production lazy-loads SDK.
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            # Lazy import: keeps module import cheap when sandbox unused.
            import docker

            self._client = docker.from_env()
        return self._client

    async def execute(
        self,
        code: str,
        *,
        timeout_seconds: float,
        memory_mb: int,
        network_blocked: bool = True,
    ) -> SandboxResult:
        """Run `code` in an isolated container; return stdout/stderr/exit/duration.

        The container is created + started + waited-for + killed-on-timeout
        + removed. Total budget = timeout_seconds + ~500ms Docker startup
        overhead (per W4P-3 audit perf baseline target).

        `code` is fed as a `python -c <code>` argv; we do NOT mount any
        host directory (would expose host fs — defeats isolation).
        """
        # Wrap synchronous docker SDK calls in a thread to keep the loop
        # responsive (the SDK uses blocking HTTP to /var/run/docker.sock).
        return await asyncio.to_thread(
            self._execute_sync,
            code,
            timeout_seconds,
            memory_mb,
            network_blocked,
        )

    def _execute_sync(
        self,
        code: str,
        timeout_seconds: float,
        memory_mb: int,
        network_blocked: bool,
    ) -> SandboxResult:
        client = self._get_client()
        # cpu_period * cpu_quota = fraction of one CPU core.
        # 100_000 period + 50_000 quota = 0.5 cores (conservative; sandbox
        # workloads are LLM-prompted scripts, not numeric kernels).
        cpu_period = 100_000
        cpu_quota = 50_000

        t0 = time.monotonic()
        # Note: docker SDK's containers.run(detach=True) returns immediately;
        # we then wait() with timeout, kill on overshoot, and capture logs.
        container = client.containers.run(
            image=self._image,
            command=["python", "-c", code],
            detach=True,
            mem_limit=f"{memory_mb}m",
            cpu_period=cpu_period,
            cpu_quota=cpu_quota,
            network_mode="none" if network_blocked else "bridge",
            read_only=True,
            tmpfs={"/tmp": "size=64m,mode=1777"},
            cap_drop=["ALL"],
            user="65534:65534",
            pids_limit=64,
            security_opt=["no-new-privileges"],
            auto_remove=False,  # we'll remove() ourselves to capture logs
            stdout=True,
            stderr=True,
        )
        killed = False
        exit_code = -1
        try:
            # docker SDK exposes `requests` exceptions and (on Windows) named-pipe
            # ReadTimeoutError; we capture all of them as a single "timeout"
            # signal. Any other exception during wait() is escalated.
            from requests.exceptions import (
                ConnectionError as RequestsConnectionError,
                ReadTimeout,
            )
            from urllib3.exceptions import ReadTimeoutError

            try:
                wait_result = container.wait(timeout=timeout_seconds)
                exit_code = int(wait_result.get("StatusCode", -1))
            except (
                ReadTimeout,
                ReadTimeoutError,
                RequestsConnectionError,
                TimeoutError,
            ):
                # All "client side gave up waiting" paths -> treat as timeout
                # and kill the container. Windows named-pipe surfaces this as
                # ConnectionError (npipe Read timed out) rather than
                # ReadTimeout, hence the union.
                killed = True
                try:
                    container.kill()
                except Exception:  # noqa: BLE001
                    pass
                # Best-effort drain wait so logs reflect the killed state.
                try:
                    container.wait(timeout=5.0)
                except Exception:  # noqa: BLE001
                    pass
                exit_code = -1
            except Exception:  # noqa: BLE001
                # Unexpected — clean up before re-raising so we don't leak
                # the container.
                try:
                    container.kill()
                    container.remove(force=True)
                except Exception:  # noqa: BLE001
                    pass
                raise

            # Capture stdout/stderr (separate streams).
            stdout_b = container.logs(stdout=True, stderr=False)
            stderr_b = container.logs(stdout=False, stderr=True)
        finally:
            try:
                container.remove(force=True)
            except Exception:  # noqa: BLE001
                # Container may already be gone (auto_remove race); ignore.
                pass

        duration = time.monotonic() - t0
        return SandboxResult(
            stdout=stdout_b.decode("utf-8", errors="replace") if stdout_b else "",
            stderr=stderr_b.decode("utf-8", errors="replace") if stderr_b else "",
            exit_code=exit_code,
            duration_seconds=duration,
            killed_by_timeout=killed,
        )


# =====================================================================
# Factory — choose Docker when reachable, else fall back to Subprocess
# =====================================================================


def default_sandbox(*, image: str | None = None) -> SandboxBackend:
    """Return DockerSandbox if Docker daemon reachable, else SubprocessSandbox.

    Production deployments MUST run with Docker reachable (per
    .claude/rules/observability-instrumentation.md + W4P-3 audit).
    SubprocessSandbox fallback is for CI / test environments without
    Docker-in-Docker capability — it logs a WARNING so misconfigurations
    surface in operator logs.
    """
    import logging

    logger = logging.getLogger(__name__)
    try:
        import docker

        client = docker.from_env()
        # Cheap reachability check; raises if daemon not running.
        client.ping()
        return DockerSandbox(image=image, client=client)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "DockerSandbox unavailable (%s: %s); falling back to "
            "SubprocessSandbox. NOT production-safe — per W4P-3 audit, "
            "Windows hosts get effectively no isolation.",
            type(exc).__name__,
            exc,
        )
        return SubprocessSandbox()


__all__ = [
    "DockerSandbox",
    "SandboxBackend",
    "SandboxResult",
    "SubprocessSandbox",
    "default_sandbox",
]
