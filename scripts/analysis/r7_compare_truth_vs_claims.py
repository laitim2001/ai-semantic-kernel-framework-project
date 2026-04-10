#!/usr/bin/env python3
"""R7 Step 3: Compare codebase truth vs V9 claims, produce diff report.

Reads r7-codebase-truth.json and r7-v9-claims.json, then:
1. Compares per-layer file counts and LOC
2. Checks class existence
3. Cross-file consistency check
4. Produces both JSON and Markdown diff reports
"""

import json
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "analysis"
TRUTH_FILE = SCRIPTS_DIR / "r7-codebase-truth.json"
CLAIMS_FILE = SCRIPTS_DIR / "r7-v9-claims.json"
DIFF_JSON = SCRIPTS_DIR / "r7-diff-report.json"
DIFF_MD = PROJECT_ROOT / "docs" / "07-analysis" / "V9" / "r7-validation-report.md"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_layer_stats(truth: dict, claims: dict) -> list:
    """Compare per-layer file counts and LOC."""
    diffs = []
    truth_layers = truth.get("backend_per_layer", {})
    claim_layers = claims.get("key_claims", {}).get("layer_files", {})

    # Also check stats file
    stats = claims.get("key_claims", {}).get("stats_file", {})

    # Build a map of V9 claimed layer stats from layer_claims
    v9_layer_stats = {}
    for file_results in claims.get("per_file", []):
        for lc in file_results.get("layer_claims", []):
            layer_id = lc["layer"]
            if layer_id not in v9_layer_stats:
                v9_layer_stats[layer_id] = []
            v9_layer_stats[layer_id].append({
                "files": lc["files"],
                "loc": lc["loc"],
                "source_file": file_results["file"],
            })

    # Compare each layer
    for layer_id, truth_data in truth_layers.items():
        if layer_id.startswith("L09-") or layer_id.startswith("L11-"):
            continue

        actual_files = truth_data["files"]
        actual_loc = truth_data["loc"]

        # Find V9 claims for this layer
        layer_claims = v9_layer_stats.get(layer_id, [])

        for claim in layer_claims:
            claimed_files = claim["files"]
            claimed_loc = claim["loc"]
            source = claim["source_file"]

            file_diff = actual_files - claimed_files
            loc_diff = actual_loc - claimed_loc
            file_pct = abs(file_diff) / max(claimed_files, 1) * 100
            loc_pct = abs(loc_diff) / max(claimed_loc, 1) * 100

            status = "PASS"
            if file_pct > 10 or loc_pct > 15:
                status = "FAIL"
            elif file_pct > 5 or loc_pct > 10:
                status = "WARN"

            diffs.append({
                "layer": layer_id,
                "source_file": source,
                "metric": "files+loc",
                "actual_files": actual_files,
                "claimed_files": claimed_files,
                "file_diff": file_diff,
                "file_pct": round(file_pct, 1),
                "actual_loc": actual_loc,
                "claimed_loc": claimed_loc,
                "loc_diff": loc_diff,
                "loc_pct": round(loc_pct, 1),
                "status": status,
            })

    return diffs


def check_class_existence(truth: dict, claims: dict) -> list:
    """Check if classes mentioned in V9 files actually exist in codebase."""
    # Build set of actual class names
    actual_classes = set()
    for cls in truth.get("backend_classes", []):
        actual_classes.add(cls["name"])

    # Check all class mentions in V9
    results = []
    checked = set()

    for file_results in claims.get("per_file", []):
        source_file = file_results["file"]
        for class_name in file_results.get("class_mentions", []):
            if class_name in checked:
                continue
            checked.add(class_name)

            exists = class_name in actual_classes
            if not exists:
                results.append({
                    "class_name": class_name,
                    "exists": False,
                    "first_mentioned_in": source_file,
                })

    return results


