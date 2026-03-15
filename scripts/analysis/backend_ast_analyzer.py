"""
IPA Platform Backend Comprehensive AST Analyzer
================================================
Scans EVERY .py file in backend/src/ using Python AST.
Produces precise counts of:
- Functions/methods: implemented vs empty vs stub
- Classes: complete vs partial
- API routes: auth coverage per endpoint
- InMemory storage patterns
- Mock/fake data patterns
- Import analysis
- Code metrics per module

Output: JSON report + human-readable summary
"""

import ast
import os
import sys
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_SRC = BASE_DIR / "backend" / "src"
BACKEND_TESTS = BASE_DIR / "backend" / "tests"

# ============================================================
# AST Analysis Helpers
# ============================================================

def is_empty_body(body: list[ast.stmt]) -> str:
    """Classify function body as: implemented, pass, ellipsis, not_implemented, docstring_only, minimal"""
    if not body:
        return "empty"

    # Filter out docstrings
    stmts = []
    has_docstring = False
    for i, stmt in enumerate(body):
        if i == 0 and isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Constant, ast.Str)):
            has_docstring = True
            continue
        stmts.append(stmt)

    if not stmts:
        return "docstring_only"

    if len(stmts) == 1:
        stmt = stmts[0]
        # pass statement
        if isinstance(stmt, ast.Pass):
            return "pass"
        # Ellipsis (...)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
            return "ellipsis"
        # raise NotImplementedError
        if isinstance(stmt, ast.Raise):
            if stmt.exc:
                if isinstance(stmt.exc, ast.Call):
                    if isinstance(stmt.exc.func, ast.Name) and stmt.exc.func.id == "NotImplementedError":
                        return "not_implemented"
                    if isinstance(stmt.exc.func, ast.Attribute) and stmt.exc.func.attr == "NotImplementedError":
                        return "not_implemented"
                if isinstance(stmt.exc, ast.Name) and stmt.exc.id == "NotImplementedError":
                    return "not_implemented"
        # Single return with simple value (potential stub)
        if isinstance(stmt, ast.Return):
            if stmt.value is None:
                return "return_none"
            if isinstance(stmt.value, ast.Dict) and len(stmt.value.keys) <= 2:
                return "minimal_return"
            if isinstance(stmt.value, ast.Constant):
                return "minimal_return"

    # Check for very short implementations (2-3 lines that are just return + simple)
    if len(stmts) <= 2:
        all_simple = all(
            isinstance(s, (ast.Return, ast.Pass, ast.Expr)) for s in stmts
        )
        if all_simple:
            return "minimal"

    return "implemented"


def get_decorator_names(decorators: list[ast.expr]) -> list[str]:
    """Extract decorator names from decorator list."""
    names = []
    for dec in decorators:
        if isinstance(dec, ast.Name):
            names.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            names.append(f"{ast.dump(dec)}")
            # Try to get simple form
            parts = []
            node = dec
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            parts.reverse()
            names.append(".".join(parts))
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Attribute):
                parts = []
                node = dec.func
                while isinstance(node, ast.Attribute):
                    parts.append(node.attr)
                    node = node.value
                if isinstance(node, ast.Name):
                    parts.append(node.id)
                parts.reverse()
                names.append(".".join(parts))
            elif isinstance(dec.func, ast.Name):
                names.append(dec.func.id)
    return names


def check_auth_in_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
    """Check if a function has auth-related parameters (Depends patterns)."""
    auth_info = {
        "has_auth_depend": False,
        "auth_type": None,
        "has_optional_auth": False,
    }

    # Check function arguments for Depends() with auth
    for arg in node.args.args + node.args.kwonlyargs:
        pass  # defaults checked below

    all_defaults = node.args.defaults + node.args.kw_defaults
    for default in all_defaults:
        if default is None:
            continue
        src = ast.dump(default)
        if "Depends" in src:
            if any(kw in src for kw in ["get_current_user", "auth", "current_user", "verify_token"]):
                auth_info["has_auth_depend"] = True
                if "optional" in src.lower():
                    auth_info["has_optional_auth"] = True
                    auth_info["auth_type"] = "optional"
                else:
                    auth_info["auth_type"] = "required"

    return auth_info


