# =============================================================================
# IPA Platform - Tool-based Generative UI Tests
# =============================================================================
# Sprint 60: AG-UI Advanced Features
# S60-1: Tool-based Generative UI (8 pts)
#
# Tests for ToolBasedUIHandler and UI component generation.
# =============================================================================

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.ag_ui.features.advanced.tool_ui import (
    UIComponentType,
    FormFieldType,
    ChartType,
    FormFieldDefinition,
    TableColumnDefinition,
    UIComponentSchema,
    UIComponentDefinition,
    ValidationResult,
    ToolBasedUIHandler,
    create_tool_ui_handler,
)


class TestUIComponentType:
    """Tests for UIComponentType enum."""

    def test_form_type(self):
        """Test FORM component type."""
        assert UIComponentType.FORM.value == "form"

    def test_chart_type(self):
        """Test CHART component type."""
        assert UIComponentType.CHART.value == "chart"

    def test_card_type(self):
        """Test CARD component type."""
        assert UIComponentType.CARD.value == "card"

    def test_table_type(self):
        """Test TABLE component type."""
        assert UIComponentType.TABLE.value == "table"

    def test_custom_type(self):
        """Test CUSTOM component type."""
        assert UIComponentType.CUSTOM.value == "custom"


class TestFormFieldType:
    """Tests for FormFieldType enum."""

    def test_text_field(self):
        """Test TEXT field type."""
        assert FormFieldType.TEXT.value == "text"

    def test_select_field(self):
        """Test SELECT field type."""
        assert FormFieldType.SELECT.value == "select"

    def test_number_field(self):
        """Test NUMBER field type."""
        assert FormFieldType.NUMBER.value == "number"

    def test_checkbox_field(self):
        """Test CHECKBOX field type."""
        assert FormFieldType.CHECKBOX.value == "checkbox"


class TestChartType:
    """Tests for ChartType enum."""

    def test_line_chart(self):
        """Test LINE chart type."""
        assert ChartType.LINE.value == "line"

    def test_bar_chart(self):
        """Test BAR chart type."""
        assert ChartType.BAR.value == "bar"

    def test_pie_chart(self):
        """Test PIE chart type."""
        assert ChartType.PIE.value == "pie"


class TestFormFieldDefinition:
    """Tests for FormFieldDefinition dataclass."""

    def test_basic_field(self):
        """Test basic field definition."""
        field = FormFieldDefinition(
            name="username",
            label="Username",
            field_type=FormFieldType.TEXT,
        )
        assert field.name == "username"
        assert field.field_type == FormFieldType.TEXT
        assert field.label == "Username"
        assert field.required is False
        assert field.options is None

    def test_required_field(self):
        """Test required field definition."""
        field = FormFieldDefinition(
            name="email",
            label="Email",
            field_type=FormFieldType.TEXT,
            required=True,
        )
        assert field.required is True

    def test_select_field_with_options(self):
        """Test select field with options."""
        field = FormFieldDefinition(
            name="country",
            label="Country",
            field_type=FormFieldType.SELECT,
            options=[
                {"value": "usa", "label": "USA"},
                {"value": "canada", "label": "Canada"},
            ],
        )
        assert len(field.options) == 2

    def test_to_dict(self):
        """Test conversion to dictionary."""
        field = FormFieldDefinition(
            name="age",
            label="Age",
            field_type=FormFieldType.NUMBER,
            required=True,
            default_value=18,
        )
        result = field.to_dict()
        assert result["name"] == "age"
        assert result["type"] == "number"
        assert result["label"] == "Age"
        assert result["required"] is True
        assert result["defaultValue"] == 18


class TestTableColumnDefinition:
    """Tests for TableColumnDefinition dataclass."""

    def test_basic_column(self):
        """Test basic column definition."""
        column = TableColumnDefinition(
            key="name",
            label="Name",
        )
        assert column.key == "name"
        assert column.label == "Name"
        assert column.sortable is False
        assert column.width is None

    def test_sortable_column(self):
        """Test sortable column definition."""
        column = TableColumnDefinition(
            key="date",
            label="Date",
            sortable=True,
            width="150px",
        )
        assert column.sortable is True
        assert column.width == "150px"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        column = TableColumnDefinition(
            key="amount",
            label="Amount",
            sortable=True,
        )
        result = column.to_dict()
        assert result["key"] == "amount"
        assert result["label"] == "Amount"
        assert result["sortable"] is True


