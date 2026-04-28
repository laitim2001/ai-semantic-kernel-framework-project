# =============================================================================
# IPA Platform - Agent Template Service
# =============================================================================
# Sprint 4: Developer Experience - Agent Template Marketplace
#
# Template management service providing:
#   - Template loading from YAML files
#   - Template searching and filtering
#   - Template instantiation to create Agents
#   - Template version management
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

import logging
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

import yaml

from src.domain.templates.models import (
    AgentTemplate,
    ParameterType,
    TemplateCategory,
    TemplateExample,
    TemplateParameter,
    TemplateStatus,
    TemplateVersion,
)


logger = logging.getLogger(__name__)


class TemplateError(Exception):
    """Template operation error."""

    pass


class TemplateService:
    """
    Agent Template Service.

    Manages Agent templates including loading, searching,
    filtering, and instantiation.
    """

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        agent_factory: Optional[Callable] = None,
    ):
        """
        Initialize template service.

        Args:
            templates_dir: Directory containing template YAML files
            agent_factory: Optional callable to create agents from templates
        """
        self._templates_dir = templates_dir
        self._agent_factory = agent_factory
        self._templates: Dict[str, AgentTemplate] = {}
        self._custom_templates: Dict[str, AgentTemplate] = {}

        # Event handlers
        self._on_instantiate: List[Callable] = []
        self._on_load: List[Callable] = []

    # =========================================================================
    # Template Loading
    # =========================================================================

    def load_templates(self) -> int:
        """
        Load all templates from templates directory.

        Returns number of templates loaded.
        """
        if not self._templates_dir or not self._templates_dir.exists():
            logger.warning(f"Templates directory not found: {self._templates_dir}")
            return 0

        loaded = 0
        for yaml_file in self._templates_dir.glob("*.yaml"):
            try:
                template = self._load_template_file(yaml_file)
                if template:
                    self._templates[template.id] = template
                    loaded += 1
                    logger.info(f"Loaded template: {template.id} ({template.name})")
            except Exception as e:
                logger.error(f"Failed to load template {yaml_file}: {e}")

        # Notify listeners
        for handler in self._on_load:
            try:
                handler(loaded)
            except Exception as e:
                logger.error(f"Load handler error: {e}")

        return loaded

    def _load_template_file(self, file_path: Path) -> Optional[AgentTemplate]:
        """Load template from YAML file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        return AgentTemplate.from_dict(data)

    def reload_templates(self) -> int:
        """Reload all templates from disk."""
        self._templates.clear()
        return self.load_templates()

    # =========================================================================
    # Template Registration
    # =========================================================================

    def register_template(self, template: AgentTemplate) -> None:
        """Register a custom template."""
        self._custom_templates[template.id] = template
        logger.info(f"Registered custom template: {template.id}")

    def unregister_template(self, template_id: str) -> bool:
        """Unregister a custom template."""
        if template_id in self._custom_templates:
            del self._custom_templates[template_id]
            return True
        return False

    # =========================================================================
    # Template Retrieval
    # =========================================================================

    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """Get template by ID."""
        # Check custom templates first
        if template_id in self._custom_templates:
            return self._custom_templates[template_id]
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        status: Optional[TemplateStatus] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "usage_count",
        ascending: bool = False,
    ) -> List[AgentTemplate]:
        """
        List templates with optional filtering.

        Args:
            category: Filter by category
            status: Filter by status
            search: Search in name, description, and tags
            tags: Filter by tags (any match)
            sort_by: Sort field (usage_count, rating, name, created_at)
            ascending: Sort order

        Returns:
            List of matching templates
        """
        # Combine built-in and custom templates
        all_templates = list(self._templates.values()) + list(
            self._custom_templates.values()
        )

        # Apply filters
        templates = all_templates

        if category:
            templates = [t for t in templates if t.category == category]

        if status:
            templates = [t for t in templates if t.status == status]

        if tags:
            templates = [
                t for t in templates if any(tag in t.tags for tag in tags)
            ]

        if search:
            search_lower = search.lower()
            templates = [
                t
                for t in templates
                if search_lower in t.name.lower()
                or search_lower in t.description.lower()
                or any(search_lower in tag.lower() for tag in t.tags)
            ]

        # Sort
        reverse = not ascending
        if sort_by == "usage_count":
            templates.sort(key=lambda t: t.usage_count, reverse=reverse)
        elif sort_by == "rating":
            templates.sort(key=lambda t: t.rating, reverse=reverse)
        elif sort_by == "name":
            templates.sort(key=lambda t: t.name.lower(), reverse=not reverse)
        elif sort_by == "created_at":
            templates.sort(key=lambda t: t.created_at, reverse=reverse)

        return templates

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with template counts."""
        category_counts: Dict[TemplateCategory, int] = {}

        for template in self._templates.values():
            category_counts[template.category] = (
                category_counts.get(template.category, 0) + 1
            )

        for template in self._custom_templates.values():
            category_counts[template.category] = (
                category_counts.get(template.category, 0) + 1
            )

        return [
            {
                "category": cat.value,
                "name": cat.name.replace("_", " ").title(),
                "count": count,
            }
            for cat, count in category_counts.items()
        ]

    def get_popular_templates(self, limit: int = 5) -> List[AgentTemplate]:
        """Get most popular templates by usage."""
        return self.list_templates(sort_by="usage_count", ascending=False)[:limit]

    def get_top_rated_templates(self, limit: int = 5) -> List[AgentTemplate]:
        """Get top rated templates."""
        return self.list_templates(sort_by="rating", ascending=False)[:limit]

    # =========================================================================
    # Template Instantiation
    # =========================================================================

    async def instantiate(
        self,
        template_id: str,
        name: str,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Instantiate template to create an Agent.

        Args:
            template_id: Template to instantiate
            name: Name for the new agent
            parameters: Template parameter values
            metadata: Additional agent metadata

        Returns:
            UUID of created agent

        Raises:
            TemplateError: If template not found or validation fails
        """
        template = self.get_template(template_id)
        if not template:
            raise TemplateError(f"Template not found: {template_id}")

        if template.status == TemplateStatus.DEPRECATED:
            logger.warning(f"Instantiating deprecated template: {template_id}")

        if template.status == TemplateStatus.ARCHIVED:
            raise TemplateError(f"Cannot instantiate archived template: {template_id}")

        params = parameters or {}

        # Validate parameters
        errors = template.validate_parameters(params)
        if errors:
            raise TemplateError(f"Parameter validation failed: {', '.join(errors)}")

        # Apply parameters to instructions
        instructions = template.apply_parameters(template.instructions, params)

        # Create agent config
        agent_config = {
            "name": name,
            "instructions": instructions,
            "tools": template.tools,
            "model": template.model,
            "temperature": template.temperature,
            "max_tokens": template.max_tokens,
            "metadata": {
                "template_id": template_id,
                "template_version": template.version,
                "parameters": params,
                **(metadata or {}),
            },
        }

        # Create agent using factory if available
        if self._agent_factory:
            agent_id = await self._agent_factory(agent_config)
        else:
            # Return a mock UUID for testing without agent factory
            agent_id = uuid4()

        # Update usage count
        template.increment_usage()

        # Notify listeners
        for handler in self._on_instantiate:
            try:
                handler(template_id, agent_id, params)
            except Exception as e:
                logger.error(f"Instantiate handler error: {e}")

        logger.info(f"Instantiated template {template_id} as agent {agent_id}")

        return agent_id

    # =========================================================================
    # Template Search
    # =========================================================================

    def search_templates(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search templates with relevance scoring.

        Returns templates sorted by relevance score.
        """
        all_templates = list(self._templates.values()) + list(
            self._custom_templates.values()
        )

        results = []
        query_lower = query.lower()

        for template in all_templates:
            if template.status == TemplateStatus.ARCHIVED:
                continue

            # Calculate relevance score
            score = 0.0

            # Name match (highest weight)
            name_similarity = SequenceMatcher(
                None, query_lower, template.name.lower()
            ).ratio()
            score += name_similarity * 0.4

            # Description match
            if query_lower in template.description.lower():
                score += 0.3

            # Tag match
            for tag in template.tags:
                if query_lower in tag.lower():
                    score += 0.2
                    break

            # Category match
            if query_lower in template.category.value:
                score += 0.1

            if score > 0.1:  # Minimum threshold
                results.append(
                    {
                        "template": template,
                        "score": score,
                    }
                )

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:limit]

    def find_similar_templates(
        self,
        template_id: str,
        limit: int = 5,
    ) -> List[AgentTemplate]:
        """Find templates similar to given template."""
        template = self.get_template(template_id)
        if not template:
            return []

        all_templates = list(self._templates.values()) + list(
            self._custom_templates.values()
        )

        results = []

        for other in all_templates:
            if other.id == template_id:
                continue

            score = 0.0

            # Same category
            if other.category == template.category:
                score += 0.4

            # Shared tags
            shared_tags = set(template.tags) & set(other.tags)
            if template.tags:
                score += len(shared_tags) / len(template.tags) * 0.3

            # Shared tools
            shared_tools = set(template.tools) & set(other.tools)
            if template.tools:
                score += len(shared_tools) / len(template.tools) * 0.3

            if score > 0.1:
                results.append((other, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in results[:limit]]

    # =========================================================================
    # Template Rating
    # =========================================================================

    def rate_template(
        self,
        template_id: str,
        rating: float,
        user_id: Optional[str] = None,
    ) -> float:
        """
        Rate a template.

        Args:
            template_id: Template to rate
            rating: Rating value (1-5)
            user_id: Optional user ID for tracking

        Returns:
            New average rating
        """
        template = self.get_template(template_id)
        if not template:
            raise TemplateError(f"Template not found: {template_id}")

        if not 1 <= rating <= 5:
            raise TemplateError("Rating must be between 1 and 5")

        template.add_rating(rating)
        return template.rating

    # =========================================================================
    # Template Version Management
    # =========================================================================

    def get_template_versions(
        self,
        template_id: str,
    ) -> List[TemplateVersion]:
        """Get version history for template."""
        template = self.get_template(template_id)
        if not template:
            return []

        return template.versions

    def deprecate_template(
        self,
        template_id: str,
        message: Optional[str] = None,
    ) -> bool:
        """Mark template as deprecated."""
        template = self.get_template(template_id)
        if not template:
            return False

        template.deprecate(message)
        logger.info(f"Deprecated template: {template_id}")
        return True

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def on_instantiate(self, handler: Callable) -> None:
        """Register handler for template instantiation events."""
        self._on_instantiate.append(handler)

    def on_load(self, handler: Callable) -> None:
        """Register handler for template load events."""
        self._on_load.append(handler)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get template service statistics."""
        all_templates = list(self._templates.values()) + list(
            self._custom_templates.values()
        )

        total_usage = sum(t.usage_count for t in all_templates)

        by_category = {}
        for template in all_templates:
            cat = template.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        by_status = {}
        for template in all_templates:
            status = template.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_templates": len(all_templates),
            "builtin_templates": len(self._templates),
            "custom_templates": len(self._custom_templates),
            "total_usage": total_usage,
            "by_category": by_category,
            "by_status": by_status,
        }
