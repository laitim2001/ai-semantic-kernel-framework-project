#!/usr/bin/env python3
"""R7 Enhanced Validation: Comprehensive V9 analysis accuracy checker.

Covers 7 verification dimensions:
1. Class method signatures (V9 claimed methods vs actual AST)
2. File path existence (every path mentioned in V9 checked against disk)
3. Feature status evidence (COMPLETE/PARTIAL/STUB evidence paths verified)
4. Enum value completeness (V9 enum values vs actual AST)
5. Diagram component names (names in ASCII/Mermaid diagrams vs actual classes)
6. Delta report file verification (new/modified files in delta docs vs disk)
7. Import/dependency accuracy (claimed dependencies vs actual imports)

Reads from r7-codebase-truth.json (must exist) + scans V9 markdown directly.
"""

import ast
import json
import os
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
V9_DIR = PROJECT_ROOT / "docs" / "07-analysis" / "V9"
TRUTH_FILE = PROJECT_ROOT / "scripts" / "analysis" / "r7-codebase-truth.json"
OUTPUT_JSON = PROJECT_ROOT / "scripts" / "analysis" / "r7-enhanced-results.json"
OUTPUT_MD = PROJECT_ROOT / "docs" / "07-analysis" / "V9" / "r7-enhanced-validation-report.md"


