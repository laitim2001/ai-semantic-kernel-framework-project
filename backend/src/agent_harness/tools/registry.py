"""
File: backend/src/agent_harness/tools/registry.py
Purpose: Production-grade ToolRegistry implementation (replaces InMemoryToolRegistry).
Category: 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 1.4

Description:
    Concrete `ToolRegistry` implementation that:
    1. Stores ToolSpecs keyed by name with duplicate-name detection.
    2. Validates each spec's `input_schema` is a syntactically-valid
       JSON Schema (Draft 2020-12) at register time, so bad specs fail
       fast rather than at first tool invocation.
    3. Provides `by_tag()` filtering helper used by chat handler /
       business_domain register helpers to assemble curated tool sets.

    Distinct from `_inmemory.InMemoryToolRegistry` (DEPRECATED-IN: 51.1)
    which had no schema validation and is removed in Day 5 of this sprint.

Key Components:
    - ToolRegistryImpl: concrete `ToolRegistry` (ABC in `_abc.py`).

Owner: 01-eleven-categories-spec.md §範疇 2
Single-source: 17.md §1.1 (ToolSpec) / §2.1 (ToolRegistry ABC) / §3.1 (registered tools)

Created: 2026-04-30 (Sprint 51.1 Day 1.4)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 51.1 Day 1.4) — ToolRegistryImpl
      with duplicate detection + Draft 2020-12 schema validation + by_tag.

Related:
    - ._abc (ToolRegistry ABC; 49.1)
    - ._inmemory (DEPRECATED-IN 51.1; deletion in Day 5)
    - sprint-51-1-plan.md §決策 2 (concrete naming) / §1.4
    - .claude/rules/category-boundaries.md (Cat 2 ownership)
"""

from __future__ import annotations

from builtins import list as _list

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import SchemaError  # type: ignore[import-untyped]

from agent_harness._contracts import ToolSpec

from ._abc import ToolRegistry


class ToolRegistryImpl(ToolRegistry):
    """Concrete ToolRegistry: name-keyed dict + JSON Schema validation."""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Tool '{spec.name}' already registered")
        try:
            Draft202012Validator.check_schema(spec.input_schema)
        except SchemaError as exc:
            raise ValueError(f"Tool '{spec.name}' has invalid JSON Schema: {exc.message}") from exc
        self._specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def list(self) -> _list[ToolSpec]:
        return [*self._specs.values()]

    def by_tag(self, tag: str) -> _list[ToolSpec]:
        """Return all specs whose `tags` tuple contains the given tag."""
        return [s for s in self._specs.values() if tag in s.tags]
