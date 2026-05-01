"""
File: backend/tests/integration/agent_harness/tools/test_sandbox_isolation.py
Purpose: P0 #17 — DockerSandbox isolation acceptance tests (RCE prevention).
Category: Tests / Integration / Agent harness / Tools
Scope: Sprint 52.5 P0 #17 (W4P-3 audit)

Description:
    These tests speak to the real Docker daemon and exercise the
    isolation guarantees DockerSandbox claims. Skipped automatically
    when Docker isn't reachable (CI without Docker-in-Docker).

    Each test runs a hostile Python snippet inside the sandbox and
    asserts the result reflects the expected isolation:

    1. test_sandbox_does_not_leak_host_filesystem
       os.listdir("/") returns the container's tiny rootfs, NOT the
       host's directory tree. On Windows, this proves we don't see
       /c, /Users, etc.; on Linux, it proves no bind mount escape.

    2. test_sandbox_blocks_network_when_network_blocked_true
       socket.connect("8.8.8.8", 53) raises (no route). Sanity-checks
       the --network=none flag is real, not decorative like the V1
       SubprocessSandbox `# noqa: ARG002` knob.

    3. test_sandbox_runs_as_unprivileged_user
       os.getuid() == 65534. RCE inside user code can't escalate.

    4. test_sandbox_kills_runaway_via_timeout
       infinite loop killed; killed_by_timeout=True; duration capped.

    5. test_sandbox_memory_limit_enforced
       allocating 200MB inside 64MB cap → OOM exit, exit_code != 0.

    6. test_sandbox_perf_baseline_under_500ms
       10-run avg startup overhead under 500ms (W4P-3 target).

    7. test_sandbox_filesystem_read_only
       Write to / fails (rootfs read_only); /tmp succeeds (tmpfs).

Created: 2026-05-01 (Sprint 52.5 P0 #17)

Related:
    - claudedocs/5-status/V2-AUDIT-W4P-3-PHASE51-1.md (audit source)
    - .claude/rules/observability-instrumentation.md
    - docker/sandbox/Dockerfile
    - backend/src/agent_harness/tools/sandbox.py
"""

from __future__ import annotations

import statistics
import time

import pytest

from agent_harness.tools.sandbox import DockerSandbox


def _docker_reachable() -> bool:
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not _docker_reachable(),
    reason="Docker daemon unreachable — DockerSandbox integration tests skipped.",
)


@pytest.fixture(scope="module")
def sandbox() -> DockerSandbox:
    """Single DockerSandbox per test module — re-uses the SDK client."""
    return DockerSandbox()


# Test 1 -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_sandbox_does_not_leak_host_filesystem(sandbox: DockerSandbox) -> None:
    """W4P-3 audit's smoking gun: pre-fix, os.listdir('C:/') from inside
    the SubprocessSandbox returned the Windows host fs. DockerSandbox
    must show only the container rootfs."""
    code = "import os, json; print(json.dumps(sorted(os.listdir('/'))))"
    result = await sandbox.execute(code, timeout_seconds=10, memory_mb=64)
    assert result.exit_code == 0, f"stderr={result.stderr!r}"
    listing = result.stdout.strip()
    # Container rootfs is small + uniform. Host paths like Users/Windows/Program
    # Files (Windows) or home/var/etc.host (Linux bind-mount escape) MUST NOT
    # appear. We assert the listing matches the python:3.12-slim shape.
    assert "sandbox" in listing  # workdir we created in the Dockerfile
    assert ".dockerenv" in listing  # only present inside containers
    # Negative checks against typical host artefacts
    assert "Users" not in listing  # Windows host
    assert "Program Files" not in listing  # Windows host
    assert "host" not in listing  # arbitrary leaked-mount tell


