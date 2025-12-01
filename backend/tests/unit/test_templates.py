# =============================================================================
# IPA Platform - Template Service Unit Tests
# =============================================================================
# Sprint 4: Developer Experience - Agent Template Marketplace
#
# Comprehensive tests for template management functionality:
#   - Template model operations
#   - Template service CRUD
#   - Template search and filtering
#   - Template instantiation
#   - API endpoint validation
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from uuid import uuid4

import pytest
import yaml
from fastapi.testclient import TestClient

from src.domain.templates.models import (
    AgentTemplate,
    ParameterType,
    TemplateCategory,
    TemplateExample,
    TemplateParameter,
    TemplateStatus,
)
from src.domain.templates.service import TemplateError, TemplateService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_parameter():
    """Create a sample template parameter."""
    return TemplateParameter(
        name="threshold",
        type=ParameterType.NUMBER,
        description="Confidence threshold",
        required=False,
        default=0.8,
        min_value=0.0,
        max_value=1.0,
    )


@pytest.fixture
def sample_template():
    """Create a sample agent template."""
    return AgentTemplate(
        id="test_agent",
        name="Test Agent",
        description="A test agent template",
        category=TemplateCategory.IT_OPERATIONS,
        status=TemplateStatus.PUBLISHED,
        version="1.0.0",
        author="Test Author",
        instructions="You are a test agent. Threshold: {{threshold}}",
        tools=["tool1", "tool2"],
        model="gpt-4",
        temperature=0.7,
        max_tokens=2048,
        parameters=[
            TemplateParameter(
                name="threshold",
                type=ParameterType.NUMBER,
                description="Threshold value",
                required=False,
                default=0.8,
                min_value=0.0,
                max_value=1.0,
            ),
            TemplateParameter(
                name="mode",
                type=ParameterType.STRING,
                description="Operation mode",
                required=True,
                options=["fast", "accurate"],
            ),
        ],
        tags=["test", "example"],
        examples=[
            TemplateExample(
                input="Test input",
                output={"result": "success"},
                description="Test example",
            ),
        ],
    )


@pytest.fixture
def template_service(tmp_path):
    """Create a template service with test templates."""
    # Create test templates directory
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Create a test template YAML
    test_template = {
        "id": "yaml_test_agent",
        "name": "YAML Test Agent",
        "description": "Agent loaded from YAML",
        "category": "it_operations",
        "status": "published",
        "version": "1.0.0",
        "author": "Test Author",
        "instructions": "Test instructions with {{param1}}",
        "tools": ["tool1"],
        "parameters": [
            {
                "name": "param1",
                "type": "string",
                "description": "Test param",
                "required": False,
                "default": "default_value",
            },
        ],
        "tags": ["yaml", "test"],
        "examples": [],
    }

    with open(templates_dir / "test_agent.yaml", "w", encoding="utf-8") as f:
        yaml.dump(test_template, f)

    service = TemplateService(templates_dir=templates_dir)
    service.load_templates()

    return service


# =============================================================================
# TemplateParameter Tests
# =============================================================================


