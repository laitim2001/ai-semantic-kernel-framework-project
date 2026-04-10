#!/usr/bin/env python3
"""R7 Step 2: Extract all claims from V9 analysis markdown files.

Scans docs/07-analysis/V9/**/*.md to extract:
- Numeric claims (X files, X LOC, X endpoints, X tools)
- Class/function name mentions
- Feature status claims (COMPLETE/PARTIAL/STUB)
- Diagram internal numbers
"""

import json
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
V9_DIR = PROJECT_ROOT / "docs" / "07-analysis" / "V9"
OUTPUT_FILE = PROJECT_ROOT / "scripts" / "analysis" / "r7-v9-claims.json"

# Patterns for extracting numeric claims
PATTERNS = {
    "files": re.compile(
        r'(\d[\d,]*)\s*(?:\.py\s+)?(?:files?|Python files?|\.tsx?/\.ts files?|\.ts/\.tsx)',
        re.IGNORECASE
    ),
    "loc": re.compile(
        r'(\d[\d,]*)\s*(?:LOC|lines?\s+of\s+code|lines)',
        re.IGNORECASE
    ),
    "loc_tilde": re.compile(
        r'~(\d[\d,]*)\s*(?:LOC|lines)',
        re.IGNORECASE
    ),
    "endpoints": re.compile(
        r'(\d[\d,]*)\s*endpoints?',
        re.IGNORECASE
    ),
    "tools": re.compile(
        r'(\d[\d,]*)\s*tools?',
        re.IGNORECASE
    ),
    "components": re.compile(
        r'(\d[\d,]*)\s*components?',
        re.IGNORECASE
    ),
    "hooks": re.compile(
        r'(\d[\d,]*)\s*hooks?',
        re.IGNORECASE
    ),
    "pages": re.compile(
        r'(\d[\d,]*)\s*pages?',
        re.IGNORECASE
    ),
    "modules": re.compile(
        r'(\d[\d,]*)\s*(?:modules?|sub-?modules?)',
        re.IGNORECASE
    ),
    "servers": re.compile(
        r'(\d[\d,]*)\s*(?:MCP\s+)?servers?',
        re.IGNORECASE
    ),
}

# Patterns for layer-specific claims
LAYER_CLAIM_PATTERNS = [
    # "Layer N: ... X files, Y LOC"
    re.compile(
        r'Layer\s+(\d+)[^|]*?(\d[\d,]*)\s*files?[^|]*?(\d[\d,]*)\s*LOC',
        re.IGNORECASE
    ),
    # "L0X: ... | X files | Y LOC"
    re.compile(
        r'L(\d+)\D+?(\d[\d,]*)\s*files?\D+?(\d[\d,]*)\s*LOC',
        re.IGNORECASE
    ),
]

# Feature status pattern
FEATURE_STATUS = re.compile(
    r'(?:V9 Status|Status)[:\s]*\*?\*?(COMPLETE|PARTIAL|STUB|SPLIT|EXCEEDED|MOCK)',
    re.IGNORECASE
)

# Class name extraction (from markdown code blocks and tables)
CLASS_NAME = re.compile(
    r'(?:class\s+|`)((?:[A-Z][a-zA-Z0-9]+)+)(?:`|\s*[:(])',
)


def parse_number(s: str) -> int:
    """Parse a number string, removing commas."""
    return int(s.replace(",", ""))


