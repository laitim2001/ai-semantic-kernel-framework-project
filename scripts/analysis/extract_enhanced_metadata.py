"""
V9 Round 4: Enhanced AST metadata extraction.
Extracts SEMANTIC content beyond structure: docstrings, TODOs, decorators,
enum values, hardcoded configs, error messages, import graph.
Guaranteed 100% file coverage.
"""
import ast
import json
import re
import sys
from pathlib import Path


def extract_comments_and_todos(content: str) -> dict:
    """Extract TODO/FIXME/HACK/STUB/DEPRECATED comments and inline comments."""
    todos = []
    comments = []
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        # TODO/FIXME/HACK/XXX/STUB/DEPRECATED
        for tag in ("TODO", "FIXME", "HACK", "XXX", "STUB", "DEPRECATED", "NOTE", "WARNING"):
            if tag in stripped and ("#" in stripped or stripped.startswith(f"# {tag}") or stripped.startswith(f"// {tag}")):
                todos.append({"line": i, "tag": tag, "text": stripped})
                break
        # Regular comments (skip shebangs and encoding declarations)
        if stripped.startswith("#") and not stripped.startswith("#!") and not "coding" in stripped:
            if len(stripped) > 5:  # Skip trivial comments
                comments.append({"line": i, "text": stripped[:200]})
    return {"todos": todos, "comment_count": len(comments)}


def extract_decorators(tree: ast.AST) -> list:
    """Extract all decorator patterns."""
    decorators = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for dec in node.decorator_list:
                try:
                    dec_str = ast.unparse(dec)
                    decorators.append({
                        "target": node.name,
                        "decorator": dec_str,
                        "line": dec.lineno,
                    })
                except:
                    pass
    return decorators


def extract_enums(tree: ast.AST, content: str) -> list:
    """Extract Enum class definitions with their values."""
    enums = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]
            is_enum = any("Enum" in b for b in bases)
            if is_enum:
                values = []
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                try:
                                    val = ast.unparse(item.value)
                                    values.append({"name": target.id, "value": val})
                                except:
                                    values.append({"name": target.id, "value": "?"})
                enums.append({
                    "name": node.name,
                    "bases": bases,
                    "values": values,
                    "line": node.lineno,
                })
    return enums


def extract_docstrings(tree: ast.AST) -> dict:
    """Extract module, class, and function docstrings."""
    result = {"module": None, "classes": {}, "functions": {}}

    # Module docstring
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, (ast.Constant, ast.Str))):
        val = tree.body[0].value
        result["module"] = val.value if isinstance(val, ast.Constant) else val.s

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            ds = ast.get_docstring(node)
            if ds:
                key = "classes" if isinstance(node, ast.ClassDef) else "functions"
                result[key][node.name] = ds[:500]  # Truncate long docstrings

    return result


