# =============================================================================
# IPA Platform - Prompts API Schemas
# =============================================================================
# Sprint 3: 集成 & 可靠性 - Prompt 模板管理
#
# Pydantic schemas for Prompts API endpoints.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================


class RenderRequest(BaseModel):
    """渲染模板請求."""

    variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="模板變量值"
    )
    strict: bool = Field(
        True,
        description="是否嚴格模式 (缺少變量時拋出錯誤)"
    )


class TemplateCreateRequest(BaseModel):
    """創建模板請求."""

    id: str = Field(..., min_length=1, max_length=100, description="模板 ID")
    name: str = Field(..., min_length=1, max_length=200, description="模板名稱")
    content: str = Field(..., min_length=1, description="模板內容")
    category: str = Field("common", description="模板分類")
    description: str = Field("", description="模板描述")
    default_values: Dict[str, Any] = Field(
        default_factory=dict,
        description="變量默認值"
    )
    version: str = Field("1.0.0", description="模板版本")
    author: str = Field("user", description="模板作者")
    tags: List[str] = Field(default_factory=list, description="標籤列表")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="額外元數據"
    )


class TemplateUpdateRequest(BaseModel):
    """更新模板請求."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    default_values: Optional[Dict[str, Any]] = Field(None)
    version: Optional[str] = Field(None)
    tags: Optional[List[str]] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)


# =============================================================================
# Response Schemas
# =============================================================================


class PromptTemplateResponse(BaseModel):
    """模板響應."""

    id: str = Field(..., description="模板 ID")
    name: str = Field(..., description="模板名稱")
    description: str = Field(..., description="模板描述")
    category: str = Field(..., description="模板分類")
    content: str = Field(..., description="模板內容")
    variables: List[str] = Field(..., description="變量列表")
    default_values: Dict[str, Any] = Field(..., description="默認值")
    version: str = Field(..., description="模板版本")
    author: str = Field(..., description="模板作者")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")
    tags: List[str] = Field(..., description="標籤列表")
    metadata: Dict[str, Any] = Field(..., description="額外元數據")


class PromptTemplateListResponse(BaseModel):
    """模板列表響應."""

    items: List[PromptTemplateResponse] = Field(..., description="模板列表")
    total: int = Field(..., description="總數")


class RenderResponse(BaseModel):
    """渲染響應."""

    template_id: str = Field(..., description="模板 ID")
    rendered_content: str = Field(..., description="渲染後的內容")
    variables_used: Dict[str, Any] = Field(..., description="使用的變量")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="渲染時間"
    )


class TemplateValidationResponse(BaseModel):
    """模板驗證響應."""

    valid: bool = Field(..., description="是否有效")
    errors: List[str] = Field(default_factory=list, description="錯誤列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")


class CategoryResponse(BaseModel):
    """分類響應."""

    categories: List[str] = Field(..., description="分類列表")
    count: Dict[str, int] = Field(..., description="每個分類的模板數量")


class ErrorResponse(BaseModel):
    """錯誤響應."""

    success: bool = Field(False, description="是否成功")
    error: str = Field(..., description="錯誤信息")
    error_code: str = Field(..., description="錯誤代碼")
    template_id: Optional[str] = Field(None, description="模板 ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="時間戳"
    )
