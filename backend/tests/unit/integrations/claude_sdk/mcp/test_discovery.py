"""Unit tests for MCP Tool Discovery.

Sprint 50: S50-2 - MCP Manager 與工具發現 (8 pts)
Tests for ToolDiscovery class.
"""

import pytest

from src.integrations.claude_sdk.mcp.discovery import (
    ToolCategory,
    ToolDiscovery,
    ToolIndex,
)
from src.integrations.claude_sdk.mcp.types import MCPToolDefinition


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def discovery():
    """Create a ToolDiscovery instance."""
    return ToolDiscovery()


@pytest.fixture
def file_tools():
    """Create file system related tools."""
    return [
        MCPToolDefinition(
            name="read_file",
            description="Read content from a file",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
            server_name="filesystem",
        ),
        MCPToolDefinition(
            name="write_file",
            description="Write content to a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
            server_name="filesystem",
        ),
        MCPToolDefinition(
            name="list_directory",
            description="List files in a directory",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
            server_name="filesystem",
        ),
    ]


@pytest.fixture
def db_tools():
    """Create database related tools."""
    return [
        MCPToolDefinition(
            name="query_database",
            description="Execute SQL query on database",
            input_schema={
                "type": "object",
                "properties": {"sql": {"type": "string"}},
            },
            server_name="database",
        ),
        MCPToolDefinition(
            name="list_tables",
            description="List all tables in database",
            input_schema={"type": "object"},
            server_name="database",
        ),
    ]


@pytest.fixture
def web_tools():
    """Create web related tools."""
    return [
        MCPToolDefinition(
            name="fetch_url",
            description="Fetch content from HTTP URL",
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
            },
            server_name="web",
        ),
        MCPToolDefinition(
            name="web_search",
            description="Search the web for information",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
            server_name="web",
        ),
    ]


# ============================================================================
# ToolCategory Tests
# ============================================================================


class TestToolCategory:
    """Tests for ToolCategory enum."""

    def test_category_values(self):
        """Test all category values are defined."""
        assert ToolCategory.FILE_SYSTEM.value == "file_system"
        assert ToolCategory.DATABASE.value == "database"
        assert ToolCategory.WEB.value == "web"
        assert ToolCategory.CODE.value == "code"
        assert ToolCategory.SEARCH.value == "search"
        assert ToolCategory.COMMUNICATION.value == "communication"
        assert ToolCategory.DATA.value == "data"
        assert ToolCategory.SYSTEM.value == "system"
        assert ToolCategory.OTHER.value == "other"

    def test_category_count(self):
        """Test correct number of categories."""
        assert len(ToolCategory) == 9


# ============================================================================
# ToolIndex Tests
# ============================================================================


class TestToolIndex:
    """Tests for ToolIndex dataclass."""

    def test_qualified_name(self):
        """Test qualified name property."""
        tool = MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={},
            server_name="test-server",
        )
        index = ToolIndex(
            tool=tool,
            server_name="test-server",
            category=ToolCategory.OTHER,
        )

        assert index.qualified_name == "test-server:test_tool"

    def test_default_values(self):
        """Test default values."""
        tool = MCPToolDefinition(
            name="test",
            description="Test",
            input_schema={},
            server_name="server",
        )
        index = ToolIndex(
            tool=tool,
            server_name="server",
            category=ToolCategory.OTHER,
        )

        assert index.tags == set()
        assert index.priority == 0


# ============================================================================
# ToolDiscovery Initialization Tests
# ============================================================================


class TestToolDiscoveryInit:
    """Tests for ToolDiscovery initialization."""

    def test_default_init(self):
        """Test default initialization."""
        discovery = ToolDiscovery()

        assert discovery.tool_count == 0

    def test_empty_indexes(self, discovery):
        """Test empty indexes on init."""
        assert len(discovery.list_all()) == 0
        assert len(discovery.list_categories()) == 0
        assert len(discovery.list_tags()) == 0


# ============================================================================
# ToolDiscovery Index Tests
# ============================================================================