def is_router_endpoint(decorators: list[str]) -> tuple[bool, str]:
    """Check if function is a router endpoint and return HTTP method."""
    http_methods = ["get", "post", "put", "delete", "patch", "options", "head", "websocket"]
    for dec in decorators:
        dec_lower = dec.lower()
        for method in http_methods:
            if f"router.{method}" in dec_lower or f".{method}" in dec_lower:
                return True, method.upper()
    return False, ""


def find_inmemory_patterns(source: str, tree: ast.Module) -> list[dict]:
    """Find in-memory storage patterns in code."""
    patterns = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                target_name = ""
                if isinstance(target, ast.Attribute):
                    target_name = target.attr
                elif isinstance(target, ast.Name):
                    target_name = target.id

                if isinstance(node.value, ast.Dict) and len(node.value.keys) == 0:
                    if any(kw in target_name.lower() for kw in ["store", "cache", "data", "registry", "storage", "memory", "state", "sessions", "agents", "workflows", "items", "records"]):
                        patterns.append({
                            "name": target_name,
                            "line": node.lineno,
                            "type": "empty_dict",
                        })
                elif isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                    if any(kw in target_name.lower() for kw in ["store", "cache", "data", "registry", "storage", "memory", "state", "items", "records", "events", "logs"]):
                        patterns.append({
                            "name": target_name,
                            "line": node.lineno,
                            "type": "empty_list",
                        })

    return patterns


def find_mock_patterns(source: str) -> list[dict]:
    """Find mock/fake/stub data patterns in source code."""
    patterns = []
    lines = source.split("\n")

    keywords = [
        "mock_data", "fake_data", "sample_data", "dummy_data", "test_data",
        "MOCK_", "FAKE_", "SAMPLE_", "DUMMY_",
        "placeholder", "hardcoded",
        "# TODO", "# FIXME", "# HACK", "# STUB",
        "NotImplementedError",
    ]

    for i, line in enumerate(lines, 1):
        line_lower = line.lower().strip()
        for kw in keywords:
            if kw.lower() in line_lower:
                patterns.append({
                    "line": i,
                    "keyword": kw,
                    "content": line.strip()[:120],
                })
                break

    return patterns


# ============================================================
# Main Analysis
# ============================================================

def analyze_file(filepath: Path) -> dict:
    """Analyze a single Python file comprehensively."""
    result = {
        "path": str(filepath.relative_to(BASE_DIR)),
        "lines": 0,
        "blank_lines": 0,
        "comment_lines": 0,
        "code_lines": 0,
        "classes": [],
        "functions": [],
        "endpoints": [],
        "imports": [],
        "inmemory_patterns": [],
        "mock_patterns": [],
        "errors": [],
    }

    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result["errors"].append(f"Read error: {e}")
        return result

    lines = source.split("\n")
    result["lines"] = len(lines)
    result["blank_lines"] = sum(1 for l in lines if not l.strip())
    result["comment_lines"] = sum(1 for l in lines if l.strip().startswith("#"))
    result["code_lines"] = result["lines"] - result["blank_lines"] - result["comment_lines"]

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        result["errors"].append(f"Syntax error: {e}")
        return result

    # Analyze imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                result["imports"].append(f"{module}.{alias.name}")

    # Analyze top-level and class functions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "line": node.lineno,
                "methods": [],
                "total_methods": 0,
                "empty_methods": 0,
                "implemented_methods": 0,
                "bases": [ast.dump(b) for b in node.bases],
            }

            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body_status = is_empty_body(item.body)
                    decorators = get_decorator_names(item.decorator_list)

                    method_info = {
                        "name": item.name,
                        "line": item.lineno,
                        "status": body_status,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                        "decorators": decorators,
                        "arg_count": len(item.args.args),
                    }

                    class_info["methods"].append(method_info)
                    class_info["total_methods"] += 1

                    if body_status in ("pass", "ellipsis", "not_implemented", "docstring_only", "empty"):
                        class_info["empty_methods"] += 1
                    else:
                        class_info["implemented_methods"] += 1

            result["classes"].append(class_info)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body_status = is_empty_body(node.body)
            decorators = get_decorator_names(node.decorator_list)
            is_endpoint, http_method = is_router_endpoint(decorators)
            auth_info = check_auth_in_function(node)

            func_info = {
                "name": node.name,
                "line": node.lineno,
                "status": body_status,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "decorators": decorators,
                "arg_count": len(node.args.args),
                "is_endpoint": is_endpoint,
                "http_method": http_method,
                "auth": auth_info,
            }

            result["functions"].append(func_info)

            if is_endpoint:
                result["endpoints"].append({
                    "name": node.name,
                    "method": http_method,
                    "line": node.lineno,
                    "status": body_status,
                    "auth": auth_info,
                })

    # Find InMemory patterns
    result["inmemory_patterns"] = find_inmemory_patterns(source, tree)

    # Find mock patterns
    result["mock_patterns"] = find_mock_patterns(source)

    return result


