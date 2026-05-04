"""
File: backend/tests/unit/agent_harness/verification/test_templates.py
Purpose: Unit tests for load_template helper + 4 default judge templates.
Category: Tests / Unit / 範疇 10
Scope: Sprint 54.1 US-2

Description:
    Covers:
    - load_template returns content for existing template
    - load_template raises FileNotFoundError for missing name
    - all 4 default templates (factual_consistency / format_compliance /
      safety_review / pii_leak_check) load + contain {output} placeholder

Created: 2026-05-04 (Sprint 54.1 Day 2)

Related:
    - backend/src/agent_harness/verification/templates/__init__.py
"""

from __future__ import annotations

import pytest

from agent_harness.verification import load_template


def test_load_template_existing_returns_content() -> None:
    content = load_template("factual_consistency")
    assert isinstance(content, str)
    assert len(content) > 0
    assert "{output}" in content
    assert "fact-checking judge" in content


def test_load_template_missing_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError) as exc_info:
        load_template("does_not_exist_template")
    assert "does_not_exist_template" in str(exc_info.value)


@pytest.mark.parametrize(
    "name",
    ["factual_consistency", "format_compliance", "safety_review", "pii_leak_check"],
)
def test_all_default_templates_load_and_have_placeholder(name: str) -> None:
    content = load_template(name)
    assert "{output}" in content, f"Template '{name}' missing {{output}} placeholder"
    assert "JSON" in content, f"Template '{name}' should request JSON response"
