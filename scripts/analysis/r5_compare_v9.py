"""
R5-B: Auto-compare V9 analysis claims against R5-A extracted JSON truth.
Reads V9 .md files, extracts numeric claims, compares with JSON data.
"""
import json, re, sys
from pathlib import Path

V9_DIR = Path(__file__).parent.parent.parent / "docs" / "07-analysis" / "V9"
REPORT = []

def load_json(name):
    with open(V9_DIR / name, encoding="utf-8") as f:
        return json.load(f)

def add_finding(category, severity, v9_file, claim, actual, detail=""):
    REPORT.append({
        "category": category,
        "severity": severity,  # MATCH, MINOR, MAJOR, CRITICAL
        "v9_file": v9_file,
        "v9_claim": claim,
        "actual": actual,
        "detail": detail,
    })

def compare_number(v9_file, label, claimed, actual, tolerance=0.05):
    """Compare a numeric claim. tolerance=0.05 means 5% is MATCH."""
    if claimed == actual:
        add_finding(label, "MATCH", v9_file, str(claimed), str(actual))
    elif abs(claimed - actual) / max(actual, 1) <= tolerance:
        add_finding(label, "MINOR", v9_file, str(claimed), str(actual),
                    f"Off by {abs(claimed-actual)} ({abs(claimed-actual)/max(actual,1)*100:.1f}%)")
    elif abs(claimed - actual) / max(actual, 1) <= 0.20:
        add_finding(label, "MAJOR", v9_file, str(claimed), str(actual),
                    f"Off by {abs(claimed-actual)} ({abs(claimed-actual)/max(actual,1)*100:.1f}%)")
    else:
        add_finding(label, "CRITICAL", v9_file, str(claimed), str(actual),
                    f"Off by {abs(claimed-actual)} ({abs(claimed-actual)/max(actual,1)*100:.1f}%)")

def extract_numbers_from_md(filepath):
    """Extract all numbers that appear near keywords in a markdown file."""
    content = Path(filepath).read_text(encoding="utf-8", errors="replace")
    numbers = {}
    # Pattern: "Files: 75" or "75 files" or "LOC: 24,000" or "~24,000 LOC"
    for m in re.finditer(r'(\d[\d,]*)\s*(?:files?|LOC|lines?|endpoints?|classes?|schemas?|tools?|components?|interfaces?)', content, re.IGNORECASE):
        val = int(m.group(1).replace(",", ""))
        numbers[m.start()] = val
    return numbers

def check_stats():
    """Compare 00-stats.md claims against R5 extracted data."""
    classes = load_json("r5-classes.json")
    routes = load_json("r5-routes.json")
    enums_data = load_json("r5-enums.json")
    schemas = load_json("r5-schemas.json")
    imports = load_json("r5-imports.json")
    frontend = load_json("r5-frontend.json")

    # Actuals from R5
    actual = {
        "backend_classes": classes["summary"]["total_classes"],
        "backend_methods": classes["summary"]["total_methods"],
        "api_endpoints": routes["summary"]["total_endpoints"],
        "enums": enums_data["summary"]["total_enums"],
        "enum_values": enums_data["summary"]["total_values"],
        "pydantic_schemas": schemas["summary"]["total_schemas"],
        "pydantic_fields": schemas["summary"]["total_fields"],
        "circular_deps": imports["summary"]["circular_dependencies"],
        "fe_components": frontend["summary"]["total_components"],
        "fe_interfaces": frontend["summary"]["total_interfaces"],
        "fe_types": frontend["summary"]["total_types"],
        "fe_hooks_defined": frontend["summary"]["total_hooks_defined"],
        "fe_props_interfaces": frontend["summary"]["total_props_interfaces"],
    }

    # Read 00-stats.md for V9 claims
    stats_file = V9_DIR / "00-stats.md"
    if stats_file.exists():
        content = stats_file.read_text(encoding="utf-8", errors="replace")

        # Extract specific claims from stats
        m = re.search(r'API Endpoint.*?\|\s*(\d+)', content)
        if m: compare_number("00-stats.md", "API Endpoints (stats)", int(m.group(1)), actual["api_endpoints"])

        m = re.search(r'Pydantic.*?Classes.*?\|\s*~?(\d+)', content)
        if m: compare_number("00-stats.md", "Pydantic Schemas (stats)", int(m.group(1)), actual["pydantic_schemas"])

    return actual

