"""
MAF ACL — Version Adapter

Provides a singleton adapter that maps stable ACL interfaces
to the current MAF API, handling version differences and
wrapping MAF exceptions into the stable AdapterError hierarchy.

Sprint 128: Story 128-2 — MAF Adapter
"""

import logging
from typing import Any, Dict, Optional, Type

from ..exceptions import (
    AdapterError,
    ExecutionError,
    WorkflowBuildError,
)
from .version_detector import MAFVersionDetector, MAFVersionInfo

logger = logging.getLogger(__name__)


# Builder type name → MAF class name mapping
BUILDER_TYPE_MAP: Dict[str, str] = {
    "groupchat": "GroupChatBuilder",
    "handoff": "HandoffBuilder",
    "concurrent": "ConcurrentBuilder",
    "magentic": "MagenticBuilder",
    "workflow": "WorkflowBuilder",
}


class MAFAdapter:
    """
    Singleton adapter for Microsoft Agent Framework API.

    Maps stable interface calls to the current MAF version's API.
    Handles version detection, API lookup, and exception wrapping.

    Usage:
        >>> adapter = get_maf_adapter()
        >>> if adapter.is_available():
        ...     builder_cls = adapter.create_builder("groupchat")
        ...     builder = builder_cls()
        ...     workflow = builder.build()

    Attributes:
        _version_info: Detected MAF version information
        _detected: Whether version detection has been performed
    """

    def __init__(self) -> None:
        """Initialize MAFAdapter with lazy version detection."""
        self._version_info: Optional[MAFVersionInfo] = None
        self._detected: bool = False

    def _ensure_detected(self) -> MAFVersionInfo:
        """
        Ensure MAF version has been detected.

        Returns:
            MAFVersionInfo from detection

        Note:
            Detection is lazy — only performed on first access.
        """
        if not self._detected:
            self._version_info = MAFVersionDetector.detect()
            self._detected = True
        return self._version_info

    def is_available(self) -> bool:
        """
        Check if MAF package is available.

        Returns:
            True if agent_framework can be imported
        """
        info = self._ensure_detected()
        return info.is_available

    def is_compatible(self) -> bool:
        """
        Check if the installed MAF version is compatible.

        Returns:
            True if compatibility is "full" or "partial"
        """
        info = self._ensure_detected()
        return info.api_compatibility in ("full", "partial")

    def get_version_info(self) -> MAFVersionInfo:
        """
        Get the detected MAF version information.

        Returns:
            MAFVersionInfo with version details
        """
        return self._ensure_detected()

    def create_builder(self, builder_type: str) -> Any:
        """
        Create a MAF builder class by type name.

        Maps the stable builder type name to the current MAF class.

        Args:
            builder_type: Builder type name (e.g., "groupchat", "handoff",
                         "concurrent", "magentic", "workflow")

        Returns:
            The MAF builder class (not an instance)

        Raises:
            AdapterError: If builder type is unknown
            AdapterError: If MAF is not available
            WorkflowBuildError: If the builder class doesn't exist in MAF
        """
        if not self.is_available():
            raise AdapterError(
                "MAF package not available",
                context={"builder_type": builder_type},
            )

        builder_type_lower = builder_type.lower()
        maf_class_name = BUILDER_TYPE_MAP.get(builder_type_lower)

        if maf_class_name is None:
            raise AdapterError(
                f"Unknown builder type: {builder_type}",
                context={
                    "builder_type": builder_type,
                    "valid_types": list(BUILDER_TYPE_MAP.keys()),
                },
            )

        try:
            import agent_framework

            builder_cls = getattr(agent_framework, maf_class_name, None)
            if builder_cls is None:
                raise WorkflowBuildError(
                    f"MAF class not found: {maf_class_name}",
                    context={
                        "builder_type": builder_type,
                        "maf_class": maf_class_name,
                        "version": self._version_info.version if self._version_info else "unknown",
                    },
                )

            logger.debug(f"Created builder: {maf_class_name}")
            return builder_cls

        except ImportError as e:
            raise AdapterError(
                "Failed to import agent_framework",
                original_error=e,
            )

    def wrap_exception(self, error: Exception) -> AdapterError:
        """
        Wrap a MAF exception into the stable AdapterError hierarchy.

        Maps MAF-specific exceptions to the appropriate AdapterError subclass.

        Args:
            error: The original MAF exception

        Returns:
            An AdapterError (or subclass) wrapping the original error
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Map known MAF exception patterns
        if "build" in error_type.lower() or "build" in error_msg.lower():
            return WorkflowBuildError(
                f"MAF build error: {error_msg}",
                original_error=error,
            )

        if "execution" in error_type.lower() or "runtime" in error_type.lower():
            return ExecutionError(
                f"MAF execution error: {error_msg}",
                original_error=error,
            )

        if "timeout" in error_type.lower() or "timeout" in error_msg.lower():
            return ExecutionError(
                f"MAF timeout: {error_msg}",
                original_error=error,
                context={"error_type": "timeout"},
            )

        # Generic fallback
        return AdapterError(
            f"MAF error: {error_msg}",
            original_error=error,
            context={"original_type": error_type},
        )

    def reset(self) -> None:
        """
        Reset the adapter state.

        Clears cached version detection, forcing re-detection on next use.
        Useful for testing or after MAF package changes.
        """
        self._version_info = None
        self._detected = False
        logger.debug("MAFAdapter reset")


# =============================================================================
# Module-level Singleton
# =============================================================================

_maf_adapter_instance: Optional[MAFAdapter] = None


def get_maf_adapter() -> MAFAdapter:
    """
    Get the singleton MAFAdapter instance.

    Creates the adapter on first call, returns the same instance thereafter.

    Returns:
        The singleton MAFAdapter instance
    """
    global _maf_adapter_instance
    if _maf_adapter_instance is None:
        _maf_adapter_instance = MAFAdapter()
    return _maf_adapter_instance
