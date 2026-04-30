"""MCP Tool Discovery mechanism.

Sprint 50: S50-2 - MCP Manager 與工具發現 (8 pts)

This module provides tool discovery and indexing functionality
for MCP servers.

Features:
- Automatic tool scanning from connected servers
- Tool categorization and tagging
- Search and filtering capabilities
- Tool schema validation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import logging
import re

from .types import MCPToolDefinition

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Tool categories for classification."""

    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    WEB = "web"
    CODE = "code"
    SEARCH = "search"
    COMMUNICATION = "communication"
    DATA = "data"
    SYSTEM = "system"
    OTHER = "other"


@dataclass
class ToolIndex:
    """Index entry for a tool."""

    tool: MCPToolDefinition
    server_name: str
    category: ToolCategory
    tags: Set[str] = field(default_factory=set)
    priority: int = 0

    @property
    def qualified_name(self) -> str:
        """Get fully qualified tool name."""
        return f"{self.server_name}:{self.tool.name}"


class ToolDiscovery:
    """Tool discovery and indexing service.

    ToolDiscovery provides:
    - Tool categorization based on name and description
    - Tag-based filtering
    - Search capabilities
    - Schema validation

    Example:
        discovery = ToolDiscovery()
        discovery.index_tools(server_name, tools)

        # Search tools
        file_tools = discovery.search("file")

        # Filter by category
        db_tools = discovery.get_by_category(ToolCategory.DATABASE)
    """

    # Keyword patterns for categorization
    CATEGORY_PATTERNS: Dict[ToolCategory, List[str]] = {
        ToolCategory.FILE_SYSTEM: [
            r"file", r"read", r"write", r"directory", r"path",
            r"folder", r"disk", r"storage", r"download", r"upload",
        ],
        ToolCategory.DATABASE: [
            r"database", r"sql", r"query", r"table", r"record",
            r"postgres", r"mysql", r"sqlite", r"mongo", r"redis",
        ],
        ToolCategory.WEB: [
            r"http", r"url", r"web", r"api", r"rest",
            r"fetch", r"request", r"browser", r"scrape",
        ],
        ToolCategory.CODE: [
            r"code", r"compile", r"run", r"execute", r"script",
            r"python", r"javascript", r"shell", r"command",
        ],
        ToolCategory.SEARCH: [
            r"search", r"find", r"lookup", r"index", r"query",
            r"semantic", r"vector", r"similarity",
        ],
        ToolCategory.COMMUNICATION: [
            r"email", r"message", r"slack", r"notify", r"send",
            r"sms", r"chat", r"mail",
        ],
        ToolCategory.DATA: [
            r"data", r"json", r"csv", r"xml", r"parse",
            r"transform", r"convert", r"format",
        ],
        ToolCategory.SYSTEM: [
            r"system", r"process", r"memory", r"cpu", r"disk",
            r"monitor", r"status", r"health",
        ],
    }

    def __init__(self):
        """Initialize tool discovery."""
        self._index: Dict[str, ToolIndex] = {}  # qualified_name -> ToolIndex
        self._by_category: Dict[ToolCategory, List[str]] = {}
        self._by_server: Dict[str, List[str]] = {}
        self._by_tag: Dict[str, List[str]] = {}

    @property
    def tool_count(self) -> int:
        """Get total number of indexed tools."""
        return len(self._index)

    def index_tools(
        self,
        server_name: str,
        tools: List[MCPToolDefinition],
    ) -> int:
        """Index tools from a server.

        Args:
            server_name: Name of the server.
            tools: List of tools to index.

        Returns:
            Number of tools indexed.
        """
        indexed = 0

        for tool in tools:
            qualified_name = f"{server_name}:{tool.name}"

            # Categorize tool
            category = self._categorize_tool(tool)

            # Extract tags
            tags = self._extract_tags(tool)

            # Create index entry
            entry = ToolIndex(
                tool=tool,
                server_name=server_name,
                category=category,
                tags=tags,
            )

            # Store in main index
            self._index[qualified_name] = entry

            # Update category index
            if category not in self._by_category:
                self._by_category[category] = []
            self._by_category[category].append(qualified_name)

            # Update server index
            if server_name not in self._by_server:
                self._by_server[server_name] = []
            self._by_server[server_name].append(qualified_name)

            # Update tag index
            for tag in tags:
                if tag not in self._by_tag:
                    self._by_tag[tag] = []
                self._by_tag[tag].append(qualified_name)

            indexed += 1

        logger.info(
            f"Indexed {indexed} tools from server: {server_name}"
        )
        return indexed

    def remove_server_tools(self, server_name: str) -> int:
        """Remove all tools from a server.

        Args:
            server_name: Name of the server.

        Returns:
            Number of tools removed.
        """
        if server_name not in self._by_server:
            return 0

        tools_to_remove = list(self._by_server[server_name])
        removed = 0

        for qualified_name in tools_to_remove:
            if qualified_name in self._index:
                entry = self._index.pop(qualified_name)

                # Remove from category index
                if entry.category in self._by_category:
                    self._by_category[entry.category] = [
                        t for t in self._by_category[entry.category]
                        if t != qualified_name
                    ]

                # Remove from tag index
                for tag in entry.tags:
                    if tag in self._by_tag:
                        self._by_tag[tag] = [
                            t for t in self._by_tag[tag]
                            if t != qualified_name
                        ]

                removed += 1

        # Clear server index
        del self._by_server[server_name]

        logger.info(
            f"Removed {removed} tools from server: {server_name}"
        )
        return removed

    def get_tool(self, qualified_name: str) -> Optional[ToolIndex]:
        """Get a tool by qualified name.

        Args:
            qualified_name: Tool name in "server:tool" format.

        Returns:
            ToolIndex if found, None otherwise.
        """
        return self._index.get(qualified_name)

    def find_tool(self, tool_name: str) -> Optional[ToolIndex]:
        """Find a tool by name (first match).

        Args:
            tool_name: Tool name without server prefix.

        Returns:
            ToolIndex if found, None otherwise.
        """
        for qualified_name, entry in self._index.items():
            if entry.tool.name == tool_name:
                return entry
        return None

    def get_by_category(
        self,
        category: ToolCategory,
    ) -> List[ToolIndex]:
        """Get all tools in a category.

        Args:
            category: Tool category.

        Returns:
            List of ToolIndex entries.
        """
        qualified_names = self._by_category.get(category, [])
        return [
            self._index[name]
            for name in qualified_names
            if name in self._index
        ]

    def get_by_server(self, server_name: str) -> List[ToolIndex]:
        """Get all tools from a server.

        Args:
            server_name: Server name.

        Returns:
            List of ToolIndex entries.
        """
        qualified_names = self._by_server.get(server_name, [])
        return [
            self._index[name]
            for name in qualified_names
            if name in self._index
        ]

    def get_by_tag(self, tag: str) -> List[ToolIndex]:
        """Get all tools with a specific tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of ToolIndex entries.
        """
        qualified_names = self._by_tag.get(tag.lower(), [])
        return [
            self._index[name]
            for name in qualified_names
            if name in self._index
        ]

    def search(
        self,
        query: str,
        category: Optional[ToolCategory] = None,
        server: Optional[str] = None,
        limit: int = 10,
    ) -> List[ToolIndex]:
        """Search tools by query.

        Args:
            query: Search query string.
            category: Optional category filter.
            server: Optional server filter.
            limit: Maximum results to return.

        Returns:
            List of matching ToolIndex entries, ranked by relevance.
        """
        query_lower = query.lower()
        results: List[tuple] = []  # (score, ToolIndex)

        for entry in self._index.values():
            # Apply filters
            if category and entry.category != category:
                continue
            if server and entry.server_name != server:
                continue

            # Calculate relevance score
            score = self._calculate_relevance(entry, query_lower)
            if score > 0:
                results.append((score, entry))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        # Return top results
        return [entry for _, entry in results[:limit]]

    def list_all(self) -> List[ToolIndex]:
        """List all indexed tools.

        Returns:
            List of all ToolIndex entries.
        """
        return list(self._index.values())

    def list_categories(self) -> Dict[ToolCategory, int]:
        """List all categories with tool counts.

        Returns:
            Dictionary mapping categories to tool counts.
        """
        return {
            category: len(tools)
            for category, tools in self._by_category.items()
        }

    def list_tags(self) -> Dict[str, int]:
        """List all tags with tool counts.

        Returns:
            Dictionary mapping tags to tool counts.
        """
        return {
            tag: len(tools)
            for tag, tools in self._by_tag.items()
        }

    def validate_schema(
        self,
        tool: MCPToolDefinition,
    ) -> List[str]:
        """Validate a tool's input schema.

        Args:
            tool: Tool to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: List[str] = []
        schema = tool.input_schema

        if not schema:
            return errors  # Empty schema is valid

        if not isinstance(schema, dict):
            errors.append("Input schema must be a dictionary")
            return errors

        # Check for standard JSON Schema fields
        if "type" in schema and schema["type"] != "object":
            errors.append(
                f"Root schema type should be 'object', got '{schema['type']}'"
            )

        if "properties" in schema:
            props = schema["properties"]
            if not isinstance(props, dict):
                errors.append("'properties' must be a dictionary")
            else:
                for prop_name, prop_def in props.items():
                    if not isinstance(prop_def, dict):
                        errors.append(
                            f"Property '{prop_name}' definition must be a dictionary"
                        )
                    elif "type" not in prop_def:
                        errors.append(
                            f"Property '{prop_name}' missing 'type' field"
                        )

        return errors

    def _categorize_tool(self, tool: MCPToolDefinition) -> ToolCategory:
        """Categorize a tool based on name and description.

        Args:
            tool: Tool to categorize.

        Returns:
            ToolCategory for the tool.
        """
        text = f"{tool.name} {tool.description}".lower()

        scores: Dict[ToolCategory, int] = {}

        for category, patterns in self.CATEGORY_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text):
                    score += 1
            if score > 0:
                scores[category] = score

        if not scores:
            return ToolCategory.OTHER

        # Return highest scoring category
        return max(scores, key=lambda k: scores[k])

    def _extract_tags(self, tool: MCPToolDefinition) -> Set[str]:
        """Extract tags from a tool.

        Args:
            tool: Tool to extract tags from.

        Returns:
            Set of tags.
        """
        tags: Set[str] = set()

        # Add category as tag
        category = self._categorize_tool(tool)
        tags.add(category.value)

        # Extract words from name
        name_parts = re.split(r"[_\-\s]", tool.name.lower())
        for part in name_parts:
            if len(part) >= 3:  # Skip short words
                tags.add(part)

        # Extract keywords from description
        if tool.description:
            words = re.findall(r"\b[a-z]{3,}\b", tool.description.lower())
            # Add common meaningful words
            for word in words:
                if word in ["file", "data", "query", "search", "read", "write",
                            "create", "update", "delete", "list", "get", "set"]:
                    tags.add(word)

        return tags

    def _calculate_relevance(
        self,
        entry: ToolIndex,
        query: str,
    ) -> float:
        """Calculate relevance score for search.

        Args:
            entry: ToolIndex entry.
            query: Search query (lowercase).

        Returns:
            Relevance score (0.0 to 1.0).
        """
        score = 0.0

        # Exact name match
        if query == entry.tool.name.lower():
            score += 1.0

        # Name contains query
        elif query in entry.tool.name.lower():
            score += 0.8

        # Description contains query
        if entry.tool.description and query in entry.tool.description.lower():
            score += 0.3

        # Tag match
        if query in entry.tags:
            score += 0.4

        # Server name match
        if query in entry.server_name.lower():
            score += 0.2

        return min(score, 1.0)

    def clear(self) -> None:
        """Clear all indexed tools."""
        self._index.clear()
        self._by_category.clear()
        self._by_server.clear()
        self._by_tag.clear()
