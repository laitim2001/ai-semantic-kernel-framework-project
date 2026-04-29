"""
File: scripts/lint/check_llm_sdk_leak.py
Purpose: Forbid `import openai` / `import anthropic` (etc.) outside adapters/<provider>/.
Category: V2 Lint / CI / Quality
Scope: Phase 49 / Sprint 49.4 Day 4 (rule from llm-provider-neutrality.md)

Usage:
    python -m scripts.lint.check_llm_sdk_leak [--root backend/src]

What it forbids:
    Any `from openai import ...`, `import openai`, `from anthropic import ...`,
    `import anthropic` (and same for `google.generativeai`, `cohere`) appearing
    outside backend/src/adapters/<provider>/.

What it allows:
    Inside backend/src/adapters/azure_openai/, openai SDK import is REQUIRED.
    Inside backend/src/adapters/anthropic/, anthropic SDK import is REQUIRED.
    Inside backend/src/adapters/_testing/, no SDK import allowed.

Why:
    The whole point of LLM provider neutrality. agent_harness/ talks to ChatClient
    ABC; only adapters translate native SDK formats. If a Cat 1 / business module
    imports openai directly, switching providers requires touching that module —
    that's exactly the lock-in we're avoiding.

Per .claude/rules/llm-provider-neutrality.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

# SDK module → which adapter directory is allowed.
SDK_TO_ADAPTER: dict[str, str] = {
    "openai": "azure_openai",  # Azure OpenAI uses the same `openai` package
    "anthropic": "anthropic",
    "google.generativeai": "google",
    "cohere": "cohere",
}

# Regex for top-of-line `import X` / `from X import ...`
# Captures the SDK module if it matches one we forbid.
IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(?P<from_mod>[\w.]+)|import\s+(?P<import_mod>[\w.]+))",
    re.MULTILINE,
)


class Violation(NamedTuple):
    file: Path
    lineno: int
    sdk: str
    line: str


def _find_sdk_imports(text: str, path: Path) -> list[Violation]:
    out: list[Violation] = []
    for match in IMPORT_RE.finditer(text):
        mod = match.group("from_mod") or match.group("import_mod") or ""
        # match SDK roots and submodules (openai.types etc.)
        for sdk in SDK_TO_ADAPTER:
            if mod == sdk or mod.startswith(f"{sdk}."):
                lineno = text.count("\n", 0, match.start()) + 1
                line = text.splitlines()[lineno - 1].strip()
                out.append(Violation(file=path, lineno=lineno, sdk=sdk, line=line))
                break
    return out


def _is_allowed_for_sdk(file_path: Path, root: Path, sdk: str) -> bool:
    """True iff file_path is inside the adapter directory permitted for this SDK."""
    try:
        rel = file_path.relative_to(root)
    except ValueError:
        return False
    parts = rel.parts
    if len(parts) < 2:
        return False
    allowed_adapter = SDK_TO_ADAPTER.get(sdk)
    if allowed_adapter is None:
        return False
    return parts[0] == "adapters" and parts[1] == allowed_adapter


def find_violations(root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for py_file in root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            text = py_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for v in _find_sdk_imports(text, py_file):
            if not _is_allowed_for_sdk(py_file, root, v.sdk):
                violations.append(v)
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="backend/src")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: --root not found: {root}", file=sys.stderr)
        return 2

    violations = find_violations(root)
    if not violations:
        print(f"OK: no LLM SDK leak under {root}")
        return 0

    print(
        f"FAIL: {len(violations)} LLM SDK import(s) outside permitted adapter dirs:",
        file=sys.stderr,
    )
    for v in violations:
        print(f"  {v.file}:{v.lineno}  [{v.sdk}]  {v.line}", file=sys.stderr)
    print(
        "\nFIX: Move SDK usage into backend/src/adapters/<provider>/, "
        "consume via ChatClient ABC.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
