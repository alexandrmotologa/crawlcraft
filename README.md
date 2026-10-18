<div align="center">
  <img src="docs/images/crawlcraft_logo.svg" alt="CrawlCraft Mark" width="130" height="130" />
  <h1>CrawlCraft</h1>
  <p><strong>Headless-free asynchronous web crawler and semantic markdown synthesizer for LLM knowledge bases and RAG pipelines.</strong></p>

  <p>
    <a href="https://github.com/alexandrmotologa/crawlcraft/actions"><img src="https://img.shields.io/badge/tests-33%20passed-10b981?style=flat-square" alt="Tests"></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.12-38bdf8?style=flat-square" alt="Python 3.12"></a>
    <a href="https://react.dev"><img src="https://img.shields.io/badge/react-19-61dafb?style=flat-square" alt="React 19"></a>
    <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/fastapi-0.110+-059669?style=flat-square" alt="FastAPI"></a>
    <a href="https://github.com/alexandrmotologa/crawlcraft/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-slate?style=flat-square" alt="License"></a>
  </p>
</div>

---

## Overview

Ingesting clean web text for Retrieval-Augmented Generation (RAG) pipelines and LLM agents usually forces a tradeoff between two approaches:
1. Cloud scraper services that bill on recurring subscriptions per API credit.
2. Full headless browser automation (Playwright or Puppeteer) that uses substantial RAM per tab and introduces latency on static pages.

CrawlCraft provides a local alternative. It runs an asynchronous HTTP/2 network engine coupled to a C-based HTML parser (Selectolax / Lexbor) that processes pages in under 1 millisecond. It parses semantic content, strips advertisements and cookie banners, preserves tables and syntax-highlighted code blocks, extracts structured metadata (JSON-LD, OpenGraph), and computes exact token counts (`cl100k_base`). A headless Chromium browser instance is only launched when the engine detects an empty Single Page Application (SPA) shell requiring client-side JavaScript execution.

---

## Live Studio & Architecture

The web interface is built with responsive breakpoints for desktop, tablet, and mobile displays.

![CrawlCraft Desktop Studio](docs/images/crawlcraft_dashboard.png)

<div align="center">
  <img src="docs/images/crawlcraft_mobile.png" alt="CrawlCraft Mobile Viewport" width="320" />
</div>

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
|  * Sitemap & RSS Feed Discovery |                 |                               |
+-------+-------------------------+                 +-----------------------+-------+
        |                                                                   |
        +---------------------------------+---------------------------------+
                                          |
                        +-----------------v-----------------+
                        |   Semantic Markdown Synthesizer   |
                        |  * C-Based HTML5 (Selectolax)     |
                        |  * Boilerplate & Ad Removal       |
                        |  * CSS Whitelist/Blacklist Select |
                        |  * Table & Code Block Fidelity    |
                        +-----------------+-----------------+
                                          |
                        +-----------------v-----------------+
                        |   RAG Chunking & Token Estimator  |
                        |  * Hierarchical Header Breadcrumbs|
                        |  * Tiktoken cl100k_base Counter   |
                        |  * SimHash Content Deduplication  |
                        |  * Prompt Pack Generator (XML/MD) |
                        +-----------------+-----------------+
                                          |
                        +-----------------v-----------------+
                        |   Local REST API & Web Studio     |
                        |  * FastAPI + SSE Live Stream      |
                        |  * Markdown Preview & RAG Chunks  |
                        |  * JSONL / Chunks / LLM Exporter  |
                        +-----------------------------------+
```

---

## Animated Demonstration

![CrawlCraft Live Demo](docs/images/crawlcraft_demo.gif)

---

## Performance

Benchmarking C-based Selectolax parsing against full headless browser execution on the identical HTML payload (tested on 3.8 GHz AMD Ryzen, Windows 11):

| Pipeline | Average Latency | Throughput | Notes |
|:---|:---:|:---:|:---|
| **CrawlCraft Selectolax Engine** | **0.53 ms** | **~1,890 pages/sec/core** | Direct C-tree DOM traversal, memory footprint < 15MB |
| **Playwright Chromium Headless** | 857.58 ms | ~1.2 pages/sec/core | Full V8 execution, DOM tree allocation, GPU emulation |

*Result: The C-based parser completes document conversion ~1,600 times faster than full headless browser instantiation.*

---

## Key Features

- **Dual-Engine Routing**: Runs HTTP/2 requests with realistic browser header rotation by default. Analyzes DOM text density and known framework mount roots (`#root`, `#app`, `#__next`) to identify unhydrated pages, deploying Chromium only when JavaScript is required.
- **Hierarchical RAG Chunking**: Breaks Markdown documents into token-bounded chunks preserving heading breadcrumb hierarchies (`# Section > ## Subsection`) and keeping code blocks and tables intact.
- **Prompt Pack Context Generator**: Compiles crawled web documents into structured XML packages with manifests and CDATA delimiters, or clean Markdown tables with system directives ready for LLM prompts.
- **Sitemap & Feed Auto-Discovery**: Automatically discovers and parses XML sitemaps, gzipped `.xml.gz` sitemaps, sitemap indexes, and RSS/Atom feeds to seed the crawl queue.
- **CSS Whitelist and Blacklist Selectors**: Isolate target containers (`--include-selector`) or strip project-specific banners and widgets (`--exclude-selector`).
- **GFM Table and Code Preservation**: Converts HTML tables to aligned GitHub Flavored Markdown tables with cell sanitization. Extracts programming language classes (`language-python`, `lang-ts`) on code blocks.
- **Noise and Banner Stripping**: Decomposes cookie consent dialogs, newsletter subscription boxes, tracking pixels, navigation menus, and footers.
- **RAG Metadata and Token Estimation**: Parses Schema.org JSON-LD scripts, OpenGraph attributes, Dublin Core elements, and computes exact token counts using `tiktoken` (`cl100k_base` model encoding).
- **Near-Duplicate Detection**: Implements 64-bit SimHash fingerprints with Hamming distance comparisons to avoid re-indexing duplicated or slightly modified pages.
- **Polite Crawling**: Per-domain token bucket rate limiting prevents target server saturation. Asynchronous robots.txt manager respects Allow and Disallow rules.
- **Interactive Web Studio**: Built with React 19, TypeScript, and Vite. Streams real-time crawling metrics, page events, and hierarchical chunk inspections.

