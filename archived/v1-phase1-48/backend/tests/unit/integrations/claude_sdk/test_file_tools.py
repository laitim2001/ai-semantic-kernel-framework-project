"""Unit tests for Claude SDK file tools.

Sprint 49: S49-1 - Built-in File Tools (8 pts)
Tests: Read, Write, Edit, MultiEdit, Glob, Grep
"""

import os
import pytest
import tempfile
from pathlib import Path

from src.integrations.claude_sdk.tools import (
    Tool,
    ToolResult,
    Read,
    Write,
    Edit,
    MultiEdit,
    Glob,
    Grep,
)
from src.integrations.claude_sdk.tools.registry import (
    register_tool,
    get_tool_instance,
    get_available_tools,
    get_tool_definitions,
    execute_tool,
)


# ============================================================
# Test ToolResult
# ============================================================

class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_create_success_result(self):
        """Test creating a successful result."""
        result = ToolResult(content="Hello, World!")
        assert result.content == "Hello, World!"
        assert result.success is True
        assert result.error is None

    def test_create_error_result(self):
        """Test creating an error result."""
        result = ToolResult(content="", success=False, error="File not found")
        assert result.content == ""
        assert result.success is False
        assert result.error == "File not found"

    def test_str_success(self):
        """Test string representation of success result."""
        result = ToolResult(content="Test content")
        assert str(result) == "Test content"

    def test_str_error(self):
        """Test string representation of error result."""
        result = ToolResult(content="", success=False, error="Error message")
        assert str(result) == "Error: Error message"


# ============================================================
# Test Read Tool
# ============================================================

class TestReadTool:
    """Tests for Read tool."""

    @pytest.fixture
    def read_tool(self):
        """Create a Read tool instance."""
        return Read()

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file with test content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_entire_file(self, read_tool, temp_file):
        """Test reading an entire file."""
        result = await read_tool.execute(path=temp_file)
        assert result.success is True
        assert "Line 1" in result.content
        assert "Line 5" in result.content

    @pytest.mark.asyncio
    async def test_read_line_range(self, read_tool, temp_file):
        """Test reading specific line range."""
        result = await read_tool.execute(path=temp_file, start_line=2, end_line=3)
        assert result.success is True
        assert "Line 2" in result.content
        assert "Line 3" in result.content
        assert "Line 1" not in result.content
        assert "Line 4" not in result.content

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, read_tool):
        """Test reading a file that doesn't exist."""
        result = await read_tool.execute(path="/nonexistent/path/file.txt")
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_directory(self, read_tool):
        """Test reading a directory (should fail)."""
        result = await read_tool.execute(path=tempfile.gettempdir())
        assert result.success is False
        assert "directory" in result.error.lower()

    def test_read_tool_properties(self, read_tool):
        """Test tool properties."""
        assert read_tool.name == "Read"
        assert "Read" in read_tool.description

    def test_read_tool_schema(self, read_tool):
        """Test tool schema."""
        schema = read_tool.get_schema()
        assert schema["type"] == "object"
        assert "path" in schema["properties"]
        assert "path" in schema["required"]

    def test_read_tool_definition(self, read_tool):
        """Test complete tool definition."""
        definition = read_tool.get_definition()
        assert definition["name"] == "Read"
        assert "description" in definition
        assert "input_schema" in definition


# ============================================================
# Test Write Tool
# ============================================================

class TestWriteTool:
    """Tests for Write tool."""

    @pytest.fixture
    def write_tool(self):
        """Create a Write tool instance."""
        return Write()

    @pytest.mark.asyncio
    async def test_write_new_file(self, write_tool):
        """Test writing to a new file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            result = await write_tool.execute(path=file_path, content="Hello, World!")

            assert result.success is True
            assert os.path.exists(file_path)
            with open(file_path) as f:
                assert f.read() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_write_overwrite_protection(self, write_tool):
        """Test overwrite protection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            # Create file first
            with open(file_path, "w") as f:
                f.write("Original")

            # Try to write with overwrite=False
            result = await write_tool.execute(
                path=file_path, content="New content", overwrite=False
            )
            assert result.success is False
            assert "already exists" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_create_dirs(self, write_tool):
        """Test creating parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "new", "nested", "dir", "test.txt")
            result = await write_tool.execute(
                path=file_path, content="Nested content", create_dirs=True
            )

            assert result.success is True
            assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_write_without_create_dirs(self, write_tool):
        """Test failure when parent dir doesn't exist and create_dirs=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent", "test.txt")
            result = await write_tool.execute(
                path=file_path, content="Content", create_dirs=False
            )

            assert result.success is False
            assert "does not exist" in result.error.lower()

    def test_write_tool_schema(self, write_tool):
        """Test tool schema."""
        schema = write_tool.get_schema()
        assert "path" in schema["properties"]
        assert "content" in schema["properties"]
        assert set(schema["required"]) == {"path", "content"}