def analyze_tests(test_dir: Path) -> dict:
    """Analyze test directory structure and coverage."""
    result = {
        "total_test_files": 0,
        "total_test_functions": 0,
        "test_files_by_dir": defaultdict(int),
        "test_functions_by_dir": defaultdict(int),
        "empty_test_files": [],
        "skip_patterns": [],
        "fixture_count": 0,
    }

    if not test_dir.exists():
        return result

    for py_file in test_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        rel_dir = str(py_file.parent.relative_to(test_dir))
        result["total_test_files"] += 1
        result["test_files_by_dir"][rel_dir] += 1

        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)

            test_count = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_"):
                        test_count += 1
                        result["total_test_functions"] += 1

                    # Check for fixtures
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Attribute) and dec.attr == "fixture":
                            result["fixture_count"] += 1
                        elif isinstance(dec, ast.Name) and dec.id == "fixture":
                            result["fixture_count"] += 1

            result["test_functions_by_dir"][rel_dir] += test_count

            if test_count == 0 and py_file.name.startswith("test_"):
                result["empty_test_files"].append(str(py_file.relative_to(BASE_DIR)))

            # Check for skip patterns
            if "pytest.mark.skip" in source or "@skip" in source:
                result["skip_patterns"].append(str(py_file.relative_to(BASE_DIR)))

        except Exception:
            pass

    # Convert defaultdicts
    result["test_files_by_dir"] = dict(result["test_files_by_dir"])
    result["test_functions_by_dir"] = dict(result["test_functions_by_dir"])

    return result


