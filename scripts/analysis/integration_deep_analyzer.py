"""
IPA Platform Integration Layer Deep Analyzer
=============================================
Scans EVERY file in backend/src/integrations/ to analyze:
- Official API usage (agent_framework imports)
- Real vs mock implementations
- Protocol/ABC definitions vs concrete implementations
- Cross-integration dependencies
- Configuration patterns
- Error handling quality

Output: human-readable summary + JSON report
"""

import ast
import os
import re
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INTEGRATIONS_DIR = BASE_DIR / "backend" / "src" / "integrations"

# ============================================================
# Integration-Specific Analysis
# ============================================================

def analyze_imports(tree: ast.Module) -> dict:
    """Analyze imports for integration patterns."""
    result = {
        "official_framework_imports": [],
        "anthropic_imports": [],
        "azure_imports": [],
        "internal_imports": [],
        "third_party_imports": [],
        "all_imports": [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                result["all_imports"].append(name)
                _classify_import(name, result)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                full_name = f"{module}.{alias.name}"
                result["all_imports"].append(full_name)
                _classify_import(full_name, result)

    return result


def _classify_import(name: str, result: dict):
    """Classify an import into categories."""
    name_lower = name.lower()

    if "agent_framework" in name_lower or "semantic_kernel" in name_lower:
        result["official_framework_imports"].append(name)
    elif "anthropic" in name_lower or "claude" in name_lower:
        result["anthropic_imports"].append(name)
    elif "azure" in name_lower or "openai" in name_lower:
        result["azure_imports"].append(name)
    elif name.startswith("src.") or name.startswith("."):
        result["internal_imports"].append(name)
    elif not name.startswith(("os", "sys", "json", "re", "typing", "datetime",
                               "pathlib", "collections", "abc", "enum", "dataclass",
                               "logging", "asyncio", "uuid", "functools", "copy",
                               "pydantic", "fastapi")):
        result["third_party_imports"].append(name)


def analyze_class_completeness(tree: ast.Module, source: str) -> list[dict]:
    """Deep analysis of class implementation completeness."""
    classes = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        class_info = {
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "bases": [],
            "is_abstract": False,
            "is_protocol": False,
            "is_dataclass": False,
            "decorators": [],
            "total_methods": 0,
            "implemented_methods": 0,
            "empty_methods": 0,
            "abstract_methods": 0,
            "property_methods": 0,
            "init_method": False,
            "has_docstring": False,
            "method_details": [],
            "class_variables": [],
            "instance_variables": [],
        }

        # Bases
        for base in node.bases:
            if isinstance(base, ast.Name):
                class_info["bases"].append(base.id)
                if base.id in ("ABC", "Protocol"):
                    class_info["is_abstract"] = True
                if base.id == "Protocol":
                    class_info["is_protocol"] = True
            elif isinstance(base, ast.Attribute):
                parts = []
                n = base
                while isinstance(n, ast.Attribute):
                    parts.append(n.attr)
                    n = n.value
                if isinstance(n, ast.Name):
                    parts.append(n.id)
                parts.reverse()
                base_name = ".".join(parts)
                class_info["bases"].append(base_name)

        # Decorators
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                class_info["decorators"].append(dec.id)
                if dec.id == "dataclass":
                    class_info["is_dataclass"] = True
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                class_info["decorators"].append(dec.func.id)
                if dec.func.id == "dataclass":
                    class_info["is_dataclass"] = True

        # Check for class docstring
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            class_info["has_docstring"] = True

        # Analyze methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                class_info["total_methods"] += 1

                if item.name == "__init__":
                    class_info["init_method"] = True

                # Check decorators
                is_abstract = False
                is_property = False
                for dec in item.decorator_list:
                    if isinstance(dec, ast.Name):
                        if dec.id == "abstractmethod":
                            is_abstract = True
                        elif dec.id == "property":
                            is_property = True
                    elif isinstance(dec, ast.Attribute):
                        if dec.attr == "abstractmethod":
                            is_abstract = True

                if is_abstract:
                    class_info["abstract_methods"] += 1
                if is_property:
                    class_info["property_methods"] += 1

                # Check implementation
                body = item.body
                has_docstring = False
                stmts = []
                for i, stmt in enumerate(body):
                    if i == 0 and isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        has_docstring = True
                        continue
                    stmts.append(stmt)

                is_empty = False
                if not stmts:
                    is_empty = True
                elif len(stmts) == 1:
                    s = stmts[0]
                    if isinstance(s, ast.Pass):
                        is_empty = True
                    elif isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is ...:
                        is_empty = True
                    elif isinstance(s, ast.Raise) and s.exc:
                        if isinstance(s.exc, ast.Call) and isinstance(s.exc.func, ast.Name) and s.exc.func.id == "NotImplementedError":
                            is_empty = True

                if is_empty and not is_abstract:
                    class_info["empty_methods"] += 1
                elif not is_empty:
                    class_info["implemented_methods"] += 1

                class_info["method_details"].append({
                    "name": item.name,
                    "line": item.lineno,
                    "is_async": isinstance(item, ast.AsyncFunctionDef),
                    "is_abstract": is_abstract,
                    "is_property": is_property,
                    "is_empty": is_empty,
                    "has_docstring": has_docstring,
                    "body_lines": getattr(item, "end_lineno", item.lineno) - item.lineno + 1,
                })

            # Class variables
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info["class_variables"].append(target.id)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                class_info["class_variables"].append(item.target.id)

        # Instance variables from __init__
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                for stmt in ast.walk(item):
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                                class_info["instance_variables"].append(target.attr)
                    elif isinstance(stmt, ast.AnnAssign):
                        if isinstance(stmt.target, ast.Attribute) and isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == "self":
                            class_info["instance_variables"].append(stmt.target.attr)

        classes.append(class_info)

    return classes


def analyze_error_handling(source: str) -> dict:
    """Analyze error handling patterns."""
    return {
        "try_except_count": len(re.findall(r'^\s*try:', source, re.MULTILINE)),
        "bare_except": len(re.findall(r'except\s*:', source, re.MULTILINE)),
        "specific_except": len(re.findall(r'except\s+\w+', source, re.MULTILINE)),
        "raise_count": len(re.findall(r'^\s*raise\b', source, re.MULTILINE)),
        "logging_error": len(re.findall(r'logger\.(error|exception|critical)', source)),
        "logging_warning": len(re.findall(r'logger\.warning', source)),
    }


def analyze_async_patterns(source: str) -> dict:
    """Analyze async/await usage patterns."""
    return {
        "async_def_count": len(re.findall(r'async\s+def\s+', source)),
        "await_count": len(re.findall(r'\bawait\s+', source)),
        "asyncio_usage": len(re.findall(r'asyncio\.', source)),
        "async_with": len(re.findall(r'async\s+with\s+', source)),
        "async_for": len(re.findall(r'async\s+for\s+', source)),
    }


# ============================================================
# Main Analysis
# ============================================================

def analyze_integration_module(module_dir: Path) -> dict:
    """Analyze a complete integration module."""
    module_name = module_dir.name

    result = {
        "name": module_name,
        "path": str(module_dir.relative_to(BASE_DIR)),
        "files": [],
        "total_files": 0,
        "total_lines": 0,
        "total_code_lines": 0,
        "total_classes": 0,
        "total_methods": 0,
        "implemented_methods": 0,
        "empty_methods": 0,
        "abstract_methods": 0,
        "official_imports": [],
        "anthropic_imports": [],
        "azure_imports": [],
        "error_handling": {"try_except_count": 0, "bare_except": 0, "specific_except": 0},
        "async_patterns": {"async_def_count": 0, "await_count": 0},
        "classes": [],
        "implementation_status": "UNKNOWN",
        "evidence": [],
    }

    py_files = sorted(module_dir.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f)]
    result["total_files"] = len(py_files)

    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = source.split("\n")
        code_lines = sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))
        result["total_lines"] += len(lines)
        result["total_code_lines"] += code_lines

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        # Import analysis
        imports = analyze_imports(tree)
        result["official_imports"].extend(imports["official_framework_imports"])
        result["anthropic_imports"].extend(imports["anthropic_imports"])
        result["azure_imports"].extend(imports["azure_imports"])

        # Class analysis
        classes = analyze_class_completeness(tree, source)
        for cls in classes:
            cls["file"] = str(py_file.relative_to(BASE_DIR))
            result["classes"].append(cls)
            result["total_classes"] += 1
            result["total_methods"] += cls["total_methods"]
            result["implemented_methods"] += cls["implemented_methods"]
            result["empty_methods"] += cls["empty_methods"]
            result["abstract_methods"] += cls["abstract_methods"]

        # Error handling
        eh = analyze_error_handling(source)
        for k in result["error_handling"]:
            if k in eh:
                result["error_handling"][k] += eh[k]

        # Async patterns
        ap = analyze_async_patterns(source)
        for k in result["async_patterns"]:
            if k in ap:
                result["async_patterns"][k] += ap[k]

        result["files"].append({
            "path": str(py_file.relative_to(BASE_DIR)),
            "lines": len(lines),
            "code_lines": code_lines,
            "classes": len(classes),
        })

    # Determine status
    if result["total_methods"] == 0:
        result["implementation_status"] = "CONFIG_ONLY"
    elif result["empty_methods"] == 0 and result["implemented_methods"] > 0:
        result["implementation_status"] = "FULLY_IMPLEMENTED"
    elif result["implemented_methods"] == 0:
        result["implementation_status"] = "STUB"
    else:
        impl_rate = result["implemented_methods"] / max(result["total_methods"] - result["abstract_methods"], 1) * 100
        if impl_rate >= 80:
            result["implementation_status"] = "FUNCTIONAL"
        elif impl_rate >= 50:
            result["implementation_status"] = "PARTIAL"
        else:
            result["implementation_status"] = "MINIMAL"
        result["implementation_rate"] = round(impl_rate, 1)

    # Evidence
    if result["official_imports"]:
        result["evidence"].append(f"Uses official Agent Framework API ({len(result['official_imports'])} imports)")
    if result["anthropic_imports"]:
        result["evidence"].append(f"Uses Anthropic/Claude SDK ({len(result['anthropic_imports'])} imports)")
    if result["azure_imports"]:
        result["evidence"].append(f"Uses Azure OpenAI ({len(result['azure_imports'])} imports)")

    return result