def extract_from_file(filepath: Path) -> dict:
    """Extract all claims from a single markdown file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return {}

    rel_path = str(filepath.relative_to(V9_DIR)).replace("\\", "/")
    result = {
        "file": rel_path,
        "numeric_claims": [],
        "layer_claims": [],
        "feature_statuses": [],
        "class_mentions": [],
    }

    lines = content.split("\n")

    # Extract numeric claims with context
    for i, line in enumerate(lines):
        for claim_type, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                value = parse_number(match.group(1))
                # Skip very small numbers that are likely not file/LOC counts
                if claim_type in ("files", "loc") and value < 2:
                    continue
                result["numeric_claims"].append({
                    "type": claim_type,
                    "value": value,
                    "line": i + 1,
                    "context": line.strip()[:150],
                })

        # Tilde LOC claims
        for match in PATTERNS["loc_tilde"].finditer(line):
            value = parse_number(match.group(1))
            if value >= 100:
                result["numeric_claims"].append({
                    "type": "loc_estimate",
                    "value": value,
                    "line": i + 1,
                    "context": line.strip()[:150],
                })

    # Extract layer-specific claims
    for pattern in LAYER_CLAIM_PATTERNS:
        for match in pattern.finditer(content):
            layer_num = int(match.group(1))
            files = parse_number(match.group(2))
            loc = parse_number(match.group(3))
            result["layer_claims"].append({
                "layer": f"L{layer_num:02d}",
                "files": files,
                "loc": loc,
            })

    # Extract feature statuses
    for match in FEATURE_STATUS.finditer(content):
        status = match.group(1).upper()
        # Get surrounding context
        pos = match.start()
        start = max(0, content.rfind("\n", 0, pos))
        end = content.find("\n", pos)
        context = content[start:end].strip()[:200]
        result["feature_statuses"].append({
            "status": status,
            "context": context,
        })

    # Extract class name mentions (unique)
    seen_classes = set()
    for match in CLASS_NAME.finditer(content):
        name = match.group(1)
        # Filter out common non-class words
        if name in ("None", "True", "False", "This", "The", "For", "Not",
                     "All", "New", "Any", "Use", "See", "Set", "Get",
                     "Add", "Run", "Yes", "Key", "LOC", "LOW", "HIGH",
                     "MEDIUM", "CRITICAL", "COMPLETE", "PARTIAL", "STUB",
                     "STILL", "FIXED", "Phase", "Sprint", "Layer",
                     "Table", "File", "Module", "Status", "Value",
                     "Description", "Purpose", "Evidence", "Changes"):
            continue
        if len(name) < 3:
            continue
        if name not in seen_classes:
            seen_classes.add(name)
            result["class_mentions"].append(name)

    return result


def extract_key_claims(all_results: list) -> dict:
    """Extract the most important claims for cross-validation."""
    key_claims = {
        "stats_file": {},
        "layer_files": {},
        "total_claims": {
            "files_claims": [],
            "loc_claims": [],
            "endpoint_claims": [],
            "tool_claims": [],
        },
    }

    for result in all_results:
        fpath = result["file"]

        # Categorize by file type
        if fpath == "00-stats.md":
            key_claims["stats_file"] = result
        elif fpath.startswith("01-architecture/layer-"):
            layer_match = re.search(r'layer-(\d+)', fpath)
            if layer_match:
                layer_num = int(layer_match.group(1))
                key_claims["layer_files"][f"L{layer_num:02d}"] = result

        # Aggregate important claims
        for claim in result.get("numeric_claims", []):
            if claim["type"] == "files" and claim["value"] >= 10:
                key_claims["total_claims"]["files_claims"].append({
                    "file": fpath,
                    **claim
                })
            elif claim["type"] in ("loc", "loc_estimate") and claim["value"] >= 1000:
                key_claims["total_claims"]["loc_claims"].append({
                    "file": fpath,
                    **claim
                })
            elif claim["type"] == "endpoints":
                key_claims["total_claims"]["endpoint_claims"].append({
                    "file": fpath,
                    **claim
                })
            elif claim["type"] == "tools":
                key_claims["total_claims"]["tool_claims"].append({
                    "file": fpath,
                    **claim
                })

    return key_claims


def main():
    print("=" * 60)
    print("R7 Step 2: Extracting V9 analysis claims")
    print("=" * 60)

    md_files = sorted(V9_DIR.rglob("*.md"))
    # Exclude plan/verification files
    exclude_prefixes = ("ROUND", "VERIFICATION", "ANALYSIS-PLAN", "r5-", "r6-")
    md_files = [
        f for f in md_files
        if not any(f.name.startswith(p) for p in exclude_prefixes)
        and "R4-semantic" not in str(f)
    ]

    print(f"\nScanning {len(md_files)} V9 markdown files...")

    all_results = []
    total_numeric = 0
    total_classes = 0
    total_features = 0

    for fpath in md_files:
        result = extract_from_file(fpath)
        if result:
            all_results.append(result)
            total_numeric += len(result.get("numeric_claims", []))
            total_classes += len(result.get("class_mentions", []))
            total_features += len(result.get("feature_statuses", []))

    print(f"\nResults:")
    print(f"  Files scanned: {len(all_results)}")
    print(f"  Numeric claims: {total_numeric}")
    print(f"  Class mentions: {total_classes}")
    print(f"  Feature statuses: {total_features}")

    # Build key claims summary
    key_claims = extract_key_claims(all_results)

    output = {
        "generated": "r7_extract_v9_claims.py",
        "summary": {
            "files_scanned": len(all_results),
            "total_numeric_claims": total_numeric,
            "total_class_mentions": total_classes,
            "total_feature_statuses": total_features,
        },
        "key_claims": key_claims,
        "per_file": all_results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Output written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