def main():
    print("=" * 80)
    print("IPA Platform Backend Comprehensive AST Analysis")
    print("=" * 80)
    print(f"Scanning: {BACKEND_SRC}")
    print()

    # Collect all .py files
    all_py_files = sorted(BACKEND_SRC.rglob("*.py"))
    all_py_files = [f for f in all_py_files if "__pycache__" not in str(f)]

    print(f"Total Python files found: {len(all_py_files)}")
    print()

    # Analyze each file
    all_results = []
    errors = []

    for i, filepath in enumerate(all_py_files):
        result = analyze_file(filepath)
        all_results.append(result)
        if result["errors"]:
            errors.extend([(filepath, e) for e in result["errors"]])

    # ============================================================
    # Aggregate Statistics
    # ============================================================

    total_files = len(all_results)
    total_lines = sum(r["lines"] for r in all_results)
    total_code_lines = sum(r["code_lines"] for r in all_results)
    total_blank = sum(r["blank_lines"] for r in all_results)
    total_comment = sum(r["comment_lines"] for r in all_results)

    # Function analysis
    all_functions = []
    all_methods = []
    all_endpoints = []
    all_classes = []
    all_inmemory = []
    all_mock = []

    for r in all_results:
        for f in r["functions"]:
            f["file"] = r["path"]
            all_functions.append(f)
        for c in r["classes"]:
            c["file"] = r["path"]
            all_classes.append(c)
            for m in c["methods"]:
                m["file"] = r["path"]
                m["class"] = c["name"]
                all_methods.append(m)
        for e in r["endpoints"]:
            e["file"] = r["path"]
            all_endpoints.append(e)
        for im in r["inmemory_patterns"]:
            im["file"] = r["path"]
            all_inmemory.append(im)
        for mp in r["mock_patterns"]:
            mp["file"] = r["path"]
            all_mock.append(mp)

    # Function status counts
    func_status = Counter(f["status"] for f in all_functions)
    method_status = Counter(m["status"] for m in all_methods)
    endpoint_status = Counter(e["status"] for e in all_endpoints)

    # Auth analysis
    endpoints_with_auth = sum(1 for e in all_endpoints if e["auth"]["has_auth_depend"])
    endpoints_optional_auth = sum(1 for e in all_endpoints if e["auth"]["has_optional_auth"])
    endpoints_no_auth = sum(1 for e in all_endpoints if not e["auth"]["has_auth_depend"])

    # Module-level analysis
    module_stats = defaultdict(lambda: {
        "files": 0, "lines": 0, "code_lines": 0,
        "functions": 0, "empty_functions": 0, "implemented_functions": 0,
        "classes": 0, "endpoints": 0, "auth_endpoints": 0, "no_auth_endpoints": 0,
    })

    for r in all_results:
        # Get top-level module (e.g., api, domain, integrations, etc.)
        parts = Path(r["path"]).parts
        if len(parts) >= 3:
            module = parts[2]  # backend/src/<module>
        else:
            module = "root"

        # Get sub-module
        if len(parts) >= 4:
            sub_module = f"{parts[2]}/{parts[3]}"
        else:
            sub_module = module

        module_stats[sub_module]["files"] += 1
        module_stats[sub_module]["lines"] += r["lines"]
        module_stats[sub_module]["code_lines"] += r["code_lines"]

        for f in r["functions"]:
            module_stats[sub_module]["functions"] += 1
            if f["status"] in ("pass", "ellipsis", "not_implemented", "docstring_only", "empty"):
                module_stats[sub_module]["empty_functions"] += 1
            else:
                module_stats[sub_module]["implemented_functions"] += 1

        for c in r["classes"]:
            module_stats[sub_module]["classes"] += 1
            module_stats[sub_module]["functions"] += c["total_methods"]
            module_stats[sub_module]["empty_functions"] += c["empty_methods"]
            module_stats[sub_module]["implemented_functions"] += c["implemented_methods"]

        for e in r["endpoints"]:
            module_stats[sub_module]["endpoints"] += 1
            if e["auth"]["has_auth_depend"]:
                module_stats[sub_module]["auth_endpoints"] += 1
            else:
                module_stats[sub_module]["no_auth_endpoints"] += 1

    # Test analysis
    test_results = analyze_tests(BACKEND_TESTS)

    # ============================================================
    # Print Report
    # ============================================================

    print("=" * 80)
    print("1. CODE METRICS")
    print("=" * 80)
    print(f"  Total Python files:     {total_files}")
    print(f"  Total lines:            {total_lines:,}")
    print(f"  Code lines:             {total_code_lines:,}")
    print(f"  Blank lines:            {total_blank:,}")
    print(f"  Comment lines:          {total_comment:,}")
    print(f"  Parse errors:           {len(errors)}")
    print()

    print("=" * 80)
    print("2. FUNCTION/METHOD IMPLEMENTATION STATUS")
    print("=" * 80)

    total_all = len(all_functions) + len(all_methods)
    empty_statuses = {"pass", "ellipsis", "not_implemented", "docstring_only", "empty"}
    total_empty = sum(1 for f in all_functions if f["status"] in empty_statuses) + \
                  sum(1 for m in all_methods if m["status"] in empty_statuses)
    total_impl = total_all - total_empty

    print(f"\n  Total functions + methods: {total_all}")
    print(f"  Implemented:              {total_impl} ({total_impl/total_all*100:.1f}%)")
    print(f"  Empty/Stub:               {total_empty} ({total_empty/total_all*100:.1f}%)")
    print()

    print("  --- Top-level Functions ---")
    print(f"  Total:        {len(all_functions)}")
    for status, count in sorted(func_status.items(), key=lambda x: -x[1]):
        print(f"    {status:25s}: {count:5d} ({count/len(all_functions)*100:.1f}%)")

    print()
    print("  --- Class Methods ---")
    print(f"  Total:        {len(all_methods)}")
    for status, count in sorted(method_status.items(), key=lambda x: -x[1]):
        print(f"    {status:25s}: {count:5d} ({count/len(all_methods)*100:.1f}%)")

    print()
    print("  --- Empty Functions Detail (by file) ---")
    empty_by_file = defaultdict(list)
    for f in all_functions:
        if f["status"] in empty_statuses:
            empty_by_file[f["file"]].append(f"{f['name']}:{f['line']} [{f['status']}]")
    for m in all_methods:
        if m["status"] in empty_statuses:
            empty_by_file[m["file"]].append(f"{m['class']}.{m['name']}:{m['line']} [{m['status']}]")

    for filepath, funcs in sorted(empty_by_file.items(), key=lambda x: -len(x[1])):
        print(f"  {filepath} ({len(funcs)} empty):")
        for fn in funcs[:10]:
            print(f"    - {fn}")
        if len(funcs) > 10:
            print(f"    ... and {len(funcs) - 10} more")

    print()
    print("=" * 80)
    print("3. API ENDPOINT ANALYSIS")
    print("=" * 80)
    print(f"\n  Total endpoints found:   {len(all_endpoints)}")
    print(f"  With required auth:      {endpoints_with_auth} ({endpoints_with_auth/max(len(all_endpoints),1)*100:.1f}%)")
    print(f"  With optional auth:      {endpoints_optional_auth}")
    print(f"  Without any auth:        {endpoints_no_auth} ({endpoints_no_auth/max(len(all_endpoints),1)*100:.1f}%)")
    print()

    print("  --- Endpoint Implementation Status ---")
    for status, count in sorted(endpoint_status.items(), key=lambda x: -x[1]):
        print(f"    {status:25s}: {count:5d}")

    print()
    print("  --- Endpoints WITHOUT Auth (detail) ---")
    no_auth_by_file = defaultdict(list)
    for e in all_endpoints:
        if not e["auth"]["has_auth_depend"]:
            no_auth_by_file[e["file"]].append(f"{e['method']:6s} {e['name']}:{e['line']}")

    for filepath, eps in sorted(no_auth_by_file.items()):
        print(f"  {filepath}:")
        for ep in eps:
            print(f"    - {ep}")

    print()
    print("=" * 80)
    print("4. CLASS ANALYSIS")
    print("=" * 80)
    print(f"\n  Total classes:           {len(all_classes)}")
    print(f"  With all methods impl:   {sum(1 for c in all_classes if c['empty_methods'] == 0 and c['total_methods'] > 0)}")
    print(f"  With some empty methods: {sum(1 for c in all_classes if c['empty_methods'] > 0)}")
    print(f"  With no methods:         {sum(1 for c in all_classes if c['total_methods'] == 0)}")

    # Classes with most empty methods
    print()
    print("  --- Classes with Most Empty Methods ---")
    sorted_classes = sorted(all_classes, key=lambda c: -c["empty_methods"])
    for c in sorted_classes[:20]:
        if c["empty_methods"] == 0:
            break
        pct = c["empty_methods"] / max(c["total_methods"], 1) * 100
        print(f"  {c['file']}::{c['name']} — {c['empty_methods']}/{c['total_methods']} empty ({pct:.0f}%)")

    print()
    print("=" * 80)
    print("5. IN-MEMORY STORAGE PATTERNS")
    print("=" * 80)
    print(f"\n  Total patterns found:    {len(all_inmemory)}")
    for im in all_inmemory:
        print(f"  {im['file']}:{im['line']} — {im['name']} = {im['type']}")

    print()
    print("=" * 80)
    print("6. MOCK/STUB/TODO PATTERNS")
    print("=" * 80)
    print(f"\n  Total patterns found:    {len(all_mock)}")

    mock_by_keyword = defaultdict(list)
    for mp in all_mock:
        mock_by_keyword[mp["keyword"]].append(mp)

    for kw, items in sorted(mock_by_keyword.items(), key=lambda x: -len(x[1])):
        print(f"\n  [{kw}] — {len(items)} occurrences:")
        for item in items[:5]:
            print(f"    {item['file']}:{item['line']} — {item['content'][:100]}")
        if len(items) > 5:
            print(f"    ... and {len(items) - 5} more")

    print()
    print("=" * 80)
    print("7. MODULE-LEVEL BREAKDOWN")
    print("=" * 80)

    print(f"\n  {'Module':<40s} {'Files':>6s} {'LOC':>7s} {'Funcs':>6s} {'Empty':>6s} {'Impl%':>6s} {'EPs':>5s} {'Auth':>5s}")
    print(f"  {'-'*40} {'-'*6} {'-'*7} {'-'*6} {'-'*6} {'-'*6} {'-'*5} {'-'*5}")

    for module, stats in sorted(module_stats.items()):
        total_f = stats["functions"]
        empty_f = stats["empty_functions"]
        impl_pct = ((total_f - empty_f) / max(total_f, 1)) * 100
        print(f"  {module:<40s} {stats['files']:>6d} {stats['code_lines']:>7d} {total_f:>6d} {empty_f:>6d} {impl_pct:>5.1f}% {stats['endpoints']:>5d} {stats['auth_endpoints']:>5d}")

    print()
    print("=" * 80)
    print("8. TEST ANALYSIS")
    print("=" * 80)
    print(f"\n  Total test files:        {test_results['total_test_files']}")
    print(f"  Total test functions:    {test_results['total_test_functions']}")
    print(f"  Fixtures defined:        {test_results['fixture_count']}")
    print(f"  Empty test files:        {len(test_results['empty_test_files'])}")
    print(f"  Files with skip markers: {len(test_results['skip_patterns'])}")

    print()
    print("  --- Test Files by Directory ---")
    for dir_name, count in sorted(test_results["test_files_by_dir"].items(), key=lambda x: -x[1]):
        func_count = test_results["test_functions_by_dir"].get(dir_name, 0)
        print(f"    {dir_name:<50s}: {count:>4d} files, {func_count:>5d} test functions")

    if test_results["empty_test_files"]:
        print()
        print("  --- Empty Test Files ---")
        for f in test_results["empty_test_files"]:
            print(f"    {f}")

    print()
    print("=" * 80)
    print("9. IMPORT ANALYSIS (Auth-related)")
    print("=" * 80)

    auth_imports = defaultdict(int)
    for r in all_results:
        for imp in r["imports"]:
            if any(kw in imp.lower() for kw in ["auth", "security", "jwt", "token", "permission"]):
                auth_imports[imp] += 1

    for imp, count in sorted(auth_imports.items(), key=lambda x: -x[1])[:30]:
        print(f"  {imp:<70s}: {count:>4d} files")

    # ============================================================
    # JSON Export
    # ============================================================

    summary = {
        "scan_date": "2026-03-15",
        "scan_scope": str(BACKEND_SRC),
        "total_files": total_files,
        "total_lines": total_lines,
        "total_code_lines": total_code_lines,
        "total_functions_and_methods": total_all,
        "implemented": total_impl,
        "empty_stub": total_empty,
        "implementation_rate": round(total_impl / max(total_all, 1) * 100, 1),
        "total_endpoints": len(all_endpoints),
        "auth_endpoints": endpoints_with_auth,
        "no_auth_endpoints": endpoints_no_auth,
        "optional_auth_endpoints": endpoints_optional_auth,
        "auth_coverage_rate": round(endpoints_with_auth / max(len(all_endpoints), 1) * 100, 1),
        "total_classes": len(all_classes),
        "inmemory_patterns": len(all_inmemory),
        "mock_patterns": len(all_mock),
        "test_files": test_results["total_test_files"],
        "test_functions": test_results["total_test_functions"],
        "parse_errors": len(errors),
    }

    json_path = BASE_DIR / "scripts" / "analysis" / "backend_analysis_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "module_stats": {k: dict(v) for k, v in module_stats.items()},
            "empty_functions_by_file": {k: v for k, v in empty_by_file.items()},
            "no_auth_endpoints": {k: v for k, v in no_auth_by_file.items()},
            "inmemory_details": all_inmemory,
            "mock_details": all_mock,
            "test_details": {
                "by_dir": test_results["test_files_by_dir"],
                "functions_by_dir": test_results["test_functions_by_dir"],
                "empty_files": test_results["empty_test_files"],
                "skip_files": test_results["skip_patterns"],
            },
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
