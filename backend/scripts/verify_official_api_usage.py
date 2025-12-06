#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
驗證腳本: 檢查 Agent Framework 適配器是否正確使用官方 API

此腳本會檢查 builders/ 目錄下的所有適配器文件，確保它們：
1. 有從 agent_framework 導入必要的官方類
2. 在類中有使用官方 Builder 的實例變數

使用方式:
    python scripts/verify_official_api_usage.py

返回碼:
    0: 所有檢查通過
    1: 有檢查失敗
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# 每個適配器文件需要導入的官方類
REQUIRED_IMPORTS: Dict[str, List[str]] = {
    "concurrent.py": ["ConcurrentBuilder"],
    "groupchat.py": ["GroupChatBuilder", "GroupChatDirective", "ManagerSelectionResponse"],
    "handoff.py": ["HandoffBuilder", "HandoffUserInputRequest"],
    "magentic.py": ["MagenticBuilder", "MagenticManagerBase", "StandardMagenticManager"],
    "workflow_executor.py": ["WorkflowExecutor", "SubWorkflowRequestMessage", "SubWorkflowResponseMessage"],
}

# 每個適配器類必須包含的官方 Builder 實例變數
REQUIRED_INSTANCE_VARS: Dict[str, List[str]] = {
    "concurrent.py": ["_builder"],  # self._builder = ConcurrentBuilder()
    "groupchat.py": ["_builder"],   # self._builder = GroupChatBuilder()
    "handoff.py": ["_builder"],     # self._builder = HandoffBuilder()
    "magentic.py": ["_builder"],    # self._builder = MagenticBuilder()
    "workflow_executor.py": ["_executor"],  # self._executor = WorkflowExecutor(...)
}

# 遷移文件和輔助文件（這些不需要使用官方 API）
SKIP_FILES = {
    "__init__.py",
    "concurrent_migration.py",
    "handoff_migration.py",
    "handoff_hitl.py",
    "groupchat_migration.py",
    "groupchat_orchestrator.py",
    "magentic_migration.py",
    "workflow_executor_migration.py",
    "edge_routing.py",
}


def extract_imports_from_agent_framework(tree: ast.AST) -> Set[str]:
    """從 AST 中提取所有從 agent_framework 導入的類名。"""
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "agent_framework" in node.module:
                for alias in node.names:
                    imported.add(alias.name)
    return imported


def check_class_has_builder_instance(tree: ast.AST, var_names: List[str]) -> Tuple[bool, List[str]]:
    """檢查類是否有指定的實例變數（通過 self.xxx = ... 賦值）。"""
    found_vars = set()
    missing_vars = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name) and target.value.id == "self":
                        found_vars.add(target.attr)

    for var_name in var_names:
        if var_name not in found_vars:
            missing_vars.append(var_name)

    return len(missing_vars) == 0, missing_vars


def verify_file(file_path: Path, required_imports: List[str], required_vars: List[str]) -> Tuple[bool, List[str]]:
    """Verify a single file uses official API correctly."""
    errors = []

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"Read error: {e}")
        return False, errors

    # Check imports
    imported = extract_imports_from_agent_framework(tree)
    missing_imports = set(required_imports) - imported
    if missing_imports:
        errors.append(f"Missing official API imports: {', '.join(sorted(missing_imports))}")

    # Check instance variables
    has_vars, missing_vars = check_class_has_builder_instance(tree, required_vars)
    if not has_vars:
        errors.append(f"Missing official Builder instance vars: {', '.join(missing_vars)}")

    return len(errors) == 0, errors


def main() -> int:
    """Main verification function."""
    print("=" * 60)
    print("Agent Framework Official API Usage Verification")
    print("=" * 60)
    print()

    # Find builders directory
    script_dir = Path(__file__).parent
    builders_dir = script_dir.parent / "src" / "integrations" / "agent_framework" / "builders"

    if not builders_dir.exists():
        print(f"[ERROR] Cannot find builders directory: {builders_dir}")
        return 1

    print(f"Checking directory: {builders_dir}")
    print()

    all_passed = True
    checked_count = 0
    passed_count = 0
    skipped_count = 0

    # Check each file that needs verification
    for filename, required_imports in REQUIRED_IMPORTS.items():
        file_path = builders_dir / filename

        if filename in SKIP_FILES:
            print(f"[SKIP] {filename}: Migration/helper file")
            skipped_count += 1
            continue

        if not file_path.exists():
            print(f"[WARN] {filename}: File not found")
            continue

        checked_count += 1
        required_vars = REQUIRED_INSTANCE_VARS.get(filename, [])
        passed, errors = verify_file(file_path, required_imports, required_vars)

        if passed:
            print(f"[PASS] {filename}")
            passed_count += 1
        else:
            print(f"[FAIL] {filename}")
            for error in errors:
                print(f"   - {error}")
            all_passed = False

    # Check for unknown files
    print()
    print("-" * 60)

    # List all .py files in builders/
    all_py_files = set(f.name for f in builders_dir.glob("*.py"))
    known_files = set(REQUIRED_IMPORTS.keys()) | SKIP_FILES
    unknown_files = all_py_files - known_files

    if unknown_files:
        print(f"[WARN] Unknown files found (not in verification list):")
        for f in sorted(unknown_files):
            print(f"   - {f}")

    print()
    print("=" * 60)
    print(f"Summary: {passed_count}/{checked_count} passed, {skipped_count} skipped")
    print("=" * 60)

    if all_passed:
        print("[SUCCESS] All checks passed!")
        return 0
    else:
        print("[ERROR] Some checks failed. Please fix and re-run.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
