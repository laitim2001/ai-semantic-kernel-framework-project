# =============================================================================
# IPA Platform - Prompts API Routes
# =============================================================================
# Sprint 3: 集成 & 可靠性 - Prompt 模板管理
#
# REST API endpoints for Prompt template management:
#   - GET /prompts/templates - 列出模板
#   - GET /prompts/templates/{id} - 獲取模板
#   - POST /prompts/templates - 創建模板
#   - PUT /prompts/templates/{id} - 更新模板
#   - DELETE /prompts/templates/{id} - 刪除模板
#   - POST /prompts/templates/{id}/render - 渲染模板
#   - POST /prompts/templates/validate - 驗證模板
#   - GET /prompts/categories - 列出分類
#   - GET /prompts/search - 搜索模板
# =============================================================================

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.v1.prompts.schemas import (
    CategoryResponse,
    ErrorResponse,
    PromptTemplateListResponse,
    PromptTemplateResponse,
    RenderRequest,
    RenderResponse,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplateValidationResponse,
)
from src.domain.prompts.template import (
    PromptCategory,
    PromptTemplate,
    PromptTemplateManager,
    TemplateNotFoundError,
    TemplateRenderError,
    TemplateValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/prompts",
    tags=["prompts"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Dependency Injection
# =============================================================================

# Global manager instance (in production, use proper DI)
_prompt_manager: Optional[PromptTemplateManager] = None


def get_prompt_manager() -> PromptTemplateManager:
    """Get or create prompt template manager."""
    global _prompt_manager

    if _prompt_manager is None:
        # 默認模板目錄
        templates_dir = Path(__file__).parent.parent.parent.parent.parent / "prompts"
        _prompt_manager = PromptTemplateManager(templates_dir=templates_dir)

        # 嘗試加載模板
        if templates_dir.exists():
            _prompt_manager.load_templates()
            logger.info(f"Loaded {_prompt_manager.get_template_count()} templates")

    return _prompt_manager


# =============================================================================
# Template Endpoints
# =============================================================================


@router.get(
    "/templates",
    response_model=PromptTemplateListResponse,
    summary="列出模板",
    description="獲取所有 Prompt 模板列表",
)
async def list_templates(
    category: Optional[str] = Query(None, description="按分類過濾"),
    tags: Optional[str] = Query(None, description="按標籤過濾 (逗號分隔)"),
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> PromptTemplateListResponse:
    """列出所有模板."""
    # 解析分類
    category_filter = None
    if category:
        try:
            category_filter = PromptCategory(category)
        except ValueError:
            pass

    # 解析標籤
    tags_filter = None
    if tags:
        tags_filter = [t.strip() for t in tags.split(",")]

    templates = manager.list_templates(category=category_filter, tags=tags_filter)

    return PromptTemplateListResponse(
        items=[
            PromptTemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                category=t.category.value,
                content=t.content,
                variables=t.variables,
                default_values=t.default_values,
                version=t.version,
                author=t.author,
                created_at=t.created_at,
                updated_at=t.updated_at,
                tags=t.tags,
                metadata=t.metadata,
            )
            for t in templates
        ],
        total=len(templates),
    )


@router.get(
    "/templates/{template_id}",
    response_model=PromptTemplateResponse,
    summary="獲取模板",
    description="獲取指定 ID 的模板",
)
async def get_template(
    template_id: str,
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> PromptTemplateResponse:
    """獲取模板."""
    template = manager.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )

    return PromptTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category.value,
        content=template.content,
        variables=template.variables,
        default_values=template.default_values,
        version=template.version,
        author=template.author,
        created_at=template.created_at,
        updated_at=template.updated_at,
        tags=template.tags,
        metadata=template.metadata,
    )


@router.post(
    "/templates",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="創建模板",
    description="創建新的 Prompt 模板",
)
async def create_template(
    request: TemplateCreateRequest,
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> PromptTemplateResponse:
    """創建模板."""
    # 檢查是否已存在
    if manager.get_template(request.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template already exists: {request.id}",
        )

    # 解析分類
    try:
        category = PromptCategory(request.category)
    except ValueError:
        category = PromptCategory.CUSTOM

    # 創建模板
    template = PromptTemplate(
        id=request.id,
        name=request.name,
        content=request.content,
        category=category,
        description=request.description,
        default_values=request.default_values,
        version=request.version,
        author=request.author,
        tags=request.tags,
        metadata=request.metadata,
    )

    # 驗證模板
    errors = manager.validate_template(template)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors},
        )

    # 註冊模板
    manager.register_template(template)

    return PromptTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category.value,
        content=template.content,
        variables=template.variables,
        default_values=template.default_values,
        version=template.version,
        author=template.author,
        created_at=template.created_at,
        updated_at=template.updated_at,
        tags=template.tags,
        metadata=template.metadata,
    )


