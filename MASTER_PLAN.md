# CrawlCraft: Master Implementation Plan

> Asynchronous web crawler and semantic markdown synthesizer for LLM knowledge bases and RAG pipelines.
> Parses modern web pages with C-based HTML parsing (Selectolax / Modest engine), removes boilerplate and advertisement containers, preserves tables and syntax-highlighted code blocks, extracts structured metadata (JSON-LD, OpenGraph), calculates cl100k_base token counts, and switches to headless Chromium only when Single Page Application (SPA) shells are detected.

---

## 1. System Architecture

```
+-----------------------------------------------------------------------------------+
|                                    CRAWLCRAFT                                     |
+-----------------------------------------+-----------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
+-------v-------------------------+                 +-----------------------v-------+
|   Async HTTP/2 Crawler Engine   |                 |     SPA Fallback Worker       |
|  * Asyncio + HTTPX Concurrency  |                 |  * Playwright Headless Lazy   |
|  * Robots.txt & Token Bucket    |                 |  * DOM Hydration Detection    |
|  * Bounded BFS / Domain Scoping |                 |  * Anti-Bot Header Rotation   |
+-------+-------------------------+                 +-----------------------+-------+
        |                                                                   |
        +---------------------------------+---------------------------------+
                                          |
                        +-----------------v-----------------+
                        |   Semantic Markdown Synthesizer   |
                        |  * C-Based HTML5 (Selectolax)     |
                        |  * Boilerplate & Ad Removal       |
                        |  * Table & Code Block Fidelity    |
                        +-----------------+-----------------+
                                          |
                        +-----------------v-----------------+
                        |   Metadata & Token Estimator      |
                        |  * JSON-LD & OpenGraph Extractor  |
                        |  * Tiktoken cl100k_base Counter   |
                        |  * SimHash Content Deduplication  |
                        +-----------------+-----------------+
                                          |
                        +-----------------v-----------------+
                        |   Local REST API & Web Studio     |
                        |  * FastAPI + SSE Live Stream      |
                        |  * Markdown Preview & Diff        |
                        |  * Directory & JSONL Exporter     |
                        +-----------------------------------+
```

---

## 2. Directory Layout

```
crawlcraft/
├── crawlcraft/
│   ├── __init__.py
│   ├── cli.py                     # Typer CLI commands (crawl, extract, serve, benchmark)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── crawler.py             # Async bounded BFS crawler orchestrator
│   │   ├── http_client.py         # HTTPX client with HTTP/2 and header rotation
│   │   ├── rate_limiter.py        # Token-bucket rate limiter per domain
│   │   ├── robots.py              # Asynchronous robots.txt fetcher and cache
│   │   └── deduplicator.py        # URL normalization and 64-bit SimHash deduplication
│   ├── extractor/
│   │   ├── __init__.py
│   │   ├── html_cleaner.py        # Selectolax tree pruner (removes nav, ads, scripts)
│   │   ├── markdown.py            # AST to clean GitHub Flavored Markdown converter
│   │   ├── tables.py              # HTML table to clean Markdown table parser
│   │   └── metadata.py            # JSON-LD, OpenGraph, Dublin Core and token estimator
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── spa_detector.py        # Heuristic detector for JS-rendered empty shells
│   │   └── headless_pool.py       # Lazy Playwright browser pool for dynamic pages
│   └── server/
│       ├── __init__.py
│       ├── app.py                 # FastAPI application setup and lifecycle
│       ├── models.py              # Pydantic schemas for requests and responses
│       ├── routes.py              # Endpoints: /v1/extract, /v1/crawl, /v1/crawl/{id}/stream
│       └── sse.py                 # Server-Sent Events streaming helper
├── web/                           # React 19 + TypeScript + Vite frontend
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── index.css
│       ├── types.ts
│       └── components/
│           ├── LiveCrawlConsole.tsx
│           ├── MarkdownPreview.tsx
│           ├── MetadataViewer.tsx
│           └── RAGTokenStats.tsx
├── tests/
│   ├── test_crawler.py
│   ├── test_extractor.py
│   ├── test_markdown.py
│   ├── test_metadata.py
│   ├── test_spa_detector.py
│   └── test_api.py
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## 3. Implementation Plan & Milestones

### Milestone 1: Core Crawl Engine
- [x] Configure Python 3.12 project structure, virtual environment, and dependencies (`pyproject.toml`, `.gitignore`).
- [ ] Implement `crawlcraft/core/http_client.py`:
  - Asynchronous HTTPX client with HTTP/2 support.
  - Realistic browser headers (User-Agent, Sec-Ch-Ua, Accept-Language, Accept-Encoding).
  - Configurable timeouts, redirection following, and SSL handling.
- [ ] Implement `crawlcraft/core/rate_limiter.py`:
  - Token-bucket algorithm with per-domain tracking.
  - Smooth request throttling without thread blocking.
- [ ] Implement `crawlcraft/core/robots.py`:
  - Non-blocking robots.txt fetcher with caching and wildcard matching.
- [ ] Implement `crawlcraft/core/deduplicator.py`:
  - Query parameter normalization (removes utm_*, fbclid, ref, trackers).
  - 64-bit SimHash generation to flag duplicate body text across distinct URLs.
- [ ] Implement `crawlcraft/core/crawler.py`:
  - Asynchronous bounded BFS crawl orchestrator.
  - Bounded concurrency with `asyncio.Semaphore`.
  - Max depth, max page count, domain scoping.
  - Real-time event hooks for streaming progress.

### Milestone 2: C-Based HTML Parser & Semantic Markdown Synthesizer
- [ ] Implement `crawlcraft/extractor/html_cleaner.py`:
  - C-based parsing via `selectolax.parser.HTMLParser`.
  - Prunes structural clutter: `<script>`, `<style>`, `<noscript>`, `<svg>`, `<header>`, `<footer>`, `<nav>`, `<aside>`, `<form>`, cookie consent modals, ad banners.
  - Main content detection based on text-to-tag ratio and semantic wrappers (`<article>`, `<main>`, `role="main"`).
- [ ] Implement `crawlcraft/extractor/tables.py`:
  - Converts HTML tables into clean GFM pipe-delimited tables.
  - Handles header rows, cell text sanitization (strips raw linebreaks), and column alignments.
- [ ] Implement `crawlcraft/extractor/markdown.py`:
  - Converts pruned DOM tree into clean GitHub Flavored Markdown.
  - Headings `#` through `######` with correct spacing.
  - Code blocks with language detection (`<pre><code class="language-python">`).
  - Lists (ordered, unordered, nested).
  - Math block protection (LaTeX `$...$`, `$$...$$`, KaTeX, MathJax).
  - Absolute URL resolution for links and images based on document base URL.
