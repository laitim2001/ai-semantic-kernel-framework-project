#!/usr/bin/env python3
"""R7 Step 1: Extract ground truth from actual codebase.

Scans backend/src/ and frontend/src/ to produce a JSON with:
- Per-directory file counts and LOC
- Per-layer aggregated stats
- Class names per file (Python AST)
- Enum names + values (Python AST)
- FastAPI route counts (regex)
- Frontend component/hook/store counts (regex)
"""

import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
OUTPUT_FILE = PROJECT_ROOT / "scripts" / "analysis" / "r7-codebase-truth.json"

# Layer mapping: directory path -> layer number
LAYER_MAP = {
    "api/v1": "L02",
    "integrations/ag_ui": "L03",
    "integrations/orchestration": "L04",
    "integrations/hybrid": "L05",
    "integrations/agent_framework": "L06",
    "integrations/claude_sdk": "L07",
    "integrations/mcp": "L08",
    "integrations/swarm": "L09-swarm",
    "integrations/llm": "L09-llm",
    "integrations/memory": "L09-memory",
    "integrations/knowledge": "L09-knowledge",
    "integrations/correlation": "L09-correlation",
    "integrations/rootcause": "L09-rootcause",
    "integrations/incident": "L09-incident",
    "integrations/patrol": "L09-patrol",
    "integrations/learning": "L09-learning",
    "integrations/audit": "L09-audit",
    "integrations/a2a": "L09-a2a",
    "integrations/n8n": "L09-n8n",
    "integrations/contracts": "L09-contracts",
    "integrations/shared": "L09-shared",
    "domain": "L10",
    "infrastructure": "L11-infra",
    "core": "L11-core",
    "middleware": "L11-middleware",
}


