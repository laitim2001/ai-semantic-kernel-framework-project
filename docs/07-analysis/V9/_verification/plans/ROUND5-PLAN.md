# V9 Round 5: Automated Precision Verification

> **Problem**: Agent-based reading is limited by context windows. Previous rounds could not truly read every line of every file.
> **Solution**: Write Python scripts that programmatically extract EVERY detail and auto-compare against V9 claims.
> **Guarantee**: Scripts use `ast.parse()` which reads the COMPLETE file. No truncation. No sampling.

---

## Strategy: Extract-Then-Compare

### Phase R5-A: Precision Extraction Scripts (7 scripts)

Each script extracts one category of data from ALL source files:

| Script | Extracts | Output JSON |
|--------|----------|-------------|
| `r5_extract_classes.py` | Every class: name, bases, ALL methods (name, args, decorators, LOC), ALL properties, line numbers | `r5-classes.json` |
| `r5_extract_routes.py` | Every API endpoint: method, path, handler name, handler args, response type, decorators, line number | `r5-routes.json` |
| `r5_extract_enums.py` | Every Enum: name, base, ALL values with assigned strings/ints | `r5-enums.json` |
| `r5_extract_schemas.py` | Every Pydantic BaseModel: name, ALL fields (name, type, default, required) | `r5-schemas.json` |
| `r5_extract_imports.py` | Complete import graph: who imports whom, circular dependency detection | `r5-imports.json` |
| `r5_extract_config.py` | Every env var, Settings field, hardcoded default, magic number | `r5-config.json` |
| `r5_extract_ts.py` | Every TS/TSX: component name, props interface, hooks used, exports, LOC | `r5-frontend.json` |

### Phase R5-B: Auto-Compare Script

One script that reads ALL V9 analysis .md files and compares against R5-A JSON data:

`r5_compare_v9.py`:
1. Parse V9 .md files for claims (class names, endpoint counts, LOC numbers, etc.)
2. Compare each claim against the extracted JSON truth
3. Output: `r5-comparison-report.json` + `r5-comparison-report.md`
   - MATCH: V9 claim matches code
   - MISMATCH: V9 claim differs from code (with both values)
   - MISSING_IN_V9: exists in code but not in V9
   - MISSING_IN_CODE: claimed in V9 but not found in code

### Phase R5-C: V9 Files Update

Based on R5-B comparison, auto-generate correction patches for V9 files.

---

## Execution

R5-A: All 7 scripts run sequentially (each takes ~10-30 seconds)
R5-B: Compare script runs after all extractions
R5-C: Apply corrections + final commit