def main():
    print("=" * 80)
    print("IPA Platform Integration Layer Deep Analysis")
    print("=" * 80)
    print(f"Scanning: {INTEGRATIONS_DIR}")
    print()

    # Find all integration modules
    modules = sorted([
        d for d in INTEGRATIONS_DIR.iterdir()
        if d.is_dir() and d.name != "__pycache__"
    ])

    print(f"Integration modules found: {len(modules)}")
    print()

    # Analyze each module
    all_results = []
    for module_dir in modules:
        result = analyze_integration_module(module_dir)
        all_results.append(result)

    # ============================================================
    # Print Report
    # ============================================================

    print("=" * 80)
    print("1. INTEGRATION MODULES OVERVIEW")
    print("=" * 80)

    print(f"\n  {'Module':<25s} {'Files':>6s} {'LOC':>7s} {'Classes':>8s} {'Methods':>8s} {'Impl':>6s} {'Empty':>6s} {'Abstr':>6s} {'Status':<20s}")
    print(f"  {'-'*25} {'-'*6} {'-'*7} {'-'*8} {'-'*8} {'-'*6} {'-'*6} {'-'*6} {'-'*20}")

    for r in sorted(all_results, key=lambda x: -x["total_code_lines"]):
        print(f"  {r['name']:<25s} {r['total_files']:>6d} {r['total_code_lines']:>7d} {r['total_classes']:>8d} {r['total_methods']:>8d} {r['implemented_methods']:>6d} {r['empty_methods']:>6d} {r['abstract_methods']:>6d} {r['implementation_status']:<20s}")

    # Totals
    total_files = sum(r["total_files"] for r in all_results)
    total_loc = sum(r["total_code_lines"] for r in all_results)
    total_classes = sum(r["total_classes"] for r in all_results)
    total_methods = sum(r["total_methods"] for r in all_results)
    total_impl = sum(r["implemented_methods"] for r in all_results)
    total_empty = sum(r["empty_methods"] for r in all_results)
    total_abstract = sum(r["abstract_methods"] for r in all_results)

    print(f"  {'TOTAL':<25s} {total_files:>6d} {total_loc:>7d} {total_classes:>8d} {total_methods:>8d} {total_impl:>6d} {total_empty:>6d} {total_abstract:>6d}")

    print()
    print("=" * 80)
    print("2. OFFICIAL API USAGE")
    print("=" * 80)

    for r in all_results:
        if r["official_imports"] or r["anthropic_imports"] or r["azure_imports"]:
            print(f"\n  [{r['name']}]")
            if r["official_imports"]:
                print(f"    Agent Framework: {len(r['official_imports'])} imports")
                for imp in sorted(set(r["official_imports"]))[:10]:
                    print(f"      - {imp}")
            if r["anthropic_imports"]:
                print(f"    Anthropic/Claude: {len(r['anthropic_imports'])} imports")
                for imp in sorted(set(r["anthropic_imports"]))[:10]:
                    print(f"      - {imp}")
            if r["azure_imports"]:
                print(f"    Azure/OpenAI: {len(r['azure_imports'])} imports")
                for imp in sorted(set(r["azure_imports"]))[:10]:
                    print(f"      - {imp}")

    print()
    print("=" * 80)
    print("3. CLASSES WITH EMPTY METHODS (Non-Abstract)")
    print("=" * 80)

    for r in all_results:
        for cls in r["classes"]:
            if cls["empty_methods"] > 0 and not cls["is_abstract"] and not cls["is_protocol"]:
                print(f"\n  {cls['file']}::{cls['name']} — {cls['empty_methods']}/{cls['total_methods']} empty")
                for m in cls["method_details"]:
                    if m["is_empty"] and not m["is_abstract"]:
                        print(f"    - {m['name']}() [line {m['line']}]")

    print()
    print("=" * 80)
    print("4. PROTOCOL/ABC DEFINITIONS (Legitimate Empty Methods)")
    print("=" * 80)

    for r in all_results:
        for cls in r["classes"]:
            if cls["is_abstract"] or cls["is_protocol"]:
                print(f"  {cls['file']}::{cls['name']} — {cls['abstract_methods']} abstract, {cls['total_methods']} total [{'Protocol' if cls['is_protocol'] else 'ABC'}]")

    print()
    print("=" * 80)
    print("5. ERROR HANDLING QUALITY")
    print("=" * 80)

    print(f"\n  {'Module':<25s} {'try/except':>12s} {'bare except':>12s} {'specific':>10s} {'logging':>10s}")
    print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*10} {'-'*10}")

    for r in sorted(all_results, key=lambda x: -x["error_handling"]["try_except_count"]):
        eh = r["error_handling"]
        print(f"  {r['name']:<25s} {eh['try_except_count']:>12d} {eh['bare_except']:>12d} {eh['specific_except']:>10d} {eh.get('logging_error', 0) + eh.get('logging_warning', 0):>10d}")

    print()
    print("=" * 80)
    print("6. ASYNC PATTERNS")
    print("=" * 80)

    print(f"\n  {'Module':<25s} {'async def':>10s} {'await':>8s} {'asyncio':>10s} {'async with':>12s}")
    print(f"  {'-'*25} {'-'*10} {'-'*8} {'-'*10} {'-'*12}")

    for r in sorted(all_results, key=lambda x: -x["async_patterns"]["async_def_count"]):
        ap = r["async_patterns"]
        print(f"  {r['name']:<25s} {ap['async_def_count']:>10d} {ap['await_count']:>8d} {ap['asyncio_usage']:>10d} {ap['async_with']:>12d}")

    print()
    print("=" * 80)
    print("7. IMPLEMENTATION STATUS SUMMARY")
    print("=" * 80)

    status_counts = Counter(r["implementation_status"] for r in all_results)
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        modules_list = [r["name"] for r in all_results if r["implementation_status"] == status]
        print(f"\n  {status}: {count} modules")
        for m in modules_list:
            print(f"    - {m}")

    # ============================================================
    # JSON Export
    # ============================================================

    summary = {
        "scan_date": "2026-03-15",
        "total_modules": len(all_results),
        "total_files": total_files,
        "total_code_lines": total_loc,
        "total_classes": total_classes,
        "total_methods": total_methods,
        "implemented_methods": total_impl,
        "empty_methods": total_empty,
        "abstract_methods": total_abstract,
        "implementation_rate": round(total_impl / max(total_methods - total_abstract, 1) * 100, 1),
        "status_distribution": dict(status_counts),
    }

    json_path = BASE_DIR / "scripts" / "analysis" / "integration_analysis_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "modules": [{
                "name": r["name"],
                "status": r["implementation_status"],
                "files": r["total_files"],
                "code_lines": r["total_code_lines"],
                "classes": r["total_classes"],
                "methods": r["total_methods"],
                "implemented": r["implemented_methods"],
                "empty": r["empty_methods"],
                "abstract": r["abstract_methods"],
                "official_imports": len(r["official_imports"]),
                "anthropic_imports": len(r["anthropic_imports"]),
                "azure_imports": len(r["azure_imports"]),
                "evidence": r["evidence"],
                "class_details": [{
                    "name": c["name"],
                    "file": c["file"],
                    "is_abstract": c["is_abstract"],
                    "is_protocol": c["is_protocol"],
                    "total_methods": c["total_methods"],
                    "implemented": c["implemented_methods"],
                    "empty": c["empty_methods"],
                    "abstract": c["abstract_methods"],
                } for c in r["classes"]],
            } for r in all_results],
        }, f, indent=2, default=str)

    print(f"\n  JSON report saved to: {json_path}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for k, v in summary.items():
        print(f"  {k:<35s}: {v}")


if __name__ == "__main__":
    main()
