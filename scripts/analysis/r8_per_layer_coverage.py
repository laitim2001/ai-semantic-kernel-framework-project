#!/usr/bin/env python3
"""R8 Phase B Prep: Per-layer class coverage analysis.

For each layer, compare the layer summary JSON (actual classes) against
the corresponding V9 layer markdown (mentioned classes).

Output: per-layer coverage stats + specific missing items per layer.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
V9_DIR = PROJECT_ROOT / "docs" / "07-analysis" / "V9"
SUMMARY_DIR = PROJECT_ROOT / "scripts" / "analysis" / "r8-layer-summaries"
OUTPUT_MD = PROJECT_ROOT / "docs" / "07-analysis" / "V9" / "r8-per-layer-coverage.md"

# Map layer ID to V9 files that document it
LAYER_V9_FILES = {
    "L01": ["01-architecture/layer-01-frontend.md", "02-modules/mod-frontend.md"],
    "L02": ["01-architecture/layer-02-api-gateway.md", "09-api-reference/api-reference.md"],
    "L03": ["01-architecture/layer-03-ag-ui.md"],
    "L04": ["01-architecture/layer-04-routing.md"],
    "L05": ["01-architecture/layer-05-orchestration.md", "02-modules/mod-integration-batch1.md"],
    "L06": ["01-architecture/layer-06-maf-builders.md", "02-modules/mod-integration-batch1.md"],
    "L07": ["01-architecture/layer-07-claude-sdk.md", "02-modules/mod-integration-batch1.md"],
    "L08": ["01-architecture/layer-08-mcp-tools.md"],
    "L09": ["01-architecture/layer-09-integrations.md", "02-modules/mod-integration-batch2.md"],
    "L10": ["01-architecture/layer-10-domain.md", "02-modules/mod-domain-infra-core.md"],
    "L11": ["01-architecture/layer-11-infrastructure.md", "02-modules/mod-domain-infra-core.md"],
}


def extract_class_mentions(filepath: Path) -> set:
    """Extract PascalCase class/enum names mentioned in a markdown file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()

    names = set()
    # Match backtick-quoted PascalCase names
    for match in re.finditer(r'`((?:[A-Z][a-zA-Z0-9]+)+)`', content):
        names.add(match.group(1))
    # Match PascalCase in table cells (with or without backticks)
    for match in re.finditer(r'\|\s*`?((?:[A-Z][a-zA-Z0-9]+){2,})`?\s*\|', content):
        names.add(match.group(1))
    # Match PascalCase in code blocks (class definitions)
    for match in re.finditer(r'class\s+((?:[A-Z][a-zA-Z0-9]+)+)', content):
        names.add(match.group(1))
    # Match PascalCase in prose (word boundary, at least 2 upper segments)
    for match in re.finditer(r'(?<![`\w])((?:[A-Z][a-z0-9]+){2,}[A-Z]?\w*)', content):
        name = match.group(1)
        if len(name) >= 6 and not name.isupper():  # Skip acronyms
            names.add(name)
    # Match in parentheses like (SessionService) or (AgentExecutor)
    for match in re.finditer(r'\(([A-Z][a-zA-Z0-9]+(?:[A-Z][a-zA-Z0-9]+)+)\)', content):
        names.add(match.group(1))
    # Match quoted names with .py context: `file.py` (ClassName)
    for match in re.finditer(r'(\w+\.py)[^|]*?((?:[A-Z][a-zA-Z]+){2,})', content):
        names.add(match.group(2))

    # Filter out common non-class words
    skip = {
        "Layer", "Phase", "Sprint", "Backend", "Frontend", "Platform",
        "Protocol", "Pipeline", "Docker", "Compose", "Checkpoint",
        "Framework", "Security", "Sandbox", "Performance", "Middleware",
        "Session", "Memory", "Cache", "Redis", "PostgreSQL", "TypeScript",
        "React", "FastAPI", "Vite", "Traditional", "Chinese", "Integration",
        "Orchestration", "Authentication", "Authorization", "Critical",
        "Complete", "Partial", "Infrastructure", "Database", "Overview",
        "Analysis", "Description", "Evidence", "Category", "Feature",
        "Workflow", "Changes", "Purpose", "Status", "Attribute",
        "Module", "Summary", "Reference", "Generated", "Verified",
        "Updated", "Created", "Modified", "Location", "Assessment",
        "Decision", "Response", "Request", "Execution", "Configuration",
        "Important", "Remaining", "Supporting", "Recommendation",
    }
    return names - skip


