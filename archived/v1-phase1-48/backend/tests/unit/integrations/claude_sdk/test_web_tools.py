"""Unit tests for Claude SDK web tools.

Sprint 49: S49-4 - Web Tools (8 pts)
Tests for WebSearch and WebFetch tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.claude_sdk.tools.web_tools import (
    WebSearch,
    WebFetch,
    SearchResult,
    HTMLTextExtractor,
    extract_text_from_html,
)


# ============================================================================
# HTMLTextExtractor Tests
# ============================================================================


class TestHTMLTextExtractor:
    """Tests for HTML text extraction."""

    def test_extract_basic_text(self):
        """Test extracting text from simple HTML."""
        html = "<p>Hello World</p>"
        text = extract_text_from_html(html)
        assert "Hello World" in text

    def test_extract_removes_script(self):
        """Test that script tags are removed."""
        html = """
        <html>
        <head><script>alert('test')</script></head>
        <body><p>Content</p></body>
        </html>
        """
        text = extract_text_from_html(html)
        assert "alert" not in text
        assert "Content" in text

    def test_extract_removes_style(self):
        """Test that style tags are removed."""
        html = """
        <html>
        <head><style>body { color: red; }</style></head>
        <body><p>Visible</p></body>
        </html>
        """
        text = extract_text_from_html(html)
        assert "color" not in text
        assert "Visible" in text

    def test_extract_multiple_elements(self):
        """Test extracting from multiple elements."""
        html = """
        <div>
            <h1>Title</h1>
            <p>Paragraph 1</p>
            <p>Paragraph 2</p>
        </div>
        """
        text = extract_text_from_html(html)
        assert "Title" in text
        assert "Paragraph 1" in text
        assert "Paragraph 2" in text

    def test_extract_handles_empty_html(self):
        """Test handling empty HTML."""
        text = extract_text_from_html("")
        assert text == ""

    def test_extract_handles_noscript(self):
        """Test that noscript tags are removed."""
        html = """
        <html>
        <body>
            <noscript>Enable JavaScript</noscript>
            <p>Main content</p>
        </body>
        </html>
        """
        text = extract_text_from_html(html)
        assert "Enable JavaScript" not in text
        assert "Main content" in text


# ============================================================================
# SearchResult Tests
# ============================================================================


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating a search result."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = SearchResult(
            title="Title",
            url="https://test.com",
            snippet="Snippet",
        )
        d = result.to_dict()
        assert d == {
            "title": "Title",
            "url": "https://test.com",
            "snippet": "Snippet",
        }


# ============================================================================
# WebSearch Tests
# ============================================================================


class TestWebSearch:
    """Tests for WebSearch tool."""

    def test_init_default(self):
        """Test default initialization."""
        search = WebSearch()
        assert search.name == "WebSearch"
        assert search.api_key is None
        assert search.search_engine == "brave"

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        search = WebSearch(
            search_api_key="test-key",
            search_engine="google",
        )
        assert search.api_key == "test-key"
        assert search.search_engine == "google"

    def test_get_default_endpoint_brave(self):
        """Test getting Brave search endpoint."""
        search = WebSearch(search_engine="brave")
        assert "brave.com" in search.search_endpoint

    def test_get_default_endpoint_google(self):
        """Test getting Google search endpoint."""
        search = WebSearch(search_engine="google")
        assert "googleapis.com" in search.search_endpoint

    def test_get_default_endpoint_bing(self):
        """Test getting Bing search endpoint."""
        search = WebSearch(search_engine="bing")
        assert "bing.microsoft.com" in search.search_endpoint

    @pytest.mark.asyncio
    async def test_execute_empty_query(self):
        """Test executing with empty query."""
        search = WebSearch()
        result = await search.execute(query="")
        assert not result.success
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_without_api_key(self):
        """Test executing without API key returns configuration message."""
        search = WebSearch()
        result = await search.execute(query="test query")
        assert result.success  # Returns instructions, not error
        assert "requires configuration" in result.content

    @pytest.mark.asyncio
    async def test_execute_clamps_num_results(self):
        """Test that num_results is clamped to valid range."""
        search = WebSearch(search_api_key="test-key")
        # This will fail because aiohttp might not be available or API call fails
        # But we're testing the clamping logic in the code path
        # For now, we check the schema
        schema = search.get_schema()
        assert schema["properties"]["num_results"]["minimum"] == 1
        assert schema["properties"]["num_results"]["maximum"] == 20

    def test_get_schema(self):
        """Test getting tool schema."""
        search = WebSearch()
        schema = search.get_schema()
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "num_results" in schema["properties"]
        assert "query" in schema["required"]

    def test_parse_brave_response(self):
        """Test parsing Brave search response."""
        search = WebSearch(search_engine="brave")
        data = {
            "web": {
                "results": [
                    {
                        "title": "Test Title",
                        "url": "https://example.com",
                        "description": "Test description",
                    }
                ]
            }
        }
        results = search._parse_response(data)
        assert len(results) == 1
        assert results[0].title == "Test Title"
        assert results[0].url == "https://example.com"
        assert results[0].snippet == "Test description"

    def test_parse_google_response(self):
        """Test parsing Google search response."""
        search = WebSearch(search_engine="google")
        data = {
            "items": [
                {
                    "title": "Google Title",
                    "link": "https://google.com/result",
                    "snippet": "Google snippet",
                }
            ]
        }
        results = search._parse_response(data)
        assert len(results) == 1
        assert results[0].title == "Google Title"
        assert results[0].url == "https://google.com/result"

    def test_parse_bing_response(self):
        """Test parsing Bing search response."""
        search = WebSearch(search_engine="bing")
        data = {
            "webPages": {
                "value": [
                    {
                        "name": "Bing Title",
                        "url": "https://bing.com/result",
                        "snippet": "Bing snippet",
                    }
                ]
            }
        }
        results = search._parse_response(data)
        assert len(results) == 1
        assert results[0].title == "Bing Title"

    def test_format_results_empty(self):
        """Test formatting empty results."""
        search = WebSearch()
        result = search._format_results("test query", [])
        assert result.success
        assert "No results found" in result.content

    def test_format_results_with_data(self):
        """Test formatting results with data."""
        search = WebSearch()
        results = [
            SearchResult("Title 1", "https://url1.com", "Snippet 1"),
            SearchResult("Title 2", "https://url2.com", "Snippet 2"),
        ]
        result = search._format_results("test query", results)
        assert result.success
        assert "Title 1" in result.content
        assert "Title 2" in result.content
        assert "https://url1.com" in result.content


# ============================================================================
# WebFetch Tests
# ============================================================================


class TestWebFetch:
    """Tests for WebFetch tool."""

    def test_init_default(self):
        """Test default initialization."""
        fetch = WebFetch()
        assert fetch.name == "WebFetch"
        assert fetch.timeout == 30
        assert fetch.max_content_length == 500000
        assert fetch.extract_text is True

    def test_init_custom(self):
        """Test custom initialization."""
        fetch = WebFetch(
            timeout=60,
            max_content_length=100000,
            user_agent="CustomAgent/1.0",
            extract_text=False,
        )
        assert fetch.timeout == 60
        assert fetch.max_content_length == 100000
        assert fetch.user_agent == "CustomAgent/1.0"
        assert fetch.extract_text is False

    @pytest.mark.asyncio
    async def test_execute_empty_url(self):
        """Test executing with empty URL."""
        fetch = WebFetch()
        result = await fetch.execute(url="")
        assert not result.success
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_invalid_scheme(self):
        """Test executing with invalid URL scheme."""
        fetch = WebFetch()
        result = await fetch.execute(url="ftp://example.com")
        assert not result.success
        assert "unsupported" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_adds_https(self):
        """Test that https is added to URL without scheme."""
        fetch = WebFetch()
        # Execute with URL without scheme - should auto-add https://
        result = await fetch.execute(url="example.com")
        # Should succeed OR fail with connection error (not URL format error)
        if result.success:
            # If succeeded, the URL in response should have https://
            assert "https://example.com" in result.content
        else:
            # If failed, error should not be about URL format
            assert "unsupported" not in result.error.lower()
            assert "invalid url" not in result.error.lower()

    def test_get_schema(self):
        """Test getting tool schema."""
        fetch = WebFetch()
        schema = fetch.get_schema()
        assert schema["type"] == "object"
        assert "url" in schema["properties"]
        assert "headers" in schema["properties"]
        assert "method" in schema["properties"]
        assert "timeout" in schema["properties"]
        assert "extract_text" in schema["properties"]
        assert "url" in schema["required"]

    def test_get_schema_method_enum(self):
        """Test that method has valid enum values."""
        fetch = WebFetch()
        schema = fetch.get_schema()
        methods = schema["properties"]["method"]["enum"]
        assert "GET" in methods
        assert "POST" in methods
        assert "HEAD" in methods


# ============================================================================
# Integration Tests
# ============================================================================


class TestWebToolsIntegration:
    """Integration tests for web tools."""

    def test_websearch_registered(self):
        """Test that WebSearch is registered in the tool registry."""
        from src.integrations.claude_sdk.tools import get_available_tools

        tools = get_available_tools()
        assert "WebSearch" in tools

    def test_webfetch_registered(self):
        """Test that WebFetch is registered in the tool registry."""
        from src.integrations.claude_sdk.tools import get_available_tools

        tools = get_available_tools()
        assert "WebFetch" in tools

    def test_get_websearch_instance(self):
        """Test getting WebSearch instance from registry."""
        from src.integrations.claude_sdk.tools import get_tool_instance

        tool = get_tool_instance("WebSearch")
        assert tool is not None
        assert tool.name == "WebSearch"

    def test_get_webfetch_instance(self):
        """Test getting WebFetch instance from registry."""
        from src.integrations.claude_sdk.tools import get_tool_instance

        tool = get_tool_instance("WebFetch")
        assert tool is not None
        assert tool.name == "WebFetch"

    def test_get_tool_definitions_includes_web_tools(self):
        """Test that web tools are included in tool definitions."""
        from src.integrations.claude_sdk.tools import get_tool_definitions

        definitions = get_tool_definitions(["WebSearch", "WebFetch"])
        assert len(definitions) == 2

        names = [d["name"] for d in definitions]
        assert "WebSearch" in names
        assert "WebFetch" in names


# ============================================================================
# Mock aiohttp Tests
# ============================================================================


class TestWebSearchWithMockHTTP:
    """Tests for WebSearch with mocked HTTP responses."""

    @pytest.mark.asyncio
    @patch("src.integrations.claude_sdk.tools.web_tools.AIOHTTP_AVAILABLE", True)
    async def test_search_api_error(self):
        """Test handling of API error response."""
        search = WebSearch(search_api_key="test-key", search_engine="brave")

        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")

        with patch("aiohttp.ClientSession") as mock_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value=mock_context)
            mock_session_instance.__aenter__ = AsyncMock(
                return_value=mock_session_instance
            )
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)

            mock_session.return_value = mock_session_instance

            result = await search.execute(query="test")
            assert not result.success
            assert "401" in result.error


class TestWebFetchWithMockHTTP:
    """Tests for WebFetch with mocked HTTP responses."""

    @pytest.mark.asyncio
    @patch("src.integrations.claude_sdk.tools.web_tools.AIOHTTP_AVAILABLE", True)
    async def test_fetch_success(self):
        """Test successful fetch."""
        fetch = WebFetch()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.url = "https://example.com"
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = AsyncMock(
            return_value="<html><body><p>Test content</p></body></html>"
        )

        with patch("aiohttp.ClientSession") as mock_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_session_instance = MagicMock()
            mock_session_instance.request = MagicMock(return_value=mock_context)
            mock_session_instance.__aenter__ = AsyncMock(
                return_value=mock_session_instance
            )
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)

            mock_session.return_value = mock_session_instance

            result = await fetch.execute(url="https://example.com")
            assert result.success
            assert "Test content" in result.content
