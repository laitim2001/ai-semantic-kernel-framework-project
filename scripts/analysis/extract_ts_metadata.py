"""
V9 Round 3: Programmatic TypeScript/TSX metadata extraction.
Scans ALL .ts/.tsx files under frontend/src/, extracts exports,
interfaces, types, imports, LOC — guaranteed 100% file coverage.
"""
import json
import re
import sys
from pathlib import Path


def extract_metadata(filepath: str) -> dict:
    """Extract metadata from a single TypeScript file using regex."""
    result = {
        "path": filepath,
        "loc": 0,
        "exports": [],
        "interfaces": [],
        "types": [],
        "enums": [],
        "components": [],
        "hooks_used": [],
        "imports_from": [],
        "parse_error": None,
    }

    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        result["loc"] = len(lines)

        # Extract exported names
        for m in re.finditer(r"export\s+(?:default\s+)?(?:function|const|class|enum|type|interface)\s+(\w+)", content):
            result["exports"].append(m.group(1))

        # Extract default exports like: export default ComponentName
        for m in re.finditer(r"export\s+default\s+(\w+)\s*;", content):
            name = m.group(1)
            if name not in result["exports"]:
                result["exports"].append(name)

        # Extract interfaces
        for m in re.finditer(r"(?:export\s+)?interface\s+(\w+)", content):
            result["interfaces"].append(m.group(1))

        # Extract type aliases
        for m in re.finditer(r"(?:export\s+)?type\s+(\w+)\s*=", content):
            result["types"].append(m.group(1))

        # Extract enums
        for m in re.finditer(r"(?:export\s+)?enum\s+(\w+)", content):
            result["enums"].append(m.group(1))

        # Extract React components (function ComponentName or const ComponentName)
        for m in re.finditer(r"(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)", content):
            name = m.group(1)
            if name not in result["components"]:
                result["components"].append(name)

        for m in re.finditer(r"(?:export\s+)?const\s+([A-Z]\w+)\s*[=:]\s*(?:React\.)?(?:FC|memo|forwardRef|\()", content):
            name = m.group(1)
            if name not in result["components"]:
                result["components"].append(name)

        # Extract hooks used (useState, useEffect, useXxx, etc.)
        hooks = set()
        for m in re.finditer(r"\buse[A-Z]\w+", content):
            hooks.add(m.group(0))
        result["hooks_used"] = sorted(hooks)

        # Extract import sources
        for m in re.finditer(r"from\s+['\"]([^'\"]+)['\"]", content):
            result["imports_from"].append(m.group(1))

    except Exception as e:
        result["parse_error"] = f"{type(e).__name__}: {e}"

    return result


def scan_directory(root_dir: str) -> list:
    """Scan all .ts/.tsx files in directory."""
    results = []
    root = Path(root_dir)

    for ts_file in sorted(root.rglob("*.ts")):
        if "node_modules" in str(ts_file) or "__pycache__" in str(ts_file):
            continue
        rel_path = str(ts_file.relative_to(root.parent.parent)).replace("\\", "/")
        metadata = extract_metadata(str(ts_file))
        metadata["path"] = rel_path
        metadata["is_test"] = ".test." in ts_file.name or ".spec." in ts_file.name or "__tests__" in str(ts_file)
        results.append(metadata)

    for tsx_file in sorted(root.rglob("*.tsx")):
        if "node_modules" in str(tsx_file) or "__pycache__" in str(tsx_file):
            continue
        rel_path = str(tsx_file.relative_to(root.parent.parent)).replace("\\", "/")
        metadata = extract_metadata(str(tsx_file))
        metadata["path"] = rel_path
        metadata["is_test"] = ".test." in tsx_file.name or ".spec." in tsx_file.name or "__tests__" in str(tsx_file)
        results.append(metadata)

    return results


def generate_summary(results: list) -> dict:
    """Generate summary statistics."""
    total_files = len(results)
    test_files = sum(1 for r in results if r["is_test"])
    code_files = total_files - test_files
    total_loc = sum(r["loc"] for r in results)
    total_exports = sum(len(r["exports"]) for r in results)
    total_interfaces = sum(len(r["interfaces"]) for r in results)
    total_types = sum(len(r["types"]) for r in results)
    total_components = sum(len(r["components"]) for r in results)

    # Group by directory
    modules = {}
    for r in results:
        parts = r["path"].split("/")
        if len(parts) >= 3:
            module = parts[1] + "/" + parts[2]  # e.g., "src/components"
        else:
            module = "root"
        if module not in modules:
            modules[module] = {"files": 0, "loc": 0, "exports": 0, "components": 0}
        modules[module]["files"] += 1
        modules[module]["loc"] += r["loc"]
        modules[module]["exports"] += len(r["exports"])
        modules[module]["components"] += len(r["components"])

    return {
        "total_files": total_files,
        "test_files": test_files,
        "code_files": code_files,
        "total_loc": total_loc,
        "total_exports": total_exports,
        "total_interfaces": total_interfaces,
        "total_types": total_types,
        "total_components": total_components,
        "modules": dict(sorted(modules.items(), key=lambda x: -x[1]["loc"])),
    }


if __name__ == "__main__":
    frontend_src = Path(__file__).parent.parent.parent / "frontend" / "src"

    if not frontend_src.exists():
        print(f"ERROR: {frontend_src} not found")
        sys.exit(1)

    print(f"Scanning {frontend_src}...")
    results = scan_directory(str(frontend_src))

    summary = generate_summary(results)

    output_dir = Path(__file__).parent.parent.parent / "docs" / "07-analysis" / "V9"
    metadata_path = output_dir / "frontend-metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "files": results}, f, indent=2, ensure_ascii=False)

    print(f"\n=== TypeScript Scan Complete ===")
    print(f"Total files: {summary['total_files']}")
    print(f"  Test files: {summary['test_files']}")
    print(f"  Code files: {summary['code_files']}")
    print(f"Total LOC: {summary['total_loc']}")
    print(f"Total exports: {summary['total_exports']}")
    print(f"Total interfaces: {summary['total_interfaces']}")
    print(f"Total types: {summary['total_types']}")
    print(f"Total components: {summary['total_components']}")
    print(f"\nTop modules by LOC:")
    for mod, stats in list(summary["modules"].items())[:15]:
        print(f"  {mod}: {stats['files']} files, {stats['loc']} LOC, {stats['components']} components")
    print(f"\nOutput: {metadata_path}")
