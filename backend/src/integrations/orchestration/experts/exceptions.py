"""Exceptions for the Agent Expert Registry.

Sprint 158 — Phase 46 Agent Expert Registry.
"""


class ExpertDefinitionError(Exception):
    """Base exception for expert definition errors."""

    pass


class ExpertNotFoundError(ExpertDefinitionError):
    """Raised when a requested expert is not found in the registry."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Expert not found: {name}")


class ExpertSchemaValidationError(ExpertDefinitionError):
    """Raised when a YAML expert definition fails schema validation."""

    def __init__(self, file_path: str, reason: str) -> None:
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Schema validation failed for {file_path}: {reason}")
