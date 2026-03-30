"""R5-A5: Extract ALL Frontend component/interface/hook/store details."""
import json, re, sys
from pathlib import Path

def extract_ts_details(filepath):
    result = {
        "loc": 0,
        "components": [],
        "interfaces": [],
        "types": [],
        "enums": [],
        "hooks_used": [],
        "hooks_defined": [],
        "store_state": [],
        "exports": [],
        "imports_from": [],
        "props_interfaces": {},
    }
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        result["loc"] = len(lines)

        # Components (function or const)
        for m in re.finditer(r'(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)\s*\(([^)]*)\)', content):
            name, params = m.group(1), m.group(2)
            result["components"].append({"name": name, "params": params[:200]})
        for m in re.finditer(r'(?:export\s+)?const\s+([A-Z]\w+)\s*[=:]\s*(?:React\.)?(?:FC|memo|forwardRef)', content):
            result["components"].append({"name": m.group(1), "params": ""})

        # Interfaces with fields
        for m in re.finditer(r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+[\w<>,\s]+)?\s*\{([^}]*)\}', content, re.DOTALL):
            name = m.group(1)
            body = m.group(2)
            fields = []
            for fm in re.finditer(r'(\w+)\??\s*:\s*([^;\n]+)', body):
                fields.append({"name": fm.group(1), "type": fm.group(2).strip()[:100]})
            result["interfaces"].append({"name": name, "fields": fields, "field_count": len(fields)})
            # Check if it's a Props interface
            if "Props" in name:
                result["props_interfaces"][name] = fields

        # Type aliases
        for m in re.finditer(r'(?:export\s+)?type\s+(\w+)\s*=\s*([^;\n]+)', content):
            result["types"].append({"name": m.group(1), "definition": m.group(2).strip()[:200]})

        # Enums
        for m in re.finditer(r'(?:export\s+)?enum\s+(\w+)\s*\{([^}]*)\}', content, re.DOTALL):
            name = m.group(1)
            body = m.group(2)
            values = [v.strip().split("=")[0].strip() for v in body.split(",") if v.strip()]
            result["enums"].append({"name": name, "values": values})

        # Hooks used
        hooks = set()
        for m in re.finditer(r'\buse[A-Z]\w+', content):
            hooks.add(m.group(0))
        result["hooks_used"] = sorted(hooks)

        # Custom hooks defined
        for m in re.finditer(r'(?:export\s+)?(?:function|const)\s+(use[A-Z]\w+)', content):
            result["hooks_defined"].append(m.group(1))

        # Zustand store state (create pattern)
        for m in re.finditer(r'create[<(].*?\)\s*\(\s*\(set(?:,\s*get)?\)\s*=>\s*\(?\{([^}]{0,2000})\}', content, re.DOTALL):
            body = m.group(1)
            state_fields = re.findall(r'(\w+)\s*:', body)
            result["store_state"] = state_fields[:50]

        # Exports
        for m in re.finditer(r'export\s+(?:default\s+)?(?:function|const|class|enum|type|interface)\s+(\w+)', content):
            result["exports"].append(m.group(1))

        # Import sources
        for m in re.finditer(r'from\s+[\'"]([^\'"]+)[\'"]', content):
            result["imports_from"].append(m.group(1))

    except Exception as e:
        result["error"] = str(e)
    return result

if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent / "frontend" / "src"
    results = {}
    total_components = 0
    total_interfaces = 0
    total_types = 0
    total_hooks_defined = 0
    total_props = 0
    for f in sorted(list(root.rglob("*.ts")) + list(root.rglob("*.tsx"))):
        if "node_modules" in str(f) or "__pycache__" in str(f): continue
        rel = str(f.relative_to(root.parent.parent)).replace("\\", "/")
        data = extract_ts_details(str(f))
        results[rel] = data
        total_components += len(data["components"])
        total_interfaces += len(data["interfaces"])
        total_types += len(data["types"])
        total_hooks_defined += len(data["hooks_defined"])
        total_props += len(data["props_interfaces"])

    output = Path(__file__).parent.parent.parent / "docs/07-analysis/V9/r5-frontend.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_files": len(results),
                "total_components": total_components,
                "total_interfaces": total_interfaces,
                "total_types": total_types,
                "total_hooks_defined": total_hooks_defined,
                "total_props_interfaces": total_props,
            },
            "files": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"Files: {len(results)} | Components: {total_components} | Interfaces: {total_interfaces}")
    print(f"Types: {total_types} | Hooks defined: {total_hooks_defined} | Props interfaces: {total_props}")
