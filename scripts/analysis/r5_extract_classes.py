"""R5-A1: Extract EVERY class with ALL methods, properties, bases, decorators."""
import ast, json, sys
from pathlib import Path

def extract_classes(filepath):
    classes = []
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                properties = []
                class_vars = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [a.arg for a in item.args.args if a.arg != "self"]
                        ret = ast.unparse(item.returns) if item.returns else None
                        decs = [ast.unparse(d) for d in item.decorator_list]
                        is_property = any("property" in d for d in decs)
                        body_lines = item.end_lineno - item.lineno + 1 if hasattr(item, 'end_lineno') else 0
                        entry = {
                            "name": item.name,
                            "args": args,
                            "return_type": ret,
                            "decorators": decs,
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                            "line": item.lineno,
                            "loc": body_lines,
                            "docstring": ast.get_docstring(item) is not None,
                        }
                        if is_property:
                            properties.append(entry)
                        else:
                            methods.append(entry)
                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                try:
                                    class_vars.append({"name": target.id, "value": ast.unparse(item.value)[:100], "line": item.lineno})
                                except: pass
                    elif isinstance(item, ast.AnnAssign) and item.target:
                        if isinstance(item.target, ast.Name):
                            ann = ast.unparse(item.annotation) if item.annotation else "?"
                            val = ast.unparse(item.value)[:100] if item.value else None
                            class_vars.append({"name": item.target.id, "type": ann, "default": val, "line": item.lineno})

                bases = [ast.unparse(b) for b in node.bases]
                decs = [ast.unparse(d) for d in node.decorator_list]
                classes.append({
                    "name": node.name,
                    "bases": bases,
                    "decorators": decs,
                    "methods": methods,
                    "properties": properties,
                    "class_vars": class_vars,
                    "line": node.lineno,
                    "end_line": getattr(node, 'end_lineno', None),
                    "docstring": (ast.get_docstring(node) or "")[:300],
                    "method_count": len(methods),
                    "property_count": len(properties),
                })
    except Exception as e:
        return [], str(e)
    return classes, None

if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent / "backend" / "src"
    results = {}
    total_classes = 0
    total_methods = 0
    errors = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in str(py): continue
        rel = str(py.relative_to(root.parent.parent)).replace("\\", "/")
        cls, err = extract_classes(str(py))
        if err: errors.append({"file": rel, "error": err})
        if cls:
            results[rel] = cls
            total_classes += len(cls)
            total_methods += sum(c["method_count"] for c in cls)

    output = Path(__file__).parent.parent.parent / "docs/07-analysis/V9/r5-classes.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"summary": {"total_classes": total_classes, "total_methods": total_methods, "files_with_classes": len(results), "parse_errors": len(errors)}, "errors": errors, "files": results}, f, indent=2, ensure_ascii=False)
    print(f"Classes: {total_classes} | Methods: {total_methods} | Files: {len(results)} | Errors: {len(errors)}")
    print(f"Output: {output}")
