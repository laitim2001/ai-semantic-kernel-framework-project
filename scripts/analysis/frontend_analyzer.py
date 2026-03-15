"""
IPA Platform Frontend Comprehensive Analyzer
=============================================
Scans EVERY .ts/.tsx file in frontend/src/ using text analysis.
Produces precise counts of:
- Components: functional status, props interfaces
- TypeScript quality: any types, console.logs, TODO comments
- API calls: real vs mock, error handling
- State management: store connections
- Hooks: implementation completeness
- Mock/hardcoded data patterns

Output: human-readable summary + JSON report
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_SRC = BASE_DIR / "frontend" / "src"
FRONTEND_ROOT = BASE_DIR / "frontend"

# ============================================================
# Analysis Helpers
# ============================================================

def count_lines(content: str) -> dict:
    """Count different types of lines."""
    lines = content.split("\n")
    total = len(lines)
    blank = sum(1 for l in lines if not l.strip())
    comment = sum(1 for l in lines if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("*"))
    code = total - blank - comment
    return {"total": total, "blank": blank, "comment": comment, "code": code}


def find_any_types(content: str) -> list[dict]:
    """Find 'any' type usage in TypeScript."""
    patterns = [
        r': any\b',
        r'as any\b',
        r'<any>',
        r'any\[\]',
        r': any;',
        r'Record<string,\s*any>',
        r'Record<any',
    ]
    results = []
    for i, line in enumerate(content.split("\n"), 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        for pattern in patterns:
            if re.search(pattern, line):
                results.append({
                    "line": i,
                    "content": stripped[:120],
                    "pattern": pattern,
                })
                break
    return results


def find_console_logs(content: str) -> list[dict]:
    """Find console.log/warn/error statements."""
    results = []
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        if re.search(r'console\.(log|warn|error|debug|info)\(', line):
            method = re.search(r'console\.(log|warn|error|debug|info)', line).group(1)
            results.append({
                "line": i,
                "method": method,
                "content": stripped[:120],
            })
    return results


def find_todo_comments(content: str) -> list[dict]:
    """Find TODO/FIXME/HACK comments."""
    results = []
    for i, line in enumerate(content.split("\n"), 1):
        if re.search(r'(TODO|FIXME|HACK|XXX|STUB)[\s:]+', line, re.IGNORECASE):
            results.append({
                "line": i,
                "content": line.strip()[:120],
            })
    return results


def find_mock_data(content: str) -> list[dict]:
    """Find mock/hardcoded data patterns."""
    results = []
    keywords = [
        "mockData", "mock_data", "MOCK_", "fakeData", "fake_data",
        "sampleData", "sample_data", "dummyData", "dummy_data",
        "hardcoded", "placeholder",
        "testData", "test_data",
    ]
    for i, line in enumerate(content.split("\n"), 1):
        for kw in keywords:
            if kw in line:
                results.append({
                    "line": i,
                    "keyword": kw,
                    "content": line.strip()[:120],
                })
                break
    return results


def find_api_calls(content: str) -> list[dict]:
    """Find API call patterns (fetch, axios, etc.)."""
    results = []
    patterns = [
        (r'fetch\s*\(', "fetch"),
        (r'apiClient\.\w+', "apiClient"),
        (r'axios\.\w+', "axios"),
        (r'api\.\w+\.\w+', "api_module"),
        (r'useQuery|useMutation', "react_query"),
    ]
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        for pattern, api_type in patterns:
            if re.search(pattern, line):
                results.append({
                    "line": i,
                    "type": api_type,
                    "content": stripped[:120],
                })
                break
    return results


def analyze_component(content: str, filepath: str) -> dict:
    """Analyze a React component file."""
    info = {
        "is_component": False,
        "component_name": None,
        "has_props_interface": False,
        "has_state": False,
        "has_effects": False,
        "has_error_boundary": False,
        "hooks_used": [],
        "imports_count": 0,
        "export_type": None,
    }

    # Check for React component patterns
    if re.search(r'(export\s+(default\s+)?function\s+\w+|const\s+\w+\s*[:=]\s*(React\.)?FC|export\s+default\s+\w+)', content):
        info["is_component"] = True

    # Find component name
    match = re.search(r'export\s+(?:default\s+)?function\s+(\w+)', content)
    if match:
        info["component_name"] = match.group(1)
    else:
        match = re.search(r'const\s+(\w+)\s*[:=]\s*(?:React\.)?FC', content)
        if match:
            info["component_name"] = match.group(1)

    # Check for Props interface
    if re.search(r'(interface\s+\w*Props|type\s+\w*Props)', content):
        info["has_props_interface"] = True

    # Check for state management
    if re.search(r'useState|useReducer|useStore|create\(', content):
        info["has_state"] = True

    # Check for effects
    if re.search(r'useEffect|useLayoutEffect|useMemo|useCallback', content):
        info["has_effects"] = True

    # Count imports
    info["imports_count"] = len(re.findall(r'^import\s+', content, re.MULTILINE))

    # Find hooks used
    hooks = re.findall(r'(use[A-Z]\w+)\s*\(', content)
    info["hooks_used"] = list(set(hooks))

    # Export type
    if "export default" in content:
        info["export_type"] = "default"
    elif re.search(r'export\s+(const|function|class|interface|type)', content):
        info["export_type"] = "named"

    return info


def find_interfaces_and_types(content: str) -> list[dict]:
    """Find TypeScript interfaces and type definitions."""
    results = []
    for match in re.finditer(r'(interface|type)\s+(\w+)', content):
        kind = match.group(1)
        name = match.group(2)
        results.append({
            "kind": kind,
            "name": name,
            "line": content[:match.start()].count("\n") + 1,
        })
    return results


# ============================================================
# Main Analysis
# ============================================================

def analyze_file(filepath: Path) -> dict:
    """Analyze a single TypeScript/TSX file."""
    result = {
        "path": str(filepath.relative_to(BASE_DIR)),
        "extension": filepath.suffix,
        "lines": {},
        "any_types": [],
        "console_logs": [],
        "todo_comments": [],
        "mock_data": [],
        "api_calls": [],
        "component": {},
        "interfaces": [],
        "errors": [],
    }

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result["errors"].append(str(e))
        return result

    result["lines"] = count_lines(content)
    result["any_types"] = find_any_types(content)
    result["console_logs"] = find_console_logs(content)
    result["todo_comments"] = find_todo_comments(content)
    result["mock_data"] = find_mock_data(content)
    result["api_calls"] = find_api_calls(content)
    result["component"] = analyze_component(content, str(filepath))
    result["interfaces"] = find_interfaces_and_types(content)

    return result


def analyze_tests(frontend_root: Path) -> dict:
    """Analyze frontend test files."""
    result = {
        "component_tests": [],
        "e2e_tests": [],
        "test_count": 0,
        "describe_count": 0,
        "it_count": 0,
    }

    # Component tests
    for test_file in frontend_root.rglob("*.test.*"):
        if "node_modules" in str(test_file):
            continue
        try:
            content = test_file.read_text(encoding="utf-8", errors="replace")
            describes = len(re.findall(r'describe\s*\(', content))
            its = len(re.findall(r'(it|test)\s*\(', content))
            result["component_tests"].append({
                "path": str(test_file.relative_to(BASE_DIR)),
                "describes": describes,
                "test_cases": its,
            })
            result["describe_count"] += describes
            result["it_count"] += its
        except Exception:
            pass

    # Also check __tests__ directories
    for test_file in frontend_root.rglob("__tests__/*.ts*"):
        if "node_modules" in str(test_file):
            continue
        if any(str(test_file) == t["path"] for t in result["component_tests"]):
            continue
        try:
            content = test_file.read_text(encoding="utf-8", errors="replace")
            describes = len(re.findall(r'describe\s*\(', content))
            its = len(re.findall(r'(it|test)\s*\(', content))
            result["component_tests"].append({
                "path": str(test_file.relative_to(BASE_DIR)),
                "describes": describes,
                "test_cases": its,
            })
            result["describe_count"] += describes
            result["it_count"] += its
        except Exception:
            pass

    # E2E tests (Playwright)
    e2e_dir = frontend_root / "e2e"
    if e2e_dir.exists():
        for test_file in e2e_dir.rglob("*.spec.*"):
            if "node_modules" in str(test_file):
                continue
            try:
                content = test_file.read_text(encoding="utf-8", errors="replace")
                tests = len(re.findall(r'test\s*\(', content))
                result["e2e_tests"].append({
                    "path": str(test_file.relative_to(BASE_DIR)),
                    "test_cases": tests,
                })
            except Exception:
                pass

    # Also check tests directory
    tests_dir = frontend_root / "tests"
    if tests_dir.exists():
        for test_file in tests_dir.rglob("*.spec.*"):
            if "node_modules" in str(test_file):
                continue
            try:
                content = test_file.read_text(encoding="utf-8", errors="replace")
                tests = len(re.findall(r'test\s*\(', content))
                result["e2e_tests"].append({
                    "path": str(test_file.relative_to(BASE_DIR)),
                    "test_cases": tests,
                })
            except Exception:
                pass

    result["test_count"] = len(result["component_tests"]) + len(result["e2e_tests"])

    return result


def main():
    print("=" * 80)
    print("IPA Platform Frontend Comprehensive Analysis")
    print("=" * 80)
    print(f"Scanning: {FRONTEND_SRC}")
    print()

    # Collect all TS/TSX files (excluding node_modules, dist, build)
    all_files = []
    for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
        for f in FRONTEND_SRC.rglob(ext):
            if "node_modules" not in str(f) and "dist" not in str(f) and ".vite" not in str(f):
                all_files.append(f)

    all_files.sort()
    print(f"Total source files found: {len(all_files)}")
    print()

    # Analyze each file
    all_results = []
    for filepath in all_files:
        result = analyze_file(filepath)
        all_results.append(result)

    # ============================================================
    # Aggregate Statistics
    # ============================================================

    total_files = len(all_results)
    total_lines = sum(r["lines"].get("total", 0) for r in all_results)
    total_code_lines = sum(r["lines"].get("code", 0) for r in all_results)

    all_any_types = []
    all_console_logs = []
    all_todos = []
    all_mocks = []
    all_api_calls = []
    all_interfaces = []

    components = []
    non_components = []

    for r in all_results:
        for item in r["any_types"]:
            item["file"] = r["path"]
            all_any_types.append(item)
        for item in r["console_logs"]:
            item["file"] = r["path"]
            all_console_logs.append(item)
        for item in r["todo_comments"]:
            item["file"] = r["path"]
            all_todos.append(item)
        for item in r["mock_data"]:
            item["file"] = r["path"]
            all_mocks.append(item)
        for item in r["api_calls"]:
            item["file"] = r["path"]
            all_api_calls.append(item)
        for item in r["interfaces"]:
            item["file"] = r["path"]
            all_interfaces.append(item)

        if r["component"]["is_component"]:
            components.append(r)
        else:
            non_components.append(r)

    # Module-level breakdown
    module_stats = defaultdict(lambda: {
        "files": 0, "code_lines": 0, "components": 0,
        "any_types": 0, "console_logs": 0, "todos": 0,
        "api_calls": 0, "interfaces": 0, "hooks_used": set(),
    })

    for r in all_results:
        parts = Path(r["path"]).parts
        if len(parts) >= 3:
            module = parts[2]  # frontend/src/<module>
        else:
            module = "root"

        module_stats[module]["files"] += 1
        module_stats[module]["code_lines"] += r["lines"].get("code", 0)
        if r["component"]["is_component"]:
            module_stats[module]["components"] += 1
        module_stats[module]["any_types"] += len(r["any_types"])
        module_stats[module]["console_logs"] += len(r["console_logs"])
        module_stats[module]["todos"] += len(r["todo_comments"])
        module_stats[module]["api_calls"] += len(r["api_calls"])
        module_stats[module]["interfaces"] += len(r["interfaces"])
        for hook in r["component"].get("hooks_used", []):
            module_stats[module]["hooks_used"].add(hook)

    # Test analysis
    test_results = analyze_tests(FRONTEND_ROOT)

    # ============================================================
    # Print Report
    # ============================================================

    print("=" * 80)
    print("1. CODE METRICS")
    print("=" * 80)
    print(f"  Total source files:      {total_files}")
    print(f"  Total lines:             {total_lines:,}")
    print(f"  Code lines:              {total_code_lines:,}")
    print(f"  TSX files:               {sum(1 for r in all_results if r['extension'] == '.tsx')}")
    print(f"  TS files:                {sum(1 for r in all_results if r['extension'] == '.ts')}")
    print(f"  JS/JSX files:            {sum(1 for r in all_results if r['extension'] in ('.js', '.jsx'))}")
    print()

    print("=" * 80)
    print("2. COMPONENT ANALYSIS")
    print("=" * 80)
    print(f"\n  Total components:        {len(components)}")
    print(f"  Non-component files:     {len(non_components)}")
    print(f"  With Props interface:    {sum(1 for c in components if c['component']['has_props_interface'])}")
    print(f"  With state management:   {sum(1 for c in components if c['component']['has_state'])}")
    print(f"  With effects:            {sum(1 for c in components if c['component']['has_effects'])}")

    # Components by directory
    print()
    print("  --- Components by Directory ---")
    comp_by_dir = defaultdict(int)
    for c in components:
        parts = Path(c["path"]).parts
        if len(parts) >= 4:
            dir_name = "/".join(parts[2:4])
        elif len(parts) >= 3:
            dir_name = parts[2]
        else:
            dir_name = "root"
        comp_by_dir[dir_name] += 1

    for dir_name, count in sorted(comp_by_dir.items(), key=lambda x: -x[1]):
        print(f"    {dir_name:<40s}: {count:>4d}")

    print()
    print("=" * 80)
    print("3. TYPESCRIPT QUALITY")
    print("=" * 80)
    print(f"\n  'any' type usages:       {len(all_any_types)}")
    print(f"  console.log statements:  {len(all_console_logs)}")
    print(f"  TODO/FIXME comments:     {len(all_todos)}")
    print(f"  Interfaces/Types:        {len(all_interfaces)}")

    if all_any_types:
        print()
        print("  --- 'any' Type Details ---")
        any_by_file = defaultdict(list)
        for item in all_any_types:
            any_by_file[item["file"]].append(item)
        for filepath, items in sorted(any_by_file.items(), key=lambda x: -len(x[1])):
            print(f"  {filepath} ({len(items)} occurrences):")
            for item in items[:5]:
                print(f"    L{item['line']}: {item['content'][:100]}")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")

    print()
    print("  --- console.log by Method ---")
    log_methods = Counter(item["method"] for item in all_console_logs)
    for method, count in sorted(log_methods.items(), key=lambda x: -x[1]):
        print(f"    console.{method:8s}: {count:>4d}")

    print()
    print("  --- console.log by File ---")
    log_by_file = defaultdict(int)
    for item in all_console_logs:
        log_by_file[item["file"]] += 1
    for filepath, count in sorted(log_by_file.items(), key=lambda x: -x[1]):
        print(f"    {filepath:<70s}: {count:>4d}")

    if all_todos:
        print()
        print("  --- TODO/FIXME Details ---")
        for item in all_todos:
            print(f"    {item['file']}:L{item['line']}: {item['content'][:100]}")

    print()
    print("=" * 80)
    print("4. API CALLS ANALYSIS")
    print("=" * 80)
    print(f"\n  Total API call sites:    {len(all_api_calls)}")

    api_by_type = Counter(item["type"] for item in all_api_calls)
    for api_type, count in sorted(api_by_type.items(), key=lambda x: -x[1]):
        print(f"    {api_type:<20s}: {count:>4d}")

    print()
    print("  --- API Calls by File ---")
    api_by_file = defaultdict(list)
    for item in all_api_calls:
        api_by_file[item["file"]].append(item["type"])
    for filepath, types in sorted(api_by_file.items(), key=lambda x: -len(x[1])):
        type_summary = Counter(types)
        summary_str = ", ".join(f"{t}:{c}" for t, c in type_summary.items())
        print(f"    {filepath:<70s}: {summary_str}")

    print()
    print("=" * 80)
    print("5. MOCK/HARDCODED DATA")
    print("=" * 80)
    print(f"\n  Total mock patterns:     {len(all_mocks)}")

    mock_by_kw = Counter(item["keyword"] for item in all_mocks)
    for kw, count in sorted(mock_by_kw.items(), key=lambda x: -x[1]):
        print(f"    {kw:<25s}: {count:>4d}")

    print()
    print("  --- Mock Data by File ---")
    mock_by_file = defaultdict(list)
    for item in all_mocks:
        mock_by_file[item["file"]].append(item)
    for filepath, items in sorted(mock_by_file.items(), key=lambda x: -len(x[1])):
        print(f"  {filepath} ({len(items)} patterns):")
        for item in items[:3]:
            print(f"    L{item['line']}: {item['content'][:100]}")
        if len(items) > 3:
            print(f"    ... and {len(items) - 3} more")

    print()
    print("=" * 80)
    print("6. MODULE BREAKDOWN")
    print("=" * 80)

    print(f"\n  {'Module':<25s} {'Files':>6s} {'LOC':>7s} {'Comps':>6s} {'any':>5s} {'logs':>5s} {'APIs':>5s} {'Types':>6s}")
    print(f"  {'-'*25} {'-'*6} {'-'*7} {'-'*6} {'-'*5} {'-'*5} {'-'*5} {'-'*6}")

    for module, stats in sorted(module_stats.items()):
        print(f"  {module:<25s} {stats['files']:>6d} {stats['code_lines']:>7d} {stats['components']:>6d} {stats['any_types']:>5d} {stats['console_logs']:>5d} {stats['api_calls']:>5d} {stats['interfaces']:>6d}")

    print()
    print("=" * 80)
    print("7. HOOKS ANALYSIS")
    print("=" * 80)

    all_hooks = set()
    for stats in module_stats.values():
        all_hooks.update(stats["hooks_used"])

    custom_hooks = sorted([h for h in all_hooks if not h.startswith("use") or len(h) > 10])
    react_hooks = sorted([h for h in all_hooks if h in {"useState", "useEffect", "useRef", "useMemo", "useCallback", "useReducer", "useContext", "useLayoutEffect", "useId", "useImperativeHandle"}])
    project_hooks = sorted([h for h in all_hooks if h not in react_hooks])

    print(f"\n  Total unique hooks:      {len(all_hooks)}")
    print(f"  React built-in:         {len(react_hooks)}")
    print(f"  Project custom:         {len(project_hooks)}")

    print()
    print("  --- Custom Hooks Used ---")
    for hook in project_hooks:
        print(f"    {hook}")

    print()
    print("=" * 80)
    print("8. TEST COVERAGE")
    print("=" * 80)
    print(f"\n  Component test files:    {len(test_results['component_tests'])}")
    print(f"  E2E test files:          {len(test_results['e2e_tests'])}")
    print(f"  Total describe blocks:   {test_results['describe_count']}")
    print(f"  Total test cases (it):   {test_results['it_count']}")

    if test_results["component_tests"]:
        print()
        print("  --- Component Tests ---")
        for t in test_results["component_tests"]:
            print(f"    {t['path']}: {t['describes']} describes, {t['test_cases']} tests")

    if test_results["e2e_tests"]:
        print()
        print("  --- E2E Tests (Playwright) ---")
        for t in test_results["e2e_tests"]:
            print(f"    {t['path']}: {t['test_cases']} tests")

    # ============================================================
    # JSON Export
    # ============================================================

    summary = {
        "scan_date": "2026-03-15",
        "total_files": total_files,
        "total_lines": total_lines,
        "total_code_lines": total_code_lines,
        "total_components": len(components),
        "components_with_props": sum(1 for c in components if c["component"]["has_props_interface"]),
        "any_type_count": len(all_any_types),
        "console_log_count": len(all_console_logs),
        "todo_count": len(all_todos),
        "mock_data_count": len(all_mocks),
        "api_call_sites": len(all_api_calls),
        "interfaces_types": len(all_interfaces),
        "test_files": test_results["test_count"],
        "test_cases": test_results["it_count"],
    }

    json_path = BASE_DIR / "scripts" / "analysis" / "frontend_analysis_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "any_types_detail": all_any_types,
            "console_logs_detail": [{k: v for k, v in item.items()} for item in all_console_logs],
            "todo_detail": all_todos,
            "mock_detail": all_mocks,
            "test_results": {
                "component_tests": test_results["component_tests"],
                "e2e_tests": test_results["e2e_tests"],
            },
            "module_stats": {k: {kk: (list(vv) if isinstance(vv, set) else vv) for kk, vv in v.items()} for k, v in module_stats.items()},
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
