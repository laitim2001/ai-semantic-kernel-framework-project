"""Web tools for Claude SDK.

Sprint 49: S49-4 - Web Tools (8 pts)
Implements WebSearch and WebFetch for web interactions.
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .base import Tool, ToolResult


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
        }


class HTMLTextExtractor(HTMLParser):
    """Extract text content from HTML."""

    def __init__(self):
        super().__init__()
        self.result = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript", "head", "meta"}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag.lower() in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self.result.append(text)

    def get_text(self) -> str:
        """Get extracted text."""
        return " ".join(self.result)


def extract_text_from_html(html: str) -> str:
    """Extract plain text from HTML content.

    Args:
        html: HTML content

    Returns:
        Plain text content
    """
    try:
        parser = HTMLTextExtractor()
        parser.feed(html)
        return parser.get_text()
    except Exception:
        # Fallback: simple regex-based extraction
        # Remove script and style blocks
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Clean whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()


class WebSearch(Tool):
    """Search the web for information.

    This tool performs web searches and returns results.
    Requires configuration of a search API (Google, Bing, Brave, etc.)

    Args:
        search_api_key: API key for search service
        search_engine: Search engine to use ('google', 'bing', 'brave')
        search_endpoint: Custom search API endpoint

    Example:
        search = WebSearch(search_api_key="your-api-key", search_engine="brave")
        result = await search.execute(query="Python tutorials")
    """

    name = "WebSearch"
    description = "Search the web and return results. Returns titles, URLs, and snippets."

    def __init__(
        self,
        search_api_key: Optional[str] = None,
        search_engine: str = "brave",
        search_endpoint: Optional[str] = None,
    ):
        self.api_key = search_api_key
        self.search_engine = search_engine
        self.search_endpoint = search_endpoint or self._get_default_endpoint()

    def _get_default_endpoint(self) -> str:
        """Get default API endpoint for search engine."""
        endpoints = {
            "brave": "https://api.search.brave.com/res/v1/web/search",
            "google": "https://www.googleapis.com/customsearch/v1",
            "bing": "https://api.bing.microsoft.com/v7.0/search",
        }
        return endpoints.get(self.search_engine, endpoints["brave"])

    async def execute(
        self,
        query: str,
        num_results: int = 10,
    ) -> ToolResult:
        """Search the web.

        Args:
            query: Search query string
            num_results: Maximum number of results to return (1-20)

        Returns:
            ToolResult with formatted search results
        """
        # Validate inputs
        if not query or not query.strip():
            return ToolResult(
                content="",
                success=False,
                error="Search query cannot be empty",
            )

        num_results = max(1, min(num_results, 20))

        # Check if API is configured
        if not self.api_key:
            return ToolResult(
                content=f"Search query: {query}\n\n"
                        f"WebSearch requires configuration:\n"
                        f"  - search_api_key: API key for your search provider\n"
                        f"  - search_engine: 'brave', 'google', or 'bing'\n\n"
                        f"Example:\n"
                        f"  search = WebSearch(search_api_key='your-key', search_engine='brave')",
                success=True,
            )

        # Check if aiohttp is available
        if not AIOHTTP_AVAILABLE:
            return ToolResult(
                content="",
                success=False,
                error="aiohttp package is required for WebSearch. Install with: pip install aiohttp",
            )

        try:
            results = await self._perform_search(query, num_results)
            return self._format_results(query, results)

        except Exception as e:
            return ToolResult(
                content="",
                success=False,
                error=f"Search failed: {str(e)}",
            )

    async def _perform_search(
        self,
        query: str,
        num_results: int,
    ) -> List[SearchResult]:
        """Perform the actual search API call."""
        headers = {}
        params = {}

        if self.search_engine == "brave":
            headers["X-Subscription-Token"] = self.api_key
            params = {"q": query, "count": num_results}

        elif self.search_engine == "google":
            params = {"key": self.api_key, "q": query, "num": num_results}

        elif self.search_engine == "bing":
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
            params = {"q": query, "count": num_results}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.search_endpoint,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Search API returned {response.status}: {error_text[:200]}")

                data = await response.json()
                return self._parse_response(data)

    def _parse_response(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse search API response into SearchResult objects."""
        results = []

        if self.search_engine == "brave":
            for item in data.get("web", {}).get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                ))

        elif self.search_engine == "google":
            for item in data.get("items", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                ))

        elif self.search_engine == "bing":
            for item in data.get("webPages", {}).get("value", []):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                ))

        return results

    def _format_results(self, query: str, results: List[SearchResult]) -> ToolResult:
        """Format search results as text."""
        if not results:
            return ToolResult(
                content=f"No results found for: {query}",
                success=True,
            )

        lines = [f"Search results for: {query}\n"]

        for i, result in enumerate(results, 1):
            lines.append(f"{i}. {result.title}")
            lines.append(f"   URL: {result.url}")
            lines.append(f"   {result.snippet}")
            lines.append("")

        return ToolResult(content="\n".join(lines))

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-20)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["query"],
        }


