# =============================================================================
# IPA Platform - Prompt Template Service
# =============================================================================
# Sprint 3: 集成 & 可靠性 - Prompt 模板管理
#
# Prompt 模板服務實現，提供：
#   - YAML 模板文件加載和解析
#   - 模板變量替換 (Jinja2 語法)
#   - 模板分類和版本管理
#   - 模板驗證和錯誤處理
# =============================================================================

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class PromptCategory(str, Enum):
    """Prompt 模板分類."""

    IT_OPERATIONS = "it_operations"
    CUSTOMER_SERVICE = "customer_service"
    COMMON = "common"
    CUSTOM = "custom"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PromptTemplate:
    """
    Prompt 模板.

    Attributes:
        id: 模板 ID
        name: 模板名稱
        description: 模板描述
        category: 模板分類
        content: 模板內容 (支持 {{variable}} 語法)
        variables: 必需的變量列表
        default_values: 變量默認值
        version: 模板版本
        author: 模板作者
        created_at: 創建時間
        updated_at: 更新時間
        tags: 標籤列表
        metadata: 額外元數據
    """

    id: str
    name: str
    content: str
    category: PromptCategory = PromptCategory.COMMON
    description: str = ""
    variables: List[str] = field(default_factory=list)
    default_values: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    author: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化後自動提取變量."""
        if not self.variables:
            self.variables = self._extract_variables()

    def _extract_variables(self) -> List[str]:
        """
        從模板內容中提取變量.

        支持 {{variable}} 和 {{ variable }} 語法.

        Returns:
            變量名列表
        """
        # 匹配 {{variable}} 或 {{ variable }}
        pattern = r"\{\{\s*(\w+)\s*\}\}"
        matches = re.findall(pattern, self.content)
        return list(set(matches))

    def get_required_variables(self) -> Set[str]:
        """
        獲取必需變量 (沒有默認值的變量).

        Returns:
            必需變量集合
        """
        all_vars = set(self.variables)
        default_vars = set(self.default_values.keys())
        return all_vars - default_vars

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "content": self.content,
            "variables": self.variables,
            "default_values": self.default_values,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """
        從字典創建模板.

        Args:
            data: 模板數據字典

        Returns:
            PromptTemplate 實例
        """
        category = data.get("category", "common")
        if isinstance(category, str):
            try:
                category = PromptCategory(category)
            except ValueError:
                category = PromptCategory.CUSTOM

        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            content=data["content"],
            category=category,
            description=data.get("description", ""),
            variables=data.get("variables", []),
            default_values=data.get("default_values", {}),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "system"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# Exceptions
# =============================================================================


class PromptTemplateError(Exception):
    """Prompt 模板相關錯誤基類."""

    def __init__(self, message: str, code: str = "TEMPLATE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class TemplateNotFoundError(PromptTemplateError):
    """模板未找到."""

    def __init__(self, template_id: str):
        super().__init__(
            f"Template not found: {template_id}",
            code="TEMPLATE_NOT_FOUND",
        )
        self.template_id = template_id


class TemplateRenderError(PromptTemplateError):
    """模板渲染錯誤."""

    def __init__(self, template_id: str, missing_vars: List[str]):
        self.missing_vars = missing_vars
        super().__init__(
            f"Template '{template_id}' render error: missing variables {missing_vars}",
            code="TEMPLATE_RENDER_ERROR",
        )


class TemplateValidationError(PromptTemplateError):
    """模板驗證錯誤."""

    def __init__(self, message: str):
        super().__init__(message, code="TEMPLATE_VALIDATION_ERROR")


# =============================================================================
# Prompt Template Manager
# =============================================================================


class PromptTemplateManager:
    """
    Prompt 模板管理器.

    提供模板的加載、存儲、渲染和管理功能。

    Attributes:
        _templates: 模板存儲
        _templates_dir: 模板目錄路徑
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        初始化管理器.

        Args:
            templates_dir: 模板目錄路徑 (可選)
        """
        self._templates: Dict[str, PromptTemplate] = {}
        self._templates_dir = templates_dir

    # -------------------------------------------------------------------------
    # Template Loading
    # -------------------------------------------------------------------------

    def load_templates(self, directory: Optional[Path] = None) -> int:
        """
        從目錄加載所有 YAML 模板文件.

        Args:
            directory: 模板目錄 (默認使用初始化時的目錄)

        Returns:
            加載的模板數量
        """
        dir_path = directory or self._templates_dir
        if not dir_path:
            logger.warning("No templates directory specified")
            return 0

        if not dir_path.exists():
            logger.warning(f"Templates directory not found: {dir_path}")
            return 0

        count = 0
        for yaml_file in dir_path.glob("*.yaml"):
            try:
                loaded = self._load_yaml_file(yaml_file)
                count += loaded
            except Exception as e:
                logger.error(f"Error loading {yaml_file}: {e}")

        # 也加載 .yml 文件
        for yml_file in dir_path.glob("*.yml"):
            try:
                loaded = self._load_yaml_file(yml_file)
                count += loaded
            except Exception as e:
                logger.error(f"Error loading {yml_file}: {e}")

        logger.info(f"Loaded {count} templates from {dir_path}")
        return count

    def _load_yaml_file(self, file_path: Path) -> int:
        """
        加載單個 YAML 文件.

        Args:
            file_path: YAML 文件路徑

        Returns:
            加載的模板數量
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return 0

        # 支持單個模板或模板列表
        templates_data = data.get("templates", [data])
        if not isinstance(templates_data, list):
            templates_data = [templates_data]

        count = 0
        for template_data in templates_data:
            if "id" not in template_data or "content" not in template_data:
                logger.warning(f"Skipping invalid template in {file_path}")
                continue

            try:
                template = PromptTemplate.from_dict(template_data)
                self.register_template(template)
                count += 1
            except Exception as e:
                logger.error(f"Error creating template: {e}")

        return count

    def load_from_yaml(self, yaml_content: str) -> List[PromptTemplate]:
        """
        從 YAML 字符串加載模板.

        Args:
            yaml_content: YAML 內容

        Returns:
            加載的模板列表
        """
        data = yaml.safe_load(yaml_content)
        if not data:
            return []

        templates_data = data.get("templates", [data])
        if not isinstance(templates_data, list):
            templates_data = [templates_data]

        templates = []
        for template_data in templates_data:
            if "id" in template_data and "content" in template_data:
                template = PromptTemplate.from_dict(template_data)
                self.register_template(template)
                templates.append(template)

        return templates

    # -------------------------------------------------------------------------
    # Template Management
    # -------------------------------------------------------------------------

    def register_template(self, template: PromptTemplate) -> None:
        """
        註冊模板.

        Args:
            template: Prompt 模板
        """
        self._templates[template.id] = template
        logger.debug(f"Registered template: {template.id}")

    def unregister_template(self, template_id: str) -> bool:
        """
        取消註冊模板.

        Args:
            template_id: 模板 ID

        Returns:
            是否成功取消註冊
        """
        if template_id in self._templates:
            del self._templates[template_id]
            logger.debug(f"Unregistered template: {template_id}")
            return True
        return False

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        獲取模板.

        Args:
            template_id: 模板 ID

        Returns:
            PromptTemplate 或 None
        """
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: Optional[PromptCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[PromptTemplate]:
        """
        列出模板.

        Args:
            category: 按分類過濾 (可選)
            tags: 按標籤過濾 (可選)

        Returns:
            模板列表
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]

        return templates

    def search_templates(self, query: str) -> List[PromptTemplate]:
        """
        搜索模板.

        Args:
            query: 搜索關鍵字

        Returns:
            匹配的模板列表
        """
        query_lower = query.lower()
        results = []

        for template in self._templates.values():
            if (
                query_lower in template.id.lower()
                or query_lower in template.name.lower()
                or query_lower in template.description.lower()
                or any(query_lower in tag.lower() for tag in template.tags)
            ):
                results.append(template)

        return results

    # -------------------------------------------------------------------------
    # Template Rendering
    # -------------------------------------------------------------------------

    def render(
        self,
        template_id: str,
        variables: Optional[Dict[str, Any]] = None,
        strict: bool = True,
    ) -> str:
        """
        渲染模板.

        Args:
            template_id: 模板 ID
            variables: 變量值字典
            strict: 是否嚴格模式 (缺少變量時拋出錯誤)

        Returns:
            渲染後的文本

        Raises:
            TemplateNotFoundError: 模板未找到
            TemplateRenderError: 渲染錯誤 (缺少變量)
        """
        template = self.get_template(template_id)
        if not template:
            raise TemplateNotFoundError(template_id)

        return self.render_template(template, variables, strict)

    def render_template(
        self,
        template: PromptTemplate,
        variables: Optional[Dict[str, Any]] = None,
        strict: bool = True,
    ) -> str:
        """
        渲染模板對象.

        Args:
            template: 模板對象
            variables: 變量值字典
            strict: 是否嚴格模式

        Returns:
            渲染後的文本

        Raises:
            TemplateRenderError: 渲染錯誤
        """
        # 合併默認值和提供的變量
        all_vars = {**template.default_values, **(variables or {})}

        # 檢查缺少的變量
        if strict:
            required = template.get_required_variables()
            provided = set(all_vars.keys())
            missing = required - provided

            if missing:
                raise TemplateRenderError(template.id, list(missing))

        # 渲染模板
        content = template.content
        for var_name, var_value in all_vars.items():
            # 支持 {{var}} 和 {{ var }}
            patterns = [
                f"{{{{{var_name}}}}}",
                f"{{{{ {var_name} }}}}",
            ]
            for pattern in patterns:
                content = content.replace(pattern, str(var_value))

        # 處理未替換的變量 (非嚴格模式)
        if not strict:
            # 用空字符串替換未提供的變量
            content = re.sub(r"\{\{\s*\w+\s*\}\}", "", content)

        return content

    # -------------------------------------------------------------------------
    # Template Validation
    # -------------------------------------------------------------------------

    def validate_template(self, template: PromptTemplate) -> List[str]:
        """
        驗證模板.

        Args:
            template: 模板對象

        Returns:
            驗證錯誤列表 (空列表表示驗證通過)
        """
        errors = []

        # 檢查必要字段
        if not template.id:
            errors.append("Template ID is required")

        if not template.content:
            errors.append("Template content is required")

        # 檢查 ID 格式
        if template.id and not re.match(r"^[a-z][a-z0-9_]*$", template.id):
            errors.append(
                "Template ID must start with lowercase letter "
                "and contain only lowercase letters, numbers, and underscores"
            )

        # 檢查變量語法 - 查找未閉合的括號
        # 查找 {{ 後沒有 }} 的情況
        open_count = template.content.count("{{")
        close_count = template.content.count("}}")
        if open_count != close_count:
            errors.append(
                f"Mismatched variable brackets: {open_count} '{{{{' vs {close_count} '}}}}'"
            )

        return errors

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_template_count(self) -> int:
        """獲取模板總數."""
        return len(self._templates)

    def get_categories(self) -> List[PromptCategory]:
        """獲取所有使用的分類."""
        categories = set(t.category for t in self._templates.values())
        return list(categories)

    def clear(self) -> None:
        """清空所有模板."""
        self._templates.clear()
        logger.debug("Cleared all templates")