@router.put(
    "/templates/{template_id}",
    response_model=PromptTemplateResponse,
    summary="更新模板",
    description="更新指定 ID 的模板",
)
async def update_template(
    template_id: str,
    request: TemplateUpdateRequest,
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> PromptTemplateResponse:
    """更新模板."""
    template = manager.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )

    # 更新字段
    if request.name is not None:
        template.name = request.name
    if request.content is not None:
        template.content = request.content
        template.variables = template._extract_variables()
    if request.category is not None:
        try:
            template.category = PromptCategory(request.category)
        except ValueError:
            template.category = PromptCategory.CUSTOM
    if request.description is not None:
        template.description = request.description
    if request.default_values is not None:
        template.default_values = request.default_values
    if request.version is not None:
        template.version = request.version
    if request.tags is not None:
        template.tags = request.tags
    if request.metadata is not None:
        template.metadata = request.metadata

    template.updated_at = datetime.utcnow()

    return PromptTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category.value,
        content=template.content,
        variables=template.variables,
        default_values=template.default_values,
        version=template.version,
        author=template.author,
        created_at=template.created_at,
        updated_at=template.updated_at,
        tags=template.tags,
        metadata=template.metadata,
    )


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除模板",
    description="刪除指定 ID 的模板",
)
async def delete_template(
    template_id: str,
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> None:
    """刪除模板."""
    if not manager.unregister_template(template_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )


# =============================================================================
# Render Endpoints
# =============================================================================


@router.post(
    "/templates/{template_id}/render",
    response_model=RenderResponse,
    summary="渲染模板",
    description="使用變量渲染指定模板",
)
async def render_template(
    template_id: str,
    request: RenderRequest,
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> RenderResponse:
    """渲染模板."""
    try:
        rendered = manager.render(
            template_id=template_id,
            variables=request.variables,
            strict=request.strict,
        )

        template = manager.get_template(template_id)

        return RenderResponse(
            template_id=template_id,
            rendered_content=rendered,
            variables_used={
                **template.default_values,
                **request.variables,
            } if template else request.variables,
        )

    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )

    except TemplateRenderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": str(e),
                "error_code": e.code,
                "missing_variables": e.missing_vars,
            },
        )


# =============================================================================
# Utility Endpoints
# =============================================================================


@router.post(
    "/templates/validate",
    response_model=TemplateValidationResponse,
    summary="驗證模板",
    description="驗證模板語法和結構",
)
async def validate_template(
    request: TemplateCreateRequest,
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> TemplateValidationResponse:
    """驗證模板."""
    # 解析分類
    try:
        category = PromptCategory(request.category)
    except ValueError:
        category = PromptCategory.CUSTOM

    # 創建臨時模板進行驗證
    template = PromptTemplate(
        id=request.id,
        name=request.name,
        content=request.content,
        category=category,
        description=request.description,
        default_values=request.default_values,
        version=request.version,
        author=request.author,
        tags=request.tags,
        metadata=request.metadata,
    )

    errors = manager.validate_template(template)

    # 檢查警告
    warnings = []
    if not template.description:
        warnings.append("Template description is empty")
    if not template.tags:
        warnings.append("Template has no tags")
    if len(template.variables) == 0:
        warnings.append("Template has no variables")

    return TemplateValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.get(
    "/categories",
    response_model=CategoryResponse,
    summary="列出分類",
    description="獲取所有模板分類",
)
async def list_categories(
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> CategoryResponse:
    """列出所有分類."""
    categories = manager.get_categories()
    all_templates = manager.list_templates()

    # 計算每個分類的數量
    count = {}
    for cat in PromptCategory:
        count[cat.value] = sum(
            1 for t in all_templates if t.category == cat
        )

    return CategoryResponse(
        categories=[c.value for c in categories],
        count=count,
    )


@router.get(
    "/search",
    response_model=PromptTemplateListResponse,
    summary="搜索模板",
    description="搜索模板",
)
async def search_templates(
    q: str = Query(..., min_length=1, description="搜索關鍵字"),
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> PromptTemplateListResponse:
    """搜索模板."""
    templates = manager.search_templates(q)

    return PromptTemplateListResponse(
        items=[
            PromptTemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                category=t.category.value,
                content=t.content,
                variables=t.variables,
                default_values=t.default_values,
                version=t.version,
                author=t.author,
                created_at=t.created_at,
                updated_at=t.updated_at,
                tags=t.tags,
                metadata=t.metadata,
            )
            for t in templates
        ],
        total=len(templates),
    )


@router.post(
    "/reload",
    summary="重新加載模板",
    description="從文件系統重新加載所有模板",
)
async def reload_templates(
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> dict:
    """重新加載模板."""
    manager.clear()
    count = manager.load_templates()

    return {
        "success": True,
        "loaded_count": count,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health",
    summary="健康檢查",
    description="Prompt 服務健康檢查",
)
async def health_check(
    manager: PromptTemplateManager = Depends(get_prompt_manager),
) -> dict:
    """健康檢查."""
    return {
        "status": "healthy",
        "service": "prompts",
        "template_count": manager.get_template_count(),
        "categories": [c.value for c in manager.get_categories()],
        "timestamp": datetime.utcnow().isoformat(),
    }