def check_cross_file_consistency(claims: dict) -> list:
    """Check if the same metric is consistent across different V9 files."""
    # Collect all LOC claims per layer
    layer_loc_claims = defaultdict(list)
    layer_file_claims = defaultdict(list)

    for file_results in claims.get("per_file", []):
        source = file_results["file"]
        for lc in file_results.get("layer_claims", []):
            layer_loc_claims[lc["layer"]].append({
                "loc": lc["loc"],
                "files": lc["files"],
                "source": source,
            })

    inconsistencies = []
    for layer_id, entries in layer_loc_claims.items():
        if len(entries) < 2:
            continue

        # Check if all LOC values match
        locs = [e["loc"] for e in entries]
        files_counts = [e["files"] for e in entries]

        if len(set(locs)) > 1:
            inconsistencies.append({
                "layer": layer_id,
                "metric": "loc",
                "values": [{"value": e["loc"], "source": e["source"]} for e in entries],
            })
        if len(set(files_counts)) > 1:
            inconsistencies.append({
                "layer": layer_id,
                "metric": "files",
                "values": [{"value": e["files"], "source": e["source"]} for e in entries],
            })

    return inconsistencies


def check_key_totals(truth: dict, claims: dict) -> list:
    """Check key aggregate numbers (total files, LOC, routes, etc.)."""
    checks = []
    totals = truth.get("project_totals", {})

    # Define expected claims from 00-stats.md
    stats_claims = claims.get("key_claims", {}).get("stats_file", {})

    # Check total route count
    actual_routes = totals.get("total_routes", 0)
    for nc in stats_claims.get("numeric_claims", []):
        if nc["type"] == "endpoints":
            claimed = nc["value"]
            diff = actual_routes - claimed
            checks.append({
                "metric": "total_endpoints",
                "actual": actual_routes,
                "claimed": claimed,
                "diff": diff,
                "pct": round(abs(diff) / max(claimed, 1) * 100, 1),
                "source": "00-stats.md",
                "status": "PASS" if abs(diff) / max(claimed, 1) < 0.1 else "WARN",
            })

    # Check total backend files
    actual_be_files = totals.get("backend_files", 0)
    for nc in stats_claims.get("numeric_claims", []):
        if nc["type"] == "files" and "793" in nc["context"]:
            checks.append({
                "metric": "backend_py_files",
                "actual": actual_be_files,
                "claimed": 793,
                "diff": actual_be_files - 793,
                "source": "00-stats.md",
                "status": "PASS" if abs(actual_be_files - 793) < 20 else "WARN",
            })

    # Check frontend files
    actual_fe_files = totals.get("frontend_files", 0)
    for nc in stats_claims.get("numeric_claims", []):
        if nc["type"] == "files" and "297" in nc["context"]:
            checks.append({
                "metric": "frontend_ts_files",
                "actual": actual_fe_files,
                "claimed": 297,
                "diff": actual_fe_files - 297,
                "source": "00-stats.md",
                "status": "PASS" if abs(actual_fe_files - 297) < 20 else "WARN",
            })

    return checks