class TestTemplateParameter:
    """Tests for TemplateParameter class."""

    def test_create_parameter(self, sample_parameter):
        """Test parameter creation."""
        assert sample_parameter.name == "threshold"
        assert sample_parameter.type == ParameterType.NUMBER
        assert sample_parameter.default == 0.8

    def test_validate_number_parameter(self, sample_parameter):
        """Test number parameter validation."""
        assert sample_parameter.validate(0.5) is True
        assert sample_parameter.validate(0.0) is True
        assert sample_parameter.validate(1.0) is True
        assert sample_parameter.validate(-0.1) is False  # Below min
        assert sample_parameter.validate(1.5) is False  # Above max
        assert sample_parameter.validate("invalid") is False  # Wrong type

    def test_validate_string_parameter(self):
        """Test string parameter validation."""
        param = TemplateParameter(
            name="mode",
            type=ParameterType.STRING,
            description="Mode",
            options=["fast", "slow"],
        )
        assert param.validate("fast") is True
        assert param.validate("slow") is True
        assert param.validate("medium") is False  # Not in options

    def test_validate_boolean_parameter(self):
        """Test boolean parameter validation."""
        param = TemplateParameter(
            name="enabled",
            type=ParameterType.BOOLEAN,
            description="Enabled flag",
        )
        assert param.validate(True) is True
        assert param.validate(False) is True
        assert param.validate("true") is False  # String, not bool

    def test_validate_pattern_parameter(self):
        """Test pattern validation for string parameter."""
        param = TemplateParameter(
            name="email",
            type=ParameterType.STRING,
            description="Email address",
            pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
        )
        assert param.validate("test@example.com") is True
        assert param.validate("invalid-email") is False

    def test_validate_required_parameter(self):
        """Test required parameter validation."""
        param = TemplateParameter(
            name="required_param",
            type=ParameterType.STRING,
            description="Required",
            required=True,
        )
        assert param.validate(None) is False
        assert param.validate("value") is True

    def test_get_effective_value(self, sample_parameter):
        """Test getting effective value."""
        assert sample_parameter.get_effective_value(0.5) == 0.5
        assert sample_parameter.get_effective_value(None) == 0.8  # Default
        assert sample_parameter.get_effective_value() == 0.8

    def test_parameter_to_dict(self, sample_parameter):
        """Test parameter serialization."""
        data = sample_parameter.to_dict()
        assert data["name"] == "threshold"
        assert data["type"] == "number"
        assert data["default"] == 0.8


# =============================================================================
# AgentTemplate Tests
# =============================================================================


class TestAgentTemplate:
    """Tests for AgentTemplate class."""

    def test_create_template(self, sample_template):
        """Test template creation."""
        assert sample_template.id == "test_agent"
        assert sample_template.name == "Test Agent"
        assert sample_template.category == TemplateCategory.IT_OPERATIONS
        assert len(sample_template.parameters) == 2
        assert len(sample_template.tools) == 2

    def test_validate_parameters_success(self, sample_template):
        """Test successful parameter validation."""
        errors = sample_template.validate_parameters({
            "threshold": 0.9,
            "mode": "fast",
        })
        assert len(errors) == 0

    def test_validate_parameters_missing_required(self, sample_template):
        """Test validation with missing required parameter."""
        errors = sample_template.validate_parameters({
            "threshold": 0.9,
            # Missing 'mode' which is required
        })
        assert len(errors) == 1
        assert "mode" in errors[0]

    def test_validate_parameters_invalid_value(self, sample_template):
        """Test validation with invalid parameter value."""
        errors = sample_template.validate_parameters({
            "threshold": 1.5,  # Above max
            "mode": "fast",
        })
        assert len(errors) == 1
        assert "threshold" in errors[0]

    def test_apply_parameters(self, sample_template):
        """Test parameter application to instructions."""
        result = sample_template.apply_parameters(
            sample_template.instructions,
            {"threshold": 0.9},
        )
        assert "0.9" in result
        assert "{{threshold}}" not in result

    def test_apply_parameters_with_default(self, sample_template):
        """Test parameter application with default values."""
        result = sample_template.apply_parameters(
            sample_template.instructions,
            {},  # Use defaults
        )
        assert "0.8" in result  # Default value

    def test_get_parameter(self, sample_template):
        """Test getting parameter by name."""
        param = sample_template.get_parameter("threshold")
        assert param is not None
        assert param.name == "threshold"

        # Non-existent parameter
        assert sample_template.get_parameter("nonexistent") is None

    def test_increment_usage(self, sample_template):
        """Test usage counter increment."""
        initial = sample_template.usage_count
        sample_template.increment_usage()
        assert sample_template.usage_count == initial + 1

    def test_add_rating(self, sample_template):
        """Test adding ratings."""
        sample_template.add_rating(5.0)
        assert sample_template.rating == 5.0
        assert sample_template.rating_count == 1

        sample_template.add_rating(3.0)
        assert sample_template.rating == 4.0  # Average of 5 and 3
        assert sample_template.rating_count == 2

    def test_add_rating_out_of_range(self, sample_template):
        """Test rating outside valid range."""
        initial_rating = sample_template.rating
        sample_template.add_rating(6.0)  # Out of range
        assert sample_template.rating == initial_rating  # Unchanged

    def test_deprecate_template(self, sample_template):
        """Test template deprecation."""
        sample_template.deprecate("No longer supported")
        assert sample_template.status == TemplateStatus.DEPRECATED
        assert sample_template.updated_at is not None

    def test_template_to_dict(self, sample_template):
        """Test template serialization."""
        data = sample_template.to_dict()
        assert data["id"] == "test_agent"
        assert data["category"] == "it_operations"
        assert len(data["parameters"]) == 2
        assert len(data["examples"]) == 1

    def test_template_from_dict(self):
        """Test template deserialization."""
        data = {
            "id": "from_dict_agent",
            "name": "From Dict Agent",
            "description": "Created from dict",
            "category": "customer_service",
            "status": "published",
            "version": "2.0.0",
            "author": "Test",
            "instructions": "Test instructions",
            "tools": ["tool1"],
            "parameters": [
                {
                    "name": "param1",
                    "type": "string",
                    "description": "A param",
                }
            ],
            "tags": ["dict", "test"],
        }

        template = AgentTemplate.from_dict(data)
        assert template.id == "from_dict_agent"
        assert template.category == TemplateCategory.CUSTOMER_SERVICE
        assert len(template.parameters) == 1


