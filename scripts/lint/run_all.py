"""
File: scripts/lint/run_all.py
Purpose: One-stop wrapper that invokes all 6 V2 architecture lint scripts with
    the correct CLI arguments + emits a per-script timing summary + final
    aggregated pass/fail count. Replaces the 6 separate manual invocations
    that historically caused silent-skip false-greens when the `--root` arg
    mismatched a script's expectation (see Sprint 53.7 Day 0 drift D1).
Category: Cross-cutting / DevOps tooling
Scope: Sprint 53.7 US-1 (closes AD-Lint-1)

Description:
    Each V2 lint enforces a different architectural invariant (AP-1 / cross-
    category import / duplicate dataclass / LLM SDK leak / sync callback /
    AP-8 PromptBuilder usage). The 6 scripts unfortunately have inconsistent
    `--root` semantics:
        - check_ap1_pipeline_disguise.py:  required `--root backend/src`
          (internally joins `<root>/agent_harness/orchestrator_loop`)
        - check_promptbuilder_usage.py:    default `backend/src/agent_harness`
        - 4 others (cross_category_import / duplicate_dataclass /
          llm_sdk_leak / sync_callback): walk default backend/src/* tree
          (no `--root` flag exposed)

    Pre-53.7 invocations passed `--root backend/src/agent_harness` to BOTH
    check_ap1 AND check_promptbuilder uniformly, which made check_ap1
    silently exit OK (`target_dir = backend/src/agent_harness/agent_harness/
    orchestrator_loop` doesn't exist → "no orchestrator_loop dir; skipping").
    This wrapper hardcodes the correct args per-script.

Usage:
    python scripts/lint/run_all.py            # exit 0 if all 6 green
    python scripts/lint/run_all.py --verbose  # also print per-lint stdout

Exit codes:
    0 = all 6 lints green
    N = N of 6 lints failed (1..6); per-script status printed to stdout

Created: 2026-05-04 (Sprint 53.7 Day 1)

Related:
    - .claude/rules/sprint-workflow.md §Before Commit Checklist (Lint + Format)
    - feedback_v2_lints_must_run_locally.md (53.4 Sprint pre-push lesson)
    - Sprint 53.6 retrospective Q4 (AD-Lint-1 origin)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

LINTS: list[tuple[str, list[str]]] = [
    # (script_filename, extra_args_after_script_path)
    ("check_ap1_pipeline_disguise.py", ["--root", "backend/src"]),
    # check_promptbuilder default root is now correct after Sprint 53.7 D1 fix
    # (was parents[1] -> scripts/; fixed to parents[2] -> repo root); pass
    # explicit --root anyway for defense-in-depth so this wrapper is robust
    # against future re-introductions of the same kind of path bug.
    ("check_promptbuilder_usage.py", ["--root", "backend/src/agent_harness"]),
    ("check_cross_category_import.py", []),
    ("check_duplicate_dataclass.py", []),
    ("check_llm_sdk_leak.py", []),
    ("check_sync_callback.py", []),
]


def run_one(
    script_path: Path, args: list[str], verbose: bool
) -> tuple[int, float, str]:
    """Run a single lint script. Return (exit_code, elapsed_seconds, stdout)."""
    cmd = [sys.executable, str(script_path), *args]
    t0 = time.time()
    cp = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    if verbose and cp.stdout:
        print(cp.stdout, end="")
    if cp.returncode != 0 and cp.stderr:
        # Always surface stderr on failure (regardless of --verbose).
        print(cp.stderr, end="", file=sys.stderr)
    return cp.returncode, elapsed, cp.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run all 6 V2 architecture lint scripts with correct args."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Also print per-lint stdout (default: only summary line per script).",
    )
    cli = parser.parse_args(argv)

    base = Path(__file__).parent
    if not base.exists():
        print(f"ERROR: scripts/lint dir not found at {base}", file=sys.stderr)
        return 99

    print("Running 6 V2 architecture lint scripts:")
    print("=" * 60)

    failures = 0
    total_elapsed = 0.0
    for script_name, extra_args in LINTS:
        script_path = base / script_name
        if not script_path.exists():
            print(f"  [MISSING] {script_name:38s}  (skipping)")
            failures += 1
            continue
        rc, elapsed, _ = run_one(script_path, extra_args, cli.verbose)
        total_elapsed += elapsed
        status = "OK  " if rc == 0 else "FAIL"
        print(f"  [{status}] {script_name:38s} {elapsed:5.2f}s")
        if rc != 0:
            failures += 1

    print("=" * 60)
    if failures == 0:
        print(f"V2 Lints: 6/6 green  (total {total_elapsed:.2f}s)")
        return 0
    print(
        f"V2 Lints: {6 - failures}/6 green -- {failures} FAILED (total {total_elapsed:.2f}s)"
    )
    return failures


if __name__ == "__main__":
    sys.exit(main())