class WebFetch(Tool):
    """Fetch and process content from a URL.

    This tool retrieves web page content and can extract text from HTML.

    Args:
        timeout: Request timeout in seconds
        max_content_length: Maximum content size to return
        user_agent: Custom User-Agent header
        extract_text: Whether to extract plain text from HTML

    Example:
        fetch = WebFetch(timeout=30, extract_text=True)
        result = await fetch.execute(url="https://example.com")
    """

    name = "WebFetch"
    description = "Fetch and process content from a URL. Can extract text from HTML."

    # Default user agent
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (compatible; ClaudeSDK/1.0; +https://anthropic.com)"
    )

    def __init__(
        self,
        timeout: int = 30,
        max_content_length: int = 500000,
        user_agent: Optional[str] = None,
        extract_text: bool = True,
    ):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.extract_text = extract_text

    async def execute(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        timeout: Optional[int] = None,
        extract_text: Optional[bool] = None,
    ) -> ToolResult:
        """Fetch content from a URL.

        Args:
            url: URL to fetch
            headers: Additional request headers
            method: HTTP method (GET, POST, etc.)
            timeout: Timeout override in seconds
            extract_text: Override for text extraction

        Returns:
            ToolResult with page content and metadata
        """
        # Validate URL
        if not url or not url.strip():
            return ToolResult(
                content="",
                success=False,
                error="URL cannot be empty",
            )

        # Parse and validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = "https://" + url
                parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return ToolResult(
                    content="",
                    success=False,
                    error=f"Unsupported URL scheme: {parsed.scheme}",
                )
        except Exception as e:
            return ToolResult(
                content="",
                success=False,
                error=f"Invalid URL: {str(e)}",
            )

        # Check if aiohttp is available
        if not AIOHTTP_AVAILABLE:
            return ToolResult(
                content="",
                success=False,
                error="aiohttp package is required for WebFetch. Install with: pip install aiohttp",
            )

        # Build headers
        request_headers = {"User-Agent": self.user_agent}
        if headers:
            request_headers.update(headers)

        # Use instance defaults or overrides
        request_timeout = timeout or self.timeout
        should_extract = extract_text if extract_text is not None else self.extract_text

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method.upper(),
                    url=url,
                    headers=request_headers,
                    timeout=aiohttp.ClientTimeout(total=request_timeout),
                    allow_redirects=True,
                ) as response:
                    # Read content
                    content = await response.text()

                    # Truncate if needed
                    truncated = False
                    if len(content) > self.max_content_length:
                        content = content[:self.max_content_length]
                        truncated = True

                    # Get content type
                    content_type = response.headers.get("Content-Type", "")
                    is_html = "text/html" in content_type.lower()

                    # Extract text from HTML if requested
                    if should_extract and is_html:
                        content = extract_text_from_html(content)

                    # Build response
                    result_lines = [
                        f"URL: {str(response.url)}",
                        f"Status: {response.status} {response.reason}",
                        f"Content-Type: {content_type}",
                        f"Content-Length: {len(content)} chars",
                    ]

                    if truncated:
                        result_lines.append(f"(truncated at {self.max_content_length} chars)")

                    result_lines.append("")
                    result_lines.append(content)

                    return ToolResult(
                        content="\n".join(result_lines),
                        success=response.status < 400,
                    )

        except aiohttp.ClientConnectorError as e:
            return ToolResult(
                content="",
                success=False,
                error=f"Connection failed: {str(e)}",
            )
        except aiohttp.ClientResponseError as e:
            return ToolResult(
                content="",
                success=False,
                error=f"HTTP error {e.status}: {str(e)}",
            )
        except TimeoutError:
            return ToolResult(
                content="",
                success=False,
                error=f"Request timed out after {request_timeout} seconds",
            )
        except Exception as e:
            return ToolResult(
                content="",
                success=False,
                error=f"Fetch failed: {str(e)}",
            )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch",
                },
                "headers": {
                    "type": "object",
                    "description": "Additional HTTP headers",
                    "additionalProperties": {"type": "string"},
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "default": "GET",
                    "enum": ["GET", "POST", "HEAD", "OPTIONS"],
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                },
                "extract_text": {
                    "type": "boolean",
                    "description": "Extract plain text from HTML",
                },
            },
            "required": ["url"],
        }
