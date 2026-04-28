"""
Data Analyzer

Specialized analyzer for data files (CSV, JSON, Excel, XML, etc.).
Uses Code Interpreter for data analysis and visualization.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import logging

from ..models import Attachment, AttachmentType
from .analyzer import BaseAnalyzer
from .types import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    SUPPORTED_EXTENSIONS
)

logger = logging.getLogger(__name__)


class DataAnalyzer(BaseAnalyzer):
    """數據分析器

    支援分析 CSV、JSON、Excel、XML 等數據格式。
    使用 Code Interpreter 進行數據分析和視覺化。

    功能:
    - 數據摘要
    - 統計分析
    - 數據轉換
    - 數據查詢
    - 視覺化生成
    """

    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS["data"]

    def __init__(
        self,
        code_interpreter: Optional[Any] = None,
        llm_client: Optional[Any] = None
    ):
        """
        初始化數據分析器

        Args:
            code_interpreter: Code Interpreter 實例 (用於數據分析)
            llm_client: LLM 客戶端 (用於數據理解)
        """
        self._code_interpreter = code_interpreter
        self._llm_client = llm_client

    def supports(self, attachment: Attachment) -> bool:
        """檢查是否支援此附件"""
        if attachment.attachment_type != AttachmentType.DATA:
            return False
        ext = self._get_file_extension(attachment.filename)
        return ext in self.SUPPORTED_EXTENSIONS

    async def analyze(
        self,
        attachment: Attachment,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """
        分析數據文件

        Args:
            attachment: 附件對象
            request: 分析請求

        Returns:
            AnalysisResult: 分析結果
        """
        try:
            # 讀取數據
            data = await self._read_data(attachment)

            # 根據分析類型執行不同分析
            if request.analysis_type == AnalysisType.SUMMARY:
                return await self._analyze_summary(attachment, data, request)
            elif request.analysis_type == AnalysisType.STATISTICS:
                return await self._analyze_statistics(attachment, data, request)
            elif request.analysis_type == AnalysisType.TRANSFORM:
                return await self._analyze_transform(attachment, data, request)
            elif request.analysis_type == AnalysisType.QUERY:
                return await self._analyze_query(attachment, data, request)
            elif request.analysis_type == AnalysisType.VISUALIZE:
                return await self._analyze_visualize(attachment, data, request)
            else:
                return await self._analyze_summary(attachment, data, request)

        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return AnalysisResult.error_result(str(e), request.analysis_type)

    async def _read_data(self, attachment: Attachment) -> Dict[str, Any]:
        """
        讀取數據文件

        Returns:
            Dict containing data structure and preview
        """
        ext = self._get_file_extension(attachment.filename)
        path = attachment.storage_path

        if ext == ".csv":
            return await self._read_csv(path)
        elif ext == ".json":
            return await self._read_json(path)
        elif ext in [".xlsx", ".xls"]:
            return await self._read_excel(path)
        elif ext == ".xml":
            return await self._read_xml(path)
        elif ext in [".yaml", ".yml"]:
            return await self._read_yaml(path)
        elif ext == ".parquet":
            return await self._read_parquet(path)
        else:
            return await self._read_generic(path)

    async def _read_csv(self, path: str) -> Dict[str, Any]:
        """讀取 CSV 文件"""
        try:
            import pandas as pd
            df = pd.read_csv(path, nrows=1000)  # 限制行數

            return {
                "format": "csv",
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "preview": df.head(10).to_dict(orient="records"),
                "dataframe": df
            }
        except ImportError:
            # 無 pandas 時的備用方案
            import csv
            import aiofiles

            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()

            reader = csv.DictReader(content.split("\n"))
            rows = list(reader)[:100]

            return {
                "format": "csv",
                "rows": len(rows),
                "columns": list(rows[0].keys()) if rows else [],
                "preview": rows[:10],
                "raw_data": rows
            }

    async def _read_json(self, path: str) -> Dict[str, Any]:
        """讀取 JSON 文件"""
        import aiofiles

        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()

        data = json.loads(content)

        if isinstance(data, list):
            return {
                "format": "json",
                "type": "array",
                "length": len(data),
                "sample_keys": list(data[0].keys()) if data and isinstance(data[0], dict) else [],
                "preview": data[:10],
                "raw_data": data
            }
        elif isinstance(data, dict):
            return {
                "format": "json",
                "type": "object",
                "keys": list(data.keys()),
                "preview": {k: v for k, v in list(data.items())[:10]},
                "raw_data": data
            }
        else:
            return {
                "format": "json",
                "type": type(data).__name__,
                "preview": data,
                "raw_data": data
            }

    async def _read_excel(self, path: str) -> Dict[str, Any]:
        """讀取 Excel 文件"""
        try:
            import pandas as pd
            df = pd.read_excel(path, nrows=1000)

            return {
                "format": "excel",
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "preview": df.head(10).to_dict(orient="records"),
                "dataframe": df
            }
        except ImportError:
            return {
                "format": "excel",
                "error": "需要 openpyxl 或 xlrd 庫來讀取 Excel 文件"
            }

    async def _read_xml(self, path: str) -> Dict[str, Any]:
        """讀取 XML 文件"""
        import aiofiles
        import xml.etree.ElementTree as ET

        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()

        root = ET.fromstring(content)

        def element_to_dict(elem):
            result = {"tag": elem.tag}
            if elem.attrib:
                result["attributes"] = elem.attrib
            if elem.text and elem.text.strip():
                result["text"] = elem.text.strip()
            children = [element_to_dict(child) for child in elem]
            if children:
                result["children"] = children[:10]  # 限制子元素
            return result

        return {
            "format": "xml",
            "root_tag": root.tag,
            "structure": element_to_dict(root),
            "raw_content": content[:5000]
        }

    async def _read_yaml(self, path: str) -> Dict[str, Any]:
        """讀取 YAML 文件"""
        try:
            import yaml
            import aiofiles

            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()

            data = yaml.safe_load(content)

            return {
                "format": "yaml",
                "type": type(data).__name__,
                "preview": data if isinstance(data, (dict, list)) else str(data),
                "raw_data": data
            }
        except ImportError:
            return {
                "format": "yaml",
                "error": "需要 PyYAML 庫來讀取 YAML 文件"
            }

    async def _read_parquet(self, path: str) -> Dict[str, Any]:
        """讀取 Parquet 文件"""
        try:
            import pandas as pd
            df = pd.read_parquet(path)

            return {
                "format": "parquet",
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "preview": df.head(10).to_dict(orient="records"),
                "dataframe": df
            }
        except ImportError:
            return {
                "format": "parquet",
                "error": "需要 pyarrow 或 fastparquet 庫來讀取 Parquet 文件"
            }

    async def _read_generic(self, path: str) -> Dict[str, Any]:
        """通用讀取方法"""
        content = await self._read_file_content(path)
        return {
            "format": "text",
            "content": content[:5000],
            "length": len(content)
        }

    async def _analyze_summary(
        self,
        attachment: Attachment,
        data: Dict[str, Any],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """生成數據摘要"""
        metadata = self._get_file_metadata(attachment)
        metadata["data_format"] = data.get("format", "unknown")

        # 生成摘要信息
        summary_parts = [f"格式: {data.get('format', 'unknown').upper()}"]

        if "rows" in data:
            summary_parts.append(f"行數: {data['rows']}")
        if "columns" in data:
            summary_parts.append(f"欄位: {len(data['columns'])}")
        if "length" in data:
            summary_parts.append(f"項目數: {data['length']}")

        # 如果有 DataFrame，計算基本統計
        stats = None
        if "dataframe" in data:
            stats = self._compute_dataframe_stats(data["dataframe"])

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.SUMMARY,
            content=", ".join(summary_parts),
            data={
                "format": data.get("format"),
                "rows": data.get("rows"),
                "columns": data.get("columns"),
                "preview": data.get("preview"),
                "statistics": stats
            },
            metadata=metadata
        )

    async def _analyze_statistics(
        self,
        attachment: Attachment,
        data: Dict[str, Any],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """生成詳細統計分析"""
        metadata = self._get_file_metadata(attachment)

        if "dataframe" in data:
            stats = self._compute_detailed_stats(data["dataframe"])
            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.STATISTICS,
                content=f"數據包含 {data['rows']} 行, {len(data['columns'])} 欄位的詳細統計",
                data={"statistics": stats},
                metadata=metadata
            )

        # 使用 Code Interpreter 進行分析
        if self._code_interpreter and "format" in data:
            result = await self._run_statistics_code(attachment.storage_path, data["format"])
            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.STATISTICS,
                content="使用 Code Interpreter 生成的統計分析",
                data={"code_interpreter_result": result},
                metadata=metadata
            )

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.STATISTICS,
            content="統計分析需要 pandas 或 Code Interpreter 支援",
            data={"raw_data": data.get("preview", data.get("raw_data"))},
            metadata=metadata
        )

    async def _analyze_transform(
        self,
        attachment: Attachment,
        data: Dict[str, Any],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """數據轉換"""
        metadata = self._get_file_metadata(attachment)

        # 獲取目標格式
        target_format = request.options.get("target_format", "json")

        if "dataframe" in data:
            df = data["dataframe"]
            if target_format == "json":
                transformed = df.to_json(orient="records")
            elif target_format == "csv":
                transformed = df.to_csv(index=False)
            elif target_format == "dict":
                transformed = df.to_dict(orient="records")
            else:
                transformed = df.to_string()

            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.TRANSFORM,
                content=f"數據已轉換為 {target_format} 格式",
                data={
                    "target_format": target_format,
                    "transformed": transformed if isinstance(transformed, (dict, list)) else transformed[:5000]
                },
                metadata=metadata
            )

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.TRANSFORM,
            content="數據轉換需要 pandas 支援",
            data={"original_format": data.get("format")},
            metadata=metadata
        )

    async def _analyze_query(
        self,
        attachment: Attachment,
        data: Dict[str, Any],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """數據查詢"""
        metadata = self._get_file_metadata(attachment)

        if not request.query:
            return AnalysisResult.error_result(
                "Query is required for QUERY analysis type",
                AnalysisType.QUERY
            )

        # 使用 Code Interpreter 執行查詢
        if self._code_interpreter:
            result = await self._run_query_code(
                attachment.storage_path,
                data.get("format"),
                request.query
            )
            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.QUERY,
                content="查詢結果",
                data={
                    "query": request.query,
                    "result": result
                },
                metadata=metadata
            )

        # 使用 LLM 理解查詢意圖
        if self._llm_client:
            answer = await self._query_with_llm(data, request.query, request)
            return AnalysisResult(
                success=True,
                analysis_type=AnalysisType.QUERY,
                content=answer,
                data={"query": request.query},
                metadata=metadata
            )

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.QUERY,
            content="數據查詢需要 Code Interpreter 或 LLM 支援",
            data={"query": request.query},
            metadata=metadata
        )

    async def _analyze_visualize(
        self,
        attachment: Attachment,
        data: Dict[str, Any],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """生成視覺化"""
        metadata = self._get_file_metadata(attachment)

        if not self._code_interpreter:
            return AnalysisResult(
                success=False,
                analysis_type=AnalysisType.VISUALIZE,
                error="視覺化需要 Code Interpreter 支援",
                metadata=metadata
            )

        chart_type = request.options.get("chart_type", "auto")
        result = await self._run_visualization_code(
            attachment.storage_path,
            data.get("format"),
            chart_type
        )

        return AnalysisResult(
            success=True,
            analysis_type=AnalysisType.VISUALIZE,
            content="視覺化圖表已生成",
            data={
                "chart_type": chart_type,
                "result": result
            },
            metadata=metadata
        )

    def _compute_dataframe_stats(self, df) -> Dict[str, Any]:
        """計算 DataFrame 基本統計"""
        stats = {
            "shape": list(df.shape),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "null_counts": df.isnull().sum().to_dict()
        }

        # 數值列統計
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        if len(numeric_cols) > 0:
            stats["numeric_summary"] = df[numeric_cols].describe().to_dict()

        return stats

    def _compute_detailed_stats(self, df) -> Dict[str, Any]:
        """計算詳細統計"""
        stats = self._compute_dataframe_stats(df)

        # 添加更多統計
        stats["memory_usage"] = df.memory_usage(deep=True).sum()

        # 類別列統計
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        if len(categorical_cols) > 0:
            stats["categorical_summary"] = {
                col: df[col].value_counts().head(10).to_dict()
                for col in categorical_cols
            }

        return stats

    async def _run_statistics_code(self, path: str, format: str) -> Any:
        """使用 Code Interpreter 運行統計代碼"""
        if not self._code_interpreter:
            return None

        code = f"""
