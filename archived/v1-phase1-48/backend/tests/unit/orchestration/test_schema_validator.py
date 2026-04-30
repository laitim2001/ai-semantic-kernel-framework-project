"""
Tests for SchemaValidator

Comprehensive test coverage for:
- SchemaDefinition creation and listing
- ServiceNow payload validation (valid and invalid)
- Prometheus payload validation (valid and invalid)
- User input validation (flexible schema)
- Custom schema registration
- Strict mode and field type validation

Sprint 130: S130-3 - Schema Validator Tests
"""

import pytest

from src.integrations.orchestration.input_gateway.schema_validator import (
    SchemaValidator,
    SchemaDefinition,
    ValidationError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def validator() -> SchemaValidator:
    """Create a SchemaValidator in strict mode for clear error detection."""
    return SchemaValidator(strict_mode=True, allow_extra_fields=True)


@pytest.fixture
def lenient_validator() -> SchemaValidator:
    """Create a SchemaValidator in lenient mode (logs warnings, no exceptions)."""
    return SchemaValidator(strict_mode=False, allow_extra_fields=True)


# =============================================================================
# TestSchemaDefinition
# =============================================================================


class TestSchemaDefinition:
    """Test SchemaDefinition creation and listing."""

    def test_schema_definition_creation(self):
        """Creating a SchemaDefinition should set required and optional fields."""
        schema = SchemaDefinition(
            name="test_schema",
            required_fields=["field_a", "field_b"],
            optional_fields=["field_c", "field_d"],
            description="A test schema for validation",
        )

        assert schema.name == "test_schema"
        assert schema.required_fields == ["field_a", "field_b"]
        assert schema.optional_fields == ["field_c", "field_d"]
        assert schema.description == "A test schema for validation"
        assert schema.nested_requirements == {}
        assert schema.field_types == {}

    def test_list_schemas(self, validator: SchemaValidator):
        """list_schemas should return all registered schema names."""
        schema_names = validator.list_schemas()

        assert isinstance(schema_names, list)
        assert "servicenow" in schema_names
        assert "prometheus" in schema_names
        assert "prometheus_alert" in schema_names
        assert "user_input" in schema_names
        assert "user" in schema_names


# =============================================================================
# TestServiceNowValidation
# =============================================================================


class TestServiceNowValidation:
    """Test ServiceNow payload validation."""

    def test_servicenow_valid(self, validator: SchemaValidator):
        """Valid ServiceNow data with all required fields should pass."""
        data = {
            "number": "INC0012345",
            "category": "incident",
            "short_description": "ETL batch job failure at 03:00 AM",
            "subcategory": "software",
            "priority": "2",
        }

        result = validator.validate(data, schema="servicenow")

        assert result == data
        assert result["number"] == "INC0012345"
        assert result["category"] == "incident"
        assert result["short_description"] == "ETL batch job failure at 03:00 AM"

    def test_servicenow_missing_required(self, validator: SchemaValidator):
        """Missing required field 'number' should raise ValidationError."""
        data = {
            "category": "incident",
            "short_description": "Something broke",
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="servicenow")

        error = exc_info.value
        assert "number" in error.message
        assert error.schema == "servicenow"
        assert len(error.errors) >= 1
        assert any("number" in e for e in error.errors)

    def test_servicenow_empty_required_field(self, validator: SchemaValidator):
        """Empty string in a required field should raise ValidationError."""
        data = {
            "number": "INC0012345",
            "category": "incident",
            "short_description": "",
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="servicenow")

        error = exc_info.value
        assert any("short_description" in e for e in error.errors)


# =============================================================================
# TestPrometheusValidation
# =============================================================================


class TestPrometheusValidation:
    """Test Prometheus Alertmanager payload validation."""

    def test_prometheus_valid(self, validator: SchemaValidator):
        """Valid Prometheus data with alerts array should pass."""
        data = {
            "status": "firing",
            "alerts": [
                {
                    "alertname": "HighCPUUsage",
                    "status": "firing",
                    "labels": {"severity": "critical"},
                    "annotations": {"summary": "CPU > 90%"},
                },
            ],
            "groupLabels": {"alertname": "HighCPUUsage"},
        }

        result = validator.validate(data, schema="prometheus")

        assert result == data
        assert result["status"] == "firing"
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["alertname"] == "HighCPUUsage"

    def test_prometheus_missing_alerts(self, validator: SchemaValidator):
        """Missing required 'alerts' field should raise ValidationError."""
        data = {
            "status": "firing",
            "groupLabels": {"alertname": "Test"},
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="prometheus")

        error = exc_info.value
        assert "alerts" in error.message
        assert error.schema == "prometheus"

    def test_prometheus_alerts_missing_nested_fields(self, validator: SchemaValidator):
        """Alerts items missing required nested fields should raise ValidationError."""
        data = {
            "alerts": [
                {
                    "status": "firing",
                    # missing "alertname" which is required by nested_requirements
                },
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data, schema="prometheus")

        error = exc_info.value
        assert any("alertname" in e for e in error.errors)


# =============================================================================
# TestUserInputValidation
# =============================================================================


class TestUserInputValidation:
    """Test user input validation (flexible schema)."""

    def test_user_input_flexible(self, validator: SchemaValidator):
        """User input schema has no required fields; any data should pass."""
        data_minimal = {}
        result_minimal = validator.validate(data_minimal, schema="user_input")
        assert result_minimal == data_minimal

        data_with_text = {"text": "Help me with something"}
        result_text = validator.validate(data_with_text, schema="user_input")
        assert result_text == data_with_text

        data_with_extras = {
            "message": "ETL 失敗了",
            "user_id": "user-123",
            "extra_field": True,
        }
        result_extras = validator.validate(data_with_extras, schema="user_input")
        assert result_extras == data_with_extras

    def test_user_input_alias(self, validator: SchemaValidator):
        """'user' schema alias should also work for user input."""
        data = {"query": "查詢系統狀態"}
        result = validator.validate(data, schema="user")
        assert result == data


# =============================================================================
# TestCustomSchema
# =============================================================================


class TestCustomSchema:
    """Test custom schema registration and validation."""

    def test_register_custom_schema(self, validator: SchemaValidator):
        """Registering a custom schema should make it available for validation."""
        custom_schema = SchemaDefinition(
            name="custom_webhook",
            required_fields=["event_type", "payload"],
            optional_fields=["timestamp", "source"],
            description="Custom webhook schema",
        )

        validator.register_schema(custom_schema)

        assert "custom_webhook" in validator.list_schemas()

        # Valid data should pass
        valid_data = {
            "event_type": "deployment",
            "payload": {"version": "1.2.3"},
            "timestamp": "2026-02-25T10:00:00Z",
        }
        result = validator.validate(valid_data, schema="custom_webhook")
        assert result == valid_data

        # Missing required field should raise ValidationError
        invalid_data = {"event_type": "deployment"}
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(invalid_data, schema="custom_webhook")
        assert "payload" in exc_info.value.message

    def test_strict_mode_rejects_unknown_fields(self):
        """Strict mode with allow_extra_fields=False should reject unknown fields."""
        strict_validator = SchemaValidator(
            strict_mode=True,
            allow_extra_fields=False,
        )

        # Register a minimal schema
        minimal_schema = SchemaDefinition(
            name="minimal",
            required_fields=["name"],
            optional_fields=["description"],
        )
        strict_validator.register_schema(minimal_schema)

        # Data with unknown field should raise ValidationError
        data_with_unknown = {
            "name": "test",
            "unknown_field": "should not be here",
        }

        with pytest.raises(ValidationError) as exc_info:
            strict_validator.validate(data_with_unknown, schema="minimal")

        error = exc_info.value
        assert any("unknown_field" in e for e in error.errors)

    def test_field_type_validation(self, validator: SchemaValidator):
        """Wrong field type should raise ValidationError."""
        # ServiceNow schema expects "number" to be str
        data_wrong_type = {
            "number": 12345,  # Should be str, not int
            "category": "incident",
            "short_description": "Test incident",
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate(data_wrong_type, schema="servicenow")

        error = exc_info.value
        assert any("number" in e and "str" in e for e in error.errors)


# =============================================================================
# TestValidationError
# =============================================================================


class TestValidationError:
    """Test ValidationError structure and serialization."""

    def test_validation_error_to_dict(self):
        """ValidationError.to_dict should return complete error information."""
        error = ValidationError(
            message="Validation failed for schema 'test'",
            errors=["Missing required field: 'name'", "Missing required field: 'value'"],
            schema="test",
            data={"partial_field": "some_value"},
        )

        result = error.to_dict()

        assert isinstance(result, dict)
        assert result["message"] == "Validation failed for schema 'test'"
        assert len(result["errors"]) == 2
        assert result["schema"] == "test"
        assert result["data_preview"] is not None

    def test_validation_error_inherits_exception(self):
        """ValidationError should be catchable as a standard Exception."""
        with pytest.raises(Exception):
            raise ValidationError("Test error")


# =============================================================================
# TestLenientMode
# =============================================================================


class TestLenientMode:
    """Test lenient mode (warnings instead of exceptions)."""

    def test_lenient_mode_returns_data_on_validation_failure(
        self, lenient_validator: SchemaValidator
    ):
        """In lenient mode, invalid data should still be returned (with warning logged)."""
        data = {
            "category": "incident",
            "short_description": "Missing number field",
        }

        # Should NOT raise, just log a warning
        result = lenient_validator.validate(data, schema="servicenow")
        assert result == data

    def test_lenient_mode_unknown_schema(self, lenient_validator: SchemaValidator):
        """In lenient mode, unknown schema should return data without error."""
        data = {"any": "data"}
        result = lenient_validator.validate(data, schema="nonexistent_schema")
        assert result == data
