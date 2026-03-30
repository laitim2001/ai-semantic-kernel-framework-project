"""R5-A4: Extract complete import dependency graph + circular dependency detection."""
import ast, json, sys
from pathlib import Path
from collections import defaultdict

def extract_imports(filepath):
    imports = {"internal": [], "external": [], "all_from_src": []}
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [a.name for a in node.names]
                if node.module.startswith("src."):
                    imports["internal"].append({"module": node.module, "names": names, "line": node.lineno})
                    imports["all_from_src"].append(node.module)
                else:
                    imports["external"].append({"module": node.module, "names": names})
    except:
        pass
    return imports

def detect_cycles(graph):
    """DFS-based cycle detection."""
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                idx = path.index(neighbor)
                cycle = path[idx:] + [neighbor]
                if len(cycle) <= 6:  # Only report short cycles
                    cycles.append(cycle)
        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)
    return cycles

if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent / "backend" / "src"
    file_imports = {}
    # Build module-level dependency graph
    dep_graph = defaultdict(set)
    fan_in = defaultdict(int)
    fan_out = defaultdict(int)

    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in str(py) or py.name == "__init__.py": continue
        rel = str(py.relative_to(root.parent.parent)).replace("\\", "/")
        imps = extract_imports(str(py))
        if imps["internal"]:
            file_imports[rel] = imps

        # Build module graph (e.g., src.integrations.hybrid → src.integrations.ag_ui)
        # Normalize to top-2 level: src.integrations.hybrid
        parts = rel.replace("backend/src/", "src/").replace("/", ".").replace(".py", "")
        src_parts = parts.split(".")
        if len(src_parts) >= 3:
            src_mod = ".".join(src_parts[:3])
        else:
            src_mod = parts

        for dep_mod in imps["all_from_src"]:
            dep_parts = dep_mod.split(".")
            if len(dep_parts) >= 3:
                dep_top = ".".join(dep_parts[:3])
            else:
                dep_top = dep_mod
            if dep_top != src_mod:
                dep_graph[src_mod].add(dep_top)
                fan_in[dep_top] += 1
                fan_out[src_mod] += 1

    # Convert sets to lists for JSON
    dep_graph_json = {k: sorted(v) for k, v in dep_graph.items()}

    # Detect cycles
    cycles = detect_cycles(dep_graph_json)

    # Top fan-in (most depended upon)
    top_fan_in = dict(sorted(fan_in.items(), key=lambda x: -x[1])[:20])
    top_fan_out = dict(sorted(fan_out.items(), key=lambda x: -x[1])[:20])

    output = Path(__file__).parent.parent.parent / "docs/07-analysis/V9/r5-imports.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "files_with_internal_imports": len(file_imports),
                "unique_modules_in_graph": len(dep_graph),
                "total_edges": sum(len(v) for v in dep_graph.values()),
                "circular_dependencies": len(cycles),
                "top_fan_in": top_fan_in,
                "top_fan_out": top_fan_out,
            },
            "cycles": cycles,
            "module_graph": dep_graph_json,
            "file_imports": file_imports,
        }, f, indent=2, ensure_ascii=False)

    print(f"Files with imports: {len(file_imports)}")
    print(f"Module graph: {len(dep_graph)} nodes, {sum(len(v) for v in dep_graph.values())} edges")
    print(f"Circular dependencies: {len(cycles)}")
    print(f"Top fan-in: {list(top_fan_in.items())[:5]}")
    print(f"Top fan-out: {list(top_fan_out.items())[:5]}")