def check_layer_files(actuals):
    """Check each layer file for LOC and file count claims."""
    # Load backend metadata for per-module LOC
    try:
        with open(V9_DIR / "backend-metadata.json", encoding="utf-8") as f:
            backend_meta = json.load(f)
        module_loc = {}
        for file_entry in backend_meta["files"]:
            path = file_entry["path"]
            parts = path.split("/")
            if len(parts) >= 4:
                mod_key = "/".join(parts[2:4])
            else:
                mod_key = "root"
            module_loc[mod_key] = module_loc.get(mod_key, 0) + file_entry["loc"]
    except:
        module_loc = {}

    # Check each layer file
    for layer_file in sorted(V9_DIR.glob("01-architecture/layer-*.md")):
        if "verification" in layer_file.name:
            continue
        content = layer_file.read_text(encoding="utf-8", errors="replace")
        name = layer_file.name

        # Extract LOC claims
        loc_claims = re.findall(r'LOC[:\s]*~?([\d,]+)', content)
        file_claims = re.findall(r'Files?[:\s]*~?(\d+)', content)

        # Store for reporting
        add_finding("layer_check", "INFO", name,
                    f"LOC claims found: {len(loc_claims)}, File claims found: {len(file_claims)}",
                    "See detailed comparison", "")

def check_class_coverage():
    """Check how many R5 classes appear in V9 analysis files."""
    classes = load_json("r5-classes.json")

    # Collect all class names from R5
    all_r5_classes = set()
    for file_classes in classes["files"].values():
        for cls in file_classes:
            all_r5_classes.add(cls["name"])

    # Scan all V9 .md files for class name mentions
    mentioned_classes = set()
    for md_file in V9_DIR.rglob("*.md"):
        if "R4-semantic" in str(md_file) or "verification" in str(md_file):
            continue  # Skip semantic summaries and verification files
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for cls_name in all_r5_classes:
            if cls_name in content and len(cls_name) > 3:  # Skip short names to avoid false matches
                mentioned_classes.add(cls_name)

    missing = all_r5_classes - mentioned_classes
    # Filter out trivial classes (private, test, etc.)
    significant_missing = {c for c in missing if not c.startswith("_") and len(c) > 5}

    add_finding("class_coverage", "INFO", "all V9 docs",
                f"R5 found {len(all_r5_classes)} unique classes",
                f"{len(mentioned_classes)} mentioned in V9 ({len(mentioned_classes)/len(all_r5_classes)*100:.1f}%)",
                f"{len(significant_missing)} significant classes not mentioned")

    return all_r5_classes, mentioned_classes, significant_missing

def check_endpoint_coverage():
    """Check all R5 endpoints against V9 api-reference."""
    routes = load_json("r5-routes.json")

    all_endpoints = []
    for file_routes in routes["files"].values():
        for r in file_routes:
            all_endpoints.append(f"{r['method']} {r['path']}")

    # Read api-reference.md
    api_ref = V9_DIR / "09-api-reference" / "api-reference.md"
    if api_ref.exists():
        content = api_ref.read_text(encoding="utf-8", errors="replace")
        mentioned_endpoints = set()
        for ep in all_endpoints:
            method, path = ep.split(" ", 1)
            if path in content:
                mentioned_endpoints.add(ep)

        add_finding("endpoint_coverage", "INFO", "api-reference.md",
                    f"R5 found {len(all_endpoints)} endpoints",
                    f"{len(mentioned_endpoints)} paths found in api-reference ({len(mentioned_endpoints)/len(all_endpoints)*100:.1f}%)",
                    f"{len(all_endpoints) - len(mentioned_endpoints)} endpoint paths not in api-reference")

def check_enum_coverage():
    """Check all R5 enums appear in V9."""
    enums = load_json("r5-enums.json")
    all_enum_names = set()
    for file_enums in enums["files"].values():
        for e in file_enums:
            all_enum_names.add(e["name"])

    mentioned = set()
    for md_file in V9_DIR.rglob("*.md"):
        if "R4-semantic" in str(md_file): continue
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for name in all_enum_names:
            if name in content and len(name) > 3:
                mentioned.add(name)

    add_finding("enum_coverage", "INFO", "all V9 docs",
                f"R5 found {len(all_enum_names)} enums",
                f"{len(mentioned)} mentioned ({len(mentioned)/max(len(all_enum_names),1)*100:.1f}%)",
                f"{len(all_enum_names) - len(mentioned)} enums not in V9")