def generate_markdown_report(layer_diffs, missing_classes, inconsistencies,
                              total_checks, truth, claims):
    """Generate human-readable markdown report."""
    lines = [
        "# V9 Round 7 Validation Report",
        "",
        "> **Generated by**: r7_compare_truth_vs_claims.py",
        "> **Date**: 2026-03-30",
        "> **Method**: Programmatic AST extraction + regex claim extraction + auto-compare",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
    ]

    # Count results
    total_pass = sum(1 for d in layer_diffs if d["status"] == "PASS")
    total_warn = sum(1 for d in layer_diffs if d["status"] == "WARN")
    total_fail = sum(1 for d in layer_diffs if d["status"] == "FAIL")
    total_pass += sum(1 for c in total_checks if c["status"] == "PASS")
    total_warn += sum(1 for c in total_checks if c["status"] == "WARN")

    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Layer stat checks | {len(layer_diffs)} |")
    lines.append(f"| Key total checks | {len(total_checks)} |")
    lines.append(f"| Classes checked | {len(missing_classes)} missing |")
    lines.append(f"| Cross-file inconsistencies | {len(inconsistencies)} |")
    lines.append(f"| **PASS** | {total_pass} |")
    lines.append(f"| **WARN** | {total_warn} |")
    lines.append(f"| **FAIL** | {total_fail} |")
    lines.append("")

    # Actual totals
    totals = truth.get("project_totals", {})
    lines.append("## 2. Actual Codebase Totals (Ground Truth)")
    lines.append("")
    lines.append("| Metric | Actual Value |")
    lines.append("|--------|-------------|")
    lines.append(f"| Backend .py files | {totals.get('backend_files', 'N/A')} |")
    lines.append(f"| Backend LOC | {totals.get('backend_loc', 'N/A')} |")
    lines.append(f"| Frontend files | {totals.get('frontend_files', 'N/A')} |")
    lines.append(f"| Frontend LOC | {totals.get('frontend_loc', 'N/A')} |")
    lines.append(f"| Total files | {totals.get('total_files', 'N/A')} |")
    lines.append(f"| Total LOC | {totals.get('total_loc', 'N/A')} |")
    lines.append(f"| Total classes | {totals.get('total_classes', 'N/A')} |")
    lines.append(f"| Total enums | {totals.get('total_enums', 'N/A')} |")
    lines.append(f"| Total routes (@router) | {totals.get('total_routes', 'N/A')} |")
    lines.append(f"| Frontend components | {totals.get('frontend_components', 'N/A')} |")
    lines.append(f"| Frontend hooks | {totals.get('frontend_hooks', 'N/A')} |")
    lines.append(f"| Frontend pages | {totals.get('frontend_pages', 'N/A')} |")
    lines.append("")

    # Per-layer breakdown
    lines.append("### 2.1 Per-Layer Actual Stats")
    lines.append("")
    lines.append("| Layer | Actual Files | Actual LOC | Classes | Enums |")
    lines.append("|-------|-------------|-----------|---------|-------|")
    for layer_id in sorted(truth.get("backend_per_layer", {}).keys()):
        if layer_id.startswith("L09-") or layer_id.startswith("L11-"):
            continue
        data = truth["backend_per_layer"][layer_id]
        lines.append(
            f"| {layer_id} | {data['files']} | {data['loc']} | "
            f"{data.get('class_count', 'N/A')} | {data.get('enum_count', 'N/A')} |"
        )
    lines.append("")

    # Layer diff results
    lines.append("## 3. Layer Stats: Actual vs V9 Claims")
    lines.append("")
    if layer_diffs:
        lines.append("| Layer | Source File | Actual Files | Claimed | Δ | Actual LOC | Claimed | Δ | Status |")
        lines.append("|-------|-----------|-------------|---------|---|-----------|---------|---|--------|")
        for d in sorted(layer_diffs, key=lambda x: x["layer"]):
            lines.append(
                f"| {d['layer']} | {d['source_file'][:30]} | "
                f"{d['actual_files']} | {d['claimed_files']} | {d['file_diff']:+d} | "
                f"{d['actual_loc']} | {d['claimed_loc']} | {d['loc_diff']:+d} | "
                f"{'✅' if d['status'] == 'PASS' else '⚠️' if d['status'] == 'WARN' else '❌'} {d['status']} |"
            )
    else:
        lines.append("No layer-level claims found to compare.")
    lines.append("")

    # Key totals
    lines.append("## 4. Key Total Checks")
    lines.append("")
    if total_checks:
        lines.append("| Metric | Actual | Claimed | Diff | Status |")
        lines.append("|--------|--------|---------|------|--------|")
        for c in total_checks:
            lines.append(
                f"| {c['metric']} | {c['actual']} | {c['claimed']} | "
                f"{c['diff']:+d} | {'✅' if c['status'] == 'PASS' else '⚠️'} {c['status']} |"
            )
    lines.append("")

    # Missing classes
    lines.append("## 5. Class Existence Check")
    lines.append("")
    if missing_classes:
        lines.append(f"**{len(missing_classes)} classes mentioned in V9 but NOT found in codebase:**")
        lines.append("")
        lines.append("| Class Name | First Mentioned In |")
        lines.append("|------------|-------------------|")
        for mc in missing_classes[:50]:  # Limit to 50
            lines.append(f"| `{mc['class_name']}` | {mc['first_mentioned_in']} |")
        if len(missing_classes) > 50:
            lines.append(f"| ... | ({len(missing_classes) - 50} more) |")
    else:
        lines.append("All mentioned classes exist in codebase. ✅")
    lines.append("")

    # Cross-file inconsistencies
    lines.append("## 6. Cross-File Consistency")
    lines.append("")
    if inconsistencies:
        lines.append(f"**{len(inconsistencies)} inconsistencies found:**")
        lines.append("")
        for inc in inconsistencies:
            lines.append(f"### {inc['layer']} — {inc['metric']}")
            for v in inc["values"]:
                lines.append(f"- `{v['source']}`: {v['value']}")
            lines.append("")
    else:
        lines.append("All cross-file values are consistent. ✅")
    lines.append("")

    # L09 sub-module breakdown
    l09 = truth.get("backend_per_layer", {}).get("L09", {})
    if l09.get("sub_modules"):
        lines.append("## 7. L09 Sub-Module Breakdown (Actual)")
        lines.append("")
        lines.append("| Sub-Module | Files | LOC |")
        lines.append("|-----------|-------|-----|")
        for name, data in sorted(l09["sub_modules"].items()):
            lines.append(f"| {name}/ | {data['files']} | {data['loc']} |")
        lines.append(f"| **Total L09** | **{l09['files']}** | **{l09['loc']}** |")
        lines.append("")

    # L11 sub-module breakdown
    l11 = truth.get("backend_per_layer", {}).get("L11", {})
    if l11.get("sub_modules"):
        lines.append("## 8. L11 Sub-Module Breakdown (Actual)")
        lines.append("")
        lines.append("| Sub-Module | Files | LOC |")
        lines.append("|-----------|-------|-----|")
        for name, data in sorted(l11["sub_modules"].items()):
            lines.append(f"| {name}/ | {data['files']} | {data['loc']} |")
        lines.append(f"| **Total L11** | **{l11['files']}** | **{l11['loc']}** |")
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("R7 Step 3: Comparing truth vs claims")
    print("=" * 60)

    if not TRUTH_FILE.exists():
        print(f"ERROR: {TRUTH_FILE} not found. Run r7_extract_codebase_truth.py first.")
        return
    if not CLAIMS_FILE.exists():
        print(f"ERROR: {CLAIMS_FILE} not found. Run r7_extract_v9_claims.py first.")
        return

    truth = load_json(TRUTH_FILE)
    claims = load_json(CLAIMS_FILE)

    print("\n[1/4] Comparing layer stats...")
    layer_diffs = compare_layer_stats(truth, claims)
    pass_count = sum(1 for d in layer_diffs if d["status"] == "PASS")
    warn_count = sum(1 for d in layer_diffs if d["status"] == "WARN")
    fail_count = sum(1 for d in layer_diffs if d["status"] == "FAIL")
    print(f"  Layer checks: {len(layer_diffs)} total — {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL")

    print("\n[2/4] Checking class existence...")
    missing_classes = check_class_existence(truth, claims)
    print(f"  Missing classes: {len(missing_classes)}")

    print("\n[3/4] Checking cross-file consistency...")
    inconsistencies = check_cross_file_consistency(claims)
    print(f"  Inconsistencies: {len(inconsistencies)}")

    print("\n[4/4] Checking key totals...")
    total_checks = check_key_totals(truth, claims)
    for c in total_checks:
        print(f"  {c['metric']}: actual={c['actual']} claimed={c['claimed']} "
              f"diff={c['diff']:+d} → {c['status']}")

    # Generate reports
    diff_data = {
        "layer_diffs": layer_diffs,
        "missing_classes": missing_classes,
        "inconsistencies": inconsistencies,
        "total_checks": total_checks,
    }

    with open(DIFF_JSON, "w", encoding="utf-8") as f:
        json.dump(diff_data, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON report: {DIFF_JSON}")

    md_report = generate_markdown_report(
        layer_diffs, missing_classes, inconsistencies, total_checks, truth, claims
    )
    with open(DIFF_MD, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"[OK] Markdown report: {DIFF_MD}")

    print(f"\n[OK] R7 comparison complete!")


if __name__ == "__main__":
    main()
