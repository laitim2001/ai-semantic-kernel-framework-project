"""
V9 Round 3: Programmatic Python AST metadata extraction.
Scans ALL .py files under backend/src/, extracts class names,
function names, imports, LOC — guaranteed 100% file coverage.
"""
import ast
import json
import os
import sys
from pathlib import Path


def extract_metadata(filepath: str) -> dict:
    """Extract metadata from a single Python file using AST."""
    result = {
        "path": filepath,
        "loc": 0,
        "classes": [],
        "functions": [],
        "imports": [],
        "parse_error": None,
    }

    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        result["loc"] = len(content.splitlines())

        tree = ast.parse(content, filename=filepath)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(ast.unparse(base))
                    else:
                        bases.append(ast.unparse(base))

                methods = [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]

                result["classes"].append(
                    {
                        "name": node.name,
                        "bases": bases,
                        "methods": methods,
                        "line": node.lineno,
                    }
                )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods inside classes)
                if isinstance(node, ast.AsyncFunctionDef):
                    prefix = "async "
                else:
                    prefix = ""

                # Check if parent is module (top-level)
                # We track all but mark class methods vs top-level
                parent_is_class = False
                for parent_node in ast.walk(tree):
                    if isinstance(parent_node, ast.ClassDef):
                        for child in parent_node.body:
                            if child is node:
                                parent_is_class = True
                                break

                if not parent_is_class:
                    args = []
                    for arg in node.args.args:
                        args.append(arg.arg)

                    result["functions"].append(
                        {
                            "name": f"{prefix}{node.name}",
                            "args": args,
                            "line": node.lineno,
                        }
                    )

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result["imports"].append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    result["imports"].append(node.module)

    except SyntaxError as e:
        result["parse_error"] = f"SyntaxError: {e}"
    except Exception as e:
        result["parse_error"] = f"{type(e).__name__}: {e}"

    return result


def scan_directory(root_dir: str) -> list:
    """Scan all .py files in directory, excluding __pycache__ and __init__.py."""
    results = []
    root = Path(root_dir)

    for py_file in sorted(root.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue

        rel_path = str(py_file.relative_to(root.parent.parent.parent)).replace(
            "\\", "/"
        )
        metadata = extract_metadata(str(py_file))
        metadata["path"] = rel_path
        metadata["is_init"] = py_file.name == "__init__.py"
        results.append(metadata)

    return results


def generate_summary(results: list) -> dict:
    """Generate summary statistics."""
    total_files = len(results)
    init_files = sum(1 for r in results if r["is_init"])
    code_files = total_files - init_files
    total_loc = sum(r["loc"] for r in results)
    total_classes = sum(len(r["classes"]) for r in results)
    total_functions = sum(len(r["functions"]) for r in results)
    parse_errors = sum(1 for r in results if r["parse_error"])

    # Group by top-level module
    modules = {}
    for r in results:
        parts = r["path"].split("/")
        if len(parts) >= 4:
            module = parts[2] + "/" + parts[3]  # e.g., "integrations/hybrid"
        else:
            module = "root"
        if module not in modules:
            modules[module] = {"files": 0, "loc": 0, "classes": 0, "functions": 0}
        modules[module]["files"] += 1
        modules[module]["loc"] += r["loc"]
        modules[module]["classes"] += len(r["classes"])
        modules[module]["functions"] += len(r["functions"])

    return {
        "total_files": total_files,
        "init_files": init_files,
        "code_files": code_files,
        "total_loc": total_loc,
        "total_classes": total_classes,
        "total_functions": total_functions,
        "parse_errors": parse_errors,
        "modules": dict(sorted(modules.items(), key=lambda x: -x[1]["loc"])),
    }


if __name__ == "__main__":
    backend_src = Path(__file__).parent.parent.parent / "backend" / "src"

    if not backend_src.exists():
        print(f"ERROR: {backend_src} not found")
        sys.exit(1)

    print(f"Scanning {backend_src}...")
    results = scan_directory(str(backend_src))

    summary = generate_summary(results)

    # Write full metadata
    output_dir = Path(__file__).parent.parent.parent / "docs" / "07-analysis" / "V9"
    metadata_path = output_dir / "backend-metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "files": results}, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n=== Python AST Scan Complete ===")
    print(f"Total files: {summary['total_files']}")
    print(f"  __init__.py: {summary['init_files']}")
    print(f"  Code files: {summary['code_files']}")
    print(f"Total LOC: {summary['total_loc']}")
    print(f"Total classes: {summary['total_classes']}")
    print(f"Total functions: {summary['total_functions']}")
    print(f"Parse errors: {summary['parse_errors']}")
    print(f"\nTop modules by LOC:")
    for mod, stats in list(summary["modules"].items())[:15]:
        print(f"  {mod}: {stats['files']} files, {stats['loc']} LOC, {stats['classes']} classes")
    print(f"\nOutput: {metadata_path}")