def generate_report():
    """Generate the comparison report."""
    summary = {"MATCH": 0, "MINOR": 0, "MAJOR": 0, "CRITICAL": 0, "INFO": 0}
    for f in REPORT:
        summary[f["severity"]] = summary.get(f["severity"], 0) + 1

    output = {
        "summary": summary,
        "total_findings": len(REPORT),
        "findings": REPORT,
    }

    # Write JSON
    with open(V9_DIR / "r5-comparison-report.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Write MD
    with open(V9_DIR / "r5-comparison-report.md", "w", encoding="utf-8") as f:
        f.write("# R5 Comparison Report: V9 Claims vs Code Reality\n\n")
        f.write(f"> Generated by `r5_compare_v9.py` | Date: 2026-03-30\n\n")
        f.write("## Summary\n\n")
        f.write(f"| Severity | Count |\n|----------|-------|\n")
        for sev in ["MATCH", "MINOR", "MAJOR", "CRITICAL", "INFO"]:
            f.write(f"| {sev} | {summary.get(sev, 0)} |\n")
        f.write(f"| **Total** | **{len(REPORT)}** |\n\n")

        f.write("## R5 Extracted Data (Ground Truth)\n\n")
        f.write("| Category | Count | Detail |\n|----------|-------|--------|\n")

        f.write("## Detailed Findings\n\n")
        for finding in REPORT:
            icon = {"MATCH": "✅", "MINOR": "⚠️", "MAJOR": "❌", "CRITICAL": "🔴", "INFO": "ℹ️"}.get(finding["severity"], "?")
            f.write(f"### {icon} [{finding['severity']}] {finding['category']}\n")
            f.write(f"- **V9 file**: {finding['v9_file']}\n")
            f.write(f"- **V9 claim**: {finding['v9_claim']}\n")
            f.write(f"- **Actual**: {finding['actual']}\n")
            if finding['detail']:
                f.write(f"- **Detail**: {finding['detail']}\n")
            f.write("\n")

    return summary

if __name__ == "__main__":
    print("R5-B: Comparing V9 claims vs code reality...")

    print("\n1. Checking stats...")
    actuals = check_stats()

    print("2. Checking layer files...")
    check_layer_files(actuals)

    print("3. Checking class coverage...")
    all_cls, mentioned_cls, missing_cls = check_class_coverage()

    print("4. Checking endpoint coverage...")
    check_endpoint_coverage()

    print("5. Checking enum coverage...")
    check_enum_coverage()

    print("\n6. Generating report...")
    summary = generate_report()

    print(f"\n=== R5-B Comparison Complete ===")
    print(f"Total findings: {len(REPORT)}")
    for sev, count in summary.items():
        print(f"  {sev}: {count}")
    print(f"\nR5 Ground Truth:")
    print(f"  Classes: {actuals['backend_classes']} ({actuals['backend_methods']} methods)")
    print(f"  Endpoints: {actuals['api_endpoints']}")
    print(f"  Enums: {actuals['enums']} ({actuals['enum_values']} values)")
    print(f"  Schemas: {actuals['pydantic_schemas']} ({actuals['pydantic_fields']} fields)")
    print(f"  Circular deps: {actuals['circular_deps']}")
    print(f"  FE components: {actuals['fe_components']}")
    print(f"  FE interfaces: {actuals['fe_interfaces']}")
    print(f"  FE props: {actuals['fe_props_interfaces']}")
    print(f"\nClass coverage: {len(mentioned_cls)}/{len(all_cls)} ({len(mentioned_cls)/len(all_cls)*100:.1f}%)")
    print(f"Significant classes missing from V9: {len(missing_cls)}")
    print(f"\nOutputs:")
    print(f"  {V9_DIR / 'r5-comparison-report.json'}")
    print(f"  {V9_DIR / 'r5-comparison-report.md'}")
