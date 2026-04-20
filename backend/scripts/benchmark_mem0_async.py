"""Mem0 async wrapping event-loop lag benchmark (Sprint 172 AC-7).

Measures whether the Sprint 172 executor wrapping prevents mem0's
synchronous SDK calls from starving the asyncio event loop under
concurrent load. Target: P95 lag < 10ms.

How it works:
  - Spawn N concurrent ``mem0_client.search_memory()`` coroutines
  - Simultaneously run a lightweight "heartbeat" coroutine that
    records the gap between ``asyncio.sleep(0.01)`` intervals
  - If mem0's sync call blocks the loop, the heartbeat gap grows;
    if it's properly wrapped in an executor, the gap stays ~10ms

Usage:
    python backend/scripts/benchmark_mem0_async.py --mode pre
    python backend/scripts/benchmark_mem0_async.py --mode post
    python backend/scripts/benchmark_mem0_async.py --validate

Artifact path: ``claudedocs/5-status/sprint-172-baseline-{pre|post}.json``
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.integrations.memory.mem0_client import Mem0Client  # noqa: E402
from src.integrations.memory.types import (  # noqa: E402
    MemoryConfig,
    MemorySearchQuery,
)

ARTIFACT_DIR = REPO_ROOT.parent / "claudedocs" / "5-status"
BASELINE_PRE = ARTIFACT_DIR / "sprint-172-baseline-pre.json"
BASELINE_POST = ARTIFACT_DIR / "sprint-172-baseline-post.json"
DEFAULT_CONCURRENCY = 100
HEARTBEAT_INTERVAL_MS = 10
P95_GATE_MS = 10  # post event loop lag P95 must be <= 10ms


async def _heartbeat(stop_event: asyncio.Event, lags_ms: list[float]) -> None:
    """Records observed gap between 10ms sleeps — our event-loop-lag probe."""
    while not stop_event.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(HEARTBEAT_INTERVAL_MS / 1000.0)
        actual_ms = (time.perf_counter() - t0) * 1000.0
        # Lag = actual - target; guard against negative scheduling noise
        lag = max(0.0, actual_ms - HEARTBEAT_INTERVAL_MS)
        lags_ms.append(lag)


async def _run(concurrency: int) -> dict[str, Any]:
    config = MemoryConfig()
    client = Mem0Client(config=config)
    await client.initialize()

    bench_user = f"bench-mem0-{uuid.uuid4().hex[:8]}"
    stop = asyncio.Event()
    lags: list[float] = []

    heartbeat_task = asyncio.create_task(_heartbeat(stop, lags))

    try:
        # Allow heartbeat to warm up
        await asyncio.sleep(0.2)

        async def _one_search(i: int) -> float:
            q = MemorySearchQuery(
                query=f"benchmark probe {i}",
                user_id=bench_user,
                limit=5,
            )
            t0 = time.perf_counter()
            await client.search_memory(q)
            return (time.perf_counter() - t0) * 1000.0

        t_total = time.perf_counter()
        latencies = await asyncio.gather(
            *(_one_search(i) for i in range(concurrency)),
            return_exceptions=True,
        )
        wall_ms = (time.perf_counter() - t_total) * 1000.0

        # Filter exceptions (mem0 may be unreachable in dev)
        ok_latencies = [v for v in latencies if isinstance(v, (int, float))]
        if not ok_latencies:
            raise RuntimeError("All mem0 search attempts failed — check infra / credentials")
    finally:
        stop.set()
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        await client.close()

    lags.sort()
    ok_latencies.sort()
    n_lag = len(lags)
    n_lat = len(ok_latencies)
    return {
        "concurrency": concurrency,
        "mem0_ops_succeeded": n_lat,
        "mem0_op_latency_ms": {
            "p50": round(statistics.median(ok_latencies), 3) if ok_latencies else None,
            "p95": (round(ok_latencies[int(n_lat * 0.95)], 3) if n_lat > 10 else None),
            "p99": (round(ok_latencies[int(n_lat * 0.99)], 3) if n_lat > 20 else None),
        },
        "event_loop_lag_ms": {
            "samples": n_lag,
            "p50": round(statistics.median(lags), 3) if lags else None,
            "p95": round(lags[int(n_lag * 0.95)], 3) if n_lag > 10 else None,
            "p99": round(lags[int(n_lag * 0.99)], 3) if n_lag > 20 else None,
            "max": round(max(lags), 3) if lags else None,
        },
        "wall_clock_ms": round(wall_ms, 3),
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_artifact(data: dict, path: Path, mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sprint": 172,
        "phase": 48,
        "mode": mode,
        "gate_p95_ms": P95_GATE_MS,
        "git_ref": os.environ.get("GIT_COMMIT", "unknown"),
        **data,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[ok] Wrote {mode} baseline → {path}")
    lag = data.get("event_loop_lag_ms", {})
    print(
        f"     loop lag P50={lag.get('p50')}ms  "
        f"P95={lag.get('p95')}ms  P99={lag.get('p99')}ms  "
        f"max={lag.get('max')}ms"
    )


def _validate() -> int:
    if not BASELINE_POST.exists():
        print(f"[err] Missing {BASELINE_POST}", file=sys.stderr)
        return 1
    post = json.loads(BASELINE_POST.read_text(encoding="utf-8"))
    p95 = post.get("event_loop_lag_ms", {}).get("p95")
    if p95 is None:
        print("[err] post baseline missing P95 lag", file=sys.stderr)
        return 1
    print(f"Post event loop lag P95: {p95} ms  (gate: <= {P95_GATE_MS}ms)")
    if p95 <= P95_GATE_MS:
        print("[ok] AC-7 event loop lag gate PASSED")
        return 0
    print("[err] AC-7 event loop lag gate FAILED", file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["pre", "post"], help="Capture baseline")
    parser.add_argument("--validate", action="store_true", help="Enforce AC-7 gate")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrent mem0 ops (default: {DEFAULT_CONCURRENCY})",
    )
    args = parser.parse_args()

    if args.validate:
        return _validate()
    if not args.mode:
        parser.error("--mode required unless --validate")

    try:
        stats = asyncio.run(_run(args.concurrency))
    except Exception as exc:
        print(f"[err] benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    target = BASELINE_PRE if args.mode == "pre" else BASELINE_POST
    _write_artifact(stats, target, args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
