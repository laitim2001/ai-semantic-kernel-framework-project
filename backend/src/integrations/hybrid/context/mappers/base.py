# =============================================================================
# IPA Platform - Base Mapper
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Abstract base class for context mappers.
#
# Provides:
#   - Common mapping utilities
#   - Error handling patterns
#   - Logging configuration
# =============================================================================

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")
U = TypeVar("U")


class MappingError(Exception):
    """Exception raised when mapping fails."""

    def __init__(
        self,
        message: str,
        source_type: str,
        target_type: str,
        field: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.source_type = source_type
        self.target_type = target_type
        self.field = field
        self.original_error = original_error


class BaseMapper(ABC, Generic[T, U]):
    """
    Abstract base class for context mappers.

    Provides common utilities for mapping between MAF and Claude contexts.

    Type Parameters:
        T: Source type
        U: Target type
    """

    def __init__(self, strict: bool = False):
        """
        Initialize mapper.

        Args:
            strict: If True, raise errors on mapping failures.
                   If False, log warnings and continue with defaults.
        """
        self.strict = strict
        self._error_count = 0
        self._warning_count = 0

    @abstractmethod
    def map(self, source: T) -> U:
        """
        Map source to target type.

        Args:
            source: Source object to map

        Returns:
            Mapped target object
        """
        ...

    def reset_counters(self) -> None:
        """Reset error and warning counters."""
        self._error_count = 0
        self._warning_count = 0

    @property
    def error_count(self) -> int:
        """Get number of errors during last mapping."""
        return self._error_count

    @property
    def warning_count(self) -> int:
        """Get number of warnings during last mapping."""
        return self._warning_count

    def _safe_get(
        self,
        data: Dict[str, Any],
        key: str,
        default: Any = None,
        expected_type: Optional[type] = None,
    ) -> Any:
        """
        Safely get value from dictionary with type checking.

        Args:
            data: Source dictionary
            key: Key to retrieve
            default: Default value if key not found
            expected_type: Expected type of value

        Returns:
            Value or default
        """
        value = data.get(key, default)

        if value is None:
            return default

        if expected_type is not None and not isinstance(value, expected_type):
            self._warning_count += 1
            logger.warning(
                f"Type mismatch for key '{key}': expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
            if self.strict:
                raise MappingError(
                    f"Type mismatch for key '{key}'",
                    source_type="dict",
                    target_type=expected_type.__name__,
                    field=key,
                )
            return default

        return value

    def _safe_map_list(
        self,
        items: List[Any],
        map_func: callable,
        context: str = "list",
    ) -> List[Any]:
        """
        Safely map list items, handling errors per item.

        Args:
            items: List of items to map
            map_func: Function to map each item
            context: Context string for error messages

        Returns:
            List of mapped items (failed items excluded in non-strict mode)
        """
        results = []
        for i, item in enumerate(items):
            try:
                results.append(map_func(item))
            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to map {context}[{i}]: {e}")
                if self.strict:
                    raise MappingError(
                        f"Failed to map {context}[{i}]",
                        source_type=type(item).__name__,
                        target_type="unknown",
                        field=f"{context}[{i}]",
                        original_error=e,
                    )
        return results

    def _truncate_string(
        self,
        value: str,
        max_length: int,
        suffix: str = "...",
    ) -> str:
        """
        Truncate string to maximum length.

        Args:
            value: String to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated string
        """
        if len(value) <= max_length:
            return value
        return value[: max_length - len(suffix)] + suffix

    def _parse_datetime(
        self,
        value: Any,
        default: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        Parse datetime from various formats.

        Args:
            value: Value to parse (str, datetime, or timestamp)
            default: Default value if parsing fails

        Returns:
            Parsed datetime or default
        """
        if value is None:
            return default

        if isinstance(value, datetime):
            return value

        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except (ValueError, OSError):
                self._warning_count += 1
                return default

        if isinstance(value, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try other common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

            self._warning_count += 1
            logger.warning(f"Could not parse datetime: {value}")
            return default

        return default

    def _format_datetime(
        self,
        dt: Optional[datetime],
        format: str = "iso",
    ) -> Optional[str]:
        """
        Format datetime to string.

        Args:
            dt: Datetime to format
            format: Format type ("iso", "readable", "timestamp")

        Returns:
            Formatted string or None
        """
        if dt is None:
            return None

        if format == "iso":
            return dt.isoformat()
        elif format == "readable":
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif format == "timestamp":
            return str(int(dt.timestamp()))
        else:
            return dt.isoformat()

    def _merge_dicts(
        self,
        base: Dict[str, Any],
        updates: Dict[str, Any],
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """
        Merge two dictionaries.

        Args:
            base: Base dictionary
            updates: Dictionary with updates
            overwrite: Whether to overwrite existing keys

        Returns:
            Merged dictionary
        """
        result = dict(base)
        for key, value in updates.items():
            if overwrite or key not in result:
                result[key] = value
        return result

    def _prefix_keys(
        self,
        data: Dict[str, Any],
        prefix: str,
    ) -> Dict[str, Any]:
        """
        Add prefix to all dictionary keys.

        Args:
            data: Source dictionary
            prefix: Prefix to add

        Returns:
            Dictionary with prefixed keys
        """
        return {f"{prefix}{key}": value for key, value in data.items()}

    def _unprefix_keys(
        self,
        data: Dict[str, Any],
        prefix: str,
    ) -> Dict[str, Any]:
        """
        Remove prefix from dictionary keys.

        Args:
            data: Source dictionary
            prefix: Prefix to remove

        Returns:
            Dictionary with unprefixed keys
        """
        result = {}
        for key, value in data.items():
            if key.startswith(prefix):
                result[key[len(prefix) :]] = value
            else:
                result[key] = value
        return result
