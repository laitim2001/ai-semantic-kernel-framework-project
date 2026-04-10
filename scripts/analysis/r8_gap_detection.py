#!/usr/bin/env python3
"""R8 Phase A: Reverse gap detection + per-layer code summary extraction.

Two objectives:
1. GAP DETECTION: Find important codebase items NOT mentioned in V9 analysis
2. LAYER SUMMARIES: Extract per-layer code summaries for AI semantic verification

Reads r7-codebase-truth.json + scans V9 markdown + reads actual source code.
"""

import ast
import json
import os
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
V9_DIR = PROJECT_ROOT / "docs" / "07-analysis" / "V9"
TRUTH_FILE = PROJECT_ROOT / "scripts" / "analysis" / "r7-codebase-truth.json"
GAP_JSON = PROJECT_ROOT / "scripts" / "analysis" / "r8-gap-report.json"
GAP_MD = PROJECT_ROOT / "docs" / "07-analysis" / "V9" / "r8-gap-report.md"
SUMMARY_DIR = PROJECT_ROOT / "scripts" / "analysis" / "r8-layer-summaries"

LAYER_DIRS = {
    "L01": {"frontend": True, "path": "frontend/src"},
    "L02": {"path": "api/v1"},
    "L03": {"path": "integrations/ag_ui"},
    "L04": {"path": "integrations/orchestration"},
    "L05": {"path": "integrations/hybrid"},
    "L06": {"path": "integrations/agent_framework"},
    "L07": {"path": "integrations/claude_sdk"},
    "L08": {"path": "integrations/mcp"},
    "L09": {"path": "integrations", "submodules": [
        "swarm", "llm", "memory", "knowledge", "correlation",
        "rootcause", "incident", "patrol", "learning", "audit",
        "a2a", "n8n", "contracts", "shared"
    ]},
    "L10": {"path": "domain"},
    "L11": {"path": "infrastructure", "extra": ["core", "middleware"]},
}


