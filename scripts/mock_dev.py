#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File: scripts/mock_dev.py
Purpose: Standalone start/stop/status helper for mock_services FastAPI app (port 8001).
Category: Dev tooling / mock backend
Scope: Phase 51 / Sprint 51.0 Day 1.7

Description:
    Independent of scripts/dev.py orchestration. Avoids weaving mock_services into
    ServiceType enum (which would require ~5 files of cross-cutting changes).
    `python scripts/dev.py mock <cmd>` shim dispatches here.

Commands:
    python scripts/mock_dev.py start    — launch uvicorn on 8001
    python scripts/mock_dev.py stop     — kill the saved PID
    python scripts/mock_dev.py status   — check process + /health endpoint

Created: 2026-04-30 (Sprint 51.0 Day 1)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
PID_FILE = PROJECT_ROOT / ".mock_services.pid"
PORT = 8001
HEALTH_URL = f"http://localhost:{PORT}/health"


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _is_alive(pid: int) -> bool:
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _ping_health() -> tuple[bool, str]:
    try:
        with urlopen(HEALTH_URL, timeout=2) as resp:
            return resp.status == 200, resp.read().decode("utf-8")
    except URLError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def cmd_start() -> int:
    existing = _read_pid()
    if existing is not None and _is_alive(existing):
        print(f"[mock] already running (pid={existing})")
        return 0

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_SRC) + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "mock_services.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(PORT),
    ]
    print(f"[mock] starting: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=BACKEND_SRC,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        ),
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"[mock] started pid={proc.pid}; polling {HEALTH_URL}")

    for _ in range(20):
        time.sleep(0.5)
        ok, _ = _ping_health()
        if ok:
            print(f"[mock] healthy on port {PORT}")
            return 0
    print("[mock] WARNING: did not respond to /health within 10s")
    return 1


def cmd_stop() -> int:
    pid = _read_pid()
    if pid is None:
        print("[mock] no PID file; nothing to stop")
        return 0
    if not _is_alive(pid):
        print(f"[mock] pid {pid} already dead; cleaning up PID file")
        PID_FILE.unlink(missing_ok=True)
        return 0
    print(f"[mock] killing pid {pid}")
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False)
        else:
            os.kill(pid, signal.SIGTERM)
            for _ in range(10):
                time.sleep(0.3)
                if not _is_alive(pid):
                    break
            else:
                os.kill(pid, signal.SIGKILL)
    finally:
        PID_FILE.unlink(missing_ok=True)
    return 0


def cmd_status() -> int:
    pid = _read_pid()
    if pid is None or not _is_alive(pid):
        print(f"[mock] stopped (port {PORT})")
        return 1
    ok, body = _ping_health()
    if ok:
        print(f"[mock] running pid={pid} health=ok body={body}")
        return 0
    print(f"[mock] running pid={pid} but /health unreachable: {body}")
    return 1


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in {"start", "stop", "status"}:
        print("usage: python scripts/mock_dev.py {start|stop|status}")
        return 2
    return {"start": cmd_start, "stop": cmd_stop, "status": cmd_status}[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
