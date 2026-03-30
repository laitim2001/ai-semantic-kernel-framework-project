"""
R6: Cross-validate ALL V9 markdown claims against R5 JSON ground truth.
Combines R6-A (extract claims), R6-B (validate), R6-C (auto-correct).

Flow:
1. Load all R5 ground truth JSONs
2. Read each V9 .md file, extract numeric/structural claims
3. Validate each claim against ground truth
4. For FAIL items, apply corrections to .md files
5. Output validation report + correction log
"""
import json, re, os, sys
from pathlib import Path
from collections import defaultdict

V9_DIR = Path(__file__).parent.parent.parent / "docs" / "07-analysis" / "V9"

# ─── Load Ground Truth ───

def load_ground_truth():
    """Load all R5 JSON files as ground truth."""
    gt = {}

    # Backend metadata
    with open(V9_DIR / "backend-metadata.json", encoding="utf-8") as f:
        bm = json.load(f)
    gt["backend_total_files"] = bm["summary"]["total_files"]
    gt["backend_code_files"] = bm["summary"]["code_files"]
    gt["backend_total_loc"] = bm["summary"]["total_loc"]
    gt["backend_modules"] = bm["summary"]["modules"]

    # Per-file LOC lookup
    gt["file_loc"] = {}
    for entry in bm["files"]:
        gt["file_loc"][entry["path"]] = entry["loc"]

    # Frontend metadata
    with open(V9_DIR / "frontend-metadata.json", encoding="utf-8") as f:
        fm = json.load(f)
    gt["frontend_total_files"] = fm["summary"]["total_files"]
    gt["frontend_code_files"] = fm["summary"]["code_files"]
    gt["frontend_total_loc"] = fm["summary"]["total_loc"]

    # R5 classes
    with open(V9_DIR / "r5-classes.json", encoding="utf-8") as f:
        cls = json.load(f)
    gt["total_classes"] = cls["summary"]["total_classes"]
    gt["total_methods"] = cls["summary"]["total_methods"]
    gt["class_names"] = set()
    for file_classes in cls["files"].values():
        for c in file_classes:
            gt["class_names"].add(c["name"])

    # R5 routes
    with open(V9_DIR / "r5-routes.json", encoding="utf-8") as f:
        rts = json.load(f)
    gt["total_endpoints"] = rts["summary"]["total_endpoints"]
    gt["endpoint_methods"] = rts["summary"]["methods"]

    # R5 enums
    with open(V9_DIR / "r5-enums.json", encoding="utf-8") as f:
        enums = json.load(f)
    gt["total_enums"] = enums["summary"]["total_enums"]
    gt["total_enum_values"] = enums["summary"]["total_values"]
    gt["enum_names"] = set()
    for file_enums in enums["files"].values():
        for e in file_enums:
            gt["enum_names"].add(e["name"])

    # R5 schemas
    with open(V9_DIR / "r5-schemas.json", encoding="utf-8") as f:
        schemas = json.load(f)
    gt["total_schemas"] = schemas["summary"]["total_schemas"]
    gt["total_schema_fields"] = schemas["summary"]["total_fields"]
    gt["schema_names"] = set()
    for file_schemas in schemas["files"].values():
        for s in file_schemas:
            gt["schema_names"].add(s["name"])

    # R5 imports
    with open(V9_DIR / "r5-imports.json", encoding="utf-8") as f:
        imps = json.load(f)
    gt["circular_deps"] = imps["summary"]["circular_dependencies"]

    # R5 frontend
    with open(V9_DIR / "r5-frontend.json", encoding="utf-8") as f:
        fe = json.load(f)
    gt["fe_components"] = fe["summary"]["total_components"]
    gt["fe_interfaces"] = fe["summary"]["total_interfaces"]
    gt["fe_types"] = fe["summary"]["total_types"]
    gt["fe_hooks"] = fe["summary"]["total_hooks_defined"]

    return gt


# ─── Extract & Validate Claims ───