- [ ] Implement `crawlcraft/extractor/metadata.py`:
  - Extracts Schema.org JSON-LD scripts (`<script type="application/ld+json">`).
  - Extracts OpenGraph meta tags (`og:title`, `og:description`, `og:image`, `og:url`, `og:type`).
  - Standard meta tags (author, canonical URL, publication date, description).
  - Token calculations using `tiktoken` with `cl100k_base` encoding, word counts, and reading time estimates.

### Milestone 3: Intelligent SPA Detection & Lazy Headless Fallback
- [ ] Implement `crawlcraft/browser/spa_detector.py`:
  - Fast heuristic checks on raw HTML:
    - Text length threshold (< 250 characters of non-nav text).
    - Client-side framework mounting roots (`<div id="root"></div>`, `<div id="__next"></div>`, `<app-root></app-root>`).
    - Standard JS requirement messages ("Please enable JavaScript to view this page").
- [ ] Implement `crawlcraft/browser/headless_pool.py`:
  - Lazy initialization of Playwright Chromium.
  - Browser context reuse with concurrency limits.
  - Waits for network idle (`networkidle`) or DOM hydration.
  - Extracts fully rendered HTML and passes it back to the Selectolax pipeline.
  - Graceful fallback with diagnostic flags if browser engine cannot start.

### Milestone 4: FastAPI REST API & Server-Sent Events
- [ ] Implement `crawlcraft/server/models.py`:
  - Pydantic models for single extraction requests, crawl jobs, crawl status, and streamed events.
- [ ] Implement `crawlcraft/server/sse.py`:
  - SSE formatting generator for streaming crawl progress.
- [ ] Implement `crawlcraft/server/routes.py` and `app.py`:
  - `POST /v1/extract`: Immediate extraction for a single URL or raw HTML string.
  - `POST /v1/crawl`: Start background crawl task, returning job ID.
  - `GET /v1/crawl/{job_id}/status`: Query current metrics and queue size.
  - `GET /v1/crawl/{job_id}/stream`: Real-time SSE stream of crawled documents.
  - `GET /v1/crawl/{job_id}/export`: Export crawled results in JSONL or Markdown formats.
  - `GET /v1/health`: Service health and capability diagnostics.

### Milestone 5: Typer Command-Line Interface (CLI)
- [ ] Implement `crawlcraft/cli.py`:
  - `crawlcraft extract <url> [--output file.md] [--browser/--no-browser]`
  - `crawlcraft crawl <url> [--depth 2] [--max-pages 50] [--output ./output] [--concurrency 5] [--format jsonl]`
  - `crawlcraft serve [--host 127.0.0.1] [--port 8000]`
  - `crawlcraft benchmark <url>`: Measures parsing speed and token counts.

### Milestone 6: React 19 Frontend Web Studio
- [ ] Set up Vite + React 19 + TypeScript in `web/`.
- [ ] Build interactive crawl configuration and URL input interface.
- [ ] Implement real-time crawl telemetry console (pages/sec, tokens accumulated, status codes).
- [ ] Implement split-pane document inspector:
  - Rendered Markdown view with copy action.
  - Raw Markdown view.
  - Extracted JSON-LD and OpenGraph metadata inspection.
  - Token and density metrics.
- [ ] Implement dataset export controls (JSONL download, combined Markdown).

### Milestone 7: Automated Test Suite & Verification
- [ ] Unit tests for Selectolax DOM cleaner and noise removal.
- [ ] Unit tests for GFM table and code block conversion.
- [ ] Unit tests for JSON-LD, OpenGraph, and token calculation.
- [ ] Unit tests for SPA detection heuristics.
- [ ] Integration tests for crawler BFS, rate limiter, and robots.txt handling using a local mock HTTP server.
- [ ] Integration tests for FastAPI endpoints and SSE stream.