class TestUIComponentSchema:
    """Tests for UIComponentSchema dataclass."""

    def test_basic_schema(self):
        """Test basic schema definition."""
        schema = UIComponentSchema(
            component_type=UIComponentType.FORM,
            required_fields=["fields"],
            optional_fields=["title"],
        )
        assert schema.component_type == UIComponentType.FORM
        assert "fields" in schema.required_fields
        assert "title" in schema.optional_fields

    def test_schema_with_validators(self):
        """Test schema with validation rules."""
        schema = UIComponentSchema(
            component_type=UIComponentType.FORM,
            required_fields=["fields"],
            validators={
                "fields": lambda x: isinstance(x, list) and len(x) > 0,
            },
        )
        assert "fields" in schema.validators

    def test_for_form_factory(self):
        """Test form schema factory method."""
        schema = UIComponentSchema.for_form()
        assert schema.component_type == UIComponentType.FORM
        assert "fields" in schema.required_fields

    def test_for_chart_factory(self):
        """Test chart schema factory method."""
        schema = UIComponentSchema.for_chart()
        assert schema.component_type == UIComponentType.CHART
        assert "chartType" in schema.required_fields
        assert "data" in schema.required_fields

    def test_for_card_factory(self):
        """Test card schema factory method."""
        schema = UIComponentSchema.for_card()
        assert schema.component_type == UIComponentType.CARD
        assert "title" in schema.required_fields

    def test_for_table_factory(self):
        """Test table schema factory method."""
        schema = UIComponentSchema.for_table()
        assert schema.component_type == UIComponentType.TABLE
        assert "columns" in schema.required_fields
        assert "data" in schema.required_fields

    def test_for_custom_factory(self):
        """Test custom schema factory method."""
        schema = UIComponentSchema.for_custom()
        assert schema.component_type == UIComponentType.CUSTOM
        assert "componentName" in schema.required_fields

    def test_get_schema(self):
        """Test get_schema static method."""
        schema = UIComponentSchema.get_schema(UIComponentType.FORM)
        assert schema.component_type == UIComponentType.FORM


