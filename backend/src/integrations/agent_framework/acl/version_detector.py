"""
MAF ACL — Version Detection

Detects the installed Microsoft Agent Framework version
and checks API compatibility.

Sprint 128: Story 128-2 — MAF Version Detection
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Known compatible MAF versions
KNOWN_COMPATIBLE: Dict[str, str] = {
    "1.0.0b251204": "full",       # Dec 2025 preview — tested
    "1.0.0b250101": "partial",    # Jan 2026 preview — untested
}

# Minimum required version
MINIMUM_VERSION = "1.0.0"


@dataclass(frozen=True)
class MAFVersionInfo:
    """
    Frozen dataclass containing MAF version information.

    Attributes:
        version: Full version string (e.g., "1.0.0b251204")
        is_preview: Whether this is a preview/beta version
        major: Major version number
        minor: Minor version number
        patch: Patch version number
        preview_tag: Preview tag string (e.g., "b251204")
        is_available: Whether the agent_framework package is importable
        api_compatibility: Compatibility level ("full", "partial", "unknown", "unavailable")
    """

    version: str = ""
    is_preview: bool = False
    major: int = 0
    minor: int = 0
    patch: int = 0
    preview_tag: str = ""
    is_available: bool = False
    api_compatibility: str = "unavailable"


class MAFVersionDetector:
    """
    Detects installed MAF version and checks API compatibility.

    Provides methods to:
    - Detect the installed agent_framework version
    - Parse version components
    - Check compatibility against known versions
    - Verify specific API availability

    Example:
        >>> info = MAFVersionDetector.detect()
        >>> print(info.version)         # "1.0.0b251204"
        >>> print(info.is_available)    # True
        >>> print(info.api_compatibility)  # "full"
        >>>
        >>> MAFVersionDetector.check_api_available("GroupChatBuilder")  # True
    """

    @classmethod
    def detect(cls) -> MAFVersionInfo:
        """
        Detect the installed MAF version.

        Attempts to import agent_framework and read its __version__.
        Returns MAFVersionInfo with is_available=False if import fails.

        Returns:
            MAFVersionInfo with detected version details
        """
        try:
            import agent_framework

            version_str = getattr(agent_framework, "__version__", "0.0.0")
            parsed = cls._parse_version(version_str)

            compatibility = KNOWN_COMPATIBLE.get(version_str, "unknown")

            info = MAFVersionInfo(
                version=version_str,
                is_preview=parsed["is_preview"],
                major=parsed["major"],
                minor=parsed["minor"],
                patch=parsed["patch"],
                preview_tag=parsed["preview_tag"],
                is_available=True,
                api_compatibility=compatibility,
            )

            logger.info(
                f"MAF detected: version={version_str}, "
                f"compatibility={compatibility}"
            )
            return info

        except ImportError:
            logger.warning("agent_framework package not available")
            return MAFVersionInfo(
                is_available=False,
                api_compatibility="unavailable",
            )
        except Exception as e:
            logger.error(f"MAF version detection error: {e}")
            return MAFVersionInfo(
                is_available=False,
                api_compatibility="unavailable",
            )

    @classmethod
    def check_api_available(cls, api_name: str) -> bool:
        """
        Check if a specific MAF API class/function exists.

        Args:
            api_name: Name of the class or function to check
                      (e.g., "GroupChatBuilder", "WorkflowBuilder")

        Returns:
            True if the API is available, False otherwise
        """
        try:
            import agent_framework
            return hasattr(agent_framework, api_name)
        except ImportError:
            return False

    @classmethod
    def get_available_apis(cls) -> List[str]:
        """
        Get list of available MAF API names.

        Returns:
            List of available API class/function names
        """
        expected_apis = [
            "WorkflowBuilder",
            "Executor",
            "Edge",
            "Workflow",
            "handler",
            "ConcurrentBuilder",
            "GroupChatBuilder",
            "HandoffBuilder",
            "MagenticBuilder",
            "ChatAgent",
            "BaseAgent",
            "CheckpointStorage",
        ]

        available = []
        try:
            import agent_framework
            for api_name in expected_apis:
                if hasattr(agent_framework, api_name):
                    available.append(api_name)
        except ImportError:
            pass

        return available

    @classmethod
    def _parse_version(cls, version_str: str) -> Dict[str, Any]:
        """
        Parse a version string into components.

        Handles formats like:
        - "1.0.0"
        - "1.0.0b251204"
        - "0.1.0-preview"

        Args:
            version_str: Version string to parse

        Returns:
            Dictionary with major, minor, patch, is_preview, preview_tag
        """
        result = {
            "major": 0,
            "minor": 0,
            "patch": 0,
            "is_preview": False,
            "preview_tag": "",
        }

        # Match version pattern: major.minor.patch[bNNNNNN | -preview | ...]
        match = re.match(
            r"(\d+)\.(\d+)\.(\d+)(?:[.-]?(b\d+|preview|alpha|beta|rc\d*))?",
            version_str,
        )
        if match:
            result["major"] = int(match.group(1))
            result["minor"] = int(match.group(2))
            result["patch"] = int(match.group(3))

            if match.group(4):
                result["is_preview"] = True
                result["preview_tag"] = match.group(4)

        return result

    @classmethod
    def is_compatible(cls, version_info: Optional[MAFVersionInfo] = None) -> bool:
        """
        Check if the installed MAF version is compatible.

        Args:
            version_info: Pre-detected version info. Detects if None.

        Returns:
            True if compatible (full or partial), False otherwise
        """
        if version_info is None:
            version_info = cls.detect()

        return version_info.api_compatibility in ("full", "partial")