def load_truth():
    with open(TRUTH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_v9_mentions():
    """Collect all class/function/enum names mentioned anywhere in V9."""
    mentions = set()
    name_pattern = re.compile(r'`((?:[A-Z][a-zA-Z0-9]+)+)`')

    for md_file in V9_DIR.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for match in name_pattern.finditer(content):
            mentions.add(match.group(1))

    return mentions


def extract_db_models():
    """Extract all SQLAlchemy model definitions with their columns."""
    models_dir = BACKEND_SRC / "infrastructure" / "database" / "models"
    models = {}

    if not models_dir.exists():
        return models

    for py_file in models_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except Exception:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            bases = [getattr(b, "id", getattr(b, "attr", "")) for b in node.bases]
            if not any(b in ("Base", "TimestampMixin", "UUIDMixin") for b in bases):
                # Check if it inherits from Base indirectly
                if not any("Model" in b or "Mixin" in b or "Base" in b for b in bases):
                    continue

            columns = []
            relationships = []
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            # Detect Column() or relationship()
                            if isinstance(item.value, ast.Call):
                                func_name = ""
                                if isinstance(item.value.func, ast.Name):
                                    func_name = item.value.func.id
                                elif isinstance(item.value.func, ast.Attribute):
                                    func_name = item.value.func.attr
                                if func_name in ("Column", "mapped_column"):
                                    columns.append(target.id)
                                elif func_name == "relationship":
                                    relationships.append(target.id)
                            else:
                                columns.append(target.id)
                elif isinstance(item, ast.AnnAssign) and item.target:
                    if isinstance(item.target, ast.Name):
                        col_name = item.target.id
                        # Check if it's a Mapped[] column
                        columns.append(col_name)

            if columns or relationships:
                models[node.name] = {
                    "file": py_file.name,
                    "bases": bases,
                    "columns": columns,
                    "relationships": relationships,
                }

    return models


def extract_api_endpoints():
    """Extract all API endpoint details: method, path, function name."""
    api_dir = BACKEND_SRC / "api" / "v1"
    endpoints = []

    if not api_dir.exists():
        return endpoints

    route_pattern = re.compile(
        r'@(?:router|app|protected_router)\.(get|post|put|delete|patch|websocket)'
        r'\s*\(\s*["\']([^"\']*)["\']'
    )

    for py_file in api_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = str(py_file.relative_to(BACKEND_SRC))
        for match in route_pattern.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            # Find the function name (next def after decorator)
            pos = match.end()
            func_match = re.search(r'(?:async\s+)?def\s+(\w+)', content[pos:pos+200])
            func_name = func_match.group(1) if func_match else "unknown"
            endpoints.append({
                "method": method,
                "path": path,
                "function": func_name,
                "file": rel_path,
            })

    return endpoints


def extract_layer_summary(layer_id: str, layer_config: dict) -> dict:
    """Extract a focused code summary for one layer."""
    summary = {
        "layer": layer_id,
        "files": [],
        "classes": [],
        "key_functions": [],
        "imports_from": set(),
        "total_files": 0,
        "total_loc": 0,
    }

    if layer_config.get("frontend"):
        base = FRONTEND_SRC
        extensions = {".ts", ".tsx"}
    else:
        base = BACKEND_SRC / layer_config["path"]
        extensions = {".py"}

    # For L09, only scan specific submodules
    if "submodules" in layer_config:
        scan_dirs = [BACKEND_SRC / "integrations" / sub for sub in layer_config["submodules"]]
    elif "extra" in layer_config:
        scan_dirs = [base] + [BACKEND_SRC / e for e in layer_config["extra"]]
    else:
        scan_dirs = [base]

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue

        for root, dirs, files in os.walk(scan_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", "dist")]
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix not in extensions:
                    continue

                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                loc = content.count("\n") + 1
                rel = str(fpath.relative_to(PROJECT_ROOT)).replace("\\", "/")
                summary["total_files"] += 1
                summary["total_loc"] += loc

                file_info = {
                    "path": rel,
                    "loc": loc,
                    "classes": [],
                    "functions": [],
                }

                if fpath.suffix == ".py":
                    try:
                        tree = ast.parse(content)
                    except Exception:
                        summary["files"].append(file_info)
                        continue

                    for node in ast.iter_child_nodes(tree):
                        if isinstance(node, ast.ClassDef):
                            methods = []
                            docstring = ""
                            for item in node.body:
                                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    # Get method signature
                                    args = []
                                    for a in item.args.args:
                                        if a.arg != "self":
                                            ann = ""
                                            if a.annotation:
                                                ann = ast.dump(a.annotation)[:30]
                                            args.append(f"{a.arg}")
                                    ret = ""
                                    if item.returns:
                                        try:
                                            ret = ast.unparse(item.returns)[:40]
                                        except Exception:
                                            ret = "..."
                                    methods.append({
                                        "name": item.name,
                                        "args": args[:8],
                                        "returns": ret,
                                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                                    })
                                elif (isinstance(item, ast.Expr) and
                                      isinstance(item.value, ast.Constant) and
                                      isinstance(item.value.value, str) and
                                      not docstring):
                                    docstring = item.value.value[:200]

                            bases = []
                            for b in node.bases:
                                try:
                                    bases.append(ast.unparse(b))
                                except Exception:
                                    bases.append("?")

                            cls_info = {
                                "name": node.name,
                                "bases": bases,
                                "docstring": docstring,
                                "methods": methods,
                                "method_count": len(methods),
                            }
                            file_info["classes"].append(cls_info)
                            summary["classes"].append(cls_info)

                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            file_info["functions"].append(node.name)
                            summary["key_functions"].append(f"{rel}:{node.name}")

                        elif isinstance(node, (ast.Import, ast.ImportFrom)):
                            if isinstance(node, ast.ImportFrom) and node.module:
                                if node.module.startswith("src."):
                                    summary["imports_from"].add(node.module)

                summary["files"].append(file_info)

    # Convert set to list for JSON
    summary["imports_from"] = sorted(summary["imports_from"])

    return summary


# ═══════════════════════════════════════════════════════════════
# GAP DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_gaps(truth: dict, v9_mentions: set) -> dict:
    """Find important items in codebase NOT mentioned in V9."""
    gaps = {
        "unmentiond_important_classes": [],
        "undocumented_db_columns": [],
        "undocumented_endpoints": [],
        "undocumented_enums": [],
        "summary": {},
    }

    # 1. Important classes not in V9 (5+ methods = important)
    for cls in truth.get("backend_classes", []):
        name = cls["name"]
        methods = cls.get("methods", [])
        if len(methods) >= 5 and name not in v9_mentions:
            gaps["unmentiond_important_classes"].append({
                "name": name,
                "file": cls.get("file", ""),
                "method_count": len(methods),
                "methods": methods[:10],
            })

    # 2. DB model columns
    db_models = extract_db_models()
    # Check V9 data-model file for column mentions
    dm_file = V9_DIR / "08-data-model" / "data-model-analysis.md"
    dm_content = dm_file.read_text(encoding="utf-8", errors="ignore") if dm_file.exists() else ""

    for model_name, info in db_models.items():
        for col in info["columns"]:
            if col not in dm_content and col not in ("id", "created_at", "updated_at"):
                gaps["undocumented_db_columns"].append({
                    "model": model_name,
                    "column": col,
                    "file": info["file"],
                })

    # 3. API endpoints not documented
    endpoints = extract_api_endpoints()
    api_file = V9_DIR / "09-api-reference" / "api-reference.md"
    api_content = api_file.read_text(encoding="utf-8", errors="ignore") if api_file.exists() else ""

    for ep in endpoints:
        # Check if endpoint path or function name is mentioned
        if ep["path"] not in api_content and ep["function"] not in api_content:
            gaps["undocumented_endpoints"].append(ep)

    # 4. Enums not documented
    for enum in truth.get("backend_enums", []):
        name = enum["name"]
        if name not in v9_mentions and len(enum.get("values", [])) >= 3:
            gaps["undocumented_enums"].append({
                "name": name,
                "file": enum.get("file", ""),
                "values": enum.get("values", [])[:10],
                "value_count": len(enum.get("values", [])),
            })

    gaps["summary"] = {
        "total_classes_in_codebase": len(truth.get("backend_classes", [])),
        "important_classes_unmentioned": len(gaps["unmentiond_important_classes"]),
        "total_db_columns": sum(len(m["columns"]) for m in db_models.values()),
        "undocumented_db_columns": len(gaps["undocumented_db_columns"]),
        "total_api_endpoints": len(endpoints),
        "undocumented_endpoints": len(gaps["undocumented_endpoints"]),
        "total_enums": len(truth.get("backend_enums", [])),
        "undocumented_enums": len(gaps["undocumented_enums"]),
    }

    return gaps


def generate_gap_report(gaps: dict) -> str:
    s = gaps["summary"]
    lines = [
        "# R8 Gap Detection Report",
        "",
        "> Reverse analysis: what's in the codebase but NOT in V9 docs?",
        "> Generated by: r8_gap_detection.py | Date: 2026-03-30",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "| Metric | Total in Code | Undocumented | Coverage |",
        "|--------|-------------|--------------|----------|",
        f"| Important classes (5+ methods) | {s['total_classes_in_codebase']} | "
        f"{s['important_classes_unmentioned']} | "
        f"{(1 - s['important_classes_unmentioned']/max(s['total_classes_in_codebase'],1))*100:.1f}% |",
        f"| DB columns | {s['total_db_columns']} | "
        f"{s['undocumented_db_columns']} | "
        f"{(1 - s['undocumented_db_columns']/max(s['total_db_columns'],1))*100:.1f}% |",
        f"| API endpoints | {s['total_api_endpoints']} | "
        f"{s['undocumented_endpoints']} | "
        f"{(1 - s['undocumented_endpoints']/max(s['total_api_endpoints'],1))*100:.1f}% |",
        f"| Enums (3+ values) | {s['total_enums']} | "
        f"{s['undocumented_enums']} | "
        f"{(1 - s['undocumented_enums']/max(s['total_enums'],1))*100:.1f}% |",
        "",
    ]

    # Important unmentioned classes
    if gaps["unmentiond_important_classes"]:
        lines.append("## Unmentioned Important Classes (5+ methods)")
        lines.append("")
        lines.append("| Class | File | Methods | Top Methods |")
        lines.append("|-------|------|---------|------------|")
        for c in sorted(gaps["unmentiond_important_classes"],
                       key=lambda x: -x["method_count"])[:40]:
            top = ", ".join(c["methods"][:5])
            lines.append(f"| `{c['name']}` | {c['file'][:40]} | {c['method_count']} | {top} |")
        lines.append("")

    # Undocumented DB columns
    if gaps["undocumented_db_columns"]:
        lines.append("## Undocumented DB Columns")
        lines.append("")
        by_model = defaultdict(list)
        for item in gaps["undocumented_db_columns"]:
            by_model[item["model"]].append(item["column"])
        for model, cols in sorted(by_model.items()):
            lines.append(f"### {model}")
            lines.append(f"Undocumented columns: `{'`, `'.join(cols)}`")
            lines.append("")

    # Undocumented endpoints
    if gaps["undocumented_endpoints"]:
        lines.append("## Undocumented API Endpoints")
        lines.append("")
        lines.append("| Method | Path | Function | File |")
        lines.append("|--------|------|----------|------|")
        for ep in gaps["undocumented_endpoints"][:50]:
            lines.append(f"| {ep['method']} | `{ep['path']}` | {ep['function']} | {ep['file'][:40]} |")
        if len(gaps["undocumented_endpoints"]) > 50:
            lines.append(f"| ... | ({len(gaps['undocumented_endpoints'])-50} more) | | |")
        lines.append("")

    # Undocumented enums
    if gaps["undocumented_enums"]:
        lines.append("## Undocumented Enums")
        lines.append("")
        lines.append("| Enum | File | Values | Count |")
        lines.append("|------|------|--------|-------|")
        for e in sorted(gaps["undocumented_enums"],
                       key=lambda x: -x["value_count"])[:30]:
            vals = ", ".join(e["values"][:5])
            lines.append(f"| `{e['name']}` | {e['file'][:35]} | {vals} | {e['value_count']} |")
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("R8 Phase A: Gap Detection + Layer Summary Extraction")
    print("=" * 70)

    truth = load_truth()

    # Collect all V9 mentions
    print("\n[1/4] Collecting V9 class/name mentions...")
    v9_mentions = collect_v9_mentions()
    print(f"  {len(v9_mentions)} unique names found in V9")

    # Gap detection
    print("\n[2/4] Running reverse gap detection...")
    gaps = detect_gaps(truth, v9_mentions)
    s = gaps["summary"]
    print(f"  Important classes unmentioned: {s['important_classes_unmentioned']}")
    print(f"  DB columns undocumented: {s['undocumented_db_columns']}")
    print(f"  API endpoints undocumented: {s['undocumented_endpoints']}")
    print(f"  Enums undocumented: {s['undocumented_enums']}")

    # Save gap report
    with open(GAP_JSON, "w", encoding="utf-8") as f:
        json.dump(gaps, f, indent=2, ensure_ascii=False)
    report = generate_gap_report(gaps)
    with open(GAP_MD, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  [OK] Gap report: {GAP_MD}")

    # Layer summaries
    print("\n[3/4] Extracting per-layer code summaries...")
    SUMMARY_DIR.mkdir(exist_ok=True)

    layer_stats = []
    for layer_id, config in sorted(LAYER_DIRS.items()):
        print(f"  Extracting {layer_id}...", end=" ")
        summary = extract_layer_summary(layer_id, config)
        # Save to file
        out_file = SUMMARY_DIR / f"{layer_id}-summary.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        print(f"{summary['total_files']} files, {len(summary['classes'])} classes, "
              f"{summary['total_loc']} LOC")
        layer_stats.append({
            "layer": layer_id,
            "files": summary["total_files"],
            "classes": len(summary["classes"]),
            "loc": summary["total_loc"],
        })

    # Summary table
    print("\n[4/4] Layer summary statistics:")
    print(f"  {'Layer':<6} {'Files':>6} {'Classes':>8} {'LOC':>8}")
    print(f"  {'-'*6} {'-'*6} {'-'*8} {'-'*8}")
    total_f = total_c = total_l = 0
    for ls in layer_stats:
        print(f"  {ls['layer']:<6} {ls['files']:>6} {ls['classes']:>8} {ls['loc']:>8}")
        total_f += ls["files"]
        total_c += ls["classes"]
        total_l += ls["loc"]
    print(f"  {'TOTAL':<6} {total_f:>6} {total_c:>8} {total_l:>8}")

    print(f"\n[OK] All outputs saved.")
    print(f"  Gap report: {GAP_MD}")
    print(f"  Layer summaries: {SUMMARY_DIR}/")


if __name__ == "__main__":
    main()
