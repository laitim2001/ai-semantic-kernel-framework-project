# =============================================================================
# IPA Platform - Hybrid Execution: Tool Router
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor
#
# Intelligent Tool Router for Hybrid MAF + Claude SDK Architecture.
# Routes tool calls to appropriate execution paths based on source,
# tool capabilities, and routing rules.
#
# Dependencies:
#   - ToolSource (src.integrations.hybrid.execution.unified_executor)
#   - ToolRegistry (src.integrations.claude_sdk.tools)
# =============================================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .unified_executor import ToolSource


class RoutingStrategy(Enum):
    """Tool routing strategies."""

    PREFER_CLAUDE = "prefer_claude"  # 優先使用 Claude SDK
    PREFER_MAF = "prefer_maf"  # 優先使用 MAF
    CAPABILITY_BASED = "capability_based"  # 根據工具能力決定
    LOAD_BALANCED = "load_balanced"  # 負載均衡
    EXPLICIT = "explicit"  # 明確指定


@dataclass
class RoutingRule:
    """
    Routing rule definition.

    Defines conditions and target source for tool routing.

    Attributes:
        name: Rule name for identification
        pattern: Tool name pattern (supports wildcards: * and ?)
        target_source: Target execution source
        priority: Rule priority (higher = evaluated first)
        condition: Optional callable for dynamic evaluation
        enabled: Whether rule is active
    """

    name: str
    pattern: str
    target_source: ToolSource
    priority: int = 0
    condition: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    enabled: bool = True