# =============================================================================
# TemplateService Tests
# =============================================================================


class TestTemplateService:
    """Tests for TemplateService class."""

    def test_load_templates(self, template_service):
        """Test loading templates from directory."""
        stats = template_service.get_statistics()
        assert stats["builtin_templates"] > 0

    def test_get_template(self, template_service):
        """Test getting template by ID."""
        template = template_service.get_template("yaml_test_agent")
        assert template is not None
        assert template.name == "YAML Test Agent"

    def test_get_template_not_found(self, template_service):
        """Test getting non-existent template."""
        template = template_service.get_template("nonexistent")
        assert template is None

    def test_list_templates(self, template_service):
        """Test listing all templates."""
        templates = template_service.list_templates()
        assert len(templates) >= 1

    def test_list_templates_by_category(self, template_service):
        """Test filtering templates by category."""
        templates = template_service.list_templates(
            category=TemplateCategory.IT_OPERATIONS
        )
        for t in templates:
            assert t.category == TemplateCategory.IT_OPERATIONS

    def test_list_templates_by_search(self, template_service):
        """Test searching templates."""
        templates = template_service.list_templates(search="YAML")
        assert len(templates) >= 1
        assert any("YAML" in t.name for t in templates)

    def test_list_templates_by_tags(self, template_service):
        """Test filtering templates by tags."""
        templates = template_service.list_templates(tags=["yaml"])
        assert len(templates) >= 1

    def test_list_templates_sorted(self, template_service):
        """Test template sorting."""
        # Add usage to a template
        template = template_service.get_template("yaml_test_agent")
        template.increment_usage()
        template.increment_usage()

        templates = template_service.list_templates(
            sort_by="usage_count",
            ascending=False,
        )
        if len(templates) > 1:
            assert templates[0].usage_count >= templates[-1].usage_count

    def test_register_custom_template(self, template_service, sample_template):
        """Test registering custom template."""
        template_service.register_template(sample_template)

        template = template_service.get_template("test_agent")
        assert template is not None
        assert template.name == "Test Agent"

    def test_unregister_custom_template(self, template_service, sample_template):
        """Test unregistering custom template."""
        template_service.register_template(sample_template)
        assert template_service.unregister_template("test_agent") is True
        assert template_service.get_template("test_agent") is None

    def test_search_templates(self, template_service):
        """Test template search with scoring."""
        results = template_service.search_templates("YAML Test")
        assert len(results) >= 1
        assert results[0]["score"] > 0

    def test_find_similar_templates(self, template_service, sample_template):
        """Test finding similar templates."""
        template_service.register_template(sample_template)

        similar = template_service.find_similar_templates("yaml_test_agent")
        # Should find the test_agent as it's in the same category
        assert isinstance(similar, list)

    def test_get_categories(self, template_service):
        """Test getting categories with counts."""
        categories = template_service.get_categories()
        assert len(categories) >= 1
        assert all("category" in c and "count" in c for c in categories)

    def test_get_popular_templates(self, template_service):
        """Test getting popular templates."""
        # Add some usage
        template = template_service.get_template("yaml_test_agent")
        for _ in range(5):
            template.increment_usage()

        popular = template_service.get_popular_templates(limit=5)
        assert len(popular) >= 1

    def test_rate_template(self, template_service):
        """Test rating a template."""
        new_rating = template_service.rate_template("yaml_test_agent", 4.5)
        assert new_rating == 4.5

    def test_rate_template_invalid(self, template_service):
        """Test rating with invalid value."""
        with pytest.raises(TemplateError):
            template_service.rate_template("yaml_test_agent", 6.0)

    def test_rate_template_not_found(self, template_service):
        """Test rating non-existent template."""
        with pytest.raises(TemplateError):
            template_service.rate_template("nonexistent", 4.0)

    def test_deprecate_template(self, template_service):
        """Test deprecating a template."""
        result = template_service.deprecate_template("yaml_test_agent")
        assert result is True

        template = template_service.get_template("yaml_test_agent")
        assert template.status == TemplateStatus.DEPRECATED

    def test_get_statistics(self, template_service):
        """Test getting service statistics."""
        stats = template_service.get_statistics()
        assert "total_templates" in stats
        assert "builtin_templates" in stats
        assert "by_category" in stats

    @pytest.mark.asyncio
    async def test_instantiate_template(self, template_service):
        """Test template instantiation."""
        agent_id = await template_service.instantiate(
            template_id="yaml_test_agent",
            name="My Agent",
            parameters={"param1": "custom_value"},
        )

        assert agent_id is not None

        # Check usage count increased
        template = template_service.get_template("yaml_test_agent")
        assert template.usage_count > 0

    @pytest.mark.asyncio
    async def test_instantiate_template_not_found(self, template_service):
        """Test instantiation with non-existent template."""
        with pytest.raises(TemplateError):
            await template_service.instantiate(
                template_id="nonexistent",
                name="My Agent",
            )

    @pytest.mark.asyncio
    async def test_instantiate_archived_template(self, template_service):
        """Test cannot instantiate archived template."""
        template = template_service.get_template("yaml_test_agent")
        template.status = TemplateStatus.ARCHIVED

        with pytest.raises(TemplateError):
            await template_service.instantiate(
                template_id="yaml_test_agent",
                name="My Agent",
            )

    def test_event_handlers(self, template_service):
        """Test event handler registration."""
        events = []

        def on_instantiate(template_id, agent_id, params):
            events.append(("instantiate", template_id))

        def on_load(count):
            events.append(("load", count))

        template_service.on_instantiate(on_instantiate)
        template_service.on_load(on_load)

        template_service.reload_templates()
        assert any(e[0] == "load" for e in events)


