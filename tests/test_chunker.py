"""Unit tests for the hierarchical Markdown chunker."""

import pytest
from crawlcraft.extractor.chunker import MarkdownChunker, chunk_markdown


SAMPLE_MARKDOWN = """# Introduction to CrawlCraft

CrawlCraft is a high-performance web crawling engine engineered specifically for LLM knowledge extraction.

## Core Architecture

The crawler combines asynchronous HTTP/2 network dispatch with compiled C-based DOM parsing.

### Network Layer

HTTP/2 client supports pipelined requests, transparent Brotli decompression, and per-domain token bucket rate limiting.

### Extraction Pipeline

Selectolax Lexbor engine strips boilerplate, cookie banners, navigation links, and converts the clean tree into GFM Markdown.

## Features and Capabilities

Here is a summary table of capabilities:

| Feature | Selectolax Engine | Playwright Fallback |
| :--- | :--- | :--- |
| Speed | 0.5 ms per page | 800 ms per page |
| Memory | Low (C bindings) | High (Chromium process) |
| JavaScript | Static DOM | Full V8 engine |

```python
from crawlcraft import AsyncCrawler, CrawlConfig

config = CrawlConfig(start_urls=["https://example.com"], max_pages=10)
crawler = AsyncCrawler(config)
```

## Conclusion

CrawlCraft minimizes LLM context window costs while maximizing extraction precision.
"""


def test_chunker_hierarchical_breadcrumbs():
    chunker = MarkdownChunker(max_tokens=60, overlap_tokens=0)
    chunks = chunker.chunk_document(SAMPLE_MARKDOWN, doc_id="https://crawlcraft.dev/docs")

    assert len(chunks) >= 3
    # First chunk should have Introduction breadcrumb
    assert "Introduction to CrawlCraft" in chunks[0].breadcrumbs

    # Find the chunk containing Network Layer
    network_chunk = next((c for c in chunks if "Network Layer" in c.content), None)
    assert network_chunk is not None
    assert "Introduction to CrawlCraft" in network_chunk.breadcrumbs
    assert "Core Architecture" in network_chunk.breadcrumbs
    assert "Network Layer" in network_chunk.breadcrumbs


def test_chunker_token_limit_enforced():
    max_tokens = 60
    chunker = MarkdownChunker(max_tokens=max_tokens, overlap_tokens=10)
    chunks = chunker.chunk_document(SAMPLE_MARKDOWN, doc_id="test_doc")

    for chunk in chunks:
        # Each chunk should adhere strictly to the max token constraint (with small leeway for single large code words)
        assert chunk.token_count <= max_tokens + 15
        assert chunk.char_count > 0
        assert chunk.word_count > 0


def test_chunker_code_block_preservation():
    chunks = chunk_markdown(SAMPLE_MARKDOWN, max_tokens=150)
    code_chunk = next((c for c in chunks if "```python" in c.content), None)

    assert code_chunk is not None
    assert "AsyncCrawler" in code_chunk.content
    assert "```" in code_chunk.content


def test_chunk_markdown_convenience_function():
    metadata = {"category": "documentation", "author": "CrawlCraft Team"}
    chunks = chunk_markdown(SAMPLE_MARKDOWN, max_tokens=100, metadata=metadata)

    assert len(chunks) > 0
    first_dict = chunks[0].to_dict()
    assert first_dict["metadata"]["category"] == "documentation"
    assert "chunk_id" in first_dict
    assert "token_count" in first_dict
    assert "breadcrumbs" in first_dict