class TestToolDiscoveryIndex:
    """Tests for tool indexing."""

    def test_index_tools(self, discovery, file_tools):
        """Test indexing tools from a server."""
        count = discovery.index_tools("filesystem", file_tools)

        assert count == 3
        assert discovery.tool_count == 3

    def test_index_multiple_servers(self, discovery, file_tools, db_tools):
        """Test indexing tools from multiple servers."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        assert discovery.tool_count == 5

    def test_index_categorizes_tools(self, discovery, file_tools):
        """Test that tools are categorized correctly."""
        discovery.index_tools("filesystem", file_tools)

        # File tools should be categorized as FILE_SYSTEM
        file_category_tools = discovery.get_by_category(ToolCategory.FILE_SYSTEM)
        assert len(file_category_tools) >= 1

    def test_index_tags_tools(self, discovery, file_tools):
        """Test that tools are tagged correctly."""
        discovery.index_tools("filesystem", file_tools)

        # Should have tags extracted from tool names/descriptions
        tags = discovery.list_tags()
        assert "file" in tags or "read" in tags

    def test_remove_server_tools(self, discovery, file_tools, db_tools):
        """Test removing tools from a server."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        removed = discovery.remove_server_tools("filesystem")

        assert removed == 3
        assert discovery.tool_count == 2

    def test_remove_nonexistent_server(self, discovery):
        """Test removing tools from non-existent server."""
        removed = discovery.remove_server_tools("nonexistent")

        assert removed == 0


# ============================================================================
# ToolDiscovery Get Tests
# ============================================================================


class TestToolDiscoveryGet:
    """Tests for getting tools."""

    def test_get_tool_by_qualified_name(self, discovery, file_tools):
        """Test getting tool by qualified name."""
        discovery.index_tools("filesystem", file_tools)

        entry = discovery.get_tool("filesystem:read_file")

        assert entry is not None
        assert entry.tool.name == "read_file"

    def test_get_tool_not_found(self, discovery, file_tools):
        """Test getting non-existent tool."""
        discovery.index_tools("filesystem", file_tools)

        entry = discovery.get_tool("filesystem:nonexistent")

        assert entry is None

    def test_find_tool_by_name(self, discovery, file_tools):
        """Test finding tool by name (first match)."""
        discovery.index_tools("filesystem", file_tools)

        entry = discovery.find_tool("read_file")

        assert entry is not None
        assert entry.tool.name == "read_file"

    def test_find_tool_not_found(self, discovery, file_tools):
        """Test finding non-existent tool."""
        discovery.index_tools("filesystem", file_tools)

        entry = discovery.find_tool("nonexistent")

        assert entry is None


# ============================================================================
# ToolDiscovery Category Tests
# ============================================================================


class TestToolDiscoveryCategory:
    """Tests for category operations."""

    def test_get_by_category(self, discovery, file_tools, db_tools):
        """Test getting tools by category."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        db_category_tools = discovery.get_by_category(ToolCategory.DATABASE)

        # At least some should be categorized as database
        assert len(db_category_tools) >= 1

    def test_get_by_category_empty(self, discovery, file_tools):
        """Test getting tools from empty category."""
        discovery.index_tools("filesystem", file_tools)

        # Communication category should be empty
        comm_tools = discovery.get_by_category(ToolCategory.COMMUNICATION)

        assert len(comm_tools) == 0

    def test_list_categories(self, discovery, file_tools, db_tools):
        """Test listing all categories."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        categories = discovery.list_categories()

        assert len(categories) >= 1
        assert all(isinstance(k, ToolCategory) for k in categories.keys())
        assert all(isinstance(v, int) for v in categories.values())


# ============================================================================
# ToolDiscovery Server Tests
# ============================================================================