def extract_hardcoded_configs(tree: ast.AST) -> list:
    """Extract hardcoded config values: timeouts, limits, default values."""
    configs = []
    patterns = re.compile(
        r"(timeout|max_|min_|limit|ttl|interval|threshold|pool_size|max_retries|"
        r"default_|retry|expire|cache_size|batch_size|chunk_size|buffer_size|"
        r"port|host|workers|concurrency)",
        re.IGNORECASE,
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and patterns.search(target.id):
                    try:
                        val = ast.unparse(node.value)
                        if len(val) < 100:
                            configs.append({
                                "name": target.id,
                                "value": val,
                                "line": node.lineno,
                            })
                    except:
                        pass
        # Also check keyword arguments in function calls (e.g., timeout=30)
        if isinstance(node, ast.keyword):
            if node.arg and patterns.search(node.arg):
                try:
                    val = ast.unparse(node.value)
                    if len(val) < 50 and isinstance(node.value, (ast.Constant, ast.Num)):
                        configs.append({
                            "name": node.arg,
                            "value": val,
                            "line": node.lineno if hasattr(node, 'lineno') else 0,
                        })
                except:
                    pass
    return configs


def extract_imports_detailed(tree: ast.AST) -> dict:
    """Extract detailed import information for dependency graph."""
    internal = []  # from src.xxx import yyy
    external = []  # from fastapi import xxx
    stdlib = []    # from os import xxx

    STDLIB_MODULES = {
        "os", "sys", "re", "json", "typing", "datetime", "pathlib", "abc",
        "asyncio", "collections", "dataclasses", "enum", "functools",
        "hashlib", "io", "logging", "math", "operator", "uuid", "time",
        "contextlib", "inspect", "itertools", "copy", "threading",
        "traceback", "textwrap", "difflib", "unittest", "warnings",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [a.name for a in node.names]
            entry = {"module": node.module, "names": names}
            if node.module.startswith("src.") or node.module.startswith("backend."):
                internal.append(entry)
            elif node.module.split(".")[0] in STDLIB_MODULES:
                stdlib.append(entry)
            else:
                external.append(entry)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                entry = {"module": alias.name, "names": [alias.name]}
                if alias.name.split(".")[0] in STDLIB_MODULES:
                    stdlib.append(entry)
                else:
                    external.append(entry)

    return {"internal": internal, "external": external, "stdlib": stdlib}


def extract_error_patterns(tree: ast.AST) -> list:
    """Extract raise statements and error class definitions."""
    errors = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc:
            try:
                errors.append({
                    "type": "raise",
                    "expr": ast.unparse(node.exc)[:200],
                    "line": node.lineno,
                })
            except:
                pass
        if isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]
            if any("Error" in b or "Exception" in b for b in bases):
                errors.append({
                    "type": "class",
                    "name": node.name,
                    "bases": bases,
                    "line": node.lineno,
                })
    return errors


def extract_enhanced_metadata(filepath: str) -> dict:
    """Extract full enhanced metadata from a Python file."""
    result = {
        "path": filepath,
        "loc": 0,
        "classes": [],
        "functions": [],
        "decorators": [],
        "enums": [],
        "docstrings": {"module": None, "classes": {}, "functions": {}},
        "todos": [],
        "comment_count": 0,
        "hardcoded_configs": [],
        "imports": {"internal": [], "external": [], "stdlib": []},
        "error_patterns": [],
        "parse_error": None,
    }

    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        result["loc"] = len(content.splitlines())

        # Comments/TODOs (regex-based, no AST needed)
        cm = extract_comments_and_todos(content)
        result["todos"] = cm["todos"]
        result["comment_count"] = cm["comment_count"]

        # AST-based extraction
        tree = ast.parse(content, filename=filepath)

        # Classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases]
                methods = [n.name for n in node.body
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                result["classes"].append({
                    "name": node.name, "bases": bases,
                    "methods": methods, "line": node.lineno,
                })

        # Top-level functions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                args = [a.arg for a in node.args.args]
                result["functions"].append({
                    "name": f"{prefix}{node.name}",
                    "args": args, "line": node.lineno,
                })

        result["decorators"] = extract_decorators(tree)
        result["enums"] = extract_enums(tree, content)
        result["docstrings"] = extract_docstrings(tree)
        result["hardcoded_configs"] = extract_hardcoded_configs(tree)
        result["imports"] = extract_imports_detailed(tree)
        result["error_patterns"] = extract_error_patterns(tree)

    except SyntaxError as e:
        result["parse_error"] = f"SyntaxError: {e}"
    except Exception as e:
        result["parse_error"] = f"{type(e).__name__}: {e}"

    return result


def scan_directory(root_dir: str) -> list:
    results = []
    root = Path(root_dir)
    for py_file in sorted(root.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        rel_path = str(py_file.relative_to(root.parent.parent.parent)).replace("\\", "/")
        metadata = extract_enhanced_metadata(str(py_file))
        metadata["path"] = rel_path
        metadata["is_init"] = py_file.name == "__init__.py"
        results.append(metadata)
    return results


def generate_summary(results: list) -> dict:
    total_files = len(results)
    init_files = sum(1 for r in results if r["is_init"])
    code_files = total_files - init_files
    total_loc = sum(r["loc"] for r in results)
    total_classes = sum(len(r["classes"]) for r in results)
    total_functions = sum(len(r["functions"]) for r in results)
    total_enums = sum(len(r["enums"]) for r in results)
    total_todos = sum(len(r["todos"]) for r in results)
    total_configs = sum(len(r["hardcoded_configs"]) for r in results)
    total_errors = sum(len(r["error_patterns"]) for r in results)
    total_decorators = sum(len(r["decorators"]) for r in results)
    parse_errors = sum(1 for r in results if r["parse_error"])

    # Docstring coverage
    files_with_module_doc = sum(1 for r in results if r["docstrings"]["module"])
    classes_with_doc = sum(len(r["docstrings"]["classes"]) for r in results)
    functions_with_doc = sum(len(r["docstrings"]["functions"]) for r in results)

    # TODO breakdown by tag
    todo_tags = {}
    for r in results:
        for t in r["todos"]:
            todo_tags[t["tag"]] = todo_tags.get(t["tag"], 0) + 1

    # Internal imports (dependency graph)
    internal_deps = {}
    for r in results:
        for imp in r["imports"]["internal"]:
            mod = imp["module"]
            if mod not in internal_deps:
                internal_deps[mod] = 0
            internal_deps[mod] += 1

    top_deps = dict(sorted(internal_deps.items(), key=lambda x: -x[1])[:20])

    # Module breakdown
    modules = {}
    for r in results:
        parts = r["path"].split("/")
        if len(parts) >= 4:
            module = parts[2] + "/" + parts[3]
        else:
            module = "root"
        if module not in modules:
            modules[module] = {
                "files": 0, "loc": 0, "classes": 0, "functions": 0,
                "enums": 0, "todos": 0, "configs": 0,
            }
        m = modules[module]
        m["files"] += 1
        m["loc"] += r["loc"]
        m["classes"] += len(r["classes"])
        m["functions"] += len(r["functions"])
        m["enums"] += len(r["enums"])
        m["todos"] += len(r["todos"])
        m["configs"] += len(r["hardcoded_configs"])

    return {
        "total_files": total_files,
        "init_files": init_files,
        "code_files": code_files,
        "total_loc": total_loc,
        "total_classes": total_classes,
        "total_functions": total_functions,
        "total_enums": total_enums,
        "total_todos": total_todos,
        "total_hardcoded_configs": total_configs,
        "total_error_patterns": total_errors,
        "total_decorators": total_decorators,
        "parse_errors": parse_errors,
        "docstring_coverage": {
            "files_with_module_doc": files_with_module_doc,
            "classes_with_doc": classes_with_doc,
            "functions_with_doc": functions_with_doc,
        },
        "todo_tags": todo_tags,
        "top_internal_dependencies": top_deps,
        "modules": dict(sorted(modules.items(), key=lambda x: -x[1]["loc"])),
    }


if __name__ == "__main__":
    backend_src = Path(__file__).parent.parent.parent / "backend" / "src"
    if not backend_src.exists():
        print(f"ERROR: {backend_src} not found")
        sys.exit(1)

    print(f"Enhanced scanning {backend_src}...")
    results = scan_directory(str(backend_src))
    summary = generate_summary(results)

    output_dir = Path(__file__).parent.parent.parent / "docs" / "07-analysis" / "V9"
    metadata_path = output_dir / "enhanced-backend-metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "files": results}, f, indent=2, ensure_ascii=False)

    print(f"\n=== Enhanced Python Scan Complete ===")
    print(f"Total files: {summary['total_files']} ({summary['code_files']} code + {summary['init_files']} __init__)")
    print(f"Total LOC: {summary['total_loc']}")
    print(f"Classes: {summary['total_classes']} | Functions: {summary['total_functions']} | Enums: {summary['total_enums']}")
    print(f"Decorators: {summary['total_decorators']}")
    print(f"TODOs/FIXMEs: {summary['total_todos']} ({summary['todo_tags']})")
    print(f"Hardcoded configs: {summary['total_hardcoded_configs']}")
    print(f"Error patterns: {summary['total_error_patterns']}")
    print(f"Parse errors: {summary['parse_errors']}")
    print(f"Docstring coverage: {summary['docstring_coverage']}")
    print(f"\nTop 10 internal dependencies:")
    for mod, count in list(summary['top_internal_dependencies'].items())[:10]:
        print(f"  {count:4d}x  {mod}")
    print(f"\nOutput: {metadata_path}")
