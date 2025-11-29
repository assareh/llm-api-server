"""Agentic search - Simon Willison's approach to RAG.

Instead of embeddings and vector search, this gives the LLM simple text search
tools and lets it iterate with query refinement. The LLM can:
- Search for keywords/patterns
- Refine queries ("dog OR canine")
- Run multiple parallel searches
- Browse document structure

Benefits:
- No embeddings to compute or store
- No chunking complexity
- LLM handles query expansion naturally
- Works great with frontier models

Based on: https://simonwillison.net/2024/Jun/21/search-based-rag/
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.tools import Tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class AgenticSearchConfig:
    """Configuration for agentic document search.

    Attributes:
        cache_dir: Directory containing cached documents (pages/ subdirectory)
        max_results_per_search: Maximum results to return per search (default: 20)
        context_chars: Characters of context around matches (default: 200)
        max_file_size_kb: Skip files larger than this (default: 500KB)
    """

    cache_dir: str
    max_results_per_search: int = 20
    context_chars: int = 200
    max_file_size_kb: int = 500


@dataclass
class SearchResult:
    """A single search result with context."""

    file_path: str
    url: str
    title: str
    match_text: str
    context: str
    line_number: int


class AgenticDocSearch:
    """Agentic document search using simple text matching.

    This implements Simon Willison's approach: give the LLM grep-like tools
    and let it iterate. Works with documents cached by DocumentCrawler.
    """

    def __init__(self, config: AgenticSearchConfig):
        """Initialize the agentic search.

        Args:
            config: Search configuration
        """
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.pages_dir = self.cache_dir / "pages"

        # Load URL mapping from crawler metadata
        self.url_map: dict[str, dict[str, Any]] = {}  # filename -> {url, title, ...}
        self._load_url_map()

    def _load_url_map(self) -> None:
        """Load URL mapping from crawl state."""
        import json

        crawl_state_file = self.cache_dir / "crawl_state.json"
        if crawl_state_file.exists():
            try:
                with open(crawl_state_file) as f:
                    state = json.load(f)
                    # Build reverse map: filename -> url info
                    for url, info in state.get("pages", {}).items():
                        if "cache_file" in info:
                            filename = Path(info["cache_file"]).name
                            self.url_map[filename] = {
                                "url": url,
                                "title": info.get("title", url),
                                "last_modified": info.get("last_modified"),
                            }
                logger.info(f"[AgenticSearch] Loaded {len(self.url_map)} documents from cache")
            except Exception as e:
                logger.warning(f"[AgenticSearch] Failed to load crawl state: {e}")

    def _get_cached_files(self) -> list[Path]:
        """Get list of cached HTML files."""
        if not self.pages_dir.exists():
            return []
        return list(self.pages_dir.glob("*.html"))

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract readable text from HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Get text with some structure preserved
        text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    def _get_file_info(self, file_path: Path) -> dict[str, str]:
        """Get URL and title for a cached file."""
        filename = file_path.name
        if filename in self.url_map:
            return self.url_map[filename]
        return {"url": filename, "title": filename}

    def search(self, query: str, case_sensitive: bool = False) -> list[dict[str, Any]]:
        """Search documents for a query pattern.

        Supports:
        - Simple keywords: "terraform"
        - OR patterns: "dog OR canine"
        - Phrase matching: '"exact phrase"'
        - Basic regex: "config.*file"

        Args:
            query: Search query (supports OR, quotes for phrases)
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of results with url, title, matches, and context
        """
        files = self._get_cached_files()
        if not files:
            logger.warning("[AgenticSearch] No cached documents found")
            return []

        # Parse query into pattern
        pattern = self._query_to_pattern(query, case_sensitive)
        flags = 0 if case_sensitive else re.IGNORECASE

        results = []
        max_file_bytes = self.config.max_file_size_kb * 1024

        for file_path in files:
            # Skip large files
            if file_path.stat().st_size > max_file_bytes:
                continue

            try:
                html_content = file_path.read_text(encoding="utf-8", errors="ignore")
                text = self._extract_text_from_html(html_content)
                lines = text.split("\n")

                file_info = self._get_file_info(file_path)
                file_matches = []

                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, flags):
                        # Get context (surrounding lines)
                        start = max(0, line_num - 3)
                        end = min(len(lines), line_num + 2)
                        context_lines = lines[start:end]
                        context = "\n".join(context_lines)

                        file_matches.append(
                            {
                                "line_number": line_num,
                                "match": line.strip()[:200],  # Truncate long lines
                                "context": context[: self.config.context_chars],
                            }
                        )

                        if len(file_matches) >= 5:  # Max 5 matches per file
                            break

                if file_matches:
                    results.append(
                        {
                            "url": file_info["url"],
                            "title": file_info["title"],
                            "matches": file_matches,
                            "match_count": len(file_matches),
                        }
                    )

                    if len(results) >= self.config.max_results_per_search:
                        break

            except Exception as e:
                logger.debug(f"[AgenticSearch] Error reading {file_path}: {e}")
                continue

        # Sort by number of matches
        results.sort(key=lambda x: x["match_count"], reverse=True)
        return results

    def _query_to_pattern(self, query: str, case_sensitive: bool = False) -> str:
        """Convert query to regex pattern.

        Supports:
        - OR: "dog OR canine" -> "dog|canine"
        - Quotes: '"exact phrase"' -> exact match
        - Basic regex passthrough
        """
        # Handle quoted phrases
        quoted_phrases = re.findall(r'"([^"]+)"', query)
        for phrase in quoted_phrases:
            query = query.replace(f'"{phrase}"', re.escape(phrase))

        # Handle OR
        if " OR " in query:
            parts = [p.strip() for p in query.split(" OR ")]
            return "|".join(re.escape(p) if not self._is_regex(p) else p for p in parts)

        # Check if it's already a regex pattern
        if self._is_regex(query):
            return query

        # Escape for literal matching, but allow word boundaries
        return re.escape(query)

    def _is_regex(self, s: str) -> bool:
        """Check if string contains regex special chars (intentional pattern)."""
        regex_chars = [".*", ".+", "\\d", "\\w", "\\s", "[", "]", "^", "$", "|"]
        return any(c in s for c in regex_chars)

    def list_documents(self, pattern: str = "") -> list[dict[str, str]]:
        """List available documents, optionally filtered by pattern.

        Args:
            pattern: Optional filter pattern for titles/URLs

        Returns:
            List of documents with url and title
        """
        files = self._get_cached_files()
        docs = []

        for file_path in files:
            info = self._get_file_info(file_path)
            # Filter by pattern in title or URL if pattern is provided
            if pattern and not (pattern.lower() in info["title"].lower() or pattern.lower() in info["url"].lower()):
                continue
            docs.append({"url": info["url"], "title": info["title"]})

        # Sort by title
        docs.sort(key=lambda x: x["title"])
        return docs

    def get_document(self, url_or_title: str) -> dict[str, Any] | None:
        """Get full content of a specific document.

        Args:
            url_or_title: URL or title to match

        Returns:
            Document content with url, title, and full text
        """
        files = self._get_cached_files()

        for file_path in files:
            info = self._get_file_info(file_path)
            if url_or_title in info["url"] or url_or_title.lower() in info["title"].lower():
                try:
                    html_content = file_path.read_text(encoding="utf-8", errors="ignore")
                    text = self._extract_text_from_html(html_content)
                    return {
                        "url": info["url"],
                        "title": info["title"],
                        "content": text[:10000],  # Limit to 10K chars
                        "truncated": len(text) > 10000,
                    }
                except Exception as e:
                    logger.error(f"[AgenticSearch] Error reading document: {e}")
                    return None

        return None


# Pydantic models for tool inputs


class TextSearchInput(BaseModel):
    """Input schema for text search tool."""

    query: str = Field(
        description=(
            "Search query. Supports:\n"
            '- Keywords: "terraform"\n'
            '- OR patterns: "dog OR canine OR puppy"\n'
            "- Phrases: '\"exact phrase\"'\n"
            '- Regex: "config.*file"'
        )
    )


class ListDocsInput(BaseModel):
    """Input schema for list documents tool."""

    pattern: str = Field(
        default="",
        description="Optional filter pattern for document titles/URLs (e.g., 'auth' to find authentication docs)",
    )


class GetDocInput(BaseModel):
    """Input schema for get document tool."""

    url_or_title: str = Field(description="URL or title of the document to retrieve (partial match supported)")


def create_agentic_search_tools(
    config: AgenticSearchConfig,
    name_prefix: str = "docs",
) -> list[Tool]:
    """Create a set of tools for agentic document search.

    Returns 3 tools:
    - {prefix}_search: Search documents with keyword/regex patterns
    - {prefix}_list: List available documents
    - {prefix}_read: Read full content of a specific document

    Args:
        config: AgenticSearchConfig with cache directory
        name_prefix: Prefix for tool names (default: "docs")

    Returns:
        List of LangChain Tools

    Example:
        >>> config = AgenticSearchConfig(cache_dir="./doc_cache")
        >>> tools = create_agentic_search_tools(config)
        >>> # LLM can now search iteratively:
        >>> # 1. docs_search("authentication")
        >>> # 2. docs_search("auth OR login OR oauth")
        >>> # 3. docs_read("API Authentication Guide")
    """
    searcher = AgenticDocSearch(config)

    def _search(query: str) -> str:
        """Search documents and format results."""
        results = searcher.search(query)
        if not results:
            return f"No documents found matching '{query}'. Try different keywords or use OR for alternatives (e.g., 'auth OR login')."

        output = [f"Found {len(results)} documents matching '{query}':\n"]
        for i, doc in enumerate(results, 1):
            output.append(f"\n**{i}. {doc['title']}**")
            output.append(f"   URL: {doc['url']}")
            for match in doc["matches"][:2]:  # Show first 2 matches per doc
                output.append(f"   Line {match['line_number']}: {match['match'][:100]}...")
        output.append("\n\nTip: Use docs_read to get full content of a specific document.")
        return "\n".join(output)

    def _list_docs(pattern: str = "") -> str:
        """List documents and format results."""
        docs = searcher.list_documents(pattern)
        if not docs:
            if pattern:
                return f"No documents found matching '{pattern}'. Try a different filter or leave empty to list all."
            return "No documents in the index. Has the crawler been run?"

        output = [f"Found {len(docs)} documents" + (f" matching '{pattern}'" if pattern else "") + ":\n"]
        for doc in docs[:30]:  # Limit to 30
            output.append(f"- {doc['title']}")
            output.append(f"  {doc['url']}")
        if len(docs) > 30:
            output.append(f"\n... and {len(docs) - 30} more. Use a filter pattern to narrow down.")
        return "\n".join(output)

    def _get_doc(url_or_title: str) -> str:
        """Get document content."""
        doc = searcher.get_document(url_or_title)
        if not doc:
            return f"Document not found: '{url_or_title}'. Use docs_list to see available documents."

        output = [f"**{doc['title']}**", f"URL: {doc['url']}", "", doc["content"]]
        if doc.get("truncated"):
            output.append("\n\n[Content truncated - document is very long]")
        return "\n".join(output)

    return [
        Tool(
            name=f"{name_prefix}_search",
            description=(
                "Search documents using keywords, OR patterns, or regex. "
                "The LLM should refine queries based on results - e.g., if 'authentication' "
                "returns few results, try 'auth OR login OR oauth OR SSO'. "
                "Returns matching excerpts with context."
            ),
            func=_search,
            args_schema=TextSearchInput,
        ),
        Tool(
            name=f"{name_prefix}_list",
            description=(
                "List all available documents, optionally filtered by a pattern. "
                "Use this to understand what documentation is available before searching."
            ),
            func=_list_docs,
            args_schema=ListDocsInput,
        ),
        Tool(
            name=f"{name_prefix}_read",
            description=(
                "Read the full content of a specific document by URL or title. "
                "Use after docs_search to get complete information from a relevant document."
            ),
            func=_get_doc,
            args_schema=GetDocInput,
        ),
    ]


# Convenience function for quick setup
def create_agentic_search_tool(
    cache_dir: str,
    name: str = "doc_search",
    description: str | None = None,
) -> Tool:
    """Create a single combined agentic search tool.

    This is a simpler alternative that provides one tool with search capability.
    For more control, use create_agentic_search_tools() which returns 3 tools.

    Args:
        cache_dir: Directory containing cached documents
        name: Tool name
        description: Custom description

    Returns:
        Single LangChain Tool
    """
    config = AgenticSearchConfig(cache_dir=cache_dir)
    searcher = AgenticDocSearch(config)

    default_description = (
        "Search documentation using text patterns. Supports OR for alternatives "
        "(e.g., 'auth OR login'), phrases in quotes, and regex patterns. "
        "Refine your search based on results."
    )

    def _search(query: str) -> str:
        results = searcher.search(query)
        if not results:
            return f"No results for '{query}'. Try synonyms with OR (e.g., 'dog OR canine')."

        output = []
        for doc in results[:10]:
            output.append(f"\n## {doc['title']}\n{doc['url']}\n")
            for match in doc["matches"][:3]:
                output.append(f"- {match['match']}")
        return "\n".join(output)

    return Tool(
        name=name,
        description=description or default_description,
        func=_search,
        args_schema=TextSearchInput,
    )