---

## Installation

### Prerequisites
- Python 3.12 or later
- Node.js 18+ (for modifying or rebuilding the web interface)

```bash
# Clone the repository
git clone https://github.com/alexandrmotologa/crawlcraft.git
cd crawlcraft

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install package dependencies
pip install -e .

# Install headless browser binaries for SPA fallback
playwright install chromium
```

---

## Usage

### 1. Command-Line Interface (CLI)

#### Single Page Extraction
Convert any web page or documentation article into clean Markdown:
```bash
crawlcraft extract "https://docs.python.org/3/tutorial/index.html" -o tutorial.md
```

Extract with hierarchical RAG chunks:
```bash
crawlcraft extract "https://docs.python.org/3/tutorial/index.html" --format chunks --chunk-size 512 -o chunks.json
```

#### Sitemap & Feed Discovery
Discover and extract all indexed URLs from a website:
```bash
crawlcraft sitemap "https://example.com" --limit 100 --output sitemap_urls.txt
```

#### Multi-Page Bounded Crawl
Run a bounded BFS crawl with concurrency caps and export directly to JSONL:
```bash
crawlcraft crawl "https://example.com" --depth 2 --max-pages 50 --concurrency 8 --output dataset.jsonl
```

Crawl seeded from sitemaps and export structured LLM prompt context:
```bash
crawlcraft crawl "https://example.com" --sitemap --max-pages 30 --format llm --output context_pack.xml
```

#### Speed Benchmark
Measure processing latency between HTTP/2 C-parsing and headless Chromium on a specific URL:
```bash
crawlcraft benchmark "https://example.com" --iterations 5
```

---

## 2. Running the REST API & Web Studio

Start the FastAPI daemon:
```bash
crawlcraft serve --host 127.0.0.1 --port 8000
```

Open `http://localhost:8000` in your browser to access the React 19 studio interface.

#### REST API Endpoints

- **`POST /v1/extract`**: Synchronous extraction for a single URL or raw HTML string.
```bash
curl -X POST "http://127.0.0.1:8000/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "allow_spa_fallback": true}'
```

- **`POST /v1/crawl`**: Start an asynchronous multi-page crawl job. Returns a `job_id`.
```bash
curl -X POST "http://127.0.0.1:8000/v1/crawl" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"], "max_depth": 2, "max_pages": 20, "concurrency": 6}'
```

- **`GET /v1/crawl/{job_id}/stream`**: Server-Sent Events stream emitting pages as they finish crawling.
- **`GET /v1/crawl/{job_id}/export?format=jsonl|markdown|chunks|llm_prompt`**: Download the full crawl dataset in the desired format.
- **`POST /v1/sitemap`**: Parse and discover URLs from sitemaps or feeds.
- **`GET /v1/health`**: Healthcheck and system capability diagnostics.

---

## 3. Python Library Usage

```python
import asyncio
from crawlcraft.core.crawler import AsyncCrawler, CrawlConfig
from crawlcraft.extractor.chunker import chunk_markdown
from crawlcraft.extractor.prompt_pack import pack_pages_for_llm

# Programmatic Crawler execution
async def run_crawler():
    config = CrawlConfig(
        start_urls=["https://example.com"],
        max_depth=2,
        max_pages=20,
        concurrency=4,
        requests_per_second=5.0,
        from_sitemap=True,
    )
    crawler = AsyncCrawler(config)
    pages = await crawler.run()
    
    # Generate RAG chunks
    for page in pages:
        chunks = chunk_markdown(page.markdown, max_tokens=512)
        print(f"URL: {page.url} -> {len(chunks)} chunks")

    # Pack into LLM XML prompt block
    xml_pack = pack_pages_for_llm(pages, format_type="xml")
    print(f"Packed {len(pages)} pages into XML knowledge base")

asyncio.run(run_crawler())
```

---

## Test Suite

Run the automated test suite with pytest:
```bash
pytest -v
```

The test suite contains 33 automated tests covering:
- HTML cleaning, ad pruning, structural boilerplate removal, and custom CSS selectors.
- GFM table parsing, code block language retention, and LaTeX math protection.
- OpenGraph tags, Dublin Core, and Schema.org JSON-LD extraction.
- Tiktoken `cl100k_base` estimation accuracy.
- Hierarchical RAG chunking and heading breadcrumbs.
- XML sitemaps, sitemap indexes, gzipped sitemaps, and RSS/Atom feed parsing.
- LLM prompt context packaging in XML and Markdown formats.
- SPA detection heuristics on empty root elements.
- URL parameter normalization and 64-bit SimHash Hamming distance checks.
- FastAPI endpoints, background tasks, and health probes.

---

## License

This project is distributed under the [MIT License](LICENSE).
