"""
File: backend/src/agent_harness/verification/types.py
Purpose: Rule ABC + 3 concrete types (Regex / Schema / Format) for RulesBasedVerifier.
Category: 範疇 10 (Verification Loops)
Scope: Sprint 54.1 US-1

Description:
    Rule is the unit of work for RulesBasedVerifier; each rule.check(output)
    returns (passed, reason, suggested_correction). RulesBasedVerifier runs
    its list of Rules in order and stops at the first failure (fail-fast).

    Three concrete types cover the common cases:
    - RegexRule: pattern must match (or NOT match) the output
    - SchemaRule: output must parse as JSON and validate against a JSON Schema
    - FormatRule: arbitrary callable check (escape hatch for custom rules)

Owner: 01-eleven-categories-spec.md §範疇 10
Related: 17-cross-category-interfaces.md §1.1 (VerificationResult contract)

Created: 2026-05-04 (Sprint 54.1 Day 1)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.1 US-1) — RulesBasedVerifier foundation
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Pattern

from jsonschema import Draft202012Validator  # type: ignore[import-untyped, unused-ignore]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped, unused-ignore]


class Rule(ABC):
    """Single verification rule. Returns (passed, reason, suggested_correction)."""

    name: str

    @abstractmethod
    def check(self, output: str) -> tuple[bool, str | None, str | None]:
        """Run this rule against output. On failure, return non-None reason."""
        ...


@dataclass
class RegexRule(Rule):
    """Pass iff output matches (or does not match, when expected_match=False) the pattern."""

    pattern: str
    expected_match: bool = True
    name: str = "regex_rule"
    suggestion: str | None = None

    def __post_init__(self) -> None:
        # Compile once at construction so per-call check() is hot.
        self._compiled: Pattern[str] = re.compile(self.pattern)

    def check(self, output: str) -> tuple[bool, str | None, str | None]:
        match_found = self._compiled.search(output) is not None
        if match_found == self.expected_match:
            return (True, None, None)
        verb = "did not match" if self.expected_match else "matched (expected no match)"
        reason = f"{self.name}: pattern '{self.pattern}' {verb}"
        return (False, reason, self.suggestion)


@dataclass
class SchemaRule(Rule):
    """Pass iff output parses as JSON and validates against `schema`."""

    schema: dict[str, Any]
    name: str = "schema_rule"
    suggestion: str | None = None

    def check(self, output: str) -> tuple[bool, str | None, str | None]:
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            return (False, f"{self.name}: output is not valid JSON: {e}", self.suggestion)
        try:
            Draft202012Validator(self.schema).validate(data)
        except ValidationError as e:
            return (False, f"{self.name}: schema violation: {e.message}", self.suggestion)
        return (True, None, None)


@dataclass
class FormatRule(Rule):
    """Escape hatch: pass iff `check_fn(output)` returns (True, _).

    `check_fn` returns (passed, reason). When passed=False, the rule's
    `suggestion` is used as suggested_correction.
    """

    check_fn: Callable[[str], tuple[bool, str | None]]
    name: str = "format_rule"
    suggestion: str | None = None

    def check(self, output: str) -> tuple[bool, str | None, str | None]:
        passed, reason = self.check_fn(output)
        if passed:
            return (True, None, None)
        return (False, reason, self.suggestion)
