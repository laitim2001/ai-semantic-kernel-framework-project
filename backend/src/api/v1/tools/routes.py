"""
Tool management REST API endpoints

Provides APIs for listing tools, executing tools, and viewing execution history.
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from src.core.tools import get_tool_factory
from src.api.dependencies import get_current_user
from src.infrastructure.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic Schemas
class ToolMetadata(BaseModel):
    """Tool 元資料回應"""

    name: str = Field(..., description="Tool 名稱")
    description: str = Field(..., description="Tool 描述")
    parameters_schema: Dict[str, Any] = Field(..., description="參數 JSON Schema")


class ToolListResponse(BaseModel):
    """Tool 列表回應"""

    tools: List[ToolMetadata] = Field(..., description="Tool 列表")
    count: int = Field(..., description="Tool 總數")


class ToolExecutionRequest(BaseModel):
    """Tool 執行請求"""

    parameters: Dict[str, Any] = Field(default_factory=dict, description="執行參數")


class ToolExecutionResponse(BaseModel):
    """Tool 執行回應"""

    success: bool = Field(..., description="執行是否成功")
    output: Optional[Any] = Field(None, description="執行輸出")
    error_message: Optional[str] = Field(None, description="錯誤訊息")
    execution_time_ms: int = Field(..., description="執行時間 (毫秒)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="執行元資料")


class ToolExecutionHistoryItem(BaseModel):
    """Tool 執行歷史項目"""

    tool_name: str
    parameters: Dict[str, Any]
    success: bool
    execution_time_ms: int
    error_message: Optional[str] = None
    timestamp: str


class ToolExecutionHistoryResponse(BaseModel):
    """Tool 執行歷史回應"""

    history: List[ToolExecutionHistoryItem]
    count: int


class ToolStatisticsResponse(BaseModel):
    """Tool 統計回應"""

    tool_name: Optional[str] = None
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time_ms: float
    success_rate: float


# API Endpoints
@router.get(
    "/tools",
    response_model=ToolListResponse,
    summary="列出所有可用的 Tools",
    description="取得所有已註冊的 Tool 及其元資料",
)
async def list_tools(
    current_user: User = Depends(get_current_user),
) -> ToolListResponse:
    """
    列出所有可用的 Tools

    Returns:
        ToolListResponse: Tool 列表
    """
    try:
        factory = get_tool_factory()
        tools = factory.list_tools()

        return ToolListResponse(tools=tools, count=len(tools))

    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tools",
        )


@router.get(
    "/tools/{tool_name}",
    response_model=ToolMetadata,
    summary="取得 Tool 詳細資訊",
    description="取得指定 Tool 的詳細元資料",
)
async def get_tool(
    tool_name: str,
    current_user: User = Depends(get_current_user),
) -> ToolMetadata:
    """
    取得 Tool 詳細資訊

    Args:
        tool_name: Tool 名稱

    Returns:
        ToolMetadata: Tool 元資料
    """
    try:
        factory = get_tool_factory()
        tool = factory.get_tool(tool_name)

        return tool.get_metadata()

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get tool '{tool_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool",
        )


@router.post(
    "/tools/{tool_name}/execute",
    response_model=ToolExecutionResponse,
    summary="執行指定的 Tool",
    description="執行指定的 Tool 並返回結果",
    status_code=status.HTTP_200_OK,
)
async def execute_tool(
    tool_name: str,
    request: ToolExecutionRequest,
    current_user: User = Depends(get_current_user),
) -> ToolExecutionResponse:
    """
    執行指定的 Tool

    Args:
        tool_name: Tool 名稱
        request: 執行請求 (包含參數)
        current_user: 當前用戶

    Returns:
        ToolExecutionResponse: 執行結果
    """
    try:
        factory = get_tool_factory()

        # Execute tool
        result = await factory.execute_tool(tool_name, **request.parameters)

        return ToolExecutionResponse(
            success=result.success,
            output=result.output,
            error_message=result.error_message,
            execution_time_ms=result.execution_time_ms,
            metadata=result.metadata,
        )

    except ValueError as e:
        # Tool not found or parameter validation failed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to execute tool '{tool_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}",
        )


@router.get(
    "/tools/history",
    response_model=ToolExecutionHistoryResponse,
    summary="取得 Tool 執行歷史",
    description="取得所有 Tool 或指定 Tool 的執行歷史",
)
async def get_execution_history(
    tool_name: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> ToolExecutionHistoryResponse:
    """
    取得 Tool 執行歷史

    Args:
        tool_name: Tool 名稱 (optional)
        limit: 返回的最大記錄數 (default: 100)
        current_user: 當前用戶

    Returns:
        ToolExecutionHistoryResponse: 執行歷史
    """
    try:
        factory = get_tool_factory()
        history = factory.get_execution_history(tool_name=tool_name, limit=limit)

        return ToolExecutionHistoryResponse(history=history, count=len(history))

    except Exception as e:
        logger.error(f"Failed to get execution history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get execution history",
        )


@router.get(
    "/tools/statistics",
    response_model=ToolStatisticsResponse,
    summary="取得 Tool 執行統計",
    description="取得所有 Tool 或指定 Tool 的執行統計",
)
async def get_tool_statistics(
    tool_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> ToolStatisticsResponse:
    """
    取得 Tool 執行統計

    Args:
        tool_name: Tool 名稱 (optional)
        current_user: 當前用戶

    Returns:
        ToolStatisticsResponse: 統計資料
    """
    try:
        factory = get_tool_factory()
        stats = factory.get_tool_statistics(tool_name=tool_name)

        return ToolStatisticsResponse(tool_name=tool_name, **stats)

    except Exception as e:
        logger.error(f"Failed to get tool statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool statistics",
        )
