"""
Schema Validator Implementation

Validates incoming webhook data against predefined schemas.
Supports ServiceNow and Prometheus Alertmanager payload formats.

Sprint 95: Story 95-6 - Implement SchemaValidator (Phase 28)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """
    Exception raised when schema validation fails.

    Attributes:
        message: Human-readable error message
        errors: List of specific validation errors
        schema: The schema that failed validation
        data: The data that failed validation (truncated for safety)
    """

    def __init__(
        self,
        message: str,
        errors: Optional[List[str]] = None,
        schema: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.errors = errors or []
        self.schema = schema
        # Truncate data for safety in logs
        if data:
            self.data_preview = {
                k: str(v)[:100] if isinstance(v, str) else type(v).__name__
                for k, v in list(data.items())[:10]
            }
        else:
            self.data_preview = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message": self.message,
            "errors": self.errors,
            "schema": self.schema,
            "data_preview": self.data_preview,
        }


@dataclass
class SchemaDefinition:
    """
    Definition of a validation schema.

    Attributes:
        name: Schema identifier
        required_fields: Fields that must be present
        optional_fields: Fields that may be present
        nested_requirements: Requirements for nested objects
        field_types: Expected types for fields
        custom_validators: Custom validation functions
    """
    name: str
    required_fields: List[str]
    optional_fields: List[str] = None
    nested_requirements: Dict[str, List[str]] = None
    field_types: Dict[str, type] = None
    description: str = ""

    def __post_init__(self):
        """Initialize default values."""
        if self.optional_fields is None:
            self.optional_fields = []
        if self.nested_requirements is None:
            self.nested_requirements = {}
        if self.field_types is None:
            self.field_types = {}


class SchemaValidator:
    """
    Schema validator for webhook payloads.

    Validates incoming data against predefined schemas for:
    - ServiceNow webhooks
    - Prometheus Alertmanager webhooks
    - User input (optional)

    Provides:
    - Required field validation
    - Type checking
    - Nested object validation
    - Clear error messages

    Example:
        >>> validator = SchemaValidator()
        >>> data = {
        ...     "number": "INC0012345",
        ...     "category": "incident",
        ...     "short_description": "ETL failure"
        ... }
        >>> validated = validator.validate(data, schema="servicenow")
        >>> print(validated)  # Same data if valid

        >>> bad_data = {"category": "incident"}  # missing number
        >>> validator.validate(bad_data, schema="servicenow")
        >>> # Raises ValidationError
    """

    # =============================================================================
    # Predefined Schemas
    # =============================================================================

    SERVICENOW_SCHEMA = SchemaDefinition(
        name="servicenow",
        required_fields=["number", "category", "short_description"],
        optional_fields=[
            "subcategory",
            "priority",
            "assignment_group",
            "assigned_to",
            "state",
            "impact",
            "urgency",
            "description",
            "caller_id",
            "opened_at",
            "closed_at",
            "resolved_at",
            "sys_id",
            "correlation_id",
        ],
        field_types={
            "number": str,
            "category": str,
            "short_description": str,
            "priority": (str, int),  # Can be string or int
        },
        description="ServiceNow incident/request webhook payload",
    )

    PROMETHEUS_SCHEMA = SchemaDefinition(
        name="prometheus",
        required_fields=["alerts"],
        optional_fields=[
            "status",
            "groupKey",
            "externalURL",
            "version",
            "receiver",
            "groupLabels",
            "commonLabels",
            "commonAnnotations",
        ],
        nested_requirements={
            "alerts": ["alertname", "status"],
        },
        field_types={
            "alerts": list,
            "status": str,
        },
        description="Prometheus Alertmanager webhook payload",
    )

    PROMETHEUS_ALERT_SCHEMA = SchemaDefinition(
        name="prometheus_alert",
        required_fields=["alertname", "status"],
        optional_fields=[
            "labels",
            "annotations",
            "startsAt",
            "endsAt",
            "generatorURL",
            "fingerprint",
        ],
        field_types={
            "alertname": str,
            "status": str,
            "labels": dict,
            "annotations": dict,
        },
        description="Individual Prometheus alert within alerts array",
    )

    USER_INPUT_SCHEMA = SchemaDefinition(
        name="user_input",
        required_fields=[],  # No required fields - very flexible
        optional_fields=[
            "text",
            "message",
            "query",
            "description",
            "input",
            "content",
        ],
        description="User input payload (optional validation)",
    )

    def __init__(
        self,
        strict_mode: bool = False,
        allow_extra_fields: bool = True,
    ):
        """
        Initialize SchemaValidator.

        Args:
            strict_mode: If True, raises errors; if False, logs warnings
            allow_extra_fields: If True, ignores fields not in schema
        """
        self.strict_mode = strict_mode
        self.allow_extra_fields = allow_extra_fields

        # Build schema registry
        self._schemas: Dict[str, SchemaDefinition] = {
            "servicenow": self.SERVICENOW_SCHEMA,
            "prometheus": self.PROMETHEUS_SCHEMA,
            "prometheus_alert": self.PROMETHEUS_ALERT_SCHEMA,
            "user_input": self.USER_INPUT_SCHEMA,
            "user": self.USER_INPUT_SCHEMA,
        }

    def register_schema(self, schema: SchemaDefinition) -> None:
        """
        Register a custom schema.

        Args:
            schema: SchemaDefinition to register
        """
        self._schemas[schema.name] = schema
        logger.info(f"Registered schema: {schema.name}")

    def validate(
        self,
        data: Dict[str, Any],
        schema: str,
    ) -> Dict[str, Any]:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema: Schema name to validate against

        Returns:
            The validated data (possibly with type coercion)

        Raises:
            ValidationError: If validation fails and strict_mode is True
        """
        if schema not in self._schemas:
            if self.strict_mode:
                raise ValidationError(
                    f"Unknown schema: {schema}",
                    schema=schema,
                )
            logger.warning(f"Unknown schema: {schema}, skipping validation")
            return data

        schema_def = self._schemas[schema]
        errors: List[str] = []

        # Validate required fields
        errors.extend(self._validate_required_fields(data, schema_def))

        # Validate field types
        errors.extend(self._validate_field_types(data, schema_def))

        # Validate nested requirements
        errors.extend(self._validate_nested(data, schema_def))

        # Check for unknown fields
        if not self.allow_extra_fields:
            errors.extend(self._check_unknown_fields(data, schema_def))

        # Handle validation results
        if errors:
            error_msg = f"Validation failed for schema '{schema}': {'; '.join(errors)}"
            if self.strict_mode:
                raise ValidationError(
                    message=error_msg,
                    errors=errors,
                    schema=schema,
                    data=data,
                )
            else:
                logger.warning(error_msg)

        return data

    def _validate_required_fields(
        self,
        data: Dict[str, Any],
        schema: SchemaDefinition,
    ) -> List[str]:
        """Validate required fields are present."""
        errors = []
        for field in schema.required_fields:
            if field not in data:
                errors.append(f"Missing required field: '{field}'")
            elif data[field] is None:
                errors.append(f"Required field '{field}' is null")
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(f"Required field '{field}' is empty")
        return errors

    def _validate_field_types(
        self,
        data: Dict[str, Any],
        schema: SchemaDefinition,
    ) -> List[str]:
        """Validate field types match expected types."""
        errors = []
        for field, expected_type in schema.field_types.items():
            if field not in data:
                continue

            value = data[field]
            if value is None:
                continue

            # Handle multiple allowed types
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    type_names = [t.__name__ for t in expected_type]
                    errors.append(
                        f"Field '{field}' expected type {' or '.join(type_names)}, "
                        f"got {type(value).__name__}"
                    )
            else:
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Field '{field}' expected type {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )
        return errors

    def _validate_nested(
        self,
        data: Dict[str, Any],
        schema: SchemaDefinition,
    ) -> List[str]:
        """Validate nested object requirements."""
        errors = []
        for parent_field, required_child_fields in schema.nested_requirements.items():
            if parent_field not in data:
                continue

            parent_value = data[parent_field]

            # Handle list of objects (e.g., alerts array)
            if isinstance(parent_value, list):
                for i, item in enumerate(parent_value):
                    if not isinstance(item, dict):
                        errors.append(
                            f"'{parent_field}[{i}]' expected object, got {type(item).__name__}"
                        )
                        continue
                    for child_field in required_child_fields:
                        if child_field not in item:
                            errors.append(
                                f"Missing '{child_field}' in '{parent_field}[{i}]'"
                            )

            # Handle single nested object
            elif isinstance(parent_value, dict):
                for child_field in required_child_fields:
                    if child_field not in parent_value:
                        errors.append(
                            f"Missing '{child_field}' in nested '{parent_field}'"
                        )

        return errors

    def _check_unknown_fields(
        self,
        data: Dict[str, Any],
        schema: SchemaDefinition,
    ) -> List[str]:
        """Check for fields not defined in schema."""
        errors = []
        known_fields = set(schema.required_fields) | set(schema.optional_fields)
        for field in data:
            if field not in known_fields:
                errors.append(f"Unknown field: '{field}'")
        return errors

    def get_schema(self, name: str) -> Optional[SchemaDefinition]:
        """Get a schema by name."""
        return self._schemas.get(name)

    def list_schemas(self) -> List[str]:
        """List all registered schema names."""
        return list(self._schemas.keys())


class MockSchemaValidator(SchemaValidator):
    """
    Mock schema validator for testing.

    Always passes validation without checks.
    """

    def __init__(self):
        """Initialize mock validator."""
        super().__init__(strict_mode=False, allow_extra_fields=True)

    def validate(
        self,
        data: Dict[str, Any],
        schema: str,
    ) -> Dict[str, Any]:
        """Always return data without validation."""
        return data


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "SchemaValidator",
    "MockSchemaValidator",
    "SchemaDefinition",
    "ValidationError",
]
