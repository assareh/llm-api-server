"""RAG (Retrieval-Augmented Generation) module for document search and indexing.

This module provides local RAG capabilities with:
- Sitemap-based and recursive web crawling
- Semantic HTML-aware chunking with parent-child relationships
- Hybrid search (BM25 + semantic vector search)
- Cross-encoder re-ranking
- Incremental index updates
- FAISS vector storage (CPU-optimized, local)

Two approaches are available:

1. **DocSearchIndex** (embeddings-based):
   - Uses vector embeddings + BM25 hybrid search
   - Better for large document sets, consistent performance
   - Requires embedding model loading

2. **AgenticDocSearch** (Simon Willison's approach):
   - Simple text search with LLM query refinement
   - No embeddings needed, faster startup
   - LLM iterates with "dog OR canine" patterns
   - Great for smaller doc sets or experimentation

Example usage (embeddings-based):
    from llm_api_server.rag import DocSearchIndex, RAGConfig

    config = RAGConfig(
        base_url="https://docs.example.com",
        cache_dir="./doc_index",
    )
    index = DocSearchIndex(config)
    index.crawl_and_index()
    results = index.search("authentication", top_k=5)

Example usage (agentic):
    from llm_api_server.rag import AgenticSearchConfig, create_agentic_search_tools

    config = AgenticSearchConfig(cache_dir="./doc_index")
    tools = create_agentic_search_tools(config)
    # Give these tools to your LLM - it will search iteratively
"""

from .agentic_search import (
    AgenticDocSearch,
    AgenticSearchConfig,
    create_agentic_search_tool,
    create_agentic_search_tools,
)
from .config import RAGConfig
from .indexer import DocSearchIndex

__all__ = [
    "AgenticDocSearch",
    "AgenticSearchConfig",
    "DocSearchIndex",
    "RAGConfig",
    "create_agentic_search_tool",
    "create_agentic_search_tools",
]
