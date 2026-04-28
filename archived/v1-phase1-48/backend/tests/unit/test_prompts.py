# =============================================================================
# IPA Platform - Prompts Unit Tests
# =============================================================================
# Sprint 3: 集成 & 可靠性 - Prompt 模板管理
#
# Tests for:
#   - PromptTemplate
#   - PromptTemplateManager
#   - Template rendering
#   - YAML loading
# =============================================================================

import tempfile
from pathlib import Path

import pytest

from src.domain.prompts.template import (
    PromptCategory,
    PromptTemplate,
    PromptTemplateError,
    PromptTemplateManager,
    TemplateNotFoundError,
    TemplateRenderError,
    TemplateValidationError,
)


# =============================================================================
# PromptTemplate Tests
# =============================================================================


class TestPromptTemplate:
    """Tests for PromptTemplate."""

    def test_initialization(self):
        """Test basic initialization."""
        template = PromptTemplate(
            id="test_template",
            name="Test Template",
            content="Hello {{name}}!",
        )

        assert template.id == "test_template"
        assert template.name == "Test Template"
        assert template.content == "Hello {{name}}!"
        assert "name" in template.variables
        assert template.category == PromptCategory.COMMON

    def test_initialization_with_options(self):
        """Test initialization with custom options."""
        template = PromptTemplate(
            id="custom_template",
            name="Custom Template",
            content="{{greeting}} {{name}}!",
            category=PromptCategory.IT_OPERATIONS,
            description="A custom template",
            default_values={"greeting": "Hello"},
            version="2.0.0",
            author="tester",
            tags=["test", "custom"],
            metadata={"key": "value"},
        )

        assert template.category == PromptCategory.IT_OPERATIONS
        assert template.description == "A custom template"
        assert template.default_values == {"greeting": "Hello"}
        assert template.version == "2.0.0"
        assert template.author == "tester"
        assert "test" in template.tags
        assert template.metadata == {"key": "value"}

    def test_extract_variables(self):
        """Test variable extraction."""
        template = PromptTemplate(
            id="vars_test",
            name="Variables Test",
            content="Hello {{name}}! Your ID is {{id}}. Welcome {{name}}!",
        )

        # Should extract unique variables
        assert set(template.variables) == {"name", "id"}

    def test_extract_variables_with_spaces(self):
        """Test variable extraction with spaces."""
        template = PromptTemplate(
            id="spaces_test",
            name="Spaces Test",
            content="Hello {{ name }}! ID: {{ id }}",
        )

        assert set(template.variables) == {"name", "id"}

    def test_get_required_variables(self):
        """Test getting required variables."""
        template = PromptTemplate(
            id="required_test",
            name="Required Test",
            content="{{greeting}} {{name}}!",
            default_values={"greeting": "Hello"},
        )

        required = template.get_required_variables()
        assert "name" in required
        assert "greeting" not in required

    def test_to_dict(self):
        """Test serialization."""
        template = PromptTemplate(
            id="dict_test",
            name="Dict Test",
            content="Hello {{name}}!",
        )

        result = template.to_dict()

        assert result["id"] == "dict_test"
        assert result["name"] == "Dict Test"
        assert result["content"] == "Hello {{name}}!"
        assert "created_at" in result

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "id": "from_dict_test",
            "name": "From Dict Test",
            "content": "Test content {{var}}",
            "category": "it_operations",
            "description": "Test description",
            "tags": ["tag1", "tag2"],
        }

        template = PromptTemplate.from_dict(data)

        assert template.id == "from_dict_test"
        assert template.name == "From Dict Test"
        assert template.category == PromptCategory.IT_OPERATIONS
        assert "var" in template.variables


# =============================================================================
# PromptTemplateManager Tests
# =============================================================================


