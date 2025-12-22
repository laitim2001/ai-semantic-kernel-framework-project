"""
Visualization API Endpoints

提供可視化圖表生成和獲取的 API 端點。

Sprint 38: 執行結果可視化

Endpoints:
    GET /code-interpreter/visualizations/{file_id}   - 獲取生成的圖表
    POST /code-interpreter/visualizations/generate   - 生成圖表
"""

import io
import json
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.integrations.agent_framework.builders.code_interpreter import (
    CodeInterpreterAdapter,
    CodeInterpreterConfig,
)
from src.integrations.agent_framework.assistant import (
    ConfigurationError,
    FileStorageService,
    get_file_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class VisualizationRequest(BaseModel):
    """可視化生成請求。"""
    data: Dict[str, Any] = Field(
        ...,
        description="要可視化的數據"
    )
    chart_type: str = Field(
        default="bar",
        description="圖表類型: bar, line, pie, scatter, hist, box"
    )
    title: Optional[str] = Field(
        default=None,
        description="圖表標題"
    )
    x_label: Optional[str] = Field(
        default=None,
        description="X 軸標籤"
    )
    y_label: Optional[str] = Field(
        default=None,
        description="Y 軸標籤"
    )
    width: int = Field(
        default=10,
        ge=4,
        le=20,
        description="圖表寬度 (英寸)"
    )
    height: int = Field(
        default=6,
        ge=3,
        le=15,
        description="圖表高度 (英寸)"
    )
    dpi: int = Field(
        default=150,
        ge=72,
        le=300,
        description="圖表解析度"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="可選的會話 ID"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "data": {"A": 10, "B": 25, "C": 15, "D": 30},
                "chart_type": "bar",
                "title": "Sales by Category",
                "x_label": "Category",
                "y_label": "Sales",
                "width": 10,
                "height": 6,
                "dpi": 150
            }
        }


class VisualizationFileInfo(BaseModel):
    """生成的可視化文件信息。"""
    type: str = Field(..., description="文件類型")
    file_id: str = Field(..., description="文件 ID")
    filename: Optional[str] = Field(default=None, description="文件名")