# Test 2 -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_sandbox_blocks_network_when_network_blocked_true(
    sandbox: DockerSandbox,
) -> None:
    """--network=none must be real. Pre-fix, network_blocked was a doc-only
    flag (W4P-3 audit: `# noqa: ARG002 — doc-only knob`)."""
    code = "import socket; s = socket.socket(); s.settimeout(2); " "s.connect(('8.8.8.8', 53))"
    result = await sandbox.execute(code, timeout_seconds=10, memory_mb=64, network_blocked=True)
    # Connection MUST fail. We accept any non-zero exit (different OS error
    # codes raise different exceptions). What we explicitly DON'T tolerate
    # is exit_code==0 (which would prove the connect succeeded).
    assert result.exit_code != 0, (
        f"connect succeeded inside network=none sandbox — leak! "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


# Test 3 -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_sandbox_runs_as_unprivileged_user(sandbox: DockerSandbox) -> None:
    """Code runs as uid 65534 (nobody). Defence in depth against RCE."""
    code = "import os; print(os.getuid())"
    result = await sandbox.execute(code, timeout_seconds=10, memory_mb=64)
    assert result.exit_code == 0
    assert result.stdout.strip() == "65534"


# Test 4 -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_sandbox_kills_runaway_via_timeout(sandbox: DockerSandbox) -> None:
    """Infinite loop killed via container kill() after timeout."""
    code = "while True: pass"
    t0 = time.monotonic()
    result = await sandbox.execute(code, timeout_seconds=2, memory_mb=64)
    elapsed = time.monotonic() - t0
    assert result.killed_by_timeout is True
    # Should be killed close to the timeout (within Docker overhead window).
    assert elapsed < 8.0, f"timeout enforcement slow: {elapsed:.2f}s"
    # exit_code surfaces as -1 / non-zero on a killed container.
    assert result.exit_code != 0


# Test 5 -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_sandbox_memory_limit_enforced(sandbox: DockerSandbox) -> None:
    """Allocating beyond mem_limit triggers OOM kill."""
    # Allocate 200MB inside a 64MB cap. List of bytes objects is the most
    # Docker-cgroup-friendly way to force RSS growth.
    code = (
        "x = []\n"
        "for _ in range(200):\n"
        "    x.append(b'A' * (1024*1024))\n"
        "print('survived')\n"
    )
    result = await sandbox.execute(code, timeout_seconds=15, memory_mb=64)
    assert result.exit_code != 0, (
        f"sandbox survived 200MB alloc inside 64MB cap! " f"stdout={result.stdout!r}"
    )
    assert "survived" not in result.stdout


# Test 6 -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_sandbox_perf_baseline_under_500ms(sandbox: DockerSandbox) -> None:
    """W4P-3 audit perf target: container startup overhead < 500ms.

    Run a no-op 10 times; the average must be under 500ms. Allows
    ~750ms for the first run (cold cache); later runs amortise.
    """
    timings: list[float] = []
    for _ in range(10):
        result = await sandbox.execute("pass", timeout_seconds=5, memory_mb=64)
        assert result.exit_code == 0
        timings.append(result.duration_seconds)
    avg = statistics.mean(timings[1:])  # drop cold start
    assert avg < 0.5, (
        f"DockerSandbox startup avg {avg*1000:.0f}ms exceeds 500ms target. "
        f"Per-run timings (s): {[round(t, 3) for t in timings]}"
    )


# Test 7 -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_sandbox_filesystem_read_only(sandbox: DockerSandbox) -> None:
    """Rootfs is read-only; /tmp is tmpfs (writable)."""
    code = (
        "import os\n"
        "errors = []\n"
        "try:\n"
        "    open('/forbidden.txt', 'w').write('x')\n"
        "except OSError as e:\n"
        "    errors.append(f'root:{type(e).__name__}')\n"
        "try:\n"
        "    open('/tmp/ok.txt', 'w').write('x')\n"
        "    os.unlink('/tmp/ok.txt')\n"
        "    errors.append('tmp:OK')\n"
        "except OSError as e:\n"
        "    errors.append(f'tmp:{type(e).__name__}')\n"
        "print('|'.join(errors))\n"
    )
    result = await sandbox.execute(code, timeout_seconds=10, memory_mb=64)
    assert result.exit_code == 0, f"stderr={result.stderr!r}"
    out = result.stdout.strip()
    # Root write must fail; /tmp write must succeed.
    assert "root:" in out
    assert "OK" not in out.split("|")[0]  # root path failed
    assert "tmp:OK" in out
