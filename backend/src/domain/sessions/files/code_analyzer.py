"""
Code Analyzer

Specialized analyzer for source code files (Python, JavaScript, TypeScript, etc.).
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import re
import logging

from ..models import Attachment, AttachmentType
from .analyzer import BaseAnalyzer
from .types import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    SUPPORTED_EXTENSIONS,
    LANGUAGE_EXTENSIONS
)

logger = logging.getLogger(__name__)


class CodeAnalyzer(BaseAnalyzer):
    """程式碼分析器

    支援分析多種程式語言的源代碼文件。

    功能:
    - 代碼統計 (行數、函數數量、類數量)
    - 結構分析 (函數、類、導入)
    - 代碼說明生成
    - 代碼問答
    """

    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS["code"]

    # 語言特定的模式
    PATTERNS = {
        "python": {
            "function": r"^\s*(?:async\s+)?def\s+(\w+)\s*\(",
            "class": r"^\s*class\s+(\w+)\s*[:\(]",
            "import": r"^(?:from\s+[\w.]+\s+)?import\s+.+",
            "comment": r"^\s*#.*$",
            "docstring": r'^\s*""".*?"""',
        },
        "javascript": {
            "function": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>)",
            "class": r"class\s+(\w+)",
            "import": r"^(?:import|export)\s+.+",
            "comment": r"^\s*//.*$",
        },
        "typescript": {
            "function": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*:\s*\([^)]*\)\s*=>)",
            "class": r"(?:class|interface)\s+(\w+)",
            "import": r"^(?:import|export)\s+.+",
            "comment": r"^\s*//.*$",
        },
        "java": {
            "function": r"(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{",
            "class": r"(?:public|private)?\s*(?:abstract\s+)?class\s+(\w+)",
            "import": r"^import\s+.+;",
            "comment": r"^\s*//.*$",
        },
        "go": {
            "function": r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
            "class": r"type\s+(\w+)\s+struct",
            "import": r'^import\s+(?:\([\s\S]*?\)|"[^"]+")',
            "comment": r"^\s*//.*$",
        },
    }

    def __init__(self, llm_client: Optional[Any] = None):
        """
        初始化程式碼分析器

        Args:
            llm_client: LLM 客戶端 (用於代碼說明)
        """
        self._llm_client = llm_client

    def supports(self, attachment: Attachment) -> bool:
        """檢查是否支援此附件"""
        if attachment.attachment_type != AttachmentType.CODE:
            return False
        ext = self._get_file_extension(attachment.filename)
        return ext in self.SUPPORTED_EXTENSIONS

    async def analyze(
        self,
        attachment: Attachment,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """
        分析程式碼

        Args:
            attachment: 附件對象
            request: 分析請求

        Returns:
            AnalysisResult: 分析結果
        """
        try:
            # 讀取代碼內容
            content = await self._read_file_content(attachment.storage_path)

            # 檢測語言
            language = self._detect_language(attachment.filename)

            # 根據分析類型執行不同分析
            if request.analysis_type == AnalysisType.SUMMARY:
                return await self._analyze_summary(attachment, content, language, request)
            elif request.analysis_type == AnalysisType.STATISTICS:
                return await self._analyze_statistics(attachment, content, language, request)
            elif request.analysis_type == AnalysisType.EXTRACT:
                return await self._analyze_extract(attachment, content, language, request)
            elif request.analysis_type == AnalysisType.QUERY:
                return await self._analyze_query(attachment, content, language, request)
            else:
                return await self._analyze_summary(attachment, content, language, request)

        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return AnalysisResult.error_result(str(e), request.analysis_type)

    def _detect_language(self, filename: str) -> str:
        """檢測程式語言"""
        ext = self._get_file_extension(filename)
        return LANGUAGE_EXTENSIONS.get(ext, "unknown")

    async def _analyze_summary(
        self,
        attachment: Attachment,
        content: str,
        language: str,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """生成代碼摘要"""
        metadata = self._get_file_metadata(attachment)
        metadata["language"] = language

        # 計算統計
        stats = self._compute_code_statistics(content, language)

        # 提取結構
        structure = self._extract_structure(content, language)

        # 如果有 LLM，生成智能說明
        explanation = None
        if self._llm_client:
            explanation = await self._generate_code_explanation(content, language, request)

        summary_parts = [
            f"語言: {language}",
            f"總行數: {stats['total_lines']}",
            f"代碼行: {stats['code_lines']}",
            f"函數: {stats['function_count']}",
            f"類: {stats['class_count']}"
        ]

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.SUMMARY,
            content=explanation or ", ".join(summary_parts),
            data={
                "statistics": stats,
                "structure": structure,
                "explanation": explanation,
                "has_llm_explanation": explanation is not None,
                "preview": content[:1000] + ("..." if len(content) > 1000 else "")
            },
            metadata=metadata
        )

    async def _analyze_statistics(
        self,
        attachment: Attachment,
        content: str,
        language: str,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """生成代碼統計"""
        metadata = self._get_file_metadata(attachment)
        metadata["language"] = language

        stats = self._compute_code_statistics(content, language)

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.STATISTICS,
            content=f"{language} 代碼: {stats['code_lines']} 行代碼, {stats['function_count']} 函數, {stats['class_count']} 類",
            data={"statistics": stats},
            metadata=metadata
        )

    async def _analyze_extract(
        self,
        attachment: Attachment,
        content: str,
        language: str,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """提取代碼結構"""
        metadata = self._get_file_metadata(attachment)
        metadata["language"] = language

        structure = self._extract_structure(content, language)

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.EXTRACT,
            content=f"提取了 {len(structure['functions'])} 個函數, {len(structure['classes'])} 個類",
            data={"structure": structure},
            metadata=metadata
        )

    async def _analyze_query(
        self,
        attachment: Attachment,
        content: str,
        language: str,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """回答代碼相關問題"""
        metadata = self._get_file_metadata(attachment)
        metadata["language"] = language

        if not request.query:
            return AnalysisResult.error_result(
                "Query is required for QUERY analysis type",
                AnalysisType.QUERY
            )

        if self._llm_client:
            answer = await self._query_code_with_llm(content, language, request.query, request)
            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.QUERY,
                content=answer,
                data={
                    "query": request.query,
                    "language": language
                },
                metadata=metadata
            )

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.QUERY,
            content="代碼問答需要 LLM 客戶端支援",
            data={"query": request.query},
            metadata=metadata
        )

    def _compute_code_statistics(self, content: str, language: str) -> Dict[str, Any]:
        """計算代碼統計"""
        lines = content.split("\n")
        total_lines = len(lines)

        # 計算各類行數
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_pattern = self.PATTERNS.get(language, {}).get("comment", r"^\s*#.*$")
        comment_lines = sum(1 for line in lines if re.match(comment_pattern, line))
        code_lines = total_lines - blank_lines - comment_lines

        # 計算函數和類
        function_pattern = self.PATTERNS.get(language, {}).get("function", r"def\s+(\w+)")
        class_pattern = self.PATTERNS.get(language, {}).get("class", r"class\s+(\w+)")
        import_pattern = self.PATTERNS.get(language, {}).get("import", r"^import\s+")

        functions = re.findall(function_pattern, content, re.MULTILINE)
        classes = re.findall(class_pattern, content, re.MULTILINE)
        imports = re.findall(import_pattern, content, re.MULTILINE)

        # 計算複雜度指標
        avg_line_length = sum(len(line) for line in lines) / total_lines if total_lines > 0 else 0

        return {
            "total_lines": total_lines,
            "code_lines": code_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "function_count": len(functions) if isinstance(functions[0], str) if functions else 0 else sum(len([f for f in func if f]) for func in functions),
            "class_count": len(classes),
            "import_count": len(imports),
            "avg_line_length": round(avg_line_length, 1),
            "char_count": len(content)
        }

    def _extract_structure(self, content: str, language: str) -> Dict[str, List]:
        """提取代碼結構"""
        structure = {
            "functions": [],
            "classes": [],
            "imports": []
        }

        lines = content.split("\n")

        # 提取函數
        function_pattern = self.PATTERNS.get(language, {}).get("function")
        if function_pattern:
            for i, line in enumerate(lines):
                match = re.match(function_pattern, line)
                if match:
                    func_name = next((g for g in match.groups() if g), None)
                    if func_name:
                        structure["functions"].append({
                            "name": func_name,
                            "line": i + 1
                        })

        # 提取類
        class_pattern = self.PATTERNS.get(language, {}).get("class")
        if class_pattern:
            for i, line in enumerate(lines):
                match = re.match(class_pattern, line)
                if match:
                    class_name = match.group(1)
                    structure["classes"].append({
                        "name": class_name,
                        "line": i + 1
                    })

        # 提取導入
        import_pattern = self.PATTERNS.get(language, {}).get("import")
        if import_pattern:
            for i, line in enumerate(lines):
                if re.match(import_pattern, line):
                    structure["imports"].append({
                        "statement": line.strip(),
                        "line": i + 1
                    })

        return structure

    async def _generate_code_explanation(
        self,
        content: str,
        language: str,
        request: AnalysisRequest
    ) -> Optional[str]:
        """使用 LLM 生成代碼說明"""
        if not self._llm_client:
            return None

        try:
            max_content = content[:request.max_content_length]

            prompt = f"""請分析以下 {language} 代碼並提供簡潔說明 (使用{request.language}):

```{language}
{max_content}
```

說明:"""

            response = await self._llm_client.generate(prompt)
            return response.strip()

        except Exception as e:
            logger.error(f"LLM code explanation failed: {e}")
            return None

    async def _query_code_with_llm(
        self,
        content: str,
        language: str,
        query: str,
        request: AnalysisRequest
    ) -> str:
        """使用 LLM 回答代碼問題"""
        if not self._llm_client:
            return "LLM 客戶端不可用"

        try:
            max_content = content[:request.max_content_length]

            prompt = f"""基於以下 {language} 代碼回答問題 (使用{request.language}):

```{language}
{max_content}
```

問題: {query}

回答:"""

            response = await self._llm_client.generate(prompt)
            return response.strip()

        except Exception as e:
            logger.error(f"LLM code query failed: {e}")
            return f"代碼問答處理失敗: {str(e)}"