def load_layer_classes(layer_id: str) -> list:
    """Load classes from layer summary JSON."""
    summary_file = SUMMARY_DIR / f"{layer_id}-summary.json"
    if not summary_file.exists():
        return []
    with open(summary_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("classes", [])


def collect_all_v9_mentions() -> set:
    """Collect class mentions from ALL V9 markdown files."""
    all_mentions = set()
    for md_file in V9_DIR.rglob("*.md"):
        all_mentions |= extract_class_mentions(md_file)
    return all_mentions


_all_v9_mentions = None

def analyze_layer(layer_id: str, v9_files: list) -> dict:
    """Analyze coverage for one layer."""
    global _all_v9_mentions
    if _all_v9_mentions is None:
        _all_v9_mentions = collect_all_v9_mentions()

    # Get actual classes from summary
    actual_classes = load_layer_classes(layer_id)
    actual_names = {c["name"] for c in actual_classes}

    # Get V9 mentions from layer-specific files
    v9_layer_mentions = set()
    for rel_path in v9_files:
        fpath = V9_DIR / rel_path
        v9_layer_mentions |= extract_class_mentions(fpath)

    # Also check against ALL V9 mentions (class mentioned anywhere counts)
    v9_mentions = v9_layer_mentions | (_all_v9_mentions & actual_names)

    # Compare
    documented = actual_names & v9_mentions
    missing = actual_names - v9_mentions
    extra = v9_mentions - actual_names  # In V9 but not in this layer (might be from other layers)

    # Categorize missing by importance (method count)
    missing_details = []
    for cls in actual_classes:
        if cls["name"] in missing:
            missing_details.append({
                "name": cls["name"],
                "methods": cls.get("method_count", 0),
                "bases": cls.get("bases", []),
                "docstring": cls.get("docstring", "")[:100],
            })

    # Sort by method count (most important first)
    missing_details.sort(key=lambda x: -x["methods"])

    # Split into important (5+ methods) and minor
    important_missing = [m for m in missing_details if m["methods"] >= 5]
    minor_missing = [m for m in missing_details if m["methods"] < 5]

    return {
        "layer": layer_id,
        "total_classes": len(actual_names),
        "documented": len(documented),
        "missing_total": len(missing),
        "important_missing": len(important_missing),
        "minor_missing": len(minor_missing),
        "coverage_pct": round(len(documented) / max(len(actual_names), 1) * 100, 1),
        "important_missing_list": important_missing[:20],
        "minor_missing_list": minor_missing[:20],
    }


def main():
    print("=" * 70)
    print("R8 Phase B Prep: Per-Layer Class Coverage Analysis")
    print("=" * 70)

    results = []
    for layer_id in sorted(LAYER_V9_FILES.keys()):
        v9_files = LAYER_V9_FILES[layer_id]
        result = analyze_layer(layer_id, v9_files)
        results.append(result)
        status = "OK" if result["coverage_pct"] >= 90 else "GAP" if result["coverage_pct"] >= 70 else "LOW"
        print(f"  {layer_id}: {result['documented']}/{result['total_classes']} "
              f"({result['coverage_pct']}%) "
              f"[{result['important_missing']} important missing] "
              f"{'<<< ' + status if status != 'OK' else status}")

    # Generate markdown report
    lines = [
        "# R8 Per-Layer Class Coverage Analysis",
        "",
        "> Which classes exist in each layer's code but are NOT mentioned in V9?",
        "> Generated by: r8_per_layer_coverage.py | Date: 2026-03-30",
        "",
        "---",
        "",
        "## Coverage Summary",
        "",
        "| Layer | Total Classes | Documented | Missing | Important Missing | Coverage |",
        "|-------|-------------|-----------|---------|-------------------|----------|",
    ]

    total_cls = total_doc = total_imp = 0
    for r in results:
        total_cls += r["total_classes"]
        total_doc += r["documented"]
        total_imp += r["important_missing"]
        status = "OK" if r["coverage_pct"] >= 90 else "GAP" if r["coverage_pct"] >= 70 else "LOW"
        lines.append(
            f"| {r['layer']} | {r['total_classes']} | {r['documented']} | "
            f"{r['missing_total']} | {r['important_missing']} | "
            f"{r['coverage_pct']}% {status} |"
        )

    overall = round(total_doc / max(total_cls, 1) * 100, 1)
    lines.append(
        f"| **TOTAL** | **{total_cls}** | **{total_doc}** | "
        f"**{total_cls - total_doc}** | **{total_imp}** | **{overall}%** |"
    )
    lines.append("")

    # Per-layer detail for layers with important gaps
    for r in results:
        if not r["important_missing_list"]:
            continue

        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## {r['layer']} — Important Missing Classes ({r['important_missing']})")
        lines.append(f"")
        lines.append(f"| Class | Methods | Bases | Description |")
        lines.append(f"|-------|---------|-------|-------------|")
        for m in r["important_missing_list"]:
            bases = ", ".join(m["bases"][:3])
            doc = m["docstring"].replace("|", "/").replace("\n", " ")[:60]
            lines.append(f"| `{m['name']}` | {m['methods']} | {bases} | {doc} |")
        lines.append("")

    report = "\n".join(lines)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n[OK] Report: {OUTPUT_MD}")
    print(f"\nOverall: {total_doc}/{total_cls} classes documented ({overall}%)")
    print(f"Important gaps: {total_imp} classes with 5+ methods need documentation")


if __name__ == "__main__":
    main()