# =============================================================================
# Template API Tests
# =============================================================================


class TestTemplateAPI:
    """Tests for Template API endpoints."""

    @pytest.fixture
    def client(self, template_service):
        """Create test client with template service."""
        from fastapi import FastAPI
        from src.api.v1.templates.routes import router, set_template_service

        app = FastAPI()
        app.include_router(router)
        set_template_service(template_service)

        return TestClient(app)

    def test_list_templates(self, client):
        """Test GET /templates/"""
        response = client.get("/templates/")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total" in data

    def test_list_templates_with_filters(self, client):
        """Test GET /templates/ with filters."""
        response = client.get("/templates/?category=it_operations&search=test")
        assert response.status_code == 200

    def test_list_templates_pagination(self, client):
        """Test GET /templates/ with pagination."""
        response = client.get("/templates/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_get_template(self, client):
        """Test GET /templates/{id}"""
        response = client.get("/templates/yaml_test_agent")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "yaml_test_agent"

    def test_get_template_not_found(self, client):
        """Test GET /templates/{id} not found."""
        response = client.get("/templates/nonexistent")
        assert response.status_code == 404

    def test_instantiate_template(self, client):
        """Test POST /templates/{id}/instantiate"""
        response = client.post(
            "/templates/yaml_test_agent/instantiate",
            json={
                "name": "My Agent",
                "parameters": {"param1": "value1"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert data["template_id"] == "yaml_test_agent"

    def test_instantiate_template_not_found(self, client):
        """Test POST /templates/{id}/instantiate not found."""
        response = client.post(
            "/templates/nonexistent/instantiate",
            json={"name": "My Agent"},
        )
        assert response.status_code == 404

    def test_search_templates(self, client):
        """Test POST /templates/search"""
        response = client.post(
            "/templates/search",
            json={"query": "YAML", "limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data

    def test_get_popular_templates(self, client):
        """Test GET /templates/popular/list"""
        response = client.get("/templates/popular/list?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data

    def test_get_top_rated_templates(self, client):
        """Test GET /templates/top-rated/list"""
        response = client.get("/templates/top-rated/list?limit=5")
        assert response.status_code == 200

    def test_get_similar_templates(self, client):
        """Test GET /templates/similar/{id}"""
        response = client.get("/templates/similar/yaml_test_agent")
        assert response.status_code == 200

    def test_get_similar_templates_not_found(self, client):
        """Test GET /templates/similar/{id} not found."""
        response = client.get("/templates/similar/nonexistent")
        assert response.status_code == 404

    def test_list_categories(self, client):
        """Test GET /templates/categories/list"""
        response = client.get("/templates/categories/list")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data

    def test_rate_template(self, client):
        """Test POST /templates/{id}/rate"""
        response = client.post(
            "/templates/yaml_test_agent/rate",
            json={"rating": 4.5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "new_rating" in data

    def test_rate_template_invalid(self, client):
        """Test POST /templates/{id}/rate with invalid rating."""
        response = client.post(
            "/templates/yaml_test_agent/rate",
            json={"rating": 6.0},  # Invalid
        )
        assert response.status_code == 422  # Validation error

    def test_get_statistics(self, client):
        """Test GET /templates/statistics/summary"""
        response = client.get("/templates/statistics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_templates" in data
        assert "by_category" in data

    def test_health_check(self, client):
        """Test GET /templates/health"""
        response = client.get("/templates/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "templates"


# =============================================================================
# Integration Tests
# =============================================================================


class TestTemplateIntegration:
    """Integration tests for template system."""

    def test_full_template_workflow(self, template_service, sample_template):
        """Test complete template workflow."""
        # 1. Register custom template
        template_service.register_template(sample_template)

        # 2. Search for it
        results = template_service.search_templates("Test Agent")
        assert len(results) >= 1

        # 3. Get details
        template = template_service.get_template("test_agent")
        assert template is not None

        # 4. Rate it
        template_service.rate_template("test_agent", 5.0)
        assert template.rating == 5.0

        # 5. Find similar
        similar = template_service.find_similar_templates("test_agent")
        assert isinstance(similar, list)

        # 6. Deprecate
        template_service.deprecate_template("test_agent")
        assert template.status == TemplateStatus.DEPRECATED

    def test_template_parameter_edge_cases(self):
        """Test parameter validation edge cases."""
        # Integer validation
        int_param = TemplateParameter(
            name="count",
            type=ParameterType.INTEGER,
            description="Count",
            min_value=0,
            max_value=100,
        )
        assert int_param.validate(50) is True
        assert int_param.validate(50.5) is False  # Not an integer
        assert int_param.validate(-1) is False

        # List validation
        list_param = TemplateParameter(
            name="items",
            type=ParameterType.LIST,
            description="Items",
        )
        assert list_param.validate([1, 2, 3]) is True
        assert list_param.validate("not a list") is False

        # Object validation
        obj_param = TemplateParameter(
            name="config",
            type=ParameterType.OBJECT,
            description="Config",
        )
        assert obj_param.validate({"key": "value"}) is True
        assert obj_param.validate([1, 2, 3]) is False
