# =============================================================================
# IPA Platform - Prompts Domain Module
# =============================================================================
# Sprint 3: 集成 & 可靠性 - Prompt 模板管理
#
# 提供 Prompt 模板管理功能：
#   - YAML 模板加載和解析
#   - 模板變量替換
#   - 模板版本管理
# =============================================================================

from src.domain.prompts.template import (
    PromptCategory,
    PromptTemplate,
    PromptTemplateError,
    PromptTemplateManager,
    TemplateNotFoundError,
    TemplateRenderError,
    TemplateValidationError,
)

__all__ = [
    "PromptCategory",
    "PromptTemplate",
    "PromptTemplateManager",
    "PromptTemplateError",
    "TemplateNotFoundError",
    "TemplateRenderError",
    "TemplateValidationError",
]
