"""CrawlCraft Command-Line Interface (CLI)."""

import asyncio
import json
from pathlib import Path
import time
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
import typer
import uvicorn

import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from crawlcraft import __version__
from crawlcraft.browser.headless_pool import HeadlessBrowserPool
from crawlcraft.browser.spa_detector import detect_spa_shell
from crawlcraft.core.crawler import AsyncCrawler, CrawlConfig, CrawledPage
from crawlcraft.core.http_client import AsyncHttpClient
from crawlcraft.core.sitemap import discover_and_parse_sitemaps
from crawlcraft.extractor.chunker import chunk_markdown
from crawlcraft.extractor.markdown import html_to_markdown
from crawlcraft.extractor.metadata import extract_metadata
from crawlcraft.extractor.prompt_pack import pack_pages_for_llm

app = typer.Typer(
    name="crawlcraft",
    help="High-throughput async web crawler and semantic markdown synthesizer for LLMs and RAG.",
    add_completion=False,
)
console = Console(legacy_windows=False)


@app.command()
def extract(
    url: str = typer.Argument(..., help="Target URL to fetch and convert to Markdown"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Optional path to write markdown/json file"),
    browser: bool = typer.Option(True, "--browser/--no-browser", help="Allow fallback to Playwright Chromium on SPAs"),
    main_only: bool = typer.Option(True, "--main-only/--full", help="Prune navigation, ads, and footers"),
    include_selector: Optional[List[str]] = typer.Option(None, "--include-selector", "-i", help="CSS selector(s) to isolate specific containers"),
    exclude_selector: Optional[List[str]] = typer.Option(None, "--exclude-selector", "-e", help="CSS selector(s) to remove unwanted elements"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown, json, or chunks"),
    chunk_size: int = typer.Option(512, "--chunk-size", help="Max tokens per chunk when using chunks format"),
) -> None:
    """Extract clean Markdown, metadata, and token counts from a single web page."""
    async def _run():
        with console.status(f"[bold cyan]Fetching and synthesizing {url}..."):
            start_t = time.perf_counter()
            rendered_with = "http2"

            async with AsyncHttpClient() as client:
                resp = await client.get(url)
                if not resp.is_success:
                    console.print(f"[bold red]Fetch error:[/] {resp.error_message or resp.status_code}")
                    raise typer.Exit(1)
                html = resp.text
                rendered_with = resp.http_version

            if browser:
                is_spa, reason = detect_spa_shell(html)
                if is_spa:
                    console.print(f"[yellow]SPA shell detected ({reason}). Launching headless Chromium...[/]")
                    pool = HeadlessBrowserPool()
                    try:
                        rendered_html = await pool.render_url(url)
                        if rendered_html:
                            html = rendered_html
                            rendered_with = "playwright_chromium"
                    finally:
                        await pool.close()

            md = html_to_markdown(
                html,
                base_url=url,
                extract_main_only=main_only,
                include_selectors=include_selector,
                exclude_selectors=exclude_selector,
            )
            meta = extract_metadata(html, url=url, text_content=md)
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        stats = meta.token_stats
        table = Table(title="Extraction Telemetry", show_header=True, header_style="bold green")
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="bold")
        table.add_row("URL", url)
        table.add_row("Title", meta.title or "(None)")
        table.add_row("Engine", rendered_with)
        table.add_row("Tokens (cl100k_base)", f"{stats.get('token_count', 0):,}")
        table.add_row("Words", f"{stats.get('word_count', 0):,}")
        table.add_row("Elapsed Time", f"{elapsed_ms:.1f} ms")
        console.print(table)

        chunks_list = []
        if format.lower() == "chunks":
            chunks_list = chunk_markdown(
                md,
                max_tokens=chunk_size,
                doc_id=url,
                metadata={"title": meta.title, "url": url},
            )
            console.print(f"[bold cyan]Hierarchical Chunks Created:[/] {len(chunks_list)} chunks")

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            if format.lower() == "json":
                data = {
                    "url": url,
                    "title": meta.title,
                    "description": meta.description,
                    "metadata": meta.to_dict(),
                    "markdown": md,
                }
                output.write_text(json.dumps(data, indent=2), encoding="utf-8")
            elif format.lower() == "chunks":
                output.write_text(json.dumps([c.to_dict() for c in chunks_list], indent=2), encoding="utf-8")
            else:
                output.write_text(md, encoding="utf-8")
            console.print(f"[bold green]Saved output to:[/] {output}")
        else:
            if format.lower() == "chunks":
                for c in chunks_list[:3]:
                    crumbs = " > ".join(c.breadcrumbs) if c.breadcrumbs else "Root"
                    console.print(Panel(c.content, title=f"Chunk #{c.index + 1} ({crumbs}) [{c.token_count} tokens]", border_style="green"))
                if len(chunks_list) > 3:
                    console.print(f"[dim]... and {len(chunks_list) - 3} more chunks[/]")
            else:
                preview = md[:1200] + ("\n...[truncated for display]" if len(md) > 1200 else "")
                console.print(Panel(preview, title="Markdown Preview", border_style="cyan"))

    asyncio.run(_run())


@app.command()
def crawl(
    url: str = typer.Argument(..., help="Seed URL to start the bounded crawl"),
    depth: int = typer.Option(2, "--depth", "-d", help="Maximum BFS link crawl depth"),
    max_pages: int = typer.Option(30, "--max-pages", "-n", help="Maximum number of pages to crawl"),
    concurrency: int = typer.Option(8, "--concurrency", "-c", help="Simultaneous request concurrency"),
    rps: float = typer.Option(5.0, "--rps", help="Politeness rate limit in requests per second"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (.jsonl, .md, .xml, .json)"),
    format: str = typer.Option("jsonl", "--format", "-f", help="Output format: jsonl, markdown, chunks, or llm"),
    same_domain: bool = typer.Option(True, "--same-domain/--cross-domain", help="Restrict crawl to initial domain"),
    browser: bool = typer.Option(True, "--browser/--no-browser", help="Allow headless fallback on SPA shells"),
    sitemap: bool = typer.Option(False, "--sitemap/--no-sitemap", help="Discover and seed crawl queue from sitemap.xml / feeds"),
    include_selector: Optional[List[str]] = typer.Option(None, "--include-selector", "-i", help="CSS selector(s) to isolate specific containers"),
    exclude_selector: Optional[List[str]] = typer.Option(None, "--exclude-selector", "-e", help="CSS selector(s) to prune unwanted elements"),
    chunk_size: int = typer.Option(512, "--chunk-size", help="Max tokens per chunk when using chunks format"),
    webhook_url: Optional[str] = typer.Option(None, "--webhook-url", help="URL to send completion notification payload"),
) -> None:
    """Perform a high-speed multi-page crawl with rate limiting and deduplication."""
    async def _run():
        config = CrawlConfig(
            start_urls=[url],
            max_depth=depth,
            max_pages=max_pages,
            concurrency=concurrency,
            requests_per_second=rps,
            same_domain_only=same_domain,
            allow_spa_fallback=browser,
            seed_from_sitemaps=sitemap,
            include_selectors=include_selector or [],
            exclude_selectors=exclude_selector or [],
            webhook_url=webhook_url,
        )

        pages_crawled = 0
        total_tokens = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            crawl_task = progress.add_task(f"[cyan]Crawling {url}...", total=max_pages)

            async def on_page_scraped(page: CrawledPage):
                nonlocal pages_crawled, total_tokens
                pages_crawled += 1
                page_tokens = page.metadata.token_stats.get("token_count", 0)
                total_tokens += page_tokens
                progress.update(
                    crawl_task,
                    advance=1,
                    description=f"[cyan]Scraped:[/] {page.url[:45]}... ({page_tokens:,} tokens)",
                )

            crawler = AsyncCrawler(config=config, on_page=on_page_scraped)
            start_t = time.perf_counter()
            results = await crawler.run()
            total_elapsed = time.perf_counter() - start_t

        console.print(f"\n[bold green]Crawl Completed in {total_elapsed:.2f} seconds![/]")
        console.print(f"Pages indexed: [bold]{len(results)}[/] | Total RAG tokens: [bold]{total_tokens:,}[/]")

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            fmt = format.lower()
            if fmt == "markdown" or str(output).endswith(".md"):
                doc = "\n\n---\n\n".join(
                    f"# {p.metadata.title or p.url}\n\n**Source:** {p.url}\n\n{p.markdown}" for p in results
                )
                output.write_text(doc, encoding="utf-8")
            elif fmt in ("llm", "xml", "prompt"):
                xml_pack = pack_pages_for_llm(results, format_type="xml")
                output.write_text(xml_pack, encoding="utf-8")
            elif fmt == "chunks":
                all_chunks = []
                for p in results:
                    chunks = chunk_markdown(
                        p.markdown,
                        max_tokens=chunk_size,
                        doc_id=p.url,
                        metadata={"title": p.metadata.title, "url": p.url},
                    )
                    all_chunks.extend([c.to_dict() for c in chunks])
                if str(output).endswith(".json"):
                    output.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")
                else:
                    output.write_text("\n".join(json.dumps(c) for c in all_chunks), encoding="utf-8")
                console.print(f"[bold cyan]Generated {len(all_chunks)} hierarchical RAG chunks.[/]")
            else:
                lines = [json.dumps(p.to_dict()) for p in results]
                output.write_text("\n".join(lines), encoding="utf-8")
            console.print(f"[bold green]Dataset saved to:[/] {output}")

    asyncio.run(_run())


@app.command()
def sitemap(
    url: str = typer.Argument(..., help="Website domain or sitemap XML / RSS feed URL"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum URLs to discover"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Optional output path (.json or .txt)"),
) -> None:
    """Discover, parse, and list URLs from sitemap.xml or RSS/Atom feeds."""
    async def _run():
        with console.status(f"[bold cyan]Discovering and parsing sitemaps for {url}..."):
            discovered = await discover_and_parse_sitemaps(url, max_urls=limit)

        if not discovered:
            console.print(f"[bold yellow]No URLs discovered via sitemap or feed for {url}[/]")
            return

        table = Table(title=f"Discovered Sitemap URLs ({len(discovered)})", show_header=True, header_style="bold blue")
        table.add_column("#", style="dim", width=4)
        table.add_column("URL", style="bold")
        table.add_column("Lastmod", style="cyan")
        table.add_column("Priority", style="magenta")

        for idx, item in enumerate(discovered[:25], 1):
            table.add_row(
                str(idx),
                item.url,
                item.lastmod or "-",
                str(item.priority) if item.priority is not None else "-",
            )

        console.print(table)
        if len(discovered) > 25:
            console.print(f"[dim]... and {len(discovered) - 25} more URLs[/]")

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            if str(output).endswith(".json"):
                output.write_text(json.dumps([item.to_dict() for item in discovered], indent=2), encoding="utf-8")
            else:
                output.write_text("\n".join(item.url for item in discovered), encoding="utf-8")
            console.print(f"[bold green]Saved sitemap list to:[/] {output}")

    asyncio.run(_run())


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable code autoreload for development"),
) -> None:
    """Launch the CrawlCraft FastAPI daemon and web studio."""
    console.print(f"[bold cyan]Launching CrawlCraft Server on http://{host}:{port}...[/]")
    uvicorn.run("crawlcraft.server.app:app", host=host, port=port, reload=reload)


@app.command()
def benchmark(
    url: str = typer.Argument(..., help="URL to benchmark"),
    iterations: int = typer.Option(5, "--iterations", "-i", help="Number of benchmark iterations"),
) -> None:
    """Measure Selectolax C-parsing vs Playwright browser execution speeds."""
    async def _run():
        console.print(f"[bold cyan]Benchmarking {url} ({iterations} iterations)...[/]")

        async with AsyncHttpClient() as client:
            resp = await client.get(url)
            if not resp.is_success:
                console.print(f"[bold red]Failed to fetch benchmark URL:[/] {resp.error_message}")
                raise typer.Exit(1)
            raw_html = resp.text

        # Measure Selectolax parse and markdown conversion
        selectolax_times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            md = html_to_markdown(raw_html, base_url=url)
            meta = extract_metadata(raw_html, text_content=md)
            selectolax_times.append((time.perf_counter() - t0) * 1000.0)

        # Measure Playwright headless render
        pool = HeadlessBrowserPool()
        playwright_times = []
        try:
            for _ in range(iterations):
                t0 = time.perf_counter()
                await pool.render_url(url)
                playwright_times.append((time.perf_counter() - t0) * 1000.0)
        finally:
            await pool.close()

        avg_c = sum(selectolax_times) / len(selectolax_times)
        avg_play = sum(playwright_times) / len(playwright_times)
        speedup = avg_play / max(0.1, avg_c)

        table = Table(title="Benchmark Comparison", show_header=True, header_style="bold magenta")
        table.add_column("Pipeline")
        table.add_column("Average Latency")
        table.add_column("Est. Max Throughput")
        table.add_row("Selectolax C Engine", f"{avg_c:.2f} ms", f"{1000.0 / avg_c:.0f} pages/sec/core")
        table.add_row("Playwright Headless", f"{avg_play:.2f} ms", f"{1000.0 / avg_play:.1f} pages/sec/core")
        console.print(table)
        console.print(f"[bold green]Selectolax is {speedup:.1f}x faster than full headless browser execution![/]")

    asyncio.run(_run())


@app.command()
def version() -> None:
    """Display CrawlCraft version information."""
    console.print(f"CrawlCraft version: [bold cyan]{__version__}[/]")


if __name__ == "__main__":
    app()
