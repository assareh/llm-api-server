"""Unit tests for DocSearchIndex lightweight behaviors."""

from pathlib import Path

import pytest
from langchain_core.documents import Document

from llm_api_server.rag import DocSearchIndex, RAGConfig


@pytest.mark.unit
def test_load_index_rebuilds_child_to_parent_mapping(tmp_path: Path, monkeypatch):
    """Ensure load_index reconstructs child_to_parent from cached chunk metadata."""
    config = RAGConfig(base_url="https://example.com", cache_dir=tmp_path)

    # Write cached chunks/parents to disk
    writer = DocSearchIndex(config)
    writer.chunks = [
        Document(
            page_content="child content",
            metadata={
                "chunk_id": "child-1",
                "parent_id": "parent-1",
                "url": "https://example.com/page",
            },
        )
    ]
    writer.parent_chunks = {"parent-1": {"text": "parent content", "url": "https://example.com/page"}}
    writer._save_chunks()
    writer._save_parent_chunks()

    # New instance simulates fresh process
    loader = DocSearchIndex(config)
    monkeypatch.setattr(loader, "_initialize_components", lambda: None)
    monkeypatch.setattr(loader, "_build_retrievers", lambda: None)

    loader.load_index()

    assert loader.child_to_parent == {"child-1": "parent-1"}
    assert loader.chunks[0].metadata["chunk_id"] == "child-1"
    assert loader.parent_chunks["parent-1"]["text"] == "parent content"
