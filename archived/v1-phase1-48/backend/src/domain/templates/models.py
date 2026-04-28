# =============================================================================
# IPA Platform - Agent Template Models
# =============================================================================
# Sprint 4: Developer Experience - Agent Template Marketplace
#
# Data models for Agent template management:
#   - TemplateCategory: Categories for organizing templates
#   - TemplateStatus: Template lifecycle status
#   - TemplateParameter: Parameter definitions with validation
#   - AgentTemplate: Complete template definition
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class TemplateCategory(str, Enum):
    """Template category for organization."""

    IT_OPERATIONS = "it_operations"
    CUSTOMER_SERVICE = "customer_service"
    MONITORING = "monitoring"
    APPROVAL = "approval"
    REPORTING = "reporting"
    KNOWLEDGE = "knowledge"
    CUSTOM = "custom"


class TemplateStatus(str, Enum):
    """Template lifecycle status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ParameterType(str, Enum):
    """Parameter data types."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"


@dataclass
class TemplateParameter:
    """
    Template parameter definition.

    Defines a configurable parameter for template instantiation,
    including type, validation rules, and default values.
    """

    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    options: Optional[List[Any]] = None  # Allowed values for enum-like params
    min_value: Optional[float] = None  # For numeric types
    max_value: Optional[float] = None  # For numeric types
    pattern: Optional[str] = None  # Regex pattern for string validation

    def validate(self, value: Any) -> bool:
        """Validate a value against this parameter definition."""
        if value is None:
            return not self.required or self.default is not None

        # Type validation
        if self.type == ParameterType.STRING:
            if not isinstance(value, str):
                return False
            if self.pattern:
                import re

                if not re.match(self.pattern, value):
                    return False

        elif self.type == ParameterType.NUMBER:
            if not isinstance(value, (int, float)):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False

        elif self.type == ParameterType.INTEGER:
            if not isinstance(value, int):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False

        elif self.type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                return False

        elif self.type == ParameterType.LIST:
            if not isinstance(value, list):
                return False

        elif self.type == ParameterType.OBJECT:
            if not isinstance(value, dict):
                return False

        # Options validation
        if self.options is not None and value not in self.options:
            return False

        return True

    def get_effective_value(self, value: Optional[Any] = None) -> Any:
        """Get effective value (provided or default)."""
        if value is not None:
            return value
        return self.default

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "options": self.options,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "pattern": self.pattern,
        }


@dataclass
class TemplateExample:
    """Example input/output for template demonstration."""

    input: str
    output: Dict[str, Any]
    description: Optional[str] = None


@dataclass
class TemplateVersion:
    """Template version information."""

    version: str
    created_at: datetime
    changelog: Optional[str] = None
    deprecated: bool = False
    deprecation_message: Optional[str] = None


@dataclass
class AgentTemplate:
    """
    Complete Agent template definition.

    Templates define reusable Agent configurations that can be
    instantiated with custom parameters.
    """

    # Identity
    id: str
    name: str
    description: str

    # Classification
    category: TemplateCategory
    status: TemplateStatus = TemplateStatus.PUBLISHED

    # Versioning
    version: str = "1.0.0"
    author: str = "IPA Platform Team"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Agent configuration
    instructions: str = ""
    tools: List[str] = field(default_factory=list)
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Parameters
    parameters: List[TemplateParameter] = field(default_factory=list)

    # Metadata
    usage_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    tags: List[str] = field(default_factory=list)

    # Examples
    examples: List[TemplateExample] = field(default_factory=list)

    # Version history
    versions: List[TemplateVersion] = field(default_factory=list)

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate provided parameters against template definition.

        Returns list of validation error messages.
        """
        errors = []

        for param_def in self.parameters:
            value = params.get(param_def.name)

            # Check required parameters
            if param_def.required and value is None and param_def.default is None:
                errors.append(f"Missing required parameter: {param_def.name}")
                continue

            # Validate value
            if value is not None and not param_def.validate(value):
                errors.append(
                    f"Invalid value for parameter {param_def.name}: "
                    f"expected {param_def.type.value}, got {type(value).__name__}"
                )

        return errors

    def apply_parameters(
        self,
        instructions: str,
        params: Dict[str, Any],
    ) -> str:
        """
        Apply parameters to instruction template.

        Supports Jinja2-style variable substitution: {{variable_name}}
        """
        result = instructions

        for param_def in self.parameters:
            value = param_def.get_effective_value(params.get(param_def.name))
            if value is not None:
                # Support both {{var}} and $var syntax
                result = result.replace(f"{{{{{param_def.name}}}}}", str(value))
                result = result.replace(f"${param_def.name}", str(value))

        return result

    def get_parameter(self, name: str) -> Optional[TemplateParameter]:
        """Get parameter definition by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def increment_usage(self) -> None:
        """Increment usage counter."""
        self.usage_count += 1

    def add_rating(self, rating: float) -> None:
        """Add a rating (1-5 scale)."""
        if 1 <= rating <= 5:
            total = self.rating * self.rating_count + rating
            self.rating_count += 1
            self.rating = total / self.rating_count

    def deprecate(self, message: Optional[str] = None) -> None:
        """Mark template as deprecated."""
        self.status = TemplateStatus.DEPRECATED
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "instructions": self.instructions,
            "tools": self.tools,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "parameters": [p.to_dict() for p in self.parameters],
            "usage_count": self.usage_count,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "tags": self.tags,
            "examples": [
                {
                    "input": e.input,
                    "output": e.output,
                    "description": e.description,
                }
                for e in self.examples
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Create template from dictionary."""
        # Parse parameters
        parameters = []
        for p in data.get("parameters", []):
            parameters.append(
                TemplateParameter(
                    name=p["name"],
                    type=ParameterType(p.get("type", "string")),
                    description=p.get("description", ""),
                    required=p.get("required", True),
                    default=p.get("default"),
                    options=p.get("options"),
                    min_value=p.get("min_value"),
                    max_value=p.get("max_value"),
                    pattern=p.get("pattern"),
                )
            )

        # Parse examples
        examples = []
        for e in data.get("examples", []):
            examples.append(
                TemplateExample(
                    input=e.get("input", ""),
                    output=e.get("output", {}),
                    description=e.get("description"),
                )
            )

        # Parse created_at
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        # Parse updated_at
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            category=TemplateCategory(data.get("category", "custom")),
            status=TemplateStatus(data.get("status", "published")),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "IPA Platform Team"),
            created_at=created_at,
            updated_at=updated_at,
            instructions=data.get("instructions", ""),
            tools=data.get("tools", []),
            model=data.get("model", "gpt-4"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            parameters=parameters,
            usage_count=data.get("usage_count", 0),
            rating=data.get("rating", 0.0),
            rating_count=data.get("rating_count", 0),
            tags=data.get("tags", []),
            examples=examples,
        )