class TestToolDiscoveryServer:
    """Tests for server operations."""

    def test_get_by_server(self, discovery, file_tools, db_tools):
        """Test getting tools by server."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        fs_tools = discovery.get_by_server("filesystem")

        assert len(fs_tools) == 3

    def test_get_by_server_empty(self, discovery, file_tools):
        """Test getting tools from non-existent server."""
        discovery.index_tools("filesystem", file_tools)

        tools = discovery.get_by_server("nonexistent")

        assert len(tools) == 0


# ============================================================================
# ToolDiscovery Tag Tests
# ============================================================================


class TestToolDiscoveryTag:
    """Tests for tag operations."""

    def test_get_by_tag(self, discovery, file_tools):
        """Test getting tools by tag."""
        discovery.index_tools("filesystem", file_tools)

        # File-related tools should have "file" tag
        file_tagged = discovery.get_by_tag("file")

        assert len(file_tagged) >= 1

    def test_get_by_tag_case_insensitive(self, discovery, file_tools):
        """Test tag lookup is case insensitive."""
        discovery.index_tools("filesystem", file_tools)

        lower_result = discovery.get_by_tag("file")
        upper_result = discovery.get_by_tag("FILE")

        assert len(lower_result) == len(upper_result)

    def test_list_tags(self, discovery, file_tools):
        """Test listing all tags."""
        discovery.index_tools("filesystem", file_tools)

        tags = discovery.list_tags()

        assert len(tags) >= 1
        assert all(isinstance(k, str) for k in tags.keys())
        assert all(isinstance(v, int) for v in tags.values())


# ============================================================================
# ToolDiscovery Search Tests
# ============================================================================


class TestToolDiscoverySearch:
    """Tests for search operations."""

    def test_search_by_name(self, discovery, file_tools, db_tools, web_tools):
        """Test searching by tool name."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)
        discovery.index_tools("web", web_tools)

        results = discovery.search("read")

        assert len(results) >= 1
        assert any("read" in r.tool.name.lower() for r in results)

    def test_search_by_description(self, discovery, file_tools):
        """Test searching by description."""
        discovery.index_tools("filesystem", file_tools)

        results = discovery.search("content")

        assert len(results) >= 1

    def test_search_with_category_filter(self, discovery, file_tools, db_tools):
        """Test searching with category filter."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        # Search for "file" but filter to DATABASE category
        results = discovery.search("query", category=ToolCategory.DATABASE)

        # Should only return database tools
        for result in results:
            assert result.category == ToolCategory.DATABASE

    def test_search_with_server_filter(self, discovery, file_tools, db_tools):
        """Test searching with server filter."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        results = discovery.search("file", server="filesystem")

        # Should only return filesystem server tools
        for result in results:
            assert result.server_name == "filesystem"

    def test_search_with_limit(self, discovery, file_tools, db_tools, web_tools):
        """Test search result limiting."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)
        discovery.index_tools("web", web_tools)

        results = discovery.search("file", limit=2)

        assert len(results) <= 2

    def test_search_no_results(self, discovery, file_tools):
        """Test search with no results."""
        discovery.index_tools("filesystem", file_tools)

        results = discovery.search("xyznonexistent")

        assert len(results) == 0

    def test_search_relevance_ranking(self, discovery, file_tools):
        """Test search results are ranked by relevance."""
        discovery.index_tools("filesystem", file_tools)

        results = discovery.search("read_file")

        # Exact name match should be first
        if results:
            assert results[0].tool.name == "read_file"


# ============================================================================
# ToolDiscovery List All Tests
# ============================================================================


class TestToolDiscoveryListAll:
    """Tests for listing all tools."""

    def test_list_all(self, discovery, file_tools, db_tools):
        """Test listing all tools."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        all_tools = discovery.list_all()

        assert len(all_tools) == 5

    def test_list_all_empty(self, discovery):
        """Test listing all with no tools."""
        all_tools = discovery.list_all()

        assert len(all_tools) == 0


# ============================================================================
# ToolDiscovery Schema Validation Tests
# ============================================================================


