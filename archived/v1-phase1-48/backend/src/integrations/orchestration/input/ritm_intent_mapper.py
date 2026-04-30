"""
RITM to IPA Intent Mapper.

Sprint 114: AD 場景基礎建設 (Phase 32)
Maps ServiceNow Requested Item (RITM) events to IPA Business Intents
using YAML-based configuration.

Features:
    - YAML-driven mapping configuration
    - Variable extraction with nested path support
    - Fallback strategy for unmapped catalog items
    - Case-insensitive catalog item matching
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .servicenow_webhook import ServiceNowRITMEvent

logger = logging.getLogger(__name__)


@dataclass
class IntentMappingResult:
    """Result of RITM to intent mapping.

    Attributes:
        matched: Whether a mapping was found
        intent: Mapped IPA business intent identifier
        variables: Extracted business variables
        cat_item_name: Original catalog item name
        fallback_used: Whether fallback strategy was used
        fallback_strategy: Name of fallback strategy if used
    """

    matched: bool
    intent: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    cat_item_name: str = ""
    fallback_used: bool = False
    fallback_strategy: str = ""


class RITMIntentMapper:
    """Maps ServiceNow RITM events to IPA business intents.

    Loads mapping configuration from YAML and provides:
    - Catalog item name to intent mapping
    - Variable extraction from RITM events
    - Configurable fallback for unmapped items

    Example:
        >>> mapper = RITMIntentMapper()
        >>> result = mapper.map_ritm_to_intent(event)
        >>> print(result.intent)  # "ad.account.unlock"
    """

    def __init__(
        self,
        mappings_path: Optional[str] = None,
        mappings_dict: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the mapper.

        Args:
            mappings_path: Path to YAML mappings file
            mappings_dict: Direct mapping dictionary (overrides file)
        """
        self._mappings: List[Dict[str, Any]] = []
        self._fallback: Dict[str, Any] = {
            "strategy": "semantic_router",
            "log_unmatched": True,
        }
        # Build case-insensitive lookup index
        self._lookup: Dict[str, Dict[str, Any]] = {}

        if mappings_dict is not None:
            self._load_from_dict(mappings_dict)
        elif mappings_path:
            self._load_from_file(mappings_path)
        else:
            # Default: load from package directory
            default_path = str(
                Path(__file__).parent / "ritm_mappings.yaml"
            )
            self._load_from_file(default_path)

    def _load_from_file(self, path: str) -> None:
        """Load mappings from YAML file.

        Args:
            path: Path to YAML file
        """
        file_path = Path(path)
        if not file_path.exists():
            logger.warning(f"Mappings file not found: {path}")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                self._load_from_dict(data)
            logger.info(
                f"Loaded {len(self._mappings)} RITM mappings from {path}"
            )
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML mappings: {e}")
            raise ValueError(f"Invalid YAML in mappings file: {e}")

    def _load_from_dict(self, data: Dict[str, Any]) -> None:
        """Load mappings from dictionary.

        Args:
            data: Mapping configuration dictionary
        """
        self._mappings = data.get("mappings", [])
        self._fallback = data.get("fallback", self._fallback)

        # Build lookup index (case-insensitive)
        self._lookup = {}
        for mapping in self._mappings:
            key = mapping.get("cat_item_name", "").strip().lower()
            if key:
                self._lookup[key] = mapping

    def map_ritm_to_intent(
        self, event: ServiceNowRITMEvent
    ) -> IntentMappingResult:
        """Map a RITM event to an IPA business intent.

        Attempts exact match (case-insensitive) on cat_item_name,
        then falls back to configured strategy.

        Args:
            event: ServiceNow RITM event

        Returns:
            IntentMappingResult with mapped intent and extracted variables
        """
        cat_item_name = event.cat_item_name.strip()
        lookup_key = cat_item_name.lower()

        mapping = self._lookup.get(lookup_key)

        if mapping:
            variables = self._extract_variables(event, mapping)
            logger.info(
                f"RITM mapped: {event.number} "
                f"({cat_item_name}) → {mapping['intent']}"
            )
            return IntentMappingResult(
                matched=True,
                intent=mapping["intent"],
                variables=variables,
                cat_item_name=cat_item_name,
            )

        # Fallback
        if self._fallback.get("log_unmatched", True):
            logger.warning(
                f"No mapping for catalog item: {cat_item_name} "
                f"(RITM: {event.number})"
            )

        return IntentMappingResult(
            matched=False,
            cat_item_name=cat_item_name,
            fallback_used=True,
            fallback_strategy=self._fallback.get("strategy", "unknown"),
        )

    def _extract_variables(
        self,
        event: ServiceNowRITMEvent,
        mapping: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract business variables from RITM event.

        Supports nested path syntax:
        - "field_name" → getattr(event, field_name)
        - "variables.key" → event.variables.get(key)

        Args:
            event: ServiceNow RITM event
            mapping: Mapping configuration with extract_variables

        Returns:
            Extracted variables dictionary
        """
        extract_config = mapping.get("extract_variables", {})
        variables: Dict[str, Any] = {}

        for var_name, path in extract_config.items():
            value = self._resolve_path(event, path)
            if value is not None:
                variables[var_name] = value
            else:
                logger.debug(
                    f"Variable not found: {var_name} (path={path})"
                )

        return variables

    def _resolve_path(
        self,
        event: ServiceNowRITMEvent,
        path: str,
    ) -> Any:
        """Resolve a dotted path against an event.

        Args:
            event: ServiceNow RITM event
            path: Dotted path string (e.g., "variables.affected_user")

        Returns:
            Resolved value or None
        """
        parts = path.split(".")

        if len(parts) == 1:
            # Top-level field
            return getattr(event, parts[0], None)

        if parts[0] == "variables" and len(parts) == 2:
            # variables.key
            return event.variables.get(parts[1])

        # Deep nested path
        current: Any = event
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            if current is None:
                return None

        return current

    def get_mappings_count(self) -> int:
        """Get the number of loaded mappings."""
        return len(self._mappings)

    def get_supported_intents(self) -> List[str]:
        """Get list of all supported intent identifiers."""
        return [m["intent"] for m in self._mappings if "intent" in m]

    def get_fallback_strategy(self) -> str:
        """Get the configured fallback strategy name."""
        return self._fallback.get("strategy", "unknown")
