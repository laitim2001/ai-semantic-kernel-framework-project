"""
Unit tests for SchemaValidator

Tests:
- Required field validation
- Type checking
- Nested object validation
- Error messages

Sprint 95: Story 95-6 - SchemaValidator Tests (Phase 28)
"""

import pytest

from backend.src.integrations.orchestration.input_gateway import (
    SchemaValidator,
    MockSchemaValidator,
    SchemaDefinition,
    ValidationError,
)


class TestSchemaValidator:
    """Tests for SchemaValidator class."""

    def test_validator_initialization(self):
        """Test validator initializes with default schemas."""
        validator = SchemaValidator()

        assert "servicenow" in validator.list_schemas()
        assert "prometheus" in validator.list_schemas()
        assert "user_input" in validator.list_schemas()

    def test_validate_servicenow_valid(self):
        """Test validating valid ServiceNow payload."""
        validator = SchemaValidator()

        data = {
            "number": "INC0012345",
            "category": "incident",
            "short_description": "Test incident",
        }

        result = validator.validate(data, schema="servicenow")

        assert result == data

    def test_validate_servicenow_missing_required(self):
        """Test validation fails for missing required field."""
        validator = SchemaValidator(strict_mode=True)

        data = {
            "category": "incident",
            "short_description": "Test incident",
            # Missing: number
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="servicenow")

        assert "number" in str(exc_info.value)
        assert exc_info.value.errors

    def test_validate_servicenow_empty_required(self):
        """Test validation fails for empty required field."""
        validator = SchemaValidator(strict_mode=True)

        data = {
            "number": "",  # Empty string
            "category": "incident",
            "short_description": "Test incident",
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="servicenow")

        assert "empty" in str(exc_info.value).lower()

    def test_validate_servicenow_with_optional(self):
        """Test validation passes with optional fields."""
        validator = SchemaValidator()

        data = {
            "number": "INC0012345",
            "category": "incident",
            "short_description": "Test incident",
            "subcategory": "software",
            "priority": "2",
            "assignment_group": "IT Support",
        }

        result = validator.validate(data, schema="servicenow")

        assert result == data

    def test_validate_prometheus_valid(self):
        """Test validating valid Prometheus payload."""
        validator = SchemaValidator()

        data = {
            "alerts": [{
                "alertname": "HighCPU",
                "status": "firing",
            }]
        }

        result = validator.validate(data, schema="prometheus")

        assert result == data

    def test_validate_prometheus_missing_alerts(self):
        """Test validation fails for missing alerts."""
        validator = SchemaValidator(strict_mode=True)

        data = {
            "status": "firing",
            # Missing: alerts
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="prometheus")

        assert "alerts" in str(exc_info.value)

    def test_validate_prometheus_nested_missing(self):
        """Test validation fails for missing nested required fields."""
        validator = SchemaValidator(strict_mode=True)

        data = {
            "alerts": [{
                "status": "firing",
                # Missing: alertname
            }]
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="prometheus")

        assert "alertname" in str(exc_info.value)

    def test_validate_type_check_list(self):
        """Test type checking for list fields."""
        validator = SchemaValidator(strict_mode=True)

        data = {
            "alerts": "not_a_list",  # Should be list
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="prometheus")

        assert "list" in str(exc_info.value).lower()

    def test_validate_non_strict_mode(self):
        """Test non-strict mode logs warnings but doesn't raise."""
        validator = SchemaValidator(strict_mode=False)

        data = {
            "category": "incident",
            # Missing: number, short_description
        }

        # Should not raise
        result = validator.validate(data, schema="servicenow")
        assert result == data

    def test_validate_unknown_schema(self):
        """Test handling unknown schema."""
        validator = SchemaValidator(strict_mode=True)

        with pytest.raises(ValidationError) as exc_info:
            validator.validate({}, schema="unknown_schema")

        assert "Unknown schema" in str(exc_info.value)

    def test_validate_unknown_schema_non_strict(self):
        """Test unknown schema in non-strict mode."""
        validator = SchemaValidator(strict_mode=False)

        data = {"field": "value"}
        result = validator.validate(data, schema="unknown_schema")

        assert result == data

    def test_register_custom_schema(self):
        """Test registering custom schema."""
        validator = SchemaValidator()

        custom_schema = SchemaDefinition(
            name="custom",
            required_fields=["id", "name"],
            optional_fields=["description"],
        )

        validator.register_schema(custom_schema)

        assert "custom" in validator.list_schemas()

        # Valid custom data
        result = validator.validate(
            {"id": "1", "name": "test"},
            schema="custom",
        )
        assert result["id"] == "1"

    def test_get_schema(self):
        """Test getting schema by name."""
        validator = SchemaValidator()

        schema = validator.get_schema("servicenow")

        assert schema is not None
        assert schema.name == "servicenow"
        assert "number" in schema.required_fields

    def test_get_nonexistent_schema(self):
        """Test getting nonexistent schema."""
        validator = SchemaValidator()

        schema = validator.get_schema("nonexistent")

        assert schema is None

    def test_allow_extra_fields(self):
        """Test allowing extra fields not in schema."""
        validator = SchemaValidator(allow_extra_fields=True)

        data = {
            "number": "INC001",
            "category": "incident",
            "short_description": "Test",
            "custom_field": "value",  # Not in schema
        }

        result = validator.validate(data, schema="servicenow")
        assert result["custom_field"] == "value"

    def test_disallow_extra_fields(self):
        """Test rejecting extra fields."""
        validator = SchemaValidator(
            strict_mode=True,
            allow_extra_fields=False,
        )

        data = {
            "number": "INC001",
            "category": "incident",
            "short_description": "Test",
            "custom_field": "value",  # Not in schema
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="servicenow")

        assert "Unknown field" in str(exc_info.value)


class TestValidationError:
    """Tests for ValidationError class."""

    def test_error_initialization(self):
        """Test error initializes with all attributes."""
        error = ValidationError(
            message="Test error",
            errors=["field1 missing", "field2 wrong type"],
            schema="test_schema",
            data={"field": "value"},
        )

        assert error.message == "Test error"
        assert len(error.errors) == 2
        assert error.schema == "test_schema"
        assert error.data_preview is not None

    def test_error_to_dict(self):
        """Test error serialization."""
        error = ValidationError(
            message="Test error",
            errors=["missing field"],
            schema="test",
        )

        result = error.to_dict()

        assert "message" in result
        assert "errors" in result
        assert "schema" in result

    def test_error_data_truncation(self):
        """Test data preview is truncated for safety."""
        long_value = "x" * 200

        error = ValidationError(
            message="Test",
            data={"field": long_value},
        )

        assert len(error.data_preview["field"]) <= 100


class TestMockSchemaValidator:
    """Tests for MockSchemaValidator."""

    def test_mock_always_passes(self):
        """Test mock validator always passes."""
        validator = MockSchemaValidator()

        data = {}  # Empty data
        result = validator.validate(data, schema="servicenow")

        assert result == data

    def test_mock_passes_invalid_schema(self):
        """Test mock validator passes invalid schema."""
        validator = MockSchemaValidator()

        data = {"field": "value"}
        result = validator.validate(data, schema="nonexistent")

        assert result == data
