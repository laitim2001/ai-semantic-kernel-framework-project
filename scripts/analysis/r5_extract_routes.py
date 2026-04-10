"""R5-A2: Extract EVERY API route with full parameters."""
import ast, json, re, sys
from pathlib import Path

def extract_routes(filepath):
    routes = []
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    dec_str = ast.unparse(dec)
                    # Match @router.get("/path"), @xxx_router.post("/path") etc
                    m = re.match(r'(\w+)\.(get|post|put|delete|patch|websocket)\((["\'])(.*?)\3', dec_str)
                    if m:
                        router_var, method, _, path = m.groups()
                        # Extract all decorator kwargs
                        kwargs = {}
                        if isinstance(dec, ast.Call):
                            for kw in dec.keywords:
                                if kw.arg:
                                    try: kwargs[kw.arg] = ast.unparse(kw.value)[:200]
                                    except: pass
                        # Extract handler args
                        args = []
                        for a in node.args.args:
                            if a.arg in ("self", "cls"): continue
                            ann = ast.unparse(a.annotation) if a.annotation else None
                            args.append({"name": a.arg, "type": ann})
                        ret = ast.unparse(node.returns) if node.returns else None
                        routes.append({
                            "method": method.upper(),
                            "path": path,
                            "handler": node.name,
                            "handler_args": args,
                            "return_type": ret,
                            "router_var": router_var,
                            "response_model": kwargs.get("response_model"),
                            "status_code": kwargs.get("status_code"),
                            "tags": kwargs.get("tags"),
                            "summary": kwargs.get("summary"),
                            "line": node.lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef),
                        })
    except Exception as e:
        return [], str(e)
    return routes, None

if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent / "backend" / "src" / "api" / "v1"
    results = {}
    total = 0
    methods_count = {"GET": 0, "POST": 0, "PUT": 0, "DELETE": 0, "PATCH": 0, "WEBSOCKET": 0}
    errors = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in str(py) or py.name == "__init__.py": continue
        rel = str(py.relative_to(root.parent.parent.parent.parent)).replace("\\", "/")
        rts, err = extract_routes(str(py))
        if err: errors.append({"file": rel, "error": err})
        if rts:
            results[rel] = rts
            total += len(rts)
            for r in rts:
                methods_count[r["method"]] = methods_count.get(r["method"], 0) + 1

    output = Path(__file__).parent.parent.parent / "docs/07-analysis/V9/r5-routes.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"summary": {"total_endpoints": total, "methods": methods_count, "files_with_routes": len(results), "parse_errors": len(errors)}, "errors": errors, "files": results}, f, indent=2, ensure_ascii=False)
    print(f"Endpoints: {total} | Methods: {methods_count} | Files: {len(results)} | Errors: {len(errors)}")
    print(f"Output: {output}")