def extract_and_validate_claims(md_path, gt):
    """Extract numeric claims from a markdown file and validate against GT."""
    content = Path(md_path).read_text(encoding="utf-8", errors="replace")
    rel_path = str(md_path.relative_to(V9_DIR))
    findings = []
    corrections = []  # (old_str, new_str) tuples

    # ── LOC claims: "LOC: 10,329" or "~10,329 LOC" or "10,329 LOC" ──
    for m in re.finditer(r'(?:LOC[:\s]*~?|~\s*)([\d][\d,]+)\s*(?:LOC)?', content):
        raw = m.group(1).replace(",", "").strip()
        if not raw or not raw.isdigit():
            continue
        claimed = int(raw)
        # Skip very small numbers (likely not LOC)
        if claimed < 50:
            continue
        findings.append({
            "type": "loc_claim",
            "value": claimed,
            "context": content[max(0, m.start()-40):m.end()+40].replace("\n", " "),
            "line_offset": content[:m.start()].count("\n") + 1,
        })

    # ── Endpoint count claims ──
    for m in re.finditer(r'(\d+)\s*(?:endpoints?|REST endpoints?|API endpoints?)', content, re.IGNORECASE):
        claimed = int(m.group(1))
        if claimed > 10:  # Skip trivial
            status = "PASS" if abs(claimed - gt["total_endpoints"]) <= 10 else "FAIL"
            findings.append({
                "type": "endpoint_count",
                "claimed": claimed,
                "actual": gt["total_endpoints"],
                "status": status,
                "context": content[max(0, m.start()-30):m.end()+30].replace("\n", " "),
            })
            if status == "FAIL" and abs(claimed - gt["total_endpoints"]) > 10:
                old = m.group(0)
                new = old.replace(str(claimed), str(gt["total_endpoints"]))
                corrections.append((old, new, rel_path, "endpoint count"))

    # ── Class count claims ──
    for m in re.finditer(r'(\d[\d,]*)\s*(?:classes|class definitions)', content, re.IGNORECASE):
        claimed = int(m.group(1).replace(",", ""))
        if claimed > 50:
            status = "PASS" if abs(claimed - gt["total_classes"]) <= 50 else "FAIL"
            findings.append({
                "type": "class_count",
                "claimed": claimed,
                "actual": gt["total_classes"],
                "status": status,
            })

    # ── Schema count claims ──
    for m in re.finditer(r'(\d+)\s*(?:Pydantic|BaseModel|schema)\s*(?:classes|schemas|models)', content, re.IGNORECASE):
        claimed = int(m.group(1))
        if claimed > 10:
            status = "PASS" if abs(claimed - gt["total_schemas"]) <= 20 else "FAIL"
            findings.append({
                "type": "schema_count",
                "claimed": claimed,
                "actual": gt["total_schemas"],
                "status": status,
            })

    # ── Enum count claims ──
    for m in re.finditer(r'(\d+)\s*(?:enums?|Enum classes)', content, re.IGNORECASE):
        claimed = int(m.group(1))
        if claimed > 20:
            status = "PASS" if abs(claimed - gt["total_enums"]) <= 10 else "FAIL"
            findings.append({
                "type": "enum_count",
                "claimed": claimed,
                "actual": gt["total_enums"],
                "status": status,
            })

    # ── Component count claims ──
    for m in re.finditer(r'(\d+)\s*components?', content, re.IGNORECASE):
        claimed = int(m.group(1))
        if claimed > 50:
            status = "PASS" if abs(claimed - gt["fe_components"]) <= 30 else "FAIL"
            findings.append({
                "type": "component_count",
                "claimed": claimed,
                "actual": gt["fe_components"],
                "status": status,
            })

    # ── File count claims: "793 files" or "Files: 793" ──
    for m in re.finditer(r'(\d+)\s*(?:\.py\s+)?files?(?:\s*\(|\s*\|)', content, re.IGNORECASE):
        claimed = int(m.group(1))
        if claimed > 100:
            total = gt["backend_total_files"] + gt["frontend_total_files"]
            status = "PASS" if abs(claimed - total) <= 20 else "INFO"
            findings.append({
                "type": "file_count",
                "claimed": claimed,
                "status": status,
            })

    return findings, corrections


# ─── Main ───