# ============================================================
# Test Edit Tool
# ============================================================

class TestEditTool:
    """Tests for Edit tool."""

    @pytest.fixture
    def edit_tool(self):
        """Create an Edit tool instance."""
        return Edit()

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for editing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, World! Hello, World!")
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_single_replacement(self, edit_tool, temp_file):
        """Test replacing first occurrence only."""
        result = await edit_tool.execute(
            path=temp_file, old_text="World", new_text="Python"
        )

        assert result.success is True
        with open(temp_file) as f:
            content = f.read()
        assert content == "Hello, Python! Hello, World!"

    @pytest.mark.asyncio
    async def test_edit_replace_all(self, edit_tool, temp_file):
        """Test replacing all occurrences."""
        result = await edit_tool.execute(
            path=temp_file, old_text="World", new_text="Python", replace_all=True
        )

        assert result.success is True
        with open(temp_file) as f:
            content = f.read()
        assert content == "Hello, Python! Hello, Python!"

    @pytest.mark.asyncio
    async def test_edit_text_not_found(self, edit_tool, temp_file):
        """Test editing with text that doesn't exist."""
        result = await edit_tool.execute(
            path=temp_file, old_text="Nonexistent", new_text="New"
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_edit_nonexistent_file(self, edit_tool):
        """Test editing a nonexistent file."""
        result = await edit_tool.execute(
            path="/nonexistent/file.txt", old_text="a", new_text="b"
        )

        assert result.success is False
        assert "not found" in result.error.lower()


# ============================================================
# Test MultiEdit Tool
# ============================================================

class TestMultiEditTool:
    """Tests for MultiEdit tool."""

    @pytest.fixture
    def multiedit_tool(self):
        """Create a MultiEdit tool instance."""
        return MultiEdit()

    @pytest.fixture
    def temp_files(self):
        """Create temporary files for multi-editing."""
        files = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(2):
                path = os.path.join(temp_dir, f"file{i}.txt")
                with open(path, "w") as f:
                    f.write(f"Content {i}: Hello")
                files.append(path)
            yield files

    @pytest.mark.asyncio
    async def test_multiedit_success(self, multiedit_tool, temp_files):
        """Test successful multi-edit."""
        edits = [
            {"path": temp_files[0], "old_text": "Hello", "new_text": "World"},
            {"path": temp_files[1], "old_text": "Hello", "new_text": "Python"},
        ]

        result = await multiedit_tool.execute(edits=edits)
        assert result.success is True

        with open(temp_files[0]) as f:
            assert "World" in f.read()
        with open(temp_files[1]) as f:
            assert "Python" in f.read()

    @pytest.mark.asyncio
    async def test_multiedit_empty_list(self, multiedit_tool):
        """Test with empty edit list."""
        result = await multiedit_tool.execute(edits=[])
        assert result.success is False
        assert "no edits" in result.error.lower()

    @pytest.mark.asyncio
    async def test_multiedit_partial_failure(self, multiedit_tool, temp_files):
        """Test partial failure in multi-edit."""
        edits = [
            {"path": temp_files[0], "old_text": "Hello", "new_text": "World"},
            {"path": "/nonexistent/file.txt", "old_text": "a", "new_text": "b"},
        ]

        result = await multiedit_tool.execute(edits=edits)
        assert result.success is False
        assert "failed" in result.error.lower()


# ============================================================
# Test Glob Tool
# ============================================================

class TestGlobTool:
    """Tests for Glob tool."""

    @pytest.fixture
    def glob_tool(self):
        """Create a Glob tool instance."""
        return Glob()

    @pytest.fixture
    def temp_structure(self):
        """Create a temporary directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files
            Path(temp_dir, "file1.py").touch()
            Path(temp_dir, "file2.py").touch()
            Path(temp_dir, "file3.txt").touch()

            # Create subdirectory
            subdir = Path(temp_dir, "subdir")
            subdir.mkdir()
            Path(subdir, "nested.py").touch()

            yield temp_dir

    @pytest.mark.asyncio
    async def test_glob_pattern_match(self, glob_tool, temp_structure):
        """Test glob pattern matching."""
        result = await glob_tool.execute(pattern="*.py", path=temp_structure)

        assert result.success is True
        assert "file1.py" in result.content
        assert "file2.py" in result.content
        assert "file3.txt" not in result.content

    @pytest.mark.asyncio
    async def test_glob_recursive(self, glob_tool, temp_structure):
        """Test recursive glob pattern."""
        result = await glob_tool.execute(pattern="**/*.py", path=temp_structure)

        assert result.success is True
        assert "nested.py" in result.content

    @pytest.mark.asyncio
    async def test_glob_no_matches(self, glob_tool, temp_structure):
        """Test glob with no matches."""
        result = await glob_tool.execute(pattern="*.xyz", path=temp_structure)

        assert result.success is True
        assert "no matching files" in result.content.lower()


# ============================================================
# Test Grep Tool
# ============================================================

class TestGrepTool:
    """Tests for Grep tool."""

    @pytest.fixture
    def grep_tool(self):
        """Create a Grep tool instance."""
        return Grep()

    @pytest.fixture
    def temp_files(self):
        """Create temporary files for searching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with content
            file1 = Path(temp_dir, "code.py")
            file1.write_text("def hello_world():\n    print('Hello')\n")

            file2 = Path(temp_dir, "readme.txt")
            file2.write_text("Welcome to the project\nHello everyone\n")

            yield temp_dir

    @pytest.mark.asyncio
    async def test_grep_simple_pattern(self, grep_tool, temp_files):
        """Test simple pattern search."""
        result = await grep_tool.execute(pattern="Hello", path=temp_files)

        assert result.success is True
        assert "Hello" in result.content

    @pytest.mark.asyncio
    async def test_grep_regex_pattern(self, grep_tool, temp_files):
        """Test regex pattern search."""
        result = await grep_tool.execute(
            pattern=r"def \w+\(\)", path=temp_files, regex=True
        )

        assert result.success is True
        assert "hello_world" in result.content

    @pytest.mark.asyncio
    async def test_grep_case_insensitive(self, grep_tool, temp_files):
        """Test case-insensitive search."""
        result = await grep_tool.execute(
            pattern="HELLO", path=temp_files, case_sensitive=False
        )

        assert result.success is True
        assert "Hello" in result.content

    @pytest.mark.asyncio
    async def test_grep_no_matches(self, grep_tool, temp_files):
        """Test grep with no matches."""
        result = await grep_tool.execute(pattern="xyz123", path=temp_files)

        assert result.success is True
        assert "no matches" in result.content.lower()

    @pytest.mark.asyncio
    async def test_grep_with_context(self, grep_tool, temp_files):
        """Test grep with context lines."""
        result = await grep_tool.execute(
            pattern="print", path=temp_files, before=1, after=0
        )

        assert result.success is True
        # Should include the line before "print"
        assert "def" in result.content


# ============================================================
# Test Registry
# ============================================================

class TestRegistry:
    """Tests for tool registry."""

    def test_get_available_tools(self):
        """Test getting available tool names."""
        tools = get_available_tools()

        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools
        assert "MultiEdit" in tools
        assert "Glob" in tools
        assert "Grep" in tools

    def test_get_tool_instance(self):
        """Test getting tool instance."""
        tool = get_tool_instance("Read")

        assert tool is not None
        assert isinstance(tool, Read)
        assert tool.name == "Read"

    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist."""
        tool = get_tool_instance("NonexistentTool")
        assert tool is None

    def test_get_tool_definitions(self):
        """Test getting tool definitions."""
        definitions = get_tool_definitions(["Read", "Write"])

        assert len(definitions) == 2
        names = [d["name"] for d in definitions]
        assert "Read" in names
        assert "Write" in names

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test executing a tool by name."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            result = await execute_tool("Read", {"path": temp_path})
            assert "Test content" in result
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist."""
        result = await execute_tool("NonexistentTool", {})
        assert "not found" in result.lower()
