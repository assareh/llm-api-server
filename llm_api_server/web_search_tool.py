"""Web search tool with Ollama API and DuckDuckGo fallback support.

This module provides web search functionality that tries Ollama's web search API
first (if an API key is configured) and falls back to DuckDuckGo if unavailable.

Optional dependencies: duckduckgo-search
Install with: uv sync --extra websearch
"""

import logging

# Optional imports - gracefully handle if not installed
try:
    from duckduckgo_search import DDGS

    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

logger = logging.getLogger(__name__)


def ollama_web_search(query: str, max_results: int = 10, api_key: str = "") -> list[dict[str, str]]:
    """Search the web using Ollama's search API.

    Args:
        query: The search query
        max_results: Maximum number of results (not enforced by API, but used for consistency)
        api_key: Ollama API key for authentication

    Returns:
        List of search result dictionaries with 'title', 'url', and 'description' keys

    Raises:
        ValueError: If API key is not provided
        Exception: If API call fails
    """
    if not api_key:
        raise ValueError("OLLAMA_API_KEY not configured")

    logger.info(f"[OLLAMA_SEARCH] Searching with query: {query}")

    try:
        import requests

        # Make API request to Ollama web search endpoint
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        response = requests.post(
            "https://api.ollama.ai/v1/web/search",
            headers=headers,
            json={"query": query, "max_results": max_results},
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        results = []

        # Parse response
        items = data.get("results", [])

        # Limit to max_results
        for item in items[:max_results]:
            results.append(
                {
                    "title": item.get("title", "No title"),
                    "url": item.get("url", ""),
                    "description": item.get("content", item.get("description", "No description")),
                }
            )

        logger.info(f"[OLLAMA_SEARCH] Found {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"[OLLAMA_SEARCH] Search failed: {e}")
        raise


def ddg_web_search(query: str, max_results: int = 10) -> list[dict[str, str]]:
    """Search the web using DuckDuckGo (free, rate-limited).

    Args:
        query: The search query
        max_results: Maximum number of results

    Returns:
        List of search result dictionaries with 'title', 'url', and 'description' keys

    Raises:
        ImportError: If duckduckgo-search is not installed
        Exception: If search fails
    """
    if not HAS_DDGS:
        raise ImportError(
            "DuckDuckGo search requires duckduckgo-search package. "
            "Install with: uv sync --extra websearch or pip install duckduckgo-search"
        )

    logger.info(f"[DDG_SEARCH] Searching with query: {query}")

    try:
        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*AsyncSession.*")
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))

        results = []
        for item in raw_results:
            results.append(
                {
                    "title": item.get("title", "No title"),
                    "url": item.get("href", ""),
                    "description": item.get("body", "No description"),
                }
            )

        logger.info(f"[DDG_SEARCH] Found {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"[DDG_SEARCH] Search failed: {e}")
        raise


def web_search(query: str, max_results: int = 10, site: str = "", ollama_api_key: str = "") -> str:
    """Search the web using Ollama API if available, otherwise fall back to DuckDuckGo.

    Args:
        query: The search query
        max_results: Maximum number of results (default 10)
        site: Optional site restriction (e.g., 'hashicorp.com')
        ollama_api_key: Ollama API key (optional, from config)

    Returns:
        Formatted string with search results
    """
    # Build search query with site restriction if provided
    search_query = f"site:{site} {query}" if site else query

    results = []
    search_method = "unknown"

    # Try Ollama first if API key is configured
    if ollama_api_key:
        try:
            logger.info("[WEB_SEARCH] Using Ollama search API")
            results = ollama_web_search(search_query, max_results, ollama_api_key)
            search_method = "Ollama"
        except Exception as e:
            logger.warning(f"[WEB_SEARCH] Ollama search failed, falling back to DuckDuckGo: {e}")
            # Fall through to DuckDuckGo

    # Fall back to DuckDuckGo if Ollama not available or failed
    if not results:
        try:
            logger.info("[WEB_SEARCH] Using DuckDuckGo search")
            results = ddg_web_search(search_query, max_results)
            search_method = "DuckDuckGo"
        except Exception as e:
            error_str = str(e)
            if "ratelimit" in error_str.lower():
                return "Web search is currently rate-limited. Please try again in a few moments or configure OLLAMA_API_KEY in your .env file for unlimited searches."
            elif isinstance(e, ImportError):
                return f"Web search failed: {error_str}"
            else:
                return f"Web search failed: {error_str}"

    # Format results
    if not results:
        return f"No web results found for query: '{query}'"

    output = [f"Found {len(results)} web result(s) via {search_method}:\n"]

    for idx, result in enumerate(results, 1):
        output.append(f"\n{idx}. {result['title']}")
        output.append(f"   URL: {result['url']}")
        output.append(f"   {result['description']}")
        output.append("")

    return "\n".join(output)


__all__ = ["ddg_web_search", "ollama_web_search", "web_search"]
