# =============================================================================
# IPA Platform - Agent Template Domain Module
# =============================================================================
# Sprint 4: Developer Experience - Agent Template Marketplace
#
# This module provides Agent template management functionality:
#   - TemplateCategory: Template categorization
#   - TemplateParameter: Parameter definition for templates
#   - AgentTemplate: Complete template data structure
#   - TemplateService: Template loading, searching, and instantiation
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from src.domain.templates.models import (
    AgentTemplate,
    TemplateCategory,
    TemplateParameter,
    TemplateStatus,
)
from src.domain.templates.service import (
    TemplateError,
    TemplateService,
)

__all__ = [
    # Models
    "TemplateCategory",
    "TemplateStatus",
    "TemplateParameter",
    "AgentTemplate",
    # Service
    "TemplateService",
    "TemplateError",
]