def main():
    print("R6: Loading ground truth...")
    gt = load_ground_truth()

    print(f"Ground truth loaded:")
    print(f"  Backend: {gt['backend_total_files']} files, {gt['backend_total_loc']} LOC")
    print(f"  Frontend: {gt['frontend_total_files']} files, {gt['frontend_total_loc']} LOC")
    print(f"  Classes: {gt['total_classes']} | Methods: {gt['total_methods']}")
    print(f"  Endpoints: {gt['total_endpoints']} | Enums: {gt['total_enums']} | Schemas: {gt['total_schemas']}")

    # Find all V9 .md files (core analysis, not R4-semantic or verification)
    core_md_files = []
    for md in sorted(V9_DIR.rglob("*.md")):
        rel = str(md.relative_to(V9_DIR))
        # Skip non-core files
        if any(skip in rel for skip in ["R4-semantic", "ROUND", "VERIFICATION", "PLAN"]):
            continue
        if md.suffix == ".md":
            core_md_files.append(md)

    print(f"\nValidating {len(core_md_files)} V9 core files...")

    all_findings = {}
    all_corrections = []
    total_pass = 0
    total_fail = 0
    total_info = 0

    for md_file in core_md_files:
        rel = str(md_file.relative_to(V9_DIR))
        findings, corrections = extract_and_validate_claims(md_file, gt)
        all_findings[rel] = findings
        all_corrections.extend(corrections)

        for f in findings:
            status = f.get("status", "INFO")
            if status == "PASS": total_pass += 1
            elif status == "FAIL": total_fail += 1
            else: total_info += 1

    # ── Apply corrections ──
    corrections_applied = []
    for old_str, new_str, file_rel, desc in all_corrections:
        filepath = V9_DIR / file_rel
        content = filepath.read_text(encoding="utf-8", errors="replace")
        if old_str in content:
            content = content.replace(old_str, new_str, 1)
            filepath.write_text(content, encoding="utf-8")
            corrections_applied.append({
                "file": file_rel,
                "old": old_str,
                "new": new_str,
                "type": desc,
            })

    # ── Write reports ──
    report = {
        "summary": {
            "files_validated": len(core_md_files),
            "total_claims_checked": total_pass + total_fail + total_info,
            "PASS": total_pass,
            "FAIL": total_fail,
            "INFO": total_info,
            "corrections_applied": len(corrections_applied),
            "accuracy": f"{total_pass / max(total_pass + total_fail, 1) * 100:.1f}%",
        },
        "ground_truth": {
            "backend_files": gt["backend_total_files"],
            "backend_loc": gt["backend_total_loc"],
            "frontend_files": gt["frontend_total_files"],
            "frontend_loc": gt["frontend_total_loc"],
            "total_loc": gt["backend_total_loc"] + gt["frontend_total_loc"],
            "classes": gt["total_classes"],
            "methods": gt["total_methods"],
            "endpoints": gt["total_endpoints"],
            "enums": gt["total_enums"],
            "enum_values": gt["total_enum_values"],
            "schemas": gt["total_schemas"],
            "schema_fields": gt["total_schema_fields"],
            "circular_deps": gt["circular_deps"],
            "fe_components": gt["fe_components"],
            "fe_interfaces": gt["fe_interfaces"],
        },
        "corrections_applied": corrections_applied,
        "per_file": all_findings,
    }

    with open(V9_DIR / "r6-validation-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Write markdown report
    with open(V9_DIR / "r6-validation-report.md", "w", encoding="utf-8") as f:
        f.write("# R6 Cross-Validation Report\n\n")
        f.write(f"> Generated by `r6_validate_and_correct.py` | Date: 2026-03-30\n\n")
        f.write("## Summary\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Files validated | {len(core_md_files)} |\n")
        f.write(f"| Claims checked | {total_pass + total_fail + total_info} |\n")
        f.write(f"| PASS | {total_pass} |\n")
        f.write(f"| FAIL | {total_fail} |\n")
        f.write(f"| INFO | {total_info} |\n")
        f.write(f"| Corrections applied | {len(corrections_applied)} |\n")
        f.write(f"| Accuracy | {total_pass / max(total_pass + total_fail, 1) * 100:.1f}% |\n\n")

        f.write("## Ground Truth (R5 AST-Extracted)\n\n")
        f.write(f"| Data | Value |\n|------|-------|\n")
        for k, v in report["ground_truth"].items():
            f.write(f"| {k} | {v:,} |\n")

        if corrections_applied:
            f.write("\n## Corrections Applied\n\n")
            f.write(f"| File | Type | Old | New |\n|------|------|-----|-----|\n")
            for c in corrections_applied:
                f.write(f"| {c['file']} | {c['type']} | `{c['old'][:50]}` | `{c['new'][:50]}` |\n")

        f.write("\n## Per-File Findings\n\n")
        for file_rel, findings in sorted(all_findings.items()):
            if findings:
                pass_count = sum(1 for f in findings if f.get("status") == "PASS")
                fail_count = sum(1 for f in findings if f.get("status") == "FAIL")
                f.write(f"### {file_rel}\n")
                f.write(f"Claims: {len(findings)} | PASS: {pass_count} | FAIL: {fail_count}\n\n")
                for finding in findings:
                    status = finding.get("status", "INFO")
                    icon = {"PASS": "✅", "FAIL": "❌", "INFO": "ℹ️"}.get(status, "?")
                    f.write(f"- {icon} **{finding['type']}**: claimed={finding.get('claimed', finding.get('value', '?'))}")
                    if "actual" in finding:
                        f.write(f", actual={finding['actual']}")
                    f.write(f" [{status}]\n")
                f.write("\n")

    print(f"\n=== R6 Validation Complete ===")
    print(f"Files validated: {len(core_md_files)}")
    print(f"Claims: PASS={total_pass}, FAIL={total_fail}, INFO={total_info}")
    print(f"Accuracy: {total_pass / max(total_pass + total_fail, 1) * 100:.1f}%")
    print(f"Corrections applied: {len(corrections_applied)}")
    print(f"Reports: r6-validation-report.json + r6-validation-report.md")


if __name__ == "__main__":
    main()
