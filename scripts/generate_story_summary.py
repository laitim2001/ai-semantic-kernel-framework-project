#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Story Summary Generator
自動生成 Story 實現摘要文件

用法:
    python scripts/generate_story_summary.py --story S4-1 --title "User Dashboard" --points 5
    python scripts/generate_story_summary.py --interactive
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 設置 stdout 編碼為 UTF-8 (解決 Windows 編碼問題)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_PATH = PROJECT_ROOT / "scripts" / "templates" / "story-summary-template.md"
DOCS_PATH = PROJECT_ROOT / "docs" / "03-implementation"


def get_sprint_number(story_id: str) -> int:
    """從 Story ID 提取 Sprint 編號"""
    match = re.match(r"S(\d+)-", story_id)
    if match:
        return int(match.group(1))
    raise ValueError(f"Invalid story ID format: {story_id}")


def slugify(title: str) -> str:
    """將標題轉換為文件名友好格式"""
    # 轉小寫，替換空格為連字符
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug


def load_template() -> str:
    """載入摘要模板"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def generate_summary(
    story_id: str,
    title: str,
    points: int,
    status: str = "✅ 已完成",
    completion_date: Optional[str] = None,
) -> str:
    """生成摘要內容"""
    template = load_template()

    if completion_date is None:
        completion_date = datetime.now().strftime("%Y-%m-%d")

    # 基本替換
    content = template.replace("{{STORY_ID}}", story_id)
    content = content.replace("{{STORY_TITLE}}", title)
    content = content.replace("{{STORY_POINTS}}", str(points))
    content = content.replace("{{STATUS}}", status)
    content = content.replace("{{COMPLETION_DATE}}", completion_date)
    content = content.replace("{{GENERATED_DATE}}", datetime.now().strftime("%Y-%m-%d"))

    # Sprint 規劃文件
    sprint_num = get_sprint_number(story_id)
    sprint_planning_files = {
        0: "sprint-0-mvp-revised.md",
        1: "sprint-1-core-services.md",
        2: "sprint-2-integrations.md",
        3: "sprint-3-security-observability.md",
        4: "sprint-4-ui-frontend.md",
        5: "sprint-5-testing-launch.md",
    }
    content = content.replace(
        "{{SPRINT_PLANNING_FILE}}",
        sprint_planning_files.get(sprint_num, f"sprint-{sprint_num}.md")
    )

    return content


def save_summary(story_id: str, title: str, content: str) -> Path:
    """保存摘要文件"""
    sprint_num = get_sprint_number(story_id)
    sprint_dir = DOCS_PATH / f"sprint-{sprint_num}" / "summaries"

    # 確保目錄存在
    sprint_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    title_slug = slugify(title)
    filename = f"{story_id}-{title_slug}-summary.md"
    filepath = sprint_dir / filename

    # 寫入文件
    filepath.write_text(content, encoding="utf-8")
    return filepath


def interactive_mode():
    """交互式模式"""
    print("\n" + "=" * 50)
    print("📝 Story Summary Generator")
    print("=" * 50 + "\n")

    # 收集輸入
    story_id = input("Story ID (e.g., S4-1): ").strip().upper()
    title = input("Story Title: ").strip()
    points = int(input("Story Points: ").strip())

    status_choice = input("Status [1=完成, 2=進行中, 3=待開始] (default: 1): ").strip()
    status_map = {"1": "✅ 已完成", "2": "🔄 進行中", "3": "⏳ 待開始"}
    status = status_map.get(status_choice, "✅ 已完成")

    completion_date = input(f"Completion Date (default: {datetime.now().strftime('%Y-%m-%d')}): ").strip()
    if not completion_date:
        completion_date = None

    # 生成並保存
    print("\n生成摘要中...")
    content = generate_summary(story_id, title, points, status, completion_date)
    filepath = save_summary(story_id, title, content)

    print(f"\n✅ 摘要已生成: {filepath}")
    print("\n⚠️  請編輯文件填寫以下內容:")
    print("   - 驗收標準達成情況")
    print("   - 技術實現細節")
    print("   - 代碼位置")
    print("   - 測試覆蓋")
    print("   - 備註")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Story Summary Document",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # 命令行模式
    python scripts/generate_story_summary.py --story S4-1 --title "User Dashboard" --points 5

    # 交互式模式
    python scripts/generate_story_summary.py --interactive

    # 指定狀態和日期
    python scripts/generate_story_summary.py --story S4-2 --title "API Refactor" --points 3 --status "🔄 進行中"
        """
    )

    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--story", "-s", type=str, help="Story ID (e.g., S4-1)")
    parser.add_argument("--title", "-t", type=str, help="Story title")
    parser.add_argument("--points", "-p", type=int, help="Story points")
    parser.add_argument("--status", type=str, default="✅ 已完成", help="Status")
    parser.add_argument("--date", "-d", type=str, help="Completion date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.story and args.title and args.points:
        content = generate_summary(
            args.story,
            args.title,
            args.points,
            args.status,
            args.date
        )
        filepath = save_summary(args.story, args.title, content)
        print(f"✅ Summary generated: {filepath}")
    else:
        parser.print_help()
        print("\n❌ Error: Please provide --story, --title, and --points, or use --interactive mode")


if __name__ == "__main__":
    main()
