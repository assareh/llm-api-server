"""RAG (Retrieval-Augmented Generation) module for document search and indexing.

This module provides local RAG capabilities with:
- Sitemap-based and recursive web crawling
- Semantic HTML-aware chunking with parent-child relationships
- Hybrid search (BM25 + semantic vector search)
- Cross-encoder re-ranking
- Incremental index updates
- FAISS vector storage (CPU-optimized, local)

Example usage:
    from llm_api_server.rag import DocSearchIndex, RAGConfig

    # Configure RAG
    config = RAGConfig(
        base_url="https://docs.example.com",
        cache_dir="./doc_index",
    )

    # Build index
    index = DocSearchIndex(config)
    index.crawl_and_index()

    # Search
    results = index.search("How do I configure authentication?", top_k=5)
"""

from .config import RAGConfig
from .indexer import DocSearchIndex

__all__ = [
    "DocSearchIndex",
    "RAGConfig",
]
