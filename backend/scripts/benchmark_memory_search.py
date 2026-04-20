"""Memory search latency benchmark for Sprint 170 AC-6.

Measures P50 / P95 / P99 latency of `UnifiedMemoryManager.search()` across
1000 iterations. Captures artifacts at `claudedocs/5-status/sprint-170-baseline-{pre|post}.json`.

CI gate: post-change P95 must be <= 105% of pre-change baseline.

Usage:
    # Pre-change baseline (run BEFORE any Sprint 170 code changes)
    python backend/scripts/benchmark_memory_search.py --mode pre

    # Post-change benchmark (run AFTER Sprint 170 code changes + tests pass)
    python backend/scripts/benchmark_memory_search.py --mode post

    # Validate regression gate (compare pre vs post)
    python backend/scripts/benchmark_memory_search.py --validate

Prerequisites:
    - Redis running on localhost:6379
    - Qdrant running on localhost:6333 (or QDRANT_PATH local)
    - Environment variables from backend/.env loaded
    - mem0 installed (MEM0_ENABLED=true or fallback seeding)

Exit codes:
    0 — Success; baseline captured or regression within gate
    1 — Benchmark failure or infrastructure not reachable
    2 — Regression gate failed (post P95 > pre P95 * 1.05)
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

# Add backend/src to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.integrations.memory.types import MemoryConfig, MemoryLayer, MemoryType  # noqa: E402
from src.integrations.memory.unified_memory import UnifiedMemoryManager  # noqa: E402

ARTIFACT_DIR = REPO_ROOT.parent / "claudedocs" / "5-status"
BASELINE_PRE = ARTIFACT_DIR / "sprint-170-baseline-pre.json"
BASELINE_POST = ARTIFACT_DIR / "sprint-170-baseline-post.json"
ITERATIONS = 1000
SEED_MEMORY_COUNT = 50
REGRESSION_GATE = 1.05  # post P95 must be <= pre P95 * 1.05


async def _seed_memories(manager: UnifiedMemoryManager, user_id: str) -> list[str]:
    """Seed a deterministic corpus of memories across tiers for benchmarking."""
    seeded_ids: list[str] = []
    tiers = [
        (MemoryLayer.WORKING, MemoryType.CONVERSATION, 15),
        (MemoryLayer.SESSION, MemoryType.SYSTEM_KNOWLEDGE, 20),
        (MemoryLayer.LONG_TERM, MemoryType.SYSTEM_KNOWLEDGE, 15),
    ]
    for layer, mem_type, count in tiers:
        for i in range(count):
            record = await manager.add(
                content=(
                    f"Benchmark fixture memory {layer.value}-{i}: "
                    f"topic={i % 5} about user preferences and project context"
                ),
                user_id=user_id,
                memory_type=mem_type,
                layer=layer,
            )
            if record and record.id:
                seeded_ids.append(record.id)
    return seeded_ids


async def _run_benchmark(n_iterations: int = ITERATIONS) -> dict[str, Any]:
    """Execute n search() calls, return timing stats in milliseconds."""
    config = MemoryConfig()
    manager = UnifiedMemoryManager(config=config)
    await manager.initialize()

    bench_user = f"bench-user-{uuid.uuid4().hex[:8]}"
    queries = [
        "user preferences",
        "project context",
        "topic 0 memory",
        "topic 3 related",
        "episodic recall",
    ]

    try:
        seeded_ids = await _seed_memories(manager, bench_user)
        if not seeded_ids:
            raise RuntimeError("Seeding produced no memory IDs — check store() path")

        # Warm-up: 20 calls discarded to prime caches and connections
        for i in range(20):
            await manager.search(
                query=queries[i % len(queries)],
                user_id=bench_user,
                limit=10,
            )

        # Measured loop
        latencies_ms: list[float] = []
        for i in range(n_iterations):
            q = queries[i % len(queries)]
            t0 = time.perf_counter()
            await manager.search(query=q, user_id=bench_user, limit=10)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies_ms.append(elapsed_ms)

        latencies_ms.sort()
        return {
            "iterations": n_iterations,
            "seeded_memory_count": len(seeded_ids),
            "latency_ms": {
                "p50": round(statistics.median(latencies_ms), 3),
                "p95": round(latencies_ms[int(n_iterations * 0.95)], 3),
                "p99": round(latencies_ms[int(n_iterations * 0.99)], 3),
                "min": round(min(latencies_ms), 3),
                "max": round(max(latencies_ms), 3),
                "mean": round(statistics.mean(latencies_ms), 3),
                "stdev": round(statistics.stdev(latencies_ms), 3),
            },
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        }
    finally:
        # Clean up seeded fixtures (best-effort)
        try:
            for mem_id in seeded_ids:
                try:
                    await manager.delete(mem_id, bench_user, MemoryLayer.WORKING)
                except Exception:
                    continue
        except Exception:
            pass
        await manager.close()


def _write_artifact(data: dict[str, Any], path: Path, mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sprint": 170,
        "phase": 48,
        "mode": mode,
        "git_ref": os.environ.get("GIT_COMMIT", "unknown"),
        **data,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[ok] Wrote {mode} baseline artifact → {path}")
    print(
        f"     P50={data['latency_ms']['p50']}ms  "
        f"P95={data['latency_ms']['p95']}ms  "
        f"P99={data['latency_ms']['p99']}ms"
    )


def _validate_regression() -> int:
    if not BASELINE_PRE.exists():
        print(f"[err] Pre-change baseline missing at {BASELINE_PRE}", file=sys.stderr)
        return 1
    if not BASELINE_POST.exists():
        print(f"[err] Post-change baseline missing at {BASELINE_POST}", file=sys.stderr)
        return 1

    pre = json.loads(BASELINE_PRE.read_text(encoding="utf-8"))
    post = json.loads(BASELINE_POST.read_text(encoding="utf-8"))
    pre_p95 = pre["latency_ms"]["p95"]
    post_p95 = post["latency_ms"]["p95"]
    ratio = post_p95 / pre_p95 if pre_p95 > 0 else float("inf")

    print(f"Pre P95:  {pre_p95} ms")
    print(f"Post P95: {post_p95} ms")
    print(f"Ratio:    {ratio:.4f}  (gate: <= {REGRESSION_GATE})")

    if ratio <= REGRESSION_GATE:
        print("[ok] AC-6 regression gate PASSED")
        return 0
    print(
        f"[err] AC-6 regression gate FAILED — post P95 exceeds "
        f"{(REGRESSION_GATE - 1) * 100:.0f}% threshold",
        file=sys.stderr,
    )
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Memory search latency benchmark")
    parser.add_argument("--mode", choices=["pre", "post"], help="Capture baseline mode")
    parser.add_argument(
        "--validate", action="store_true", help="Compare pre vs post and enforce regression gate"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=ITERATIONS,
        help=f"Number of search iterations (default: {ITERATIONS})",
    )
    args = parser.parse_args()

    if args.validate:
        return _validate_regression()

    if not args.mode:
        parser.error("--mode is required unless --validate is specified")

    try:
        stats = asyncio.run(_run_benchmark(n_iterations=args.iterations))
    except Exception as exc:
        print(f"[err] Benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("      Verify Redis/Qdrant/mem0 infrastructure is reachable.", file=sys.stderr)
        return 1

    target = BASELINE_PRE if args.mode == "pre" else BASELINE_POST
    _write_artifact(stats, target, args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
