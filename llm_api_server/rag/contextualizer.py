"""Contextual Retrieval - LLM-generated context for chunks.

Implements Anthropic's Contextual Retrieval approach:
https://www.anthropic.com/news/contextual-retrieval

Key idea: Prepend LLM-generated context to each chunk before embedding,
reducing retrieval failures by ~40-50% when combined with hybrid search + reranking.

The context situates the chunk within the overall document, e.g.:
"This chunk is from the Configuration section of the Vault PKI documentation.
It describes certificate authority setup options."
"""

import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from .config import RAGConfig

logger = logging.getLogger(__name__)


class ChunkContextualizer:
    """Generate and cache contextual prefixes for document chunks using local LLM."""

    def __init__(self, config: RAGConfig, cache_dir: Path):
        """Initialize the contextualizer.

        Args:
            config: RAG configuration with contextual retrieval settings
            cache_dir: Directory to cache contextualized chunks
        """
        self.config = config
        self.cache_dir = cache_dir
        self.context_cache_file = cache_dir / "chunk_contexts.json"

        # Load existing context cache
        self.context_cache: dict[str, str] = self._load_context_cache()

    def contextualize_chunks(
        self,
        chunks: list[dict[str, Any]],
        page_contents: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Add contextual prefixes to chunks using local LLM.

        Args:
            chunks: List of chunk dicts with 'content', 'chunk_id', and 'url' or parent with 'url'
            page_contents: Dict mapping URL -> full page text content

        Returns:
            Chunks with contextualized content (context prepended)
        """
        if not self.config.contextual_retrieval_enabled:
            return chunks

        logger.info(f"[RAG] Contextualizing {len(chunks)} chunks using {self.config.contextual_model}...")
        start_time = time.time()

        # Identify chunks that need context generation (not in cache)
        chunks_to_process = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            content_hash = self._hash_content(chunk.get("content", ""))

            # Check cache by chunk_id + content hash
            cache_key = f"{chunk_id}:{content_hash}"
            if cache_key not in self.context_cache:
                chunks_to_process.append((chunk, cache_key))

        cached_count = len(chunks) - len(chunks_to_process)
        if cached_count > 0:
            logger.info(
                f"[RAG] Using cached context for {cached_count} chunks, generating for {len(chunks_to_process)}"
            )

        # Generate context for uncached chunks in parallel
        if chunks_to_process:
            self._generate_contexts_parallel(chunks_to_process, page_contents)
            # Save updated cache
            self._save_context_cache()

        # Apply context to all chunks
        contextualized_chunks = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            content_hash = self._hash_content(chunk.get("content", ""))
            cache_key = f"{chunk_id}:{content_hash}"

            context = self.context_cache.get(cache_key, "")
            if context:
                # Prepend context to chunk content
                contextualized_content = f"<context>\n{context}\n</context>\n\n{chunk['content']}"
                contextualized_chunk = {
                    **chunk,
                    "content": contextualized_content,
                    "original_content": chunk["content"],
                }
            else:
                contextualized_chunk = chunk

            contextualized_chunks.append(contextualized_chunk)

        elapsed = time.time() - start_time
        logger.info(f"[RAG] Contextualization complete in {elapsed:.1f}s")

        return contextualized_chunks

    def _generate_contexts_parallel(
        self,
        chunks_to_process: list[tuple[dict[str, Any], str]],
        page_contents: dict[str, str],
    ):
        """Generate contexts for chunks in parallel using ThreadPoolExecutor.

        Args:
            chunks_to_process: List of (chunk, cache_key) tuples
            page_contents: Dict mapping URL -> full page text content
        """
        total = len(chunks_to_process)
        completed = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=self.config.contextual_max_workers) as executor:
            # Submit all tasks
            future_to_chunk = {}
            for chunk, cache_key in chunks_to_process:
                url = chunk.get("url") or chunk.get("metadata", {}).get("url", "")
                document_content = page_contents.get(url, "")

                if not document_content:
                    logger.warning(f"[RAG] No document content found for URL: {url}")
                    continue

                future = executor.submit(
                    self._generate_single_context,
                    chunk["content"],
                    document_content,
                )
                future_to_chunk[future] = (chunk, cache_key)

            # Process completed tasks
            for future in as_completed(future_to_chunk):
                chunk, cache_key = future_to_chunk[future]
                completed += 1

                try:
                    context = future.result()
                    if context:
                        self.context_cache[cache_key] = context
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"[RAG] Context generation failed for chunk {chunk.get('chunk_id')}: {e}")
                    failed += 1

                # Progress update every 10 chunks or at milestones
                if completed % 10 == 0 or completed == total or completed in [1, 5, 25, 50]:
                    logger.info(
                        f"[RAG] Context generation: {completed}/{total} ({100*completed/total:.1f}%) "
                        f"- {failed} failed"
                    )

    def _generate_single_context(self, chunk_content: str, document_content: str) -> str | None:
        """Generate context for a single chunk using Ollama.

        Args:
            chunk_content: The chunk text to contextualize
            document_content: The full document text

        Returns:
            Generated context string, or None if failed
        """
        # Build prompt from template
        prompt = self.config.contextual_prompt.format(
            document=document_content,
            chunk=chunk_content,
        )

        try:
            response = requests.post(
                f"{self.config.contextual_ollama_base_url}/api/generate",
                json={
                    "model": self.config.contextual_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.config.contextual_timeout,
            )
            response.raise_for_status()

            result = response.json()
            context = result.get("response", "").strip()

            # Basic validation - context should be reasonable length
            if len(context) < 10:
                logger.warning(f"[RAG] Generated context too short: {context[:50]}")
                return None

            if len(context) > 1000:
                # Truncate overly long contexts
                context = context[:1000] + "..."
                logger.debug("[RAG] Truncated long context to 1000 chars")

            return context

        except requests.exceptions.Timeout:
            logger.warning(f"[RAG] Context generation timed out after {self.config.contextual_timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[RAG] Ollama request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"[RAG] Context generation error: {e}")
            return None

    def _hash_content(self, content: str) -> str:
        """Generate hash of content for cache key."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _load_context_cache(self) -> dict[str, str]:
        """Load context cache from disk."""
        if not self.context_cache_file.exists():
            return {}

        try:
            cache = json.loads(self.context_cache_file.read_text())
            logger.info(f"[RAG] Loaded {len(cache)} cached chunk contexts")
            return cache
        except Exception as e:
            logger.warning(f"[RAG] Failed to load context cache: {e}")
            return {}

    def _save_context_cache(self):
        """Save context cache to disk."""
        try:
            self.context_cache_file.write_text(json.dumps(self.context_cache, indent=2))
            logger.debug(f"[RAG] Saved {len(self.context_cache)} chunk contexts to cache")
        except Exception as e:
            logger.error(f"[RAG] Failed to save context cache: {e}")

    def clear_cache(self):
        """Clear the context cache (forces regeneration on next run)."""
        self.context_cache = {}
        if self.context_cache_file.exists():
            self.context_cache_file.unlink()
        logger.info("[RAG] Context cache cleared")
