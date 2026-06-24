"""
File: backend/scripts/benchmark_key_condition.py
Purpose: Permanent A/B harness — generic output_quality judge vs the key_condition judge.
Category: 範疇 10 (Verification Loops) — eval tooling
Scope: Phase 57 / Sprint 57.138 (AD-Verification-KeyCondition-PerTask / research #8)

Description:
    Measures whether the per-task key_condition judge (Sprint 57.138) catches
    instruction-following failures (count / format / ordering / unit / inclusion)
    that the GENERIC output_quality judge is structurally blind to — and whether
    it does so WITHOUT over-flagging acceptable answers (the stricter-judge risk).

    The generic 5-failure-mode judge passes any coherent, on-topic, non-empty
    answer; an answer that violates a precise task constraint (5 items when
    "exactly 3" was asked) is coherent → it PASSES. The key_condition judge
    extracts the request's must-satisfy conditions and checks each. This harness
    runs BOTH templates over the same labeled corpus and reports:
      - generic_accuracy / key_condition_accuracy (overall)
      - key_condition_gain  = key_condition_acc − generic_acc on instruction_violation
                              (the catch the generic judge misses; HIGHER = better)
      - false_positive_rate = acceptable cases the key_condition judge WRONGLY fails
                              (the over-flag risk; LOWER = better)
      - key_condition_recommended = gain ≥ GAIN_FLOOR AND fp ≤ FP_CEILING

    The reusable logic lives here (importable as `scripts.benchmark_key_condition`):
      - load_cases(path)         — parse + schema-validate the golden YAML fixture
      - run_judge(judge, cases)  — run a Verifier over the cases (trace-aware)
      - build_report(...)        — pure gain / false-positive / per-class computation
      - main()                   — CLI: build the Azure profile, run both templates, write a report
    The pytest unit `tests/unit/scripts/test_benchmark_key_condition.py` covers
    load_cases / run_judge / build_report CI-safe (a stub Verifier, no Azure).

    Run on demand:
      RUN_AZURE_INTEGRATION=1 AZURE_OPENAI_*=... python scripts/benchmark_key_condition.py

LLM Provider Neutrality: the core (load/run/score) operates on the Verifier ABC; only
main() builds the Azure ModelProfile (the concrete on-demand entry, mirroring benchmark_judge.py).

Created: 2026-06-24 (Sprint 57.138)

Modification History (newest-first):
    - 2026-06-24: Initial creation (Sprint 57.138) — generic-vs-key_condition A/B harness

Related:
    - backend/tests/fixtures/verification/key_condition_cases.yaml (the golden corpus)
    - backend/src/agent_harness/verification/templates/key_condition.txt (the judge under test)
    - backend/scripts/benchmark_judge.py (Sprint 57.111 A3 — the mirrored scaffold)
    - docs/03-implementation/agent-harness-planning/42-verification-key-condition-design.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from uuid import uuid4

import yaml

from agent_harness._contracts.chat import Message
from agent_harness._contracts.state import (
    DurableState,
    LoopState,
    StateVersion,
    TransientState,
)
from agent_harness.verification import LLMJudgeVerifier, Verifier

# Spike thresholds (this sprint defines them; the design note records the verdict). The
# key_condition judge is "worth it" when it catches a MATERIAL share of the instruction
# violations the generic judge misses (gain) WITHOUT over-flagging acceptable answers (fp).
GAIN_FLOOR = 0.30  # key_condition must beat generic by ≥30pp on instruction_violation
FP_CEILING = 0.20  # key_condition must wrongly fail ≤20% of acceptable answers

_INSTRUCTION_VIOLATION = "instruction_violation"
_ACCEPTABLE = "acceptable"
_VALID_CLASSES = (_INSTRUCTION_VIOLATION, _ACCEPTABLE)


@dataclass(frozen=True)
class KeyCondCase:
    """One labeled key-condition benchmark case."""

    id: str
    output: str
    expected_passed: bool
    klass: str  # instruction_violation | acceptable
    trace: list[Message] = field(default_factory=list)


@dataclass(frozen=True)
class JudgeRun:
    """The result of running one judge over the cases (aligned to the case order)."""

    verdicts: list[bool]
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class KeyCondReport:
    """Computed A/B metrics: generic vs key_condition."""

    total: int
    generic_accuracy: float
    key_condition_accuracy: float
    key_condition_gain: float  # key_cond_acc − generic_acc on instruction_violation
    false_positive_rate: float  # acceptable cases key_condition WRONGLY fails
    per_class: dict[str, dict[str, float]]
    generic_tokens: int
    key_condition_tokens: int
    gain_floor: float
    fp_ceiling: float
    key_condition_recommended: bool


def load_cases(path: str | Path) -> list[KeyCondCase]:
    """Parse + schema-validate the golden YAML fixture into KeyCondCase objects."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError("benchmark fixture must be a mapping with a top-level 'cases' list")
    raw_cases = data["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("'cases' must be a non-empty list")

    cases: list[KeyCondCase] = []
    seen_ids: set[str] = set()
    for i, rc in enumerate(raw_cases):
        if not isinstance(rc, dict):
            raise ValueError(f"case #{i} is not a mapping")
        for key in ("id", "output", "expected_passed", "class"):
            if key not in rc:
                raise ValueError(f"case #{i} missing required key '{key}'")
        cid = str(rc["id"])
        if cid in seen_ids:
            raise ValueError(f"duplicate case id '{cid}'")
        seen_ids.add(cid)
        klass = str(rc["class"])
        if klass not in _VALID_CLASSES:
            raise ValueError(f"case '{cid}' has invalid class '{klass}'")
        if not isinstance(rc["expected_passed"], bool):
            raise ValueError(f"case '{cid}' expected_passed must be a bool")
        trace: list[Message] = []
        for j, tm in enumerate(rc.get("trace", []) or []):
            if not isinstance(tm, dict) or "role" not in tm or "content" not in tm:
                raise ValueError(f"case '{cid}' trace entry #{j} needs 'role' + 'content'")
            role = str(tm["role"])
            content = str(tm["content"])
            trace.append(Message(role=role, content=content))  # type: ignore[arg-type]
        cases.append(
            KeyCondCase(
                id=cid,
                output=str(rc["output"]),
                expected_passed=bool(rc["expected_passed"]),
                klass=klass,
                trace=trace,
            )
        )
    return cases


def _state_from_trace(trace: list[Message]) -> LoopState | None:
    """Wrap a case's trace as a minimal LoopState the trace-aware judge reads (None if empty)."""
    if not trace:
        return None
    sid = uuid4()
    return LoopState(
        transient=TransientState(messages=list(trace)),
        durable=DurableState(session_id=sid, tenant_id=sid),
        version=StateVersion(
            version=0,
            parent_version=None,
            created_at=datetime.now(),
            created_by_category="benchmark",
        ),
    )


async def run_judge(judge: Verifier, cases: list[KeyCondCase]) -> JudgeRun:
    """Run `judge` over every case (trace-aware); return verdicts + token totals.

    Both judges are run WITH the case trace so the comparison is apples-to-apples (the
    key_condition judge needs the trace to extract the request's conditions; the generic
    output_quality judge also reads {trace} for its contradicts-trace floor).
    """
    verdicts: list[bool] = []
    in_tok = 0
    out_tok = 0
    for case in cases:
        state = _state_from_trace(case.trace)
        result = await judge.verify(output=case.output, state=state)
        verdicts.append(result.passed)
        in_tok += result.input_tokens
        out_tok += result.output_tokens
    return JudgeRun(verdicts=verdicts, input_tokens=in_tok, output_tokens=out_tok)


def _accuracy(cases: list[KeyCondCase], verdicts: list[bool]) -> float:
    if not cases:
        return 0.0
    return mean(1.0 if v == c.expected_passed else 0.0 for c, v in zip(cases, verdicts))


def build_report(
    cases: list[KeyCondCase],
    generic: JudgeRun,
    key_condition: JudgeRun,
    *,
    gain_floor: float = GAIN_FLOOR,
    fp_ceiling: float = FP_CEILING,
) -> KeyCondReport:
    """Pure A/B metric computation: accuracy, instruction-violation gain, false-positive rate."""
    per_class: dict[str, dict[str, float]] = {}
    for klass in _VALID_CLASSES:
        idx = [i for i, c in enumerate(cases) if c.klass == klass]
        if not idx:
            continue
        sub = [cases[i] for i in idx]
        per_class[klass] = {
            "n": float(len(idx)),
            "generic_accuracy": _accuracy(sub, [generic.verdicts[i] for i in idx]),
            "key_condition_accuracy": _accuracy(sub, [key_condition.verdicts[i] for i in idx]),
        }

    # gain = key_condition − generic accuracy on the instruction_violation class (the catch
    # the generic judge is blind to). 0.0 if there are no instruction_violation cases.
    iv_idx = [i for i, c in enumerate(cases) if c.klass == _INSTRUCTION_VIOLATION]
    if iv_idx:
        iv_cases = [cases[i] for i in iv_idx]
        gen_iv = _accuracy(iv_cases, [generic.verdicts[i] for i in iv_idx])
        kc_iv = _accuracy(iv_cases, [key_condition.verdicts[i] for i in iv_idx])
        key_condition_gain = kc_iv - gen_iv
    else:
        key_condition_gain = 0.0

    # false positive = acceptable cases (expected_passed True) the key_condition judge
    # WRONGLY fails (verdict False). 0.0 if there are no acceptable cases.
    ok_idx = [i for i, c in enumerate(cases) if c.klass == _ACCEPTABLE]
    if ok_idx:
        false_positive_rate = mean(1.0 if not key_condition.verdicts[i] else 0.0 for i in ok_idx)
    else:
        false_positive_rate = 0.0

    return KeyCondReport(
        total=len(cases),
        generic_accuracy=_accuracy(cases, generic.verdicts),
        key_condition_accuracy=_accuracy(cases, key_condition.verdicts),
        key_condition_gain=key_condition_gain,
        false_positive_rate=false_positive_rate,
        per_class=per_class,
        generic_tokens=generic.input_tokens + generic.output_tokens,
        key_condition_tokens=key_condition.input_tokens + key_condition.output_tokens,
        gain_floor=gain_floor,
        fp_ceiling=fp_ceiling,
        key_condition_recommended=(
            key_condition_gain >= gain_floor and false_positive_rate <= fp_ceiling
        ),
    )


def report_to_markdown(report: KeyCondReport, *, stamp: str) -> str:
    """Render a human-readable A/B report (for the design-note verdict)."""
    lines = [
        f"# Key-Condition vs Generic Judge — A/B — {stamp}",
        "",
        f"- cases: **{report.total}**",
        f"- generic accuracy (all): **{report.generic_accuracy:.2%}**",
        f"- key_condition accuracy (all): **{report.key_condition_accuracy:.2%}**",
        f"- **key_condition gain** (key_cond − generic on instruction_violation): "
        f"**{report.key_condition_gain:+.2%}**",
        f"- **false_positive_rate** (acceptable wrongly failed by key_condition): "
        f"**{report.false_positive_rate:.2%}**",
        f"- generic tokens: {report.generic_tokens} · key_condition tokens: "
        f"{report.key_condition_tokens}",
        f"- thresholds: gain ≥ {report.gain_floor:.0%} AND fp ≤ {report.fp_ceiling:.0%} → "
        f"**{'RECOMMENDED' if report.key_condition_recommended else 'NOT recommended'}**",
        "",
        "## Per class",
        "",
        "| class | n | generic acc | key_condition acc |",
        "|-------|---|-------------|-------------------|",
    ]
    for klass, m in report.per_class.items():
        lines.append(
            f"| {klass} | {int(m['n'])} | {m['generic_accuracy']:.2%} | "
            f"{m['key_condition_accuracy']:.2%} |"
        )
    return "\n".join(lines) + "\n"


async def _amain(fixture: Path, out_dir: Path) -> int:
    # Imported lazily so a CI-safe import of this module's pure helpers does not require
    # the Azure adapter env (mirrors benchmark_judge.py).
    from adapters.azure_openai.profile import build_azure_model_profile

    cases = load_cases(fixture)
    profile = build_azure_model_profile()
    generic_judge = LLMJudgeVerifier(
        chat_client=profile.cheap, judge_template="output_quality", temperature=0.0
    )
    key_condition_judge = LLMJudgeVerifier(
        chat_client=profile.cheap, judge_template="key_condition", temperature=0.0
    )

    generic = await run_judge(generic_judge, cases)
    key_condition = await run_judge(key_condition_judge, cases)
    report = build_report(cases, generic, key_condition)

    out_dir.mkdir(parents=True, exist_ok=True)
    md = report_to_markdown(report, stamp=datetime.now().isoformat(timespec="seconds"))
    (out_dir / "key_condition_report.md").write_text(md, encoding="utf-8")
    (out_dir / "key_condition_report.json").write_text(
        json.dumps(
            {
                "total": report.total,
                "generic_accuracy": report.generic_accuracy,
                "key_condition_accuracy": report.key_condition_accuracy,
                "key_condition_gain": report.key_condition_gain,
                "false_positive_rate": report.false_positive_rate,
                "per_class": report.per_class,
                "generic_tokens": report.generic_tokens,
                "key_condition_tokens": report.key_condition_tokens,
                "gain_floor": report.gain_floor,
                "fp_ceiling": report.fp_ceiling,
                "key_condition_recommended": report.key_condition_recommended,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(md)
    return 0


def main() -> int:
    # The report markdown carries non-ASCII typography (− · → ≥); a Windows cp950 console
    # can't encode it. Force the stdout text layer to UTF-8 so the print never crashes.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — best-effort; redirected/odd streams keep their codec
        pass
    parser = argparse.ArgumentParser(
        description="Key-condition vs generic judge A/B (research #8)."
    )
    parser.add_argument(
        "--fixture",
        default=str(
            Path(__file__).resolve().parent.parent
            / "tests"
            / "fixtures"
            / "verification"
            / "key_condition_cases.yaml"
        ),
    )
    parser.add_argument(
        "--out", default=str(Path(__file__).resolve().parent.parent / "benchmark_reports")
    )
    args = parser.parse_args()
    return asyncio.run(_amain(Path(args.fixture), Path(args.out)))


if __name__ == "__main__":
    sys.exit(main())