@dataclass
class RoutingDecision:
    """
    Result of routing decision.

    Contains the routing decision and metadata about the decision process.

    Attributes:
        tool_name: Name of the tool being routed
        source: Determined execution source
        rule_applied: Name of the rule that was applied (if any)
        fallback_sources: Alternative sources if primary fails
        metadata: Additional routing metadata
    """

    tool_name: str
    source: ToolSource
    rule_applied: Optional[str] = None
    fallback_sources: List[ToolSource] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRouter:
    """
    Intelligent Tool Router for hybrid execution.

    Routes tool calls to appropriate execution source based on:
    - Explicit routing rules
    - Tool capabilities
    - Current system state
    - Load balancing considerations

    Example:
        >>> router = ToolRouter()
        >>> router.add_rule(RoutingRule(
        ...     name="maf_tools",
        ...     pattern="maf_*",
        ...     target_source=ToolSource.MAF,
        ...     priority=100
        ... ))
        >>> decision = router.route("maf_search", {"query": "test"})
        >>> print(decision.source)  # ToolSource.MAF
    """

    def __init__(
        self,
        default_strategy: RoutingStrategy = RoutingStrategy.PREFER_CLAUDE,
        default_source: ToolSource = ToolSource.CLAUDE,
    ):
        """
        Initialize ToolRouter.

        Args:
            default_strategy: Default routing strategy when no rules match
            default_source: Default source when strategy is EXPLICIT
        """
        self._rules: List[RoutingRule] = []
        self._default_strategy = default_strategy
        self._default_source = default_source

        # Tool capability mappings
        self._maf_tools: Set[str] = set()
        self._claude_tools: Set[str] = set()
        self._hybrid_tools: Set[str] = set()

        # Load balancing state
        self._call_counts: Dict[ToolSource, int] = {
            ToolSource.MAF: 0,
            ToolSource.CLAUDE: 0,
            ToolSource.HYBRID: 0,
        }

    def add_rule(self, rule: RoutingRule) -> None:
        """
        Add a routing rule.

        Args:
            rule: Routing rule to add
        """
        self._rules.append(rule)
        # Sort by priority (descending)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove a routing rule by name.

        Args:
            rule_name: Name of the rule to remove

        Returns:
            True if rule was found and removed, False otherwise
        """
        original_count = len(self._rules)
        self._rules = [r for r in self._rules if r.name != rule_name]
        return len(self._rules) < original_count

    def register_tool_capability(
        self,
        tool_name: str,
        source: ToolSource,
    ) -> None:
        """
        Register a tool's capability/availability for a source.

        Args:
            tool_name: Name of the tool
            source: Source where tool is available
        """
        if source == ToolSource.MAF:
            self._maf_tools.add(tool_name)
        elif source == ToolSource.CLAUDE:
            self._claude_tools.add(tool_name)
        elif source == ToolSource.HYBRID:
            self._hybrid_tools.add(tool_name)

    def register_tools_batch(
        self,
        tool_names: List[str],
        source: ToolSource,
    ) -> None:
        """
        Register multiple tools for a source.

        Args:
            tool_names: List of tool names
            source: Source where tools are available
        """
        for name in tool_names:
            self.register_tool_capability(name, source)

    def route(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        hint_source: Optional[ToolSource] = None,
    ) -> RoutingDecision:
        """
        Route a tool call to appropriate source.

        Args:
            tool_name: Name of the tool to route
            arguments: Tool arguments (for conditional routing)
            hint_source: Optional hint for preferred source

        Returns:
            RoutingDecision with determined source and metadata
        """
        # Check explicit hint first
        if hint_source is not None:
            return RoutingDecision(
                tool_name=tool_name,
                source=hint_source,
                rule_applied="explicit_hint",
                fallback_sources=self._get_fallback_sources(hint_source, tool_name),
                metadata={"routing_method": "hint"},
            )

        # Check routing rules
        for rule in self._rules:
            if not rule.enabled:
                continue

            if self._matches_pattern(tool_name, rule.pattern):
                # Check condition if present
                if rule.condition is not None:
                    if not rule.condition(tool_name, arguments):
                        continue

                self._call_counts[rule.target_source] += 1
                return RoutingDecision(
                    tool_name=tool_name,
                    source=rule.target_source,
                    rule_applied=rule.name,
                    fallback_sources=self._get_fallback_sources(
                        rule.target_source, tool_name
                    ),
                    metadata={"routing_method": "rule", "rule_priority": rule.priority},
                )

        # Apply default strategy
        source = self._apply_strategy(tool_name)
        self._call_counts[source] += 1

        return RoutingDecision(
            tool_name=tool_name,
            source=source,
            rule_applied=None,
            fallback_sources=self._get_fallback_sources(source, tool_name),
            metadata={
                "routing_method": "strategy",
                "strategy": self._default_strategy.value,
            },
        )

    def _matches_pattern(self, tool_name: str, pattern: str) -> bool:
        """
        Check if tool name matches pattern.

        Supports wildcards:
        - * matches any sequence of characters
        - ? matches any single character

        Args:
            tool_name: Tool name to check
            pattern: Pattern to match against

        Returns:
            True if tool name matches pattern
        """
        import fnmatch

        return fnmatch.fnmatch(tool_name, pattern)

    def _apply_strategy(self, tool_name: str) -> ToolSource:
        """
        Apply default routing strategy.

        Args:
            tool_name: Tool name for capability-based routing

        Returns:
            Determined ToolSource
        """
        if self._default_strategy == RoutingStrategy.PREFER_CLAUDE:
            if tool_name in self._claude_tools or tool_name not in self._maf_tools:
                return ToolSource.CLAUDE
            return ToolSource.MAF

        elif self._default_strategy == RoutingStrategy.PREFER_MAF:
            if tool_name in self._maf_tools or tool_name not in self._claude_tools:
                return ToolSource.MAF
            return ToolSource.CLAUDE

        elif self._default_strategy == RoutingStrategy.CAPABILITY_BASED:
            # Check where tool is registered
            if tool_name in self._hybrid_tools:
                return ToolSource.HYBRID
            if tool_name in self._claude_tools and tool_name not in self._maf_tools:
                return ToolSource.CLAUDE
            if tool_name in self._maf_tools and tool_name not in self._claude_tools:
                return ToolSource.MAF
            # Available in both or neither - use default
            return self._default_source

        elif self._default_strategy == RoutingStrategy.LOAD_BALANCED:
            # Route to source with fewer calls
            maf_count = self._call_counts[ToolSource.MAF]
            claude_count = self._call_counts[ToolSource.CLAUDE]

            # Only consider sources where tool is available
            if tool_name in self._maf_tools and tool_name not in self._claude_tools:
                return ToolSource.MAF
            if tool_name in self._claude_tools and tool_name not in self._maf_tools:
                return ToolSource.CLAUDE

            return ToolSource.MAF if maf_count <= claude_count else ToolSource.CLAUDE

        else:  # EXPLICIT
            return self._default_source

    def _get_fallback_sources(
        self,
        primary: ToolSource,
        tool_name: str,
    ) -> List[ToolSource]:
        """
        Get fallback sources for a tool.

        Args:
            primary: Primary source being used
            tool_name: Tool name to check capabilities

        Returns:
            List of fallback sources in priority order
        """
        fallbacks = []

        # Build fallback list based on tool capabilities
        all_sources = [ToolSource.CLAUDE, ToolSource.MAF, ToolSource.HYBRID]

        for source in all_sources:
            if source == primary:
                continue

            # Check if tool is available in this source
            if source == ToolSource.CLAUDE and tool_name in self._claude_tools:
                fallbacks.append(source)
            elif source == ToolSource.MAF and tool_name in self._maf_tools:
                fallbacks.append(source)
            elif source == ToolSource.HYBRID and tool_name in self._hybrid_tools:
                fallbacks.append(source)

        return fallbacks

    def get_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.

        Returns:
            Dictionary with routing statistics
        """
        return {
            "call_counts": dict(self._call_counts),
            "rule_count": len(self._rules),
            "maf_tools": len(self._maf_tools),
            "claude_tools": len(self._claude_tools),
            "hybrid_tools": len(self._hybrid_tools),
            "default_strategy": self._default_strategy.value,
        }

    def reset_stats(self) -> None:
        """Reset call count statistics."""
        self._call_counts = {
            ToolSource.MAF: 0,
            ToolSource.CLAUDE: 0,
            ToolSource.HYBRID: 0,
        }


# =============================================================================
# Factory Functions
# =============================================================================


def create_default_router() -> ToolRouter:
    """
    Create a ToolRouter with default configuration.

    Returns:
        Configured ToolRouter instance
    """
    router = ToolRouter(
        default_strategy=RoutingStrategy.PREFER_CLAUDE,
        default_source=ToolSource.CLAUDE,
    )

    # Add default rules for common patterns
    router.add_rule(
        RoutingRule(
            name="maf_prefixed",
            pattern="maf_*",
            target_source=ToolSource.MAF,
            priority=100,
        )
    )

    router.add_rule(
        RoutingRule(
            name="claude_prefixed",
            pattern="claude_*",
            target_source=ToolSource.CLAUDE,
            priority=100,
        )
    )

    router.add_rule(
        RoutingRule(
            name="workflow_tools",
            pattern="workflow_*",
            target_source=ToolSource.MAF,
            priority=90,
        )
    )

    router.add_rule(
        RoutingRule(
            name="agent_tools",
            pattern="agent_*",
            target_source=ToolSource.MAF,
            priority=90,
        )
    )

    return router
