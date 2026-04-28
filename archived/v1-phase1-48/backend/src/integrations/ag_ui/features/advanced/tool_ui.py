# =============================================================================
# IPA Platform - Tool-based Generative UI Handler
# =============================================================================
# Sprint 60: AG-UI Advanced Features
# S60-1: Tool-based Generative UI (8 pts)
#
# Provides dynamic UI component generation based on tool execution results.
# Supports form, chart, card, table, and custom component types with
# schema validation and AG-UI event integration.
#
# Key Features:
#   - Dynamic UI component emission via CustomEvent
#   - Schema validation for component definitions
#   - Type-safe component building
#   - Integration with AG-UI event streaming
#
# Dependencies:
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from src.integrations.ag_ui.events import (
    AGUIEventType,
    CustomEvent,
)

logger = logging.getLogger(__name__)


class UIComponentType(str, Enum):
    """Type of UI component to render."""

    FORM = "form"
    CHART = "chart"
    CARD = "card"
    TABLE = "table"
    CUSTOM = "custom"


class ChartType(str, Enum):
    """Type of chart for chart components."""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    DOUGHNUT = "doughnut"


class FormFieldType(str, Enum):
    """Type of form field."""

    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PASSWORD = "password"
    TEXTAREA = "textarea"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DATE = "date"
    DATETIME = "datetime"
    FILE = "file"


@dataclass
class FormFieldDefinition:
    """
    Definition of a form field.

    Attributes:
        name: Field name (used as key in form data)
        label: Display label
        field_type: Type of form field
        required: Whether the field is required
        placeholder: Placeholder text
        default_value: Default value
        options: Options for select/radio fields
        validation: Validation rules
    """

    name: str
    label: str
    field_type: FormFieldType = FormFieldType.TEXT
    required: bool = False
    placeholder: Optional[str] = None
    default_value: Optional[Any] = None
    options: Optional[List[Dict[str, str]]] = None
    validation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "label": self.label,
            "type": self.field_type.value,
            "required": self.required,
        }
        if self.placeholder:
            result["placeholder"] = self.placeholder
        if self.default_value is not None:
            result["defaultValue"] = self.default_value
        if self.options:
            result["options"] = self.options
        if self.validation:
            result["validation"] = self.validation
        return result


@dataclass
class TableColumnDefinition:
    """
    Definition of a table column.

    Attributes:
        key: Column key (matches data key)
        label: Display header
        sortable: Whether column is sortable
        filterable: Whether column is filterable
        width: Column width
        align: Text alignment
    """

    key: str
    label: str
    sortable: bool = False
    filterable: bool = False
    width: Optional[str] = None
    align: str = "left"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "key": self.key,
            "label": self.label,
            "sortable": self.sortable,
            "filterable": self.filterable,
            "align": self.align,
        }
        if self.width:
            result["width"] = self.width
        return result


