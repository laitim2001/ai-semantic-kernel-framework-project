"""
File: backend/tests/unit/scripts/test_benchmark_key_condition.py
Purpose: CI-safe coverage of the key-condition A/B benchmark logic (load/run/score) — no Azure.
Category: Tests / Unit / 範疇 10
Scope: Sprint 57.138 (AD-Verification-KeyCondition-PerTask / research #8)
Created: 2026-06-24

The real-LLM A/B run lives in scripts/benchmark_key_condition.py :: main (RUN_AZURE_INTEGRATION,
on-demand). This file pins the pure logic with a stub Verifier + synthetic JudgeRuns so the
harness is validated WITHOUT Azure credentials.

Related:
    - backend/scripts/benchmark_key_condition.py
    - backend/tests/fixtures/verification/key_condition_cases.yaml
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from agent_harness._contracts import VerificationResult
from agent_harness._contracts.chat import Message
from agent_harness.verification import Verifier

# Load backend/scripts/benchmark_key_condition.py via importlib — the plain
# `from scripts.benchmark_key_condition import ...` is shadowed by the `tests.unit.scripts`
# package (same idiom as test_benchmark_judge.py). Register in sys.modules BEFORE
# exec_module (Python 3.12 dataclass type-resolution accesses sys.modules[__module__]).
_ROOT = Path(__file__).resolve().parents[3]
_BENCH_PATH = _ROOT / "scripts" / "benchmark_key_condition.py"
_spec = importlib.util.spec_from_file_location("_benchmark_key_condition_under_test", _BENCH_PATH)
assert _spec is not None and _spec.loader is not None
_bench = importlib.util.module_from_spec(_spec)
sys.modules["_benchmark_key_condition_under_test"] = _bench
_spec.loader.exec_module(_bench)

KeyCondCase = _bench.KeyCondCase
JudgeRun = _bench.JudgeRun
build_report = _bench.build_report
load_cases = _bench.load_cases
run_judge = _bench.run_judge

_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "verification" / "key_condition_cases.yaml"
)


# === load_cases ============================================================


def test_load_real_fixture_schema() -> None:
    cases = load_cases(_FIXTURE)
    assert 9 <= len(cases) <= 16  # the plan's curated range (≥6 iv + ≥4 acceptable)
    assert {c.klass for c in cases} == {"instruction_violation", "acceptable"}
    assert len({c.id for c in cases}) == len(cases)  # unique ids
    # every instruction_violation case is labeled false; every acceptable labeled true
    for c in cases:
        if c.klass == "instruction_violation":
            assert c.expected_passed is False, f"{c.id} should expect a fail"
        else:
            assert c.expected_passed is True, f"{c.id} should expect a pass"
    # instruction_violation cases carry a constraining-request trace (needed to extract
    # the condition); without it the judge cannot know the condition.
    iv = [c for c in cases if c.klass == "instruction_violation"]
    assert all(c.trace for c in iv), "every instruction_violation case needs a trace"


def test_load_rejects_missing_key(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("cases:\n  - id: x\n    output: hi\n    class: acceptable\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required key"):
        load_cases(p)


def test_load_rejects_bad_class(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "cases:\n  - id: x\n    output: hi\n    class: nonsense\n    expected_passed: true\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid class"):
        load_cases(p)


def test_load_rejects_duplicate_id(tmp_path: Path) -> None:
    p = tmp_path / "dup.yaml"
    p.write_text(
        "cases:\n"
        "  - id: x\n    output: a\n    class: acceptable\n    expected_passed: true\n"
        "  - id: x\n    output: b\n    class: instruction_violation\n    expected_passed: false\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate case id"):
        load_cases(p)


# === run_judge =============================================================


class _StubJudge(Verifier):
    """Returns a per-id verdict map (default True); records the states it received."""

    def __init__(self, verdict_by_id: dict[str, bool] | None = None) -> None:
        self._verdict_by_id = verdict_by_id or {}
        self._i = 0
        self.states: list[object] = []
        self._ids: list[str] = []

    def with_ids(self, ids: list[str]) -> _StubJudge:
        self._ids = ids
        return self

    async def verify(
        self, *, output: str, state: object = None, trace_context: object = None
    ) -> VerificationResult:
        cid = self._ids[self._i] if self._i < len(self._ids) else ""
        self._i += 1
        self.states.append(state)
        return VerificationResult(
            passed=self._verdict_by_id.get(cid, True),
            verifier_name="stub",
            verifier_type="llm_judge",
            input_tokens=10,
            output_tokens=2,
        )


@pytest.mark.asyncio
async def test_run_judge_builds_trace_state_and_accumulates_tokens() -> None:
    cases = [
        KeyCondCase(
            id="a",
            output="x",
            expected_passed=True,
            klass="acceptable",
        ),
        KeyCondCase(
            id="b",
            output="y",
            expected_passed=False,
            klass="instruction_violation",
            trace=[Message(role="user", content="exactly 3")],
        ),
    ]
    stub = _StubJudge().with_ids(["a", "b"])
    run = await run_judge(stub, cases)  # type: ignore[arg-type]

    assert run.verdicts == [True, True]
    assert run.input_tokens == 20 and run.output_tokens == 4
    assert stub.states[0] is None  # no trace → state=None
    assert stub.states[1] is not None  # trace → minimal LoopState built
    assert stub.states[1].transient.messages[0].content == "exactly 3"  # type: ignore[attr-defined]


# === build_report ==========================================================


def _cases_ab() -> list[KeyCondCase]:
    return [
        KeyCondCase(
            id="iv1", output="5 items", expected_passed=False, klass="instruction_violation"
        ),
        KeyCondCase(
            id="iv2", output="paragraph", expected_passed=False, klass="instruction_violation"
        ),
        KeyCondCase(id="ok1", output="3 items", expected_passed=True, klass="acceptable"),
        KeyCondCase(id="ok2", output="Yes.", expected_passed=True, klass="acceptable"),
    ]


def test_build_report_gain_and_no_false_positive() -> None:
    """Generic misses both instruction_violations (passes them); key_condition catches both
    and does not over-flag the acceptable answers → max gain, zero FP, RECOMMENDED."""
    cases = _cases_ab()
    # generic: wrongly passes both iv (True), correctly passes both ok (True) → iv acc 0.0
    generic = JudgeRun(verdicts=[True, True, True, True], input_tokens=10, output_tokens=2)
    # key_condition: correctly fails both iv (False), correctly passes both ok (True) → iv acc 1.0
    key_condition = JudgeRun(verdicts=[False, False, True, True], input_tokens=20, output_tokens=4)
    rep = build_report(cases, generic, key_condition)

    assert rep.key_condition_gain == 1.0  # 1.0 (kc iv acc) − 0.0 (generic iv acc)
    assert rep.false_positive_rate == 0.0  # no acceptable wrongly failed
    assert rep.generic_accuracy == 0.5  # 2/4 (only the acceptable ones)
    assert rep.key_condition_accuracy == 1.0
    assert rep.key_condition_recommended is True


def test_build_report_over_flag_blocks_recommendation() -> None:
    """key_condition catches the violations BUT also wrongly fails the acceptable answers →
    high FP → NOT recommended even though the gain is high."""
    cases = _cases_ab()
    generic = JudgeRun(verdicts=[True, True, True, True], input_tokens=10, output_tokens=2)
    # catches both iv (False) but ALSO fails both acceptable (False) → FP = 1.0
    key_condition = JudgeRun(
        verdicts=[False, False, False, False], input_tokens=20, output_tokens=4
    )
    rep = build_report(cases, generic, key_condition)

    assert rep.key_condition_gain == 1.0
    assert rep.false_positive_rate == 1.0
    assert rep.key_condition_recommended is False  # FP ceiling exceeded


def test_build_report_per_class_and_tokens() -> None:
    cases = _cases_ab()
    generic = JudgeRun(verdicts=[True, True, True, True], input_tokens=10, output_tokens=2)
    key_condition = JudgeRun(verdicts=[False, True, True, True], input_tokens=20, output_tokens=4)
    rep = build_report(cases, generic, key_condition)

    assert rep.per_class["instruction_violation"]["n"] == 2.0
    assert rep.per_class["instruction_violation"]["generic_accuracy"] == 0.0
    assert rep.per_class["instruction_violation"]["key_condition_accuracy"] == 0.5  # caught 1/2
    assert rep.per_class["acceptable"]["key_condition_accuracy"] == 1.0
    assert rep.generic_tokens == 12 and rep.key_condition_tokens == 24


def test_build_report_no_recommendation_when_gain_below_floor() -> None:
    """Gain below the floor → NOT recommended even with zero false positives."""
    cases = _cases_ab()
    generic = JudgeRun(verdicts=[False, True, True, True], input_tokens=10, output_tokens=2)
    # same as generic on iv (catches the same 1/2) → gain 0.0
    key_condition = JudgeRun(verdicts=[False, True, True, True], input_tokens=20, output_tokens=4)
    rep = build_report(cases, generic, key_condition)

    assert rep.key_condition_gain == 0.0
    assert rep.false_positive_rate == 0.0
    assert rep.key_condition_recommended is False  # gain below GAIN_FLOOR
