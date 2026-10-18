"""CrawlCraft Command-Line Interface (CLI)."""

import asyncio
import json
from pathlib import Path
import time
from typing import Optional
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
from crawlcraft.extractor.markdown import html_to_markdown
from crawlcraft.extractor.metadata import extract_metadata

app = typer.Typer(
    name="crawlcraft",
    help="High-throughput async web crawler and semantic markdown synthesizer for LLMs and RAG.",
    add_completion=False,
)
console = Console(legacy_windows=False)


@app.command()
def extract(
    url: str = typer.Argument(..., help="Target URL to fetch and convert to Markdown"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Optional path to write markdown file"),
    browser: bool = typer.Option(True, "--browser/--no-browser", help="Allow fallback to Playwright Chromium on SPAs"),
    main_only: bool = typer.Option(True, "--main-only/--full", help="Prune navigation, ads, and footers"),
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

            md = html_to_markdown(html, base_url=url, extract_main_only=main_only)
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

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(md, encoding="utf-8")
            console.print(f"[bold green]Saved Markdown to:[/] {output}")
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
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (.jsonl or .md)"),
    format: str = typer.Option("jsonl", "--format", "-f", help="Output format: jsonl or markdown"),
    same_domain: bool = typer.Option(True, "--same-domain/--cross-domain", help="Restrict crawl to initial domain"),
    browser: bool = typer.Option(True, "--browser/--no-browser", help="Allow headless fallback on SPA shells"),
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
            if format.lower() == "markdown" or str(output).endswith(".md"):
                doc = "\n\n---\n\n".join(
                    f"# {p.metadata.title or p.url}\n\n**Source:** {p.url}\n\n{p.markdown}" for p in results
                )
                output.write_text(doc, encoding="utf-8")
            else:
                lines = [json.dumps(p.to_dict()) for p in results]
                output.write_text("\n".join(lines), encoding="utf-8")
            console.print(f"[bold green]Dataset saved to:[/] {output}")

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