class TestPromptTemplateManager:
    """Tests for PromptTemplateManager."""

    @pytest.fixture
    def manager(self):
        """Create manager instance."""
        return PromptTemplateManager()

    @pytest.fixture
    def template(self):
        """Create test template."""
        return PromptTemplate(
            id="test_template",
            name="Test Template",
            content="Hello {{name}}!",
        )

    # -------------------------------------------------------------------------
    # Template Management Tests
    # -------------------------------------------------------------------------

    def test_register_template(self, manager, template):
        """Test registering template."""
        manager.register_template(template)

        assert manager.get_template("test_template") == template

    def test_unregister_template(self, manager, template):
        """Test unregistering template."""
        manager.register_template(template)
        result = manager.unregister_template("test_template")

        assert result is True
        assert manager.get_template("test_template") is None

    def test_unregister_nonexistent_template(self, manager):
        """Test unregistering non-existent template."""
        result = manager.unregister_template("nonexistent")
        assert result is False

    def test_list_templates(self, manager, template):
        """Test listing templates."""
        manager.register_template(template)

        templates = manager.list_templates()

        assert len(templates) == 1
        assert templates[0] == template

    def test_list_templates_by_category(self, manager):
        """Test listing templates by category."""
        t1 = PromptTemplate(
            id="it_template",
            name="IT Template",
            content="IT {{action}}",
            category=PromptCategory.IT_OPERATIONS,
        )
        t2 = PromptTemplate(
            id="cs_template",
            name="CS Template",
            content="CS {{action}}",
            category=PromptCategory.CUSTOMER_SERVICE,
        )

        manager.register_template(t1)
        manager.register_template(t2)

        it_templates = manager.list_templates(category=PromptCategory.IT_OPERATIONS)

        assert len(it_templates) == 1
        assert it_templates[0].id == "it_template"

    def test_list_templates_by_tags(self, manager):
        """Test listing templates by tags."""
        t1 = PromptTemplate(
            id="tagged1",
            name="Tagged 1",
            content="Content 1",
            tags=["incident", "triage"],
        )
        t2 = PromptTemplate(
            id="tagged2",
            name="Tagged 2",
            content="Content 2",
            tags=["report"],
        )

        manager.register_template(t1)
        manager.register_template(t2)

        templates = manager.list_templates(tags=["incident"])

        assert len(templates) == 1
        assert templates[0].id == "tagged1"

    def test_search_templates(self, manager):
        """Test searching templates."""
        t1 = PromptTemplate(
            id="incident_triage",
            name="Incident Triage",
            content="Triage content",
            description="Triage incidents",
        )
        t2 = PromptTemplate(
            id="customer_inquiry",
            name="Customer Inquiry",
            content="Inquiry content",
            description="Handle inquiries",
        )

        manager.register_template(t1)
        manager.register_template(t2)

        # Search by name
        results = manager.search_templates("incident")
        assert len(results) == 1
        assert results[0].id == "incident_triage"

        # Search by description
        results = manager.search_templates("inquiries")
        assert len(results) == 1
        assert results[0].id == "customer_inquiry"

    # -------------------------------------------------------------------------
    # Rendering Tests
    # -------------------------------------------------------------------------

    def test_render_template(self, manager):
        """Test rendering template."""
        template = PromptTemplate(
            id="render_test",
            name="Render Test",
            content="Hello {{name}}!",
        )
        manager.register_template(template)

        result = manager.render("render_test", {"name": "World"})

        assert result == "Hello World!"

    def test_render_with_default_values(self, manager):
        """Test rendering with default values."""
        template = PromptTemplate(
            id="default_test",
            name="Default Test",
            content="{{greeting}} {{name}}!",
            default_values={"greeting": "Hello"},
        )
        manager.register_template(template)

        result = manager.render("default_test", {"name": "World"})

        assert result == "Hello World!"

    def test_render_override_default(self, manager):
        """Test rendering overriding default value."""
        template = PromptTemplate(
            id="override_test",
            name="Override Test",
            content="{{greeting}} {{name}}!",
            default_values={"greeting": "Hello"},
        )
        manager.register_template(template)

        result = manager.render(
            "override_test",
            {"name": "World", "greeting": "Hi"},
        )

        assert result == "Hi World!"

    def test_render_missing_variable_strict(self, manager):
        """Test rendering with missing variable in strict mode."""
        template = PromptTemplate(
            id="strict_test",
            name="Strict Test",
            content="Hello {{name}} {{surname}}!",
        )
        manager.register_template(template)

        with pytest.raises(TemplateRenderError) as exc_info:
            manager.render("strict_test", {"name": "John"})

        assert "surname" in exc_info.value.missing_vars

    def test_render_missing_variable_non_strict(self, manager):
        """Test rendering with missing variable in non-strict mode."""
        template = PromptTemplate(
            id="non_strict_test",
            name="Non-Strict Test",
            content="Hello {{name}} {{surname}}!",
        )
        manager.register_template(template)

        result = manager.render(
            "non_strict_test",
            {"name": "John"},
            strict=False,
        )

        assert result == "Hello John !"

    def test_render_template_not_found(self, manager):
        """Test rendering non-existent template."""
        with pytest.raises(TemplateNotFoundError):
            manager.render("nonexistent", {})

    def test_render_with_spaced_variables(self, manager):
        """Test rendering with spaced variable syntax."""
        template = PromptTemplate(
            id="spaced_test",
            name="Spaced Test",
            content="Hello {{ name }}!",
        )
        manager.register_template(template)

        result = manager.render("spaced_test", {"name": "World"})

        assert result == "Hello World!"

    # -------------------------------------------------------------------------
    # YAML Loading Tests
    # -------------------------------------------------------------------------

    def test_load_from_yaml(self, manager):
        """Test loading templates from YAML string."""
        yaml_content = """
templates:
  - id: yaml_test
    name: YAML Test
    content: "Hello {{name}}!"
    category: common
    tags:
      - test
"""
        templates = manager.load_from_yaml(yaml_content)

        assert len(templates) == 1
        assert templates[0].id == "yaml_test"
        assert manager.get_template("yaml_test") is not None

    def test_load_from_yaml_multiple(self, manager):
        """Test loading multiple templates from YAML."""
        yaml_content = """
templates:
  - id: template1
    name: Template 1
    content: "Content 1 {{var1}}"
  - id: template2
    name: Template 2
    content: "Content 2 {{var2}}"
"""
        templates = manager.load_from_yaml(yaml_content)

        assert len(templates) == 2
        assert manager.get_template_count() == 2

    def test_load_templates_from_directory(self):
        """Test loading templates from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test YAML file
            yaml_path = Path(tmpdir) / "test.yaml"
            yaml_path.write_text("""