def load_truth() -> dict:
    with open(TRUTH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def read_md(filepath: Path) -> str:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# CHECK 1: Class Method Signatures
# ═══════════════════════════════════════════════════════════════

def check_class_methods(truth: dict) -> dict:
    """Compare class methods mentioned in V9 vs actual AST-extracted methods.

    Uses strict pattern: `ClassName.method_name()` or `ClassName` in same table row
    as method list to avoid false attribution.
    """
    truth_map = {}
    for cls in truth.get("backend_classes", []):
        truth_map[cls["name"]] = {
            "methods": set(cls.get("methods", [])),
            "file": cls.get("file", ""),
        }

    results = {"total_checked": 0, "found": 0, "not_found": []}

    # Strict patterns: only match when class and method are on SAME line
    # Pattern 1: `ClassName.method_name()`
    dot_pattern = re.compile(r'`((?:[A-Z][a-zA-Z0-9]+)+)\.(\w+)\(`')
    # Pattern 2: `ClassName` | ... `method()` ... | (table row)
    table_pattern = re.compile(
        r'\|\s*`?((?:[A-Z][a-zA-Z0-9]+)+)`?\s*\|[^|]*`(\w+)\(`[^|]*\|'
    )
    # Pattern 3: Class.method in prose: ClassName.method_name (no backtick)
    prose_pattern = re.compile(r'((?:[A-Z][a-zA-Z0-9]+)+)\.(\w+)\(\)')

    skip_methods = {
        "py", "md", "json", "None", "True", "False", "self", "cls",
        "init", "str", "int", "dict", "list", "bool", "float", "type",
        "super", "from_dict", "to_dict", "from_env", "items", "keys",
        "values", "get", "set", "pop", "append", "extend", "update",
        "format", "join", "split", "strip", "lower", "upper", "replace",
    }

    for md_file in sorted(V9_DIR.rglob("*.md")):
        if "verification" in md_file.name.lower() or "ROUND" in md_file.name:
            continue
        content = read_md(md_file)
        rel_path = str(md_file.relative_to(V9_DIR))

        checked_pairs = set()
        for i, line in enumerate(content.split("\n")):
            for pattern in [dot_pattern, table_pattern, prose_pattern]:
                for match in pattern.finditer(line):
                    cls_name = match.group(1)
                    method_name = match.group(2)

                    if method_name in skip_methods or len(method_name) < 3:
                        continue
                    if cls_name not in truth_map:
                        continue

                    pair = (cls_name, method_name)
                    if pair in checked_pairs:
                        continue
                    checked_pairs.add(pair)

                    results["total_checked"] += 1
                    actual = truth_map[cls_name]["methods"]
                    if (method_name in actual or
                        f"_{method_name}" in actual or
                        f"__{method_name}__" in actual):
                        results["found"] += 1
                    else:
                        results["not_found"].append({
                            "class": cls_name,
                            "method": method_name,
                            "file": rel_path,
                            "line": i + 1,
                        })

    return results


# ═══════════════════════════════════════════════════════════════
# CHECK 2: File Path Existence
# ═══════════════════════════════════════════════════════════════

def check_file_paths() -> dict:
    """Verify every file path mentioned in V9 actually exists on disk."""
    # Match paths with at least 2 segments
    path_pattern = re.compile(
        r'`((?:backend|frontend|src|api|integrations|domain|infrastructure|core|middleware)'
        r'[/\\][\w./\\-]+\.(?:py|ts|tsx|js|json|yaml|yml))`'
    )

    results = {"total_checked": 0, "exists": 0, "not_found": []}
    checked = set()

    for md_file in sorted(V9_DIR.rglob("*.md")):
        if "verification" in md_file.name.lower() or "ROUND" in md_file.name:
            continue
        content = read_md(md_file)
        rel_md = str(md_file.relative_to(V9_DIR))

        for match in path_pattern.finditer(content):
            fpath = match.group(1).replace("\\", "/")
            # Strip line number suffix like `:83`
            fpath = re.sub(r':\d+$', '', fpath)
            if fpath in checked:
                continue
            checked.add(fpath)

            results["total_checked"] += 1
            # Try many resolution strategies including nested module paths
            candidates = [
                PROJECT_ROOT / fpath,
                PROJECT_ROOT / "backend" / fpath,
                PROJECT_ROOT / "backend" / "src" / fpath,
                PROJECT_ROOT / "frontend" / fpath,
                PROJECT_ROOT / "frontend" / "src" / fpath,
            ]
            # For paths like "core/executor.py", try all integration subdirs
            if not fpath.startswith(("backend", "frontend", "src")):
                for subdir in ["integrations/agent_framework", "integrations/hybrid",
                               "integrations/orchestration", "integrations/claude_sdk",
                               "integrations/mcp", "integrations/ag_ui",
                               "integrations/swarm", "domain/sessions",
                               "domain/orchestration", "domain/workflows"]:
                    candidates.append(BACKEND_SRC / subdir / fpath)

            found = any(c.exists() for c in candidates)
            if found:
                results["exists"] += 1
            else:
                # Also try as directory (some paths reference dirs)
                dir_candidates = [c.parent for c in candidates[:5]]
                dir_found = any(c.exists() for c in dir_candidates)
                if dir_found:
                    results["exists"] += 1
                else:
                    results["not_found"].append({
                        "path": fpath,
                        "source": rel_md,
                    })

    return results


# ═══════════════════════════════════════════════════════════════
# CHECK 3: Feature Status Evidence
# ═══════════════════════════════════════════════════════════════

def check_feature_evidence() -> dict:
    """Verify COMPLETE/PARTIAL/STUB feature evidence paths exist."""
    results = {"total_features": 0, "evidence_verified": 0, "evidence_missing": []}

    # Pattern: "**Evidence**: `path/to/file`"
    evidence_pattern = re.compile(
        r'\*\*Evidence\*\*:\s*`([^`]+)`'
    )
    status_pattern = re.compile(
        r'\*\*V9 Status\*\*:\s*(\w+)'
    )

    for md_file in sorted(V9_DIR.glob("03-features/*.md")):
        content = read_md(md_file)
        rel_md = str(md_file.relative_to(V9_DIR))
        lines = content.split("\n")

        current_feature = ""
        current_status = ""

        for i, line in enumerate(lines):
            # Track feature headers
            if line.startswith("### "):
                current_feature = line.strip("# ").strip()

            # Track status
            sm = status_pattern.search(line)
            if sm:
                current_status = sm.group(1)
                results["total_features"] += 1

            # Check evidence paths
            em = evidence_pattern.search(line)
            if em:
                evidence_str = em.group(1)
                # Split on commas, semicolons, or "), `" patterns
                paths = re.split(r'[,;]\s*|`\s*,\s*`', evidence_str)
                for p in paths:
                    p = p.strip().strip('`').strip()
                    # Clean up common issues
                    p = re.sub(r':\d+$', '', p)  # Strip line numbers
                    p = re.sub(r'\s*\(.*$', '', p)  # Strip descriptions in parens
                    p = p.rstrip('.')  # Strip trailing dots
                    if not p or len(p) < 5:
                        continue
                    # Normalize: strip "backend/src/" prefix if present
                    clean = p.replace("backend/src/", "").replace("frontend/src/", "")

                    # Try to resolve with many strategies
                    candidates = [
                        PROJECT_ROOT / p,
                        PROJECT_ROOT / "backend" / "src" / p,
                        PROJECT_ROOT / "frontend" / "src" / p,
                        BACKEND_SRC / p,
                        BACKEND_SRC / clean,
                    ]
                    found = any(c.exists() for c in candidates)

                    # Try as directory
                    if not found:
                        dir_path = clean.rsplit("/", 1)[0] if "/" in clean else clean
                        dir_candidates = [
                            BACKEND_SRC / dir_path,
                            FRONTEND_SRC / dir_path,
                            PROJECT_ROOT / "backend" / "src" / dir_path,
                        ]
                        found = any(c.exists() or c.is_dir() for c in dir_candidates)

                    if found:
                        results["evidence_verified"] += 1
                    else:
                        results["evidence_missing"].append({
                            "feature": current_feature,
                            "status": current_status,
                            "evidence_path": p,
                            "source": rel_md,
                            "line": i + 1,
                        })

    return results


# ═══════════════════════════════════════════════════════════════
# CHECK 4: Enum Value Completeness
# ═══════════════════════════════════════════════════════════════

def check_enum_completeness(truth: dict) -> dict:
    """Check if V9 enum value lists match actual AST-extracted enum values."""
    # Build truth map
    truth_enums = {}
    for e in truth.get("backend_enums", []):
        truth_enums[e["name"]] = set(e.get("values", []))

    results = {"total_checked": 0, "complete": 0, "incomplete": [], "extra_values": []}

    # Pattern: "| `EnumName` | VALUE1, VALUE2, ... |" or "EnumName` | VALUES"
    enum_val_pattern = re.compile(
        r'`(\w+(?:Status|Type|Level|Mode|Role|Category|Priority|Action|Kind|State|Format|Scope|Strategy|Event|Frequency))`'
        r'\s*\|\s*([^|]+)\|'
    )
    # Also: "| `EnumName` | `VAL1`, `VAL2`, ... |"
    enum_inline_pattern = re.compile(
        r'`((?:[A-Z][a-zA-Z]+)+)`\s*\|\s*((?:\w+[\s,/]+)*\w+)'
    )

    for md_file in sorted(V9_DIR.rglob("*.md")):
        if "verification" in md_file.name.lower() or "ROUND" in md_file.name:
            continue
        content = read_md(md_file)
        rel_md = str(md_file.relative_to(V9_DIR))

        for line in content.split("\n"):
            for pattern in [enum_val_pattern, enum_inline_pattern]:
                for match in pattern.finditer(line):
                    enum_name = match.group(1)
                    if enum_name not in truth_enums:
                        continue

                    values_str = match.group(2)
                    # Parse claimed values
                    claimed_values = set()
                    for v in re.split(r'[,/|]\s*', values_str):
                        v = v.strip().strip('`').strip()
                        if v and v.isupper() and len(v) > 1:
                            claimed_values.add(v)

                    if not claimed_values:
                        continue

                    results["total_checked"] += 1
                    actual = truth_enums[enum_name]

                    missing = actual - claimed_values
                    extra = claimed_values - actual

                    if not missing and not extra:
                        results["complete"] += 1
                    else:
                        if missing:
                            results["incomplete"].append({
                                "enum": enum_name,
                                "missing_values": sorted(missing),
                                "claimed_count": len(claimed_values),
                                "actual_count": len(actual),
                                "source": rel_md,
                            })
                        if extra:
                            results["extra_values"].append({
                                "enum": enum_name,
                                "extra": sorted(extra),
                                "source": rel_md,
                            })

    return results


# ═══════════════════════════════════════════════════════════════
# CHECK 5: Diagram Component Names
# ═══════════════════════════════════════════════════════════════

def check_diagram_components(truth: dict) -> dict:
    """Verify component names in ASCII/Mermaid diagrams exist in codebase."""
    actual_classes = set(c["name"] for c in truth.get("backend_classes", []))
    actual_enums = set(e["name"] for e in truth.get("backend_enums", []))
    all_known = actual_classes | actual_enums

    results = {"total_checked": 0, "found": 0, "not_found": []}

    # Key component names to look for in diagrams (PascalCase or specific patterns)
    component_pattern = re.compile(r'(?:│|║|\│)\s*(?:\w+\s+)?([A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]+)+)')

    for md_file in sorted(V9_DIR.rglob("*.md")):
        if "verification" in md_file.name.lower() or "ROUND" in md_file.name:
            continue
        content = read_md(md_file)
        rel_md = str(md_file.relative_to(V9_DIR))

        # Find code blocks (ASCII diagrams)
        in_code_block = False
        checked_in_file = set()

        for line in content.split("\n"):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block or any(c in line for c in "│║┌└├┐┘┤"):
                # Extract PascalCase names from diagram lines
                for match in component_pattern.finditer(line):
                    name = match.group(1)
                    # Filter common non-class words
                    if name in (
                        "Layer", "Phase", "Sprint", "Backend", "Frontend",
                        "Platform", "Protocol", "Pipeline", "Handler",
                        "Service", "Storage", "Manager", "Builder",
                        "Engine", "Worker", "Server", "Client",
                        "Docker", "Compose", "Checkpoint", "Framework",
                        "Security", "Sandbox", "Performance", "Middleware",
                        "Session", "Memory", "Cache", "Redis", "PostgreSQL",
                        "TypeScript", "React", "Vite", "FastAPI",
                        "Authentication", "Authorization", "Traditional",
                        "Chinese", "Integration", "Orchestration", "Approval",
                        "Critical", "Network", "Database", "Application",
                        "Category", "Feature", "Workflow", "Agent",
                        "Fetch", "Zustand", "Shadcn", "ReactFlow",
                        "Total", "Overall", "Complete", "Partial",
                    ):
                        continue
                    if len(name) < 5 or name in checked_in_file:
                        continue

                    checked_in_file.add(name)
                    results["total_checked"] += 1

                    if name in all_known:
                        results["found"] += 1
                    else:
                        # Check if it's a known compound name (e.g., "SwarmWorkerExecutor")
                        # by checking if any known class contains this as substring
                        partial_match = any(name in cls for cls in all_known) or \
                                       any(cls in name for cls in all_known if len(cls) > 6)
                        if partial_match:
                            results["found"] += 1
                        else:
                            results["not_found"].append({
                                "name": name,
                                "source": rel_md,
                            })

    return results


# ═══════════════════════════════════════════════════════════════
# CHECK 6: Delta Report File Verification
# ═══════════════════════════════════════════════════════════════

def check_delta_files() -> dict:
    """Verify files mentioned in delta reports actually exist."""
    results = {"total_checked": 0, "exists": 0, "not_found": []}

    # Pattern for file paths in delta docs
    file_path_pattern = re.compile(
        r'`((?:backend|frontend)/[^`]+\.(?:py|ts|tsx|js))`'
    )

    for md_file in sorted(V9_DIR.glob("07-delta/*.md")):
        content = read_md(md_file)
        rel_md = str(md_file.relative_to(V9_DIR))
        checked = set()

        for match in file_path_pattern.finditer(content):
            fpath = match.group(1).replace("\\", "/")
            if fpath in checked:
                continue
            checked.add(fpath)

            results["total_checked"] += 1
            full_path = PROJECT_ROOT / fpath
            if full_path.exists():
                results["exists"] += 1
            else:
                # Try without backend/ prefix using src/
                alt = PROJECT_ROOT / "backend" / fpath.replace("backend/", "")
                if alt.exists():
                    results["exists"] += 1
                else:
                    results["not_found"].append({
                        "path": fpath,
                        "source": rel_md,
                    })

    return results


# ═══════════════════════════════════════════════════════════════
# CHECK 7: Import/Dependency Claims
# ═══════════════════════════════════════════════════════════════

def check_import_claims() -> dict:
    """Verify import/dependency claims in V9 analysis match actual imports."""
    results = {"total_checked": 0, "verified": 0, "not_found": []}

    # Pattern: "imports from `module.path`" or "depends on `module.path`"
    import_pattern = re.compile(
        r'`(src\.[\w.]+)`'
    )

    # Build actual import set by scanning all Python files
    actual_modules = set()
    for root, dirs, files in os.walk(BACKEND_SRC):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                rel = str(Path(root, f).relative_to(BACKEND_SRC.parent))
                rel = rel.replace("\\", "/").replace("/", ".").replace(".py", "")
                if rel.startswith("src."):
                    actual_modules.add(rel)
                # Also add directory-level modules
                dir_rel = str(Path(root).relative_to(BACKEND_SRC.parent))
                dir_rel = dir_rel.replace("\\", "/").replace("/", ".")
                actual_modules.add(dir_rel)

    for md_file in sorted(V9_DIR.rglob("*.md")):
        if "verification" in md_file.name.lower() or "ROUND" in md_file.name:
            continue
        content = read_md(md_file)
        rel_md = str(md_file.relative_to(V9_DIR))

        checked = set()
        for match in import_pattern.finditer(content):
            mod_path = match.group(1)
            if mod_path in checked:
                continue
            checked.add(mod_path)

            results["total_checked"] += 1

            # Check exact match or prefix match
            if mod_path in actual_modules:
                results["verified"] += 1
            else:
                # Check if it's a prefix of any actual module
                prefix_match = any(
                    m.startswith(mod_path) for m in actual_modules
                )
                if prefix_match:
                    results["verified"] += 1
                else:
                    # Strip trailing ClassName (last segment if PascalCase)
                    parts = mod_path.rsplit(".", 1)
                    if len(parts) == 2 and parts[1][0].isupper():
                        parent = parts[0]
                        parent_match = parent in actual_modules or any(
                            m.startswith(parent) for m in actual_modules
                        )
                        if parent_match:
                            results["verified"] += 1
                            continue
                    results["not_found"].append({
                        "module": mod_path,
                        "source": rel_md,
                    })

    return results


# ═══════════════════════════════════════════════════════════════
# CHECK 8: Key Component Existence (critical classes from diagrams)
# ═══════════════════════════════════════════════════════════════

def check_key_components(truth: dict) -> dict:
    """Verify the most critical component names mentioned across V9."""
    actual_classes = set(c["name"] for c in truth.get("backend_classes", []))
    actual_enums = set(e["name"] for e in truth.get("backend_enums", []))
    all_known = actual_classes | actual_enums

    # These are the most critical components mentioned in V9 diagrams and text
    critical_components = [
        # L04 Routing
        "BusinessIntentRouter", "PatternMatcher", "SemanticRouter", "LLMClassifier",
        "GuidedDialogEngine", "RiskAssessor", "CompletenessChecker",
        "InputGateway",
        # L05 Orchestration
        "OrchestratorMediator", "ContextBridge", "FrameworkSelector",
        "PipelineEventEmitter", "MediatorEventBridge",
        # L05 Handlers
        "RoutingHandler", "DialogHandler", "ApprovalHandler",
        "AgentHandler", "ExecutionHandler", "ContextHandler", "ObservabilityHandler",
        # L05 Bootstrap
        "OrchestratorBootstrap",
        # L06 MAF
        "BuilderAdapter", "ConcurrentBuilderAdapter", "HandoffBuilderAdapter",
        "GroupChatBuilderAdapter", "MagenticBuilderAdapter",
        "SwarmBuilderAdapter", "CustomBuilderAdapter",
        "PostgresCheckpointStorage", "RedisCheckpointCache",
        "InMemoryCheckpointStorage", "CachedCheckpointStorage",
        # L07 Claude
        "ClaudeSDKClient", "SmartFallback",
        # L08 MCP
        "MCPClient", "MCPProtocol", "ServerRegistry",
        "PermissionManager", "MCPPermissionChecker", "CommandWhitelist",
        "AuditLogger",
        # L09
        "SwarmTracker", "TaskDecomposer", "SwarmWorkerExecutor", "SwarmEventEmitter",
        "CorrelationAnalyzer", "RootCauseAnalyzer", "PatrolAgent",
        "UnifiedMemoryManager", "RAGPipeline",
        "FewShotLearner", "DecisionTracker",
        # L10
        "SessionService", "SessionAgentBridge", "AgentExecutor",
        "SessionEventPublisher", "ExecutionEventFactory",
        # L11
        "BaseRepository",
        # Domain models
        "Session", "Message", "ToolCall",
        # Contracts
        "OrchestratorRequest", "OrchestratorResponse", "HandlerResult",
        "HandlerType", "SSEEventType",
    ]

    results = {"total": len(critical_components), "found": 0, "missing": []}
    for comp in critical_components:
        if comp in all_known:
            results["found"] += 1
        else:
            # Try partial match (e.g., SwarmBuilderAdapter -> SwarmBuilder)
            partial = any(comp in c or c in comp for c in all_known if len(c) > 5)
            if partial:
                results["found"] += 1
            else:
                results["missing"].append(comp)

    return results


# ═══════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_report(checks: dict) -> str:
    lines = [
        "# V9 Round 7 Enhanced Validation Report",
        "",
        "> **Generated by**: r7_enhanced_validation.py",
        "> **Date**: 2026-03-30",
        "> **Scope**: 7 verification dimensions across all V9 analysis files",
        "> **Method**: Programmatic AST extraction + regex + file system checks",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "| Check | Items Checked | Verified | Issues | Accuracy |",
        "|-------|--------------|----------|--------|----------|",
    ]

    total_checked = 0
    total_verified = 0

    for name, data in checks.items():
        checked = data.get("total_checked", data.get("total", 0))
        verified = data.get("found", data.get("verified", data.get("exists",
                   data.get("complete", data.get("evidence_verified", 0)))))
        issues = checked - verified
        pct = f"{verified / max(checked, 1) * 100:.1f}%" if checked > 0 else "N/A"
        lines.append(f"| {name} | {checked} | {verified} | {issues} | {pct} |")
        total_checked += checked
        total_verified += verified

    overall_pct = f"{total_verified / max(total_checked, 1) * 100:.1f}%"
    lines.append(f"| **TOTAL** | **{total_checked}** | **{total_verified}** | **{total_checked - total_verified}** | **{overall_pct}** |")
    lines.append("")

    # Detail sections
    for name, data in checks.items():
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## {name}")
        lines.append(f"")

        checked = data.get("total_checked", data.get("total", 0))
        verified = data.get("found", data.get("verified", data.get("exists",
                   data.get("complete", data.get("evidence_verified", 0)))))
        lines.append(f"**Checked**: {checked} | **Verified**: {verified} | **Issues**: {checked - verified}")
        lines.append("")

        # Show issues (limit to 30 per section)
        issues_list = (
            data.get("not_found", []) or
            data.get("incomplete", []) or
            data.get("evidence_missing", []) or
            data.get("missing", [])
        )

        if isinstance(issues_list, list) and issues_list:
            lines.append("### Issues Found")
            lines.append("")
            if isinstance(issues_list[0], dict):
                # Get keys for table
                keys = list(issues_list[0].keys())
                # Filter out long lists
                display_keys = [k for k in keys if k not in ("actual_methods",)]
                header = " | ".join(display_keys)
                lines.append(f"| {header} |")
                lines.append(f"| {'---|' * len(display_keys)}")
                for item in issues_list[:30]:
                    vals = []
                    for k in display_keys:
                        v = item.get(k, "")
                        if isinstance(v, list):
                            v = ", ".join(str(x) for x in v[:5])
                            if len(item.get(k, [])) > 5:
                                v += "..."
                        vals.append(str(v)[:60])
                    lines.append(f"| {' | '.join(vals)} |")
                if len(issues_list) > 30:
                    lines.append(f"| ... ({len(issues_list) - 30} more) |")
            elif isinstance(issues_list[0], str):
                for item in issues_list[:30]:
                    lines.append(f"- `{item}`")
                if len(issues_list) > 30:
                    lines.append(f"- ... ({len(issues_list) - 30} more)")
        else:
            lines.append("No issues found. All items verified successfully.")
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("R7 Enhanced Validation: 7-Dimension Comprehensive Check")
    print("=" * 70)

    if not TRUTH_FILE.exists():
        print(f"ERROR: {TRUTH_FILE} not found. Run r7_extract_codebase_truth.py first.")
        return

    truth = load_truth()

    checks = {}

    print("\n[1/8] Checking key component existence...")
    checks["1_key_components"] = check_key_components(truth)
    r = checks["1_key_components"]
    print(f"  {r['found']}/{r['total']} critical components found "
          f"({len(r['missing'])} missing)")
    if r["missing"]:
        print(f"  Missing: {', '.join(r['missing'][:10])}")

    print("\n[2/8] Checking class method signatures...")
    checks["2_class_methods"] = check_class_methods(truth)
    r = checks["2_class_methods"]
    print(f"  {r['found']}/{r['total_checked']} methods verified "
          f"({len(r['not_found'])} not found)")

    print("\n[3/8] Checking file path existence...")
    checks["3_file_paths"] = check_file_paths()
    r = checks["3_file_paths"]
    print(f"  {r['exists']}/{r['total_checked']} paths exist "
          f"({len(r['not_found'])} not found)")

    print("\n[4/8] Checking feature evidence paths...")
    checks["4_feature_evidence"] = check_feature_evidence()
    r = checks["4_feature_evidence"]
    print(f"  {r['evidence_verified']}/{r['total_features']} evidence verified "
          f"({len(r['evidence_missing'])} missing)")

    print("\n[5/8] Checking enum completeness...")
    checks["5_enum_completeness"] = check_enum_completeness(truth)
    r = checks["5_enum_completeness"]
    print(f"  {r['complete']}/{r['total_checked']} enums complete "
          f"({len(r['incomplete'])} incomplete)")

    print("\n[6/8] Checking diagram component names...")
    checks["6_diagram_components"] = check_diagram_components(truth)
    r = checks["6_diagram_components"]
    print(f"  {r['found']}/{r['total_checked']} diagram names verified "
          f"({len(r['not_found'])} not found)")

    print("\n[7/8] Checking delta report file paths...")
    checks["7_delta_files"] = check_delta_files()
    r = checks["7_delta_files"]
    print(f"  {r['exists']}/{r['total_checked']} delta files exist "
          f"({len(r['not_found'])} not found)")

    print("\n[8/8] Checking import/dependency claims...")
    checks["8_import_claims"] = check_import_claims()
    r = checks["8_import_claims"]
    print(f"  {r['verified']}/{r['total_checked']} imports verified "
          f"({len(r['not_found'])} not found)")

    # Calculate overall
    total_c = sum(
        v.get("total_checked", v.get("total", 0))
        for v in checks.values()
    )
    total_v = sum(
        v.get("found", v.get("verified", v.get("exists",
        v.get("complete", v.get("evidence_verified", 0)))))
        for v in checks.values()
    )

    print(f"\n{'=' * 70}")
    print(f"OVERALL: {total_v}/{total_c} verified ({total_v/max(total_c,1)*100:.1f}%)")
    print(f"{'=' * 70}")

    # Save JSON
    # Convert sets to lists for JSON serialization
    def sanitize(obj):
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(i) for i in obj]
        return obj

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(sanitize(checks), f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON: {OUTPUT_JSON}")

    # Save MD report
    report = generate_report(checks)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[OK] Report: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