import pandas as pd

# 讀取數據
df = pd.read_{format}("{path}")

# 基本統計
summary = {{
    "shape": df.shape,
    "columns": list(df.columns),
    "dtypes": df.dtypes.to_dict(),
    "describe": df.describe().to_dict(),
    "null_counts": df.isnull().sum().to_dict()
}}

summary
"""
        return await self._code_interpreter.execute(code=code)

    async def _run_query_code(self, path: str, format: str, query: str) -> Any:
        """使用 Code Interpreter 運行查詢代碼"""
        if not self._code_interpreter:
            return None

        code = f"""
import pandas as pd

# 讀取數據
df = pd.read_{format}("{path}")

# 執行查詢 (用戶查詢: {query})
# 這裡可以根據查詢生成適當的 pandas 操作
result = df.head(10).to_dict(orient="records")

result
"""
        return await self._code_interpreter.execute(code=code)

    async def _run_visualization_code(self, path: str, format: str, chart_type: str) -> Any:
        """使用 Code Interpreter 生成視覺化"""
        if not self._code_interpreter:
            return None

        code = f"""
import pandas as pd
import matplotlib.pyplot as plt

# 讀取數據
df = pd.read_{format}("{path}")

# 生成圖表
fig, ax = plt.subplots(figsize=(10, 6))