class VisualizationResponse(BaseModel):
    """可視化生成響應。"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="執行信息")
    chart_type: str = Field(..., description="圖表類型")
    files: List[VisualizationFileInfo] = Field(
        default_factory=list,
        description="生成的文件"
    )
    execution_time: float = Field(..., description="執行時間")
    error: Optional[str] = Field(default=None, description="錯誤信息")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Chart generated successfully",
                "chart_type": "bar",
                "files": [
                    {
                        "type": "image",
                        "file_id": "file-abc123",
                        "filename": "chart.png"
                    }
                ],
                "execution_time": 2.5,
                "error": None
            }
        }


# =============================================================================
# Supported Chart Types
# =============================================================================

SUPPORTED_CHART_TYPES = {
    "bar": "柱狀圖",
    "barh": "水平柱狀圖",
    "line": "折線圖",
    "pie": "圓餅圖",
    "scatter": "散點圖",
    "hist": "直方圖",
    "box": "箱線圖",
}


# =============================================================================
# API Endpoints
# =============================================================================

@router.get(
    "/visualizations/types",
    summary="獲取支援的圖表類型",
    description="返回所有支援的圖表類型列表",
)
async def get_chart_types() -> Dict[str, Any]:
    """
    獲取支援的圖表類型。

    Returns:
        Dict 包含所有支援的圖表類型
    """
    return {
        "chart_types": SUPPORTED_CHART_TYPES,
        "default": "bar",
    }


@router.get(
    "/visualizations/{file_id}",
    summary="獲取可視化圖表",
    description="下載生成的可視化圖表文件",
)
async def get_visualization(
    file_id: str,
    inline: bool = True,
) -> StreamingResponse:
    """
    獲取可視化圖表。

    Args:
        file_id: 圖表文件 ID
        inline: 是否內聯顯示 (True) 或下載 (False)

    Returns:
        StreamingResponse: 圖片文件流

    Raises:
        HTTPException: 當獲取失敗時
    """
    try:
        file_service = get_file_service()
        content = file_service.download(file_id)

        # Determine content disposition
        disposition = "inline" if inline else "attachment"

        return StreamingResponse(
            io.BytesIO(content),
            media_type="image/png",
            headers={
                "Content-Disposition": f"{disposition}; filename={file_id}.png"
            },
        )

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "no such file" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visualization not found: {file_id}"
            )
        logger.error(f"Get visualization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get visualization: {str(e)}"
        )


@router.post(
    "/visualizations/generate",
    response_model=VisualizationResponse,
    summary="生成可視化圖表",
    description="使用 Code Interpreter 生成可視化圖表",
)
async def generate_visualization(
    request: VisualizationRequest,
) -> VisualizationResponse:
    """
    生成可視化圖表。

    支援的圖表類型:
    - bar: 柱狀圖
    - barh: 水平柱狀圖
    - line: 折線圖
    - pie: 圓餅圖
    - scatter: 散點圖
    - hist: 直方圖
    - box: 箱線圖

    Args:
        request: 包含數據和圖表配置

    Returns:
        VisualizationResponse: 生成結果

    Raises:
        HTTPException: 當生成失敗時
    """
    # Validate chart type
    if request.chart_type not in SUPPORTED_CHART_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chart type: {request.chart_type}. "
                   f"Supported types: {list(SUPPORTED_CHART_TYPES.keys())}"
        )

    try:
        # Create adapter
        config = CodeInterpreterConfig(timeout=60)
        adapter = CodeInterpreterAdapter(config=config)

        # Generate chart code
        code = _generate_chart_code(
            data=request.data,
            chart_type=request.chart_type,
            title=request.title,
            x_label=request.x_label,
            y_label=request.y_label,
            width=request.width,
            height=request.height,
            dpi=request.dpi,
        )

        logger.info(f"Generating {request.chart_type} chart...")

        # Execute chart generation
        result = adapter.execute(code=code)

        # Cleanup
        adapter.cleanup()

        # Convert files to response format
        files = [
            VisualizationFileInfo(
                type=f.get("type", "image"),
                file_id=f.get("file_id", ""),
                filename=f.get("filename"),
            )
            for f in result.files
        ]

        return VisualizationResponse(
            success=result.success,
            message=result.output,
            chart_type=request.chart_type,
            files=files,
            execution_time=result.execution_time,
            error=result.error,
        )

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not configured: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Visualization generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate visualization: {str(e)}"
        )


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_chart_code(
    data: Dict[str, Any],
    chart_type: str,
    title: Optional[str] = None,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    width: int = 10,
    height: int = 6,
    dpi: int = 150,
) -> str:
    """
    生成圖表繪製代碼。

    Args:
        data: 圖表數據
        chart_type: 圖表類型
        title: 標題
        x_label: X 軸標籤
        y_label: Y 軸標籤
        width: 寬度
        height: 高度
        dpi: 解析度

    Returns:
        Python 代碼字符串
    """
    data_json = json.dumps(data)
    title_str = title or "Generated Chart"
    x_label_str = x_label or ""
    y_label_str = y_label or ""

    # Base imports and data setup
    code = f"""
import matplotlib.pyplot as plt
import json

# Setup Chinese font support
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Data
data = {data_json}
labels = list(data.keys())
values = list(data.values())

# Create figure
fig, ax = plt.subplots(figsize=({width}, {height}))
"""

    # Chart-specific code
    if chart_type == "bar":
        code += """
ax.bar(labels, values, color='steelblue', edgecolor='black')
"""
    elif chart_type == "barh":
        code += """
ax.barh(labels, values, color='steelblue', edgecolor='black')
"""
    elif chart_type == "line":
        code += """
ax.plot(labels, values, marker='o', linewidth=2, markersize=8, color='steelblue')
ax.fill_between(labels, values, alpha=0.2)
"""
    elif chart_type == "pie":
        code += """
ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
ax.axis('equal')
"""
    elif chart_type == "scatter":
        code += """
# For scatter, interpret values as y coordinates
x_vals = list(range(len(values)))
ax.scatter(x_vals, values, s=100, c='steelblue', edgecolors='black')
ax.set_xticks(x_vals)
ax.set_xticklabels(labels)
"""
    elif chart_type == "hist":
        code += """
# For histogram, use values directly
ax.hist(values, bins='auto', color='steelblue', edgecolor='black')
"""
    elif chart_type == "box":
        code += """
# For box plot, group data by labels
ax.boxplot([values], labels=['Data'])
"""

    # Add labels and title
    code += f"""
# Labels and title
ax.set_title('{title_str}', fontsize=14, fontweight='bold')
"""

    if chart_type not in ["pie"]:
        code += f"""
ax.set_xlabel('{x_label_str}', fontsize=12)
ax.set_ylabel('{y_label_str}', fontsize=12)
"""

    # Finalize
    code += f"""
# Layout and save
plt.tight_layout()
plt.savefig('chart.png', dpi={dpi}, bbox_inches='tight')
print('Chart generated successfully: chart.png')
"""

    return code