def count_loc(filepath: Path) -> int:
    """Count total lines in a file (matching wc -l methodology used by V9)."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def extract_python_info(filepath: Path) -> dict:
    """Extract classes, enums, functions from a Python file using AST."""
    result = {"classes": [], "enums": [], "functions": [], "decorators": []}
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
    except Exception:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = [
                getattr(b, "id", getattr(b, "attr", ""))
                for b in node.bases
            ]
            is_enum = any(
                b in ("Enum", "IntEnum", "StrEnum", "str, Enum", "Flag")
                for b in bases
            )
            if is_enum:
                values = []
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                values.append(target.id)
                result["enums"].append({"name": node.name, "values": values})
            else:
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                result["classes"].append({
                    "name": node.name,
                    "bases": bases,
                    "methods": methods,
                })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only top-level functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    dec_name = ""
                    if isinstance(decorator, ast.Attribute):
                        dec_name = getattr(decorator, "attr", "")
                    elif isinstance(decorator, ast.Call):
                        func = decorator.func
                        if isinstance(func, ast.Attribute):
                            dec_name = func.attr
                    if dec_name in ("get", "post", "put", "delete", "patch", "websocket"):
                        result["decorators"].append(dec_name)

    return result


def count_routes(filepath: Path) -> int:
    """Count FastAPI route decorators in a file."""
    count = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        count = len(re.findall(
            r'@(?:router|app|protected_router)\.(get|post|put|delete|patch|websocket)\s*\(',
            content
        ))
    except Exception:
        pass
    return count


def scan_backend():
    """Scan backend/src/ for all Python files."""
    results = {
        "total_files": 0,
        "total_loc": 0,
        "per_directory": {},
        "per_layer": defaultdict(lambda: {"files": 0, "loc": 0, "classes": [], "enums": []}),
        "all_classes": [],
        "all_enums": [],
        "total_routes": 0,
        "route_files": {},
    }

    if not BACKEND_SRC.exists():
        print(f"WARNING: {BACKEND_SRC} does not exist")
        return results

    for root, dirs, files in os.walk(BACKEND_SRC):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        root_path = Path(root)
        rel_dir = root_path.relative_to(BACKEND_SRC)

        py_files = [f for f in files if f.endswith(".py")]
        if not py_files:
            continue

        dir_files = 0
        dir_loc = 0
        dir_classes = []
        dir_enums = []
        dir_routes = 0

        for fname in py_files:
            fpath = root_path / fname
            loc = count_loc(fpath)
            dir_files += 1
            dir_loc += loc

            # Extract Python info
            info = extract_python_info(fpath)
            for cls in info["classes"]:
                cls["file"] = str(rel_dir / fname)
                dir_classes.append(cls)
            for enum in info["enums"]:
                enum["file"] = str(rel_dir / fname)
                dir_enums.append(enum)

            # Count routes
            routes = count_routes(fpath)
            if routes > 0:
                dir_routes += routes
                results["route_files"][str(rel_dir / fname)] = routes

        results["per_directory"][str(rel_dir)] = {
            "files": dir_files,
            "loc": dir_loc,
        }
        results["total_files"] += dir_files
        results["total_loc"] += dir_loc
        results["total_routes"] += dir_routes
        results["all_classes"].extend(dir_classes)
        results["all_enums"].extend(dir_enums)

        # Map to layer
        rel_str = str(rel_dir).replace("\\", "/")
        layer = None
        for prefix, layer_id in LAYER_MAP.items():
            if rel_str == prefix or rel_str.startswith(prefix + "/"):
                layer = layer_id
                break
        if layer:
            results["per_layer"][layer]["files"] += dir_files
            results["per_layer"][layer]["loc"] += dir_loc
            results["per_layer"][layer]["classes"].extend(
                [c["name"] for c in dir_classes]
            )
            results["per_layer"][layer]["enums"].extend(
                [e["name"] for e in dir_enums]
            )

    # Aggregate L09 sub-modules
    l09_total = {"files": 0, "loc": 0, "classes": [], "enums": [], "sub_modules": {}}
    for key, val in list(results["per_layer"].items()):
        if key.startswith("L09-"):
            sub_name = key.replace("L09-", "")
            l09_total["sub_modules"][sub_name] = {"files": val["files"], "loc": val["loc"]}
            l09_total["files"] += val["files"]
            l09_total["loc"] += val["loc"]
            l09_total["classes"].extend(val["classes"])
            l09_total["enums"].extend(val["enums"])
    results["per_layer"]["L09"] = l09_total

    # Aggregate L11
    l11_total = {"files": 0, "loc": 0, "classes": [], "enums": [], "sub_modules": {}}
    for key in ["L11-infra", "L11-core", "L11-middleware"]:
        if key in results["per_layer"]:
            val = results["per_layer"][key]
            sub_name = key.replace("L11-", "")
            l11_total["sub_modules"][sub_name] = {"files": val["files"], "loc": val["loc"]}
            l11_total["files"] += val["files"]
            l11_total["loc"] += val["loc"]
            l11_total["classes"].extend(val["classes"])
            l11_total["enums"].extend(val["enums"])
    results["per_layer"]["L11"] = l11_total

    # Convert defaultdict
    results["per_layer"] = dict(results["per_layer"])

    return results


def scan_frontend():
    """Scan frontend/src/ for TypeScript/React files."""
    results = {
        "total_files": 0,
        "total_loc": 0,
        "per_directory": {},
        "components": [],
        "hooks": [],
        "stores": [],
        "pages": [],
    }

    if not FRONTEND_SRC.exists():
        print(f"WARNING: {FRONTEND_SRC} does not exist")
        return results

    ts_extensions = {".ts", ".tsx", ".js", ".jsx"}

    for root, dirs, files in os.walk(FRONTEND_SRC):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".next", "dist")]
        root_path = Path(root)
        rel_dir = root_path.relative_to(FRONTEND_SRC)

        ts_files = [f for f in files if Path(f).suffix in ts_extensions]
        if not ts_files:
            continue

        dir_files = 0
        dir_loc = 0

        for fname in ts_files:
            fpath = root_path / fname
            loc = count_loc(fpath)
            dir_files += 1
            dir_loc += loc

            rel_path = str(rel_dir / fname).replace("\\", "/")

            # Classify
            if "components/" in rel_path and not rel_path.endswith(".test.tsx"):
                results["components"].append(rel_path)
            if "hooks/" in rel_path or fname.startswith("use"):
                results["hooks"].append(rel_path)
            if "store" in rel_path.lower():
                results["stores"].append(rel_path)
            if "pages/" in rel_path:
                results["pages"].append(rel_path)

        results["per_directory"][str(rel_dir)] = {
            "files": dir_files,
            "loc": dir_loc,
        }
        results["total_files"] += dir_files
        results["total_loc"] += dir_loc

    return results


def main():
    print("=" * 60)
    print("R7 Step 1: Extracting codebase ground truth")
    print("=" * 60)

    print("\n[1/2] Scanning backend/src/ ...")
    backend = scan_backend()
    print(f"  Backend: {backend['total_files']} files, {backend['total_loc']} LOC")
    print(f"  Classes: {len(backend['all_classes'])}")
    print(f"  Enums: {len(backend['all_enums'])}")
    print(f"  Routes: {backend['total_routes']}")

    # Print per-layer summary
    print("\n  Per-layer breakdown:")
    for layer_id in sorted(backend["per_layer"].keys()):
        if layer_id.startswith("L09-") or layer_id.startswith("L11-"):
            continue
        info = backend["per_layer"][layer_id]
        files = info["files"]
        loc = info["loc"]
        print(f"    {layer_id}: {files} files, {loc} LOC")

    print("\n[2/2] Scanning frontend/src/ ...")
    frontend = scan_frontend()
    print(f"  Frontend: {frontend['total_files']} files, {frontend['total_loc']} LOC")
    print(f"  Components: {len(frontend['components'])}")
    print(f"  Hooks: {len(frontend['hooks'])}")
    print(f"  Pages: {len(frontend['pages'])}")
    print(f"  Stores: {len(frontend['stores'])}")

    # Build output
    output = {
        "generated": "r7_extract_codebase_truth.py",
        "project_totals": {
            "backend_files": backend["total_files"],
            "backend_loc": backend["total_loc"],
            "frontend_files": frontend["total_files"],
            "frontend_loc": frontend["total_loc"],
            "total_files": backend["total_files"] + frontend["total_files"],
            "total_loc": backend["total_loc"] + frontend["total_loc"],
            "total_classes": len(backend["all_classes"]),
            "total_enums": len(backend["all_enums"]),
            "total_routes": backend["total_routes"],
            "frontend_components": len(frontend["components"]),
            "frontend_hooks": len(frontend["hooks"]),
            "frontend_pages": len(frontend["pages"]),
        },
        "backend_per_layer": {},
        "backend_per_directory": backend["per_directory"],
        "backend_classes": backend["all_classes"],
        "backend_enums": backend["all_enums"],
        "backend_routes": backend["route_files"],
        "frontend_per_directory": frontend["per_directory"],
        "frontend_components": frontend["components"],
        "frontend_hooks": frontend["hooks"],
        "frontend_pages": frontend["pages"],
        "frontend_stores": frontend["stores"],
    }

    # Simplify per_layer for output (remove class/enum lists, keep counts)
    for layer_id, info in backend["per_layer"].items():
        if layer_id.startswith("L09-") or layer_id.startswith("L11-"):
            continue
        entry = {
            "files": info["files"],
            "loc": info["loc"],
            "class_count": len(info.get("classes", [])),
            "enum_count": len(info.get("enums", [])),
        }
        if "sub_modules" in info:
            entry["sub_modules"] = info["sub_modules"]
        output["backend_per_layer"][layer_id] = entry

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Output written to: {OUTPUT_FILE}")
    print(f"   Total: {output['project_totals']['total_files']} files, "
          f"{output['project_totals']['total_loc']} LOC")


if __name__ == "__main__":
    main()