if "{chart_type}" == "auto":
    # 自動選擇圖表類型
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    if len(numeric_cols) >= 2:
        df.plot(x=numeric_cols[0], y=numeric_cols[1], ax=ax)
    else:
        df[numeric_cols[0]].hist(ax=ax)
elif "{chart_type}" == "bar":
    df.plot.bar(ax=ax)
elif "{chart_type}" == "line":
    df.plot.line(ax=ax)
elif "{chart_type}" == "scatter":
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    if len(numeric_cols) >= 2:
        df.plot.scatter(x=numeric_cols[0], y=numeric_cols[1], ax=ax)

plt.tight_layout()
plt.savefig("/tmp/chart.png")
"Chart saved to /tmp/chart.png"
"""
        return await self._code_interpreter.execute(code=code)

    async def _query_with_llm(
        self,
        data: Dict[str, Any],
        query: str,
        request: AnalysisRequest
    ) -> str:
        """使用 LLM 回答數據問題"""
        if not self._llm_client:
            return "LLM 客戶端不可用"

        try:
            preview = json.dumps(data.get("preview", data.get("raw_data", {})), indent=2, ensure_ascii=False)[:3000]

            prompt = f"""基於以下數據回答問題 (使用{request.language}):

數據預覽:
{preview}

問題: {query}

回答:"""

            response = await self._llm_client.generate(prompt)
            return response.strip()

        except Exception as e:
            logger.error(f"LLM data query failed: {e}")
            return f"數據查詢處理失敗: {str(e)}"
