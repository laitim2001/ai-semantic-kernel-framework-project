"""
Report Generator

Specialized generator for report files (Markdown, HTML, PDF).
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import uuid
import logging

from ..models import Attachment, AttachmentType
from .generator import BaseGenerator
from .types import (
    GenerationType,
    GenerationRequest,
    GenerationResult,
    ExportFormat,
    CONTENT_TYPE_MAP
)

logger = logging.getLogger(__name__)


class ReportGenerator(BaseGenerator):
    """報告生成器

    生成各種格式的報告文件。

    功能:
    - Markdown 報告
    - HTML 報告
    - 自動目錄生成
    - 樣式模板支援
    """

    # 報告格式對應的擴展名
    FORMAT_TO_EXT = {
        ExportFormat.MARKDOWN: ".md",
        ExportFormat.HTML: ".html",
        ExportFormat.TEXT: ".txt",
        ExportFormat.PDF: ".pdf"
    }

    # HTML 模板
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{ color: #2c3e50; }}
        h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
        }}
        pre {{
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #e1e4e8;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .metadata {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 20px;
        }}
        .toc {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .toc ul {{ margin: 0; padding-left: 20px; }}
    </style>
</head>
<body>
    <div class="metadata">
        <p>生成時間: {timestamp}</p>
        <p>Session: {session_id}</p>
    </div>
    {toc}
    {content}
</body>
</html>
"""

    # Markdown 報告頭模板
    MARKDOWN_HEADER = """---
title: {title}
date: {timestamp}
session: {session_id}
---

"""

    def __init__(self, storage: Optional[Any] = None):
        """
        初始化報告生成器

        Args:
            storage: 存儲服務實例
        """
        self._storage = storage

    def supports(self, generation_type: GenerationType) -> bool:
        """檢查是否支援此生成類型"""
        return generation_type == GenerationType.REPORT

    async def generate(
        self,
        session_id: str,
        request: GenerationRequest
    ) -> GenerationResult:
        """
        生成報告文件

        Args:
            session_id: Session ID
            request: 生成請求

        Returns:
            GenerationResult: 生成結果
        """
        try:
            # 確定輸出格式
            export_format = request.export_format or ExportFormat.MARKDOWN
            extension = self.FORMAT_TO_EXT.get(export_format, ".md")

            # 生成文件名
            filename = request.filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{timestamp}{extension}"
            elif not filename.endswith(extension):
                filename = f"{filename}{extension}"

            # 根據格式生成內容
            if export_format == ExportFormat.HTML:
                content = self._generate_html_report(
                    content=request.content,
                    title=request.options.get("title", "Report"),
                    session_id=session_id,
                    options=request.options
                )
                content_type = "text/html"
            elif export_format == ExportFormat.MARKDOWN:
                content = self._generate_markdown_report(
                    content=request.content,
                    title=request.options.get("title", "Report"),
                    session_id=session_id,
                    options=request.options
                )
                content_type = "text/markdown"
            else:
                content = request.content
                content_type = "text/plain"

            # 創建附件
            attachment_id = str(uuid.uuid4())
            size = len(content.encode("utf-8"))

            # 存儲文件
            if self._storage:
                storage_path = await self._storage.store_content(
                    session_id=session_id,
                    attachment_id=attachment_id,
                    content=content,
                    filename=filename
                )
            else:
                storage_path = f"/tmp/sessions/{session_id}/{attachment_id}/{filename}"

            logger.info(f"Generated report: {filename} ({size} bytes)")

            return GenerationResult(
                success=True,
                generation_type=GenerationType.REPORT,
                attachment_id=attachment_id,
                filename=filename,
                content_type=content_type,
                size=size
            )

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return GenerationResult(
                success=False,
                generation_type=GenerationType.REPORT,
                error=str(e)
            )

    def _generate_html_report(
        self,
        content: str,
        title: str,
        session_id: str,
        options: Dict[str, Any]
    ) -> str:
        """生成 HTML 報告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 轉換 Markdown 內容為 HTML (簡化版)
        html_content = self._markdown_to_html(content)

        # 生成目錄 (如果啟用)
        toc = ""
        if options.get("include_toc", True):
            toc = self._generate_toc(content)

        return self.HTML_TEMPLATE.format(
            title=title,
            timestamp=timestamp,
            session_id=session_id,
            toc=toc,
            content=html_content
        )

    def _generate_markdown_report(
        self,
        content: str,
        title: str,
        session_id: str,
        options: Dict[str, Any]
    ) -> str:
        """生成 Markdown 報告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 添加 YAML 頭
        if options.get("include_header", True):
            header = self.MARKDOWN_HEADER.format(
                title=title,
                timestamp=timestamp,
                session_id=session_id
            )
            content = header + content

        # 生成目錄 (如果啟用)
        if options.get("include_toc", False):
            toc = self._generate_markdown_toc(content)
            # 在第一個標題後插入目錄
            lines = content.split("\n")
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith("#") and not line.startswith("---"):
                    insert_pos = i + 1
                    break
            lines.insert(insert_pos, "\n## 目錄\n" + toc + "\n")
            content = "\n".join(lines)

        return content

    def _markdown_to_html(self, markdown_content: str) -> str:
        """簡化的 Markdown 轉 HTML"""
        import re

        html = markdown_content

        # 標題
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # 粗體和斜體
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # 程式碼區塊
        html = re.sub(
            r'```(\w*)\n(.*?)\n```',
            r'<pre><code class="language-\1">\2</code></pre>',
            html,
            flags=re.DOTALL
        )

        # 行內程式碼
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # 列表
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n)+', r'<ul>\g<0></ul>', html)

        # 段落
        paragraphs = html.split('\n\n')
        processed = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('<'):
                p = f'<p>{p}</p>'
            processed.append(p)
        html = '\n'.join(processed)

        return html

    def _generate_toc(self, content: str) -> str:
        """生成 HTML 目錄"""
        import re

        headings = re.findall(r'^(#{1,3})\s+(.+)$', content, re.MULTILINE)
        if not headings:
            return ""

        toc_items = []
        for level, title in headings:
            depth = len(level)
            anchor = title.lower().replace(' ', '-')
            indent = "  " * (depth - 1)
            toc_items.append(f'{indent}<li><a href="#{anchor}">{title}</a></li>')

        return f'<div class="toc"><h3>目錄</h3><ul>{"".join(toc_items)}</ul></div>'

    def _generate_markdown_toc(self, content: str) -> str:
        """生成 Markdown 目錄"""
        import re

        headings = re.findall(r'^(#{1,3})\s+(.+)$', content, re.MULTILINE)
        if not headings:
            return ""

        toc_items = []
        for level, title in headings:
            depth = len(level)
            anchor = title.lower().replace(' ', '-')
            indent = "  " * (depth - 1)
            toc_items.append(f'{indent}- [{title}](#{anchor})')

        return "\n".join(toc_items)

    async def generate_report(
        self,
        session_id: str,
        content: str,
        filename: str,
        title: str = "Report",
        format: ExportFormat = ExportFormat.MARKDOWN,
        include_toc: bool = True,
        include_header: bool = True
    ) -> GenerationResult:
        """
        便捷方法：生成報告文件

        Args:
            session_id: Session ID
            content: 報告內容
            filename: 文件名
            title: 報告標題
            format: 輸出格式
            include_toc: 是否包含目錄
            include_header: 是否包含頭部

        Returns:
            GenerationResult: 生成結果
        """
        request = GenerationRequest(
            generation_type=GenerationType.REPORT,
            content=content,
            filename=filename,
            export_format=format,
            options={
                "title": title,
                "include_toc": include_toc,
                "include_header": include_header
            }
        )

        return await self.generate(session_id, request)

    async def generate_analysis_report(
        self,
        session_id: str,
        analysis_results: List[Dict[str, Any]],
        title: str = "Analysis Report",
        format: ExportFormat = ExportFormat.MARKDOWN
    ) -> GenerationResult:
        """
        生成分析報告

        Args:
            session_id: Session ID
            analysis_results: 分析結果列表
            title: 報告標題
            format: 輸出格式

        Returns:
            GenerationResult: 生成結果
        """
        # 構建報告內容
        sections = []
        sections.append(f"# {title}\n")

        for i, result in enumerate(analysis_results, 1):
            sections.append(f"## {i}. {result.get('title', f'Analysis {i}')}\n")

            if result.get("summary"):
                sections.append(f"### 摘要\n{result['summary']}\n")

            if result.get("findings"):
                sections.append("### 發現\n")
                for finding in result["findings"]:
                    sections.append(f"- {finding}\n")

            if result.get("recommendations"):
                sections.append("### 建議\n")
                for rec in result["recommendations"]:
                    sections.append(f"- {rec}\n")

            if result.get("data"):
                sections.append("### 資料\n")
                sections.append(f"```json\n{result['data']}\n```\n")

            sections.append("\n")

        content = "\n".join(sections)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_report_{timestamp}"

        return await self.generate_report(
            session_id=session_id,
            content=content,
            filename=filename,
            title=title,
            format=format
        )