@dataclass
class UIComponentSchema:
    """
    Schema for UI component validation.

    Attributes:
        component_type: Type of component
        required_fields: Required fields in the definition
        optional_fields: Optional fields in the definition
        validators: Custom validators for fields
    """

    component_type: UIComponentType
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    validators: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def for_form(cls) -> "UIComponentSchema":
        """Create schema for form component."""
        return cls(
            component_type=UIComponentType.FORM,
            required_fields=["fields"],
            optional_fields=["title", "submitLabel", "cancelLabel", "layout"],
            validators={
                "fields": lambda x: isinstance(x, list) and len(x) > 0,
            },
        )

    @classmethod
    def for_chart(cls) -> "UIComponentSchema":
        """Create schema for chart component."""
        return cls(
            component_type=UIComponentType.CHART,
            required_fields=["chartType", "data"],
            optional_fields=["title", "xAxisLabel", "yAxisLabel", "legend", "colors"],
            validators={
                "chartType": lambda x: x in [t.value for t in ChartType],
                "data": lambda x: isinstance(x, (list, dict)),
            },
        )

    @classmethod
    def for_card(cls) -> "UIComponentSchema":
        """Create schema for card component."""
        return cls(
            component_type=UIComponentType.CARD,
            required_fields=["title"],
            optional_fields=["subtitle", "content", "image", "actions", "icon", "footer"],
            validators={
                "title": lambda x: isinstance(x, str) and len(x) > 0,
            },
        )

    @classmethod
    def for_table(cls) -> "UIComponentSchema":
        """Create schema for table component."""
        return cls(
            component_type=UIComponentType.TABLE,
            required_fields=["columns", "data"],
            optional_fields=["title", "pagination", "pageSize", "sortable", "filterable"],
            validators={
                "columns": lambda x: isinstance(x, list) and len(x) > 0,
                "data": lambda x: isinstance(x, list),
            },
        )

    @classmethod
    def for_custom(cls) -> "UIComponentSchema":
        """Create schema for custom component."""
        return cls(
            component_type=UIComponentType.CUSTOM,
            required_fields=["componentName"],
            optional_fields=["props", "children", "styles"],
            validators={
                "componentName": lambda x: isinstance(x, str) and len(x) > 0,
            },
        )

    @classmethod
    def get_schema(cls, component_type: UIComponentType) -> "UIComponentSchema":
        """Get schema for a component type."""
        schemas = {
            UIComponentType.FORM: cls.for_form,
            UIComponentType.CHART: cls.for_chart,
            UIComponentType.CARD: cls.for_card,
            UIComponentType.TABLE: cls.for_table,
            UIComponentType.CUSTOM: cls.for_custom,
        }
        return schemas[component_type]()


@dataclass
class UIComponentDefinition:
    """
    Definition of a UI component to be rendered.

    Attributes:
        component_type: Type of UI component
        component_id: Unique component identifier
        props: Component properties
        title: Optional title
        description: Optional description
        metadata: Additional metadata
        created_at: Creation timestamp
    """

    component_type: UIComponentType
    props: Dict[str, Any]
    component_id: str = field(default_factory=lambda: f"ui-{uuid.uuid4().hex[:12]}")
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "componentId": self.component_id,
            "componentType": self.component_type.value,
            "props": self.props,
            "createdAt": self.created_at,
        }
        if self.title:
            result["title"] = self.title
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UIComponentDefinition":
        """Create from dictionary representation."""
        return cls(
            component_type=UIComponentType(data.get("componentType", "custom")),
            props=data.get("props", {}),
            component_id=data.get("componentId", f"ui-{uuid.uuid4().hex[:12]}"),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
            created_at=data.get("createdAt", time.time()),
        )