class TestUIComponentDefinition:
    """Tests for UIComponentDefinition dataclass."""

    def test_basic_definition(self):
        """Test basic component definition."""
        definition = UIComponentDefinition(
            component_type=UIComponentType.FORM,
            props={"fields": []},
            component_id="form-123",
            title="User Form",
        )
        assert definition.component_id == "form-123"
        assert definition.component_type == UIComponentType.FORM
        assert definition.title == "User Form"
        assert definition.props == {"fields": []}

    def test_definition_with_metadata(self):
        """Test component definition with metadata."""
        definition = UIComponentDefinition(
            component_type=UIComponentType.TABLE,
            props={"columns": [], "data": []},
            title="User List",
            metadata={"source": "api"},
        )
        assert definition.metadata["source"] == "api"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        definition = UIComponentDefinition(
            component_type=UIComponentType.CHART,
            props={"chartType": "line", "data": []},
            component_id="chart-789",
            title="Sales Chart",
        )
        result = definition.to_dict()
        assert result["componentId"] == "chart-789"
        assert result["componentType"] == "chart"
        assert result["title"] == "Sales Chart"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "componentId": "test-123",
            "componentType": "form",
            "props": {"fields": []},
            "title": "Test Form",
        }
        definition = UIComponentDefinition.from_dict(data)
        assert definition.component_id == "test-123"
        assert definition.component_type == UIComponentType.FORM
        assert definition.title == "Test Form"

    def test_auto_generated_id(self):
        """Test auto-generated component ID."""
        definition = UIComponentDefinition(
            component_type=UIComponentType.CARD,
            props={"title": "Test"},
        )
        assert definition.component_id.startswith("ui-")

    def test_created_at_timestamp(self):
        """Test created_at timestamp is set."""
        before = time.time()
        definition = UIComponentDefinition(
            component_type=UIComponentType.CARD,
            props={"title": "Test"},
        )
        after = time.time()
        assert before <= definition.created_at <= after


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test valid validation result."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []

    def test_invalid_result(self):
        """Test invalid validation result."""
        result = ValidationResult(
            is_valid=False,
            errors=["Missing required field: title"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_result_with_warnings(self):
        """Test validation result with warnings."""
        result = ValidationResult(
            is_valid=True,
            warnings=["Unknown field: extra"],
        )
        assert result.is_valid is True
        assert len(result.warnings) == 1


class TestToolBasedUIHandler:
    """Tests for ToolBasedUIHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a ToolBasedUIHandler instance."""
        return ToolBasedUIHandler(validate_schema=True)

    def test_initialization(self, handler):
        """Test handler initialization."""
        assert handler.validate_schema is True
        assert handler.strict_mode is False

    def test_initialization_strict_mode(self):
        """Test handler initialization with strict mode."""
        handler = ToolBasedUIHandler(strict_mode=True)
        assert handler.strict_mode is True

    def test_get_component_not_found(self, handler):
        """Test getting non-existent component."""
        result = handler.get_component("nonexistent")
        assert result is None

    def test_list_components_empty(self, handler):
        """Test listing components when empty."""
        result = handler.list_components()
        assert result == []

    def test_emit_form_component(self, handler):
        """Test emitting a form component."""
        fields = [
            FormFieldDefinition(
                name="username",
                label="Username",
                field_type=FormFieldType.TEXT,
                required=True,
            ),
        ]
        event = handler.emit_form_component(
            thread_id="thread-123",
            run_id="run-456",
            fields=fields,
            title="Login",
        )
        assert event is not None
        assert event.event_name == "ui_component"
        assert event.payload["action"] == "render"

    def test_emit_chart_component(self, handler):
        """Test emitting a chart component."""
        data = [
            {"month": "Jan", "value": 100},
            {"month": "Feb", "value": 150},
        ]
        event = handler.emit_chart_component(
            thread_id="thread-123",
            run_id="run-456",
            chart_type=ChartType.LINE,
            data=data,
            title="Monthly Sales",
        )
        assert event is not None
        assert event.payload["component"]["props"]["chartType"] == "line"

    def test_emit_card_component(self, handler):
        """Test emitting a card component."""
        event = handler.emit_card_component(
            thread_id="thread-123",
            run_id="run-456",
            title="System Status",
            content="All systems operational",
        )
        assert event is not None
        assert event.payload["component"]["props"]["title"] == "System Status"

    def test_emit_table_component(self, handler):
        """Test emitting a table component."""
        columns = [
            TableColumnDefinition(key="id", label="ID"),
            TableColumnDefinition(key="name", label="Name"),
        ]
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        event = handler.emit_table_component(
            thread_id="thread-123",
            run_id="run-456",
            columns=columns,
            data=data,
            title="Users",
        )
        assert event is not None
        assert len(event.payload["component"]["props"]["columns"]) == 2

    def test_emit_custom_component(self, handler):
        """Test emitting a custom component."""
        event = handler.emit_custom_component(
            thread_id="thread-123",
            run_id="run-456",
            component_name="WeatherWidget",
            props={"city": "Tokyo", "units": "metric"},
        )
        assert event is not None
        assert event.payload["component"]["props"]["componentName"] == "WeatherWidget"

    def test_validate_component_schema_valid(self, handler):
        """Test validation of valid component data."""
        component = UIComponentDefinition(
            component_type=UIComponentType.FORM,
            props={"fields": [{"name": "test", "label": "Test"}]},
        )
        result = handler.validate_component_schema(component)
        assert result.is_valid is True

    def test_validate_component_schema_missing_required(self, handler):
        """Test validation with missing required field."""
        component = UIComponentDefinition(
            component_type=UIComponentType.FORM,
            props={},  # Missing 'fields'
        )
        result = handler.validate_component_schema(component)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_emit_update_component(self, handler):
        """Test updating an existing component."""
        # First emit a component
        handler.emit_card_component(
            thread_id="thread-123",
            run_id="run-456",
            title="Initial Title",
            component_id="card-001",
        )

        # Then update it
        event = handler.emit_update_component(
            component_id="card-001",
            thread_id="thread-123",
            run_id="run-456",
            props_update={"content": "Updated content"},
        )
        assert event is not None
        assert event.payload["action"] == "update"

    def test_emit_update_component_not_found(self, handler):
        """Test updating a non-existent component."""
        event = handler.emit_update_component(
            component_id="nonexistent",
            thread_id="thread-123",
            run_id="run-456",
            props_update={"content": "New content"},
        )
        assert event is None

    def test_emit_remove_component(self, handler):
        """Test removing a component."""
        # First emit a component
        handler.emit_card_component(
            thread_id="thread-123",
            run_id="run-456",
            title="To Be Removed",
            component_id="card-002",
        )

        # Then remove it
        event = handler.emit_remove_component(
            component_id="card-002",
            thread_id="thread-123",
            run_id="run-456",
        )
        assert event is not None
        assert event.payload["action"] == "remove"
        assert handler.get_component("card-002") is None

    def test_clear_components(self, handler):
        """Test clearing all components."""
        # Emit some components
        handler.emit_card_component(
            thread_id="thread-123",
            run_id="run-456",
            title="Card 1",
        )
        handler.emit_card_component(
            thread_id="thread-123",
            run_id="run-456",
            title="Card 2",
        )

        assert len(handler.list_components()) == 2
        handler.clear_components()
        assert len(handler.list_components()) == 0

    def test_strict_mode_validation_error(self):
        """Test strict mode raises error on validation failure."""
        handler = ToolBasedUIHandler(strict_mode=True)

        with pytest.raises(ValueError):
            handler.emit_ui_component(
                component_type=UIComponentType.FORM,
                props={},  # Missing required 'fields'
                thread_id="thread-123",
                run_id="run-456",
            )


class TestCreateToolUIHandler:
    """Tests for create_tool_ui_handler factory function."""

    def test_create_handler(self):
        """Test creating handler with factory function."""
        handler = create_tool_ui_handler()
        assert isinstance(handler, ToolBasedUIHandler)
        assert handler.validate_schema is True

    def test_create_handler_no_validation(self):
        """Test creating handler without schema validation."""
        handler = create_tool_ui_handler(validate_schema=False)
        assert handler.validate_schema is False

    def test_create_handler_strict_mode(self):
        """Test creating handler with strict mode."""
        handler = create_tool_ui_handler(strict_mode=True)
        assert handler.strict_mode is True