templates:
  - id: dir_test
    name: Directory Test
    content: "Test {{content}}"
""")
            manager = PromptTemplateManager(templates_dir=Path(tmpdir))
            count = manager.load_templates()

            assert count == 1
            assert manager.get_template("dir_test") is not None

    def test_load_templates_nonexistent_directory(self, manager):
        """Test loading from non-existent directory."""
        manager._templates_dir = Path("/nonexistent/path")
        count = manager.load_templates()

        assert count == 0

    # -------------------------------------------------------------------------
    # Validation Tests
    # -------------------------------------------------------------------------

    def test_validate_template_valid(self, manager):
        """Test validating valid template."""
        template = PromptTemplate(
            id="valid_template",
            name="Valid Template",
            content="Hello {{name}}!",
        )

        errors = manager.validate_template(template)

        assert len(errors) == 0

    def test_validate_template_empty_id(self, manager):
        """Test validating template with empty ID."""
        template = PromptTemplate(
            id="",
            name="Empty ID",
            content="Content",
        )

        errors = manager.validate_template(template)

        assert any("ID" in e for e in errors)

    def test_validate_template_empty_content(self, manager):
        """Test validating template with empty content."""
        template = PromptTemplate(
            id="empty_content",
            name="Empty Content",
            content="",
        )

        errors = manager.validate_template(template)

        assert any("content" in e.lower() for e in errors)

    def test_validate_template_invalid_id_format(self, manager):
        """Test validating template with invalid ID format."""
        template = PromptTemplate(
            id="Invalid-ID",
            name="Invalid ID",
            content="Content",
        )

        errors = manager.validate_template(template)

        assert any("ID" in e for e in errors)

    # -------------------------------------------------------------------------
    # Utility Tests
    # -------------------------------------------------------------------------

    def test_get_template_count(self, manager, template):
        """Test getting template count."""
        assert manager.get_template_count() == 0

        manager.register_template(template)

        assert manager.get_template_count() == 1

    def test_get_categories(self, manager):
        """Test getting categories."""
        t1 = PromptTemplate(
            id="it1",
            name="IT 1",
            content="C1",
            category=PromptCategory.IT_OPERATIONS,
        )
        t2 = PromptTemplate(
            id="cs1",
            name="CS 1",
            content="C2",
            category=PromptCategory.CUSTOMER_SERVICE,
        )

        manager.register_template(t1)
        manager.register_template(t2)

        categories = manager.get_categories()

        assert PromptCategory.IT_OPERATIONS in categories
        assert PromptCategory.CUSTOMER_SERVICE in categories

    def test_clear(self, manager, template):
        """Test clearing all templates."""
        manager.register_template(template)
        manager.clear()

        assert manager.get_template_count() == 0


# =============================================================================
# Exception Tests
# =============================================================================


class TestPromptExceptions:
    """Tests for prompt exceptions."""

    def test_template_error(self):
        """Test base template error."""
        error = PromptTemplateError("Test message", code="TEST_CODE")

        assert str(error) == "Test message"
        assert error.code == "TEST_CODE"

    def test_template_not_found_error(self):
        """Test template not found error."""
        error = TemplateNotFoundError("missing_template")

        assert "missing_template" in str(error)
        assert error.code == "TEMPLATE_NOT_FOUND"
        assert error.template_id == "missing_template"

    def test_template_render_error(self):
        """Test template render error."""
        error = TemplateRenderError("test_template", ["var1", "var2"])

        assert "test_template" in str(error)
        assert error.missing_vars == ["var1", "var2"]
        assert error.code == "TEMPLATE_RENDER_ERROR"

    def test_template_validation_error(self):
        """Test template validation error."""
        error = TemplateValidationError("Validation failed")

        assert "Validation failed" in str(error)
        assert error.code == "TEMPLATE_VALIDATION_ERROR"


# =============================================================================
# Category Tests
# =============================================================================


class TestPromptCategory:
    """Tests for PromptCategory enum."""

    def test_category_values(self):
        """Test category values."""
        assert PromptCategory.IT_OPERATIONS.value == "it_operations"
        assert PromptCategory.CUSTOMER_SERVICE.value == "customer_service"
        assert PromptCategory.COMMON.value == "common"
        assert PromptCategory.CUSTOM.value == "custom"

    def test_category_from_string(self):
        """Test creating category from string."""
        category = PromptCategory("it_operations")
        assert category == PromptCategory.IT_OPERATIONS

    def test_category_invalid_string(self):
        """Test creating category from invalid string."""
        with pytest.raises(ValueError):
            PromptCategory("invalid_category")