@dataclass
class ValidationResult:
    """Result of component validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ToolBasedUIHandler:
    """
    Handler for tool-based generative UI.

    Provides dynamic UI component generation based on tool execution results.
    Integrates with AG-UI event streaming to deliver UI updates to clients.

    Key Features:
    - Emit UI components as AG-UI CustomEvents
    - Schema validation for component definitions
    - Type-safe component building with helper methods
    - Component library management

    Example:
        >>> handler = ToolBasedUIHandler()
        >>> # Create a form component
        >>> form_event = handler.emit_form_component(
        ...     thread_id="thread-123",
        ...     run_id="run-456",
        ...     fields=[
        ...         FormFieldDefinition(name="name", label="Name", required=True),
        ...         FormFieldDefinition(name="email", label="Email", field_type=FormFieldType.EMAIL),
        ...     ],
        ...     title="User Registration",
        ... )
        >>> # Create a chart component
        >>> chart_event = handler.emit_chart_component(
        ...     thread_id="thread-123",
        ...     run_id="run-456",
        ...     chart_type=ChartType.BAR,
        ...     data={"labels": ["A", "B"], "values": [10, 20]},
        ... )
    """

    def __init__(
        self,
        *,
        validate_schema: bool = True,
        strict_mode: bool = False,
    ):
        """
        Initialize ToolBasedUIHandler.

        Args:
            validate_schema: Whether to validate component schemas
            strict_mode: If True, raise exceptions on validation errors
        """
        self._validate_schema = validate_schema
        self._strict_mode = strict_mode
        self._component_registry: Dict[str, UIComponentDefinition] = {}

        logger.info(
            f"ToolBasedUIHandler initialized: "
            f"validate_schema={validate_schema}, strict_mode={strict_mode}"
        )

    @property
    def validate_schema(self) -> bool:
        """Get schema validation setting."""
        return self._validate_schema

    @property
    def strict_mode(self) -> bool:
        """Get strict mode setting."""
        return self._strict_mode

    def get_component(self, component_id: str) -> Optional[UIComponentDefinition]:
        """Get a registered component by ID."""
        return self._component_registry.get(component_id)

    def list_components(self) -> List[UIComponentDefinition]:
        """List all registered components."""
        return list(self._component_registry.values())

    def validate_component_schema(
        self,
        component: UIComponentDefinition,
    ) -> ValidationResult:
        """
        Validate a component against its schema.

        Args:
            component: Component definition to validate

        Returns:
            ValidationResult with is_valid, errors, and warnings
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Get schema for component type
        schema = UIComponentSchema.get_schema(component.component_type)

        # Check required fields
        for field_name in schema.required_fields:
            if field_name not in component.props:
                errors.append(f"Missing required field: {field_name}")

        # Run validators
        for field_name, validator in schema.validators.items():
            if field_name in component.props:
                try:
                    if not validator(component.props[field_name]):
                        errors.append(f"Validation failed for field: {field_name}")
                except Exception as e:
                    errors.append(f"Validator error for {field_name}: {str(e)}")

        # Check for unknown fields (warning only)
        all_known_fields = set(schema.required_fields) | set(schema.optional_fields)
        for field_name in component.props.keys():
            if field_name not in all_known_fields:
                warnings.append(f"Unknown field: {field_name}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _build_component_event(
        self,
        component: UIComponentDefinition,
        thread_id: str,
        run_id: str,
        *,
        action: str = "render",
    ) -> CustomEvent:
        """
        Build a CustomEvent for the component.

        Args:
            component: Component definition
            thread_id: Thread ID
            run_id: Run ID
            action: Event action (render, update, remove)

        Returns:
            CustomEvent with component data
        """
        # Validate if enabled
        if self._validate_schema:
            result = self.validate_component_schema(component)
            if not result.is_valid:
                if self._strict_mode:
                    raise ValueError(f"Component validation failed: {result.errors}")
                else:
                    for error in result.errors:
                        logger.warning(f"Component validation warning: {error}")

        # Register component
        self._component_registry[component.component_id] = component

        # Build event
        return CustomEvent(
            type=AGUIEventType.CUSTOM,
            event_name="ui_component",
            payload={
                "action": action,
                "component": component.to_dict(),
                "threadId": thread_id,
                "runId": run_id,
            },
        )

    def emit_ui_component(
        self,
        component_type: UIComponentType,
        props: Dict[str, Any],
        thread_id: str,
        run_id: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        component_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CustomEvent:
        """
        Emit a generic UI component event.

        Args:
            component_type: Type of component
            props: Component properties
            thread_id: Thread ID
            run_id: Run ID
            title: Optional component title
            description: Optional component description
            component_id: Optional custom component ID
            metadata: Additional metadata

        Returns:
            CustomEvent for the component
        """
        component = UIComponentDefinition(
            component_type=component_type,
            props=props,
            component_id=component_id or f"ui-{uuid.uuid4().hex[:12]}",
            title=title,
            description=description,
            metadata=metadata or {},
        )

        return self._build_component_event(component, thread_id, run_id)

    def emit_form_component(
        self,
        thread_id: str,
        run_id: str,
        fields: List[Union[FormFieldDefinition, Dict[str, Any]]],
        *,
        title: Optional[str] = None,
        submit_label: str = "Submit",
        cancel_label: str = "Cancel",
        layout: str = "vertical",
        on_submit_action: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> CustomEvent:
        """
        Emit a form component event.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            fields: Form field definitions
            title: Form title
            submit_label: Submit button label
            cancel_label: Cancel button label
            layout: Form layout (vertical, horizontal, grid)
            on_submit_action: Action to trigger on submit
            component_id: Optional custom component ID

        Returns:
            CustomEvent for the form
        """
        # Convert fields to dicts if needed
        field_dicts = []
        for f in fields:
            if isinstance(f, FormFieldDefinition):
                field_dicts.append(f.to_dict())
            else:
                field_dicts.append(f)

        props = {
            "fields": field_dicts,
            "submitLabel": submit_label,
            "cancelLabel": cancel_label,
            "layout": layout,
        }
        if on_submit_action:
            props["onSubmitAction"] = on_submit_action

        return self.emit_ui_component(
            component_type=UIComponentType.FORM,
            props=props,
            thread_id=thread_id,
            run_id=run_id,
            title=title,
            component_id=component_id,
        )

    def emit_chart_component(
        self,
        thread_id: str,
        run_id: str,
        chart_type: Union[ChartType, str],
        data: Union[List[Dict[str, Any]], Dict[str, Any]],
        *,
        title: Optional[str] = None,
        x_axis_label: Optional[str] = None,
        y_axis_label: Optional[str] = None,
        legend: bool = True,
        colors: Optional[List[str]] = None,
        component_id: Optional[str] = None,
    ) -> CustomEvent:
        """
        Emit a chart component event.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            chart_type: Type of chart
            data: Chart data
            title: Chart title
            x_axis_label: X-axis label
            y_axis_label: Y-axis label
            legend: Whether to show legend
            colors: Custom color palette
            component_id: Optional custom component ID

        Returns:
            CustomEvent for the chart
        """
        chart_type_str = chart_type.value if isinstance(chart_type, ChartType) else chart_type

        props: Dict[str, Any] = {
            "chartType": chart_type_str,
            "data": data,
            "legend": legend,
        }
        if x_axis_label:
            props["xAxisLabel"] = x_axis_label
        if y_axis_label:
            props["yAxisLabel"] = y_axis_label
        if colors:
            props["colors"] = colors

        return self.emit_ui_component(
            component_type=UIComponentType.CHART,
            props=props,
            thread_id=thread_id,
            run_id=run_id,
            title=title,
            component_id=component_id,
        )

    def emit_card_component(
        self,
        thread_id: str,
        run_id: str,
        title: str,
        *,
        subtitle: Optional[str] = None,
        content: Optional[str] = None,
        image: Optional[str] = None,
        icon: Optional[str] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        footer: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> CustomEvent:
        """
        Emit a card component event.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            title: Card title
            subtitle: Card subtitle
            content: Card content (text or HTML)
            image: Image URL
            icon: Icon name
            actions: Action buttons
            footer: Footer content
            component_id: Optional custom component ID

        Returns:
            CustomEvent for the card
        """
        props: Dict[str, Any] = {"title": title}
        if subtitle:
            props["subtitle"] = subtitle
        if content:
            props["content"] = content
        if image:
            props["image"] = image
        if icon:
            props["icon"] = icon
        if actions:
            props["actions"] = actions
        if footer:
            props["footer"] = footer

        return self.emit_ui_component(
            component_type=UIComponentType.CARD,
            props=props,
            thread_id=thread_id,
            run_id=run_id,
            title=title,
            component_id=component_id,
        )

    def emit_table_component(
        self,
        thread_id: str,
        run_id: str,
        columns: List[Union[TableColumnDefinition, Dict[str, Any]]],
        data: List[Dict[str, Any]],
        *,
        title: Optional[str] = None,
        pagination: bool = True,
        page_size: int = 10,
        sortable: bool = True,
        filterable: bool = False,
        component_id: Optional[str] = None,
    ) -> CustomEvent:
        """
        Emit a table component event.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            columns: Column definitions
            data: Table data rows
            title: Table title
            pagination: Enable pagination
            page_size: Rows per page
            sortable: Enable sorting
            filterable: Enable filtering
            component_id: Optional custom component ID

        Returns:
            CustomEvent for the table
        """
        # Convert columns to dicts if needed
        column_dicts = []
        for col in columns:
            if isinstance(col, TableColumnDefinition):
                column_dicts.append(col.to_dict())
            else:
                column_dicts.append(col)

        props = {
            "columns": column_dicts,
            "data": data,
            "pagination": pagination,
            "pageSize": page_size,
            "sortable": sortable,
            "filterable": filterable,
        }

        return self.emit_ui_component(
            component_type=UIComponentType.TABLE,
            props=props,
            thread_id=thread_id,
            run_id=run_id,
            title=title,
            component_id=component_id,
        )

    def emit_custom_component(
        self,
        thread_id: str,
        run_id: str,
        component_name: str,
        *,
        props: Optional[Dict[str, Any]] = None,
        children: Optional[List[Dict[str, Any]]] = None,
        styles: Optional[Dict[str, str]] = None,
        title: Optional[str] = None,
        component_id: Optional[str] = None,
    ) -> CustomEvent:
        """
        Emit a custom component event.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            component_name: Name of the custom component
            props: Component props
            children: Child components
            styles: Inline styles
            title: Component title
            component_id: Optional custom component ID

        Returns:
            CustomEvent for the custom component
        """
        component_props: Dict[str, Any] = {"componentName": component_name}
        if props:
            component_props["props"] = props
        if children:
            component_props["children"] = children
        if styles:
            component_props["styles"] = styles

        return self.emit_ui_component(
            component_type=UIComponentType.CUSTOM,
            props=component_props,
            thread_id=thread_id,
            run_id=run_id,
            title=title,
            component_id=component_id,
        )

    def emit_update_component(
        self,
        component_id: str,
        thread_id: str,
        run_id: str,
        *,
        props_update: Optional[Dict[str, Any]] = None,
        replace: bool = False,
    ) -> Optional[CustomEvent]:
        """
        Emit an update event for an existing component.

        Args:
            component_id: ID of component to update
            thread_id: Thread ID
            run_id: Run ID
            props_update: Properties to update
            replace: If True, replace all props; if False, merge

        Returns:
            CustomEvent for the update, or None if component not found
        """
        component = self._component_registry.get(component_id)
        if not component:
            logger.warning(f"Component not found for update: {component_id}")
            return None

        # Update props
        if props_update:
            if replace:
                component.props = props_update
            else:
                component.props.update(props_update)

        return CustomEvent(
            type=AGUIEventType.CUSTOM,
            event_name="ui_component",
            payload={
                "action": "update",
                "component": component.to_dict(),
                "threadId": thread_id,
                "runId": run_id,
            },
        )

    def emit_remove_component(
        self,
        component_id: str,
        thread_id: str,
        run_id: str,
    ) -> CustomEvent:
        """
        Emit a remove event for a component.

        Args:
            component_id: ID of component to remove
            thread_id: Thread ID
            run_id: Run ID

        Returns:
            CustomEvent for the removal
        """
        # Remove from registry
        if component_id in self._component_registry:
            del self._component_registry[component_id]

        return CustomEvent(
            type=AGUIEventType.CUSTOM,
            event_name="ui_component",
            payload={
                "action": "remove",
                "componentId": component_id,
                "threadId": thread_id,
                "runId": run_id,
            },
        )

    def clear_components(self) -> None:
        """Clear all registered components."""
        self._component_registry.clear()
        logger.info("Cleared all registered UI components")


def create_tool_ui_handler(
    *,
    validate_schema: bool = True,
    strict_mode: bool = False,
) -> ToolBasedUIHandler:
    """
    Factory function to create ToolBasedUIHandler.

    Args:
        validate_schema: Whether to validate component schemas
        strict_mode: If True, raise exceptions on validation errors

    Returns:
        Configured ToolBasedUIHandler instance
    """
    return ToolBasedUIHandler(
        validate_schema=validate_schema,
        strict_mode=strict_mode,
    )