class TestToolDiscoverySchemaValidation:
    """Tests for schema validation."""

    def test_validate_valid_schema(self, discovery):
        """Test validating a valid schema."""
        tool = MCPToolDefinition(
            name="valid_tool",
            description="A valid tool",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
            },
            server_name="test",
        )

        errors = discovery.validate_schema(tool)

        assert len(errors) == 0

    def test_validate_empty_schema(self, discovery):
        """Test validating empty schema (valid)."""
        tool = MCPToolDefinition(
            name="no_params",
            description="Tool with no parameters",
            input_schema={},
            server_name="test",
        )

        errors = discovery.validate_schema(tool)

        assert len(errors) == 0

    def test_validate_non_object_root(self, discovery):
        """Test validating non-object root type."""
        tool = MCPToolDefinition(
            name="invalid_root",
            description="Tool with invalid root type",
            input_schema={"type": "array"},
            server_name="test",
        )

        errors = discovery.validate_schema(tool)

        assert len(errors) >= 1
        assert any("object" in e for e in errors)

    def test_validate_property_missing_type(self, discovery):
        """Test validating property missing type."""
        tool = MCPToolDefinition(
            name="missing_type",
            description="Property missing type",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"description": "The path"},
                },
            },
            server_name="test",
        )

        errors = discovery.validate_schema(tool)

        assert len(errors) >= 1
        assert any("type" in e for e in errors)

    def test_validate_invalid_properties(self, discovery):
        """Test validating invalid properties field."""
        tool = MCPToolDefinition(
            name="invalid_props",
            description="Invalid properties",
            input_schema={
                "type": "object",
                "properties": "not_a_dict",
            },
            server_name="test",
        )

        errors = discovery.validate_schema(tool)

        assert len(errors) >= 1


# ============================================================================
# ToolDiscovery Clear Tests
# ============================================================================


class TestToolDiscoveryClear:
    """Tests for clearing discovery."""

    def test_clear(self, discovery, file_tools, db_tools):
        """Test clearing all indexed tools."""
        discovery.index_tools("filesystem", file_tools)
        discovery.index_tools("database", db_tools)

        discovery.clear()

        assert discovery.tool_count == 0
        assert len(discovery.list_all()) == 0
        assert len(discovery.list_categories()) == 0
        assert len(discovery.list_tags()) == 0


# ============================================================================
# ToolDiscovery Categorization Tests
# ============================================================================


class TestToolDiscoveryCategorization:
    """Tests for tool categorization logic."""

    def test_categorize_file_tool(self, discovery):
        """Test file system tool categorization."""
        tools = [
            MCPToolDefinition(
                name="read_file",
                description="Read a file from disk",
                input_schema={},
                server_name="test",
            ),
        ]
        discovery.index_tools("test", tools)

        entry = discovery.find_tool("read_file")
        assert entry.category == ToolCategory.FILE_SYSTEM

    def test_categorize_database_tool(self, discovery):
        """Test database tool categorization."""
        tools = [
            MCPToolDefinition(
                name="execute_sql",
                description="Execute SQL query on PostgreSQL database",
                input_schema={},
                server_name="test",
            ),
        ]
        discovery.index_tools("test", tools)

        entry = discovery.find_tool("execute_sql")
        assert entry.category == ToolCategory.DATABASE

    def test_categorize_web_tool(self, discovery):
        """Test web tool categorization."""
        tools = [
            MCPToolDefinition(
                name="http_request",
                description="Make HTTP API request to URL",
                input_schema={},
                server_name="test",
            ),
        ]
        discovery.index_tools("test", tools)

        entry = discovery.find_tool("http_request")
        assert entry.category == ToolCategory.WEB

    def test_categorize_code_tool(self, discovery):
        """Test code tool categorization."""
        tools = [
            MCPToolDefinition(
                name="run_python",
                description="Execute Python script code",
                input_schema={},
                server_name="test",
            ),
        ]
        discovery.index_tools("test", tools)

        entry = discovery.find_tool("run_python")
        assert entry.category == ToolCategory.CODE

    def test_categorize_search_tool(self, discovery):
        """Test search tool categorization."""
        tools = [
            MCPToolDefinition(
                name="semantic_search",
                description="Perform vector similarity search",
                input_schema={},
                server_name="test",
            ),
        ]
        discovery.index_tools("test", tools)

        entry = discovery.find_tool("semantic_search")
        assert entry.category == ToolCategory.SEARCH

    def test_categorize_unknown_tool(self, discovery):
        """Test uncategorizable tool defaults to OTHER."""
        tools = [
            MCPToolDefinition(
                name="mysterious_action",
                description="Does something mysterious",
                input_schema={},
                server_name="test",
            ),
        ]
        discovery.index_tools("test", tools)

        entry = discovery.find_tool("mysterious_action")
        assert entry.category == ToolCategory.OTHER
