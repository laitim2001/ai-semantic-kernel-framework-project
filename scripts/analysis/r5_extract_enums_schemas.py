"""R5-A3: Extract ALL Enum values and ALL Pydantic BaseModel fields."""
import ast, json, sys
from pathlib import Path

def extract_enums_and_schemas(filepath):
    enums = []
    schemas = []
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=filepath)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef): continue
            bases = [ast.unparse(b) for b in node.bases]
            bases_str = " ".join(bases)

            # Enum detection
            if any("Enum" in b for b in bases):
                values = []
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for t in item.targets:
                            if isinstance(t, ast.Name):
                                try: val = ast.unparse(item.value)
                                except: val = "?"
                                values.append({"name": t.id, "value": val})
                enums.append({"name": node.name, "bases": bases, "values": values, "line": node.lineno, "value_count": len(values)})

            # Pydantic BaseModel detection
            if any(b in ("BaseModel", "BaseSettings") or "BaseModel" in b or "BaseSettings" in b for b in bases):
                fields = []
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and item.target and isinstance(item.target, ast.Name):
                        ann = ast.unparse(item.annotation) if item.annotation else "?"
                        default = None
                        required = True
                        if item.value:
                            try:
                                default = ast.unparse(item.value)[:150]
                                if "None" in (default or "") or "=" in (default or "") or "Field(" in (default or ""):
                                    required = False
                            except: pass
                        else:
                            # No default = required (unless Optional)
                            if "Optional" in ann or "None" in ann:
                                required = False
                        fields.append({"name": item.target.id, "type": ann, "default": default, "required": required, "line": item.lineno})
                if fields:
                    schemas.append({"name": node.name, "bases": bases, "fields": fields, "line": node.lineno, "field_count": len(fields)})
    except Exception as e:
        return [], [], str(e)
    return enums, schemas, None

if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent / "backend" / "src"
    all_enums = {}
    all_schemas = {}
    total_enums = 0
    total_enum_values = 0
    total_schemas = 0
    total_fields = 0
    errors = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in str(py): continue
        rel = str(py.relative_to(root.parent.parent)).replace("\\", "/")
        enums, schemas, err = extract_enums_and_schemas(str(py))
        if err: errors.append({"file": rel, "error": err})
        if enums:
            all_enums[rel] = enums
            total_enums += len(enums)
            total_enum_values += sum(e["value_count"] for e in enums)
        if schemas:
            all_schemas[rel] = schemas
            total_schemas += len(schemas)
            total_fields += sum(s["field_count"] for s in schemas)

    out_dir = Path(__file__).parent.parent.parent / "docs/07-analysis/V9"
    with open(out_dir / "r5-enums.json", "w", encoding="utf-8") as f:
        json.dump({"summary": {"total_enums": total_enums, "total_values": total_enum_values, "files": len(all_enums), "errors": len(errors)}, "errors": errors, "files": all_enums}, f, indent=2, ensure_ascii=False)
    with open(out_dir / "r5-schemas.json", "w", encoding="utf-8") as f:
        json.dump({"summary": {"total_schemas": total_schemas, "total_fields": total_fields, "files": len(all_schemas), "errors": len(errors)}, "errors": errors, "files": all_schemas}, f, indent=2, ensure_ascii=False)
    print(f"Enums: {total_enums} ({total_enum_values} values) in {len(all_enums)} files")
    print(f"Schemas: {total_schemas} ({total_fields} fields) in {len(all_schemas)} files")
    print(f"Errors: {len(errors)}")
