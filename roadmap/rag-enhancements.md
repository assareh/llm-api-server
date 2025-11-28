# RAG Module Enhancement Roadmap

This document outlines potential enhancements to the RAG (Retrieval-Augmented Generation) module identified during implementation review.

## Current State

The RAG module is production-ready with solid fundamentals:
- Parent-child chunking with hierarchical context
- Hybrid search using Reciprocal Rank Fusion (RRF)
- Cross-encoder re-ranking (MS MARCO)
- Token-aware chunking with tiktoken
- Local-first design (FAISS + HuggingFace)

## Proposed Enhancements

### 1. Crawler Robustness

**Priority:** Medium
**Complexity:** Low-Medium

#### Exponential Backoff for Rate Limiting

**Current:** Fixed delay between requests (`rate_limit_delay`)
**Proposed:** Add exponential backoff for 429/503 responses

```python
# Proposed config additions
retry_backoff_base: float = 2.0      # Base multiplier
retry_backoff_max: float = 60.0      # Max delay in seconds
retry_on_status_codes: list = [429, 503, 502]
```

**Benefits:**
- More resilient to temporary server issues
- Respects server rate limiting signals
- Reduces failed crawls

#### Circuit Breaker Pattern

**Current:** Retry up to `max_url_retries` per URL
**Proposed:** Add circuit breaker for domains with repeated failures

```python
# Proposed config additions
circuit_breaker_threshold: int = 5   # Failures before opening circuit
circuit_breaker_timeout: float = 300 # Seconds before retry
```

**Benefits:**
- Faster crawl completion when domain is down
- Prevents wasted requests to failing servers

---

### 2. Query Enhancement

**Priority:** Medium
**Complexity:** Medium

#### Query Expansion / Synonyms

**Current:** Queries searched as-is
**Proposed:** Add optional query expansion

Options:
- **Static synonyms:** User-provided synonym map
- **LLM-based expansion:** Use embedding model to find related terms
- **WordNet integration:** Leverage lexical database

```python
# Proposed config additions
query_expansion_enabled: bool = False
synonym_map: dict[str, list[str]] = {}  # {"terraform": ["tf", "hcl"]}
```

**Benefits:**
- Better recall for technical terminology
- Handles abbreviations and aliases

#### Query Reformulation

**Current:** Single query execution
**Proposed:** Generate multiple query variants, merge results

```python
def search_with_reformulation(self, query: str, variants: int = 3) -> list:
    # Generate query variants (paraphrases)
    # Execute each variant
    # Merge and deduplicate results via RRF
```

**Benefits:**
- Improved recall for ambiguous queries
- Captures different phrasings of same intent

---

### 3. Metadata-Based Filtering

**Priority:** Medium
**Complexity:** Low

#### Pre-Search Filtering

**Current:** No filtering before search
**Proposed:** Add metadata filters to search API

```python
results = index.search(
    query="authentication",
    top_k=5,
    filters={
        "doc_type": ["tutorial", "guide"],      # Include only these types
        "version": ">=2.0",                      # Version constraint
        "date_range": ("2024-01-01", None),     # After date
    }
)
```

**Benefits:**
- Scoped search within document subsets
- Better precision for known constraints
- Enables faceted search UX

---

### 4. Content Format Support

**Priority:** Low
**Complexity:** Medium

#### Markdown Support

**Current:** HTML only
**Proposed:** Add markdown chunking path

```python
# Proposed config additions
content_formats: list = ["html", "markdown"]  # Supported formats
```

Implementation:
- Detect content type (HTML vs Markdown)
- Route to appropriate chunker
- Unify output format (both produce `Document` objects)

**Benefits:**
- Index markdown documentation directly
- Support for GitHub READMEs, wiki pages

---

### 5. Observability & Monitoring

**Priority:** Medium
**Complexity:** Low-Medium

#### Metrics Export

**Current:** Logging only
**Proposed:** Add optional metrics hooks

```python
# Proposed config additions
metrics_enabled: bool = False
metrics_callback: Callable | None = None  # User-provided callback

# Metrics to track:
# - crawl_duration_seconds
# - pages_crawled_total
# - chunks_created_total
# - search_latency_seconds
# - rerank_latency_seconds
# - cache_hit_ratio
```

**Benefits:**
- Integration with Prometheus, DataDog, etc.
- Performance profiling
- Production monitoring dashboards

#### Index Health Checks

**Current:** Checksum verification only
**Proposed:** Add comprehensive health check

```python
def health_check(self) -> HealthStatus:
    return HealthStatus(
        index_age_hours=...,
        document_count=...,
        tombstone_ratio=...,      # For incremental updates
        embedding_model_match=...,
        last_error=...,
    )
```

**Benefits:**
- Proactive issue detection
- Automated alerting on staleness

---

### 6. Chunking Improvements

**Priority:** Low
**Complexity:** Medium

#### NLP-Based Sentence Splitting

**Current:** Regex-based sentence splitting
**Proposed:** Optional NLP tokenizer (spaCy, NLTK)

```python
# Proposed config additions
sentence_splitter: str = "regex"  # "regex", "spacy", "nltk"
```

**Benefits:**
- Better handling of abbreviations (Dr., Inc., etc.)
- Improved accuracy for complex sentences

#### Configurable Boilerplate Selectors

**Current:** Hard-coded CSS selectors for boilerplate removal (now applied in v0.7.2)
**Proposed:** Make selectors configurable via RAGConfig

```python
# Proposed config additions
boilerplate_selectors: list = [
    "nav", "aside", "footer", "header",
    ".sidebar", ".navigation", ".breadcrumb"
]
custom_boilerplate_selectors: list = []  # User additions
```

**Benefits:**
- Adapt to different site structures
- Remove site-specific noise

---

### 7. Advanced Search Features

**Priority:** Low
**Complexity:** High

#### Multi-Hop Retrieval

**Current:** Single-stage retrieval
**Proposed:** Iterative retrieval with context accumulation

Use case: Complex questions requiring information from multiple documents.

**Complexity:** Requires integration with LLM for query decomposition.

#### Hybrid Re-ranking During Retrieval

**Current:** Re-ranking happens post-retrieval
**Proposed:** Integrate re-ranking into retrieval pipeline

Options:
- ColBERT-style late interaction
- Dense Passage Retrieval (DPR) with cross-attention

**Benefits:**
- Better precision at lower latency
- Reduced candidate pool requirements

---

## Implementation Priority Matrix

| Enhancement | Priority | Complexity | Impact |
|------------|----------|------------|--------|
| Exponential backoff | Medium | Low | High |
| Circuit breaker | Medium | Low | Medium |
| Query expansion | Medium | Medium | Medium |
| Metadata filtering | Medium | Low | High |
| Metrics export | Medium | Low | Medium |
| Health checks | Medium | Low | Medium |
| Markdown support | Low | Medium | Medium |
| NLP sentence splitting | Low | Medium | Low |
| Configurable selectors | Low | Low | Low |
| Multi-hop retrieval | Low | High | Medium |
| Hybrid re-ranking | Low | High | Medium |

## Related Roadmap Items

- [Incremental RAG Index Updates](./incremental-rag-index-updates.md) - HTTP conditional requests and partial index updates

## References

- [Reciprocal Rank Fusion (RRF)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [MS MARCO Cross-Encoders](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-12-v2)
- [ColBERT: Efficient and Effective Passage Search](https://arxiv.org/abs/2004.12832)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)

---

*Created: 2025-11-28*
